#!/usr/bin/env bash
# Report 35 E7: KLD of Qwen3.6-35B-A3B UD-IQ4_XS vs Q8_0 (16e: upstream llama-perplexity -fa on -b 2048 -ub 1024;
# wiki.test.raw 100 x 512 as asked, plprose = PL text 20 x 2048 in place of the PL chat corpus), plus a --n-cpu-moe smoke of the IQ4_XS.
# Q8_0 (36.9 GB) does not fit 24 GB: experts of the first NCM layers stay in RAM. Run ONLY from the GPU queue.
set -uo pipefail
bd=$HOME/llama-master/build-hip/bin
export LD_LIBRARY_PATH="$bd:/opt/rocm/core-10.0/lib" GGML_HIP_PM4=0
m=$HOME/models/q36; o=/tmp/x35/e7; mkdir -p $o
pkill -f 'llama-topka/bin/llama-server' && sleep 5
"$HOME/qwen-opt/lookup/vram_ok.sh" || exit 1
declare -A C=([wiki]=$HOME/wt/lfm3-prof/wikitext-2-raw/wiki.test.raw [plprose]=$HOME/qwen-opt/hipfire/corp/plprose.txt)
declare -A A=([wiki]="-c 512 --chunks 100" [plprose]="-c 2048 --chunks 20")
for c in wiki plprose; do
    timeout 900 taskset -c 2-5 "$bd/llama-perplexity" -m $m/Qwen3.6-35B-A3B-Q8_0.gguf -f "${C[$c]}" ${A[$c]} \
        -fa on -b 2048 -ub 1024 -ngl 999 --n-cpu-moe ${NCM:-22} --kl-divergence-base $o/base-$c.bin > $o/base-$c.log 2>&1 || exit 1
    timeout 600 taskset -c 2-5 "$bd/llama-perplexity" -m $m/Qwen3.6-35B-A3B-UD-IQ4_XS.gguf ${A[$c]} \
        -fa on -b 2048 -ub 1024 -ngl 999 --kl-divergence-base $o/base-$c.bin --kl-divergence > $o/kld-$c.log 2>&1 || exit 1
    echo "== $c"; grep -E "Mean +KLD|Same top|Mean PPL\(Q\)|Mean PPL\(base\)|99.0%" $o/kld-$c.log
done
# smoke: 10 GB-class offload (report 33: 3080 --n-cpu-moe 28) on llama-bench
timeout 300 taskset -c 2-5 "$bd/llama-bench" -m $m/Qwen3.6-35B-A3B-UD-IQ4_XS.gguf -fa 1 -ctk q4_0 -ctv q4_0 -p 512 -n 128 \
    -r 2 -ngl 999 -ncmoe 0,21,28 -d 0,32768 2>&1 | grep -E "^\|" | tee $o/bench.log
