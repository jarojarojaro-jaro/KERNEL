#!/usr/bin/env python3
"""K-118 long arm: one cold ~128k-token filler prompt through the running llama-server, then 256 tokens at T=0.
Rows -> /root/res/long.jsonl (prompt_n, prefill t/s, decode t/s from the server timings, draft stats).
   lp.py <port> <label>"""
import json, random, sys, time, urllib.request

port, label = int(sys.argv[1]), sys.argv[2]
W = ("river stone paper cloud engine garden silver market winter orange signal harbor violet candle forest mirror "
     "thunder copper meadow lantern bridge window planet rocket silence morning").split()
rng = random.Random(128)
doc = " ".join(rng.choice(W) for _ in range(92000))   # ~1.33 tokens/word in K-114's pf.py -> ~122k tokens (ctx 139264)
body = {"messages": [{"role": "user", "content": doc + "\n\nWrite a 200-word story that uses the ten most frequent words above."}],
        "max_tokens": 256, "temperature": 0, "cache_prompt": False}
req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions", json.dumps(body).encode(),
                             {"Content-Type": "application/json"})
t0 = time.time()
r = json.loads(urllib.request.urlopen(req, timeout=1800).read())
t = r.get("timings", {})
row = {"label": label, "prompt_n": t.get("prompt_n"), "prompt_ms": t.get("prompt_ms"),
       "pp_tps": round(t["prompt_n"] / t["prompt_ms"] * 1000, 1) if t.get("prompt_ms") else None,
       "predicted_n": t.get("predicted_n"), "tg_tps": t.get("predicted_per_second"),
       "draft_n": t.get("draft_n"), "draft_n_accepted": t.get("draft_n_accepted"), "wall_s": round(time.time() - t0, 1)}
open("/root/res/long.jsonl", "a").write(json.dumps(row) + "\n")
print(row, flush=True)
