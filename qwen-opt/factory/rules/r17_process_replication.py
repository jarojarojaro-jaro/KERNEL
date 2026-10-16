"""R17: every arm runs in >= 2 fresh processes per verification, with an A/A control."""
from rules import RulePolicy
from rules._util import by_arm

POLICY = RulePolicy(
    "R17", "process-replication", ("measurement",), "block", "INVALID",
    source="LFM expert gate+up 24.3 -> 27.2 us per call in 4/8 profiles, also on an unchanged build (~0.11 ms/token); "
           "KERNEL/qwen-opt/NOTES.md:359",
    lesson="lekcja-losowe-spowolnienia", failure_mode="07#17")


def check(ctx):
    if not ctx.get("runs"):
        return []
    out = []
    arms = by_arm(ctx)
    for arm in ("A", "B"):
        pids = {r.get("pid") for r in arms.get(arm, [])}
        if len(pids) < 2:
            out.append(f"arm {arm}: {len(pids)} process(es), need >= 2")
    if not ctx.get("aa"):
        out.append("no A/A control")
    return out
