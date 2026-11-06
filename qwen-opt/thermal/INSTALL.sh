#!/bin/bash
# INSTALL.sh — run ONCE by the user:  sudo ~/qwen-opt/thermal/INSTALL.sh
# Installs the report-64 OD fix (kernel 6.8: fan curve and sclk cap must go to the firmware in ONE commit):
#   /usr/local/lib/xtx-od.sh   shared writer (xtx_apply: 5 fan points + `s 1 <cap>` + one `c`, under a lock)
#   /usr/local/sbin/xtx-eco    the sclk cap tool (status | sclk MHZ 1600..2885 | stock | verify)
#   /usr/local/sbin/xtx-fan    fan.sh.new; xtx-fan.service is repointed to it (timer unchanged)
#   /etc/sudoers.d/xtx-eco     <user> may run exactly /usr/local/sbin/xtx-eco without a password (checked by visudo)
#   /etc/tmpfiles.d/xtx-eco.conf + /run/xtx-eco   state dir (tmpfs: a reboot always returns to stock)
# Backups of everything replaced: /var/backups/xtx-eco/<time>/ (UNINSTALL.sh restores the oldest = pre-install state).
# Does NOT write to the GPU: the restarted fan service only re-commits if the curve in sysfs differs from its state.
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "run with sudo" >&2; exit 1; }
user=${SUDO_USER:-jaro}
src=$(cd "$(dirname "$(readlink -f "$0")")" && pwd)
for f in xtx-od.sh xtx-eco fan.sh.new UNINSTALL.sh; do [ -f "$src/$f" ] || { echo "missing $src/$f" >&2; exit 1; }; bash -n "$src/$f"; done
[ -e /sys/class/drm/card0/device/gpu_od/fan_ctrl/fan_curve ] || { echo "overdrive off (amdgpu.ppfeaturemask)" >&2; exit 1; }

bk=/var/backups/xtx-eco/$(date -u +%Y%m%dT%H%M%S); mkdir -p "$bk"
for f in /etc/systemd/system/xtx-fan.service /etc/systemd/system/xtx-fan.timer /usr/local/sbin/xtx-eco /usr/local/sbin/xtx-fan \
         /usr/local/lib/xtx-od.sh /etc/sudoers.d/xtx-eco /etc/tmpfiles.d/xtx-eco.conf; do
    [ -e "$f" ] && cp -a --parents "$f" "$bk/"
done
old_exec=$(sed -n 's/^ExecStart=\([^ ]*\).*/\1/p' /etc/systemd/system/xtx-fan.service 2>/dev/null || true)
[ -n "$old_exec" ] && [ -f "$old_exec" ] && cp -a "$old_exec" "$bk/fan.sh.old"   # the user's ~/qwen-opt/tools/fan.sh stays untouched
echo "backup: $bk"

install -o root -g root -m 0644 "$src/xtx-od.sh" /usr/local/lib/xtx-od.sh
install -o root -g root -m 0755 "$src/xtx-eco"   /usr/local/sbin/xtx-eco
install -o root -g root -m 0755 "$src/fan.sh.new" /usr/local/sbin/xtx-fan
install -o root -g root -m 0755 "$src/UNINSTALL.sh" /usr/local/sbin/xtx-eco-uninstall
echo 'd /run/xtx-eco 0755 root root -' > /etc/tmpfiles.d/xtx-eco.conf
systemd-tmpfiles --create /etc/tmpfiles.d/xtx-eco.conf
# Stock max sclk of THIS boot (it changed 2885 -> 2935 between boots; 2026-11-06). Optional arg = the value printed
# at the first install of this boot, needed when an older xtx-fan already committed a hard-coded cap since boot.
stock=${1:-$(sed -n '/^OD_SCLK:/,/^OD_MCLK:/s/^1: *\([0-9]*\)Mhz.*/\1/p' /sys/class/drm/card0/device/pp_od_clk_voltage)}
[[ $stock =~ ^[0-9]+$ ]] && [ "$stock" -ge 2500 ] && [ "$stock" -le 3100 ] || { echo "bad stock sclk '$stock'" >&2; exit 1; }
echo "$stock" > /run/xtx-eco/stock; echo "stock sclk this boot: $stock MHz"

tmp=$(mktemp); trap 'rm -f "$tmp"' EXIT
echo "$user ALL=(root) NOPASSWD: /usr/local/sbin/xtx-eco" > "$tmp"
visudo -cf "$tmp" > /dev/null || { echo "sudoers rule rejected by visudo" >&2; exit 1; }
install -o root -g root -m 0440 "$tmp" /etc/sudoers.d/xtx-eco
visudo -c > /dev/null || { rm -f /etc/sudoers.d/xtx-eco; echo "visudo -c failed: rule removed" >&2; exit 1; }

cat > /etc/systemd/system/xtx-fan.service <<'EOF'
[Unit]
Description=RX 7900 XTX fan curve + sclk cap (one OD commit, report 64)
[Service]
Type=oneshot
ExecStart=/usr/local/sbin/xtx-fan max quiet
EOF
systemctl daemon-reload
systemctl restart --no-block xtx-fan.service

# validation (read-only)
sudo -u "$user" sudo -n /usr/local/sbin/xtx-eco status
systemctl cat xtx-fan.service | grep '^ExecStart='
systemctl is-active xtx-fan.timer
echo "installed. Next: bugcheck.sh through the GPU queue, then sweep.sh. Undo: sudo /usr/local/sbin/xtx-eco-uninstall"
