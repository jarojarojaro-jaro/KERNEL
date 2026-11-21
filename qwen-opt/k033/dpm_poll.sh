#!/usr/bin/env bash
# K-033: read-only poll of the XTX every 0.25 s while another queue job runs (0 extra GPU time). One line per sample:
#   epoch_s  sclk_MHz  mclk_MHz  fclk_MHz  gpu_busy_%  vram_used_MiB
# (active DPM level = the line with '*' in pp_dpm_{sclk,mclk,fclk}). Never writes sysfs. usage: dpm_poll.sh OUT (until killed)
d=/sys/class/drm/card0/device
act() { grep -m1 '\*' "$d/$1" | grep -o '[0-9]*Mhz' | tr -d Mhz; }
while :; do
    echo "$(date +%s.%N | cut -c1-14) $(act pp_dpm_sclk) $(act pp_dpm_mclk) $(act pp_dpm_fclk) $(cat $d/gpu_busy_percent)" \
         "$(( $(cat $d/mem_info_vram_used) / 1048576 ))"
    sleep 0.25
done >> "$1"
