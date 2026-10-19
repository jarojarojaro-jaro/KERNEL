#!/usr/bin/env python3
"""24j: oracle ceiling of a lookup-tail / DFlash2 router on mvs, from the per-step lookup logs of topka's config
(LLAMA_SPEC_LOOKUP=3, W16; ~/qwen-opt/lookup/logs/e4-mvs-{W5,D3,D4}.lk.jsonl, requests 2-5 = T=0, 6-13 = T=1).

Per step: k = 0 drafter only (tail missed), 1 MTP4 + tail, 2 lookup chain; a = accepted drafts, tokens = a + 1.
DFlash2 has block 8, so at most 8 tokens per step. The ceiling gives every chosen step 8 tokens at no extra cost:
  router: only tail-miss steps (k = 0) -> 8 tokens;   any<8: every step with < 8 tokens -> 8 tokens.
Step costs only matter for the topka t/s model (XTX 2k, 16b E2: MTP4 29.8 ms, tail +6.4, chain -3.6)."""
import collections
import json

LOGS = "/home/jaro/qwen-opt/lookup/logs/e4-mvs-%s.lk.jsonl"


def load(path):
    reqs = collections.OrderedDict()
    for line in open(path):
        d = json.loads(line)
        if "b" in d:
            reqs[d["b"]] = []
        else:
            reqs[d["r"]].append(d)
    return reqs


for arm in ("W5", "D3", "D4"):
    reqs = load(LOGS % arm)
    for name, rs in (("T0", range(2, 6)), ("T1", range(6, 14))):
        steps = [s for r in rs for s in reqs[r]]
        n = sum(s["a"] + 1 for s in steps)
        miss = [s for s in steps if s["k"] == 0]
        router = sum(8 if s["k"] == 0 else s["a"] + 1 for s in steps)
        any8 = sum(max(s["a"] + 1, 8) for s in steps)
        print(f"{arm} {name}: steps {len(steps)}, tok/step {n / len(steps):.2f}, tail-miss steps {len(miss)} "
              f"({100 * len(miss) / len(steps):.1f}%, MTP accepted {collections.Counter(s['a'] for s in miss)}), "
              f"ceiling router +{100 * (router / n - 1):.2f}%, any<8 +{100 * (any8 / n - 1):.2f}%")
