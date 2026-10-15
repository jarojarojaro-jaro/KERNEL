# Gdzie skończyliśmy (2026-10-15, ~02:30) — od tego zaczynamy po powrocie

GPU: testy wstrzymane na prośbę użytkownika. Żaden llama-server ani benchmark nie działa. Agenty nie pracują.

## Stan zainstalowany (`~/llama-opt`, gałąź `amd-opt` @ c36fd2c87, 65 łatek, na GitHubie)
| model | t/s (spec_sweep 6x3, T=1) |
|---|---|
| Qwen3.8-27B UD-Q4_K_XL, MTP | 108.8 |
| Qwen3.8-27B Uncensored, MTP | 115.3 |
| LFM2.5-24B-A2B, KV q8_0 | ~292 (llama-bench 295, 98k: 213) |
| LFM2.5 Uncensored | ~264 |

`run-llm.sh` ustawia `LLAMA_SERVER_REASONING_CONTROL=0` (łatka 0065), więc web UI nie spowalnia przez `reasoning_control`.

## Czeka na GPU (w tej kolejności)

### 1. Sampler fast path — gałąź `opt-samp` (4 commity na c36fd2c87), build `~/wt/samp/inst`
Szybka ścieżka top-k także z budżetem myślenia, `n_probs`, `logit_bias`, gramatyką (narzędzia omp). Harness CPU:
312k wektorów, 0 różnic. GPU, LFM, build fast (zmierzone 2026-10-15): plain 294.5, reasoning_control 294.5,
budget 2048 294.0, tools 294.1, logit_bias 293.6 t/s (wcześniej 255/254/~245/255 na wolnej ścieżce).
**Brakuje:** przebiegu „slow” (te same zapytania z wyłącznikami) do porównania md5 seeded outputs, potem to samo dla
Qwen MTP. Komenda (ok. 5 min GPU na model):
```
cd ~/qwen-opt
# fast
flock /tmp/gpu.lock flock /tmp/quiet.lock bash -c 'REASONING_CONTROL=1 ROCM_DIR=$HOME/wt/samp/inst PORT=18470 ./run-llm.sh lfm >/dev/null 2>&1 & until curl -sf localhost:18470/health >/dev/null; do sleep 1; done; .venv/bin/python samp_ab.py --port 18470; pkill -f "llama-server.*18470"'
# slow: to samo z env LLAMA_SAMPLER_FAST_RBUDGET=0 LLAMA_SAMPLER_FAST_NPROBS=0 LLAMA_SAMPLER_FAST_LOGIT_BIAS=0 LLAMA_SAMPLER_FAST_GRAMMAR=0
```
md5 każdej linii fast == slow → merge `opt-samp` do `amd-opt`, `cmake --install` do `~/llama-opt`, eksport łatek.

### 2. Qwen runda 5 — gałąź `opt-qwen5` (worktree `~/wt/qwen5`), raport `research/qwen-round5.md`
Zmierzone już w oknie GPU 2026-10-15:
- GDN „fast” (DPP, stan po 16 B): **nie bitowy** (inna kontrakcja FMA), wycofany. Przyszła próba: jawne fmaf zgodne z ISA bazy, kernel plain nietknięty.
- MMQ y-double-buffer: bitowy, ale **−2.6% pp4096** (3 → 2 bloki/WGP), wycofany.
- Ablacja MMQ (pp4096): ~66% czasu prefillu to vec_dot (WMMA + epilog skal), ładowania ~11%, bariery ~7%. Prefill jest ograniczony matematyką epilogu, nie ładowaniem — prefetch kafli da max ~12% i tylko bez utraty obłożenia. Dźwignia: tańszy epilog (64 cvt + 128 fma_mix + 33 fmac na 16 WMMA) przy bitowych logitach.
- DFlash2 szeroki blok (n=15) na greedy EN kod / PL proza: 89.7 / 38.3 vs n=6 104.8 / 44.2 t/s — te same tokeny zaakceptowane, 2.5x więcej draftu → **wolniej**. Wynik hipfire (318 t/s) wymaga ich draftera MQ4V2 + promptu bez myślenia; u nas nie powtórzone.
Niezrobione: tryb „draft 16, verify k” (`LLAMA_DFLASH_BLOCK`), mniejszy słownik głowicy DFlash (commit bbac7d7ae, niezmierzony), maska w kernelu (szacunek ≤0.3%, odpuszczone), kopia logitów (pomiar P6). Komendy P1-P9 w raporcie.

### 3. Pomysły na kolejne rundy (z `research/repos/REPOS-PODSUMOWANIE.md`)
- LFM: narzut PM4 ~40 us/token (czekanie po stronie GPU), spekulacja n-gram po analizie offline unii ekspertów.
- Oba: leave-one-out 65 łatek, tablice per kształt (Kernel Tuner), thread trace rocprofv3 (ATT).
- Qwen: tańszy epilog MMQ (bitowo), stan GDN fp16 (zmienia numerykę → KLD + zgoda użytkownika).

## Inne
- Monitor: `reactor` (`~/KERNEL/monitor/`), jasna wersja, ~3.3% jednego rdzenia.
- LocalMaxxing (https://www.localmaxxing.com): możliwe wysłanie wyników przez API po założeniu konta (klucz `bhk_…` od użytkownika).
- Telefon (MiniCPM): prompt `~/telefon/PROMPT-minicpm-speed.md` przekazany użytkownikowi.
