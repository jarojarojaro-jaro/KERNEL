#!/usr/bin/env python3
"""HumanEval+ execution for a jakość-mini run: the subset's sanitized solutions (answers.jsonl) are run against the
evalplus base + plus tests in the EvalPlus sandbox (../evalplus/sandbox_eval.py): Landlock (no TCP, fs writes only in
the run dir, /dev/shm, /dev/null), Python socket guard, evalplus reliability_guard + per-test time limits in every
worker. run.py code-eval adds nice 19 + systemd-run --user --scope MemoryMax=4G CPUQuota=200%.
evalplus.evaluate() insists on all 164 tasks, so this calls its check_correctness() per task with the same defaults
(fast_check, DEFAULT_MIN_TIME_LIMIT, DEFAULT_GT_TIME_LIMIT_FACTOR).
Output: <run>/humaneval_plus_eval.json {task_id: {"base": status, "plus": status}}.
"""
import argparse, json, os, shutil, sys, tempfile
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "evalplus"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--parallel", type=int, default=2)
    a = ap.parse_args()
    if os.geteuid() == 0:
        sys.exit("refusing to run untrusted code as root")
    from sandbox_eval import landlock, socket_guard
    from evalplus.data import get_human_eval_plus, get_human_eval_plus_hash
    from evalplus.evaluate import DEFAULT_GT_TIME_LIMIT_FACTOR, DEFAULT_MIN_TIME_LIMIT, check_correctness, get_groundtruth
    run = os.path.abspath(a.run)
    sols = {}
    for l in open(os.path.join(run, "answers.jsonl")):
        r = json.loads(l)
        if r["cat"] == "humaneval_plus":
            sols[r["id"]] = r["solution"]
    problems = get_human_eval_plus()
    expected = get_groundtruth(problems, get_human_eval_plus_hash(), [])  # trusted, cached before the sandbox closes
    scratch = tempfile.mkdtemp(prefix="sbx-", dir=run)
    os.environ["TMPDIR"] = scratch
    tempfile.tempdir = scratch
    landlock([run, "/dev/shm", "/dev/null"])
    socket_guard()
    print(f"sandbox: landlock (TCP denied, writes -> {run}, /dev/shm), socket guard, {len(sols)} solutions", flush=True)
    res = {}
    with ProcessPoolExecutor(max_workers=a.parallel) as ex:
        futs = [ex.submit(check_correctness, "humaneval", 0, problems[t], s, expected[t], False, True, t,
                          DEFAULT_MIN_TIME_LIMIT, DEFAULT_GT_TIME_LIMIT_FACTOR) for t, s in sols.items()]
        for f in futs:
            r = f.result()
            res[r["task_id"]] = {"base": r["base"][0], "plus": r["plus"][0]}
            print(r["task_id"], res[r["task_id"]], flush=True)
    json.dump(res, open(os.path.join(run, "humaneval_plus_eval.json"), "w"), indent=1)
    shutil.rmtree(scratch, ignore_errors=True)
    n = sum(v["base"] == "pass" and v["plus"] == "pass" for v in res.values())
    print(f"HumanEval+ pass (base and plus): {n}/{len(res)}")


if __name__ == "__main__":
    main()
