---
typ: metoda
tags: [metody, sufit, roofline, dekod, prefill, kv, skill-io]
aktualizacja: 2026-11-17
zrodlo: ~/kernel/zrodla/inference-optimisation-skill @ fda968e — skills/inference-optimisation/references/ceilings.md:1-79, SKILL.md:60-76, scripts/ceiling.py:1-51; nasze wejście i wynik ~/KERNEL/qwen-opt/skill-io/{ceiling-qwen27b-unc-xtx.json,ceiling-out.txt}
status: aktualne
---
# Sufity wg skill-io (ceilings.md + ceiling.py) i nasz sufit Qwen3.8-27B Q4_K_M na XTX

**Dekod jest ograniczony pasmem: sufit = zmierzone pasmo ÷ bajty na wyemitowany token. Prefill jest ograniczony obliczeniami: sufit = 50% zmierzonego szczytu FLOPS ÷ FLOP na token. Dla naszej produkcji wychodzi: czat T=1 (3,2 tok/krok) 167 t/s przy 2k, a mierzymy 119–127, czyli 71–77%. Prefill przy głębokości 128k: 521 t/s, a mierzymy 486, czyli 93% (2026-11-17).**

**Definicje** (`ceilings.md:3-45`):
- **Pasmo i FLOPS mierzymy, nie bierzemy ze specyfikacji.** Pasmo z kopii dużego bufora, FLOPS z GEMM 4096³ i 8192³ (większy pokazuje spadek zegara). Sufit praktyczny zakłada ~100% zmierzonego pasma i ~50% zmierzonego szczytu FLOPS (`:3`).
- **Bajty na przebieg celu:** wagi gęste + eksperci × top_k/n + głowica LM („często 10–25%”) + KV × kontekst + stan rekurencyjny × 2 (`:9-15`). Rozmiary bierzemy z checkpointu, nie z „parametry × bity” (`:17`).
- **Spekulacja:** bajty / wyemitowany token = (weryfikacja + k × (warstwa draftu + głowica draftu)) / a, gdzie a = przyjęte tokeny na krok (`:21-25`). Przycięta głowica draftu bywa warta więcej niż dodatkowy draft (`:71`).
- **Prefill:** FLOP/token ≈ 2 × aktywne parametry + 4 × warstwy atencji × głowy × head_dim × pozycja (średnio L/2) (`:32-36`).
- **TTFT:** jeden przebieg + tokenizacja i harmonogram (`:43`).
- **Start:** bajty wag ÷ szybkość dysku (`:44`).
- **KV:** bajty/token = warstwy z KV × 2 × głowy KV × head_dim × bajty (`:45`).

**Nasze wejście** (plik JSON w `qwen-opt/skill-io/`):
- 926 GB/s (zmierzony sufit odczytu, [[raport-24r-mmvq-pasmo]]);
- 107 TFLOPS FP16 (cudzy pomiar rocBLAS; własnego GEMM brak, K-108);
- wagi gęste 15,09 GB = plik 16,9 − embd 0,715 − blok MTP 0,351 − głowica 1,043, plus stan GDN 0,30;
- głowica 1,043 GB;
- KV q4_0 18 432 B/token;
- draft: warstwa ~0,22 GB i głowica 64k IQ4_XS 0,178 GB, 4 drafty.

| tryb (c1) | sufit 2k / 32k / 128k / 256k | zmierzone | % sufitu |
|---|---|---|---|
| bez spekulacji | 57 / 55 / 50 / 44 | 43,2 (2k, 10-15) | 76% |
| MTP n4, a = 3,2 (czat T=1) | 167 / 162 / 147 / 131 | spec_sweep 119,3; sesja 0–32k 127,2, 64–96k 116,6 | 71–79% |
| MTP n4, a = 3,6 (T=0, 1,7k) | 188 | 133,9 ([[REKORDY]]) | 71% |
| MTP n4, a = 4,8 (kod T=0) | 250 | HumanEval+ 174,2 | 70% |
| prefill (średnia po L) | 1037 / 928 / 695 / 521 | 4k 955; 32k 775; 255k fill 493 | 92% / 84% / – / 95% |

**Wnioski:**
- **Krok MTP:** sufit 19,2 ms przy 2k, mierzymy 26,9 ms. Te 7,7 ms to nasz realny zapas w dekodzie, a nie akceptacja draftu. Zgodne z [[lekcja-bledny-roofline]] i [[sufit-pasma-i-mapa-czasu]]. Rozkład luki na składniki: K-111.
- **Prefill** jest blisko sufitu przy 50% MFU. Dalsze zyski tylko przez wyższe MFU kernela (FA wariant 83 robi 50,5 TFLOPS przy 131k).
- `ceiling.py` nie liczy stanu GDN (dodałem do „dense”) ani drugiego przejścia KV przy N=5 (flaga `kv_per_verify_row`).

## Powiązane
- [[skill-io-przeglad]]
- [[sufit-pasma-i-mapa-czasu]]
- [[raport-24r-mmvq-pasmo]]
- [[REKORDY]]
- [[KOLEJKA-TESTOW]]
