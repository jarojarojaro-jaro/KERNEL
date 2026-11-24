#!/bin/bash
# K-138: Unsloth llama.cpp prebuild (b12651-mix-c7059d6, gfx110X, bundled ROCm 7 libs) vs our r14 on XTX. KV q4_0.
set -u
U=$HOME/k138; O=$HOME/wt/upstream-inkling/build-hip/bin
R14="GGML_HIP_INK_FUSE=1 GGML_HIP_INK_FUSE2=1 GGML_HIP_INK_FUSE3=1 GGML_HIP_INK_NOBLAS=1 GGML_HIP_INK_STABLE_GRAPH=1 GGML_HIP_INK_PLANAR_Q8=1 GGML_HIP_INK_F4_ROUTER=1 GGML_HIP_INK_F4_COMBINE=1 GGML_HIP_INK_F4_QKVCONV=1 GGML_HIP_INK_F4_LOOPMSG=1 GGML_HIP_INK_LOADFIRST=1 GGML_HIP_INK_NT=1"
MI=$HOME/models/inkling; D=$MI/dspark-Inkling-2-Mini-Q8_0.gguf; KV="-ctk q4_0 -ctv q4_0"
case ${1:-} in
  tg) for m in Inkling-2-Mini-Uncensored-AD-Q4_K Inkling-2-Mini-UD-Q4_K_XL; do
        echo "$m unsloth $(cd $U && LD_LIBRARY_PATH=$U ./llama-bench -m $MI/$m.gguf -p 0 -n 128 -fa 1 -ngl 99 $KV -r 3 2>&1 | grep tg128 | awk -F'|' '{print $(NF-1)}')"
        echo "$m ours-r14 $(env GGML_HIP_PM4=0 $R14 LD_LIBRARY_PATH=$O:/opt/rocm/core-10.0/lib $O/llama-bench -m $MI/$m.gguf -p 0 -n 128 -fa 1 -ngl 99 $KV -r 3 2>&1 | grep tg128 | awk -F'|' '{print $(NF-1)}')"
        echo "$m unsloth-pp2048 $(cd $U && LD_LIBRARY_PATH=$U ./llama-bench -m $MI/$m.gguf -p 2048 -n 0 -fa 1 -ngl 99 $KV -r 2 2>&1 | grep pp2048 | awk -F'|' '{print $(NF-1)}')"
      done ;;
  serve) for a in "unsloth-ds|$U|$U/llama-server|" "ours-ds|$O:/opt/rocm/core-10.0/lib|$O/llama-server|GGML_HIP_PM4=0 $R14"; do
      IFS='|' read name lib exe ev <<< "$a"
      env $ev LD_LIBRARY_PATH=$lib $exe -m $MI/Inkling-2-Mini-Uncensored-AD-Q4_K.gguf -md $D --spec-type draft-dspark --spec-draft-n-max 7 --spec-draft-sampling probabilistic $KV -ctkd q4_0 -ctvd q4_0 -ngl 99 -fa on -c 16384 --port 18794 --jinja > /tmp/k138-$name.log 2>&1 &
      pid=$!; for i in $(seq 180); do curl -fs localhost:18794/health >/dev/null && break; kill -0 $pid 2>/dev/null || break; sleep 1; done
      if curl -fs localhost:18794/health >/dev/null; then python3 ~/turbo-jobs/xbench.py 18794 ~/turbo/tests k138-$name | grep -E "Q1|Q4|Q6|L2048|L8192"; else echo "$name: did not start"; grep -iE "error| E " /tmp/k138-$name.log | head -3; fi
      kill -TERM $pid 2>/dev/null; for i in $(seq 60); do kill -0 $pid 2>/dev/null || break; sleep 1; done; kill -KILL $pid 2>/dev/null
      grep -E "draft acceptance" /tmp/k138-$name.log | tail -1 | cut -c30-200
    done ;;
esac
