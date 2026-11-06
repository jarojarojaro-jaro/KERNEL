---
typ: lekcja
tags: [lekcje, mtp, vram, llama-cpp]
aktualizacja: 2026-11-05
zrodlo: ~/qwen-opt/q63/NOTES.md:28-48; ~/qwen-opt/q63/logs/summary.txt:14-19
status: aktualne
---
# Stockowa rezerwa MTP płaci za kopię f16 całego KV draftu

**Rezerwa grafu kontekstu draftu MTP w llama.cpp alokuje bufor na graf, który nigdy się nie wykonuje: pełną atencję `n_ubatch` tokenów nad całym KV draftu, z kopią f16 tego KV dla kernela MMA (≈800 MiB przy ctx 204800).**

- Składniki stock (ctx 204800, KV draftu q4_0, ub 512): kopia f16 K+V 800 MiB, maska f16 200 MiB, aktywacje ~68 MiB. Zmierzone 2026-11-05: bufor compute MTP ROCm0 1081.23 MiB.
- Rzeczywisty draft liczy 1 token przez kernel kvq (≤ 16 tokenów), który kopii f16 nie potrzebuje.
- Chuda rezerwa (catch-up tylko K/V + krok 1 tokenu): 40.28 MiB, VRAM 23360 → 22319 MB, wyjście bit w bit ([[2026-11-05-q63-topka]]).
- Lekcja: rozmiar bufora rezerwy to nie koszt modelu, tylko najgorszego grafu, jaki scheduler sobie wyobraża. Przy każdym dodatkowym kontekście (draft, sidecar) sprawdzaj linie `sched_reserve` z `-lv 4` i pytaj, czy ten graf w ogóle się wykonuje.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-cache-ram-za-maly]]
- [[lekcja-rocm10-lds-128kb]]
- [[qwen3-8-27b]]
