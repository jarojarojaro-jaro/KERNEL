"""RSI-F transfer test (report 21h §5.3 step 4, §5.7 P1): does a playbook help a FRESH agent on a DIFFERENT target?

Target  rsi/targets/<id>.json: {id, title, task (public description), profile, metric, ops_hint, scope [paths],
        workspace (prepared snapshot dir, one per arm), base_commit, where "local"|"cloud", cloud {...}}
Brief   generated from the target (+ the rendered playbook for arm A) and NOTHING else: no diff, no ledger rows, no
        sealed text. Both arms get the same rules, limits and commands; the brief passes the same no-diff review as
        the playbook; its sha256 goes into a ledger `rsi-brief` note and into the agent's card (card.rsi).
Score   per (target, arm) the latest verdict of a card with card.rsi: success (CONFIRMED / human-approved) | g3 (a
        statistical verdict, i.e. G0-G3 passed, but no success) | invalid (agent fault) | void (refused: hardware or
        infrastructure, re-run, never scored) | none. SPR weight: success 1.0, g3 0.25, else 0 (partial < 1).
Kill    k1 no playbook passes review without diff text; k2 arm A reaches G3 on no target, or spends >= the effort of
        arm B; k3 any GPU fault or quarantine during the pilot (H3). P2 gate: A success or g3 on >= 1 target at
        <= 50 % of B's effort, or A succeeds where B does not.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from . import hwgates, paths
from . import playbook as pbm
from .hashing import sha256_bytes
from .ledger import Ledger

SPR = {"success": 1.0, "g3": 0.25, "invalid": 0.0}
STAT_VERDICTS = ("CONFIRMED", "NULL", "REFUTED", "REGRESSION", "NEEDS-HUMAN")


def targets_dir() -> Path:
    return paths.RSI / "targets"


def load_target(tid: str) -> dict:
    return json.loads((targets_dir() / f"{tid}.json").read_text())


def build_commands(ws: str) -> list[dict]:
    """The only build recipe the agents get. H11: one heavy job machine-wide, nice 19, 2 cores, -j2; the shared quiet
    lock keeps builds out of GPU measurements; rsi/build-slot.sh builds every workspace in ONE fixed build tree, so
    after the first full build only the files a workspace changed recompile. Installs into <ws>/inst."""
    bld = f"cpuheavy --quiet bash {paths.RSI}/build-slot.sh {ws} -j2"
    return [{"kind": "build", "cmd": bld}]


RULES = """\
## Rules (enforced by the factory, not by trust)
- You never touch the GPU: do not run llama-server, llama-bench, llama-cli, test-backend-ops, rocprof or anything that
  opens /dev/kfd. The planner runs `factory verify` later; the factory refuses GPU work from anyone else.
- Never use sudo; never write to /sys; no clock, voltage, power-limit or fan changes (gate H7 refuses such diffs).
- Builds only with the commands below. Every CPU-heavy command (build, big grep/strings over binaries, ISA dumps
  of large libraries, python analyses) runs as `cpuheavy CMD` (builds: `cpuheavy --quiet CMD`; one heavy
  job machine-wide, max 2 cores, -j2). Never create, touch or delete lock files.
- Work only in your workspace. Do not read other worktrees (~/wt/*), ~/llama-master, ~/llama-opt sources, git history
  of other repos, ~/KERNEL (wiki and research reports), ~/qwen-opt/factory/{{playbooks,rsi,sealed,ledger*}} or
  other agents' transcripts. Your workspace is a fresh one-commit snapshot; `git log` shows only that commit.
- Every change sits behind an env switch whose `off` value restores the old code path exactly; correctness class
  BIT (bit-identical outputs) unless you can argue otherwise in the card.
- Offline evidence is welcome (ISA via the build's own flags: `--save-temps`, `llvm-objdump`, VGPR/spill counts),
  but the verdict comes only from the factory.
- Limits: at most {minutes} minutes of wall clock for the whole task. If no claim is ready by then, stop and report
  why; an honest "not feasible" is a valid result.
"""

FLOW = """\
## Deliverable: a registered claim card (factory v1 flow, README in ~/qwen-opt/factory/README.md §1-3)
```
cd ~/qwen-opt/factory
./factory card new {card_id} --author {agent}
# fill: hypothesis, mechanism, profile "{profile}", metric "{metric}", expected.effect_pct, expected.p_confirmed
#       (your probability that the factory says CONFIRMED), kill.effect_pct_below, correctness_class, switch,
#       probe {{"kind": "timing"}}, ops (test-backend-ops filters for the ops you changed, e.g. {ops_hint})
# and this block exactly:
#   "rsi": {rsi_json}
git -C {ws} add -A && git -C {ws} commit -qm "<what, behind which switch>"
cpuheavy ./factory card fill claims/{card_id}.json --base-build {ws}/inst \\
    --cand-build {ws}/inst --repo {ws} --base {base_commit} --cand $(git -C {ws} rev-parse HEAD)
./factory card check claims/{card_id}.json      # must print OK
./factory register claims/{card_id}.json
./factory verify claims/{card_id}.json --dry-run   # plan only; NEVER without --dry-run
```
(probe timing: arm A of the measurement is your binary with the switch off, so base and cand build are the same dir.)
Report at the end: card id, commit, what you changed and why, offline evidence, wall-clock minutes, and anything that
blocked you.
"""


def brief(target: dict, arm: str, agent: str, card_id: str, pb: dict | None = None,
          minutes: int = 90) -> tuple[str, str, list[dict]]:
    """(text, sha256, build commands). The sha256 is of the text with the "<sha below>" placeholder in card.rsi."""
    assert arm in ("A", "B") and (arm == "A") == (pb is not None)
    ws = target["workspace"][arm]
    rsi = {"playbook": pb["id"] if pb else None, "arm": arm, "target": target["id"], "brief_sha256": "<sha below>"}
    cmds = build_commands(ws)
    text = (f"# Task brief: {target['title']} (fresh implementer, arm {arm})\n\n"
            f"You are a fresh implementer agent `{agent}` in our llama.cpp fork (HIP, RX 7900 XTX gfx1100, ROCm 10.0).\n\n"
            f"## Target\n{target['task']}\n\nWorkspace (fresh snapshot, already prepared): `{ws}`\n"
            f"Base commit in that workspace: `{target['base_commit_ws'][arm]}`\n\n"
            f"## Build (exactly these commands)\n```\n" + "\n".join(c["cmd"] for c in cmds) + "\n```\n"
            f"Builds share one prebuilt tree: a header change recompiles only the affected instances (~10-30 min "
            f"on 2 cores; the command waits for the CPU lock). Commit before building: the build carries your commit."
            f"\n\n" +
            RULES.format(minutes=minutes) + "\n" +
            FLOW.format(card_id=card_id, agent=agent, profile=target["profile"], metric=target["metric"],
                        ops_hint=target.get("ops_hint", "MUL_MAT|type_a=..."), ws=ws,
                        base_commit=target["base_commit_ws"][arm], rsi_json=json.dumps(rsi)))
    if pb is not None:
        text += ("\n## Playbook (a technique that worked on a different target; adapt it, do not assume it fits)\n\n"
                 + pbm.render(pb))
    sha = sha256_bytes(text.encode())
    return text.replace('"brief_sha256": "<sha below>"', f'"brief_sha256": "{sha}"') + \
        f"\n<!-- brief sha256 (of the text with the placeholder): {sha} -->\n", sha, cmds


def issue(target_id: str, arm: str, agent: str, card_id: str, led: Ledger, diff: str, playbook_id: str | None = None,
          minutes: int = 90, by: str = "planner") -> dict:
    """Generate, review and record a brief: the review must pass (no diff text, no sealed text) and the build commands
    must satisfy H11; then a ledger note pins its sha256. Returns {path, sha256, review}."""
    target = load_target(target_id)
    pb = pbm.load(playbook_id) if playbook_id else None
    rows = led.rows()
    if pb is not None:
        st = pbm.ledger_status(rows, pb)
        if st not in ("candidate", "accepted"):
            raise pbm.PlaybookError(f"{playbook_id}: ledger status {st}; only reviewed playbooks go to agents")
        if target_id == pb["source"]["target"]:
            raise pbm.PlaybookError("transfer target equals the playbook's source target")
    text, sha, cmds = brief(target, arm, agent, card_id, pb, minutes)
    src = pbm.source_row(pb, rows) if pb else None
    rev = pbm.review(text, diff, src)
    h11 = hwgates.h11({"commands": [{"kind": c["kind"], "cmd": c["cmd"].split("   #")[0]} for c in cmds]})
    h10 = hwgates.h10({"where": target.get("where", "local"), "cloud": target.get("cloud")})
    if not rev["pass"] or h11 or h10:
        raise pbm.PlaybookError(f"brief refused: review {rev['hits']} H11 {h11} H10 {h10}")
    d = paths.RSI / "briefs"
    d.mkdir(parents=True, exist_ok=True)
    out = d / f"{target_id}-{arm}-{sha[:12]}.md"
    out.write_text(text)
    led.append({"kind": "note", "note": "rsi-brief", "target": target_id, "arm": arm, "agent": agent,
                "card_id": card_id, "playbook": playbook_id, "content_sha256": pbm.content_sha(pb) if pb else None,
                "brief_sha256": sha, "path": str(out), "minutes": minutes, "by": by})
    return {"path": str(out), "sha256": sha, "review": rev}


# ------------------------------------------------------------------------------------------- scoring


def classify(row: dict | None, rows: list[dict]) -> str:
    if row is None:
        return "none"
    if pbm.is_success(row, rows):
        return "success"
    v = row.get("verdict")
    if v == "VOID":
        return "void"
    if v == "INVALID":  # since VOID exists, INVALID is the candidate's fault (incl. an H3 GPU fault)
        return "invalid"
    if v in STAT_VERDICTS:
        return "g3"
    return "invalid"


def load_effort() -> dict:
    """rsi/transfer-effort.jsonl: {target, arm, agent, minutes, tool_calls, tokens} written by the planner from the
    agent run (tokens when the harness reports them)."""
    f = paths.RSI / "transfer-effort.jsonl"
    out = {}
    if f.exists():
        for l in f.read_text().splitlines():
            if l.strip():
                r = json.loads(l)
                out[(r["target"], r["arm"])] = r
    return out


def score(target_ids: list[str], led: Ledger, faults: list[str] | None = None,
          review_passed: bool | None = None) -> dict:
    rows = led.rows()
    eff = load_effort()
    cells = {}
    for t in target_ids:
        for arm in ("A", "B"):
            mine = [r for r in pbm.transfer_rows(rows) if r["card"]["rsi"].get("target") == t and
                    r["card"]["rsi"].get("arm") == arm]
            scored = [r for r in mine if classify(r, rows) != "void"]
            last = scored[-1] if scored else (mine[-1] if mine else None)
            c = classify(last, rows)
            e = eff.get((t, arm), {})
            cells[f"{t}/{arm}"] = {"target": t, "arm": arm, "class": c, "spr": SPR.get(c), "verdict": (last or {}).get(
                "verdict"), "median": (last or {}).get("median"), "ci95": (last or {}).get("ci95"),
                "seq": (last or {}).get("seq"), "claim_id": (last or {}).get("claim_id"), "attempts": len(mine),
                "minutes": e.get("minutes"), "tokens": e.get("tokens"), "tool_calls": e.get("tool_calls")}

    def effort(arm, key):
        v = [cells[f"{t}/{arm}"][key] for t in target_ids if cells[f"{t}/{arm}"][key] is not None]
        return sum(v) if len(v) == len(target_ids) else None

    key = "tokens" if effort("A", "tokens") is not None and effort("B", "tokens") is not None else "minutes"
    ea, eb = effort("A", key), effort("B", key)
    a_g3 = [t for t in target_ids if cells[f"{t}/A"]["class"] in ("success", "g3")]
    a_win = [t for t in target_ids if cells[f"{t}/A"]["class"] == "success" and cells[f"{t}/B"]["class"] != "success"]
    kills = {
        "k1": None if review_passed is None else (not review_passed),
        "k2": (not a_g3) or (ea is not None and eb is not None and ea >= eb),
        "k3": bool(faults),
    }
    p2 = bool(a_win) or bool(a_g3 and ea is not None and eb is not None and ea <= 0.5 * eb)
    return {"cells": cells, "effort_key": key, "effort": {"A": ea, "B": eb}, "kill": kills,
            "kill_any": any(v for v in kills.values()), "go_p2": p2 and not any(v for v in kills.values()),
            "spr": {arm: sum(cells[f"{t}/{arm}"]["spr"] or 0 for t in target_ids) for arm in ("A", "B")}}


# ------------------------------------------------------------------------------------------- workspaces (21i A9)
def snapshot(repo: str, commit: str, dest: str) -> str:
    """A fresh implementer workspace: the tree of `commit` as ONE commit without history, remotes or reflog (so `git
    log`/`git show` cannot reveal the source patch or later patches). Returns the snapshot's commit sha."""
    d = Path(dest)
    if d.exists() and any(d.iterdir()):
        raise FileExistsError(f"{d} is not empty")
    d.mkdir(parents=True, exist_ok=True)
    arch = subprocess.run(["git", "-C", repo, "archive", "--format=tar", commit], capture_output=True, check=True)
    subprocess.run(["tar", "-x", "-C", str(d)], input=arch.stdout, check=True)
    env = {"GIT_AUTHOR_NAME": "rsi", "GIT_AUTHOR_EMAIL": "rsi@local", "GIT_COMMITTER_NAME": "rsi",
           "GIT_COMMITTER_EMAIL": "rsi@local", "GIT_AUTHOR_DATE": "2026-01-01T00:00:00Z",
           "GIT_COMMITTER_DATE": "2026-01-01T00:00:00Z", "PATH": "/usr/bin:/bin"}
    for args in (["init", "-q"], ["add", "-A"], ["commit", "-qm", "base (snapshot without history)"]):
        subprocess.run(["git", "-C", str(d), *args], check=True, env=env, capture_output=True)
    return subprocess.run(["git", "-C", str(d), "rev-parse", "HEAD"], capture_output=True, text=True,
                          check=True).stdout.strip()
