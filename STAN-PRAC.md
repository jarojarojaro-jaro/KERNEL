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
  - longspec ~27k: tylko `base` zrobiony (decode 111.8 t/s, prefill 948.7 t/s); `new` i `bx` **niezmierzone** (przerwane).
- **Do zrobienia:** powtórzyć tylko `longspec` (`cp ~/wt/bx-isa/validate.sh /tmp/bxv-frozen5.sh && /tmp/bxv-frozen5.sh longspec`); uzupełnić raport 12 §13 + wiki; potem decyzja użytkownika o wdrożeniu do produkcji.

### XtxLookupTail: ogon z lookupu za MTP (`~/wt/lookup`, gałąź `lookup-tail`, **zmiany NIEzacommitowane**, build `build-hip` gotowy)
- Zaimplementowane za `LLAMA_SPEC_LOOKUP` (0 wył., 1 log, 2 ogon, 3 ogon + łańcuchy bez draftera), `LLAMA_SPEC_LOOKUP_W` (domyślnie 8), `_MMIN` (6).
- E1 (log na sucho): na czacie ogon bezużyteczny (0.46% pozycji); **na kopii/kodzie: 84% pozycji z trafieniem ≥8, zgodność z MTP 0.995, +2.4 tokenu/krok przy W8** (baza 3.86) — kierunek potwierdzony.
- Greedy md5 przy włączonym ogonie niezweryfikowane (ogon nie odpalił na tych promptach).
- E2 (koszt weryfikacji 5/8/16 × 2k/8k/32k/64k): przerwany, brak wyników.
- **Do zrobienia:** zacommitować kod; E2; E3 A/B (`~/qwen-opt/lookup/e3_ab.sh`, tryby copy/sweep/long/mvs); raport 16b.

### XtxPm4Pdl: PM4 bez barier + prefetch (`~/wt/pm4pdl`, **zmiany NIEzacommitowane**)
- X1 mikrobenchmark (`~/qwen-opt/pm4pdl/x1/bench4.log`): oszczędność 0.05–0.11 µs dla kształtu LFM 2048² → **poniżej progu 0.5 µs**; większe siatki 0.5–1.1 µs.
- X2/X3 (`x2/ab1.log`): zdążyła 1 runda z 26: produkcja 291.4, baza 293.1, UB=conv (górna granica, niebezpieczna) 296.3 t/s (+1.1%).
- **Do zrobienia:** puścić `~/qwen-opt/pm4pdl/x2/run1.sh` od nowa; jeśli górna granica < +3% → wynik negatywny; raport 16a.

### XtxQuickWins: szybkie testy (`~/wt/quickwins`, **zmiany NIEzacommitowane**; w chwili zapisu w tle kończy się kompilacja `llama-server`)
- **E4, cache promptu (ważne dla omp):** obce zapytanie wyrzuca slot i serwer liczy od nowa ~7.3k tokenów promptu systemowego. Łatka `LLAMA_SERVER_CACHE_SHARE_MIN=1024`: Qwen 8019 → 1612 ms, LFM 1357 → 230 ms (z `LLAMA_LFM2_MSG_SPANS=1`: 166 ms). Niesprawdzone, czy sam omp wysyła takie poboczne zapytania.
- E5 zapis/odczyt sesji z dysku: Qwen 2.39 GB, odczyt 2.51 s, potem start 2.2 s zamiast 8.0 s.
- E3: narzut haka MTP przy prefillu +15.8% (2k), +8.1% (8k), +4.5% (32k) — tyle można odzyskać; samo złożenie niezaimplementowane.
- E1 (LFM `-ub 2048`), E2 (typ głowy MTP): nieuruchomione.
- **Do zrobienia:** E1, E2, E3; zacommitować; raport 16f.

### XtxLfmMoe: pasmo MoE w LFM (`~/wt/lfmmoe`, kod produkcyjny nietknięty; narzędzia w `~/wt/lfmmoe-prof/`)
- Kernele MoE osiągają ~690 GB/s vs ~850 GB/s idealnego odczytu. Najlepszy bit-exact wariant gate_up −1.4 µs (−6%), down Q6_K −1.0 µs → łącznie ~70 µs/token ≈ **2%** [INFERENCE].
- **Do zrobienia:** rep 3 (`./rep.sh 3 r6`), decyzja (2% to mało), raport 16g.

### CoupledSampling: sprzężone losowanie (`~/wt/coupled`, gałąź `opt-coupled`, **kod napisany, NIEskompilowany, NIEzacommitowany**)
- Cały kod za `LLAMA_SPEC_COUPLED` (nowy op `GGML_OP_GUMBEL_MAX` CPU+HIP, draft MTP z szumem Gumbela, test statystyczny `tests/test-coupled-sampling.cpp`). Skrypty `~/qwen-opt/coupled/{arm,run}.sh`.
- **Do zrobienia:** kompilacja CPU → test statystyczny → HIP → ABBA T=1/0.7; raport 16k.

### MagnitudeVulkanXtx: Magnitude przez Vulkan na XTX (`~/qwen-opt/magnitude-xtx/`)
- Lokalny sterownik RADV w `~/.local/vk/` (`. ~/.local/vk/env.sh`). Pierwszy start: przygotowanie kerneli nie skończyło się w 300 s (125 artefaktów Vulkan w `cache/smoke`).
- Drafter `Qwen3.8-27B-DFlash2-Q8_0.gguf` **nie pobrał się** (pusty `.incomplete` w `~/models/magnitude/`).
- **Do zrobienia:** pobrać drafter, dłuższy pierwszy start (cache), pomiar; raport 16j.

### QuantKLD: jakość nowych kwantów (chmura usunięta, wyniki lokalnie)
- **KLD na A40** (`results/quantkld-20261016/pod/kld.json`, pełne w `pod-final/`), wiki vs Qwen BF16: U3 (UD-Q3_K_XL) 0.039, A3 0.040, ISTA I4 0.073, I2 0.164, Saluki 0.257, Bonsai 0.352; Swift W4 0.072–0.076, W3 0.119, W2 0.164–0.166, W1 0.222; szum Q8_0 0.0038.
- Zadania (20 promptów): W4 1.0, W2 0.95, I2/I4/Saluki 0.85; U3 i Bonsai — sprawdzić `pod-final/res/tasks/`.
- Prędkość 5060 Ti (`5060ti/speed.json`): U3 29.1 → MTP 51.7 t/s, I4 i W4 30.3 → 50.0.
- Prędkość 3060 (`results/3060-20261016/opt/`): Saluki 17.2 → MTP 24.3 t/s; Bonsai repack 27.6 t/s (sweep niedokończony).
- **Do zrobienia (CPU):** zebrać wszystko w raport 16e. Bez nowego wynajmu, chyba że użytkownik zdecyduje inaczej.

### LandingWow: strona (`~/KERNEL/app`, **runda po commicie `22bce75` NIEzacommitowana**, build aktualny)
- Zrobione wszystkie uwagi użytkownika: hero wyśrodkowane z widocznymi zegarami, menu z płynną pigułką, Dobór ~1.3 s, animowany stos + oś kerneli, linijka KLD + bit-exact, usunięty cennik, FAQ pod końcowym CTA, nowy onboarding, gorące akcenty na wszystkich podstronach.
- Juror runda 5: 6.5 / 6 / 5.5. Otwarte: treść pod szklanym nagłówkiem, większe zegary + „meta” wyścigu, jasny motyw, legenda jakości, LCP 3.0–3.5 s.
- **Do zrobienia:** zacommitować rundę; dalsze poprawki po uwagach użytkownika.

### WikiIngest
- Wiki aktualne do 16c/16d/16i/16h + naprawa regresji (381 notatek, lint 0/0). Czeka na kolejne raporty.

## Odłożone (decyzja użytkownika)

### Nemotron 3.5 Bolt na RTX 3090 — „odpuszczamy, wrócimy kiedyś”
- Stan: raport 14 (kampania skrócona do ~2.3 h z 10 h). Upstream najlepsze flagi + DFlash 131.4 t/s, nasz fork z łatkami 141.1 t/s (×1.07; ×1.62 vs domyślne 87.2). KLD `TOPK_MOE_NP2` PASS (14 §13). Kod: `nemotron-3090` @ `e46d34e0e` (`~/wt/nemotron-opt`, czysty).
- Do zrobienia przy powrocie (14 §10): kernel IQ2_XXS MMVQ (320–400 vs 805 GB/s), replay stanu Mamby przy weryfikacji, szybszy `topk_moe`, FA q8_0 przy GQA 16:1 / kvq z CUDA, A/B per łatka, długi kontekst 128k, sweep n_max. Kod pisać lokalnie przed wynajmem, potem jedna sesja na 3090.

## Pozostałe po wątkach (do posprzątania przy wznowieniu)
- `~/.cargo` (Rust, do budowy Magnitude), `~/qwen-opt/magnitude/` (8.4 GB źródeł i buildów).
- Niezacommitowane worktree: `lookup`, `pm4pdl`, `quickwins`, `coupled` — nie usuwać.
