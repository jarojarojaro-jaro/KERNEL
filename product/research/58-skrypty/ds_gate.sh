#!/bin/bash
# Report 58 gates (draft-sample: LLAMA_DFLASH_SAMPLE, LLAMA_DRAFT_CUMP). GPU queue only. On the s53d.sh pattern (report
# 53/56): fusion/greedy.sh setup (2 prompts, T=0, thinking off, 400 tok, -np 1, ctx 8192, KV q4_0, MTP n=4 + 64k draft
# vocab), env as topka (PM4 WA=2 GUARD, HSA_USE_SVM=0, lookup 3 W16, coupled, host-gap switches).
#   ds_gate.sh base     switches off: plain == c4708318, MTP == 6f14e814 (the build is the reference);
#                       LLAMA_DFLASH_SAMPLE=1: plain == c4708318, MTP == 6f14e814;
#                       LLAMA_DRAFT_CUMP=0.2: plain == c4708318                          -> md5/GATE_PASS
#   ds_gate.sh cump THR  CONFIG rule of the MTP draft-length change: CUMP=THR MTP r1 == r2 (deterministic),
#                       GPU_VERIFY=0 == =1, near-tie at the first token differing from 6f14e814 (nt_gap.py, report
#                       53; JSON in the log, judged in the report)                       -> md5/CUMP_<THR>.PASS
#   ds_gate.sh dflash   DFlash2 (Q4_K_M drafter, n=6) T=0: LLAMA_DFLASH_SAMPLE=1 == off (greedy: argmax path by
#                       construction); CUMP=0.2 r1 == r2, GPU_VERIFY=0 == =1, nt_gap vs off -> md5/DFLASH.PASS
set -uo pipefail
D=$HOME/qwen-opt/draft-sample; B=$D/inst/bin; o=$D/md5; mkdir -p $o
what=${1:?base|cump THR|dflash}
. "$D/ds_stop.sh"
ds_stop 8080 'llama-topka/bin/llama-server' || true
$HOME/qwen-opt/lookup/vram_ok.sh || exit 1
export GGML_HIP_PM4=1 GGML_HIP_PM4_WA=2 GGML_HIP_PM4_GUARD=1 HSA_USE_SVM=0 LLAMA_SPEC_LOOKUP=3 LLAMA_SPEC_LOOKUP_W=16 \
    LLAMA_SPEC_COUPLED=1 LLAMA_SERVER_YIELD_FAST=2 GGML_HIP_PM4_MIN_DISPATCH=16 GGML_HIP_PM4_LAZY_EXEC=1 PORT=18873
g() { taskset -c 2-5 $HOME/qwen-opt/fusion/greedy.sh $B $B "$@" qwen > /dev/null; }
m() { [ -s "$1" ] && md5sum < "$1" | cut -c1-8 || echo missing; }
rc=0; chk() { if [ "$2" = "$3" ]; then echo "PASS $1 ($2)"; else echo "FAIL $1 ($2 != $3)"; rc=1; fi; }
# nt_gap.py of two greedy outputs on a plain server (only when they differ; nt_gap needs a difference)
gap() {
    local a=$1 b=$2 pid
    [ "$(m $a)" = "$(m $b)" ] && { echo "nt_gap: ${a##*/} == ${b##*/}, nothing to compare"; return; }
    LD_LIBRARY_PATH=$B:/opt/rocm/core-10.0/lib $B/llama-server --port 18874 --host 127.0.0.1 -np 1 --no-webui \
        -m $HOME/models/Qwen3.8-27B-UD-Q4_K_XL.gguf -ngl 999 -fa on -ctk q4_0 -ctv q4_0 -c 8192 > $o/gap.server.log 2>&1 &
    pid=$!
    for _ in $(seq 180); do curl -sf http://127.0.0.1:18874/health > /dev/null && break; sleep 1; done
    for pi in 0 1; do
        $HOME/qwen-opt/.venv/bin/python $HOME/KERNEL/product/research/53-skrypty/nt_gap.py --port 18874 --prompt-index $pi $a $b \
            || echo "nt_gap failed (prompt $pi)"
    done
    ds_stop 18874 "llama-server --port 18874"
    wait $pid 2>/dev/null
}
# DFlash2 greedy run (greedy.sh setup with the run-llm.sh dflash drafter flags); env passes through
dflash() {
    local out=$1 pid
    LD_LIBRARY_PATH=$B:/opt/rocm/core-10.0/lib taskset -c 2-5 $B/llama-server --port 18875 --host 127.0.0.1 -np 1 --no-webui \
        -m $HOME/models/Qwen3.8-27B-UD-Q4_K_XL.gguf -ngl 999 -fa on -ctk q4_0 -ctv q4_0 -c 8192 \
        -md $HOME/models/draft/Qwen3.8-27B-DFlash2-Q4_K_M.gguf -ngld 99 --spec-type draft-dflash --spec-draft-n-max 6 \
        > $out.log 2>&1 &
    pid=$!
    for _ in $(seq 180); do curl -sf http://127.0.0.1:18875/health > /dev/null && break; sleep 1; done
    : > $out.txt
    for p in 'Explain how a hash map works, then implement one in C with open addressing.' \
             'Napisz krótkie opowiadanie o latarniku i sztormie.'; do
        curl -s http://127.0.0.1:18875/v1/chat/completions -H 'Content-Type: application/json' \
            -d "$(jq -n --arg p "$p" '{messages:[{role:"user",content:$p}],max_tokens:400,temperature:0,chat_template_kwargs:{enable_thinking:false}}')" \
            | jq -r '(.choices[0].message.reasoning_content // "") + (.choices[0].message.content // "")' >> $out.txt
    done
    ds_stop 18875 "llama-server --port 18875"
    wait $pid 2>/dev/null
}
case $what in
base)
    rm -f $o/GATE_PASS $o/off.* $o/smp.* $o/cp.*
    # (assignments before a function call are exported to its commands for that call)
    LLAMA_GPU_VERIFY=1 MODES="plain mtp" g $o/off
    LLAMA_GPU_VERIFY=1 LLAMA_DFLASH_SAMPLE=1 MODES="plain mtp" g $o/smp
    LLAMA_GPU_VERIFY=1 LLAMA_DRAFT_CUMP=0.2 MODES=plain g $o/cp
    chk "off: plain == c4708318" "$(m $o/off.plain.txt)" c4708318
    chk "off: MTP == 6f14e814" "$(m $o/off.mtp.txt)" 6f14e814
    chk "DFLASH_SAMPLE=1: plain == c4708318" "$(m $o/smp.plain.txt)" c4708318
    chk "DFLASH_SAMPLE=1: MTP == 6f14e814" "$(m $o/smp.mtp.txt)" 6f14e814
    chk "DRAFT_CUMP=0.2: plain == c4708318" "$(m $o/cp.plain.txt)" c4708318
    [ $rc = 0 ] && touch $o/GATE_PASS && echo "GATE PASS" || echo "GATE FAIL" ;;
cump)
    t=${2:?threshold}; rm -f $o/CUMP_$t.PASS $o/c$t-*
    [ -e $o/GATE_PASS ] || { echo "no GATE_PASS"; exit 1; }
    for r in r1 r2; do LLAMA_DRAFT_CUMP=$t LLAMA_GPU_VERIFY=1 MODES=mtp g $o/c$t-$r; done
    LLAMA_DRAFT_CUMP=$t LLAMA_GPU_VERIFY=0 MODES=mtp g $o/c$t-gv0
    echo "CUMP=$t MTP md5 $(m $o/c$t-r1.mtp.txt) (off 6f14e814)"
    grep -h "draft cutoff on the product" $o/c$t-r1.mtp.log | head -1
    grep -h "draft acceptance" $o/c$t-r1.mtp.log $o/off.mtp.log | tail -4
    chk "CUMP=$t: MTP r2 == r1 (determinism)" "$(m $o/c$t-r2.mtp.txt)" "$(m $o/c$t-r1.mtp.txt)"
    chk "CUMP=$t: GPU_VERIFY=0 == =1" "$(m $o/c$t-gv0.mtp.txt)" "$(m $o/c$t-r1.mtp.txt)"
    gap $o/off.mtp.txt $o/c$t-r1.mtp.txt
    # the near-tie judgement is read from the nt_gap JSON above (report 53 rule); the ABBA arms require this marker
    [ $rc = 0 ] && touch $o/CUMP_$t.PASS && echo "CUMP $t PASS" || echo "CUMP $t FAIL" ;;
dflash)
    rm -f $o/DFLASH.PASS $o/df-*
    [ -e $o/GATE_PASS ] || { echo "no GATE_PASS"; exit 1; }
    LLAMA_GPU_VERIFY=1 dflash $o/df-off
    LLAMA_GPU_VERIFY=1 LLAMA_DFLASH_SAMPLE=1 dflash $o/df-smp
    LLAMA_GPU_VERIFY=1 LLAMA_DFLASH_SAMPLE=1 LLAMA_DRAFT_CUMP=0.2 dflash $o/df-c1
    LLAMA_GPU_VERIFY=1 LLAMA_DFLASH_SAMPLE=1 LLAMA_DRAFT_CUMP=0.2 dflash $o/df-c2
    LLAMA_GPU_VERIFY=0 LLAMA_DFLASH_SAMPLE=1 LLAMA_DRAFT_CUMP=0.2 dflash $o/df-cgv0
    echo "DFlash2 T=0 md5: off $(m $o/df-off.txt), CUMP=0.2 $(m $o/df-c1.txt)"
    grep -h "draft acceptance" $o/df-off.log $o/df-c1.log | tail -4
    [ -s $o/df-off.txt ] && [ $(wc -c < $o/df-off.txt) -gt 500 ] || { echo "FAIL DFlash2 off produced no text"; rc=1; }
    chk "DFlash2: DFLASH_SAMPLE=1 == off (T=0)" "$(m $o/df-smp.txt)" "$(m $o/df-off.txt)"
    chk "DFlash2 CUMP=0.2: r2 == r1" "$(m $o/df-c2.txt)" "$(m $o/df-c1.txt)"
    chk "DFlash2 CUMP=0.2: GPU_VERIFY=0 == =1" "$(m $o/df-cgv0.txt)" "$(m $o/df-c1.txt)"
    gap $o/df-off.txt $o/df-c1.txt
    [ $rc = 0 ] && touch $o/DFLASH.PASS && echo "DFLASH PASS" || echo "DFLASH FAIL" ;;
*) echo "usage: ds_gate.sh base|cump THR|dflash" >&2; exit 2 ;;
esac
exit $rc
