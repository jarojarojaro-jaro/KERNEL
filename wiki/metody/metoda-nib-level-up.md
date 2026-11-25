---
typ: metoda
tags: [metody, proces, optymalizacja, silnik, agenci]
aktualizacja: 2026-11-25
zrodlo: github.com/Chromadera/nib 2e16cf0 (komentarze i nagłówki z pomiarami, scripts/, src/main.cpp); przegląd 3 podagentów 2026-11-25 (NibMethod, NibKernels, OurProcess); pomiary [[nib-chromadera]] i [[bonsai-2-5-uncensored]]; polecenie JARO 2026-11-25 04:26
status: aktualne
---
# Metoda Nib i co zmieniamy u siebie („level wyżej”)

**Nib nie ma jednej magicznej techniki: wygrywa dyscypliną procesu, czyli jeden silnik na jeden model, build w 30 s, każdy wariant za przełącznikiem w runtime, tabela µs na token w nagłówku przy każdej decyzji i poprawność wbudowana w ten sam plik binarny. U nas wiedza o kernelach jest porównywalna, przegrywamy kosztem przejścia od pomysłu do zweryfikowanej liczby.**

## Jak zbudowano Nib (z kodu, historia zgnieciona do 2 commitów)
- **Dziennik kroków w kodzie**: „Step 5 … 7C–7K, 8A–8D”. Każdy krok ma pomiar przed i po oraz werdykt w komentarzu przy fladze. Przykłady: FA v2 124,40 → 127,78 tok/s (`include/kernels_fa_decode_v2.h:107`); MoE v3 przegrywa z dotychczasowym kernelem 130,18 vs 140,72 tok/s przy d=0 i zostaje tylko flagą (`include/kernels_moe_v3.h:116`); fuzja wo+B to −24 węzły grafu, ale ~2 tok/s wolniej, więc też tylko flaga (`src/engine.hpp:83`); `slc dlc` daje 136,51 vs 135,54 (`kernels_fa_decode_v4.h:84`).
- **Księga czasu**: tabele µs/wywołanie i µs/token per kernel w nagłówkach (`kernels_fa_decode_v2.h:7-13`: SWA 483 µs/tok, score 177, topk 108, global 188), z rocprofv3 i `bench -p 0 -n 128 -r 3`. Decyzja zawsze na zegarze całego kroku, nie na mikrobenchu.
- **Każdy wariant zostaje skompilowany i wybierany w runtime** (`--moe-gu-v3 off|auto|alt|ship`, `--fuse-*`, `--fa-swa`, `--fdot2`). Domyślny = zwycięzca A/B, a przegrane warianty zostają jako punkt odniesienia. A/B nie wymaga przebudowy.
- **Poprawność w tym samym binarnym pliku**: tryby `selftest` (prefill vs dekod token po tokenie, cos > 0,999, MTP), `oracle` (zrzut logitów), `ppl`, `bench`, `gen`. Do tego bramka igły 258k, bramka PPL dla wariantów niebitowych (fdot2 tylko flaga, bo PPL 3,6036 vs 3,5788) i KLD 0,0033 do llama.cpp Q8_0. Obserwacja autora: 1 ulp różnicy w tym modelu przesuwa PPL o ~0,05 (`engine.cpp:60-65`), więc bitowość jest bramką wejścia.
- **Narzędzia budowy**: `scripts/spill_audit.sh` (zero spillów VGPR/SGPR/scratch jako twardy warunek), `sim_gpu.sh` (LD_PRELOAD: maska CU i limit VRAM, symuluje 7900 XT / W7800; nie symuluje czasu). Build HIP całego silnika na jaroserverai trwał ok. 30 s (2026-11-25), a topka 4–15 min, Maya ok. 10 min.
- **Architektura**: jeden statyczny graf HIP na token (ok. 290 węzłów), grafy weryfikacji m=1..8 i 4 grafy draftu, occupancy liczona przed capture, bariery międzyblokowe z samoresetującymi licznikami (`kernels_step7i_fused.h:83-135`), repack SoA wag przy ładowaniu (1,6 s), wagi MoE `global_load_b128 slc dlc`.
- **Prawie na pewno praca z agentem** (wniosek z formatu komentarzy „MEASURED/WHY”, numeracji kroków, `/tmp/prof_stepNx` w komentarzach): człowiek ustala bramki, agent pisze warianty i mierzy jednym harnessem.

## Co to znaczy dla nas (zestawienie z naszymi danymi)
- **Czas idzie na koordynację, nie na inżynierię**: FA D256 ~27 h od startu do wyniku przy ~62 min GPU ([[lekcja-czas-optymalizacji-to-metryka]]); noc Bonsai 2026-11-25: 13 rund w ~5 h, z czego dużo kosztowały buildy 4–15 min, kolejka GPU, zombie-serwer, nadpisany skrypt i mikrobench, który kłamał (K-156: 1,9× w mikro, 0% w dekodzie).
- **Ogólny fork zamiast silnika per model**: topka nie znała Hadamarda (port K-151), każda nowa architektura to port, a nie dopisanie kernela. Przy tym Maya ma już graf na token i porównywalne kernele. Nib ma przewagę głównie w tańszym DSparku (graf draftu, szerokość z pewności, top-256 na GPU) i w fuzjach z barierami międzyblokowymi.
- **Przełączniki env już mamy** (GGML_HIP_K150_*, K155, K157 itd.), ale bez księgi µs/token, bez bramki spillów w buildzie i bez trybu oracle/selftest w samym silniku (md5 przez serwer, KLD przez osobny `llama-perplexity`).

## Nowy sposób pracy (od 2026-11-25)
1. **Jedna komenda `perf`** dla silnika: build przyrostowy → spill audit → selftest/oracle (md5 greedy + KLD 40×512 do bazy) → rocprof księga µs/token per kernel z GB/s do sufitu → ABBA e2e (xbench/wall.py) → wpis. Bez ręcznego składania jobów.
2. **Księga czasu modelu** w notatce modelu: każdy kernel, µs/token, bajty, GB/s, % sufitu; każda łatka aktualizuje księgę. Decyzja tylko z e2e.
3. **Każdy wariant w runtime** (nie rebuild na A/B); domyślny = zwycięzca, przegrany zostaje jako flaga z wynikiem w komentarzu.
4. **Silnik per model, gdy model jest ważny** (Inkling, Bonsai/Qwen3.8): krótki build, tylko potrzebne kernele; ogólny fork tylko jako baza i źródło kerneli.
5. **Agenci w pętli kroków**: jeden właściciel worktree na agenta, każdy krok = wariant + pomiar + werdykt; integracja przez jedną gałąź i jedną komendę `perf`; GPU nie stoi, bo builda nie robi się w kolejce.
6. **Metryka procesu**: czas od pomysłu do zweryfikowanej liczby (cel ≤ 1 h na wariant przy buildzie ≤ 2 min) i liczba zweryfikowanych zysków e2e na dobę.

## Szybka pętla eval: liczby (JARO 2026-11-25 04:35: „on robi eval w minuty, my w godziny”)
Typowy wariant nocy Bonsai (2026-11-25): build nowego worktree 8–14 min (przyrostowy 0,5–3 min), job w kolejce na ramię: start serwera z 7,9 GB ok. 20 s + xbench 60–90 s + kopia 60 s + restore :8080 7 s, czyli ABBA 4 ramion 12–15 min, do tego md5/KLD 5 min i ręczne składanie jobów ok. 10 min: **30–45 min na wariant, 1–2 warianty na godzinę.**

Co już mamy, a nie użyliśmy tej nocy: xtxbench z przełącznikami w runtime (`GGML_HIP_RUNTIME_SWITCH_FILE`, jeden serwer, zmiana wariantu w 20 ms bez przeładowania modelu; K-028: koszt haka 0, wariant 0,3 min, cała sesja 0,7 min) i adaptacyjną regułą (WIN/LOSS po jednej parze, gdy |d| ≥ max(5 × szum, 0,5%)).

Plan (cel: ≥ 15 wariantów na godzinę na jednej karcie):
1. **Każdy przełącznik kernela jako przełącznik runtime** (`GGML_CUDA_RT_SWITCH`): hak xtxbench przeniesiony na topka-bonsai + K-150T/K-155/K-157 (`qwen-opt/bonsai25/topka-rtswitch.patch`, `tools/perf/rtswitch_convert.py`, 2026-11-25; do zbudowania na karcie). Wariant = plik z `NAZWA=WARTOŚĆ`, model ładuje się raz na sesję.
2. **xtxbench niezależny od modelu**: profil serwera (model, argumenty, prompty, głębokości) zamiast twardego `run-topka.sh` Qwena (K-163).
3. **Warianty partiami**: agent pisze N wariantów jako przełączniki w jednym buildzie; jeden job GPU przechodzi wszystkie (jak Nib: wszystko skompilowane, wybór w runtime); build tylko przy nowym kodzie i zawsze poza kolejką karty.
4. **Build ≤ 1–2 min**: jeden długożyjący worktree na silnik (nie nowy na każdą łatkę), ccache, mniej instancji FA, łatki w osobnych plikach .cu (ggml-cuda.cu to jeden ogromny plik).
5. **Bramki według kosztu**: md5 z restore w xtxbench przy każdym wariancie (sekundy), KLD tylko dla zwycięzców partii, e2e zawsze, mikrobench najwyżej jako filtr z buforami większymi niż 96 MB Infinity Cache.
6. **:8080 w trybie sesji**: w nocy jedna blokada na cały blok wariantów zamiast stop/restore przy każdym jobie.

## Pilot (K-161, K-162)
- K-161: `tools/perf` dla topki i Mai (punkty 1–3), pierwszy na Bonsai (topka-k157) i Inklingu (Maya): księga µs/token, spill audit, oracle.
- K-162: profil Nib vs Maya kernel po kernelu na XTX (rocprofv3, ten sam prompt), potem port DSpark z Nib do Mai (K-158) w krokach z księgą.

## Powiązane
- [[playbook-optymalizacji]]
- [[nib-chromadera]]
- [[bonsai-2-5-uncensored]]
- [[lekcja-czas-optymalizacji-to-metryka]]
- [[lekcja-mikrobench-klamie]]
