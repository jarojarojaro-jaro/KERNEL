#!/usr/bin/env python3
"""Temporal MoE routing locality from a maya-ik2 IK2_TRACE file (ik2_main.cu:350, 3477-3481, 4148-4152).

IK2_TRACE records: int32 (layer, T, K) then T*K int32 expert ids, one record per visit per forward call,
visits in order (Inkling 2 Mini: layers 0-5, 6-17 x3, 18-23 = 48 visits). A forward starts at layer 0.

Reports what moe-xray (static histograms) does not:
  U(B)      mean distinct experts in a window of B consecutive tokens / K, vs independent routing
            (E/K)(1-(1-K/E)^B): the expert-read factor of a B-row verify window when picks are grouped by expert.
  overlap1  |E_t & E_t+1| / K per visit (consecutive tokens).
  xpass     |E_(L,pass p) & E_(L,pass q)| / K for the looped layers, same token (chance = K/E).
  --jsonl   writes moe-xray's {"layer": visit, "experts": [...]} events for `moe_xray.py profile`.
Stdlib only.
"""
import argparse, json, struct, sys
from collections import defaultdict


def read_trace(path):
    data = open(path, "rb").read()
    off, recs = 0, []
    while off + 12 <= len(data):
        layer, T, K = struct.unpack_from("<3i", data, off)
        off += 12
        n = T * K
        ex = struct.unpack_from(f"<{n}i", data, off)
        off += 4 * n
        recs.append((layer, T, K, ex))
    if off != len(data):
        sys.exit(f"{path}: trailing {len(data) - off} bytes (not an IK2_TRACE file?)")
    return recs


def to_tokens(recs):
    """-> K, n_visit, visit layers, tokens: list of per-token lists [visit] -> frozenset(experts)."""
    fwds, cur = [], None
    for r in recs:
        if r[0] == 0 and (cur is None or any(x[0] != 0 for x in cur)):
            cur = []
            fwds.append(cur)
        cur.append(r)
    nvis = max(len(f) for f in fwds)
    fwds = [f for f in fwds if len(f) == nvis]
    layers = [r[0] for r in fwds[0]]
    K = fwds[0][0][2]
    toks = []
    for f in fwds:
        T = f[0][1]
        for t in range(T):
            toks.append([frozenset(r[3][t * K:(t + 1) * K]) for r in f])
    return K, nvis, layers, toks


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("trace")
    ap.add_argument("--experts", type=int, default=128)
    ap.add_argument("--max-b", type=int, default=8)
    ap.add_argument("--skip", type=int, default=0, help="tokens to drop at the start (e.g. the chat template)")
    ap.add_argument("--jsonl", help="write moe-xray events (layer = visit index)")
    ap.add_argument("--json", dest="json_out")
    a = ap.parse_args()
    K, nvis, layers, toks = to_tokens(read_trace(a.trace))
    toks = toks[a.skip:]
    E, n = a.experts, len(toks)
    if n < a.max_b + 1:
        sys.exit(f"only {n} tokens")
    out = {"tokens": n, "visits": nvis, "K": K, "E": E}
    print(f"{n} tokens x {nvis} visits, top-{K} of {E}")

    ub = {}
    for B in range(1, a.max_b + 1):
        tot = cnt = 0
        for v in range(nvis):
            for t in range(n - B + 1):
                tot += len(frozenset().union(*(toks[t + i][v] for i in range(B))))
                cnt += 1
        ind = (E / K) * (1 - (1 - K / E) ** B)
        ub[B] = (tot / cnt / K, ind)
    print("B   U(B) measured   independent   (expert reads of a B-row window / one token's)")
    for B, (m, i) in ub.items():
        print(f"{B:<3} {m:14.2f} {i:13.2f}")
    out["U"] = {B: {"measured": round(m, 4), "independent": round(i, 4)} for B, (m, i) in ub.items()}

    ov = [sum(len(toks[t][v] & toks[t + 1][v]) for t in range(n - 1)) / (n - 1) / K for v in range(nvis)]
    print(f"consecutive-token overlap per visit: mean {sum(ov)/nvis:.3f} (chance {K/E:.3f}), "
          f"min {min(ov):.3f} @v{ov.index(min(ov))}, max {max(ov):.3f} @v{ov.index(max(ov))}")
    out["overlap1"] = [round(x, 4) for x in ov]

    vis_of = defaultdict(list)
    for v, l in enumerate(layers):
        vis_of[l].append(v)
    xp = {}
    for l, vs in sorted(vis_of.items()):
        if len(vs) < 2:
            continue
        for i in range(len(vs)):
            for j in range(i + 1, len(vs)):
                s = sum(len(tk[vs[i]] & tk[vs[j]]) for tk in toks) / n / K
                xp.setdefault(f"p{i+1}-p{j+1}", []).append(s)
    for k, vals in xp.items():
        print(f"cross-pass overlap {k} (same layer, same token): mean {sum(vals)/len(vals):.3f} over {len(vals)} layers")
    out["xpass"] = {k: round(sum(v) / len(v), 4) for k, v in xp.items()}

    if a.jsonl:
        with open(a.jsonl, "w") as f:
            for tk in toks:
                for v in range(nvis):
                    f.write(json.dumps({"layer": v, "experts": sorted(tk[v])}) + "\n")
    if a.json_out:
        json.dump(out, open(a.json_out, "w"), indent=1)


if __name__ == "__main__":
    main()
