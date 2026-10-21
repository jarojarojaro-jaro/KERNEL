#!/usr/bin/env bash
# R57g path A (NOT RUN; cloud spend and any weight transfer need the user's OK). Runs ON the build server
# (buildfarm.sh run '<this script> <phase>'), where HF downloads go over the data-centre link, never over our SIM.
# Only small results (logs, alloc numbers) come back by default; a candidate GGUF (~16 GB) comes home only if it
# passes the KLD gate AND the user approves the transfer.
#   phases: fetch | quant | kbase | kld | sum | all
#   prerequisites on the server: rbuild ~/wt/kld-ear llama-quantize llama-perplexity (same absolute paths),
#   ~/qwen-opt/quantalloc/alloc-*.txt and the two corpora copied (small).
set -euo pipefail
W=/root/work/quantalloc; M=$W/m; K=$W/kb; L=$W/logs; mkdir -p "$M" "$K" "$L"
B=/home/jaro/wt/kld-ear/build-hip/bin          # CPU code of this build runs fine without a GPU (-ngl 0)
Q=/home/jaro/qwen-opt/quantalloc
HF=https://huggingface.co/unsloth/Qwen3.8-27B-GGUF/resolve/main
BF=$M/Qwen3.8-27B-BF16-00001-of-00002.gguf
T=${THREADS:-22}
corp() { case $1 in plprose) echo $Q/corp/plprose.txt ;; code) echo $Q/corp/code.txt ;; esac; }
fetch() {
    for f in BF16/Qwen3.8-27B-BF16-00001-of-00002.gguf BF16/Qwen3.8-27B-BF16-00002-of-00002.gguf imatrix_unsloth.gguf \
             Qwen3.8-27B-UD-Q4_K_XL.gguf; do
        [ -s "$M/$(basename $f)" ] || curl -sfL -C - -o "$M/$(basename $f)" "$HF/$f"
    done
}
quant() {
    for c in qa1-iq4-1.0 qa2-q4k-1.0 qa3-iq4-1.5; do
        o=$M/Qwen3.8-27B-${c%%-*}.gguf; [ -s "$o" ] && continue
        nice -n 19 $B/llama-quantize --imatrix $M/imatrix_unsloth.gguf --tensor-type-file $Q/alloc-$c.txt \
            "$BF" "$o" Q4_K_M $T > $L/quant.$c.log 2>&1
        (cd $M && sha256sum "$(basename $o)" > "$(basename $o).sha256")
    done
}
kbase() {
    for c in plprose code; do
        [ -s $K/bf16-$c.bin ] || nice -n 19 $B/llama-perplexity -m "$BF" -f "$(corp $c)" -c 2048 --chunks 10 -t $T -ngl 0 \
            --kl-divergence-base $K/bf16-$c.bin > $L/kbase.$c.log 2>&1
    done
}
kld() {
    for arm in U4 qa1 qa2 qa3; do
        m=$M/Qwen3.8-27B-$arm.gguf; [ $arm = U4 ] && m=$M/Qwen3.8-27B-UD-Q4_K_XL.gguf
        for c in plprose code; do
            grep -qs 'Mean EAR' $L/kld.$arm.$c.log && continue
            nice -n 19 $B/llama-perplexity -m "$m" -f "$(corp $c)" -c 2048 --chunks 10 -t $T -ngl 0 \
                --kl-divergence-base $K/bf16-$c.bin --kl-divergence > $L/kld.$arm.$c.log 2>&1
        done
    done
}
sum() { mkdir -p $Q/logs; cp $L/kld.*.log $Q/logs/; cd $Q && python3 qa_sum.py gate; }
case ${1:-all} in fetch) fetch ;; quant) quant ;; kbase) kbase ;; kld) kld ;; sum) sum ;; all) fetch; quant; kbase; kld; sum ;; esac
