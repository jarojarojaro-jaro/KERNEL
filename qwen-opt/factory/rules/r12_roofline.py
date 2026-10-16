"""R12: no number may beat the memory roofline (bytes per model pass, not per token)."""
import re

from fk import paths
from rules import RulePolicy
from rules._util import by_arm, med

POLICY = RulePolicy(
    "R12", "roofline", ("physics", "text"), "block", "INVALID",
    source="report autokernel-amd 15-road-to-65 §16 claimed 1075 GB/s = 112% of peak: bytes per token instead of per "
           "pass; with MTP one pass serves ~2.7 tokens, real ~400 GB/s; KERNEL/qwen-opt/NOTES.md:104-105",
    lesson="lekcja-bledny-roofline", failure_mode="07#12")

GBS = re.compile(r"(\d+(?:[.,]\d+)?)\s*GB/s")
PCT_PEAK = re.compile(r"(\d+(?:[.,]\d+)?)\s*%\s*(?:of\s+)?peak", re.I)


def check(ctx):
    out = []
    peak = ctx.get("peak_bw", paths.PEAK_BW)
    prof = ctx.get("profile") or {}
    bpp = prof.get("bytes_per_pass")
    if bpp:
        for arm, runs in sorted(by_arm(ctx).items()):
            ms = med([r["values"][k] for r in runs for k in ("ms_step", "ms_token") if k in (r.get("values") or {})])
            if ms:
                bw = bpp / (ms / 1000.0)
                if bw > paths.ROOFLINE_MAX * peak:
                    out.append(f"arm {arm}: {bpp / 1e9:.2f} GB per pass in {ms:.3f} ms = {bw / 1e9:.0f} GB/s "
                               f"> {paths.ROOFLINE_MAX:.0%} of {peak / 1e9:.0f} GB/s")
    text = ctx.get("text")
    if text:
        for m in GBS.finditer(text):
            v = float(m.group(1).replace(",", "."))
            if v > peak / 1e9:
                out.append(f"text: {m.group(0)} is above the {peak / 1e9:.0f} GB/s peak")
        for m in PCT_PEAK.finditer(text):
            if float(m.group(1).replace(",", ".")) > 100:
                out.append(f"text: {m.group(0)} is above 100% of peak")
    return out
