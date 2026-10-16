"""R07: verdicts only on end-to-end metrics (server ms/step, ms/token, t/s; llama-bench pp/tg), never microbenchmarks."""
from fk.stats import E2E_METRICS
from rules import RulePolicy

POLICY = RulePolicy(
    "R07", "e2e-metric", ("static",), "block", "INVALID",
    source="mmvq-bench microbenchmark decided against Q6_K and GLC|DLC, the model with rocprofv3 gained "
           "(mmvq 24.3 -> 22.1 ms per verification); NOTES.md:247",
    lesson="lekcja-mikrobench-klamie", failure_mode="07#7")


def check(ctx):
    m = (ctx.get("card") or {}).get("metric")
    if m is None or m in E2E_METRICS:
        return []
    return [f"metric {m!r} is not end-to-end ({', '.join(sorted(E2E_METRICS))})"]
