"""R04: md5 comparisons only within one decode mode (plain with plain, MTP with MTP)."""
from rules import RulePolicy

POLICY = RulePolicy(
    "R04", "same-mode-md5", ("correctness",), "block", "INVALID",
    source="speculative verification changes batch numerics: MTP diverges from plain after 129 chars, DFlash after 229; "
           "production XTX md5 plain c4708318 vs MTP 6f14e814 (both correct); NOTES.md:287, qwen-round5.md",
    lesson="lekcja-spekulacja-zmienia-numeryke", failure_mode="07#4")


def check(ctx):
    return [f"md5 of mode {a} compared with mode {b}" for a, b in ctx.get("greedy_compared") or [] if a != b]
