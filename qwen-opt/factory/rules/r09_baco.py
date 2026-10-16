"""R09: runtime suspend (BACO) moves VRAM into GTT; the model then runs over PCIe."""
from rules import RulePolicy

POLICY = RulePolicy(
    "R09", "baco-runtime-suspend", ("preflight", "measurement"), "block", "INVALID",
    source="2026-10-10: vram_used 35 MB, gtt_used 23.8 GB, 4.4 instead of 92 t/s; fix power/control=on or "
           "gpu-keepawake; KERNEL/qwen-opt/NOTES.md:122-126",
    lesson="baco-runtime-suspend", failure_mode="07#9")

GTT_MAX = 4 << 30


def check(ctx):
    out = []
    s = ctx.get("snapshot")
    if s and s.get("power_control") not in (None, "on") and not s.get("keepawake"):
        out.append(f"power/control={s.get('power_control')} and no gpu-keepawake: the card can suspend (BACO)")
    for r in ctx.get("runs") or []:
        t = r.get("telemetry") or {}
        g, v = t.get("max_gtt_used"), t.get("max_vram_used")
        if g is not None and v is not None and g > GTT_MAX and g > v:
            out.append(f"run {r.get('arm')}{r.get('round')}.{r.get('pos')}: gtt_used {g / 2**30:.1f} GiB > vram_used "
                       f"{v / 2**30:.1f} GiB (model evicted to system RAM)")
    return out
