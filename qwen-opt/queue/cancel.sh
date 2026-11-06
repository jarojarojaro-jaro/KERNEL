#!/bin/bash
# Cancel one queued/running jobs file safely: stops the run-jobs.sh process AND its whole descendant tree.
# Root cause of the 04:07 / 12:46 SQC page faults (report 55): a SECOND SIGTERM makes llama-server call exit() inside
# its signal handler while a PM4 tape still runs. The arm scripts' EXIT traps already send the server one SIGTERM,
# so cancel.sh NEVER signals a server itself with TERM: it stops the clients/wrappers (their traps stop the server
# once), waits up to 90 s, and only if the server is still alive uses SIGKILL (no handler runs, no exit()).
#   cancel.sh <jobs-file-substring>
set -u
pat=${1:?jobs file name or substring}
desc() { local c; for c in $(pgrep -P "$1"); do desc "$c"; echo "$c"; done; }
alive() { local p; for p in "$@"; do kill -0 "$p" 2>/dev/null && return 0; done; return 1; }
is_server() { tr '\0' ' ' < "/proc/$1/cmdline" 2>/dev/null | grep -q 'bin/llama-server'; }
for p in $(pgrep -f "run-jobs.sh .*${pat}"); do
    kids=$(desc "$p"); servers=""; others=""
    for k in $kids; do if is_server "$k"; then servers+=" $k"; else others+=" $k"; fi; done
    echo "cancel: run-jobs $p, servers:${servers:- none}, other descendants: $(echo $others | wc -w)"
    kill -STOP "$p" 2>/dev/null
    # 1) clients and wrappers first (benchmark scripts stop sending requests); keep the servers alive
    for k in $others; do kill -0 "$k" 2>/dev/null && ! tr '\0' ' ' < "/proc/$k/cmdline" 2>/dev/null | grep -q run-topka && kill -TERM "$k" 2>/dev/null; done
    # 2) the wrappers' EXIT traps stop their servers with ONE SIGTERM; never add a second one here (report 55)
    for _ in $(seq 90); do alive $servers || break; sleep 1; done
    alive $servers && { echo "cancel: server still alive after 90 s, SIGKILL (no second SIGTERM)"; kill -KILL $servers 2>/dev/null; }
    kill -KILL $others 2>/dev/null
    kill -TERM "$p" 2>/dev/null; kill -CONT "$p" 2>/dev/null
done
pgrep -af "run-jobs.sh .*${pat}" | grep -v pgrep || echo "cancel: done"
