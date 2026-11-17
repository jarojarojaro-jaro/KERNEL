#!/usr/bin/env python3
"""Cold prefill through the running llama-server: unique filler documents (~4k and ~14k tokens), max_tokens 1,
prefill t/s = timings.prompt_n / timings.prompt_ms (server clock), 2 reps each. Rows -> /root/res/prefill.jsonl.
   pf.py <port>"""
import json, random, sys, time, urllib.request

port = int(sys.argv[1])
W = ("river stone paper cloud engine garden silver market winter orange signal harbor violet candle forest mirror "
     "thunder copper meadow lantern bridge window planet rocket silence morning").split()
out = open("/root/res/prefill.jsonl", "a")
for words in (3000, 10500):
    for rep in (1, 2):
        rng = random.Random(words * 10 + rep)
        doc = f"[doc {time.time_ns()}] " + " ".join(rng.choice(W) for _ in range(words))
        body = {"messages": [{"role": "user", "content": doc + "\n\nSummarise in one word."}], "max_tokens": 1,
                "temperature": 0, "cache_prompt": False}
        req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions", json.dumps(body).encode(),
                                     {"Content-Type": "application/json"})
        t0 = time.time()
        r = json.loads(urllib.request.urlopen(req, timeout=1800).read())
        t = r.get("timings", {})
        row = {"words": words, "rep": rep, "prompt_n": t.get("prompt_n"), "prompt_ms": t.get("prompt_ms"),
               "pp_tps": round(t["prompt_n"] / t["prompt_ms"] * 1000, 1) if t.get("prompt_ms") else None,
               "wall_s": round(time.time() - t0, 2)}
        out.write(json.dumps(row) + "\n"); out.flush(); print(row, flush=True)
