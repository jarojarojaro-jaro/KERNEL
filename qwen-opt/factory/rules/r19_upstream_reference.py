"""R19: 'bit-identical to upstream' is not a BIT claim: the fork differs from upstream through 0001/0002/0013."""
from rules import RulePolicy

POLICY = RulePolicy(
    "R19", "upstream-reference", ("static",), "block", "INVALID",
    source="NVIDIA campaign: fork md5 != upstream in plain mode with all 31 switches = 0 (MMVQ multi-column 0001/0002, "
           "GDN prologue fusion 0013); LFM fork 894e56e4, with -DMMVQ_DISABLE_MULTI upstream 949a753b",
    lesson="lekcja-md5-wzgledem-upstreamu", failure_mode="lekcja")


def check(ctx):
    card = ctx.get("card") or {}
    if card.get("reference") == "upstream" and card.get("correctness_class") == "BIT":
        return ["reference upstream with class BIT: use NEAR-TIE (first divergence a tie <= 0.1 logit) or KLD"]
    return []
