"""R02: kernel numerics touched (reductions, tiles, split-K) but the card claims SAME-TOK (a host/sampler class)."""
import re

from rules import RulePolicy
from rules._util import touched

POLICY = RulePolicy(
    "R02", "reduction-order-class", ("static",), "block", "INVALID",
    source="new FA prefill tile changed the accumulation order: KLD 0.0135, fixed by 0043 (K chunks in order, KLD 0); "
           "patches/llama.cpp-amd-opt/0043-*.patch touches ggml/src/ggml-cuda/fattn-mma-f16.cuh",
    lesson="lekcja-kolejnosc-akumulacji-fa", failure_mode="07#2")

NUMERIC = re.compile(r"ggml/src/ggml-[a-z]+/.*(fattn|mmq|mmvq|mmf|reduce|softmax|norm|ssm|gated|gdn|sum|rope|convert|"
                     r"quantize|mul_mat|wkv|topk|argmax|vec_dot|vecdotq|template-instances)")


def check(ctx):
    card = ctx.get("card") or {}
    t = touched(ctx)
    if not t or card.get("correctness_class") != "SAME-TOK":
        return []
    return [f"{p}: kernel numerics changed, but SAME-TOK only covers host/sampler changes (use BIT, NEAR-TIE or KLD)"
            for p in t if NUMERIC.search(p)]
