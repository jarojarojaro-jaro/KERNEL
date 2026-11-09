#!/usr/bin/env python3
"""ctx262/fill.py with a frozen corpus (fa-d256/corpus.txt, wiki + research as of 2026-11-07 23:5x), so both arms get
the same prompt: fill a running llama-server to N prompt tokens, decode 256 on top (T=0). Prints timings + text md5."""
import hashlib, json, os, sys, urllib.request
port, n = int(sys.argv[1]), int(sys.argv[2])
def post(path, body, t=3600):
    r = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=t))
txt = open(os.path.expanduser("~/qwen-opt/fa-d256/corpus.txt"), encoding="utf-8").read()
toks = post("/tokenize", {"content": txt})["tokens"]
while len(toks) < n: toks += toks
prompt = toks[:n - 40] + post("/tokenize", {"content": "\n\nPodsumuj powyższy tekst w kilku zdaniach po polsku."})["tokens"]
d = post("/completion", {"prompt": prompt, "n_predict": 256, "temperature": 0, "cache_prompt": True})
t = d["timings"]
print(json.dumps({"n_ctx_target": n, "prompt_n": t["prompt_n"], "prompt_tps": round(t["prompt_per_second"], 1), "prompt_s": round(t["prompt_ms"] / 1000, 1),
                  "gen_n": t["predicted_n"], "decode_tps": round(t["predicted_per_second"], 1),
                  "text_md5": hashlib.md5(d["content"].encode()).hexdigest()[:8], "text": d["content"][:160]}, ensure_ascii=False))
