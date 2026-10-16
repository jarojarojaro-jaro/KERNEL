---
typ: produkt
tags: [produkt, app, skan]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/app/REPORT.md:15,45,84; ~/KERNEL/app/scan/TEST-linux.txt:1-30,103-154,200-215,251-312; ~/KERNEL/app/scan/scan.sh:38-40,452
status: aktualne
---
# Skrypty skanu sprzętu (scan.sh, scan-macos.sh, scan.ps1)

**Trzy skrypty tylko do odczytu wypisują specyfikację i czytelny kod `HW1;os=…;gpu=…;sum=XXXX` do wklejenia w formularz; na Linuksie `strace` uruchomienia przez `sh` pokazał 0 otwarć `/dev/*`.**

Dokumenty: [REPORT.md](../../app/REPORT.md), [DESIGN.md](../../app/design/DESIGN.md), [APP-ARCHITECTURE.md](../../app/design/APP-ARCHITECTURE.md).

- Linux czyta tylko sysfs (`/sys/bus/pci`, `/sys/class/drm`), procfs (`/proc/cpuinfo`, `/proc/meminfo`), `/etc/os-release` i `lspci`; nie czyta nazwy hosta ani użytkownika, numerów seryjnych, UUID GPU, MAC ani logów. Przy kartach NVIDIA VRAM to „?”, bo odczyt wymagałby otwarcia urządzenia.
- Dowód (`scan/TEST-linux.txt`, 2026-10-16 03:30): `strace -f -e trace=openat,open,execve`; przez `sh` (dash) zero otwarć `/dev/*`; przez `bash` jedna nieudana próba `/dev/tty` (ENXIO), czyli nic nie otwarto. Działa też bez `lspci` (degradacja do identyfikatorów PCI).
- Suma kontrolna: `h = (h*31 + bajt) % 65521`, 4 cyfry hex; self-test `HW1;os=linux` → `E787` w `scan.sh`, `scan-macos.sh`, `scan.ps1` (pwsh 7), w JS (`hwcode.ts`) i w gawk/mawk/nawk/busybox awk.
- Windows (`scan.ps1`) tylko parsowany w PowerShell 7; macOS tylko sprawdzony składniowo i na zaślepkach poleceń – na prawdziwych systemach jeszcze nie uruchamiane.

## Powiązane
- [[produkt/_hub|produkt]]
- [[app-onboarding-prototyp]]
- [[aplikacja-w-budowie]]
- [[produkt-prawo]]
- [[raport-04-sprzet]]
