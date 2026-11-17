# hostguard.sh — sourced helper for Vast runners (owner rule 2026-11-17: only full-power cards).
#   hg_pick "<GPU name>" [extra vastai filters]   -> offer ids (cheapest first), machines from hosty-zle.txt skipped
#   hg_check <iid> <ssh_host> <ssh_port> <ssh opts...>  -> 0 = full power; else destroys the instance, appends its
#        machine_id to hosty-zle.txt and returns 1. Run right after SSH works, BEFORE downloading the model.
# Thresholds: power.limit >= 95% power.default_limit, clocks.max.mem >= 95% of karty.json mem_clock_mhz, idle temp < 80 C.
# Note: a host can still drop the memory clock only under load (3090 2026-11-17: max 9751, load 5001 MHz) — runners
# record smi.csv and summ.py flags medians < 95% as LIMITED; such results are lower bounds, not card numbers.
HG_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
HG_BAD=$HG_DIR/hosty-zle.txt
HG_KARTY=$HG_DIR/../skill-io/karty.json
export PATH=$HOME/.local/bin:$PATH

hg_bad_ids() { awk '!/^#/ && NF {print $1}' "$HG_BAD" 2>/dev/null | paste -sd, -; }

hg_pick() {
    local gpu=$1; shift
    local bad; bad=$(hg_bad_ids)
    vastai search offers "gpu_name=${gpu// /_} num_gpus=1 rentable=true verified=true reliability>0.97 inet_down>500 \
        inet_down_cost<=0.003 disk_space>=40 cuda_max_good>=12.8 direct_port_count>=1 $*" -o dph_total --raw |
        jq -r --arg bad ",$bad," '.[] | (.machine_id|tostring) as $m | select($bad | contains("," + $m + ",") | not) | .id'
}

hg_check() {
    local iid=$1 H=$2 P=$3; shift 3
    local q name pl pdl mm temp spec mid verdict=ok why=""
    q=$(ssh "$@" -p "$P" root@"$H" 'nvidia-smi --query-gpu=name,power.limit,power.default_limit,clocks.max.mem,temperature.gpu --format=csv,noheader,nounits' 2>/dev/null | tail -1)
    IFS=, read -r name pl pdl mm temp <<<"$q"
    name=$(sed 's/^ *NVIDIA GeForce //; s/ *$//' <<<"$name")
    spec=$(jq -r --arg n "$name" '.mem_clock_mhz[$n] // empty' "$HG_KARTY")
    awk -v a="$pl" -v b="$pdl" 'BEGIN { exit !(a + 0 >= 0.95 * b) }' || { verdict=bad; why+="power ${pl// }/${pdl// } W; "; }
    if [ -n "$spec" ]; then
        awk -v a="$mm" -v b="$spec" 'BEGIN { exit !(a + 0 >= 0.95 * b) }' || { verdict=bad; why+="mem ${mm// }/$spec MHz; "; }
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
