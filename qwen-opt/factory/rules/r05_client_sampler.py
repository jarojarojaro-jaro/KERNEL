"""R05: a sampler/server change must be measured with the client-UI request variants too."""
import re

from rules import RulePolicy
from rules._util import touched

POLICY = RulePolicy(
    "R05", "client-sampler-workload", ("static", "measurement"), "block", "INVALID",
    source="web UI reasoning_control, thinking budget, repeat_penalty 1.05 in the LFM GGUF, tool grammar, logit_bias, "
           "n_probs switched to the full 128k/248k candidate path: LFM 291.4 vs 255.6 t/s (2026-10-15); 0048, 0065-0069 "
           "touch common/sampling.cpp and tools/server/server-context.cpp; NOTES.md:345,381-392",
    lesson="lekcja-wolna-sciezka-samplera", failure_mode="07#5")

SAMPLER = re.compile(r"^(common/sampling|common/reasoning|common/chat|src/llama-sampl|src/llama-grammar|"
                     r"tools/server/server-(context|task|common))")
UI_VARIANT = "client-ui"


def needs_client_ui(paths) -> bool:
    return any(SAMPLER.match(p) for p in paths or [])


def check(ctx):
    t = touched(ctx)
    if not needs_client_ui(t):
        return []
    variants = set((ctx.get("workload") or {}).get("variants") or [])
    if UI_VARIANT in variants:
        return []
    hit = [p for p in t if SAMPLER.match(p)]
    return [f"{', '.join(hit)} touched, workload lacks the {UI_VARIANT} variant (reasoning_control, logit_bias, n_probs, "
            f"grammar)"]
