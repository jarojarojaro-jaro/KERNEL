import hashlib, json, os, subprocess, sys, time, urllib.request

BIN, R, MODEL, PORT = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
URL = f"http://127.0.0.1:{PORT}"

def http_post(path, payload):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(f"{URL}{path}", data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.loads(r.read().decode())

def wait_ready(proc):
    for _ in range(300):
        if proc.poll() is not None:
            raise RuntimeError(f"server exited early with {proc.returncode}")
        try:
            with urllib.request.urlopen(f"{URL}/health", timeout=2) as r:
                if json.loads(r.read().decode()).get("status") == "ok":
                    return
        except Exception:
            pass
        time.sleep(0.5)
    raise RuntimeError("server did not become ready")

def start_server(extra_env, log_path):
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = f"{BIN}:{R}:" + env.get("LD_LIBRARY_PATH", "")
    env["LLAMA_SERVER_AP_TIMING"] = "1"
    env.update(extra_env)
    cmd = [
        f"{BIN}/llama-server", "-m", MODEL, "--host", "127.0.0.1", "--port", str(PORT),
        "-c", "65536", "-np", "1", "-b", "2048", "-ub", "2048",
        "-fa", "on", "-ctk", "q4_0", "-ctv", "q4_0",
        "--cache-ram", "16384", "--ctx-checkpoints", "32",
    ]
    # Add your standard production MTP/PM4/FA flags here if desired:
    # e.g. extra_flags from K005_SRV_FLAGS env var
    extra = os.environ.get("K005_SRV_FLAGS", "").split()
    cmd.extend(extra)
    lf = open(log_path, "w")
    proc = subprocess.Popen(cmd, env=env, stdin=subprocess.DEVNULL, stdout=lf, stderr=subprocess.STDOUT)
    wait_ready(proc)
    return proc, lf

def run_req(prompt, cache_prompt=True, n_predict=64):
    t0 = time.monotonic()
    res = http_post("/completion", {
        "prompt": prompt,
        "n_predict": n_predict,
        "temperature": 0.0,
        "seed": 42,
        "cache_prompt": cache_prompt,
    })
    wall_s = time.monotonic() - t0
    txt = res.get("content", "")
    tm = res.get("timings", {})
    return {
        "cache_n": tm.get("cache_n", 0),
        "prompt_n": tm.get("prompt_n", 0),
        "prompt_ms": tm.get("prompt_ms", 0.0),
        "pred_ms": tm.get("predicted_ms", 0.0),
        "wall_s": wall_s,
        "md5": hashlib.md5(txt.encode()).hexdigest()[:12],
        "head": repr(txt[:60]),
    }

def build_prompts():
    # Build deterministic ~60k-token P1 and P2 sharing first 90% (~54k tokens) and differing in last 10% (~6k tokens)
    unit_a = "Record {:05d}: alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu.\n"
    unit_b = "Edited {:05d}: omega psi chi phi upsilon tau sigma rho pi omicron xi nu.\n"
    # Calibrate token count via /tokenize on the running server
    s1 = "".join(unit_a.format(i) for i in range(100))
    toks_per_100 = len(http_post("/tokenize", {"content": s1})["tokens"])
    n_lines_total = int(60000 * 100 / toks_per_100)
    n_lines_prefix = int(n_lines_total * 0.90)
    prefix = "".join(unit_a.format(i) for i in range(n_lines_prefix))
    tail_1 = "".join(unit_a.format(i) for i in range(n_lines_prefix, n_lines_total)) + "\nSummarize the final record number and words concisely:"
    tail_2 = "".join(unit_b.format(i) for i in range(n_lines_prefix, n_lines_total)) + "\nSummarize the final record number and words concisely:"
    p1 = prefix + tail_1
    p2 = prefix + tail_2
    t1 = len(http_post("/tokenize", {"content": p1})["tokens"])
    t2 = len(http_post("/tokenize", {"content": p2})["tokens"])
    tp = len(http_post("/tokenize", {"content": prefix})["tokens"])
    print(f"Prompts built: P1={t1} tok, P2={t2} tok, common_prefix={tp} tok ({100.0*tp/t2:.1f}%)")
    return p1, p2

results = {}
# Arm 1: Baseline (LLAMA_CKPT_GRID=0) -> P1 (warm) -> P2 (edit last 10%, expected full 60k recompute = cold ref!)
proc, lf = start_server({"LLAMA_CKPT_GRID": "0"}, "/tmp/k005_off.log")
try:
    p1, p2 = build_prompts()
    results["off_p1"] = run_req(p1, cache_prompt=True)
    results["off_p2_edit10"] = run_req(p2, cache_prompt=True)
    results["cold_p2"] = run_req(p2, cache_prompt=False)
finally:
    proc.terminate(); proc.wait(); lf.close()

# Arm 2: Grid ON (LLAMA_CKPT_GRID=8192, budget 4096 MiB, LLAMA_CKPT_VRAM=2) -> P1 -> P2 (edit 10%) -> fork branch
proc, lf = start_server({"LLAMA_CKPT_GRID": "8192", "LLAMA_CKPT_GRID_MIB": "4096", "LLAMA_CKPT_VRAM": "2"}, "/tmp/k005_on.log")
try:
    results["grid_p1"] = run_req(p1, cache_prompt=True)
    results["grid_p2_edit10"] = run_req(p2, cache_prompt=True)
    # Fork-point check: extend P2 by 500 tokens, then branch back to exact end of P2 with a different suffix
    p2_ext = p2 + "\n" + "Extension line for turn 2.\n" * 60 + "Answer:"
    p2_fork = p2 + "\nAlternative branch from P2 end. Answer:"
    results["grid_p2_ext"] = run_req(p2_ext, cache_prompt=True, n_predict=16)
    results["grid_p2_fork"] = run_req(p2_fork, cache_prompt=True, n_predict=16)
finally:
    proc.terminate(); proc.wait(); lf.close()

print("\n=== K-005 Summary ===")
for k, v in results.items():
    print(f"{k:16s} cache_n={v['cache_n']:6d} prompt_n={v['prompt_n']:6d} prompt_ms={v['prompt_ms']:8.1f} wall_s={v['wall_s']:6.2f} md5={v['md5']} {v['head']}")
print(f"\nEdit-10% md5 match vs cold: grid={results['grid_p2_edit10']['md5']} cold={results['cold_p2']['md5']} equal={results['grid_p2_edit10']['md5'] == results['cold_p2']['md5']}")
