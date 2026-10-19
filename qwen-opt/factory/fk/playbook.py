"""RSI-F playbooks (report 21h §5.3): a verified success rewritten as a technique recipe, never as a patch.

A playbook is playbooks/<id>.json. Content fields (written by a Rewriter in a fresh context):
  id            pb-<slug>
  title         one line
  technique     what the technique does and why it helps, in prose
  applies_when  [conditions that make it worth trying]      not_when  [conditions where it lost or broke]
  steps         [>= 3 steps from zero: profile, find the place, change, prove, measure]
  profiling     [commands or tools that show whether a kernel is a candidate]
  pitfalls      [what went wrong or nearly went wrong]       correctness  how to prove the class (BIT etc.)
  rules_fired   [factory rules that fired on the source claim]
  source        {"ledger_seq": n, "ledger_sha256": sha of the verdict row, "claim_id": id, "target": label}
  author, created (YYYY-MM-DD), expires (YYYY-MM-DD; R1 re-validation after a large rebase)
Library fields (only this module writes them): status, review, transfers, history.

Statuses and the evidence each transition needs (every transition is a ledger `note` row, so the history is
hash-chained with the verdicts it rests on):
  draft      the source row is a real-mode verdict CONFIRMED, or NEEDS-HUMAN whose stat_verdict is CONFIRMED and that
             a human approved (`human-approval` note). Partial gate passes (G0-G3 + NULL) never qualify.
  candidate  the no-diff review passed (review(): 0 diff 8-grams, 0 long diff lines, no new identifiers or commit
             hashes of the source patch, no sealed text, no measured numbers of the source as targets) AND a
             reviewer other than the author signed it.
  accepted   a FRESH agent (author differs from the playbook's and the source card's) given only the generated brief
             (fk/transfer.py) reached a CONFIRMED (or human-approved) verdict on a DIFFERENT target, arm A, with the
             brief whose sha256 is in the ledger for this playbook content.
  rejected   by a reviewer, or by kill criteria; terminal.
Changing the content after `candidate` changes content_sha256: the status falls back to draft until re-reviewed.
"""
from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path

from . import paths, sealed
from .diffscan import parse_unified
from .hashing import sha256_json
from .ledger import Ledger

CONTENT = ("id", "title", "technique", "applies_when", "not_when", "steps", "profiling", "pitfalls", "correctness",
           "rules_fired", "source", "author", "created", "expires")
LISTS = ("applies_when", "not_when", "steps", "profiling", "pitfalls", "rules_fired")
STATUSES = ("draft", "candidate", "accepted", "rejected")
ID_RE = re.compile(r"^pb-[a-z0-9][a-z0-9-]*$")
NGRAM = 8
LONG_LINE = 25
SUCCESS = ("CONFIRMED",)


class PlaybookError(Exception):
    pass


def path_of(pid: str) -> Path:
    return paths.PLAYBOOKS / f"{pid}.json"


def load(pid_or_path) -> dict:
    p = Path(pid_or_path)
    if not p.suffix:
        p = path_of(str(pid_or_path))
    return json.loads(p.read_text())


def save(pb: dict):
    paths.PLAYBOOKS.mkdir(parents=True, exist_ok=True)
    path_of(pb["id"]).write_text(json.dumps(pb, indent=1, ensure_ascii=False) + "\n")


def content(pb: dict) -> dict:
    return {k: pb.get(k) for k in CONTENT}


def content_sha(pb: dict) -> str:
    return sha256_json(content(pb))


def text_of(pb: dict) -> str:
    """Everything an agent would read (for the leak checks)."""
    parts = []
    for k in CONTENT:
        v = pb.get(k)
        if k == "source":
            continue
        if isinstance(v, list):
            parts += [str(x) for x in v]
        elif v is not None:
            parts.append(str(v))
    return "\n".join(parts)


def validate(pb: dict) -> list[str]:
    p = []
    if not ID_RE.match(str(pb.get("id", ""))):
        p.append("id: pb-<slug>")
    for k in ("title", "technique", "correctness", "author", "created", "expires"):
        if not isinstance(pb.get(k), str) or not pb[k].strip():
            p.append(f"missing {k}")
    for k in LISTS:
        if not isinstance(pb.get(k), list) or not all(isinstance(x, str) and x.strip() for x in pb[k]):
            p.append(f"{k}: list of non-empty strings")
    if len(pb.get("steps") or []) < 3:
        p.append("steps: at least 3 (from zero to a measured claim)")
    if not pb.get("applies_when"):
        p.append("applies_when: at least one condition")
    s = pb.get("source") or {}
    if not (isinstance(s.get("ledger_seq"), int) and re.fullmatch(r"[0-9a-f]{64}", str(s.get("ledger_sha256", "")))
            and s.get("claim_id") and s.get("target")):
        p.append("source: {ledger_seq, ledger_sha256, claim_id, target}")
    for k in ("created", "expires"):
        try:
            dt.date.fromisoformat(str(pb.get(k)))
        except ValueError:
            p.append(f"{k}: YYYY-MM-DD")
    return p


# ------------------------------------------------------------------------------------------- ledger evidence
def human_approved(rows: list[dict], verdict_seq: int) -> dict | None:
    for r in rows:
        if r.get("kind") == "note" and r.get("note") == "human-approval" and r.get("verdict_seq") == verdict_seq:
            return r
    return None


def is_success(row: dict, rows: list[dict]) -> bool:
    """The only success signal of RSI-F: a real verdict CONFIRMED (or NEEDS-HUMAN with a CONFIRMED statistic that a
    human approved). NULL, REFUTED, INVALID or passed gates G0-G3 alone never count."""
    if row.get("kind") != "verdict" or row.get("mode") != "real":
        return False
    if row.get("verdict") in SUCCESS:
        return True
    return row.get("verdict") == "NEEDS-HUMAN" and row.get("stat_verdict") == "CONFIRMED" and \
        human_approved(rows, row["seq"]) is not None


def source_row(pb: dict, rows: list[dict]) -> dict:
    s = pb.get("source") or {}
    seq = s.get("ledger_seq")
    if not isinstance(seq, int) or seq >= len(rows):
        raise PlaybookError(f"source ledger row {seq} does not exist")
    r = rows[seq]
    if r.get("sha256") != s.get("ledger_sha256"):
        raise PlaybookError(f"source row {seq}: sha256 {str(r.get('sha256'))[:12]} != playbook "
                            f"{str(s.get('ledger_sha256'))[:12]}")
    if r.get("claim_id") != s.get("claim_id"):
        raise PlaybookError(f"source row {seq} is claim {r.get('claim_id')}, not {s.get('claim_id')}")
    return r


def notes(rows: list[dict], pid: str) -> list[dict]:
    return [r for r in rows if r.get("kind") == "note" and r.get("note") == "rsi-playbook" and r.get("playbook") == pid]


def ledger_status(rows: list[dict], pb: dict) -> str | None:
    """Status as proven by the ledger for the CURRENT content (a content change drops candidate/accepted)."""
    st = None
    sha = content_sha(pb)
    for r in notes(rows, pb["id"]):
        if r["to"] in ("draft", "rejected") or r.get("content_sha256") == sha:
            st = r["to"]
        elif r["to"] in ("candidate", "accepted"):
            st = "draft"
    return st


def _transition(led: Ledger, pb: dict, to: str, evidence: dict, by: str) -> dict:
    frm = pb.get("status")
    row = led.append({"kind": "note", "note": "rsi-playbook", "playbook": pb["id"], "from": frm, "to": to,
                      "content_sha256": content_sha(pb), "by": by, "evidence": evidence})
    pb["status"] = to
    pb.setdefault("history", []).append({"ts": row["ts"], "from": frm, "to": to, "ledger": f"{row['seq']}/"
                                         f"{row['sha256'][:8]}", "by": by})
    save(pb)
    return row


# ------------------------------------------------------------------------------------------- no-diff review
WORD = re.compile(r"\w+", re.U)
# a code-shaped name: has an underscore, an inner capital (camelCase) or a digit; plain English words from patch
# comments ("accumulator", "products") are not names that point at the answer
IDENT = re.compile(r"\b(?=[A-Za-z_][A-Za-z0-9_]{5,}\b)(?:[A-Za-z0-9]*_[A-Za-z0-9_]*|[a-z]+[A-Z][A-Za-z0-9]*|"
                   r"[A-Za-z]+[0-9][A-Za-z0-9]*)\b")
PCT = re.compile(r"[+-]?\d+(?:\.\d+)?(?=\s*%)")


def _code_grams(lines, n=NGRAM):
    out = set()
    for l in lines:
        w = [x.lower() for x in WORD.findall(l)]
        out |= {tuple(w[i:i + n]) for i in range(len(w) - n + 1)}
    # n-grams that span lines too (a hunk copied as prose would re-flow)
    w = [x.lower() for l in lines for x in WORD.findall(l)]
    out |= {tuple(w[i:i + n]) for i in range(len(w) - n + 1)}
    return out


def _norm(s):
    return re.sub(r"\s+", " ", s).strip()


def review(text: str, diff: str, source: dict | None = None, extra_forbidden=()) -> dict:
    """The automatic no-diff check (21h §5.3 'Recenzent przecieku'); threshold 0 for every class of hit.
    text: what the agent would read (playbook or brief); diff: the source patch; source: its verdict row."""
    files = parse_unified(diff)
    changed = [l for f in files for l in f.added + f.removed]
    added = [l for f in files for l in f.added]
    removed = [l for f in files for l in f.removed]
    hits = {}
    tg = {tuple(x.lower() for x in g) for g in sealed.ngrams(text, NGRAM)}
    g = tg & _code_grams(changed)
    if g:
        hits["diff_8grams"] = [" ".join(x) for x in sorted(g)[:5]] + ([f"... {len(g)} total"] if len(g) > 5 else [])
    nt = _norm(text)
    long_lines = sorted({_norm(l) for l in changed if len(_norm(l)) >= LONG_LINE and _norm(l) in nt})
    if long_lines:
        hits["diff_lines"] = long_lines[:5]
    code = lambda ls: "\n".join(l for l in ls if not l.lstrip().startswith(("//", "*", "/*", "#")))  # noqa: E731
    base_idents = set(IDENT.findall(code(removed)))
    new_idents = set(IDENT.findall(code(added))) - base_idents
    # identifiers the patch introduced: a name would point the agent at the answer in the tree
    found = sorted(i for i in new_idents if re.search(rf"\b{re.escape(i)}\b", text))
    if found:
        hits["new_identifiers"] = found[:10]
    forb = list(extra_forbidden)
    if source:
        cm = source.get("commits") or (source.get("card") or {}).get("commits") or {}
        forb += [c[:7] for c in cm.values() if c and len(c) >= 7]
        sw = ((source.get("card") or {}).get("switch") or {}).get("name")
        if sw:
            forb.append(sw)
    f2 = sorted({x for x in forb if x and x in text})
    if f2:
        hits["forbidden_tokens"] = f2
    sg = sealed.sealed_ngrams(sealed.load_all(), NGRAM) & sealed.ngrams(text, NGRAM)
    if sg:
        hits["sealed_8grams"] = len(sg)
    if source and isinstance(source.get("median"), (int, float)):
        m = source["median"]
        nums = [float(x) for x in PCT.findall(text)]
        bad = sorted({x for x in nums if abs(abs(x) - abs(m)) <= 0.051})
        if bad:
            hits["measured_numbers"] = [f"{x:g}% ~ the source verdict's median {m:.3f}%" for x in bad]
    return {"pass": not hits, "hits": hits, "n_diff_lines": len(changed), "n_text_chars": len(text)}


# ------------------------------------------------------------------------------------------- library operations
def create(pb: dict, led: Ledger, by: str) -> dict:
    probs = validate(pb)
    if probs:
        raise PlaybookError("; ".join(probs))
    if path_of(pb["id"]).exists():
        raise PlaybookError(f"{path_of(pb['id'])} exists")
    rows = led.rows()
    src = source_row(pb, rows)
    if not is_success(src, rows):
        raise PlaybookError(f"source row {src['seq']} is {src.get('mode')}/{src.get('verdict')} "
                            f"(stat {src.get('stat_verdict')}): only a real CONFIRMED (or a human-approved "
                            f"NEEDS-HUMAN with a CONFIRMED statistic) becomes a playbook")
    pb = {**content(pb), "status": None, "review": None, "transfers": [], "history": []}
    _transition(led, pb, "draft", {"source": f"{src['seq']}/{src['sha256'][:8]}", "verdict": src.get("verdict"),
                                   "stat_verdict": src.get("stat_verdict")}, by)
    return pb


def do_review(pid: str, led: Ledger, diff: str, reviewer: str, verdict: str, notes_text: str = "") -> dict:
    pb = load(pid)
    if pb.get("status") not in ("draft",):
        raise PlaybookError(f"{pid} is {pb.get('status')}, review applies to drafts")
    if reviewer == pb.get("author"):
        raise PlaybookError("the reviewer must not be the author")
    rows = led.rows()
    src = source_row(pb, rows)
    auto = review(text_of(pb), diff, src)
    pb["review"] = {"auto": auto, "reviewer": reviewer, "verdict": verdict, "notes": notes_text,
                    "content_sha256": content_sha(pb), "diff_sha256": sha256_json(diff)}
    if verdict == "pass" and auto["pass"]:
        _transition(led, pb, "candidate", {"auto": auto, "reviewer": reviewer, "notes": notes_text}, reviewer)
    elif verdict == "reject":
        _transition(led, pb, "rejected", {"auto": auto, "reviewer": reviewer, "notes": notes_text}, reviewer)
    else:
        save(pb)  # stays draft: the rewriter fixes the hits and asks again
    return pb


def transfer_rows(rows: list[dict], pid: str | None = None) -> list[dict]:
    return [r for r in rows if r.get("kind") == "verdict" and (r.get("card") or {}).get("rsi") and
            (pid is None or r["card"]["rsi"].get("playbook") == pid)]


def acceptance_evidence(pb: dict, rows: list[dict]) -> tuple[dict | None, list[str]]:
    """The first transfer verdict that makes this playbook `accepted`, or the reasons none does."""
    why = []
    src = source_row(pb, rows)
    src_author = (src.get("card") or {}).get("author")
    briefs = {r["brief_sha256"]: r for r in rows if r.get("kind") == "note" and r.get("note") == "rsi-brief"}
    for r in transfer_rows(rows, pb["id"]):
        c, rs = r["card"], r["card"]["rsi"]
        tag = f"seq {r['seq']} ({c.get('id')}, arm {rs.get('arm')}, {r.get('verdict')})"
        b = briefs.get(rs.get("brief_sha256"))
        if rs.get("arm") != "A":
            continue
        if not is_success(r, rows):
            why.append(f"{tag}: not a success")
        elif rs.get("target") == pb["source"]["target"]:
            why.append(f"{tag}: same target as the source")
        elif c.get("author") in (pb.get("author"), src_author):
            why.append(f"{tag}: not a fresh agent (author {c.get('author')})")
        elif not b or b.get("playbook") != pb["id"] or b.get("content_sha256") != content_sha(pb) or \
                b.get("target") != rs.get("target") or b.get("arm") != "A":
            why.append(f"{tag}: its brief is not a ledger-recorded brief of this playbook content and target")
        else:
            return r, why
    if not why:
        why.append("no arm-A transfer verdict yet")
    return None, why


def accept(pid: str, led: Ledger, by: str) -> dict:
    pb = load(pid)
    rows = led.rows()
    if ledger_status(rows, pb) != "candidate":
        raise PlaybookError(f"{pid}: ledger status {ledger_status(rows, pb)}, needs candidate (reviewed content)")
    r, why = acceptance_evidence(pb, rows)
    if not r:
        raise PlaybookError(f"{pid} not accepted: " + "; ".join(why))
    pb.setdefault("transfers", []).append({"target": r["card"]["rsi"]["target"], "claim_id": r["claim_id"],
                                           "ledger": f"{r['seq']}/{r['sha256'][:8]}", "verdict": r["verdict"],
                                           "median": r.get("median")})
    _transition(led, pb, "accepted", {"transfer": f"{r['seq']}/{r['sha256'][:8]}", "claim_id": r["claim_id"],
                                      "target": r["card"]["rsi"]["target"]}, by)
    return pb


def reject(pid: str, led: Ledger, by: str, reason: str) -> dict:
    pb = load(pid)
    _transition(led, pb, "rejected", {"reason": reason}, by)
    return pb


def library(led: Ledger | None = None) -> list[dict]:
    """Every playbook with its file status, the ledger-proven status and staleness."""
    rows = led.rows() if led else []
    out = []
    today = dt.date.today().isoformat()
    for f in sorted(paths.PLAYBOOKS.glob("pb-*.json")) if paths.PLAYBOOKS.exists() else []:
        pb = json.loads(f.read_text())
        ls = ledger_status(rows, pb) if led else None
        out.append({"id": pb["id"], "title": pb.get("title"), "status": pb.get("status"), "ledger_status": ls,
                    "consistent": ls == pb.get("status") if led else None,
                    "stale": pb.get("expires", "9999") < today, "source": pb.get("source", {}).get("claim_id"),
                    "transfers": len(pb.get("transfers") or [])})
    return out


def render(pb: dict) -> str:
    """Markdown an agent reads (no provenance hashes: those are for the ledger, not for the implementer)."""
    def ul(xs):
        return "\n".join(f"- {x}" for x in xs) or "- (none)"
    return (f"# Playbook {pb['id']}: {pb['title']}\n\n## Technique\n{pb['technique']}\n\n"
            f"## Worth trying when\n{ul(pb['applies_when'])}\n\n## Not when\n{ul(pb['not_when'])}\n\n"
            f"## Steps\n" + "\n".join(f"{i}. {s}" for i, s in enumerate(pb["steps"], 1)) +
            f"\n\n## Profiling\n{ul(pb['profiling'])}\n\n## Pitfalls\n{ul(pb['pitfalls'])}\n\n"
            f"## Proving correctness\n{pb['correctness']}\n\n## Factory rules that fired on the source claim\n"
            f"{ul(pb['rules_fired'])}\n")
