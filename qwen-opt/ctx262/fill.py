#!/usr/bin/env python3
"""Fill a running llama-server to N prompt tokens (corpus), then decode 256 tokens on top. Prints timings."""
import glob, json, os, sys, urllib.request
port, n = int(sys.argv[1]), int(sys.argv[2])
def post(path, body, t=1800):
    r = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=t))
files = sorted(glob.glob(os.path.expanduser("~/KERNEL/product/research/*.md"))) + sorted(glob.glob(os.path.expanduser("~/KERNEL/wiki/**/*.md"), recursive=True))
txt = "\n\n".join(open(f, encoding="utf-8", errors="ignore").read() for f in files)
toks = post("/tokenize", {"content": txt})["tokens"]
while len(toks) < n: toks += toks
prompt = toks[:n - 40] + post("/tokenize", {"content": "\n\nPodsumuj powyższy tekst w kilku zdaniach po polsku."})["tokens"]
d = post("/completion", {"prompt": prompt, "n_predict": 256, "temperature": 0, "cache_prompt": True})
t = d["timings"]
print(json.dumps({"n_ctx_target": n, "prompt_n": t["prompt_n"], "prompt_tps": round(t["prompt_per_second"], 1), "prompt_s": round(t["prompt_ms"] / 1000, 1),
                  "gen_n": t["predicted_n"], "decode_tps": round(t["predicted_per_second"], 1), "text": d["content"][:160]}, ensure_ascii=False))
