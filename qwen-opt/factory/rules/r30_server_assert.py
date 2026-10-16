"""R30: a server that asserted, crashed or exited early gives no measurement."""
import re

from rules import RulePolicy

POLICY = RulePolicy(
    "R30", "server-assert", ("measurement", "correctness"), "block", "INVALID",
    source="after the v0.7.0 rebase Qwen MTP with the draft vocab aborted on the first request: "
           "GGML_ASSERT(ubatch->embd_state ...) in llm_graph_input_embd_h::set_input (upstream 781dbc5ac)",
    lesson="lekcja-mtp-embd-state", failure_mode="lekcja")

CRASH = re.compile(r"GGML_ASSERT|GGML_ABORT|Segmentation fault|core dumped|terminate called|Aborted|HIP error|"
                   r"CUDA error")


def check(ctx):
    out = []
    for r in ctx.get("runs") or []:
        name = f"run {r.get('arm')}{r.get('round')}.{r.get('pos')}"
        m = CRASH.search(r.get("log_tail") or "")
        if m:
            out.append(f"{name}: {m.group(0)} in the server log")
        elif r.get("ok") is False:
            out.append(f"{name}: failed ({str(r.get('error', ''))[:80]})")
    return out
