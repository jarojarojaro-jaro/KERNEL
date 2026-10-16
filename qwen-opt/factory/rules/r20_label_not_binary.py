"""R20: a label is not a binary: every measurement carries lib sha256 and build_info."""
from rules import RulePolicy

POLICY = RulePolicy(
    "R20", "label-not-binary", ("measurement", "history"), "block", "INVALID",
    source="fusion/spec_sweep.jsonl: label 'r1-base-qwen' is 41.70 ms/step on 2026-10-12 18:17 and 33.15 on "
           "2026-10-13 13:38 (different binaries under one name); 'base' -> overwritten ~/llama-opt 29.12-29.81 ms",
    lesson="lekcja-label-to-nie-binarka", failure_mode="lekcja")

DRIFT = 0.01


def check(ctx):
    out = []
    for r in ctx.get("runs") or []:
        if r.get("ok", True) and not (r.get("lib_sha256") and r.get("build_info")):
            out.append(f"run {r.get('arm')}{r.get('round')}.{r.get('pos')}: no lib_sha256/build_info")
    groups = {}
    for r in ctx.get("history") or []:
        if "median_ms_step" in r and not r.get("lib_sha256"):
            groups.setdefault(r["label"], []).append(r["median_ms_step"])
    for label, xs in sorted(groups.items()):
        if len(xs) > 1 and max(xs) / min(xs) - 1 > DRIFT:
            out.append(f"label {label!r}: {min(xs):.2f}-{max(xs):.2f} ms/step without a binary hash")
    return out
