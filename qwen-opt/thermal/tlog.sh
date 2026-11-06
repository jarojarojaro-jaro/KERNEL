#!/bin/bash
# Passive thermal/power logger (read-only sysfs, no root): 1 line/s.
# time,gpu_w,cap_w,sclk,mclk,edge,junction,mem,fan_rpm,cpu_tctl,cpu_mhz_avg
d=/sys/class/drm/card0/device; g=/sys/class/hwmon/hwmon2; c=/sys/class/hwmon/hwmon1
cur() { sed -n 's/^[0-9]*: \([0-9]*\)Mhz \*$/\1/p' "$1"; }
out=${1:?csv}; [ -s "$out" ] || echo "time,gpu_w,cap_w,sclk,mclk,edge,junction,mem,fan_rpm,cpu_tctl,cpu_mhz" > "$out"
while :; do
  mhz=$(awk '{s+=$1;n++} END{printf "%d", s/n/1000}' /sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq)
  echo "$(date -u +%FT%T),$(( $(cat $g/power1_average)/1000000 )),$(( $(cat $g/power1_cap)/1000000 )),$(cur $d/pp_dpm_sclk),$(cur $d/pp_dpm_mclk),$(( $(cat $g/temp1_input)/1000 )),$(( $(cat $g/temp2_input)/1000 )),$(( $(cat $g/temp3_input)/1000 )),$(cat $g/fan1_input),$(( $(cat $c/temp1_input)/1000 )),$mhz" >> "$out"
  sleep 1
done
