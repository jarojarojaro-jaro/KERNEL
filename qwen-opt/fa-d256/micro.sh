#!/usr/bin/env bash
# Step 3: kernel microbench, test-backend-ops perf FLASH_ATTN_EXT on the Qwen prompt shape (D 256, 4 KV heads, GQA 6,
# 512 tokens, KV q4_0 and f16 at 8k/32k/131k). Variants that passed the gate, in order S then reversed S (ABBA-like).
# -> res/micro.txt: "pass VAR type kv us_per_run TFLOPS"
set -uo pipefail
. "$HOME/qwen-opt/fa-d256/common.sh"
[ -f "$D/BUILD_OK" ] || { echo "no BUILD_OK"; exit 1; }
ok=$(awk '$2=="PASS"{print $1}' "$D/res/tbo.txt" | tr '\n' ' ')
echo "variants: $ok"
re='hsk=256,hsv=256,nh=4,nr23=\[6,1\],kv=(8192|32768|131072),nb=512,'
seq_fwd=$ok
seq_rev=$(echo $ok | tr ' ' '\n' | tac | tr '\n' ' ')
: > "$D/res/micro.txt"
pass=0
for v in $seq_fwd $seq_rev; do
    pass=$((pass + 1))
    GGML_HIP_FA_D256_VAR=$v taskset -c 2-5 "$BIN/test-backend-ops" perf -o FLASH_ATTN_EXT -p "$re" -b ROCm0 > "$D/logs/perf-$pass-$v.log" 2>&1
    python3 - "$D/logs/perf-$pass-$v.log" "$pass" "$v" >> "$D/res/micro.txt" <<'EOF'
import re, sys
log, p, v = sys.argv[1:4]
for line in open(log, errors="ignore"):
    m = re.search(r"kv=(\d+),.*type_K=(\w+),.*?(\d+) runs - +([\d.]+) us/run", line)
    if m:
        print(p, v, m.group(2), m.group(1), m.group(4))
EOF
done
cat "$D/res/micro.txt"
