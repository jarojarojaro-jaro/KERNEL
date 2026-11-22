---
typ: model
tags: [modele, rl, qwen, agenci, trening, telegram]
aktualizacja: 2026-11-19
zrodlo: https://x.com/radixark/status/2123115052127633536 (Telegram „gpu”, 2026-11-19); huggingface.co/RadixArk/DaisyRose-27B (karta, Apache-2.0); huggingface.co/bartowski/RadixArk_DaisyRose-27B-GGUF (Q4_K_M 17,33 GB)
status: aktualne
model: daisyrose-27b
rozmiar: 27B
kwant: Q4_K_M
k: K-120
---
# DaisyRose-27B (RadixArk): pełny RL na Qwen3.8-27B, 144 × H200 przez 18 dni — duży koszt, mały zysk poza Terminal-Bench 4.1

**RadixArk (twórcy DSpark) wytrenował nasz model bazowy samym RL-em (bez SFT i destylacji) na ~1200 długich zadaniach agentowych, z sesjami do 1M tokenów. Koszt to 144 H200 × 18 dni ≈ 62 tys. GPU-godzin. Zysk: Terminal-Bench 4.1 5,6 → 12,0%, na pozostałych testach +0,4…+4 pp. Ta sama architektura i ten sam szablon, więc zastępuje Qwen3.8-27B bez zmian; GGUF Q4_K_M działa w naszym silniku bez łatek [INFERENCE: ten sam typ `qwen35`].**

**Wyniki** (karta, tryb myślenia `xhigh`, średnie z 4–8 powtórzeń):

| test | Qwen3.8-27B | DaisyRose-27B | różnica |
|---|---|---|---|
| Terminal-Bench 4.1 | 5,6 | 12,0 | +6,4 pp (×2,1) |
| Terminal-Bench 2.1 | 73,0 | 75,5 | +2,5 |
| DeepSWE v1.1 | 42,2 | 46,2 | +4,0 |
| SWE-bench Pro v2 | 91,3 | 94,7 | +3,4 (baza z innej pracy, inny harness) |
| HLE (tekst) | 33,9 | 34,3 | +0,4 |
| IFBench | 79,5 | 82,4 | +2,9 |
| GPQA Diamond | 89,2 | 90,7 | +1,5 |

**Lekcje (filar trening):**
1. **Koszt do zysku:** adaptery harness-hub to LoRA, 2 × B200, ~150 kroków. Dały +16…33 pp w jednym harnessie i 6–8 × mniej tokenów ([[qwen38-27b-pi-adapter]]). DaisyRose to pełny RL za ~62k GPU-h i +2…4 pp ogólnie. **Dla naszych zastosowań (omp, jeden harness) tani, celowany adapter ma wielokrotnie lepszy stosunek zysku do kosztu.** Dobrze ogólnie poprawić model jest bardzo drogo.
2. **Czas = tokeny:** DaisyRose myśli długo („dziesiątki tysięcy tokenów”, bez limitu `max_tokens`). Przy naszych ~120 t/s każde 10k tokenów to ~83 s. Mierzyć trzeba czas na zadanie, nie tylko % rozwiązanych ([[lekcja-czas-optymalizacji-to-metryka]]).
3. **MTP:** głowica MTP (0,42B) jest w checkpoincie. Karta nie mówi, czy była trenowana razem z modelem, a do szybkiej spekulacji polecają osobny drafter DSpark. Akceptację naszego MTP n4 trzeba zmierzyć, bo może spaść, jeśli rozkład modelu się przesunął.

**Dla nas:** kandydat do porównania w K-120 (zadania omp: rozwiązane, tokeny, czas ściany, akceptacja MTP). Plik Q4_K_M ma 17,3 GB (pobranie za zgodą). Zmiana modelu na produkcji to decyzja właściciela.

## Powiązane
- [[qwen38-27b-pi-adapter]]
- [[trening-llm-mapa]]
- [[lekcja-czas-optymalizacji-to-metryka]]
- [[KOLEJKA-TESTOW]]
