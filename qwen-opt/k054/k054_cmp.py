#!/usr/bin/env python3
"""K-054: pass@1 (base / plus) of effort xhigh vs low on the tasks xhigh has answered (a partial run is fine).
Pads the xhigh samples with empty answers for the missing tasks (evalplus evaluate needs every task) into
runs/uncensored-xhigh-pad/; run `jakosc-mini.sh --tag uncensored-xhigh-pad --datasets DS eval` in between; cmp then
compares with runs/uncensored-low on the answered subset.
usage: k054_cmp.py pad|cmp humaneval|mbpp"""
import json, os, sys

EP = os.path.expanduser("~/qwen-opt/evalplus/runs")
X, P, L = f"{EP}/uncensored-xhigh", f"{EP}/uncensored-xhigh-pad", f"{EP}/uncensored-low"


def results(path):
    ev = json.load(open(path))["eval"]
    return {t: (v[0]["base_status"] == "pass", v[0]["plus_status"] == "pass") for t, v in ev.items()}


def tokens(path):
    return {r["prompt_head"]: r["completion_tokens"] for r in map(json.loads, open(path)) if r.get("completion_tokens")}


ds = sys.argv[2]
if sys.argv[1] == "pad":
    from evalplus.data import get_human_eval_plus, get_mbpp_plus
    tasks = get_human_eval_plus() if ds == "humaneval" else get_mbpp_plus()
    done = {r["task_id"]: r for r in map(json.loads, open(f"{X}/{ds}.jsonl"))}
    os.makedirs(P, exist_ok=True)
    with open(f"{P}/{ds}.jsonl", "w") as f:
        for t in tasks:
            f.write(json.dumps(done.get(t, {"task_id": t, "solution": ""})) + "\n")
    json.dump(sorted(done), open(f"{P}/{ds}.answered.json", "w"))
    print(f"{ds} padded: {len(done)} answered of {len(tasks)}")
else:
    ids = json.load(open(f"{P}/{ds}.answered.json"))
    x, l = results(f"{P}/{ds}_eval_results.json"), results(f"{L}/{ds}_eval_results.json")
    n = len(ids)
    for name, r in (("low", l), ("xhigh", x)):
        print(f"{name:5}: base {sum(r[t][0] for t in ids)}/{n} = {100 * sum(r[t][0] for t in ids) / n:.1f}%, "
              f"plus {sum(r[t][1] for t in ids)}/{n} = {100 * sum(r[t][1] for t in ids) / n:.1f}%")
    flip = [(t, l[t][1], x[t][1]) for t in ids if l[t][1] != x[t][1]]
    print("plus differs:", flip)
    tx, tl = tokens(f"{X}/{ds}.stats.jsonl"), tokens(f"{L}/{ds}.stats.jsonl")
    common = [k for k in tx if k in tl]
    if common:
        print(f"tokens/answer on {len(common)} common: low {sum(tl[k] for k in common) / len(common):.0f}, "
              f"xhigh {sum(tx[k] for k in common) / len(common):.0f}")
