#!/usr/bin/env python3
"""R69b Q1: identical OpenAI chat requests to a running server (llama-server fork or qwen-warp serve.py), streamed.

Decode t/s = generated tokens after the first streamed chunk / (last chunk - first chunk) wall time on the client.
Tokens in the first chunk: usage.completion_tokens of that chunk (vLLM continuous_usage_stats), else 1 (llama-server
streams one chunk per token). Prefill = prompt_tokens / TTFT on a cold prompt.
   bench.py <engine-label> <port> <model-name> <block...>
   blocks: short | depth:<tokens> | prefill:<tokens>
Rows -> /root/res/bench.jsonl. Docs are built from /root/nv/corpus.txt with the fork's /tokenize (first run) and cached
in /root/res/docs/ so both engines get byte-identical prompts."""
import hashlib
import http.client
import json
import os
import statistics
import sys
import time
import urllib.request

PROMPTS = {
    "pl-proza": "Napisz opowiadanie (około 800 słów) o starym latarniku, który pewnej sztormowej nocy dostaje sygnał z okrętu, który zatonął 50 lat temu. Opisz dokładnie miejsce, pogodę, jego wspomnienia i zakończ zaskakującym zwrotem akcji.",
    "pl-tech": "Wyjaśnij krok po kroku, jak działa protokół TCP: nawiązywanie połączenia, numery sekwencyjne, okno przesuwne, kontrola przeciążenia i zamykanie połączenia. Do każdego etapu podaj przykład z liczbami.",
    "pl-kod": "Napisz w Pythonie klasę LRUCache z metodami get i put (O(1)), z type hintami, docstringami i testami w pytest.",
    "en-chat": "Hey! How are you doing today? Tell me a bit about what you like to talk about.",
    "en-tech": "Explain how a B-tree index works in a relational database: node layout, search, insertion with splits, deletion with merges, and why it suits disks. Use a concrete example with numbers.",
    "en-code": "Write a complete Python module implementing a thread-safe LRU cache with TTL expiry: type hints, docstrings, and a full pytest test suite. Write all the code, no placeholders.",
}
TOK = int(os.environ.get("TOK", "400"))
TEMPS = [float(t) for t in os.environ.get("TEMPS", "0,1").split(",")]
RES = os.environ.get("RES", "/root/res")
DOCS = f"{RES}/docs"
FORK_TOKENIZE_PORT = int(os.environ.get("TOKENIZE_PORT", "0"))

label, port, model = sys.argv[1], int(sys.argv[2]), sys.argv[3]
blocks = sys.argv[4:]
os.makedirs(DOCS, exist_ok=True)
out = open(f"{RES}/bench.jsonl", "a")


def vram() -> int:
    o = os.popen("nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits").read()
    return int(float(o.split()[0])) if o.split() else -1


def stream(messages: list, temp: float, max_tokens: int = TOK) -> dict:
    body = {"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": temp, "top_p": 0.95,
            "top_k": 20, "min_p": 0.0, "seed": 1, "stream": True,
            "stream_options": {"include_usage": True, "continuous_usage_stats": True}}
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=3600)
    t0 = time.time()
    c.request("POST", "/v1/chat/completions", json.dumps(body), {"Content-Type": "application/json"})
    r = c.getresponse()
    if r.status != 200:
        return {"error": f"HTTP {r.status}: {r.read()[:400]!r}"}
    t_first = t_last = None
    n_first = None
    n_chunks = 0
    usage, timings = {}, {}
    text = []
    buf = b""
    while True:
        line = r.readline()
        if not line:
            break
        line = line.strip()
        if not line.startswith(b"data:"):
            continue
        payload = line[5:].strip()
        if payload == b"[DONE]":
            break
        now = time.time()
        d = json.loads(payload)
        if d.get("usage"):
            usage = d["usage"]
        if d.get("timings"):
            timings = d["timings"]
        for ch in d.get("choices") or []:
            dl = ch.get("delta") or {}
            piece = (dl.get("content") or "") + (dl.get("reasoning") or "") + (dl.get("reasoning_content") or "")
            if piece:
                text.append(piece)
                n_chunks += 1
                if t_first is None:
                    t_first = now
                    n_first = (d.get("usage") or {}).get("completion_tokens")
                t_last = now
    c.close()
    n = usage.get("completion_tokens") or timings.get("predicted_n") or n_chunks
    if n_first is None:
        n_first = 1
    gen_s = (t_last - t_first) if t_first and t_last else 0
    txt = "".join(text)
    row = {"n": n, "n_first": n_first, "chunks": n_chunks, "ttft_s": round(t_first - t0, 3) if t_first else None,
           "gen_s": round(gen_s, 3), "tps": round((n - n_first) / gen_s, 2) if gen_s > 0 else None,
           "prompt_tokens": usage.get("prompt_tokens") or timings.get("prompt_n"),
           "cached": ((usage.get("prompt_tokens_details") or {}).get("cached_tokens") if usage.get("prompt_tokens_details")
                      else timings.get("cache_n")),
           "md5": hashlib.md5(txt.encode()).hexdigest()[:8], "head": txt[:80]}
    if timings:
        row["srv_tps"] = round(timings.get("predicted_per_second", 0), 2)
        row["draft"], row["acc"] = timings.get("draft_n"), timings.get("draft_n_accepted")
        row["prompt_ms"] = timings.get("prompt_ms")
    return row


def tokenize(text: str) -> int:
    req = urllib.request.Request(f"http://127.0.0.1:{FORK_TOKENIZE_PORT}/tokenize", json.dumps({"content": text}).encode(),
                                 {"Content-Type": "application/json"})
    return len(json.load(urllib.request.urlopen(req, timeout=600))["tokens"])


def doc(ntok: int, tag: str = "") -> str:
    """corpus repeated with numbered parts, cut to ~ntok tokens (by the fork tokenizer; same vocabulary as Swift)."""
    path = f"{DOCS}/doc-{ntok}{tag}.txt"
    if os.path.exists(path):
        return open(path).read()
    assert FORK_TOKENIZE_PORT, "doc not cached and no tokenizer port"
    corpus = open(os.environ.get("CORPUS", "/root/nv/corpus.txt")).read()
    parts, i = [], 0
    while sum(len(p) for p in parts) < ntok * 5:
        parts.append(f"\n\n## Część {i + 1}\n\n" + corpus)
        i += 1
    full = (f"[{tag}]\n" if tag else "") + "Materiał referencyjny:\n" + "".join(parts)
    sample = full[:200000]
    est = int(ntok * len(sample) / tokenize(sample))
    lo, hi = int(est * 0.85), min(len(full), int(est * 1.15))
    for _ in range(16):  # bisection on character length
        mid = (lo + hi) // 2
        if tokenize(full[:mid]) <= ntok:
            lo = mid
        else:
            hi = mid
    text = full[:lo]
    open(path, "w").write(text)
    return text


def emit(row: dict) -> None:
    row.update({"engine": label, "time": round(time.time(), 1), "vram": vram()})
    out.write(json.dumps(row, ensure_ascii=False) + "\n")
    out.flush()
    print(json.dumps({k: row.get(k) for k in ("engine", "block", "prompt", "temp", "tps", "n", "ttft_s", "prompt_tokens",
                                             "cached", "srv_tps", "md5", "error")}, ensure_ascii=False), flush=True)


def decode_block(block: str, system: str | None) -> None:
    if system is None:  # warmup; never between a primed long prefix and its prompts (it would evict the prefix)
        stream([{"role": "user", "content": "Hi"}], 0.0, 16)
    for temp in TEMPS:
        tps = []
        for name, p in PROMPTS.items():
            msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": p}]
            r = stream(msgs, temp)
            r.update({"block": block, "prompt": name, "temp": temp})
            emit(r)
            if r.get("tps"):
                tps.append(r["tps"])
        emit({"block": block, "prompt": "MEDIAN", "temp": temp, "tps": statistics.median(tps) if tps else None,
              "n_ok": len(tps)})


for b in blocks:
    if b == "short":
        decode_block("short", None)
    elif b.startswith("depth:"):
        n = int(b.split(":")[1])
        d = doc(n)
        # prime: prefill the shared system prefix once (its cost is not part of decode), then the 6 prompts x temps
        r = stream([{"role": "system", "content": d}, {"role": "user", "content": "OK?"}], 0.0, 8)
        r.update({"block": b, "prompt": "PRIME", "temp": 0.0})
        emit(r)
        decode_block(b, d)
    elif b.startswith("prefill:"):
        n = int(b.split(":")[1])
        for rep in (1, 2):
            d = doc(n, f"cold{rep}")
            r = stream([{"role": "system", "content": d}, {"role": "user", "content": "Streść krótko."}], 0.0, 2)
            r.update({"block": b, "prompt": f"cold{rep}", "temp": 0.0,
                      "prefill_tps": round(r["prompt_tokens"] / r["ttft_s"], 1) if r.get("ttft_s") else None})
            emit(r)
