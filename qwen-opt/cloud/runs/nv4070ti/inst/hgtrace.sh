#!/usr/bin/env bash
# ON the box: [TENV=..] hgtrace.sh <label> — T server with LLAMA_HOSTGAP_TRACE=1 (report every 256 steps), chat T=1
# en-code + pl-proza seed 1 (400 tok each) and mvs T=0 one prompt; the hostgap tables land in prof/<label>.server.log.
set -uo pipefail
. /root/cloud/lib4070.sh
lab=$1; P=$RES/prof; mkdir -p "$P"
TENV="LLAMA_HOSTGAP_TRACE=1 $TENV"
srv T "$P/$lab.server.log" || { say "server failed"; exit 1; }
(cd "$P" && $BC python3 $H/spec_sweep.py --label "hg.$lab" --port $PORT --temps 1.0 --seeds 1 --tokens 400) | cut -c1-200
srv_stop
grep -c "hostgap\[" "$P/$lab.server.log"
