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

### XtxLookupTail: ogon z lookupu za MTP (`~/wt/lookup`, gałąź `lookup-tail`, zacommitowane `6e12530cc` + `586f1d596`; build `build-hip` = `6e12530cc`, kontroler jeszcze NIEzbudowany)
- Przełączniki: `LLAMA_SPEC_LOOKUP` (0 wył., 1 log, 2 ogon, 3 ogon + łańcuchy), `_W` (8), `_MMIN` (6), `_ADAPT=1` (kontroler 5/8/16, commit `586f1d596`, niezmierzony).
- E1 gotowe: czat 0.5% pozycji z trafieniem ≥ 8; kopia/edycje 83.9%, P(MTP d1 | lookup d1) 0.995 (`~/qwen-opt/lookup/logs/e1-*.stats.json`).
- Greedy md5: LOOKUP=0 plain `c4708318` / MTP `6f14e814`; LOOKUP=1/2/3 MTP `6f14e814`. Na zestawie copy przy T=0 tekst identyczny w ramionach A/B/C (6/6).
- E2 gotowe (`~/qwen-opt/lookup/e2/e2.jsonl`, mediana próbek 3–5): V8−V5 = 2.47/2.75/3.25/3.79 ms, V16−V5 = 6.38/7.20/9.50/12.45 ms przy 2k/8k/32k/64k.
- E3 copy gotowe (ABC CBA): wył. 163.3 → tryb 3 230.6 t/s (+41.2%) T=0, 160.0 → 208.8 (+30.5%) T=1; tryb 2 +30.6% / +30.1%.
- **Pauza (reboot). Do zrobienia po wznowieniu:**
  1. `cd /tmp/lookup-run` (jeśli nie istnieje: `mkdir -p /tmp/lookup-run && cp ~/qwen-opt/lookup/{arm.sh,copy_bench.py,copy_prompts.json,e3_ab.sh,e2_bench.sh,vram_ok.sh} /tmp/lookup-run/`), potem `export LOGDIR=~/qwen-opt/lookup/logs BLOCK_S=600; for s in sweep mvs long; do ./e3_ab.sh $s; done 2>&1 | tee -a $LOGDIR/e3_run.txt` (z `~/wt/lookup/build-hip` = `6e12530cc`; NIE przebudowywać przed tym).
  2. Potem przebudować (`flock -s /tmp/quiet.lock nice -n 10 cmake --build ~/wt/lookup/build-hip -j6 --target llama-server`) i zmierzyć W16 oraz `_ADAPT=1` (`EXTRA_ENV="LLAMA_SPEC_LOOKUP_W=16 LLAMA_SPEC_LOOKUP_ADAPT=1"`) na mvs/copy/long + spec_sweep.
  3. Podsumowanie: `~/qwen-opt/.venv/bin/python ~/qwen-opt/lookup/ab_summary.py ~/qwen-opt/lookup/logs`; raport `~/KERNEL/product/research/16b-lookup-tail.md`.

### XtxPm4Pdl: PM4 bez barier + prefetch (`~/wt/pm4pdl`, gałąź `pm4-pdl`, commit `f19d4a050`, build `build-hip` aktualny; PAUZA 2026-10-18 ~20:25 UTC)
- X1 mikrobench gotowy (`~/qwen-opt/pm4pdl/x1/bench4.log`, czysty przebieg): kształt LFM 2048², 1024 bloki: B 4.775 → najlepszy PDL (relay ×16) 4.669 µs/kernel = **−0.11 µs < progu 0.5 → kill**. 1536 bl. −0.59, 2560 −1.09, 3072 −0.95 µs. Bez synchronizacji (dolna granica, złe wyniki) −1.7…−2.8 µs: synchronizacja zjada prawie cały zysk. Siatka 6144 (2× pojemność GPU): bez zakleszczenia, 0 wygaśnięć. Flagi RELEASE_MEM (CP): wygasają, odrzucone. Soak 10⁵ nieuruchomiony (zbędny po kill).
- X2 górna granica (`GGML_HIP_PM4_UB`, bez synchronizacji, złe wyniki), `x2/ab2.log`, **1 runda**: prod 294.84, build 294.07, UB conv 288.88, down 306.06 (+4.1%), mmvq1 303.25 (+3.1%), router 297.08, norm 297.19 t/s. UB conv,down,mmvq1,router,norm: taśma wisi (abort 10 s, `x2/comb.err`), też „all” nie mierzyć.
- **Ważne pomiary:** `x2/ab1.log` (1 runda, 3 konfiguracje: prod 291.35, build 293.13, UB conv 296.31) i `x2/ab2.log` (1 runda, 7 konfiguracji, wyżej). **`x2/ab3.log` NIEWAŻNY** (biegł w czasie pauzy, Main go nie liczy); tylko orientacyjnie: UB down 308/306, UB down,mmvq1 325.5 (+12%), TOUCH 1024–16384 KiB 294/290/290/284 (≤ build) → X3 prawdopodobnie negatywne, do potwierdzenia.
- Wniosek roboczy (do potwierdzenia ważnym pomiarem): górna granica UB down+mmvq1 ~+12%, ale X1 pokazuje, że synchronizacja zjada większość zysku na małych siatkach (1024 bl.: zostaje 0.11 z 1.7 µs), na większych ok. 40% (2560 bl.: 1.09 z 2.48 µs). Realny PDL [INFERENCE] ≈ +2–5%, przy progu +3%.
- **Wznowienie:** sprawdzić `pgrep -f "llama-server.*--port 8080"`; `mkdir -p /tmp/pm4pdl-run && cp ~/qwen-opt/pm4pdl/x2/frozen/*.sh /tmp/pm4pdl-run/ && sed -i 's/ab3.log/ab4.log/g' /tmp/pm4pdl-run/run3.sh && /tmp/pm4pdl-run/run3.sh` (2 rundy × 12 konfiguracji → `x2/ab4.log`; NIE nadpisywać ab3.log; TOUCH zostawić — X3 do potwierdzenia). Potem decyzja X2 wg powyższego wniosku i raport `~/KERNEL/product/research/16a-pm4-pdl.md` (jeszcze nienapisany).

### XtxQuickWins: szybkie testy (`~/wt/quickwins`, gałąź `quickwins`, zacommitowane: 50c3a2f2a, fc89bc486; PAUZA 2026-10-18 ~20:25 przed restartem)
- **E4, cache promptu:** omp 18.10.4 wysyła stały prompt systemowy (md5 `f3b2fed4`, 10194 zn., 11 narzędzi; data/cwd w wiadomości usera) i w `-p` żadnych zapytań pobocznych do llama.cpp (przechwycone `qw/capture_proxy.py`). Przeliczanie 7.3k na starcie sesji = slot zajęty przez obce zapytanie (inny klient, subagent, web UI) + reguła `f_keep < 0.25`. Łatka `LLAMA_SERVER_CACHE_SHARE_MIN=1024`: Qwen start sesji 8019 → 1612 ms, LFM 1357 → 230 ms (+`LLAMA_LFM2_MSG_SPANS=1`: 166 ms). Bez obcego zapytania już dziś trafia (LFM 554 ms, 502 tok.).
- E5 slot save/restore: LFM 53k tok. 553 MiB, zapis 0.37 s, odczyt 0.53 s; Qwen 2.28 GiB, zapis 1.99 s, odczyt 2.51 s, potem start 2.2 s zamiast 8.0 s.
- **E1 (LFM `-b 2048 -ub 2048` vs 512, ABBA):** bench pp4096 6108 → 7148 (+17%), pp16384 5654 → 6680 (+18%); TTFT 8k 1471 → 1254 ms, 32k 6668 → 5692 ms (−15%), 512 bez zmian; VRAM +498 MiB (18591 → 19089 MiB, ctx 131072). Wygrywa; brak KLD.
- **E2 (typ bloku MTP, głowa iq4_xs, 3 rundy ABA):** iq4_xs 106.4 t/s / 28.30 ms/krok; natywny Q6_K 108.5 / 28.96 (+2.0% t/s); q8_0 103.1 / 29.23. Tylko 2 seedy × 6 promptów.
- **E3:** TTFT MTP vs none +15.8% (2k), +8.3% (8k), +4.7% (32k); `LLAMA_MTP_HOOK_TIMING=1`: sam hak (dekod MTP + kopia) ~38 ms na 2k (~1.7%) → złożenie haka w graf da najwyżej ~2%; reszta różnicy w przebiegu celu z MTP (niewyjaśniona). `LLAMA_MTP_HOOK_SKIP=64` zbudowany do dekompozycji (niezmierzony).
- Greedy md5 z wyłączonymi przełącznikami = bazy (c4708318 / 6f14e814 / 894e56e4). Z włączonymi (g2): kolejka zabita, niezrobione.
- **Wznowienie:** `mkdir -p /tmp/qwq && cp ~/wt/quickwins/qw/blocks/*.sh /tmp/qwq/ && cd ~/wt/quickwins/qw && (shopt -s globstar; cat ~/KERNEL/wiki/**/*.md > kld.txt)`; potem `./seq.sh 0 "bash /tmp/qwq/g2.sh" "bash /tmp/qwq/e3d-none.sh" "bash /tmp/qwq/e3d-mtp.sh" "bash /tmp/qwq/e3d-skip.sh" "bash /tmp/qwq/e3d-skip.sh" "bash /tmp/qwq/e3d-mtp.sh" "bash /tmp/qwq/e3d-none.sh" "bash /tmp/qwq/k1.sh"` (k1 = KLD LFM ub 512 vs 2048/1024 + A/A). Opcjonalnie E2 z `SEEDS=1,2,3,4,5` (iq4 vs native, ABBA przez `./sweep.sh`). Potem raport `~/KERNEL/product/research/16f-xtx-szybkie.md`.

### XtxLfmMoe: pasmo MoE w LFM — **ZAKOŃCZONE** (raport `product/research/16g-lfm-moe-pasmo.md`; gałąź `opt-lfmmoe` @ `7c5b2a116`)
- `GGML_HIP_MOE_GU_BLOCK` bitowe (hashe, md5 894e56e4, test-backend-ops OK). LFM llama-bench +0.33% (poniżej progu +0.7%), spec_sweep +0.2%, Uncensored +1.39%; usuwa rozrzut między procesami. Scalenie do amd-opt: do decyzji.

### CoupledSampling: sprzężone losowanie E-X4 (`~/wt/coupled`, gałąź `opt-coupled`, commit `760ee6990`; pauza przed rebootem 2026-10-18)
- Kod za `LLAMA_SPEC_COUPLED` (1: cel Gumbel-max kluczowany (seed, pozycja, token) + draft MTP z szumem celu przez nowy op `GGML_OP_GUMBEL_MAX` CPU+HIP; 2: cel sprzężony + draft greedy; `LLAMA_SPEC_COUPLED_DT` mnożnik temp. draftu). Build `~/wt/coupled/build-hip`, zamrożona kopia `~/qwen-opt/coupled/inst` (bin+lib dla `ROCM_DIR`).
- **Zrobione:** test CPU `build-cpu/bin/test-coupled-sampling 200000` wszystko OK (`~/qwen-opt/coupled/test-coupled-sampling-200k.txt`: chi² p > 1e-4, spekulacja == plain dla każdego seeda 0/20000, zabawka T=1 tok/krok greedy 1.60 → sprzężony 3.02); `test-backend-ops -o GUMBEL_MAX -b ROCm0` 152/152; greedy md5 przy off i =1: plain `c4708318`, MTP `6f14e814` (= baza, `~/qwen-opt/coupled/greedy/`).
- **Nie zrobione:** ABBA spec_sweep. Dwa podejścia przerwane: serwer pada na `hip-pm4.cu:664 tape of 823 dispatches did not complete within 10 s` (także w trybie 0, czyli nie przez kod sprzężenia; za każdym razem w tym czasie startował serwer użytkownika na 8080 [INFERENCE: rywalizacja o VRAM]); wstępnie (pojedyncze bloki, niepewne) T=1: off 107.0, tryb 2 115.7 t/s (`logs/run1-aborted/`). Port 18471 zajmuje inny agent → teraz 18493.
- **Wznowienie (GPU):** `cp ~/qwen-opt/coupled/arm.sh /tmp/coupled-arm2.sh && sed -i 's#here=$(cd "$(dirname "$0")" \&\& pwd)#here=$HOME/qwen-opt/coupled#' /tmp/coupled-arm2.sh && cp ~/qwen-opt/coupled/driver.sh /tmp/coupled-driver.sh && /tmp/coupled-driver.sh /tmp/coupled-arm2.sh id-m1:1:ident id-m2:2:ident s1-m0:0:sweep s2-m1:1:sweep s3-m2:2:sweep s4-m2:2:sweep s5-m1:1:sweep s6-m0:0:sweep s7-m1:1:sweep s8-m0:0:sweep s9-m2:2:sweep s10-m2:2:sweep s11-m0:0:sweep s12-m1:1:sweep > ~/qwen-opt/coupled/ex4-run3.log 2>&1` (każdy blok bierze locki sam; nieudane próby trafiają do `logs/bad.txt`), potem `python3 ~/qwen-opt/coupled/analyze.py`. Kill: < +2% t/s przy T=1. Potem raport `~/KERNEL/product/research/16k-sprzezone-probkowanie.md` i commit z liczbą.

### MagnitudeVulkanXtx: Magnitude przez Vulkan na XTX — **ZAKOŃCZONE** (raport `product/research/16j-magnitude-vulkan-xtx.md`)
- Dane `~/qwen-opt/magnitude-xtx/` (`x/xbench.jsonl`, `results.txt`). Qwen 27B: my ×1.94–×2.22 (sweep 100.0 vs 50.1, copy64k 141.2 vs 63.7, code 170.0 vs 87.7 t/s); LFM Q4_K_M: ×1.42–×2.24. Autotune Magnitude 67/67 defaults. Nic do zrobienia.

### QuantKLD: jakość nowych kwantów (chmura usunięta, wyniki lokalnie)
- **KLD na A40** (`results/quantkld-20261016/pod/kld.json`, pełne w `pod-final/`), wiki vs Qwen BF16: U3 (UD-Q3_K_XL) 0.039, A3 0.040, ISTA I4 0.073, I2 0.164, Saluki 0.257, Bonsai 0.352; Swift W4 0.072–0.076, W3 0.119, W2 0.164–0.166, W1 0.222; szum Q8_0 0.0038.
- Zadania (20 promptów): W4 1.0, W2 0.95, I2/I4/Saluki 0.85; U3 i Bonsai — sprawdzić `pod-final/res/tasks/`.
- Prędkość 5060 Ti (`5060ti/speed.json`): U3 29.1 → MTP 51.7 t/s, I4 i W4 30.3 → 50.0.
- Prędkość 3060 (`results/3060-20261016/opt/`): Saluki 17.2 → MTP 24.3 t/s; Bonsai repack 27.6 t/s (sweep niedokończony).
- **Do zrobienia (CPU):** zebrać wszystko w raport 16e. Bez nowego wynajmu, chyba że użytkownik zdecyduje inaczej.

### LandingWow: strona (`~/KERNEL/app`, wszystko zacommitowane; build `landing/build` = runda 8)
- Runda 8 zbudowana i sprawdzona: svelte-check 0/0, hydration 0 (14 stron), hero QA 40/40, axe 0 (20 stron × 2), Lighthouse mobile /pl/ 87 (LCP 3.6 s). Juror r8: 7 / 6 / 7 (cel 8/8/8 nieosiągnięty).
- Otwarte (juror r8): wyścig na mobile (szybki tor poniżej ekranu), zegar użyty 6×, jedna generyczna grafika GPU, nagłówki scen pod nawigacją, legenda jakości, drugi „wielki moment” po hero. Skrypty QA: `app/landing/scripts/qa/`.

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
