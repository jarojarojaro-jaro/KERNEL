"""R10: at T=1 t/s mixes kernel speed and draft acceptance; spec measurements need ms/step and tok/step."""
from rules import RulePolicy

POLICY = RulePolicy(
    "R10", "t1-decomposition", ("static", "measurement", "history"), "block", "INVALID",
    source="per-prompt t/s in one config spans 58-96 (15f E-C); spec_sweep.jsonl rows of 2026-10-10 have only t/s "
           "and acceptance, no ms/step or tok/step, so kernel and acceptance effects cannot be separated; NOTES.md:168",
    lesson="lekcja-szum-t-s-przy-t1", failure_mode="07#10")


def check(ctx):
    out = []
    card, prof = ctx.get("card") or {}, ctx.get("profile") or {}
    if card.get("metric") == "tps" and prof.get("spec"):
        out.append("metric tps on a speculative profile: claim ms_step (kernel) or tok_step (acceptance) instead")
    for i, r in enumerate(ctx.get("history") or []):
        if r.get("temp") == 1.0 and "median_ms_step" not in r:
            out.append(f"history row {i} ({r.get('label', '')[:30]}): T=1 without ms_step/tok_step")
    for r in ctx.get("runs") or []:
        vals = r.get("values") or {}
        if r.get("kind", "serve") == "serve" and prof.get("spec") and r.get("ok", True) and \
                not ("ms_step" in vals and "tok_step" in vals):
            out.append(f"run {r.get('arm')}{r.get('round')}.{r.get('pos')}: no ms_step/tok_step")
    return out
