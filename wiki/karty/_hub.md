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
## Notatki (10)

- [[mi300x|AMD Instinct MI300X (tylko do sanity-checku)]] — Datacenterowy CDNA3 (gfx942, wave64, MFMA); nie jest rynkiem produktu, a darmowe $100 kredytu AMD wystarczy do sprawdzenia, czy wspólny kod HIP działa na CDNA.
- [[radeon-ai-pro-r9700|AMD Radeon AI PRO R9700 (do wynajęcia)]] — RDNA4 gfx1201 z 32 GB (ten sam Navi48 co RX 9070 XT); jedyny RDNA4 do wynajęcia z root na godziny (Hostkey, €0.471/h), plan na kampanie RDNA4.
- [[rx-7900-xtx|AMD Radeon RX 7900 XTX (główna karta)]] — Nasza główna karta: RDNA3 gfx1100, 24 GB GDDR6, 960 GB/s; na niej powstało 70 łatek i rekordy Qwen 109 t/s i LFM 294 t/s.
- [[rx-9070-xt|AMD Radeon RX 9070 XT (planowany zakup)]] — Najpopularniejszy Radeon w Steam (RDNA4, gfx1201, 16 GB, 640 GB/s); w planie do kupienia, bo RDNA4 wymaga przepisania naszych kerneli WMMA.
- [[strix-halo|AMD Strix Halo (Ryzen AI Max, gfx1151)]] — APU RDNA3.5 z pamięcią zunifikowaną do 128 GB; cel na fazę 3 produktu, dziś tylko w danych z raportów.
- [[arc-b580-i-mac|Intel Arc B580 i Mac mini M4 (platformy spoza AMD/NVIDIA)]] — Dwie platformy z listy MVP, których nie da się wynająć z root na godziny (Arc) albo wynajmuje się je tylko z 24-godzinnym minimum (Mac); w planie zakup.
- [[rtx-3060|NVIDIA RTX 3060 12 GB (wynajem, shakedown harnessu)]] — Ampere sm_86 z 12 GB — najtańsza karta (~$0.10/h z dyskiem) i #5 w Steam; poszła na pierwszy ogień, żeby przetestować cały harness chmurowy.
- [[rtx-3090|NVIDIA RTX 3090 (wynajem, Vast)]] — Ampere sm_86 z 24 GB — ulubiona karta entuzjastów LLM; uruchamia ten sam plik Qwen3.8-27B co nasz RX 7900 XTX, więc daje bezpośrednie porównanie.
- [[rtx-5060-ti|NVIDIA RTX 5060 Ti 16 GB (lokalnie + wynajem)]] — Blackwell sm_120 z 16 GB; druga karta w naszym serwerze (PNY OC) i #3 w Steam — najważniejsza karta NVIDIA dla produktu; jedyna w planie z PDL.
- [[inne-karty-nvidia|Pozostałe karty NVIDIA w planie (4060 Ti, 4070, 4090, 5070, 5090, A40, L40S)]] — Karty z listy MVP produktu, których jeszcze nie testowaliśmy; dane rynkowe z raportu 05 (2026-10).
<!-- AUTO:END -->
