"""R22: every request of every run follows the harness protocol (tokens, seeds, temperature, no prompt cache)."""
from fk.profiles import PROTOCOL
from rules import RulePolicy

POLICY = RulePolicy(
    "R22", "protocol-fixed", ("measurement",), "block", "INVALID",
    source="Sakana AI Scientist v3 (arXiv 2610.18933 §6.3): in 2 of 3 Pi runs the agent switched evaluation to "
           "majority vote instead of pass@1, unnoticed by evaluator and rubrics; our analogue: max_tokens, cache_prompt, "
           "seeds or temperature in spec_sweep",
    lesson="lekcja-agent-zmienia-protokol", failure_mode="lekcja")

KEYS = ("tokens", "temps", "seeds", "cache_prompt")


def check(ctx):
    proto = ctx.get("protocol") or PROTOCOL
    out = []
    for r in ctx.get("runs") or []:
        req = r.get("request")
        if req is None:
            continue
        bad = [f"{k}={req.get(k)!r} (protocol {proto[k]!r})" for k in KEYS if req.get(k) != proto[k]]
        extra = sorted(set(req) - set(KEYS) - {"variants"})
        if extra:
            bad.append(f"extra request fields {extra}")
        if bad:
            out.append(f"run {r.get('arm')}{r.get('round')}.{r.get('pos')}: " + "; ".join(bad))
    return out
