"""R37: on a speculative profile a faster step must not be bought with worse drafts (21i A1, Apple acceptance gate).

Greedy md5 (G2) cannot see a degraded drafter: the verifier keeps the text identical, only fewer drafts are accepted.
If the claim's metric is not tok_step, the paired tok_step effects of G4 must not have their whole 95 % CI below
-max(MDE floor of tok_step, 1 %); otherwise the verdict is INVALID (a tok_step claim is judged by its own CI).
"""
from fk import stats
from rules import RulePolicy

POLICY = RulePolicy(
    "R37", "acceptance-floor", ("measurement",), "block", "INVALID",
    source="Apple RSI-Inference Bench acceptance.py INFB_ACCEPT_RTOL=0.04 (21i §2.3); our case: a cheaper, worse "
           "drafter raises raw t/s while acceptance falls (DFlash2 / MTP head +-2 %, metody/wyniki-negatywne.md)",
    lesson="lekcja-szum-t-s-przy-t1", failure_mode="lekcja")

FLOOR_PCT = 1.0


def check(ctx):
    card, prof = ctx.get("card") or {}, ctx.get("profile") or {}
    if not prof.get("spec") or card.get("metric") == "tok_step":
        return []
    vals = {(r["round"], r["pos"]): (r["arm"], r["values"]["tok_step"]) for r in ctx.get("runs") or []
            if r.get("ok", True) and "tok_step" in (r.get("values") or {})}
    eff, _, _ = stats.paired_effects(vals, "tok_step")
    if len(eff) < 2:
        return []
    s = stats.summarize(eff)
    lo, hi = s["ci95"]
    bar = -max(stats.MDE_FLOOR["tok_step"], (card.get("spec") or {}).get("acceptance_floor_pct", FLOOR_PCT))
    if hi == hi and hi < bar:
        return [f"tok_step CI [{lo:+.2f}, {hi:+.2f}] % lies below {bar:.2f} %: drafts got worse (acceptance floor)"]
    return []
