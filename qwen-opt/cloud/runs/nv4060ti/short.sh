#!/usr/bin/env bash
cd /root
export C=32768 XBIN=/root/bin/TP XENV="LLAMA_SPEC_COUPLED=1 GGML_CUDA_GDN_MMA=1 GGML_CUDA_KVQ=1"
./nv.sh full T 1; ./nv.sh full X 1; ./nv.sh lb final T X; ./nv.sh full U1 1
./nv.sh gate gate.TP.gv1; XENV="$XENV LLAMA_GPU_VERIFY=0" ./nv.sh gate gate.TP.gv0
touch res/short.done
