"""R33: the saving cannot exceed the time of the attacked kernels (Amdahl), and is checked against the prediction."""
from rules import RulePolicy

POLICY = RulePolicy(
    "R33", "amdahl", ("physics",), "block", "INVALID",
    source="15f §5.4 T8: |dt_step| <= sum of attacked kernel times; AlphaEvolve +23% kernels = -1% e2e means the kernels "
           "were ~4-5% of the time (arXiv 2506.13131 §3.3.2)",
    lesson="lekcja-megakernel-prefetch-nie-granica", failure_mode="lekcja")

REL_TOL, ABS_TOL_MS = 0.10, 0.02


def check(ctx):
    card = ctx.get("card") or {}
    share = (card.get("attacked") or {}).get("share_ms")
    s = ctx.get("summary") or {}
    d = s.get("saving_ms")
    if share is None or d is None:
        return []
    if d > share * (1 + REL_TOL) + ABS_TOL_MS:
        return [f"saving {d:.3f} ms > attacked share {share:.3f} ms (+{REL_TOL:.0%}): the change acted elsewhere, or the "
                f"measurement is wrong"]
    return []
