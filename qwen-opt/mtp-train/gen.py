"""Generate the target's own responses (exact token ids) via a running llama-server.

Uses the server's default sampler (GGUF: T=1, top-k 20, top-p 0.95) and chat template / thinking setting,
i.e. what the user's traffic sees. Appends {id, lang, cat, prompt_ids, resp_ids} to the output jsonl and
skips prompts already present, so it can be run in time-boxed blocks (--deadline seconds).
"""
import argparse
import json
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed


def post(port, path, body, timeout=1800):
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def run_one(port, p, n_predict, seed):
    tmpl = post(port, "/apply-template", {"messages": [{"role": "user", "content": p["prompt"]}]})["prompt"]
    ids = post(port, "/tokenize", {"content": tmpl, "add_special": True, "parse_special": True})["tokens"]
    r = post(port, "/completion", {"prompt": ids, "n_predict": n_predict, "seed": seed,
                                   "return_tokens": True, "cache_prompt": False})
    return {"id": p["id"], "lang": p["lang"], "cat": p["cat"], "seed": seed, "prompt_ids": ids,
            "resp_ids": r["tokens"], "stop_type": r.get("stop_type"),
            "tps": r["timings"]["predicted_per_second"], "text": r["content"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompts", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--port", type=int, default=8099)
    ap.add_argument("--np", type=int, default=4)
    ap.add_argument("--n-predict", type=int, default=1400)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--deadline", type=float, default=480)
    a = ap.parse_args()

    prompts = [json.loads(l) for l in open(a.prompts)]
    done = set()
    try:
        done = {json.loads(l)["id"] for l in open(a.out)}
    except FileNotFoundError:
        pass
    todo = [p for p in prompts if p["id"] not in done]
    t0 = time.time()
    it = iter(todo)
    n_tok = 0
    with ThreadPoolExecutor(a.np) as ex, open(a.out, "a") as fo:
        running = {}
        for _ in range(a.np):
            p = next(it, None)
            if p:
                running[ex.submit(run_one, a.port, p, a.n_predict, a.seed)] = p
        while running:
            fut = next(as_completed(running))
            running.pop(fut)
            rec = fut.result()
            fo.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fo.flush()
            n_tok += len(rec["resp_ids"])
            print(f"{rec['id']}: {len(rec['resp_ids'])} tok, {rec['tps']:.1f} t/s, agg {n_tok / (time.time() - t0):.1f} t/s",
                  flush=True)
            if time.time() - t0 < a.deadline:
                p = next(it, None)
                if p:
                    running[ex.submit(run_one, a.port, p, a.n_predict, a.seed)] = p
    print(f"done {len(done) + 0} prev; generated {n_tok} tokens in {time.time() - t0:.0f}s; "
          f"remaining {len(todo) - sum(1 for _ in open(a.out)) + len(done)}")


if __name__ == "__main__":
    main()
