#!/bin/bash
# RX 7900 XTX fan control (RDNA3 overdrive; needs amdgpu.ppfeaturemask=0xfff7ffff).
# The systemd timer xtx-fan.timer (installed once with `sudo fan.sh install`) runs `fan.sh max quiet`
# as root every 30 s; that call follows the GPU load for ~28 s:
#   GPU working (busy >= 10%)        -> fan curve 95% at every temperature (~3300 RPM), immediately
#   GPU idle (< 10% for 20 s in a row) -> idle curve: 40% below 50 C, 95% from 50 C
# The curve is re-committed only on a state change, or when a GPU reset has wiped it.
# Manual (sudo): fan.sh max | fan.sh install | fan.sh auto (driver defaults, timer removed)
set -u
dev=/sys/class/drm/card0/device
od=$dev/gpu_od/fan_ctrl
hw=$(echo $dev/hwmon/hwmon*)
busy_f=$dev/gpu_busy_percent
arg=${1:-max}
quiet=${2:-}
FAN=90          # % ; measured: 95% -> ~3480 RPM, 44% -> ~1800 RPM, so 90% ≈ 3300 RPM
BUSY=10         # % GPU busy = "card is working" (idle reads 0–2%)
IDLE_HOLD=20    # s below BUSY before going back to the idle curve
state_f=/run/xtx-fan.state
[ "$(id -u)" = 0 ] || { echo "run with sudo"; exit 1; }
[ -e "$od/fan_curve" ] || { echo "overdrive off: add amdgpu.ppfeaturemask=0xfff7ffff to GRUB and reboot"; exit 2; }

# set_curve <load|idle>. SMU13 fan modes are exclusive (curve / acoustic / target temperature) and the
# last committed one wins, so only the curve is ever written.
set_curve() {
    local i=0 t s
    for t in 25 40 50 65 80; do
        if [ "$1" = load ]; then s=$FAN; else s=$(( t < 50 ? 40 : FAN )); fi
        echo "$i $t $s" > "$od/fan_curve" || return 1; i=$((i+1))
    done
    echo c > "$od/fan_curve" && echo "$1" > "$state_f"
    logger -t xtx-fan "fan curve: $1 (${FAN}%)"
}
# expected "point 0" line for a state; a GPU reset zeroes the curve, which this detects
p0() { [ "$1" = load ] && echo "0: 25C ${FAN}%" || echo "0: 25C 40%"; }
ensure() {
    local cur; cur=$(cat "$state_f" 2>/dev/null)
    if [ "$cur" != "$1" ] || ! grep -q "$(p0 "$1")" "$od/fan_curve"; then set_curve "$1"; fi
}

case "$arg" in
auto)
    echo r > "$od/fan_curve"; echo c > "$od/fan_curve"; rm -f "$state_f"
    systemctl disable --now xtx-fan.timer 2>/dev/null
    rm -f /etc/systemd/system/xtx-fan.service /etc/systemd/system/xtx-fan.timer; systemctl daemon-reload
    echo "fan: driver defaults, timer removed"; exit 0 ;;
install)
    cat > /etc/systemd/system/xtx-fan.service <<EOF
[Unit]
Description=RX 7900 XTX fan control (follows GPU load)
[Service]
Type=oneshot
ExecStart=$(readlink -f "$0") max quiet
EOF
    cat > /etc/systemd/system/xtx-fan.timer <<EOF
[Unit]
Description=RX 7900 XTX fan control every 30 s
[Timer]
OnBootSec=20
OnUnitActiveSec=30
AccuracySec=1
[Install]
WantedBy=timers.target
EOF
    systemctl daemon-reload && systemctl enable --now xtx-fan.timer && systemctl list-timers xtx-fan.timer --no-pager | head -3
    exit 0 ;;
esac

if [ -z "$quiet" ]; then   # manual call: full fan now
    set_curve load; sleep 3; sed -n 1,6p "$od/fan_curve"; echo "fan now $(cat $hw/fan1_input) RPM"; exit 0
fi

# timer call: follow the load for ~28 s, sampling every second
low=0
[ "$(cat $state_f 2>/dev/null)" = idle ] && low=$IDLE_HOLD
for _ in $(seq 28); do
    b=$(cat "$busy_f" 2>/dev/null || echo 100)
    if [ "$b" -ge "$BUSY" ]; then low=0; ensure load
    else
        low=$((low + 1))
        if [ "$low" -ge "$IDLE_HOLD" ]; then ensure idle; else ensure "$(cat $state_f 2>/dev/null || echo load)"; fi
    fi
    sleep 1
done
exit 0
