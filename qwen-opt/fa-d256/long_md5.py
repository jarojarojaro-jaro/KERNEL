#!/usr/bin/env python3
"""Greedy text md5 of one fresh 32768-token prompt on a running llama-server (q63: does the FA occupancy cap move the
prefill numerics at depth?). Prompt: the first 32768 tokens of ~/KERNEL/product/research/*.md + a summary request,
T=0, 256 tokens, thinking off, no prompt cache. Appends one line to --out.

usage: long_md5.py --port P --label L --out long_md5.txt [--tokens 32768]
"""
import argparse, glob, hashlib, json, os, urllib.request


def post(port, path, body):
    r = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=json.dumps(body).encode(),
                               headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=1800))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--tokens", type=int, default=32768)
    a = ap.parse_args()
    files = sorted(glob.glob(os.path.expanduser("~/KERNEL/product/research/*.md")))
    text = "\n\n".join(open(f, encoding="utf-8", errors="ignore").read() for f in files)
    toks = post(a.port, "/tokenize", {"content": text})["tokens"][:a.tokens]
    doc = post(a.port, "/detokenize", {"tokens": toks})["content"]
    r = post(a.port, "/v1/chat/completions", {
        "messages": [{"role": "user", "content": doc + "\n\nSummarize the documents above."}],
        "max_tokens": 256, "temperature": 0, "cache_prompt": False, "chat_template_kwargs": {"enable_thinking": False}})
    m = r["choices"][0]["message"]
    s = (m.get("reasoning_content") or "") + (m.get("content") or "")
    t = r["timings"]
    line = (f"{a.label} long{a.tokens} md5 {hashlib.md5(s.encode()).hexdigest()[:8]} prompt_n {t['prompt_n']} "
            f"gen {t['predicted_n']} prefill {t['prompt_per_second']:.1f} t/s")
    print(line, flush=True)
    with open(a.out, "a") as f:
        f.write(line + "\n")


if __name__ == "__main__":
    main()
