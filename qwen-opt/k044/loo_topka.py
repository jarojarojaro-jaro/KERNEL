#!/usr/bin/env python3
"""K-044: leave-one-out of the env-switch patches (tools/loo.py plan, trials, ABBA order, results/report format) on the
production engine ~/llama-topka (topka-q70) from inside the GPU queue. Differences to `loo.py run`:
  * engine ~/llama-topka (libraries in bin/) instead of the old amd-opt ~/llama-opt;
  * no `flock` wrapper and no 45 s pauses: the queue already holds the GPU locks (a nested flock would wait for itself);
  * port 18795; blocks run in-process until --budget seconds (one queue job <= 10 min), finished trials are skipped.
usage:  loo_topka.py --only N[,N] [--models qwen] [--rounds 2] [--budget 500]
report: python3 ~/qwen-opt/tools/loo.py report --out ~/qwen-opt/k044/loo
"""
import argparse, json, os, sys, time, types

sys.path.insert(0, os.path.expanduser("~/qwen-opt/tools"))
import loo  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "loo")
TOPKA_BIN = os.path.expanduser("~/llama-topka/bin")
loo.variant_install = lambda e, variant: (TOPKA_BIN, TOPKA_BIN)  # env/cli patches: the same binary in both arms


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", required=True)
    ap.add_argument("--models", default="qwen")
    ap.add_argument("--rounds", type=int, default=2)
    ap.add_argument("--budget", type=int, default=500)
    a = ap.parse_args()
    t0 = time.time()
    results = os.path.join(OUT, "loo-results.jsonl")
    plan = loo.load_plan(OUT)
    trials = loo.trials_for(plan, types.SimpleNamespace(only=a.only, models=a.models, kind="env", rounds=a.rounds))
    if loo.user_server_running():
        sys.exit("refusing: :8080 is running")
    while True:
        loo.learn_est(results)
        done = loo.done_keys(results)
        todo = [t for t in trials if loo.trial_key(t) not in done]
        left = a.budget - (time.time() - t0)
        blk, s = [], 0
        for t in todo:
            est = loo.EST_S[(t["measure"], t["model"])]
            if s + est > left:
                break
            blk.append(t)
            s += est
        print(f"{len(trials)} trials, {len(todo)} to run, {left:.0f} s left, block of {len(blk)}", flush=True)
        if not blk:
            break
        bf = os.path.join(OUT, "block.json")
        with open(bf, "w") as f:
            json.dump(blk, f)
        loo.BLOCK_S = int(left)
        loo.cmd_block(types.SimpleNamespace(out=OUT, block=bf, results=results, port=18795))
        if len(done) == len(loo.done_keys(results)):
            sys.exit("block finished no trial: stopping")


if __name__ == "__main__":
    main()
