#!/bin/bash
# Maya (Inkling 2 Mini, UD-Q4_K_XL, --drafting on) as the owner chat on :18796 (owner 2026-11-23 02:27 "odpal maye").
# Holds /tmp/gpu.lock (topka-keeper will not restart :8080 meanwhile), stops :8080, serves up to 12 h or until
# ~/k134/STOP-MAYA exists, then restores :8080. Stop now: touch ~/k134/STOP-MAYA
exec 8>>/tmp/gpu.lock; flock 8
rm -f ~/k134/STOP-MAYA
restore() { kill -TERM $SPID 2>/dev/null; for i in $(seq 60); do kill -0 $SPID 2>/dev/null || break; sleep 1; done; kill -KILL $SPID 2>/dev/null; pkill -KILL -P $SPID 2>/dev/null; kill $GPID 2>/dev/null; ~/qwen-opt/l1tok/chat8080.sh restore 8>&-; }
trap restore EXIT
~/qwen-opt/l1tok/chat8080.sh stop 8>&-
~/qwen-opt/tools/gpu-guard.sh > ~/k134/gpu-guard.out 2>&1 8>&- & GPID=$!
cd ~/k134/maya/src
# 2026-11-23: uncensored (IK2_ABLATE=AtomicChat LoRA as a runtime projection, maya-unsloth-ablate.json); stock was:
# LD_LIBRARY_PATH=/opt/rocm/core-10.0/lib taskset -c 2-5 ~/qwen-opt/mtp-train/.venv/bin/python serve/server.py --engine maya --config /home/jaro/k134/maya-unsloth-on.json --port 18796 --host 0.0.0.0 > ~/k134/mayaserve.log 2>&1 8>&- & SPID=$!
# 2026-11-24: AtomicChat AD-Q4_K natively (K-137: T=0.7 104.3 -> 113.2); previous: unsloth + IK2_ABLATE, config maya-unsloth-ablate.json
LD_LIBRARY_PATH=/opt/rocm/core-10.0/lib taskset -c 2-5 ~/qwen-opt/mtp-train/.venv/bin/python serve/server.py --engine maya --config /home/jaro/k134/maya-atomic.json --port 18796 --host 0.0.0.0 > ~/k134/mayaserve.log 2>&1 8>&- & SPID=$!
for i in $(seq 4320); do [ -f ~/k134/STOP-MAYA ] && break; kill -0 $SPID 2>/dev/null || break; sleep 10; done
