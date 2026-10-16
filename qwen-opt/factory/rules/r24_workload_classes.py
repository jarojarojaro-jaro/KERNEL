"""R24: the held-out workload covers both classes (new writing, copy/edit) and both languages (PL, EN)."""
from rules import RulePolicy

POLICY = RulePolicy(
    "R24", "workload-classes", ("measurement",), "block", "INVALID",
    source="HyperQwen 381 t/s on verbatim copy vs 133 on chat; tqLLM 273 at T=0/320 tok vs 131-155 on summaries "
           "(15b, 15c); PFlash probe: PL top-1 1/10 vs EN 10/10 (15d)",
    lesson="lekcja-benchmark-kopia", failure_mode="lekcja")

NEED = {"class": {"new-writing", "copy-edit"}, "lang": {"pl", "en"}}


def check(ctx):
    w = ctx.get("workload")
    if not w:
        return []
    sealed = [p for p in w.get("prompts") or [] if p.get("set", "sealed") == "sealed"]
    out = []
    for key, need in NEED.items():
        have = {p.get(key) for p in sealed}
        if not need <= have:
            out.append(f"sealed set lacks {key} {sorted(need - have)}")
    return out
