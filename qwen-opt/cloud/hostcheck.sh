#!/usr/bin/env bash
# Host gate for a Vast GPU box (SOP-DOBOR-I-POMIARY.md §5). Two modes:
#   hostcheck.sh offer <offer_id> <download_GB> <hours>   LOCAL, before renting: price incl. transfer, reliability, driver
#   hostcheck.sh box <hf_model_url> <model_GB>             ON THE BOX, first 5 minutes: power limit, PCIe, HF speed, disk, RAM
# Exit 0 = PASS, 1 = FAIL (destroy the box / skip the offer), 2 = usage. Every line prints PASS/FAIL/INFO.
# Thresholds (env): MAX_DL_COST (0.002 $/GB), MIN_REL (0.98), MIN_HF_MBS (25 MB/s), MIN_RAM_GB (24), MIN_DRIVER (570)
set -uo pipefail
mode=${1:-}; fail=0
ok()   { echo "PASS  $*"; }
bad()  { echo "FAIL  $*"; fail=1; }
info() { echo "INFO  $*"; }

case $mode in
offer)
    offer=${2:?offer id}; dl=${3:?download GB}; h=${4:?hours}
    . "$(dirname "$0")/lib.sh"
    oj=$(offer_json "$offer" 70) || true
    [ -n "$oj" ] || { echo "FAIL  offer $offer not found (rented or gone)"; exit 1; }
    read -r gpu rel dph store dlc ulc ver drv cuda pg pw down ram geo < <(jq -r '[(.gpu_name|gsub(" ";"_")), .reliability,
        .dph_base, .storage_cost, .inet_down_cost, .inet_up_cost, .verification, .driver_version, .cuda_max_good,
        .pci_gen, .gpu_lanes, (.inet_down|floor), (.cpu_ram/1000|floor), (.geolocation|gsub(" ";"_"))] | @tsv' <<<"$oj")
    info "offer $offer $gpu $geo, driver $drv (CUDA $cuda), PCIe ${pg}x$pw, down ${down} Mbit/s, RAM ${ram} GB"
    [ "$ver" = verified ] && ok "verified" || bad "not verified ($ver)"
    awk -v r="$rel" -v m="${MIN_REL:-0.98}" 'BEGIN{exit !(r>m)}' && ok "reliability $rel > ${MIN_REL:-0.98}" || bad "reliability $rel"
    awk -v c="$dlc" -v m="${MAX_DL_COST:-0.002}" 'BEGIN{exit !(c<=m)}' && ok "inet_down_cost \$$dlc/GB <= \$${MAX_DL_COST:-0.002}" \
        || bad "inet_down_cost \$$dlc/GB (x $dl GB = \$$(awk -v c="$dlc" -v g="$dl" 'BEGIN{printf "%.2f", c*g}'))"
    awk -v d="${drv%%.*}" -v m="${MIN_DRIVER:-570}" 'BEGIN{exit !(d>=m)}' && ok "driver $drv >= ${MIN_DRIVER:-570}" || bad "driver $drv < ${MIN_DRIVER:-570} (CUDA 12.8 falls back to CPU)"
    [ "${ram:-0}" -ge "${MIN_RAM_GB:-24}" ] && ok "host RAM $ram GB" || bad "host RAM $ram GB < ${MIN_RAM_GB:-24} (mmap + cache-ram)"
    [ "${pw:-0}" -ge 8 ] && ok "PCIe x$pw advertised" || info "PCIe x$pw advertised (x1 riser seen on 3060: GV=1 mandatory)"
    awk -v p="$dph" -v s="$store" -v c="$dlc" -v u="$ulc" -v g="$dl" -v h="$h" 'BEGIN {
        gpu=p*h; disk=s*70/730*h; tr=c*g+u*1; t=gpu+disk+tr;
        printf "INFO  cost %.1f h: GPU $%.3f + disk(70 GB) $%.3f + transfer $%.3f = $%.3f; x1.3 margin = $%.3f\n", h, gpu, disk, tr, t, t*1.3 }'
    ;;
box)
    url=${2:?hf url}; mgb=${3:?model GB}
    command -v nvidia-smi >/dev/null || { echo "FAIL  no nvidia-smi"; exit 1; }
    q=$(nvidia-smi -q -d POWER)
    cur=$(awk -F: '/Current Power Limit/{gsub(/[ W]/,"",$2); print $2; exit}' <<<"$q")
    def=$(awk -F: '/Default Power Limit/{gsub(/[ W]/,"",$2); print $2; exit}' <<<"$q")
    [ -n "$cur" ] && [ "$cur" = "$def" ] && ok "power limit $cur W == default $def W" || bad "power limit $cur W != default $def W -> DESTROY (3090 at 200 W: SM 405-480 MHz)"
    nvidia-smi --query-gpu=name,memory.total,driver_version,pcie.link.gen.max,pcie.link.width.max --format=csv,noheader | sed 's/^/INFO  gpu: /'
    # PCIe width under load: start a 10 s GPU-busy probe if a llama-bench binary exists, else report idle width
    w=$(nvidia-smi --query-gpu=pcie.link.width.current --format=csv,noheader,nounits | head -1)
    [ "${w:-0}" -ge 8 ] && ok "PCIe width now x$w" || info "PCIe width now x$w (idle reading; re-check under load; x1 => GV=1, note in report)"
    clk=$(nvidia-smi --query-gpu=clocks_event_reasons.active --format=csv,noheader 2>/dev/null | head -1)
    info "clock event reasons (idle): $clk"
    # HF speed: 1 GiB range of the real model file, single stream (what the staging download uses)
    r=$(curl -sL -r 0-1073741823 -o /dev/null -w '%{speed_download} %{http_code}' --max-time 120 "$url")
    mbs=$(awk -v s="${r%% *}" 'BEGIN{printf "%.1f", s/1e6}')
    awk -v s="$mbs" -v m="${MIN_HF_MBS:-25}" 'BEGIN{exit !(s>=m)}' && ok "HF download $mbs MB/s (1 GiB range, HTTP ${r##* })" \
        || bad "HF download $mbs MB/s < ${MIN_HF_MBS:-25} (model $mgb GB would take $(awk -v s="$mbs" -v g="$mgb" 'BEGIN{printf "%.0f", (s>0)? g*1000/s/60 : 9999}') min) -> DESTROY"
    free=$(df -BG --output=avail /root | tail -1 | tr -dc 0-9)
    need=$(awk -v g="$mgb" 'BEGIN{printf "%d", g+30}')
    [ "${free:-0}" -ge "$need" ] && ok "disk free ${free} GB >= model+30 = $need" || bad "disk free ${free} GB < $need"
    ram=$(awk '/MemTotal/{printf "%d", $2/1048576}' /proc/meminfo)
    [ "$ram" -ge "${MIN_RAM_GB:-24}" ] && ok "RAM $ram GB" || bad "RAM $ram GB"
    quota=$(cat /sys/fs/cgroup/cpu.max 2>/dev/null || cat /sys/fs/cgroup/cpu/cpu.cfs_quota_us 2>/dev/null)
    info "nproc $(nproc), cgroup cpu quota: $quota (bench -t = quota CPUs, taskset on one NUMA node/CCX)"
    ;;
*) sed -n 2,6p "$0"; exit 2 ;;
esac
[ $fail = 0 ] && echo "RESULT PASS" || echo "RESULT FAIL"
exit $fail
