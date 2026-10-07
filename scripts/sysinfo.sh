#!/usr/bin/env bash
# Zbiera informacje o systemie potrzebne do benchmarków (tylko odczyt, nic nie zmienia).
# Użycie: bash scripts/sysinfo.sh > sysinfo.txt

section() { printf '\n===== %s =====\n' "$1"; }
run() { command -v "$1" >/dev/null 2>&1 && "$@" 2>&1 || echo "(brak: $1)"; }

section "OS / jądro"
run lsb_release -ds
uname -r
cat /proc/cmdline

section "CPU / RAM"
lscpu | grep -E 'Model name|^CPU\(s\)'
grep -o -w -E 'avx2|avx512f' /proc/cpuinfo | sort -u
free -g
run sudo -n dmidecode -t memory 2>/dev/null | grep -E 'Configured Memory Speed|Size: [0-9]' | sort | uniq -c

section "GPU (PCI)"
run lspci -nn | grep -Ei 'vga|3d|display'
for d in /sys/bus/pci/devices/*; do
  if [[ "$(cat "$d/class" 2>/dev/null)" == 0x03* ]]; then
    echo "$(basename "$d"): link $(cat "$d/current_link_speed" 2>/dev/null) x$(cat "$d/current_link_width" 2>/dev/null) (max $(cat "$d/max_link_speed" 2>/dev/null) x$(cat "$d/max_link_width" 2>/dev/null))"
  fi
done

section "amdgpu"
cat /sys/class/drm/card*/device/power_dpm_force_performance_level 2>/dev/null
cat /sys/module/pcie_aspm/parameters/policy 2>/dev/null
run sudo -n dmesg 2>/dev/null | grep -iE 'resizable bar|BAR=|amdgpu: VRAM' | head

section "Vulkan"
run vulkaninfo --summary | grep -E 'deviceName|driverName|driverInfo|apiVersion|conformanceVersion'
dpkg -l 2>/dev/null | grep -E 'mesa-vulkan-drivers' | awk '{print $2, $3}'
run glslc --version | head -1

section "ROCm"
cat /opt/rocm/.info/version 2>/dev/null || echo "(brak /opt/rocm)"
run rocminfo | grep -E 'Marketing Name|Name: +gfx' | head
run hipconfig --version

section "NVIDIA"
run nvidia-smi --query-gpu=name,driver_version,memory.total,pcie.link.gen.current,pcie.link.width.current --format=csv
run nvcc --version | tail -1
