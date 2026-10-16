#!/bin/sh
# Hardware scan (paste-code HW1) for macOS.
#
# Purpose: show which chip, RAM and graphics this Mac has, and print one line
# ("HW1;...") that you can paste into the form on our website so it can suggest
# a model that fits your hardware. Read-only: needs no administrator password,
# makes no network connections, writes no files. Runs with the stock /bin/sh
# (bash 3.2) and zsh. Run: sh scan-macos.sh   (checksum self-test: sh scan-macos.sh --selftest)
#
# Exact list of sources read (nothing else):
#   sw_vers -productName / -productVersion / -buildVersion
#   sysctl -n machdep.cpu.brand_string hw.memsize hw.logicalcpu
#             hw.optional.arm64 hw.optional.avx512f hw.optional.avx2_0 hw.optional.avx1_0
#   system_profiler -detailLevel mini SPDisplaysDataType
#     ("mini" = Apple's level without personal information; only these GPU keys
#      are used: Chipset Model, Type, Bus, Total Number of Cores, VRAM, Vendor,
#      PCIe Lane Width, Metal Support / Metal Family; everything else is ignored)
# Programs run: sw_vers, sysctl, system_profiler, od, awk, tr, cut.
#
# Never read: computer/host name, user name, home paths, serial numbers
# (no SPHardwareDataType), hardware UUID, MAC addresses, disk serials, logs.
# No network access, no files written, no sudo.
#
# SPDX-License-Identifier: MIT

# ---- language (decided before forcing the C locale) -------------------------
PL=0
case "${LC_ALL:-${LC_MESSAGES:-${LANG:-}}}" in pl*|PL*) PL=1 ;; esac
LC_ALL=C
export LC_ALL
TAB=$(printf '\t')

# ---- helpers (identical to scan.sh) ----------------------------------------
# Checksum per contract: h = (h*31 + byte) % 65521 over the exact bytes; 4 hex digits.
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

is_uint() { case $1 in ''|*[!0-9]*) return 1 ;; esac; return 0; }

# sysctl value into $R, or empty when the key does not exist on this Mac.
sc() {
	R=$(sysctl -n "$1" 2>&1) || R=
	case $R in *unknown\ oid*|*:*) R= ;; esac
}

dnum() { if [ "$PL" = 1 ]; then case $1 in *.*) printf '%s,%s' "${1%.*}" "${1#*.}"; return ;; esac; fi; printf '%s' "$1"; }

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
	T_READS='Czyta: sw_vers, sysctl (procesor, RAM, instrukcje) oraz system_profiler SPDisplaysDataType'
	T_READS2='       w trybie „mini” (bez danych osobowych).'
	T_SAFE='Nic nie wysyła, niczego nie zapisuje na dysku i nie potrzebuje hasła administratora.'
	T_NEVER='Nie czyta nazwy komputera ani użytkownika, numerów seryjnych, UUID, adresów MAC ani logów.'
	T_COMPUTER='Komputer'
	T_GPUS='Grafika'
	L_OS='System     '
	L_CPU='Procesor   '
	L_THR='Wątki      '
	L_ISA='Instrukcje '
	L_RAM='Pamięć RAM '
	L_CHIP='Układ      '
	L_CORES='Rdzenie GPU'
	L_VENDOR='Producent  '
	L_TYPE='Rodzaj     '
	L_VRAM='VRAM       '
	L_DRV='Sterownik  '
	L_PCIE='Magistrala '
	T_PRIMARY='trafia do kodu'
	T_DISCRETE='dedykowana'
	T_INTEGRATED='zintegrowana (pamięć wspólna z RAM)'
	T_UNIFIED='zintegrowana, pamięć zunifikowana (GPU i CPU dzielą RAM)'
	T_VRAM_UNIFIED='brak osobnej — GPU korzysta ze wspólnej pamięci RAM'
	T_VRAM_DYN='dynamicznie z RAM, maks.'
	T_NONE='brak'
	T_UNKNOWN='nieznane'
	T_NOGPU='system_profiler nie zwrócił karty graficznej; wybierz swój sprzęt w formularzu.'
	T_FOUND='Wykryto:'
	T_CODE='Kod do wklejenia na stronie — skopiuj całą linię zaczynającą się od HW1;'
	T_CODE2='Kod zawiera wyłącznie pola pokazane powyżej; możesz go przeczytać przed wklejeniem.'
	T_SELF='Test sumy kontrolnej'
else
	T_TITLE='Hardware scan (HW1 code) - read-only'
	T_READS='Reads: sw_vers, sysctl (CPU, RAM, instruction set) and system_profiler SPDisplaysDataType'
	T_READS2='       at the "mini" level (no personal information).'
	T_SAFE='Sends nothing, writes nothing to disk, needs no administrator password.'
	T_NEVER='Never reads computer or user name, serial numbers, UUIDs, MAC addresses or logs.'
	T_COMPUTER='Computer'
	T_GPUS='Graphics'
	L_OS='OS         '
	L_CPU='CPU        '
	L_THR='Threads    '
	L_ISA='SIMD       '
	L_RAM='RAM        '
	L_CHIP='Chip       '
	L_CORES='GPU cores  '
	L_VENDOR='Vendor     '
	L_TYPE='Type       '
	L_VRAM='VRAM       '
	L_DRV='Driver     '
	L_PCIE='Bus        '
	T_PRIMARY='goes into the code'
	T_DISCRETE='discrete'
	T_INTEGRATED='integrated (shares system RAM)'
	T_UNIFIED='integrated, unified memory (GPU and CPU share RAM)'
	T_VRAM_UNIFIED='none of its own - the GPU uses the shared RAM'
	T_VRAM_DYN='dynamic from RAM, up to'
	T_NONE='none'
	T_UNKNOWN='unknown'
	T_NOGPU='system_profiler returned no graphics; pick your hardware in the form.'
	T_FOUND='Found:'
	T_CODE='Paste code for the website - copy the whole line starting with HW1;'
	T_CODE2='The code contains only the fields shown above; you can read it before pasting.'
	T_SELF='Checksum self-test'
fi

if [ "${1:-}" = "--selftest" ]; then
	printf '%s: HW1;os=linux -> %s\n' "$T_SELF" "$(cksum16 'HW1;os=linux')"
	exit 0
fi

# ---- OS, CPU, RAM ------------------------------------------------------------
os_name=$(sw_vers -productName 2>&1) || os_name=macOS
os_ver=$(sw_vers -productVersion 2>&1) || os_ver=
os_build=$(sw_vers -buildVersion 2>&1) || os_build=
os_label="$os_name $os_ver"
[ -n "$os_build" ] && os_label="$os_label ($os_build)"

sc machdep.cpu.brand_string; cpu_model=${R:-?}
sc hw.logicalcpu; thr=$R; is_uint "$thr" || thr=?
sc hw.memsize; ram=?
is_uint "$R" && ram=$(awk -v b="$R" 'BEGIN { printf "%.1f", b / 1073741824 }')

isa=none
sc hw.optional.arm64
if [ "$R" = 1 ]; then isa=neon
else
	sc hw.optional.avx512f
	if [ "$R" = 1 ]; then isa=avx512
	else
		sc hw.optional.avx2_0
		if [ "$R" = 1 ]; then isa=avx2
		else
			sc hw.optional.avx1_0
			[ "$R" = 1 ] && isa=avx
		fi
	fi
fi
case $isa in
	avx512) isa_label='AVX-512' ;; avx2) isa_label='AVX2' ;; avx) isa_label='AVX' ;;
	neon) isa_label='NEON' ;; *) isa_label=$T_NONE ;;
esac

# ---- GPUs (system_profiler text, parsed in one awk pass) ---------------------
# Prints the readable block, then a line "@@P@@" followed by tab-separated fields
# of the primary GPU: count, chip, sub, vendor, vram, um, pcie, metal.
gpu_out=$(system_profiler -detailLevel mini SPDisplaysDataType 2>&1 | awk \
	-v pl="$PL" -v Lchip="$L_CHIP" -v Lcores="$L_CORES" -v Lvendor="$L_VENDOR" -v Ltype="$L_TYPE" \
	-v Lvram="$L_VRAM" -v Ldrv="$L_DRV" -v Lbus="$L_PCIE" -v Tdisc="$T_DISCRETE" -v Tint="$T_INTEGRATED" \
	-v Tuni="$T_UNIFIED" -v Tvuni="$T_VRAM_UNIFIED" -v Tdyn="$T_VRAM_DYN" -v Tunk="$T_UNKNOWN" \
	-v osver="$os_ver" '
	function dn(x) { if (pl == 1) sub(/\./, ",", x); return x }
	function reset() { name = chip = type = bus = cores = vram = vk = vendor = lanes = metal = "" }
	function flush(   key, gib, mib, um, dyn, drv, pcie, sub_, score, vlabel) {
		if (name == "") return
		if (type != "" && type !~ /GPU/) { reset(); return }
		n++
		if (chip == "") chip = name
		lv = tolower(vendor " " chip)
		if (lv ~ /apple|0x106b/) key = "apple"
		else if (lv ~ /nvidia|0x10de/) key = "nvidia"
		else if (lv ~ /amd|ati|radeon|0x1002/) key = "amd"
		else if (lv ~ /intel|0x8086/) key = "intel"
		else key = "none"
		gib = -1; dyn = (vk ~ /Dynamic/)
		if (vram != "") {
			split(vram, p, " ")
			if (p[2] ~ /^GB/) gib = p[1] + 0; else if (p[2] ~ /^MB/) gib = (p[1] + 0) / 1024
		}
		um = (key == "apple" || bus ~ /Built-In/ || dyn) ? 1 : 0
		mib = (gib > 0 && !dyn) ? int(gib * 1024) : 0
		pcie = "?"
		drv = "macOS " osver
		if (metal ~ /^Metal [0-9]/) drv = drv " " metal
		sub_ = (cores ~ /^[0-9]+$/) ? cores " GPU cores" : "?"

		printf "  GPU %d\n", n
		printf "  %s %s\n", Lchip, chip
		if (cores != "") printf "  %s %s\n", Lcores, cores
		printf "  %s %s\n", Lvendor, (vendor != "" ? vendor : Tunk)
		printf "  %s %s\n", Ltype, (key == "apple" ? Tuni : (um ? Tint : Tdisc))
		if (key == "apple") vlabel = Tvuni
		else if (gib > 0 && dyn) vlabel = Tdyn " " dn(sprintf("%.1f", gib)) " GiB"
		else if (gib > 0) vlabel = dn(sprintf("%.1f", gib)) " GiB"
		else vlabel = Tunk
		printf "  %s %s\n", Lvram, vlabel
		printf "  %s %s\n", Ldrv, drv
		printf "  %s %s\n", Lbus, (bus != "" ? bus : Tunk) (lanes != "" ? " " lanes : "")

		score = (1 - um) * 10000000 + mib
		if (score > best) {
			best = score
			bn = n
			bchip = chip; bsub = sub_; bkey = key; bum = um; bpcie = pcie; bdrv = drv
			bvram = (gib > 0 && !dyn && key != "apple") ? sprintf("%.1f", gib) : "?"
		}
		reset()
	}
	BEGIN { reset(); n = 0; best = -1; bn = 0 }
	/^    [^ ].*:[ \t]*$/ { flush(); name = $0; sub(/^ +/, "", name); sub(/:[ \t]*$/, "", name); next }
	/^      [^ ]/ && name != "" {
		line = $0; sub(/^ +/, "", line)
		k = line; sub(/:.*/, "", k)
		v = line; sub(/^[^:]*:[ \t]*/, "", v)
		if (k == "Chipset Model") chip = v
		else if (k == "Type") type = v
		else if (k == "Bus") bus = v
		else if (k == "Total Number of Cores") cores = v
		else if (k ~ /^VRAM/) { vram = v; vk = k }
		else if (k == "Vendor") vendor = v
		else if (k == "PCIe Lane Width") lanes = v
		else if (k == "Metal Support") metal = v
		else if (k ~ /^Metal/ && metal == "") metal = v
	}
	END {
		flush()
		printf "@@P@@%d\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%d", n, bchip, bsub, bkey, bvram, bum, bpcie, bdrv, bn
	}')

gpu_block=${gpu_out%%@@P@@*}
p=${gpu_out#*@@P@@}
ngpu=${p%%"$TAB"*}; p=${p#*"$TAB"}
b_chip=${p%%"$TAB"*}; p=${p#*"$TAB"}
b_sub=${p%%"$TAB"*}; p=${p#*"$TAB"}
b_vendor=${p%%"$TAB"*}; p=${p#*"$TAB"}
b_vram=${p%%"$TAB"*}; p=${p#*"$TAB"}
b_um=${p%%"$TAB"*}; p=${p#*"$TAB"}
b_pcie=${p%%"$TAB"*}; p=${p#*"$TAB"}
b_drv=${p%%"$TAB"*}; p=${p#*"$TAB"}
best_n=$p
is_uint "$ngpu" || ngpu=0

# ---- output ------------------------------------------------------------------
printf '\n%s\n' "$T_TITLE"
printf '%s\n%s\n' "$T_READS" "$T_READS2"
printf '%s\n%s\n\n' "$T_SAFE" "$T_NEVER"

printf '%s\n' "$T_COMPUTER"
row "$L_OS" "$os_label"
row "$L_CPU" "$cpu_model"
if is_uint "$thr"; then
	if [ "$PL" = 1 ]; then thr_label="$thr $(plural "$thr" 'wątek logiczny' 'wątki logiczne' 'wątków logicznych')"
	else thr_label="$thr logical"; fi
else thr_label=$T_UNKNOWN; fi
row "$L_THR" "$thr_label"
row "$L_ISA" "$isa_label"
if [ "$ram" = '?' ]; then row "$L_RAM" "$T_UNKNOWN"; else row "$L_RAM" "$(dnum "$ram") GiB"; fi

printf '\n%s\n' "$T_GPUS"
if [ "$ngpu" -eq 0 ]; then
	printf '  %s\n' "$T_NOGPU"
else
	printf '%s' "$gpu_block"
	if [ "$PL" = 1 ]; then
		printf '  %s %s %s; GPU %s %s.\n' "$T_FOUND" "$ngpu" "$(plural "$ngpu" 'układ graficzny' 'układy graficzne' 'układów graficznych')" "$best_n" "$T_PRIMARY"
	else
		if [ "$ngpu" -eq 1 ]; then w='graphics processor'; else w='graphics processors'; fi
		printf '  %s %s %s; GPU %s %s.\n' "$T_FOUND" "$ngpu" "$w" "$best_n" "$T_PRIMARY"
	fi
fi
printf '\n'

# ---- paste code --------------------------------------------------------------
c_gpu=? c_sub=? c_vendor=none c_vram=? c_drv=? c_pcie=? c_um=0
if [ "$ngpu" -gt 0 ]; then
	clean "$b_chip"; c_gpu=$V
	clean "$b_sub"; c_sub=$V
	case $b_vendor in amd|nvidia|intel|apple) c_vendor=$b_vendor ;; esac
	case $b_vram in [0-9]*.[0-9]) c_vram=$b_vram ;; esac
	clean "$b_drv"; c_drv=$V
	[ "$b_um" = 1 ] && c_um=1
	c_pcie=${b_pcie:-?}
fi
clean "$isa"; c_isa=$V
clean "$thr"; c_thr=$V
clean "$ram"; c_ram=$V

code="HW1;os=macos;gpu=$c_gpu;sub=$c_sub;vendor=$c_vendor;vram=$c_vram;ngpu=$ngpu;drv=$c_drv;ram=$c_ram;thr=$c_thr;isa=$c_isa;pcie=$c_pcie;um=$c_um"
code="$code;sum=$(cksum16 "$code")"

rule='--------------------------------------------------------------------------------'
printf '%s\n' "$T_CODE"
printf '%s\n\n' "$rule"
printf '%s\n\n' "$code"
printf '%s\n' "$rule"
printf '%s\n\n' "$T_CODE2"
