#!/usr/bin/env bash
# resumable Q8_0 download: a fresh curl -C - per attempt (curl --retry reuses the first resume offset and truncated the
# file once, 23.7 GB -> 0), then the E7 queue
m=$HOME/models/q36; f=$m/Qwen3.6-35B-A3B-Q8_0.gguf; n=36903140320
u=https://huggingface.co/unsloth/Qwen3.6-35B-A3B-GGUF/resolve/main/Qwen3.6-35B-A3B-Q8_0.gguf
for _ in $(seq 200); do
    [ "$(stat -c %s $f.part 2>/dev/null || echo 0)" = $n ] && break
    nice -n 19 curl -sL -C - -o $f.part "$u"; sleep 5
done
[ "$(stat -c %s $f.part)" = $n ] || { echo "download incomplete"; exit 1; }
mv $f.part $f; date; "$HOME/qwen-opt/queue/run-jobs.sh" "$HOME/qwen-opt/queue/x35-e7.jobs"
