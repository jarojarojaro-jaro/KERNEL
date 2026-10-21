#!/bin/sh
# report 53 CPU steps, each under its own cpuheavy --quiet (the GPU queue interleaves between steps)
P=$HOME/qwen-opt/mtp-train/.venv/bin/python; S=$HOME/KERNEL/product/research/53-skrypty/sl_head.py; R40=$HOME/KERNEL/product/research/40-skrypty
cd $HOME/qwen-opt/draft-shortlist
for i in 0 1 2 3 4 5 6 7; do cpuheavy --quiet $P $S eval --part $i/8 --threads 2 --cfgs init_ab.pt:1024,ridge_l300_t32.pt:1024,ridge_l300_t32.pt:256,ridge_l3000_t32.pt:256,ridge_l3000_t32.pt:1024; done
for d in ext_full ext_sl_*; do cpuheavy --quiet $P $R40/pa_offline.py --ext $d --data $HOME/qwen-opt/prose-accept/e0x --cats pl-prose,en-prose --out off_$d.json > off_$d.log 2>&1; done
cpuheavy --quiet $P $R40/pa_offline.py --ext $HOME/qwen-opt/prose-accept/ext_e0_base --data $HOME/qwen-opt/prose-accept/e0x --cats pl-prose,en-prose --out off_base64k.json > off_base64k.log 2>&1
