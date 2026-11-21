#!/usr/bin/env python3
"""K-053: the 12 NInfer scenario fixtures (code/story/translation/structured x3, ~/src/research63/ninfer
examples/cli/manifest.json; the set YASAKANI measured) on a running llama-server: as YASAKANI, greedy (T=0), thinking
off, max_new of the fixture (4096), no prompt cache. Per fixture one JSON line: tokens, finish, decode t/s of the server,
YASAKANI t/s = (tokens - 1) / generation time, prefill, draft acceptance, md5.
usage: k053.py --port P --out F.jsonl NAME|all ..."""
import argparse, hashlib, json, os, time, urllib.request

NI = os.path.expanduser("~/src/research63/ninfer/examples/cli")


def post(port, body):
    r = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions", data=json.dumps(body).encode(),
                               headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=900))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("names", nargs="+")
    a = ap.parse_args()
    cases = {c["name"]: c for c in json.load(open(f"{NI}/manifest.json"))["cases"] if c["name"].startswith("scenario_")}
    names = sorted(cases) if a.names == ["all"] else a.names
    for name in names:
        c = cases[name]
        msgs = json.load(open(os.path.join(NI, c["messages"])))
        t0 = time.time()
        r = post(a.port, {"messages": msgs, "max_tokens": c["max_new"], "temperature": 0, "seed": 1,
                          "cache_prompt": False, "chat_template_kwargs": {"enable_thinking": bool(c["thinking"])}})
        t = r["timings"]
        text = r["choices"][0]["message"]["content"] or ""
        n = t["predicted_n"]
        res = {"name": name, "prompt_n": t["prompt_n"], "tokens": n, "finish": r["choices"][0]["finish_reason"],
               "decode_tps": round(t["predicted_per_second"], 1),
               "yasakani_tps": round((n - 1) / (t["predicted_ms"] / 1000), 1),
               "prefill_tps": round(t["prompt_per_second"], 1), "wall_s": round(time.time() - t0, 1),
               "draft_n": t.get("draft_n"), "draft_acc": t.get("draft_n_accepted"),
               "md5": hashlib.md5(text.encode()).hexdigest()[:8]}
        print(json.dumps(res), flush=True)
        with open(a.out, "a") as f:
            f.write(json.dumps(res) + "\n")


if __name__ == "__main__":
    main()
