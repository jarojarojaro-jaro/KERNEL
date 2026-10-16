#!/bin/sh
# Hardware scan (paste-code HW1) for Linux.
#
# Purpose: show which CPU, RAM and graphics cards this computer has, and print
# one line ("HW1;...") that you can paste into the form on our website so it
# can suggest a model that fits your hardware. Read-only: needs no root, makes
# no network connections, writes no files. Run: sh scan.sh   (self-test of the
# checksum: sh scan.sh --selftest)
#
# Exact list of sources read (nothing else):
#   /sys/bus/pci/devices/*/class, vendor, device, subsystem_vendor,
#     subsystem_device, current_link_speed, current_link_width
#   /sys/bus/pci/devices/*/driver            (symlink target name only)
#   /sys/class/drm/card*/device              (symlink target name only, maps card -> PCI slot)
#   /sys/class/drm/card*/device/mem_info_vram_total, mem_info_gtt_total   (amdgpu)
#   /sys/class/drm/card*/device/tile0/physical_vram_size_bytes           (Intel xe, if present)
#   /sys/module/<gpu driver>/version          (out-of-tree/DKMS drivers, e.g. nvidia)
#   /proc/driver/nvidia/version               (NVIDIA driver version line only)
#   /proc/meminfo (MemTotal), /proc/cpuinfo (model name, processor count, flags/Features)
#   /etc/os-release (PRETTY_NAME), /proc/sys/kernel/osrelease
#   lspci -mm -s <slot>                       (device names from pci.ids; optional)
# Programs run: lspci (optional), readlink, od, awk, tr, cut.
#
# Never read: hostname, user name, home paths, serial numbers, GPU UUIDs
# (so /proc/driver/nvidia/gpus/*/information is NOT read), MAC addresses,
# disk serials, /proc/cmdline, dmesg, system logs. Never opens /dev/* and
# never runs nvidia-smi, rocm-smi, amd-smi, vulkaninfo, glxinfo or clinfo.
#
# SPDX-License-Identifier: MIT

# ---- language (decided before forcing the C locale) -------------------------
PL=0
case "${LC_ALL:-${LC_MESSAGES:-${LANG:-}}}" in pl*|PL*) PL=1 ;; esac
LC_ALL=C
export LC_ALL

# ---- helpers -----------------------------------------------------------------
# Checksum per contract: h = (h*31 + byte) % 65521 over the exact bytes; 4 hex digits.
# The byte list is passed with -v so awk never reads stdin (gawk reopens fd 0 on /dev/null after EOF).
cksum16() {
	_bytes=$(printf '%s' "$1" | od -An -tu1 -v | tr '\n' ' ')
	awk -v b="$_bytes" 'BEGIN { h = 0; n = split(b, a, " ")
		for (i = 1; i <= n; i++) h = (h * 31 + a[i]) % 65521
		printf "%04X", h }'
}

# Field value per contract: ASCII printable only, ';' and '=' -> space,
# whitespace collapsed, trimmed, max 48 chars, empty -> '?'. Result in $V.
clean() {
	V=$(printf '%s' "$1" | tr -c '\040-\072\074\076-\176' ' ' | tr -s ' ')
	V=${V# }
	V=${V% }
	if [ ${#V} -gt 48 ]; then
		V=$(printf '%s' "$V" | cut -c1-48)
		V=${V% }
	fi
	[ -n "$V" ] || V='?'
}

# First line of a text file into $R (empty if unreadable). Uses the shell's read, no exec.
rd() {
	R=
	if [ -r "$1" ]; then IFS= read -r R < "$1" || :; fi
}

# Nth double-quoted field of an `lspci -mm` line into $Q (1=class 2=vendor 3=device 4=subvendor 5=subdevice).
qfield() {
	_s=$1 _n=0 Q=
	while :; do
		case $_s in *\"*\"*) ;; *) return 1 ;; esac
		_s=${_s#*\"}
		_f=${_s%%\"*}
		_s=${_s#*\"}
		_n=$((_n + 1))
		if [ "$_n" -eq "$2" ]; then Q=$_f; return 0; fi
	done
}

is_uint() { case $1 in ''|*[!0-9]*) return 1 ;; esac; return 0; }

# Bytes -> GiB with one decimal (dot).
gib() { awk -v b="$1" 'BEGIN { printf "%.1f", b / 1073741824 }'; }

# Dot decimal -> display decimal (comma in Polish).
dnum() { if [ "$PL" = 1 ]; then case $1 in *.*) printf '%s,%s' "${1%.*}" "${1#*.}"; return ;; esac; fi; printf '%s' "$1"; }

# Polish plural: plural N one few many
plural() {
	if [ "$1" -eq 1 ]; then printf '%s' "$2"; return; fi
	_m10=$(($1 % 10)) _m100=$(($1 % 100))
	if [ "$_m10" -ge 2 ] && [ "$_m10" -le 4 ] && { [ "$_m100" -lt 12 ] || [ "$_m100" -gt 14 ]; }; then
		printf '%s' "$3"
	else
		printf '%s' "$4"
	fi
}

# Labels are pre-padded to 11 visible characters (printf pads bytes, not letters).
row() { printf '  %s %s\n' "$1" "$2"; }

# ---- strings -----------------------------------------------------------------
if [ "$PL" = 1 ]; then
	T_TITLE='Skan sprzętu (kod HW1) — tylko odczyt'
	T_READS='Czyta: /sys/bus/pci, /sys/class/drm, /sys/module, /proc/cpuinfo, /proc/meminfo,'
	T_READS2='       /proc/driver/nvidia/version, /etc/os-release oraz lspci (nazwy z bazy pci.ids).'
	T_SAFE='Nic nie wysyła, niczego nie zapisuje na dysku i nie potrzebuje uprawnień roota.'
	T_NEVER='Nie czyta nazwy komputera ani użytkownika, numerów seryjnych, UUID kart, adresów MAC ani logów.'
	T_COMPUTER='Komputer'
	T_GPUS='Karty graficzne'
	L_OS='System     '
	L_KERNEL='Jądro      '
	L_CPU='Procesor   '
	L_THR='Wątki      '
	L_ISA='Instrukcje '
	L_RAM='Pamięć RAM '
	L_CHIP='Układ      '
	L_BOARD='Karta      '
	L_VENDOR='Producent  '
	L_TYPE='Rodzaj     '
	L_VRAM='VRAM       '
	L_DRV='Sterownik  '
	L_PCIE='PCIe       '
	T_PRIMARY='trafia do kodu'
	T_DISCRETE='dedykowana'
	T_INTEGRATED='zintegrowana (pamięć wspólna z RAM)'
	T_NODRV='brak sterownika GPU — nie liczona do ngpu'
	T_NONE='brak'
	T_UNKNOWN='nieznane'
	T_VRAM_NV='nieznana — sterownik NVIDIA podaje ją tylko po otwarciu urządzenia, a skan tego nie robi; wybierz swoją kartę w formularzu'
	T_VRAM_INTEL='nieznana (brak pliku w sysfs); wybierz swoją kartę w formularzu'
	T_VRAM_SHARED='brak własnej — używa RAM systemu'
	T_VRAM_UNK='nieznana; wybierz swoją kartę w formularzu'
	T_CARVE='wydzielone w BIOS/UEFI (carve-out)'
	T_GTT='GTT (RAM systemu dostępny dla GPU)'
	T_LINK='bieżące łącze; bez obciążenia karta często je zwalnia'
	T_NOGPU='Nie znaleziono karty graficznej w /sys/bus/pci.'
	T_NOLSPCI='(brak programu lspci — nazwy kart jako identyfikatory PCI)'
	T_FOUND='Wykryto:'
	T_CODE='Kod do wklejenia na stronie — skopiuj całą linię zaczynającą się od HW1;'
	T_CODE2='Kod zawiera wyłącznie pola pokazane powyżej; możesz go przeczytać przed wklejeniem.'
	T_SELF='Test sumy kontrolnej'
else
	T_TITLE='Hardware scan (HW1 code) - read-only'
	T_READS='Reads: /sys/bus/pci, /sys/class/drm, /sys/module, /proc/cpuinfo, /proc/meminfo,'
	T_READS2='       /proc/driver/nvidia/version, /etc/os-release and lspci (names from pci.ids).'
	T_SAFE='Sends nothing, writes nothing to disk, needs no root.'
	T_NEVER='Never reads host or user name, serial numbers, GPU UUIDs, MAC addresses or logs.'
	T_COMPUTER='Computer'
	T_GPUS='Graphics'
	L_OS='OS         '
	L_KERNEL='Kernel     '
	L_CPU='CPU        '
	L_THR='Threads    '
	L_ISA='SIMD       '
	L_RAM='RAM        '
	L_CHIP='Chip       '
	L_BOARD='Board      '
	L_VENDOR='Vendor     '
	L_TYPE='Type       '
	L_VRAM='VRAM       '
	L_DRV='Driver     '
	L_PCIE='PCIe       '
	T_PRIMARY='goes into the code'
	T_DISCRETE='discrete'
	T_INTEGRATED='integrated (shares system RAM)'
	T_NODRV='no GPU driver bound - not counted in ngpu'
	T_NONE='none'
	T_UNKNOWN='unknown'
	T_VRAM_NV='unknown - the NVIDIA driver only reports it after opening the device, which this scan never does; pick your card in the form'
	T_VRAM_INTEL='unknown (no sysfs file); pick your card in the form'
	T_VRAM_SHARED='none of its own - uses system RAM'
	T_VRAM_UNK='unknown; pick your card in the form'
	T_CARVE='reserved in BIOS/UEFI (carve-out)'
	T_GTT='GTT (system RAM usable by the GPU)'
	T_LINK='current link; cards often slow it down when idle'
	T_NOGPU='No graphics card found in /sys/bus/pci.'
	T_NOLSPCI='(lspci not installed - cards shown by PCI ID)'
	T_FOUND='Found:'
	T_CODE='Paste code for the website - copy the whole line starting with HW1;'
	T_CODE2='The code contains only the fields shown above; you can read it before pasting.'
	T_SELF='Checksum self-test'
fi

if [ "${1:-}" = "--selftest" ]; then
	printf '%s: HW1;os=linux -> %s\n' "$T_SELF" "$(cksum16 'HW1;os=linux')"
	exit 0
fi

LSPCI=$(command -v lspci) || LSPCI=

# ---- CPU, RAM, OS ------------------------------------------------------------
cpu_model=? thr=? isa=?
if [ -r /proc/cpuinfo ]; then
	# One pass; output "threads|isa|model" (model last: it may contain '|').
	_cpu=$(awk '
		function val(s) { sub(/^[^:]*:[ \t]*/, "", s); return s }
		/^processor[ \t]*:/ { n++ }
		/^model name[ \t]*:/ && m == "" { m = val($0) }
		/^(Hardware|Model)[ \t]*:/ && alt == "" { alt = val($0) }
		/^flags[ \t]*:/ && isa == "" { f = " " $0 " "
			if (f ~ / avx512f /) isa = "avx512"; else if (f ~ / avx2 /) isa = "avx2"
			else if (f ~ / avx /) isa = "avx"; else isa = "none" }
		/^Features[ \t]*:/ && isa == "" { f = " " $0 " "
			if (f ~ / (asimd|neon) /) isa = "neon"; else isa = "none" }
		END { if (m == "") m = alt
			printf "%s|%s|%s", (n ? n : "?"), (isa != "" ? isa : "?"), (m != "" ? m : "?") }' /proc/cpuinfo)
	thr=${_cpu%%|*}
	_cpu=${_cpu#*|}
	isa=${_cpu%%|*}
	cpu_model=${_cpu#*|}
fi
case $isa in
	avx512) isa_label='AVX-512' ;; avx2) isa_label='AVX2' ;; avx) isa_label='AVX' ;;
	neon) isa_label='NEON' ;; none) isa_label=$T_NONE ;; *) isa_label=$T_UNKNOWN ;;
esac

ram=?
if [ -r /proc/meminfo ]; then
	ram=$(awk '/^MemTotal:/ { printf "%.1f", $2 / 1048576; exit }' /proc/meminfo)
	[ -n "$ram" ] || ram=?
fi

os_name=
if [ -r /etc/os-release ]; then
	os_name=$(awk -F= '
		$1 == "PRETTY_NAME" { v = $0; sub(/^[^=]*=/, "", v); gsub(/^"|"$/, "", v); p = v }
		$1 == "NAME" { v = $0; sub(/^[^=]*=/, "", v); gsub(/^"|"$/, "", v); n = v }
		$1 == "VERSION_ID" { v = $0; sub(/^[^=]*=/, "", v); gsub(/^"|"$/, "", v); ver = v }
		END { if (p != "") print p; else if (n != "") print n " " ver }' /etc/os-release)
fi
[ -n "$os_name" ] || os_name=Linux
rd /proc/sys/kernel/osrelease
kernel=${R:-?}

# ---- GPUs --------------------------------------------------------------------
is_gpu_driver() { case $1 in amdgpu|radeon|nvidia|nouveau|i915|xe) return 0 ;; esac; return 1; }

# DRM card directory for a PCI slot into $CARD (empty if none).
card_for_slot() {
	CARD=
	for _c in /sys/class/drm/card*; do
		[ -e "$_c/device" ] || continue
		case ${_c##*/} in *-*) continue ;; esac
		_l=$(readlink "$_c/device") || continue
		if [ "${_l##*/}" = "$1" ]; then CARD=$_c; return 0; fi
	done
	return 1
}

# AMD integrated (APU) graphics: by pci.ids codename, or a "Radeon" CPU name when there is no name.
amd_apu() {
	case $1 in
		*Renoir*|*Cezanne*|*Lucienne*|*Barcelo*|*Rembrandt*|*Phoenix*|*Hawk\ Point*|*Raphael*|\
		*Granite\ Ridge*|*Strix*|*Krackan*|*Mendocino*|*VanGogh*|*Van\ Gogh*|*Picasso*|*Raven*|\
		*Dali*|*Pollock*|*Stoney*|*Carrizo*|*Kaveri*|*Kabini*|*Mullins*|*Beema*|*Wrestler*|\
		*Trinity*|*Richland*|*Sumo*|*Cyan\ Skillfish*|*Sarlak*) return 0 ;;
		PCI\ *) case $cpu_model in *Radeon*) return 0 ;; esac ;;
	esac
	return 1
}

# Collect everything about one display device (slot) into G_* variables.
gpu_info() {
	_d=/sys/bus/pci/devices/$1
	rd "$_d/vendor"; _ven=${R#0x}
	rd "$_d/device"; _dev=${R#0x}
	rd "$_d/subsystem_vendor"; _sven=${R#0x}
	rd "$_d/subsystem_device"; _sdev=${R#0x}
	rd "$_d/current_link_speed"; _speed=$R
	rd "$_d/current_link_width"; _width=$R
	G_DRV_NAME=
	if [ -e "$_d/driver" ]; then
		_l=$(readlink "$_d/driver") && G_DRV_NAME=${_l##*/}
	fi

	case $_ven in
		1002) G_VENDOR=amd; G_VENDOR_LABEL=AMD ;;
		10de) G_VENDOR=nvidia; G_VENDOR_LABEL=NVIDIA ;;
		8086) G_VENDOR=intel; G_VENDOR_LABEL=Intel ;;
		106b) G_VENDOR=apple; G_VENDOR_LABEL=Apple ;;
		*) G_VENDOR=none; G_VENDOR_LABEL="PCI $_ven" ;;
	esac

	G_NAME="PCI $_ven:$_dev" G_SUB= G_BOARD=
	_svn= _sdn=
	if [ -n "$LSPCI" ]; then
		_line=$("$LSPCI" -mm -s "$1" 2>&1)
		if qfield "$_line" 2 && [ -n "$Q" ]; then G_VENDOR_LABEL=$Q; fi
		if qfield "$_line" 3 && [ -n "$Q" ]; then G_NAME=$Q; fi
		qfield "$_line" 4 && _svn=$Q
		qfield "$_line" 5 && _sdn=$Q
	fi
	if [ -n "$_sven" ] && [ "$_sven" != 0000 ]; then
		case $_sdn in
			''|Device\ ????) if [ -n "$_svn" ]; then G_SUB="$_svn $_sven:$_sdev"; else G_SUB="$_sven:$_sdev"; fi
				G_BOARD=$G_SUB ;;
			*) G_SUB=$_sdn; if [ -n "$_svn" ]; then G_BOARD="$_svn $_sdn"; else G_BOARD=$_sdn; fi ;;
		esac
	fi

	G_HAS_DRV=0
	is_gpu_driver "$G_DRV_NAME" && G_HAS_DRV=1

	# integrated?
	G_UM=0
	case $G_VENDOR in
		intel) [ "$1" = 0000:00:02.0 ] && G_UM=1 ;;
		amd) amd_apu "$G_NAME" && G_UM=1 ;;
	esac

	# VRAM
	G_VRAM=? G_VRAM_MIB=0 G_VRAM_NOTE=
	card_for_slot "$1"
	case $G_DRV_NAME in
		amdgpu|radeon)
			_b= _g=
			if [ -n "$CARD" ]; then
				rd "$CARD/device/mem_info_vram_total"; _b=$R
				rd "$CARD/device/mem_info_gtt_total"; _g=$R
			fi
			if is_uint "$_b" && [ "$_b" -gt 0 ]; then
				G_VRAM=$(gib "$_b"); G_VRAM_MIB=$((_b / 1048576))
				if [ "$G_UM" = 1 ]; then
					G_VRAM_NOTE="$T_CARVE"
					is_uint "$_g" && G_VRAM_NOTE="$G_VRAM_NOTE; + $(dnum "$(gib "$_g")") GiB $T_GTT"
				fi
			else
				G_VRAM_NOTE=$T_VRAM_UNK
			fi ;;
		xe)
			_b=
			[ -n "$CARD" ] && { rd "$CARD/device/tile0/physical_vram_size_bytes"; _b=$R; }
			if is_uint "$_b" && [ "$_b" -gt 0 ]; then
				G_VRAM=$(gib "$_b"); G_VRAM_MIB=$((_b / 1048576))
			elif [ "$G_UM" = 1 ]; then G_VRAM_NOTE=$T_VRAM_SHARED
			else G_VRAM_NOTE=$T_VRAM_INTEL
			fi ;;
		i915)
			if [ "$G_UM" = 1 ]; then G_VRAM_NOTE=$T_VRAM_SHARED; else G_VRAM_NOTE=$T_VRAM_INTEL; fi ;;
		nvidia|nouveau) G_VRAM_NOTE=$T_VRAM_NV ;;
		*)
			if [ "$G_VENDOR" = intel ] && [ "$G_UM" = 1 ]; then G_VRAM_NOTE=$T_VRAM_SHARED; else G_VRAM_NOTE=$T_VRAM_UNK; fi ;;
	esac

	# Driver name + version
	G_DRV=?
	if [ "$G_HAS_DRV" = 1 ]; then
		rd "/sys/module/$G_DRV_NAME/version"; _ver=$R
		if [ "$G_DRV_NAME" = nvidia ]; then
			_kind=nvidia
			if [ -r /proc/driver/nvidia/version ]; then
				_nv=$(awk '/^NVRM version:/ {
						k = ($0 ~ /Open Kernel Module/) ? "nvidia-open" : "nvidia"
						for (i = 1; i <= NF; i++) if ($i ~ /^[0-9]+\.[0-9]+(\.[0-9]+)?$/) { print k " " $i; exit }
						print k; exit }' /proc/driver/nvidia/version)
				[ -n "$_nv" ] && _kind=${_nv%% *} && [ -z "$_ver" ] && case $_nv in *\ *) _ver=${_nv#* } ;; esac
			fi
			G_DRV="$_kind ${_ver:-?}"
		elif [ -n "$_ver" ]; then
			G_DRV="$G_DRV_NAME $_ver"
		else
			G_DRV="$G_DRV_NAME $kernel"
		fi
	fi

	# PCIe link
	G_PCIE=? G_PCIE_LABEL=
	case ${_speed%% *} in
		2.5) _gen=1 ;; 5|5.0) _gen=2 ;; 8|8.0) _gen=3 ;; 16|16.0) _gen=4 ;; 32|32.0) _gen=5 ;; 64|64.0) _gen=6 ;; *) _gen= ;;
	esac
	if [ -n "$_gen" ] && is_uint "$_width" && [ "$_width" -gt 0 ]; then
		G_PCIE="${_gen}x$_width"
		G_PCIE_LABEL="$_gen.0 x$_width (${_speed%% *} GT/s; $T_LINK)"
	fi

	# Ranking key for the primary GPU: has GPU driver > discrete > VRAM size.
	G_SCORE=$((G_HAS_DRV * 20000000 + (1 - G_UM) * 10000000 + G_VRAM_MIB))
}

# ---- output ------------------------------------------------------------------
printf '\n%s\n' "$T_TITLE"
printf '%s\n%s\n' "$T_READS" "$T_READS2"
printf '%s\n%s\n\n' "$T_SAFE" "$T_NEVER"

printf '%s\n' "$T_COMPUTER"
row "$L_OS" "$os_name"
row "$L_KERNEL" "$kernel"
row "$L_CPU" "$cpu_model"
if is_uint "$thr"; then
	if [ "$PL" = 1 ]; then thr_label="$thr $(plural "$thr" 'wątek logiczny' 'wątki logiczne' 'wątków logicznych')"
	else thr_label="$thr logical"; fi
else thr_label=$T_UNKNOWN; fi
row "$L_THR" "$thr_label"
row "$L_ISA" "$isa_label"
if [ "$ram" = '?' ]; then row "$L_RAM" "$T_UNKNOWN"; else row "$L_RAM" "$(dnum "$ram") GiB"; fi
printf '\n%s\n' "$T_GPUS"
[ -n "$LSPCI" ] || printf '  %s\n' "$T_NOLSPCI"

# One pass over display-class PCI devices: print each, remember the best one for the code.
ngpu=0 ndisp=0 best_n=0 best_score=-1
c_gpu=? c_sub=? c_vendor=none c_vram=? c_drv=? c_pcie=? c_um=0
for d in /sys/bus/pci/devices/*; do
	[ -r "$d/class" ] || continue
	rd "$d/class"
	case $R in 0x03*) ;; *) continue ;; esac
	gpu_info "${d##*/}"
	ndisp=$((ndisp + 1))
	[ "$G_HAS_DRV" = 1 ] && ngpu=$((ngpu + 1))

	printf '  GPU %s\n' "$ndisp"
	row "$L_CHIP" "$G_NAME"
	[ -n "$G_BOARD" ] && row "$L_BOARD" "$G_BOARD"
	row "$L_VENDOR" "$G_VENDOR_LABEL"
	if [ "$G_UM" = 1 ]; then row "$L_TYPE" "$T_INTEGRATED"; else row "$L_TYPE" "$T_DISCRETE"; fi
	if [ "$G_VRAM" = '?' ]; then row "$L_VRAM" "$G_VRAM_NOTE"
	elif [ -n "$G_VRAM_NOTE" ]; then row "$L_VRAM" "$(dnum "$G_VRAM") GiB $G_VRAM_NOTE"
	else row "$L_VRAM" "$(dnum "$G_VRAM") GiB"; fi
	if [ "$G_HAS_DRV" = 1 ]; then row "$L_DRV" "$G_DRV"
	elif [ -n "$G_DRV_NAME" ]; then row "$L_DRV" "$G_DRV_NAME ($T_NODRV)"
	else row "$L_DRV" "$T_NONE ($T_NODRV)"; fi
	row "$L_PCIE" "${G_PCIE_LABEL:-$T_UNKNOWN}"

	if [ "$G_SCORE" -gt "$best_score" ]; then
		best_score=$G_SCORE best_n=$ndisp
		clean "$G_NAME"; c_gpu=$V
		clean "$G_SUB"; c_sub=$V
		c_vendor=$G_VENDOR c_vram=$G_VRAM c_pcie=$G_PCIE c_um=$G_UM c_drv=?
		[ "$G_HAS_DRV" = 1 ] && { clean "$G_DRV"; c_drv=$V; }
	fi
done

if [ "$ndisp" -eq 0 ]; then
	printf '  %s\n' "$T_NOGPU"
else
	if [ "$PL" = 1 ]; then
		printf '  %s %s %s; GPU %s %s.\n' "$T_FOUND" "$ngpu" \
			"$(plural "$ngpu" 'karta graficzna z działającym sterownikiem' 'karty graficzne z działającym sterownikiem' 'kart graficznych z działającym sterownikiem')" \
			"$best_n" "$T_PRIMARY"
	else
		if [ "$ngpu" -eq 1 ]; then w='graphics card'; else w='graphics cards'; fi
		printf '  %s %s %s with a working driver; GPU %s %s.\n' "$T_FOUND" "$ngpu" "$w" "$best_n" "$T_PRIMARY"
	fi
fi
printf '\n'

# ---- paste code --------------------------------------------------------------
clean "$isa"; c_isa=$V
clean "$thr"; c_thr=$V
clean "$ram"; c_ram=$V

code="HW1;os=linux;gpu=$c_gpu;sub=$c_sub;vendor=$c_vendor;vram=$c_vram;ngpu=$ngpu;drv=$c_drv;ram=$c_ram;thr=$c_thr;isa=$c_isa;pcie=$c_pcie;um=$c_um"
code="$code;sum=$(cksum16 "$code")"

rule='--------------------------------------------------------------------------------'
printf '%s\n' "$T_CODE"
printf '%s\n\n' "$rule"
printf '%s\n\n' "$code"
printf '%s\n' "$rule"
printf '%s\n\n' "$T_CODE2"
