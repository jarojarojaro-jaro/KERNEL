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

### 3. Runda 6 (CPU, 2026-10-15) — gotowe do testu na GPU, wszystko UNMEASURED
Łatki: `patches/pending/<gałąź>/`, raporty: `research/round6/`. Każda gałąź od c36fd2c87, każda zmiana z wyłącznikiem.
| gałąź / worktree | co | dowód offline | wyłącznik |
|---|---|---|---|
| `opt-gdn6` `~/wt/gdn6` (b4e819237, 0d89ce56c) | GDN fast: DPP zamiast ds_bpermute, nakładanie tokenów t/t+1, stan b128 przez LDS | emulator symboliczny ISA (`~/wt/gdn6-isa/gdnemu.py`, `gdncmp.py`): każde wyjście = to samo wyrażenie co baza; stary kernel ISA identyczny; 476→423 instr./token | `GGML_HIP_GDN_FAST=0`, `GGML_HIP_GDN_B128=0` |
| `opt-mmq6` `~/wt/mmq6` (ae1ef6a97) | epilog MMQ Q4_K/Q5_K J≥48: skale f32 raz na k01, akumulator z biasem 0x4B400000, VOPD | Q4_K J=128 pętla 298→243 instr., VALU 237→178, LDS bez zmian (3 bloki/WGP); dowód bitowy w raporcie; szac. +5% pp4096 | `GGML_HIP_MMQ_EPI=0` |
| `tools6` + `~/qwen-opt/tools/` (kopia `tools/`) | `loo.py` (leave-one-out: 27 env + 2 CLI + 22 build-time + 14 bez wpływu na prędkość), `kld_canary.sh` (kanarki muszą FAIL/PASS), `kt/` (Kernel Tuner: 39 kształtów MMVQ, MoE, GDN) | dry-run / fake data; 53 warianty kt kompilują się; harness = ISA produkcji | — |
Kolejność na GPU: (1) samplery opt-samp, (2) gdn6: `test-backend-ops -o GATED_DELTA_NET*` fast on/off + greedy md5 Qwen plain/MTP + A/B, (3) mmq6: `-o MUL_MAT` + KLD = 0 + pp512/pp4096 A/B, (4) `loo.py run`, (5) `kld_canary.sh`, (6) Kernel Tuner. Dokładne komendy: `REPORT.md` w każdym worktree i `tools/README.md`.

### 4. Prompt cache (pomysły, nic nie zrobione)
Z logów 9 sesji LFM: cache hit 91% tokenów (tura omp ~99.8%, mediana 25 nowych tokenów), prefill 3.8% czasu GPU; pełne przeliczenia tylko na starcie sesji (7–10k tok., ~1.7 s).
- zapis prefiksu na dysk (`--slot-save-path` + slot save/restore) — przetrwa restart serwera;
- licznik cache hit w REACTOR (CPU);
- rozjazd w środku rozmowy na modelach hybrydowych (GDN / conv: stanu nie da się cofnąć) → sprawdzić checkpointy kontekstu (`--ctx-checkpoints`) przy regeneracji / edycji / kompaktowaniu omp / szablonie Qwena wycinającym `<think>`.

### 5. Dalsze pomysły
- LFM: narzut PM4 ~40 us/token, spekulacja n-gram po analizie offline unii ekspertów.
- thread trace rocprofv3 (ATT); stan GDN fp16 (zmienia numerykę → KLD + zgoda użytkownika); skale x jako f32 w LDS dla MMQ (~2% pętli).

## Inne
- Monitor: `reactor` (`~/KERNEL/monitor/`), jasna wersja, ~3.3% jednego rdzenia.
- LocalMaxxing (https://www.localmaxxing.com): możliwe wysłanie wyników przez API po założeniu konta (klucz `bhk_…` od użytkownika).
- Telefon (MiniCPM): prompt `~/telefon/PROMPT-minicpm-speed.md` przekazany użytkownikowi.
