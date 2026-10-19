"""`factory report`: markdown from the ledger for the wiki (Kronikarz). Numbers only from ledger rows, each with
`ledger:<seq>/<sha8>` so the wiki number audit can trace them."""
from __future__ import annotations

import math
import re
import time

NEG = ("NULL", "REFUTED", "REGRESSION", "INVALID")


def f(x, fmt="{:+.3f}"):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "—"
    return fmt.format(x)


def ci(c):
    if not c or any(v is None or (isinstance(v, float) and math.isnan(v)) for v in c):
        return "—"
    return f"[{c[0]:+.3f}, {c[1]:+.3f}]"


def ref(r):
    return f"`ledger:{r['seq']}/{r['sha256'][:8]}`"


def render(rows: list[dict], chain_problems: list[str], title="Fabryka v1: werdykty z ledgera") -> str:
    verdicts = [r for r in rows if r.get("kind") == "verdict"]
    regs = [r for r in rows if r.get("kind") == "register"]
    locks = [r for r in rows if r.get("kind") == "harness-lock"]
    out = [f"# {title}", "",
           f"Wygenerowano {time.strftime('%Y-%m-%d %H:%M')} z {len(rows)} wierszy ledgera "
           f"({len(regs)} rejestracji kart, {len(verdicts)} werdyktów, {len(locks)} blokad harnessu).",
           "Łańcuch hashy: " + ("**nienaruszony**." if not chain_problems else "**USZKODZONY**: " +
                                "; ".join(chain_problems)), ""]
    counts = {}
    for r in verdicts:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    if counts:
        out += ["Werdykty: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())), ""]
    out += ["## Werdykty", "",
            "Efekt = zmiana na korzyść kandydata w % (dodatni = lepiej), mediana par ABBA na zestawie zapieczętowanym; "
            "CI 95 %; A/A = mediana różnicy dwóch procesów tej samej binarki.", "",
            "| karta | profil | metryka | przewidziane | zmierzone | CI 95 % | A/A | MDE | spec6 (publiczny) | werdykt | "
            "źródło |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in verdicts:
        pub = r.get("public") or {}
        out.append(f"| {r.get('claim_id')} | {r.get('profile')} | {r.get('metric')} | "
                   f"{f(r.get('expected_effect_pct'))} | {f(r.get('median'))} | {ci(r.get('ci95'))} | "
                   f"{f((r.get('aa') or {}).get('median'))} | {f(r.get('mde_pct'), '{:.2f}')} | "
                   f"{f(pub.get('median'))} {ci(pub.get('ci95'))} | **{r.get('verdict')}**"
                   f"{' (fake)' if r.get('mode') == 'fake' else ''} | {ref(r)} |")
    neg = [r for r in verdicts if r["verdict"] in NEG or r.get("verdict") == "NEEDS-HUMAN"]
    out += ["", "## Wyniki negatywne i do decyzji (szkice)", ""]
    if not neg:
        out.append("- brak")
    for r in neg:
        card = r.get("card") or {}
        out += [f"### {r.get('claim_id')}: {r['verdict']}", "",
                f"- Hipoteza: {card.get('hypothesis', '—')}",
                f"- Przełącznik `{(card.get('switch') or {}).get('name')}`, klasa {card.get('correctness_class')}, "
                f"commit `{str((r.get('commits') or {}).get('cand', ''))[:12]}`, harness `{str(r.get('harness_sha256'))[:12]}`.",
                f"- Zmierzone {f(r.get('median'))} % {ci(r.get('ci95'))} wobec przewidzianych "
                f"{f(r.get('expected_effect_pct'))} % (kill < {f(r.get('kill_effect_pct_below'))} %).",
                "- Powody:"]
        out += [f"  - {x}" for x in (r.get("reasons") or [])[:12]] or ["  - —"]
        out += [f"- Logi: `{r.get('logs')}`; {ref(r)}", ""]
    calib = [(r["claim_id"], r["expected_effect_pct"], r["median"]) for r in verdicts
             if r.get("expected_effect_pct") and r.get("median") is not None and r["verdict"] not in ("INVALID", "VOID")]
    out += ["## Kalibracja przewidywań (karta vs ledger)", ""]
    if calib:
        out += ["| karta | przewidziane % | zmierzone % | zmierzone / przewidziane |", "|---|---|---|---|"]
        out += [f"| {c} | {e:+.3f} | {m:+.3f} | {m / e:.2f} |" for c, e, m in calib]
    else:
        out.append("- brak wierszy z pomiarem")
    return "\n".join(out) + "\n"


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9-]+", "-", s.lower()).strip("-")


def wiki_draft(r: dict) -> tuple[str, str]:
    """(file name, note) in the wiki format of KONWENCJE.md; the main agent decides whether it goes in."""
    card = r.get("card") or {}
    date = str(card.get("created", ""))[:10] or time.strftime("%Y-%m-%d")
    name = f"{date}-{slug(str(r.get('claim_id')))}"
    status = "aktualne" if r["verdict"] in ("CONFIRMED", "REFUTED", "REGRESSION", "NULL") else "do-sprawdzenia"
    body = [
        "---", "typ: eksperyment", "tags: [eksperymenty, fabryka]", f"aktualizacja: {time.strftime('%Y-%m-%d')}",
        f"zrodlo: qwen-opt/factory/ledger.jsonl seq {r['seq']} ({r['sha256'][:12]})", f"status: {status}", "---",
        f"# {card.get('hypothesis', r.get('claim_id'))[:90]}", "",
        f"**Werdykt fabryki: {r['verdict']} – {r.get('metric')} {f(r.get('median'))} % {ci(r.get('ci95'))} "
        f"(przewidziane {f(r.get('expected_effect_pct'))} %).**", "",
        f"Profil {r.get('profile')}, {r.get('driver', {}).get('rounds')} rundy ABBA, A/A "
        f"{f((r.get('aa') or {}).get('median'))} %, MDE {f(r.get('mde_pct'), '{:.2f}')} %, zestaw zapieczętowany "
        f"`{str(r.get('sealed_sha256'))[:12]}`, spec6 {f((r.get('public') or {}).get('median'))} %. "
        f"Przełącznik `{(card.get('switch') or {}).get('name')}`, klasa {card.get('correctness_class')}, commit "
        f"`{str((r.get('commits') or {}).get('cand', ''))[:12]}`.", "",
        "Powody: " + "; ".join((r.get("reasons") or [])[:6]), "",
        "## Powiązane", "- [[eksperymenty/_hub|eksperymenty]]", "- [[fabryka-v1]]", "- [[pomiar-abba]]", ""]
    return name + ".md", "\n".join(body)
