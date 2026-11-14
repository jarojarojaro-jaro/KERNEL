#!/usr/bin/env python3
"""K-003: where do the ~210-230 ms of fixed per-request cost go? Production config on a test port with
LLAMA_SERVER_AP_TIMING=1; 40 distinct short chat requests (/v1/chat/completions, max_tokens 8, T=0) after one warm-up.
Per request: wall (client), prompt_ms / predicted_ms (server timings), and the AP_TIMING log lines in between.
Runs only inside the GPU queue (~/qwen-opt/queue/run-jobs.sh)."""
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


def chat(i):
    body = {"messages": [{"role": "user", "content": f"Zadanie {i}: ile to {17 + i} razy {23 + 2 * i}? Odpowiedz jedną liczbą."}],
            "max_tokens": 8, "temperature": 0, "seed": 1}
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}/v1/chat/completions", json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    t0 = time.perf_counter()
    r = json.load(urllib.request.urlopen(req, timeout=120))
    return (time.perf_counter() - t0) * 1000, r.get("timings", {}), r.get("usage", {})


def main():
    if not xb.under_queue():
        sys.exit("REFUSED: outside ~/qwen-opt/queue/run-jobs.sh")
    run = xb.Run("k003", "ttft")
    pid = xb.find_server_pid(8080)
    if pid:
        xb.stop_pid(pid, run.log, ":8080")
    srv = xb.Server(run, xb.Arm("prod-ap", xb.PROD, {"LLAMA_SERVER_AP_TIMING": "1"}, [], {}), "ap", PORT)
    rows = []
    try:
        srv.start()
        chat(-1)
        for i in range(N):
            w, t, u = chat(i)
            rows.append({"wall_ms": round(w, 1), "prompt_n": t.get("prompt_n"), "cache_n": t.get("cache_n"),
                         "prompt_ms": t.get("prompt_ms"), "predicted_n": t.get("predicted_n"),
                         "predicted_ms": t.get("predicted_ms")})
        m = lambda k: round(statistics.median(r[k] for r in rows if r[k] is not None), 1)
        other = statistics.median(r["wall_ms"] - r["prompt_ms"] - r["predicted_ms"] for r in rows)
        run.log(f"K-003 n={N}: wall {m('wall_ms')} ms, prompt_ms {m('prompt_ms')} (prompt_n {m('prompt_n')}, "
                f"cache_n {m('cache_n')}), predicted_ms {m('predicted_ms')} for {m('predicted_n')} tok, other {other:.1f} ms")
    finally:
        srv.stop()
        xb.save_json(os.path.join(run.dir, "k003.json"), rows)
        log = getattr(srv, "log_path", None)
        run.log(f"done, results {run.dir}/k003.json, server log {log}")


if __name__ == "__main__":
    main()
