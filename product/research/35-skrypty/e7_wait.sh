#!/usr/bin/env bash
# waits for both E7 downloads (curl -C -), checks the sizes, renames .part and queues x35-e7.jobs
set -u; m=$HOME/models/q36
while pgrep -f "curl.*Qwen3.6-35B-A3B" >/dev/null; do sleep 30; done
s4=$(stat -c %s $m/Qwen3.6-35B-A3B-UD-IQ4_XS.gguf.part); s8=$(stat -c %s $m/Qwen3.6-35B-A3B-Q8_0.gguf.part)
echo "sizes $s4 $s8"; [ "$s4" = 17730509792 ] && [ "$s8" = 36903140320 ] || exit 1
mv $m/Qwen3.6-35B-A3B-UD-IQ4_XS.gguf.part $m/Qwen3.6-35B-A3B-UD-IQ4_XS.gguf
mv $m/Qwen3.6-35B-A3B-Q8_0.gguf.part $m/Qwen3.6-35B-A3B-Q8_0.gguf
date; "$HOME/qwen-opt/queue/run-jobs.sh" "$HOME/qwen-opt/queue/x35-e7.jobs"
