#!/usr/bin/env python3
"""K-001 step 3: where do R1 (first restore) and R2 (restore after an unrelated chat) diverge, and by how much?
Fresh server (production config): restore the 1.7k snapshot, T=0 with n_probs=2 (R1); unrelated greedy chat; restore
again (R2). Prints the first token where the texts differ and the top-2 probabilities of both runs around it:
a tie-level gap (|p1-p2| ~ 1e-6..1e-4) = summation order / buffer reuse; a large one = uninitialized state.
Runs only inside the GPU queue."""
import json, os, sys, time
sys.path.insert(0, os.path.expanduser("~/qwen-opt/xtxbench"))
import xtxbench as xb  # noqa: E402

PORT, D, N, SNAP = 18794, 1700, 256, "k001c-d1700.bin"
ROOT = os.environ.get("K001_ROOT", xb.PROD)


def probs_run(srv, T):
    r = srv.call("/completion", {"prompt": T, "n_predict": N, "temperature": 0.0, "seed": 1, "cache_prompt": True,
                                 "stream": False, "n_probs": 2})
    out = []
    for p in r.get("completion_probabilities", []):
        tops = p.get("top_probs") or p.get("top_logprobs") or []
        out.append((p.get("token"), [(t.get("token"), t.get("prob", t.get("logprob"))) for t in tops[:2]]))
    return out


def main():
    if not xb.under_queue():
        sys.exit("REFUSED: outside ~/qwen-opt/queue/run-jobs.sh")
    run = xb.Run("k001c", os.environ.get("K001_LABEL", "probs"))
    pid = xb.find_server_pid(8080)
    if pid:
        xb.stop_pid(pid, run.log, ":8080")
    srv = None
    res = {}
    try:
        srv = xb.Server(run, xb.Arm("prod", ROOT, {}, [], {}), "s0", PORT)
        srv.start()
        P, T = xb.Prompts(srv, 40000).snap(D)
        srv.slot("erase"); srv.complete(P, 1, cache_prompt=True); srv.slot("save", SNAP)
        res["F"] = probs_run(srv, T); srv.stop()
        srv = xb.Server(run, xb.Arm("prod", ROOT, {}, [], {}), "v", PORT)
        srv.start()
        srv.slot("restore", SNAP); res["R1"] = probs_run(srv, T); srv.slot("erase")
        srv.slot("restore", SNAP); m1 = srv.complete(T, N, 0.0, 1, True)["md5"]; srv.slot("erase")
        srv.greedy_md5(); srv.slot("erase")
        srv.slot("restore", SNAP); res["R2"] = probs_run(srv, T); srv.slot("erase")
        srv.slot("restore", SNAP); m2 = srv.complete(T, N, 0.0, 1, True)["md5"]; srv.slot("erase")
        run.log(f"plain md5 (no n_probs): after R1 {m1}, after R2 {m2}")
        srv.stop(); srv = None
        for a, b in (("F", "R1"), ("R1", "R2")):
            A, B = res[a], res[b]
            i = next((k for k in range(min(len(A), len(B))) if A[k][0] != B[k][0]), None)
            if i is None:
                run.log(f"{a} vs {b}: identical tokens over {min(len(A), len(B))}"); continue
            run.log(f"{a} vs {b}: first different token at {i}: {A[i][0]!r} vs {B[i][0]!r}")
            for k in range(max(0, i - 2), min(i + 1, len(A), len(B))):
                run.log(f"  step {k}: {a} {A[k][1]}  |  {b} {B[k][1]}")
            # largest top-1 probability difference before the split (same token): numerics drift
            dd = max((abs(A[k][1][0][1] - B[k][1][0][1]) for k in range(i) if A[k][1] and B[k][1]), default=0.0)
            run.log(f"  max |d top1 logprob| before the split: {dd:.3g}")
        xb.save_json(os.path.join(run.dir, "k001c.json"), res)
    finally:
        if srv is not None:
            srv.stop()
        try: os.remove(os.path.join(xb.SLOTS, SNAP))
        except OSError: pass
        run.log(f"done in {time.time() - run.t0:.0f} s, results {run.dir}")


if __name__ == "__main__":
    main()
