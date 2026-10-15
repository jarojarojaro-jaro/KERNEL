# Gdzie skończyliśmy (2026-10-15) — od tego zaczynamy po powrocie

Kolejka GPU z rundy 6 przerobiona: (1) samplery — scalone, (2) GDN opt-gdn6 — bitowy, ale zysk w szumie, nie scalony, (3) MMQ epilog — scalony (+2.2% prefill Qwen).

## Stan zainstalowany (`~/llama-opt`, gałąź `amd-opt` @ f61994f58, 70 łatek, na GitHubie)
Finalny pomiar 2026-10-15 (spec_sweep 6 promptów x 3 seedy, T=1, świeży serwer `run-llm.sh <model>`):
| model | t/s (mediana) | ms/krok |
|---|---|---|
| Qwen3.8-27B UD-Q4_K_XL, MTP | 109.0 | 27.74 |
| Qwen3.8-27B Uncensored, MTP | 115.5 | 26.68 |
| LFM2.5-24B-A2B, KV q8_0 | 293.7 | 3.41 |
| LFM2.5 Uncensored, KV q8_0 | 267.3 | 3.74 |

Greedy md5 po instalacji = bazy (Qwen plain c4708318…, MTP 6f14e814…, LFM 894e56e4…).
`run-llm.sh` ustawia `LLAMA_SERVER_REASONING_CONTROL=0` (łatka 0065); od 0066-0069 web UI z budżetem myślenia i narzędzia omp też idą szybką ścieżką.

## Kolejka GPU

### 1. Sampler fast path — ZROBIONE (scalone do amd-opt, zainstalowane, NOTES.md „Sampler: …”)
Te same tokeny fast == slow (LFM + Qwen MTP, 5 przypadków). Web UI / budżet / narzędzia omp: LFM ~255 -> ~293 t/s, Qwen MTP +6-8%.

### 2. Qwen runda 5 — gałąź `opt-qwen5` (worktree `~/wt/qwen5`), raport `research/qwen-round5.md`
Zmierzone już w oknie GPU 2026-10-15:
- GDN „fast” (DPP, stan po 16 B): **nie bitowy** (inna kontrakcja FMA), wycofany. Przyszła próba: jawne fmaf zgodne z ISA bazy, kernel plain nietknięty.
- MMQ y-double-buffer: bitowy, ale **−2.6% pp4096** (3 → 2 bloki/WGP), wycofany.
- Ablacja MMQ (pp4096): ~66% czasu prefillu to vec_dot (WMMA + epilog skal), ładowania ~11%, bariery ~7%. Prefill jest ograniczony matematyką epilogu, nie ładowaniem — prefetch kafli da max ~12% i tylko bez utraty obłożenia. Dźwignia: tańszy epilog (64 cvt + 128 fma_mix + 33 fmac na 16 WMMA) przy bitowych logitach.
- DFlash2 szeroki blok (n=15) na greedy EN kod / PL proza: 89.7 / 38.3 vs n=6 104.8 / 44.2 t/s — te same tokeny zaakceptowane, 2.5x więcej draftu → **wolniej**. Wynik hipfire (318 t/s) wymaga ich draftera MQ4V2 + promptu bez myślenia; u nas nie powtórzone.
Niezrobione: tryb „draft 16, verify k” (`LLAMA_DFLASH_BLOCK`), mniejszy słownik głowicy DFlash (commit bbac7d7ae, niezmierzony), maska w kernelu (szacunek ≤0.3%, odpuszczone), kopia logitów (pomiar P6). Komendy P1-P9 w raporcie.

### 3. Runda 6 — ZMIERZONE 2026-10-15: MMQ epilog scalony (0070, Qwen pp4096 +2.2%), GDN bitowy ale w szumie (nie scalony). Zostało na GPU: (4) `loo.py run`, (5) `kld_canary.sh`, (6) Kernel Tuner.
Raporty z wynikami: `research/round6/`. Opis gałęzi (stan sprzed pomiarów):
| gałąź / worktree | co | dowód offline | wyłącznik |
|---|---|---|---|
| `opt-gdn6` `~/wt/gdn6` (b4e819237, 0d89ce56c) | GDN fast: DPP zamiast ds_bpermute, nakładanie tokenów t/t+1, stan b128 przez LDS | emulator symboliczny ISA (`~/wt/gdn6-isa/gdnemu.py`, `gdncmp.py`): każde wyjście = to samo wyrażenie co baza; stary kernel ISA identyczny; 476→423 instr./token | `GGML_HIP_GDN_FAST=0`, `GGML_HIP_GDN_B128=0` |
| `opt-mmq6` `~/wt/mmq6` (ae1ef6a97) | epilog MMQ Q4_K/Q5_K J≥48: skale f32 raz na k01, akumulator z biasem 0x4B400000, VOPD | Q4_K J=128 pętla 298→243 instr., VALU 237→178, LDS bez zmian (3 bloki/WGP); dowód bitowy w raporcie; szac. +5% pp4096 | `GGML_HIP_MMQ_EPI=0` |
| `tools6` + `~/qwen-opt/tools/` (kopia `tools/`) | `loo.py` (leave-one-out: 27 env + 2 CLI + 22 build-time + 14 bez wpływu na prędkość), `kld_canary.sh` (kanarki muszą FAIL/PASS), `kt/` (Kernel Tuner: 39 kształtów MMVQ, MoE, GDN) | dry-run / fake data; 53 warianty kt kompilują się; harness = ISA produkcji | — |
Komendy dla (4)-(6): `tools/README.md`.

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
