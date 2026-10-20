#!/usr/bin/env bash
# ON the box: after q1 (q1.done): config ABBAs of T on the same binary — draft depth n-max 3 and 5 vs 4, and the
# draft vocab 32768 vs 65536 (the 64k iq4_xs head is ~1.5 ms of each step's draft chain at 475 GB/s).
set -uo pipefail
R=/root/results/opt-4070ti-20261020
while [ ! -f $R/q1.done ]; do sleep 10; done
cd /root/cloud
XB="--spec-draft-n-max 3" ./ab.sh nmax3 "" ""
XB="--spec-draft-n-max 5" ./ab.sh nmax5 "" ""
XB="--spec-draft-vocab-n 32768" ./ab.sh dv32k "" ""
touch $R/q2.done
