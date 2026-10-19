---
typ: produkt
tags: [produkt, cache, ssd, zuzycie]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/21d-kv-na-dysku.md:5-13,34-56,124-146,168-193
status: nieaktualne
---
# Cache KV na dysku: polityka warstw i budżet zużycia SSD

**Dysk zabija tylko naiwna polityka: pełny zapis slotu po każdej turze w formacie E5 to ~582 GB na sesję 150k i ~4.7 TB/dzień (dysk 300 TBW w ~64 dni), a polityka „najpierw RAM/tmpfs, na dysk tylko przy shutdown lub presji RAM, top-2 sesje” to ~7 GB/dzień pod twardym limitem 10 GB/dzień (raport 21d, 2026-10-19).**

| polityka | GB / sesja 150k | GB / dzień | 300 TBW starcza na |
|---|---|---|---|
| P0 pełny zapis co turę, obecny format | 582 | ~4 660 | ~64 dni |
| P0′ j.w., 1 checkpoint | 321 | ~2 570 | ~117 dni |
| P1 Mirai (pełny co +8k) | 26.9 | ~215 | ~3.8 roku |
| P2 Mirai (delty + pełny co 8) | 6.9 | ~55 | ~15 lat |
| P3 append KV + 2 zrzuty stanu, bez RAM | 3.6 | ~29 | ~28 lat |
| **P4 tmpfs, na dysk tylko shutdown/presja, top-2** | – | **~7 (limit 10)** | > 100 lat |

Reguły projektu: warstwy L0 VRAM → L1 `--cache-ram` → L2 tmpfs (`/dev/shm`, min(12 GiB, 20% RAM), przeżywa restart serwera i zmianę modelu) → L3 SSD (tylko shutdown, wypchnięcie wpisu wznawianego ≥ 1×, „przypnij sesję”; nigdy na ścieżce żądania). Do L2 tylko sesje ≥ 16k przy bezczynności ≥ 60 s. Format: segmenty KV po 8192 pozycji adresowane BLAKE3 bajtów (append-only), jeden punkt stanu (GDN + MTP sidecar + 1 checkpoint), manifest z fingerprintem; zapis tmp → `fdatasync` → `rename` → fsync katalogu. Limity: zapis L3 ≤ 2% pojemności/dzień, miejsce ≤ min(32 GB, 10%), zajętość FS ≤ 80%, TTL 72 h; strażnik SMART (`percent_used` ≥ 80, spare, `critical_warning`, rosnące `media_errors`) wyłącza L3. Odczyty nie zużywają NAND.

Bajty: Qwen q4_0 18 432 B/token (+ MTP 1152), stan GDN 156.9 MB, checkpoint 178.6 MB; LFM q8_0 10 880 B/token. Plik Qwena z 1 checkpointem: 53k 1.31 GB, 150k 3.10 GB, 200k 4.02 GB (dziś z 7 checkpointami 2.21 / 6.14 / 8.13 GB).

**Decyzja użytkownika 2026-10-19:** KV/sesje tylko w RAM, bez SSD – [[2026-10-19-kv-tylko-w-ram]].

## Powiązane
- [[produkt/_hub|produkt]]
- [[cache-sesji-na-dysku]]
- [[dysk-serwera-pm9b1]]
- [[lekcja-restore-stanu-exactness]]
