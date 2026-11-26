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

### K-182 · Kernel weryfikacji na rdzeniach tensorowych dla K-quantów przy 2–16 wierszach (wzór qwen-warp `k_w4`), Ampere i RDNA3
- data: 2026-11-26 ([[qwen-warp-dlaczego-szybszy-2026-11-26]])
- powód: warp czyta wagi z 92–96% pasma i weryfikuje 16 wierszy za ×1,52 kosztu jednego; nasz fork 57% pasma, V(5)/V(1) = 1,59; to główna bezstratna przyczyna kopii 64k 77 vs 137 t/s
- krok 1 (10 min, następna fala Vast 3090): GB/s naszych MMVQ Q4_K/Q5_K/Q6_K przy n=1…16 per kształt (test-backend-ops perf + nsys jednego kroku), ta sama tabela dla XTX z kolejki
- krok 2: prototyp kernela (kafel 16 wierszy, dekwantyzacja w rejestrach, `mma`/WMMA z tokenami jako B, trwały strumień), bramka bitowa wobec obecnego MMVQ przez test-backend-ops + KLD
- zysk szacowany: krok weryfikacji 43,5 → ok. 28 ms na 3090 (przypuszczam), więcej przy kopii
- priorytet: najwyższy (NVIDIA i XTX)

- **wynik pomiaru 2026-11-26 02:43–02:51 (XTX, q4_K/q6_K, kształty produkcji, zimne):** q4_K n=1 853–860 GB/s (89%), n=2–5 784–864 (82–90%), n=8 688–723 (72–75%), n=12 643–656 (67–68%), n=16 631–643 (66–67%); V(16)/V(1) ≈ 1,33–1,35 dla dużych macierzy. Słabe punkty: ssm_alpha/beta 48×5120 (601 → 113 GB/s, V(16)/V(1) 5,3: koszt startu kernela) i attn_k/v 1024×5120 (856 → 531). q6_K lm_head 749–887. Cel K-182: n 8–16 z 67–72% do ≥ 85%, małe macierze przez fuzję startów. Prototyp k182b: build bez RPATH (exit 127), poprawiany.
- **K-182b 2026-11-26 05:45 (prototyp kernela weryfikacji, bitowo zgodny z emulacją CPU):** **NO-GO**: najlepsza konfiguracja c2_rt1ks4u1 ma 70,9% pasma przy n=2..16 i ×1,05 wobec obecnego kernela WMMA przy n=9..16; próg ≥5% na każde n i ≥10% łącznie nie spełniony. ffn_down 5120×17408 tylko 55–61% (gorzej niż produkcja 634–864 GB/s). Wniosek: przewaga warpa nie wynika z samego GEMV weryfikacji na naszych kształtach; zostają małe macierze (ssm_alpha/beta, koszt startu) jako tańszy cel.
### K-158 · Maya: mechanizmy DSpark z Nib (graf draftu, szerokość z pewności, top-k na GPU), żeby DSpark opłacał się przy T=0,7
- data: 2026-11-25 ([[nib-chromadera]]: Nib T=0,7 130–151 t/s vs Maya 112,5 tym samym klientem; u nas DSpark przy T=0,7 −11%, K-139)
- plan: `dspark_mtp.cpp:767-803` (graf draftu per długość), `server.cpp:2721` (szerokość = wiodące drafty z p>0,8), `kernels_mtp_verify.hip:155-345` (top-256 na GPU) przenieść do `ik2_draft.cu`/`ik2_main.cu`; parytet 11/11 + rep2 + wall.py
- zysk: +15…30% T=0,7 [SZACUNEK z różnicy do Nib]
- dopisane 2026-11-25 (zwiad): drzewo DSpark z Pando (2611.32269, 16 węzłów bez dodatkowego przejścia) i temperatura draftu 0,4–0,6 (2611.33111, +9–11% akceptacji), oba bezstratne przy próbkowaniu draftu z q
- priorytet: wysoki
- **wynik 2026-11-25 (gałąź Mai `k158-dspark` 7372462b, przełączniki `IK2_K158_DGRAPH/CONF/GSORT/SFXDS`, domyślnie wyłączone):** test kerneli OK, parytet 11/11 IDENTYCZNY (g, all, all-sl). rep2 Q1 (T=0) / Q6 (T=0,7) / L2k: plain 129,7 / 114,2 / 107,1; base (draft) 110,7 / 93,6 / 100,4; DGRAPH 100,1 / 93,9 / 101,8; CONF 148,8 / **70,1** / 97,2; all 148,8 / 70,4 / 97,0; all-sl-c0 121,1 / 84,2 / 100,8; GSORT bez drafta 129,7 / 114,8 / 107,2.
- wniosek: CONF daje +14,7% przy T=0 (148,8 vs 129,7), ale przy T=0,7 −39%. Statystyka (conf, T=0,7): 806 okien, 542 z 1097 draftów przyjętych = 1,67 tok./okno przy 70 t/s, czyli **ok. 24 ms na okno ≈ 2,7 zwykłego tokenu**; u Nib runda (draft 1,40 ms + weryfikacja m≈2,2 12,3 ms) ≈ 1,6 tokenu. Graf draftu nic nie dał, więc winna jest weryfikacja Mai przy małym m, nie host. Dalej K-158b: księga ms (plain, propose, verify(m) dla m=1..8, host) i poprawki weryfikacji.
- **K-158b 2026-11-25 (e76d3e33, `IK2_K158_BENCH=1` = księga rundy na prawdziwym modelu, P=1024, mediany 20 przebiegów):** zwykły token 9,37 ms; propose(7) 3,61 ms (warstwy 1,79, głowa 0,64, Markov 1,18); host < 0,2 ms wszędzie (nie jest problemem). verify(1/2/3/8) T=0: przed 13,08 / 17,32 / 21,47 / 39,98 ms; `IK2_K158_VATT` (atencja okna w jednym launchu) 13,09 / 16,54 / 19,79 / 34,15; `IK2_K158_VEXP` (eksperci okna kernelami tokenu) 12,20 / 15,67 / 19,48 / 36,75; **oba 12,21 / 14,94 / 17,79 / 30,87** (P=4096: 12,36 / 15,21 / 18,10 / 31,65). Parytet 11/11 dla vatt, vexp, vx, base-vx.
- części (GPU ms, zwykły token → okno 1 wiersza, vx): normy 1,29 → 1,56, qkv 1,74 → 2,64, atencja 1,79 → 1,75, wyjście 1,04 → 1,30, wejście MoE + router 1,58 → 2,60, eksperci 2,97 → 3,17, combine 0,50 → 0,74; eksperci rosną o ok. 2 ms na każdy dodatkowy wiersz (pasmo: 16 różnych ekspertów ≈ 2× bajtów).
- wniosek: nawet okno 1 wiersza kosztuje +2,8 ms ponad zwykły token, bo ścieżka okna nie używa fuzji tokenu (PCONV, FUSE). Nib: verify m≈2,2 ≈ zwykły + 3,8 ms, my vx verify(2) = zwykły + 5,6 ms. Następny krok K-158c: fuzje tokenu w oknie (cel verify(1) ≤ zwykły + 0,5 ms), tańszy Markov, sonda akceptacji przy top-k 40.
- **rep2 K-158b (Q1 T=0 / Q6 T=0,7 / L2k T=0):** plain 129,5 / 114,2 / 107,4; all 148,5 / 70,4 / 96,7; vatt 166,4 / 74,0 / 103,6; vexp 163,0 / 76,2 / 105,8; **vx 185,2 / 80,4 / 114,0** (powtórka 185,2 / 80,3 / 113,9); vx-c0 185,2 / 92,7 / 114,7; vx-sl 147,1 / 81,6 / **120,9**; base-vx (szerokość SpecCtl) 161,6 / 102,0 / 104,4. Czyli przy T=0: **+43% na krótkim i +6…13% na 2k**, przy T=0,7 każdy tryb z draftem traci. Dalej K-158c: polityka per zapytanie (T=0 → CONF+vx, T>0 → bez DSpark), fuzje tokenu w oknie.
- **K-158c 2026-11-25 (853f250e: fuzje tokenu w oknie `IK2_K158_VMVF16/VROUTE/VQKV/VCOMB`, polityka `IK2_K158_POLICY`, Markov `IK2_DRAFT_SHORTLIST=8`):** testy OK, parytet 11/11 dla f, f-sl8, f-pol, f-pol2, f-g8, f-sl8-pol. Bench P=1024: verify(1/2/3) f 10,58 / 13,52 / 16,67 ms (zwykły 9,39; verify(2) = zwykły + 4,1 ms, Nib + 3,8 — strona weryfikacji domknięta). propose 3,62 ms, z SL8 3,11 (Markov 1,18 → 0,66). Sonda (3 × 200 tok.): ok. 2 tok./rundę, okna prawie zawsze 2, a drafter zawsze robi 7 draftów → K-158d: wczesne wyjście drafta.
- rep2 Q1 / Q6 / L2k: produkcja 129,9 / 114,2–114,3 / 107,7–107,9; f 191,1 / 86,7 / 119,6; f-pol 191,1 / 110,9 / 119,6; **f-pol2 191,1 / 114,0 / 119,8** (T=0 +47% / +11%, T=0,7 bez zmian); f-sl8 195,2 / 88,7 / 128,0; **f-sl8-pol 195,2 / 110,9 / 128,1** (+50% / +19%, T=0,7 −3%); f-c0 191,1 / 95,3 / 118,3; f-g8 bez zysku.
- **wall.py ABBA (f-pol2 vs produkcja, 4 prompty × 300 tok.):** produkcja T=0 113,6 (code 110,6, tech 113,7, pl 113,5, json 113,6), T=0,7 112,8; f-pol2 T=0 **140,5 (+24%)**: code 162,8, tech 118,1, **pl 68,8 (−39%)**, json 187,9; T=0,7 112,2 (−0,5%). Nie wdrażamy: polski tekst ma niską akceptację, a CONF nie wycofuje się do zwykłego dekodu. K-158e: bramka adaptacyjna per zapytanie (cel: pl ≥ zwykły −2%).
- **K-158d 2026-11-25 (2e1a484c: `IK2_K158_EARLY` wczesne wyjście Markova, `IK2_K158_DQ8` drafter Q8):** EARLY_CHECK 0 różnic w 900 rundach (okno i drafty identyczne jak przy 7), parytet 11/11 dla early, early-q8, eq8-pol, early-q8-sl8, early-pol. propose przy 1/2/3 draftach: early 2,77 / 2,92 / 3,06 ms, early-q8 2,43 / 2,58 / 2,73 (warstwy 1,47, głowa 0,64, Markov 0,32). DSpark to drafter blokowy (8 wierszy naraz), więc wczesne wyjście tnie tylko Markova. Sonda (pomiar vs zwykły): early-q8 T=0 109,6 / 106,0, T=0,7 pełny 113,2 / 105,6, **T=0,7 top-k 40 116,2 / 105,6 (+10%)**; próg: najlepiej `IK2_K_CONF` 0,7–0,8 przy CMIN 0. rep2 Q1 / Q6 / L2k: produkcja 129,7 / 114,1 / 107,7; early-pol 194,4 / 111,2 / 122,7; **eq8-pol 196,9 / 111,4 / 123,2**; early-q8-sl8 199,1 / 92,7 / **131,1**; f 191,1 / 86,6 / 119,3. Dalej K-158e: bramka adaptacyjna `IK2_K158_GATE`, krótka głowa `IK2_K158_HSL` (jak Nib).
- **K-158e 2026-11-25 (20855b25: bramka `IK2_K158_GATE=1/2`, krótka głowa `IK2_K158_HSL`):** testy OK, parytet 11/11 (4 konfiguracje). propose przy 1/2 draftach: eq8 2,44 / 2,58 ms, **eq8-hsl 1,96 / 2,04 ms** (Nib 1,4). rep2 Q1 / Q6 / L2k: produkcja 129,7 / 114,2 / 107,8; eq8-pol-gate 196,9 / 111,4 / 124,0; **eq8-hsl-pol-gate 202,7 / 111,0 / 121,2**; eq8-pol2-gate2 196,9 / 114,4 / 105,4; eq8-hsl-pol2-gate2 202,7 / 114,1 / 105,8.
- wall.py (T=0: code / tech / pl / json; T=0,7 mediana): produkcja 110,9 / 113,9 / 113,8 / 113,9; 113,0. eq8-hsl-pol2-gate2 115,8 / 112,6 / **111,7** / **196,4**; 112,8. eq8-pol2-gate2 112,5 / 112,7 / 112,0 / 190,9; 112,9. Bramka chroni polski (−1,8% zamiast −39%), ale za wcześnie wyłącza draft na kodzie (115,8 vs 162,8 bez bramki) i GATE=2 psuje L2k (105,8 vs 121,2). Nie wdrażamy jeszcze; K-158f: strojenie bramki (dłuższa ocena, decyzja z akceptacji, nie z pierwszych 2 rund), GATE=1 dla długiego kontekstu.
- **K-158f 2026-11-25 (2cbb89f0: bramka z histerezą, sondy seriami, `c_plain` mierzone):** parytet 11/11. wall.py T=0 code / tech / pl / json (produkcja 101,2 / 113,5 / 113,4 / 108,8): pol2-gate **165,6 / 115,4 / 107,9 / 196,9** (kod +64%, json +81%, polski −4,9%); T=0,7 mediana 112,2 vs 112,2 (ale tech 101,5 do sprawdzenia). rep2 Q1 201,3, L2k 105,2 (spadek względem 121–124 z K-158e). Nie wdrażamy: polski poniżej progu −2% i L2k. K-158g: symulacja bramki offline (w benchu nie zadziałała), naprawa L2k.

- **wynik K-158g 2026-11-25 21:19–21:34 (`wt-k158g` 791e2a6f, GATE_DEFER):** parytet IDENTICAL 11/11. wall.py T=0: prod code 110,3 / tech 113,3 / pl 112,7 / json 112,9 → gated **169,3 / 115,6 / 110,8 (−1,7%) / 197,6**, mediana 112,8 → **142,5 (+26,3%)**; T=0,7 wszystkie kategorie = prod (112,7 → 112,9; pl 111,8 → 112,9), bo polityka wyłącza drafter przy próbkowaniu. rep2: Q1 129,5 → 202,7, Q6 113,8 → 114,0, **L2k 107,5 → 119,6 (+11,3%)**. Bramka −2% przechodzi (najgorzej pl T=0 −1,7%). Werdykt: **wygrany**, wdrożenie K-177.
- **K-179 2026-11-26 00:39–00:45 (K-148 both + K-158g gated w jednej binarce, `wt-k179` 1f11609e):** parytet IDENTICAL 11/11, kernel test PASS; wall T=0: code 111,2 → 169,5 (+52,4%), json 114,0 → 197,6 (+73,5%), tech +0,5%, **pl 113,8 → 110,8 (−2,7%, FAIL)**; T=0,7 wszystko ±0,1%; edycja `python_edit` ok. 293 → 395 t/s (+35%). Bramka nie przeszła o 0,7 pkt na polskim T=0 → wdrożony sam K-158g (K-177); do poprawy: polityka bramki dla polskiego w połączonej wersji.
- **K-158r 2026-11-26 12:59–13:10 (Maya, `wt-k158r` b1831852):** z planu brakowało tylko draftu przy T>0 (produkcja ma `IK2_K158_POLICY=2`, czyli drafter wyłączony dla żądań losowanych). Ramię A = `POLICY=0`, Q = A + losowanie draftu z rozkładu draftera (`IK2_K158R_QS=0.7`, odrzucanie min(1,p/q), rozkład celu bez zmian). Parity 11/11 identyczne, md5 T=0 identyczne. **T=0,7 vs produkcja: kod 110,6 → 171,8 (A) / 181,4 (Q) (+55/+64%), json 112,9 → 199,6 / 193,3 (+77/+71%), tech +2,4/+3,8%, pl −2,3/−3,0% (FAIL bramki −2%)**; mediana T=0,7 112,7 → 143,7 / 149,3. Strata pl to koszt bramki K-158g przy tekście losowanym, nie draftu. Poprawka K-158s (osobna bramka dla żądań losowanych) w kolejce.
### K-129 · Enigma NVIDIA: `DRAFT_N=2` zamiast 4 na Ampere i 5060 Ti (droga weryfikacja V(5))
- data: 2026-11-19
- źródło: [[2026-11-19-k118-nvidia-pelna-moc]]: n2 vs n4 T=1 3090 +7,9%, 3060 +4,3%, 5060 Ti +3,2% (K-114); T=0 +3,0…3,3%; 4080 SUPER bez różnicy
- test: CPU: wpis w `app/engine/data/engines.json` (DRAFT_N per architektura: sm_86 i sm_120 → 2, sm_89 → 4), `bun test`; potwierdzenie na 1 karcie Vast z md5 T=0 vs n4 (spekulacja bezstratna, tekst może się różnić tylko numerycznie)
- zysk: +3…8% dekodu dla użytkowników Enigmy z 30xx i 5060 Ti
- ryzyko karty: brak
- priorytet: wysoki (tanie, zmierzone na 3 kartach)
- wynik 2026-11-20: zrobione po stronie CPU. W profilu `qwen38-kvq-mtp4` silnika `enigma-cuda-fork` doszło `mtp.nMaxByArch` (`app/engine/data/engines.json`: sm_86 → 2, sm_120 → 2, reszta, czyli sm_89, zostaje 4); `mtpArgs`/`enigmaConfig` biorą n po architekturze karty (`app/engine/src/server/engine.ts`, wywołanie w `optimize.ts`). Test w `app/engine/test/enigma-cuda.test.ts` (sm_86/sm_89/sm_120 → 2/4/2); `bun test` 208 pass, 0 fail; `tsc` czysty. Planer pamięci dalej liczy draft dla n 4 (bezpieczny zapas). Uwaga: RTX 5090 (też sm_120) mierzona była tylko z n 4, więc dostaje 2 bez pomiaru. Zostaje potwierdzenie md5 T=0 n2 vs n4 na 1 karcie Vast.

- **2026-11-25 (L4, K-016):** n2 +6,9% i n3 +6,3% T=1 vs n4, kopia bez straty; brakuje 3090 i 5060 Ti (wynajem) przed zmianą domyślnej wartości Enigmy.
- **wynik 2026-11-26 (Vast 5060 Ti nvq, [[2026-11-26-nvq-5060ti]]):** 5060 Ti T=1: n2 53,55, n3 52,51, n4 45,54 (−15%), n5 47,45; kopia: n3 198,8 (+14,6% vs n2 173,5). Enigma: n2 domyślnie zostaje, n3 jako profil kopii; 3090 w drugiej paczce nvq.
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

- **2026-11-26:** adapter 0,64 GB (mniej niż 2 GB), ale decyzja „pracuj na tych co masz”; czeka na wyraźne „tak” JARO.
### K-122 · llamAmpere v0.7 w trybie dokładnym vs nasz fork na pełnej mocy 3090, ten sam plik wag (łączyć z K-118 na jednej instancji)
- data: 2026-11-18
- źródło: [[llamampere]] (nagłówkowe 110+ t/s przy T=1 w trybie mb-MTP, czyli nie dokładnym; drafter DFlash2 ×3,4 po usunięciu podwójnego kroku); [[2026-11-17-k114-nvidia-sufit]]
- hipoteza: w trybie dokładnym (`--no-spec-mb-mtp`, bez rzadkiej atencji, MTP) na UD-Q4_K_XL llamAmpere jest szybszy od forka (80 t/s) o ≥ 15%; różnica to narzut kroku draftu (K-116), a nie kernele głównego GEMV
- test: jedna instancja 3090 z hostguardem (ta sama co K-118): wydanie v0.7 (binarka znver3 — host z AMD Zen3+, inaczej build z tagu) i fork `kvqleana`/`kvqlean`, UD-Q4_K_XL, spec_sweep T=0/T=1 ABBA, `nsys` jednego kroku w każdym; KLD vs wyjście bazowe na 1280 pozycjach
- miara: t/s (fork → llamAmpere dokładny), ms kroku i ms/draft, KLD
- zysk: wskazuje gotowe rozwiązanie dla K-116 (port do Enigmy NVIDIA); koszt ~$0,15 razem z K-118 [INFERENCE]
- ryzyko karty: brak (wynajem)
- priorytet: średni (czeka na kredyt)

- **2026-11-26 (Vast 3090 nvq, [[2026-11-26-nvq-3090]]):** tylko ramię forka (T=0 93,48, T=1 88,16); build llamAmpere v0.7 nie zdążył przed terminem; do powtórki z buildem przygotowanym przed wynajmem.
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

- **2026-11-25 (Colab L4, torch, GPU bezczynne):** kopia w pamięci GPU 230,8 GB/s, fp16 GEMM 75,4 / 59,8 TFLOPS (4096³ / 8192³), int8 42,7 / 19,6 TOPS. Prefill vs upstream nie sparsowany. 5060 Ti i 3090 wymagają wynajmu.
- **wynik 2026-11-26 (Vast 5060 Ti nvq, [[2026-11-26-nvq-5060ti]]):** 5060 Ti: kopia GPU 386,2 GB/s, fp16 44,4 TFLOPS, int8 45,0 TOPS; prefill fork vs upstream b12110 pp4096 873,0 vs 884,8 (−1,3%), pp32768 768,7 vs 772,7 (−0,5%).
### K-113 · `bench.py` skill-io 1:1 na XTX, 5060 Ti i 3090 (ta sama konfiguracja) — pierwsza tabela między firmami z jednego harnessu
- data: 2026-11-17
- źródło: [[skill-io-skrypty]]; ich 3090 Qwen3.8-27B EXL3 3 bpw + MTP 96,2 proza / 141,1 kod (`README.md:33`); K-110 (część XTX)
- hipoteza: na 3090 nasz fork (UD-Q4_K_XL) da ~80 t/s prozy przy ich panelu; porównanie z ich 96,2 (3 bpw = mniej bajtów, inny silnik) pokaże, ile z różnicy to bajty, a ile silnik
- test: `bench.py run` z `config-existing-server.json` (T 0,6, c1 6 × 512, prefill 4k/16k, `--long` 65 536 z igłami), te same 3 serwery: topka (XTX), fork kvqlean (5060 Ti lokalnie, 3090 Vast); ≤ 10 min na kartę
- miara: c1 mediana, prefill, TTFT, retrieval k/3 + % sufitu karty
- zysk: porównywalne liczby dla Enigmy i publikacji; 0 t/s
- ryzyko karty: brak
- priorytet: średni
- **bieg 2026-11-25 17:09 nieważny:** serwer testowy nie wstał (`Connection refused`), bo w tym czasie plik modelu Qwen był skasowany (`~/models/orca`, pobrany ponownie 18:06). Ponownie w kolejce 2026-11-25 19:25.

- **wynik XTX 2026-11-25 21:35 (topka produkcji, port 18794):** skill-io bench.py: TTFT krótki 304,7 ms, dekod c1 145,4 t/s; długi 65 259 tok.: TTFT 83,2 s, prefill 784,8 t/s, dekod 118,7 t/s, igły 3/3. Część 5060 Ti / 3090 w paczce Vast nvq (2026-11-26).
- **2026-11-26 (Vast 5060 Ti nvq, [[2026-11-26-nvq-5060ti]]):** część 5060 Ti nieudana: serwer OOM przy starcie (ctx za duży z MTP na 16 GB); do powtórki z mniejszym ctx.
### K-014 · Graf CUDA na cały cykl draft + weryfikacja (ścieżka hosta 3,7 ms/krok = 14% na 3090)
- data: 2026-10-21 (Orca), 2026-11-09 (qwen-warp pkt 4)
- źródło: `R/69b-tensorfold-qwen-warp.md:75`, [[2026-11-09-qwen-warp-vs-fork-3090]], sesja Orca 2026-10-21 (archiwum, `O:1986-2003`); potwierdzenie kierunku: Baseten deepseek-ultrafast, krok spec-dec z weryfikacją 7 tokenów w jednym grafie ([[telegram-2026-11-14-silniki-agenci]])
- test: 5060 Ti lokalnie: spec_sweep T=1 + ms/krok z rozbiciem host/GPU, fork vs fork+graf; ≤ 10 min/ramię. Kod: tygodnie.
- zysk: +10–20% decode na 3090 [SZACUNEK]; część przewagi qwen-warp ×1,34–1,81
- ryzyko karty: brak
- priorytet: średni (duży, drogi w kodzie)
- zwiad 2026-11-15: 1Cat-vLLM `a013fb3dc` — próbkowanie T>0 bez synchronizacji hosta przez warunkowy graf CUDA (B=1..4) + fuzja top-K, kolejny wzór ([[zwiad-2026-11-14]])

- **2026-11-26:** pierwszy krok: ślad nsys jednego kroku n4 na 3090 (ok. 30 min, ok. 0,2 $) w następnej fali Vast; kod (tygodnie) tylko gdy przerwa hosta > 2 ms/krok.
### K-015 · Regresja `kvq` na sm_120 przy krótkim kontekście (−4,4% na 5080, −4,7% na 3090) i przegląd `GGML_CUDA_KVQ_BPSM` 1/2/3/4/6
- data: 2026-11-07
- źródło: `R/67-nvidia-vast-kampania.md` §5, `R/67c-nvidia-backlog-testow.md:107` (B13)
- test: 5060 Ti lokalnie: `test-backend-ops perf -o FLASH_ATTN_EXT` hs256 q4_0 przy 32k/98k/196k dla każdego BPSM, potem spec_sweep KVQ 0/1; ≤ 10 min
- zysk: odzysk +4…5% przy krótkim kontekście przy zachowaniu +9,5% decode przy 64k
- ryzyko karty: brak (16 GB: uważać na OOM przy dużym kontekście)
- priorytet: średni (lokalnie, tanio)

- **2026-11-25 (L4):** mikrobench kvq: KVQ1 vs KVQ0 nb2 191,5 → 37,7 µs, nb5 249,8 → 59,3, nb8 253,3 → 80,1 (kvq dużo szybsze na sm_89); BPSM 1/2 bez zmian, 3/4 gorzej (nb5 78,4 / 75,2). Regresja z wpisu dotyczy sm_120 (5080, 5060 Ti): wymaga wynajmu.
- **wynik 2026-11-26 (Vast 5060 Ti nvq, [[2026-11-26-nvq-5060ti]]):** mikrokernel kvq 3–6× szybszy od zwykłego FA przy nb 2–16 (8192 nb5 284,7 → 48,5 µs); BPSM 1/3/4/6 gorsze od domyślnego. End-to-end KVQ0 vs KVQ1 (n2): T=0 +1,6%, kopia +12,2% (194,6 vs 173,5), T=1 −1,8%: regresja jest w ścieżce szerokiej weryfikacji, nie w kernelu. Następny krok: nsys kopii.
### K-030 · Enigma 12/16 GB: porównanie jakości kandydatów (AP-Q3_K_XL vs UD-Q3_K_XL na 16 GB, IQ3_XXS-mtp Swift W3 / ISTA na 12 GB) zestawem jakość-mini + KLD
- data: 2026-10-18 (16e), zgoda na porównanie 2026-11-09
- status: **czeka na decyzję** (źródła danych i pobrania modeli do potwierdzenia, [[2026-11-09-decyzje-runda-69]])
- źródło: [[testy/2026-10-18-e1-kwanty-27b-kld]], `R/67b-wybor-modeli-nvidia.md`, [[jakosc-mini]]
- test: 5060 Ti: `~/qwen-opt/jakosc-mini/run.py gen` + KLD na każdym kandydacie (> 10 min, podzielić po zbiorze)
- zysk: wybór modeli katalogu (AP vs U3: KLD czat −12%, kod −23% przy tych samych bajtach)
- ryzyko karty: brak
- priorytet: średni (produkt)

- **2026-11-26 ocena:** KLD A3 vs U3 już jest (16e); brakuje ISTA IQ3_XXS-mtp i W3 na 5 korpusach (A40 ok. 1 h, ok. 0,6 $, pobranie BF16 54 GB na wynajętej maszynie) i jakości-mini (ok. 4 h na 3090, ok. 1,1 $). Wymaga budżetu.
- **2026-11-26 wyjaśnienie dla JARO:** to nie test prędkości, tylko wybór pliku modelu, który Enigma poleca dla kart 12/16 GB (który kwant najmniej odbiega od pełnego modelu, KLD + krótki test jakości). Porównanie A3 vs U3 już jest (16e: A3 lepszy, KLD czat −12%, kod −23%); brakuje tylko ISTA IQ3_XXS-mtp i W3. Rekomendacja: odłożyć, dopóki Enigma nie oferuje tych plików.
### K-037 · Megakernel / rezydentna pętla MTP (PoC-A w trwałej siatce 96–192 WG)
- data: 2026-10-16 (15a), 2026-11-07 (66c)
- źródło: [[budzet-megakernela-qwen-xtx]], [[lekcja-megakernel-prefetch-nie-granica]], `R/66c-hyperkernel-megakernele.md` §7
- test: XTX mikrobench PoC-A (kill > 0,3 µs albo < 30% zysku „bez granicy”); ≤ 10 min, kod 1–1,5 dnia
- zysk: krótki ctx +4…9,5%, 199k +2…4%, za 40–70 osobodni [SZACUNEK]
- ryzyko karty: **wysokie**: ewikcja kolejki KFD przy kernelu rezydentnym → możliwy reset
- priorytet: niski (koszt i ryzyko; wspólny PoC z K-021)

- **2026-11-25:** pierwszy krok wspólny z K-021: mikrobench przekazania PoC-A `~/qwen-opt/klab/handoff/handoff.hip` (w przygotowaniu).
- **2026-11-26 różnice wobec K-021:** K-021 mierzył już siatkę 96 WG (licznik globalny H1, sztafeta ×16 H16, s_sleep 1); 192 WG nie jest współrezydentne (3 WG/WGP × 48 = 144). Dobudowane warianty K-037 w `~/qwen-opt/k037/handoff37.hip`: flagi per WG (HW, bez atomowego RMW), s_sleep 0/1/2/4, siatki 48/96/144. W kolejce `k037.jobs` (PM4=0, ok. 6 min karty).
### K-056 · Rebase łatek topki na nowszy upstream (baza b11528 → llama.cpp v1.0.0 = b12359)
- data: 2026-10-16, ostatnio 2026-11-07
- źródło: [[2026-10-16-rebase-v070]], `R/68d-swieze-od-spolecznosci.md:14,18` (#31247 przesunie md5)
- nowe (2026-11-14): v1.0.0 zawiera już u nas portowane #30137, a do tego #30541 (kopia stanu dla skwantowanego KV, K-001), #31533 (few-row MMQ CUDA, K-013/K-103), #31927 (MTP czyta stan celu z bufora na urządzeniu), #32078 (tylko fuzowany GDN), #32009/#32089 (ponowne użycie schedulera), #31838 (ROCm: stały workspace BLAS); API: `defrag_thold` usunięte, NextN w `llama.h`
- test: build (CPU), XTX greedy md5 vs baza, `test-backend-ops`, spec_sweep A/B ≤ 10 min/ramię; zmiana md5 przez #31247 → bramka KLD
- zysk: poprawki upstream; prędkość ~0 (68d: „prawie wszystko topka ma mocniej”)
- ryzyko karty: nowe kernele w PM4
- priorytet: niski (mało zysku)

- **ocena 2026-11-25:** cel `upstream-master` 6792507b7 (11-21): fork 110 plików (+21,5k/−1,2k); 3-way: 62 pliki czysto, 48 plików z 142 konfliktami (`~/qwen-opt/specprep/k056-conflicts.txt`); 2–4 dni + build + pełna bramka.
- **2026-11-26 w toku:** `~/wt/k056-rebase` (WIP 68b781b8a, 46fc73f14): 49 plików z konfliktami (139 kawałków), rozwiązane 32, zostało 17 (100 kawałków; `.k056/unresolved.txt`). Upstream zmienił sumę q8_1 (md5 się przesunie → bramka KLD), parser czatu (SAFE_TOOLS/SPECIAL do portu), cache promptu w `server-slot-sched.*`. Zostało 1,5–2,5 dnia agenta + build + bramka ok. 60 min karty.
### K-060 · Pilot fabryki RSI-F: P0 (`./factory verify claims/2026-10-17-mmq-epi-0070.json`) i P1 (playbook 0070 na nowe cele)
- data: 2026-10-19 (21h)
- status: **czeka na decyzję**
- źródło: [[KOLEJKA-TESTOW]], [[petla-rsi-f]], [[otwarte-decyzje-techniczne]] (`:21`)
- test: XTX `GGML_HIP_PM4=0`, P0 ~20 min → 2 joby, P1 4 × 15–20 min
- zysk: walidacja fabryki, 0 t/s
- ryzyko karty: brak
- priorytet: niski (proces)
- 2026-11-24 14:37: pierwsze uruchomienie odrzucone przez fabrykę (port 18794 poza zakresem fabryki 18434–18499; skrypt poprawiony na 18450, uruchomione ponownie).
- 2026-11-24 15:18: fabryka INVALID, bo zmieniona uprząż (`ext/spec_sweep.py` po audycie 19.11, `ext/fusion/greedy.sh`) bez wpisu w HARNESS.lock; zablokowana z powodem (ledger seq 11), test ponownie w kolejce 15:40.
- 2026-11-24 16:08: fabryka VOID przez bramkę sprzętu H4: niepotwierdzony page fault z 2026-11-23 01:09 (proces strata-inkling, znany incydent K-134). Potwierdzenie (`factory rsi hw ack --reason …`) to według fabryki krok człowieka: **czeka na JARO**, potem jedno uruchomienie `K-060.jobs` (ok. 25 min).

- **2026-11-26:** części CPU przechodzą (card check, harness seq 11, ledger 14 wierszy). P0 potrzebuje kroku człowieka: JARO uruchamia `cd ~/qwen-opt/factory && ./factory rsi hw ack --reason "K-134"`, potem `kq/K-060.jobs` (ok. 25 min karty).
- **2026-11-26:** `factory rsi hw ack` wykonany przez Kernela na polecenie JARO („ty pusc”), ledger seq 14, nowych błędów 0; `kq/K-060.jobs` w kolejce.
- **2026-11-26 bieg nieważny:** oba przebiegi P0 przekroczyły limit 880 s (rc 124) przy temperaturze 38–39 °C, czyli karta głównie stała (najpewniej skan H4 fabryki + start); do skrócenia przed powtórką.
- **2026-11-26 przyczyna rc 124 i poprawka:** bramka H1 czekała do 15 min na `gpu-guard.sh`, który nie działał. Do tego kolejka trzyma `gpu.lock` i `quiet.lock` przez cały plik jobów, więc `flock` bloku fabryki zakleszczyłby się. Teraz `kq/K-060.sh` uruchamia strażnika i przepuszcza locki przez nakładkę `kq/k060-bin/flock` (tylko gdy kolejka trzyma je na fd 8/9). Watermark H4 przesunięto (ack, ledger seq 15, 0 nowych faultów), bo zalew `init_user_pages` w journalu jądra (11:29–11:43) wydłużał skan H4 do 60 s na blok.
- **2026-11-26 P0 na k183e:** nowa karta `claims/2026-11-26-mmq-epi-0070-k183e.json` (ledger seq 17). Obie gałęzie używają tych samych binarek k183e, różni je tylko `GGML_HIP_MMQ_EPI` 0/1. Narzędzia są w `~/k060/k183e-inst`: llama-bench i test-backend-ops z `~/wt/k183e/build-hip`, libggml-hip identyczny z produkcją. Baza diffu to `a012922be` (e3ab5b9e3 + revert 0070). Dry-run G0 jest czysty poza ostrzeżeniami R29, więc najlepszy możliwy werdykt to NEEDS-HUMAN. Job: 1 runda ABBA, 8 bloków, 13 min karty. Przy 1 rundzie (2 pary) CI będzie szerokie, więc werdykt NULL jest bardzo prawdopodobny. P1 (playbook 0070 na `t-iq4xs-mmq` i `t-q6k-mmq`) wymaga najpierw CONFIRMED P0 i implementacji przez świeżych agentów, więc nie dziś.
- **2026-11-26 12:47 bieg nieważny (rc 124):** nakładka flock się nie włączyła. Kolejka uruchamia job z zamkniętymi fd 8/9, a locki trzyma sam proces `run-jobs.sh`, więc test fd zwrócił 0 i pierwszy blok czekał na `gpu.lock` przez 750 s. Poprawka: skrypt szuka przodka `queue/run-jobs.sh` i sprawdza `flock -n` na obu plikach; wyjście fabryki jest teraz niebuforowane, ze znacznikami czasu. Plik jobów ma dwa niezależne pełne verify (fabryka nie wznawia przebiegu między jobami).
### K-066 · Pipeline kafli MMQ w stylu DeepGEMM / strojenie configu MMQ IQ4_XS (`mmq-config-ampere.cuh`) pod prefill CUDA
- data: 2026-10-16 (15d), 2026-10-21 (Orca)
- źródło: `R/67c-nvidia-backlog-testow.md:133` (C16), sesja Orca (`O:1788-1796`, `O:2187-2196`: occupancy 2 → −11,5%)
- test: przebudowy compile-time + `llama-bench -p 512,4096` + md5/PPL; 5060 Ti lokalnie, 3090 wynajem
- zysk: pp +3…12% (DeepGEMM), +10–20% (config IQ4_XS) [SZACUNEK]
- ryzyko karty: brak
- priorytet: niski (dużo pracy)

- **2026-11-26:** w paczce Vast `nvq2` (3090, 35–45 min): sweep configu MMQ IQ4_XS (nthreads 128/512, K_vram 512, stream_k off, I 64), test-backend-ops + llama-bench pp512/pp4096 + PPL; IQ4_XS to 29,5% wag UD-Q4_K_XL, więc +15% kernela ≈ +4% prefillu.
- **wynik 2026-11-26 (Vast 3090 nvq2, [[2026-11-26-nvq2-3090-k071-k066]]):** `nthreads 128` prefill +11,5% (pp4096 ub512 1441 → 1604), testy 49/49, **PPL niezmierzony**; `K_vram 512` +11% ale PPL 1160 (zepsute, testy przechodziły); stream_k off −1,6%; I 64 i nthreads 512 bez pomiaru. Następny krok: PPL/KLD nthreads 128 (5 min).
### K-067 · Kernel GDN chunked MMA w CUDA zintegrowany z cache i snapshotami (gałąź `orca-gdn2`)
- data: 2026-10-21 (Orca)
- źródło: sesja Orca (`O:1449-1462`: +10,5% pp2048, ale PPL nan; po poprawce 0%; `O:1791`)
- test: PPL + md5 + pp2048, 3090 (wynajem), 2–3 h → podzielić
- zysk: do +10% prefillu
- ryzyko karty: brak
- priorytet: niski (numeryka do naprawy)

- **2026-11-26:** NaN naprawiony 2026-10-21 (`729b77311`); PPL 130k w drugiej próbie: kernel MMA czyta niezapisany bufor pominiętego GET_ROWS i zapisuje stan poza slotem cache; plan naprawy 3 kroki (2–3 h kodu), potem Colab L4 + 3090; wynik nie będzie bitowy (bramka KLD, decyzja K-007 pozwala).
### K-070 · NVIDIA: soak termiczny 600 s przy fill 262k (E3) i sweep limitu mocy → perf/W na wynajętych kartach (E1)
- data: 2026-11-07
- status: E1 **czeka na decyzję** (zmienia limit mocy; czy zasada „karta fabrycznie” obejmuje karty z wynajmu); E3 otwarte
- źródło: `R/67c-nvidia-backlog-testow.md:152,154`
- test: E3 `stab soak_s=600` (10 min); E1 4 ramiona × ~3 min (`nvidia-smi -pl` 100/85/70/55% TDP), tylko wynajem
- zysk: dane do „cichego trybu” Enigmy; 0 t/s
- ryzyko karty: E1 zmiana mocy; E3 temperatury
- priorytet: niski (produkt)

- **wynik E3 2026-11-26 (Vast 3090 nvq, [[2026-11-26-nvq-3090]]):** fill 262k 531,4 s, soak 600 s 65,4 → 69,4 t/s (+0,7% dryf), maks. 75 °C, SM min. 1515 MHz, moc śr. 328 W: bez dławienia. E1 (sweep limitu mocy) poza zakresem (karta fabrycznie).
### K-071 · qwen-warp: DFlash2 ≤ 64k na replayu agentowym (W2)
- data: 2026-11-09
- status: **czeka na decyzję** (3,85 GB pobrania na wynajmie)
- źródło: `R/69-SYNTEZA.md:29` (W2), `R/69b-tensorfold-qwen-warp.md:65`
- test: 3090 (wynajem), ten sam replay co spec_sweep, oba drafty, ~10 min/ramię
- zysk: czat ×1,07–1,34, agent z kopiowaniem −31% (dane autora); u nas −10…+10% [INFERENCE]
- ryzyko karty: brak
- priorytet: niski (agent traci)

- **2026-11-26:** w paczce Vast `nvq2` (3090, ok. 35 min): fork MTP n2 vs qwen-warp 689901c (mtp / dflash2 ABBA), tylko publiczne prompty (spec_sweep, kopie, kopia 52k z korpusu Enigmy); prywatne sesje omp nie wychodzą poza nasze maszyny.
- **wynik 2026-11-26 (Vast 3090 nvq2):** fork MTP n2 czat 90,2 / kopia 101,9 / kopia 64k 77,0; qwen-warp MTP (Swift INT4) czat 117,9 (+31%), kopia 64k 137,1 (+78%); DFlash2 nie wystartował (drafter bf16 bez `weight_packed`). Do powtórki z poprawnym formatem draftera.
- **2026-11-26 uwaga JARO („ta sama jakość, po prostu szybciej”):** pliki: warp Swift-1.5 INT4 (W4A16) 19,47 GB, nasz UD-Q4_K_XL 17,66 GB, więc warp czyta więcej bajtów, a nie mniej; przewaga nie wynika z niższego kwantu. Ale to inny model (Swift = Qwen3.8 dostrojony na krótsze myślenie) i jakość obu plików nie była porównana. Do następnej fali: KLD obu wobec BF16 na tych samych promptach (wymuszanie tokenów) i nasz fork na Swift GGUF o podobnym rozmiarze, żeby porównać ten sam model przy tej samej jakości.
### K-072 · Nemotron 3.5 Bolt na NVIDIA: KLD fuzji `GGML_CUDA_TOPK_MOE_NP2`, `MMVQ_N1_IQ2`, kernel IQ2_XXS MMVQ, replay stanu Mamby
- data: 2026-10-16 (raport 14 §10)
- status: **czeka na decyzję** (model odłożony „na później”)
- źródło: `R/14-nemotron-3090.md`, `R/67c-nvidia-backlog-testow.md:114` (B20), `STAN-PRAC.md` („Odłożone”)
- test: 3090/4090 (wynajem), KLD vs upstream (~$0,3) + A/B per łatka ≤ 10 min
- zysk: 87,2 → 141,1 t/s już zmierzone; KLD warunkuje publikację; łatki razem +6,1%
- ryzyko karty: brak
- priorytet: niski (model poza katalogiem)

- **2026-11-26:** pytanie do JARO: czy Nemotron 3.5 Bolt wraca do katalogu i czy zgoda na KLD vs upstream (ok. 0,3 $, model pobierany na wynajętej karcie).
### K-131 · Fork CUDA na Ampere: MMVQ celu tylko 58% pasma na 3090 (4080 SUPER 78%) — strumieniowanie wag przez `cp.async`
- data: 2026-11-20
- źródło: [[2026-11-19-k118-nvidia-pelna-moc]] (plain 3090 19,2 ms = 540 GB/s z 936; 3060 60%; 4080S 78%); TensorFold v1.3.0 #2266: rura `cp.async` per warp w dekodzie ekspertów NVFP4 +24% na sm_120, bity te same
- test: CPU: `ncu` niedostępne bez karty, więc najpierw przegląd kodu MMVQ IQ3_XXS/IQ4_XS forka (szerokość ładowań, wypełnienie SM); potem Vast 3090 (reaper, ≤ 10 min): `llama-bench -p 0 -n 128` i `test-backend-ops MUL_MAT` n=1, wariant z `cp.async`/ładowaniami 128-bit vs fork, md5 T=0
- zysk: do +30% dekodu plain na 3090 [INFERENCE: 58 → 75% pasma], spekulacja proporcjonalnie (weryfikacja to ten sam kernel, łączy się z K-013)
- ryzyko karty: brak (wynajem)
- priorytet: średni

- **wynik 2026-11-26 (Vast 3090 nvq, [[2026-11-26-nvq-3090]]):** UD-Q4_K_XL plain tg: domyślne 44,97 t/s = 793,6 GB/s (85% pasma), rows1 477,6, rows4 770,0, L2PF bez zmiany. 58% z wpisu dotyczył IQ3_XXS; dla jednego wiersza zapas jest mały, luka jest w weryfikacji (K-182).
### K-132 · Jądro Linux 7.0/7.2 vs 6.8 na jaroserverai (start, cache promptów w RAM) i odciążanie MoE z `mmap` na CPU
- data: 2026-11-20
- źródło: [[telegram-2026-11-20-linux-7-2-pamiec]]
- test: (1) CPU teraz, bez karty: model MoE z odciążeniem z `mmap` przy ograniczonym RAM (cgroup), refault i t/s, jądro 7.0 (serwer Jarva) — pomiar bazowy; (2) jaroserverai za zgodą właściciela: boot 7.x obok 6.8, start do /health, TTFT po restore z `--cache-ram` przy presji RAM, dekod 1,7k (kontrola), PM4 i amdgpu bez błędów
- zysk: start i przywracanie cache promptów; porady dla Enigmy przy odciążaniu; dekod XTX bez zmian [INFERENCE]
- ryzyko karty: zmiana jądra pod ROCm 10.0 i PM4, tylko za zgodą właściciela
- priorytet: niski
- **wynik 2026-11-26 część (1), Jarva (jądro 7.0.0-43, 2 vCPU i5-7500T, CPU-only, `nice -n 15`, `-t 2`):** model MoE z dysku nie mieścił się w limicie łącza (Inkling 16,5 GB przez łącze ~0,3 MB/s), więc pobrany granite-3.1-1b-a400m-instruct Q8_0 (1,42 GB, MoE). `llama-bench -lm mmap -p 64 -n 32 -r 3` w `systemd-run --user --scope -p MemoryMax=… -p MemorySwapMax=0`, cache pliku zrzucony przez `posix_fadvise(DONTNEED)` (bez roota); skrypt `qwen-opt/k132/k132-moe.sh`. Mediany: bez limitu pp 93,8 / tg 40,5 t/s, refault 248; **1 GiB: 21,3 / 4,19 t/s, refault 1,49 mln stron (≈ 5,7 GB odczytu)**; 768 MiB: 15,5 / 1,96, refault 3,83 mln; 512 MiB: 14,8 / 0,61, refault 11,4 mln. Dekod spada ~10× już przy limicie 70% rozmiaru modelu: przy odciążaniu MoE z `mmap` cały plik ekspertów musi się mieścić w page cache.
- przygotowane 2026-11-26 (2): `qwen-opt/k132/k132-68.jobs` (6.8.0-138, teraz) i `k132-70.jobs` (po jednorazowym restarcie do 7.0.0-44 przez `grub-reboot`, wymaga sudo właściciela): start produkcyjnego Qwen do /health (2× ciepły, 2× zimny cache plików), restore z `--cache-ram` bez presji i z presją RAM (hog zostawia 6 GiB), dekod 1,7k T=0 (t/s + md5), błędy amdgpu/OOM w logu jądra, Inkling `-ncmoe 99 -lm mmap` bez limitu i w cgroup 8 GiB, granite CPU-only jak na Jarvie. Podsumowanie: `bash ~/qwen-opt/k132/k132-sum.sh`.

## W toku

(pusto)

## Zrobione

### K-047 · GDN w weryfikacji: forma chunkwise/WY w fp32 albo fuzja conv + rekurencja + gated RMSNorm ze stanem w VGPR
- data: 2026-11-05 (63 #21)
- status: **czeka na decyzję** (inna kolejność redukcji fp32 → bramka KLD, nie md5)
- źródło: `R/68b-spekulacja-nowe.md:162`, `R/68-SYNTEZA.md:20`; ta sama fuzja (conv1d + SiLU + norma Q/K + rekurencja) w kernelu weryfikacji KDA u TokenSpeed ([[tokenspeed]], 2026-11-14)
- test: XTX `test-backend-ops perf -o GATED_DELTA_NET` (n 5/8/16), spec_sweep ABBA, KLD + md5 plain; ≤ 10 min/krok
- zysk: +1,1…1,7% na każdym kontekście [SZACUNEK]; tańszy wiersz dla drzew (K-075)
- ryzyko karty: brak
- priorytet: niski (poniżej progu)

- **2026-11-25 ocena:** GDN w produkcji 14,7 µs/uruchomienie (0,715 ms/krok) przy podłodze bajtów 7,86 µs, więc sufit zysku ok. 0,33 ms/krok (≈ 1,1% przy n=5, realnie 0,5%); WY w fp32 3–5 dni i niebitowo (decyzja KLD). Pomiar bazy w kolejce (`k047.jobs`): zabić, gdy (base − floor) × 48 < 0,15 ms.
- **wynik bazy 2026-11-26 (gdnbench):** n=5 koszt ponad podłogę 10,1–10,3 µs/uruchomienie = **0,48–0,50 ms/krok** (n=8: 0,63–0,77, n=16: 1,16–1,40). Powyżej progu 0,25 ms z planu → wariant WY ma sens (3–5 dni, bramka KLD jest już zgodą K-007).
- **K-047b 2026-11-26 13:10–13:17 (XTX, `~/wt/k047` 24aa8b3a3 = k183e + osobny kernel weryfikacji GDN `GGML_HIP_K047=1`: q/k ładowane i normowane raz na CTA przez LDS):** test-backend-ops 67/67 PASS, dowód ISA na emulatorze 72/72 identyczne, kernel LAG n=5 9,54 → 9,40 µs, n=16 10,55 → 10,36 µs (−1,5…−1,8%). **Wall ABBA ×2: +0,3…+0,4% we wszystkich 8 kategoriach (n=4/4), md5 T=0 identyczne → PASS.** Zysk mały, ale stały; wejdzie w następny łączny build silnika Qwena. Pełna fuzja conv + rekurencja + RMSNorm i postać WY zostają (3–5 dni).
- przeniesione 2026-11-26: PASS, czeka na łączny build

- **K-132 ramię 6.8 2026-11-26 12:33–12:47 (jaroserverai 6.8.0-138, produkcja k183e):** start Qwen do `/health`: zimny page cache **45,2–45,4 s**, ciepły **6,0 s**; przywrócenie cache promptu z RAM 97–99 ms (8k słów, bez i z presją pamięci, swap 0); amdgpu/OOM 0. Inkling `-ncmoe 99 -lm mmap`: bez limitu pp 516 / tg 9,94 t/s, cgroup 8 GiB pp 79 / tg 4,02 (refault 3,1 mln stron). granite CPU: bez limitu tg 78,8, 1 GiB 9,2, 768 MiB 3,1, 512 MiB 0,7 t/s (Jarva 7.0, 2 vCPU: 40,5 / 4,2 / 2,0 / 0,6). Ramię 7.0 czeka na restart JARO: `sudo grub-reboot 'Advanced options for Ubuntu>Ubuntu, with Linux 7.0.0-44-generic' && sudo reboot`, potem `~/qwen-opt/k132/k132-70.jobs`. Wniosek już teraz: zimny start 45 s to odczyt 16 GB z dysku; restart :8080 po zrzuceniu page cache kosztuje 39 s więcej niż ciepły.
### K-159 · Nib na tym samym modelu co Maya (uncensored): AtomicChat w paczce NVFP4 albo AD-Q4_K w Nib
- data: 2026-11-25 (Nib liczy na NVFP4-Mixed, nie na naszych wagach uncensored)
- plan: wtopić LoRA AtomicChat (43 MB) w paczkę Nib albo dodać Q4_K do loadera Nib; wall.py T=0 / T=0,7, KV q4_0, Quest wyłączony do 14k
- priorytet: średni

- **2026-11-25:** droga LoRA zrobiona (K-165). Uruchomienie wag Mai (AD-Q4_K) w Nibie: Nib nie ma ścieżki Q4_K (GEMV, MoE, dekod, weryfikacja, prefill WMMA), szacunek 1–2 tygodnie. Czeka na decyzję JARO.
- **2026-11-26:** plik Mai: gęste Q8_0 (Nib obsługuje), eksperci gate_up Q4_K (8,54 GiB) i down **Q5_0** (5,22 GiB); szacunek zmniejszony do 5–8 dni; pierwszy commit: loader + test parytetu dekwantyzacji na CPU.
- **K-159 2026-11-26 12:00–12:17 (XTX, ten sam dzień, wallacc.py: 4 prompty wall + 3 polskie, 3× każdy, mediany):**
  | ramię | odmowy | T=0 median4 / PL | T=0,7 median4 / PL | akceptacja kod / pl (tok./rundę u Niba) |
  |---|---|---|---|---|
  | **Maya produkcja (k185)** | 0/5 | **149,4 / 110,4** | **113,2 / 112,9** | 0,78 / 0,33 (przyjęte/oferowane) |
  | Nib 0.1.2 + łata WE2 proj | 0/5 | 100,8 / 79,6 | 94,5 / 73,1 | 1,50 / 1,10 |
  | Nib 0.1.2 bez łaty (z cenzurą) | 5/5 | 169,1 / 86,3 | 150,6 / 76,9 | 4,05 / 1,18 |
  **Werdykt: Maya zostaje.** (1) Łata WE2 przeniesiona na 0.1.2 (`nib-we2-012` d1b4eda) zdejmuje odmowy, ale psuje drafter MTP: kod 4,05 → 1,50 tok./rundę, wall 169 → 101; na starym `nib-we2` było 165,2 (szablon WE2), więc to regresja przeniesienia (podejrzenie: łata nie trafia w wejście głowicy MTP albo w tok_embd używany przez drafter na 0.1.2) — do naprawy, jeśli Nib wróci. (2) Polski u Niba jest wolny przez drafter: nawet bez łaty pl 1,1–1,2 tok./rundę vs kod 4,05; lekarstwem byłby drafter trenowany na polskim, nie wagi. Maya ma polski 110–113 t/s przy obu temperaturach.
- przeniesione 2026-11-26: Maya wygrywa; Nib + WE2 zostaje demonstracją

### K-006 · Wpis „wspólny początek” (Maya #607) i chude checkpointy (stan GDN tylko na granicach wiadomości) zamiast kopii całej sesji w cache
- data: 2026-11-05
- źródło: [[wspolny-poczatek-promptu]], `R/63-SYNTEZA.md:85-86` (plan #6, #7), `R/63b-colibri-maya-delta.md` §6, `R/68c-dlugi-kontekst-gdn.md:143`
- test: najpierw implementacja. XTX: `switch.py` z cachesave (2 przeplatane wątki 75–120k, 14 tur ≈ 3 min), mediana tury, `prompt_n`, md5 = zimny start; ≤ 10 min/ramię.
- zysk: start sesji po wyrzuceniu z cache 4,4 s → 0,3–0,5 s, przy 100k+ ~5–7 s → 0,3–0,5 s [SZACUNEK]; wpis 118k 14,2 GB → ~3–4 GB, czyli 3–4 długie wątki w cache zamiast 1
- ryzyko karty: brak (RAM hosta; `HSA_USE_SVM=0` już jest)
- priorytet: wysoki (≥ 1 s/turę agenta)

- **wynik 2026-11-25 20:54–21:19 (XTX, `~/wt/k006` k006-thin, ABBA A=prod / C=THIN=4+PREFIX=2):** zapis wpisu cache mediana 5291 → **3404 MiB (−36%)**, maks. 8331 → 4049 MiB (−51%), checkpointy 12 → 5; tura agenta bez zmian (12,5 vs 12,3–12,6 s). Nowa sesja z tym samym system promptem: 1221 → 913–1341 ms; po wyrzuceniu slotu wpis „wspólny początek” daje **8543 → 860 ms (−90%)**. md5: 7 z 30 różnych, ale także między ramionami bez zmian (suite: A2 a0dde0fa vs EA/EB f3e9f53e), więc harness nie jest deterministyczny między serwerami; bezstratności nie da się tu orzec md5. Werdykt: duży zysk pamięci i TTFT, wdrożenie wymaga bramki KLD/wymuszania tokenów (decyzja K-007).
- **2026-11-26 bramka K-007: PASS** (KLD 0 na ścieżce przywracania z wpisu „wspólny początek”). Do wdrożenia razem z K-001 po bramce prędkości.
- **K-006g 2026-11-26 11:37–11:42 (XTX, silnik k183e e3ab5b9e3 = k183c + K-006, `LLAMA_SERVER_CACHE_THIN=4 PREFIX=2`, ABBA 2 pary):** GATE PASS: wall −0,1…+0,2%, md5 T=0 i T=0,7 identyczne. **Restart sesji po wyrzuceniu z cache: 8447–8584 ms → 755–848 ms (−90%)**, prompt_n 7309 → 31; zapis wpisu prefiksu 352 MiB w 71 ms. Odpowiedzi z wpisu prefiksu różnią się md5 od zimnego startu (4/10), co pokrywa bramka KLD K-007 (PASS). **Wdrożone na :8080 2026-11-26 11:43** (`~/llama-topka-k183e`, smoke: exe i biblioteki z nowego katalogu, md5 = produkcja, env THIN/PREFIX widoczne w procesie).
- przeniesione 2026-11-26: w produkcji

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

- **2026-11-25:** `~/wt/k001-fix` (qprep-spec + r3 556ad799f + r4 a557fc3c5 z gałęzi duo, testy masked-tail 5/16/17); w kolejce `k001.jobs`: bramka tbo kvq wył./wł. × wariant 0/83, test wycieku restore (rozszerzenia 1/31/32/33/63/64 tok.), llama-bench ABBA przy wariancie 83 (koszt prefillu dotąd mierzony tylko przy 0: −0,65%).
- **wynik 2026-11-26 00:23–00:28 (`~/wt/k001-fix`):** produkcja: **3 wycieki stanu na 12 sprawdzeń** (LEAK-PREFILL po post33 i u63, LEAK-DECODE po post32), poprawka: **0 na 12**; koszt: wariant 83 pp512 −0,25%, pp2048 −0,45%, tg64 +0,1%; wariant 0 pp2048 −0,6%. To błąd poprawności w produkcji (inne odpowiedzi po przywróceniu sesji) → bramka wdrożenia K-183 w kolejce.
- **K-183 2026-11-26 02:26–02:30 (wall.py, `~/wt/k001-fix` vs produkcja):** **GATE FAIL**: wszystkie kategorie −5…−12% (pl T=0 80,2 → 70,5), md5 inne. Poprawka wycieku w ścieżce dekodu kvq (r4) jest za droga przy weryfikacji spekulacji; potrzebna tańsza wersja (maska tylko dla kafli z zamaskowanymi komórkami, plan 3–5 h z wpisu). Produkcja dalej ma wyciek po przywróceniu sesji.
- **K-183c 2026-11-26 06:47–06:58 (łączny silnik k183c 6c1449f91 = K-012 + K-001c):** GATE PASS: wall −0,1…+0,2%, md5 T=0 i T=0,7 identyczne we wszystkich 4 promptach i przebiegach, wycieki 0/12, FRESH-MD5 identyczne, 94k dekod 121,16 → 123,73 t/s (+2,1%). **Wdrożone na :8080** (`topki/xtx/qwen-uncensored.sh` → `~/llama-topka-k183c`, `GGML_HIP_K012=1`; kopia skryptu `.pre-k183c`); smoke: exe i biblioteki z nowego katalogu, linia K012 w logu, md5 = produkcja.
- przeniesione 2026-11-26: w produkcji

### K-001c · Tańsza poprawka wycieku stanu K-001 (po K-183 FAIL −5…−12%)
- Plan: maska tylko dla przywróconych slotów / kafli z zamaskowanymi komórkami; bramka jak K-183 (12× wyciek + wall.py vs produkcja). Przygotowuje agent K001Cheap.

- **wynik 2026-11-26 06:09–06:40 (XTX, `~/wt/k001-cheap`, bez zmian w ggml):** wyciek prod 3/12 → cheap **0/12**, FRESH-MD5 identyczne, md5 T=0 4/4 identyczne. Wall 4 pary ABBA: +0,9…+2,0% we wszystkich kategoriach poza T=0,7 tech −3,0% (po 2 parach −6,2%: szum próbkowania, kernele te same). Formalnie FAIL bramki −2%; łączny build z K-012 idzie bramką K-183c z md5 T=0,7.
- **K-183c 2026-11-26 06:47–06:58 (łączny silnik k183c 6c1449f91 = K-012 + K-001c):** GATE PASS: wall −0,1…+0,2%, md5 T=0 i T=0,7 identyczne we wszystkich 4 promptach i przebiegach, wycieki 0/12, FRESH-MD5 identyczne, 94k dekod 121,16 → 123,73 t/s (+2,1%). **Wdrożone na :8080** (`topki/xtx/qwen-uncensored.sh` → `~/llama-topka-k183c`, `GGML_HIP_K012=1`; kopia skryptu `.pre-k183c`); smoke: exe i biblioteki z nowego katalogu, linia K012 w logu, md5 = produkcja.
- przeniesione 2026-11-26: w produkcji

### K-012 · `kvq` przy W=5 bliżej rooflinu: nowy układ (K dekwantowane raz, głębszy prefetch K/V), cel ~172–300 µs/warstwę przy 98–196k
- data: 2026-11-07
- źródło: [[2026-11-08-kvq-once-profil]] (`:86`: ONCE=1/2 KILL, „potrzebny inny układ”; FA = 30% kroku przy 199k, 11,32 ms), `R/68c-dlugi-kontekst-gdn.md:142`, `R/70-fa-d256-jak-to-zrobilismy.md:188` (#5)
- test: XTX `kvq-once/job.sh` kperf (d98k/196k, nb1/nb5) + `fa_hash` ≤ 10 min; potem xtxbench 199k osobnym jobem
- zysk: sufit +12…16% decode przy 196–255k; realnie +1,5…3% przy ≥ 94k [SZACUNEK]
- ryzyko karty: nowy kernel w taśmie PM4 (bramka `test-backend-ops` przed serwerem)
- priorytet: średni (duży sufit, dwa nieudane podejścia)
- zwiad 2026-11-14: hipfire #989 (WMMA split-K verify attention, gfx1100, numeryczne) zszedł do 309,5 µs przy 100k i 4 wierszach, czyli tyle co nasz `kvq` przy nb5 i 98k (~319 µs); bitowa droga musi zejść niżej ([[zwiad-2026-11-14]])

- **2026-11-25 ocena:** cel 172 µs/warstwę przy 98k nieosiągalny bezstratnie (podłoga pamięci 118, MMA 119, K/V dekwantowane raz ok. 152, dziś 319). Układ „pair-split” ok. −10% kernela = +2,5% dekodu przy 199k (poniżej progu 3–5%), 3–4 dni. Sonda w kolejce (`k012.jobs`, `GGML_HIP_KVQ_PROBE`): implementacja tylko przy ≤ −15% przy nb5/196k.
- **2026-11-26 bieg nieważny:** bramka sondy oblana (kontrola PROBE=7 nb=1 zmieniła hash, choć nie powinna) — błąd w łatce sondy, nie wynik.
- **wynik sondy 2026-11-26 02:30–02:35:** 96k: nb1 175,9 µs/warstwę (644 GB/s), nb5 322,4 (351 GB/s); 192k: nb1 327,9, nb5 620,8. Szacunek „K/V dekwantowane raz” nb5: **−18,7% (96k) i −19,2% (192k)**, powyżej progu −15% → **GO** dla nowego układu (3–4 dni).
- **K-012b 2026-11-26 06:20–06:50 (XTX, gałąź k012-layout 0e8935d97, `GGML_HIP_K012=1|2`, pary fal dzielą K po półbajtach i V po połowie głowy):** test-backend-ops i fa_hash bitowo identyczne z produkcją; kernel nb5: 32k −12,1%, **96k −14,5%, 192k −16,9%** (K2 −11,0/−13,8/−15,3%), nb1/nb8 bez zmian. Serwer T=0: 1,7k 118,1 vs 118,1 (−0,1%), **94k 114,6 → 116,9 t/s (+2,0%)**, 33,57 vs 34,22 ms/krok; md5 wszędzie SAME; wall T=0 117,2 → 117,2, T=0,7 120,5 → 120,3. **PASS** (bezstratne, zysk tylko przy długim kontekście). Wdrożenie razem z K-001c jako K-183c.
- **K-183c 2026-11-26 06:47–06:58 (łączny silnik k183c 6c1449f91 = K-012 + K-001c):** GATE PASS: wall −0,1…+0,2%, md5 T=0 i T=0,7 identyczne we wszystkich 4 promptach i przebiegach, wycieki 0/12, FRESH-MD5 identyczne, 94k dekod 121,16 → 123,73 t/s (+2,1%). **Wdrożone na :8080** (`topki/xtx/qwen-uncensored.sh` → `~/llama-topka-k183c`, `GGML_HIP_K012=1`; kopia skryptu `.pre-k183c`); smoke: exe i biblioteki z nowego katalogu, linia K012 w logu, md5 = produkcja.
- przeniesione 2026-11-26: w produkcji

### K-185 · Port Tintero PR #2 do Mai: grupowana weryfikacja ekspertów raz na okno, drafter w grafie, online-softmax draft_attn (zwiad 26.11)
- Źródło: GodGMN/tintero a9d857803, ta sama karta (XTX) i model: plain 111 → 121 (+9%), draft kod 103 → 151–160, okno B=5 37,6 → 21 ms. Bezstratność: zgodność greedy z plain.
- Plan: diff mechanizmów z `~/k134/wt-k158g`, port brakujących za przełącznikami w `~/k134/wt-k185`, A/B z produkcją Mai (nib-ab.sh) + md5 T=0, ≤15 min GPU. Przygotowuje agent K185Tintero.
- Port (`~/k134/wt-k185`, k185-tintero be8e5c16): GEXP (eksperci Q4_K/Q5_0 czytani raz na grupę w oknie), LGB (bramki pętli raz na okno), DONLINE (online-softmax draft_attn), EMAG (strażnik EMA); drafter w grafie, bf16/q8 mv, fuzja QKV i router mv Maya już miała.
- **wynik 2026-11-26 06:03–06:08 (XTX):** testy bitowe ok; PARITY 11/11 md5 identyczne z produkcją. Bench P=1024: eksperci v2 3,78 → 2,97 ms (GEXP), propose(7) 2,00 → 1,56 ms (−22%, DONLINE), LGB pogarsza weryfikację (v8 28,06 → 30,72 ms). **Wall prod → all: T=0 mediana 141,8 → 152,0 (+7,2%)**, kod +5,2%, tech +10,1%, json +5,7%, pl +0,3%; T=0,7 112,7 → 113,0 (+0,3%). Żadna kategoria poniżej −2% → **wdrożone 2026-11-26** (`maya-atomic.json`, kopia `maya-atomic.prev-k158g.json`). Dalej: K-185b wall „all bez LGB”.
- **K-185b 2026-11-26 06:10 (ABBA, produkcja vs bez LGB):** T=0 mediana A 147,4/152,1 vs B 151,2/147,5 (średnie 149,8 vs 149,4), T=0,7 112,2/113,0 vs 113,0/112,9: różnica w szumie; LGB zostaje jak wdrożone.
- przeniesione 2026-11-26: zwycięzca, w produkcji

### K-184 · Poprawka DFlash2 dla Inklinga z llama.cpp PR #33049 (link JARO 26.11) na XTX
- Port: `~/wt/k184` (gałąź k184-dflash2-ink, df64666ae): klucz `target_visits`, RMS-norm pożyczonych embeddingów `tok_norm` celu, softcap selektora po korekcie; drafter skonwertowany do `~/models/inkling/dflash2-Inkling-2-Mini-bf16.gguf` (989 MB).
- **wynik 2026-11-26 02:35–02:42 (XTX, Inkling AD-Q4_K, wszystko na GPU, KV q4_0, 300 tok.):** bez spekulacji 26,4 t/s; DFlash2 bez poprawki: akceptacja ≤0,15%, 12,7 t/s; **DFlash2 z poprawką: akceptacja 18–37%, 28,0–44,4 t/s (+6…+68% vs bez spekulacji)**; DSpark 20,7–31,9. md5 T=0 spec = bez spec. Maya produkcja w tej samej sesji: 112,8 t/s T=0,7. Poprawka działa, ale ścieżka llama.cpp dla Inklinga na XTX jest 2,5–4× wolniejsza od Mai; dla Enigmy (CUDA) PR jest warunkiem DFlash2 z Inklingiem. Nasze GGUF mają rozwinięte 48 wizyt, więc `target_visits` = `target_layers`; upstreamowy konwerter `DFlashModel` zapisałby id+1 (błąd dla Inklinga).

### K-007 · Bramka „wymuszanie tokenów + KLD” (SpecPilot) zamiast md5 dla zmian polityki draftu i szerokości weryfikacji, z kalibracją kanarkami
- data: 2026-11-07 (kanarki: 2026-10-15)
- status: **czeka na decyzję** właściciela (decyzja 6 z rundy 69: czy dopuścić „te same tokeny + KLD” zamiast md5)
- źródło: `R/68b-spekulacja-nowe.md:161`, `R/69-SYNTEZA.md:33,41`, [[raport-69-synteza]], [[bramka-kld-kanarki]] (`:27`, nigdy nieuruchomione na GPU), `Q/tools/kld_canary.sh`
- wzór oceny (2026-11-14): PearlQuant ma 3 warstwy: KLD, benchmarki, cechy tekstu (liczba „Wait” na 1000 słów, ślepy sędzia = sam model), a do tego celowo zepsute konfiguracje jako kontrola pozytywna ([[telegram-2026-11-14-pearlquant-llamacpp-v1]])
- test: skrypt teacher-forced na CPU. XTX: topka vs topka (szum), DRAFT_N=5 (powinno przejść), wstrzyknięty bias logitu (musi odpaść), 6 promptów × 2k tok. T=0. Kanarki po jednym na job ≤ 10 min.
- zysk: 0% sama; odblokowuje K-008, K-017 i K-046 (+3…7%)
- ryzyko karty: brak
- priorytet: wysoki (odblokowuje największy bezstratny decode)

- **decyzja JARO 2026-11-26:** zgoda ([[2026-11-26-bramka-kld]]): zmiany zmieniające md5 wchodzą po bramce KLD + wymuszanie tokenów + wall.py −2%. Następny krok: narzędzie bramki i pierwsze użycie na K-006 i K-017.
- **wynik 2026-11-26 00:45–01:00 (`~/wt/k007` 8f2fb5ccd, wymuszanie tokenów, 6 promptów × do 2048 tok., 9510 pozycji/ramię):** kalibracja VALID (n5 PASS, zmiana rope +1% FAIL: mean KLD 2,1e-5 / max 0,0747, bias1 FAIL); **K-017 PASS i K-006 PASS** (KLD 0,000000, top-1 100%, 0 rozbieżności). Uwaga: ramię plain ma top-1 0,07% (błąd zapisu logprobów w trybie bez spekulacji), próg wyszedł więc „KLD dokładnie 0” — surowszy niż planowany, wynik ważny. Narzędzie bramki: `~/qwen-opt/k007/`.
- przeniesione 2026-11-26: narzędzie gotowe, K-017/K-006 przeszły

### K-177 · Wdrożenie w Mai: K-158g `eq8-hsl-pol2-gated` jako `maya-atomic.json`
- data: 2026-11-25 (wynik K-158g niżej)
- plan: po zakończeniu K-176 i K-171 (używają `maya-atomic.json` jako bazy) podmienić konfigurację, kopia `maya-atomic.prev.json`; potem jedno wall.py kontrolne

- **2026-11-25:** K-176 (K-148 `both`) też przeszedł bramkę (czat −0,4…−0,5%, parytet 11/11, edycja +14,2%); obie zmiany połączone w K-179 (`wt-k179` 1f11609e, w kolejce). Wdrażamy zwycięzcę K-179, a gdy nie przejdzie, sam K-158g.
- **2026-11-26:** K-179 (K-148 + K-158g razem) nie przeszedł bramki (pl T=0 −2,7%), więc wdrożony sam K-158g: `~/k134/maya-atomic.json` = `k158g-eq8-hsl-pol2-gated.json` bez `IK2_STATS` (poprzednia: `maya-atomic.prev-k137.json`).
- przeniesione 2026-11-26: wdrożone (K-158g)

### K-178 · Wdrożenie samego K-020 (wyrzucanie cache ważone kosztem) na :8080
- data: 2026-11-25 (K-175 FAIL na AGR2/KVD)
- test: `k178.jobs`: PROD (`run-topka.sh uncensored`, `~/llama-topka`) vs Q (qprep-spec 50ca29355 + `LLAMA_SERVER_CACHE_EVICT=cost`), ABBA wall.py + md5 T=0 + replay K-020; bramka −2% i md5 identyczne
- uwaga: `topka-keeper.sh:19` restartuje `run-topka.sh qwen` (UD-Q4_K_XL z cenzurą, ctx 204 800), a `chat8080.sh restore` startuje `uncensored` (ctx 262 144): dwa różne modele produkcji zależnie od tego, kto podnosi czat
- czas karty: ok. 9 min
- **wynik 2026-11-26 00:31–00:39 (XTX):** wall.py Q vs PROD wszystkie kategorie −0,1…+0,1%, md5 T=0 IDENTICAL we wszystkich 4; replay K-020: 4 → 0 ponownych prefilli, 207,9 → 101,8 s (−51%). **GATE PASS → wdrożone 2026-11-26 02:40:** silnik `~/llama-topka-k020` (kopia qprep-spec 50ca29355) + `LLAMA_SERVER_CACHE_EVICT=cost` w `~/qwen-opt/topki/xtx/qwen-uncensored.sh`; działa od najbliższego podniesienia czatu.
- przeniesione 2026-11-26: wdrożone

- **2026-11-26:** JARO zgadza się na test; restart wymaga `sudo` z hasłem (Kernel go nie ma) i nie może przerwać kolejki: po opróżnieniu kolejki JARO wpisuje `grub-reboot` + `reboot`, a Kernel robi pomiary.
### K-026 · Enigma: próg draftu `--spec-draft-p-min` {0; 0,5; 0,8} × n {1,2,4} dla MoE z `--n-cpu-moe` na kartach ≤ 16 GB
- data: 2026-11-07 (66a A2)
- źródło: [[prog-draftu-od-kosztu-wiersza]], `R/66-SYNTEZA.md` poz. 10
- test: 5060 Ti z Qwen3.6-35B-A3B `--n-cpu-moe 20/30/40` albo emulacja na XTX; spec_sweep T=0/T=1 ABBA ~10 min/klasę
- zysk: 0…+15% na MoE z offloadem (Strata +5,6…9,3%); model rezydentny ~0
- ryzyko karty: brak
- priorytet: średni (produkt Enigma)

- **2026-11-25:** `~/models/q36` pusty, więc zamiennik: Inkling-2-Mini AD-Q4_K (MoE 128/8) z DSpark przez `~/wt/upstream-inkling`, `--n-cpu-moe 12`; w kolejce `k026a.jobs` (głębokość 0/1/2/4) i `k026b.jobs` (p-min 0 / 0,5 / 0,8).
- **wynik 2026-11-25 23:46–00:17 (XTX, Inkling 2 Mini AD-Q4_K, DSpark, `--n-cpu-moe 12`, serwer na 4 rdzeniach, `~/wt/upstream-inkling`):** bez spekulacji 15,7 / 15,7 t/s (T=1 / T=0); draft n1 9,2 / 9,5, n2 7,9 / 8,4, n4 6,0 / 6,8 (akceptacja 1,1–1,26 tok/krok, krok 121–194 ms vs 64 ms). p-min 0,5 i 0,8 przy n4: 15,3 (drafter praktycznie wyłączony, −2,5% narzutu). **Wniosek dla Enigmy: przy MoE z ekspertami na CPU spekulacja szkodzi (do −62%), więc domyślnie wyłączona**, bo każdy dodatkowy wiersz weryfikacji uruchamia ekspertów na CPU.
- przeniesione 2026-11-26: zmierzone, reguła dla Enigmy

- **2026-11-26:** jądro 7.0.0-43 już zainstalowane obok 6.8 (GRUB przypięty do 6.8). Test jednorazowy wymaga JARO: `sudo grub-reboot "Advanced options for Ubuntu>Ubuntu, with Linux 7.0.0-43-generic" && sudo reboot` (kolejny reboot wraca do 6.8), potem ok. 30 min pomiarów.
### K-121 · Adapter GA z wyścigami (Rohan Arun) do naszych sweepów wariantów: test-backend-ops perf na XTX i na NVIDIA (kernele draftu K-116)
- data: 2026-11-18
- źródło: [[ga-racing-rohanarun]] (`Auto-research-agent` @ `9367733`, eliminacja na log-ratio do mediany żywych, bramka rel < 0,997 i CI < 1 na świeżych danych, `pending` → czarna lista); demo działa tu na CPU (1,4 s, syntetyczne)
- hipoteza: automatyczny wyścig znajduje w tym samym czasie GPU co nasza siatka tego samego zwycięzcę (FA D256 wariant 83) albo lepszego, przy mniejszej liczbie pomiarów; na NVIDIA wybierze kafle/wątki kerneli draftu MTP
- test: CPU: adapter `hip_tbo.py` (komórki = kształty z profilu kroku, geny = zmienne `GGML_HIP_FA_D256_VAR` / warianty MMQ, pomiar = `test-backend-ops -o perf` na kształcie, build = sprawdzenie `test-backend-ops` bitowo); karta: XTX przez `run-jobs.sh`, `GGML_HIP_PM4=0`, ≤ 10 min; potem to samo na 5060 Ti (Vast, hostguard)
- miara: zwycięzca i jego czas vs nasz wybór z siatki; liczba pomiarów do decyzji
- zysk: szybsze strojenie per architektura (dźwignie kernelowe trzeba stroić osobno na każdą kartę); 0 t/s samo w sobie
- ryzyko karty: reset przy wariancie z faultem → tylko PM4=0, nadzór, kolejka
- priorytet: niski

- **2026-11-25:** w kolejce (`k121.jobs`): Auto-research-agent `9367733` z adapterem `hip_tbo.py`, geny = 12 bezstratnych wartości `GGML_HIP_FA_D256_VAR`; pytanie: czy wyścig wybierze 83 mniejszą liczbą pomiarów.
- **wynik 2026-11-25 23:3x (XTX, Auto-research-agent `9367733` + `hip_tbo.py`, FA D256 f16 KV 64k nb512):** bramka 12/12 wariantów 173/173. Wyścig skupił pomiary na v131 (n=20, 19 132,8 µs) i v3 (n=12, 19 089,4 µs); v83 19 896,9 µs (n=3), v0 19 574,9. Adapter działa: wyścig sam zawęża pomiary do najlepszych. Dla f16 KV najlepsze są 3/131 (−4% vs 83), produkcja ma KV q4_0, gdzie 83 wygrało w raporcie 70, więc bez zmiany produkcji; narzędzie do użycia w następnych sweepach.
- przeniesione 2026-11-26: narzędzie działa

### K-176 · Wdrożenie w Mai: K-148 `both` (szerokie okno sufiksu, edycja kodu +14,2%)
- data: 2026-11-25
- test: wall.py `pl` T=0 / T=0,7 prod vs `wt-k148` z SFXBLK=32 SFXRG=16, bramka −2%; potem `maya-atomic.json` → binarka k148
- czas karty: ok. 5 min
- priorytet: wysoki
- **wynik 2026-11-25 21:42–21:45:** GATE PASS (czat T=0/T=0,7 −0,4…−0,5%, kod T=0 +3,0%), parytet IDENTICAL 11/11; scalone z K-158g w K-179.
- przeniesione 2026-11-26: zmierzone, wchodzi przez K-179/K-177

### K-115 · Bramka igieł (K-109) na NVIDIA: 5060 Ti (IQ3_XXS, 196k) i 3090 (UD-Q4_K_XL, 245k) z przepisami Enigmy
- data: 2026-11-17
- źródło: [[skill-io-publikacja]] (bramka 5: igła ~85% okna); [[final-recipes-nvidia]] (konteksty przepisów)
- hipoteza: 3/3 kody przy 50% i 85% okna; jeśli nie, przepis Enigmy obiecuje kontekst, którego model nie czyta (KV q4_0 + mały kwant)
- test: `bench.py run --long <0,5·ctx>` i osobny job `--long <0,85·ctx>` na każdej karcie; fill 167k (85% z 196k) na 5060 Ti: 3 min przy suficie prefillu 924 t/s, ~10 min przy 30% sufitu [INFERENCE: prefillu 5060 Ti nie mierzyliśmy, K-112 najpierw]; jeśli > 10 min, bramka 85% jako jedyny job tej sesji
- miara: retrieval k/3, TTFT, szczyt VRAM vs przepis
- zysk: poprawność przepisów Enigmy NVIDIA; 0 t/s
- ryzyko karty: brak
- priorytet: średni
- **wynik (Colab L4 sm_89, fork 007a6f813, 2026-11-25, `/tmp/nvc/res` na Jarvie):** igły 5/5, 0 zmyślonych przy 96 362 i 164 487 tokenach promptu (278 s i 372 s), VRAM 16,1 GB. PASS na L4; 5060 Ti i 3090 wymagają wynajmu.
- przeniesione 2026-11-25: PASS na L4

- **wynik 3090 2026-11-26 (Vast 3090 nvq, [[2026-11-26-nvq-3090]]):** 120k i 208k: 5/5, 0 zmyślonych.
### K-064 · Zwinięcie haka promptu MTP do grafu celu (TTFT) w forku CUDA
- data: 2026-10-16
- źródło: `R/67c-nvidia-backlog-testow.md:113` (B19), `R/15d-prefill-dlugi-kontekst.md:110`
- test: 5060 Ti: build + TTFT 512/2k, md5; ≤ 10 min
- zysk: TTFT −5…7% przy 2k
- ryzyko karty: brak
- priorytet: niski (mały TTFT)
- **wynik (Colab L4 sm_89, fork 007a6f813, 2026-11-25, `/tmp/nvc/res` na Jarvie):** hak promptu MTP kosztuje w prefillu pp512 835 → 1143 ms (+37%), pp2048 2955 → 3385 ms (+14,5%); z 168 ms haka 140 ms to synchronizacja hosta (`h_sync`), draft 24 ms. Zwinięcie haka do grafu celu może oddać do ok. 140 ms na 512 tokenów TTFT; to praca w forku CUDA (nowa pozycja przy następnym wynajmie).
- przeniesione 2026-11-25: zmierzone

### K-117 · Fork CUDA: cache skwantowanej głowicy draftu i MTP (`LLAMA_MTP_REQUANT_CACHE` jak na XTX) — start na słabym CPU 12 min → sekundy
- data: 2026-11-17
- źródło: [[2026-11-17-k114-nvidia-sufit]] (host 3090 TW: 12 min od „initializing” do gotowości; 5060 Ti na 64 rdzeniach 32 s); XTX: start 39,8 → 6,5 s z cache ([[REKORDY]])
- hipoteza: port przełącznika z topki do forka CUDA (kod w `common/`, nie w kernelach) skraca każdy kolejny start do < 10 s; bitowo te same wagi draftu
- test: CPU (budowa) + dowolna karta NVIDIA: start zimny vs ciepły, md5 T=0 identyczne
- miara: s do `/health` przy drugim starcie
- zysk: start Enigmy na NVIDIA ze słabym CPU: minuty → sekundy (UX, 0 t/s)
- ryzyko karty: brak
- priorytet: średni
- **wynik (Colab L4 sm_89, fork 007a6f813, 2026-11-25, `/tmp/nvc/res` na Jarvie):** start serwera bez cache 28,75 / 29,05 s, cache zimny 29,35 s, **cache ciepły 6,86 / 6,84 s (−76%)**, md5 identyczne (439bdb8f, c62d8d52). Wygrany dla czasu startu (Enigma).
- przeniesione 2026-11-25: wygrany (start −76%)

### K-068 · CUDA `kvq`: KLD wariantu z wyjątkiem n=1 D256 q4_0 (`678473a27`) i serwer MTP@64k z wyjątkiem
- data: 2026-10-18
- źródło: `STAN-PRAC.md` (CudaKvq, „Niezmierzone”), [[2026-10-16-kvq-cuda-zostaje]]
- test: `llama-perplexity --kl-divergence --chunks 5` Qwen q4_0 ub1 + serwer MTP 64k; 3090 (wynajem) albo 5060 Ti przy mniejszym kontekście; ≤ 10 min/ramię
- zysk: poprawność (przy ub1 = vec z konstrukcji [INFERENCE])
- ryzyko karty: brak
- priorytet: niski (formalność)
- **wynik 2026-11-24 (Colab, [[colab-kolejka-2026-11-24]]):** L4, 63k bez MTP: wyłączenie wyjątku n=1 (`GGML_CUDA_KVQ_N1_D256_Q4=1`) dekod 12,54 → 16,64 t/s (+32,7%), ale wyjście się zmienia; z MTP ok. +2% (38,1–38,3 → 39,0), wyjście identyczne. Prawdziwy KLD niewykonany (paczka bez `llama-perplexity`); top-10 prawdopodobieństw różni się średnio 4,3e-4, tyle co kvq vs zwykła uwaga. Decyzja wymaga KLD.
- **wynik (Colab L4 sm_89, fork 007a6f813, 2026-11-25, `/tmp/nvc/res` na Jarvie), llama-perplexity KLD vs f16 (PPL 6,1868):** q4 KVQ0 (stock vec) i KVQ1 z wyjątkiem: mean KLD 0,002471, max 0,260; KVQ1 **bez wyjątku n=1 D256 q4_0**: 0,002256, max 0,059, top-1 97,96%. Bez wyjątku KLD jest niższe, więc wyjątek `678473a27` można usunąć (serwer MTP@64k nie zdążył).
- przeniesione 2026-11-25: zmierzone

### K-016 · Fork CUDA: ogon lookupu W8/W16/off oraz MTP n 2/3/5 per klasa na promptach kopiujących
- data: 2026-11-07
- źródło: `R/67c-nvidia-backlog-testow.md:99-101` (B5–B7; 5060 Ti: n=3 ≥ n=4, fork ma sztywne 4), [[final-recipes-nvidia]]
- test: 5060 Ti: `LLAMA_SPEC_LOOKUP_W=8/16`, `LLAMA_SPEC_LOOKUP=0`, `--spec-draft-n-max 2/3/5`, `mvs` + spec_sweep; po jednym ramieniu na job ≤ 10 min
- zysk: dobór przepisu Enigmy per klasa; W16 na wąskiej szynie może przegrywać [INFERENCE]
- ryzyko karty: brak
- priorytet: średni (przepis Enigmy, lokalnie)
- **wynik (Colab L4 sm_89, fork 007a6f813, 2026-11-25, `/tmp/nvc/res` na Jarvie), Qwen3.8-27B IQ3_XXS:** T=1: n4 34,25 / 34,22 → **n2 36,59 (+6,9%)**, n3 36,39 (+6,3%), n5 31,67 (−7,5%); kopia T=0: n4 138,7 → n2 138,2, n3 140,4 (+1,2%), n5 125,0; ogon W8 kopia 81,8 (−41%), bez lookupu 63,2 (−54%); KVQ0 T=1 33,45 (−2,3%). Werdykt: na L4 n3 (albo n2) lepsze od n4 przy T=1 bez straty kopii; ogon W16 zostaje. Potwierdza kierunek K-129.
- przeniesione 2026-11-25: zmierzone

### K-004 · Fork CUDA: dokładne próbkowanie spekulacyjne na GPU przy T=1 (jak qwen-warp)
- data: 2026-11-09
- źródło: [[2026-11-09-qwen-warp-vs-fork-3090]] (pkt 2: fork traci przy T=1 7–13%, warp nie traci), `R/69b-tensorfold-qwen-warp.md` §3
- **poprawka planu (audyt 2026-11-19):** wydany fork `kvqlean`/`kvqleana` (cuda-topka2 + kvq `007a6f813`) **nie ma** sprzężonego próbkowania `7cdc0121b`, więc `LLAMA_SPEC_COUPLED` 0/1 na nim nic nie zmieni [INFERENCE: potwierdzić `strings llama-server | grep LLAMA_SPEC_COUPLED`]. Zmierzone sprzężone na CUDA: +5,3…5,5% (3060/3080, `31-3060-3080.md:146`), +5,4% (4060 Ti), 5060 Ti +1,9% z CI [−4,9; +8,3]. Strata „7–13%” to spadek T=0 → T=1 z akceptacji (K-114), nie cały do odzyskania
- test: (1) CPU: build kvqlean + merge `7cdc0121b` (merge-tree bez konfliktów), `test-backend-ops`; (2) 5060 Ti (Vast + hostguard) spec_sweep T=1 ABBA COUPLED 0/1, 6 promptów × seedy 1–4, md5 T=0 6/6; (3) dopisać `LLAMA_SPEC_COUPLED=1` do profilu Enigmy dopiero z nową binarką. Stary plan: Po porcie: ABBA 6 × 3 seedy, md5 T=0 bez zmian; potwierdzenie na 3090 (wynajem, metoda `nv69q`).
- zysk: +5…5,5% przy T=1 na NVIDIA (zmierzone na sm_86/89); wszyscy użytkownicy Enigmy z NVIDIA
- ryzyko karty: brak
- priorytet: wysoki (Enigma NVIDIA, tani pierwszy pomiar)
- zwiad 2026-11-14: tqLLM 1.5.0 robi dokładne próbkowanie MTP przy T>0 (3090, T=0,7: 50 → 104–117 t/s), wzór do portu ([[zwiad-2026-11-14]])

- **2026-11-25 (Colab L4):** bramki: `test-backend-ops -o GUMBEL_MAX` 152/152, `test-coupled-sampling` all passed; pomiar T=1 COUPLED 0/1 nie zdążył (`/tmp/nvc/colab/run.py k004`, ok. 20 min L4).
- **wynik (Colab L4 sm_89, fork 007a6f813, 2026-11-25, `/tmp/nvc/res` na Jarvie):** T=1 COUPLED 0 → 1: 34,24 / 33,89 → 35,01 / 34,98 t/s (**+2,7%**), T=0 37,54 → 37,43 (bez zmian); bramki GUMBEL_MAX 152/152, test-coupled-sampling OK. Poniżej progu 3% na L4; powtórzyć na 3090/5060 Ti przy wynajmie.
- przeniesione 2026-11-25: zysk poniżej progu na L4

### K-025 · FA D256 wariant 83 dla innych modeli i kształtów (Saluki/Bonsai, Qwen3.6-35B-A3B, LFM2.5 D=64, f16 KV, RDNA3.5) przed włączeniem domyślnie w kodzie
- data: 2026-11-09
- źródło: `R/70-fa-d256-jak-to-zrobilismy.md:184,187` (#1, #4), §6.2; dziś 83 tylko dla qwen/uncensored przez launcher (f16 KV przy 131k: −2,4%)
- test: XTX `fa-d256/bench.sh` z `M=<model>` przy 4k/32k/131k (~17 min → 2 joby), md5 jak `md5.sh`; dla 35B-A3B rozszerzyć warunek `:2216` i sweep
- zysk: Saluki/Bonsai ≥ +5,8% fillu [INFERENCE], 35B-A3B przy ≥ 128k +3…5%, LFM +1…2%; dla katalogu Enigmy, nie produkcji
- ryzyko karty: brak
- priorytet: średni (Enigma)

- **bieg 2026-11-25 19:55 nieważny:** md5 Bonsai 0 = 83 (4b32fc1a), ale `var_log=0` w obu ramionach, więc wariant 83 nie został użyty (przełącznik nie trafia w kernel tego kształtu); serwer Qwen3.6-A3B nie wstał (Connection refused). Do naprawy skryptu przed powtórką.
- **2026-11-25 diagnoza:** `var_log=0` to problem logowania (INFO ggml w llama-server wymaga `-lv 4`, llama-bench `-v`), wariant 83 działał. Skrypty poprawione (`~/qwen-opt/k025/{md5,bench,common}.sh`), joby A3B wyłączone (brak modelu). Ponownie w kolejce.
- **wynik 2026-11-25 22:10–22:26 (XTX, `~/wt/k025` 7e6bd853c, poprawione skrypty):** test-backend-ops FA hsk=256 173/173 (kształty 16x4, 32x2, 8x8); md5 12k: Bonsai q4_0 0 = 83 (4b32fc1a, kontrola 7 różna), Bonsai f16 0 = 83, Qwen3.5-0.8B 0 = 83 (kształt 16x4). Bonsai 2.5 Q2_0 llama-bench pp512 ABBA: d4k 876,2 → 880,7 (+0,5%), **d32k 711,8 → 726,0 (+2,0%)**, d128k 387,1 / 441,5 → 465,1 (+5…+20%, ramiona 0 rozjechane; średnio +12%). Werdykt: zysk jest już w produkcji: Bonsai (GQA 6) używa kształtu 32x2, a topka-k157 ma wariant 83 dla 32x2 (`fattn-mma-f16.cuh:2216,2310`) i `bonsai25/serve.sh:11` go włącza; pomiar to VAR 0 vs 83, nie prod vs nowy. Łatka k025 dodaje tylko kształty 16x4 i 8x8 (GQA 4/8), bez modelu w produkcji. Qwen3.6-A3B i LFM bez modelu na dysku.
- przeniesione 2026-11-25: zmierzone; nic do wdrożenia

### K-171 · Inkling na równych warunkach z llamAmpere: T=1, top-k 20, top-p 0,95 (Maya prod, Nib + LoRA, K-158f)
- data: 2026-11-25 (panel JARO: llamAmpere v0.7.5 189 t/s przy 3K i 144,7 przy 100K na 3090 Ti, „T=1”)
- powód: ich profile ustawiają top-k 20 (`common/preset.cpp:117`); my mierzymy T=0,7 pełnym rozkładem; K-167 pokazał, że top-k zmienia wynik ×3,8. Bez tego testu nie wiemy, czy przegrywamy
- test: wall.py z samplerem T=1 / top-k 20 / top-p 0,95, prompty 3K i 32K, odpowiedź 2048 tok., 3 seedy, ramiona: Maya `maya-atomic.json` (prod), Nib + LoRA (`~/wt/nib-unc`), Maya k158-dspark; port 18796, PM4=0
- czas karty: ok. 10 min
- priorytet: wysoki (wyścig Inkling)
- **wynik 2026-11-25 21:45–21:59 (XTX, PM4=0, odpowiedź 2048 tok., 3 seedy, mediana):** T=1 / top-k 20 / top-p 0,95, prompt 3K / 32K: Maya prod **101,8 / 90,7**, Maya K-158 (bez POLICY) **110,3 / 105,9**, Nib + LoRA 75,0 / 70,7 (rzadka atencja od 14k), Nib gęsty 32K 92,6. Maya T=0,7 pełny rozkład 100,7 / 90,8. llamAmpere v0.7.5 na 3090 Ti (1008 GB/s) w tych warunkach: 189,0 / 182,6. **Jesteśmy ok. 1,7× wolniejsi przy długich odpowiedziach**; 150 t/s Niba dotyczyło odpowiedzi 300 tok. Różnice: ich kwant 5,4 bpw i drafter ATX 0,45 GB (nie DSpark), KV 4-bit. Następny krok: przejrzeć ich drafter i ścieżkę weryfikacji (`~/kernel/zrodla/llamAmpere`, v0.7.5) pod kątem bezstratnych dźwigni.
- przeniesione 2026-11-25: zmierzone

### K-022 · Natywne q4_0 K/V w prefillu FA D256 (bit 128 / #31802): wyjaśnić md5 wariantów 131/147, alternatywnie szybszy staging q4_0→f16
- data: 2026-11-07
- źródło: [[2026-11-08-fa-d256-prefill]] (`:35`), `R/70-fa-d256-jak-to-zrobilismy.md` §3.6 (173/173 w `test-backend-ops`, ale md5 e9dcdd80 ≠ 816334e4), `R/68d-swieze-od-spolecznosci.md:137`, `R/68c-dlugi-kontekst-gdn.md:137`
- test: najpierw różnica na CPU (ścieżka dekwantu vs `dequantize_q4_0`, ogon KV). XTX `fa-d256/md5.sh` + micro (≤ 10 min); szczyt VRAM przy fill 255k osobnym jobem (~9 min).
- zysk: VRAM −~1 GiB przy 262k, fill 255k +2…3%; staging sam −2% fillu (~11 s)
- ryzyko karty: VRAM (szczyt może się przesunąć)
- priorytet: średni (VRAM daje zapas dla K-048)
- **wynik 2026-11-25 19:56–20:54 (XTX, `~/wt/k022` k022-kq4, wariant 211 = 83 + natywne q4_0):** op FA bit w bit (0 z 4 497 408 floatów), md5 drabinki równe (VERDICT lossless). Prefill pp d32k 776,5/773,8 → 775,2/776,0 (±0,2%), d128k 484,2/485,0 → 485,9/486,0 (+0,3%). Fill 255k: prefill 492,0 → 494,0 t/s (+0,4%), md5 tekstu równe (97070884), **szczyt VRAM 23 323 → 22 346 MiB (−977 MiB)**. Werdykt: prędkość bez zmian, ale ok. 1 GB VRAM mniej przy pełnym kontekście bezstratnie; do wdrożenia przy najbliższym buildzie produkcji (K-175 zostaje jak jest). `~/qwen-opt/k022/res/`.
- przeniesione 2026-11-25: bezstratne, −1 GB VRAM, prędkość bez zmian

### K-038 · Przeszukiwanie flag spekulacji (TPE: DRAFT_N, LOOKUP_W/MMIN, PM4_MIN_DISPATCH, typ KV draftu) na odłożonym zestawie
- data: 2026-11-05
- źródło: `R/63-SYNTEZA.md:93` (#14), `R/63e-metodologia-agenci.md` §11, [[zestaw-odlozony]]
- test: XTX xtxbench `--var-switch` po jednej fladze na job (~4 min), zwycięzcy na holdoucie; zmiany szerokości tylko po K-007
- zysk: spec_sweep +1…5% [SZACUNEK]
- ryzyko karty: brak
- priorytet: niski (szum, klątwa zwycięzcy)
- **wynik 2026-11-25 19:17–19:30 (XTX, `~/wt/qprep-spec`, dev = sweep T=1 seed 1,2 + kopia short/mvs T=0; prod P1/P2/P3 T=1 120,0 / 120,0 / 120,1):** PM4_MIN_DISPATCH 8: 119,6; 32: 120,0; LOOKUP_MMIN 4: 116,1 T=1 (kopia +2,0%); MMIN 8: 120,1; **KV draftu q8_0: 122,2 (+1,8% T=1)**, kopia bez zmian. Plik zwycięzcy nie powstał (próg łączny dev). Kandydat `KVD=q8_0` (precyzja wyższa niż q4_0, wyjście bez zmian) potwierdzić ABBA w K-175.
- przeniesione 2026-11-25: screening zrobiony; KVD q8_0 do K-175

### K-165 · Inkling uncensored w Nib: LoRA AtomicChat (rank 1, 98 tensorów) w runtime Nib, cel ≥ 145 t/s przy T=0,7
- data: 2026-11-25 (JARO: „nowe infra ma 150 t/s”; Nib 150,6 t/s T=0,7 KV q4 na naszym XTX, ale wagi ocenzurowane)
- plan: agent dopisuje `--lora` do Nib (attn_output + ffn_down_exps, wszystkie ścieżki, grafy HIP); XTX: selftest z/bez LoRA, 5 promptów odmowy przy T=0, wall.py T=0 / T=0,7 KV q4; potem Nib jako czat Inkling zamiast Mai
- czas karty: ok. 15 min
- priorytet: najwyższy
- **wynik 2026-11-25:** pierwszy bieg (13:27) unieważniony: odpowiadał osierocony serwer Mai z K-164 ([[lekcja-zabicie-skryptu-nie-serwera]]). Powtórka k165b: odmowy stock 5/5, z LoRA 0/5; wall.py T=0 / T=0,7: stock 168,2 / 149,9, **LoRA 156,6 / 147,3** (Maya 113,9 / 113,4). Cel ≥ 145 osiągnięty. Dalej: jakość NVFP4+LoRA vs AD-Q4_K (KLD/odpowiedzi), decyzja JARO o czacie Inkling na Nib.
- **jakość (K-168, HumanEval+):** Nib + LoRA 92,1 / 87,2% vs Maya 90,2 / 85,4%; dekod kodu 209,5 vs 124,4 t/s. Gotowe do decyzji JARO (czat Inkling na Nib + LoRA).
- przeniesione 2026-11-25: zmierzone; wdrożenie Niba czeka na decyzję JARO (polski −30%)

### K-020 · Polityka wyrzucania `--cache-ram` ważona kosztem przeliczenia (Marconi) zamiast LRU
- data: 2026-11-07
- źródło: `R/68c-dlugi-kontekst-gdn.md:143` (#9)
- test: XTX replay 3 wątków (2 długie + krótkie) z `LLAMA_SERVER_PREFIX_LOG`, liczba pełnych prefilli ≥ 20k; ~10 min
- zysk: chroni wpisy ≥ 100k (przeliczenie 100–550 s) przy presji 40 GB [INFERENCE]
- ryzyko karty: brak
- priorytet: średni (rzadkie, ale ogromne tury)
- **wynik 2026-11-25 19:06–19:17 (replay 3 wątki: 2 × 24k + 12 × 3k, `--cache-ram 8192`):** LRU (prod, A1/A2): 4 pełne ponowne prefille długich wątków, prefill łącznie 201,5 s, follow-up długiego wątku 107,7 s, wall 208,0 s; koszt α=1 i α=4 (B1, C1): **0 ponownych prefilli, prefill 95,2 s (−53%), follow-up 1,5 s, wall 102,0 s (−51%)**. Wyjście modelu się nie zmienia (to tylko polityka cache). Werdykt: **wygrany**, wdrożenie α=1 razem z K-018 (K-175).
- przeniesione 2026-11-25: wygrany, wdrożenie K-175

### K-019 · Cache sufiksów między sesjami (draft z poprzednich wyjść agenta, styl SuffixDecoding)
- data: 2026-10-19 (raport 18), 2026-11-07 (67c C18)
- źródło: `R/67c-nvidia-backlog-testow.md:135`, archiwum (`A:21140`)
- test: symulacja CPU na logach omp, potem XTX spec_sweep PL + replay agenta ABBA (kill < +1%); ≤ 10 min
- zysk: +5–15% na agentach [SZACUNEK]; zmienia tylko drafty
- ryzyko karty: brak
- priorytet: średni (agenci, tani offline)
- wynik 2026-11-20: symulacja CPU (`qwen-opt/k019/suffix_sim.ts`, wynik `qwen-opt/k019/wynik-2026-11-20.txt`): 190 sesji omp, 212 epok, 8,52 mln tokenów wyjść agenta (tokenizer Qwen3), model kroku jak w `product/research/21c-cplm/oracle.py` (MTP n 4, ogon przy m ≥ 6 i k = 4). Cache sufiksów z wcześniejszych sesji (CROSS) zamiast lookupu w sesji: 3,39 → 3,70 tok/krok, +8,4% t/s (model); oba razem (UNION: lokalny, a gdy nie trafi, cache sufiksów) 3,98 tok/krok, **+15,9%**. Najwięcej `write` +19,8% i tekst asystenta +22%, najmniej `edit` +14,7% i `bash` +13%. Ograniczenia: wyjścia pisał Claude, nie Qwen; podagenci powtarzają podobne teksty, więc wynik to raczej górna granica. Następny krok bez zmian: XTX spec_sweep PL + replay agenta ABBA.
- **wynik 2026-11-25 18:43–19:06 (ABBA, LIVE=0, korpus omp 2026-11):** replay agenta 61 tur T=0: 138,1 / 138,5 → 140,6 / 140,0 t/s (**+1,4%**), tok/krok 4,111 → 4,198 (+2,1%); spec_sweep T=1 110,0 → 115,1, ale tok/krok identyczne, więc to szum termiczny, nie zysk. Werdykt: poniżej progu 3%, nie wdrażamy osobno; wróci z korpusem LIVE=1.
- przeniesione 2026-11-25: poniżej progu

### K-018 · AGR2: kandydat lookupu zgodny z 4 draftami MTP (`LLAMA_SPEC_LOOKUP_AGREE=1`) + dynamiczny słownik draftu
- data: 2026-10-19 (21c), 2026-11-05 (63 #18)
- źródło: [[agr-lookup-zgodny-z-mtp]], [[2026-10-19-sufit-pointera-lookup]], `R/21c-copy-paste-lm.md:185-194`, `R/63-SYNTEZA.md:97`
- test: najpierw symulacja CPU; XTX ABBA w jednej binarce na `mvs`, `copy` (hashline-pl) i spec_sweep T=0/T=1; kill < +2% hashline albo > +0,5% ms/krok na czacie; ≤ 10 min
- zysk: agent +3,7%, hashline +5,4%, czat +0,6% (symulacja); zmienia tylko drafty
- ryzyko karty: brak
- priorytet: średni (na granicy progu)
- **wynik 2026-11-25 18:31–18:43 (XTX, ABBA, `~/wt/qprep-spec` 50ca29355, konfiguracja produkcji):** kopiowanie mvs T=0 434,8 → **458,4 (+5,4%)**, short T=0 407,5 → 427,7 (+5,0%), short T=1 386,7 → 402,4 (+4,1%), md5 T=0 równe na wszystkich promptach; spec_sweep T=0 127,9 → 125,3 (**−2,0%**), T=1 115,5 → 117,6 (+1,8%). Werdykt: wygrany na kopii/edycji, czat w granicy bramki (−2,0%); wdrożenie razem z K-020 (K-175) po wall.py `pl`.
- przeniesione 2026-11-25: wygrany, wdrożenie K-175

### K-164 · Inkling: drafter DFlash2 (incoai, 0,99 GB) zamiast DSpark w Mai na XTX
- data: 2026-11-25 (zwiad: H200 T=1 akceptacja 4,96 vs 3,52 DSpark, GSM8K 482 vs 375 t/s; tqllm Metal exact+DFlash2 57,1 vs 52,1)
- plan: pobrać `incoai/Inkling-2-Mini-DFlash2` (0,99 GB); w Mai brak DFlash2 (jest DSpark) → port na podstawie tqllm 788055720 i `sglang_inkling_dflash2.py`; najpierw CPU: kształty i referencja; potem XTX: parytet 11/11, wall.py T=0 / T=0,7 vs produkcja i vs DSpark
- zysk: +20…40% przy T=0,7, jeśli krok weryfikacji tani (łączyć z K-158) [SZACUNEK]
- priorytet: wysoki
- **wynik 2026-11-25 (gałąź `k164-dflash2` fea522a0):** test GPU vs referencja CPU PASS (drafty identyczne, propose 3,84 ms z głowicą Q8, 8,29 ms FP16, write_context 0,13–0,20 ms), test akceptacji q (min(1,p/q)) passed, parytet 11/11. rep2 Q1 / Q6 / L2k: produkcja 129,7 / 114,1 / 107,7; df2 85,9 / 96,4 / 101,1; df2only 115,7 / 96,6 / 99,0; df2q (próbkowanie z q) 85,5 / 98,1 / 100,7; df2qonly 115,7 / 98,3 / 102,2. wall.py: produkcja 108,5 / 110,5, df2 108,6 / 108,4, df2q 107,9 / 106,9.
- wniosek: DFlash2 w Mai dziś przegrywa przy T=0,7 (−14%) z tego samego powodu co K-158: droga runda weryfikacji. Q1 dwumodalne (82–86 albo 124–134 na bieg), do wyjaśnienia (sterownik spekulacji). Dalej: statystyki akceptacji (IK2_STATS) i ponowny pomiar po K-158b.
- **k164b 2026-11-25 (build 9b95ffbe: grafy okien przed READY, koszt draftu osobno, sonda z odstępem; okno 8 w każdym kroku, bez lookupu, IK2_STATS):**
  - DFlash2 greedy (df2m): T=0 **3,73 tok./okno**, Q1 **209,8 t/s** (+62% vs 129,7), ale L2k 80,9; T=0,7 1,93 tok./okno, Q6 44,6. Próbkowanie z q (df2qm): T=0,7 2,05 tok./okno, Q6 47,6. DSpark (dsm): T=0 3,09, T=0,7 1,58 tok./okno, Q1 104,4.
  - **Księga rundy Mai:** zwykły token 7,8 ms; draft 3,2–3,8 ms (Nib 1,4); weryfikacja okna 8 ok. 40 ms (5,1 tokenu), c[2..8] = 13,3 / 16,4 / 23 / 18–25 / 29 / 21 / 41 ms. Przy T=0,7 rep2 wysyła pełny rozkład, więc drafty punktowe trafiają rzadko (8–15% draftów).
  - z nowym sterownikiem (df2only, df2qonly, dsonly) sterownik słusznie prawie nie draftuje przy T=0,7: Q6 107,8–109,4 vs 114,1 produkcja (−4…−5%), Q1 122,6–124,5.
  - wniosek: DFlash2 to najlepszy drafter przy T=0 (3,73 vs 3,09 tok./okno), ale zysk zjada weryfikacja: koszt rośnie z kontekstem (L2k −25%) i z szerokością. Kolejność: K-158b (atencja okna w jednym launchu, eksperci okna przez kernele tokenu), tani draft (K-159: głowa skrócona, wagi Q8), potem ponownie df2 z oknem wg pewności.
- **k164c 2026-11-25 (ac47cca2: shortlista głowy 32768 + kontekst, wagi Q8, graf, okno wg pewności):** propose 3,43 → 2,54 ms (warstwy 2,4–2,8 ms nie schodzą z Q8, więc ograniczone opóźnieniem, nie pasmem; głowa 0,74 → 0,15 ms). Parytet 11/11. rep2 Q1 / Q6 / L2k: df2m-sl 106,3 / 43,9 / 83,0; df2-conf-sl 144,0 / 77,0 / 105,5; df2-conf-slq 145,4 / 81,5 / 106,8. Akceptacja: okno 8 T=0 3,54 tok., T=0,7 1,86–2,02; okno wg pewności T=0 2,45 tok. (86% draftów), T=0,7 1,60. Weryfikacja na tej gałęzi bez poprawek K-158b (okno 8 = 40 ms), więc DFlash2 ocenić dopiero po przeniesieniu na `k158-dspark`.
- **wynik K-164d 2026-11-25 17:10–17:24 (DFlash2 na gałęzi K-158 `k164-on-k158` 09574b81):** rep2 prod Q1 / Q6 / L2k 129,5 / 113,8 / 107,4; DFlash2 + gate 178,6 / 108,7 / 122,3 (L2k +13,9%, Q6 −4,5%); DSpark pol-gate 202,2 / 111,0 / 120,8. wall.py T=0,7: df2-gate mediana 122,4 (code 135,4, tech 109,4, **pl 105,9**, json 186,9), df2-pol-gate 107,9 (pl 107,1). Produkcja pl ok. 113: bramka `pl` (−2%) blokuje oba. Werdykt: nie wdrażamy; DFlash2 wygrywa długi kontekst, przegrywa polski.
- przeniesione 2026-11-25: bez wdrożenia (bramka pl)

### K-148 · Maya: szybsza weryfikacja szerokiego okna sufiksowego (dziś ścieżka prefillu, ok. 0,2 s na 96 tokenów)
- data: 2026-11-24 (K-147: nasz sufiks 404–452 / 299 t/s vs GodGMN 708 / 494 na tym samym teście i karcie)
- plan: profil `forward()` dla T=16–128 z `g_rec` (IK2_PROF), porównanie z presetem GodGMN (`IK2_PREFILL_WMMA`, `IK2_PREFILL_DENSE=2`, `IK2_EXPERT_TILE_LDS`); cel: koszt okna 96 tokenów ≤ 0,14 s; bramka: parytet 11/11 + `ik2_copy_edit.py` + rep2 czatu
- zysk: copy/edit do +60% [SZACUNEK z różnicy do GodGMN]
- ryzyko karty: niskie (ścieżka prefillu już używana)
- priorytet: wysoki dla agentów i edycji kodu

**TOPKA na teraz (właściciel 2026-11-19: „tylko najważniejsze”).** Kolejność niżej = kolejność pracy; reszta czeka bez terminu.
1. K-001 wyciek stanu po restore (poprawność produkcji; 19.11: hipotezy pamięci, hosta i kvq odpadły, następny zrzut logitów). 2. ~~K-125~~ zrobione 19.11: PASS, kvq bliżej f16 niż standardowy kernel. 3. K-013 szybsza weryfikacja kilku wierszy na RDNA3 i NVIDIA (największa dźwignia dekodu: XTX K-111 MMVQ weryfikacji 20,2 ms; NVIDIA V(5)/V(1) = 1,26–1,64, K-118). 3a. K-129 `DRAFT_N=2` w Enigmie dla Ampere i 5060 Ti (+3…8%). 4–5. K-007 → K-008 dynamiczna głębokość draftu (+3,9…4,8%, czeka na decyzję właściciela o bramce). 6. K-004 na NVIDIA (wymaga buildu forka z `7cdc0121b`); K-116 odrzucone 19.11.
- **wynik 2026-11-25 17:25–17:45 (XTX, `~/k134/wt-k148` k148-sfx, PM4=0, picks SFXBLK=32 SFXRG=16):** parytet greedy IDENTICAL 11/11 (vx, blk128 i reszta). Edycja kodu `python_edit` (936 → 886 tok., dokładnie): prod 292,4 / 292,8 → **both 334,1 / 334,0 t/s (+14,2%)**, rg 318, blk 315, vx 301, blk128 244 (gorzej). Czat bez zmian: Q6 114,1 → 113,9, L2k 107,7 → 107,0 (−0,6%, szum). Werdykt: **wygrany (both)**, do wdrożenia w Mai po wall.py `pl` (K-176). Log: `~/qwen-opt/queue/logs/k148-*.log`.
- przeniesione 2026-11-25: wygrany, wdrożenie K-176

### K-174 · Tokenizacja BPE bez alokacji (PR #32859) w topce: czas tokenizacji długiego promptu (CPU)
- data: 2026-11-25 (panel JARO; PR scalony 2026-11-24, `2a48778`; autor: qwen2 −49%)
- po co: serwer tokenizuje całą historię przy każdej turze agenta, także gdy prefill idzie z cache, więc przy 100k kontekstu to stały koszt TTFT
- test: CPU na jaroserverai (`~/tokbench`), llama-tokenize przed/po na słowniku Qwen, potem port do topki (łatka nie wchodzi czysto na qprep-spec: konflikt w `src/llama-vocab.cpp:15`)
- czas karty: 0
- **wynik 2026-11-25 (jaroserverai CPU, rdzenie 6–9, llama-tokenize, słownik Qwen3.8-27B-Uncensored, 400 KB tekstu wiki = 178 289 tokenów, 5 biegów, czas minus czas pustego pliku):** ID tokenów identyczne (md5 41dce45f…); przed 121 ms (120–125), po 102 ms (89–112), czyli **−16%, ok. 20 ms na 178k tokenów**, a nie −49% jak u autora (inny tekst: polski i kod). Przy turze agenta ze 100k historii to ok. 11 ms przy TTFT ok. 1,5 s (< 1%). Werdykt: brak osobnego wdrożenia, łatka wchodzi przy najbliższym rebase topki na upstream.
- przeniesione 2026-11-25: zysk poniżej progu 1%


### K-160 · Bonsai 2.5: kernel Q2_0 a pasmo DRAM (K-156 dał 1,9× w mikrobenchu i 0% w dekodzie)
- data: 2026-11-25 (MMVQ Q2_0 ok. 695 GB/s w całym kroku)
- plan: profil PM4-off z licznikami pamięci (rocprofv3 --pmc) na pełnym dekodzie; sprawdzić, czy limit to DRAM, czy kolejność/rozmiar kerneli; bramka: plain ≥ 85 t/s
- priorytet: średni
- wynik 2026-11-25 (`qwen-opt/bonsai25/k160-dram.sh`): MMVQ Q2_0 = 80,5% czasu GPU dekodu (11121 wywołań na 32 tokeny). Liczniki rocprofv3 (FETCH_SIZE, GL2C_EA_RDREQ_*, GL2C_HIT/MISS) na gfx1100 z ROCm core-10.0 zwracają 0 dla każdego kernela, więc bajtów z DRAM tą drogą nie zmierzymy. Odpowiedź daje mikrobench pełnego kroku (wszystkie macierze > 96 MB cache) agenta BonsaiMmvqBandwidth (ładowania nontemporal, 128-bit, więcej fal); zamknięte tutaj, kontynuacja tam.

### K-105 · Enigma NVIDIA: few-row MMQ (#31533) w naszym forku CUDA (szeroka weryfikacja: lookup W16, MTP n4)
- data: 2026-11-14
- źródło: K-103 ([[2026-11-14-k103-llamacpp-v1-nvidia]]): few-row MMQ daje +10…12% na przebieg przy 8–16 kolumnach, a przy MTP n2 (3 kolumny) ~0
- test: 5060 Ti w jaroserverai (gdy online) lub 3090 z wynajmu: b11856 vs v1.0.0, MTP n 3/4, spec_sweep T=1 ABBA; 24 GB z UD-Q4_K_XL n3
- stan po bramce K-103: przy MTP n2/n3 upstream v1.0.0 daje +3,8% / +0,6%, KLD ~2σ ponad szumem. Few-row MMQ opłaci się dopiero przy szerokiej weryfikacji (fork z lookupem W16, n4), więc sens ma port #31533 do naszego forka CUDA (bramka KLD vs fork), a nie zmiana pinu.
- zysk: +5…12% decode na NVIDIA przy szerokiej weryfikacji [SZACUNEK]
- ryzyko karty: brak
- priorytet: średni (zysk tylko w forku z szeroką weryfikacją)
- zamknięte 2026-11-25: zastąpione werdyktem K-013 (Q4_K szybsze przy każdym n).

### K-151 · Bonsai 2.5 w naszej topce: port `prism.hadamard` (runtime FWHT) z upstream do topka-q70 i PM4 replay
- data: 2026-11-25 (topka b11528 nie zna Hadamarda; upstream od b11556; PM4 dał Qwenowi +6,4%)
- plan: port `load_hparams_hadamard`/`load_tensors_hadamard` + graf qwen35, md5 greedy vs prism Q2_0, b25.sh z silnikiem topki
- zysk: PM4 + nasze MTP-lean, kilka–kilkanaście % [SZACUNEK]
- ryzyko karty: PM4 (zasady PM4)
- priorytet: średni
- **wynik 2026-11-25:** port do topki (c76335b) działa; PM4 + env produkcji: T=0,7 77,7 → 101,7–106,0; z kolejnymi łatkami 116,9. Zrobione.
- zamknięte 2026-11-25: port w topce (c76335b), topka-k157 T=0,7 116,9 t/s.

### K-150 · Bonsai 2.5: przerwa hosta 19% kroku dekodu (3,4 ms z 18,2 ms), HIP graphs + MTP w forku prism
- data: 2026-11-25 (profil rocprofv3: GPU 14,8 ms na token, zegar 18,2 ms)
- plan: sprawdzić, czy grafy działają przy MTP w prism na HIP (`GGML_HIP_GRAPHS`), profil hosta; ewentualnie fuzja FWHT + quantize_q8_1 (razem 7,2% GPU)
- zysk: do +10…19% [SZACUNEK]
- ryzyko karty: brak
- priorytet: średni
- **wynik 2026-11-25:** przyczyna przerw to ok. 1080 kerneli na token i fuzje tylko dla NVIDIA; prism + łatka Gemini +11,5% (77,6 → 86,5), topka + PM4 + K-150T + K-157: 70,6 → 76,9 bez spekulacji. Zrobione.
- zamknięte 2026-11-25: K-150 Gemini +11,5% w prism, przeniesione do topki (K-150T), topka-k157 76,9 t/s bez spekulacji.

### K-149 · Bonsai 2.5: kernel PTQ1_0 dla RDNA3 (n = 1–4 kolumny, ograniczony pasmem), żeby MTP działało na pliku 5,99 GB
- data: 2026-11-25 ([[bonsai-2-5-uncensored]]: PTQ1_0 na HIP 446–583 GB/s przy n=1 i 3,8× dłużej przy n=4; Q2_0 ma 7,3 GB na token)
- plan: dekodowanie trytów przez LUT (bajt → 5 trytów) w LDS, kolumny 1–4 w jednym przejściu wag; `test-backend-ops` MUL_MAT ptq1_0, potem b25.sh (prism ptq1 mtp 2) ABBA vs prism Q2_0 MTP n2
- zysk: wag o 21% mniej → do +15…20% dekodu przy T=0,7 [SZACUNEK]
- ryzyko karty: niskie (nowy kernel, bramka test-backend-ops)
- priorytet: wysoki dla Bonsai
- **wynik 2026-11-25:** kernel PT na HIP (agent) poprawny (255/255, 120/120, 85/85), 17408×5120 n=4 167 → 43 µs; prism PTQ1_0 MTP n2 T=0,7 33,8 → 75,9. W topce (K-153) PTQ1_0 102,4 vs Q2_0 105,0: zostaje Q2_0. Zrobione.
- zamknięte 2026-11-25: kernel PT 255/255 testów, ale w topce Q2_0 szybszy (K-153: T=0,7 102,4 vs 105,0), zostaje Q2_0.

### K-161 · `tools/perf` na topce i Mai: jedna komenda build → spill audit → oracle (md5 + KLD) → księga µs/token z rocprof → ABBA e2e
- data: 2026-11-25 ([[metoda-nib-level-up]], polecenie JARO „level wyżej”)
- plan: CPU: skrypt i spill audit (wzór `nib/scripts/spill_audit.sh`); XTX: jeden przebieg na topka-k157 (Bonsai) i Maya (Inkling), księga do notatek modeli; cel: wariant ≤ 1 h od pomysłu do liczby
- priorytet: najwyższy (proces)
- zamknięte 2026-11-25 jako proces: księga rundy w Mai (`IK2_K158_BENCH`), `tools/perf/sweep.sh`, `b25-ledger.sh`; spill audit Nib-style zostaje w [[perf]].

### K-162 · Profil Nib vs Maya kernel po kernelu (rocprofv3, ten sam prompt, KV q4) i księga µs/token obu
- data: 2026-11-25 (Nib T=0,7 130–151 vs Maya 112,5; bench Nib przy d=0 140,7 tok/s bez MTP wg nagłówka)
- plan: `nib bench -d 0,8192 -p 512 -n 128 --kv-type q4_0 --sparse-pages 0` i Maya gen pod rocprofv3; tabela etap → µs/token; wynik kieruje K-158
- czas: ok. 10 min karty
- zamknięte 2026-11-25: księga w [[nib-chromadera]] (Maya plain 127 > Nib 118; przewaga Nib = spekulacja).

### K-163 · Szybka pętla: przełączniki runtime w topce Bonsai + xtxbench z profilem modelu, cel ≥ 15 wariantów/h
- data: 2026-11-25 (JARO: „on robi eval w minuty, my w godziny”; [[metoda-nib-level-up]])
- plan: (1) zbudować topka-k157 + `topka-rtswitch.patch` (+ `rtswitch_convert.py` dla BZ16), test-backend-ops, koszt haka ABBA (K-028: 0); (2) xtxbench: profil serwera zamiast `run-topka.sh` (Bonsai, Inkling/Maya osobno); (3) sesja: 10 przełączników K-15x po kolei w jednym serwerze, zmierzyć minuty/wariant
- miara: minuty na wariant (dziś 30–45), warianty/h
- priorytet: najwyższy (proces)
- **wynik 2026-11-25 12:55:** `tools/perf/sweep.sh` na `~/wt/topka-rt` (hak + przełączniki runtime): 14 s na wariant zamiast 30–45 min, 10 wariantów w 2,5 min, bez fault; ablacja w [[perf]]. Zrobione; następnie: profil Mai i sito dla każdej nowej łatki.
- zamknięte 2026-11-25: sweep.sh 14 s/wariant (wynik wyżej).

### K-152 · Ternary Bonsai 2.5 27B Uncensored (AtomicChat) na XTX: pobrać i zoptymalizować (JARO 2026-11-24 23:37)
- wynik 2026-11-25: plik AtomicChat PTQ1_0 (SHA zgodne) + głowica MTP PrismML → PTQ1_0-mtp i bezstratny Q2_0-mtp; fork PrismML zbudowany na gfx1100; najlepiej **prism Q2_0 + MTP n2: T=0,7 77,7, T=0 117,9, L2k 97,5, L8k 92,6 t/s** (bez spekulacji 54,4; PTQ1_0 + MTP 33,8 przy T=0,7). Szczegóły i tabela: [[bonsai-2-5-uncensored]]. Dalej K-149, K-150, K-151.


### K-005 · Siatka checkpointów GDN co ~8192 tokenów + checkpoint w punkcie rozwidlenia + łańcuch fallbacku (edycja, regeneracja, kompaktowanie omp)
- data: 2026-10-15 (STATUS-NEXT §4), ponownie 2026-11-07 (66 poz. 6)
- źródło: [[siatka-checkpointow-gdn]], `Q/STATUS-NEXT.md:44`, `R/66-SYNTEZA.md:57`, `R/67c-nvidia-backlog-testow.md:116` (B22)
- test: najpierw implementacja w topce. XTX: replay prompt 60k → zmieniony koniec → rodzeństwo; `prompt_n`, TTFT, md5 vs zimny start (~1,5 min prefillu na ramię, ≤ 10 min).
- zysk: edycja ostatnich 10% promptu 60k: TTFT ~65 s → ~8–10 s [SZACUNEK]; ≥ 1 s/turę, gdy dojdzie do rozjazdu
- ryzyko karty: brak (~150 MiB RAM hosta na checkpoint)
- priorytet: wysoki (≥ 1 s/turę)

- wynik 2026-11-23 (bisekcja spadku prefillu po poprawce K-001, duet): pp2048 1021,8 → 981,6 (−3,9%); winne commity Gemini 5ff6a15 (−1,8%) i 0bb43ee (−1,5%); bank GDN 0/1 daje identyczne odpowiedzi (produkcja bez wpływu). Log `~/qwen-opt/queue/logs/duo-r14-*.log`.

- wynik 2026-11-23 15:09 UTC (r11 `LLAMA_CKPT_GRID=1`, produkcyjna konfiguracja, prompt 40k, edycja w 10% długości): wznowienie po edycji 74,1 → **19,4 s (−74%)**, tekst identyczny z liczeniem od zera (md5 równe); dopisek na końcu 2,09 → 2,18 s (w szumie); rozwidlenie 0,46 s. Kandydat do wdrożenia z poprawką K-001 (po naprawie spadku prefillu). Log `~/qwen-opt/queue/logs/duo-r13-k005-*.log`.
- przegląd 2026-11-24: zrobione wcześniej (r13 LLAMA_CKPT_GRID=1: wznowienie po edycji 40k 74,1 → 19,4 s (−74%), md5 równe (REKORDY.md:237, duo-r13-k005-on/off.log). Wdrożenie czeka na naprawę spadku prefillu K-001 (r14: winne commity 5ff6a15/0bb43ee): to decyzja o wdrożeniu, nie test | 0 | -)

### K-011 · Kontrola ewikcji VRAM do GTT przy 262k (`amd-evicted-vram`, `drm-memory-*` w fdinfo)
- data: 2026-11-07
- źródło: `R/68a-rdna3-kernele.md:123` (4.5), `R/68-SYNTEZA.md:24`
- test: doczepić do najbliższego fillu 255k: odczyt `/proc/<pid>/fdinfo/*` przed promptem, po prefillu i po 256 tokenach (0 dodatkowego czasu GPU)
- zysk: 0%, jeśli ewikcji nie ma; jeśli jest, decode przy 255k jest dziś zaniżony
- ryzyko karty: brak (odczyt)
- priorytet: średni (darmowe, może zaskoczyć)
- wynik 2026-11-20: serwer w konfiguracji produkcyjnej (ctx 262144, port testowy). Fill 131 000 tokenów zamiast 255k, bo 255k to ~548 s samego prefillu, a limit testu to 10 min. **Ewikcji brak**: `amd-evicted-vram` = 0 KiB we wszystkich trzech odczytach. VRAM 22,39 GiB przed promptem → 22,74 GiB po prefillu (650 t/s, 201 s) → 22,78 GiB po 256 tokenach (134 t/s). GTT stoi na ~6,1 MiB. Log: `~/qwen-opt/queue/logs/k011-fdinfo.log`, skrypt `qwen-opt/k011/fdinfo.sh`
- przegląd 2026-11-24: zrobione wcześniej (Ewikcji brak: amd-evicted-vram 0 KiB we wszystkich 3 odczytach przy fill 131k, VRAM 22,39 → 22,78 GiB, GTT ~6 MiB (log k011-fdinfo.log jest na boxie) | 0 | -)

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
- przegląd 2026-11-24: zrobione wcześniej (2026-11-20 kern.sh/k013-kern.log: our Q4_K is faster at every n (−9…−33%); few-row wins only Q6_K n≤2. Verdict: full few-row not taken. The Q6_K n≤2 remainder already went into duo (GGML_HIP_MMVQ_Q6FR in duo-r7). | 0 | -)

### K-029 · xtx-eco: odczytywać fabryczny `OD_SCLK` przy każdym boocie przed pierwszym zapisem OD (stock zmienia się między bootami: 2885 vs 2935 MHz)
- data: 2026-11-06
- źródło: [[2026-11-06-xtx-eco-instalacja]] (`:12-13`, „poprawka w toku — status do sprawdzenia”), [[raport-64-termika]]
- test: XTX bez obciążenia: po restarcie porównać `pp_od_clk_voltage` z zapisanym stanem bootu, sprawdzić krzywą wentylatora (`pwm1`/RPM); ≤ 10 min
- zysk: 0 t/s; „powrót do stock” nie obniża już limitu o 50 MHz (zasada: karta fabrycznie)
- ryzyko karty: zapis OD na jądrze 6.8 gubi krzywą wentylatora, więc pilnować temperatur
- priorytet: średni (bezpieczeństwo ustawień fabrycznych)
- wynik 2026-11-20 (bez restartu, odczyt bieżącego bootu 13:32): stan zapisany przy starcie `/run/xtx-eco/stock` = 2940 MHz. To trzecia różna wartość fabryczna (2885, 2935, 2940), więc poprawka „odczyt przy każdym boocie” jest potrzebna i działa (`xtx-od.sh` zapisuje stock do `/run` przed pierwszym zapisem). `OD_SCLK 1` = 2200 MHz (limit eco), `power1_cap` 285 W. Krzywa wentylatora jest zapisana (`fan_curve` 25–80 °C → 100%), ale w spoczynku (hotspot 45 °C) `pwm1` = 0 i 0 RPM, czyli tryb zero-RPM. Pod obciążeniem nie sprawdzano. Log: `~/qwen-opt/queue/logs/k029-od.log`
- przegląd 2026-11-24: zrobione wcześniej (Result line of 2026-11-20 in the queue: stock is read at every boot into /run/xtx-eco/stock (2940 MHz, the third distinct value after 2885/2935), so the fix works; OD_SCLK1 = 2200, cap 285 W, fan_curve is set, idle is zero-RPM. Log ~/qwen-opt/queue/logs/k029-od.log. Fan under load was not checked an)

### K-031 · Maska KQ poza ścieżką krytyczną albo pochodna maska w kernelu (bez `n_kv × n_tokens` z hosta)
- data: 2026-10-13 (K3), 2026-11-07 (66 #9, 68c #4)
- źródło: [[maska-kq-host-dlugi-ctx]], [[2026-11-08-kvq-once-profil]] (`:50,89`: `graph→inputs` 355 µs przy 199k), `R/68c-dlugi-kontekst-gdn.md:15-17,138`
- test: XTX `LLAMA_HOSTGAP_TRACE=16` + xtxbench decode 199k ABBA, md5 (osobny job na 199k)
- zysk: decode 199–255k +0,5…1,5%, fill 255k +0…3%, −256 MiB VRAM i −256 MiB pinned [SZACUNEK]
- ryzyko karty: brak (host); wariant w kernelu = nowy kernel w PM4
- priorytet: niski (sam poniżej progu, łączyć z K-012)
- wynik 2026-11-21: **maska leży na ścieżce krytycznej, ale zdjęcie jej daje tylko ~0,4% przy 94k i ~0,8% przy 199k, poniżej progu.** Ślad hosta `LLAMA_HOSTGAP_TRACE=16`, konfiguracja produkcyjna na porcie testowym, jedno zimne żądanie na głębokość (T=0, 256 tok.). Ramię A to produkcja (szybka maska). Ramię B to `LLAMA_KV_MASK_FAST=0`, czyli celowo wolniejsza maska jako sonda: jeśli krok rośnie o tyle, o ile rośnie budowa maski, to maska blokuje GPU. Przy 94k (ABBA): `graph→inputs` A 136 µs, B 396 µs (+260 µs); ściana kroku 32,83 → 33,07 ms (+0,24 ms, prawie 1:1); decode 120,95 → 119,98 t/s (−0,8%). Przy 199k (jedna para A/B, wypełnienie 360 s): `graph→inputs` A 303 µs, B 909 µs; ściana 37,77 → 38,67 ms; decode 95,05 → 93,08 t/s (−2,1%). Przy 1,7k budowa maski kosztuje ~40 µs i A = B. md5 identyczne w obu ramionach (94k `3f0651b0`, 199k `efdb8053`, to samo co w [[2026-11-08-kvq-once-profil]]). Zysk z przeniesienia maski poza ścieżkę krytyczną to najwyżej czas maski w A: 136 µs na 32,8 ms (0,4%) i 303 µs na 37,8 ms (0,8%). Priorytet zostaje niski, łączyć z K-012. Źródło: `~/qwen-opt/queue/logs/k031-{A1,B2,B3,A4,199A,199B}.log`, skrypt `Q/k031/k031.sh`.
- przegląd 2026-11-24: zrobione wcześniej (Result line of 2026-11-21: the mask is on the critical path, but removing it gives only ~0.4% at 94k (step 32.83→33.07 ms, 120.95→119.98 t/s with the slow-mask probe) and ~0.8% at 199k (95.05→93.08 t/s probe). Below threshold, merge into K-012. Logs: queue/logs/k031-{A1,B2,B3,A4,199A,199B}.log. | 0 )

### K-032 · Amplifikacja odczytu KV w `kvq` (bajty z liczników vs 1152 B/token/warstwę)
- data: 2026-11-07
- źródło: `R/68a-rdna3-kernele.md:124` (4.6), [[2026-11-08-kvq-once-profil]] (`:77`, `FETCH_SIZE` = 0)
- test: XTX `rocprofv3 --pmc TCC_EA_RDREQ_sum TCC_EA_RDREQ_32B_sum` na `llama-bench -fa 1 -ctk q4_0 -ctv q4_0 -p 5 -ub 5 -d 131072`, `GGML_HIP_PM4=0`; ≤ 10 min
- zysk: 0…3% decode przy ≥ 128k [INFERENCE]; zasila K-012
- ryzyko karty: brak
- priorytet: niski (diagnostyka)
- wynik 2026-11-20: **liczniki nie działają.** Na gfx1100 nie ma `TCC_EA_RDREQ_*` (rocprofv3: „Missing”). Ich odpowiedniki `GL2C_EA_RDREQ_{32,64,96,128}B_sum` dają 0 we wszystkich 4160 dispatchach (to samo co `FETCH_SIZE` = 0 w [[2026-11-08-kvq-once-profil]]), więc bajtów z liczników nie da się dziś zmierzyć. Wynik zastępczy z czasów rocprofv3 (`llama-bench pp5 @ d131072`, produkcyjna `~/llama-topka`, PM4 0, fill z `-ub 512`): `flash_attn_ext_kvq<256,8,q4_0>` mediana 408 µs na warstwę + combine 4 µs, pp5 99,9 t/s. Przy 1152 B/token/warstwę × 131072 = 151 MB to ~370 GB/s efektywnie, około 39% z 960 GB/s. Pod profilerem dispatche idą szeregowo, więc to szacunek. Amplifikacji z tego nie da się oddzielić od niskiej zajętości kernela. Log: `~/qwen-opt/queue/logs/k032-rdreq2.log`, skrypt `qwen-opt/k032/rdreq.sh`
- przegląd 2026-11-24: zrobione wcześniej (Result line of 2026-11-20: TCC_EA_RDREQ_* is "Missing" on gfx1100 and GL2C_EA_RDREQ_* reads 0 in all 4160 dispatches, so amplification cannot be measured with counters. Proxy: kvq<256,8,q4_0> 408 µs/layer @131k ≈ 370 GB/s (39% of peak); pp5 99.9 t/s. Logs: k032-rdreq{,2}.log. Further work only via K)

### K-033 · Diagnoza FCLK/MCLK pod obciążeniem, stock vs eco (tylko odczyt `pp_dpm_*`)
- data: 2026-10-12
- źródło: `R/68a-rdna3-kernele.md:122` (4.4), §2.9
- test: pętla `grep '\*' pp_dpm_{sclk,mclk,fclk}` co 0,25 s doczepiona do najbliższego spec_sweep (0 dodatkowego czasu)
- zysk: 0% sam; wyjaśnia, czy −1,9% decode na eco to fabric
- ryzyko karty: brak (odczyt)
- priorytet: niski (darmowa diagnostyka)
- wynik 2026-11-21 (tylko eco, zegarów nie zmieniamy, więc ramienia stock nie ma): **pod obciążeniem pamięć i fabric stoją na najwyższych poziomach, które faktycznie są używane.** Pętla `dpm_poll.sh` (co 0,25 s, sam odczyt sysfs) chodziła przy 9 jobach: decode 1,7k/94k/199k, prefill 12k/94k/199k, pp4096, LFM pN. Próbki z `gpu_busy` ≥ 50%: MCLK 1249 MHz (najwyższy poziom) w 88–100% próbek, FCLK 2000 MHz w 88–100%, a poziomy 2201–2301 MHz w 0–5%. SCLK mediana 2183–2187 MHz (sufit eco 2200). Spadki do 772 MHz MCLK i 1200 MHz FCLK (0–12%) wypadają na krótkie przerwy między żądaniami. Pamięć nie jest dławiona na eco. Czy −1,9% decode na eco to FCLK 2000 zamiast 2301, rozstrzygnie dopiero odczyt na stocku przy okazji, gdy karta i tak będzie na stocku (sami nie przełączamy). Źródło: `~/qwen-opt/queue/logs/k048-*.log`, `k031-*.log`, `k045-g1.log`, skrypty `Q/k033/dpm_poll.sh`, `dpm_sum.py`.
- przegląd 2026-11-24: zrobione wcześniej (Result line of 2026-11-21 (eco arm): under load MCLK 1249 is at 88–100% and FCLK 2000 at 88–100%, SCLK median 2183–2187, so there is no memory throttling on eco. The stock arm is not allowed by the owner's factory-settings rule; read it opportunistically if the card is ever on stock. | 0 | –)

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
- przegląd 2026-11-24: zrobione wcześniej (Result line of 2026-11-20: XTX `-lv 4` (k034/bufs.py, 64k→128k) gives target compute 420.29→740.29 MiB = +5.0 KiB/token (f16 K/V copy ~4 KiB + mask ~1 KiB); the MTP draft compute is a flat 40.28 MiB, so lean-reserve works. The remaining ~1 GiB @262k moves to K-022. Log k034-bufs.log. | 0 | –)

### K-039 · Q5_K MMVQ `big_rows` (`GGML_HIP_MMVQ_Q5K_BIG_ROWS=6144`): dokończyć ABBA i sprawdzić env w produkcji
- data: 2026-10-20 (raport 50b)
- źródło: [[raport-50b-mmvq-q5k]], `R/43-integracja-2026-10-20.md:68`, archiwum (`A:36426`: „brakuje 2 z 4 ramion”, md5 PASS)
- test: XTX `~/qwen-opt/queue/i43-int7.jobs` od `i43g-B1b` (2 ramiona × ~2,5 min)
- zysk: kernel −1,3…−3,5%, ~+0,4% decode
- ryzyko karty: brak
- priorytet: niski (poniżej progu, łączyć)
- wynik 2026-11-20: dokończone ramiona B1b i A1b z `i43-int7.jobs`, po nowej bramce md5 (qwen i lfm PASS). Uwaga: A1a/B1a są z 2026-10-21, a B1b/A1b z dzisiaj, i dzisiejsza para jest o ~1,7% wolniejsza w obu ramionach. Proza (T=1): A = (79,86 + 78,59)/2 = 79,23 → B = (79,99 + 78,55)/2 = 79,27 t/s (+0,06%). mvs (T=0): 433,2 → 433,4 t/s (+0,06%). W parach z tej samej sesji: 10-21 +0,16% / +0,09%, 11-20 −0,05% / +0,02%. Zysku nie widać ponad szum, więc nie włączać do produkcji. W produkcji tej zmiennej nie ma: brak `BIG_ROWS` w `run-topka.sh` i `run-llm.sh`. Logi: `~/qwen-opt/queue/logs/i43g-{A1a,B1a}.log`, `k039-i43g-{B1b,A1b}.log`, jobs `qwen-opt/k039/xq.jobs`
- przegląd 2026-11-24: zrobione wcześniej (Result line of 2026-11-20: all 4 ABBA arms are done, md5 PASS (qwen, lfm). Prose 79.23→79.27 t/s (+0.06%), mvs 433.2→433.4 (+0.06%), within noise, so it does not go to production. BIG_ROWS is absent from run-topka.sh/run-llm.sh. Logs k039-i43g-{B1b,A1b,md5-*}.log, i43g-{A1a,B1a}.log. | 0 | –)

### K-041 · Licznik realokacji grafu (#30329): czy przejścia MTP5 ↔ W16 ↔ catch-up przebudowują graf albo taśmę PM4
- data: 2026-11-07
- źródło: `R/68d-swieze-od-spolecznosci.md:141` (#7)
- test: XTX serwer testowy, replay sesji agenta, licznik w logu + `GGML_HIP_PM4_DEBUG`; ≤ 10 min
- zysk: 0% wprost; kilka % na krokach zmieniających szerokość, jeśli realokacje istnieją [INFERENCE]
- ryzyko karty: brak
- priorytet: niski (diagnostyka)
- wynik 2026-11-20: serwer produkcyjny (PM4 WA=2 + GUARD) z `GGML_HIP_PM4_DEBUG=1`. Replay agentpath `w6.json`: 4 sesje po kolei, 24 tury, 98,9k tokenów prefillu, 3k wygenerowanych, 140 s. Taśm budowanych jest 81 na 967 uruchomień taśmy (każda użyta średnio ~12 razy), czyli ~3,4 przebudowy na żądanie. **Rozmiary są zawsze tylko dwa: 809 i 107 dispatchy**, więc szerokości MTP / W16 / catch-up nie tworzą nowych taśm. Przebudowy to ponowne przechwycenie tych samych dwóch grafów, prawdopodobnie po każdym prefillu [INFERENCE]. Do tego 77 małych grafów (12–14 kernel) idzie zwykłą ścieżką HIP graph, 518 uruchomień grafu bez taśmy, 13 eksmisji kolejki (0 w trakcie taśmy). Następny krok, jeśli warto: zmierzyć koszt jednej przebudowy (ms) × ~3,4 na żądanie. Log: `~/qwen-opt/queue/logs/k041-realloc2.log`, `~/qwen-opt/k041/out/launch.log`
- przegląd 2026-11-24: zrobione wcześniej (2026-11-20 result in the queue entry: 81 tapes per 967 launches; only 2 sizes (809 and 107 dispatches), so MTP/W16/catch-up widths create no new tapes; 13 evictions. Logs `k041-realloc.log`, `k041-realloc2.log` | 0 | –)

### K-044 · Leave-one-out łatek (`loo.py run`) i Kernel Tuner (`kt tune`) na GPU
- data: 2026-10-15 (runda 6)
- źródło: [[runda-6]], [[loo]], `Q/STATUS-NEXT.md:31-37`, `R/07-nasze-metody-uogolnienie.md:250-252`
- test: XTX `GGML_HIP_PM4=0`, po jednej łatce/fladze na job (xtxbench ~4 min); LOO ~3,8 h + buildy w sumie
- zysk: 0 t/s wprost; wykrywa łatki bez zysku (koszt utrzymania)
- ryzyko karty: niskie (mikrobenche)
- priorytet: niski (higiena)
- wynik 2026-11-21 (częściowo: tylko łatki z wyłącznikiem env, bez łatek „tylko build” i bez `kt tune`): **żadna łatka nie daje ≥ 3% na Qwenie, ale prawie wszystkie mierzalnie pomagają. Kandydaci do usunięcia: 52, 58 i 59 (Qwen), 62 i 64 (LFM).** Narzędzie `loo.py` zostało bez zmian; owijka `Q/k044/loo_topka.py` puszcza te same próby (ABBA) na silniku produkcyjnym `~/llama-topka` z kolejki, bez zagnieżdżonego flocka, port testowy, PM4 0. Qwen UD-Q4_K_XL, tg128 + serwer MTP n4 (2 prompty × 256 tok., T=0), 4 rundy. Spadek po wyjęciu łatki (95% CI) w serwerze: 31 top-k −2,72%, 33 replay GDN −1,58%, 29 asynchroniczne wejścia −1,45%, 24 para MMVQ −1,30%, 47 −1,23%, 28 −0,92%, 25 −0,91%, 30 −0,82%, 27 −0,65%, 38 −0,40%, 26 −0,28%. Neutralne: 48 (0,00%), 58 (+0,13% / tg +0,04%), 59 (−0,06% / tg −0,19%). Szybciej bez łatki: 52 (`GGML_HIP_MMVQ_N1_ROWS`) tg +1,31% ± 0,11, w serwerze +0,29% (neutralnie). LFM2.5-24B, 2 rundy, szerokie CI: najwięcej dają 48 (−13,7%), 31 (−12,2%), 50 tg (−9,4%), 53 tg (−6,7%), 29 (−6,0%), 49 tg (−5,3%), 51 (−4,5%). Szybciej bez łatki: 62 tg +0,39% i 64 tg +0,79%, w serwerze neutralnie. Pominięte: 60 (to sam PM4, a punkt odniesienia jest z PM4 0), 65 (flaga web UI, w produkcji i tak wyłączona), CLI 4 i 32 oraz 22 łatki „tylko build” (wymagają buildów z revertem, czyli pracy nad kodem). Decyzja o usuwaniu łatek należy do właściciela. Źródło: `~/qwen-opt/queue/logs/k044-*.log`, raport `~/qwen-opt/k044/loo/loo-report.md`, wyniki `loo-results.jsonl` (316 prób, 0 błędów).
- przegląd 2026-11-24: zrobione wcześniej (Partial result 2026-11-21: no patch gives ≥3% on Qwen. Removal candidates: 52, 58, 59 (Qwen) and 62, 64 (LFM). Logs `k044-*.log` (24 files). Not done: build-only patches and `kt tune` (each needs a rebuild per patch, XTX-NEEDS-BUILD, ~3.8 h; low value) | 0 | –)

### K-045 · Model kosztu weryfikacji MoE LFM2.5 (pomiar G1) i drafter dla LFM (LFM2.5-2.6B-QAD-Q4_0 jest na dysku)
- data: 2026-10-19 (raport 18), drafter 2026-10-14
- źródło: [[model-kosztu-weryfikacji-moe]], [[raport-24d-lfm-lookup]], archiwum (`A:36446`)
- test: XTX `llama-bench -p 1,2,3,4,5,8,16 -n 0 -d 0,32768` (bramki T(8) ≤ 13,6 ms, T(3) ≤ 6,8 ms); potem LFM24B + draft 2.6B spec_sweep T=1 + `mvs`; ≤ 10 min każdy
- zysk: decyduje, czy tani drafter dla LFM ma sens (od α ≈ 0,4); LFM poza produkcją
- ryzyko karty: VRAM (+1,6 GB draftera przy KV q8_0 131k)
- priorytet: niski (LFM poza produkcją)
- wynik 2026-11-21: **bramka G1 na surowym `llama-bench` niespełniona; po odjęciu narzutu ścieżki pN spełniona tylko przy d0.** Build `~/llama-topka`, LFM2.5-24B-A2B Q5_K_M, KV q8_0, PM4 0. Surowe T(N) = N / t/s przy d0: T(1) 7,56, T(2) 8,42, T(3) 8,86, T(4) 8,93, T(5) 13,18, T(8) 15,09, T(16) 20,94 ms. Przy d32768: 6,53 / 8,90 / 10,03 / 10,77 / 15,15 / 17,12 / 23,50 ms. Bramki T(3) ≤ 6,8 i T(8) ≤ 13,6 ms padają w obu głębokościach. Ścieżka pN ma stały narzut: ten sam build daje tg128 239,6 t/s (4,17 ms na token) przy d0 i 217,3 t/s (4,60 ms) przy d32768, a p1 7,56 i 6,53 ms. Po odjęciu tej różnicy: przy d0 T(3) ≈ 5,5 ms (model 5,47) i T(8) ≈ 11,7 ms (model 9,58), obie bramki spełnione; przy d32768 T(3) ≈ 8,1 i T(8) ≈ 15,2 ms, obie niespełnione. Wyraźny skok między 4 a 5 kolumnami (+4,3 ms) wskazuje, że od 5 kolumn działa inny kernel [INFERENCE]. Jeśli drafter, to najwyżej 3 tokeny draftu (weryfikacja 4 kolumn). Drugiej części testu (LFM24B + drafter 2.6B, spec_sweep) nie uruchamiałem: bramka nie przeszła jednoznacznie, a LFM jest poza produkcją. Źródło: `~/qwen-opt/queue/logs/k045-g1.log`, `k045-tg.log`, skrypt `Q/k045/k045.sh`.
- przegląd 2026-11-24: zrobione wcześniej (2026-11-21: G1 fails on raw numbers (d0 T(3) 8.86 ms, T(8) 15.09 ms) and passes only at d0 after subtracting the pN overhead (T(3) ≈ 5.5, T(8) ≈ 11.7). Logs `k045-g1.log`, `k045-tg.log`. The drafter stage was not run; LFM is outside production | 0 | –)

### K-051 · Wyjaśnić ~16 tys. wierszy `amdgpu: init_user_pages: Failed to get user pages: -1` przy każdym starcie serwera
- data: 2026-11-06
- źródło: [[init-user-pages-failed]]
- test: XTX dwa starty serwera `--mmap` vs `--no-mmap`, licznik wierszy w `journalctl -k`, bez obciążenia; ≤ 10 min
- zysk: diagnostyka (krótszy start, czystszy log jądra); 0 t/s
- ryzyko karty: brak
- priorytet: niski (diagnostyka)
- wynik 2026-11-20 (`journalctl -k` działa bez sudo): start serwera produkcyjnego na porcie testowym. `-lm mmap` (domyślne `auto` = mmap) daje **15 553** wiersze `init_user_pages: Failed to get user pages`, a `-lm none` (bez mmap) **0**. Start do health w obu wariantach 5–6 s. Wiersze pochodzą więc z mapowania pliku modelu przez mmap. Para jest jedna: powtórka nie zmieściła się w 10 min, bo liczenie `journalctl` po długim boocie jest wolne. W topce flaga to `-lm`, nie `--no-mmap`. Log: `~/qwen-opt/queue/logs/k051-mmap2.log`, skrypt `qwen-opt/k051/mmap.sh`
- przegląd 2026-11-24: zrobione wcześniej (2026-11-20: mmap gives 15 553 `init_user_pages` lines, `-lm none` gives 0; start 5–6 s in both. Log `k051-mmap2.log`. Cause explained | 0 | –)

### K-053 · Wspólne punkty odniesienia: zestaw YASAKANI/NInfer (12 zadań + edycja) na XTX
- data: 2026-11-05
- źródło: `R/63-SYNTEZA.md:104` (#25), `R/63a-silniki-lokalne.md` §9
- test: XTX ~15 min (2 joby)
- zysk: wiedza i porównanie 1:1 z innymi silnikami; 0 t/s
- ryzyko karty: brak
- priorytet: niski (wiedza)
- wynik 2026-11-21: **12 zadań NInfer zmierzone, edycji YASAKANI nie ma na dysku.** Zestaw: 12 scenariuszy z `examples/cli/manifest.json` klonu NInfer (kod, proza, tłumaczenie, dane strukturalne po 3). Ustawienia jak u YASAKANI: greedy, thinking off, limit 4096 tokenów, bez cache promptu. Konfiguracja produkcyjna (MTP n4, lookup W16) na porcie testowym. Ich edycja kodu (`textwrap`) i JSONL 300 zamówień są prywatne, więc ich nie ma. Dekod w t/s, licząc jak YASAKANI, czyli (tokeny − 1) / czas generacji: kod 150,2 / 157,4 / 141,6, dane JSONL 190,8 / CSV 142,6 / SQL 169,3, proza EN 140,9, proza ZH 64,7 i 46,4, tłumaczenie ZH→EN 127,2, EN→ZH 68,9, markdown 76,6. Mediana z 12 zadań to 141,3 t/s. Dla porównania YASAKANI JSONL 160 wierszy daje ~455 t/s po przeliczeniu na pasmo XTX i bajty wag (`R/63a-silniki-lokalne.md` §9), a my na JSONL 190,8. Słabe są zadania z chińskim tekstem: akceptacja draftu 18%, 6% i 21% wobec 62–76% w kodzie i danych. Prawdopodobna przyczyna to okrojony słownik głowicy draftu (65 536 tokenów) [INFERENCE]. Źródło: `~/qwen-opt/queue/logs/k053-a.log`, `k053-b.log`, skrypt `Q/k053/k053.py`.
- przegląd 2026-11-24: zrobione wcześniej (2026-11-21: 12 NInfer scenarios, median 141.3 t/s (code 141.6–157.4, JSONL 190.8, ZH prose 46.4–64.7). The YASAKANI edit set is private, so it is missing. Logs `k053-a.log`, `k053-b.log` | 0 | –)

### K-054 · EvalPlus z `--effort xhigh` vs `low`: czy effort low kosztuje dokładność
- data: 2026-11-09
- źródło: [[2026-11-09-evalplus-qwen-uncensored]] (`:25`), [[evalplus-jakosc-kodu]]
- test: XTX `~/qwen-opt/evalplus/jakosc-mini.sh --effort xhigh --port 8097 all` (HE+ 164 + MBPP+ 378; > 10 min, podzielić po zbiorze)
- zysk: jakość, nie prędkość; potwierdza albo zmienia domyślny effort low (dziś HE+ 92,7%, MBPP+ 80,2%)
- ryzyko karty: brak
- priorytet: niski (nie prędkość)
- wynik 2026-11-21 (częściowo: HE+ 130 ze 164 zadań, MBPP+ 98 z 378; 10 jobów po ≤ 10 min, codegen wznawiany): **xhigh nie poprawia dokładności, a kosztuje ~3,7× więcej tokenów, więc domyślne low zostaje.** Konfiguracja produkcyjna na porcie testowym, `EFFORT=xhigh`. Porównanie z przebiegiem low z 2026-11-09 na tych samych zadaniach. HumanEval+ plus: 94,6% (123/130) → 93,8% (122/130), base 97,7% → 94,6%. MBPP+ plus: 85,7% → 85,7% (84/98), base 95,9% → 95,9%. Między ramionami przechodzi inny zestaw zadań: 7 zadań zmienia wynik w HE, 10 w MBPP. Tokeny na odpowiedź: HE 730 → 2637, MBPP 613 → 2386. Przy xhigh 4 odpowiedzi HE i 3 MBPP dobiły do limitu 32 768 tokenów. Dekod 134–135 t/s. Źródło: `~/qwen-opt/queue/logs/k054-*.log`, `~/qwen-opt/evalplus/runs/uncensored-xhigh/`, `uncensored-xhigh-pad/`, skrypty `Q/k054/k054.sh`, `k054_cmp.py`.
- przegląd 2026-11-24: zrobione wcześniej (2026-11-21 (partial: HE+ 130/164, MBPP+ 98/378): xhigh does not improve accuracy (HE+ 94.6 → 93.8%, MBPP+ 85.7 → 85.7%) and costs ~3.7× tokens → keep low. Logs `k054-gen*.log`, `k054-mbpp*.log`. Finishing the remaining tasks is pointless | 0 | –)

### K-055 · Usunąć z topki martwy kod capu LDS FA (`57204db1e`, no-op na ROCm 10.0 pre4) przy najbliższym buildzie
- data: 2026-11-06
- źródło: [[2026-11-05-q63-topka]] (wynik negatywny), dawny wpis `DO-ZAPISANIA.txt`
- test: przy następnym buildzie produkcji bramka md5 (long 32k e460e3b6, fill 255k 31b6525a); bez osobnego okna GPU
- zysk: 0 (porządek w kodzie)
- ryzyko karty: brak
- priorytet: niski (przy okazji)
- wynik 2026-11-20: usunięte w `llama-duo` (gałąź `duo`), commit `e1f9524` = czysty revert `57204db1e` (tylko `ggml/src/ggml-cuda/fattn-common.cuh`, −53 linie, ani `GGML_HIP_FA_OCC_*`, ani skrypty uruchomieniowe go nie używały). Bez buildu; bramka md5 (long 32k e460e3b6, fill 255k 31b6525a) przy najbliższym buildzie produkcji.
- przegląd 2026-11-24: zrobione wcześniej (2026-11-20: removed in `llama-duo` commit e1f9524 (revert of 57204db1e). The md5 gate (long 32k e460e3b6, fill 255k 31b6525a) runs with the next production build and needs no separate GPU slot | 0 | –)

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
- przegląd 2026-11-24: zrobione wcześniej (GEMM f16 4096³ 91,3 / 8192³ 98,1 TFLOPS, D2D 385 GB/s (log k108-gemm.log jest na boxie). Zostało tylko przeliczenie ceiling-qwen27b-unc-xtx.json, praca na CPU | 0 | -)

### K-128 · Czy klient (omp) obcina `<think>` z historii i przez to psuje trafienia prompt-cache w turach agenta (analiza logów, bez karty)
- data: 2026-11-19
- źródło: audyt Gemini (H.9) i [[zwiad-2026-11-14]] (TensorFold: „[INFERENCE: sprawdzić na surowych logach omp]”)
- test: CPU: surowe logi serwera/omp z sesji agentowych (`~/kernel/archiwum`, logi topki, gdy jaroserverai online): `cache_n` vs `prompt_n` per tura, czy prefiks rozjeżdża się na granicy bloku myślenia
- miara: udział tokenów promptu z cache per tura; jeśli dziury > 10% → poprawka po stronie szablonu/serwera
- zysk: TTFT tur agenta (jeśli problem istnieje); 0 t/s dekodu
- ryzyko karty: brak
- priorytet: średni
- wynik 2026-11-20: problemu nie ma. Logi serwera z jaroserverai (`qwen-opt/logs/server-*.log`, 264 pliki, 964 tury), skrypt `qwen-opt/k128/cache_hits.py`. Całość: 48,4 mln tokenów promptu, z cache 90,1%. W 386 turach agenta, w których rozmowa urosła i prefiks został w slocie, cache pokrył 99,2% promptu, a historia rozjechała się łącznie na 14 tokenach. Odpowiedź poprzedniej tury (z blokiem myślenia) wróciła w prompcie w 89,7% tokenów: 347 tur > 90%, 29 częściowo, 10 wcale, więc omp nie wycina `<think>` w sposób, który psuje cache. 66 tur „rozjechanych” to w 47 przypadkach przeskok do innej rozmowy z tym samym początkiem (wspólny prefiks stoi na ~7650 tokenach, czyli system + narzędzia; podagenci na jednym slocie), nie granica myślenia. Dziury < 10%, poprawka szablonu niepotrzebna. [INFERENCE: logi mają tylko `f_keep`, nie surowy tekst promptu.]
- przegląd 2026-11-24: zrobione wcześniej (Problemu nie ma: 964 tury, 90,1% promptu z cache, tury agenta 99,2%, odpowiedź z <think> wraca w 89,7% (qwen-opt/k128/cache_hits.py, wynik w kolejce 2026-11-20) | 0 | -)

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
- przegląd 2026-11-24: zrobione wcześniej (r15 gate done 2026-11-24 01:47 (ink-r15-tg.log: base 49.84, r13 56.94, r14 58.09). Result per log.md: r15 +1–3% plus a ctl bug. Production Inkling = Maya. Next step is Gemini round r16b (hit the 429 limit), which needs a build. | 0 | -)

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
- przegląd 2026-11-24: zrobione wcześniej (Maya 1.1.73 on XTX: T=0.7 80.7 → later 104.3/113.2 in production. Strata 0.1.66 page-faulted, so no repeat. Logs k134-maya.log, k134-strata.log. | 0 | -)

### K-135 · Maya Inkling na XTX: `GPU_MAX_HW_QUEUES=2` (vllm-redshift: R9700 37,8 → 59,9 t/s)
- data: 2026-11-23 (zwiad; repo abhinand5/vllm-redshift łatka 0101)
- test: XTX, Maya `ik2` produkcyjna konfiguracja (bez cenzury, KV q4, kernele HIP) z i bez `GPU_MAX_HW_QUEUES=2`, rep2 mediana 5 (Q1, Q6 T=0,7, L2k, prefill); ≤ 10 min, tekst bit w bit
- oczekiwany zysk: kilka–kilkanaście % (u nas ~777 launchy, przerwa ~2 µs/launch) [INFERENCE]
- ryzyko karty: brak (zmienna runtime)
- priorytet: wysoki (najtańsza droga do >100 t/s)
- wynik 2026-11-23 13:52–13:58 UTC (ABBA, rep2 mediana 5): bez → z `GPU_MAX_HW_QUEUES=2`: Q6 T=0,7 94,5 / 94,5 → 94,5 / 94,5; L2k 93,3 / 93,6 → 93,5 / 93,6; Q1 93,8 → 93,8–94,0; prefill bez zmian → **0%, odrzucone** (na RDNA3 nie ma kary przełączania kolejki, którą łatka 0101 leczy na RDNA4). Log: `~/qwen-opt/queue/logs/k135-*.log`.
- przegląd 2026-11-24: zrobione wcześniej (2026-11-23 ABBA: `GPU_MAX_HW_QUEUES=2` gives 0% (T=0.7 94.5/94.5) and was rejected. Logs ~/qwen-opt/queue/logs/k135-*.log. | 0 | -)

### K-136 · Maya v1.1.75 na XTX: drafter DSpark GGUF w grafie + próbkowanie Gumbel-max (3090: nowy kod 124 → 201 t/s)
- data: 2026-11-23 (link JARO, panel 19:04)
- test: stock v1.1.75 `--drafting auto` i `on` z `dspark-Inkling-2-Mini-Q8_0.gguf` vs nasza produkcja (1.1.73 + hipx14), ten sam rep2 i xbench T=0,7; potem nasze łatki przeniesione na 1.1.75
- oczekiwany zysk: przy T=0,7 drafter u nas przegrywał (79 vs 94); krótsze okno (−30%) i wspólny szum mogą to odwrócić [INFERENCE]
- ryzyko karty: brak nowych kerneli naszych; build stock
- priorytet: wysoki
- **wynik 2026-11-24 02:02–02:07 UTC (XTX, unsloth + ablacja, rep2):** produkcja 1.1.73 Q1/T=0,7/L2k 118,3 / 104,3 / 100,2; 1.1.75 + nasze łatki: lookup 118,1 / 103,9 / 101,0; DSpark wymuszony 94,6 / **94,8** / 95,0 (krótkie odpowiedzi do 134, ale średnio wolniej); `auto` 117,8 / 103,8 / 100,1 (zmierzył: bez 103,9, lookup 105,4, drafter 101,2). **Wniosek:** nowy drafter 1.1.75 na XTX nadal przegrywa przy T=0,7, bo okno weryfikacji nie ma naszych przyspieszeń (EXPV, NT, PCONV, FUSE…). Okno przyspieszamy w wyścigu (gałąź kern-maya: `IK2_K_W*`, `IK2_K_D*`).
- przegląd 2026-11-24: zrobione wcześniej (2026-11-24 02:02–02:07: forced 1.1.75 DSpark gives T=0.7 94.8 vs production 104.3, auto 103.8, so the drafter still loses. Logs ~/k134/k136-*.log. | 0 | -)

### K-137 · AtomicChat Uncensored AD-Q4_K natywnie w Maya (eksperci Q4_K + Q5_0): ile szybciej niż ablacja w locie
- data: 2026-11-23 (JARO, panel 19:02: „zoptymalizować ten atomic chat i zobaczyć, ile może śmigać”)
- stan: Maya odrzuca plik (`type Q4_K not decoded here`); eksperci AtomicChat: gate_up Q4_K (9,17 GB), down Q5_0 (5,61 GB), reszta Q8_0 (nagłówek GGUF). Odczyt ekspertów na token jak w unsloth UD-Q4_K_XL: 1,847 vs 1,847 GB (pętla 3× w warstwach 6–17), dense 1,73 vs 1,82 GB
- praca (CPU): kernele Q4_K/Q5_0 w `ik2` (dekod, okno, prefill WMMA, NT), gałąź `ad-q4k` w `~/praca/maya-ad`; poprawność na Colab T4 (`tests/ik2_kernels_test.cu`), potem XTX
- test (XTX, ≤ 15 min): rep2 mediana 5 (Q1, Q6 T=0,7, L2k, prefill 2k) AD-Q4_K natywnie vs produkcja (unsloth + `IK2_ABLATE`); odmowy 8 pytań; zgodność z llama.cpp na tym samym pliku (top-1, KLD)
- oczekiwany zysk: 0–5% (bez rzutu ablacji, który kosztował 2–5%) [INFERENCE]; wierność kwantom AtomicChat (KLD 0,0115 do BF16)
- ryzyko karty: nowe kernele → najpierw test-kernel i krótki smoke
- priorytet: wysoki (polecenie JARO)
- **wynik 2026-11-24 01:58–02:09 UTC (XTX, rep2 mediana 5, ABA):** produkcja (unsloth + ablacja w locie) → AtomicChat natywnie (1.1.73 + hipx14 + Q4_K/Q5_0): Q1 118,3 → 128,6 (+8,7%), **T=0,7 104,2 → 113,2 (+8,6%)**, L2k 99,9 → 107,1 (+7,2%), prefill 2k 3457 → 3314 (−4,2%). Na bazie 1.1.75 (k175-ad, `--drafting auto` z DSpark): 127,3 / 112,1 / 106,2 / 3309; auto zmierzył: bez zgadywania 112,3, lookup 113,3, drafter 108,7. Jakość: kopia i 2k poprawne, odmowy 0/8, 1.1.73 i 1.1.75 dają identyczne odpowiedzi. Test kerneli: wszystkie Q4_K/Q5_0 ok; 1 próg tolerancji w starym teście NVFP4 przesunięty losowaniem (poprawka testu d01275e/8773c98). **Wdrożone** do `mayaserve.sh` (konfiguracja `maya-atomic.json`, exe `maya-ik2.adq4k` md5 2bda43fd…).
- stan 2026-11-23 20:00 UTC: kod gotowy, niezmierzony (serwer wyłączony). Gałęzie w `~/praca/maya-ad` (`ad-q4k` 30ff426, na 1.1.73 + hipx14) i `~/praca/maya-175` (`k175` 88b6a6c = hipx14 na 1.1.75; `k175-ad` 60dffeb = to + Q4_K/Q5_0). Test hosta: wartości Q4_K/Q5_0 = ggml `dequantize_row` bit w bit (1 024 256 wartości), iloczyny wierszy w kolejności kerneli 0/97 różnic; nvcc czysto. Nowe kernele rejestrowe `experts_q4k_gu_kernel`/`experts_q50_down_kernel` (styl EXPV, NT), kafle WMMA prefillu Q4_K/Q5_0. Start: `qwen-opt/inkling/start-maya-k136-k137.sh` (build na pudle + kolejka `maya-k13x.jobs`, ~55 min karty razem z K-136).
- przegląd 2026-11-24: zrobione wcześniej (2026-11-24 01:58–02:09, rep2: T=0.7 104.2 → 113.2 (+8.6%), Q1 +8.7%, refusals 0/8. Deployed (mayaserve, maya-atomic.json, maya-ik2.adq4k). Logs ~/k134/k137-ad*.log. | 0 | -)

### K-138 · Unsloth llama.cpp (prebuild b12649-mix, fuzje Inkling) na XTX vs nasz r14 i Maya
- data: 2026-11-23 (link JARO, panel 19:57; Unsloth: RTX PRO 6000 81 → 125 t/s, gfx1151 24 → 33 bez spekulacji)
- test: gotowa paczka `app-b12649-mix-c7059d6-linux-x64-rocm-gfx110X.tar.gz` (bez budowania), AD-Q4_K i UD-Q4_K_XL, KV q4_0: llama-bench tg128 vs nasz r14 (58,4) i stock; serwer z DSpark n7 (xbench Q4, T=0,7, L2k, L8k) vs r14 i Maya (T=0,7 104,3); ≤ 10 min
- oczekiwany zysk: dla Mai brak [INFERENCE: Maya na 3090 124 t/s ≈ Unsloth na PRO 6000 przy 2× większym paśmie]; dla naszego llama.cpp sprawdzić, które ich fuzje nie pokrywają się z naszymi FUSE/F4 (#401, #402, #411, #412, #414) i dać je Gemini w r16
- ryzyko karty: obca paczka ROCm; PM4 nie dotyczy (to nie nasz fork), test pod blokadą GPU
- priorytet: średni
- wynik 2026-11-24 01:35–01:38 UTC (XTX, KV q4_0, AtomicChat AD-Q4_K): llama-bench tg128 Unsloth 40,9 vs nasz r14 58,2 (UD-Q4_K_XL: 44,1 vs 60,9) → nasz +42% w samym dekodzie; prefill pp2048 Unsloth 968. Serwer z DSpark n7 (xbench): Unsloth / nasz r14: krótki Q1 71,0 / 46,0, kopie Q4 98,3 / 85,9, **T=0,7 31,1 / 23,6**, L2k 72,4 / 62,0 (prefill 761 / 1339), L8k 67,9 / 66,5. Wniosek: ich serwer traci mniej na kroku niż nasz (potwierdza narzut 7,8 ms/token z r14 → r15), ale oba 3× za Mayą (T=0,7 104,3). Paczka Unsloth na XTX nie jest dla nas kandydatem; ich pętla serwera do przejrzenia w r16.
- przegląd 2026-11-24: zrobione wcześniej (2026-11-24 01:35: llama-bench tg128 Unsloth 40.9 vs r14 58.2. Server T=0.7: 31.1 vs 23.6, both 3× behind Maya 104.3. Not a candidate (KOLEJKA item result, ~/KERNEL/qwen-opt/inkling/k138.sh). | 0 | -)

### K-059 · Pomiar w warunkach LocalMaxxing (`reasoning-v1`/`code-v1`, T=0, 320 tok.) do publikacji wyników XTX
- data: 2026-10-16
- status: **czeka na decyzję** (publikacja „wkrótce”, na razie tylko odczyt: [[2026-10-20-bez-publikacji-localmaxxing]], [[2026-11-09-decyzje-runda-69]])
- źródło: [[raport-32f-ninfer-tqllm]], [[raport-32d-localmaxxing]]
- test: XTX ~15 min (2 joby)
- zysk: 0 t/s (marketing); szacunek ~147 t/s w ich warunkach
- ryzyko karty: brak
- priorytet: niski (nie wydajność)
- zwiad 2026-11-14: XTX top verified na LocalMaxxing nadal 97,2 t/s (llama.cpp IQ3_S MTP); szacunek topki w ich warunkach ~147 ([[zwiad-2026-11-14]])
- **wynik 2026-11-24 14:36 (XTX, produkcja Qwen3.8-27B Uncensored, warunki LocalMaxxing: kanoniczne prompty, T=0, 320 tok., mediana 3):** konfiguracja produkcyjna (lookup W16) reasoning-v1 **139,4** t/s, code-v1 **123,5**; bez lookupu (`LLAMA_SPEC_LOOKUP=0`, ramię do publikacji) 149,4 / 122,0. Akceptacja draftu ~75% (reasoning), ~58% (code). Publikacja nadal wstrzymana (decyzja właściciela).
- przeniesione 2026-11-24 po teście (wynik wyżej)

### K-073 · Flint (NVFP4) na XTX: rozstrzygnąć nieudany test igły przed katalogiem Enigmy
- data: 2026-10-21
- status: **czeka na decyzję** (inny model; PR #30928 niescalony)
- źródło: `R/59-flint.md`, archiwum (`A:37717-37753`)
- test: XTX needle przy długim kontekście, Flint na topce z poprawkami (`run-topka.sh flint`); ≤ 10 min
- zysk: ~2× vs Qwen27B na XTX, ale to zmiana modelu
- ryzyko karty: temperatury (prefill 160–262k: junction 94 °C, 286 W przed eco)
- priorytet: niski (inny model)
- **wynik 2026-11-24 14:38–14:43 (XTX, Flint, KV q4_0, PM4=0):** igła przy 150k i 64k znaleziona w obu buildach (obecny i bazowy upstream+#30928), odpowiedź kończy się `stop`, sekret także w rozumowaniu; dekod obecny 82,0 / 89,0 t/s vs bazowy 35,3 / 49,2 (×2,3 / ×1,8). Wcześniejsza pusta odpowiedź przy 150k się nie powtarza → test igły zaliczony; Flint może wrócić do rozważań katalogu (jakość osobno). Ramię q8_0 pominięte (zasada KV ≤ q6).
- przeniesione 2026-11-24 po teście (wynik wyżej)

### K-074 · OrcaCyber-Nano na XTX z drafterem DFlash2 (dotąd tylko 3090) i E1 RSR-27B vs Qwen (TB 2.1, omp-bench-20)
- data: 2026-10-19 / 2026-10-21
- status: **czeka na decyzję** (Orca: tylko na prośbę; RSR-27B: wydatek $40–70, ~120 GPU-h)
- źródło: [[raport-56-orca-3090]], [[KOLEJKA-TESTOW]], [[otwarte-decyzje-techniczne]] (`:22`)
- test: Orca: XTX MTP vs DFlash2 ≤ 10 min; RSR: wynajem, test do zdefiniowania
- zysk: wiedza o innych modelach; 0 t/s dla produkcji
- ryzyko karty: VRAM (Orca 15,7 + 2,1 GB przy 262k)
- priorytet: niski (inne modele)
- **wynik 2026-11-24 14:44–14:59 (XTX, OrcaCyber-Nano 15,7G, fork produkcyjny `~/llama-opt`, KV q4_0, PM4=0, xbench, kolejność none / MTP / DFlash / DFlash / MTP):** bez zgadywania Q4 43,7, T=0,7 43,7, L2k 42,4, L8k 41,3; **MTP n4** Q4 144,1–145,0, T=0,7 61,0–63,0, L2k 129,9–130,5, L8k 129,3–129,4 (akceptacja 0,91–0,92); **DFlash2 n6** Q4 194,8–196,3 (+35%), T=0,7 68,5–68,6 (+10%), L2k 175,8–177,2 (+36%), L8k 152,0–153,5 (+18%), akceptacja 0,85–0,96; krótkie Q2/Q3 DFlash wolniejszy (81–92 vs 96–103). Prefill z drafterem DFlash −10…−20% (762–877 vs 816–930). Wniosek: na XTX DFlash2 bije MTP dla Orci (wcześniej mierzone tylko na 3090). Połowa E1 (RSR-27B) czeka na budżet.
- przeniesione 2026-11-24 po teście (wynik wyżej)

### K-142 · Maya: redukcje fali przez DPP (`lane_xor`, mw00 #1164) w ik2 i naszych kernelach
- test (≤10 min po buildzie): `ik2_kernels_test` te same bity; rep2 ABA Q1 / T=0,7 / L2k
- oczekiwany zysk: +0,5–2% [INFERENCE z +1,6% na Hy4 3×XTX]; mamy już DPP w llama.cpp (argmax, rmsnorm)
- priorytet: średni
- **wynik 2026-11-24 15:10–15:18 (XTX, gałąź `ad-dpp` = produkcja + `ik2_lane_xor.h`, 49 zamian `__shfl_xor_sync` na DPP/permlanex16):** `ik2_kernels_test` all passed (387 ok); odpowiedzi greedy identyczne z produkcją (11/11); rep2 ABBA prod / dpp / dpp / prod: Q1 128,4 / 129,9 / 130,1 / 128,6, **T=0,7 112,8 / 114,1 / 113,7 / 113,3 (+0,75%)**, L2k 107,0 / 108,0 / 107,7 / 107,3 (+0,6%). Mały, ale stały zysk, ten sam wynik bit w bit → **wdrożone**: `maya-ik2.adq4k-dpp` (md5 7cbf71e2…) w `maya-atomic.json` (łatka `qwen-opt/inkling/maya-ik2-dpp-lanexor.patch`).
- przeniesione 2026-11-24 po teście (wynik wyżej)

### K-028 · xtxbench: smoke przełącznika bez restartu `GGML_HIP_RUNTIME_SWITCH_FILE`
- data: 2026-11-09
- źródło: [[xtxbench-szybki-ab]] (`:39,48`), `Q/patches/xtxbench/0001-runtime-switch-hook-GGML_HIP_RUNTIME_SWITCH_FILE.patch`
- test: XTX `xtxbench.py t1 --var-switch …` A/A; obowiązkowe ramię md5 ze świeżym startem (wyciek K-001); ≤ 10 min
- zysk: narzędziowy: bez restartu 1,5–2 min na ramię, więc każdy przyszły A/B krótszy
- ryzyko karty: brak
- priorytet: średni (przyspiesza całą kolejkę)
- pominięte 2026-11-20: w `~/wt/xtxbench/build-hip/bin` są tylko biblioteki (`libggml-base`, `libggml-cpu`), nie ma `llama-server`, a xtxbench bez binarki odmawia pracy. Potrzebna jest najpierw budowa gałęzi `xtxbench`, czyli praca nad kodem
- **wynik 2026-11-24 15:37–15:40 (XTX):** llama-server z hakiem przełączników xtxbench (d5454e0) przechodzi bramkę md5 (c4708318 / 6f14e814 PASS), przełącznik `GGML_HIP_MMVQ_PAIR=0` przez `--var-switch` zadziałał (1 przełączenie w logu serwera); llama-bench ABBA vs produkcja: pp4096 997,35 → 997,60 (+0,02%), tg128 41,24 → 41,21 (−0,06%) = koszt haka zerowy. **Zrobione**: hak można włączyć do builda produkcyjnego (A/B bez restartu serwera).
- przeniesione 2026-11-24 po teście (wynik wyżej)

### K-139 · Ekonomia zgadywania Inklinga na XTX (Maya): pomiar kosztu okna, podatku draftera, lokalności ekspertów, parytetu przy T>0
- data: 2026-11-24 (analiza skilli ashhart, [[ashhart-skills-infra]])
- test (rep2/STAT, łącznie ~40 min): E1 wymuszona szerokość `IK2_DRAFT_ADAPT=0 IK2_DRAFT_WIDTH=2..8` → c[B], j, s, a (15 min); E2 podatek draftera: bez `--draft` vs drafter wczytany, a kontroler wybiera zwykły krok (5 min); E3 `IK2_TRACE` 256 tokenów → `route_locality.py` U(B) (2 min); E4 `parity.py` drafting wył./wł., seedy 1,2, T 0/0,7 (10 min); E5 drift routera AD vs UD (5 min); E6 priory SpecCtl z E1 + maks. szerokość (5 min)
- oczekiwany zysk: E1+E6 0–3% przy T=0,7, E2 do ~3% [INFERENCE]; przede wszystkim liczby zamiast założeń dla wyścigu
- ryzyko karty: brak (konfiguracje istniejących buildów)
- priorytet: wysoki
- **wynik 2026-11-24 14:23–14:31 (XTX, Maya 1.1.75 + hipx14 + Q4_K/Q5_0, AtomicChat, KV q4, rep2 mediana 5; Q1 = krótka T=0, Q6 = T=0,7, L2k):**
  - bez zgadywania 127,1 / 112,3 / 106,3; lookup 127,7 / 112,4 / 106,7; `auto` 127,7 / 112,3 / 106,7 (pomiar auto: bez 111,7, lookup 113,4, drafter 107,5, oba 109,2).
  - **DSpark z kontrolerem: Q1 157,9 (+24% nad lookupem), T=0,7 100,2 (−11%), L2k 102,8 (−4%).** DSpark wygrywa przy T=0 i krótkich odpowiedziach, przegrywa przy T=0,7.
  - Wymuszona szerokość (bez kontrolera) T=0,7: w2 77,1, w3 72,4, w4 66,4, w5 59,4, w8 45,9 t/s — każde wymuszone okno traci; T=0 Q1: w3 133,7, w5 157,9, w8 119,8.
  - **Podatek draftera potwierdzony:** lookup z wczytanym drafterem 107,9 / 102,2 vs lookup bez 112,4 / 106,7 → −4,0% / −4,2% na każdym kroku (zapis kontekstu draftera w zwykłych krokach).
  - Lokalność ekspertów (IK2_TRACE, 256 tokenów): suma ekspertów okna U(B) 1,60 / 2,09 / 2,52 / 2,89 / 3,81 dla B=2/3/4/5/8 vs routing niezależny 1,94 / 2,82 / 3,64 / 4,41 / 6,45 (deklaracja Mai 2,7 dla 5 potwierdzona: 2,89); nakładanie sąsiednich tokenów 0,40 (losowo 0,06); między przejściami pętli 0,43–0,57.
  - Parytet greedy (11 odpowiedzi) drafting wył. vs DSpark: identyczne.
  - Wniosek: (1) wyłączyć zapis kontekstu draftera w zwykłych krokach (−4% podatku) → DSpark auto byłby co najmniej równy lookupowi przy T=0,7; (2) wybór drafter vs lookup według temperatury: DSpark przy T=0 (+24% Q1), lookup przy T>0; (3) stały koszt okna nadal główny problem (wymuszone okna przy T=0,7 tracą 31–59%).
- przeniesione 2026-11-24 po teście (wynik wyżej)

### K-141 · Inkling na XTX: nasz silnik vs port GodGMN (release Victora) tym samym testem + wiersz code-v1 T=0 jak LocalMaxxing
- data: 2026-11-24 (zwiad: GodGMN 117 / T=0,7 115,7 / 2k 114,2 na jego XTX, Victor 106 przy 272 W; R9700 z DSpark 144,6 na code-v1 T=0)
- test (~25 min): binarka `maya-ik2-f472e94-rocm10-gfx1100` (sha256 z release) na ggml-org IQ4_NL (pobranie 17,6 GB — zgoda JARO) vs nasza `maya-ik2.adq4k`; ta sama procedura: głębokość 512 / 2k / 8k, greedy i T=0,7; do tego prompt code-v1 (`/tmp/zw-lm-code-v1.txt`, sha a737db73) T=0, 2048 wyj.: off / lookup / DSpark / auto
- oczekiwany zysk: wiedza, czy różnica ±5–10% to maszyna czy kernele; uczciwy wiersz do rankingu
- priorytet: wysoki
- **wynik 2026-11-24 16:00–16:07 (XTX, ten sam komputer, `tools/ik2_bench.py` GodGMN, 2 przebiegi):** nasza produkcja (adq4k-dpp, AD-Q4_K, KV q4, lookup) vs GodGMN f472e94 (zbudowany u nas, bo wydanie wymaga glibc 2.43; preset `ik2-mini-gfx1100.json`, IQ4_NL, KV fp8). **T=0:** głębokość 512 / 2k / 8k: nasz 110,0 / 106,3 / 103,1, ich 104,8 / 102,1 / 95,3 → **+5% / +4% / +8% dla nas**; prefill nasz 2593 / 3048 / 2996, ich 2354 / 3044 / 3051 (przy 8k −2% dla nas). **T=0,7:** nasz 108,3 / 104,8 / 101,9, ich 103,8 / 101,0 / 94,4 → **+4% / +4% / +8%**. Ich 115,7 t/s z README nie powtarza się na naszej karcie (103,8). Uwaga: inne pliki wag (AD-Q4_K vs IQ4_NL), porównanie stosów, nie kerneli.
- przeniesione 2026-11-24 po teście (wynik wyżej)

### K-143 · Inkling: dekod na długim kontekście (32k / 128k), KV q4 vs f16
- data: 2026-11-24 (arXiv 2611.30027: kernele 4-bit KV przy batch 1 biorą 18–38% pasma; Inkling czyta ~1,2 GB KV/token przy 128k)
- test (≤10 min): Maya prod, prompt 32k i 128k + 128 tokenów greedy, `IK2_KV=q4` vs f16; efektywne pasmo atencji z rocprofv3
- oczekiwany zysk: wiedza; jeśli atencja q4 < 40% pasma → kernel
- priorytet: średni
- **wynik 2026-11-24 14:30 (XTX, Maya 1.1.75 port + hipx14, AtomicChat, CLI 128 tokenów greedy, IK2_DEPTH):** głębokość 0 / 8k / 32k / 128k: **KV q4 112,6 / 101,1 / 92,8 / 70,2 t/s**, KV f16 112,6 / 96,9 / 87,7 / 63,4. q4 szybsze od f16 o 4–11% (mniej bajtów), spadek przy 128k −38% (q4) / −44% (f16). Kandydat: atencja na długim kontekście (8 wizyt globalnych) — przy 128k ok. 5,4 ms/token więcej niż przy 0.
- przeniesione 2026-11-24 po teście (wynik wyżej)

### K-144 · Maya: szerokie okna lookupu (GodGMN `IK2_SUFFIX`, do 512) i `IK2_SLOT_KEEP` (alesha #11)
- test (≤10 min): kopia/edycja kodu i proza: nasz lookup (okno ≤8) vs binarka GodGMN z `IK2_SUFFIX=128`; rozmowa 30k + boczne żądanie 2k + powrót (czas wznowienia)
- oczekiwany zysk: kopie ×5–9 (Victor HTTP 99 → 939 t/s), powrót do rozmowy ~10 s → <0,2 s; proza −8–13% bez kontrolera, więc tylko z SpecCtl
- priorytet: wysoki (agenci w Mai)
- **wynik 2026-11-24 16:07 (XTX, `tests/ik2_copy_edit.py`, przepisanie 582 tokenów i edycja 583 tokenów, wyniki dokładne we wszystkich ramionach):** nasz lookup 115,3 / 106,9 t/s; GodGMN domyślnie 103,0 / 103,1; **GodGMN `IK2_SUFFIX=128` (drzewo sufiksów, okno weryfikacji do 128 tokenów): 708,5 / 493,6 t/s (×6,1 / ×4,6 względem nas)**, akceptacja 564/570 i 547/767. Wniosek: przy kopiowaniu i edycji kodu (agenci, poprawki plików) szerokie okno sufiksowe daje kilkukrotny zysk, którego nasz lookup (okno ≤ 16) nie łapie. Nowa pozycja K-147.
- przeniesione 2026-11-24 po teście (wynik wyżej)

### K-147 · Maya: szerokie okno sufiksowe (do 128 tokenów) zamiast lookupu W16 dla edycji i przepisywania
- data: 2026-11-24 (K-144: GodGMN `IK2_SUFFIX=128` 708 / 494 t/s vs nasz lookup 115 / 107 na copy/edit, wyniki dokładne)
- plan: przenieść `IK2_SUFFIX` (drzewo sufiksów, weryfikacja do 128 wejść w jednym przejściu) z GodGMN f472e94 do gałęzi produkcyjnej; parytet greedy 11/11, rep2 (Q1, T=0,7, L2k: nie może stracić > 0,5%) i `ik2_copy_edit.py`; najpierw na CPU przegląd kodu (nvcc), potem jedna bramka na XTX do 10 min
- **wynik 2026-11-24 16:22–16:30 (XTX, gałąź `ad-suffix` 8621f0d = produkcja ad-dpp + `IK2_SUFFIX`, łatka `qwen-opt/inkling/maya-ik2-suffix128.patch`):** odpowiedzi greedy identyczne z produkcją 11/11 (sufiks zadziałał w nich 7 razy); `ik2_copy_edit.py` (dokładne we wszystkich ramionach, 2 powtórzenia): przepisanie 118,3 / 110,9 → **403,8 / 451,8 t/s (×3,7)**, edycja 114,9 / 107,2 → **298,6 / 298,6 (×2,7)**, akceptacja 564/576 i 1108/1376; czat rep2 ABBA bez zmian: Q1 130,1 / 130,1 → 130,1 / 129,7, T=0,7 114,1 / 114,1 → 114,3 / 114,2, L2k 108,1 / 108,0 → 108,1 / 108,0. **Wdrożone** do `maya-atomic.json` (`maya-ik2.adq4k-dpp-sfx`, md5 b9dcf28a…, `IK2_SUFFIX=128`). Różnica do GodGMN (708 / 494): nasze okno idzie ścieżką prefillu `forward()` (ok. 0,2 s na 96 tokenów); następny krok: szybsza weryfikacja szerokiego okna. Ścieżka T>0 (próbka celu w każdym wierszu, zgodna z rozkładem z konstrukcji) nie była osobno mierzona na edycji.
- przeniesione 2026-11-24 po teście (wynik wyżej)

### K-023 · Bisekcja regresji prefillu forka CUDA względem upstream (sm_89 −3,5…−3,9%, 3060 TTFT 512 +30%) i LOO przełączników forka
- data: 2026-10-20 (raport 29)
- źródło: `R/67c-nvidia-backlog-testow.md:103,105` (B9, B11), `product/BENCHMARKI-PRZED-PO-2026-10-19.md` §4, [[raport-15d-prefill-dlugi-kontekst]]
- test: 5060 Ti lokalnie (sm_120): `llama-bench -p 512,4096` upstream vs fork + po jednym przełączniku `=0` na job; sm_89 wynajem
- zysk: odzysk 3…12% prefillu i TTFT na NVIDIA
- ryzyko karty: brak
- priorytet: średni (TTFT Enigmy)
- **wynik 2026-11-24 (Colab, [[colab-kolejka-2026-11-24]]):** L4, prefill 512 / 4096: fork vs upstream b12110 −4,7% / −3,6%, fork vs swoja baza b11620 **+3,2% / +3,4%**; wyłączenie każdego z 17 przełączników forka i `GGML_CUDA_KVQ=0` zmienia prefill o ≤ ±0,5%. Regresja to stara baza (upstream +8% prefillu między b11620 a b12110), nie nasze łatki: lekarstwo = rebase forka.
- przeniesione 2026-11-24 po teście (wynik wyżej)

### K-027 · Profil kroku przy długim kontekście na NVIDIA (`nsys` + `LLAMA_HOSTGAP_TRACE` przy 1,7k/94k/199k)
- data: 2026-11-07
- źródło: `R/67c-nvidia-backlog-testow.md:118` (C1)
- test: 3090/4090 (wynajem; 16 GB 5060 Ti nie zmieści 199k z 27B), po jednym kontekście na job ≤ 10 min
- zysk: 0% sam; rozstrzyga K-062, K-063 i maskę na CUDA
- ryzyko karty: brak
- priorytet: średni (bramka decyzji NVIDIA)
- **wynik 2026-11-24 (Colab, [[colab-kolejka-2026-11-24]]):** L4 nsys: dekod 1,7k / 94k / 199k = 37,5 / 30,0 / 25,0 t/s (73,9 / 93,2 / 126,7 ms na krok); udział uwagi 1,5% / 18% / 32%; bezczynność hosta 10,7 / 11,1 / 17,2 ms na krok (12–14%); odczyt wag stałe 54–58 ms. Wniosek: uwaga (K-062) liczy się tylko przy długim kontekście, przerwy hosta (K-031) to stałe 12–14% kroku.
- przeniesione 2026-11-24 po teście (wynik wyżej)

### K-061 · Tryb wielu użytkowników na NVIDIA: naprawić start `-np 4` z MTP (`failed to create context`), potem k zależne od liczby klientów (`K_BY_B`)
- data: 2026-10-21 (raport 56)
- źródło: `R/67c-nvidia-backlog-testow.md:110` (B16), `R/67-nvidia-vast-kampania.md` §7.2 (`-np 2` agregat +30…36%), `R/69b-tensorfold-qwen-warp.md:77`
- test: 5060 Ti: `-np 2/4` ctx 32k + MTP n=2, C = 1/2/4/8 klientów, suma t/s; ≤ 10 min
- zysk: agregat +20–30% (dane warp: ×2,7–2,9 przy 4–8 klientach); latencja 0
- ryzyko karty: VRAM OOM
- priorytet: niski (jeden użytkownik)
- **wynik 2026-11-24 (Colab, [[colab-kolejka-2026-11-24]]):** L4, 204 800 kontekstu, `-np 4` + MTP: start pada na OOM (`allocating 9576.00 MiB` → `failed to allocate buffer for rs cache`); 131k: zdrowy, OOM przy pierwszym zapytaniu; 32k i 64k działają. Każdy dodatkowy slot z MTP kosztuje 2,4–3,1 GB VRAM: to brak pamięci, nie błąd slotów.
- przeniesione 2026-11-24 po teście (wynik wyżej)

### K-065 · Zimny start `--no-mmap` (pierwszy prompt po restarcie 0,39–1,07 t/s) i nieprzetestowane flagi upstream (`--spec-draft-n-ubatch 64`, `GRAPH_CHUNK_SIZE`, `-fa off`, `--spec-default`)
- data: 2026-11-07
- źródło: `R/67c-nvidia-backlog-testow.md:79-91` (A4, A8, A10, A12, A16)
- test: 5060 Ti, po jednym ramieniu na job ≤ 10 min
- zysk: A12: TTFT pierwszego żądania; reszta ~0 [INFERENCE]
- ryzyko karty: brak
- priorytet: niski (UX)
- **wynik 2026-11-24 (Colab, [[colab-kolejka-2026-11-24]]):** L4: wolny pierwszy prompt po restarcie się nie powtarza; `-lm none` start szybszy o 2–3 s; `--spec-draft-n-ubatch 64` bez zmiany szybkości, −48 MiB VRAM; `GGML_CUDA_GRAPH_CHUNK_SIZE` domyślny najlepszy (1: −1,6%); `--spec-default` na przepisywaniu kodu 133–134 t/s vs 17,6–18,2 bez i 45 z MTP n3 (×7,4), na zwykłym czacie bez zysku; wyjście bajt w bajt identyczne. A10 (`-fa off`) pominięte (wymaga KV f16).
- przeniesione 2026-11-24 po teście (wynik wyżej)

### K-069 · Turing sm_75 (2080 Ti): build forka i smoke test
- data: 2026-11-07
- źródło: `R/67c-nvidia-backlog-testow.md:149` (D6)
- test: build `-DCMAKE_CUDA_ARCHITECTURES=75`, `test-backend-ops`, fork vs upstream; wynajem ≤ 10 min po buildzie
- zysk: nieznany; poprawność dla klasy 11 GB w Enigmie
- ryzyko karty: brak
- priorytet: niski (mała klasa)
- **wynik 2026-11-24 (Colab, [[colab-kolejka-2026-11-24]]):** na T4 wydany fork CUDA (kvqleana, build 11620) pada przy starcie: `no kernel image is available` (brak sm_75); upstream b12110 działa: pp512 302,3, tg128 9,14 t/s. **Silnik Enigmy CUDA nie działa na Turingu (2080 Ti, T4)**: dodać arch 75 do wydania albo planer ma wybierać upstream poniżej sm_86. Build forka na sm_75 niezrobiony (źródło tylko na jaroserverai).
- przeniesione 2026-11-24 po teście (wynik wyżej)

### K-040 · Flaga kompilatora `-mllvm --amdgpu-unroll-threshold-local=600`
- data: 2026-11-07
- źródło: `R/68a-rdna3-kernele.md:126` (4.8)
- test: build + `klab isadiff` gorących kerneli (CPU); GPU tylko, gdy ISA się zmienia: `llama-bench -p 4096` + spec_sweep ABBA + md5 ≤ 10 min
- zysk: 0…2% [INFERENCE]
- ryzyko karty: brak (spille przy większej liczbie VGPR)
- priorytet: niski (tani, mały)
- wynik 2026-11-20: pominięte. Na serwerze Jarvo nie ma ROCm (`hipcc` brak), a build HIP i `klab isadiff` trzeba robić na jaroserverai, czyli na maszynie z GPU, której ten przebieg nie używa.
- przeniesione 2026-11-24 po teście (wynik wyżej)


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

### K-124 · Agentowy megakernel pętli draftu MTP + weryfikacji (metoda megakernel-zoo) — najpierw fork CUDA (5060 Ti/3090), potem XTX (HIP)
- data: 2026-11-19
- źródło: [[megakernel-zoo]] (Qwen3.8-27B B200: SGLang 9,52 → 8,44 ms, ~63 h agenta; ewaluator FP64 + ukryty zbiór + odwrócenie batcha + audyt); [[2026-11-17-k114-nvidia-sufit]] (draft 4–15 × droższy niż bajty, 37–40% kroku); [[budzet-megakernela-qwen-xtx]] (+4…9,5% za 40–70 osobodni)
- hipoteza: trwały kernel dla n kroków draftu (warstwa MTP + głowica 64k + argmax w pętli bez powrotu do hosta) zbliża koszt draftu do bajtów: na 5060 Ti krok n4 51 → ~36 ms (+40%) [INFERENCE]; na XTX mniej (PM4 już tnie granice)
- test: po K-116 (`nsys`): agent w pętli autoresearch z ewaluatorem jak w zoo (odniesienie = obecny fork, tokeny T=0 bitowo + KLD T=1, ukryty zbiór promptów PL/EN/kod, odwrócenie kolejności, audyt drugim agentem); 5060 Ti na Vast z hostguardem, budżet godzin agenta i GPU ustalony z właścicielem; zegar etapów
- miara: ms/draft i t/s n4 T=1 (49,4 → ?), md5 T=0, godziny agenta do pierwszego wyniku przechodzącego ewaluator
- zysk: Enigma NVIDIA do +40% [INFERENCE]; dowód, czy agentowa praca nad kernelem skraca nasze 40–70 osobodni do dni
- ryzyko karty: zawieszenia kernela rezydentnego (na Vast bez ryzyka dla naszej karty; na XTX dopiero po PoC-A z [[budzet-megakernela-qwen-xtx]])
- priorytet: średni (decyzja właściciela: budżet agent-godzin i GPU)

- **2026-11-25:** bez paczki: wymaga budżetu (godziny agentów + GPU) i najpierw K-116 (nsys pętli draftu NVIDIA, Vast 5060 Ti). Decyzja JARO.
- **2026-11-26:** przesłanka obalona na 3090/3060/4080 SUPER (K-116: draft ≈ koszt bajtów); jedyny brakujący pomiar to V(1)…V(5) na 5060 Ti (ok. 10 min) w następnej fali; potem zamknięcie albo zmiana zakresu.
- **K-124 2026-11-26 13:17–13:26 (XTX, `~/wt/k124` 93f2f9b7c: catch-up MTP wpięty w taśmę draftu `LLAMA_K124=1` + ewaluator `~/qwen-opt/k124/eval.py`):** wynik bitowy C1 vs P1 T=0 9/9, T=1 9/9, KLD 0; wall −0,2…−0,4% (GATE PASS formalnie, ale bez zysku), C2 rc=5. **KILL**: wpięcie catch-upu cofa nakładanie jego pracy GPU na próbkowanie hosta. Ewaluator zostaje jako narzędzie dla pętli agentów. **Znalezisko:** te same prompty w odwrotnej kolejności dają inny tekst T=0 nawet w produkcji (P2 vs P1 „reversed identical 0/9”): wynik zależy od poprzednich żądań (ponowne użycie cache promptu czyta stare komórki, jak w K-001c). Do zbadania jako K-187.
- przeniesione 2026-11-26: brak zysku

### K-036 · Nakładanie kroków: wejścia kroku t+1 przed synchronizacją hosta (ZOS-lite), obcinanie po stop-tokenie na GPU
- data: 2026-10-20 (36 L11)
- źródło: `R/36-xtx-qwen-roadmap.md:196`, `R/63-SYNTEZA.md:90`, `R/66-SYNTEZA.md:63`, `R/67c-nvidia-backlog-testow.md:129` (C12)
- test: md5 + test „stop-token w środku okna”, spec_sweep ABBA ≤ 10 min (XTX i 5060 Ti)
- zysk: XTX +0,7…1,8% (luka GPU 410 µs z 27,3 ms), 5060 Ti ≤ +3,9%, LFM +4…6%
- ryzyko karty: PM4 (zmiana porządku taśm)
- priorytet: niski (XTX poniżej progu)

- **2026-11-25:** krok 1 w kolejce (`k036.jobs`): ślad przerw hosta produkcji (`LLAMA_HOSTGAP_TRACE=1`); nakładanie kroków (2–4 dni) tylko gdy bezczynność ≥ 1% kroku.
- **2026-11-25 bieg nieważny:** ślad przerw hosta nie wyprodukował raportu („no report with >= 30 steps”); przełącznik `LLAMA_HOSTGAP_TRACE` prawdopodobnie nie istnieje w buildzie qprep-spec (jest w topka-q63). Do poprawki skryptu.
- **K-036t 2026-11-26 11:32 (ślad przerw hosta na produkcji k183c, `LLAMA_HOSTGAP_TRACE=1`):** bezczynność GPU między krokami: kod 1086–2222 µs z 38,0 ms (2,9–5,8%), proza 1075–1092 µs z 33,1 ms (3,2–3,3%) → **WORTH IT (≥ 1%)**. Wcześniejszy „brak raportu” to zły plik (stderr w `.stdout`). Implementacja `LLAMA_K036` w `~/wt/k036` w toku.
- **K-036m 2026-11-26 11:41 (ślad z medianą, blokada kbuild trzymana, 0 kompilatorów):** bezczynność GPU między taśmami **468–479 µs/krok (1,82–1,85%)** z 25,4–26,3 ms; największy fragment hosta `llm.inputs → cuda.gc.in` 69–75 µs/krok. Żaden kawałek ≥ 0,5 ms → **stop K-036**: całe nakładanie dałoby najwyżej ~1,8%, a największy element strukturalny (catch-up w taśmie draftu) 60–100 µs. Wcześniejsze 2,9–5,8% to artefakt średnich (pojedyncze synchronizacje prefillu 78–95 ms) i builda na rdzeniach SMT serwera.
- przeniesione 2026-11-26: zysk < progu

### K-017 · Głębokość i szerokość draftu per klasa żądania (`LLAMA_SPEC_ROUTE`: rozumowanie/kod T=0 → n=5, proza → n=3)
- data: 2026-10-21 (raport 44)
- status: **czeka na decyzję** (bramka K-007; n=5 zmienia md5 → d71a2c04). Najpierw naprawić crash ABBA `ggml-cpu.c:2504` w `ggml_graph_plan`.
- źródło: `R/44-routing-profili-spekulacji.md:5-7`, [[raport-44-spec-route]], `R/36-xtx-qwen-roadmap.md:183`
- test: XTX `~/qwen-opt/xtxlab/sr_gate.sh` + `sr_arm.sh` (`x44.jobs`), reason_bench T=0, spec_sweep, `mvs`; po jednym na job ≤ 10 min
- zysk: rozumowanie T=0 +6,8%, proza +4,3%, kod/JSON T=0 +5…10%, czat 0 (kill < −1%)
- ryzyko karty: brak
- priorytet: średni (zależy od decyzji)

- **wynik 2026-11-25 22:28–22:37 (XTX, qprep-spec 50ca29355, `LLAMA_SPEC_ROUTE` + `DRAFT_N=5` vs prod, ABBA):** bramka: routing ≤ 4 = prod (aa522e89), routing 5 = zwykłe n5. Proza T=1 bez myślenia 104,9 / 108,0 → 110,1 / 110,1 (**+3,4%**), czat T=1 109,2 / 115,4 → 113,9 / 113,6 (+1,3%), kopia T=0 407,5 / 427,6 → 410,9 / 410,1 (−1,7%). Zysk na granicy progu 3% tylko dla prozy; głębokość 5 zmienia md5 T=0 z założenia, więc wdrożenie zależy od decyzji K-007.
- **2026-11-26 bramka K-007: PASS** (rozkład identyczny). Zysk +3,4% proza / −1,7% kopia: wdrożenie dopiero po wall.py −2% (K-183 następny).
- **K-017g 2026-11-26 11:33–11:37 (XTX, produkcja k183c vs produkcja + `LLAMA_SPEC_ROUTE=1 DRAFT_N=5`, ABBA 2 pary, wallm.py):** **FAIL**: T=0 kod −6,0%, tech −3,5%, pl −17,2%, json −0,3%; T=0,7 kod −11,2%, tech −13,8%, json −17,5%, pl +4,0%; kopia mvs 413,5 → 397,2 t/s (−3,9%). Routing przydziela promptom czatu profil „reason” z głębią 5, a weryfikacja 6 wierszy kosztuje więcej niż zysk akceptacji. Odrzucone.
- przeniesione 2026-11-26: FAIL wall

### K-186 · Nib v0.1.2: kernele bez spilli VGPR, prefill 128K +32% na XTX (zwiad 26.11)
- Plan: build v0.1.2 obok naszego, `nib bench -p 512 -n 64 -c 131072 --sparse-pages 224` stary vs nowy, logity identyczne, przeniesienie `--weights-patch` (WE2). ≤12 min GPU. Przygotowuje agent K186Nib012.
- **wynik 2026-11-26 05:53–05:57 (XTX, q8_0, --sparse-pages 224):** stary 2e16cf0 → v0.1.2: pp512 głęb. 0 4471,8 → 4471,9, głęb. 130048 3090,8 → 3098,1 (+0,2%), tg64 123,0 → 123,0 i 114,9 → 114,8; wall T=0 138,9 → 139,0, T=0,7 130,3 → 130,2; logity identyczne (4k, 32k, także we2-012). **0% u nas**: nasz clang 23 (ROCm core-10.0) miał tylko 6 spilli w kernels_fa zamiast 1312 u autora (clang 22). WE2 `--weights-patch` przeniesiony na v0.1.2 (`~/wt/nib-we2-012`, d1b4eda).
- przeniesione 2026-11-26: 0% zysku

### K-021 · Dataflow w taśmie PM4: usunąć granice dispatchy w łańcuchu MMVQ → norma → MMVQ weryfikacji (najpierw PoC-A: hand-off w trwałej siatce)
- data: 2026-10-20 (raport 36 L7)
- źródło: `R/37-proza-100.md:17-19` (górna granica `GGML_HIP_PM4_UB=mmvq,norm` −2,17 ms/partię 5 wierszy, −8,8%), `R/36-xtx-qwen-roadmap.md:190`, `R/66-SYNTEZA.md:66` (#15), [[budzet-megakernela-qwen-xtx]]
- test: XTX `klab` mikrobench hand-off, `GGML_HIP_PM4=0` (kill: > 0,3 µs albo < 30% zysku „bez granicy”); potem PoC-B md5 + spec_sweep ABBA; każdy krok ≤ 10 min
- zysk: etap 1 +2,6…4,2%, pełny +3…6% krótki kontekst / +2…4% przy 199k, po 40–70 osobodniach [SZACUNEK]
- ryzyko karty: **wysokie**: zawieszenia taśmy PM4 i resety (16a, 24l); tylko z `gpu-guard.sh`
- priorytet: średni (jedyna duża dźwignia w kernelach, drogie i ryzykowne)

- **2026-11-25:** PoC-A w kolejce (`k021.jobs`, `~/qwen-opt/klab/handoff/handoff.hip`): koszt przekazania między etapami w trwałej siatce vs osobne dispatche; KILL gdy > 0,3 µs albo < 30% zysku. PoC-B w forku: 1–2 tygodnie.
- **2026-11-26 bieg nieważny:** mikrobench `handoff` zlinkowany z `libamdhip64.so.7`, a na jaroserverai jest runtime ROCm 10 → exit 127. Do przebudowy.
- **wynik 2026-11-26 02:27–02:30 (handoff PoC-A, przebudowany z RPATH ROCm 10):** **KILL**: przekazanie między etapami w trwałej siatce 3,09 µs (r5120) i 0,81–0,83 µs (r1024) przy progu 0,3 µs; zachowane 8% zysku wobec szacunku PM4 (próg 30%). Usuwanie granic dispatchy trwałą siatką nie opłaca się na gfx1100.
- przeniesione 2026-11-26: KILL

### K-050 · Runtime ROCm 7.2.4 z kompilatorem ROCm 10
- data: 2026-11-07
- status: **czeka na decyzję** (pobranie runtime)
- źródło: `R/68a-rdna3-kernele.md:127` (4.9)
- test: XTX `LD_LIBRARY_PATH` na 7.2.4, `llama-bench -p 512,4096 -d 0,16384 -r 3` ABA ≤ 10 min, potem soak PM4
- zysk: prefill 0…+5% (dane z innej XTX); decode ~0 (PM4 omija runtime)
- ryzyko karty: **wysokie**: PM4 zależy od ROCr/CLR (raport 17), page faulty/resety
- priorytet: niski (ryzyko > zysk)

- **2026-11-26:** potrzebne tylko 4 pakiety runtime 7.2.4 (73 MB: hip-runtime-amd, hsa-rocr, comgr, rocprofiler-register) rozpakowane bez roota do `~/rocm-rt/7.2.4/lib` (cofnięcie: usunięcie katalogu); symbole i code object v6 zgodne. W kolejce `~/qwen-opt/kq/K-050.jobs` (md5 + bench d0/d16k ABBA, PM4=0, ok. 15 min).
- **wynik 2026-11-26 00:58–01:05 (runtime ROCm 7.2.4 z `~/rocm-rt/7.2.4`, binarka topka-q70, PM4=0, ABBA):** md5 PASS (c4708318 / 6f14e814); pp512 996,1 → 998,1 (+0,2%), pp4096 999,7 → 999,7, tg128 41,34 → 41,38 (+0,1%), d16384: pp512 +0,16%, tg128 −0,1%. Bez zysku.
- przeniesione 2026-11-26: bez zysku

### K-035 · Głowica draftu MTP: grube przejście (IQ4_XS/Q2_K) + dokładny rerank top-8 na wierszach Q6_K
- data: 2026-10-20 (36 L6c), 2026-11-07 (66 #5)
- źródło: [[glowica-draftu-rerank]], `R/66-SYNTEZA.md:56`
- test: offline na logitach (czy top-8 grubej głowicy zawiera argmax Q6_K); XTX spec_sweep T=1 + E0 + `mvs` ABBA ≤ 10 min
- zysk: +1…3% (B1), +1…4% (B2) [SZACUNEK]; cel nietknięty, md5 bez zmian
- ryzyko karty: brak
- priorytet: niski (poniżej progu)

- **2026-11-25:** krok 1 w kolejce (`k035.jobs`): głowica draftu iq4_xs (prod) vs q6_K (dokładna) vs q2_K, tok/krok; rerank top-8 (1,5–2 h kodu) tylko gdy q6_K wyraźnie wygra.
- **wynik kroku 1, 2026-11-25 (XTX, głowica draftu MTP):** tok/krok pl-proza: iq4_xs (prod) 2,84 / 2,84, **q6_K (dokładna) 2,86 (+0,7%)**, q2_K 2,81; kopia T=0 440,0 / 431,9 (prod) vs 438,7 (q6_K). Dokładna głowica prawie nic nie dodaje do akceptacji, więc grube przejście + rerank top-8 nie ma czego odzyskać.
- przeniesione 2026-11-26: sufit zysku < 1%

### K-075 · Drzewo weryfikacji MTP na hybrydzie GDN (forma WY, maska przodków)
- data: 2026-10-20 (24s), 2026-11-07 (66d C)
- źródło: [[drzewo-weryfikacji-gdn-wy]], `R/66-SYNTEZA.md:65`, `R/68b-spekulacja-nowe.md` („dziś kill”: +1,6% przy 0,85 ms/wiersz)
- test: najpierw symulacja `tree_dynamic` na logach MTP (CPU); na XTX tylko koszt wiersza (`test-backend-ops perf` MMVQ n=5 vs n=6) ≤ 10 min; wraca dopiero, gdy wiersz ≤ 0,57 ms (po K-013)
- zysk: kod/T=0 +3…8%, czat T=1 0…+4% [SZACUNEK]
- ryzyko karty: nowe kernele GDN w PM4
- priorytet: niski (zależne od K-013 i K-007)

- **2026-11-25:** krok 1 w kolejce (`k075.jobs`): koszt jednego wiersza weryfikacji `llama-bench -p 1..9`, PM4 wył./wł., ctx 0 i 32k; drzewo opłaca się przy ≤ 0,57 ms/wiersz i wymaga decyzji K-007.
- **wynik kroku 1, 2026-11-25 23:3x (XTX, llama-bench -p 1..9, ctx 0):** PM4 wł.: 2 wiersze 22,54 ms, 9 wierszy 28,46 ms, czyli **ok. 0,85 ms na dodatkowy wiersz** (0,44–1,75), PM4 wył. ok. 0,8 ms. Próg opłacalności drzewa: ≤ 0,57 ms/wiersz → drzewo weryfikacji się nie opłaca na XTX.
- przeniesione 2026-11-26: koszt wiersza powyżej progu

### K-057 · Tryb „identyczne odpowiedzi” `LLAMA_SPEC_BITEXACT=1` jako opt-in (port gałęzi `batch-invariant` na topkę)
- data: 2026-10-16 (raport 12)
- status: **czeka na decyzję** (wdrożyć przełącznik, domyślnie wyłączony)
- źródło: [[2026-10-16-bit-exact]], [[otwarte-decyzje-techniczne]] (`:14`), `STAN-PRAC.md` (BitExactSpec, `365af3e5e`)
- test: XTX `validate.sh` (plain == MTP) + spec_sweep krótko i przy 27k; ≤ 10 min
- zysk: ujemny (0% krótko, −9% przy ~27k); wartość: dowód bezstratności
- ryzyko karty: brak
- priorytet: niski (nie przyspiesza)

- **ocena 2026-11-25:** port gałęzi bitexact koliduje już na pierwszym commicie (`c09ac6aab`, 6 kawałków w `mmvq.cu`, od bazy +2916 linii mmvq i +802 fattn-kvq); 1,5–3 dni + build, zysk prędkości ujemny. Czeka na decyzję JARO, czy tryb identycznych odpowiedzi jest potrzebny.
- **2026-11-26:** po decyzji K-007 (bramka KLD) tryb bit-exact nie jest warunkiem wdrożeń; port 1,5–3 dni bez zysku prędkości.
- przeniesione 2026-11-26: zbędne po K-007

### K-024 · Enigma ROCm na innych kartach AMD + autotune wariantu FA przy instalacji (gfx1101/1102/1151/1201)
- data: 2026-11-09
- źródło: `R/70-fa-d256-jak-to-zrobilismy.md:186` (#3)
- test: wynajem kart AMD; `fa-d256` micro + md5 + bench przy głębokości na każdej architekturze; ~1 h wynajmu
- zysk: RDNA3 gfx1101/1102: prefill przy głębokości +3…6%; gfx1151 nieznane; gfx1201 wymaga portu [INFERENCE]
- ryzyko karty: brak (wynajem)
- priorytet: średni (warunek sprzedaży Enigmy na inne Radeony)
- **2026-11-26:** wymaga innych kart AMD (gfx1101/1102/1201); mamy tylko XTX, a Vast nie ma ofert Radeonów.
- przeniesione 2026-11-26: brak sprzętu

### K-107 · Dwie karty w jednym komputerze: XTX + RTX 5060 Ti (podział warstw `-sm layer` przez Vulkan albo dwa niezależne serwery dla roju agentów)
- data: 2026-11-15
- źródło: [[mapa-inferencji-roadmap]] (luki #3–#6, #10); plan z `hardware/rx-7900-xtx.md` §2 („do przetestowania”)
- test: gdy 5060 Ti online w jaroserverai: (a) dwa serwery (XTX Qwen 27B + 5060 Ti LFM albo Qwen IQ3) i fan-out omp, ściana sesji; (b) Vulkan `-sm layer` Qwen 27B na 40 GB: decode/prefill vs sam XTX; ≤ 10 min na ramię
- (c) dodane 2026-11-19 ([[zwiad-2026-11-19]]): prefill dzielony warstwami jak oMLX „Prefill Accelerator” (Qwen3.8-27B 64K 352 → 1879 t/s z 2 × A6000): 5060 Ti liczy pierwsze k warstw chunku promptu, XTX resztę i dekod; KV/stan GDN warstw k przesyłany przez PCIe; miara: fill 64k/255k t/s vs sam XTX (493 t/s przy 255k), md5 dekodu po fillu
- zysk: (a) przepustowość roju agentów; (b) tylko pojemność (większy model), decode wolniejszy [SZACUNEK]; (c) prefill, jeśli udział warstw na 5060 Ti i koszt PCIe na to pozwolą [INFERENCE]; reguła dla Enigmy „kiedy druga karta pomaga”
- ryzyko karty: brak (bez PM4 na Vulkan)
- priorytet: średni (5060 Ti offline)
- **2026-11-26:** w jaroserverai nie ma RTX 5060 Ti (lspci: tylko Navi 31, 2026-11-25), więc test dwóch kart w jednym komputerze jest niewykonalny.
- przeniesione 2026-11-26: brak sprzętu

### K-126 · Enigma Windows NVIDIA: wydanie z CUDA 13.4 dla Blackwell (sm_120) zamiast CUDA 12.4
- data: 2026-11-19
- źródło: audyt Gemini (C.1.4b) potwierdzony: `app/engine/data/engines.json:155-182` pinuje `win-cuda-12.4`; release b11856 ma `llama-b11856-bin-win-cuda-13.4-x64.zip` (sha256 `06478e0f…`) i `cudart-…-13.4` (`738f8c25…`); `baselineEngineFor` (`engine.ts:88-90`) bierze pierwszy wpis i nie patrzy na architekturę GPU; JIT z PTX: Strata 173 s → 0,34 s ([[strata]])
- test: CPU: wpis `upstream-windows-x64-cuda13` z `gpuArchs: [sm_120]`, wybór po architekturze w `baselineEngineFor`, rozmiary z API GitHub, testy `bun test`; potem pomiar pierwszej odpowiedzi na Windows z kartą 50xx (nie mamy: Vast nie ma Windows) [INFERENCE: CUDA 13 wymaga sterownika ≥ R580, sprawdzać przy wykrywaniu]
- miara: czas do pierwszego tokena przy pierwszym starcie, t/s 12.4 vs 13.4
- zysk: najpopularniejsze karty (RTX 5070 6,15% Steam) bez minut JIT przy pierwszym starcie
- ryzyko karty: brak
- priorytet: średni
- wynik 2026-11-20: zrobione po stronie CPU. Nowy wpis `upstream-windows-x64-cuda13` w `app/engine/data/engines.json` (b11856, `gpuArchs: [sm_120]`, `minDriver: 580`; rozmiary i sha256 z API GitHub: zip 159 939 681 B `06478e0f…`, cudart 423 535 356 B `738f8c25…`). `baselineEngineFor` (`app/engine/src/server/engine.ts:92-98`) wybiera wpis pod architekturę karty, gdy sterownik jest znany i ≥ 580, w innym wypadku zostaje CUDA 12.4. Testy w `app/engine/test/engine.test.ts:79-83` (sm_120 + 581 → 13.4; sterownik 576, brak sterownika albo sm_86 → 12.4); `bun test` 208 pass. Zostaje pomiar pierwszej odpowiedzi na Windows z kartą 50xx.
- **2026-11-26:** wymaga Windows z RTX 50xx; nie mamy takiej maszyny ani wynajmu z Windows.
- przeniesione 2026-11-26: brak sprzętu

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
- **2026-11-26:** wymaga pobrania nowego modelu; decyzja JARO „pracuj na tych co masz” ([[2026-11-26-bez-pobierania-modeli]]).
- przeniesione 2026-11-26: decyzja JARO: bez pobierania

### K-172 · Silniki strumienia ekspertów MoE na XTX: Magnitude 0.3.3 (Vulkan) i RustingStrata 1.3.3 (`--backend hip`) vs topka `-ncmoe`
- data: 2026-11-25 (panel JARO: RustingStrata 160 t/s na 3060, Magnitude strumień z SSD)
- po co: Enigma nie ma offloadu MoE dla kart 8–16 GB; test na modelu większym niż 24 GB pokazuje, czy rozmieszczenie ekspertów po routingu bije statyczne `-ncmoe`
- test: `Qwen3.6-35B-A3B-Q8_0.gguf` (35 GB, nie mieści się, jest na dysku); dekod po 4K i prefill 4K, 3 biegi na silnik, T=0; ten sam prompt
- uwaga dysk: wymaga zostawienia `~/models/q36` (35 GB), który był na liście do usunięcia
- czas karty: ok. 15 min
- priorytet: średni

- **2026-11-25:** `~/models/q36` pusty od 17:38 (model skasowany). RustingStrata 1.3.3 i Magnitude 0.3.3 zainstalowane w `~/wt/moe-engines`, `k172.jobs` gotowy z blokadą „brak modelu”; Magnitude ma port 10100 na sztywno i wymaga Vulkana z `~/vk`. Wymaga pobrania 35 GB: decyzja JARO.
- **2026-11-26:** JARO nie zgadza się na pobranie modelu ([[2026-11-26-bez-pobierania-modeli]]).
- przeniesione 2026-11-26: decyzja JARO: bez pobierania

### K-170 · Lucebox `inkling2_loop` (#1056) na XTX: Inkling 2 Mini z DSpark vs Maya
- data: 2026-11-25 (panel JARO: Lucebox na R9700 AR 81,7, z DSpark 143,5 t/s temp=1)
- test: build lucebox `d0e9473` dla gfx1100 (`~/qwen-opt/tools/rbuild`, cel `luce_server`), model nasz `Inkling-2-Mini-UD-Q4_K_XL.gguf` + `~/models/inkling/mtp.safetensors` (bez pobierania); najpierw krótki smoke (page fault = stop), potem wall.py T=0 / T=0,7 i bez spekulacji, porównanie z Mayą w tej samej sesji
- ryzyko karty: nowy silnik HIP; gałąź RDNA3 w ich FA istnieje, ale była testowana tylko na gfx1201/1151
- czas karty: ok. 10 min
- priorytet: wysoki

- **2026-11-25:** lucebox `d0e94739` zbudowany dla gfx1100 (`~/wt/lucebox/server/build-hip`), ale loader czyta tylko ich konwersję (`inkling2_loop`, klucze `loop.start/end/count`, bez skal NVFP4 ekspertów; `server/src/inkling2/inkling2_loader.cpp:94-305`); nasz plik unsloth się nie załaduje. Wymaga pobrania `Inkling-2-Mini-Fast-IQ4_NL.gguf` (17,6 GB, inny model, test tylko szybkości silnika) albo portu loadera (kilka godzin). `k170.jobs` gotowy z blokadą „brak modelu”. Nasz `mtp.safetensors` = ich DSpark (sha256 7c3b6513…). Decyzja JARO.
- **2026-11-26:** JARO nie zgadza się na pobranie modelu ([[2026-11-26-bez-pobierania-modeli]]).
- przeniesione 2026-11-26: decyzja JARO: bez pobierania

### K-063 · Wyzwalacz PDL + prefetch L2 przed `pdl_sync` w gęstym MMVQ (sm_120) i sterowanie L2 (`evict_first`, persisting window `GGML_CUDA_L2_PERSIST`)
- data: 2026-10-19 (21b)
- źródło: [[pdl-mmvq-trigger]], [[l2-persist]], `R/67c-nvidia-backlog-testow.md:122-125` (C5–C8)
- test: 5060 Ti: `GGML_CUDA_MMVQ_PREWAIT=0/1/2`, `WEIGHT_EVICT_FIRST`, `L2_PERSIST`, md5 + tg128/spec_sweep ABBA; ≤ 10 min każdy; kill < +1,5% LFM tg128
- zysk: LFM +1,1…4,6%, Qwen +0,7…2,6% (PDL); L2 +0,5…2% [SZACUNEK]
- ryzyko karty: brak
- priorytet: niski (małe)

- **2026-11-25:** PDL wymaga PTX ≥ 90 (`common.cuh:1895`), więc na L4/Ampere nic nie robi; potrzebna karta sm_120. `WEIGHT_EVICT_FIRST` i `L2_PERSIST` nie istnieją w forku 007a6f813.
- **wynik (Colab L4 sm_89, fork 007a6f813, 2026-11-25, `/tmp/nvc/res` na Jarvie):** `GGML_CUDA_MMVQ_L2PF=1`: spekulacja T=0 37,51 / 37,43 → 37,19 / 37,21 (−0,7%), plain tg128 20,33 → 20,31. Bez zysku na sm_89; część PDL wymaga sm_120.
- przeniesione 2026-11-25: bez zysku na L4

- **wynik 2026-11-26 (Vast 5060 Ti nvq, [[2026-11-26-nvq-5060ti]]):** PDL1 vs PDL0 T=0 54,71 / 54,68 vs 54,17 / 53,96 (+1,1%), plain tg 32,02 vs 31,91; L2 prefetch bez zysku. PDL domyślnie włączony zostaje.
### K-058 · Strażnik „drugie `</think>` zabronione” w `reasoning-budget.cpp` (T7, niezależny od Astry)
- data: 2026-11-09
- status: **czeka na decyzję** (2d; zmienia wyjście tylko przy przecieku)
- źródło: `R/69-SYNTEZA.md:27,37-40` (A3), [[astra-stop]]
- test: build + md5 bazy (musi być =) + skan 50 zadań agentowych; ≤ 10 min/partię
- zysk: 0 t/s; poprawność formatu
- ryzyko karty: brak
- priorytet: niski (nie szybkość)
- **wynik 2026-11-25 22:45–22:54 (XTX, `~/wt/k058` f0542416f, replay 31 tur agenta omp 8k–45k, T=0):** bramka on = off PASS; wycieki `</think>`: off 0, on 0; **wywołania narzędzi: off 25, on 0**. Strażnik maskował tag także tam, gdzie po bloku rozumowania następuje wywołanie narzędzia, i zepsuł format tool calls. Werdykt: nie wdrażać; w tym korpusie problem drugiego `</think>` w ogóle nie wystąpił.
- przeniesione 2026-11-25: psuje wywołania narzędzi

### K-046 · Szerokość ogona lookup zależna od kontekstu: W16 → W8/W5 przy ≥ 128k (`LLAMA_SPEC_LOOKUP_ADAPT=1`)
- data: 2026-10-18, 2026-11-07 (68c #7)
- status: **czeka na decyzję** (bramka K-007, zmiana szerokości zmienia md5)
- źródło: `R/68c-dlugi-kontekst-gdn.md:141`, [[kontroler-szerokosci-draftu]]
- test: najpierw dane z CPU (`LLAMA_SPEC_LOOKUP_LOG`: udział kroków `tail` przy n_past ≥ 128k); XTX `ADAPT=1` vs W16 na replayu 128–200k ABBA ≤ 10 min
- zysk: krok W16 przy 255k to ~+20–25 ms; zależy od udziału ogonów (kill < 2% kroków)
- ryzyko karty: brak
- priorytet: niski (najpierw dane)
- **wynik 2026-11-25 22:55–23:00 (XTX, `~/wt/k046` 15f7b5209, jeden serwer, prefill ok. 140k, odpowiedź 384 tok.):** T=0 W16 233,5 / W8 176,5 / W5 140,0 t/s (md5 równe 1b57c02c), T=1 W16 227,6 / W8 174,0 / W5 140,9. Lookup przy ≥ 131k to 37,8% kroków. **Węższy ogon jest wolniejszy (W8 −24%, W5 −40%)**; hipoteza „przy długim kontekście W8/W5” odrzucona, zostaje W16.
- przeniesione 2026-11-25: hipoteza odwrotna do pomiaru

### K-008 · Dynamiczna głębokość draftu MTP z luki Gumbela z wczesnym wyjściem z łańcucha (dmin 2, dmax 5)
- data: 2026-10-10 (zmienna długość draftu), 2026-11-07 (68b #1)
- status: **czeka na decyzję** (bramka K-007; zmienna szerokość weryfikacji zmienia md5 T=0, choć rozkład jest zachowany)
- źródło: `R/68b-spekulacja-nowe.md:160,164`, `R/68-SYNTEZA.md:17`, `R/40-akceptacja-prozy.md:116` (proza `DRAFT_N=3` +4,3%, 82,4 vs 79,0 t/s, 8/8 promptów), [[lekcja-glebokosc-zmienia-tekst]]
- test: XTX, `spec_sweep.sh "LLAMA_SPEC_DEPTH_GAP=0" "LLAMA_SPEC_DEPTH_GAP=2"` T=1, ABBA po 2 ramiona na job; xtxbench 1,7k/94k/199k
- zysk: symulacja +3,9% ogółem, czat PL +4,8%, EN +2,9%; bez wczesnego wyjścia ~0
- ryzyko karty: PM4 (warunkowe wyjście w taśmie draftu)
- priorytet: wysoki (największy bezstratny zysk decode, PL najwolniejszy: 120 t/s)
- **wynik etapu 1, 2026-11-25 22:39–22:44 (XTX, `~/wt/k008` 0d024983c, `LLAMA_SPEC_DEPTH_CONF`):** prod P1/P2 T=1 120,0 / 120,1, kopia T=0 429,6 / 429,8; τ=0,6: 117,3 (−2,3%) / 426,7; τ=0,85: 118,5 (−1,3%) / 425,1. Wczesne zatrzymanie łańcucha MTP według pewności głowicy nie opłaca się (krótszy łańcuch kosztuje więcej, niż oszczędza). Etap 2 (luka Gumbela, 1,5–2 h + build) nie ma podstaw.
- przeniesione 2026-11-25: wolniej

### K-173 · Dekwantyzacja K-quantów przy prefillu: bloki 32/64 wątków → dim3(32, 8) (jak PR #32875 dla NVFP4)
- data: 2026-11-25 (panel JARO, PR ggml-org/llama.cpp#32875: NVFP4 dequant 4,2×, prefill Qwen3.8-27B +17,7% na V100)
- mechanizm u nas: na RDNA3 `ggml_cuda_should_use_mmq` zwraca false dla Q6_K przy ne11 > 128 (`mmq.cu`), więc prefill Q4_K_M idzie przez dekwantyzację + hipBLAS dla tensorów Q6_K; `dequantize_row_q6_K_cuda` startuje `<<<nb, 64>>>`, q4_K `<<<nb, 32>>>` (`convert.cu:307,319`, topka qprep-spec 50ca29355). Nib ma własny silnik HIP bez tej ścieżki
- test: łatka (indeks bloku `blockIdx.x*blockDim.y + threadIdx.y` z warunkiem `i < nb`), test-backend-ops MUL_MAT q4_K/q6_K bitowo + perf, xtxbench prefill 32k ABBA; próg ≥ 1% prefillu
- czas karty: ok. 8 min
- priorytet: średni
- **wynik 2026-11-25 22:00–22:09 (XTX, `~/wt/k173-dequant` 6c7824556, `GGML_HIP_DQ_Y`):** test-backend-ops 17/17 dla Y=1/4/8. Perf q6_K (jedyny typ na ścieżce dekwantyzacja + hipBLAS na RDNA3 przy n > 128): 17408×512×5120 2086–2199 GFLOPS bez różnicy między Y; pp2048 1004,6/1002,6 (Y=1) vs 1004,0/1004,0 (Y=8), pp32k 890,1/890,5 vs 889,4/889,9: **0%**. Na gfx1100 bloki 64 wątków (2 fale wave32) nie są wąskim gardłem; zysk z PR #32875 dotyczy NVIDII (bloki 32 wątków = 1 warp).
- przeniesione 2026-11-25: bez efektu

### K-175 · Wdrożenie na :8080: K-020 (wyrzucanie cache ważone kosztem, α=1) + K-018 (AGR2) z `~/wt/qprep-spec`
- data: 2026-11-25 (wyniki K-018, K-020 wyżej)
- test: wall.py z promptem `pl` prod vs qprep-spec (AGR2 + koszt α=1), bramka: żadna kategoria < −2%; potem przełączenie `chat8080.sh` na nowy build w oknie kolejki i smoke md5
- czas karty: ok. 8 min
- priorytet: najwyższy (−51% czasu przy wielu wątkach agenta)
- **wynik 2026-11-25 21:37–21:40 (wall.py ABBA, `~/qwen-opt/k175/summary.py`):** N (AGR2 + koszt α=1 + KVD q8_0) vs P: T=0 code +4,5%, tech +1,3%, pl +2,2%, json +6,0%; T=0,7 code +2,9%, **tech −3,6% (FAIL)**, pl +0,1%, json +5,1%; md5 T=0 różne we wszystkich 4 kategoriach (KV draftu q8_0 zmienia wyjście). NB (bez KVD, n=1): T=0 tech −6,7%, pl −8,5%, md5 pl/json różne. **GATE FAIL: AGR2 i KVD q8_0 nie wchodzą.** Sam K-020 (neutralny dla wyjścia) idzie osobno jako K-178.
- przeniesione 2026-11-25: bramka nie przeszła

### K-062 · Dekoder FA CUDA z `__launch_bounds__(…,2)` (dual-CTA)
- data: 2026-11-07
- źródło: `R/67c-nvidia-backlog-testow.md:121` (C4), `R/66b-1cat-tokenspeed.md:97-98`
- test: 5060 Ti: perf FA + long_ctx, md5; ≤ 10 min/krok (po K-027)
- zysk: 1Cat V100 128k +19% bitowo; u nas po `kvq` nieznane
- ryzyko karty: brak
- priorytet: niski (po profilu)
- **wynik 2026-11-24 (Colab, [[colab-kolejka-2026-11-24]]):** pominięte na Colabie: `__launch_bounds__` to zmiana źródła kernela, nie flaga builda (wymaga kodu).
- **wynik 2026-11-25 (Colab L4 sm_89, fork 007a6f813):** `__launch_bounds__(128,1)` → `(128,2)` w `fattn-vec.cuh` daje identyczny kod maszynowy: 48/48 kerneli vec bez zmian, rejestry bez zmian (max 255), bo 2 bloki po 128 wątków nie ograniczają rejestrów. Zysk 0%. Prawdziwe dual-CTA wymaga bloków 256 albo limitu rejestrów (nowa praca).
- przeniesione 2026-11-25: bez efektu

### K-042 · Spekulatywny prefill następnej tury w przerwie (serwer prefilluje swoją odpowiedź, przerywa na granicy ubatcha)
- data: 2026-11-07
- źródło: `R/68c-dlugi-kontekst-gdn.md:140` (#6)
- test: XTX replay sesji (`agent_bench`): TTFT na turę, trafienie prefiksu (LCP), md5 „trafienie vs zimny start”; ≤ 10 min/ramię
- zysk: ~10–25% czasu małych tur [SZACUNEK], więcej przy ≥ 128k
- ryzyko karty: brak (GPU zajęte w przerwach)
- priorytet: niski (zależne od klienta)
- **ocena 2026-11-25:** ok. 2–3 dni kodu serwera; K-128 pokazał, że poprzednia odpowiedź wraca z cache w 89,7% tokenów, a tury agenta trafiają w cache w 99,2%, więc zysk dotyczy najwyżej ok. 10% tur. Łączymy z K-128.
- przeniesione 2026-11-25: koszt nieproporcjonalny do zysku

### K-010 · Fuzja gate/up + GLU w MMQ dla WMMA RDNA3 (port upstream #29948)
- data: 2026-11-05
- źródło: `R/68a-rdna3-kernele.md:120`, `R/68-SYNTEZA.md:21`, `R/68d-swieze-od-spolecznosci.md` §2.2
- test: XTX `test-backend-ops -o MUL_MAT` z fuzją, `llama-bench -p 512,4096 -ub 512 -r 5` ABBA, md5; ≤ 10 min/krok
- zysk: pp ≤ 32k +2…4% [INFERENCE] (CUDA u autora +4,6…7,4%)
- ryzyko karty: brak (wariant MoE był na RDNA3 wolniejszy o 3…16%, więc mierzyć)
- priorytet: średni (prefill, pakiet z K-009)
- **wynik (zmierzone 2026-11-20, zebrane 2026-11-25):** port jako `GGML_HIP_MMQ_GLU` (`1fc561dd6`, gałąź duo): pp512 972,9 → 959,8 (−1,3%), pp2048 981,9 → 972,5 (−1,0%), KLD PASS (`~/qwen-opt/queue/logs/duo-r5-bench.log`).
- przeniesione 2026-11-25: wolniej

### K-009 · Przegląd configu MMQ na RDNA3 metodą wariantów jak FA 83 (maska `GGML_HIP_MMQ_VAR`: Q4_K/Q6_K/IQ4_XS, `sched_barrier`, offsety u32, prefetch K, skale x f32 w LDS)
- data: 2026-11-09 (skale x f32: 2026-10-15)
- źródło: `R/70-fa-d256-jak-to-zrobilismy.md:185` (#2), `R/68d-swieze-od-spolecznosci.md:138-139`, `Q/STATUS-NEXT.md:49`, [[sweep-wariantow-kernela]]
- test: ISA na CPU (`isa.sh`). XTX: `test-backend-ops perf -o MUL_MAT` Q4_K/Q6_K, md5 12k jak `Q/fa-d256/md5.sh`, ABBA `llama-bench -p 512,4096`; każdy krok ≤ 10 min (szablon `~/qwen-opt/fa-d256/`)
- zysk: pp ≤ 32k +2…4%, fill 255k +1…2% [INFERENCE]; MMQ to 63–81% prefillu, jedyna dźwignia prefillu przy krótkich promptach
- ryzyko karty: brak
- priorytet: średni (prefill; w pakiecie z K-010)
- **wynik 2026-11-25 19:31–19:55 (XTX, `~/wt/k009` f7d9d3286, PM4=0):** gate test-backend-ops PASS, md5 12k równe (816334e4) dla wszystkich masek. perf n=512 ABBA vs VAR 0: VAR 2 q4_K −6,6%, q6_K +0,1%, iq4_xs −5,6%, Qwen −3,2%; VAR 8 q4_K −29,9%, Qwen −17,0%; VAR 10 q4_K −5,3%, Qwen −2,7%. Żaden wariant nie wygrywa (select: NONE). `sched_barrier` po WMMA i prefetch kafla y do rejestrów szkodzą na gfx1100.
- przeniesione 2026-11-25: bez zysku

### K-166 · Maya: fuzje i sztuczki kerneli dekodu z Nib (LGQ8, ACOMB, ROUTE, MIX, HEAD)
- data: 2026-11-25 (gałąź Mai `k166-nibk` cd79d669, przełączniki `IK2_K166_*`; launche na token 689 → 595)
- wynik (rep2 Q1 T=0 / Q6 T=0,7 / L2k, XTX): produkcja 129,5–129,9 / 114,1–114,2 / 107,7; gałąź bez przełączników 128,6 / 113,1 / 107,0; LGQ8 125,2 / 110,4 / 104,2 (−2,6%); ACOMB 127,7 / 112,6 / 106,1; ROUTE 128,8 / 113,3 / 107,0; MIX 129,1 / 113,7 / 106,9 (parytet DIFF 9/11); HEAD 128,6 / 113,1 / 107,0; wszystkie 124,3 / 109,2 / 102,9 (−3,4%). Parytet 11/11 dla LGQ8, ACOMB, ROUTE, HEAD.
- wniosek: odrzucone. −94 launchy na token nic nie dały, bo dekod Mai bez spekulacji (127–130 t/s) już jest szybszy niż Nib (118). Mniej bajtów bramek (LGQ8, 226 → 60 MB/tok) dało wolniej, czyli te kernele nie były ograniczone pasmem. Przewaga Nib jest w spekulacji, patrz K-158.

### K-043 · Profil i optymalizacja atencji draftu MTP przy długim kontekście (~1,3 ms/krok przy 199k), np. pamięć MASW (ujścia + okno + sloty)
- data: 2026-11-07
- źródło: `R/68c-dlugi-kontekst-gdn.md:144` (#10), [[2026-11-08-kvq-once-profil]] (`:92`)
- test: offline symulacja akceptacji MTP z oknem 128 + sloty; potem spec_sweep + xtxbench 199k. Wymaga treningu adaptera.
- zysk: sufit +3…5% przy 255k minus spadek akceptacji [SZACUNEK]
- ryzyko karty: brak
- priorytet: niski (trening, niepewne; samo okno MTP to KILL, K-090)
- przegląd 2026-11-24: nieaktualne (The entry itself says "the MTP window alone is a KILL (K-090)". The rest (MASW sinks+slots) needs adapter training, has an uncertain ceiling of +3–5%, and has no data or code. Recommend moving it to Odrzucone, or to an owner decision if training shou)

### K-048 · Mikrobatch prefillu `-ub 1024` dla Qwena (po odzyskaniu VRAM)
- data: 2026-10-12 (A7)
- status: **czeka na decyzję**, jeśli md5 ≠ (zmiana ub zmienia kolejność sum)
- źródło: `Q/NOTES.md:218` (ub 2048 pp +3%, OOM przy 204800), `R/63-SYNTEZA.md:84`
- test: XTX md5 greedy 12k ub 512 vs 1024 (jeśli różne → do Odrzuconych); jeśli równe, `llama-bench -p 4096 -ub 1024` + szczyt VRAM przy fill 255k osobnym jobem
- zysk: pp4096 +3…8% [SZACUNEK]
- ryzyko karty: **VRAM OOM przy 262k**
- priorytet: niski (OOM, numeryka; po K-022/K-034)
- wynik 2026-11-21: **ub 1024 zmienia wynik i nie przyspiesza → odrzucić.** md5 greedy (prompt 12k, T=0, 256 tok., konfiguracja produkcyjna na porcie testowym, kolejność 512/1024/1024/512): ub 512 `8f23c7d9` w obu przebiegach, ub 1024 `669c414a` w obu, czyli inna kolejność sum. Prefill 12k: 894,7 → 871,1 t/s (−2,6%). `llama-bench` pp4096 (PM4 0, FA 83, ABBA): 1003,1 → 994,5 t/s (−0,9%). VRAM po starcie serwera przy ctx 262144: 22955 → 23352 MiB (+397 MiB). Przy 255k z ub 512 zostaje 1193 MiB zapasu, więc wypełnienia 255k z ub 1024 nie uruchamiałem (ryzyko OOM, a zysku i tak nie ma). Źródło: `~/qwen-opt/queue/logs/k048-md5.log`, `k048-bench.log`, skrypt `Q/k048/k048.sh`.
- przeniesione 2026-11-24: wynik bez zysku albo nie wdrażamy (wyżej)

### K-049 · ROCm 10.1 na gfx1100: md5 + hash logitów + pomiar `kvq` (spill 8 VGPR)
- data: 2026-10-16 (raport 13), 2026-11-05 (63c)
- źródło: [[rocm-10-1]] (`:28-30`), [[lekcja-rocm10-lds-128kb]]
- test: build topki na `~/opt/rocm-10.1` (CPU), XTX md5 greedy/long 32k + xtxbench t1; ≤ 10 min
- zysk: nieznany (RDNA-FAST: 10.1 +3,1% vs 7.2 na innej bazie); `kvq` może zwolnić przez spill
- ryzyko karty: nowy runtime + PM4 (możliwy fault/reset)
- priorytet: niski (niepewny zysk, ryzyko)
- **wynik 2026-11-24 15:33–15:36 (XTX, topka-q70 3191b25 zbudowana na ROCm 10.1, PM4=0, xtxbench t1):** bramka md5 świeżego startu PASS (c4708318 / 6f14e814), ale xtxbench: decode@1,7k 121,28 → 120,88 (−0,33%, szum), **prefill@32k 875,9 → 861,3 (−1,67%, LOSS)**, md5 greedy czatu inny (d36768ee → 662da515). Werdykt **KILL**: ROCm 10.1 wolniejszy w prefillu (zgodne z ISA: spill `flash_attn_ext_kvq<256,8,Q4_0>` 0→36 B). Zostajemy na 10.0; 10.2 to K-130.
- przeniesione 2026-11-24: wynik bez zysku albo nie wdrażamy (wyżej)

### K-130 · Topka zbudowana ROCm 10.2 (hipcc/LLVM) vs 10.0: czy nowy kompilator przyspiesza nasze kernele
- data: 2026-11-19
- źródło: blog ROCm 10.2.0 (Telegram „gpu” 2026-11-19); wcześniej 10.1 nic nie dało ([[stos/rocm-10-1]])
- test: ROCm 10.2 w osobnym katalogu na jaroserverai (bez ruszania /opt/rocm 10.0 produkcji), rbuild topki tym samym commitem; `test-backend-ops` MUL_MAT/FA bitowo + xtxbench ABBA dekod 1,7k i prefill 32k, md5 T=0; ≤ 10 min karty
- zysk: nieznany (AMD nie wymienia gfx1100 GEMV/FA); próg przyjęcia ≥ 3%
- ryzyko karty: brak (PM4=0 w teście); ryzyko systemu: druga instalacja ROCm, tylko za zgodą właściciela (~3 GB)
- priorytet: niski
- **wynik 2026-11-24 15:40–15:44 (XTX, topka-q70 3191b25 na ROCm 10.2 z `~/rocm-10.2`, PM4=0):** md5 świeżego startu PASS (c4708318 / 6f14e814); test-backend-ops MUL_MAT 2496/2496, FLASH_ATTN_EXT hsk=256 173/173; xtxbench t1: decode@1,7k 122,38 → 121,08 (−1,07%, w szumie), prefill@32k 869,5 → 868,2 (−0,15%, w szumie). Werdykt xtxbench KILL: brak zysku ≥ +1%. Uwaga: md5 greedy czatu ramienia B (662da515) jest ten sam dla 10.1 i 10.2, więc różnica md5 pochodzi z przebudowy lub ścieżki uruchomienia, nie z ROCm (do wyjaśnienia przy następnym buildzie). Zostajemy na 10.0.
- przeniesione 2026-11-24: wynik bez zysku albo nie wdrażamy (wyżej)

### K-140 · Wyścig Maya: pomiar gałęzi Gemini `gem-maya` (runda 1: IK2_G_WEXP/WCOLS/WROUTE/WLOOP/DGRAPH/DFAST)
- data: 2026-11-24 (runda maya-g1c, commit 96f45fc)
- stan: nvcc czysto (kernels, main, draft); Gemini nie dodał testów; prognoza autora 135–155 t/s przy T=0,7 [jego szacunek, nasz model ze śladu daje dużo mniej: te same pomysły u Kernela dały DSpark 102,2 → 106,7, lookup 112,9]
- test (~35 min karty): build `wt-gem-maya` (jak build-kr1.sh), `qwen-opt/inkling/race-gem1.sh` + `race-gem1.jobs`: testy kerneli z/bez IK2_G_*, rep2: bez przełączników lookup / DSpark, wszystkie IK2_G_* DSpark on / auto / lookup, parytet greedy drafting wył. vs wł.
- baza: produkcja 113,2 t/s T=0,7 (AtomicChat, lookup)
- ryzyko karty: nowe kernele HIP bez testów → najpierw g1-test, przy page fault stop
- priorytet: wysoki (wyścig)
- **testy kerneli 2026-11-24 14:33 (gałąź Gemini 96f45fc):** NIE przechodzą — `window experts Q8_0 (row dots), 2/5/8 tokens: h and y the one-token path's to the bit` FAIL także BEZ przełączników IK2_G_* (zmiana Gemini psuje domyślną ścieżkę Q8_0 okna, czyli plik unsloth warstwy 20–23), plus znany próg NVFP4. Reguła „bit w bit, gdy wyłączone” złamana.
- **wynik 2026-11-24 14:33–14:36 (XTX, AtomicChat AD-Q4_K, KV q4, rep2 mediana 5, ta sama sesja):** bez przełączników lookup Q1 / T=0,7 / L2k 127,5 / 112,5 / 106,9 (powtórka 127,8 / 112,5 / 106,9); **wszystkie IK2_G_* + lookup 130,4 / 114,3 / 108,3 (+2,3 / +1,6 / +1,3%)**; auto 129,9 / 114,2 / 108,2; DSpark bez przełączników 157,3 / 101,8 / 102,2, z przełącznikami 117,0 / 107,4 / 102,8 (T=0,7 +5,5%, ale krótkie T=0 −26%). Parytet greedy drafting wył./wł. z przełącznikami: identyczne (11/11). Kernel race runda 1 (`IK2_K_*`): T=0,7 +0,6%. **Gemini prowadzi o ~1 pkt proc.**, ale ścieżka Q8_0 okna jest niedokładna nawet bez przełączników (plik unsloth) — przed wdrożeniem do naprawy.
- przeniesione 2026-11-24: wynik bez zysku albo nie wdrażamy (wyżej)

### K-145 · Maya: kontekst draftera zwykłych kroków zapisywany partią (`IK2_K_LAZYCTX`) — podatek draftera
- data: 2026-11-24 (K-139: drafter wczytany kosztuje −4% na każdym kroku)
- **wynik 2026-11-24 15:21–15:25 (XTX, gałąź `k175-lazy` e106fe7, AtomicChat, KV q4, ABAB):** odpowiedzi identyczne (11/11); DSpark z kontrolerem T=0,7 **100,7 / 100,6 → 102,7 / 102,6 (+2,0%)**, Q1 157,9 bez zmian, L2k 103,9 / 102,9 → 103,4 / 103,1; lookup + drafter wczytany T=0,7 100,7 / 100,8 → 102,7 / 103,7. Podatek zmniejszony o połowę, ale DSpark przy T=0,7 nadal poniżej samego lookupu (112,4).
- przeniesione 2026-11-24: wynik bez zysku albo nie wdrażamy (wyżej)

### K-146 · Maya: drafter tylko dla zapytań greedy (`IK2_K_DRAFT_T0`), przy T>0 lookup bez kontekstu draftera
- data: 2026-11-24 (K-139: DSpark +24% przy T=0, −11% przy T=0,7)
- test: `qwen-opt/inkling/k146.sh` ABBA prod vs k175-lazy z `IK2_K_LAZYCTX=1 IK2_K_DRAFT_T0=1`; parytet greedy
- **wynik 2026-11-24 15:58–16:10 (XTX, ABBA, produkcja = adq4k-dpp):** odpowiedzi identyczne 11/11; Q1 130,1 / 129,7 → **157,6 / 157,6 (+21%)**, T=0,7 114,1 / 114,1 → 112,2 / 112,2 (**−1,7%**), L2k 108,0 / 108,1 → 102,9 / 104,3 (−4%, greedy z drafterem na długim kontekście). Wniosek: przy T>0 sama obecność draftera nadal kosztuje 1,7% (gałąź 1.1.75 bez DPP + rezerwa VRAM, do rozdzielenia), a na długim greedy drafter przegrywa z lookupem. **Nie wdrażamy** (metryka główna T=0,7). Następny krok, jeśli wrócimy: DPP w gałęzi lazy i drafter tylko dla krótkiego kontekstu (< 1k).
- przeniesione 2026-11-24: wynik bez zysku albo nie wdrażamy (wyżej)

### K-052 · HRX (Lemonade `hrx-b99`) jako referencja kerneli: tg128/pp512/pp4096 obok topki
- data: 2026-11-07
- źródło: `R/68a-rdna3-kernele.md:125` (4.7)
- test: XTX `llama-bench -fa 1 -p 512,4096 -n 128 -r 3` HRX vs topka, eco (~30 min → 3 joby); wymaga buildu i pobrania HRX
- zysk: 0% wprost; wzór do portu, jeśli HRX wygra prefill (producent: +30–50% vs HIP upstream)
- ryzyko karty: nieznany runtime (inne kolejki, bez gpu-guard)
- priorytet: niski (wiedza)
- **wynik 2026-11-24 15:44–15:58 (XTX, HRX `hrx-b99` z ROCm/ggml-staging-automation: hrx-system 32b86d4, llama.cpp AMD-Ecosystem 2ba2ddc, build gfx1100 na ROCm 10.1, KV f16 w obu ramionach):** smoke OK (443 słowa, tekst sensowny), ale sam smoke 370 s; llama-bench `-p 512,4096 -n 128 -r 3` w ramieniu HRX przekroczył 200 s w obu rundach (produkcja: ok. 30 s na rundę) i nie dał ani jednego wiersza (stderr pusty, ubity przez timeout). Wniosek: HRX na tym buildzie jest co najmniej ok. 6× wolniejszy albo wisi przy benchu; bez gfxhub fault. Odłożone do nowego wydania HRX (dalszy czas karty nieopłacalny).
- przeniesione 2026-11-24: wynik bez zysku albo nie wdrażamy (wyżej)


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
