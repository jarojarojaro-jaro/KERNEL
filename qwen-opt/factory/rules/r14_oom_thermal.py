"""R14: OOM in the server log or a junction temperature near the limit invalidates the run."""
import re

from rules import RulePolicy

POLICY = RulePolicy(
    "R14", "oom-thermal", ("preflight", "measurement"), "block", "INVALID",
    source="-ub 2048 with ctx 204800 went OOM (24.5 GB VRAM) on the first long prompt (NOTES.md:218); junction 106 C "
           "during a 196k prefill (edge 66 C, 281 W, NOTES.md:118)",
    lesson="lekcja-oom-ub2048", failure_mode="07#14")

OOM = re.compile(r"out of memory|failed to allocate|hipErrorOutOfMemory|cudaMalloc failed|"
                 r"ErrorOutOfDeviceMemory|unable to allocate", re.I)
JUNCTION_RUN_MAX = 100.0
JUNCTION_START_MAX = 90.0


def check(ctx):
    out = []
    s = ctx.get("snapshot")
    if s:
        j = (s.get("temp_c") or {}).get("junction")
        if j is not None and j >= JUNCTION_START_MAX:
            out.append(f"junction {j:.0f} C at start >= {JUNCTION_START_MAX:.0f} C (cool down first)")
    for r in ctx.get("runs") or []:
        name = f"run {r.get('arm')}{r.get('round')}.{r.get('pos')}"
        m = OOM.search(r.get("log_tail") or "")
        if m:
            out.append(f"{name}: server log: {m.group(0)}")
        j = (r.get("telemetry") or {}).get("max_junction_c")
        if j is not None and j >= JUNCTION_RUN_MAX:
            out.append(f"{name}: junction reached {j:.0f} C (thermal throttling)")
    return out
