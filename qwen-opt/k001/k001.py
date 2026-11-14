#!/usr/bin/env python3
"""K-001: second slot restore on the same server vs a fresh prefill (state leak), production config on a test port.

Server S0 (production config): prefill P (1.7k), save the slot, decode P+post (= fresh prefill md5 F).
Then for every config (prod first, then bisection variants given as NAME=VAL[,NAME=VAL] arguments) on a FRESH server:
  R1  restore -> P+post T=0 256 tok md5          (first restore, trusted)
  R1b restore again                              (leak from the decode itself?)
  U1  unrelated short chat (greedy, 256 tok)
  R2  restore                                    (leak from a short unrelated request?)
  U2  cold 32k prefill (cache_prompt=false, n_predict=1)
  R3  restore                                    (leak from a long request: KV cells / n_kv?)
  F2  erase, fresh prefill P + P+post            (fresh prefill on a used server)
Runs only inside the GPU queue. Usage: k001.py [VAR ...]   e.g. k001.py LLAMA_SPEC_LOOKUP=0 GGML_HIP_PM4=0
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.expanduser("~/qwen-opt/xtxbench"))
import xtxbench as xb  # noqa: E402

PORT = 18794
D = 1700
N = 256
SNAP = "k001-d1700.bin"


def main():
    if not xb.under_queue():
        sys.exit("REFUSED: outside ~/qwen-opt/queue/run-jobs.sh")
    run = xb.Run("k001", os.environ.get("K001_LABEL", "aa"))
    out = {"variants": {}}
    pid = xb.find_server_pid(8080)
    if pid:
        run.log(f":8080 pid {pid}: ONE SIGTERM")
        xb.stop_pid(pid, run.log, ":8080")
    variants = [("prod", {})] + [(v, dict(kv.split("=", 1) for kv in v.split(","))) for v in sys.argv[1:]]
    srv = None
    try:
        srv = xb.Server(run, xb.Arm("prod", xb.PROD, {}, [], {}), "s0", PORT)
        srv.start()
        prompts = xb.Prompts(srv, 40000)
        P, T = prompts.snap(D)
        srv.slot("erase")
        r = srv.complete(P, 1, cache_prompt=True)
        s = srv.slot("save", SNAP)
        f = srv.complete(T, N, 0.0, 1, True)
        run.log(f"S0: prefill {r['prompt_n']} tok, saved {s['n_written'] / 2**20:.0f} MiB; fresh F md5 {f['md5']} "
                f"prompt_n {f['prompt_n']} {f['decode_tps']} t/s")
        out["F"] = f
        srv.stop()
        for name, env in variants:
            tag = name.replace('=', '').replace(',', '_')
            rec = {}
            if env:  # another config cannot restore prod's slot file: own snapshot + own fresh reference first
                srv = xb.Server(run, xb.Arm(name, xb.PROD, env, [], {}), f"s0-{tag}", PORT)
                srv.start()
                srv.slot("erase")
                srv.complete(P, 1, cache_prompt=True)
                srv.slot("save", SNAP)
                fv = srv.complete(T, N, 0.0, 1, True)
                rec["F"] = fv
                run.log(f"[{name}] own snapshot; fresh F md5 {fv['md5']} {fv['decode_tps']} t/s "
                        f"draft {fv['draft_n']}/{fv['accepted']}")
                srv.stop()
            srv = xb.Server(run, xb.Arm(name, xb.PROD, env, [], {}), f"v-{tag}", PORT)
            srv.start()

            def restore(tag):
                rr = srv.slot("restore", SNAP)
                c = srv.complete(T, N, 0.0, 1, True)
                c["restore_ms"] = round(rr["timings"]["restore_ms"], 1)
                rec[tag] = c
                run.log(f"[{name}] {tag}: md5 {c['md5']} prompt_n {c['prompt_n']} {c['decode_tps']} t/s "
                        f"draft {c['draft_n']}/{c['accepted']}")
                srv.slot("erase")

            restore("R1")
            restore("R1b")
            g = srv.greedy_md5()
            rec["U1_greedy"] = g
            run.log(f"[{name}] U1 greedy chat md5 {g[0]} / {g[1]}")
            srv.slot("erase")
            restore("R2")
            u2 = srv.complete(prompts.total(32768), 1, cache_prompt=False)
            run.log(f"[{name}] U2 cold 32k prefill {u2['prompt_n']} tok {u2['prefill_tps']} t/s")
            srv.slot("erase")
            restore("R3")
            srv.complete(P, 1, cache_prompt=True)
            c = srv.complete(T, N, 0.0, 1, True)
            rec["F2"] = c
            run.log(f"[{name}] F2 fresh prefill on used server: md5 {c['md5']} prompt_n {c['prompt_n']}")
            srv.slot("erase")
            srv.stop()
            srv = None
            out["variants"][name] = rec
            md = {k: v["md5"] for k, v in rec.items() if isinstance(v, dict)}
            run.log(f"[{name}] SUMMARY F={f['md5']} " + " ".join(f"{k}={v}" for k, v in md.items()))
            xb.save_json(os.path.join(run.dir, "k001.json"), out)
            if False:  # always run every variant (K-001 bisection, 2026-11-14)
                run.log("prod: no leak reproduced, bisection variants skipped")
                break
    finally:
        if srv is not None:
            srv.stop()
        xb.save_json(os.path.join(run.dir, "k001.json"), out)
        try:
            os.remove(os.path.join(xb.SLOTS, SNAP))
        except OSError:
            pass
        run.log(f"done in {time.time() - run.t0:.0f} s, results {run.dir}/k001.json")


if __name__ == "__main__":
    main()
