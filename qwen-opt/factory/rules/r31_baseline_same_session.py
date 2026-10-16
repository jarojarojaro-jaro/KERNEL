"""R31: the baseline is measured in the same verification session as the candidate, never taken from history."""
from rules import RulePolicy
from rules._util import by_arm

POLICY = RulePolicy(
    "R31", "baseline-same-session", ("measurement",), "block", "INVALID",
    source="Lucebox PFlash v1 '~10.4x' vs a cold llama.cpp (~257 s) instead of warm 169.3 s (x6.8); our 'base' label "
           "drifted 29.12-29.81 ms/step between sessions (15f E-B)",
    lesson="lekcja-baseline-wlasnego-silnika", failure_mode="lekcja")


def check(ctx):
    if not ctx.get("runs"):
        return []
    arms = by_arm(ctx)
    out = []
    if not arms.get("A"):
        out.append("no baseline (A) runs in this session")
    sessions = {r.get("session") for r in ctx["runs"]}
    if len(sessions) > 1:
        out.append(f"runs come from {len(sessions)} sessions: {sorted(map(str, sessions))[:3]}")
    return out
