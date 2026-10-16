"""R21: anomaly breaker: a value below half the recent median of its family is an incident, not a result."""
import statistics

from rules import RulePolicy
from rules._util import by_arm

POLICY = RulePolicy(
    "R21", "anomaly-breaker", ("measurement", "history"), "block", "INVALID",
    source="spec_sweep.jsonl row 15: DRAFT_N=5, 2026-10-10 22:48, 5.6 t/s against a median of 86.4 (zombie DFlash "
           "server sharing VRAM); 15f E-D backtest",
    lesson="lekcja-zombie-serwery", failure_mode="07#8")

WINDOW, FACTOR = 5, 0.5
FAMILIES = {"qwen": "qwen", "unc": "unc", "uncensored": "unc", "lfm": "lfm", "lfm-uncensored": "lfm-unc"}


def family(row) -> str:
    """Model family from structured fields, else from whole label words (never substrings like 'lfm3_inst')."""
    if row.get("model"):
        return row["model"]
    fam = "qwen"
    for w in str(row.get("label", "")).replace("/", " ").split():
        if w in FAMILIES:
            fam = FAMILIES[w]
    return fam


def history_flags(rows):
    hist, out = {}, []
    for i, r in enumerate(rows):
        key = (family(r), r.get("temp"))
        prev = hist.setdefault(key, [])
        v = r.get("median_tps")
        if v is not None and len(prev) >= 3:
            m = statistics.median(prev[-WINDOW:])
            if v < FACTOR * m:
                out.append((i, v, m))
        if v is not None:
            prev.append(v)
    return out


def check(ctx):
    out = [f"history row {i} ({ctx['history'][i].get('label', '')[:30]}): {v:.1f} t/s < {FACTOR} x median {m:.1f}"
           for i, v, m in history_flags(ctx.get("history") or [])]
    metric = (ctx.get("card") or {}).get("metric")
    for arm, runs in sorted(by_arm(ctx).items()):
        xs = [r["values"][metric] for r in runs if metric in (r.get("values") or {})]
        if len(xs) < 2:
            continue
        m = statistics.median(xs)
        for r in runs:
            v = r["values"].get(metric)
            if v and (v > m / FACTOR or v < m * FACTOR):
                out.append(f"run {arm}{r.get('round')}.{r.get('pos')}: {metric} {v:.4g} vs arm median {m:.4g}")
    return out
