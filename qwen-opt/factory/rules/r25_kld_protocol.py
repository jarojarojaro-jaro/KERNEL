"""R25: KLD numbers compare only under one protocol (context, chunks, reference logits, corpus)."""
from rules import RulePolicy

POLICY = RulePolicy(
    "R25", "kld-protocol", ("correctness",), "block", "INVALID",
    source="ISTA GSQ-RCO IQ3_S: KLD 0.0519 at ctx 512 and 0.0665 at ctx 2048 (+28%) for the same file; Swift measures "
           "against its own BF16 (15e)",
    lesson="lekcja-kld-protokoly", failure_mode="lekcja")

KEYS = ("ctx", "chunks", "ppl_base", "reference", "text")


def check(ctx):
    k = ctx.get("kld")
    if not k or "base" not in k or "cand" not in k:
        return []
    b, c = k["base"], k["cand"]
    return [f"KLD {key}: base {b.get(key)!r} vs cand {c.get(key)!r}" for key in KEYS
            if key in b or key in c if b.get(key) != c.get(key)]
