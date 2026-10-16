"""R01: a BIT or SAME-TOK claim with any greedy md5 different from the base (FMA contraction, reordered sums)."""
from rules import RulePolicy

POLICY = RulePolicy(
    "R01", "bit-md5-mismatch", ("correctness",), "block", "INVALID",
    source="FMA contraction in 0025 (GGML_HIP_NORM_FAST, unrolled x*x, 1 ulp in ~4% rows): "
           "qwen-opt/fusion/greedy/k2a.plain.txt md5 32b54d31 vs k2base.plain.txt c4708318, first difference at char 129",
    lesson="determinizm-fma", failure_mode="07#1")


def check(ctx):
    card = ctx.get("card") or {}
    g = ctx.get("greedy")
    if not g or card.get("correctness_class") not in ("BIT", "SAME-TOK"):
        return []
    out = []
    for mode, md5 in sorted((g.get("base") or {}).items()):
        c = (g.get("cand") or {}).get(mode)
        if c is None:
            out.append(f"{mode}: no candidate md5")
        elif c != md5:
            out.append(f"{mode}: md5 {c[:8]} != base {md5[:8]} for a {card['correctness_class']} claim (FMA contraction or a reordered sum?)")
    return out
