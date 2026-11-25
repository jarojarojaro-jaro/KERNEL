#!/usr/bin/env bash
# Runs ON jaroserverai. One-command perf loop for a llama.cpp-family engine worktree vs a base worktree:
#   build (CPU, outside the GPU lock) -> spill audit vs base -> GPU queue: test-backend-ops, greedy md5 parity,
#   KLD 40x512, rocprof time ledger (us/token per kernel, delta to base), ABBA chat (xbench) + copy -> one summary.
# usage: perf-remote.sh PROFILE ENGINE_WT BASE_WT [--no-build] [--tag T]
set -uo pipefail
P=$1 E=$2 BW=$3; shift 3; BUILD=1; TAG=$(basename $E)
while [ $# -gt 0 ]; do case $1 in --no-build) BUILD=0; shift;; --tag) TAG=$2; shift 2;; *) shift;; esac; done
D=$(cd "$(dirname "$0")" && pwd); source "$D/profiles/$P.env"
R=$HOME/qwen-opt/perf/$TAG-$(date +%m%d-%H%M); mkdir -p $R; EB=$E/build-hip/bin; BB=$BW/build-hip/bin
log() { echo "$(date +%T) $*" | tee -a $R/summary.txt; }
log "perf $P engine=$E ($(git -C $E log --oneline -1 | cut -c1-60)) base=$BW ($(git -C $BW log --oneline -1 | cut -c1-60))"
if [ $BUILD = 1 ]; then
  t0=$(date +%s); HF_UI_VERSION=${HF_UI_VERSION:-b11647} nice -n 19 taskset -c 6-15 cmake --build $E/build-hip -j8 \
    --target llama-server llama-bench test-backend-ops llama-perplexity > $R/build.log 2>&1 || { log "BUILD FAILED"; tail -20 $R/build.log; exit 1; }
  log "build $(( $(date +%s) - t0 )) s"
fi
[ -s $R/../spill-$(basename $BW).tsv ] || $D/spill_audit.sh $BW/build-hip --out $R/../spill-$(basename $BW).tsv > /dev/null
$D/spill_audit.sh $E/build-hip --out $R/spill.tsv --base $R/../spill-$(basename $BW).tsv | tail -12 | tee -a $R/summary.txt
# GPU part: one jobs file through the queue (stop/restore :8080 handled by each job / last line)
cat > $R/gpu.sh <<EOS
#!/usr/bin/env bash
set -uo pipefail
source $D/profiles/$P.env; R=$R; EB=$EB; BB=$BB; PORT=18796
~/qwen-opt/l1tok/chat8080.sh stop
srv() { local B=\$1; shift; env $RUN_ENV LD_LIBRARY_PATH=\$B:/opt/rocm/core-10.0/lib taskset -c 2-5 \$B/llama-server -m \$MODEL \$SRV_ARGS --port \$PORT "\$@" > \$R/srv.log 2>&1 & SP=\$!
  for _ in \$(seq 400); do curl -sf 127.0.0.1:\$PORT/health >/dev/null && return 0; kill -0 \$SP 2>/dev/null || return 1; sleep 1; done; return 1; }
stop() { kill -TERM \$SP 2>/dev/null; for _ in \$(seq 15); do kill -0 \$SP 2>/dev/null || break; sleep 1; done; kill -9 \$SP 2>/dev/null; true; }
trap stop EXIT
echo "== test-backend-ops"
for f in \$TBO_FILTER; do o=\${f%%:*}; p=\${f#*:}; GGML_HIP_PM4=0 LD_LIBRARY_PATH=\$EB:/opt/rocm/core-10.0/lib taskset -c 2-5 timeout 200 \$EB/test-backend-ops -b ROCm0 -o \$o \${p:+-p \$p} 2>&1 | grep -E "tests passed|FAIL" | tail -1 | sed "s/^/TBO \$o \$p: /"; done
echo "== parity (greedy md5, 3 x 256 tok, no spec)"
for B in \$BB \$EB; do srv \$B || { echo "server failed \$B"; continue; }
  h=\$(for q in "Explain TCP congestion control." "Write a Python quicksort with tests." "Opowiedz o historii Krakowa."; do curl -s 127.0.0.1:\$PORT/v1/chat/completions -d "{\\"messages\\":[{\\"role\\":\\"user\\",\\"content\\":\\"\$q\\"}],\\"temperature\\":0,\\"max_tokens\\":256,\\"chat_template_kwargs\\":{\\"enable_thinking\\":false}}" | python3 -c "import json,sys;print(json.load(sys.stdin)['choices'][0]['message']['content'])"; done | md5sum | cut -c1-8)
  echo "MD5 \$(basename \$(dirname \$(dirname \$B))) \$h"; stop; done
echo "== KLD vs base (40 x 512)"
L=\$R/base.kld; GGML_HIP_PM4=0 LD_LIBRARY_PATH=\$BB:/opt/rocm/core-10.0/lib taskset -c 2-5 timeout 300 \$BB/llama-perplexity -m \$MODEL -ngl 999 -fa on -f \$CORPUS -c 512 --chunks 40 --kl-divergence-base \$L > /dev/null 2>&1
GGML_HIP_PM4=0 LD_LIBRARY_PATH=\$EB:/opt/rocm/core-10.0/lib taskset -c 2-5 timeout 300 \$EB/llama-perplexity -m \$MODEL -ngl 999 -fa on -f \$CORPUS -c 512 --chunks 40 --kl-divergence-base \$L --kl-divergence 2>&1 | grep -E "Mean    KLD|Maximum KLD|Same top p|Mean PPL\(Q\)/PPL" | sed "s/^/KLD /"
rm -f \$L
echo "== ledger (rocprofv3, llama-bench tg64, PM4 off)"
for B in \$BB \$EB; do n=\$(basename \$(dirname \$(dirname \$B))); mkdir -p \$R/prof-\$n; ( cd \$R/prof-\$n && GGML_HIP_PM4=0 LD_LIBRARY_PATH=\$B:/opt/rocm/core-10.0/lib taskset -c 2-5 timeout 250 /opt/rocm/core-10.0/bin/rocprofv3 --kernel-trace --stats --output-format csv -d . -o p -- \$B/llama-bench -m \$MODEL -ngl 999 -fa 1 -ctk q4_0 -ctv q4_0 -p 0 -n 64 -r 1 > bench.txt 2>&1 ); done
python3 $D/ledger.py \$(find \$R/prof-\$(basename $E) -name "*kernel_stats.csv" | head -1) 65 \$(find \$R/prof-\$(basename $BW) -name "*kernel_stats.csv" | head -1) 65 --top 20
echo "== ABBA chat (xbench) engine/base, PM4 + profile env"
for B in \$EB \$BB \$BB \$EB; do srv \$B \$SPEC_ARGS || { echo "server failed"; continue; }; n=\$(basename \$(dirname \$(dirname \$B)))
  taskset -c 2-5 timeout 500 python3 ~/turbo-jobs/xbench.py \$PORT ~/turbo/tests "\$n" | grep -E " Q1 | Q4 | Q6 |L2048|L8192" | sed "s/^/ABBA /"
  taskset -c 2-5 timeout 400 python3 ~/qwen-opt/lookup/copy_bench.py --label "\$n" --port \$PORT --set short --temps 0.0 --seeds 1 --tokens 512 --out \$R/copy.jsonl 2>&1 | grep -E "median" | cut -c1-80 | sed "s/^/COPY /"
  stop; done
echo "gfxhub \$(journalctl -k --since '-30min' --no-pager | grep -c gfxhub)"
EOS
chmod +x $R/gpu.sh
printf '%s\n' "# perf $TAG" "perf-$TAG|900|$R|$R/gpu.sh" "perf-$TAG-restore8080|400|~|~/qwen-opt/l1tok/chat8080.sh restore" > $R/perf.jobs
log "queued: $R/perf.jobs (results: ~/qwen-opt/queue/logs/perf-$TAG.log)"
echo "$R"
