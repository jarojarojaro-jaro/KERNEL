#!/usr/bin/env bash
# Step 2: test-backend-ops FLASH_ATTN_EXT (hsk=256, vs CPU) for every compiled variant -> res/tbo.txt ("VAR PASS|FAIL ...").
set -uo pipefail
. "$HOME/qwen-opt/fa-d256/common.sh"
[ -f "$D/BUILD_OK" ] || { echo "no BUILD_OK"; exit 1; }
: > "$D/res/tbo.txt"
for v in $VARS_ALL; do
    GGML_HIP_FA_D256_VAR=$v taskset -c 2-5 "$BIN/test-backend-ops" -o FLASH_ATTN_EXT -p 'hsk=256' -b ROCm0 > "$D/logs/tbo-$v.log" 2>&1
    rc=$?
    nfail=$(grep -c 'FAIL' "$D/logs/tbo-$v.log")
    passed=$(grep -oE '[0-9]+/[0-9]+ tests passed' "$D/logs/tbo-$v.log" | head -1)
    seen=$(grep -c "GGML_HIP_FA_D256_VAR=$v\b" "$D/logs/tbo-$v.log")
    st=PASS; { [ $rc != 0 ] || [ "$nfail" != 0 ] || [ -z "$passed" ]; } && st=FAIL
    [ "$v" != 0 ] && [ "$seen" = 0 ] && st=FAIL
    echo "$v $st rc=$rc fail_lines=$nfail $passed var_log=$seen" | tee -a "$D/res/tbo.txt"
done
