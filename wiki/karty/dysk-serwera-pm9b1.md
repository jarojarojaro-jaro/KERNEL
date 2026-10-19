---
typ: karta
tags: [karty, dysk, serwer]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/21d-kv-na-dysku.md:104-122; lsblk, /sys/class/nvme/nvme0, UDisks2 SmartGetAttributes, dd iflag=direct (2026-10-19)
status: aktualne
---
# Dysk serwera: Samsung PM9B1 512 GB (NVMe)

**Serwer ma `SAMSUNG MZVL4512HBLU-00BH1` (PM9B1 512 GB, OEM, kontroler Marvell, bez DRAM, TLC 128L) na łączu PCIe 3.0 x4 mimo dysku Gen4; SMART 2026-10-19: 1.875 TB zapisane, 0% zużycia, spare 100%, 0 błędów nośnika, 46 niebezpiecznych wyłączeń, 38 °C.**

- Odczyt O_DIRECT (obciążona maszyna): 1.05 GB/s (16 MiB), 1.60 GB/s (1 MiB), 1.11 GB/s (4 strumienie) – ~30–45% specyfikacji 3.5 GB/s; restore E5 (0.95 GB/s) już jest blisko limitu dysku.
- Bieżący zapis ~4.0 GB/h, ~95 GB/dzień przy pracy deweloperskiej (`/sys/block/nvme0n1/stat`: 27.05 GB w 6.81 h).
- TBW nieopublikowane; proxy 300 TBW / 5 lat (detaliczne 500 GB) → 1.875 TB to 0.6%. Progi temperatury 83/85 °C. TRIM cotygodniowy (`fstrim.timer`), zajętość / 55%.
- Skutki: 46 niebezpiecznych wyłączeń wymusza atomowy zapis plików stanu ([[lekcja-restore-stanu-exactness]]); budżet zapisu cache KV w [[kv-na-dysku-polityka]].

## Powiązane
- [[karty/_hub|Karty]]
- [[rx-7900-xtx]]
- [[cache-sesji-na-dysku]]
