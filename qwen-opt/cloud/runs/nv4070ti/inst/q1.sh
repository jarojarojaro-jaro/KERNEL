#!/usr/bin/env bash
# ON the box: after fin4070 (main.done): md5 gate of T as is (gate "base"), then short ABBAs of the existing switches
# with the same binary: LLAMA_SERVER_YIELD_FAST=2 (host-gap, report 24o) and LLAMA_SPEC_COUPLED=1 (report 24p).
set -uo pipefail
R=/root/results/opt-4070ti-20261020
while [ ! -f $R/main.done ]; do sleep 10; done
cd /root/cloud
./gate.sh base
./ab.sh yfast "" "LLAMA_SERVER_YIELD_FAST=2"
./ab.sh coupled "" "LLAMA_SPEC_COUPLED=1"
TENV="LLAMA_SERVER_YIELD_FAST=2" ./gate.sh yfast
touch $R/q1.done
