#!/usr/bin/env python3
"""K-104 A/B: LLAMA_SERVER_SHORT_TAIL (short prompt tail in one batch). Fresh server per arm, production config on a test
port; per arm: 40 short chat turns (as K-003, greedy, 32 tok, response md5 each), 2 greedy chat md5s and a 1.7k fresh
prefill + 256-token T=0 decode md5. Arms: P = production ~/llama-topka, C = new build flag off, V = new build flag 32.
Runs only inside the GPU queue."""
import hashlib
import json
import os
import statistics
import sys
import time
import urllib.request

sys.path.insert(0, os.path.expanduser("~/qwen-opt/xtxbench"))
import xtxbench as xb  # noqa: E402

PORT = 18794
N = 40
BUILD = os.path.expanduser("~/wt/l1-cachesave/build-hip")


def chat(i):
    body = {"messages": [{"role": "user", "content": f"Zadanie {i}: ile to {17 + i} razy {23 + 2 * i}? Odpowiedz jedną liczbą."}],
            "max_tokens": 32, "temperature": 0, "seed": 1}
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}/v1/chat/completions", json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    t0 = time.perf_counter()
    r = json.load(urllib.request.urlopen(req, timeout=120))
    m = r["choices"][0]["message"]
    txt = (m.get("reasoning_content") or "") + "|" + (m.get("content") or "")
    return (time.perf_counter() - t0) * 1000, r.get("timings", {}), hashlib.md5(txt.encode()).hexdigest()[:8]


def main():
    if not xb.under_queue():
        sys.exit("REFUSED: outside ~/qwen-opt/queue/run-jobs.sh")
    run = xb.Run("k104", "short-tail")
    pid = xb.find_server_pid(8080)
    if pid:
        xb.stop_pid(pid, run.log, ":8080")
    arms = [("P", xb.PROD, {}), ("C", BUILD, {"LLAMA_SERVER_SHORT_TAIL": "0"}), ("V", BUILD, {"LLAMA_SERVER_SHORT_TAIL": "32"}),
            ("P2", xb.PROD, {})]
    out = {}
    for name, root, env in arms:
        srv = xb.Server(run, xb.Arm(name, root, env, [], {}), f"a-{name}", PORT)
        try:
            srv.start()
            chat(-1)
            rows = []
            for i in range(N):
                w, t, h = chat(i)
                rows.append({"wall_ms": round(w, 1), "prompt_ms": t.get("prompt_ms"), "prompt_n": t.get("prompt_n"),
                             "predicted_ms": t.get("predicted_ms"), "predicted_n": t.get("predicted_n"), "md5": h})
            g = srv.greedy_md5()
            prompts = xb.Prompts(srv, 40000)
            P, T = prompts.snap(1700)
            srv.slot("erase")
            srv.complete(P, 1, cache_prompt=True)
            f = srv.complete(T, 256, 0.0, 1, True)
            med = lambda k: round(statistics.median(r[k] for r in rows), 1)
            mean = lambda k: round(statistics.mean(r[k] for r in rows), 1)
            seq = hashlib.md5("".join(r["md5"] for r in rows).encode()).hexdigest()[:8]
            out[name] = {"rows": rows, "greedy": g, "long_md5": f["md5"], "long_tps": f["decode_tps"], "seq_md5": seq}
            run.log(f"[{name}] wall med {med('wall_ms')} mean {mean('wall_ms')} | prompt_ms med {med('prompt_ms')} mean "
                    f"{mean('prompt_ms')} | pred med {med('predicted_ms')} | 40-turn md5 {seq} | greedy {g[0]}/{g[1]} | "
                    f"1.7k md5 {f['md5']} {f['decode_tps']} t/s")
        finally:
            srv.stop()
            xb.save_json(os.path.join(run.dir, "k104.json"), out)
    run.log(f"done, results {run.dir}/k104.json")


if __name__ == "__main__":
    main()
