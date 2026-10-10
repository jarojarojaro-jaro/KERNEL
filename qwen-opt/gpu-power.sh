#!/usr/bin/env bash
# GPU power limiting for the RX 7900 XTX (card0). Needs root.
#
#   gpu-power.sh status          current cap, clocks, power, temperatures
#   gpu-power.sh cap WATTS       power cap (driver range on this card: 272-350 W, default 303 W)
#   gpu-power.sh sclk LEVEL      pin the shader clock DPM level: 2 = 2371 MHz, 1 = 2656 MHz (boost)
#   gpu-power.sh eco             272 W cap + shader clock pinned to 2371 MHz (target ~250 W)
#   gpu-power.sh reset           driver defaults (303 W, auto clocks)
#
# Settings are lost on reboot. Memory clock is never touched (it sets decode speed).
set -euo pipefail

dev=/sys/class/drm/card0/device
hw=$(echo $dev/hwmon/hwmon*)

status() {
    echo "power cap : $(( $(cat $hw/power1_cap) / 1000000 )) W  (min $(( $(cat $hw/power1_cap_min) / 1000000 )), max $(( $(cat $hw/power1_cap_max) / 1000000 )), default $(( $(cat $hw/power1_cap_default) / 1000000 )))"
    echo "power now : $(( $(cat $hw/power1_average) / 1000000 )) W"
    echo "perf level: $(cat $dev/power_dpm_force_performance_level)"
    echo "sclk      : $(tr '\n' ' ' < $dev/pp_dpm_sclk)"
    echo "mclk      : $(tr '\n' ' ' < $dev/pp_dpm_mclk)"
    for f in $hw/temp*_label; do echo "temp $(cat $f): $(( $(cat ${f%_label}_input) / 1000 )) C"; done
}

need_root() { [ "$(id -u)" = 0 ] || { echo "run with sudo" >&2; exit 1; }; }

case ${1:-status} in
    status) status ;;
    cap)    need_root; echo $(( ${2:?watts} * 1000000 )) > $hw/power1_cap; status ;;
    sclk)   need_root; echo manual > $dev/power_dpm_force_performance_level; echo "${2:?level}" > $dev/pp_dpm_sclk; status ;;
    eco)    need_root; echo 272000000 > $hw/power1_cap
            echo manual > $dev/power_dpm_force_performance_level; echo 2 > $dev/pp_dpm_sclk; status ;;
    reset)  need_root; cat $hw/power1_cap_default > $hw/power1_cap
            echo auto > $dev/power_dpm_force_performance_level; status ;;
    *) echo "usage: $0 status|cap W|sclk LEVEL|eco|reset" >&2; exit 2 ;;
esac
