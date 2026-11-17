---
typ: metoda
tags: [metody, sufit, roofline, dekod, prefill, kv, skill-io]
aktualizacja: 2026-11-17
zrodlo: ~/kernel/zrodla/inference-optimisation-skill @ fda968e — skills/inference-optimisation/references/ceilings.md:1-79, SKILL.md:60-76, scripts/ceiling.py:1-51; nasze wejście i wynik ~/KERNEL/qwen-opt/skill-io/{ceiling-qwen27b-unc-xtx.json,ceiling-out.txt}
status: aktualne
---
# Sufity wg skill-io (ceilings.md + ceiling.py): nasz Qwen3.8-27B Q4_K_M na XTX i 18 kartach AMD i NVIDIA

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

## Sufity dla kart AMD i NVIDIA (ten sam model i kwant, 2026-11-17)

**Ten sam model (Qwen3.8-27B Q4_K_M, KV q4_0, MTP n4, a = 3,2) i ta sama metoda `ceiling.py`. Pasmo i FLOPS wziąłem ze stron producentów:**
- **AMD:** strony produktów Radeon i Instinct;
- **NVIDIA:** whitepaper RTX Blackwell (tabela 3090/4090/5090, wartości gęste) oraz strony A100/H100/H200/HGX (rzadkie ÷ 2).

**Wartości wyprowadzone:**
- 5060 Ti: z 759 AI TOPS FP4 rzadkich ÷ 16;
- RTX 3060 12 GB (dopisana 2026-11-17): 28 SM × 1,777 GHz × 512 FLOP/clk/SM = 25,5 TFLOPS FP16 z akumulacją FP32, INT8 101,9. Ta sama reguła na 3090 daje 71,2 jak whitepaper. Zgadza się też ze stroną NVIDIA (101 Tensor TFLOPS rzadkie); pasmo 360 GB/s.
- INT8 na RDNA2: dot4 = 2 × FP16.

**Skrypt i dane:** `qwen-opt/skill-io/karty.py` + `karty.json` (źródła w polu `_zrodla`), wynik w `karty-out.md`.

**Kolumny:**
- dekod w t/s przy c1;
- prefill w t/s przy 50% MFU: przy 4k osobno ze szczytu FP16 i INT8, przy 32k i 256k (średnia po L) tylko ze szczytu INT8 (ścieżka MMQ llama.cpp mnoży wagi przez aktywacje q8_1);
- „262k”: czy wagi + MTP + ~1 GB buforów + KV 262k mieszczą się w VRAM.

| firma | karta | arch | VRAM GB | GB/s | FP16 / INT8 TFLOPS | plain 2k | MTP 2k | MTP 128k | prefill 4k FP16 / INT8 | 32k | 256k | 262k? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| AMD | RX 6800 | RDNA2 gfx1030 | 16 | 512 | 32,3 / 64,7 | 32 | 92 | 81 | 311 / 622 | 561 | 315 | nie (wagi > VRAM) |
| AMD | RX 6900 XT | RDNA2 gfx1030 | 16 | 512 | 46,1 / 92,2 | 32 | 92 | 81 | 443 / 886 | 800 | 449 | nie |
| AMD | RX 7900 GRE | RDNA3 gfx1100 | 16 | 576 | 92 / 92 | 36 | 104 | 92 | 885 / 885 | 798 | 448 | nie |
| AMD | RX 7900 XT | RDNA3 gfx1100 | 20 | 800 | 103 / 103 | 49 | 144 | 127 | 990 / 990 | 893 | 501 | ~196k |
| AMD | **RX 7900 XTX** | RDNA3 gfx1100 | 24 | 960 | 123 / 123 | 59 | **173** | 153 | 1183 / 1183 | 1067 | 599 | tak |
| AMD | RX 9070 XT | RDNA4 gfx1201 | 16 | 640 | 195 / 389 | 40 | 115 | 102 | 1875 / 3740 | 3374 | 1893 | nie |
| AMD | MI250 | CDNA2 gfx90a | 128 | 3277 | 362 / 362 | 203 | 590 | 521 | 3481 / 3481 | 3141 | 1762 | tak |
| AMD | MI300X | CDNA3 gfx942 | 192 | 5300 | 1307 / 2615 | 328 | 955 | 842 | 12 570 / 25 141 | 22 682 | 12 726 | tak |
| AMD | MI325X | CDNA3 gfx942 | 256 | 6000 | 1307 / 2615 | 371 | 1081 | 953 | 12 570 / 25 141 | 22 682 | 12 726 | tak |
| AMD | MI355X | CDNA4 gfx950 | 288 | 8000 | 2500 / 5000 | 495 | 1441 | 1271 | 24 036 / 48 072 | 43 371 | 24 333 | tak |
| NVIDIA | **RTX 3060 12 GB** | Ampere sm_86 | 12 | 360 | 25,5 / 101,9 | 22 | **65** | 57 | 245 / 980 | 884 | 496 | nie |
| NVIDIA | **RTX 3090** | Ampere sm_86 | 24 | 936 | 71,2 / 284,7 | 58 | **169** | 149 | 685 / 2737 | 2470 | 1386 | tak |
| NVIDIA | RTX 4090 | Ada sm_89 | 24 | 1008 | 165,2 / 660,6 | 62 | 182 | 160 | 1588 / 6351 | 5730 | 3215 | tak |
| NVIDIA | **RTX 5060 Ti 16 GB** | Blackwell sm_120 | 16 | 448 | 47,4 / 189,8 | 28 | **81** | 71 | 456 / 1825 | 1646 | 924 | nie |
| NVIDIA | RTX 5090 | Blackwell sm_120 | 32 | 1792 | 209,5 / 838 | 111 | 323 | 285 | 2014 / 8057 | 7269 | 4078 | tak |
| NVIDIA | A100 80 GB SXM | Ampere sm_80 | 80 | 2039 | 312 / 624 | 126 | 367 | 324 | 3000 / 5999 | 5413 | 3037 | tak |
| NVIDIA | H100 SXM | Hopper sm_90 | 80 | 3350 | 989 / 1979 | 207 | 604 | 532 | 9513 / 19 027 | 17 166 | 9631 | tak |
| NVIDIA | H200 SXM | Hopper sm_90 | 141 | 4800 | 989 / 1979 | 297 | 865 | 763 | 9513 / 19 027 | 17 166 | 9631 | tak |
| NVIDIA | B200 | Blackwell sm_100 | 180 | 8000 | 2250 / 4500 | 495 | 1441 | 1271 | 21 632 / 43 265 | 39 034 | 21 900 | tak |

**Zmierzone a sufit.** Pomiary NVIDIA pochodzą z [[final-recipes-nvidia]]. Każdy liczony z sufitem własnego kwantu.

| karta | kwant, silnik | sufit MTP (a = 3,2) | zmierzone | % |
|---|---|---|---|---|
| RX 7900 XTX | Q4_K_M, topka-q70, T=1 | 173 (spec) / 167 (926 GB/s) | 119,3 | 69–71% |
| RTX 4090 (250 W) | UD-Q4_K_XL, fork kvqlean | 172 | 101,3 | 59% |
| RTX 5090 | UD-Q6_K, fork kvqlean | 251 | 148,6 | 59% |
| RTX 3090 (340 W) | UD-Q4_K_XL, fork kvqleana | 160 | 80,0 | 50% |
| RTX 5060 Ti (160 W) | IQ3_XXS GSQ, fork kvqlean, 196k | 120 | 49,4 | 41% |
| RTX 3060 (140 W) | Bonsai 2 27B PTQ1_0, prism MTP n2 (6,02 GB/krok) | 107–129 (a = 2,0–2,4; draft ~0,35 GB/krok) [INFERENCE] | 58,3 | 45–54% |

Pomiary NVIDIA mają MTP n3 i inny harness, więc to przybliżenie (K-113 zrobi to 1:1). XTX pp4096 1123 t/s (UD-Q4_K_XL, [[REKORDY]]) to 95% sufitu prefillu.

**Wnioski dla obu firm:**
1. **Dekod zależy tylko od pasma.**
   - Infinity Cache AMD („efektywne 3500 GB/s” na stronie XTX) ani duże L2 NVIDIA (4090 72 MB, 5090 96 MB) nie pomagają, bo 16 GB wag nie mieści się w 96 MB.
   - Cache pomaga tylko KV przy krótkim kontekście i kafelkom kerneli.
   - 3090, XTX i 4090 mają prawie ten sam sufit (169 / 173 / 182).
2. **Największy niewykorzystany zapas jest na NVIDIA:** 41–59% sufitu, podczas gdy XTX jest na 69–71%. Nasza praca nad kernelami szła na gfx1100, a NVIDIA nie ma odpowiednika PM4, `GPU_VERIFY` traci przy T=1 (K-004), a limity mocy na hostach Vast obniżają wynik. Diagnoza: K-114.
3. **Prefill zależy od jednostek macierzowych i typu danych:**
   - na GeForce INT8 = 4 × FP16 z akumulacją FP32 (3090: 284,7 vs 71,2);
   - na RDNA3 WMMA INT8 = FP16 (123);
   - na RDNA4, CDNA3/4, Hopper i Blackwell INT8 = 2 × FP16.

   Sufit prefillu 3090 (2737 przy 4k) jest więc 2,3 × wyższy niż XTX (1183), choć dekod mają równy. Prefillu NVIDIA nigdy nie zmierzyliśmy (K-112).
4. **Karty 16 GB nie mieszczą Q4_K_M** (16,6 GB wag + MTP), dlatego Enigma daje im IQ3_XXS. Kwant wybieramy tam, żeby model się zmieścił, nie dla prędkości.
5. **Karty centrów danych (MI300X, H100 i nowsze)** mają sufit c1 600–1400 t/s, czyli krok 2–5 ms. Tam koszt hosta i startu kerneli dominuje, a llama.cpp nie jest silnikiem c1. Ich sens to współbieżność (wagi czytane raz na krok dla N strumieni, `ceilings.md:28`). Tych kart nie mamy.

## Powiązane
- [[skill-io-przeglad]]
- [[sufit-pasma-i-mapa-czasu]]
- [[raport-24r-mmvq-pasmo]]
- [[final-recipes-nvidia]]
- [[REKORDY]]
- [[KOLEJKA-TESTOW]]
