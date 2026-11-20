#!/usr/bin/env python3
"""K-034: compute/KV/RS buffer sizes per context length from the production server log (start, read, stop). Queue only."""
import os, re, sys, glob
sys.path.insert(0, os.path.expanduser("~/qwen-opt/xtxbench"))
import xtxbench as xb  # noqa: E402
if not xb.under_queue():
    sys.exit("REFUSED: outside the queue")
run = xb.Run("k034", "bufs")
pid = xb.find_server_pid(8080)
if pid:
    xb.stop_pid(pid, run.log, ":8080")
for ctx in (65536, 131072, 262144):
    srv = xb.Server(run, xb.Arm(f"c{ctx}", xb.PROD, {}, ["-c", str(ctx), "-lv", "4"], {}), f"c{ctx}", 18794)
    srv.start()
    srv.stop()
    for f in glob.glob(os.path.join(run.dir, f"srv-c{ctx}.*")):
        for line in open(f, errors="replace"):
            if re.search(r"(buffer size)", line):
                run.log(f"c{ctx}: {line.strip()[-140:]}")
