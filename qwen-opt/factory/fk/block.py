"""`factory.py _block SPEC.json`: one GPU block, run by the verifier inside `flock gpu.lock flock quiet.lock timeout`.

Kinds: serve (measurement run), greedy (fusion/greedy.sh copy), neartie, probe, bench (llama-bench), ops
(test-backend-ops), kld (llama-perplexity --kl-divergence). Before the work: refuse on the production server (exit
97) or a blocking preflight rule (exit 98); writes the result JSON to spec["out"] in every case.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

from . import hashing, hwgates, measure, paths, preflight

LOAD_RETRIES, LOAD_WAIT_S = 2, 20
H1_WAIT_S = 45


def _preflight(spec):
    import rules
    for attempt in range(LOAD_RETRIES + 1):
        snap = preflight.snapshot(spec.get("port"))
        found = rules.blocking(rules.run("preflight", {"snapshot": snap}))
        only_load = found and all(f.rule == "R15" for f in found)
        if not found or not only_load or attempt == LOAD_RETRIES:
            return snap, found
        time.sleep(LOAD_WAIT_S)
    return snap, found


def _run(argv, env, log, deadline, info=None):
    """Run to completion inside the block deadline; info gets the pid (a fresh process per run, rule R17)."""
    with open(log, "w") as lf:
        p = subprocess.Popen([*paths.HOST_PIN, *argv], env=env, stdout=lf, stderr=subprocess.STDOUT)
        if info is not None:
            info["pid"] = p.pid
        try:
            rc = p.wait(timeout=max(5, deadline - time.time()))
        except subprocess.TimeoutExpired:
            p.kill()
            p.wait()
            raise
    return rc, Path(log).read_text(errors="replace")


def do_greedy(spec):
    script = Path(spec["script"])
    if hashing.sha256_file(script, use_cache=False) != spec["script_sha256"]:
        raise RuntimeError(f"{script}: harness copy changed before the run")
    env = measure.block_env(spec)
    rc, out = _run(["bash", str(script), spec["bin_dir"], spec["lib_dir"], spec["out_prefix"], spec["model"]],
                   env, spec["log"], spec["deadline"])
    md5 = {}
    for mode in spec["modes"]:
        f = Path(f"{spec['out_prefix']}.{mode}.txt")
        if f.exists():
            md5[mode] = hashlib.md5(f.read_bytes()).hexdigest()
    logs = "".join(Path(f"{spec['out_prefix']}.{m}.log").read_text(errors="replace")[-3000:]
                   for m in spec["modes"] if Path(f"{spec['out_prefix']}.{m}.log").exists())
    return {"rc": rc, "md5": md5, "stdout_tail": out[-2000:], "log_tail": logs[-4000:]}


def do_bench(spec):
    info = {}
    rc, out = _run(spec["argv"], measure.block_env(spec), spec["log"], spec["deadline"], info)
    rows = [json.loads(l) for l in out.splitlines() if l.startswith("{")]
    if rc != 0 or not rows:
        raise RuntimeError(f"llama-bench rc {rc}: {out[-500:]}")
    row = rows[-1]
    return {"avg_ts": row["avg_ts"], "stddev_ts": row.get("stddev_ts"), "samples_ts": row.get("samples_ts"),
            "build_commit": row.get("build_commit"), "pid": info.get("pid"), "log_tail": out[-2000:]}


def tbo_parser():
    import importlib.util
    spec = importlib.util.spec_from_file_location("tbo_parse", paths.TBO_PARSE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.parse_test_backend_ops


def do_ops(spec):
    rc, out = _run(spec["argv"], measure.block_env(spec), spec["log"], spec["deadline"])
    fails = re.findall(r"^.*FAIL.*$", out, re.M)
    passed = re.search(r"(\d+)/(\d+) tests passed", out)
    # 21j P4: the pass/fail of every case is recomputed from the printed error vs threshold and the summary counts;
    # any contradiction between what the tool says and its own numbers fails G1
    p = tbo_parser()(out)
    contra = p.get("contradictions") or []
    return {"rc": rc, "ok": rc == 0 and not fails and not contra, "fails": fails[:20] + [
            f"contradiction {c.get('kind')}: {str(c.get('detail'))[:120]}" for c in contra[:5]],
            "recomputed": {k: p.get(k) for k in ("status", "n_ok", "n_fail", "summary_passed", "summary_total")},
            "passed": passed.group(0) if passed else None, "log_tail": out[-2000:]}


def do_kld(spec):
    rc, out = _run(spec["argv"], measure.block_env(spec), spec["log"], spec["deadline"])
    return {"rc": rc, "log": spec["log"], "log_tail": out[-2000:]}


KINDS = {"serve": measure.serve_run, "neartie": measure.neartie_run, "probe": measure.probe_run,
         "greedy": do_greedy, "bench": do_bench, "ops": do_ops, "kld": do_kld}


def main(spec_path: str) -> int:
    spec = json.loads(Path(spec_path).read_text())
    out = Path(spec["out"])
    spec["deadline"] = time.time() + spec.get("budget_s", paths.BLOCK_TIMEOUT_S - 10)
    res = {"name": spec["name"], "kind": spec["kind"], "started": time.time(), "ok": False}
    if preflight.user_server_listening():  # H8: anything on :8080 is the user's server (ss, not pgrep)
        if spec.get("stop_topka"):  # inside both locks; topka-keeper restarts it once the GPU lock is free
            from .cycle import stop_user_server
            res["topka_stopped"] = stop_user_server(log=lambda *a: None)
        if preflight.user_server_listening():
            res["refused"] = [f"H8 something listens on :{paths.USER_PORT} (the user's server)"]
            out.write_text(json.dumps(res))
            return 97
    h0 = hashing.hash_harness()
    snap, found = _preflight(spec)
    res["snapshot"] = snap
    if found:
        res["refused"] = [f"{f.rule} {f.message}" for f in found]
        out.write_text(json.dumps(res))
        return 98
    # H1 inside both locks: the previous holder may have left the card hot; wait (sysfs reads) up to H1_WAIT_S
    waited = 0
    while True:
        hot = hwgates.h1({"temp_c": (snap.get("temp_c") if waited == 0 else hwgates.temps())})
        if not hot or waited >= H1_WAIT_S:
            break
        time.sleep(15)
        waited += 15
    if hot:
        res["refused"] = [f"H1 {m}" for m in hot]
        out.write_text(json.dumps(res))
        return 98
    try:
        done = KINDS[spec["kind"]](spec)
        res.update(done)
        res["ok"] = done.get("rc", 0) == 0 if spec["kind"] in ("greedy", "kld") else done.get("ok", True)
    except Exception as e:  # recorded, never hidden: the verifier turns it into INVALID
        res["error"] = f"{type(e).__name__}: {e}"
    res["snapshot_after"] = preflight.snapshot()
    res["harness_before"], res["harness_after"] = hashing.tree_sha(h0), hashing.tree_sha(hashing.hash_harness())
    res["secs"] = round(time.time() - res["started"], 1)
    out.write_text(json.dumps(res))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
