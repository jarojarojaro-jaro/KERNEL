# Stan prac: punkt kontrolny 2026-10-16, 18:10 UTC

**Co się stało:** o 17:48 UTC omp padł (`panic: Segmentation fault at address 0x0`, błąd Bun 1.4.3, nie naszego kodu; log `~/.omp/logs/omp.2026-10-16.1235.log`). Wszyscy agenci zostali „zaparkowani” w połowie pracy. Na życzenie użytkownika **nic nie jest kontynuowane**: lokalne testy GPU zatrzymane, maszyny w chmurze usunięte po ściągnięciu wyników.

**Stan zasobów w chwili zapisu:**
- XTX: wolny (GPU 0%, VRAM 0%), blokada `/tmp/gpu.lock` wolna. Produkcja `~/llama-opt` bez zmian (`amd-opt` @ `f61994f58`).
- Chmura: **0 instancji** na Vast i RunPod. Wyniki ściągnięte przed usunięciem: 3060 → `~/qwen-opt/cloud/results/quantkld-20261016/` i `results/3060-20261016/opt/`, A40 → `results/quantkld-20261016/pod-final/`.
- Podgląd strony: http://127.0.0.1:18433/pl/ (działa, build aktualny).

**Jak wznowić:** każdego agenta da się obudzić wiadomością (`write agent://<Nazwa>`) z poleceniem „wznów od punktu kontrolnego w `~/KERNEL/STAN-PRAC.md`, sekcja <Nazwa>”. Wszystkie GPU pod `flock /tmp/gpu.lock flock /tmp/quiet.lock`, sprawdzić wcześniej, czy serwer na :8080 nie działa.

## Gotowe przed awarią (raporty w `product/research/`, wszystko w wiki, wypchnięte)
| Wątek | Wynik | Raport |
|---|---|---|
| kvq na CUDA | 3090 przy 64k: Qwen +36.8%, LFM +30.4%, Qwen+MTP +27.6%; KLD 4/5 (Qwen plain +2.53σ, do powtórki `--chunks 4` przy następnym wynajmie 3090) | 16c |
| Magnitude vs nasz fork | LFM: wygrywamy +30–40%; Qwen: remis przy pisaniu, oni wygrywają kopię/kod (sufit draftu); Nemotron KLD PASS | 16d, 14 §13 |
| Co Magnitude robi dobrze | adaptacyjna szerokość draftu 2/4/8/16, sprzężone losowanie; brak lookupu; słabi po polsku | 16i |
| Fabryka v1 | claim cards, ledger z łańcuchem hashy, weryfikator, 36 reguł, 57 testów | 16h |
| Landing v2 (commit `22bce75`) | hero z wyścigiem Qwena, /wyniki, /karty | — |

## W toku: stan każdego wątku

### BitExactSpec: bit-exact MTP (`~/wt/batchinv`, gałąź `batch-invariant` @ `365af3e5e`, wszystko zacommitowane)
- Naprawiona regresja −6% (przyczyna `ce2105d32`, poprawka `02813c1c5`); `365af3e5e`: maskowane wiersze z zerowego wiersza w pamięci (14 → 1 wyciekły rejestr).
- **Run 4 (przerwany w ostatniej sekcji, `/tmp/bxv/summary.txt`, `/tmp/bxv-run4.log`):**
  - greedy: domyślny `new` i `v070` = `c4708318` ✓; bit-exact plain = MTP n_max 1–7 (`5fdc8a14`) ✓;
  - tg128: produkcja 43.17/42.91, new 42.96/43.02, bx 41.79/41.79 t/s;
  - pp5@32k: produkcja 152.1/156.8, new 152.3/150.4, bx 133.8/134.5;
  - **spec_sweep (flagi produkcyjne): produkcja 107.7 / new 109.0 / bx 108.3 / produkcja 107.6 t/s** → bit-exact w MTP bez kosztu;
  - longspec ~27k (decode t/s): produkcja 111.77/111.85, new 113.2, bx 102.66 (−9%).
- **Zakończone.** Raport 12 §13 + „Do bazy wiedzy” uzupełnione. Czeka na decyzję użytkownika o wdrożeniu (przełącznik domyślnie wyłączony; „new” = produkcja).

### XtxLookupTail: ogon z lookupu za MTP (`~/wt/lookup`, gałąź `lookup-tail`, zacommitowane `6e12530cc` + `586f1d596`; build `build-hip` = `586f1d596`; STOP GPU 2026-10-18 ~23:50 UTC)
- Przełączniki: `LLAMA_SPEC_LOOKUP` (0 wył., 1 log, 2 ogon, 3 ogon + łańcuchy), `_W` (8), `_MMIN` (6), `_ADAPT=1` (kontroler 5/8/16).
- Gotowe: E1, E2 (`e2/e2_table.txt`), E3 copy/mvs/long/sweep (`logs/e3_summary.txt`), E4 W8/W16/adapt na mvs/copy/long (`logs/e4_summary.txt`). Tekst T=0 identyczny we wszystkich ramionach (W8, W16, adapt) na 11/11 promptach.
- Liczby: mvs wył. 166.2 → W8+łańcuchy 255.6 (+54%) → W16 400.9 / adapt 401.6 t/s (×2.41) przy T=0; T=1 166.1 → 231.0 → 376 t/s. Kontroler zawsze wybiera 16 (= W16).
- **Problem:** spec_sweep (6×3, seedy 1–3) tryb 3 W8: ms/krok 29.06 → 29.13 (+0.2%), ale t/s −1.1% (8 ogonów na 2258 kroków zmieniło tekst T=1 w pl-proza/pl-kod; kill 15b −0.5%). Rozstrzygnąć na nowych seedach.
- **Do zrobienia po wznowieniu (GPU):** `mkdir -p /tmp/lookup-run && cp ~/qwen-opt/lookup/{arm.sh,copy_bench.py,copy_prompts.json,e4_ab.sh,vram_ok.sh} /tmp/lookup-run/ && cd /tmp/lookup-run && export LOGDIR=~/qwen-opt/lookup/logs BLOCK_S=900 && ./e4_ab.sh sweep && I0=10 ./e4_ab.sh long && I0=10 ./e4_ab.sh copy` (sweep: A B D D B A, seedy 4–9; long/copy: powtórki ramion odrzuconych w oknie locków 23:18–23:30 i przy 8080; odrzucone dane już w `logs/discarded/`).
- Potem raport `~/KERNEL/product/research/16b-lookup-tail.md` (jest szkic nagłówka) i `ab_summary.py logs --prefix e4-`.

### XtxPm4Pdl: PM4 bez barier + prefetch — **ZAKOŃCZONE 2026-10-18 ~22:30 UTC** (`~/wt/pm4pdl`, gałąź `pm4-pdl`, commit `3a008359b`)
- Raport: `product/research/16a-pm4-pdl.md` (z „Do bazy wiedzy”). Wyniki: `~/qwen-opt/pm4pdl/x1/bench4.log`, `x2/ab4.log` (2 ważne rundy).
- X1 kill (−0.11 µs przy 1024 bl.), X2 kill (górna granica +12.0%, realnie ≈ +2.9% [SZACUNEK]), X3 kill (+0.2…+0.6% szum, 16 MiB −2.4%). Qwen nie testowany. Nic do produkcji. Brak działających procesów.

### XtxQuickWins: szybkie testy — **ZAKOŃCZONE 2026-10-18 ~23:55 UTC** (`~/wt/quickwins`, gałąź `quickwins` @ `7369380bf`)
- Raport: `product/research/16f-xtx-szybkie.md` (z „Do bazy wiedzy” i proponowanym diffem `run-llm.sh`). Brak działających procesów.
- E1 LFM `-b/-ub 2048` **wygrywa**: pp4096 +17%, TTFT ≥8k −15%, VRAM +0.5 GB; KLD ub2048 vs ub512 0.068 = tyle samo co dowolna zmiana podziału batcha (także upstream).
- E2 blok MTP: IQ4_XS zostaje (5 seedów: 113.2 vs Q6_K 109.4 t/s).
- E3 hak MTP: sam hak 2.2–2.6% TTFT → złożenie nie warte; checkpoint stanu Qwena ~94–104 ms × 2 na prompt to większy cel; pinned staging bez efektu (cofnięte).
- E4 cache agenta: przyczyna = obce zapytanie + `f_keep < 0.25`; `LLAMA_SERVER_CACHE_SHARE_MIN=1024`: Qwen 8.0 → 1.6 s, LFM 1.36 → 0.23 s (md5 bez zmian). E5: slot save/restore wykonalny (Qwen 53k odczyt 2.5 s vs ~61.5 s prefillu).
- Niezmierzone przez stop GPU: md5 z `LLAMA_STATE_PINNED` (kod cofnięty, więc zbędne).

### XtxLfmMoe: pasmo MoE w LFM — **ZAKOŃCZONE** (raport `product/research/16g-lfm-moe-pasmo.md`; gałąź `opt-lfmmoe` @ `7c5b2a116`)
- `GGML_HIP_MOE_GU_BLOCK` bitowe (hashe, md5 894e56e4, test-backend-ops OK). LFM llama-bench +0.33% (poniżej progu +0.7%), spec_sweep +0.2%, Uncensored +1.39%; usuwa rozrzut między procesami. Scalenie do amd-opt: do decyzji.

### CoupledSampling: sprzężone losowanie E-X4 (`~/wt/coupled`, gałąź `opt-coupled`, commity `760ee6990`, `3f25fc204`; STOP GPU 2026-10-18 ~23:45)
- Kod za `LLAMA_SPEC_COUPLED` (1: cel Gumbel-max kluczowany (seed, pozycja, token) + draft MTP z szumem celu, op `GGML_OP_GUMBEL_MAX`; 2: cel sprzężony + draft greedy; `LLAMA_SPEC_COUPLED_DT`). Poprawność: test CPU OK, `test-backend-ops GUMBEL_MAX` 152/152 (build 1 i 2), greedy md5 off/on = `c4708318`/`6f14e814`.
- **Run3 (`logs/`, 3 seedy × 4 bloki/tryb, ważny):** T=1 tok/krok off 3.00 / tryb 1 3.16 / tryb 2 3.11, ms/krok 28.12 / 28.57 / 28.16; teksty per tryb stałe między blokami, więc off vs on to w dużej części szum tekstu (tryb 2 vs off +3.6% tok/krok przy tym samym drafcie). Identyczność (`logs/ident.jsonl`): tryb 1 vs 2 akceptacja 0.404 vs 0.377 (T=1).
- **Run4 (`logs4/`, seedy 4–23):** ważny tylko b1-m0-a3; b2-m1-a2 odrzucony (okno 23:18–23:30, `logs4/discard.txt`); reszta przerwana przez STOP.
- `3f25fc204` (szybszy kernel) zbudowany w `build-hip`, **NIEsprawdzony na GPU i NIEzamrożony** (`inst` = build 2).
- **Wznowienie:** (1) `cd ~/wt/coupled/build-hip/bin && LD_LIBRARY_PATH=.:/opt/rocm/core-10.0/lib flock /tmp/gpu.lock flock /tmp/quiet.lock timeout 900 ./test-backend-ops -o GUMBEL_MAX -b ROCm0` → jeśli OK: `cp -a llama-server ~/qwen-opt/coupled/inst/bin/ && cp -a *.so* ~/qwen-opt/coupled/inst/lib/`; (2) `cd ~/qwen-opt/coupled && mv logs4 logs4-old; export LOGDIR=$HOME/qwen-opt/coupled/logs5 SEEDS=$(seq -s, 4 23); (frozen/driver.sh ~/qwen-opt/coupled/frozen/arm.sh c1-m0:0:sweep c2-m1:1:sweep c3-m2:2:sweep; EXTRA_ENV=LLAMA_SPEC_COUPLED_DT=1.3 frozen/driver.sh ~/qwen-opt/coupled/frozen/arm.sh c4-m1dt13:1:sweep; frozen/driver.sh ~/qwen-opt/coupled/frozen/arm.sh c5-m2:2:sweep c6-m1:1:sweep) > ex4-run5.log 2>&1`; (3) `python3 analyze.py logs5 ex4-run5.log`; raport `~/KERNEL/product/research/16k-sprzezone-probkowanie.md` (szkielet gotowy, §0/4/5/6/7 do wypełnienia).

### MagnitudeVulkanXtx: Magnitude przez Vulkan na XTX — **ZAKOŃCZONE** (raport `product/research/16j-magnitude-vulkan-xtx.md`)
- Dane `~/qwen-opt/magnitude-xtx/` (`x/xbench.jsonl`, `results.txt`). Qwen 27B: my ×1.94–×2.22 (sweep 100.0 vs 50.1, copy64k 141.2 vs 63.7, code 170.0 vs 87.7 t/s); LFM Q4_K_M: ×1.42–×2.24. Autotune Magnitude 67/67 defaults. Nic do zrobienia.

### QuantKLD: jakość nowych kwantów (chmura usunięta, wyniki lokalnie)
- **KLD na A40** (`results/quantkld-20261016/pod/kld.json`, pełne w `pod-final/`), wiki vs Qwen BF16: U3 (UD-Q3_K_XL) 0.039, A3 0.040, ISTA I4 0.073, I2 0.164, Saluki 0.257, Bonsai 0.352; Swift W4 0.072–0.076, W3 0.119, W2 0.164–0.166, W1 0.222; szum Q8_0 0.0038.
- Zadania (20 promptów): W4 1.0, W2 0.95, I2/I4/Saluki 0.85; U3 i Bonsai — sprawdzić `pod-final/res/tasks/`.
- Prędkość 5060 Ti (`5060ti/speed.json`): U3 29.1 → MTP 51.7 t/s, I4 i W4 30.3 → 50.0.
- Prędkość 3060 (`results/3060-20261016/opt/`): Saluki 17.2 → MTP 24.3 t/s; Bonsai repack 27.6 t/s (sweep niedokończony).
- **Do zrobienia (CPU):** zebrać wszystko w raport 16e. Bez nowego wynajmu, chyba że użytkownik zdecyduje inaczej.

### LandingWow: strona (`~/KERNEL/app`, wszystko zacommitowane; build `landing/build` = runda 12)
- Rundy 9–12 zrobione i sprawdzone: svelte-check 0/0, hydration 0, hero QA 40/40, axe 0, Lighthouse mobile /pl/ 87 (LCP 3.6 s). Bit-exact na stronie z przebiegu 4 (`research/12-…md:325-326`).
- Juror utknął na ~7 / 6 / 7 od rundy 6; cel 8/8/8 nieosiągnięty, uwagi jurorów częściowo sprzeczne z wcześniejszymi i z życzeniami użytkownika. Otwarte: powtarzalny środek strony (drugi „set-piece”), szablonowy onboarding, balans wykresu jakości, liczba pigułek „źródło”. Skrypty QA: `app/landing/scripts/qa/`.

### WikiIngest
- Wiki aktualne do 16c/16d/16i/16h + naprawa regresji (381 notatek, lint 0/0). Czeka na kolejne raporty.

### CudaKvq: E1 port `kvq` na CUDA (`~/wt/kvq-cuda`, gałąź `kvq-cuda`, ostatni commit `678473a27`, czysty) — ZAKOŃCZONE
- Raport `product/research/16c-kvq-cuda.md` (§1–8 z 2026-10-16, §9 z 2026-10-18, „Do bazy wiedzy” pkt 1–10). Wyniki: `~/qwen-opt/cloud/results/kvq-cuda-20261016/` (§9: `kld-c5/`).
- §9: bramka KLD Qwena na 5 × 8192 tok. FAIL na ogonie (99.9% ×2.04; kontrola szumu ×1.41). Wszedł wyjątek: decode 1 tokenu D256 q4_0 domyślnie na vec (`GGML_CUDA_KVQ_N1_D256_Q4=1` włącza kvq). Pomiar: tg64@64k 27.29 / kvq 36.99 / wyjątek 27.40 t/s; pp5@64k 103.18 / 139.27 / 141.83.
- Niezmierzone: KLD wariantu z wyjątkiem (przerwane przy niszczeniu; przy ub 1 z konstrukcji = vec) i serwer MTP@64k z wyjątkiem. Oba wymagają nowego wynajmu, więc najpierw zgoda.
- Chmura: wszystkie instancje zniszczone (ostatnia 56603163), watchdogi zabite, 0 naszych instancji. Koszt E1 łącznie ~$1.40.

## Odłożone (decyzja użytkownika)

### Nemotron 3.5 Bolt na RTX 3090 — „odpuszczamy, wrócimy kiedyś”
- Stan: raport 14 (kampania skrócona do ~2.3 h z 10 h). Upstream najlepsze flagi + DFlash 131.4 t/s, nasz fork z łatkami 141.1 t/s (×1.07; ×1.62 vs domyślne 87.2). KLD `TOPK_MOE_NP2` PASS (14 §13). Kod: `nemotron-3090` @ `e46d34e0e` (`~/wt/nemotron-opt`, czysty).
- Do zrobienia przy powrocie (14 §10): kernel IQ2_XXS MMVQ (320–400 vs 805 GB/s), replay stanu Mamby przy weryfikacji, szybszy `topk_moe`, FA q8_0 przy GQA 16:1 / kvq z CUDA, A/B per łatka, długi kontekst 128k, sweep n_max. Kod pisać lokalnie przed wynajmem, potem jedna sesja na 3090.

## Pozostałe po wątkach (do posprzątania przy wznowieniu)
- `~/.cargo` (Rust, do budowy Magnitude), `~/qwen-opt/magnitude/` (8.4 GB źródeł i buildów).
- Niezacommitowane worktree: `lookup`, `pm4pdl`, `quickwins`, `coupled` — nie usuwać.
