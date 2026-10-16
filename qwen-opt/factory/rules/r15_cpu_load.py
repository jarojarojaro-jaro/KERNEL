"""R15: background CPU load (builds) skews decode timing; measure only in a quiet window."""
from rules import RulePolicy

POLICY = RulePolicy(
    "R15", "cpu-load", ("preflight",), "block", "REFUSE",
    source="-bs measurement spoiled by CPU load, redone (NOTES.md:169); RTX 3060 2026-10-16: during a build Saluki "
           "9.7 instead of 22.5 t/s, numbers dropped",
    lesson="lekcja-obciazenie-cpu", failure_mode="07#15")


def limit(nproc):
    return max(4.0, 0.5 * (nproc or 8))


def check(ctx):
    s = ctx.get("snapshot")
    if not s or not s.get("loadavg"):
        return []
    l1 = s["loadavg"][0]
    lim = limit(s.get("nproc"))
    return [f"loadavg {l1:.1f} > {lim:.1f} on {s.get('nproc')} CPUs"] if l1 > lim else []
