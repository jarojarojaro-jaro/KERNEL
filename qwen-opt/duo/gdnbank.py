#!/usr/bin/env python3
"""LLAMA_GDN_BANK 0 vs 1 sanity in the PRODUCTION config (xtxbench Server = run-topka.sh uncensored, duo build, test
port 18796). Per arm: chat greedy md5 (T=0, 256 tok), a ~3k-token prompt (multi-ubatch prefill + MTP rollback) md5,
an unrelated prompt (moves A into the --cache-ram prompt cache), then A again (state_read_data restore: r11 pend_l
plane_size fix) whose md5 must equal the first. Queue only. Usage: python3 gdnbank.py [arms, default "0 1"]"""
import os, sys
sys.path.insert(0, os.path.expanduser("~/qwen-opt/xtxbench"))
import xtxbench as xb  # noqa: E402

ROOT = os.path.expanduser("~/wt/l1-cachesave/build-hip")
if not xb.under_queue():
    sys.exit("REFUSED: outside ~/qwen-opt/queue/run-jobs.sh")
run = xb.Run("duo-gdnbank", "ab")
pid = xb.find_server_pid(8080)
if pid:
    xb.stop_pid(pid, run.log, ":8080")
summary = []
for arm in (sys.argv[1:] or ["0", "1"]):
    srv = xb.Server(run, xb.Arm(f"bank{arm}", ROOT, {"LLAMA_GDN_BANK": arm}, ["-lv", "4"], {}), f"bank{arm}", 18796)
    srv.start()
    try:
        log = "".join(open(f, errors="replace").read() for f in (srv.logfile, srv.out) if os.path.exists(f))
        bank_line = next((l.strip() for l in log.splitlines() if "delta-net state bank" in l), "bank line not logged")
        g_content, g_all = srv.greedy_md5()
        a = srv.tokenize("".join(f"Line {i:04d}: the quick brown fox jumps over the lazy dog number {i}.\n"
                                 for i in range(200)) + "\nWhich line number comes after Line 0150? Answer:", False)
        b = srv.tokenize("Write a haiku about autumn rain." * 40, False)
        r1 = srv.complete(a, 128)
        rb = srv.complete(b, 32)
        r2 = srv.complete(a, 128)
        line = (f"BANK={arm}: {bank_line} | greedy {g_content}/{g_all} | A {len(a)} tok md5 {r1['md5']} "
                f"prompt_ms {r1['prompt_ms']} | B md5 {rb['md5']} | A again cache_n {r2['cache_n']} prompt_n "
                f"{r2['prompt_n']} md5 {r2['md5']} restore_equal={r1['md5'] == r2['md5']} decode {r1['decode_tps']} t/s")
        run.log(line)
        summary.append((arm, g_all, r1["md5"], r2["md5"]))
    finally:
        srv.stop()
if len(summary) == 2:
    (_, g0, a0, _), (_, g1, a1, _) = summary
    run.log(f"BANK 0 vs 1: greedy equal={g0 == g1}, A equal={a0 == a1}")
