#!/usr/bin/env bash
# Greedy md5 parity of GGML_HIP_Q2BW knob sets vs the table's launch ("base") on one resident llama-server per mode
# (runtime switch file, production env of the bonsai25 profile): 3 prompts x 256 tokens at T=0, no prompt cache;
# mode plain (one-token decode) and mtp (one-token decode + the 2-3 column verify). Runs ON the box.
# usage: bw-md5.sh BUILD_BIN VARIANT...   VARIANT: NAME=VAL,NAME=VAL
set -uo pipefail
B=$1; shift
source ~/qwen-opt/perf-tools/profiles/bonsai25.env
SW=/tmp/bw-md5-switch.$$; PORT=18796; SP=
~/qwen-opt/l1tok/chat8080.sh stop
stop() { [ -n "$SP" ] || return 0; kill -TERM $SP 2>/dev/null; for _ in $(seq 15); do kill -0 $SP 2>/dev/null || break; sleep 1; done; kill -9 $SP 2>/dev/null; SP=; }
trap 'stop; rm -f $SW' EXIT
md5run() {
  for q in "Explain TCP congestion control." "Write a Python quicksort with tests." "Opowiedz o historii Krakowa."; do
    curl -s 127.0.0.1:$PORT/v1/chat/completions -d "{\"messages\":[{\"role\":\"user\",\"content\":\"$q\"}],\"temperature\":0,\"max_tokens\":256,\"cache_prompt\":false,\"chat_template_kwargs\":{\"enable_thinking\":false}}" \
      | python3 -c "import json,sys;print(json.load(sys.stdin)['choices'][0]['message']['content'])"
  done | md5sum | cut -c1-8
}
for mode in plain mtp; do
  : > $SW
  args=(); [ $mode = mtp ] && read -ra args <<< "$SPEC_ARGS"
  env $RUN_ENV GGML_HIP_RUNTIME_SWITCH_FILE=$SW LD_LIBRARY_PATH=$B:/opt/rocm/core-10.0/lib taskset -c 2-5 "$B/llama-server" \
    -m "$MODEL" $SRV_ARGS "${args[@]}" --port $PORT > /tmp/bw-md5-srv.log 2>&1 & SP=$!
  ok=0; for _ in $(seq 400); do curl -sf 127.0.0.1:$PORT/health >/dev/null && { ok=1; break; }; kill -0 $SP 2>/dev/null || break; sleep 1; done
  [ $ok = 1 ] || { echo "MD5 $mode: server failed"; tail -5 /tmp/bw-md5-srv.log; stop; continue; }
  md5run > /dev/null # warm-up
  for v in base "$@"; do
    if [ "$v" = base ]; then : > $SW; else echo "$v" | tr ',' '\n' > $SW; fi
    sleep 0.5
    echo "MD5 $mode [$v] $(md5run)"
  done
  stop
done
echo "gfxhub $(journalctl -k --since '-30min' --no-pager | grep -c gfxhub)"
