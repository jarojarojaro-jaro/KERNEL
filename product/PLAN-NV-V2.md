# PLAN-NV-V2 — kampania NVIDIA v2: najlepszy model z kontekstem ≥ 131k na każdą kartę

Wersja 2, 2026-10-20 (UTC ~19:00). Autor: PlanNvV2 (Opus, tylko CPU, nic nie wynajęte). Zmiana względem v1 (eeb29e9):
karty 10–16 GB dostają **Qwen3.6-35B-A3B (MoE) z ekspertami częściowo w RAM (`--n-cpu-moe`)** zgodnie z raportem
[`33-modele-na-karty.md`](research/33-modele-na-karty.md) (f305dfb). 24 GB i 32 GB bez zmian (Qwen3.8-27B + MTP).
Kampania w chmurze dla MoE startuje **dopiero po bramce jakości E7** (KLD kwantów Qwen3.6 do BF16, mierzone lokalnie
przez XtxLab, raport 35).

Procedura: [`qwen-opt/cloud/SOP-DOBOR-I-POMIARY.md`](../qwen-opt/cloud/SOP-DOBOR-I-POMIARY.md); brief inżyniera:
[`qwen-opt/cloud/ENGINEER-PROMPT.md`](../qwen-opt/cloud/ENGINEER-PROMPT.md); narzędzia: `qwen-opt/cloud/fitcalc.py`
(v2: MoE, `--n-cpu-moe`, szacunek t/s), `hostcheck.sh` (v2: bramki RAM/PCIe dla MoE), `needle.py`.

Co poszło źle 2026-10-20 (raporty `31-*`, [[lekcja-vast-transfer-kosztuje]], [[2026-10-20-kontekst-min-131k]]):
kontekst 32–37k, 2-bitowe Qwen na 10–12 GB (wbrew [[2026-10-16-saluki-bonsai-na-3060]]), transfer $3.80 z $6.90,
kredyt skończył się w połowie. Ten plan naprawia każdy z tych punktów regułą, a nie dobrą wolą.

## 0. Werdykt

Bramki (twarde, SOP §4): **J1 jakość** KLD do BF16 tego samego modelu: wiki ≤ 0.05, czat ≤ 0.07 (protokół 16e);
**J2 zadania** PL/EN czat + edycja kodu poprawna; **J3 kontekst** `-c ≥ 131072`, szczyt VRAM po prompcie długości `-c`
+ 512 MiB ≤ VRAM, bez OOM w pełnej sekwencji, needle 5/5; **J4 prędkość** decode ≥ 20 t/s po 64k (T=1);
**J5 (nowa, MoE z ekspertami w RAM) TTFT** przy promptcie 32k ≤ 120 s; TTFT przy 131k raportowany.

| karta | model | kwant, flagi | `-c` | VRAM szczyt / całość MiB; RAM na ekspertów | t/s plain 0 / 64k / 131k | warunek startu |
|---|---|---|---|---|---|---|
| **RTX 3090 24 GB** | **Qwen3.8-27B** + MTP (ramię T) | UD-Q4_K_XL 17.56 GB | **131072** | 23630 / 24576 (walidowane: 21380 po załadowaniu, `27-3090-final.md:207`) | **zmierzone T**: czat T=1 93.3, po 60k 56.7 (`27:232,200`) | brak — rdzeń |
| **RTX 5060 Ti 16 GB** | **Qwen3.6-35B-A3B** | **UD-IQ4_XS** 18.21 GB (plik MTP-GGUF), `--n-cpu-moe 11` | **131072** (max 168k) | 15246 / 16311; 4.1 GB | 88 / 62 / 48 `[SZACUNEK]` | E7: IQ4_XS ✓ J1 |
| **RTX 4060 Ti 16 GB** | Qwen3.6-35B-A3B | UD-IQ4_XS, `--n-cpu-moe 11` | 131072 | 15236 / 16380; 4.1 GB | 65 / 44 / 33 `[SZACUNEK]` | E7 + wynik 5060 Ti |
| **RTX 3060 12 GB** | Qwen3.6-35B-A3B | UD-IQ4_XS, `--n-cpu-moe 21` | 131072 (max 138k) | 11666 / 12288; 7.8 GB | 52 / 40 / 32 `[SZACUNEK]` | E7 + **zmiana decyzji 2026-10-16** (dziś tylko Saluki/Bonsai, oba ✗ J1) |
| RTX 3080 10 GB | Qwen3.6-35B-A3B | UD-IQ4_XS, `--n-cpu-moe 28` | 131072 (max 143k) | 9530 / 10240; 10.5 GB | 64 / 55 / 47 `[SZACUNEK]` | E7 + zgoda na transfer $0.0026/GB (brak darmowej oferty) — opcja |
| RTX 4070 Ti 12 GB | Qwen3.6-35B-A3B | UD-IQ4_XS, `--n-cpu-moe 21` | 131072 | 11758 / 12282; 7.8 GB | 69 / 54 / 44 `[SZACUNEK]` | **brak ofert na Vast** (18:48 UTC) — nie w kampanii |
| RTX 5090 32 GB (referencja) | Qwen3.8-27B + MTP | UD-Q6_K 21.98 GB | **204800** | 31321 / 32607 `[SZACUNEK ovh]` | plain 64 / 52 / 43; z MTP ~110 po 64k `[SZACUNEK]` | opcja (faza 3) |

**Odstępstwo od raportu 33 na 16 GB (świadome):** raport proponuje UD-Q3_K_XL `--n-cpu-moe 8`. fitcalc pokazuje, że
**UD-IQ4_XS z `--n-cpu-moe 11` też mieści 131k** (szczyt 15246 MiB, zapas 1065; max 168k) przy decode po 64k 62 vs 66 t/s
(−6%) `[SZACUNEK]`; z MTP (ramię U1) n 15 nadal 131k (szczyt 15177, max 156k). Wyższy kwant przy prawie tej samej prędkości wygrywa (SOP §4: najwyższa jakość, która się mieści).
Do tego **jeden plik dla wszystkich kart 10–16 GB**: jedna bramka E7, jedna referencja md5. Q3_K_XL zostaje kwantem
zapasowym dla 16 GB, gdyby J5 (TTFT) albo J4 wypadły na granicy.

**Doładowanie Vast: $8** (pełny: 3090 + 5060 Ti + 4060 Ti + 3060 + 5090 = $8.19 − kredyt $0.23). **Wariant oszczędny:
$3** (3090 + 5060 Ti = $2.83 − $0.23 = $2.60): jedna karta gęsta 24 GB i jedna MoE 16 GB. Opcja 3080: +$1.77. §6.

Kolejność: E7 (lokalnie, $0) → faza 1 (3090 i 5060 Ti równolegle) → faza 2 (4060 Ti i 3060 po wyniku 5060 Ti) →
faza 3 (5090). Jeśli E7 da IQ4_XS ✗ J1 → MoE nie idzie w chmurę, zostaje sama faza 1 dla 3090 ($1.79).

## 1. Model pamięci (z nagłówków GGUF i logów serwera)

### 1.1 Architektura kandydatów (nagłówki: lokalne pliki + HF range requests, `fitcalc.py`; nic nie pobrane w całości)

| model | warstwy | pełna uwaga | n_head_kv × head_dim | KV q4_0 B/token (cel + MTP) | stan rekurencyjny | uwagi |
|---|---|---|---|---|---|---|
| Qwen3.8-27B (wszystkie UD/AP, Swift, Saluki-MTP) | 64 + 1 MTP (`nextn_predict_layers=1`) | 16 (co 4., `full_attention_interval=4`: 3,7,…,63) + 1 w MTP | 4 × 256 | 18 432 + 1 152 | 48 warstw GDN: S 144.0 MiB + R 5.6 MiB f32; bufor RS z rollbackiem **252.19 MiB** (log) | słownik 248 320, `token_embd` na hoście |
| Qwen3.8-27B UD-IQ1_M/IQ2_XXS/IQ2_S, Saluki (bez MTP), Bonsai | 64 | 16 | 4 × 256 | 18 432 | jw. | brak tensorów MTP |
| LFM2.5-24B-A2B | 40 (30 shortconv + 10 GQA) | 10 | 8 × 64 | q8_0 (decyzja): 10 880 | shortconv `l_cache=3`, < 1 MiB | `context_length` **131072** (max 128k), głowica związana (token_embd na GPU) |
| Qwen3.5-9B | 32 | 8 | 4 × 256 | 9 216 | 24 GDN: S 48 MiB | brak MTP w GGUF unsloth |

Rozmiary wag na GPU (= wszystkie tensory bez `token_embd`), MiB: UD-Q2_K_XL 8965 (= log `CUDA0 model buffer 8965.31`),
UD-IQ3_XXS 10020, UD-IQ3_S 10952, UD/AP-Q3_K_XL 12006, UD/AP-IQ4_XS 13061, UD-Q4_K_S 14115, UD-Q4_K_M 15009,
UD-Q4_K_XL 16053 (= log 16053.22), UD-Q5_K_S 17109, UD-Q5_K_M 18163, UD-Q5_K_XL 18905, UD-Q6_K 19960, UD-Q6_K_M 21014,
Swift IQ3_XXS-mtp 9560, Swift IQ3_S-mtp 11160, Saluki-MTP 7687, Saluki 7257, 9B Q8_0 8045, 9B UD-Q5_K_XL 5754,
LFM QAD-Q4_0 12941 (wszystkie tensory: głowica związana), LFM Q6_K 18769 (jw.). Typy głowicy `output`: Q2/IQ3_XXS Q4_K, Q3_K_XL/IQ4_XS
Q5_K, Q4_K_S…Q5_K_M Q6_K, Q5_K_XL/Q6_K* Q8_0.

### 1.2 Składniki (llama-server naszego forka, ramię T, KV q4_0)

Z logów z pełnym rozbiciem buforów: `~/qwen-opt/cloud/results/opt-4070ti-20261020/logs/kvdbg.server.log:173,195,201,208,231,240,249-251,328`
(Q2_K_XL, c 36864), `nv-amp-3080-f3080-20261020/logs/dbg.T.ckpt.server.log:169,191,197,204,227,236,245-247`,
`magnitude-vs-3090-20261016/harness/qwen-fork/logs/llama.cpp-block-1.log:163,185,198,221,230,239,241` (Q4_K_XL, c 64512).

```
VRAM_loaded(c) = W_gpu                                   # wagi bez token_embd
               + 252.19                                  # RS (GDN, rollback replay)
               + 100.29·(ub/512) + c·(18432 + 10·ub) B   # KV celu + bufor obliczeń celu (280.29 @36864 → 415.29 @64512 ⇒ 5120 B/token @ub512)
               + 80.28·(ub/512)  + c·(1152 + 10·ub) B    # kontekst draftu MTP (KV 40.50 @36864; bufor 260.28 → 395.28)
               + head64k + emb64k + 385.2                # T: głowica draftu 64k (Q4_K 180 / Q6_K 262.5 / Q3_K 137.5 MiB),
                                                         #    embeddingi 64k (Q2_K 105 MiB), requant MTP iq4_xs (385.2)
               + ovh(karta)                              # kontekst CUDA, cuBLAS, pule przy starcie
VRAM_peak(c, p) = VRAM_loaded(c) + g·p                   # p = długość promptu; g = pule konwersji K/V q4_0→f16 dla FA MMA
                                                         # w prefillu (31-4060ti.md:64) + re-rezerwacja grafu
usable c = max c: VRAM_peak(c, p=c) + 512 MiB ≤ VRAM     # g = 18 000 B/token do planu (górna obwiednia), 14 000 centralnie
```

ovh dopasowany na pierwszym punkcie każdej karty (MiB): 3060 174, 4060 Ti 184, 5060 Ti 194, 4070 Ti 266, 3090 338,
3080 417 (ub 256, ścieżka cuBLAS IQ1_M), XTX (HIP) 220; 4090 480 i 5090 600 `[SZACUNEK: ovh ≈ 120 + 2.8 × liczba SM]`.
U1 (upstream) zajmuje mniej niż T o 206–526 MiB (brak głowicy 64k i requantu), więc T jest ramieniem wiążącym.

### 1.3 Walidacja (tabela błędów, wszystkie zmierzone punkty)

| karta | plik (ramię T) | -c | ub | KV | po załadowaniu zmierzone | model | błąd | szczyt zmierzony (prompt) | model szczyt g=14K / g=18K | błąd g=18K | źródło |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 3090 | UD-Q4_K_XL | 131072 | 512 | q4_0 | 21380 | 21380 (fit ovh) | 0 | 22198 (55569) | 22122 / 22334 | +136 | `27-3090-final.md:207` |
| 3090 | UD-Q4_K_XL | 204800 | 512 | q4_0 | 23493 | 23477 | −16 | OOM przy 55.6k (+219.8 MiB) | model: 24431 + 220 > 24576 → OOM ✓ | — | `27-3090-final.md:211` |
| 3090 | Uncensored Q4_K_M | 204800 | 512 | q4_0 | 22764 | 22763 | −1 | 60k OK | — | — | `27-3090-final.md:160,213` |
| 3090 | UD-Q6_K_M | 32768 | 512 | q4_0 | 23706 | 23704 | −2 | 24120 (32041) | 24132 / 24254 | +134 | `31-3090.md:44` |
| XTX (HIP) | UD-Q4_K_XL | 204800 | 512 | q4_0 | 23359 | 23359 (fit ovh) | 0 | — | — | — | `qwen-opt/bench-final/queue-logs/fb-qwen-T-p1.log:1` |
| 4070 Ti | UD-Q2_K_XL | 32768 | 512 | q4_0 | 11265 | 11266 | +1 | 11545 (~31.5k) | 11688 / 11808 | +263 | `31-4070ti.md:47` |
| 4070 Ti | UD-Q2_K_XL | 36864 | 512 | q4_0 | 11383 | 11383 (fit ovh) | 0 | 11817 (34566) | 11844 / 11976 | +159 | `31-4070ti.md:46` |
| 4070 Ti | UD-Q2_K_XL | 40960 | 512 | q4_0 | 11499 | 11499 | 0 | OOM przy 38.5k (+155.6) | 12160 + 156 > 12282 → OOM ✓ | — | `31-4070ti.md:45` |
| 4070 Ti | UD-Q2_K_XL | 49152 | 512 | q4_0 | 11731 | 11732 | +1 | OOM przy 46k | 12521 > 12282 → OOM ✓ | — | `31-4070ti.md:44` |
| 3060 | UD-Q2_K_XL | 36864 | 512 | q4_0 | 11291 | 11291 (fit ovh) | 0 | 11903 (35778) | 11768 / 11905 | +2 | `31-3060-3080.md:35,78` |
| 3060 | Saluki IQ2-mix-MTP (n=2) | 20480 | 512 | **q8_0** | 9811 | 9809 | −2 | — | — | — | `27-3090-final.md:187-188` |
| 3080 | UD-IQ2_XXS + graft MTP | 32768 | 256 | q4_0 | 9015 | 9015 (fit ovh) | 0 | 9661 (31385) | 9434 / 9554 | **−107** | `31-3060-3080.md:42,62` |
| 5060 Ti | UD-IQ4_XS | 36864 | 512 | q4_0 | 15479 | 15479 (fit ovh) | 0 | OOM na 2. 16k w sekwencji | reguła: odrzuca ✓ | — | `31-5060ti.md:40,66` |
| 5060 Ti | UD-IQ4_XS | 32768 | 512 | q4_0 | — | 15363 | — | 15839 (28.1k) | 15738 / 15845 | +6 | `31-5060ti.md:40` |
| 4060 Ti | UD-IQ4_XS | 32768 | 512 | q4_0 | 15353 | 15353 (fit ovh) | 0 | 15817 (31.8k) | 15777 / 15898 | +81 | `31-4060ti.md:62` |
| 4060 Ti | UD-IQ4_XS | 36864 | 512 | q4_0 | 15471 | 15469 | −2 | 15945 (35.9k), OOM w sekwencji | 15948 / 16085 → odrzuca ✓ | +140 | `31-4060ti.md:61` |
| 4060 Ti | UD-IQ4_XS | 40960 | 512 | q4_0 | 15587 | 15586 | −1 | 15943 (40.6k), OOM 2. prompt | 16128 / 16282 → odrzuca ✓ | +339 | `31-4060ti.md:60` |
| 4060 Ti | UD-IQ4_XS | 49152 | 512 | q4_0 | 15819 | 15819 | 0 | OOM przy 48k | 16643 > 16380 → OOM ✓ | — | `31-4060ti.md:59` |
| 4060 Ti | UD-Q3_K_XL (stary build) | 32768 | 512 | **q8_0** | 14848 | 14841 | −7 | — | — | — | `29-4060ti.md:70` |

Wnioski z walidacji:
- **Część statyczna: błąd poza punktem dopasowania |≤ 16| MiB** na 13 punktach (inne `-c` od 20k do 205k, inne kwanty,
  KV q8_0, inny build, inne hosty tej samej karty). Nachylenie 29.8 KB/token potwierdzone na 3090 (131k → 205k).
- **Szczyt: g = 18 KB/token przeszacowuje o 2–339 MiB** (bezpiecznie) wszędzie poza 3080 (−107 MiB: ub 256 + bufory
  cuBLAS dla IQ1_M) — dla niej preset g = 21.6 KB. Reguła „szczyt(g=18K) + 512 ≤ VRAM” odrzuca wszystkie 6 konfiguracji,
  które zmierzono jako OOM, i odrzuca 2 konfiguracje, które przeszły z zapasem < 512 MiB (3060 c36864: 385; 3090 Q6_K_M: 456),
  a 2 przeszłe z zapasem 472–563 MiB odrzuca o 30–46 MiB (konserwatywnie).
- **Największa niepewność: g zmierzone tylko do promptu 55.6k.** Przy 131k ekstrapolacja liniowa daje +2.25 GiB (g=18K).
  Dlatego `-c` zatwierdza dopiero test wypełnienia na karcie (SOP §7), a fitcalc służy do wyboru kwantu przed wynajmem.

### 1.4 Rozszerzenie dla MoE z ekspertami w RAM (fitcalc v2, raport 33 §1.1)

Qwen3.6-35B-A3B (`qwen35moe`, nagłówek `unsloth/Qwen3.6-35B-A3B-MTP-GGUF`): 40 warstw = 10 pełnej uwagi (2 × 256,
KV q4_0 5 760 B/token) + 30 GDN + MTP (`nextn`, KV 576 B/token); 256 ekspertów, 8 aktywnych + shared; eksperci UD-IQ4_XS
15.22 GB z 17.66 GB wag na GPU-bez-`token_embd`; aktywne bajty/token 2.49 GB. `--n-cpu-moe N` zdejmuje ekspertów warstw
0..N−1 do RAM. Ten sam rachunek co §1.2 (RS z GDN, bufory `c·10·ub`, ovh karty, wzrost szczytu g × skala warstwy 0.5),
więc walidacja z §1.3 przenosi się na część stałą; **dla qwen35moe nie ma jeszcze ani jednego naszego pomiaru VRAM** —
pierwszy test na karcie (SOP §7) kalibruje.

| karta, plik | n | VRAM po załadowaniu / szczyt @131k | zapas | eksperci w RAM | max `-c` | ramię z MTP (n) |
|---|---|---|---|---|---|---|
| 5060 Ti / 4060 Ti, UD-IQ4_XS | 11 | 14684 / 15246; 14674 / 15236 | 1065 / 1144 | 4.11 GB | 168k / 174k | n 15: 14052 / 15177, 5.6 GB RAM, max 156k ✓ |
| 5060 Ti, UD-IQ4_XS | 12 | 14328 / 14890 | 1421 | 4.48 GB | 193k | (zapas na `-ub 1024`, +640 MiB) |
| 4060 Ti, UD-Q3_K_XL (zapas) | 8 | 14998 / 15560 | 820 | 2.79 GB | 151k | — |
| 5060 Ti, UD-Q3_K_XL (zapas) | 8 / 12 (MTP) | 15008 / 15570; 14472 / 15597 (U1) | 741 / 714 | 2.79 / 4.18 GB | 146k / 139k | n 12 ✓ |
| 3060, UD-IQ4_XS | 21 | 11104 / 11666 | 622 | 7.84 GB | 138k | n 24: max 123k ✗; **n 25: 10472 / 11597, 9.3 GB RAM, max 138k ✓** |
| 4070 Ti, UD-IQ4_XS | 21 | 11196 / 11758 | 524 | 7.84 GB | 131k | — |
| 3080, UD-IQ4_XS | 28 | 8855 / 9530 | 710 | 10.45 GB | 143k | — |

Prefill z ekspertami w RAM: dla ubatcha ≥ 32 tokenów llama.cpp kopiuje wagi ekspertów warstw CPU na GPU co ubatch
(`GGML_OP_OFFLOAD_MIN_BATCH`, raport 04 §2.2.5). Szacunek `[SZACUNEK]` samej kopii przy `-ub 512`
(131072/512 = 256 ubatchy): 5060 Ti (4.1 GB, PCIe 4 x8 ~13 GB/s) ~80 s; 4060 Ti (4.1 GB, PCIe 3 x8 ~6.5 GB/s) ~160 s;
3060 (7.8 GB, PCIe 3 x16 ~12 GB/s) ~170 s; 3080 (10.5 GB) ~225 s — plus obliczenia. Przy 32k: ćwierć tego. `-ub 1024`
połowi kopie kosztem +640 MiB VRAM przy 131k (mieści się na 16 GB przy n 12, nie na 10–12 GB). Dlatego **PCIe ≥ gen3
x8 to twardy filtr hosta**, a TTFT jest bramką J5.

## 2. Kandydaci i jakość

KLD do BF16, protokół 16e (wiki / czat PL; `16e-kwanty-kld.md:133-144`). `[SZACUNEK]` = log-liniowa interpolacja po
rozmiarze pliku w rodzinie unsloth UD między U3 (13.15 GB), U4 (17.56 GB) i Q8_0 (29.05 GB).

### 2.1 Qwen3.8-27B (24/32 GB)

| kandydat | GB | KLD wiki / czat | J1 | uwagi |
|---|---|---|---|---|
| UD-Q6_K_M / Q6_K | 23.09 / 21.98 | ~0.008 / ~0.009; ~0.009 / ~0.011 `[SZACUNEK]` | ✓ | 5090 |
| UD-Q5_K_XL / Q5_K_M / Q5_K_S | 20.88 / 19.77 / 18.67 | ~0.010–0.013 / ~0.013–0.019 `[SZACUNEK]` | ✓ | nie mieszczą 131k na 24 GB |
| **UD-Q4_K_XL (U4)** | 17.56 | **0.0153 / 0.0226** (zmierzone) | ✓ | 3090 |
| UD-Q4_K_M / IQ4_XS | 16.46 / 14.25 | ~0.019 / ~0.029; ~0.031 / ~0.049 `[SZACUNEK]` | ✓ | więcej ctx, gorsza jakość |
| U3 / A3 (Q3_K_XL) | 13.15 | 0.039 / 0.0635; 0.040 / 0.056 | ✓ (próg) | na 16 GB nie mieści 131k z MTP (v1 §3) |
| IQ3_S i niżej, Saluki, Bonsai | ≤ 12.04 | 0.054–0.352 / 0.088–0.437 | ✗ | |

### 2.2 Qwen3.6-35B-A3B (10–16 GB) — bramka E7 przed chmurą

Jakość bazowa (raport 33 §3): AA v4.3.2 **18** (Qwen3.8-27B: 34), GPQA-D 86.0, SWE-bench V 73.4, LCB v6 80.4 — najlepszy
model, który mieści 131k na 10–16 GB; gęste alternatywy (Ornith/Qwen3.5-9B, Gemma 4 12B) mają AA 11–14 i 20–40 t/s.
**KLD kwantów Qwen3.6 nie mamy** (unsloth publikuje tylko wykres). Dlatego:

| E7 (XtxLab, lokalnie, raport 35) | plik | próg PASS | jeśli FAIL |
|---|---|---|---|
| E7.1 | UD-IQ4_XS 18.21 GB (MTP-GGUF) | KLD do BF16 wiki ≤ 0.05 i czat PL ≤ 0.07, protokół 16e (20 × 2048, 5 korpusów) | MoE nie idzie w chmurę na 10–12 GB; 16 GB: UD-Q4_K_M 22.66 GB z większym n (przeliczyć fitcalc, RAM ≥ 48 GB) albo „brak modelu” |
| E7.2 | UD-Q3_K_XL 17.23 GB | jw. | 16 GB tylko IQ4_XS |
| E7.3 | J2 na CPU/XTX: 3 czaty PL + 3 EN, 3 edycje kodu z testem, ramię plain | wszystkie poprawne | brak chmury |
| E7.4 | czy nasz fork ładuje `qwen35moe` z flagami T (`--spec-draft-vocab` 64k, `--spec-draft-head-type iq4_xs`, `--spec-mtp-type iq4_xs`) i md5 T=0 `LLAMA_GPU_VERIFY` 0 == 1 na CPU/XTX | działa / nie | ramię T bez tych flag (lookup + share + GV) |

Kampania MoE startuje po E7.1 + E7.3 = PASS. Ornith-1.5-35B-A3B (ten sam szkielet, MIT) jest #2 z raportu 33 — nie
wchodzi do tej kampanii (jakość tylko z deklaracji vendora, MTP w pliku z akceptacją ~0.13).

## 3. Karty: decyzje

### RTX 3090 24 GB — **Qwen3.8-27B UD-Q4_K_XL, `-c 131072`, ramię T** (bez zmian względem v1)

| model | max `-c` pewny / górny | J1 | ≥131k | t/s | decyzja |
|---|---|---|---|---|---|
| UD-Q6_K_M … Q5_K_M | 27–91k | ✓ | ✗ | Q6_K_M czat T=1 73.2 (`31-3090.md:66`) | odpada |
| **UD-Q4_K_XL** | **137k / 171k** | ✓ zmierzone | ✓ | czat T=1 93.3, mvs 349 (`27:232,234`); po 32k / 60k T=1 64.8 / 56.7 (host 280 W, `27:202,200`); po 128k ~43 `[SZACUNEK]`; TTFT 32k 28.8 s, 60k 60.4 s (`27:204-206`) | **WYBRANY** |
| UD-Q4_K_M / IQ4_XS | 159k / 203k | ✓ szac. | ✓ | — | nie: kontekst ponad 131k za cenę jakości |
| Qwen3.6-35B-A3B / Ornith (MoE) | 164–211k | E7 | ✓ | plain 106–117 po 64k `[SZACUNEK]` | „tryb szybki”, nie w tej kampanii (AA 18 vs 34) |

### RTX 5060 Ti 16 GB — **Qwen3.6-35B-A3B UD-IQ4_XS, `--n-cpu-moe 11`, `-c 131072`**

| model | konfiguracja | max `-c` | szczyt @131k | t/s 0/64k/131k | jakość | decyzja |
|---|---|---|---|---|---|---|
| **Qwen3.6 UD-IQ4_XS** | n 11, ub 512 (n 12 przy ub 1024; n 15 z MTP) | 168k | 15246 | 88 / 62 / 48 | E7.1 | **WYBRANY** |
| Qwen3.6 UD-Q3_K_XL | n 8 (n 12 z MTP) | 146k | 15570 | 95 / 66 / 50 | E7.2 | zapas |
| Qwen3.6 UD-IQ3_XXS (całość w VRAM) | n 0 | 162k | 15322 | 132 / 81 / 59 | ✗ prawdopodobnie (3-bit IQ) | nie |
| Qwen3.8-27B ≥ Q3_K_XL | z MTP | 51–66k | — | — | ✓ | ✗ J3 (v1 §3) |

Spekulacja: MTP z pliku (n=2) mieści 131k przy n 15 (decode plain po 64k 59 vs 62 t/s, 5.6 GB RAM); raport 33 §6: MTP przy ekspertach w RAM daje mało lub ujemnie
(numsu 8 GB), 3060 +20% (tanhaien) → pomysł O-M1 w pętli, nie domyślnie.

### RTX 4060 Ti 16 GB — jak 5060 Ti (ten sam plik, n 11)

Pasmo 288 GB/s i PCIe 3 x8: szczyt 15236 / 16380, decode 65 / 44 / 33 t/s `[SZACUNEK]`, TTFT 131k ~2× dłuższy niż 5060 Ti `[SZACUNEK]`. Faza 2: tylko gdy
5060 Ti zaliczy J1–J5 (ten sam plik, więc J1/J2 przenoszą się; mierzymy J3–J5).

### RTX 3060 12 GB — Qwen3.6-35B-A3B UD-IQ4_XS, `--n-cpu-moe 21`, `-c 131072` — **warunkowo**

**Obowiązuje decyzja [[2026-10-16-saluki-bonsai-na-3060]]** (tylko Saluki/Bonsai). Oba oblewają J1 (KLD-wiki 0.257 /
0.352, `16e-kwanty-kld.md:143-144`), więc bez zmiany decyzji: „ta karta: brak modelu spełniającego próg”. Po zgodzie
użytkownika na Qwen3.6: szczyt 11666 / 12288 (zapas 622), 7.8 GB RAM, 52 / 40 / 32 t/s `[SZACUNEK]`; społeczność:
Q4_K_M ncmoe 25 → 50–58 t/s przy 32k (raport 33 §4). Ryzyko J5: TTFT 32k ~45–60 s, 131k ~4–5 min `[SZACUNEK]`.

### RTX 3080 10 GB — opcja (UD-IQ4_XS, n 28, szczyt 9530, 10.5 GB RAM)

Na Vast 18:48 UTC brak oferty z transferem ≤ $0.002/GB, RAM ≥ 32 GB i PCIe ≥ x8; najbliższa: 54738116 (Hiszpania,
$0.265/h, $0.0026/GB, 64 GB RAM, gen3 x16) — transfer 25 GB = $0.065, ale to łamie regułę → tylko z
`--allow-paid-traffic` i zgodą użytkownika. Najdłuższy TTFT z kart (10.5 GB ekspertów przez PCIe).

### RTX 4070 Ti 12 GB — konfiguracja jak 3060 (n 21, szczyt 11758), **brak ofert** na Vast → nie w kampanii.

### RTX 5090 32 GB — Qwen3.8-27B UD-Q6_K, `-c 204800` (bez zmian względem v1; faza 3, referencja)

## 4. Protokół testu (SOP §7–§9; poniżej to, co dochodzi dla MoE)

1. **hostcheck box** w pierwszych 5 min: `hostcheck.sh box <url> <GB> <eksperci_GB>` — limit mocy = domyślny, HF ≥ 25 MB/s,
   dysk, **MemAvailable ≥ eksperci + 8 GB, PCIe link ≥ gen3 x8**; FAIL → zniszcz.
2. **Staging raz:** jeden plik (3090: UD-Q4_K_XL; 10–16 GB: `unsloth/Qwen3.6-35B-A3B-MTP-GGUF` UD-IQ4_XS, 18 209 036 576 B,
   sha256 `df27a780…`), buildy upstream + `nv-v2`, nigdy w trakcie pomiaru. Na hoście z RAM ≤ 48 GB: `--no-mmap`
   nie używać (mmap + eksperci w RAM to jedna kopia).
3. **Test wypełnienia (J3) + strojenie MoE (≤ 30 min):** sekwencja 512 → 16k → 64k → (c−1.2k) T=0 → drugi (c−1.2k) T=1 →
   czat, VRAM co 0.2 s, RAM (`free -m`) co 1 s; siatka: n ∈ {n_fit, n_fit+1, n_fit+2} × ub ∈ {512, 1024 jeśli mieści}; wybór =
   najmniejsze n, które przechodzi z zapasem ≥ 512 MiB; potem TTFT 32k dla każdej przechodzącej pary (J5). PCIe
   `pcie.link.width.current` pod obciążeniem prefillu zapisany.
4. **Bramki jakości na karcie:** J3 `needle.py --tokens 131072` (5/5, 0 zmyśleń); J2 ramię T (3 PL + 3 EN + 3 edycje kodu);
   md5: GPU verify 0 == 1 (22 wiersze).
5. **Ramiona przy wybranym `-c`, n, ub:**
   - U0 = upstream `llama-server -m` (domyślny `-fit`; dla MoE `-fit` sam dobiera offload — zapisać jego n_ctx i n);
   - U1 = upstream `-fit off -ngl 99 --n-cpu-moe <n> -fa on -ctk q4_0 -ctv q4_0 -c 131072 -ub <ub> -np 1 --jinja
     --cache-ram 8192 --reasoning-effort low -t <kwota>` (gęsty 27B: + `--spec-type draft-mtp --spec-draft-n-max 4 -ctkd/-ctvd q4_0`);
   - T = gałąź `nv-v2` z flagami U1 + `LLAMA_SPEC_LOOKUP=3 LLAMA_SPEC_LOOKUP_W=16 LLAMA_SERVER_CACHE_SHARE_MIN=1024
     LLAMA_GPU_VERIFY=1`; dla 27B dodatkowo MTP n=4 + słownik draftu 64k + głowice iq4_xs (jak `31-*`); dla Qwen3.6 MTP
     tylko jeśli O-M1 przejdzie (plain + lookup domyślnie).
6. **Obciążenia:** czat T=1 (6 × 3 × 400 tok); mvs T=0 (4 × 1024) + edit; **decode po 16k / 64k / 128k** T=0 i T=1 (jeden
   haystack rosnący prefiksami → prompt cache oszczędza prefill); **prefill + TTFT przy 32k i 131k** (zimny cache,
   osobny serwer, 2 powtórzenia); VRAM i RAM.
7. **ABBA** U0 U1 T | T U1 U0, świeży serwer na ramię, p1 seedy 1–3, p2 seedy 4–6, CI95 bootstrap; taskset na jednym
   węźle NUMA/CCX, **`-t` = kwota CPU** (eksperci liczą się na CPU — liczba wątków ma znaczenie, w siatce §4.3 sprawdzić
   `-t` kwota vs kwota−2).
8. **Pętla optymalizacji (≤ 10 min GPU na pomysł):**

| # | pomysł | dowód | 3090 (27B) | 16 GB MoE | 12 GB MoE |
|---|---|---|---|---|---|
| O1 | `GGML_CUDA_KVQ=1` | 4060 Ti po 29.5k +28% (`31-4060ti.md:33-34,89`) | **pierwszy** | tak (10 warstw uwagi — mniejszy zysk) | tak |
| O2 | `LLAMA_SPEC_COUPLED=1` | +5.3…+6.8% T=1 (`31-3060-3080.md:146`, `31-4070ti.md:180`, `31-4060ti.md:87`) | tak | tylko z MTP | tylko z MTP |
| O3 | `GGML_CUDA_GDN_MMA=1` (prefill) | pp +3.8% (`31-4060ti.md:88`) | tak | **tak (TTFT)** | tak |
| O4 | głębokość draftu n=3/5 | `31-3060-3080.md:147`, `31-4060ti.md:91` | tak | — | — |
| O5 | `LLAMA_SERVER_YIELD_FAST=2` | +1.0% (`31-4070ti.md:178`) | gdy host < 8 rdzeni | tak (CPU zajęty ekspertami) | tak |
| O-M1 | MTP z pliku n=2 (+ coupled); 16 GB n 15, 3060 n 25 (fitcalc §1.4) | raport 33 §6: 3060 +20%, 8 GB ±; akceptacja 83% (n=2) | — | tak | tak |
| O-M2 | `-ub 1024` / `-b 2048` (mniej kopii ekspertów w prefillu) | §1.4 | — | **tak (J5)** | nie mieści |
| O-M3 | `GGML_OP_OFFLOAD_MIN_BATCH` (próg kopiowania ekspertów) i `-t` | raport 04 §2.2.5 | — | tak | tak |
| O7 | słownik draftu 32k | sufit ~2% (`31-4060ti.md:93`) | tak | — | — |
| O9 | Q6_K MMVQ (PIPE debug na CPU) | `31-3090.md:21-22,136-137` | po teście bitowym | — | — |

   Przyjęcie: CI95 t/s wyklucza 0 albo ms/krok spada na każdym prompcie + bramki md5/KLD (SOP §9). Finał T' vs T na
   początku okna kredytu, potem pełne U0/U1/T/T'.

## 5. Logistyka

### 5.1 Filtr hostów (live, 2026-10-20 18:48 UTC)

```
# 24/32 GB (gęsty, bez ekspertów w RAM):
vastai search offers 'gpu_name=<GPU> num_gpus=1 gpu_ram>=<V> reliability>0.98 verified=true rentable=true direct_port_count>=1
  disk_space>=60 inet_down>=300 cuda_vers>=12.8 inet_down_cost<=0.002 inet_up_cost<=0.002 cpu_cores_effective>=4
  cpu_ram>=24 geolocation notin [CN]' --storage 70 -o dph_total --raw
# 10–16 GB MoE (eksperci w RAM, prefill przez PCIe):
...  cpu_cores_effective>=4 cpu_ram>=32 pci_gen>=3 gpu_lanes>=8 ...
```
Potem `hostcheck.sh offer <id> <GB> <h> [eksperci_GB]` (MoE: RAM ≥ max(32, eksperci + 16) GB, PCIe ≥ gen3 x8, transfer
≤ $0.002/GB), `up.sh <id> --download-gb <GB> --hours <h> --go`, na boxie `hostcheck.sh box <url> <GB> [eksperci_GB]`
(limit mocy = domyślny, MemAvailable ≥ eksperci + 8, HF ≥ 25 MB/s). Hosty x1 (riser, `31-3060-3080.md:23`) są wykluczone.

| karta | oferta (hostcheck PASS) | $/h z dyskiem | GPU $/h | transfer $/GB | rel | RAM / PCIe | zapas |
|---|---|---|---|---|---|---|---|
| 3090 | **52272575** Oregon | 0.246 | 0.227 | 0.0013 | 0.998 | 32 GB / 4.0 x16 | 51372161 Virginia $0.296 |
| 5060 Ti | **54073766** Australia | 0.186 | 0.173 | ~0 | 0.998 | 32 GB / 4.0 x8 | — (jedyna) |
| 4060 Ti | **56468701** Floryda (host z `31-4060ti.md`, 165 W stock) | 0.186 | 0.173 | ~0 | 0.991 | 48 GB / 3.0 x8 | 13645294 Kentucky $0.193 |
| 3060 | **55447316** Michigan | 0.126 | 0.093 | 0.0013 | 0.998 | 40 GB / 3.0 x16 | — (z płatnym transferem: 47594089 $0.099, $0.0026/GB) |
| 3080 | 54738116 Hiszpania (płatny transfer) | 0.265 | 0.252 | **0.0026** | 0.993 | 64 GB / 3.0 x16 | — |
| 4070 Ti | — | — | — | — | — | — | brak jakichkolwiek ofert |
| 5090 | **56935334** Wietnam | 0.805 | 0.785 | ~0 | 0.990 | 51 GB / 5.0 x16 | 50452984 Ontario $0.69 (transfer $0.00195) |

### 5.2 Staging (jeden plik na kartę)

3090: `unsloth/Qwen3.8-27B-GGUF` `Qwen3.8-27B-UD-Q4_K_XL.gguf` (17 559 178 144 B, sha256 3f227079…).
10–16 GB: `unsloth/Qwen3.6-35B-A3B-MTP-GGUF` `Qwen3.6-35B-A3B-UD-IQ4_XS.gguf` (18 209 036 576 B, sha256 df27a780…; MTP
w pliku — ten sam plik dla ramienia plain i O-M1). 5090: `Qwen3.8-27B-UD-Q6_K.gguf` (21 983 677 344 B). Pobranie =
model + obraz ~5 GB + źródła ~1 GB ≈ 24–28 GB.

### 5.3 Faza 0 — lokalnie, $0, przed doładowaniem

| # | zadanie | kto |
|---|---|---|
| **E7** | KLD Qwen3.6 UD-IQ4_XS / UD-Q3_K_XL do BF16 (protokół 16e) + J2 + fork z flagami T dla `qwen35moe` (§2.2) | XtxLab (raport 35) |
| F0.1 | gałąź `nv-v2` = `cuda-topka2` + coupled `7cdc0121b` + host-gap `49bc932a8` + GDN MMA `e55006b3a` + KVQ `007a6f813`; kompilacja sm_86/89/120 lokalnie | Opus + DeepSeek |
| F0.2 | `corpus256k.txt` (PL+EN), rozmiary 64k/128k w `long_bench.py`, `fillseq.sh` z RAM-em i siatką n × ub | Opus |
| F0.3 | zestaw J2 (3 PL + 3 EN + 3 edycje kodu z testem) | Opus |
| F0.4 | `needle.py` sprawdzony na CPU małym modelem | Opus |
| F0.5 | `ttft.py`: zimny prefill 32k / 131k, osobny serwer, zapis PCIe width i RAM | Opus |
| F0.6 | (zrobione) fitcalc ramienia MTP: 16 GB n 15, 3060 n 25 — §1.4 | PlanNvV2 |

### 5.4 Godziny na kartę

| karta | build + pobranie | wypełnienie + siatka n×ub + J2/J3/J5 | ABBA U0/U1/T (z TTFT 32k/131k) | optymalizacja + finał | raport | razem (+25%) |
|---|---|---|---|---|---|---|
| 3090 (27B) | 0.45 | 0.8 | 0.75 | 1.6 | 0.2 | **5.0 h** |
| 5060 Ti (MoE) | 0.45 | 0.8 | 0.9 | 0.8 | 0.2 | **4.0 h** |
| 4060 Ti (MoE) | 0.45 | 0.8 | 0.9 | 0.8 | 0.2 | **4.0 h** |
| 3060 (MoE) | 0.45 | 0.9 | 1.1 (prefill 131k ~4–5 min/ramię) | 0.8 | 0.2 | **4.5 h** |
| 3080 (opcja) | 0.45 | 0.9 | 1.1 | 0.8 | 0.2 | 4.5 h |
| 5090 (27B) | 0.4 | 0.6 | 0.5 | 1.2 | 0.2 | **3.5 h** |

## 6. Koszt i doładowanie (ceny live 18:48 UTC; `hostcheck.sh offer`; dysk 70 GB; +30%; rezerwa = 1–2 złe hosty × 0.3 h)

| karta (oferta) | h | GPU | dysk | transfer (GB × $/GB) | suma | ×1.3 | rezerwa | **razem** |
|---|---|---|---|---|---|---|---|---|
| 3090 (52272575) | 5.0 | $1.133 | $0.096 | 25 × 0.0013 = $0.033 | $1.263 | $1.64 | $0.15 | **$1.79** |
| 5060 Ti (54073766) | 4.0 | $0.693 | $0.051 | 24 × ~0 = $0.000 | $0.745 | $0.97 | $0.07 | **$1.04** |
| 4060 Ti (56468701) | 4.0 | $0.693 | $0.051 | 24 × 0.00004 = $0.001 | $0.745 | $0.97 | $0.07 | **$1.04** |
| 3060 (55447316) | 4.5 | $0.420 | $0.144 | 25 × 0.0013 = $0.034 | $0.598 | $0.78 | $0.05 | **$0.83** |
| 5090 (56935334) | 3.5 | $2.375 | $0.067 | 28 × ~0 = $0.000 | $2.442 | $3.17 | $0.31 | **$3.49** |
| 3080 (54738116, opcja) | 4.5 | $1.134 | $0.059 | 25 × 0.0026 = $0.065 | $1.258 | $1.64 | $0.13 | $1.77 |

- **Pełny** (3090 + 5060 Ti + 4060 Ti + 3060 + 5090): $8.19 − kredyt $0.23 (`vastai show user`, 18:50 UTC) = $7.96 →
  **doładowanie $8**. Bez 3060 (jeśli decyzja 2026-10-16 zostaje): $7.36 → $7.50.
- **Oszczędny** (3090 + 5060 Ti): $2.83 − $0.23 = $2.60 → **doładowanie $3**.
- Z opcją 3080: +$1.77. Inżynierowie Opus i robotnicy DeepSeek poza budżetem Vast.

### 6.1 Kolejność i strażnik kredytu

1. E7 + F0 lokalnie (bez kredytu). E7 FAIL → tylko 3090.
2. Faza 1 równolegle: 3090 i 5060 Ti (osobni inżynierowie, osobne `--hours`).
3. Faza 2 po raporcie 5060 Ti (J3–J5 PASS): 4060 Ti, 3060 (po zmianie decyzji), 3080 (po zgodzie na transfer).
4. Faza 3: 5090.
5. Co 30 min `vastai show user`; kredyt < 1.3 × koszt pozostałych godzin wszystkich boxów → finał T/T', bez nowych pomysłów.

## 7. Organizacja pracy

- Jeden inżynier Opus na kartę, brief = `qwen-opt/cloud/ENGINEER-PROMPT.md` + karta parametrów z §0/§5 (dla MoE dopisać
  n, ub, eksperci_GB, J5).
- Kod piszą robotnicy DeepSeek v4.1 Flash przez `~/qwen-opt/tools/ds-agent` (brief `DEEPSEEK-WORKER-PROMPT.md`),
  ≤ 3 naraz, ≤ 45 min, bez GPU.
- Reguły jak w kampanii 31 plus: `-c ≥ 131072`, KV q4_0, jeden plik na kartę, bramki J1–J5, rozliczenie z
  `vastai show invoices-v1 --charges` po zniszczeniu.

## 8. Ryzyka

| ryzyko | skutek | zabezpieczenie |
|---|---|---|
| E7: IQ4_XS Qwen3.6 > 0.05 / 0.07 KLD (MoE z 256 ekspertami bywa czulsze na kwant) | brak modelu na 10–16 GB | chmura MoE dopiero po E7; zapas: Q4_K_M z większym n na 16 GB (RAM ≥ 48 GB) |
| **brak naszego pomiaru VRAM dla `qwen35moe`** (fitcalc kalibrowany na qwen35) | szczyt inny o ±300 MiB | zapas 1065 MiB na 16 GB; na 12 GB tylko 524–622 → siatka n_fit…n_fit+2 w teście wypełnienia |
| TTFT 131k z ekspertami w RAM to minuty (§1.4) | J5 FAIL na 4060 Ti / 3060 / 3080 | PCIe ≥ gen3 x8 w filtrze; O-M2 (`-ub 1024`) i O-M3; J5 liczony przy 32k, 131k raportowany |
| RAM hosta DDR4 i współdzielony (Vast `cpu_ram` = przydział) | decode −10–20% `[SZACUNEK]`, OOM hosta | MemAvailable ≥ eksperci + 8 GB w `hostcheck box`; RSS serwera logowany |
| spekulacja przy ekspertach w RAM nie daje zysku (raport 33 §6) | T ≈ U1 na MoE | T bez MTP domyślnie (lookup + GV + share); MTP jako O-M1 |
| nasze flagi T (słownik 64k, requant MTP) nie obsługują `qwen35moe` | brak ramienia T z MTP | E7.4 lokalnie |
| g (wzrost szczytu) zmierzone tylko do 55.6k (3090) | 131k nie mieści się z zapasem | test wypełnienia pierwszy; `-ub 256`, O1 KVQ; Q4_K_M jako jedyny zamiennik na 3090 |
| oferty znikają (3080 56540010 zniknęła w 10 min) | inna cena | `hostcheck.sh offer` tuż przed `up.sh`, oferty zapasowe w §5.1 |
| decyzja 2026-10-16 (3060) | 3060 poza kampanią | pytanie do użytkownika przed fazą 2 |
| kredyt kończy się w połowie | brak finału | rezerwa w budżecie, strażnik co 30 min, finał T/T' na początku okna, `--hours` + samozniszczenie |

## 9. Źródła

`product/research/33-modele-na-karty.md:17-35,177,190,202,213-216,255,273,301-325`; `27-3090-final.md:160,187-188,198-207,211,232-234`;
`31-3090.md:21-29,44,66`; `31-4070ti.md:44-47,178,180`; `31-3060-3080.md:10,23,35,42,62,78,146-147`; `31-5060ti.md:15,40,43,66`;
`31-4060ti.md:15,33-34,59-64,87-93`; `29-4060ti.md:70`; `16e-kwanty-kld.md:133-144`; `09-chmura-5060ti.md:174-179`;
`qwen-opt/bench-final/queue-logs/fb-qwen-T-p1.log:1`; logi buforów §1.2; fitcalc v2 na nagłówkach HF
`unsloth/Qwen3.6-35B-A3B-MTP-GGUF` (UD-IQ4_XS, UD-Q3_K_XL; 2026-10-20 18:30–19:00 UTC); oferty: `vastai search offers`
2026-10-20 18:48 UTC + `hostcheck.sh offer`; kredyt: `vastai show user` 2026-10-20 18:50 UTC.
