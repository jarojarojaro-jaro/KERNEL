"""R18: the harness must not change while it runs (hash before == hash after every block)."""
from rules import RulePolicy

POLICY = RulePolicy(
    "R18", "harness-overwrite", ("measurement",), "block", "INVALID",
    source="RTX 5060 Ti: scp overwrote the running plan.sh (same inode) and cut the Qwen host-switch phase after 2 "
           "switches; rerun as plan2.sh",
    lesson="lekcja-nadpisanie-dzialajacego-skryptu", failure_mode="lekcja")


def check(ctx):
    a, b = ctx.get("harness_before"), ctx.get("harness_after")
    if a is None or b is None or a == b:
        return []
    if isinstance(a, dict) and isinstance(b, dict):
        changed = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
        return [f"harness changed during the run: {', '.join(changed[:5])}"]
    return ["harness changed during the run"]
