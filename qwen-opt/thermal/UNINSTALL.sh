#!/bin/bash
# UNINSTALL.sh — undo INSTALL.sh:  sudo ~/qwen-opt/thermal/UNINSTALL.sh   (also installed as /usr/local/sbin/xtx-eco-uninstall)
# 1. sclk back to stock through the new writer (curve + `s 1 2885` + one `c`), if it is still installed;
# 2. xtx-fan.service / .timer and any replaced file restored from the OLDEST /var/backups/xtx-eco/<time>/ (= the state
#    before the first install; later backups contain our own files)
#    (fallback: the unit as it was before, ExecStart=/home/jaro/qwen-opt/tools/fan.sh max quiet);
# 3. removes /usr/local/sbin/xtx-eco, xtx-fan, xtx-eco-uninstall, /usr/local/lib/xtx-od.sh, the sudoers rule,
#    the tmpfiles rule and /run/xtx-eco; checks sudoers with visudo.
# The old fan.sh re-applies its curve on its own (same curve values), so the fan keeps the 100 % policy.
set -uo pipefail
[ "$(id -u)" = 0 ] || { echo "run with sudo" >&2; exit 1; }
[ -x /usr/local/sbin/xtx-eco ] && [ -f /usr/local/lib/xtx-od.sh ] && { /usr/local/sbin/xtx-eco stock || echo "WARN: xtx-eco stock failed (a reboot restores stock)" >&2; }

bk=$(ls -1d /var/backups/xtx-eco/*/ 2>/dev/null | sort | head -1)
rm -f /usr/local/sbin/xtx-eco /usr/local/sbin/xtx-fan /usr/local/lib/xtx-od.sh /etc/sudoers.d/xtx-eco /etc/tmpfiles.d/xtx-eco.conf
rm -rf /run/xtx-eco
if [ -n "$bk" ]; then
    echo "restoring from $bk"
    ( cd "$bk" && find . -path ./fan.sh.old -prune -o -type f -print | while read -r f; do cp -a "$f" "/${f#./}"; done )
fi
if ! grep -q '^ExecStart=' /etc/systemd/system/xtx-fan.service 2>/dev/null || grep -q '/usr/local/sbin/xtx-fan' /etc/systemd/system/xtx-fan.service; then
    cat > /etc/systemd/system/xtx-fan.service <<'EOF'
[Unit]
Description=RX 7900 XTX fan curve (re-apply)
[Service]
Type=oneshot
ExecStart=/home/jaro/qwen-opt/tools/fan.sh max quiet
EOF
fi
visudo -c > /dev/null || echo "WARN: visudo -c reports a problem in sudoers (not from xtx-eco, its rule is removed)" >&2
systemctl daemon-reload
systemctl restart --no-block xtx-fan.service
rm -f /usr/local/sbin/xtx-eco-uninstall
systemctl cat xtx-fan.service | grep '^ExecStart='
echo "uninstalled"
