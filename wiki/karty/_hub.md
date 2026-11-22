---
typ: hub
tags: [karty, hub]
aktualizacja: 2026-11-22
zrodlo: wiki/tools/wiki.py index
status: aktualne
streszczono: 2026-11-22
---
# Karty GPU

**Każda karta, której używamy lub którą planujemy: parametry, gdzie stoi (lokalnie / chmura), co zmierzyliśmy.**

<!-- Jarvo:STRESZCZENIE -->
Główna karta: [[rx-7900-xtx]] (gfx1100, 24 GB, 960 GB/s) w maszynie [[jaroserverai]] (zwykle wyłączona, testy tylko przez kolejkę i na polecenie JARO, profil eco 2200 MHz). NVIDIA w wynajmie: [[vast-ai]] (3090, 3060, 5060 Ti, 4080 SUPER; pełna moc sprawdzana przed pobraniem modelu), [[runpod]], od 2026-11-22 [[google-colab]] (200 jednostek/mies.). Najlepsze wyniki per karta: [[najlepsze-wyniki]]; 4080 SUPER: MTP n4 107,3 t/s Qwen3.8-27B ([[rtx-4080-super]], K-118).
<!-- /Jarvo:STRESZCZENIE -->

Lokalna maszyna: RX 7900 XTX + RTX 5060 Ti. Karty NVIDIA z chmury: [[karty/_hub|Chmura]]. Stosy: [[stos/_hub|ROCm]], [[stos/_hub|NVIDIA]].

Wróć: [[index|Strona główna]]. Lista niżej jest generowana przez `python3 tools/wiki.py index`; nie edytuj jej ręcznie.

<!-- AUTO:START -->
## Notatki (21)

- [[amd-dev-cloud|AMD Developer Cloud i inne programy AMD]] — AMD daje $100 kredytu na MI300X (30 dni) i krótkie testy stacji Radeon PRO, ale z zakazami użycia komercyjnego; dla nas tylko do sanity-checku kodu HIP na CDNA3.
- [[mi300x|AMD Instinct MI300X (tylko do sanity-checku)]] — Datacenterowy CDNA3 (gfx942, wave64, MFMA); nie jest rynkiem produktu, a darmowe $100 kredytu AMD wystarczy do sprawdzenia, czy wspólny kod HIP działa na CDNA.
- [[radeon-ai-pro-r9700|AMD Radeon AI PRO R9700 (do wynajęcia)]] — RDNA4 gfx1201 z 32 GB (ten sam Navi48 co RX 9070 XT); jedyny RDNA4 do wynajęcia z root na godziny (Hostkey, €0.471/h), plan na kampanie RDNA4.
- [[rx-7900-xtx|AMD Radeon RX 7900 XTX (główna karta)]] — Nasza główna karta: RDNA3 gfx1100, 24 GB GDDR6, 960 GB/s; na niej powstało 70 łatek i rekordy Qwen 109 t/s i LFM 294 t/s.
- [[rx-9070-xt|AMD Radeon RX 9070 XT (planowany zakup)]] — Najpopularniejszy Radeon w Steam (RDNA4, gfx1201, 16 GB, 640 GB/s); w planie do kupienia, bo RDNA4 wymaga przepisania naszych kerneli WMMA.
- [[strix-halo|AMD Strix Halo (Ryzen AI Max, gfx1151)]] — APU RDNA3.5 z pamięcią zunifikowaną do 128 GB; cel na fazę 3 produktu, dziś tylko w danych z raportów.
- [[dysk-serwera-pm9b1|Dysk serwera: Samsung PM9B1 512 GB (NVMe)]] — Serwer ma `SAMSUNG MZVL4512HBLU-00BH1` (PM9B1 512 GB, OEM, kontroler Marvell, bez DRAM, TLC 128L) na łączu PCIe 3.0 x4 mimo dysku Gen4; SMART 2026-10-19: 1.875 TB zapisane, 0% zużycia, spare 100%, 0 błędów nośnika, 46 niebezpiecznych wyłączeń, 38 °C.
- [[radeony-do-wynajecia|Gdzie wynająć Radeona, Arca i Maca (Hostkey, GigaGPU, Scaleway, hyperscalerzy)]] — Konsumenckich Radeonów z root prawie nie ma w chmurze godzinowej; jedynym RDNA4 na godziny jest Hostkey R9700, reszta to dedyki miesięczne albo WSL2 bez `/dev/kfd`.
- [[google-colab|Google Colab: drugie GPU (NVIDIA T4, L4, G4, A100, H100)]] — Od 2026-11-22 mamy Colab z subskrypcji JARO (200 jednostek miesięcznie) jako drugie GPU obok [[jaroserverai]]: T4 i L4 od razu, A100 i H100 tylko z zapowiedzią kosztu; maszynę zawsze wyłączamy po pracy.
- [[arc-b580-i-mac|Intel Arc B580 i Mac mini M4 (platformy spoza AMD/NVIDIA)]] — Dwie platformy z listy MVP, których nie da się wynająć z root na godziny (Arc) albo wynajmuje się je tylko z 24-godzinnym minimum (Mac); w planie zakup.
- [[jaroserverai|jaroserverai: maszyna z naszą RX 7900 XTX]] — Domowa maszyna JARO z jedyną naszą stałą kartą GPU, [[rx-7900-xtx]] (24 GB, gfx1100): produkcyjny czat na :8080 i wszystkie testy XTX przez kolejkę GPU; zwykle wyłączona, testy tylko na wyraźne polecenie JARO.
- [[karty-nvidia-parametry|Karty NVIDIA (i XTX): pasmo, L2, SM – liczby do rachunków]] — Parametry do modeli kosztu: XTX 960 GB/s, 6 MB L2 + 96 MB MALL, 96 CU; 3090 936 GB/s, 6 MB, 82 SM; 4090 1008 GB/s, 72 MB, 128 SM; 5060 Ti 448 GB/s, 32 MB, 36 SM; 5090 1792 GB/s, 96 MB (persist ≤ 60 MB), 170 SM (raport 21b, 2026-10-19).
- [[rtx-3060|NVIDIA RTX 3060 12 GB (wynajem)]] — Ampere sm_86 z 12 GB, najtańsza karta i #5 w Steam; w kampanii 2026-10-16 (decyzja: tylko Saluki i Bonsai) nasz silnik dał jednocyfrowy zysk, bo te modele nie mają MTP.
- [[rtx-3090|NVIDIA RTX 3090 (wynajem, Vast)]] — Ampere sm_86 z 24 GB uruchamia ten sam plik Qwen3.8-27B co nasz RX 7900 XTX; w kampanii 2026-10-16 nasz silnik dał Qwen 39 → 78 t/s i LFM2.5 180 → 264 t/s.
- [[rtx-4060-ti|NVIDIA RTX 4060 Ti 16 GB (Vast, serwer buildów)]] — Ada sm_89, 16 GB GDDR6 288 GB/s; zmierzona 2026-10-20 na hoście Vast z limitem mocy 100 W i PCIe gen3 x8: nasz silnik daje Qwen3.8-27B UD-Q3_K_XL czat 18.6 → 35.4 t/s (×1.90) i LFM2.5 QAD-Q4_0 114.4 → 149.4 t/s (×1.31).
- [[rtx-4080-super|NVIDIA RTX 4080 SUPER (wynajem, Vast)]] — Karta z jednego wynajmu na Vast (K-118, 2026-11-19): nasz fork CUDA z MTP n4 T=0 daje 107,3 t/s Qwen3.8-27B przy pełnej mocy, a dekod plain wykorzystuje 78% pasma (3090: 58%).
- [[rtx-5060-ti|NVIDIA RTX 5060 Ti 16 GB (lokalnie + wynajem)]] — Blackwell sm_120 z 16 GB, #3 w Steam i druga karta w naszym serwerze; w kampanii 2026-10-16 nasz silnik dał Qwen3.8-27B (Q3_K_XL) 28 → 51.7 t/s i LFM2.5 (Q4_K_M) 148 → 208 t/s.
- [[inne-karty-nvidia|Pozostałe karty NVIDIA (2080 Ti, 3070, 3080, 4060 Ti, 4070, 5080, 4090, 5070, 5090, A40, L40S)]] — Karty bez osobnej strony: dane rynkowe z raportu 05 (2026-10) i zmierzone picki Enigmy z kampanii 67c (2026-11-07).
- [[runpod|RunPod]] — Druga chmura w harnessie: Community i Secure Cloud z kartami 3070…5090, jedyne AMD to MI300X ($2.39/h); u nas przewidziany dla RTX 4090 i 5090, których nie ma w pierwszej rundzie.
- [[salad|SaladCloud (domowe PC graczy, WSL2)]] — Sieć domowych komputerów do gier: tanie NVIDIA (3060…5090) i pięć klas Radeonów, ale tylko jako kontener w WSL2 bez SSH; nadaje się do sprawdzenia „czy działa u gracza na Windowsie”, nie do strojenia kerneli.
- [[vast-ai|Vast.ai (główne źródło kart NVIDIA)]] — Marketplace hostów z kartami NVIDIA od GTX 10xx do RTX 50xx; tu wynajmujemy karty do kampanii (3060, 5060 Ti, 3090), bo zakup jest dużo droższy; AMD na Vast nie ma.
<!-- AUTO:END -->
