#!/usr/bin/env bash
# R57g EAR check on CPU (tiny model): old (topka-int cf927413b) vs new (kld-ear) llama-perplexity.
#  1) base logits from both binaries -> identical bytes;  2) KLD vs a requantized model: every old output line identical,
#  new adds only "Mean EAR";  3) identical model vs its own base -> EAR ~ 100 %.
set -euo pipefail
cd ~/qwen-opt/quantalloc; mkdir -p eartest; cd eartest
OLD=~/wt/kld-ear-base/build-cpu/bin/llama-perplexity; NEW=~/wt/kld-ear/build-cpu/bin/llama-perplexity
QZ=~/wt/kld-ear/build-cpu/bin/llama-quantize
M=~/models/lfm/LFM2.5-2.6B-QAD-Q4_0.gguf
head -c 60000 ../corp/plprose.txt > corp.txt
[ -s m2.gguf ] || cpuheavy $QZ --allow-requantize "$M" m2.gguf Q3_K_M 2 > quant.log 2>&1
A=(-f corp.txt -c 512 --chunks 8 -t 2 -ngl 0)
cpuheavy $OLD -m "$M" "${A[@]}" --kl-divergence-base base.old.bin > base.old.log 2>&1
cpuheavy $NEW -m "$M" "${A[@]}" --kl-divergence-base base.new.bin > base.new.log 2>&1
cmp base.old.bin base.new.bin && echo "BASE identical: $(md5sum < base.old.bin)"
cpuheavy $OLD -m m2.gguf "${A[@]}" --kl-divergence-base base.old.bin --kl-divergence > kld.old.log 2>&1
cpuheavy $NEW -m m2.gguf "${A[@]}" --kl-divergence-base base.old.bin --kl-divergence > kld.new.log 2>&1
cpuheavy $NEW -m "$M" "${A[@]}" --kl-divergence-base base.old.bin --kl-divergence > kld.self.log 2>&1
filt() { sed -n '/^chunk /,$p' "$1" | grep -v -E 'Mean EAR|llama_perf|load time|eval time|total time|graphs reused|memory_breakdown|^llama_memory|^\s*$'; }
diff <(filt kld.old.log) <(filt kld.new.log) && echo "KLD/top/Δp output identical (old vs new)"
grep -E 'Mean    KLD|Same top p|Mean EAR' kld.new.log
echo "-- self (identical logits):"; grep -E 'Mean    KLD|Same top p|Mean EAR' kld.self.log
