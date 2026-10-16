"""R11: per-process values of one arm split into two clusters (grid = exactly one wave of the GPU, etc.)."""
from rules import RulePolicy
from rules._util import by_arm

POLICY = RulePolicy(
    "R11", "bimodal-per-process", ("measurement",), "block", "NEEDS-HUMAN",
    source="LFM round 4 (2026-10-14): a grid of exactly 3072 blocks on 96 CU gave 13.6 or 14.6 us per process, "
           "2560 blocks always 12.2 us; fixed for conv by 0062; KERNEL/qwen-opt/NOTES.md:378",
    lesson="lekcja-siatka-pelna-fala", failure_mode="07#11")


def bimodal(xs, min_rel_gap=0.005, ratio=5.0):
    xs = sorted(xs)
    if len(xs) < 4:
        return None
    gaps = [(xs[i + 1] - xs[i], i) for i in range(len(xs) - 1)]
    g, i = max(gaps)
    lo, hi = xs[:i + 1], xs[i + 1:]
    if len(lo) < 2 or len(hi) < 2:
        return None
    spread = max(lo[-1] - lo[0], hi[-1] - hi[0])
    mid = xs[len(xs) // 2]
    if g / mid >= min_rel_gap and g > ratio * spread:
        return (sum(lo) / len(lo), sum(hi) / len(hi))
    return None


def check(ctx):
    out = []
    metric = (ctx.get("card") or {}).get("metric") or ctx.get("metric")
    for arm, runs in sorted(by_arm(ctx).items()):
        xs = [r["values"][metric] for r in runs if metric in (r.get("values") or {})]
        b = bimodal(xs)
        if b:
            out.append(f"arm {arm}: {metric} per process splits into {b[0]:.4g} and {b[1]:.4g}")
    return out
