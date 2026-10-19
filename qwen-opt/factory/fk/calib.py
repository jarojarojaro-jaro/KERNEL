"""Prediction calibration: the critic RSI-F inherits from cycle to cycle (report 21h §5.1, 15f X5). Never reset.

Per real verdict row: predicted effect (card expected.effect_pct) vs measured median, absolute error, ratio, and the
Brier term of the implementer's probability of CONFIRMED (card expected.p_confirmed; outcome 1 only for a success in
the sense of fk/playbook.is_success). Refused/void rows (hardware, infrastructure) are excluded: they say nothing
about the prediction. The log rsi/calibration.jsonl is append-only by ledger seq (rows already logged stay).
The prior P(CONFIRMED) for ranking the next queue is Laplace (successes + 1) / (verdicts + 2).
"""
from __future__ import annotations

import json
import statistics

from . import paths
from .ledger import Ledger
from .playbook import is_success


def entries(rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        if r.get("kind") != "verdict" or r.get("mode") != "real" or r.get("refused") or r.get("verdict") == "VOID":
            continue
        exp = (r.get("card") or {}).get("expected") or {}
        e, m, pc = exp.get("effect_pct"), r.get("median"), exp.get("p_confirmed")
        o = 1 if is_success(r, rows) else 0
        out.append({"seq": r["seq"], "sha8": r["sha256"][:8], "claim_id": r.get("claim_id"), "verdict": r.get("verdict"),
                    "predicted_pct": e, "measured_pct": m, "ci95": r.get("ci95"),
                    "abs_err_pp": abs(m - e) if isinstance(e, (int, float)) and isinstance(m, (int, float)) else None,
                    "ratio": (m / e) if isinstance(e, (int, float)) and e and isinstance(m, (int, float)) else None,
                    "p_confirmed": pc, "outcome": o,
                    "brier": (pc - o) ** 2 if isinstance(pc, (int, float)) else None,
                    "rsi": (r.get("card") or {}).get("rsi")})
    return out


def summary(es: list[dict]) -> dict:
    ae = [e["abs_err_pp"] for e in es if e["abs_err_pp"] is not None]
    ra = [abs(e["ratio"]) for e in es if e["ratio"] is not None]
    br = [e["brier"] for e in es if e["brier"] is not None]
    n, s = len(es), sum(e["outcome"] for e in es)
    return {"n": n, "successes": s, "prior_p_confirmed": (s + 1) / (n + 2),
            "mae_pp": statistics.mean(ae) if ae else None, "median_abs_ratio": statistics.median(ra) if ra else None,
            "brier": statistics.mean(br) if br else None, "n_brier": len(br)}


def log(led: Ledger) -> dict:
    """Append new entries to rsi/calibration.jsonl; return the summary over everything logged."""
    f = paths.RSI / "calibration.jsonl"
    have = set()
    if f.exists():
        have = {json.loads(l)["seq"] for l in f.read_text().splitlines() if l.strip()}
    es = entries(led.rows())
    new = [e for e in es if e["seq"] not in have]
    if new:
        f.parent.mkdir(parents=True, exist_ok=True)
        with open(f, "a") as fh:
            for e in new:
                fh.write(json.dumps(e, sort_keys=True) + "\n")
    return {**summary(es), "new": len(new)}


def rank(cards: list[dict], prior: float, gpu_min: dict | None = None) -> list[tuple[float, dict]]:
    """Queue order: expected gain x P(CONFIRMED) / GPU minutes. P blends the card's own probability with the
    inherited prior (mean of the two), so an overconfident implementer cannot jump the queue alone."""
    out = []
    for c in cards:
        exp = c.get("expected") or {}
        p = exp.get("p_confirmed")
        p = prior if p is None else (p + prior) / 2
        mins = (gpu_min or {}).get(c["id"]) or (15 if c.get("metric") in ("pp_tps", "tg_tps") else 45)
        out.append((max(0.0, exp.get("effect_pct") or 0) * p / mins, c))
    return sorted(out, key=lambda x: -x[0])
