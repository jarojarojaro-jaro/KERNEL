#!/usr/bin/env python3
"""K-005 LLAMA_CKPT_GRID A/B in the PRODUCTION config (xtxbench Server = run-topka.sh uncensored, duo build, test port).
One arm per queue job (each <= 10 min):  python3 k005_grid.py off|on   [env K005_TOKENS (40000), K005_PORT (18796),
K005_ROOT (~/wt/l1-cachesave/build-hip)]. Conversation (token lists, exact shared prefix):
  P1 = prefix + tail_a (K005_TOKENS), P2 = prefix + tail_b (the last 10 % edited), P3 = P2 + one appended turn.
off: P1, P2 (edit: resume time without the grid), P3 (append), cold P2 (cache_prompt=false, md5 reference).
on (LLAMA_CKPT_GRID=8192, 4096 MiB): P1, P2, P3, fork back to the end of P2 (kind fork).
Results: ~/qwen-opt/duo/k005-<arm>.json; the on arm compares md5 with k005-off.json. Queue only."""
import json, os, sys
sys.path.insert(0, os.path.expanduser("~/qwen-opt/xtxbench"))
import xtxbench as xb  # noqa: E402

ARM = sys.argv[1]
N = int(os.environ.get("K005_TOKENS", "40000"))
PORT = int(os.environ.get("K005_PORT", "18796"))
ROOT = os.path.expanduser(os.environ.get("K005_ROOT", "~/wt/l1-cachesave/build-hip"))
OUT = os.path.expanduser("~/qwen-opt/duo/k005-%s.json")
ENV = {"off": {"LLAMA_CKPT_GRID": "0"}, "on": {"LLAMA_CKPT_GRID": "8192", "LLAMA_CKPT_GRID_MIB": "4096"}}[ARM]
if not xb.under_queue():
    sys.exit("REFUSED: outside ~/qwen-opt/queue/run-jobs.sh")
run = xb.Run("duo-k005", ARM)
pid = xb.find_server_pid(8080)
if pid:
    xb.stop_pid(pid, run.log, ":8080")
srv = xb.Server(run, xb.Arm(f"grid-{ARM}", ROOT, ENV, [], {}), ARM, PORT)
srv.start()
res = {"arm": ARM, "tokens": N, "env": ENV}
try:
    def toks(fmt, a, b):
        return srv.tokenize("".join(fmt.format(i) for i in range(a, b)), False)
    unit_a = "Record {:05d}: alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu.\n"
    unit_b = "Edited {:05d}: omega psi chi phi upsilon tau sigma rho pi omicron xi nu.\n"
    per_line = len(toks(unit_a, 0, 100)) / 100
    lines = int(N / per_line)
    cut = int(lines * 0.9)
    q = srv.tokenize("\nSummarize the final record number and words concisely:", False)
    prefix = toks(unit_a, 0, cut)
    p1 = prefix + toks(unit_a, cut, lines) + q
    p2 = prefix + toks(unit_b, cut, lines) + q
    turn = srv.tokenize(" The final record is listed above.\n" + "Follow-up question: list three of the words again.\n" * 40, False)
    p3 = p2 + turn
    fork = p2 + srv.tokenize("\nAlternative branch from here. Answer:", False)
    res["len"] = {"p1": len(p1), "p2": len(p2), "prefix": len(prefix), "p3": len(p3)}
    run.log(f"P1 {len(p1)} P2 {len(p2)} shared prefix {len(prefix)} ({100 * len(prefix) / len(p2):.1f} %) P3 {len(p3)}")
    steps = [("p1", p1, True, 64), ("p2_edit10", p2, True, 64), ("p3_append", p3, True, 64)]
    steps += [("cold_p2", p2, False, 64)] if ARM == "off" else [("p2_fork", fork, True, 16)]
    for name, p, cache, n in steps:
        r = srv.complete(p, n, cache_prompt=cache)
        res[name] = r
        run.log(f"{name:10s} cache_n={r['cache_n']} prompt_n={r['prompt_n']} prompt_ms={r['prompt_ms']} "
                f"wall_s={r['wall_s']} md5={r['md5']}")
finally:
    srv.stop()
xb.save_json(OUT % ARM, res)
if ARM == "on" and os.path.exists(OUT % "off"):
    off = xb.load_json(OUT % "off", {})
    for k in ("p2_edit10", "p3_append"):
        a, b = off[k], res[k]
        run.log(f"{k}: resume prompt_ms off {a['prompt_ms']} -> on {b['prompt_ms']} ({100 * (b['prompt_ms'] / a['prompt_ms'] - 1):+.1f} %), "
                f"wall {a['wall_s']} -> {b['wall_s']} s, md5 off {a['md5']} on {b['md5']} equal={a['md5'] == b['md5']}")
    run.log(f"md5 grid p2_edit10 {res['p2_edit10']['md5']} vs cold {off['cold_p2']['md5']}: "
            f"equal={res['p2_edit10']['md5'] == off['cold_p2']['md5']}")
