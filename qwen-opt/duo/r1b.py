#!/usr/bin/env python3
"""Duo r1b: production config (xtxbench Arm = run-topka uncensored settings) from the duo build on a test port,
GGML_HIP_MMVQ_TURBO 0 vs 1 (ABAB), then xbench (no-think: copy tasks, T=0.7 story, long 2k/8k). Queue only."""
import os, subprocess, sys
sys.path.insert(0, os.path.expanduser("~/qwen-opt/xtxbench"))
import xtxbench as xb  # noqa: E402
ROOT = os.path.expanduser("~/wt/l1-cachesave/build-hip")
PORT = 18794
if not xb.under_queue():
    sys.exit("REFUSED: outside ~/qwen-opt/queue/run-jobs.sh")
run = xb.Run("duo-r1b", "turbo")
pid = xb.find_server_pid(8080)
if pid:
    xb.stop_pid(pid, run.log, ":8080")
for t in ("0", "1", "0", "1"):
    srv = xb.Server(run, xb.Arm(f"turbo{t}", ROOT, {"GGML_HIP_MMVQ_TURBO": t}, [], {}), f"t{t}", PORT)
    srv.start()
    try:
        out = subprocess.run(["python3", os.path.expanduser("~/turbo-jobs/xbench.py"), str(PORT),
                              os.path.expanduser("~/turbo/tests"), f"turbo{t}"], capture_output=True, text=True, timeout=900)
        for line in out.stdout.splitlines():
            run.log(line)
    finally:
        srv.stop()
