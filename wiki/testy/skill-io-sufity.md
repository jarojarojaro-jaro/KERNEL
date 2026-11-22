---
typ: test
tags: [testy, sufit, roofline, dekod, prefill, kv, skill-io]
aktualizacja: 2026-11-17
zrodlo: ~/kernel/zrodla/inference-optimisation-skill @ fda968e — skills/inference-optimisation/references/ceilings.md:1-79, SKILL.md:60-76, scripts/ceiling.py:1-51; nasze wejście i wynik ~/KERNEL/qwen-opt/skill-io/{ceiling-qwen27b-unc-xtx.json,ceiling-out.txt}
status: aktualne
---
# Sufity wg skill-io (ceilings.md + ceiling.py): nasz Qwen3.8-27B Q4_K_M na XTX i 34 kartach AMD, NVIDIA, Apple, Intel i Tenstorrent

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
- Modele z pętlą warstw (SenseNova-Loop-9B, Ouro): bajty bloku × liczba przejść, KV i stan per wykonanie; plik 5,3 GB czyta ~7,7 GB/token ([[sensenova-loop-9b]]).
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

Pomiary NVIDIA mają MTP n3 i inny harness, więc to przybliżenie (K-113 zrobi to 1:1).

**Pomiar 1:1 z 2026-11-17 (K-114, ten sam model GSQ IQ3_XXS-mtp i ten sam silnik na trzech kartach, [[2026-11-17-k114-nvidia-sufit]]):**
- 5060 Ti: 51,0 t/s (61% sufitu), prefill 43–47%;
- 3060 (host 135 W, **dolna granica, nie pomiar karty**): 28,6 (42%), prefill 46–47%;
- 3090 (host 250 W, pamięć 5001 MHz, **dolna granica, nie pomiar karty**): 44,4 (23%), prefill 12–26%. Powtórka na pełnej mocy: K-118.

Przyczyny luki:
- 4–15 × droższy draft niż jego bajty (K-116);
- limity hostów Vast. XTX pp4096 1123 t/s (UD-Q4_K_XL, [[REKORDY]]) to 95% sufitu prefillu.

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

## Apple, Intel, Tenstorrent (zakres: wszystkie firmy, 2026-11-17)

**Model i metoda bez zmian.** Źródła producentów są w `karty.json → _zrodla`.

**Apple** nie publikuje TFLOPS, więc wartości są wyprowadzone:
- FP16 = rdzenie GPU × 128 ALU × 2 × zegar;
- M5: × 4 względem M4, bo Apple podaje „> 4× szczytu GPU dla AI” dzięki Neural Accelerators w każdym rdzeniu;
- pasmo z newsroomu Apple (M3 Max 400, M4 Pro 273, M4 Max 546, M5 153, M5 Pro 307, M5 Max 614 GB/s).

**Pamięć użyteczna:**
- Apple: ~75% RAM (limit `iogpu.wired_limit_mb`);
- iGPU Intela: ~50–70% [INFERENCE].

**Kolumna INT8 w zależności od firmy:**
- Apple: = FP16, bo Metal w llama.cpp liczy prefill w f16 (`simdgroup_matrix`);
- Tenstorrent: = BLOCKFP8.

| firma | karta | arch | pamięć GB | GB/s | FP16 / INT8 TFLOPS | plain 2k | MTP 2k | MTP 128k | prefill 4k FP16 / INT8 | 32k | 256k | 262k? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Apple | M3 Max 40c (128 GB) | Apple GPU / Metal | 96 | 400 | 14,3 / 14,3 | 25 | 72 | 64 | 137 / 137 | 124 | 70 | tak |
| Apple | M4 Pro 20c (48 GB) | Apple GPU / Metal | 36 | 273 | 8,1 / 8,1 | 17 | 49 | 43 | 78 / 78 | 70 | 39 | tak |
| Apple | M4 Max 40c (128 GB) | Apple GPU / Metal | 96 | 546 | 16,2 / 16,2 | 34 | 98 | 87 | 156 / 156 | 141 | 79 | tak |
| Apple | M5 10c (32 GB) | GPU + Neural Accelerators | 24 | 153 | ~16 / ~16 | 9 | 28 | 24 | 158 / 158 | 142 | 80 | tak |
| Apple | M5 Pro 20c (64 GB) | GPU + Neural Accelerators | 48 | 307 | ~33 / ~33 | 19 | 55 | 49 | 312 / 312 | 282 | 158 | tak |
| Apple | M5 Max 40c (128 GB) | GPU + Neural Accelerators | 96 | 614 | ~65 / ~65 | 38 | 111 | 98 | 625 / 625 | 564 | 316 | tak |
| Intel | Arc A770 16 GB | Xe-HPG | 16 | 560 | 131 / 262 | 35 | 101 | 89 | 1259 / 2519 | 2273 | 1275 | nie |
| Intel | Arc B580 12 GB | Xe2 | 12 | 456 | 116,5 / 233 | 28 | 82 | 72 | 1120 / 2240 | 2021 | 1134 | nie |
| Intel | Arc Pro B70 32 GB | Xe2 | 32 | 608 | 183,5 / 367 | 38 | 110 | 97 | 1764 / 3528 | 3183 | 1786 | tak |
| Intel | Lunar Lake Arc 140V (32 GB) | Xe2 iGPU | ~16 | 136,5 | 33,5 / 67 | 8 | 25 | 22 | 322 / 644 | 581 | 326 | nie |
| Intel | Panther Lake Arc B390 (64 GB) | Xe3 iGPU | ~46 | 153,6 (zmierzone 115) | 60 / 120 (zmierzone FP16 35,8) | 9 | 28 | 24 | 577 / 1154 | 1041 | 584 | tak |
| Intel | Gaudi 3 | MME | 128 | 3700 | 1678 / 1678 | 229 | 667 | 588 | 16 133 | 14 555 | 8166 | tak |
| Tenstorrent | Wormhole n150 | Tensix | 12 | 288 | ~74 / 148 | 18 | 52 | 46 | 711 / 1423 | 1284 | 720 | nie |
| Tenstorrent | Wormhole n300 (2 chipy) | Tensix | 24 | 576 | ~131 / 262 | 36 | 104 | 92 | 1259 / 2519 | 2273 | 1275 | tak (TP=2) |
| Tenstorrent | Blackhole p150 | Tensix | 32 | 512 | ~332 / 664 | 32 | 92 | 81 | 3192 / 6384 | 5760 | 3231 | tak |

**Jedyny pomiar 1:1 (ten sam kwant Q4_K_M):** Arc Pro B70 z llama.cpp robi 25,0 t/s (`README.md:31` skill-io). To 66% sufitu bez spekulacji (37,7) i 23% sufitu MTP. Ten sam model w vLLM z ich kernelami XPU (EXL3 4 bpw) robi 91,2 t/s. Na Intelu llama.cpp zostawia więc ~3,6 × prędkości.

**Wnioski:**
1. **Weryfikacja MTP na Apple M1–M4 jest ograniczona obliczeniami, nie pasmem.**
   - Weryfikacja N = 5 to 2 × 25,6 G × 5 = 256 GFLOP na krok. Przy 50% szczytu FP16 zajmuje to 63 ms na M4 Pro, a odczyt bajtów 59 ms; na M4 Max 32 ms obliczeń i 30 ms bajtów.
   - Dla porównania XTX: 4 ms obliczeń i 17 ms bajtów.
   - Wyjaśnia to pułapkę skill-io „M4: 6,35 → 3,25 t/s z 3 draftami” (`levers.md:35`).
   - **Na Apple przed M5 tylko krótki draft (n1–2).** M5 z Neural Accelerators (~4 × FP16) przywraca przewagę pasma (M5 Max: 8 ms obliczeń vs 26 ms bajtów).
2. **Pasmo:**
   - M5 Max (614 GB/s) ma sufit dekodu 111 t/s, czyli 64% XTX;
   - M4 Max ma 98;
   - iGPU Intela (136–154 GB/s) mają 25–28 t/s, czyli tyle co M5 base.
3. **Intel dyskretny i Tenstorrent mają sufity prefillu jak NVIDIA** (B70: 3528 t/s przy 4k, p150: 6384), a dekod jak XTX lub niżej (110 / 92).
4. **Karty 12–16 GB** (B580, A770, n150, Lunar Lake) **nie mieszczą Q4_K_M**. To ta sama reguła co w Enigmie: mniejszy kwant tylko po to, żeby model się zmieścił.

## Powiązane
- [[skill-io-przeglad]]
- [[sufit-pasma-i-mapa-czasu]]
- [[raport-24r-mmvq-pasmo]]
- [[final-recipes-nvidia]]
- [[REKORDY]]
- [[KOLEJKA-TESTOW]]
