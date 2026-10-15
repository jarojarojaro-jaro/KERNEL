#!/usr/bin/env python3
"""Leave-one-out (LOO) of the amd-opt patches: plan, GPU runner, revert builds, report.

  loo.py plan    [--repo R] [--base B] [--head H]        -> loo-plan.json, loo-plan.md (CPU only, git)
  loo.py run     [--dry-run|--fake] [--rounds N] [--only NN,..] [--kind env|build|all] [--models qwen,lfm]
                                                           -> loo-results.jsonl (resume: finished trials are skipped)
  loo.py builds  [--dry-run]                              -> loo-builds.sh (revert builds, CPU, run it by hand)
  loo.py report  [--results F]                            -> loo-report.md (means, paired 95 % CI, flags)

GPU rules: every block of trials runs as `flock /tmp/gpu.lock flock /tmp/quiet.lock python3 loo.py _block ...`,
refuses to start while `pgrep -f 'llama-server.*--port 8080'` finds the user's server, is <= 5 min long and is
followed by a 45 s pause. Servers use ports 18433-18499 (default 18440).
"""
import argparse
import json
import math
import os
import random
import re
import shlex
import signal
import subprocess
import sys
import time
import urllib.request

HOME = os.path.expanduser("~")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "loo")
REPO = os.path.join(HOME, "llama-master")
BASE = "e60eff95f"
HEAD = "c36fd2c87"
ROCM_LIB = "/opt/rocm/core-10.0/lib"
REF_INST = os.path.join(HOME, "llama-opt")              # installed amd-opt @ HEAD (bin/, lib/)
LOO_SRC = os.path.join(HOME, "wt", "loo-build")         # scratch worktree of the revert builds
LOO_BINS = os.path.join(HOME, "wt", "loo-bins")         # <NN>/ (and ref/): llama-bench, llama-server + .so
GPU_WRAP = ["flock", "/tmp/gpu.lock", "flock", "/tmp/quiet.lock"]
USER_SERVER = "llama-server.*--port 8080"
BLOCK_S = 300        # max GPU block
PAUSE_S = 45         # pause between blocks
TRIAL_TIMEOUT = 280  # one trial (server start + requests or one llama-bench) never exceeds this

MODELS = {
    "qwen": dict(gguf=f"{HOME}/models/Qwen3.8-27B-UD-Q4_K_XL.gguf", kv="q4_0", ctx=204800, spec=True),
    "lfm":  dict(gguf=f"{HOME}/models/lfm/LFM2.5-24B-A2B-Q5_K_M.gguf", kv="q8_0", ctx=131072, spec=False),
}
MTP_ARGS = ["--spec-type", "draft-mtp", "--spec-draft-n-max", "4",
            "--spec-draft-vocab", f"{HOME}/models/draft/draft_vocab_qwen38.txt", "--spec-draft-vocab-n", "65536",
            "--spec-draft-head-type", "iq4_xs", "--spec-mtp-type", "iq4_xs", "-ctkd", "{kv}", "-ctvd", "{kv}"]
PROMPTS = ["Explain how a hash map works, then implement one in C with open addressing.",
           "Napisz krótkie opowiadanie o latarniku i sztormie."]
# measures: tg = llama-bench tg128 (-r 3), pp = llama-bench pp4096 (-r 3),
#           serve = llama-server decode (Qwen: MTP n=4 as run-llm.sh, LFM: plain), 2 prompts x 256 tokens, T=0
EST_S = {("tg", "qwen"): 45, ("tg", "lfm"): 35, ("pp", "qwen"): 55, ("pp", "lfm"): 40,
         ("serve", "qwen"): 75, ("serve", "lfm"): 50}

# ---------------------------------------------------------------------------------------------------------------
# Manual classification (judgement from the commit messages and diffs at c36fd2c87). Keyed by patch number.
#   cat: env | cli | build | nonspeed
#   env: {NAME: value that turns the patch OFF};  cli_drop: CLI args removed for the OFF variant
#   models / measures: where the patch acts in the production configs (run-llm.sh)
#   active: False = not on the default path of run-llm.sh (opt-in feature), excluded from the runner
#   why: nonspeed reason or coverage note
# ---------------------------------------------------------------------------------------------------------------
B, Q, L = ("qwen", "lfm"), ("qwen",), ("lfm",)
CLASS = {
    1:  dict(cat="build", models=Q, measures=["serve"], why="multi-column MMVQ (MTP verify)"),
    2:  dict(cat="build", models=Q, measures=["serve"], why="multi-column MMVQ i-quants/Q2_K"),
    3:  dict(cat="build", models=B, measures=["tg", "serve"], why="q8_1 activation reuse"),
    4:  dict(cat="cli", models=Q, measures=["serve"], cli_drop=["--spec-draft-vocab", "--spec-draft-vocab-n"],
             why="reduced-vocabulary draft head; OFF = full-vocabulary draft head"),
    5:  dict(cat="nonspeed", why="build hygiene (drops a local tuning include)"),
    6:  dict(cat="nonspeed", why="Vulkan backend only (not in the ROCm path)"),
    7:  dict(cat="nonspeed", why="Vulkan backend only (not in the ROCm path)"),
    8:  dict(cat="nonspeed", why="Vulkan backend only (not in the ROCm path)"),
    9:  dict(cat="nonspeed", why="Vulkan backend only (not in the ROCm path)"),
    10: dict(cat="nonspeed", why="Vulkan backend only (not in the ROCm path)"),
    11: dict(cat="build", models=Q, measures=["tg", "serve"], why="FA kvq kernel for q4_0 KV (Qwen KV q4_0)"),
    12: dict(cat="build", models=Q, measures=["serve"], why="bias/residual ADD epilogue, multi-column MMVQ"),
    13: dict(cat="build", models=Q, measures=["tg", "serve"], why="GDN prologue fusion"),
    14: dict(cat="build", models=B, measures=["tg", "serve"], why="conv-state concat/snapshots folded into SSM_CONV"),
    15: dict(cat="build", models=B, measures=["tg", "serve"], why="q8_1 activations written by norm/GLU/unary*mul"),
    16: dict(cat="build", models=Q, measures=["tg", "serve"], why="GDN alpha/beta MMVQ templated on token count"),
    17: dict(cat="build", models=Q, measures=["tg", "serve"], why="IMROPE fused into RMS_NORM+MUL+ROPE"),
    18: dict(cat="nonspeed", why="correctness fix (FA race, upstream cherry-pick)"),
    19: dict(cat="build", models=B, measures=["tg", "serve"], why="q/k Hadamard rotation folded into norm+rope"),
    20: dict(cat="build", models=Q, measures=["serve"], why="MTP draft chain graph (no switch; p_min>0 is not equivalent)"),
    21: dict(cat="build", models=Q, measures=["serve"], why="multi-column MMVQ buffer loads/occupancy/DPP"),
    22: dict(cat="build", models=Q, measures=["serve"], why="multi-column MMVQ GLC|DLC streaming"),
    23: dict(cat="nonspeed", why="correctness fix (fp16 clamp of q8_1 d/sum)"),
    24: dict(cat="env", env={"GGML_HIP_MMVQ_PAIR": "0"}, models=Q, measures=["tg", "serve"]),
    25: dict(cat="env", env={"GGML_HIP_NORM_FAST": "0"}, models=B, measures=["tg", "serve"]),
    26: dict(cat="env", env={"GGML_HIP_ARGMAX_FAST": "0"}, models=Q, measures=["serve"],
             why="GPU argmax: MTP greedy drafts"),
    27: dict(cat="env", env={"GGML_HIP_NORM_GATE": "0"}, models=Q, measures=["tg", "serve"]),
    28: dict(cat="env", env={"GGML_HIP_GDN_CONV_AB": "0"}, models=Q, measures=["tg", "serve"]),
    29: dict(cat="env", env={"LLAMA_ASYNC_INPUTS": "0"}, models=B, measures=["tg", "serve"]),
    30: dict(cat="env", env={"LLAMA_MTP_CHAIN_SCHED": "0"}, models=Q, measures=["serve"]),
    31: dict(cat="env", env={"LLAMA_SAMPLER_FAST_TOPK": "0", "LLAMA_SPEC_LAZY_SAVE": "0"}, models=B,
             measures=["serve"], why="host sampler / server spec loop"),
    32: dict(cat="cli", models=Q, measures=["serve"], cli_drop=["--spec-draft-head-type", "--spec-mtp-type"],
             why="re-quantized MTP head/block; OFF = GGUF types (draft numerics differ, output identical)"),
    33: dict(cat="env", env={"LLAMA_GDN_REPLAY": "0"}, models=Q, measures=["serve"],
             why="OFF also disables the later lag refinements 34-36, 38"),
    34: dict(cat="build", models=Q, measures=["serve"], why="lag info layout (refines 33)"),
    35: dict(cat="build", models=Q, measures=["serve"], why="GDN_LAG load scheduling"),
    36: dict(cat="build", models=Q, measures=["serve"], why="lagged state read from its cache row (refines 33/34)"),
    37: dict(cat="build", models=Q, measures=["serve"], active=False,
             why="verify batches of 9-16 columns: inactive at MTP n=4 (5 columns)"),
    38: dict(cat="env", env={"LLAMA_CONV_LAG": "0"}, models=Q, measures=["serve"]),
    39: dict(cat="nonspeed", why="opt-in (--spec-draft-adaptive, not used by run-llm.sh); LLAMA_VERIFY_SCHED only with it"),
    40: dict(cat="build", models=B, measures=["pp"], why="prefill: MMQ narrower tile"),
    41: dict(cat="build", models=Q, measures=["serve", "pp"], why="MTP layer K/V-only rows"),
    42: dict(cat="build", models=Q, measures=["pp"], why="prefill: FA MMA D=256 tile Q in SRAM"),
    43: dict(cat="nonspeed", why="numerics fix (bit-identical prompt logits of 42; KLD 0.0135 -> 0)"),
    44: dict(cat="nonspeed", why="tests only"),
    45: dict(cat="build", models=Q, measures=["pp"], why="prefill: GDN l2 pre-pass"),
    46: dict(cat="nonspeed", why="opt-in WIP (--spec-mtp-window, not used by run-llm.sh)"),
    47: dict(cat="env", env={"LLAMA_KV_MASK_FAST": "0", "LLAMA_KV_SEQ_RM_SCAN": "1"}, models=B, measures=["serve"],
             why="partial: the draft prompt-copy skip has no switch"),
    48: dict(cat="env", env={"LLAMA_SAMPLER_FAST_PENALTIES": "0"}, models=B, measures=["serve"]),
    49: dict(cat="env", env={"GGML_HIP_Q8_IDS": "0"}, models=L, measures=["tg", "serve"]),
    50: dict(cat="env", env={"GGML_HIP_CONV_MUL": "0"}, models=L, measures=["tg", "serve"],
             why="OFF also disables 54/62 (they build on it)"),
    51: dict(cat="env", env={"GGML_HIP_MOE_DOWN_REDUCE": "0"}, models=L, measures=["tg", "serve"]),
    52: dict(cat="env", env={"GGML_HIP_MMVQ_N1_ROWS": "1"}, models=B, measures=["tg", "serve"],
             why="one-column K-quant MMVQ: Qwen plain decode + LFM"),
    53: dict(cat="env", env={"GGML_HIP_NORM_ROUTER": "0"}, models=L, measures=["tg", "serve"]),
    54: dict(cat="env", env={"GGML_HIP_INPROJ_CONV": "0"}, models=L, measures=["tg", "serve"]),
    55: dict(cat="env", env={"GGML_HIP_KVQ_Q8": "0"}, models=L, measures=["tg", "serve"],
             why="not bitwise (KLD-gated); KV q8_0 only"),
    56: dict(cat="env", env={"GGML_HIP_GATE_UP_Q8": "0"}, models=L, measures=["tg", "serve"]),
    57: dict(cat="env", env={"GGML_HIP_ATTN_PREP": "0"}, models=L, measures=["tg", "serve"]),
    58: dict(cat="env", env={"GGML_HIP_KVQ_FWHT": "0"}, models=B, measures=["tg", "serve"]),
    59: dict(cat="env", env={"GGML_HIP_INPUT_BATCH": "0"}, models=B, measures=["tg", "serve"]),
    60: dict(cat="env", env={"GGML_HIP_PM4": "0"}, models=B, measures=["tg", "serve"]),
    61: dict(cat="nonspeed", why="tooling (GGML_HIP_PM4_DEBUG=2 timing)"),
    62: dict(cat="env", env={"GGML_HIP_CONV_ROWS4": "0"}, models=L, measures=["tg", "serve"]),
    63: dict(cat="nonspeed", why="refactor (switches read through ggml_cuda_env_switch)"),
    64: dict(cat="env", env={"GGML_HIP_MMVQ_N1_Q8_0": "0"}, models=L, measures=["tg", "serve"]),
    65: dict(cat="env", env={"LLAMA_SERVER_REASONING_CONTROL": "1"}, models=B, measures=["serve"],
             base_env={"LLAMA_SERVER_REASONING_CONTROL": "0"}, request_extra={"reasoning_control": True},
             why="web-UI requests only: measured with reasoning_control=true in the request"),
}
ENV_RE = re.compile(r"\b((?:GGML_HIP|GGML_CUDA|LLAMA)_[A-Z0-9_]+)\b")
CLI_ENV_PREFIX = "LLAMA_ARG_"


def git(*args, repo=REPO, check=True):
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)
    if check and r.returncode not in (0, 1):
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr}")
    return r


def env_literal_in_code(repo, rev, name):
    """Code (non-comment) lines at rev that contain the string literal "NAME"."""
    r = git("grep", "-n", f'"{name}"', rev, "--", "ggml", "src", "common", "tools", repo=repo)
    hits = []
    for line in r.stdout.splitlines():
        _, path, lno, text = line.split(":", 3)
        if text.lstrip().startswith("//"):
            continue
        hits.append(f"{path}:{lno}")
    return hits


def revert_check(repo, head, sha):
    """Clean revert of sha on head? (git merge-tree, no worktree). Returns (clean, conflicted files)."""
    r = git("merge-tree", "--write-tree", "--name-only", "--no-messages", f"--merge-base={sha}", head, f"{sha}^",
            repo=repo)
    lines = r.stdout.splitlines()
    files = [x for x in lines[1:] if x.strip()]
    return r.returncode == 0, files


def cmd_plan(a):
    revs = git("rev-list", "--reverse", f"{a.base}..{a.head}", repo=a.repo).stdout.split()
    if len(revs) != len(CLASS):
        sys.exit(f"{len(revs)} commits but {len(CLASS)} classified: update CLASS")
    touched = {}
    for sha in revs:
        touched[sha] = set(git("show", "--name-only", "--format=", sha, repo=a.repo).stdout.split())
    plan = []
    for i, sha in enumerate(revs, 1):
        c = dict(CLASS[i])
        subj = git("log", "-1", "--format=%s", sha, repo=a.repo).stdout.strip()
        body = git("log", "-1", "--format=%B", sha, repo=a.repo).stdout
        diff_add = "\n".join(l for l in git("show", "--format=", sha, repo=a.repo).stdout.splitlines()
                             if l.startswith("+") and not l.startswith("+++"))
        msg_env = sorted(set(ENV_RE.findall(body)))
        diff_env = sorted(set(n for n in re.findall(r'"((?:GGML_HIP|GGML_CUDA|LLAMA)_[A-Z0-9_]+)"', diff_add)
                              if not n.startswith(CLI_ENV_PREFIX)))
        cli_env = sorted(set(n for n in re.findall(r'"(LLAMA_ARG_[A-Z0-9_]+)"', diff_add)))
        e = dict(n=i, sha=sha[:9], subject=subj, msg_env=msg_env, diff_env=diff_env, cli_env=cli_env,
                 files=sorted(touched[sha]), **c)
        e.setdefault("models", [])
        e.setdefault("measures", [])
        e.setdefault("active", c["cat"] != "nonspeed")
        e["models"] = list(e["models"])
        if c["cat"] == "env":
            e["env_found"] = {n: env_literal_in_code(a.repo, a.head, n) for n in c["env"]}
            missing = [n for n, h in e["env_found"].items() if not h]
            if missing:
                sys.exit(f"patch {i}: switch {missing} not in the source at {a.head}")
            undeclared = [n for n in c["env"] if n not in msg_env + diff_env]
            if undeclared:
                e["note_env"] = f"switch not introduced by this commit's text/diff: {undeclared}"
        # names this commit introduces that the classification does not use (cross-check, shown in the .md)
        e["env_unused"] = [n for n in diff_env if n not in c.get("env", {})]
        if c["cat"] == "build":
            clean, files = revert_check(a.repo, a.head, sha)
            e["revert_clean"] = clean
            e["revert_conflicts"] = files
            if not clean:
                later = [f"{j:02d}" for j, s in enumerate(revs, 1) if j > i and touched[s] & set(files)]
                e["revert_blockers"] = later
        plan.append(e)
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "loo-plan.json"), "w") as f:
        json.dump(dict(repo=a.repo, base=a.base, head=a.head, patches=plan), f, indent=1, ensure_ascii=False)
    md = plan_md(plan, a)
    with open(os.path.join(a.out, "loo-plan.md"), "w") as f:
        f.write(md)
    print(md.split("\n## ")[0])
    print(f"wrote {a.out}/loo-plan.json, loo-plan.md")


def plan_md(plan, a):
    cnt = {}
    for e in plan:
        cnt[e["cat"]] = cnt.get(e["cat"], 0) + 1
    b_clean = sum(1 for e in plan if e["cat"] == "build" and e["revert_clean"])
    b_act = sum(1 for e in plan if e["cat"] == "build" and e["active"])
    nonspeed_kinds = {}
    for e in plan:
        if e["cat"] == "nonspeed":
            k = e["why"].split(" (")[0].split(":")[0]
            nonspeed_kinds[k] = nonspeed_kinds.get(k, 0) + 1
    out = [f"# LOO plan: {len(plan)} patches {a.base}..{a.head}\n",
           f"- runtime env switch (verified in source): {cnt.get('env', 0)}",
           f"- runtime CLI switch (OFF = drop the args): {cnt.get('cli', 0)}",
           f"- build-time only (git revert + rebuild): {cnt.get('build', 0)} "
           f"(clean revert {b_clean}, conflicts {cnt.get('build', 0) - b_clean}; on the default path {b_act})",
           f"- non-speed: {cnt.get('nonspeed', 0)} ("
           + ", ".join(f"{k} {v}" for k, v in sorted(nonspeed_kinds.items(), key=lambda x: -x[1])) + ")",
           "", "## Patches", "",
           "| # | sha | cat | OFF | models | measures | revert | note | subject |", "|---|---|---|---|---|---|---|---|---|"]
    for e in plan:
        off = ""
        if e["cat"] == "env":
            off = " ".join(f"{k}={v}" for k, v in e["env"].items())
        elif e["cat"] == "cli":
            off = "drop " + " ".join(e["cli_drop"])
        rev = ""
        if e["cat"] == "build":
            rev = "clean" if e["revert_clean"] else "CONFLICT " + ",".join(
                os.path.basename(x) for x in e["revert_conflicts"]) + " (later: " + ",".join(e["revert_blockers"]) + ")"
        note = e.get("why", "")
        if not e["active"] and e["cat"] != "nonspeed":
            note = "INACTIVE: " + note
        if e.get("env_unused"):
            note += f" [also introduces {','.join(e['env_unused'])}]"
        out.append(f"| {e['n']:02d} | {e['sha']} | {e['cat']} | {off} | {','.join(e['models'])} | "
                   f"{','.join(e['measures'])} | {rev} | {note} | {e['subject'][:90].replace('|', '/')} |")
    out += ["", "Env switches: name found as a string literal in non-comment code at HEAD "
            "(file:line in loo-plan.json `env_found`).",
            "Revert check: `git merge-tree --write-tree --merge-base=<sha> HEAD <sha>^` (no worktree). A conflicting "
            "revert lists the later patches touching the conflicted files: those need a manual LOO port or a group "
            "revert.", ""]
    return "\n".join(out)


# ---------------------------------------------------------------------------------------------------------------
# runner
# ---------------------------------------------------------------------------------------------------------------
def load_plan(out):
    with open(os.path.join(out, "loo-plan.json")) as f:
        return json.load(f)["patches"]


def variant_install(e, variant):
    """(bin dir, lib dir) of a trial."""
    if e["cat"] == "build":
        d = os.path.join(LOO_BINS, "ref" if variant == "on" else f"{e['n']:02d}")
        return d, d
    return os.path.join(REF_INST, "bin"), os.path.join(REF_INST, "lib")


def variant_env(e, variant):
    env = dict(e.get("base_env", {}))
    if variant == "off" and e["cat"] == "env":
        env.update(e["env"])
    return env


def drop_args(args, names):
    out, skip = [], False
    for x in args:
        if skip:
            skip = False
            continue
        if x in names:
            skip = True
            continue
        out.append(x)
    return out


def trial_command(e, model, measure, variant, port):
    """argv of one trial (llama-bench) or None for serve (done in-process). Also returns env and bin dir."""
    m = MODELS[model]
    bin_dir, lib_dir = variant_install(e, variant)
    env = variant_env(e, variant)
    env["LD_LIBRARY_PATH"] = f"{lib_dir}:{ROCM_LIB}"
    if measure in ("tg", "pp"):
        pn = ["-p", "0", "-n", "128"] if measure == "tg" else ["-p", "4096", "-n", "0"]
        argv = [f"{bin_dir}/llama-bench", "-m", m["gguf"], "-ngl", "99", "-fa", "1", "-ctk", m["kv"], "-ctv", m["kv"],
                *pn, "-r", "3", "-o", "jsonl"]
    else:
        argv = [f"{bin_dir}/llama-server", "--port", str(port), "--host", "127.0.0.1", "-np", "1", "--no-webui",
                "-m", m["gguf"], "-ngl", "999", "-fa", "on", "-ctk", m["kv"], "-ctv", m["kv"], "-c", str(m["ctx"]),
                "--jinja"]
        if m["spec"]:
            spec = [x.replace("{kv}", m["kv"]) for x in MTP_ARGS]
            if variant == "off" and e["cat"] == "cli":
                spec = drop_args(spec, set(e["cli_drop"]))
            argv += spec
    return argv, env


def trials_for(plan, a):
    """Ordered list of trials (dict), ABBA within a round pair, rounds of a (patch, model, measure) consecutive."""
    only = set(int(x) for x in a.only.split(",")) if a.only else None
    models = set(a.models.split(","))
    out = []
    for e in plan:
        if e["cat"] == "nonspeed" or not e["active"]:
            continue
        if e["cat"] == "build" and not e.get("revert_clean"):
            continue  # no revert build exists (loo-plan.md lists the later patches it conflicts with)
        if a.kind != "all" and (e["cat"] == "build") != (a.kind == "build"):
            continue
        if only and e["n"] not in only:
            continue
        for model in e["models"]:
            if model not in models:
                continue
            for measure in e["measures"]:
                for r in range(1, a.rounds + 1):
                    order = ("on", "off") if r % 2 else ("off", "on")
                    for v in order:
                        out.append(dict(n=e["n"], model=model, measure=measure, round=r, variant=v))
    return out


def trial_key(t):
    return f"{t['n']:02d}/{t['model']}/{t['measure']}/{t['round']}/{t['variant']}"


def learn_est(path):
    """Trial duration estimates: the slowest finished trial of each (measure, model) once there is one."""
    if not os.path.exists(path):
        return
    seen = {}
    with open(path) as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                if r.get("ok") and "secs" in r:
                    k = (r["measure"], r["model"])
                    seen[k] = max(seen.get(k, 0), r["secs"])
    for k, v in seen.items():
        EST_S[k] = max(10, math.ceil(v))


def done_keys(path):
    keys = set()
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    r = json.loads(line)
                    if r.get("ok"):
                        keys.add(r["key"])
    return keys


def user_server_running():
    return subprocess.run(["pgrep", "-f", USER_SERVER], capture_output=True).returncode == 0


def post(port, body, timeout):
    req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def run_serve(argv, env, port, e, deadline, log):
    full_env = dict(os.environ, **env)
    with open(log, "w") as lf:
        p = subprocess.Popen(argv, env=full_env, stdout=lf, stderr=subprocess.STDOUT)
    try:
        while time.time() < deadline:
            if p.poll() is not None:
                raise RuntimeError(f"server exited {p.returncode}, see {log}")
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2) as r:
                    if r.status == 200:
                        break
            except Exception:
                time.sleep(1)
        else:
            raise RuntimeError("server not healthy before the trial deadline")
        tps, acc, ntok = [], [], 0
        for prompt in PROMPTS:
            body = dict(messages=[dict(role="user", content=prompt)], max_tokens=256, temperature=0,
                        chat_template_kwargs=dict(enable_thinking=False), **e.get("request_extra", {}))
            r = post(port, body, max(5, deadline - time.time()))
            t = r["timings"]
            tps.append(t["predicted_per_second"])
            ntok += t["predicted_n"]
            if t.get("draft_n"):
                acc.append(t["draft_n_accepted"] / t["draft_n"])
        return dict(value=sum(tps) / len(tps), per_prompt=tps, tokens=ntok,
                    accept=(sum(acc) / len(acc)) if acc else None)
    finally:
        p.terminate()
        try:
            p.wait(20)
        except subprocess.TimeoutExpired:
            p.kill()
            p.wait()


def run_bench(argv, env, deadline):
    r = subprocess.run(argv, env=dict(os.environ, **env), capture_output=True, text=True,
                       timeout=max(5, deadline - time.time()))
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-800:])
    rows = [json.loads(l) for l in r.stdout.splitlines() if l.startswith("{")]
    row = rows[-1]
    return dict(value=row["avg_ts"], stddev=row.get("stddev_ts"), samples=row.get("samples_ts"))


def fake_value(t):
    """Synthetic t/s for --fake: patch n costs n*0.1 % when removed, every 7th patch is neutral, 13th faster off."""
    base = {"qwen": 110.0, "lfm": 290.0}[t["model"]] * {"tg": 1.0, "pp": 8.0, "serve": 1.0}[t["measure"]]
    eff = 0.0 if t["n"] % 7 == 0 else (+0.006 if t["n"] % 13 == 0 else -0.001 * t["n"])
    rnd = random.Random(trial_key(t))
    v = base * (1 + (eff if t["variant"] == "off" else 0)) * (1 + rnd.gauss(0, 0.002))
    return dict(value=v)


def cmd_block(a):
    """Runs inside the GPU locks: trials from a JSON file until BLOCK_S would be exceeded."""
    plan = {e["n"]: e for e in load_plan(a.out)}
    learn_est(a.results)
    with open(a.block) as f:
        trials = json.load(f)
    if user_server_running():
        sys.exit("refusing: user's llama-server on port 8080 is running")
    t0 = time.time()
    os.makedirs(os.path.join(a.out, "logs"), exist_ok=True)
    for t in trials:
        est = EST_S[(t["measure"], t["model"])]
        if time.time() - t0 + est > BLOCK_S:
            break
        e = plan[t["n"]]
        argv, env = trial_command(e, t["model"], t["measure"], t["variant"], a.port)
        deadline = min(time.time() + TRIAL_TIMEOUT, t0 + BLOCK_S + 30)
        rec = dict(key=trial_key(t), **t, env={k: v for k, v in env.items() if k != "LD_LIBRARY_PATH"},
                   ts=time.strftime("%F %T"))
        ts = time.time()
        try:
            if t["measure"] == "serve":
                res = run_serve(argv, env, a.port, e, deadline,
                                os.path.join(a.out, "logs", trial_key(t).replace("/", "_") + ".log"))
            else:
                res = run_bench(argv, env, deadline)
            rec.update(res, ok=True)
        except Exception as ex:  # recorded, retried on the next run (ok=False is not a finished trial)
            rec.update(ok=False, error=str(ex)[-500:])
        rec["secs"] = round(time.time() - ts, 1)
        with open(a.results, "a") as f:
            f.write(json.dumps(rec) + "\n")
        print(f"  {rec['key']}: {rec.get('value', rec.get('error'))} ({rec['secs']} s)", flush=True)


def cmd_run(a):
    plan = load_plan(a.out)
    if not (18433 <= a.port <= 18499):
        sys.exit("port must be in 18433-18499")
    trials = trials_for(plan, a)
    results = a.results
    if a.fake:
        results = a.results.replace(".jsonl", ".fake.jsonl")
    done = done_keys(results)
    learn_est(results)
    todo = [t for t in trials if trial_key(t) not in done]
    est = sum(EST_S[(t["measure"], t["model"])] for t in todo)
    nblk = max(1, math.ceil(est / (BLOCK_S - 30)))
    print(f"{len(trials)} trials, {len(trials) - len(todo)} done, {len(todo)} to run; "
          f"~{est / 3600:.1f} h GPU + ~{nblk * PAUSE_S / 3600:.1f} h pauses ({nblk} blocks)")
    if a.fake:
        with open(results, "a") as f:
            for t in todo:
                f.write(json.dumps(dict(key=trial_key(t), **t, ok=True, fake=True, **fake_value(t))) + "\n")
        print(f"fake: appended {len(todo)} synthetic trials to {results}")
        return
    if not a.dry_run:
        def have(d):
            return os.path.exists(os.path.join(LOO_BINS, d, "llama-server"))
        miss = sorted({f"{t['n']:02d}" for t in todo if plan[t["n"] - 1]["cat"] == "build"
                       and not (have("ref") and have(f"{t['n']:02d}"))})
        if miss:
            print(f"skipping build-time patches without binaries (ref or own) in {LOO_BINS}: {miss} (run loo-builds.sh)")
            todo = [t for t in todo if f"{t['n']:02d}" not in miss]
    blk_file = os.path.join(a.out, "block.json")
    while todo:
        # one block: as many trials as fit in BLOCK_S (by estimate; the block process also enforces it)
        blk, s = [], 0
        for t in todo:
            est_t = EST_S[(t["measure"], t["model"])]
            if blk and s + est_t > BLOCK_S - 30:
                break
            blk.append(t)
            s += est_t
        argv = GPU_WRAP + [sys.executable, os.path.abspath(__file__), "_block", "--block", blk_file,
                           "--results", results, "--out", a.out, "--port", str(a.port)]
        if a.dry_run:
            print(f"# block ~{s} s: " + ", ".join(trial_key(t) for t in blk))
            for t in blk:
                cmdv, env = trial_command(plan[t["n"] - 1], t["model"], t["measure"], t["variant"], a.port)
                envs = " ".join(f"{k}={shlex.quote(v)}" for k, v in env.items())
                print(f"   env {envs} {shlex.join(cmdv)}")
                if t["measure"] == "serve":
                    print(f"   + POST /v1/chat/completions x{len(PROMPTS)} (max_tokens 256, T=0) -> timings.predicted_per_second"
                          + (f", extra {plan[t['n'] - 1]['request_extra']}" if plan[t['n'] - 1].get('request_extra') else ""))
            print("   " + shlex.join(argv))
            print(f"   sleep {PAUSE_S}")
            todo = todo[len(blk):]
            continue
        if user_server_running():
            sys.exit("refusing: user's llama-server on port 8080 is running (pgrep -f 'llama-server.*--port 8080')")
        with open(blk_file, "w") as f:
            json.dump(blk, f)
        subprocess.run(argv)
        done = done_keys(results)
        before = len(todo)
        todo = [t for t in todo if trial_key(t) not in done]
        if len(todo) == before:
            sys.exit("block finished no trial (see the errors in the results file): stopping")
        if todo:
            time.sleep(PAUSE_S)


# ---------------------------------------------------------------------------------------------------------------
# revert builds
# ---------------------------------------------------------------------------------------------------------------
CMAKE_FLAGS = ["-DCMAKE_BUILD_TYPE=Release", "-DBUILD_SHARED_LIBS=ON", "-DGGML_HIP=ON", "-DGPU_TARGETS=gfx1100",
               "-DAMDGPU_TARGETS=gfx1100", "-DCMAKE_HIP_COMPILER=/opt/rocm/core-10.0/lib/llvm/bin/clang++",
               "-DCMAKE_PREFIX_PATH=/opt/rocm/core-10.0", "-DGGML_HIP_GRAPHS=ON", "-DGGML_HIP_NO_VMM=ON",
               "-DGGML_CUDA_FA_QUANTS=q4_0-q4_0;q8_0-q8_0;f16-f16;bf16-bf16", "-DGGML_NATIVE=ON",
               "-DLLAMA_BUILD_TESTS=OFF"]


def cmd_builds(a):
    plan = load_plan(a.out)
    blds = [e for e in plan if e["cat"] == "build" and e["active"]]
    clean = [e for e in blds if e["revert_clean"]]
    flags = " ".join(shlex.quote(x) for x in CMAKE_FLAGS)
    lines = ["#!/usr/bin/env bash",
             "# Revert builds for the LOO of the build-time patches (CPU only). One scratch worktree, incremental:",
             "# every step checks out HEAD, reverts one patch, rebuilds the touched files and copies bin + libs to",
             f"# {LOO_BINS}/<NN>; 'ref' is HEAD itself. Generated by loo.py builds; re-running skips finished ones.",
             "set -euo pipefail",
             f"src={LOO_SRC}; bins={LOO_BINS}; head={HEAD}",
             "J=${J:-4}",
             f"[ -d $src ] || git -C {REPO} worktree add --detach $src $head",
             f"[ -f $src/build/CMakeCache.txt ] || cmake -S $src -B $src/build {flags}",
             "build_one() {  # NAME SHA|-",
             "    local name=$1 sha=$2",
             "    [ -x $bins/$name/llama-server ] && { echo \"$name: done\"; return 0; }",
             "    git -C $src checkout -q -f $head && git -C $src reset -q --hard $head",
             "    if [ \"$sha\" != - ]; then",
             "        git -C $src revert --no-commit $sha || { git -C $src revert --abort || true; echo \"$name: REVERT CONFLICT\"; return 0; }",
             "    fi",
             "    flock -s /tmp/quiet.lock nice -n 10 cmake --build $src/build -j$J --target llama-server llama-bench llama-perplexity",
             "    mkdir -p $bins/$name.tmp && cp -a $src/build/bin/llama-server $src/build/bin/llama-bench \\",
             "        $src/build/bin/llama-perplexity $src/build/bin/*.so* $bins/$name.tmp/ && mv $bins/$name.tmp $bins/$name",
             "    git -C $src log -1 --format=%h > $bins/$name/HEAD; git -C $src diff --stat HEAD > $bins/$name/REVERTED",
             "    echo \"$name: built\"",
             "}",
             "build_one ref -"]
    for e in clean:
        lines.append(f"build_one {e['n']:02d} {e['sha']}   # {e['subject'][:80]}")
    conf = [e for e in blds if not e["revert_clean"]]
    if conf:
        lines.append("# revert conflicts (need a manual LOO port or group revert, see loo-plan.md):")
        for e in conf:
            lines.append(f"#   {e['n']:02d} {e['sha']} conflicts in {','.join(e['revert_conflicts'])}; "
                         f"later patches: {','.join(e['revert_blockers'])}")
    lines.append(f"git -C $src checkout -q -f $head")
    path = os.path.join(a.out, "loo-builds.sh")
    script = "\n".join(lines) + "\n"
    if a.dry_run:
        print(script)
        return
    with open(path, "w") as f:
        f.write(script)
    os.chmod(path, 0o755)
    print(f"wrote {path}: ref + {len(clean)} clean reverts, {len(conf)} conflicts listed")


# ---------------------------------------------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------------------------------------------
T975 = [12.706, 4.303, 3.182, 2.776, 2.571, 2.447, 2.365, 2.306, 2.262, 2.228, 2.201, 2.179, 2.160, 2.145, 2.131,
        2.120, 2.110, 2.101, 2.093, 2.086, 2.080, 2.074, 2.069, 2.064, 2.060, 2.056, 2.052, 2.048, 2.045, 2.042]


def tq(df):
    return T975[df - 1] if 1 <= df <= len(T975) else 1.96


def mean_ci(xs):
    n = len(xs)
    m = sum(xs) / n
    if n < 2:
        return m, float("nan")
    sd = math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1))
    return m, tq(n - 1) * sd / math.sqrt(n)


def cmd_report(a):
    plan = {e["n"]: e for e in load_plan(a.out)}
    res = {}
    with open(a.results) as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            if not r.get("ok"):
                continue
            res[r["key"]] = r  # last record of a key wins
    groups = {}
    for r in res.values():
        groups.setdefault((r["n"], r["model"], r["measure"]), {}).setdefault(r["round"], {})[r["variant"]] = r["value"]
    rows = ["| # | patch | model | measure | rounds | on t/s | off t/s | off vs on (paired, 95 % CI) | flag |",
            "|---|---|---|---|---|---|---|---|---|"]
    flagged = []
    for (n, model, measure), rounds in sorted(groups.items()):
        pairs = [(v["on"], v["off"]) for v in rounds.values() if "on" in v and "off" in v]
        if not pairs:
            continue
        on_m, on_ci = mean_ci([p[0] for p in pairs])
        off_m, off_ci = mean_ci([p[1] for p in pairs])
        d_m, d_ci = mean_ci([100.0 * (p[1] / p[0] - 1) for p in pairs])
        if math.isnan(d_ci):
            flag = "n<2"
        elif d_m - d_ci > 0:
            flag = "REMOVAL FASTER"
        elif d_m + d_ci >= 0:
            flag = "NEUTRAL"
        else:
            flag = "helps"
        if flag in ("REMOVAL FASTER", "NEUTRAL"):
            flagged.append((n, model, measure, flag, d_m, d_ci))
        rows.append(f"| {n:02d} | {plan[n]['subject'][:50]} | {model} | {measure} | {len(pairs)} | "
                    f"{on_m:.2f} ± {on_ci:.2f} | {off_m:.2f} ± {off_ci:.2f} | {d_m:+.2f} % ± {d_ci:.2f} | {flag} |")
    out = ["# LOO report", "", f"results: {a.results} ({len(res)} trials)", "",
           "off vs on = t/s with the patch removed relative to the full build, mean of the per-round (ABBA) paired "
           "ratios, Student t 95 % CI. NEUTRAL: CI contains 0; REMOVAL FASTER: CI above 0 (candidates to drop).", ""]
    out += rows + ["", "## Flagged (removal neutral or faster)", ""]
    out += [f"- {n:02d} {model} {measure}: {flag} ({d:+.2f} % ± {ci:.2f})" for n, model, measure, flag, d, ci in flagged] \
        or ["- none"]
    md = "\n".join(out) + "\n"
    path = a.report or os.path.join(a.out, "loo-report.md" if not a.results.endswith(".fake.jsonl") else
                                    "loo-report.fake.md")
    with open(path, "w") as f:
        f.write(md)
    print(md)
    print(f"wrote {path}")


def main():
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)  # `loo.py run --dry-run | head` ends quietly
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("cmd", choices=["plan", "run", "builds", "report", "_block"])
    p.add_argument("--repo", default=REPO)
    p.add_argument("--base", default=BASE)
    p.add_argument("--head", default=HEAD)
    p.add_argument("--out", default=OUT_DIR)
    p.add_argument("--results", default=None)
    p.add_argument("--report", default=None)
    p.add_argument("--rounds", type=int, default=4, help="rounds per (patch, model, measure); ABBA = 2 rounds")
    p.add_argument("--only", default="", help="patch numbers, comma separated")
    p.add_argument("--kind", default="env", choices=["env", "build", "all"], help="env includes the CLI switches")
    p.add_argument("--models", default="qwen,lfm")
    p.add_argument("--port", type=int, default=18440)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--fake", action="store_true", help="synthetic results (no GPU) to validate resume + report")
    p.add_argument("--block", default=None)
    a = p.parse_args()
    a.results = a.results or os.path.join(a.out, "loo-results.jsonl")
    {"plan": cmd_plan, "run": cmd_run, "builds": cmd_builds, "report": cmd_report, "_block": cmd_block}[a.cmd](a)


if __name__ == "__main__":
    main()
