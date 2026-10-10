#!/usr/bin/env bash
# GPU power/thermal helper for the RX 7900 XTX (card0).
#
#   gpu-power.sh status          cap, power, clocks, temperatures, fan
#   gpu-power.sh monitor [FILE]  one line per second (Ctrl+C to stop); optional CSV log
#   gpu-power.sh cap WATTS       power cap, root (driver range here: 272-350 W, default 303 W)
#   gpu-power.sh eco             cap 272 W (lowest the driver allows without OverDrive), root
#   gpu-power.sh maxclk MHZ      max shader clock, root + OverDrive (amdgpu.ppfeaturemask=0xfff7ffff)
#   gpu-power.sh undervolt MV    shader voltage offset -MV, root + OverDrive
#   gpu-power.sh reset           driver defaults, root
#
# Settings are lost on reboot. Memory clock is never touched (it sets decode speed).
# Note: power1_* is the chip power the SMU limits (303 W default), not the 355 W total board power.
set -euo pipefail

dev=/sys/class/drm/card0/device
hw=$(echo $dev/hwmon/hwmon*)
od=$dev/pp_od_clk_voltage

w() { echo $(( $(cat "$1") / 1000000 )); }
c() { echo $(( $(cat "$1") / 1000 )); }
cur() { sed -n 's/^[0-9]*: \([0-9]*\)Mhz \*$/\1/p' "$1"; }

status() {
    echo "power cap : $(w $hw/power1_cap) W  (min $(w $hw/power1_cap_min), max $(w $hw/power1_cap_max), default $(w $hw/power1_cap_default))"
    echo "power now : $(w $hw/power1_average) W"
    echo "clocks    : shader $(cur $dev/pp_dpm_sclk) MHz, memory $(cur $dev/pp_dpm_mclk) MHz"
    echo "temps     : edge $(c $hw/temp1_input) C, junction $(c $hw/temp2_input) C (throttle $(c $hw/temp2_crit)), mem $(c $hw/temp3_input) C (throttle $(c $hw/temp3_crit))"
    echo "fan       : $(cat $hw/fan1_input) RPM (max $(cat $hw/fan1_max))"
    echo "overdrive : $([ -e $od ] && echo enabled || echo 'disabled (amdgpu.ppfeaturemask=0xfff7ffff to enable)')"
}

monitor() {
    local log=${1:-}
    [ -n "$log" ] && echo "time,power_w,cap_w,sclk_mhz,mclk_mhz,edge_c,junction_c,mem_c,fan_rpm" > "$log"
    printf '%-8s %5s %5s %6s %6s %5s %5s %5s %5s\n' time W cap sclk mclk edge junct mem fan
    while :; do
        local l
        l="$(date +%T),$(w $hw/power1_average),$(w $hw/power1_cap),$(cur $dev/pp_dpm_sclk),$(cur $dev/pp_dpm_mclk),$(c $hw/temp1_input),$(c $hw/temp2_input),$(c $hw/temp3_input),$(cat $hw/fan1_input)"
        printf '%-8s %5s %5s %6s %6s %5s %5s %5s %5s\n' ${l//,/ }
        [ -n "$log" ] && echo "$l" >> "$log"
        sleep 1
    done
}

need_root() { [ "$(id -u)" = 0 ] || { echo "run with sudo" >&2; exit 1; }; }
need_od() { [ -e $od ] || { echo "OverDrive disabled: add amdgpu.ppfeaturemask=0xfff7ffff to the kernel command line and reboot" >&2; exit 1; }; }

case ${1:-status} in
    status)    status ;;
    monitor)   monitor "${2:-}" ;;
    cap)       need_root; echo $(( ${2:?watts} * 1000000 )) > $hw/power1_cap; status ;;
    eco)       need_root; cat $hw/power1_cap_min > $hw/power1_cap; status ;;
    maxclk)    need_root; need_od; echo "s 1 ${2:?MHz}" > $od; echo c > $od; status ;;
    undervolt) need_root; need_od; echo "vo -${2:?mV}" > $od; echo c > $od; status ;;
    reset)     need_root; cat $hw/power1_cap_default > $hw/power1_cap
               [ -e $od ] && { echo r > $od; echo c > $od; }
               echo auto > $dev/power_dpm_force_performance_level; status ;;
    *) echo "usage: $0 status|monitor [FILE]|cap W|eco|maxclk MHZ|undervolt MV|reset" >&2; exit 2 ;;
esac
