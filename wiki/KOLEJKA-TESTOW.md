---
typ: meta
tags: [meta, kolejka, testy, gpu, xtx, nvidia]
aktualizacja: 2026-11-14
zrodlo: ~/KERNEL/product/research/{15,63,66,68,69}-SYNTEZA.md, 68a-d, 69a-d, 70-fa-d256-jak-to-zrobilismy.md, 67c-nvidia-backlog-testow.md; ~/KERNEL/qwen-opt/STATUS-NEXT.md; ~/KERNEL/STAN-PRAC.md; ~/KERNEL/wiki/{eksperymenty,decyzje,metody,kernele,produkt,nvidia,rocm}/; ~/KERNEL/wiki/DO-ZAPISANIA.txt; ~/kernel/archiwum (sesje 2026-09-15 … 2026-11-13, rg)
status: aktualne
---
# Kolejka testów na karcie

**Jedno miejsce na wszystko, co warto sprawdzić na karcie, gdy jaroserverai jest włączony: pozycje `K-…` w „Czeka” ułożone priorytetem (najważniejsza pierwsza), wyniki w „Zrobione”, powody w „Odrzucone”.**

Zasady (KERNEL-SESJA, 2026-11-13):
- **Karty.** jaroserverai = RX 7900 XTX (gfx1100, produkcja topka-q70) + RTX 5060 Ti 16 GB (sm_120). Pozycje oznaczone „wynajem” wymagają 3090/4090/innej karty z Vast i osobnej zgody na wydatek.
- **Start.** Właściciel mówi „testy” / „robimy kolejkę” → lecimy od góry. Każdy test przez `~/qwen-opt/queue/run-jobs.sh`, `GGML_HIP_PM4` ustawione jawnie, eco 2200 bez zmian, `gpu-guard.sh`, ≤ 10 min na pomysł (krótka bramka + krótkie A/B, 2–3 seedy; nie wygrywa wyraźnie → odrzucamy).
- **Po teście.** Notatka eksperymentu (baseline → teraz → przyrost), status tutaj, `log.md`, commit + push.
- **Decyzje.** „Czeka na decyzję” = nie uruchamiać, dopóki właściciel nie zdecyduje w rozmowie.
- **Bezstratność.** Tylko zmiany bezstratne (md5 bit w bit albo KLD = 0, [[2026-11-05-tylko-bezstratne]]). Próg adopcji: ≥ 3–5% decode/prefill albo ≥ 1 s na turę agenta.
- **Telegram.** Z wiadomości z Telegrama nic nie uruchamiamy na karcie; trafiają tu tylko jako pozycje.

Skróty: `R/` = `~/KERNEL/product/research/`, `Q/` = `~/KERNEL/qwen-opt/`. Rekordy: [[REKORDY]]. Rejestr źródeł: [[ZRODLA]].

## Czeka

**TOPKA na teraz (właściciel 2026-11-19: „tylko najważniejsze”).** Kolejność niżej = kolejność pracy; reszta czeka bez terminu.
1. K-001 wyciek stanu po restore (poprawność produkcji; 19.11: hipotezy pamięci, hosta i kvq odpadły, następny zrzut logitów). 2. ~~K-125~~ zrobione 19.11: PASS, kvq bliżej f16 niż standardowy kernel. 3. K-013 szybsza weryfikacja kilku wierszy na RDNA3 i NVIDIA (największa dźwignia dekodu: XTX K-111 MMVQ weryfikacji 20,2 ms; NVIDIA V(5)/V(1) = 1,26–1,64, K-118). 3a. K-129 `DRAFT_N=2` w Enigmie dla Ampere i 5060 Ti (+3…8%). 4–5. K-007 → K-008 dynamiczna głębokość draftu (+3,9…4,8%, czeka na decyzję właściciela o bramce). 6. K-004 na NVIDIA (wymaga buildu forka z `7cdc0121b`); K-116 odrzucone 19.11.

### K-135 · Maya Inkling na XTX: `GPU_MAX_HW_QUEUES=2` (vllm-redshift: R9700 37,8 → 59,9 t/s)
- data: 2026-11-23 (zwiad; repo abhinand5/vllm-redshift łatka 0101)
- test: XTX, Maya `ik2` produkcyjna konfiguracja (bez cenzury, KV q4, kernele HIP) z i bez `GPU_MAX_HW_QUEUES=2`, rep2 mediana 5 (Q1, Q6 T=0,7, L2k, prefill); ≤ 10 min, tekst bit w bit
- oczekiwany zysk: kilka–kilkanaście % (u nas ~777 launchy, przerwa ~2 µs/launch) [INFERENCE]
- ryzyko karty: brak (zmienna runtime)
- priorytet: wysoki (najtańsza droga do >100 t/s)
- wynik 2026-11-23 13:52–13:58 UTC (ABBA, rep2 mediana 5): bez → z `GPU_MAX_HW_QUEUES=2`: Q6 T=0,7 94,5 / 94,5 → 94,5 / 94,5; L2k 93,3 / 93,6 → 93,5 / 93,6; Q1 93,8 → 93,8–94,0; prefill bez zmian → **0%, odrzucone** (na RDNA3 nie ma kary przełączania kolejki, którą łatka 0101 leczy na RDNA4). Log: `~/qwen-opt/queue/logs/k135-*.log`.

### K-134 · Inkling 2 Mini w Maya v1.1.73 na XTX: 93,6 t/s bez spekulacji (społeczność) vs nasze 49,5 — skąd różnica
- data: 2026-11-22 (zwiad; LocalMaxxing run cmwraqz5108dlmi01cwdleupp, verified, UD-Q4_K_XL)
- źródło: github.com/mw00/project-maya v1.1.73 (silnik Inkling @alesha-pro); [[inkling-2-mini]]
- test: najpierw CPU: przeczytać kernele HIP Inkling w Maya (pętla, MoE, liczba uruchomień na token) i porównać z naszym DUO-INKLING; potem XTX: Maya 1.1.73 tym samym plikiem UD-Q4_K_XL, tg i czat T=0, ≤ 10 min
- oczekiwany zysk: wiedza, które sklejenia dają 2× (cel 93,6 t/s bez spekulacji, ze spekulacją DSpark wyżej)
- ryzyko karty: brak (zwykły dekod)
- priorytet: wysoki
- delta 2026-11-23: Strata v0.2.20 (`strata-inkling` 0.1.66) też uruchamia Inkling na gfx1100: gotowa paczka `strata-inkling-0.1.66-linux-x86_64-hip-rx7900` (96 MB), ładuje nasz plik UD-Q4_K_XL wprost (lossless GGUF_RAW), DSpark „W=4 Markov Beam Tree”; deklaracja 5090: 250,3 t/s z DSpark, XTX bez liczb. Test rozszerzony: Maya 1.1.73 i Strata 0.1.66 tym samym plikiem, bez i z DSpark, ≤ 10 min każde (pobranie ~0,4 GB razem).
- wynik 2026-11-23 01:08 UTC (Strata `strata-inkling` 0.1.66 hip-rx7900, UD-Q4_K_XL `--native`, DSpark `--draft dspark`, `--max-context 32768`, xbench, eco 2200):
  - **krótkie zadania ze zgadywaniem:** Q4/Q5 kopie 100,6 / 109,6 t/s, Q2 136,2, **T=0,7 60,6 t/s**; nasz rekord (2026-11-23, AD-Q4_K): kopie 91,2, T=0,7 26,8 → Strata szybsza o ~10–20% na kopiach i 2,3× przy T=0,7 (inne pliki: UD-Q4_K_XL vs AD-Q4_K);
  - **GPU page fault** przy przejściu do długich promptów (L2048): `[gfxhub] page fault … process strata-inkling` 01:09:20 UTC, bez resetu karty; kolejka zatrzymana, Maya nieuruchomiona, :8080 przywrócony. Według zasady: Straty na XTX nie powtarzamy bez poprawki autora (zgłoszenie z logiem).
  - log: `~/qwen-opt/queue/logs/k134-strata.log`, konfiguracja `~/k134/strata.json` (jaroserverai).
- wynik 2026-11-23 01:19 UTC (Maya 1.1.73 `maya-ik2` zbudowany dla gfx1100, UD-Q4_K_XL, `--drafting on` bez pliku draftera (drafter Mayi wymaga safetensors, nasz GGUF DSpark odrzucony) → przypuszczam: tylko prompt lookup; `--max-context 16384`, KV domyślne; xbench, eco 2200):
  - **kopie Q4 / Q5 112,7 / 100,3 t/s, krótkie Q1–Q3 79–93, T=0,7 80,7 t/s, długi 2k / 8k 80,0 / 72,6 t/s, prefill 2k / 8k 1911 / 3180 t/s**; bez page fault, :8080 przywrócony;
  - vs nasz rekord (AD-Q4_K, DSpark n7): kopie 91,2 → 112,7 (+24%), T=0,7 26,8 → 80,7 (3,0×), długi 2k 73,4 → 80,0 (+9%), prefill 2k 1300 → 1911 (+47%) — inne pliki (UD vs AD), więc kierunkowo;
  - wniosek: Maya bez naszego DSpark i tak 3× szybsza przy T=0,7 → ich dekod/weryfikacja i obsługa T>0 są do przeczytania w kodzie (silnik @alesha-pro), zanim dalej kleimy llama.cpp; następny krok: Maya z oficjalnym drafterem (safetensors, wymaga pobrania) i AD-Q4_K.
  - log: `~/qwen-opt/queue/logs/k134-maya.log`, `~/k134/maya.json` (jaroserverai).
- wynik 2026-11-23 06:10 UTC (Maya po rundzie 2 kerneli HIP, bez cenzury, KV q4): bez draftera → z oficjalnym drafterem: krótkie Q1–Q3 88,8/104,5/102,7 → 98,7/100,5/99,9; kopie 93,4 → 141,4; **T=0,7 94,2 → 79,3**; długi 2k 93,5 → 90,4; prefill 3388 → 3345. Czat domyślnie T=1,0 → produkcja :18796 bez draftera (T=0,7 94,2–94,5, długi 2k 93,5 t/s).
- wynik 2026-11-23 04:02 UTC (Maya bez cenzury + KV q4, oficjalny drafter `mtp.safetensors` 0,6 GB z thinkingmachines/Inkling-2-Mini, xbench): bez → z drafterem: krótkie czaty Q1–Q3 T=0 75,4/88,0/80,7 → 93,1/90,3/78,8; kopie 103,3/97,1 → 129,7/131,8; **T=0,7 76,9 → 65,3 (−15%)**; długi 2k / 8k 73,5/72,4 → 78,2/76,7 (+6%); prefill 2k 3398 → 3346. Domyślna temperatura modelu to 1,0, więc w czacie drafter szkodzi → produkcja :18796 zostaje bez draftera. Dla porównania Qwen produkcja xbench (eco): Q1–Q3 T=0 121,6/139,3/139,6, T=0,7 79,0, prefill 2k 861. Odniesienie autora (README alesha-pro/maya-inkling-mini): RTX 3090 dekod bez draftera 128 t/s, u nas na XTX ~82 → ścieżka ekspertów HIP (skalarna, `ik2_main.cu:2448-2452`) to główna dźwignia.
- wynik 2026-11-23 01:28–01:31 UTC (polecenie właściciela 02:27 CET: Maya z unsloth i AtomicChat, najszybsze runy):
  - **AtomicChat AD-Q4_K w Mayi nie działa:** `maya-ik2: blk.0.ffn_gate_up_exps.weight: type Q4_K not decoded here` (Maya nie ma kernela Q4_K dla ekspertów), oba tryby (`on`, `auto`);
  - unsloth UD-Q4_K_XL `--drafting on` (powtórka): kopie 111,6 / 99,8, T=0,7 80,6, długi 2k / 8k 77,8 / 74,0 t/s, prefill 3398 / 3183 t/s;
  - `--drafting auto` (Maya sama mierzy, co szybsze): kopie 80,1 / 80,4, T=0,7 82,0, długi 2k / 8k 78,2 / 74,7 t/s → `on` lepsze na kopiach o ~39%, przy T=0,7 i długich równe;
  - po testach Maya (unsloth, `--drafting on`) uruchomiona jako czat właściciela na :18796 (`~/k134/mayaserve.sh`, trzyma blokadę GPU, :8080 wyłączony, stop: `touch ~/k134/STOP-MAYA`).

### K-133 · Inkling 2 Mini (MoE z pętlą warstw, 26,4B / 5,4B efektywnie aktywnych) na XTX: prędkość i jakość vs Qwen3.8-27B
- data: 2026-11-20 (Telegram właściciela 23:29)
- źródło: [[inkling-2-mini]], HF `unsloth/Inkling-2-Mini-GGUF`, mainline llama.cpp `src/models/inkling2.cpp`
- test (po zgodzie na pobranie ~16,6 GB):
  - CPU: build mainline llama.cpp HIP (topka nie zna architektury);
  - XTX: `llama-bench -p 512,2048 -n 64 -fa 1` dla UD-Q4_K_M;
  - XTX: czat T=0 na tych samych promptach co xbench i szybki EvalPlus (jakość-mini) vs Qwen3.8-27B; ≤ 10 min GPU.
- oczekiwany zysk: dekod ~150–170 t/s vs 42 t/s Qwen bez spekulacji [INFERENCE: ~3,3 GB odczytu na token]; jakość według producenta jak Qwen3.8-27B (AA 20,1)
- ryzyko karty: brak (zwykły dekod, eco 2200)
- priorytet: wysoki (decyzja o modelu produkcyjnym należy do właściciela)
- stan 2026-11-22 04:20 (STOP na polecenie właściciela): build r8+r9 gotowy na jaroserverai, bramka r8/r9 nieuruchomiona (kolejka zabita w oczekiwaniu); wznowienie: `qwen-opt/inkling/start-r8.sh`. Szczegóły: `DUO-INKLING.md` (llama-inkling).
- czeka 2026-11-23: runda 15 Gemini (`LLAMA_INK_SRV_FAST=1`: stały graf zwykłego kroku, top-k na GPU zamiast sortu 200k na CPU, bez buforów DSpark w zwykłych krokach; cel: zabrać ~7,8 ms narzutu serwera na słowo) — niezmierzona, bramka gotowa: `qwen-opt/inkling/start-r15.sh` (~25 min karty).
- wynik 2026-11-23 16:00 UTC (r14, nasz llama.cpp): wagi nietemporalne +1,7% (tg128 58,4, razem +17% od bazy, KLD 0); kontroler zgadywania nadal przegrywa: w serwerze zwykły krok 24,9 ms vs 17,1 ms w llama-bench (+46% narzutu serwera) → r15 szuka tego narzutu. Najlepszy nasz czat: DSpark bez kontrolera, długi 8k 67,2 t/s; T=0,7 24–41 t/s. Produkcja Inkling = Maya (T=0,7 104,3).
- wynik 2026-11-23 14:50 UTC (r13, nasz llama.cpp, KV q4_0): KLD 0 dla wszystkich; tg128 50,0 → 57,5 (+15%) z wszystkimi; DSpark naprawiony (akceptacja 0,61): długi 2k 61,8 → 64,6, 8k 56,7 → 68,7 (+21%), T=0,7 28,1 bez zmian → r14 (kontroler + losowanie draftu).
- wynik 2026-11-23 05:20 UTC (r12, nasz llama.cpp, KV q4_0): wszystkie przełączniki KLD 0; tg128 49,9 → 53,7 (+7,6%) z wszystkimi; DSpark z wszystkimi nadal 0/413 (błąd na ścieżce n=1/n=8) → r13; najlepszy serwer (bez przełączników r11/r12) kopie 95,4, T=0,7 28,2, długi 2k 61,7 t/s. Produkcja Inkling = Maya (czat T=0,7 91,3 t/s).
- wynik 2026-11-23 03:50 UTC (r11 port Mayi, KV q4_0): nasz llama.cpp z KV q4_0 + DSpark n7: kopie 95,2, T=0,7 28,0, długi 2k 61,7 t/s; STABLE_GRAPH neutralny (KLD 0); FUSE4 wolniejszy (tg 49,5 → 42,4) i KLD 0,0077; PLANAR_Q8 nie jest bezstratny (KLD 0,0081, błąd); wszystkie razem psują DSpark (akceptacja 0/413) → runda 12 naprawia.
- wynik 2026-11-23 02:27 UTC (r10, kontroler spekulacji `LLAMA_SPEC_CTL=1`, AD-Q4_K, DSpark n7): T=0,7 26,8 → 35,9 t/s (+34%), kopie z ngram 91,2 → 96,9 (+6%), ale długi 2k 73,4 → 53,9 (−27%); ub 2048 OOM (bufor 12,15 GiB). Do poprawy w r11/r12.
- wynik 2026-11-23 01:00–01:10 UTC (zgoda właściciela 01:57 CET; r8 + r9, `inkling-opt` 854c58e, eco 2200, AD-Q4_K, DSpark n7, `-c 16384`):
  - FUSE3 naprawiony: KLD 4,68 → 0,0022 (PPL ×1,0001), md5 PM4 0/1 równe;
  - **rekord ze zgadywaniem:** kopie 84,6 → **91,2 t/s** (+7,8%, FUSE3 wył. → wł., ta sama sesja), długi 2k 67,4 → 73,4 (+8,9%), 8k 59,0 → 66,8 (+13%), T=0,7 24,9 → 26,8; prefill 2k 994 → 1300 t/s (+31%);
  - losowanie draftu (`--spec-draft-sampling probabilistic`) nie podniosło akceptacji przy T=0,7 (0,55, T=0,7 nadal ~27 t/s) — do zbadania;
  - PM4 z DSpark: 68,8 t/s (−25% vs bez PM4) mimo VEC FA; r9 MEGA: 46,2 t/s (−33%) → odrzucony;
  - z `-c 32768` serwer z FUSE3 i DSpark nie startuje (OOM 508 MiB): FUSE3 trzyma dodatkową kopię wag atencji;
  - logi: `~/qwen-opt/queue/logs/ink-r8-*.log`, `ink-r8b-*.log`, `ink-r9*.log`.
- wynik 2026-11-21 (XTX eco 2200, AtomicChat AD-Q4_K, stock PR #32695 6196d98):
  - llama-bench: pp512 1333, pp2048 1125, **tg64 26,9 t/s**;
  - czat xbench: dekod ~26 t/s (krótkie i długie prompty), prefill 887 t/s przy 2k i 537 t/s przy 8k;
  - **szacunek [INFERENCE] 150–170 t/s był błędny o ~6×:** dekod ograniczają ~7700 uruchomień kerneli na token, nie pasmo;
  - Gemini INK_FUSE: 26,9 → 30,8 t/s (+14,5%), ale zmienia tekst (KLD w toku);
  - PM4: tapa odrzucona (kernel rocBLAS w grafie), −20%;
  - DSpark nie wczytuje się z AtomicChat (słownik 200058 vs 201024);
  - log: `DUO-INKLING.md` (llama-inkling), kolejka `ink-ad-*`, `ink-r2-*`.
- wynik 2026-11-21 08:00 (runda 3 Gemini):
  - INK_FUSE + INK_FUSE2: tg64 26,85 → 37,31 t/s (+39%); KLD 0,0024 do wersji bez sklejeń, PPL bez zmian (max KLD 1,61 do sprawdzenia);
  - UD-Q4_K_XL się wczytuje: tg64 28,6 → 39,7 t/s (+39%), czat ~38 t/s;
  - DSpark nadal czeka na rundę 4.
- wynik 2026-11-21 08:25 (runda 4):
  - taśma PM4 działa po usunięciu kernela rocBLAS (NOBLAS): 1 taśma, 3925 dispatchy, tekst bajt w bajt;
  - tg64 37,35 → 43,0 t/s (+15%), od stocku 26,85 → 43,0 (+60%); rozrzut ±2,5;
  - DSpark: nowy błąd (markov_w2 wymagany), runda 6.
- wynik 2026-11-21 08:45 (runda 5): FUSE3 daje tg64 42,3 → 58,0 t/s (+37%), ale psuje model (KLD 4,68, PPL ×114, tekst bez sensu) → wyłączone, Gemini szuka błędu (runda 7); do produkcji tylko z KLD PASS.
- wynik 2026-11-21 09:05 (runda 6):
  - czat bez zgadywania stabilnie 47,6–50,3 t/s (stock 26,0–27,1, +85%);
  - DSpark działa (akceptacja 0,83 przy 3 tokenach, 0,55 przy 7), ale jest wolniejszy od czatu bez zgadywania (39 / 53 t/s na kopiach, 21–22 t/s przy T=0,7);
  - przyczyna: grafy weryfikacji bez taśmy PM4 i 170 ms na każde tworzenie grafu.
- wynik 2026-11-21 09:30 (diagnoza Kernela):
  - najlepsze dziś ustawienie ze zgadywaniem to DSpark z 7 tokenami draftu bez PM4: kopie 85 t/s, długi prompt 2k 67,7 t/s, T=0,7 26,4 t/s (Qwen w produkcji: 252 / 97,5 / 79);
  - PM4 psuje zgadywanie, bo kernel atencji przy weryfikacji używa scratch i taśma jest odrzucana;
  - FUSE3: błąd w pakowaniu wag q/k/v (KLD 4,68 → 0,139 po wyłączeniu), drugi mniejszy błąd do znalezienia; runda 8 Gemini startuje o 11:25.

### K-129 · Enigma NVIDIA: `DRAFT_N=2` zamiast 4 na Ampere i 5060 Ti (droga weryfikacja V(5))
- data: 2026-11-19
- źródło: [[2026-11-19-k118-nvidia-pelna-moc]]: n2 vs n4 T=1 3090 +7,9%, 3060 +4,3%, 5060 Ti +3,2% (K-114); T=0 +3,0…3,3%; 4080 SUPER bez różnicy
- test: CPU: wpis w `app/engine/data/engines.json` (DRAFT_N per architektura: sm_86 i sm_120 → 2, sm_89 → 4), `bun test`; potwierdzenie na 1 karcie Vast z md5 T=0 vs n4 (spekulacja bezstratna, tekst może się różnić tylko numerycznie)
- zysk: +3…8% dekodu dla użytkowników Enigmy z 30xx i 5060 Ti
- ryzyko karty: brak
- priorytet: wysoki (tanie, zmierzone na 3 kartach)
- wynik 2026-11-20: zrobione po stronie CPU. W profilu `qwen38-kvq-mtp4` silnika `enigma-cuda-fork` doszło `mtp.nMaxByArch` (`app/engine/data/engines.json`: sm_86 → 2, sm_120 → 2, reszta, czyli sm_89, zostaje 4); `mtpArgs`/`enigmaConfig` biorą n po architekturze karty (`app/engine/src/server/engine.ts`, wywołanie w `optimize.ts`). Test w `app/engine/test/enigma-cuda.test.ts` (sm_86/sm_89/sm_120 → 2/4/2); `bun test` 208 pass, 0 fail; `tsc` czysty. Planer pamięci dalej liczy draft dla n 4 (bezpieczny zapas). Uwaga: RTX 5090 (też sm_120) mierzona była tylko z n 4, więc dostaje 2 bez pomiaru. Zostaje potwierdzenie md5 T=0 n2 vs n4 na 1 karcie Vast.

### K-001 · Naprawić wyciek stanu przy drugim restore slotu (drugi restore na tym samym serwerze ≠ świeży prefill)
- data: 2026-11-09 (ten sam objaw w `det_probe` 2026-10-14)
- źródło: [[2026-11-08-kvq-once-profil]] (`:81-82`), [[lekcja-ten-sam-serwer-pending-h]], `R/68-SYNTEZA.md:31`, `Q/xtxbench/README.md:79-85`; podejrzany niezresetowany kontekst draftu MTP / stan GDN / `pending_h` (por. upstream #30574, `Q/patches/topka-q63/0003-*`)
- hipoteza (2026-11-14): upstream #30541 (w llama.cpp v1.0.0) naprawia kopię stanu „on device” dla skwantowanego KV: liczba elementów liczona jako bloki, więc dla q4_0 kopiowane było 1/32 zakresu → zły stan po restore. Topka (baza b11528) tej poprawki nie ma, a my mamy KV q4_0 [INFERENCE: czy ścieżka `LLAMA_STATE_SEQ_FLAGS_ON_DEVICE` jest używana przez cache/checkpointy topki — sprawdzić w kodzie na CPU przed testem] ([[telegram-2026-11-14-pearlquant-llamacpp-v1]])
- test: najpierw repro na CPU (LFM2.5-2.6B pokazał wzór przy 0,6k). Potem XTX, port testowy, `run-topka.sh uncensored`: restore migawki 1,7k → md5 T=0 → inne żądanie → drugi restore → md5, porównanie z `md5_fresh` (xtxbench t1 A/A). Bez 199k ≤ 10 min.
- zysk: poprawność, nie szybkość. Cachesave i `--cache-ram` odtwarzają wpisy w sesjach agenta, więc produkcja może dziś po cichu zmieniać odpowiedzi. Bez naprawy werdykty md5 xtxbench są pewne tylko przy pierwszym restore.
- ryzyko karty: brak
- priorytet: wysoki (bezstratność produkcji)
- wynik 2026-11-14: wzór R1 = R1b = świeży (3f26f79c), R2/R3/F2 inne; identyczny przy `LLAMA_SPEC_LOOKUP=0`, `LLAMA_SPEC_COUPLED=0`, `GGML_HIP_PM4=0`, a F2 (bez restore) też się różni → to zależność od historii serwera, nie od pliku slotu ([[2026-11-14-k001-wyciek-stanu-restore]]). #30541 odpada (topka nie używa `FLAGS_ON_DEVICE`).
- wynik 2026-11-19 ([[2026-11-19-k125-k001-xtx]]): build z logiem `LLAMA_K001_LOG` (gałąź `k001-log`). Przesunięcie komórka − pozycja = 0, `used_max_p1 == used`, `n_kv` i komórka GDN takie same w R1 i R2, więc **pamięć odpada**. Wzór jest identyczny przy `CACHE_RAM=0` i `LLAMA_CKPT_VRAM=0` (**host odpada**) i przy `GGML_HIP_KVQ_OFF=1` (F c141fb1d, R2 = F2 = 3f26f79c), więc **kernel atencji odpada**. Zostają GPU-owe bufory poza KV/GDN (pula, scratch, przechowywany graf) i `common_speculative`.
- zwiad 2026-11-20: błąd ik_llama `06a141f3b` (restore po odrzuceniu nadpisuje pozycję komórki atencji w hybrydzie) sprawdzony — topka-q70 nie ma tej ścieżki, odpada
- następny test: zrzut top-2 logitów pierwszych ~40 kroków R1 vs R2 (`LLAMA_K001_LOG` + `n_probs`): pierwszy rozjazd i jego wielkość (1e-6 na remisie = kolejność redukcji; duża = niezainicjowany stan); jeden job ≤ 5 min
- wynik 2026-11-20 (`qwen-opt/k001/k001c.py`, run `1120-162340-k001c-probs`): md5 bez `n_probs` znów R1 3f26f79c ≠ R2 2a48020a; tekst R1 = R2 do tokenu 216, rozjazd na 217. **Już pierwszy token po restore ma inne prawdopodobieństwa: top-1 „Based” logprob −0,483 (R1) vs −0,565 (R2), drugi „Here” −0,988 vs −0,863 — różnica 0,08, nie poziom remisu.** F = R1 co do bitu. Czyli logity dopełnienia promptu po restore zależą od tego, co serwer liczył wcześniej → stan nieustawiony przez restore albo bufor czytany przed zapisem (nie kolejność redukcji). `n_probs` daje prawdopodobieństwa tylko dla tokenów spoza draftu (2 z 256), więc dalej porównujemy logity pierwszego tokenu.
- wynik 2026-11-20 bisekcja (`k001d.py`: restore → logprob 1. tokenu → restore → to samo, bez niczego pomiędzy): **przeciek zależy tylko od długości dopełnienia promptu po restore**. Delta 1, 2, 5, 8, 16, 17, 24, 32, 48, 64, 128, 256 tokenów: R1 = R2 co do bitu; **delta 31 i 33 (dwa różne teksty): R1 ≠ R2** (np. „Based” −0,4830 vs −0,4808). Ten sam wzór z `GGML_CUDA_DISABLE_GRAPHS=1`, `GGML_HIP_PM4=0` i `GGML_HIP_KVQ_OFF=1`, a typ zakłócenia (czat, prefill 300, dekod 64, nic) nie ma znaczenia. Nawet R1 przy delcie 33 zależy od wcześniejszych żądań na tym serwerze. Wniosek: jakiś kernel prefillu przy n_tokens 31/33 (kafel 32 niepełny albo z jednym tokenem) czyta pamięć sprzed żądania — kandydaci: conv GDN (`gdn_conv_ab`), MMQ/quantize z paddingiem, FA prefill. Zadanie dla duetu: Gemini szuka w kodzie, Kernel `test-backend-ops` z n=31/33 i buforami wypełnionymi śmieciami.
- wynik 2026-11-20 wieczór, **przyczyna zlokalizowana** (gałąź `duo`, narzędzia debug `GGML_CUDA_HASHDUMP` / `GGML_CUDA_POISON`; szczegóły `~/praca/llama-duo/K001.md`):
  - Serwer liczy deltę 33 tokenów jako dwa ubatche, 29 + 4.
  - Hashe wyjść wszystkich węzłów grafu 29 tokenów, R1 vs R2: pierwszy prawdziwy rozjazd to **FLASH_ATTN_EXT w warstwie 3** (pierwsza warstwa pełnej atencji).
  - Q i maska są identyczne. Maska jest poprawna: wiersz 0 odsłania kolumny do 1712, wiersz 28 do 1740.
  - K/V w oknie n_kv = 1792 różnią się tylko w zamaskowanych komórkach 1741–1791, czyli w starych danych poprzedniego żądania.
  - Wniosek: **kernele FA dopuszczają, żeby zamaskowane, stare komórki K/V zmieniały wynik** (o 0,002–0,07 logprob, bez NaN), i dotyczy to i kvq, i kernela standardowego.
  - Wykluczone: pula pamięci (`POISON=3` bez zmian), stan GDN (wejścia GDN_LAG identyczne), `LLAMA_GDN_REPLAY=0`, `LLAMA_CONV_LAG=0`.
  - Poprawkę w kernelu FA (maska przed max/exp, pomijanie w pełni zamaskowanych kafli) plus test `test-backend-ops` ze śmieciami w zamaskowanym ogonie robi Gemini (runda duo-r3); Kernel mierzy.
- wynik 2026-11-20 ~20:15, **poprawka Gemini r3 (llama-duo `556ad79`) zmierzona na XTX**:
  - przeciek zniknął: wszystkie 6 przypadków dopełnień identyczne co do bitu przy ponownym wczytaniu (wcześniej 4 przeciekały);
  - hashe K/V co 64 komórki: R1 i R2 różniły się tylko w bloku zamaskowanych starych komórek;
  - jakość: KLD przy ub 512 identyczne z wersją sprzed poprawki (prefill bit w bit), przy ub 5 PASS (+0,09 sd);
  - prędkość: pp512 −0,2% (szum), pp2048 1021,2 → 1014,5 t/s (−0,65%), tg64 +0,2%;
  - otwarte: ścieżka kvq przy 1 zapytaniu (dekod) nadal przecieka (test jednostkowy: błąd 2e-9); naprawa i odzyskanie −0,65% prefillu to runda duo-r4;
  - wdrożenie do produkcji (przebudowa topki) czeka na decyzję właściciela.

### K-013 · Tańsza weryfikacja 2–24 kolumn (MTP n=5 i lookup W16): port kernela „few-row” upstream #31533 na RDNA3 (iu8 WMMA)
- data: 2026-11-07
- źródło: `R/68d-swieze-od-spolecznosci.md:140`, `R/69-SYNTEZA.md:30` (W3), [[2026-11-09-qwen-warp-vs-fork-3090]] (pkt 3), `R/67c-nvidia-backlog-testow.md:131` (C14)
- test: XTX `llama-bench -fa 1 -ctk q4_0 -ctv q4_0 -p 1,5,8,9,16 -n 0 -d 2048,32768` przed/po (krzywa V(w)), potem `mvs` + czat ABBA i md5; ≤ 10 min. NVIDIA: `test-backend-ops MUL_MAT` n=8/16 na 5060 Ti.
- nowe (2026-11-14): #31533 scalone w llama.cpp v1.0.0. Na NVIDIA spec-dec Qwen3.8-27B +16,7…34,9% tok/s (3090 Ti 57,6 → 77,7), KLD jak master; port HIP (`6ad15f48`, am17an) na RDNA3.5 z DFlash2: 21 → 37 tok/s. Weryfikacja MTP n=5 (5 kolumn) też w zakresie 2–24. Inny kernel = inna kolejność sum, więc md5 T=0 się zmieni: wdrożenie na XTX wymaga bramki K-007 albo decyzji właściciela.
- zysk: V16 − V5 = 6,4 ms przy 2k; połowa tego → kroki W16 −9%, tury agenta z kopiowaniem +5…10% [SZACUNEK]; czat 0. Warunek dla drzew (K-075).
- ryzyko karty: nowy kernel w PM4
- priorytet: wysoki (zmierzone +17…35% u autora, ten sam model)
- baseline 2026-11-14 (produkcja, r=3): V16 − V5 = 7,1 ms przy 2k, 10,1 ms przy 32k; V5 26,8 / 28,3 ms ([[2026-11-14-k002-k003-k013-xtx]]); port HIP #31533 jeszcze niezbudowany
- (zakończone) build upstream 6ad15f48 (#31533 + port HIP RDNA3 WMMA; Q4_K/Q5_K/Q6_K/Q8_0/IQ4_NL) dla gfx1100 na jaroserverai (`~/wt/fewrow-hip`, cpuheavy 2 rdzenie), potem automatycznie job kolejki `k013-fewrow` (V(w) na tym samym modelu) przez `~/qwen-opt/k013/after-build.sh`; wynik w następnej turze
- wynik 2026-11-14 (całe silniki, nie sam kernel): upstream 6ad15f48 z few-row MMQ HIP vs topka-q70, `llama-bench -p 1,5,8,9,16 -d 2048,32768`: V5 26,8 → 37,9 ms (+41%), V16 33,9 → 47,0 (+39%) przy 2k; V1 też +3…31% → upstream bez naszych łatek jest wolniejszy, więc few-row nie jest szybszy niż nasza ścieżka weryfikacji. Do rozstrzygnięcia tylko poziom kernela: `test-backend-ops perf -o MUL_MAT` (q4_K, n 5/8/16) obu buildów ([[2026-11-14-k002-k003-k013-xtx]])

- wynik 2026-11-20 (kernel, `test-backend-ops perf -o MUL_MAT`, m 4096 k 14336, XTX eco 2200, `qwen-opt/k013/kern.sh`), nasz fork (duo) vs upstream few-row (`~/wt/fewrow-hip`), µs na wywołanie:
  - Q4_K: n=1 35,6 vs 39,1; n=2 38,1 vs 56,6; n=4 42,6 vs 57,3; n=5 46,0 vs 57,3; n=8 50,9 vs 57,6. **Nasz kernel wygrywa przy każdym n (−9…−33%).**
  - Q6_K: n=1 33,7 vs 29,1; n=2 56,5 vs 42,4. **Few-row wygrywa przy n = 1–2 (−14% / −25%).** Przy n=4 60,9 vs 66,9 i n=5 64,5 vs 83,2 wygrywamy my.
  - Werdykt: całego few-row nie bierzemy. Jedyna dźwignia to jego układ dla Q6_K przy n ≤ 2 (dekod i draft), do przeniesienia w duecie.
### K-007 · Bramka „wymuszanie tokenów + KLD” (SpecPilot) zamiast md5 dla zmian polityki draftu i szerokości weryfikacji, z kalibracją kanarkami
- data: 2026-11-07 (kanarki: 2026-10-15)
- status: **czeka na decyzję** właściciela (decyzja 6 z rundy 69: czy dopuścić „te same tokeny + KLD” zamiast md5)
- źródło: `R/68b-spekulacja-nowe.md:161`, `R/69-SYNTEZA.md:33,41`, [[raport-69-synteza]], [[bramka-kld-kanarki]] (`:27`, nigdy nieuruchomione na GPU), `Q/tools/kld_canary.sh`
- wzór oceny (2026-11-14): PearlQuant ma 3 warstwy: KLD, benchmarki, cechy tekstu (liczba „Wait” na 1000 słów, ślepy sędzia = sam model), a do tego celowo zepsute konfiguracje jako kontrola pozytywna ([[telegram-2026-11-14-pearlquant-llamacpp-v1]])
- test: skrypt teacher-forced na CPU. XTX: topka vs topka (szum), DRAFT_N=5 (powinno przejść), wstrzyknięty bias logitu (musi odpaść), 6 promptów × 2k tok. T=0. Kanarki po jednym na job ≤ 10 min.
- zysk: 0% sama; odblokowuje K-008, K-017 i K-046 (+3…7%)
- ryzyko karty: brak
- priorytet: wysoki (odblokowuje największy bezstratny decode)

### K-008 · Dynamiczna głębokość draftu MTP z luki Gumbela z wczesnym wyjściem z łańcucha (dmin 2, dmax 5)
- data: 2026-10-10 (zmienna długość draftu), 2026-11-07 (68b #1)
- status: **czeka na decyzję** (bramka K-007; zmienna szerokość weryfikacji zmienia md5 T=0, choć rozkład jest zachowany)
- źródło: `R/68b-spekulacja-nowe.md:160,164`, `R/68-SYNTEZA.md:17`, `R/40-akceptacja-prozy.md:116` (proza `DRAFT_N=3` +4,3%, 82,4 vs 79,0 t/s, 8/8 promptów), [[lekcja-glebokosc-zmienia-tekst]]
- test: XTX, `spec_sweep.sh "LLAMA_SPEC_DEPTH_GAP=0" "LLAMA_SPEC_DEPTH_GAP=2"` T=1, ABBA po 2 ramiona na job; xtxbench 1,7k/94k/199k
- zysk: symulacja +3,9% ogółem, czat PL +4,8%, EN +2,9%; bez wczesnego wyjścia ~0
- ryzyko karty: PM4 (warunkowe wyjście w taśmie draftu)
- priorytet: wysoki (największy bezstratny zysk decode, PL najwolniejszy: 120 t/s)

### K-004 · Fork CUDA: dokładne próbkowanie spekulacyjne na GPU przy T=1 (jak qwen-warp)
- data: 2026-11-09
- źródło: [[2026-11-09-qwen-warp-vs-fork-3090]] (pkt 2: fork traci przy T=1 7–13%, warp nie traci), `R/69b-tensorfold-qwen-warp.md` §3
- **poprawka planu (audyt 2026-11-19):** wydany fork `kvqlean`/`kvqleana` (cuda-topka2 + kvq `007a6f813`) **nie ma** sprzężonego próbkowania `7cdc0121b`, więc `LLAMA_SPEC_COUPLED` 0/1 na nim nic nie zmieni [INFERENCE: potwierdzić `strings llama-server | grep LLAMA_SPEC_COUPLED`]. Zmierzone sprzężone na CUDA: +5,3…5,5% (3060/3080, `31-3060-3080.md:146`), +5,4% (4060 Ti), 5060 Ti +1,9% z CI [−4,9; +8,3]. Strata „7–13%” to spadek T=0 → T=1 z akceptacji (K-114), nie cały do odzyskania
- test: (1) CPU: build kvqlean + merge `7cdc0121b` (merge-tree bez konfliktów), `test-backend-ops`; (2) 5060 Ti (Vast + hostguard) spec_sweep T=1 ABBA COUPLED 0/1, 6 promptów × seedy 1–4, md5 T=0 6/6; (3) dopisać `LLAMA_SPEC_COUPLED=1` do profilu Enigmy dopiero z nową binarką. Stary plan: Po porcie: ABBA 6 × 3 seedy, md5 T=0 bez zmian; potwierdzenie na 3090 (wynajem, metoda `nv69q`).
- zysk: +5…5,5% przy T=1 na NVIDIA (zmierzone na sm_86/89); wszyscy użytkownicy Enigmy z NVIDIA
- ryzyko karty: brak
- priorytet: wysoki (Enigma NVIDIA, tani pierwszy pomiar)
- zwiad 2026-11-14: tqLLM 1.5.0 robi dokładne próbkowanie MTP przy T>0 (3090, T=0,7: 50 → 104–117 t/s), wzór do portu ([[zwiad-2026-11-14]])

### K-117 · Fork CUDA: cache skwantowanej głowicy draftu i MTP (`LLAMA_MTP_REQUANT_CACHE` jak na XTX) — start na słabym CPU 12 min → sekundy
- data: 2026-11-17
- źródło: [[2026-11-17-k114-nvidia-sufit]] (host 3090 TW: 12 min od „initializing” do gotowości; 5060 Ti na 64 rdzeniach 32 s); XTX: start 39,8 → 6,5 s z cache ([[REKORDY]])
- hipoteza: port przełącznika z topki do forka CUDA (kod w `common/`, nie w kernelach) skraca każdy kolejny start do < 10 s; bitowo te same wagi draftu
- test: CPU (budowa) + dowolna karta NVIDIA: start zimny vs ciepły, md5 T=0 identyczne
- miara: s do `/health` przy drugim starcie
- zysk: start Enigmy na NVIDIA ze słabym CPU: minuty → sekundy (UX, 0 t/s)
- ryzyko karty: brak
- priorytet: średni

### K-119 · SenseNova-Loop-9B: pobrać i sprawdzić, jak naprawdę działa (jakość, zachowanie, prędkość), bez optymalizacji
- data: 2026-11-17
- **cel (właściciel 2026-11-17 18:17):** „nie wszystko musimy optymalizować, wysłałem, żebyśmy pamiętali, pobrali i przetestowali, jak to rzeczywiście wygląda”. Najpierw zwykły test modelu: odpowiedzi PL/EN, kod, narzędzia, długi kontekst, obraz. Prędkość mierzymy przy okazji, bez kerneli
- źródło: [[sensenova-loop-9b]] (sufit bez spekulacji ~2,1 × Qwen3.8-27B: 5060 Ti 58 vs 28 t/s, 3060 47 vs 22; jakość wg producenta NL2Repo 41,36 vs 44,60, AIDABench 65,31 vs 65,01); llama.cpp #31571 otwarte, łatany build AtomicChat (GGUF Preview)
- hipoteza: na 12–16 GB Loop-9B Q4_K_M (~5,3 GB) z KV q4_0 przy 128–256K jest szybszy niż obecne przepisy (5060 Ti 51 t/s z GSQ IQ3_XXS + MTP; 3060 Bonsai 58 t/s) przy jakości ≥ 90% Qwen3.8-27B w naszej bramce (EvalPlus HE+, jakość-mini)
- test: najprościej, czym działa dziś: oficjalne AWQ 4-bit (~4,9 GB) w SGLang (PR #47281) albo vLLM na wynajętej karcie ≥ 16 GB z hostguardem, albo GGUF Preview z łatanym llama.cpp, gdy obsługa trafi do upstream. Sprawdzić: (1) ręczny panel 10 promptów PL/EN (rozmowa, kod, narzędzia, obraz) z wyjściami w notatce; (2) jakość-mini + EvalPlus HE+ vs Qwen3.8-27B (92,7 / 87,9%); (3) igła 128k; (4) t/s i % sufitu przy okazji. Wagi są gated na HF (trzeba zaakceptować warunki na koncie)
- miara: t/s i % sufitu, HE+ i jakość-mini vs 92,7 / 87,9% (Qwen3.8-27B Uncensored)
- zysk: Enigma 8–16 GB: do ~2 × dekodu w zasięgu sufitu, kontekst 256K w 12 GB [INFERENCE]; zmiana modelu = decyzja właściciela
- ryzyko karty: brak (wynajem)
- zegar (2026-11-18): znaczniki etapów od pobrania do tabeli „zmierzone vs sufit”, wiersz „czas: ściana / GPU / najwolniejszy etap” ([[lekcja-czas-optymalizacji-to-metryka]])
- priorytet: średni (prośba właściciela; koszt wynajmu ~$0,10–0,20, czeka na kredyt)

### K-120 · Qwen3.8-27B-pi-adapted (LoRA RL pod pi) w naszym stosie: czy pomaga w omp, ile kosztuje w dekodzie, co z MTP
- data: 2026-11-18
- źródło: [[qwen38-27b-pi-adapter]] (pod pi: SWE-bench Pro hard 51 29,4 → 62,7%, Terminal-Bench 2.1 39,5 → 55,8%, −55…62% wywołań narzędzi); adapter GGUF F16 dla llama.cpp (`--lora`)
- 2026-11-18: doszedł adapter OpenCode (v2): bez myślenia = baza z myśleniem `xhigh` przy 6–8 × mniej tokenów (SWE-bench Pro mediana 31,8k → 3,9k); omp to fork pi, więc testujemy oba adaptery i bazę z myśleniem; główna miara: **tokeny wygenerowane i czas ściany na zadanie** (nie tylko t/s)
- 2026-11-19: trzeci kandydat DaisyRose-27B ([[daisyrose-27b]], pełny RL na Qwen3.8-27B, GGUF Q4_K_M 17,3 GB, ten sam silnik): porównać tymi samymi zadaniami omp; myśli długo, więc tokeny i czas na zadanie są kluczowe; zmierzyć akceptację MTP n4
- hipoteza: (a) w omp adapter też skraca zadania (mniej wywołań, ≥ tyle samo rozwiązanych); (b) `--lora` bez scalania kosztuje > 4% dekodu (małe kernele, K-114); (c) po scaleniu + Q4_K_M akceptacja MTP spada, bo blk.64 nietrenowany
- test: (1) bez karty: zestaw 20 zadań agentowych z naszych sesji omp (`~/kernel/archiwum`) lub `agentx-harness`, myślenie wyłączone jak w treningu; (2) karta (XTX po zgodzie albo Vast ≥ 24 GB z hostguardem): baza Qwen3.8-27B Q4_K_M vs ta sama + `--lora` F16 vs scalone i skwantowane; spec_sweep T=1 (t/s, tok/krok), md5 nie dotyczy (inny model); zadania omp: rozwiązane, wywołania, czas. Pobrania: baza ~17 GB + adapter 0,6 GB (zgoda właściciela)
- miara: rozwiązane/20 i wywołania na zadanie (baza → adapter); t/s i tok/krok (baza → LoRA → scalone)
- zysk: krótsze sesje agenta (u nich −55…62% wywołań = mniej tur, każda tura ~1 s+); zmiana modelu = decyzja właściciela
- ryzyko karty: brak
- właściciel 2026-11-18 00:32: „super fajne pomysły” (K-120 i adapter pod omp z naszych sesji); start czeka na zgodę na pobranie ~17 GB i kredyt Vast
- zegar (2026-11-18): znaczniki etapów od pobrania do tabeli „zmierzone vs sufit”, wiersz „czas: ściana / GPU / najwolniejszy etap” ([[lekcja-czas-optymalizacji-to-metryka]])
- priorytet: średni

### K-121 · Adapter GA z wyścigami (Rohan Arun) do naszych sweepów wariantów: test-backend-ops perf na XTX i na NVIDIA (kernele draftu K-116)
- data: 2026-11-18
- źródło: [[ga-racing-rohanarun]] (`Auto-research-agent` @ `9367733`, eliminacja na log-ratio do mediany żywych, bramka rel < 0,997 i CI < 1 na świeżych danych, `pending` → czarna lista); demo działa tu na CPU (1,4 s, syntetyczne)
- hipoteza: automatyczny wyścig znajduje w tym samym czasie GPU co nasza siatka tego samego zwycięzcę (FA D256 wariant 83) albo lepszego, przy mniejszej liczbie pomiarów; na NVIDIA wybierze kafle/wątki kerneli draftu MTP
- test: CPU: adapter `hip_tbo.py` (komórki = kształty z profilu kroku, geny = zmienne `GGML_HIP_FA_D256_VAR` / warianty MMQ, pomiar = `test-backend-ops -o perf` na kształcie, build = sprawdzenie `test-backend-ops` bitowo); karta: XTX przez `run-jobs.sh`, `GGML_HIP_PM4=0`, ≤ 10 min; potem to samo na 5060 Ti (Vast, hostguard)
- miara: zwycięzca i jego czas vs nasz wybór z siatki; liczba pomiarów do decyzji
- zysk: szybsze strojenie per architektura (dźwignie kernelowe trzeba stroić osobno na każdą kartę); 0 t/s samo w sobie
- ryzyko karty: reset przy wariancie z faultem → tylko PM4=0, nadzór, kolejka
- priorytet: niski

### K-122 · llamAmpere v0.7 w trybie dokładnym vs nasz fork na pełnej mocy 3090, ten sam plik wag (łączyć z K-118 na jednej instancji)
- data: 2026-11-18
- źródło: [[llamampere]] (nagłówkowe 110+ t/s przy T=1 w trybie mb-MTP, czyli nie dokładnym; drafter DFlash2 ×3,4 po usunięciu podwójnego kroku); [[2026-11-17-k114-nvidia-sufit]]
- hipoteza: w trybie dokładnym (`--no-spec-mb-mtp`, bez rzadkiej atencji, MTP) na UD-Q4_K_XL llamAmpere jest szybszy od forka (80 t/s) o ≥ 15%; różnica to narzut kroku draftu (K-116), a nie kernele głównego GEMV
- test: jedna instancja 3090 z hostguardem (ta sama co K-118): wydanie v0.7 (binarka znver3 — host z AMD Zen3+, inaczej build z tagu) i fork `kvqleana`/`kvqlean`, UD-Q4_K_XL, spec_sweep T=0/T=1 ABBA, `nsys` jednego kroku w każdym; KLD vs wyjście bazowe na 1280 pozycjach
- miara: t/s (fork → llamAmpere dokładny), ms kroku i ms/draft, KLD
- zysk: wskazuje gotowe rozwiązanie dla K-116 (port do Enigmy NVIDIA); koszt ~$0,15 razem z K-118 [INFERENCE]
- ryzyko karty: brak (wynajem)
- priorytet: średni (czeka na kredyt)

### K-124 · Agentowy megakernel pętli draftu MTP + weryfikacji (metoda megakernel-zoo) — najpierw fork CUDA (5060 Ti/3090), potem XTX (HIP)
- data: 2026-11-19
- źródło: [[megakernel-zoo]] (Qwen3.8-27B B200: SGLang 9,52 → 8,44 ms, ~63 h agenta; ewaluator FP64 + ukryty zbiór + odwrócenie batcha + audyt); [[2026-11-17-k114-nvidia-sufit]] (draft 4–15 × droższy niż bajty, 37–40% kroku); [[budzet-megakernela-qwen-xtx]] (+4…9,5% za 40–70 osobodni)
- hipoteza: trwały kernel dla n kroków draftu (warstwa MTP + głowica 64k + argmax w pętli bez powrotu do hosta) zbliża koszt draftu do bajtów: na 5060 Ti krok n4 51 → ~36 ms (+40%) [INFERENCE]; na XTX mniej (PM4 już tnie granice)
- test: po K-116 (`nsys`): agent w pętli autoresearch z ewaluatorem jak w zoo (odniesienie = obecny fork, tokeny T=0 bitowo + KLD T=1, ukryty zbiór promptów PL/EN/kod, odwrócenie kolejności, audyt drugim agentem); 5060 Ti na Vast z hostguardem, budżet godzin agenta i GPU ustalony z właścicielem; zegar etapów
- miara: ms/draft i t/s n4 T=1 (49,4 → ?), md5 T=0, godziny agenta do pierwszego wyniku przechodzącego ewaluator
- zysk: Enigma NVIDIA do +40% [INFERENCE]; dowód, czy agentowa praca nad kernelem skraca nasze 40–70 osobodni do dni
- ryzyko karty: zawieszenia kernela rezydentnego (na Vast bez ryzyka dla naszej karty; na XTX dopiero po PoC-A z [[budzet-megakernela-qwen-xtx]])
- priorytet: średni (decyzja właściciela: budżet agent-godzin i GPU)

### K-126 · Enigma Windows NVIDIA: wydanie z CUDA 13.4 dla Blackwell (sm_120) zamiast CUDA 12.4
- data: 2026-11-19
- źródło: audyt Gemini (C.1.4b) potwierdzony: `app/engine/data/engines.json:155-182` pinuje `win-cuda-12.4`; release b11856 ma `llama-b11856-bin-win-cuda-13.4-x64.zip` (sha256 `06478e0f…`) i `cudart-…-13.4` (`738f8c25…`); `baselineEngineFor` (`engine.ts:88-90`) bierze pierwszy wpis i nie patrzy na architekturę GPU; JIT z PTX: Strata 173 s → 0,34 s ([[strata]])
- test: CPU: wpis `upstream-windows-x64-cuda13` z `gpuArchs: [sm_120]`, wybór po architekturze w `baselineEngineFor`, rozmiary z API GitHub, testy `bun test`; potem pomiar pierwszej odpowiedzi na Windows z kartą 50xx (nie mamy: Vast nie ma Windows) [INFERENCE: CUDA 13 wymaga sterownika ≥ R580, sprawdzać przy wykrywaniu]
- miara: czas do pierwszego tokena przy pierwszym starcie, t/s 12.4 vs 13.4
- zysk: najpopularniejsze karty (RTX 5070 6,15% Steam) bez minut JIT przy pierwszym starcie
- ryzyko karty: brak
- priorytet: średni
- wynik 2026-11-20: zrobione po stronie CPU. Nowy wpis `upstream-windows-x64-cuda13` w `app/engine/data/engines.json` (b11856, `gpuArchs: [sm_120]`, `minDriver: 580`; rozmiary i sha256 z API GitHub: zip 159 939 681 B `06478e0f…`, cudart 423 535 356 B `738f8c25…`). `baselineEngineFor` (`app/engine/src/server/engine.ts:92-98`) wybiera wpis pod architekturę karty, gdy sterownik jest znany i ≥ 580, w innym wypadku zostaje CUDA 12.4. Testy w `app/engine/test/engine.test.ts:79-83` (sm_120 + 581 → 13.4; sterownik 576, brak sterownika albo sm_86 → 12.4); `bun test` 208 pass. Zostaje pomiar pierwszej odpowiedzi na Windows z kartą 50xx.

### K-128 · Czy klient (omp) obcina `<think>` z historii i przez to psuje trafienia prompt-cache w turach agenta (analiza logów, bez karty)
- data: 2026-11-19
- źródło: audyt Gemini (H.9) i [[zwiad-2026-11-14]] (TensorFold: „[INFERENCE: sprawdzić na surowych logach omp]”)
- test: CPU: surowe logi serwera/omp z sesji agentowych (`~/kernel/archiwum`, logi topki, gdy jaroserverai online): `cache_n` vs `prompt_n` per tura, czy prefiks rozjeżdża się na granicy bloku myślenia
- miara: udział tokenów promptu z cache per tura; jeśli dziury > 10% → poprawka po stronie szablonu/serwera
- zysk: TTFT tur agenta (jeśli problem istnieje); 0 t/s dekodu
- ryzyko karty: brak
- priorytet: średni
- wynik 2026-11-20: problemu nie ma. Logi serwera z jaroserverai (`qwen-opt/logs/server-*.log`, 264 pliki, 964 tury), skrypt `qwen-opt/k128/cache_hits.py`. Całość: 48,4 mln tokenów promptu, z cache 90,1%. W 386 turach agenta, w których rozmowa urosła i prefiks został w slocie, cache pokrył 99,2% promptu, a historia rozjechała się łącznie na 14 tokenach. Odpowiedź poprzedniej tury (z blokiem myślenia) wróciła w prompcie w 89,7% tokenów: 347 tur > 90%, 29 częściowo, 10 wcale, więc omp nie wycina `<think>` w sposób, który psuje cache. 66 tur „rozjechanych” to w 47 przypadkach przeskok do innej rozmowy z tym samym początkiem (wspólny prefiks stoi na ~7650 tokenach, czyli system + narzędzia; podagenci na jednym slocie), nie granica myślenia. Dziury < 10%, poprawka szablonu niepotrzebna. [INFERENCE: logi mają tylko `f_keep`, nie surowy tekst promptu.]

### K-108 · Zmierzyć na XTX szczyt FP16 WMMA (GEMM 4096³ i 8192³, hipBLASLt/rocBLAS) i pasmo kopii device→device
- data: 2026-11-17
- źródło: [[skill-io-sufity]] (`ceilings.md:3`: mierzyć, nie brać ze specyfikacji); dziś sufit prefillu liczony z cudzych 107 TFLOPS (#52585)
- hipoteza: zmierzony szczyt 90–110 TFLOPS; wtedy prefill 4k–255k jest na 84–95% praktycznego sufitu i K-009/K-010 dają najwyżej kilka %
- test: XTX, `rocblas-bench`/`hipblaslt-bench` gemm f16 4096 i 8192 (min z N), `hipMemcpy` 4 GB D2D; `GGML_HIP_PM4=0`; ≤ 10 min
- miara: TFLOPS 4096/8192, GB/s; przeliczenie `ceiling-qwen27b-unc-xtx.json`
- zysk: priorytety prefillu oparte na liczbie; 0 t/s
- ryzyko karty: temperatury (krótki GEMM), eco 2200 bez zmian
- priorytet: średni (tani, porządkuje kolejkę)
- wynik 2026-11-20: w `/opt/rocm` nie ma `rocblas-bench`/`hipblaslt-bench`, więc własny test hipBLAS `GemmEx` f16 (liczenie w f32) i `hipMemcpy` (`qwen-opt/k108/bench.cpp`), przy limicie eco 2200 MHz. GEMM 4096³: 91,3 TFLOPS (min z 50), 8192³: 98,1 TFLOPS (min z 20). Kopia D2D 4 GiB: 385 GB/s (771 GB/s odczyt+zapis). Wynik mieści się w hipotezie 90–110; zakładane 107 TFLOPS jest o ~8% za wysoko dla 8192³ przy eco. `ceiling-qwen27b-unc-xtx.json` jeszcze nie przeliczony. Log: `~/qwen-opt/queue/logs/k108-gemm.log`

### K-112 · NVIDIA: zmierzyć pasmo, szczyt GEMM FP16/INT8 i prefill pp4096/pp32768 na 5060 Ti (lokalnie) i 3090 (wynajem)
- data: 2026-11-17
- źródło: [[skill-io-sufity]] (sufit prefillu 3090 z INT8 MMQ 2737 t/s przy 4k = 2,3 × XTX; prefillu NVIDIA nigdy nie mierzyliśmy); [[skill-io-metodyka]] (narzędzia CUDA)
- hipoteza: zmierzone pasmo ≥ 90% specyfikacji (3090 ≥ 840, 5060 Ti ≥ 400 GB/s); prefill forka na NVIDIA < 50% sufitu INT8 → dźwignia TTFT dla Enigmy
- test: `nvbandwidth` / `cudaMemcpy` D2D 4 GB; `cublasLt` f16 i i8 4096³ i 8192³ (min z N); `llama-bench -p 4096,32768 -n 0` fork vs upstream b11856 (ABBA, ten sam host); ≤ 10 min na kartę
- miara: GB/s, TFLOPS/TOPS, pp t/s i % sufitu; przeliczenie `karty.py` ze zmierzonymi wartościami
- zysk: sufity NVIDIA z pomiaru zamiast specyfikacji; decyzja, czy prefill NVIDIA jest dźwignią
- częściowo zrobione 2026-11-17 (K-114): prefill przez serwer 5060 Ti 788–828 t/s (43–47% sufitu INT8), 3060 442–461 (46–47%), 3090 na ograniczonym hoście 319–696; pasmo i GEMM dalej niezmierzone (archiwum forka bez `llama-bench`)
- ryzyko karty: brak
- priorytet: średni

### K-113 · `bench.py` skill-io 1:1 na XTX, 5060 Ti i 3090 (ta sama konfiguracja) — pierwsza tabela między firmami z jednego harnessu
- data: 2026-11-17
- źródło: [[skill-io-skrypty]]; ich 3090 Qwen3.8-27B EXL3 3 bpw + MTP 96,2 proza / 141,1 kod (`README.md:33`); K-110 (część XTX)
- hipoteza: na 3090 nasz fork (UD-Q4_K_XL) da ~80 t/s prozy przy ich panelu; porównanie z ich 96,2 (3 bpw = mniej bajtów, inny silnik) pokaże, ile z różnicy to bajty, a ile silnik
- test: `bench.py run` z `config-existing-server.json` (T 0,6, c1 6 × 512, prefill 4k/16k, `--long` 65 536 z igłami), te same 3 serwery: topka (XTX), fork kvqlean (5060 Ti lokalnie, 3090 Vast); ≤ 10 min na kartę
- miara: c1 mediana, prefill, TTFT, retrieval k/3 + % sufitu karty
- zysk: porównywalne liczby dla Enigmy i publikacji; 0 t/s
- ryzyko karty: brak
- priorytet: średni

### K-115 · Bramka igieł (K-109) na NVIDIA: 5060 Ti (IQ3_XXS, 196k) i 3090 (UD-Q4_K_XL, 245k) z przepisami Enigmy
- data: 2026-11-17
- źródło: [[skill-io-publikacja]] (bramka 5: igła ~85% okna); [[final-recipes-nvidia]] (konteksty przepisów)
- hipoteza: 3/3 kody przy 50% i 85% okna; jeśli nie, przepis Enigmy obiecuje kontekst, którego model nie czyta (KV q4_0 + mały kwant)
- test: `bench.py run --long <0,5·ctx>` i osobny job `--long <0,85·ctx>` na każdej karcie; fill 167k (85% z 196k) na 5060 Ti: 3 min przy suficie prefillu 924 t/s, ~10 min przy 30% sufitu [INFERENCE: prefillu 5060 Ti nie mierzyliśmy, K-112 najpierw]; jeśli > 10 min, bramka 85% jako jedyny job tej sesji
- miara: retrieval k/3, TTFT, szczyt VRAM vs przepis
- zysk: poprawność przepisów Enigmy NVIDIA; 0 t/s
- ryzyko karty: brak
- priorytet: średni

### K-105 · Enigma NVIDIA: few-row MMQ (#31533) w naszym forku CUDA (szeroka weryfikacja: lookup W16, MTP n4)
- data: 2026-11-14
- źródło: K-103 ([[2026-11-14-k103-llamacpp-v1-nvidia]]): few-row MMQ daje +10…12% na przebieg przy 8–16 kolumnach, a przy MTP n2 (3 kolumny) ~0
- test: 5060 Ti w jaroserverai (gdy online) lub 3090 z wynajmu: b11856 vs v1.0.0, MTP n 3/4, spec_sweep T=1 ABBA; 24 GB z UD-Q4_K_XL n3
- stan po bramce K-103: przy MTP n2/n3 upstream v1.0.0 daje +3,8% / +0,6%, KLD ~2σ ponad szumem. Few-row MMQ opłaci się dopiero przy szerokiej weryfikacji (fork z lookupem W16, n4), więc sens ma port #31533 do naszego forka CUDA (bramka KLD vs fork), a nie zmiana pinu.
- zysk: +5…12% decode na NVIDIA przy szerokiej weryfikacji [SZACUNEK]
- ryzyko karty: brak
- priorytet: średni (zysk tylko w forku z szeroką weryfikacją)

### K-107 · Dwie karty w jednym komputerze: XTX + RTX 5060 Ti (podział warstw `-sm layer` przez Vulkan albo dwa niezależne serwery dla roju agentów)
- data: 2026-11-15
- źródło: [[mapa-inferencji-roadmap]] (luki #3–#6, #10); plan z `hardware/rx-7900-xtx.md` §2 („do przetestowania”)
- test: gdy 5060 Ti online w jaroserverai: (a) dwa serwery (XTX Qwen 27B + 5060 Ti LFM albo Qwen IQ3) i fan-out omp, ściana sesji; (b) Vulkan `-sm layer` Qwen 27B na 40 GB: decode/prefill vs sam XTX; ≤ 10 min na ramię
- (c) dodane 2026-11-19 ([[zwiad-2026-11-19]]): prefill dzielony warstwami jak oMLX „Prefill Accelerator” (Qwen3.8-27B 64K 352 → 1879 t/s z 2 × A6000): 5060 Ti liczy pierwsze k warstw chunku promptu, XTX resztę i dekod; KV/stan GDN warstw k przesyłany przez PCIe; miara: fill 64k/255k t/s vs sam XTX (493 t/s przy 255k), md5 dekodu po fillu
- zysk: (a) przepustowość roju agentów; (b) tylko pojemność (większy model), decode wolniejszy [SZACUNEK]; (c) prefill, jeśli udział warstw na 5060 Ti i koszt PCIe na to pozwolą [INFERENCE]; reguła dla Enigmy „kiedy druga karta pomaga”
- ryzyko karty: brak (bez PM4 na Vulkan)
- priorytet: średni (5060 Ti offline)

### K-005 · Siatka checkpointów GDN co ~8192 tokenów + checkpoint w punkcie rozwidlenia + łańcuch fallbacku (edycja, regeneracja, kompaktowanie omp)
- data: 2026-10-15 (STATUS-NEXT §4), ponownie 2026-11-07 (66 poz. 6)
- źródło: [[siatka-checkpointow-gdn]], `Q/STATUS-NEXT.md:44`, `R/66-SYNTEZA.md:57`, `R/67c-nvidia-backlog-testow.md:116` (B22)
- test: najpierw implementacja w topce. XTX: replay prompt 60k → zmieniony koniec → rodzeństwo; `prompt_n`, TTFT, md5 vs zimny start (~1,5 min prefillu na ramię, ≤ 10 min).
- zysk: edycja ostatnich 10% promptu 60k: TTFT ~65 s → ~8–10 s [SZACUNEK]; ≥ 1 s/turę, gdy dojdzie do rozjazdu
- ryzyko karty: brak (~150 MiB RAM hosta na checkpoint)
- priorytet: wysoki (≥ 1 s/turę)

- wynik 2026-11-23 (bisekcja spadku prefillu po poprawce K-001, duet): pp2048 1021,8 → 981,6 (−3,9%); winne commity Gemini 5ff6a15 (−1,8%) i 0bb43ee (−1,5%); bank GDN 0/1 daje identyczne odpowiedzi (produkcja bez wpływu). Log `~/qwen-opt/queue/logs/duo-r14-*.log`.

- wynik 2026-11-23 15:09 UTC (r11 `LLAMA_CKPT_GRID=1`, produkcyjna konfiguracja, prompt 40k, edycja w 10% długości): wznowienie po edycji 74,1 → **19,4 s (−74%)**, tekst identyczny z liczeniem od zera (md5 równe); dopisek na końcu 2,09 → 2,18 s (w szumie); rozwidlenie 0,46 s. Kandydat do wdrożenia z poprawką K-001 (po naprawie spadku prefillu). Log `~/qwen-opt/queue/logs/duo-r13-k005-*.log`.

### K-006 · Wpis „wspólny początek” (Maya #607) i chude checkpointy (stan GDN tylko na granicach wiadomości) zamiast kopii całej sesji w cache
- data: 2026-11-05
- źródło: [[wspolny-poczatek-promptu]], `R/63-SYNTEZA.md:85-86` (plan #6, #7), `R/63b-colibri-maya-delta.md` §6, `R/68c-dlugi-kontekst-gdn.md:143`
- test: najpierw implementacja. XTX: `switch.py` z cachesave (2 przeplatane wątki 75–120k, 14 tur ≈ 3 min), mediana tury, `prompt_n`, md5 = zimny start; ≤ 10 min/ramię.
- zysk: start sesji po wyrzuceniu z cache 4,4 s → 0,3–0,5 s, przy 100k+ ~5–7 s → 0,3–0,5 s [SZACUNEK]; wpis 118k 14,2 GB → ~3–4 GB, czyli 3–4 długie wątki w cache zamiast 1
- ryzyko karty: brak (RAM hosta; `HSA_USE_SVM=0` już jest)
- priorytet: wysoki (≥ 1 s/turę agenta)

### K-009 · Przegląd configu MMQ na RDNA3 metodą wariantów jak FA 83 (maska `GGML_HIP_MMQ_VAR`: Q4_K/Q6_K/IQ4_XS, `sched_barrier`, offsety u32, prefetch K, skale x f32 w LDS)
- data: 2026-11-09 (skale x f32: 2026-10-15)
- źródło: `R/70-fa-d256-jak-to-zrobilismy.md:185` (#2), `R/68d-swieze-od-spolecznosci.md:138-139`, `Q/STATUS-NEXT.md:49`, [[sweep-wariantow-kernela]]
- test: ISA na CPU (`isa.sh`). XTX: `test-backend-ops perf -o MUL_MAT` Q4_K/Q6_K, md5 12k jak `Q/fa-d256/md5.sh`, ABBA `llama-bench -p 512,4096`; każdy krok ≤ 10 min (szablon `~/qwen-opt/fa-d256/`)
- zysk: pp ≤ 32k +2…4%, fill 255k +1…2% [INFERENCE]; MMQ to 63–81% prefillu, jedyna dźwignia prefillu przy krótkich promptach
- ryzyko karty: brak
- priorytet: średni (prefill; w pakiecie z K-010)

### K-010 · Fuzja gate/up + GLU w MMQ dla WMMA RDNA3 (port upstream #29948)
- data: 2026-11-05
- źródło: `R/68a-rdna3-kernele.md:120`, `R/68-SYNTEZA.md:21`, `R/68d-swieze-od-spolecznosci.md` §2.2
- test: XTX `test-backend-ops -o MUL_MAT` z fuzją, `llama-bench -p 512,4096 -ub 512 -r 5` ABBA, md5; ≤ 10 min/krok
- zysk: pp ≤ 32k +2…4% [INFERENCE] (CUDA u autora +4,6…7,4%)
- ryzyko karty: brak (wariant MoE był na RDNA3 wolniejszy o 3…16%, więc mierzyć)
- priorytet: średni (prefill, pakiet z K-009)

### K-011 · Kontrola ewikcji VRAM do GTT przy 262k (`amd-evicted-vram`, `drm-memory-*` w fdinfo)
- data: 2026-11-07
- źródło: `R/68a-rdna3-kernele.md:123` (4.5), `R/68-SYNTEZA.md:24`
- test: doczepić do najbliższego fillu 255k: odczyt `/proc/<pid>/fdinfo/*` przed promptem, po prefillu i po 256 tokenach (0 dodatkowego czasu GPU)
- zysk: 0%, jeśli ewikcji nie ma; jeśli jest, decode przy 255k jest dziś zaniżony
- ryzyko karty: brak (odczyt)
- priorytet: średni (darmowe, może zaskoczyć)
- wynik 2026-11-20: serwer w konfiguracji produkcyjnej (ctx 262144, port testowy). Fill 131 000 tokenów zamiast 255k, bo 255k to ~548 s samego prefillu, a limit testu to 10 min. **Ewikcji brak**: `amd-evicted-vram` = 0 KiB we wszystkich trzech odczytach. VRAM 22,39 GiB przed promptem → 22,74 GiB po prefillu (650 t/s, 201 s) → 22,78 GiB po 256 tokenach (134 t/s). GTT stoi na ~6,1 MiB. Log: `~/qwen-opt/queue/logs/k011-fdinfo.log`, skrypt `qwen-opt/k011/fdinfo.sh`

### K-012 · `kvq` przy W=5 bliżej rooflinu: nowy układ (K dekwantowane raz, głębszy prefetch K/V), cel ~172–300 µs/warstwę przy 98–196k
- data: 2026-11-07
- źródło: [[2026-11-08-kvq-once-profil]] (`:86`: ONCE=1/2 KILL, „potrzebny inny układ”; FA = 30% kroku przy 199k, 11,32 ms), `R/68c-dlugi-kontekst-gdn.md:142`, `R/70-fa-d256-jak-to-zrobilismy.md:188` (#5)
- test: XTX `kvq-once/job.sh` kperf (d98k/196k, nb1/nb5) + `fa_hash` ≤ 10 min; potem xtxbench 199k osobnym jobem
- zysk: sufit +12…16% decode przy 196–255k; realnie +1,5…3% przy ≥ 94k [SZACUNEK]
- ryzyko karty: nowy kernel w taśmie PM4 (bramka `test-backend-ops` przed serwerem)
- priorytet: średni (duży sufit, dwa nieudane podejścia)
- zwiad 2026-11-14: hipfire #989 (WMMA split-K verify attention, gfx1100, numeryczne) zszedł do 309,5 µs przy 100k i 4 wierszach, czyli tyle co nasz `kvq` przy nb5 i 98k (~319 µs); bitowa droga musi zejść niżej ([[zwiad-2026-11-14]])

### K-014 · Graf CUDA na cały cykl draft + weryfikacja (ścieżka hosta 3,7 ms/krok = 14% na 3090)
- data: 2026-10-21 (Orca), 2026-11-09 (qwen-warp pkt 4)
- źródło: `R/69b-tensorfold-qwen-warp.md:75`, [[2026-11-09-qwen-warp-vs-fork-3090]], sesja Orca 2026-10-21 (archiwum, `O:1986-2003`); potwierdzenie kierunku: Baseten deepseek-ultrafast, krok spec-dec z weryfikacją 7 tokenów w jednym grafie ([[telegram-2026-11-14-silniki-agenci]])
- test: 5060 Ti lokalnie: spec_sweep T=1 + ms/krok z rozbiciem host/GPU, fork vs fork+graf; ≤ 10 min/ramię. Kod: tygodnie.
- zysk: +10–20% decode na 3090 [SZACUNEK]; część przewagi qwen-warp ×1,34–1,81
- ryzyko karty: brak
- priorytet: średni (duży, drogi w kodzie)
- zwiad 2026-11-15: 1Cat-vLLM `a013fb3dc` — próbkowanie T>0 bez synchronizacji hosta przez warunkowy graf CUDA (B=1..4) + fuzja top-K, kolejny wzór ([[zwiad-2026-11-14]])

### K-015 · Regresja `kvq` na sm_120 przy krótkim kontekście (−4,4% na 5080, −4,7% na 3090) i przegląd `GGML_CUDA_KVQ_BPSM` 1/2/3/4/6
- data: 2026-11-07
- źródło: `R/67-nvidia-vast-kampania.md` §5, `R/67c-nvidia-backlog-testow.md:107` (B13)
- test: 5060 Ti lokalnie: `test-backend-ops perf -o FLASH_ATTN_EXT` hs256 q4_0 przy 32k/98k/196k dla każdego BPSM, potem spec_sweep KVQ 0/1; ≤ 10 min
- zysk: odzysk +4…5% przy krótkim kontekście przy zachowaniu +9,5% decode przy 64k
- ryzyko karty: brak (16 GB: uważać na OOM przy dużym kontekście)
- priorytet: średni (lokalnie, tanio)

### K-016 · Fork CUDA: ogon lookupu W8/W16/off oraz MTP n 2/3/5 per klasa na promptach kopiujących
- data: 2026-11-07
- źródło: `R/67c-nvidia-backlog-testow.md:99-101` (B5–B7; 5060 Ti: n=3 ≥ n=4, fork ma sztywne 4), [[final-recipes-nvidia]]
- test: 5060 Ti: `LLAMA_SPEC_LOOKUP_W=8/16`, `LLAMA_SPEC_LOOKUP=0`, `--spec-draft-n-max 2/3/5`, `mvs` + spec_sweep; po jednym ramieniu na job ≤ 10 min
- zysk: dobór przepisu Enigmy per klasa; W16 na wąskiej szynie może przegrywać [INFERENCE]
- ryzyko karty: brak
- priorytet: średni (przepis Enigmy, lokalnie)

### K-017 · Głębokość i szerokość draftu per klasa żądania (`LLAMA_SPEC_ROUTE`: rozumowanie/kod T=0 → n=5, proza → n=3)
- data: 2026-10-21 (raport 44)
- status: **czeka na decyzję** (bramka K-007; n=5 zmienia md5 → d71a2c04). Najpierw naprawić crash ABBA `ggml-cpu.c:2504` w `ggml_graph_plan`.
- źródło: `R/44-routing-profili-spekulacji.md:5-7`, [[raport-44-spec-route]], `R/36-xtx-qwen-roadmap.md:183`
- test: XTX `~/qwen-opt/xtxlab/sr_gate.sh` + `sr_arm.sh` (`x44.jobs`), reason_bench T=0, spec_sweep, `mvs`; po jednym na job ≤ 10 min
- zysk: rozumowanie T=0 +6,8%, proza +4,3%, kod/JSON T=0 +5…10%, czat 0 (kill < −1%)
- ryzyko karty: brak
- priorytet: średni (zależy od decyzji)

### K-018 · AGR2: kandydat lookupu zgodny z 4 draftami MTP (`LLAMA_SPEC_LOOKUP_AGREE=1`) + dynamiczny słownik draftu
- data: 2026-10-19 (21c), 2026-11-05 (63 #18)
- źródło: [[agr-lookup-zgodny-z-mtp]], [[2026-10-19-sufit-pointera-lookup]], `R/21c-copy-paste-lm.md:185-194`, `R/63-SYNTEZA.md:97`
- test: najpierw symulacja CPU; XTX ABBA w jednej binarce na `mvs`, `copy` (hashline-pl) i spec_sweep T=0/T=1; kill < +2% hashline albo > +0,5% ms/krok na czacie; ≤ 10 min
- zysk: agent +3,7%, hashline +5,4%, czat +0,6% (symulacja); zmienia tylko drafty
- ryzyko karty: brak
- priorytet: średni (na granicy progu)

### K-019 · Cache sufiksów między sesjami (draft z poprzednich wyjść agenta, styl SuffixDecoding)
- data: 2026-10-19 (raport 18), 2026-11-07 (67c C18)
- źródło: `R/67c-nvidia-backlog-testow.md:135`, archiwum (`A:21140`)
- test: symulacja CPU na logach omp, potem XTX spec_sweep PL + replay agenta ABBA (kill < +1%); ≤ 10 min
- zysk: +5–15% na agentach [SZACUNEK]; zmienia tylko drafty
- ryzyko karty: brak
- priorytet: średni (agenci, tani offline)
- wynik 2026-11-20: symulacja CPU (`qwen-opt/k019/suffix_sim.ts`, wynik `qwen-opt/k019/wynik-2026-11-20.txt`): 190 sesji omp, 212 epok, 8,52 mln tokenów wyjść agenta (tokenizer Qwen3), model kroku jak w `product/research/21c-cplm/oracle.py` (MTP n 4, ogon przy m ≥ 6 i k = 4). Cache sufiksów z wcześniejszych sesji (CROSS) zamiast lookupu w sesji: 3,39 → 3,70 tok/krok, +8,4% t/s (model); oba razem (UNION: lokalny, a gdy nie trafi, cache sufiksów) 3,98 tok/krok, **+15,9%**. Najwięcej `write` +19,8% i tekst asystenta +22%, najmniej `edit` +14,7% i `bash` +13%. Ograniczenia: wyjścia pisał Claude, nie Qwen; podagenci powtarzają podobne teksty, więc wynik to raczej górna granica. Następny krok bez zmian: XTX spec_sweep PL + replay agenta ABBA.

### K-020 · Polityka wyrzucania `--cache-ram` ważona kosztem przeliczenia (Marconi) zamiast LRU
- data: 2026-11-07
- źródło: `R/68c-dlugi-kontekst-gdn.md:143` (#9)
- test: XTX replay 3 wątków (2 długie + krótkie) z `LLAMA_SERVER_PREFIX_LOG`, liczba pełnych prefilli ≥ 20k; ~10 min
- zysk: chroni wpisy ≥ 100k (przeliczenie 100–550 s) przy presji 40 GB [INFERENCE]
- ryzyko karty: brak
- priorytet: średni (rzadkie, ale ogromne tury)

### K-021 · Dataflow w taśmie PM4: usunąć granice dispatchy w łańcuchu MMVQ → norma → MMVQ weryfikacji (najpierw PoC-A: hand-off w trwałej siatce)
- data: 2026-10-20 (raport 36 L7)
- źródło: `R/37-proza-100.md:17-19` (górna granica `GGML_HIP_PM4_UB=mmvq,norm` −2,17 ms/partię 5 wierszy, −8,8%), `R/36-xtx-qwen-roadmap.md:190`, `R/66-SYNTEZA.md:66` (#15), [[budzet-megakernela-qwen-xtx]]
- test: XTX `klab` mikrobench hand-off, `GGML_HIP_PM4=0` (kill: > 0,3 µs albo < 30% zysku „bez granicy”); potem PoC-B md5 + spec_sweep ABBA; każdy krok ≤ 10 min
- zysk: etap 1 +2,6…4,2%, pełny +3…6% krótki kontekst / +2…4% przy 199k, po 40–70 osobodniach [SZACUNEK]
- ryzyko karty: **wysokie**: zawieszenia taśmy PM4 i resety (16a, 24l); tylko z `gpu-guard.sh`
- priorytet: średni (jedyna duża dźwignia w kernelach, drogie i ryzykowne)

### K-022 · Natywne q4_0 K/V w prefillu FA D256 (bit 128 / #31802): wyjaśnić md5 wariantów 131/147, alternatywnie szybszy staging q4_0→f16
- data: 2026-11-07
- źródło: [[2026-11-08-fa-d256-prefill]] (`:35`), `R/70-fa-d256-jak-to-zrobilismy.md` §3.6 (173/173 w `test-backend-ops`, ale md5 e9dcdd80 ≠ 816334e4), `R/68d-swieze-od-spolecznosci.md:137`, `R/68c-dlugi-kontekst-gdn.md:137`
- test: najpierw różnica na CPU (ścieżka dekwantu vs `dequantize_q4_0`, ogon KV). XTX `fa-d256/md5.sh` + micro (≤ 10 min); szczyt VRAM przy fill 255k osobnym jobem (~9 min).
- zysk: VRAM −~1 GiB przy 262k, fill 255k +2…3%; staging sam −2% fillu (~11 s)
- ryzyko karty: VRAM (szczyt może się przesunąć)
- priorytet: średni (VRAM daje zapas dla K-048)

### K-023 · Bisekcja regresji prefillu forka CUDA względem upstream (sm_89 −3,5…−3,9%, 3060 TTFT 512 +30%) i LOO przełączników forka
- data: 2026-10-20 (raport 29)
- źródło: `R/67c-nvidia-backlog-testow.md:103,105` (B9, B11), `product/BENCHMARKI-PRZED-PO-2026-10-19.md` §4, [[raport-15d-prefill-dlugi-kontekst]]
- test: 5060 Ti lokalnie (sm_120): `llama-bench -p 512,4096` upstream vs fork + po jednym przełączniku `=0` na job; sm_89 wynajem
- zysk: odzysk 3…12% prefillu i TTFT na NVIDIA
- ryzyko karty: brak
- priorytet: średni (TTFT Enigmy)

### K-024 · Enigma ROCm na innych kartach AMD + autotune wariantu FA przy instalacji (gfx1101/1102/1151/1201)
- data: 2026-11-09
- źródło: `R/70-fa-d256-jak-to-zrobilismy.md:186` (#3)
- test: wynajem kart AMD; `fa-d256` micro + md5 + bench przy głębokości na każdej architekturze; ~1 h wynajmu
- zysk: RDNA3 gfx1101/1102: prefill przy głębokości +3…6%; gfx1151 nieznane; gfx1201 wymaga portu [INFERENCE]
- ryzyko karty: brak (wynajem)
- priorytet: średni (warunek sprzedaży Enigmy na inne Radeony)

### K-025 · FA D256 wariant 83 dla innych modeli i kształtów (Saluki/Bonsai, Qwen3.6-35B-A3B, LFM2.5 D=64, f16 KV, RDNA3.5) przed włączeniem domyślnie w kodzie
- data: 2026-11-09
- źródło: `R/70-fa-d256-jak-to-zrobilismy.md:184,187` (#1, #4), §6.2; dziś 83 tylko dla qwen/uncensored przez launcher (f16 KV przy 131k: −2,4%)
- test: XTX `fa-d256/bench.sh` z `M=<model>` przy 4k/32k/131k (~17 min → 2 joby), md5 jak `md5.sh`; dla 35B-A3B rozszerzyć warunek `:2216` i sweep
- zysk: Saluki/Bonsai ≥ +5,8% fillu [INFERENCE], 35B-A3B przy ≥ 128k +3…5%, LFM +1…2%; dla katalogu Enigmy, nie produkcji
- ryzyko karty: brak
- priorytet: średni (Enigma)

### K-026 · Enigma: próg draftu `--spec-draft-p-min` {0; 0,5; 0,8} × n {1,2,4} dla MoE z `--n-cpu-moe` na kartach ≤ 16 GB
- data: 2026-11-07 (66a A2)
- źródło: [[prog-draftu-od-kosztu-wiersza]], `R/66-SYNTEZA.md` poz. 10
- test: 5060 Ti z Qwen3.6-35B-A3B `--n-cpu-moe 20/30/40` albo emulacja na XTX; spec_sweep T=0/T=1 ABBA ~10 min/klasę
- zysk: 0…+15% na MoE z offloadem (Strata +5,6…9,3%); model rezydentny ~0
- ryzyko karty: brak
- priorytet: średni (produkt Enigma)

### K-027 · Profil kroku przy długim kontekście na NVIDIA (`nsys` + `LLAMA_HOSTGAP_TRACE` przy 1,7k/94k/199k)
- data: 2026-11-07
- źródło: `R/67c-nvidia-backlog-testow.md:118` (C1)
- test: 3090/4090 (wynajem; 16 GB 5060 Ti nie zmieści 199k z 27B), po jednym kontekście na job ≤ 10 min
- zysk: 0% sam; rozstrzyga K-062, K-063 i maskę na CUDA
- ryzyko karty: brak
- priorytet: średni (bramka decyzji NVIDIA)

### K-028 · xtxbench: smoke przełącznika bez restartu `GGML_HIP_RUNTIME_SWITCH_FILE`
- data: 2026-11-09
- źródło: [[xtxbench-szybki-ab]] (`:39,48`), `Q/patches/xtxbench/0001-runtime-switch-hook-GGML_HIP_RUNTIME_SWITCH_FILE.patch`
- test: XTX `xtxbench.py t1 --var-switch …` A/A; obowiązkowe ramię md5 ze świeżym startem (wyciek K-001); ≤ 10 min
- zysk: narzędziowy: bez restartu 1,5–2 min na ramię, więc każdy przyszły A/B krótszy
- ryzyko karty: brak
- priorytet: średni (przyspiesza całą kolejkę)
- pominięte 2026-11-20: w `~/wt/xtxbench/build-hip/bin` są tylko biblioteki (`libggml-base`, `libggml-cpu`), nie ma `llama-server`, a xtxbench bez binarki odmawia pracy. Potrzebna jest najpierw budowa gałęzi `xtxbench`, czyli praca nad kodem

### K-029 · xtx-eco: odczytywać fabryczny `OD_SCLK` przy każdym boocie przed pierwszym zapisem OD (stock zmienia się między bootami: 2885 vs 2935 MHz)
- data: 2026-11-06
- źródło: [[2026-11-06-xtx-eco-instalacja]] (`:12-13`, „poprawka w toku — status do sprawdzenia”), [[raport-64-termika]]
- test: XTX bez obciążenia: po restarcie porównać `pp_od_clk_voltage` z zapisanym stanem bootu, sprawdzić krzywą wentylatora (`pwm1`/RPM); ≤ 10 min
- zysk: 0 t/s; „powrót do stock” nie obniża już limitu o 50 MHz (zasada: karta fabrycznie)
- ryzyko karty: zapis OD na jądrze 6.8 gubi krzywą wentylatora, więc pilnować temperatur
- priorytet: średni (bezpieczeństwo ustawień fabrycznych)
- wynik 2026-11-20 (bez restartu, odczyt bieżącego bootu 13:32): stan zapisany przy starcie `/run/xtx-eco/stock` = 2940 MHz. To trzecia różna wartość fabryczna (2885, 2935, 2940), więc poprawka „odczyt przy każdym boocie” jest potrzebna i działa (`xtx-od.sh` zapisuje stock do `/run` przed pierwszym zapisem). `OD_SCLK 1` = 2200 MHz (limit eco), `power1_cap` 285 W. Krzywa wentylatora jest zapisana (`fan_curve` 25–80 °C → 100%), ale w spoczynku (hotspot 45 °C) `pwm1` = 0 i 0 RPM, czyli tryb zero-RPM. Pod obciążeniem nie sprawdzano. Log: `~/qwen-opt/queue/logs/k029-od.log`

### K-030 · Enigma 12/16 GB: porównanie jakości kandydatów (AP-Q3_K_XL vs UD-Q3_K_XL na 16 GB, IQ3_XXS-mtp Swift W3 / ISTA na 12 GB) zestawem jakość-mini + KLD
- data: 2026-10-18 (16e), zgoda na porównanie 2026-11-09
- status: **czeka na decyzję** (źródła danych i pobrania modeli do potwierdzenia, [[2026-11-09-decyzje-runda-69]])
- źródło: [[testy/2026-10-18-e1-kwanty-27b-kld]], `R/67b-wybor-modeli-nvidia.md`, [[jakosc-mini]]
- test: 5060 Ti: `~/qwen-opt/jakosc-mini/run.py gen` + KLD na każdym kandydacie (> 10 min, podzielić po zbiorze)
- zysk: wybór modeli katalogu (AP vs U3: KLD czat −12%, kod −23% przy tych samych bajtach)
- ryzyko karty: brak
- priorytet: średni (produkt)

### K-031 · Maska KQ poza ścieżką krytyczną albo pochodna maska w kernelu (bez `n_kv × n_tokens` z hosta)
- data: 2026-10-13 (K3), 2026-11-07 (66 #9, 68c #4)
- źródło: [[maska-kq-host-dlugi-ctx]], [[2026-11-08-kvq-once-profil]] (`:50,89`: `graph→inputs` 355 µs przy 199k), `R/68c-dlugi-kontekst-gdn.md:15-17,138`
- test: XTX `LLAMA_HOSTGAP_TRACE=16` + xtxbench decode 199k ABBA, md5 (osobny job na 199k)
- zysk: decode 199–255k +0,5…1,5%, fill 255k +0…3%, −256 MiB VRAM i −256 MiB pinned [SZACUNEK]
- ryzyko karty: brak (host); wariant w kernelu = nowy kernel w PM4
- priorytet: niski (sam poniżej progu, łączyć z K-012)
- wynik 2026-11-21: **maska leży na ścieżce krytycznej, ale zdjęcie jej daje tylko ~0,4% przy 94k i ~0,8% przy 199k, poniżej progu.** Ślad hosta `LLAMA_HOSTGAP_TRACE=16`, konfiguracja produkcyjna na porcie testowym, jedno zimne żądanie na głębokość (T=0, 256 tok.). Ramię A to produkcja (szybka maska). Ramię B to `LLAMA_KV_MASK_FAST=0`, czyli celowo wolniejsza maska jako sonda: jeśli krok rośnie o tyle, o ile rośnie budowa maski, to maska blokuje GPU. Przy 94k (ABBA): `graph→inputs` A 136 µs, B 396 µs (+260 µs); ściana kroku 32,83 → 33,07 ms (+0,24 ms, prawie 1:1); decode 120,95 → 119,98 t/s (−0,8%). Przy 199k (jedna para A/B, wypełnienie 360 s): `graph→inputs` A 303 µs, B 909 µs; ściana 37,77 → 38,67 ms; decode 95,05 → 93,08 t/s (−2,1%). Przy 1,7k budowa maski kosztuje ~40 µs i A = B. md5 identyczne w obu ramionach (94k `3f0651b0`, 199k `efdb8053`, to samo co w [[2026-11-08-kvq-once-profil]]). Zysk z przeniesienia maski poza ścieżkę krytyczną to najwyżej czas maski w A: 136 µs na 32,8 ms (0,4%) i 303 µs na 37,8 ms (0,8%). Priorytet zostaje niski, łączyć z K-012. Źródło: `~/qwen-opt/queue/logs/k031-{A1,B2,B3,A4,199A,199B}.log`, skrypt `Q/k031/k031.sh`.

### K-032 · Amplifikacja odczytu KV w `kvq` (bajty z liczników vs 1152 B/token/warstwę)
- data: 2026-11-07
- źródło: `R/68a-rdna3-kernele.md:124` (4.6), [[2026-11-08-kvq-once-profil]] (`:77`, `FETCH_SIZE` = 0)
- test: XTX `rocprofv3 --pmc TCC_EA_RDREQ_sum TCC_EA_RDREQ_32B_sum` na `llama-bench -fa 1 -ctk q4_0 -ctv q4_0 -p 5 -ub 5 -d 131072`, `GGML_HIP_PM4=0`; ≤ 10 min
- zysk: 0…3% decode przy ≥ 128k [INFERENCE]; zasila K-012
- ryzyko karty: brak
- priorytet: niski (diagnostyka)
- wynik 2026-11-20: **liczniki nie działają.** Na gfx1100 nie ma `TCC_EA_RDREQ_*` (rocprofv3: „Missing”). Ich odpowiedniki `GL2C_EA_RDREQ_{32,64,96,128}B_sum` dają 0 we wszystkich 4160 dispatchach (to samo co `FETCH_SIZE` = 0 w [[2026-11-08-kvq-once-profil]]), więc bajtów z liczników nie da się dziś zmierzyć. Wynik zastępczy z czasów rocprofv3 (`llama-bench pp5 @ d131072`, produkcyjna `~/llama-topka`, PM4 0, fill z `-ub 512`): `flash_attn_ext_kvq<256,8,q4_0>` mediana 408 µs na warstwę + combine 4 µs, pp5 99,9 t/s. Przy 1152 B/token/warstwę × 131072 = 151 MB to ~370 GB/s efektywnie, około 39% z 960 GB/s. Pod profilerem dispatche idą szeregowo, więc to szacunek. Amplifikacji z tego nie da się oddzielić od niskiej zajętości kernela. Log: `~/qwen-opt/queue/logs/k032-rdreq2.log`, skrypt `qwen-opt/k032/rdreq.sh`

### K-033 · Diagnoza FCLK/MCLK pod obciążeniem, stock vs eco (tylko odczyt `pp_dpm_*`)
- data: 2026-10-12
- źródło: `R/68a-rdna3-kernele.md:122` (4.4), §2.9
- test: pętla `grep '\*' pp_dpm_{sclk,mclk,fclk}` co 0,25 s doczepiona do najbliższego spec_sweep (0 dodatkowego czasu)
- zysk: 0% sam; wyjaśnia, czy −1,9% decode na eco to fabric
- ryzyko karty: brak (odczyt)
- priorytet: niski (darmowa diagnostyka)
- wynik 2026-11-21 (tylko eco, zegarów nie zmieniamy, więc ramienia stock nie ma): **pod obciążeniem pamięć i fabric stoją na najwyższych poziomach, które faktycznie są używane.** Pętla `dpm_poll.sh` (co 0,25 s, sam odczyt sysfs) chodziła przy 9 jobach: decode 1,7k/94k/199k, prefill 12k/94k/199k, pp4096, LFM pN. Próbki z `gpu_busy` ≥ 50%: MCLK 1249 MHz (najwyższy poziom) w 88–100% próbek, FCLK 2000 MHz w 88–100%, a poziomy 2201–2301 MHz w 0–5%. SCLK mediana 2183–2187 MHz (sufit eco 2200). Spadki do 772 MHz MCLK i 1200 MHz FCLK (0–12%) wypadają na krótkie przerwy między żądaniami. Pamięć nie jest dławiona na eco. Czy −1,9% decode na eco to FCLK 2000 zamiast 2301, rozstrzygnie dopiero odczyt na stocku przy okazji, gdy karta i tak będzie na stocku (sami nie przełączamy). Źródło: `~/qwen-opt/queue/logs/k048-*.log`, `k031-*.log`, `k045-g1.log`, skrypty `Q/k033/dpm_poll.sh`, `dpm_sum.py`.

### K-034 · Nadmiar ~10 KiB/token VRAM (nachylenie 29,1 vs 18,4 KiB/token): znaleźć bufor rosnący z kontekstem
- data: 2026-11-05
- źródło: `R/63-SYNTEZA.md:88` (#9), `R/65-vram-rezerwa-mtp-kontekst.md` §5
- test: najpierw CPU (`llama-context`); XTX `-lv 4` przy 131k/262k i szczyt VRAM (fill osobnym jobem)
- zysk: +~2,7 GiB zapasu przy 262k [SZACUNEK], 0 t/s; zapas na OOM i `-ub 1024`
- ryzyko karty: brak
- priorytet: niski (0 t/s)
- wynik 2026-11-20: czytanie kodu `llama-duo` daje ~10 KiB/token z dwóch buforów compute, oba z kontekstu głównego i draftu MTP. (1) FA na KV q4_0 przy prefillu (ub 512, kernel MMA/TILE) potrzebuje kopii f16 całego K i V jednej warstwy w buforze compute: `ggml/src/ggml-cuda/fattn.cu:745-763` (need_f16_K/V) + `ggml/src/ggml-cuda/fattn-common.cuh:53-75` (rozmiar = n_kv × 1024 × 2 B na K i na V) = 4 KiB/token. (2) maska FA f16 n_kv × ub: `src/llama-graph.cpp:30-42` = 1 KiB/token przy ub 512. Razem 5 KiB/token na kontekst. Pomiar 29,1 (R56, 2026-10-21) był przed łatką lean reserve, więc kontekst draftu MTP dokładał drugie tyle (`src/llama-context.cpp:315-326`, opis 800 MiB przy 204 800). 2 × 5 ≈ 10 z 10,7 KiB/token nadmiaru [INFERENCE: bez pomiaru `-lv 4`]. Po q63 zostaje ~5 KiB/token z kontekstu głównego (~1,25 GiB przy 262k); zbić to może tylko FA bez kopii f16 przy prefillu (kvq/VEC czytające q4_0) albo prefill w kawałkach KV. Do potwierdzenia na XTX `-lv 4` (linie `sched_reserve`).

- wynik 2026-11-20 na XTX (`qwen-opt/k034/bufs.py`, produkcja `-lv 4`, ctx 64k i 128k): bufor compute celu 420,29 → 740,29 MiB, czyli **+5,0 KiB/token**, zgodnie z czytaniem kodu (kopia f16 K/V do FA przy prefillu ~4 KiB + maska ~1 KiB). Bufor compute draftu MTP stały, 40,28 MiB, więc łatka lean-reserve działa. KV 18 KiB/token.
  - Przy 262k compute ≈ 1,38 GiB, z czego ~1 GiB to kopia f16. Natywne q4_0 K/V w FA prefillu (K-022) zwolni ok. 1 GiB VRAM.
### K-035 · Głowica draftu MTP: grube przejście (IQ4_XS/Q2_K) + dokładny rerank top-8 na wierszach Q6_K
- data: 2026-10-20 (36 L6c), 2026-11-07 (66 #5)
- źródło: [[glowica-draftu-rerank]], `R/66-SYNTEZA.md:56`
- test: offline na logitach (czy top-8 grubej głowicy zawiera argmax Q6_K); XTX spec_sweep T=1 + E0 + `mvs` ABBA ≤ 10 min
- zysk: +1…3% (B1), +1…4% (B2) [SZACUNEK]; cel nietknięty, md5 bez zmian
- ryzyko karty: brak
- priorytet: niski (poniżej progu)

### K-036 · Nakładanie kroków: wejścia kroku t+1 przed synchronizacją hosta (ZOS-lite), obcinanie po stop-tokenie na GPU
- data: 2026-10-20 (36 L11)
- źródło: `R/36-xtx-qwen-roadmap.md:196`, `R/63-SYNTEZA.md:90`, `R/66-SYNTEZA.md:63`, `R/67c-nvidia-backlog-testow.md:129` (C12)
- test: md5 + test „stop-token w środku okna”, spec_sweep ABBA ≤ 10 min (XTX i 5060 Ti)
- zysk: XTX +0,7…1,8% (luka GPU 410 µs z 27,3 ms), 5060 Ti ≤ +3,9%, LFM +4…6%
- ryzyko karty: PM4 (zmiana porządku taśm)
- priorytet: niski (XTX poniżej progu)

### K-037 · Megakernel / rezydentna pętla MTP (PoC-A w trwałej siatce 96–192 WG)
- data: 2026-10-16 (15a), 2026-11-07 (66c)
- źródło: [[budzet-megakernela-qwen-xtx]], [[lekcja-megakernel-prefetch-nie-granica]], `R/66c-hyperkernel-megakernele.md` §7
- test: XTX mikrobench PoC-A (kill > 0,3 µs albo < 30% zysku „bez granicy”); ≤ 10 min, kod 1–1,5 dnia
- zysk: krótki ctx +4…9,5%, 199k +2…4%, za 40–70 osobodni [SZACUNEK]
- ryzyko karty: **wysokie**: ewikcja kolejki KFD przy kernelu rezydentnym → możliwy reset
- priorytet: niski (koszt i ryzyko; wspólny PoC z K-021)

### K-038 · Przeszukiwanie flag spekulacji (TPE: DRAFT_N, LOOKUP_W/MMIN, PM4_MIN_DISPATCH, typ KV draftu) na odłożonym zestawie
- data: 2026-11-05
- źródło: `R/63-SYNTEZA.md:93` (#14), `R/63e-metodologia-agenci.md` §11, [[zestaw-odlozony]]
- test: XTX xtxbench `--var-switch` po jednej fladze na job (~4 min), zwycięzcy na holdoucie; zmiany szerokości tylko po K-007
- zysk: spec_sweep +1…5% [SZACUNEK]
- ryzyko karty: brak
- priorytet: niski (szum, klątwa zwycięzcy)

### K-039 · Q5_K MMVQ `big_rows` (`GGML_HIP_MMVQ_Q5K_BIG_ROWS=6144`): dokończyć ABBA i sprawdzić env w produkcji
- data: 2026-10-20 (raport 50b)
- źródło: [[raport-50b-mmvq-q5k]], `R/43-integracja-2026-10-20.md:68`, archiwum (`A:36426`: „brakuje 2 z 4 ramion”, md5 PASS)
- test: XTX `~/qwen-opt/queue/i43-int7.jobs` od `i43g-B1b` (2 ramiona × ~2,5 min)
- zysk: kernel −1,3…−3,5%, ~+0,4% decode
- ryzyko karty: brak
- priorytet: niski (poniżej progu, łączyć)
- wynik 2026-11-20: dokończone ramiona B1b i A1b z `i43-int7.jobs`, po nowej bramce md5 (qwen i lfm PASS). Uwaga: A1a/B1a są z 2026-10-21, a B1b/A1b z dzisiaj, i dzisiejsza para jest o ~1,7% wolniejsza w obu ramionach. Proza (T=1): A = (79,86 + 78,59)/2 = 79,23 → B = (79,99 + 78,55)/2 = 79,27 t/s (+0,06%). mvs (T=0): 433,2 → 433,4 t/s (+0,06%). W parach z tej samej sesji: 10-21 +0,16% / +0,09%, 11-20 −0,05% / +0,02%. Zysku nie widać ponad szum, więc nie włączać do produkcji. W produkcji tej zmiennej nie ma: brak `BIG_ROWS` w `run-topka.sh` i `run-llm.sh`. Logi: `~/qwen-opt/queue/logs/i43g-{A1a,B1a}.log`, `k039-i43g-{B1b,A1b}.log`, jobs `qwen-opt/k039/xq.jobs`

### K-040 · Flaga kompilatora `-mllvm --amdgpu-unroll-threshold-local=600`
- data: 2026-11-07
- źródło: `R/68a-rdna3-kernele.md:126` (4.8)
- test: build + `klab isadiff` gorących kerneli (CPU); GPU tylko, gdy ISA się zmienia: `llama-bench -p 4096` + spec_sweep ABBA + md5 ≤ 10 min
- zysk: 0…2% [INFERENCE]
- ryzyko karty: brak (spille przy większej liczbie VGPR)
- priorytet: niski (tani, mały)
- wynik 2026-11-20: pominięte. Na serwerze Jarvo nie ma ROCm (`hipcc` brak), a build HIP i `klab isadiff` trzeba robić na jaroserverai, czyli na maszynie z GPU, której ten przebieg nie używa.

### K-041 · Licznik realokacji grafu (#30329): czy przejścia MTP5 ↔ W16 ↔ catch-up przebudowują graf albo taśmę PM4
- data: 2026-11-07
- źródło: `R/68d-swieze-od-spolecznosci.md:141` (#7)
- test: XTX serwer testowy, replay sesji agenta, licznik w logu + `GGML_HIP_PM4_DEBUG`; ≤ 10 min
- zysk: 0% wprost; kilka % na krokach zmieniających szerokość, jeśli realokacje istnieją [INFERENCE]
- ryzyko karty: brak
- priorytet: niski (diagnostyka)
- wynik 2026-11-20: serwer produkcyjny (PM4 WA=2 + GUARD) z `GGML_HIP_PM4_DEBUG=1`. Replay agentpath `w6.json`: 4 sesje po kolei, 24 tury, 98,9k tokenów prefillu, 3k wygenerowanych, 140 s. Taśm budowanych jest 81 na 967 uruchomień taśmy (każda użyta średnio ~12 razy), czyli ~3,4 przebudowy na żądanie. **Rozmiary są zawsze tylko dwa: 809 i 107 dispatchy**, więc szerokości MTP / W16 / catch-up nie tworzą nowych taśm. Przebudowy to ponowne przechwycenie tych samych dwóch grafów, prawdopodobnie po każdym prefillu [INFERENCE]. Do tego 77 małych grafów (12–14 kernel) idzie zwykłą ścieżką HIP graph, 518 uruchomień grafu bez taśmy, 13 eksmisji kolejki (0 w trakcie taśmy). Następny krok, jeśli warto: zmierzyć koszt jednej przebudowy (ms) × ~3,4 na żądanie. Log: `~/qwen-opt/queue/logs/k041-realloc2.log`, `~/qwen-opt/k041/out/launch.log`

### K-042 · Spekulatywny prefill następnej tury w przerwie (serwer prefilluje swoją odpowiedź, przerywa na granicy ubatcha)
- data: 2026-11-07
- źródło: `R/68c-dlugi-kontekst-gdn.md:140` (#6)
- test: XTX replay sesji (`agent_bench`): TTFT na turę, trafienie prefiksu (LCP), md5 „trafienie vs zimny start”; ≤ 10 min/ramię
- zysk: ~10–25% czasu małych tur [SZACUNEK], więcej przy ≥ 128k
- ryzyko karty: brak (GPU zajęte w przerwach)
- priorytet: niski (zależne od klienta)

### K-043 · Profil i optymalizacja atencji draftu MTP przy długim kontekście (~1,3 ms/krok przy 199k), np. pamięć MASW (ujścia + okno + sloty)
- data: 2026-11-07
- źródło: `R/68c-dlugi-kontekst-gdn.md:144` (#10), [[2026-11-08-kvq-once-profil]] (`:92`)
- test: offline symulacja akceptacji MTP z oknem 128 + sloty; potem spec_sweep + xtxbench 199k. Wymaga treningu adaptera.
- zysk: sufit +3…5% przy 255k minus spadek akceptacji [SZACUNEK]
- ryzyko karty: brak
- priorytet: niski (trening, niepewne; samo okno MTP to KILL, K-090)

### K-044 · Leave-one-out łatek (`loo.py run`) i Kernel Tuner (`kt tune`) na GPU
- data: 2026-10-15 (runda 6)
- źródło: [[runda-6]], [[loo]], `Q/STATUS-NEXT.md:31-37`, `R/07-nasze-metody-uogolnienie.md:250-252`
- test: XTX `GGML_HIP_PM4=0`, po jednej łatce/fladze na job (xtxbench ~4 min); LOO ~3,8 h + buildy w sumie
- zysk: 0 t/s wprost; wykrywa łatki bez zysku (koszt utrzymania)
- ryzyko karty: niskie (mikrobenche)
- priorytet: niski (higiena)
- wynik 2026-11-21 (częściowo: tylko łatki z wyłącznikiem env, bez łatek „tylko build” i bez `kt tune`): **żadna łatka nie daje ≥ 3% na Qwenie, ale prawie wszystkie mierzalnie pomagają. Kandydaci do usunięcia: 52, 58 i 59 (Qwen), 62 i 64 (LFM).** Narzędzie `loo.py` zostało bez zmian; owijka `Q/k044/loo_topka.py` puszcza te same próby (ABBA) na silniku produkcyjnym `~/llama-topka` z kolejki, bez zagnieżdżonego flocka, port testowy, PM4 0. Qwen UD-Q4_K_XL, tg128 + serwer MTP n4 (2 prompty × 256 tok., T=0), 4 rundy. Spadek po wyjęciu łatki (95% CI) w serwerze: 31 top-k −2,72%, 33 replay GDN −1,58%, 29 asynchroniczne wejścia −1,45%, 24 para MMVQ −1,30%, 47 −1,23%, 28 −0,92%, 25 −0,91%, 30 −0,82%, 27 −0,65%, 38 −0,40%, 26 −0,28%. Neutralne: 48 (0,00%), 58 (+0,13% / tg +0,04%), 59 (−0,06% / tg −0,19%). Szybciej bez łatki: 52 (`GGML_HIP_MMVQ_N1_ROWS`) tg +1,31% ± 0,11, w serwerze +0,29% (neutralnie). LFM2.5-24B, 2 rundy, szerokie CI: najwięcej dają 48 (−13,7%), 31 (−12,2%), 50 tg (−9,4%), 53 tg (−6,7%), 29 (−6,0%), 49 tg (−5,3%), 51 (−4,5%). Szybciej bez łatki: 62 tg +0,39% i 64 tg +0,79%, w serwerze neutralnie. Pominięte: 60 (to sam PM4, a punkt odniesienia jest z PM4 0), 65 (flaga web UI, w produkcji i tak wyłączona), CLI 4 i 32 oraz 22 łatki „tylko build” (wymagają buildów z revertem, czyli pracy nad kodem). Decyzja o usuwaniu łatek należy do właściciela. Źródło: `~/qwen-opt/queue/logs/k044-*.log`, raport `~/qwen-opt/k044/loo/loo-report.md`, wyniki `loo-results.jsonl` (316 prób, 0 błędów).

### K-045 · Model kosztu weryfikacji MoE LFM2.5 (pomiar G1) i drafter dla LFM (LFM2.5-2.6B-QAD-Q4_0 jest na dysku)
- data: 2026-10-19 (raport 18), drafter 2026-10-14
- źródło: [[model-kosztu-weryfikacji-moe]], [[raport-24d-lfm-lookup]], archiwum (`A:36446`)
- test: XTX `llama-bench -p 1,2,3,4,5,8,16 -n 0 -d 0,32768` (bramki T(8) ≤ 13,6 ms, T(3) ≤ 6,8 ms); potem LFM24B + draft 2.6B spec_sweep T=1 + `mvs`; ≤ 10 min każdy
- zysk: decyduje, czy tani drafter dla LFM ma sens (od α ≈ 0,4); LFM poza produkcją
- ryzyko karty: VRAM (+1,6 GB draftera przy KV q8_0 131k)
- priorytet: niski (LFM poza produkcją)
- wynik 2026-11-21: **bramka G1 na surowym `llama-bench` niespełniona; po odjęciu narzutu ścieżki pN spełniona tylko przy d0.** Build `~/llama-topka`, LFM2.5-24B-A2B Q5_K_M, KV q8_0, PM4 0. Surowe T(N) = N / t/s przy d0: T(1) 7,56, T(2) 8,42, T(3) 8,86, T(4) 8,93, T(5) 13,18, T(8) 15,09, T(16) 20,94 ms. Przy d32768: 6,53 / 8,90 / 10,03 / 10,77 / 15,15 / 17,12 / 23,50 ms. Bramki T(3) ≤ 6,8 i T(8) ≤ 13,6 ms padają w obu głębokościach. Ścieżka pN ma stały narzut: ten sam build daje tg128 239,6 t/s (4,17 ms na token) przy d0 i 217,3 t/s (4,60 ms) przy d32768, a p1 7,56 i 6,53 ms. Po odjęciu tej różnicy: przy d0 T(3) ≈ 5,5 ms (model 5,47) i T(8) ≈ 11,7 ms (model 9,58), obie bramki spełnione; przy d32768 T(3) ≈ 8,1 i T(8) ≈ 15,2 ms, obie niespełnione. Wyraźny skok między 4 a 5 kolumnami (+4,3 ms) wskazuje, że od 5 kolumn działa inny kernel [INFERENCE]. Jeśli drafter, to najwyżej 3 tokeny draftu (weryfikacja 4 kolumn). Drugiej części testu (LFM24B + drafter 2.6B, spec_sweep) nie uruchamiałem: bramka nie przeszła jednoznacznie, a LFM jest poza produkcją. Źródło: `~/qwen-opt/queue/logs/k045-g1.log`, `k045-tg.log`, skrypt `Q/k045/k045.sh`.

### K-046 · Szerokość ogona lookup zależna od kontekstu: W16 → W8/W5 przy ≥ 128k (`LLAMA_SPEC_LOOKUP_ADAPT=1`)
- data: 2026-10-18, 2026-11-07 (68c #7)
- status: **czeka na decyzję** (bramka K-007, zmiana szerokości zmienia md5)
- źródło: `R/68c-dlugi-kontekst-gdn.md:141`, [[kontroler-szerokosci-draftu]]
- test: najpierw dane z CPU (`LLAMA_SPEC_LOOKUP_LOG`: udział kroków `tail` przy n_past ≥ 128k); XTX `ADAPT=1` vs W16 na replayu 128–200k ABBA ≤ 10 min
- zysk: krok W16 przy 255k to ~+20–25 ms; zależy od udziału ogonów (kill < 2% kroków)
- ryzyko karty: brak
- priorytet: niski (najpierw dane)

### K-047 · GDN w weryfikacji: forma chunkwise/WY w fp32 albo fuzja conv + rekurencja + gated RMSNorm ze stanem w VGPR
- data: 2026-11-05 (63 #21)
- status: **czeka na decyzję** (inna kolejność redukcji fp32 → bramka KLD, nie md5)
- źródło: `R/68b-spekulacja-nowe.md:162`, `R/68-SYNTEZA.md:20`; ta sama fuzja (conv1d + SiLU + norma Q/K + rekurencja) w kernelu weryfikacji KDA u TokenSpeed ([[tokenspeed]], 2026-11-14)
- test: XTX `test-backend-ops perf -o GATED_DELTA_NET` (n 5/8/16), spec_sweep ABBA, KLD + md5 plain; ≤ 10 min/krok
- zysk: +1,1…1,7% na każdym kontekście [SZACUNEK]; tańszy wiersz dla drzew (K-075)
- ryzyko karty: brak
- priorytet: niski (poniżej progu)

### K-048 · Mikrobatch prefillu `-ub 1024` dla Qwena (po odzyskaniu VRAM)
- data: 2026-10-12 (A7)
- status: **czeka na decyzję**, jeśli md5 ≠ (zmiana ub zmienia kolejność sum)
- źródło: `Q/NOTES.md:218` (ub 2048 pp +3%, OOM przy 204800), `R/63-SYNTEZA.md:84`
- test: XTX md5 greedy 12k ub 512 vs 1024 (jeśli różne → do Odrzuconych); jeśli równe, `llama-bench -p 4096 -ub 1024` + szczyt VRAM przy fill 255k osobnym jobem
- zysk: pp4096 +3…8% [SZACUNEK]
- ryzyko karty: **VRAM OOM przy 262k**
- priorytet: niski (OOM, numeryka; po K-022/K-034)
- wynik 2026-11-21: **ub 1024 zmienia wynik i nie przyspiesza → odrzucić.** md5 greedy (prompt 12k, T=0, 256 tok., konfiguracja produkcyjna na porcie testowym, kolejność 512/1024/1024/512): ub 512 `8f23c7d9` w obu przebiegach, ub 1024 `669c414a` w obu, czyli inna kolejność sum. Prefill 12k: 894,7 → 871,1 t/s (−2,6%). `llama-bench` pp4096 (PM4 0, FA 83, ABBA): 1003,1 → 994,5 t/s (−0,9%). VRAM po starcie serwera przy ctx 262144: 22955 → 23352 MiB (+397 MiB). Przy 255k z ub 512 zostaje 1193 MiB zapasu, więc wypełnienia 255k z ub 1024 nie uruchamiałem (ryzyko OOM, a zysku i tak nie ma). Źródło: `~/qwen-opt/queue/logs/k048-md5.log`, `k048-bench.log`, skrypt `Q/k048/k048.sh`.

### K-049 · ROCm 10.1 na gfx1100: md5 + hash logitów + pomiar `kvq` (spill 8 VGPR)
- data: 2026-10-16 (raport 13), 2026-11-05 (63c)
- źródło: [[rocm-10-1]] (`:28-30`), [[lekcja-rocm10-lds-128kb]]
- test: build topki na `~/opt/rocm-10.1` (CPU), XTX md5 greedy/long 32k + xtxbench t1; ≤ 10 min
- zysk: nieznany (RDNA-FAST: 10.1 +3,1% vs 7.2 na innej bazie); `kvq` może zwolnić przez spill
- ryzyko karty: nowy runtime + PM4 (możliwy fault/reset)
- priorytet: niski (niepewny zysk, ryzyko)

### K-050 · Runtime ROCm 7.2.4 z kompilatorem ROCm 10
- data: 2026-11-07
- status: **czeka na decyzję** (pobranie runtime)
- źródło: `R/68a-rdna3-kernele.md:127` (4.9)
- test: XTX `LD_LIBRARY_PATH` na 7.2.4, `llama-bench -p 512,4096 -d 0,16384 -r 3` ABA ≤ 10 min, potem soak PM4
- zysk: prefill 0…+5% (dane z innej XTX); decode ~0 (PM4 omija runtime)
- ryzyko karty: **wysokie**: PM4 zależy od ROCr/CLR (raport 17), page faulty/resety
- priorytet: niski (ryzyko > zysk)

### K-051 · Wyjaśnić ~16 tys. wierszy `amdgpu: init_user_pages: Failed to get user pages: -1` przy każdym starcie serwera
- data: 2026-11-06
- źródło: [[init-user-pages-failed]]
- test: XTX dwa starty serwera `--mmap` vs `--no-mmap`, licznik wierszy w `journalctl -k`, bez obciążenia; ≤ 10 min
- zysk: diagnostyka (krótszy start, czystszy log jądra); 0 t/s
- ryzyko karty: brak
- priorytet: niski (diagnostyka)
- wynik 2026-11-20 (`journalctl -k` działa bez sudo): start serwera produkcyjnego na porcie testowym. `-lm mmap` (domyślne `auto` = mmap) daje **15 553** wiersze `init_user_pages: Failed to get user pages`, a `-lm none` (bez mmap) **0**. Start do health w obu wariantach 5–6 s. Wiersze pochodzą więc z mapowania pliku modelu przez mmap. Para jest jedna: powtórka nie zmieściła się w 10 min, bo liczenie `journalctl` po długim boocie jest wolne. W topce flaga to `-lm`, nie `--no-mmap`. Log: `~/qwen-opt/queue/logs/k051-mmap2.log`, skrypt `qwen-opt/k051/mmap.sh`

### K-052 · HRX (Lemonade `hrx-b99`) jako referencja kerneli: tg128/pp512/pp4096 obok topki
- data: 2026-11-07
- źródło: `R/68a-rdna3-kernele.md:125` (4.7)
- test: XTX `llama-bench -fa 1 -p 512,4096 -n 128 -r 3` HRX vs topka, eco (~30 min → 3 joby); wymaga buildu i pobrania HRX
- zysk: 0% wprost; wzór do portu, jeśli HRX wygra prefill (producent: +30–50% vs HIP upstream)
- ryzyko karty: nieznany runtime (inne kolejki, bez gpu-guard)
- priorytet: niski (wiedza)

### K-053 · Wspólne punkty odniesienia: zestaw YASAKANI/NInfer (12 zadań + edycja) na XTX
- data: 2026-11-05
- źródło: `R/63-SYNTEZA.md:104` (#25), `R/63a-silniki-lokalne.md` §9
- test: XTX ~15 min (2 joby)
- zysk: wiedza i porównanie 1:1 z innymi silnikami; 0 t/s
- ryzyko karty: brak
- priorytet: niski (wiedza)
- wynik 2026-11-21: **12 zadań NInfer zmierzone, edycji YASAKANI nie ma na dysku.** Zestaw: 12 scenariuszy z `examples/cli/manifest.json` klonu NInfer (kod, proza, tłumaczenie, dane strukturalne po 3). Ustawienia jak u YASAKANI: greedy, thinking off, limit 4096 tokenów, bez cache promptu. Konfiguracja produkcyjna (MTP n4, lookup W16) na porcie testowym. Ich edycja kodu (`textwrap`) i JSONL 300 zamówień są prywatne, więc ich nie ma. Dekod w t/s, licząc jak YASAKANI, czyli (tokeny − 1) / czas generacji: kod 150,2 / 157,4 / 141,6, dane JSONL 190,8 / CSV 142,6 / SQL 169,3, proza EN 140,9, proza ZH 64,7 i 46,4, tłumaczenie ZH→EN 127,2, EN→ZH 68,9, markdown 76,6. Mediana z 12 zadań to 141,3 t/s. Dla porównania YASAKANI JSONL 160 wierszy daje ~455 t/s po przeliczeniu na pasmo XTX i bajty wag (`R/63a-silniki-lokalne.md` §9), a my na JSONL 190,8. Słabe są zadania z chińskim tekstem: akceptacja draftu 18%, 6% i 21% wobec 62–76% w kodzie i danych. Prawdopodobna przyczyna to okrojony słownik głowicy draftu (65 536 tokenów) [INFERENCE]. Źródło: `~/qwen-opt/queue/logs/k053-a.log`, `k053-b.log`, skrypt `Q/k053/k053.py`.

### K-054 · EvalPlus z `--effort xhigh` vs `low`: czy effort low kosztuje dokładność
- data: 2026-11-09
- źródło: [[2026-11-09-evalplus-qwen-uncensored]] (`:25`), [[evalplus-jakosc-kodu]]
- test: XTX `~/qwen-opt/evalplus/jakosc-mini.sh --effort xhigh --port 8097 all` (HE+ 164 + MBPP+ 378; > 10 min, podzielić po zbiorze)
- zysk: jakość, nie prędkość; potwierdza albo zmienia domyślny effort low (dziś HE+ 92,7%, MBPP+ 80,2%)
- ryzyko karty: brak
- priorytet: niski (nie prędkość)
- wynik 2026-11-21 (częściowo: HE+ 130 ze 164 zadań, MBPP+ 98 z 378; 10 jobów po ≤ 10 min, codegen wznawiany): **xhigh nie poprawia dokładności, a kosztuje ~3,7× więcej tokenów, więc domyślne low zostaje.** Konfiguracja produkcyjna na porcie testowym, `EFFORT=xhigh`. Porównanie z przebiegiem low z 2026-11-09 na tych samych zadaniach. HumanEval+ plus: 94,6% (123/130) → 93,8% (122/130), base 97,7% → 94,6%. MBPP+ plus: 85,7% → 85,7% (84/98), base 95,9% → 95,9%. Między ramionami przechodzi inny zestaw zadań: 7 zadań zmienia wynik w HE, 10 w MBPP. Tokeny na odpowiedź: HE 730 → 2637, MBPP 613 → 2386. Przy xhigh 4 odpowiedzi HE i 3 MBPP dobiły do limitu 32 768 tokenów. Dekod 134–135 t/s. Źródło: `~/qwen-opt/queue/logs/k054-*.log`, `~/qwen-opt/evalplus/runs/uncensored-xhigh/`, `uncensored-xhigh-pad/`, skrypty `Q/k054/k054.sh`, `k054_cmp.py`.

### K-055 · Usunąć z topki martwy kod capu LDS FA (`57204db1e`, no-op na ROCm 10.0 pre4) przy najbliższym buildzie
- data: 2026-11-06
- źródło: [[2026-11-05-q63-topka]] (wynik negatywny), dawny wpis `DO-ZAPISANIA.txt`
- test: przy następnym buildzie produkcji bramka md5 (long 32k e460e3b6, fill 255k 31b6525a); bez osobnego okna GPU
- zysk: 0 (porządek w kodzie)
- ryzyko karty: brak
- priorytet: niski (przy okazji)
- wynik 2026-11-20: usunięte w `llama-duo` (gałąź `duo`), commit `e1f9524` = czysty revert `57204db1e` (tylko `ggml/src/ggml-cuda/fattn-common.cuh`, −53 linie, ani `GGML_HIP_FA_OCC_*`, ani skrypty uruchomieniowe go nie używały). Bez buildu; bramka md5 (long 32k e460e3b6, fill 255k 31b6525a) przy najbliższym buildzie produkcji.

### K-056 · Rebase łatek topki na nowszy upstream (baza b11528 → llama.cpp v1.0.0 = b12359)
- data: 2026-10-16, ostatnio 2026-11-07
- źródło: [[2026-10-16-rebase-v070]], `R/68d-swieze-od-spolecznosci.md:14,18` (#31247 przesunie md5)
- nowe (2026-11-14): v1.0.0 zawiera już u nas portowane #30137, a do tego #30541 (kopia stanu dla skwantowanego KV, K-001), #31533 (few-row MMQ CUDA, K-013/K-103), #31927 (MTP czyta stan celu z bufora na urządzeniu), #32078 (tylko fuzowany GDN), #32009/#32089 (ponowne użycie schedulera), #31838 (ROCm: stały workspace BLAS); API: `defrag_thold` usunięte, NextN w `llama.h`
- test: build (CPU), XTX greedy md5 vs baza, `test-backend-ops`, spec_sweep A/B ≤ 10 min/ramię; zmiana md5 przez #31247 → bramka KLD
- zysk: poprawki upstream; prędkość ~0 (68d: „prawie wszystko topka ma mocniej”)
- ryzyko karty: nowe kernele w PM4
- priorytet: niski (mało zysku)

### K-057 · Tryb „identyczne odpowiedzi” `LLAMA_SPEC_BITEXACT=1` jako opt-in (port gałęzi `batch-invariant` na topkę)
- data: 2026-10-16 (raport 12)
- status: **czeka na decyzję** (wdrożyć przełącznik, domyślnie wyłączony)
- źródło: [[2026-10-16-bit-exact]], [[otwarte-decyzje-techniczne]] (`:14`), `STAN-PRAC.md` (BitExactSpec, `365af3e5e`)
- test: XTX `validate.sh` (plain == MTP) + spec_sweep krótko i przy 27k; ≤ 10 min
- zysk: ujemny (0% krótko, −9% przy ~27k); wartość: dowód bezstratności
- ryzyko karty: brak
- priorytet: niski (nie przyspiesza)

### K-058 · Strażnik „drugie `</think>` zabronione” w `reasoning-budget.cpp` (T7, niezależny od Astry)
- data: 2026-11-09
- status: **czeka na decyzję** (2d; zmienia wyjście tylko przy przecieku)
- źródło: `R/69-SYNTEZA.md:27,37-40` (A3), [[astra-stop]]
- test: build + md5 bazy (musi być =) + skan 50 zadań agentowych; ≤ 10 min/partię
- zysk: 0 t/s; poprawność formatu
- ryzyko karty: brak
- priorytet: niski (nie szybkość)

### K-059 · Pomiar w warunkach LocalMaxxing (`reasoning-v1`/`code-v1`, T=0, 320 tok.) do publikacji wyników XTX
- data: 2026-10-16
- status: **czeka na decyzję** (publikacja „wkrótce”, na razie tylko odczyt: [[2026-10-20-bez-publikacji-localmaxxing]], [[2026-11-09-decyzje-runda-69]])
- źródło: [[raport-32f-ninfer-tqllm]], [[raport-32d-localmaxxing]]
- test: XTX ~15 min (2 joby)
- zysk: 0 t/s (marketing); szacunek ~147 t/s w ich warunkach
- ryzyko karty: brak
- priorytet: niski (nie wydajność)
- zwiad 2026-11-14: XTX top verified na LocalMaxxing nadal 97,2 t/s (llama.cpp IQ3_S MTP); szacunek topki w ich warunkach ~147 ([[zwiad-2026-11-14]])

### K-060 · Pilot fabryki RSI-F: P0 (`./factory verify claims/2026-10-17-mmq-epi-0070.json`) i P1 (playbook 0070 na nowe cele)
- data: 2026-10-19 (21h)
- status: **czeka na decyzję**
- źródło: [[KOLEJKA-TESTOW]], [[petla-rsi-f]], [[otwarte-decyzje-techniczne]] (`:21`)
- test: XTX `GGML_HIP_PM4=0`, P0 ~20 min → 2 joby, P1 4 × 15–20 min
- zysk: walidacja fabryki, 0 t/s
- ryzyko karty: brak
- priorytet: niski (proces)

### K-061 · Tryb wielu użytkowników na NVIDIA: naprawić start `-np 4` z MTP (`failed to create context`), potem k zależne od liczby klientów (`K_BY_B`)
- data: 2026-10-21 (raport 56)
- źródło: `R/67c-nvidia-backlog-testow.md:110` (B16), `R/67-nvidia-vast-kampania.md` §7.2 (`-np 2` agregat +30…36%), `R/69b-tensorfold-qwen-warp.md:77`
- test: 5060 Ti: `-np 2/4` ctx 32k + MTP n=2, C = 1/2/4/8 klientów, suma t/s; ≤ 10 min
- zysk: agregat +20–30% (dane warp: ×2,7–2,9 przy 4–8 klientach); latencja 0
- ryzyko karty: VRAM OOM
- priorytet: niski (jeden użytkownik)

### K-062 · Dekoder FA CUDA z `__launch_bounds__(…,2)` (dual-CTA)
- data: 2026-11-07
- źródło: `R/67c-nvidia-backlog-testow.md:121` (C4), `R/66b-1cat-tokenspeed.md:97-98`
- test: 5060 Ti: perf FA + long_ctx, md5; ≤ 10 min/krok (po K-027)
- zysk: 1Cat V100 128k +19% bitowo; u nas po `kvq` nieznane
- ryzyko karty: brak
- priorytet: niski (po profilu)

### K-063 · Wyzwalacz PDL + prefetch L2 przed `pdl_sync` w gęstym MMVQ (sm_120) i sterowanie L2 (`evict_first`, persisting window `GGML_CUDA_L2_PERSIST`)
- data: 2026-10-19 (21b)
- źródło: [[pdl-mmvq-trigger]], [[l2-persist]], `R/67c-nvidia-backlog-testow.md:122-125` (C5–C8)
- test: 5060 Ti: `GGML_CUDA_MMVQ_PREWAIT=0/1/2`, `WEIGHT_EVICT_FIRST`, `L2_PERSIST`, md5 + tg128/spec_sweep ABBA; ≤ 10 min każdy; kill < +1,5% LFM tg128
- zysk: LFM +1,1…4,6%, Qwen +0,7…2,6% (PDL); L2 +0,5…2% [SZACUNEK]
- ryzyko karty: brak
- priorytet: niski (małe)

### K-064 · Zwinięcie haka promptu MTP do grafu celu (TTFT) w forku CUDA
- data: 2026-10-16
- źródło: `R/67c-nvidia-backlog-testow.md:113` (B19), `R/15d-prefill-dlugi-kontekst.md:110`
- test: 5060 Ti: build + TTFT 512/2k, md5; ≤ 10 min
- zysk: TTFT −5…7% przy 2k
- ryzyko karty: brak
- priorytet: niski (mały TTFT)

### K-065 · Zimny start `--no-mmap` (pierwszy prompt po restarcie 0,39–1,07 t/s) i nieprzetestowane flagi upstream (`--spec-draft-n-ubatch 64`, `GRAPH_CHUNK_SIZE`, `-fa off`, `--spec-default`)
- data: 2026-11-07
- źródło: `R/67c-nvidia-backlog-testow.md:79-91` (A4, A8, A10, A12, A16)
- test: 5060 Ti, po jednym ramieniu na job ≤ 10 min
- zysk: A12: TTFT pierwszego żądania; reszta ~0 [INFERENCE]
- ryzyko karty: brak
- priorytet: niski (UX)

### K-066 · Pipeline kafli MMQ w stylu DeepGEMM / strojenie configu MMQ IQ4_XS (`mmq-config-ampere.cuh`) pod prefill CUDA
- data: 2026-10-16 (15d), 2026-10-21 (Orca)
- źródło: `R/67c-nvidia-backlog-testow.md:133` (C16), sesja Orca (`O:1788-1796`, `O:2187-2196`: occupancy 2 → −11,5%)
- test: przebudowy compile-time + `llama-bench -p 512,4096` + md5/PPL; 5060 Ti lokalnie, 3090 wynajem
- zysk: pp +3…12% (DeepGEMM), +10–20% (config IQ4_XS) [SZACUNEK]
- ryzyko karty: brak
- priorytet: niski (dużo pracy)

### K-067 · Kernel GDN chunked MMA w CUDA zintegrowany z cache i snapshotami (gałąź `orca-gdn2`)
- data: 2026-10-21 (Orca)
- źródło: sesja Orca (`O:1449-1462`: +10,5% pp2048, ale PPL nan; po poprawce 0%; `O:1791`)
- test: PPL + md5 + pp2048, 3090 (wynajem), 2–3 h → podzielić
- zysk: do +10% prefillu
- ryzyko karty: brak
- priorytet: niski (numeryka do naprawy)

### K-068 · CUDA `kvq`: KLD wariantu z wyjątkiem n=1 D256 q4_0 (`678473a27`) i serwer MTP@64k z wyjątkiem
- data: 2026-10-18
- źródło: `STAN-PRAC.md` (CudaKvq, „Niezmierzone”), [[2026-10-16-kvq-cuda-zostaje]]
- test: `llama-perplexity --kl-divergence --chunks 5` Qwen q4_0 ub1 + serwer MTP 64k; 3090 (wynajem) albo 5060 Ti przy mniejszym kontekście; ≤ 10 min/ramię
- zysk: poprawność (przy ub1 = vec z konstrukcji [INFERENCE])
- ryzyko karty: brak
- priorytet: niski (formalność)

### K-069 · Turing sm_75 (2080 Ti): build forka i smoke test
- data: 2026-11-07
- źródło: `R/67c-nvidia-backlog-testow.md:149` (D6)
- test: build `-DCMAKE_CUDA_ARCHITECTURES=75`, `test-backend-ops`, fork vs upstream; wynajem ≤ 10 min po buildzie
- zysk: nieznany; poprawność dla klasy 11 GB w Enigmie
- ryzyko karty: brak
- priorytet: niski (mała klasa)

### K-070 · NVIDIA: soak termiczny 600 s przy fill 262k (E3) i sweep limitu mocy → perf/W na wynajętych kartach (E1)
- data: 2026-11-07
- status: E1 **czeka na decyzję** (zmienia limit mocy; czy zasada „karta fabrycznie” obejmuje karty z wynajmu); E3 otwarte
- źródło: `R/67c-nvidia-backlog-testow.md:152,154`
- test: E3 `stab soak_s=600` (10 min); E1 4 ramiona × ~3 min (`nvidia-smi -pl` 100/85/70/55% TDP), tylko wynajem
- zysk: dane do „cichego trybu” Enigmy; 0 t/s
- ryzyko karty: E1 zmiana mocy; E3 temperatury
- priorytet: niski (produkt)

### K-071 · qwen-warp: DFlash2 ≤ 64k na replayu agentowym (W2)
- data: 2026-11-09
- status: **czeka na decyzję** (3,85 GB pobrania na wynajmie)
- źródło: `R/69-SYNTEZA.md:29` (W2), `R/69b-tensorfold-qwen-warp.md:65`
- test: 3090 (wynajem), ten sam replay co spec_sweep, oba drafty, ~10 min/ramię
- zysk: czat ×1,07–1,34, agent z kopiowaniem −31% (dane autora); u nas −10…+10% [INFERENCE]
- ryzyko karty: brak
- priorytet: niski (agent traci)

### K-072 · Nemotron 3.5 Bolt na NVIDIA: KLD fuzji `GGML_CUDA_TOPK_MOE_NP2`, `MMVQ_N1_IQ2`, kernel IQ2_XXS MMVQ, replay stanu Mamby
- data: 2026-10-16 (raport 14 §10)
- status: **czeka na decyzję** (model odłożony „na później”)
- źródło: `R/14-nemotron-3090.md`, `R/67c-nvidia-backlog-testow.md:114` (B20), `STAN-PRAC.md` („Odłożone”)
- test: 3090/4090 (wynajem), KLD vs upstream (~$0,3) + A/B per łatka ≤ 10 min
- zysk: 87,2 → 141,1 t/s już zmierzone; KLD warunkuje publikację; łatki razem +6,1%
- ryzyko karty: brak
- priorytet: niski (model poza katalogiem)

### K-073 · Flint (NVFP4) na XTX: rozstrzygnąć nieudany test igły przed katalogiem Enigmy
- data: 2026-10-21
- status: **czeka na decyzję** (inny model; PR #30928 niescalony)
- źródło: `R/59-flint.md`, archiwum (`A:37717-37753`)
- test: XTX needle przy długim kontekście, Flint na topce z poprawkami (`run-topka.sh flint`); ≤ 10 min
- zysk: ~2× vs Qwen27B na XTX, ale to zmiana modelu
- ryzyko karty: temperatury (prefill 160–262k: junction 94 °C, 286 W przed eco)
- priorytet: niski (inny model)

### K-074 · OrcaCyber-Nano na XTX z drafterem DFlash2 (dotąd tylko 3090) i E1 RSR-27B vs Qwen (TB 2.1, omp-bench-20)
- data: 2026-10-19 / 2026-10-21
- status: **czeka na decyzję** (Orca: tylko na prośbę; RSR-27B: wydatek $40–70, ~120 GPU-h)
- źródło: [[raport-56-orca-3090]], [[KOLEJKA-TESTOW]], [[otwarte-decyzje-techniczne]] (`:22`)
- test: Orca: XTX MTP vs DFlash2 ≤ 10 min; RSR: wynajem, test do zdefiniowania
- zysk: wiedza o innych modelach; 0 t/s dla produkcji
- ryzyko karty: VRAM (Orca 15,7 + 2,1 GB przy 262k)
- priorytet: niski (inne modele)

### K-075 · Drzewo weryfikacji MTP na hybrydzie GDN (forma WY, maska przodków)
- data: 2026-10-20 (24s), 2026-11-07 (66d C)
- źródło: [[drzewo-weryfikacji-gdn-wy]], `R/66-SYNTEZA.md:65`, `R/68b-spekulacja-nowe.md` („dziś kill”: +1,6% przy 0,85 ms/wiersz)
- test: najpierw symulacja `tree_dynamic` na logach MTP (CPU); na XTX tylko koszt wiersza (`test-backend-ops perf` MMVQ n=5 vs n=6) ≤ 10 min; wraca dopiero, gdy wiersz ≤ 0,57 ms (po K-013)
- zysk: kod/T=0 +3…8%, czat T=1 0…+4% [SZACUNEK]
- ryzyko karty: nowe kernele GDN w PM4
- priorytet: niski (zależne od K-013 i K-007)

### K-130 · Topka zbudowana ROCm 10.2 (hipcc/LLVM) vs 10.0: czy nowy kompilator przyspiesza nasze kernele
- data: 2026-11-19
- źródło: blog ROCm 10.2.0 (Telegram „gpu” 2026-11-19); wcześniej 10.1 nic nie dało ([[stos/rocm-10-1]])
- test: ROCm 10.2 w osobnym katalogu na jaroserverai (bez ruszania /opt/rocm 10.0 produkcji), rbuild topki tym samym commitem; `test-backend-ops` MUL_MAT/FA bitowo + xtxbench ABBA dekod 1,7k i prefill 32k, md5 T=0; ≤ 10 min karty
- zysk: nieznany (AMD nie wymienia gfx1100 GEMV/FA); próg przyjęcia ≥ 3%
- ryzyko karty: brak (PM4=0 w teście); ryzyko systemu: druga instalacja ROCm, tylko za zgodą właściciela (~3 GB)
- priorytet: niski

### K-131 · Fork CUDA na Ampere: MMVQ celu tylko 58% pasma na 3090 (4080 SUPER 78%) — strumieniowanie wag przez `cp.async`
- data: 2026-11-20
- źródło: [[2026-11-19-k118-nvidia-pelna-moc]] (plain 3090 19,2 ms = 540 GB/s z 936; 3060 60%; 4080S 78%); TensorFold v1.3.0 #2266: rura `cp.async` per warp w dekodzie ekspertów NVFP4 +24% na sm_120, bity te same
- test: CPU: `ncu` niedostępne bez karty, więc najpierw przegląd kodu MMVQ IQ3_XXS/IQ4_XS forka (szerokość ładowań, wypełnienie SM); potem Vast 3090 (reaper, ≤ 10 min): `llama-bench -p 0 -n 128` i `test-backend-ops MUL_MAT` n=1, wariant z `cp.async`/ładowaniami 128-bit vs fork, md5 T=0
- zysk: do +30% dekodu plain na 3090 [INFERENCE: 58 → 75% pasma], spekulacja proporcjonalnie (weryfikacja to ten sam kernel, łączy się z K-013)
- ryzyko karty: brak (wynajem)
- priorytet: średni

### K-132 · Jądro Linux 7.0/7.2 vs 6.8 na jaroserverai (start, cache promptów w RAM) i odciążanie MoE z `mmap` na CPU
- data: 2026-11-20
- źródło: [[telegram-2026-11-20-linux-7-2-pamiec]]
- test: (1) CPU teraz, bez karty: model MoE z odciążeniem z `mmap` przy ograniczonym RAM (cgroup), refault i t/s, jądro 7.0 (serwer Jarva) — pomiar bazowy; (2) jaroserverai za zgodą właściciela: boot 7.x obok 6.8, start do /health, TTFT po restore z `--cache-ram` przy presji RAM, dekod 1,7k (kontrola), PM4 i amdgpu bez błędów
- zysk: start i przywracanie cache promptów; porady dla Enigmy przy odciążaniu; dekod XTX bez zmian [INFERENCE]
- ryzyko karty: zmiana jądra pod ROCm 10.0 i PM4, tylko za zgodą właściciela
- priorytet: niski

## W toku

(pusto)

## Zrobione

### K-118 · Powtórka K-114 dla 3090 i 3060 na hostach z pełną mocą (dzisiejsze wyniki to dolne granice)
- data: 2026-11-17
- źródło: [[2026-11-17-k114-nvidia-sufit]] (3090: 250 z 420 W, pamięć 5001 z 9751 MHz → 23% sufitu; 3060: 135 z 170 W, 85 °C → 42%); [[lekcja-vast-tylko-pelna-moc]]
- hipoteza: na pełnej mocy 3090 osiąga ≥ 50% sufitu dekodu (jak 5060 Ti 61%), plain ≥ 70% pasma; 3060 ~50%; rozkład kroku (draft 4–15 × bajty) bez zmian
- test: `qwen-opt/cloud/k114/launch.sh "RTX 3090" qwenbench-k118-3090` i to samo dla „RTX 3060” (hostguard przed pobraniem, hosty z `hosty-zle.txt` pomijane), ten sam model GSQ IQ3_XXS-mtp i runner; `summ.py` bez flagi LIMITED HOST; host z mocnym CPU (start: requant 12 min na słabym)
- dodatkowo (audyt 2026-11-19): K-114 szedł przy ctx 8192, czyli diagnostyka, nie wynik karty (decyzja ≥ 131k); w K-118 dodać ramię ≥ 131k (plain + n2 przy głębokości ~128k)
- miara: t/s n2/n4 T=0/T=1, plain, prefill ~3k/~11k i % sufitu vs dolne granice 44,4 / 28,6 t/s
- koszt: ~$0,15–0,25 za obie karty [INFERENCE: 3090 ~$0,22/h, 3060 ~$0,07/h, ~40 min]; **nie wynajmować przy kredycie $0,16** — czeka na doładowanie i zgodę właściciela
- ryzyko karty: brak (wynajem)
- priorytet: średni
- **wynik 2026-11-19 ([[2026-11-19-k118-nvidia-pelna-moc]]):** pełna moc: 3090 n4 T=0 47,1 → 86,6 t/s (+84% vs dolna granica), n2 89,5 / 79,6; 3060 33,0 (+7%), n2 34,0 / 31,8; nowa 4080 SUPER n4 107,3 / 91,2. Plain 58–78% pasma; prefill 3090 1349–1386, 4080S 1554–1862 t/s. Ramię 95,6k: 3090 plain 30,2 → n2 71,8 t/s, prefill 925 t/s

### K-127 · Fork CUDA: build z AVX2 (`kvqlean`) vs bez (`kvqleana`) — czy pobieracz ma wybierać wariant po flagach CPU
- data: 2026-11-19
- źródło: audyt Gemini (C.1.4d) potwierdzony: `engines.json:516,534` wysyła wszystkim `kvqleana`, bo „the downloader cannot choose by CPU flags”; `app/engine/src/hw/linux.ts:274` już czyta cpuinfo
- test: 5060 Ti (Vast, hostguard, host z AVX2): spec_sweep T=1 ABBA kvqlean vs kvqleana, md5 T=0
- miara: t/s, czas startu (requant draftu na CPU)
- zysk: jeśli ≥ 3% albo krótszy start → wybór po flagach w pobieraczu; inaczej zostaje
- ryzyko karty: brak
- priorytet: niski (można połączyć z K-004 na jednej instancji)
- **wynik 2026-11-19:** różnica ≤ 1,4% (szum) na 3090, 3060 i 4080 SUPER, start 10–26 s w obu → zostaje `kvqleana` dla wszystkich ([[2026-11-19-k118-nvidia-pelna-moc]])

### K-125 · KLD ścieżki `kvq` (łatka 0011) dla Qwena na XTX — kvq jest BLIŻEJ referencji f16 niż standardowy kernel
- data: 2026-11-19 (zgłoszone i zrobione tego samego dnia)
- źródło: audyt Gemini (C.2.3a): [[fattn-kvq]], `08-analiza-platformy-latek.md:395`; bramka [[bramka-kld-kanarki]]
- test: `llama-perplexity --kl-divergence`, Qwen3.8-27B-Uncensored Q4_K_M, wikitext-2, `-c 8192 --chunks 2 -ub 5`, PM4=0; referencja KV f16; base = KV q4_0 z `GGML_HIP_KVQ_OFF=1`, cand = KV q4_0 z kvq (produkcja), cand2 = powtórka
- wynik: base → kvq: średnie KLD 0,004522 → 0,003862 (−14,6%, −3,4 σ), top-1 97,06 → 97,60%, 99,9% KLD 0,170 → 0,138, maks. 0,61 → 0,36; powtórka identyczna co do bitu; PASS ([[2026-11-19-k125-k001-xtx]])
- przy okazji: pierwszy przebieg nieważny (wyłącznik przez `ggml_cuda_env_switch` był włączony domyślnie) → [[lekcja-env-switch-domyslnie-wlaczony]]

### K-123 · Czy nasza weryfikacja spekulacyjna (GPU_VERIFY / sprzężona) przyjmuje drafty po EOG — błąd naprawiony w strix-llama.cpp `4b43cfb96`
- data: 2026-11-19
- źródło: [[zwiad-2026-11-19]] (rejekcja bez przerwania po EOG zostawia drafty w slocie, następna tura je czyta; upstream `9581154` ma przerwanie tylko w ścieżce greedy, `common/sampling.cpp:709`)
- hipoteza: nasza ścieżka T=1 (`LLAMA_GPU_VERIFY=1`, `LLAMA_SPEC_COUPLED`) nie przerywa po EOG → po turze w slocie zostają tokeny po końcu odpowiedzi; to może też dokładać do zależności md5 od historii serwera (K-001) [INFERENCE, mała szansa: K-001 mierzone przy T=0]
- test: CPU, gdy jaroserverai online: przegląd kodu weryfikacji w gałęzi `topka-q70` i w forku CUDA (`kvqlean`); jeśli błąd jest: test na porcie testowym — tura T=1 kończąca się EOG z aktywnym draftem, `n_past` slotu vs długość odpowiedzi; poprawka = przerwanie po EOG jak w greedy
- miara: liczba tokenów w slocie po turze (oczekiwane = prompt + odpowiedź); md5/rozkład następnej tury
- zysk: poprawność (agent nie czyta śmieci po końcu odpowiedzi), 0 t/s
- ryzyko karty: brak
- priorytet: wysoki (poprawność, tani przegląd kodu)
- **wynik 2026-11-19** ([[2026-11-19-k111-k123-krok-xtx]]): przegląd kodu 3191b25f4 — produkcja (MTP + coupled) i forki CUDA (draft greedy) idą ścieżką `sample_and_accept_n` z przerwaniem po EOG; ścieżka rejekcji ma ten sam brak co strix-llama.cpp, ale działa tylko przy `--spec-draft-sampling probabilistic` bez coupled; poprawka obronna przy najbliższym buildzie

### K-111 · Rozłożyć lukę kroku MTP do sufitu: 26,9 ms zmierzone vs 19,2 ms sufitu pasma przy 2k (dekod czatu na 71–77% sufitu)
- data: 2026-11-17
- źródło: [[skill-io-sufity]] (ceiling.py na naszych rozmiarach: weryfikacja 16,1 GB + 4 drafty × 0,4 GB ÷ 926 GB/s); [[raport-24r-mmvq-pasmo]] (weryfikacja N=5 osiąga 762 z 926 GB/s); profil kroku 26,3 ms stałej części ([[2026-11-08-kvq-once-profil]])
- hipoteza: luka 7,7 ms to (a) MMVQ weryfikacji poniżej pasma (~82%), (b) 4 sekwencyjne kroki draftu z małymi kernelami, (c) głowica LM, (d) przerwy hosta; największa część to (a)+(b)
- test: XTX, rocprofv3 na kroku przy 1,7k (`GGML_HIP_PM4=0` do rozbicia, potem czas taśmy PM4): ms i GB/s na grupę kerneli vs ich sufit bajtowy; ≤ 10 min
- miara przed/po: tabela grupa → ms zmierzone / ms sufitu / % ; wybór dźwigni o największej luce (×prawdopodobieństwo)
- zysk: diagnostyka; każda 1 ms z kroku = +3,7% dekodu
- ryzyko karty: brak
- priorytet: wysoki (wskazuje, gdzie leży 30% zapasu dekodu)
- **wynik 2026-11-19** ([[2026-11-19-k111-k123-krok-xtx]], bez karty, ślad rocprofv3 z 2026-11-07): krok 27 ms = MMVQ weryfikacji 20,2 ms (800 GB/s, 86%) + MMVQ draftów 1,9 ms (~830 GB/s; na XTX draft ≈ bajty) + ~3,5 ms małych kerneli (normy 1,07, GDN 0,82, kvq 0,66, reszta ~1); dźwignie: sprawność MMVQ (+~5%), pakiet norma+bramka+zapis KV (+~5,5% [INFERENCE])

### K-109 · Bramka igieł długiego kontekstu (3 kody przy 50% i ~85–100% z 262k), dokładna odpowiedź — warunek „najlepsze” i część bramki wdrożenia
- data: 2026-11-17
- źródło: [[skill-io-metodyka]] (`methodology.md:37-38`, SKILL.md:95-98), [[skill-io-publikacja]] (bramka 5 przy 85% okna); `bench.py document()` (`:107-119`)
- hipoteza: topka-q70 (KV q4_0, FA83) znajduje 3/3 kody przy 131k i 223k; jeśli nie, KV q4_0 przy długim kontekście psuje odczyt (fill md5 tego nie wykrywa)
- test: XTX, produkcja na porcie testowym, `bench.py run --long 131072` i osobno `--long 223000` (fill ~8 min każdy → 2 joby kolejki)
- miara: retrieval k/3 per głębokość, TTFT, decode po fillu, szczyt VRAM; po PASS dopisać do `deploy-q70`/przyszłych bramek
- zysk: poprawność (dowód 262k), 0 t/s
- ryzyko karty: temperatury przy fillu (junction < 95 °C, eco 2200)
- priorytet: wysoki (luka w bramce produkcji)
- **wynik 2026-11-19** ([[2026-11-19-k109-k110-k106-xtx]]): topka-q70 3/3 igły przy 130 376 i 221 728 tokenach (50% i 85% okna), prefill 650,8 / 527,0 t/s, dekod po fillu 105,9 / 86,3 t/s — PASS

### K-110 · Ich `bench.py` bez zmian na XTX (port testowy): liczby 1:1 z ich 3090/B70 i z LocalMaxxing-like warunkami
- data: 2026-11-17
- źródło: [[skill-io-skrypty]]; ich wyniki 3090 Qwen3.8-27B EXL3 3 bpw + MTP 96,2 proza / 141,1 kod (`README.md:33`)
- test: config jak `examples/config-existing-server.json` (temperatura 0,6, prefill 4k/16k, c1 6 × 512 tok.); produkcja na porcie testowym; ≤ 10 min
- miara: c1 mediana, prefill 4k/16k, TTFT krótkiego promptu; porównanie z ich tabelą i z naszym spec_sweep (inny harness, opisać różnice)
- zysk: publikowalna liczba porównawcza; 0 t/s
- ryzyko karty: brak
- priorytet: średni (marketing i kalibracja harnessów)
- **wynik 2026-11-19** ([[2026-11-19-k109-k110-k106-xtx]]): c1 110,3 t/s (T 0,6, 6 × 512), prefill 839 t/s @2,8k i 933 t/s @10,9k, TTFT 140 ms

### K-106 · Interferencja prefill–decode przy agentach: ile pisanie jednego wątku traci, gdy drugi wątek wysyła długi prompt
- data: 2026-11-15
- źródło: [[mapa-inferencji-roadmap]] (luka #1); agenci mają przez 37% czasu ≥ 2 żądania w locie, prefill to 58% zegara sesji ([[2026-10-19-workload-omp]])
- test: XTX, produkcja na porcie testowym (`-np 1`): strumień A dekoduje 512 tok. przy 1,7k, w trakcie wchodzi żądanie B z promptem 32k. Mierzyć: czas do kolejnego tokena A (blokada), sumaryczną ścianę A i B vs sekwencyjnie, md5 obu. ≤ 10 min
- zysk: wiedza; jeśli A stoi przez cały prefill B (~40 s przy 32k), kandydat na podział prefillu na kawałki przeplatane z dekodem (bezstratne dla A) [SZACUNEK]
- ryzyko karty: brak
- priorytet: średni (agenci, tani pomiar)
- zwiad 2026-11-16: Superfluid (arXiv 2611.17753) przesuwa interaktywne żądania przed pracę agentów w jednym harmonogramie, czyli kandydat na rozwiązanie, jeśli K-106 pokaże długą blokadę ([[zwiad-2026-11-14]])
- **wynik 2026-11-19** ([[2026-11-19-k109-k110-k106-xtx]]): przy `-np 1` A nie stoi (maks. przerwa 39–89 ms), B czeka na resztę A (TTFT 39,2 vs 36,6 s), ściana = sekwencyjnie, md5 te same; przeplot prefillu ma sens tylko przy `-np > 1` (odrzucone K-086) — zamknięte

### K-114 · NVIDIA: rozłożyć krok MTP na 3090, 5060 Ti i 3060 względem sufitu — fork jest na 41–59% sufitu dekodu, XTX na 69–71% (+ K-112 prefill w tym samym runie)
- data: 2026-11-17
- źródło: [[skill-io-sufity]] (tabela „zmierzone a sufit”: 3090 80,0 z 160, 4090 101,3 z 172, 5090 148,6 z 251, 5060 Ti 49,4 z 120); metoda jak K-111
- hipoteza: luka do sufitu na NVIDIA to głównie (a) próbkowanie CPU przy T=1 (K-004, 7–13%), (b) kroki draftu MTP n2/n3 z małymi kernelami, (c) limit mocy hosta; MMVQ CUDA blisko pasma
- **wstępna odpowiedź z danych, które już mamy** (2026-11-17, bez nowego pomiaru), z R69b na wynajętej 3090 przy limicie mocy 350 W, czyli fabrycznym (`qwen-opt/cloud/nv69q/gpu.csv`, `summary.txt`):
  - (c) limit mocy odpada dla 3090;
  - (a) próbkowanie przy T=1 to 82,9 → 76,9 t/s, czyli −7%;
  - **qwen-warp na tej samej karcie robi 121–124 t/s przy 82,9/76,9 forka (× 1,46–1,61), choć czyta więcej bajtów** (INT4 18,6 GB + MTP 0,85 vs Q4_K_XL 16,8). Większość luki to więc silnik: kernele weryfikacji i draftu oraz host między krokami, czyli (b). Sprzęt ani pasmo nie są przyczyną.
  - Wniosek: nowy run ma rozbić (b) na składniki.
- **zgoda właściciela 2026-11-17 02:31:** wynajem 3090, 5060 Ti i 3060 na Vast, łącznie ≤ $1. Wstrzymane, bo jaroserverai jest wyłączony, a na serwerze Jarva nie ma klucza Vast ani CLI.
- runner gotowy: `qwen-opt/cloud/k114/run.sh` + `k114/bench.py` (kopia `nv69q/bench.py`). Ten sam model na trzech kartach (GSQ IQ3_XXS-mtp 10,44 GB, mieści się w 12 GB przy ctx 16k), fork `kvqlean`/`kvqleana`. Mierzy:
  - limit mocy i zegary;
  - tg128 (czas przebiegu celu → GB/s vs sufit);
  - pp5 ub5 (koszt weryfikacji);
  - pp4096/pp16384 (prefill, K-112);
  - serwer MTP n4/n2/n4 przy T=0/T=1.

  Krok = weryfikacja + drafty + host.
- uruchomienie (z jaroserverai): `up.sh <oferta> --hours 1.5 --disk 40 --label qwenbench-k114-<karta> --download-gb 11 --go`, scp `k114/*` do `/root/k114/`, `setsid nohup bash /root/k114/run.sh &`, znacznik `/root/res/DONE`, `down.sh <id> --go`. Szacunek: ~45 min, ~$0,35–0,50 za trzy karty [INFERENCE: ceny ofert z listopada]
- test: jak w runnerze wyżej, po jednej instancji na kartę; ≤ 10 min pomiaru na ramię
- miara przed/po: tabela grupa kerneli → ms / GB/s / % sufitu bajtowego; ms na host między krokami
- zysk: diagnostyka; wskazuje dźwignię dla wszystkich użytkowników Enigmy z NVIDIA (spodziewane +10…25%, bo luka do poziomu XTX to 10–28 pp sufitu)
- ryzyko karty: brak (5060 Ti 160 W)
- priorytet: wysoki
- **wynik 2026-11-17** ([[2026-11-17-k114-nvidia-sufit]], Vast $0,33):
  - 5060 Ti n2 T=1 51,0 t/s (61% sufitu), n4 49,4 (51%), plain 74%, prefill 788–828 t/s (43–47%);
  - 3060 (135 W) n2 28,6 (42%), n4 28,0 (35%), plain 53%, prefill 442–461 (46–47%);
  - 3090 (host 250 W, pamięć 5001 MHz) n4 44,4 (23%), plain 34%, prefill 319–696 (12–26%).
- **odpowiedź na hipotezę:** (b) tak, draft 4,8–9 ms vs ~1 ms bajtów, 37–40% kroku → K-116; (a) nie, krok przy T=1 bez zmian, strata to akceptacja; (c) tak na hostach Vast 3090/3060. Start 12 min na słabym CPU → K-117.

### K-103 · Enigma NVIDIA: silnik na llama.cpp v1.0.0 (few-row MMQ #31533) zamiast pinu b11856, z MTP
- data: 2026-11-14
- źródło: [[telegram-2026-11-14-pearlquant-llamacpp-v1]]; PR #31533 (Qwen3.8-27B + DFlash2, 7 draftów: 3090 Ti 57,6 → 77,7 tok/s, +34,9%; RTX PRO 6000 +16,7%; 5090 +20,6%; 80/80 rozmów szybciej, KLD jak master); pin b11856 został, bo b12110 był ~9% wolniejszy z MTP na sm_120 ([[final-recipes-nvidia]])
- test: 5060 Ti lokalnie: spec_sweep T=1 + `mvs`, MTP n 2/4, pin b11856 vs v1.0.0 (b12359), ABBA ≤ 10 min; `llama-bench -p 576 -n 0 -ub 4,8,16` przed/po; KLD vs upstream jak w kampanii 67
- zysk: weryfikacja MTP/DFlash na NVIDIA +10…35% tok/s (dane autora); jeśli regresja b12110 z MTP nie wróci, nowe przepisy Enigmy dla wszystkich kart NVIDIA
- ryzyko karty: brak
- priorytet: wysoki (duży zmierzony zysk, tani test lokalnie)
- wynik 2026-11-14 (Vast 5060 Ti, 150 W, ~0,10 USD): spec_sweep T=1 MTP n2 b11856 43,95 → v1.0.0 45,62 t/s (+3,8%, mediany ABBA; parami +3,5 / +4,2%), ms/krok bez zmian; przebieg weryfikacji ub 8 +12,1%, ub 16 +9,8%, ub 4 +2,8%; brak regresji b12110. Bramka (druga instancja): KLD vs b11856 0,000700 ± 0,000026 przy szumie upstreamu 0,000569–0,000615 (~2σ ponad), MTP n3 39,94 → 40,17 t/s (+0,6%) → **pin zostaje b11856** (nie bezstratne, poniżej progu, +48 MiB VRAM przy zapasie 4090 46 MiB) ([[2026-11-14-k103-llamacpp-v1-nvidia]])

### K-003 · Rozłożyć stały koszt ~210–230 ms na każde żądanie (TTFT krótkich promptów) i dokończyć tańszy zapis stanu GDN (stash `opt-s4`)
- wynik 2026-11-14: koszt stały to serwer, nie HTTP: ściana 258 ms = prompt 139 (restore checkpointu GDN 11–32, 2 checkpointy 2×11, prefill 5–8 tok. w 2–3 przebiegach ~80–100) + dekod 8 tok. 105 + poza serwerem 2 ms; dawne ~75 ms to harness klienta. Kontynuacja: K-104. [[2026-11-14-k002-k003-k013-xtx]]


## Odrzucone

### K-116 · NVIDIA (i XTX): draft MTP kosztuje 4–15 × swoje bajty — graf CUDA/HIP na całą pętlę draftu i fuzja kroku draftu
- data: 2026-11-17
- źródło: [[2026-11-17-k114-nvidia-sufit]] (krok n4 5060 Ti 51,1 ms = cel 31,3 + 4 × ~5 ms; bajty draftu ~0,9 ms); na XTX ten sam pomiar to K-111
- dodatkowo (2026-11-18): kolejka uruchomień CUDA ma ~1024 kernele (pomiar 4060 Ti, [[skill-io-pulapki]]); w `nsys` sprawdzić, czy krok z 4 draftami bez grafu nie dobija do tego limitu (host czeka na GPU)
- **metodyka (audyt 2026-11-19):** K-114 przypisał całe 51,1 − 31,3 ms czterem draftom, bez odjęcia krańcowego kosztu weryfikacji N=5 względem N=1 (w archiwum nie było `llama-bench`). Najpierw zmierzyć V(5) − V(1) (`llama-bench -p 1,5 -ub 1/5 -n 0` z buildu z llama-bench), dopiero potem `nsys` i ms/draft
- hipoteza: narzut pętli draftu (osobne launche: warstwa MTP, głowica 64k, argmax/sampling, synchronizacja hosta po każdym kroku) dominuje; jedna sekwencja grafu na n draftów zbliży koszt draftu do bajtów
- test: 5060 Ti (Vast ~$0,10 albo lokalnie w jaroserverai): `nsys` jednego kroku n4 (fork `kvqlean`), czas draftu na kernel i przerwy hosta; po prototypie grafu ABBA spec_sweep T=0/T=1, md5 T=0 bez zmian; ≤ 10 min na ramię
- miara przed/po: ms/draft (5060 Ti 4,8–5,2 ms → cel ≤ 2 ms), t/s n4 T=1 49,4 → cel ≥ 60
- zysk: do +40% dekodu na NVIDIA [INFERENCE: jeśli draft = bajty], podobnie na XTX; wszyscy użytkownicy Enigmy
- ryzyko karty: brak
- priorytet: wysoki
- **odrzucone 2026-11-19 ([[2026-11-19-k118-nvidia-pelna-moc]]):** V(n) z upstream llama-bench: draft kosztuje 0,5–0,9 ms ≈ swoje bajty (3090, 3060, 4080 SUPER). Luka kroku to weryfikacja V(5)/V(1) = 1,26–1,64, nie pętla draftu; dźwignia przechodzi do K-013

### K-104 · Krótki ogon promptu w jednym przebiegu zamiast 2–3 (granice checkpointów GDN)
- powód: 2026-11-14 A/B (świeże serwery, P/C/V/P2): prompt krótkiej tury 148,7 → 148,5 ms (0%), a `SHORT_TAIL=32` zmienia md5 (greedy, 1,7k) i obniża decode 1,7k 135,4 → 128,0 t/s; diagnoza K-003 o 2–3 przebiegach była błędna ([[2026-11-14-k104-krotki-ogon-promptu]])

### K-002 · Sprawdzić, czy ogon lookupu W16 spowalnia pisanie przy krótkim kontekście
- powód: 2026-11-14 przy 1,7k T=0 produkcja 130,4 t/s vs bez lookupu 131,2 (R1 128,2 vs 129,2; R1b 133,9 = 133,9), te same drafty i md5 → lookup W16 nie spowalnia krótkiego kontekstu ([[2026-11-14-k002-k003-k013-xtx]])

### K-076 · Astra-Stop (LoRA rank-1 skracająca myślenie)
- powód: zmienia zachowanie, przeciek `</think>` 11/32; decyzja właściciela 2026-11-09 ([[2026-11-09-decyzje-runda-69]], [[astra-stop]]). Wraca tylko jako temat fine-tuningu z benchmarkami.

### K-077 · DSpine-27B jako drafter (także test τ T1)
- powód: na 24 GB obcina kontekst do ~64k, proza i PL gorzej niż MTP, mieszanka agentowa +0…4%; decyzja 2026-11-09 ([[drafter-dspine]]).

### K-078 · Zmiana kwantu dla prędkości (lżejszy GGUF wzorem qwen-warp ×1,24, IQ4_XS/Q4_0, mieszanki per tensor, LFM Q4_K_M/QAD-Q4_0, EXL3, NVFP4, Flash-Next, DCQ)
- powód: zmienia odpowiedzi; zakaz właściciela „nie zmieniamy kwantów, żeby przyspieszyć” ([[dcq-kotwica-stanu-gdn]], [[2026-11-09-qwen-warp-vs-fork-3090]]).

### K-079 · Stratna atencja i KV: QSA, LSA, KVA, FLy, KV 3-bit / FP8 / blok 16, PearlQuant (E8, 3,2 bita), stan GDN fp16/bf16/int8, Nucleus SD, `--cache-reuse-hybrid`, HIP fast-math, chunked GDN bf16, `kvq` CUDA P·V f32
- powód: zmienia odpowiedzi (KLD ≠ 0); decyzja „tylko bezstratne” ([[2026-11-05-tylko-bezstratne]]).

### K-080 · FA D256: 83 + `exp2f` (maska 91), config #31746, `nbatch_fa` 32
- powód: zmienia md5 (stratne, ~+1,5% fillu); tylko w pakiecie stratnym z bramką KLD ([[2026-11-08-fa-d256-prefill]]).

### K-081 · PFlash: stratny tryb „szybki odczyt długich dokumentów”
- powód: stratny; decyzja „tylko bezstratne” ([[tryb-stratny-pflash]]).

### K-082 · Uncensored jako tryb w locie (rzut `h ← h − r(r·h)`) / restore KV z drugiego modelu
- powód: nie jest bit-exact (inne wagi efektywne) ([[przelaczanie-main-uncensored]]).

### K-083 · Wykrywacz pętli myślenia / kierunek pętli jako LoRA (WSP E1–E3)
- powód: zmienia odpowiedzi; decyzja właściciela. Obserwacja: 1/290 odpowiedzi jakość-mini zapętliła się do 32 768 tok. ([[2026-11-09-jakosc-mini-qwen-unc]]).

### K-084 · Podkręcanie VRAM, wymuszony FCLK, limit mocy, undervolt XTX
- powód: karta zostaje fabrycznie ([[2026-10-20-karta-fabrycznie]]); jedyny wyjątek to wdrożony eco 2200 ([[2026-11-06-profil-eco-2200]]).

### K-085 · Cache sesji na SSD / slot save przeżywający restart (`--slot-save-path`)
- powód: decyzja „KV tylko w RAM” ([[2026-10-19-kv-tylko-w-ram]]). Szacunek przy powrocie do tematu: pierwsza tura po restarcie przy 50k ~55 s → ~2–4 s.

### K-086 · Więcej slotów `-np 2` / `-np k` na XTX dla roju agentów
- powód: zmierzone 24c: pojedyncze żądanie −5…−17%, fan-out omp wall +11%, ~2,4 GB stanu na slot ([[wyniki-negatywne]]).

### K-087 · `kvq` raz na weryfikację: ONCE=1 / ONCE=2 i przegląd podziałów
- powód: KILL 2026-11-08: ONCE=1 FA −6,1% (e2e +0,9…1,8%), ONCE=2 −0,38%, podział domyślny najlepszy ([[2026-11-08-kvq-once-profil]]). Cel nowego układu żyje w K-012.

### K-088 · Q6_K MMQ: skale jednym `int`
- powód: KILL 0,0% ([[2026-11-07-q6k-mmq-skale]]).

### K-089 · Cache tokenizacji + parser O(n) / parser raz na krok MTP (l1tok)
- powód: −85 ms na turę (tokenizacja 14,0 → 6,6 ms), md5 =, ale poniżej progu ≥ 1 s/turę ([[2026-11-08-l1-tokenizacja-parser]], [[strumien-on-wyrocznia]]).

### K-090 · Okno uwagi draftu MTP (`--spec-mtp-window`, mtpw)
- powód: KILL 2026-10-14, job mtpw anulowany przez właściciela 2026-11-09; zysk maks. ~1,3 ms/krok.

### K-091 · Łatka 0071 `GGML_HIP_MOE_GU_BLOCK` (LFM gate+up)
- powód: LFM +0,33%, Uncensored +1,39%, poniżej progu 3–5% ([[2026-10-18-lfm-moe-pasmo]]).

### K-092 · Drobne kernele poniżej progu: LaunchCut, shortlist draftu EAGLE, Q6_K/Q4_K MMVQ big_rows/stream, GDN bank v3, merge split-KV, split-K MMVQ 1024, taśma delt GDN, fuzje kleju GDN, cięcia granic poza łańcuchem MMVQ, `opt-gdn6`, dalsze rundy klab
- powód: zmierzone −1,9…+0,7% (szum) albo ≤ 2% u autora; kernele na 77–88% z 926 GB/s, zapas leży w drafterze ([[runda-6]], `R/54-mniej-granic.md`).

### K-093 · PM4-PDL, prefetch wag do Infinity Cache, trwała siatka zamiast PM4, czekanie LFM po stronie GPU w taśmie PM4
- powód: 16a: PDL −0,11 µs, MALL w szumie; PM4 z guardem ma 0 faultów; czekanie GPU-side w taśmie = ryzyko resetu za ≤ 1,2% LFM ([[trwala-siatka-bez-pm4]]).

### K-094 · Prefetch L2 w pętli MMVQ (CUDA, `ncols_dst ≥ 2`) i szeroki loader `mmvq_ld` (b128)
- powód: KILL: −0,4…−0,8% i −1,0% tg128 ([[mmvq-prefetch-l2]], [[mmvq-n1-wiersze]]).

### K-095 · Próg pewności draftu `p_min`, obcinanie po iloczynie (`LLAMA_DRAFT_CUMP`), adaptacyjna długość z historii, bitexact + adaptacyjna głębokość (E5)
- powód: `p_min` 0,3 neutralne, 0,5 −7%, 0,5/0,8 gorzej na NVIDIA; E5 ≈ 0; żywa jest tylko wersja z luką Gumbela (K-008). Wyjątek: MoE z offloadem w Enigmie (K-026).

### K-096 · Lookup nadpisujący MTP („zastąp, gdy pewny”)
- powód: −1…−2%, bo MTP trafia w 96,8% tam, gdzie lookup (`R/15b`).

### K-097 · DFlash / DFlash2 na XTX: blok „draft 16, verify k”, słownik głowicy, `LLAMA_DFLASH_SAMPLE`, tryb kod/T=0 EN
- powód: szeroki blok wolniejszy (89,7 vs 104,8 t/s), PL proza ×0,67, MTP + lookup wygrywa; inny tekst T=0 niż produkcja ([[qwen-runda-5]]).

### K-098 · Douczanie głowicy MTP na polskiej prozie (self-distillation 20M tok.)
- powód: pilot 1,7M tok. dał −0,2…+0,2%, głowica jest na optimum ([[2026-10-16-mtp-pl-pilot]], [[lekcja-mtp-glowica-optimum]]).

### K-099 · Bezstratna kompresja wag (entropia, styl DFloat11) czytana w locie
- powód: skale to 2,19% bajtów UD-Q4_K_XL; sufit ≤ 5%, realnie < 1% (24t).

### K-100 · Ścieżka Vulkan, kernele 2-bitowe dla Saluki, MiniCPM5-2B przy 131k
- powód: decyzje właściciela (ROCm domyślny od 2026-10-12, Saluki porzucony 2026-10-14, CC BY-NC); MiniCPM poza produkcją.

### K-101 · `LLAMA_LFM2_MSG_SPANS=1` (start sesji LFM 230 → 166 ms)
- powód: −64 ms tylko dla LFM, poniżej progu ≥ 1 s/turę ([[REKORDY]] `:66`).

### K-102 · Bisekcja regresji prefillu forka vs upstream na NVIDIA z 15d (−1,5…−1,9%)
- powód: część wyjaśnił hak MTP (2,2–2,6% TTFT, 16f); reszta poniżej progu i zastąpiona szerszą K-023.

## Powiązane
- [[index]]
- [[REKORDY]]
- [[ZRODLA]]
- [[decyzje/_hub|decyzje]]
- [[sweep-wariantow-kernela]]
- [[xtxbench-szybki-ab]]
