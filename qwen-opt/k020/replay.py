#!/usr/bin/env python3
"""K-020 3-thread replay under --cache-ram pressure: two long threads (A, B: --long tokens of distinct corpus text each)
and short unrelated requests (--short tokens, own system prompt each) interleaved:
    A1 B1 | s1..sN | A2 B2 | sN+1..s2N | A3 B3
A2/A3 (B2/B3) extend A1 (B1): with the entry still in --cache-ram only the new question is prefilled, after an eviction
the whole thread is (prompt_n >= 20k = a full re-prefill). T=0, 32 tokens per answer, prompt cache on.
Prints per request prompt_n / prompt_ms; summary: full re-prefills of the long threads, prefill seconds, wall.

usage: replay.py --port P --label L [--long 24000] [--short 3000] [--n-short 6] [--out F]
"""
import argparse, json, os, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CORPUS = os.path.expanduser("~/qwen-opt/xtxbench/corpus.txt")


def post(port, path, body):
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=900))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--long", type=int, default=24000)
    ap.add_argument("--short", type=int, default=3000)
    ap.add_argument("--n-short", type=int, default=6)
    ap.add_argument("--out", default=os.path.join(HERE, "replay.jsonl"))
    a = ap.parse_args()

    toks = post(a.port, "/tokenize", {"content": open(CORPUS).read()})["tokens"]
    need = 2 * a.long + 2 * a.n_short * a.short
    assert len(toks) >= need, f"corpus has {len(toks)} tokens, need {need}"
    cut, pos = [], 0
    for n in [a.long, a.long] + [a.short] * (2 * a.n_short):
        cut.append(post(a.port, "/detokenize", {"tokens": toks[pos:pos + n]})["content"])
        pos += n

    threads = {"A": [{"role": "system", "content": "You are reviewing document A for the user."},
                     {"role": "user", "content": cut[0] + "\n\nQuestion 1: what is the first section about? One sentence."}],
               "B": [{"role": "system", "content": "You are reviewing document B for the user."},
                     {"role": "user", "content": cut[1] + "\n\nQuestion 1: what is the first section about? One sentence."}]}
    rows = []
    t0 = time.time()

    def ask(name, messages):
        r = post(a.port, "/v1/chat/completions", {"messages": messages, "max_tokens": 32, "temperature": 0.0, "seed": 1,
                                                  "cache_prompt": True})
        t = r["timings"]
        rows.append({"req": name, "prompt_n": t.get("prompt_n", 0), "prompt_ms": round(t.get("prompt_ms", 0.0), 1),
                     "cache_n": t.get("cache_n", 0)})
        print(f"  {name:4s} prompt_n {rows[-1]['prompt_n']:6d} cache_n {rows[-1]['cache_n']:6d} "
              f"prefill {rows[-1]['prompt_ms'] / 1000:6.1f} s", flush=True)
        return r["choices"][0]["message"].get("content") or ""

    def turn(th, k):
        ans = ask(f"{th}{k}", threads[th])
        threads[th] += [{"role": "assistant", "content": ans},
                        {"role": "user", "content": f"Question {k + 1}: name one detail from the middle of the document."}]

    s = 0
    for k in (1, 2, 3):
        turn("A", k)
        turn("B", k)
        if k < 3:
            for _ in range(a.n_short):
                ask(f"s{s + 1}", [{"role": "system", "content": f"Short task {s + 1}: summarize briefly."},
                                  {"role": "user", "content": cut[2 + s] + "\n\nSummarize in one sentence."}])
                s += 1
    full = [r["req"] for r in rows if r["req"][0] in "AB" and r["req"][1] != "1" and r["prompt_n"] >= 20000]
    summ = {"label": a.label, "time": time.time(), "long": a.long, "short": a.short, "n_short": a.n_short,
            "full_reprefills": len(full), "which": full,
            "prefill_s": round(sum(r["prompt_ms"] for r in rows) / 1000, 1),
            "long_followup_prefill_s": round(sum(r["prompt_ms"] for r in rows if r["req"][0] in "AB" and r["req"][1] != "1") / 1000, 1),
            "wall_s": round(time.time() - t0, 1), "rows": rows}
    with open(a.out, "a") as f:
        f.write(json.dumps(summ) + "\n")
    print(f"{a.label}: long-thread full re-prefills {len(full)} {full}, prefill {summ['prefill_s']} s "
          f"(long follow-ups {summ['long_followup_prefill_s']} s), wall {summ['wall_s']} s", flush=True)


if __name__ == "__main__":
    main()
