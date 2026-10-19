#!/usr/bin/env python3
"""21f: AgentX v1.0 (256k) trace statistics + single-user local replay model (CPU only).

Input: traces.jsonl from https://huggingface.co/datasets/semianalysisai/cc-traces-weka-062126-256k
usage: [MODEL=qwen|lfm] 21f-agentx-stats.py /tmp/agentx/traces.jsonl

Prefix-cache policies (hash ids are session-scoped *chained* 64-token block hashes, so a seen id
implies its whole prefix was seen):
  radix  - any earlier request of the session (vLLM/SGLang APC; llama.cpp would need many slots)
  lane   - previous request of the same lane (main chain or one subagent) = one slot per lane
  single - previous request in session time order = llama-server -np 1 (one shared slot)

Local models (RX 7900 XTX, our fork, ~/qwen-opt/long_ctx.jsonl; Qwen label e2e-final = NOTES:331, LFM lfm-base = NOTES:336):
  prefill T(N) = a*N + b*N^2 fitted to the ~30k/~94k points -> marginal cost a + 2*b*D per token at depth D
  decode ms/token(D) linear through the 1.7k and 94k points (Qwen: MTP n=4, T=0; LFM: no speculation)
Tool/think time between requests is capped at 10 s like the AgentX scenario ("globally idle" cap).
"""
from __future__ import annotations

import json
import os
import statistics
import sys
from collections import Counter

BLOCK = 64
IDLE_CAP_S = 10.0

CURVES = {
    # prefill (tokens, t/s) x2, decode (depth, t/s) x2, cache-ram state (fixed bytes, bytes at 53k)
    "qwen": ((29510, 939.1), (94181, 763.2), (1714, 130.2), (94181, 97.51), (0.15e9, 2.28 * 2**30)),
    "lfm": ((29733, 5172.2), (94974, 3708.7), (1707, 173.73), (94974, 153.06), (0.05e9, 553 * 2**20)),
}
(P1, R1), (P2, R2), (D1, V1), (D2, V2), (STATE_FIXED_B, STATE_53K_B) = CURVES[os.environ.get("MODEL", "qwen")]
T1, T2 = P1 / R1, P2 / R2
B = (T2 / P2 - T1 / P1) / (P2 - P1)
A = T1 / P1 - B * P1
S1, S2 = 1 / V1, 1 / V2
DEC_SLOPE = (S2 - S1) / (D2 - D1)
# llama-server --cache-ram restore (16f E4/E5: Qwen 53k entry 2.3 GB, copy ~1.1 s => ~2.1 GB/s; LFM 553 MiB at 53k)
STATE_PER_TOKEN_B = (STATE_53K_B - STATE_FIXED_B) / 53_000
RESTORE_BPS = 2.3e9 / 1.1


def prefill_s(new: int, depth_end: int) -> float:
    """Seconds to prefill `new` tokens ending at depth `depth_end`."""
    d0 = max(depth_end - new, 0)
    return A * (depth_end - d0) + B * (depth_end**2 - d0**2)


def decode_s(out: int, depth: int) -> float:
    return out * (S1 + DEC_SLOPE * (depth - D1))


def restore_s(depth: int) -> float:
    return (STATE_FIXED_B + STATE_PER_TOKEN_B * depth) / RESTORE_BPS


def pct(v: list[float], p: float) -> float:
    s = sorted(v)
    k = (len(s) - 1) * p / 100
    f = int(k)
    return s[f] if f + 1 >= len(s) else s[f] + (k - f) * (s[f + 1] - s[f])


def matched(hashes: list[int], seen: set[int]) -> int:
    n = 0
    for h in hashes:
        if h not in seen:
            break
        n += 1
    return n


def common_prefix(a: list[int], b: list[int]) -> int:
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    return n


def main() -> None:
    path = sys.argv[1]
    reqs = []  # flattened per request
    sub_groups = []
    sessions = 0
    max_par = []
    with open(path) as f:
        for line in f:
            tr = json.loads(line)
            sessions += 1
            flat = []
            intervals = []
            for r in tr["requests"]:
                if r["type"] == "subagent":
                    intervals.append((r["t"], r["t"] + r["duration_ms"] / 1000))
                    sub_groups.append(len(r["requests"]))
                    for q in r["requests"]:
                        flat.append((q, "sub:" + r["agent_id"]))
                else:
                    flat.append((r, "main"))
            # peak concurrent subagent groups
            ev = sorted([(a, 1) for a, _ in intervals] + [(b, -1) for _, b in intervals])
            cur = peak = 0
            for _, d in ev:
                cur += d
                peak = max(peak, cur)
            max_par.append(peak)
            flat.sort(key=lambda x: x[0]["t"])
            seen: set[int] = set()
            last_lane: dict[str, list[int]] = {}
            last_any: list[int] = []
            prev_lane = "main"
            for q, lane in flat:
                h = q["hash_ids"]
                m_radix = matched(h, seen)
                m_lane = common_prefix(h, last_lane.get(lane, []))
                m_single = common_prefix(h, last_any)
                seen.update(h)
                last_lane[lane] = h
                last_any = h
                switch = lane != prev_lane
                prev_lane = lane
                n_in = q["in"]
                reqs.append({
                    "sid": tr["id"], "lane": lane, "main": lane == "main", "model": q["model"],
                    "in": n_in, "out": q["out"], "api": q.get("api_time", 0.0),
                    "think": q.get("think_time", 0.0),
                    "new_radix": max(n_in - BLOCK * m_radix, 0),
                    "new_lane": max(n_in - BLOCK * m_lane, 0),
                    "new_single": max(n_in - BLOCK * m_single, 0),
                    "switch": switch,
                })

    n = len(reqs)
    ins = [r["in"] for r in reqs]
    outs = [r["out"] for r in reqs]
    print(f"sessions {sessions}  requests {n}  subagent groups {len(sub_groups)}")
    print(f"input  tokens total {sum(ins):,}  mean {statistics.mean(ins):,.0f}  p50 {pct(ins,50):,.0f}  p90 {pct(ins,90):,.0f}  p99 {pct(ins,99):,.0f}")
    print(f"output tokens total {sum(outs):,}  mean {statistics.mean(outs):,.0f}  p50 {pct(outs,50):,.0f}  p90 {pct(outs,90):,.0f}  p99 {pct(outs,99):,.0f}")
    print(f"input:output ratio {sum(ins)/sum(outs):.1f}")
    main_r = [r for r in reqs if r["main"]]
    sub_r = [r for r in reqs if not r["main"]]
    print(f"main requests {len(main_r)}  subagent requests {len(sub_r)}")
    for name, rr in (("main", main_r), ("sub", sub_r)):
        print(f"  {name}: in p50 {pct([r['in'] for r in rr],50):,.0f}  out p50 {pct([r['out'] for r in rr],50):,.0f}  out mean {statistics.mean([r['out'] for r in rr]):,.0f}")
    print("models:", Counter(r["model"] for r in reqs).most_common())
    for cap in (32_000, 64_000, 100_000, 128_000, 200_000):
        keep = [r for r in reqs if r["in"] + r["out"] <= cap]
        print(f"cap {cap//1000:>3}k: requests kept {len(keep)/n:6.1%}  output tokens kept {sum(r['out'] for r in keep)/sum(outs):6.1%}")
    print(f"subagent groups: requests/group p50 {pct(sub_groups,50):.0f}; sessions with peak parallel groups >=2: "
          f"{sum(1 for p in max_par if p>=2)}/{sessions}, peak max {max(max_par)}")
    thinks = [r["think"] for r in reqs if r["think"] > 0]
    print(f"think/tool time >0: p50 {pct(thinks,50):.2f}s p90 {pct(thinks,90):.1f}s; share >10s {sum(1 for t in thinks if t>10)/len(thinks):.1%}")

    for pol in ("radix", "lane", "single"):
        new = [r[f"new_{pol}"] for r in reqs]
        print(f"uncached tokens [{pol:6}]: total {sum(new):,} = {sum(new)/sum(ins):.1%} of input; p50 {pct(new,50):,.0f} p90 {pct(new,90):,.0f} p99 {pct(new,99):,.0f}")

    # --- local single-user replay model, sequential (one request at a time) ---
    print(f"\nlocal model: prefill a={A*1e3:.3f} ms/tok b={B*1e9:.3f} ns/tok^2 -> marginal @0 {1/A:.0f} t/s, @100k {1/(A+2*B*100_000):.0f} t/s, @200k {1/(A+2*B*200_000):.0f} t/s")
    print(f"             decode @1.7k {1/S1:.1f} t/s, @100k {1/(S1+DEC_SLOPE*(100_000-D1)):.1f}, @200k {1/(S1+DEC_SLOPE*(200_000-D1)):.1f}")
    for cap in (200_000, 128_000, 64_000):
        rr = [r for r in reqs if r["in"] + r["out"] <= cap]
        tool = sum(min(r["think"], IDLE_CAP_S) for r in rr)
        dec = sum(decode_s(r["out"], r["in"]) for r in rr)
        api = sum(r["api"] for r in rr)
        for pol in ("radix", "lane", "single"):
            pre = sum(prefill_s(r[f"new_{pol}"], r["in"]) for r in rr)
            tot = pre + dec + tool
            print(f"cap {cap//1000:>3}k {pol:6}: prefill {pre/3600:7.1f} h ({pre/tot:5.1%})  decode {dec/3600:6.1f} h ({dec/tot:5.1%})  "
                  f"tool<=10s {tool/3600:6.1f} h ({tool/tot:5.1%})  | x2 decode -> wall -{dec/2/tot:5.1%}; x2 prefill -> wall -{pre/2/tot:5.1%}"
                  f"  | Anthropic api_time {api/3600:.1f} h")
        # llama-server -np 1 + --cache-ram: lane prefix kept in RAM, each lane switch restores the state
        pre = sum(prefill_s(r["new_lane"], r["in"]) for r in rr)
        rest = sum(restore_s(r["in"]) for r in rr if r["switch"])
        tot = pre + rest + dec + tool
        print(f"cap {cap//1000:>3}k cram  : prefill {pre/3600:7.1f} h + RAM restore {rest/3600:5.1f} h "
              f"({sum(1 for r in rr if r['switch'])} switches)  decode {dec/tot:5.1%} of wall {tot/3600:.1f} h")
        # per-request p90 'interactivity' proxy: out / decode time, at depth
        intv = [r["out"] / decode_s(r["out"], r["in"]) for r in rr if r["out"] > 1]
        e2e = [r["out"] / (decode_s(r["out"], r["in"]) + prefill_s(r["new_lane"], r["in"])) for r in rr if r["out"] > 1]
        print(f"            model interactivity (tok/s/user): p50 {pct(intv,50):.1f}  slow-tail p10 {pct(intv,10):.1f}; "
              f"E2E-normalized (lane cache) p50 {pct(e2e,50):.1f} p10 {pct(e2e,10):.1f}")


if __name__ == "__main__":
    main()
