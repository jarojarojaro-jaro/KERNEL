# hostguard.sh — sourced helper for Vast runners (owner rule 2026-11-17: only full-power cards).
#   hg_pick "<GPU name>" [extra vastai filters]   -> offer ids (cheapest first), machines from hosty-zle.txt skipped
#   hg_check <iid> <ssh_host> <ssh_port> <ssh opts...>  -> 0 = full power; else destroys the instance, appends its
#        machine_id to hosty-zle.txt and returns 1. Run right after SSH works, BEFORE downloading the model.
# Thresholds: power.limit >= 85% power.default_limit, clocks.max.mem >= 85% of karty.json mem_clock_mhz, idle temp < 80 C.
# Note: a host can still drop the memory clock only under load (3090 2026-11-17: max 9751, load 5001 MHz) — runners
# record smi.csv and summ.py flags medians < 85% as LIMITED; such results are lower bounds, not card numbers.
HG_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
HG_BAD=$HG_DIR/hosty-zle.txt
HG_KARTY=$HG_DIR/../skill-io/karty.json
export PATH=$HOME/.local/bin:$PATH

hg_bad_ids() { awk '!/^#/ && NF {print $1}' "$HG_BAD" 2>/dev/null | paste -sd, -; }

HG_MAX_DL=${MAX_DL_COST_PER_GB:-0.002}   # $/GB, same default as up.sh
hg_pick() {
    local gpu=$1; shift
    local bad; bad=$(hg_bad_ids)
    vastai search offers "gpu_name=${gpu// /_} num_gpus=1 rentable=true verified=true reliability>0.97 inet_down>500 \
        inet_down_cost<=$HG_MAX_DL disk_space>=40 cuda_max_good>=12.8 direct_port_count>=1 $*" -o dph_total --raw |
        jq -r --arg bad ",$bad," '.[] | (.machine_id|tostring) as $m | select($bad | contains("," + $m + ",") | not) | .id'
}

# hg_offer_ok <offer_id> [download_GB]: the same gate as up.sh for an offer chosen by id — download price <= HG_MAX_DL
# $/GB (lekcja-vast-transfer-kosztuje, AGENTS.md 2026-10-20: cost = GPU + disk + TRANSFER) and machine not in
# hosty-zle.txt. Prints the offer and the estimate for 1 h; returns 1 (and says why) otherwise.
hg_offer_ok() {
    local offer=$1 gb=${2:-11} oj
    oj=$(curl -fsS -X POST https://console.vast.ai/api/v0/bundles/ -H 'Content-Type: application/json' \
        -d "{\"ask_contract_id\":{\"eq\":$offer},\"type\":\"on-demand\",\"allocated_storage\":30}" | jq '.offers[0] // empty')
    [ -n "$oj" ] || { echo "offer $offer not found: cannot check its transfer price; refusing" >&2; return 1; }
    jq -r --argjson g "$gb" '"offer \(.id) machine \(.machine_id): \(.gpu_name), $\(.dph_total*1000|round/1000)/h, download $\(.inet_down_cost)/GB, 1 h + \($g) GB ≈ $\((.dph_total + .inet_down_cost*$g)*100|round/100)"' <<<"$oj"
    awk -v c="$(jq -r .inet_down_cost <<<"$oj")" -v m="$HG_MAX_DL" 'BEGIN { exit !(c <= m) }' \
        || { echo "offer $offer charges more than \$$HG_MAX_DL/GB download; refusing (pick another or get approval)" >&2; return 1; }
    grep -qx "$(jq -r .machine_id <<<"$oj")" <(awk '!/^#/ && NF {print $1}' "$HG_BAD") \
        && { echo "offer $offer is on a machine in hosty-zle.txt; refusing" >&2; return 1; }
    return 0
}

hg_check() {
    local iid=$1 H=$2 P=$3; shift 3
    local q name pl pdl mm temp spec mid verdict=ok why=""
    q=$(ssh "$@" -p "$P" root@"$H" 'nvidia-smi --query-gpu=name,power.limit,power.default_limit,clocks.max.mem,temperature.gpu --format=csv,noheader,nounits' 2>/dev/null | tail -1)
    IFS=, read -r name pl pdl mm temp <<<"$q"
    name=$(sed 's/^ *NVIDIA GeForce //; s/ *$//' <<<"$name")
    spec=$(jq -r --arg n "$name" '.mem_clock_mhz[$n] // empty' "$HG_KARTY")
    awk -v a="$pl" -v b="$pdl" 'BEGIN { exit !(a + 0 >= 0.85 * b) }' || { verdict=bad; why+="power ${pl// }/${pdl// } W; "; }
    if [ -n "$spec" ]; then
        awk -v a="$mm" -v b="$spec" 'BEGIN { exit !(a + 0 >= 0.85 * b) }' || { verdict=bad; why+="mem ${mm// }/$spec MHz; "; }
    else why+="(no mem spec for '$name' in karty.json) "; fi
    [ "${temp// }" -lt 80 ] 2>/dev/null || { verdict=bad; why+="idle ${temp// } C; "; }
    [ -n "$q" ] || { verdict=bad; why="nvidia-smi unreadable"; }
    echo "hostguard $iid: $name power ${pl// }/${pdl// } W, mem max ${mm// }/${spec:-?} MHz, ${temp// } C -> $verdict $why"
    [ $verdict = ok ] && return 0
    mid=$(vastai show instance "$iid" --raw 2>/dev/null | jq -r '.machine_id // empty')
    vastai destroy instance "$iid" -y > /dev/null
    [ -n "$mid" ] && printf '%s\t%s\t%s\t%s\n' "$mid" "$(date +%F)" "$name" "hostguard: ${why% }" >> "$HG_BAD"
    return 1
}
