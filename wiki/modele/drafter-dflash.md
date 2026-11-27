---
typ: model
tags: [modele, dflash, spekulacja]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/qwen-opt/research/drafters.md:9-11,28-29,44-57; ~/KERNEL/qwen-opt/NOTES.md:45-50,148-160; ~/KERNEL/qwen-opt/research/qwen-round5.md:26-28; ~/KERNEL/qwen-opt/SPEC-QWEN27B.md:24,74-75; ls ~/models/draft (2026-10-16); ~/KERNEL/product/research/15b-spekulacja-frontier.md:21,113-123; ~/KERNEL/product/research/16i-magnitude-co-robia-dobrze.md:28-29,43-52,295-301; ~/KERNEL/product/research/16d-magnitude-vs-nasz.md:14,66-67; ~/KERNEL/product/research/21a-dspine.md:17-21
status: aktualne
model: drafter-dflash
rozmiar: 5 warstw
kwant: Q4_K_M
karty: rx-7900-xtx, rtx-3090
wyniki:
  - drafter-dflash | rx-7900-xtx | 115.7 t/s | dekod EN; n=6, cache q8_1 | 2026-10-09
  - drafter-dflash | rx-7900-xtx | 90.6 t/s | dekod mediana T=0; PL/EN, n=6, 285 W | 2026-10-10
  - drafter-dflash | rx-7900-xtx | 71.9 t/s | dekod mediana T=1; PL/EN, n=6 | 2026-10-10
  - drafter-dflash | rx-7900-xtx | 104.8 t/s | dekod EN kod; n=6, runda 5 | 2026-10-15
  - drafter-dflash | rtx-3090 | 109.2 t/s | dekod pl-kod T=1; Magnitude, Q8_0 | 2026-10-16
---
# Drafter DFlash2 dla Qwen3.8-27B

**Osobny mały model draftujący (z-lab / incoai, 5 warstw) — świetny na angielski kod przy T=0, ale na szerszym zestawie i po polsku nie bije głowicy MTP, więc domyślnie używamy MTP.**

- Plik: `~/models/draft/Qwen3.8-27B-DFlash2-Q4_K_M.gguf` (1.06 GiB); architektura: 5 warstw, hidden 5120, SWA 2048, selektor top-16, blok 8 (7 draftów), tapy z warstw 5/19/33/47/61 celu.
- Publikowane AL (H200, T=1, thinking xhigh): MT-Bench MTP 3.74 / DFlash2 4.10; GSM8K 5.02 / 5.46.
- U nas:
  - 2026-10-09: upstream DFlash2 n=7 97.7 t/s, nasze kernele n=6 111–112 t/s, z cache q8_1 115.7 (prompty EN); po polsku 65 t/s (MTP 78) — drafter słabo zna polski;
  - 2026-10-10 (zestaw PL/EN, 285 W): przy T=0 mediana DFlash n=6 90.6 vs MTP n=5 86.3; przy T=1 71.9 vs 81.1 (DFlash nie ma rejection sampling); „120 t/s” to był jeden prompt;
  - 2026-10-15 (runda 5): szeroki blok n=15 wolniejszy niż n=6 (EN kod 89.7 vs 104.8 t/s) przy tych samych zaakceptowanych tokenach.
- Pomysł z drafters.md: probabilistyczny wybór ścieżki + rejection w llama.cpp (~40 linii) — szacunek +20–24% na EN czat T=1, niezrobione.
- `run-llm.sh qwen dflash` uruchamia wariant DFlash.

DFlash2 n=15 przy T=1 (runda 5, przeliczone w raporcie 15b): akceptacja rośnie na kodzie (pl-kod 4.21 → 5.67 tok/krok), ale spada na prozie (2.59 → 2.43), a krok rośnie 32.9 → 39.1 ms; średnio 97.9 t/s < MTP 108.8. Artykuł DFlash (Tab. 8): drafter trenowany na b8 testowany na b16 ma niższe τ (np. MT-Bench 3.29 → 3.09). DFlash2 NVIDIA to drafter 8 pozycji; blok 16 to ekstrapolacja.

Magnitude (2026-10-16): DFlash2 27B blok 8 (7 propozycji), okno 2048, Q8_0 2.06 GB; trening DFlash ~800K próbek Nemotron v2 + CodeAlpaca, ≤ 3072 tokenów, bez PL. 3090 T=1: pl-kod 109.2 vs MTP 79.3, pl-proza 30.1 vs 44.9 t/s. Ten sam DFlash2 w naszym forku: 64.0 vs 47.6 ms/krok u Magnitude ([[2026-10-16-magnitude-vs-fork]]).

Następca z tej rodziny: [[drafter-dspine]] (przyczynowy kręgosłup, +3.7…+6.9% τ nad DFlash2 przy tych samych danych).

## Aktualizacja 2026-11-19: DNeo (arXiv 2611.21925, Cerebras; Telegram „gpu”)

- Następca DFlash/DSpark tej samej rodziny (drafter równoległy warunkowany cechami celu). Zmiany:
  - MoFA: koder cech bez „mieszania residuum”;
  - pamięć robocza odrzuconych propozycji;
  - konwolucje 2-tap, cross-attention tylko do prefiksu;
  - nierównomierny wybór warstw celu.
- Wynik autorów: 1,3 × szybciej niż DFlash2 przy tym samym rozmiarze draftera; bezstratnie (standardowa rejekcja). Pomiar na H100, Qwen3-4B, b = 15.
- Wagi: tylko `J-sandler/Qwen3-4B-DNeo`; **brak wersji dla Qwen3.8-27B i brak llama.cpp**.
- Dla nas bez zmian: DFlash2 przegrywa u nas z MTP po polsku i przy T=1 (powyżej). Nawet +30% względem DFlash2 nie gwarantuje wygranej z MTP n4.
- Lekcja treningowa: pamięć odrzuconych propozycji to pomysł niezależny od architektury. Do sprawdzenia przy douczaniu naszej głowicy MTP (akceptacja PL 0,64 na głębokości 1).
- Wraca, gdy pojawią się wagi dla Qwen3.8-27B.

<!-- TABELE:START -->
## Wyniki z notatek (5)

Najlepszy wynik na metrykę z pól `wynik` notatek testów (tools/tabele.py, 2026-11-27); pełna tabela: [[najlepsze-wyniki]].

| karta | metryka | najlepszy | warunki | data | źródło |
|---|---|---|---|---|---|
| NVIDIA RTX 3090 [[rtx-3090]] | dekod pl-kod T=1 | **109.2 t/s** | Magnitude, Q8_0 | 2026-10-16 | [[drafter-dflash]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod EN | **115.7 t/s** | n=6, cache q8_1 | 2026-10-09 | [[drafter-dflash]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod EN kod | **104.8 t/s** | n=6, runda 5 | 2026-10-15 | [[drafter-dflash]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod mediana T=0 | **90.6 t/s** | PL/EN, n=6, 285 W | 2026-10-10 | [[drafter-dflash]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod mediana T=1 | **71.9 t/s** | PL/EN, n=6 | 2026-10-10 | [[drafter-dflash]] |
<!-- TABELE:END -->

## Powiązane
- [[modele/_hub|Modele]]
- [[glowica-mtp]]
- [[latki-oczekujace]]
- [[qwen-runda-5]]
- hipfire
- [[raport-15b-spekulacja-frontier]]
