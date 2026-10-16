"""R03: greedy md5 evidence must come from fresh servers: never the same prompt twice in one process."""
from rules import RulePolicy

POLICY = RulePolicy(
    "R03", "fresh-server-md5", ("correctness",), "block", "INVALID",
    source="det_probe.py 2026-10-14: the same greedy request without prompt cache gives another text on the 2nd call "
           "after server start (diverges after ~270 chars), upstream e60eff95f too; KERNEL/qwen-opt/NOTES.md:377",
    lesson="lekcja-ten-sam-serwer-pending-h", failure_mode="07#3")


def check(ctx):
    reqs = ctx.get("greedy_requests")
    if not reqs:
        return []
    seen, out = set(), []
    for r in reqs:
        k = (r.get("pid"), r.get("prompt"))
        if k in seen:
            out.append(f"pid {r.get('pid')}: prompt {str(r.get('prompt'))[:40]!r} sent twice to one server process")
        seen.add(k)
    return out
