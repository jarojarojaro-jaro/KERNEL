# xtx-od.sh: the ONE writer of the RX 7900 XTX (card0) OverDrive table. Sourced by /usr/local/sbin/xtx-eco and
# /usr/local/sbin/xtx-fan (both run as root). Installed root-owned at /usr/local/lib/xtx-od.sh by INSTALL.sh.
#
# Why (report 64 §3.2): on kernel 6.8 the fan curve, the clock limits and the rest of OD are ONE firmware table. Each
# commit uploads only the bits edited since the last upload, and PMFW resets every feature whose bit is clear. So
# `s 1 X; c` silently drops the fan curve, and a fan-curve commit silently drops the sclk cap, while sysfs still shows
# both (upstream fix 6027db7db773 / 44d0d3031e47, mainline v7.4-rc1, not in Ubuntu 6.8).
# Rule: every commit stages ALL 5 fan-curve points AND `s 1 <cap>`, then ONE `c`, under one lock. Never `r`, never
# acoustic_* / fan_minimum_pwm / fan_target_temperature / `m` / `vo`.
#
# State: /run/xtx-eco/cap = current sclk cap in MHz (missing = stock). /run is a tmpfs, so a reboot always returns to
# stock (report 64 §8). /run/xtx-fan.state = load|idle (written by xtx-fan).
XTX_DEV=/sys/class/drm/card0/device
XTX_OD=$XTX_DEV/pp_od_clk_voltage
XTX_FC=$XTX_DEV/gpu_od/fan_ctrl/fan_curve
XTX_HW=$(echo $XTX_DEV/hwmon/hwmon*)
XTX_STATE_DIR=/run/xtx-eco
XTX_CAP_F=$XTX_STATE_DIR/cap
XTX_FAN_STATE_F=/run/xtx-fan.state
XTX_LOCK=/run/lock/xtx-od.lock
# Stock max sclk = OD_SCLK 1 as the driver reports it at boot (2885 on 2026-11-05, 2935 after the 2026-11-06 boot:
# NOT a constant). Captured once per boot into /run (tmpfs) BEFORE any of our commits; a GPU reset restores the same
# boot table, and the "stock" arm/command must write exactly this value, never a guessed one.
XTX_STOCK_F=$XTX_STATE_DIR/stock
xtx_stock() {
    local s; s=$(cat "$XTX_STOCK_F" 2>/dev/null)
    if ! [[ $s =~ ^[0-9]+$ ]]; then
        s=$(sed -n '/^OD_SCLK:/,/^OD_MCLK:/s/^1: *\([0-9]*\)Mhz.*/\1/p' "$XTX_OD")
        [[ $s =~ ^[0-9]+$ ]] || { echo "xtx-od: cannot read OD_SCLK 1" >&2; return 1; }
        [ "$(id -u)" = 0 ] && echo "$s" > "$XTX_STOCK_F" 2>/dev/null
    fi
    echo "$s"
}
XTX_STOCK=$(xtx_stock) || XTX_STOCK=2885
XTX_FLOOR=1600      # below ~1800 MHz there is no efficiency gain (report 64 §9)
XTX_FAN=100         # % at every curve point while the GPU works (decision 2026-10-19)
XTX_TEMPS="25 40 50 65 80"
XTX_FAULT_RE='amdgpu.*(page fault|ring .* timeout|GPU reset begin|MES failed|MES might be|Failed to upload overdrive)'

xtx_log() { logger -t xtx-od "$*" 2>/dev/null; echo "xtx-od: $*" >&2; }

# current cap: the state file if it holds a valid value, else stock
xtx_cap() {
    local c; c=$(cat "$XTX_CAP_F" 2>/dev/null)
    if [[ $c =~ ^[0-9]+$ ]] && [ "$c" -ge "$XTX_FLOOR" ] && [ "$c" -le "$XTX_STOCK" ]; then echo "$c"; else echo "$XTX_STOCK"; fi
}
xtx_fan_state() { local s; s=$(cat "$XTX_FAN_STATE_F" 2>/dev/null); [ "$s" = idle ] && echo idle || echo load; }

# percentage of curve point with temperature $2 for state $1 (load = 100% everywhere; idle = 40% below 50 C)
xtx_pct() { if [ "$1" = load ]; then echo "$XTX_FAN"; elif [ "$2" -lt 50 ]; then echo 40; else echo "$XTX_FAN"; fi; }
# expected "point 0" line regex; point 0 is 25 C, or 26 C after a forced upload (xtx_apply ... force)
xtx_p0_re() { echo "^0: 2[56]C $(xtx_pct "$1" 25)%"; }
xtx_p0_temp() { sed -n 's/^0: \([0-9]*\)C .*/\1/p' "$XTX_FC" 2>/dev/null; }

# Unlocked body: stage the 5 points + s 1 <cap>, one commit. $1 = load|idle, $2 = force (toggle point 0 between 25 and
# 26 C so the table differs from the last upload: an identical table is never sent, report 64 §3.2 C).
_xtx_apply() {
    local state=$1 force=${2:-} cap t0=25 i=0 t
    cap=$(xtx_cap)
    if [ "$force" = force ]; then [ "$(xtx_p0_temp)" = 25 ] && t0=26; else t0=$(xtx_p0_temp); [ "$t0" = 26 ] || t0=25; fi
    for t in $XTX_TEMPS; do
        [ $i = 0 ] && t=$t0
        echo "$i $t $(xtx_pct "$state" "$t")" > "$XTX_FC" || return 1
        i=$((i + 1))
    done
    echo "s 1 $cap" > "$XTX_OD" || return 1
    echo c > "$XTX_FC" || return 1
    # driver-side readback (necessary, not sufficient: it is the driver's cache, not PMFW state)
    grep -q "^1: ${cap}Mhz" < <(sed -n '/^OD_SCLK:/,/^OD_MCLK:/p' "$XTX_OD") || { xtx_log "readback: OD_SCLK 1 != $cap"; return 1; }
    grep -qE "$(xtx_p0_re "$state")" "$XTX_FC" || { xtx_log "readback: fan_curve point 0 != $state"; return 1; }
    xtx_log "applied: fan $state, sclk cap $cap${force:+ (forced upload)}"
}
# xtx_apply load|idle [force]  — the only entry point; serialised between xtx-eco and the fan timer
xtx_apply() { ( flock -w 20 9 || { xtx_log "lock timeout"; exit 1; }; _xtx_apply "$@" ) 9> "$XTX_LOCK"; }

# 1 if the kernel log of this boot (since $1, default boot start) has an amdgpu fault/reset
xtx_gpu_faulted() {
    local since=${1:-}
    if [ -n "$since" ]; then journalctl -k --since "$since" --no-pager -o cat 2>/dev/null | grep -qE "$XTX_FAULT_RE"
    else journalctl -k -b 0 --no-pager -o cat 2>/dev/null | grep -qE "$XTX_FAULT_RE"; fi
}

xtx_sclk_now() { sed -n 's/^[0-9]*: \([0-9]*\)Mhz \*$/\1/p' "$XTX_DEV/pp_dpm_sclk"; }

# Physical check under load (report 64 §10.4). Collects up to $1 s (default 40) of samples with busy >= 90 %, needs
# >= 10 of them. Pass: median sclk <= cap + 50 MHz; the last 5 loaded samples have the fan on the 100 % curve
# (pwm1 >= 240 and fan1_input >= 3200 RPM), or are all 0 RPM with hotspot < 70 C (firmware zero-RPM).
# Returns 0 pass, 3 fail, 4 not enough load to judge. Prints one summary line.
xtx_verify() {
    local max=${1:-40} cap n=0 s b rpm pwm hot i sc=() rp=() pw=() ht=() med fan_ok=1 k
    cap=$(xtx_cap)
    for ((i = 0; i < max && n < 15; i++)); do
        b=$(cat "$XTX_DEV/gpu_busy_percent" 2>/dev/null || echo 0)
        if [ "$b" -ge 90 ]; then
            s=$(xtx_sclk_now); rpm=$(cat "$XTX_HW/fan1_input"); pwm=$(cat "$XTX_HW/pwm1"); hot=$(( $(cat "$XTX_HW/temp2_input") / 1000 ))
            sc+=("${s:-0}"); rp+=("$rpm"); pw+=("$pwm"); ht+=("$hot"); n=$((n + 1))
        fi
        sleep 1
    done
    if [ "$n" -lt 10 ]; then echo "verify: only $n loaded samples in ${max}s (cap $cap) -> cannot judge"; return 4; fi
    med=$(printf '%s\n' "${sc[@]}" | sort -n | awk '{a[NR]=$1} END{print a[int((NR+1)/2)]}')
    for ((k = n - 5; k < n; k++)); do
        if [ "${rp[k]}" -gt 0 ]; then { [ "${pw[k]}" -ge 240 ] && [ "${rp[k]}" -ge 3200 ]; } || fan_ok=0
        else [ "${ht[k]}" -lt 70 ] || fan_ok=0; fi
    done
    echo "verify: cap $cap, median sclk $med (n=$n), last rpm ${rp[n-1]} pwm ${pw[n-1]} hotspot ${ht[n-1]} C, fan_ok=$fan_ok"
    [ "$med" -le $((cap + 50)) ] && [ "$fan_ok" = 1 ] && return 0
    return 3
}
