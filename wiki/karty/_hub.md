---
typ: hub
tags: [karty, hub]
aktualizacja: 2026-10-16
zrodlo: wiki/tools/wiki.py index
status: aktualne
---
# Karty GPU

**Każda karta, której używamy lub którą planujemy: parametry, gdzie stoi (lokalnie / chmura), co zmierzyliśmy.**

Lokalna maszyna: RX 7900 XTX + RTX 5060 Ti. Karty NVIDIA z chmury: [[chmura/_hub|Chmura]]. Stosy: [[rocm/_hub|ROCm]], [[nvidia/_hub|NVIDIA]].

Wróć: [[index|Strona główna]]. Lista niżej jest generowana przez `python3 tools/wiki.py index`; nie edytuj jej ręcznie.

<!-- AUTO:START -->
## Notatki (12)

- [[mi300x|AMD Instinct MI300X (tylko do sanity-checku)]] — Datacenterowy CDNA3 (gfx942, wave64, MFMA); nie jest rynkiem produktu, a darmowe $100 kredytu AMD wystarczy do sprawdzenia, czy wspólny kod HIP działa na CDNA.
- [[radeon-ai-pro-r9700|AMD Radeon AI PRO R9700 (do wynajęcia)]] — RDNA4 gfx1201 z 32 GB (ten sam Navi48 co RX 9070 XT); jedyny RDNA4 do wynajęcia z root na godziny (Hostkey, €0.471/h), plan na kampanie RDNA4.
- [[rx-7900-xtx|AMD Radeon RX 7900 XTX (główna karta)]] — Nasza główna karta: RDNA3 gfx1100, 24 GB GDDR6, 960 GB/s; na niej powstało 70 łatek i rekordy Qwen 109 t/s i LFM 294 t/s.
- [[rx-9070-xt|AMD Radeon RX 9070 XT (planowany zakup)]] — Najpopularniejszy Radeon w Steam (RDNA4, gfx1201, 16 GB, 640 GB/s); w planie do kupienia, bo RDNA4 wymaga przepisania naszych kerneli WMMA.
- [[strix-halo|AMD Strix Halo (Ryzen AI Max, gfx1151)]] — APU RDNA3.5 z pamięcią zunifikowaną do 128 GB; cel na fazę 3 produktu, dziś tylko w danych z raportów.
- [[dysk-serwera-pm9b1|Dysk serwera: Samsung PM9B1 512 GB (NVMe)]] — Serwer ma `SAMSUNG MZVL4512HBLU-00BH1` (PM9B1 512 GB, OEM, kontroler Marvell, bez DRAM, TLC 128L) na łączu PCIe 3.0 x4 mimo dysku Gen4; SMART 2026-10-19: 1.875 TB zapisane, 0% zużycia, spare 100%, 0 błędów nośnika, 46 niebezpiecznych wyłączeń, 38 °C.
- [[arc-b580-i-mac|Intel Arc B580 i Mac mini M4 (platformy spoza AMD/NVIDIA)]] — Dwie platformy z listy MVP, których nie da się wynająć z root na godziny (Arc) albo wynajmuje się je tylko z 24-godzinnym minimum (Mac); w planie zakup.
- [[rtx-3060|NVIDIA RTX 3060 12 GB (wynajem)]] — Ampere sm_86 z 12 GB, najtańsza karta i #5 w Steam; w kampanii 2026-10-16 (decyzja: tylko Saluki i Bonsai) nasz silnik dał jednocyfrowy zysk, bo te modele nie mają MTP.
- [[rtx-3090|NVIDIA RTX 3090 (wynajem, Vast)]] — Ampere sm_86 z 24 GB uruchamia ten sam plik Qwen3.8-27B co nasz RX 7900 XTX; w kampanii 2026-10-16 nasz silnik dał Qwen 39 → 78 t/s i LFM2.5 180 → 264 t/s.
- [[rtx-4060-ti|NVIDIA RTX 4060 Ti 16 GB (Vast, serwer buildów)]] — Ada sm_89, 16 GB GDDR6 288 GB/s; zmierzona 2026-10-20 na hoście Vast z limitem mocy 100 W i PCIe gen3 x8: nasz silnik daje Qwen3.8-27B UD-Q3_K_XL czat 18.6 → 35.4 t/s (×1.90) i LFM2.5 QAD-Q4_0 114.4 → 149.4 t/s (×1.31).
- [[rtx-5060-ti|NVIDIA RTX 5060 Ti 16 GB (lokalnie + wynajem)]] — Blackwell sm_120 z 16 GB, #3 w Steam i druga karta w naszym serwerze; w kampanii 2026-10-16 nasz silnik dał Qwen3.8-27B (Q3_K_XL) 28 → 51.7 t/s i LFM2.5 (Q4_K_M) 148 → 208 t/s.
- [[inne-karty-nvidia|Pozostałe karty NVIDIA w planie (4060 Ti, 4070, 4090, 5070, 5090, A40, L40S)]] — Karty z listy MVP produktu, których jeszcze nie testowaliśmy; dane rynkowe z raportu 05 (2026-10).
<!-- AUTO:END -->
