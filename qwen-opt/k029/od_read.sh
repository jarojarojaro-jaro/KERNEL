#!/usr/bin/env bash
# K-029: read-only check of the per-boot factory OD_SCLK capture and the fan curve (no sysfs writes).
D=$(for c in /sys/class/drm/card*/device; do [ -e "$c/pp_od_clk_voltage" ] && echo "$c"; done | head -1)
H=$(ls -d "$D"/hwmon/hwmon* | head -1)
echo "boot: $(uptime -s)"
echo "/run/xtx-eco/stock (captured at boot): $(cat /run/xtx-eco/stock 2>&1)"
echo "/run/xtx-eco/cap: $(cat /run/xtx-eco/cap 2>&1)"
echo "== pp_od_clk_voltage"; cat "$D/pp_od_clk_voltage"
echo "== pp_dpm_sclk"; cat "$D/pp_dpm_sclk"
for x in pwm1 pwm1_enable fan1_input temp1_input temp2_input temp3_input power1_cap power1_average; do echo "$x=$(cat "$H/$x" 2>/dev/null)"; done
echo "== fan_curve"; cat "$D/gpu_od/fan_ctrl/fan_curve" 2>&1
echo "== xtx-eco status"; xtx-eco status 2>&1 | head -20
echo "== xtx-eco log (stock lines)"; journalctl -b 0 --no-pager 2>/dev/null | grep -i 'xtx' | grep -i 'stock' | tail -5
