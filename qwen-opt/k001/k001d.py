#!/usr/bin/env python3
"""K-001 step 4: first-token top-2 logprobs after a slot restore, before / after a perturbation, per perturbation kind
and delta length. Every case on a fresh server: restore -> probs (R1); perturbation; restore -> probs (R2).
A case 'leaks' when R2 != R1. Runs only inside the GPU queue."""
import os, sys, time
sys.path.insert(0, os.path.expanduser("~/qwen-opt/xtxbench"))
import xtxbench as xb  # noqa: E402

PORT, D, SNAP = 18794, 1700, "k001d-d1700.bin"
ROOT = os.environ.get("K001_ROOT", xb.PROD)


def first(srv, T):
    r = srv.call("/completion", {"prompt": T, "n_predict": 1, "temperature": 0.0, "seed": 1, "cache_prompt": True,
                                 "stream": False, "n_probs": 2})
    p = r["completion_probabilities"][0]
    lp = lambda t: t.get("logprob", t.get("prob"))
    return [(t["token"], round(lp(t), 6) if lp(t) is not None else "NaN") for t in (p.get("top_logprobs") or p.get("top_probs"))[:2]]


def main():
    if not xb.under_queue():
        sys.exit("REFUSED: outside ~/qwen-opt/queue/run-jobs.sh")
    run = xb.Run("k001d", os.environ.get("K001_LABEL", "bisect"))
    pid = xb.find_server_pid(8080)
    if pid:
        xb.stop_pid(pid, run.log, ":8080")
    srv = None
    try:
        srv = xb.Server(run, xb.Arm("prod", ROOT, {}, [], {}), "s0", PORT)
        srv.start()
        pr = xb.Prompts(srv, 40000)
        P, T = pr.snap(D)
        U = pr.total(600)[-300:]   # an unrelated 300-token prompt
        srv.slot("erase"); srv.complete(P, 1, cache_prompt=True); srv.slot("save", SNAP)   # prod snapshot (all arms restore it)
        deltas = {f"post{n}": T[:len(P) + n] for n in (1, 31, 32, 33)}
        deltas.update({f"u{n}": P + U[:n] for n in (48, 63, 64)})
        if os.environ.get("K001_DELTAS"):   # e.g. post33,post32
            deltas = {k: v for k, v in deltas.items() if k in os.environ["K001_DELTAS"].split(",")}
        srv.stop()
        envs = [("prod", {})] + [(v, dict(kv.split("=", 1) for kv in v.split(","))) for v in sys.argv[1:]]
        fn = lambda s: None   # restore twice, nothing in between (enough to show the leak, 2026-11-20)
        for pn, env in envs:
            xargs = os.environ["K001_ARGS"].split(",") if os.environ.get("K001_ARGS") else []   # e.g. -c,32768
            srv = xb.Server(run, xb.Arm(pn, ROOT, env, xargs, {}), f"v-{pn.replace('=', '').replace(',', '_')}", PORT)
            srv.start()
            if os.environ.get("K001_OWN_SNAP"):   # configs whose state format differs: own snapshot from this server
                srv.slot("erase"); srv.complete(P, 1, cache_prompt=True); srv.slot("save", SNAP); srv.slot("erase")
            for dn, TT in deltas.items():
                srv.slot("restore", SNAP); r1 = first(srv, TT); srv.slot("erase")
                fn(srv); srv.slot("erase")
                srv.slot("restore", SNAP); r2 = first(srv, TT); srv.slot("erase")
                run.log(f"{pn:12s} {dn:8s} R1 {r1}  R2 {r2}  {'LEAK' if r1 != r2 else 'same'}")
            srv.stop(); srv = None
    finally:
        if srv is not None:
            srv.stop()
        try: os.remove(os.path.join(xb.SLOTS, SNAP))
        except OSError: pass
        run.log(f"done in {time.time() - run.t0:.0f} s")


if __name__ == "__main__":
    main()
