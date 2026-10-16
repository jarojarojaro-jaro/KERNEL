"""R13: never a one-prompt benchmark: >= 6 prompts including the sealed set, and every run covers all of them."""
from rules import RulePolicy

POLICY = RulePolicy(
    "R13", "prompt-count", ("measurement",), "block", "INVALID",
    source="'DFlash 120 t/s' was one prompt (EN code LRU, 256 tok, T=0); on the prompt set ~ MTP; NOTES.md:158",
    lesson="lekcja-jeden-prompt", failure_mode="07#13")

MIN_PROMPTS, MIN_SEALED = 6, 4


def check(ctx):
    w = ctx.get("workload")
    if not w:
        return []
    prompts = w.get("prompts") or []
    out = []
    if len(prompts) < MIN_PROMPTS:
        out.append(f"{len(prompts)} prompts < {MIN_PROMPTS}")
    sealed = [p for p in prompts if p.get("set") == "sealed"]
    if len(sealed) < MIN_SEALED:
        out.append(f"{len(sealed)} sealed prompts < {MIN_SEALED} (held-out set missing)")
    ids = {p["id"] for p in prompts}
    for r in ctx.get("runs") or []:
        if r.get("ok", True) and r.get("n_tokens") is not None:
            missing = ids - set(r["n_tokens"])
            if missing:
                out.append(f"run {r.get('arm')}{r.get('round')}.{r.get('pos')}: prompts missing {sorted(missing)[:3]}")
    return out
