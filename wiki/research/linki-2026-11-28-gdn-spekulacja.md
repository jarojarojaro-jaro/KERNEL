---
typ: research
tags: [research, linki, spekulacja, gdn, qwen, bonsai, llama-cpp, dfly2]
aktualizacja: 2026-11-28
zrodlo: github ggml-org/llama.cpp issue #32776 (2026-11-22..26, komentarze); arXiv 2611.34776 (DFly2); ~/wt/k207/common/common.h:420-431 (b12811), ~/wt/k047/common/common.h:417-423 (jaroserverai)
status: aktualne
---
# Linki 2026-11-28: spekulacja z drafterem na hybrydzie GDN ×0,41–0,60 (llama.cpp #32776) i DFly2 (delta)

**Żadna topka się nie zmienia: nasze stosy na GDN (Qwen3.8 MTP n4 + lookup, Bonsai MTP n2, przepisy Enigmy z MTP) używają typów, dla których llama.cpp trzyma migawki stanu rekurencyjnego w VRAM; spowolnienie z #32776 dotyczy tylko klasycznego `draft-simple` (osobny model draftu), który przełącza serwer w tryb checkpointów przez RAM hosta. Do playbooka dopisana pułapka; DFly2 bez delty od 26.11.**

## #32776 (llama.cpp, CUDA)
- Pomiar autora (T=0, 160 tok., n_max 3, akceptacja ok. 56%): Qwen3.5-4B + 0.8B ×0,46 (RTX 4070) i ×0,41 (3070); 9B ×0,60; kontrola bez GDN (Qwen3-4B + 0.6B) ×0,82–0,90 przy tej samej akceptacji.
- Mechanizm (komentarz z kodu): `need_n_rs_seq()` w `common/common.h` prosi o migawki stanu tylko dla MTP, EAGLE3, DFlash, DSpark, DFlash2, Lilicorr; dla `draft-simple` cel jest „full-rollback”, serwer co krok serializuje stan GDN do RAM hosta i odtwarza przy częściowej akceptacji. Nsight na GTX 1650: 185 zapisów/odtworzeń, 3,7 GB przesłane, 1,5 s z 5,4 s generacji w checkpointach.
- Łatki badawcze (mathesonlj16-eng, `787a5612`): cofanie bez checkpointu celu + bez zbędnego ponownego dekodu draftu: 51,3 → 79,7 t/s (×1,56 vs stock) na 4070 SUPER, nadal ×0,80 względem dekodu bez draftu (mały cel 4B).
- U nas: w b12811 (`~/wt/k207/common/common.h:420-431`) i w forku k047 (`:417-423`, plus `common_spec_lookup_n_max()`) MTP jest na liście, więc topka Qwena i Bonsai jest poza problemem; Inkling nie ma GDN.
- Lekcja dla nas: przy każdym nowym typie spekulacji na modelu z rekurencją sprawdzić, czy jest w `need_n_rs_seq()`. Hipoteza do sprawdzenia przy następnym podejściu do DSpine (K-197, PR #31941 spoza upstream): część jego −50% na polskim mogła być checkpointem, nie akceptacją.

## DFly2 (arXiv 2611.34776)
- Bez delty względem [[linki-2026-11-26-wieczor]]: abstrakt ten sam (akceptacja +3,9…10,5% vs DSpark ogólnie, +10…31,5% długi kontekst/agenci, przepustowość +62/81% przy 64k). Wymaga celu z natywną rzadką uwagą i indekserem (DS-V4.1-Flash, GLM-5.3-Flash, Hy4 flash); Qwen3.8, Bonsai i Inkling go nie mają, więc nic dla naszych topek.

## Na później
- Gdyby Enigma dostała przepis z osobnym modelem draftu na GDN: najpierw łatki z #32776 (cofanie bez checkpointu) albo tylko MTP.
- DFly2 wraca, gdy weźmiemy model z rzadką uwagą (DS-V4.1-Flash, GLM-5.3-Flash).

## Test u nas
Nie da się dziś: nasze topki na GDN nie używają `draft-simple` (MTP jest objęte migawkami), więc nie ma czego mierzyć; DSpine sprawdzimy przy powrocie K-197.

## Powiązane
- [[rodzaje-modeli]]
- [[gdn-replay]]
- [[qwen3-8-27b]]
