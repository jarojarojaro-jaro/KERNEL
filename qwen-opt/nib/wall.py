#!/usr/bin/env python3
"""Engine-neutral decode speed: streaming /v1/chat/completions, tokens = content+reasoning delta chunks (usage if given),
decode t/s = (tokens-1) / (t_last - t_first). usage: wall.py PORT TAG"""
import json, sys, time, urllib.request, statistics
port, tag = sys.argv[1], sys.argv[2]
import os
EXTRA = {k: (int(v) if k == "top_k" else float(v)) for k, v in (("top_k", os.environ.get("WALL_TOPK")), ("top_p", os.environ.get("WALL_TOPP"))) if v}
P = {"code": "Write a complete Python module implementing a thread-safe LRU cache with TTL expiry, type hints and pytest tests.",
     "tech": "Explain how a B-tree index works in a relational database: node layout, search, insertion with splits, deletion.",
     "pl": "Napisz opowiadanie (około 400 słów) o starym latarniku i sygnale z zatopionego okrętu.",
     "json": "Return a JSON array of 15 fictional employees with fields id, name, email, department, salary, start_date."}
def run(prompt, temp, n=300):
    b = {"messages": [{"role": "user", "content": prompt}], "max_tokens": n, "temperature": temp, "stream": True,
         "seed": 1, **EXTRA, "chat_template_kwargs": {"enable_thinking": False}, "stream_options": {"include_usage": True}}
    req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions", data=json.dumps(b).encode(), headers={"Content-Type": "application/json"})
    t0 = time.time(); tf = tl = None; k = 0; usage = None
    with urllib.request.urlopen(req, timeout=900) as r:
        for line in r:
            line = line.decode().strip()
            if not line.startswith("data:") or line.endswith("[DONE]"): continue
            d = json.loads(line[5:])
            if d.get("usage"): usage = d["usage"].get("completion_tokens")
            ch = d.get("choices") or []
            if ch and ((ch[0].get("delta") or {}).get("content") or (ch[0].get("delta") or {}).get("reasoning_content")):
                now = time.time(); tf = tf or now; tl = now; k += 1
    n_tok = usage or k
    return (n_tok - 1) / (tl - tf) if tl and tl > tf else 0, tf - t0, n_tok, k
for temp in (0.0, 0.7):
    rs = []
    for name, p in P.items():
        tps, ttft, nt, k = run(p, temp); rs.append(tps)
        print(f"WALL {tag} T={temp} {name}: {tps:.1f} t/s (tokens {nt}, chunks {k}, ttft {ttft*1000:.0f} ms)", flush=True)
    print(f"WALL {tag} T={temp} median {statistics.median(rs):.1f} t/s", flush=True)
