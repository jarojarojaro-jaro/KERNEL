# PLAN-NV-V2 — kampania NVIDIA v2: najlepszy model z kontekstem ≥ 131k na każdą kartę

Data: 2026-10-20 (UTC ~18:00). Autor: PlanNvV2 (Opus, tylko CPU, nic nie wynajęte). Procedura, z której wynika ten plan:
[`qwen-opt/cloud/SOP-DOBOR-I-POMIARY.md`](../qwen-opt/cloud/SOP-DOBOR-I-POMIARY.md); brief inżyniera:
[`qwen-opt/cloud/ENGINEER-PROMPT.md`](../qwen-opt/cloud/ENGINEER-PROMPT.md); kalkulator pamięci:
`qwen-opt/cloud/fitcalc.py`; bramka hosta: `qwen-opt/cloud/hostcheck.sh`; bramka długiego kontekstu: `qwen-opt/cloud/needle.py`.

Co poszło źle 2026-10-20 (raporty `31-*`, [[lekcja-vast-transfer-kosztuje]], [[2026-10-20-kontekst-min-131k]]):
kontekst 32–37k, 2-bitowe Qwen na 10–12 GB (wbrew [[2026-10-16-saluki-bonsai-na-3060]]), transfer $3.80 z $6.90,
kredyt skończył się w połowie. Ten plan naprawia każdy z tych punktów regułą, a nie dobrą wolą.

## 0. Werdykt

Bramki (twarde, SOP §4): **J1 jakość** KLD-wiki ≤ 0.05 i KLD-czat ≤ 0.07 (protokół 16e, do BF16); **J2 zadania** PL/EN
czat + edycja kodu poprawna; **J3 kontekst** `-c ≥ 131072`, szczyt VRAM po prompcie długości `-c` + 512 MiB ≤ VRAM,
bez OOM w pełnej sekwencji żądań, needle 5/5 przy `-c`; **J4 prędkość** decode ≥ 20 t/s po 64k (T=1); TTFT 32k raportowany.

| karta | rekomendacja | kwant (plik) | `-c` | VRAM: po załadowaniu / szczyt (model, g=18K) / całość MiB | jakość (KLD wiki / czat) | oczekiwane t/s | status |
|---|---|---|---|---|---|---|---|
| **RTX 3090 24 GB** | **Qwen3.8-27B** | **UD-Q4_K_XL** (17.56 GB, MTP w pliku) | **131072**, ub 512 | 21380 (zmierzone, `27-3090-final.md:207`) / 23630 / 24576 → zapas 946 | 0.0153 / 0.0226 (zmierzone, `16e-kwanty-kld.md:134`) | czat T=1 ~93 (`27-3090-final.md:232`); decode po 60k T=1 **56.7** (host 280 W, `27-3090-final.md:200`) | **faza 1 (rdzeń)** |
| RTX 5090 32 GB (referencja) | Qwen3.8-27B | **UD-Q6_K** (21.98 GB) | **204800**, ub 512 | 27806 / 31321 / 32607 → zapas 1286 `[SZACUNEK: ovh 5090 niezmierzony]` | ~0.009 / ~0.011 `[SZACUNEK]` | czat ~140, po 64k ~110 `[SZACUNEK z pasma]` | faza 2 (opcja, zalecana) |
| RTX 4090 24 GB (referencja) | Qwen3.8-27B | UD-Q4_K_XL | 131072 | 21522 / 23772 / 24564 → 792 `[SZACUNEK ovh]` | jak 3090 | ~1.1× 3090 `[SZACUNEK]` | opcja, niezalecana (ta sama pamięć co 3090) |
| RTX 5060 Ti 16 GB | **ta karta: brak modelu 27B spełniającego próg** | — | — | najlepszy 27B z J1 (AP-Q3_K_XL) mieści 51k (g=18K) / 66k (ub 256, g=14K) | — | — | brak wynajmu w fazie 1–2 |
|  | kandydat warunkowy | Qwen3.5-9B Q8_0 (9.53 GB) | 262144 | 12006 / 14256 / 16311 | ≈ podłoga Q8 `[SZACUNEK]`, J2/J3 do zmierzenia | ~40 po 64k `[SZACUNEK]` | faza 3, tylko po zgodzie na 9B |
| RTX 4060 Ti 16 GB | **ta karta: brak modelu 27B spełniającego próg** | — | — | jak 5060 Ti | — | — | jw. |
|  | kandydat warunkowy | Qwen3.5-9B Q8_0 | 262144 | 11998 / 14248 / 16380 | jw. | ~27 po 64k `[SZACUNEK]` | faza 3 |
| RTX 4070 Ti 12 GB | **ta karta: brak modelu spełniającego próg** (27B ≥ Q3_K_XL nie mieści się nawet bez kontekstu; brak ofert na Vast 2026-10-20 18:00) | — | — | — | — | — | brak wynajmu |
| RTX 3060 12 GB | **ta karta: brak modelu spełniającego próg** — decyzja [[2026-10-16-saluki-bonsai-na-3060]] dopuszcza tylko Saluki/Bonsai, a oba oblewają J1 (KLD-wiki 0.257 / 0.352, PL 0.320 / 0.508, `16e-kwanty-kld.md:143-144`) | — | — | Saluki plain 125k, Bonsai PQ2_0 144k (mieszczą się, ale J1 ✗) | — | — | brak wynajmu |
| RTX 3080 10 GB | **ta karta: brak modelu spełniającego próg** (brak też oferty spełniającej filtr hosta) | — | — | — | — | — | brak wynajmu |

**Doładowanie Vast: $8** (zalecane = faza 1 + faza 2 + faza 3 z marginesem 30% i rezerwą na złe hosty: $7.49 − kredyt
$0.23 = $7.26). Minimum (tylko 3090): $1.81 − $0.23 = **$1.58**. Szczegóły w §6.

Najważniejszy wniosek liczbowy: przy KV q4_0 nasz T kosztuje **~29.8 KB VRAM na token kontekstu po załadowaniu**
(KV celu 18 432 B + KV draftu 1 152 B + bufory obliczeń 2 × 5 120 B przy ub 512) **i do ~18 KB/token więcej szczytowo
po długim prompcie**. 131k tokenów to więc ~3.6 GiB + do ~2.2 GiB ponad wagi i ~1.6 GiB stałych. Na 16 GB zostaje na
wagi ~9 GB, czyli tylko klasa IQ2/Q2 — a ta oblewa J1. Stąd „brak modelu” na 10/12/16 GB, nie z ostrożności.

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

## 2. Kandydaci i jakość

KLD do BF16, protokół 16e (wiki / czat PL; `16e-kwanty-kld.md:133-144`). Wartości bez pomiaru: `[SZACUNEK]` =
log-liniowa interpolacja po rozmiarze pliku w rodzinie unsloth UD między U3 (13.15 GB), U4 (17.56 GB) i Q8_0 (29.05 GB).

| kandydat | GB | KLD wiki / czat | J1 (≤ 0.05 / ≤ 0.07) | uwagi |
|---|---|---|---|---|
| UD-Q6_K_M | 23.09 | ~0.008 / ~0.009 `[SZACUNEK]` | ✓ | |
| UD-Q6_K | 21.98 | ~0.009 / ~0.011 `[SZACUNEK]` | ✓ | |
| UD-Q5_K_XL / Q5_K_M / Q5_K_S | 20.88 / 19.77 / 18.67 | ~0.010–0.013 / ~0.013–0.019 `[SZACUNEK]` | ✓ | |
| **UD-Q4_K_XL (U4)** | 17.56 | **0.0153 / 0.0226** | ✓ | zmierzone |
| UD-Q4_K_M / Q4_K_S | 16.46 / 15.36 | ~0.019 / ~0.029; ~0.024 / ~0.038 `[SZACUNEK]` | ✓ | |
| UD-IQ4_XS / AP-IQ4_XS | 14.25 | ~0.031 / ~0.049 `[SZACUNEK]` | ✓ | KLD nigdy nie mierzony (`31-5060ti.md:43`) |
| **UD-Q3_K_XL (U3) / AP-Q3_K_XL (A3)** | 13.15 | 0.0390 / 0.0635; **0.0400 / 0.0559** | ✓ (próg) | zmierzone; A3 lepszy na czacie/kodzie |
| UD-IQ3_S | 12.04 | ~0.054 / ~0.09 `[SZACUNEK: 1.39 × U3 z 15e]` | ✗ | |
| GSQ IQ3_S (I4) / Swift IQ3_S (W4) | 11.77 | 0.073 / 0.088; 0.076 / 0.094 | ✗ | |
| Swift IQ3_XXS (W3) | 10.09 | 0.119 / 0.161 | ✗ | licencja < US$1M |
| IQ2_S (W2/I2), UD-Q2_K_XL, UD-IQ2_XXS | 7.3–9.8 | 0.164 / 0.19–0.21 (W2/I2) | ✗ | |
| Saluki S0 | 7.90 | 0.257 / 0.315 (PL 0.320) | ✗ | decyzja 3060 |
| Bonsai B0 | 7.62 | 0.352 / 0.437 (PL 0.508) | ✗ | decyzja 3060 |
| LFM2.5 QAD-Q4_0 / Q4_K_M / Q5_K_M | 13.58 / 14.53 / 17.03 | 0.203 / 0.201 / 0.124 (do własnego Q8_0, wikitext 512; Qwen U3 w tym protokole 0.0265) | ✗ | `09-chmura-5060ti.md:174-179` |
| LFM2.5 Q6_K | 19.69 | niezmierzony | ? | max 128k; na 24 GB i tak przegrywa z 27B Q4_K_XL `[INFERENCE]` |
| Qwen3.5-9B Q8_0 / UD-Q5_K_XL | 9.53 / 6.74 | do własnego BF16: ~podłoga Q8 (0.004) / niezmierzony `[SZACUNEK]` | ✓ formalnie | inny, mniejszy model: J2/J3 rozstrzygają, czy „do pracy”; użytkownik wykluczył 9B na 3060 |

Próg J1 (uzasadnienie): U3/A3 to najniższy **zmierzony** tier, przy którym PL same-top ≥ 91.9% i PPL(Q)/PPL(BF16) ≤ 1.02
(`16e-kwanty-kld.md:135-136`), i to on jest wyborem decyzji E1 dla 16 GB. Następny zmierzony tier (I4/W4, IQ3_S) ma 1.9×
wyższy KLD-wiki i same-top 89.6–89.9%. Próg 0.05 / 0.07 leży między nimi — **żaden kwant klasy IQ3_S i niżej, w tym
wszystkie IQ2/Q2, go nie przechodzi**.

Próg J4 (20 t/s po 64k): Qwen myśli; przy `--reasoning-effort low` odpowiedź to ~1–2k tokenów, czyli ≤ 100 s przy 20 t/s
— górna granica pracy interaktywnej. 20 t/s to też U0 (goły upstream) na najwolniejszej karcie z kampanii
(3060: 20.6 t/s, `31-3060-3080.md:10`).

## 3. Karty: każdy wykonalny model, max `-c`, jakość, prędkość, decyzja

Max `-c` z `fitcalc` (T, KV q4_0, zapas 512 MiB): **pewny** = ub 512, g = 18K; **górny** = ub 256, g = 14K
(do sprawdzenia testem wypełnienia). Kandydaci bez MTP liczeni jako ramię plain (połowa g).

### RTX 3090 24 GB (24576 MiB, 936 GB/s, sm_86) — rekomendacja: **UD-Q4_K_XL, `-c 131072`**

| model | max `-c` pewny / górny | J1 | ≥131k | t/s (źródło) | decyzja |
|---|---|---|---|---|---|
| UD-Q6_K_M / Q6_K / Q5_K_XL / Q5_K_M | 27k / 50k / 72k / 91k (górny 36–116k) | ✓ | ✗ | Q6_K_M czat T=1 73.2 (`31-3090.md:66`) | odpada (kontekst) |
| UD-Q5_K_S | 114k / 143k | ✓ | tylko górny | — | odpada (nie „pewny”) |
| **UD-Q4_K_XL** | **137k / 171k** | ✓ zmierzone | ✓ | czat T=1 93.3 (`27:232`), mvs 349 (`27:234`), po 32k / 60k T=1 64.8 / 56.7 (host 280 W, `27:202,200`); po 128k ~43 `[SZACUNEK: liniowo w ms/token]`; prefill 60k 924 t/s, TTFT 32k 28.8 s / 60k 60.4 s (`27:204-206`); TTFT 128k ~165 s `[SZACUNEK]` | **WYBRANY** |
| UD-Q4_K_M | 159k / 199k | ✓ (szac.) | ✓ | ~+6% vs Q4_K_XL `[SZACUNEK z bajtów]` | nie: +20k ctx za ~+25% KLD |
| UD-IQ4_XS | 203k / 253k | ✓ (szac. 2×U4) | ✓ (200k) | — | nie: 200k kosztuje jakość (zasada „200k tylko bez kosztu jakości”) |

`-c 131072` daje przewidywany szczyt 23630 MiB (zapas 946 MiB) — zgodne z pomiarem 22198 MiB po 55.6k (`27:207`).
Rozszerzenie: test wypełnienia także `-c 163840 -ub 256` (model: szczyt 24241, zapas 335 < 512 → odrzucony z góry;
nie testować). `-c` 131072 jest finalny.

### RTX 4090 24 GB (referencja, opcjonalnie) — jak 3090: UD-Q4_K_XL, `-c 131072` (szczyt 23772, zapas 792 `[SZACUNEK ovh]`). Niezalecana: ta sama pojemność, odpowiada tylko „o ile szybciej”.

### RTX 5090 32 GB (32607 MiB, 1792 GB/s, sm_120) — rekomendacja: **UD-Q6_K, `-c 204800`**

| model | max `-c` pewny / górny | J1 | ≥131k / 200k | decyzja |
|---|---|---|---|---|
| UD-Q6_K_M | 194k / 242k | ✓ (~0.008) | ✓ / tylko górny | nie: 200k niepewne |
| **UD-Q6_K** | **216k / 256k** | ✓ (~0.009) | ✓ / ✓ | **WYBRANY**: 200k bez straty jakości (Δ KLD vs Q6_K_M ~0.001 `[SZACUNEK]`) |
| UD-Q5_K_XL | 239k / 256k | ✓ | ✓ / ✓ | nie: niższa jakość za kontekst ponad 200k, którego nie potrzebujemy |

Prędkość `[SZACUNEK]`: czat T=1 ~140 t/s (3090 Q6_K_M 73.2 × 1.9 pasma), po 64k ~110. Nic nie zmierzone na 5090 — stąd
faza 2 jako referencja górnej półki.

### RTX 5060 Ti 16 GB (16311 MiB) i RTX 4060 Ti 16 GB (16380 MiB) — **brak modelu 27B spełniającego próg**

| model | max `-c` 5060 Ti / 4060 Ti (pewny\|górny) | J1 | powód odpadnięcia |
|---|---|---|---|
| UD-IQ4_XS (dotychczasowy wybór) | 29\|38k / 30\|40k | ✓ | kontekst (zmierzone: 32k, `31-4060ti.md:62`) |
| AP-Q3_K_XL (najniższy z J1) | 51\|66k / 53\|68k | ✓ | kontekst; nawet bez MTP przy ub 256: zapas 60 MiB przy 131k (< 512) |
| UD-IQ3_S / Swift IQ3_S | 74\|94k | ✗ | jakość i kontekst |
| Swift IQ3_XXS / UD-Q2_K_XL / Saluki-MTP | 106–147\|133–184k | ✗ | jakość (KLD 0.12–0.26) |
| Saluki / Bonsai (plain) | 251–256k | ✗ | jakość |
| LFM QAD-Q4_0 (KV q8_0) | 122\|142k (max 128k z modelu) | ✗ (KLD 0.203) | jakość |
| **Qwen3.5-9B Q8_0** | **256k / 256k** | ✓ formalnie | **warunkowy**: J2/J3/J4 niezmierzone; t/s ~40 (5060 Ti) / ~27 (4060 Ti) po 64k `[SZACUNEK: 0.85–0.9 × pasma / (8.4 GB wag + ~1.2 GB odczytu KV)]` |

Żeby 27B ≥ Q3_K_XL weszło na 16 GB przy 131k, potrzebna jest zmiana silnika: prefill FA bez pełnej konwersji K/V
do f16 (dziś g ≈ 14–18 KB/token, `31-4060ti.md:64`), mniejszy bufor kontekstu draftu, ub 256. Rachunek `[SZACUNEK fitcalc]`:
nawet z g → 2 KB/token i ub 256 AP-Q3_K_XL **z MTP** mieści ~98k (✗), **bez MTP** ~157k (✓, ale bez spekulacji:
plain Q3_K_XL na 5060 Ti 28.9 t/s przy krótkim kontekście, `09-chmura-5060ti.md:174`; 4060 Ti 18.8 t/s, `29-4060ti.md:68`
→ 4060 Ti oblewa J4). To projekt deweloperski na CPU (DeepSeek), nie zakup godzin GPU — poza budżetem tego planu.

### RTX 4070 Ti 12 GB, RTX 3060 12 GB, RTX 3080 10 GB — **brak modelu spełniającego próg**

- 27B ≥ Q3_K_XL: same wagi (12006 MiB) ≥ VRAM po odjęciu stałych. Nie mieści się przy żadnym `-c`.
- 3060: **tu obowiązuje decyzja 2026-10-16** (tylko Saluki/Bonsai). Mieszczą się przy 131k bez MTP (Saluki 125|147k,
  Bonsai PQ2_0 144|169k), Saluki z MTP tylko 61|78k — ale oba oblewają J1 (KLD-wiki 0.257 / 0.352). Wynik: brak modelu.
  Gdyby użytkownik dopuścił 9B: Qwen3.5-9B Q8_0 `-c 131072` (szczyt 11320, zapas 968) — faza 3, tylko na jego polecenie.
- 4070 Ti: 9B Q8_0 `-c 131072` mieściłby się (szczyt 11410), ale 2026-10-20 18:00 na Vast nie ma żadnej oferty 4070 Ti.
- 3080: 9B UD-Q5_K_XL `-c 131072` mieściłby się (szczyt 9271); żadna oferta 3080 nie przechodzi filtra hosta
  (najtańsza: transfer $0.0026/GB i 15 GB RAM).

## 4. Protokół testu (każda wynajęta karta; szczegóły i listy kontrolne w SOP §7–§9)

1. **hostcheck box** w pierwszych 5 min (limit mocy = domyślny, HF ≥ 25 MB/s, dysk, RAM); FAIL → zniszcz.
2. **Staging raz:** jeden plik modelu z HF na boxie (sha256 z HF LFS), źródła jako `git diff`, buildy upstream `4c3c5810f`
   i gałęzi `nv-v2` (sm_86/89/120), nigdy w trakcie pomiaru.
3. **Test wypełnienia (J3 VRAM):** ramię T przy wybranym `-c`: 512 → 16k T=0 → 16k T=1 → 64k → (c−1.2k) T=0 →
   drugi (c−1.2k) innym tekstem T=1 → czat; nvidia-smi co 0.2 s; PASS = 0 błędów i szczyt + 512 ≤ VRAM. Tak samo U1.
4. **Bramki jakości na karcie:** J3 `needle.py --tokens <c>` (5/5, 0 zmyśleń; dla 5090 także 200k); J2: 3 czaty PL + 3 EN
   (T=1, czytane przez inżyniera: spójne, poprawny język, bez pętli) + 3 edycje kodu z testem (diff stosuje się, test przechodzi).
5. **Ramiona przy wybranym `-c`:** U0 = upstream `-m` (domyślny fit; jego n_ctx zapisany, obciążenia ponad jego kontekst „—”);
   U1 = upstream + `-fit off -ngl 99 -fa on -ctk q4_0 -ctv q4_0 -c <c> -ub <ub> -np 1 --jinja --cache-ram 8192
   --reasoning-effort low --spec-type draft-mtp --spec-draft-n-max 4 -ctkd q4_0 -ctvd q4_0`; T = `cuda-topka2` z flagami U1
   + słownik draftu 64k, głowice iq4_xs, `LLAMA_SPEC_LOOKUP=3 LLAMA_SPEC_LOOKUP_W=16 LLAMA_SERVER_CACHE_SHARE_MIN=1024
   LLAMA_GPU_VERIFY=1` (jak w 31-*, żeby wyniki były porównywalne). 9B: U0 i T bez MTP (lookup).
6. **Obciążenia:** czat T=1 (spec_sweep 6 promptów × 3 seedy × 400 tok); edycja kodu mvs T=0 (4 × 1024) + zestaw edit;
   decode po 16k / 64k / 128k (+200k na 5090) przy T=0 i T=1 (256 tok); prefill 32k i 128k z TTFT; VRAM.
7. **ABBA:** U0 U1 T | T U1 U0, świeży serwer na ramię, p1 seedy 1–3, p2 seedy 4–6; CI95 bootstrap po (prompt, seed).
8. **Bramki md5:** 22 wiersze (6 czat T=0, 6 czat T=1 seed 1, 4 mvs, 6 copy): `LLAMA_GPU_VERIFY=0` == `=1`; build z
   przełącznikami off == `cuda-topka2`; przełącznik bitowy → md5 = baza; niebitowy (GDN MMA, KVQ) → KLD vs referencja
   CPU fp32 PASS (metoda `31-4060ti.md:88-89`); zmiana głębokości draftu → nowe md5 referencyjne + deterministyczność.
9. **Pętla optymalizacji (≤ 10 min GPU na pomysł, kolejność wg oczekiwanego zysku):**

| # | pomysł | dowód z 31-* | 3090 Q4_K_XL | 5090 Q6_K | 9B (faza 3) |
|---|---|---|---|---|---|
| O1 | `GGML_CUDA_KVQ=1` (FA czyta q4_0 w weryfikacji) | 4060 Ti: po 16k +10%, po 29.5k **+28%**, usuwa OOM T (`31-4060ti.md:33-34,89`) | **pierwszy** (128k!) | tak | tak |
| O2 | `LLAMA_SPEC_COUPLED=1` | +5.3…+6.8% czat T=1 na sm_86/89 (`31-3060-3080.md:146`, `31-4070ti.md:180`, `31-4060ti.md:87`); 5060 Ti nierozstrzygnięte | tak | tak | nie (brak MTP) |
| O3 | `GGML_CUDA_GDN_MMA=1` (chunked GDN w prefillu) | pp +3.8% (`31-4060ti.md:88`) → TTFT 128k | tak | tak | tak |
| O4 | głębokość draftu n=3 / n=5 (statyczna na kartę, reguła przyjęta 2026-10-20) | 3060 n=3, 3080 n=2 (+3…+5%, `31-3060-3080.md:147`), 4060 Ti n=5 −0.75% (`31-4060ti.md:91`) | n=3 i n=5 | n=5 (szybka weryfikacja) | — |
| O5 | `LLAMA_SERVER_YIELD_FAST=2` | +1.0% na słabym CPU (`31-4070ti.md:178`) | tylko gdy host < 8 rdzeni | nie | tak |
| O6 | `-ub 256` vs 512 | −5% prefill, −640 MiB przy 131k | tylko jeśli J3 wymaga | — | — |
| O7 | słownik draftu 32k | sufit ~2% (`31-4060ti.md:93`) | tak | tak | — |
| O8 | MMVQ i-quantów (`GGML_CUDA_MMVQ_IQ_TUNE=2`, RPB, Q3K_MULTI) | +1.4% tylko dla IQ3/IQ2 (`31-5060ti.md:15`); RPB/Q3K/OCC odrzucone | **pomijamy**: Q4_K_XL ma 0.15 GB typów IQ3/Q3_K | pomijamy (Q6_K/Q8_0) | pomijamy (Q8_0) |
| O9 | Q6_K MMVQ przy K=5120 (555 GB/s z 936, `31-3090.md:21-22`): PIPE (błędne wyjście) i Q8_WIDE | KILL / niezmierzone | najpierw debug PIPE na CPU (DeepSeek) — na GPU tylko po teście bitowym | jw. (Q6_K dominuje w pliku) | — |

   Przyjęcie: CI95 zmiany t/s wyklucza 0 albo ms/krok spada na każdym prompcie, + bramki md5/KLD. Finał T' vs T ABBA
   na tym samym binarnym, potem pełne U0/U1/T/T' (najpierw T i T', na początku okna — lekcja z 2026-10-20).

## 5. Logistyka

### 5.1 Filtr hostów (live, `vastai search offers`, 2026-10-20 17:33 UTC)

```
vastai search offers 'gpu_name=<GPU> num_gpus=1 gpu_ram>=<V> reliability>0.98 verified=true rentable=true
  direct_port_count>=1 disk_space>=60 inet_down>=300 cuda_vers>=12.8 inet_down_cost<=0.002 inet_up_cost<=0.002
  cpu_cores_effective>=4 cpu_ram>=24 geolocation notin [CN]' --storage 60 -o dph_total --raw
```

Potem przed wynajmem `hostcheck.sh offer <id> <GB pobrania> <h>` (cena z transferem, verified, rel, driver ≥ 570, RAM),
`up.sh <id> --download-gb <GB> --hours <h> --go` (od 76e6ac2 sam odrzuca transfer > $0.002/GB), a po starcie
`hostcheck.sh box <url modelu> <GB>`: `nvidia-smi -q -d POWER` Current == Default (inaczej zniszcz), HF ≥ 25 MB/s
(1 GiB range), dysk ≥ model + 30 GB, RAM ≥ 24 GB, szerokość PCIe.

| karta | oferta (wybrana) | $/h z dyskiem 60 GB | GPU / dysk $/h | transfer $/GB | rel | uwagi |
|---|---|---|---|---|---|---|
| 3090 | **56607987** Oregon, PCIe 4 x16 | 0.2433 | 0.2267 / 0.0167 | 0.0013 | 0.998 | zapas: 54042498 Tajwan $0.2233, transfer 0, rel 0.987 (tajwański 3090 miał limit 200 W, `31-3090.md:28`) |
| 5090 | **52411630** Czechy, 6.5 Gb/s | 0.904 | 0.8873 / 0.0167 | 0 | 0.984 | zapas 51969545 Kalifornia $0.984 |
| 4090 | 53960908 Oregon | 0.470 | 0.4533 / 0.0167 | 0.0013 | 0.997 | opcja |
| 5060 Ti | 54073761 Australia | 0.1844 | 0.1733 / 0.0111 | ~0 | 0.998 | jedyna przechodząca filtr |
| 4060 Ti | 56468703 Floryda (host z `31-4060ti.md`, 165 W stock) | 0.1844 | 0.1733 / 0.0111 | ~0 | 0.991 | jedyna przechodząca filtr |
| 3060 | 55447325 Michigan | 0.1211 | 0.0933 / 0.0278 | 0.0013 | 0.998 | tylko gdy użytkownik zmieni decyzję |
| 3080 | — | — | — | — | — | brak oferty z transferem ≤ $0.002 i RAM ≥ 24 GB |
| 4070 Ti | — | — | — | — | — | brak jakiejkolwiek oferty |

### 5.2 Staging: jeden plik na kartę, pobrany raz na boxie

3090/4090: `unsloth/Qwen3.8-27B-GGUF` `Qwen3.8-27B-UD-Q4_K_XL.gguf` (17 559 178 144 B, sha256 3f227079…, `models.tsv`).
5090: `Qwen3.8-27B-UD-Q6_K.gguf` (21 983 677 344 B). 5060 Ti / 4060 Ti: `unsloth/Qwen3.5-9B-GGUF` `Qwen3.5-9B-Q8_0.gguf`
(9 527 502 048 B). Pobranie = model + obraz ~5 GB + źródła/apt ~1 GB. Nigdy nie wysyłać modeli ze stacji (upload 0.45 MB/s).

### 5.3 Faza 0 — lokalnie, $0, przed doładowaniem (CPU, `nice -n 19`)

| # | zadanie | po co |
|---|---|---|
| F0.1 | Gałąź `nv-v2` = `cuda-topka2` + coupled `7cdc0121b` + host-gap `49bc932a8` + GDN MMA `e55006b3a` + KVQ `007a6f813` (z `nv-4060ti` `6edd8d8b9`); wszystkie przełączniki domyślnie off; kompilacja lokalna sm_86/89/120 (CUDA 12.8 w `~/opt/cuda-12.8`) | żadnego debugowania buildu na płatnym boxie |
| F0.2 | `corpus256k.txt` (PL+EN: wiki + raporty + kod, ≥ 900 KB) i rozmiary 64k/128k/200k w `long_bench.py`; `fillseq.sh` uogólniony z `runs/nv5060ti/inst/fitseq.sh` (sekwencja z §4.3, model i `-c` z parametrów) | obciążenia 128k/200k nie istnieją w harnessie (corpus60k ma 199 KB) |
| F0.3 | Zestaw J2: 3 PL + 3 EN prompty czatu, 3 edycje kodu z testem (np. funkcje z `qwen-opt/tools`) | bramka zadań powtarzalna |
| F0.4 | Próba `needle.py` na CPU z małym modelem (np. LFM2.5-2.6B przy 8k) | skrypt sprawdzony przed GPU |
| F0.5 | Faza 3 tylko jeśli: 9B Q8_0 KLD do BF16 (CPU, 20 × 2048) i J2 na CPU zaliczone **oraz użytkownik zgodzi się na 9B** | nie płacić za kartę bez modelu |
| F0.6 | DeepSeek: debug `GGML_CUDA_MMVQ_PIPE` na CPU (hash MUL_MAT, `31-3090.md:136-137`) | O9 tylko jeśli bitowo poprawne |

### 5.4 Godziny na kartę

| karta | build + pobranie | wypełnienie + J2/J3 | ABBA U0/U1/T | optymalizacja + finał T' | raport/zniszczenie | razem z zapasem 25% |
|---|---|---|---|---|---|---|
| 3090 | 0.45 h | 0.8 h (prefill 128k ~3 min × ~10) | 0.75 h | 1.6 h | 0.2 h | **5.0 h** |
| 5090 | 0.4 h | 0.6 h | 0.5 h | 1.2 h | 0.2 h | **3.5 h** |
| 4090 (opcja) | 0.4 h | 0.6 h | 0.5 h | 1.2 h | 0.2 h | 3.5 h |
| 5060 Ti (faza 3) | 0.45 h | 0.6 h | 0.4 h | 0.4 h | 0.15 h | **2.5 h** |
| 4060 Ti (faza 3, tylko gdy 5060 Ti zaliczy) | 0.45 h | 0.5 h | 0.3 h | 0.3 h | 0.1 h | **2.0 h** |

## 6. Koszt i doładowanie (ceny live 2026-10-20 17:33 UTC; transfer = GB × $/GB; +30%)

| karta | h | GPU | dysk | transfer | suma | +30% | rezerwa na zły host (+30%) | **razem** |
|---|---|---|---|---|---|---|---|---|
| 3090 (56607987) | 5.0 | $1.133 | $0.083 | 25 GB × $0.0013 = $0.033 | $1.249 | $1.62 | 2 × 0.3 h = $0.19 | **$1.81** |
| 5090 (52411630) | 3.5 | $3.106 | $0.058 | 28 GB × $0 = $0 | $3.164 | $4.11 | 1 × 0.3 h = $0.35 | **$4.46** |
| 5060 Ti (54073761) | 2.5 | $0.433 | $0.028 | 16 GB × ~$0 = $0.00 | $0.461 | $0.60 | $0.07 | **$0.67** |
| 4060 Ti (56468703) | 2.0 | $0.347 | $0.022 | 16 GB × $0.00004 = $0.00 | $0.369 | $0.48 | $0.07 | **$0.55** |
| 4090 (opcja, 53960908) | 3.5 | $1.587 | $0.058 | 25 GB × $0.0013 = $0.033 | $1.678 | $2.18 | $0.18 | $2.36 |
| 3060 (tylko po zmianie decyzji) | 2.0 | $0.187 | $0.056 | 16 GB × $0.0013 = $0.021 | $0.264 | $0.34 | $0.05 | $0.39 |

- Faza 1 (3090): **$1.81**. Faza 1 + 2 (5090): **$6.27**. Faza 1 + 2 + 3 (5060 Ti, 4060 Ti): **$7.49**. Z 4090: $9.85.
- Kredyt teraz: **$0.23** (`vastai show user`, 2026-10-20). **Doładowanie: $8** (pokrywa fazy 1–3 = $7.26 netto).
  Wariant oszczędny: $2 (tylko 3090).
- Robotnicy DeepSeek i inżynierowie Opus nie są w budżecie Vast.

### 6.1 Kolejność

1. Faza 0 lokalnie (F0.1–F0.4) — bez kredytu.
2. **Fazy 1 i 2 równolegle** (3090 i 5090, osobni inżynierowie, osobne `--hours`): rdzeń i referencja nie zależą od siebie;
   tanie karty nie idą pierwsze, bo nie mają modelu spełniającego próg.
3. Faza 3 po raporcie z faz 1–2 i tylko po decyzji użytkownika o 9B: najpierw 5060 Ti, 4060 Ti tylko jeśli 5060 Ti zaliczy J2–J4.
4. Strażnik kredytu: inżynier sprawdza `vastai show user` co 30 min; przy kredycie < 1.3 × (koszt pozostałych godzin
   wszystkich boxów) przechodzi od razu do finału T/T' (bez nowych pomysłów).

## 7. Organizacja pracy

- Jeden inżynier Opus na kartę, brief = `qwen-opt/cloud/ENGINEER-PROMPT.md` + karta parametrów z §0/§5 tej strony.
- Kod piszą robotnicy DeepSeek v4.1 Flash przez `~/qwen-opt/tools/ds-agent <name> <worktree> <brief> [45m]`, brief wg
  `qwen-opt/cloud/DEEPSEEK-WORKER-PROMPT.md`; ≤ 3 naraz na inżyniera, ≤ 45 min, edycja tylko w swoim worktree, bez GPU.
- Reguły jak w kampanii 31 plus: `-c ≥ 131072` zawsze (decyzja 2026-10-20), KV q4_0 (cel i draft; LFM q8_0), jeden model
  na kartę wybrany tutaj, bramki J1–J4, rozliczenie z `vastai show invoices-v1 --charges` po zniszczeniu.

## 8. Ryzyka

| ryzyko | skutek | zabezpieczenie |
|---|---|---|
| g (wzrost szczytu) zmierzone tylko do promptu 55.6k; przy 131k może być większe niż 18 KB/token | 3090 nie utrzyma 131k z zapasem 512 MiB | test wypełnienia jako pierwszy krok; kolejno: `-ub 256` (−640 MiB), O1 KVQ, a jeśli dalej brak → raport „131k nie mieści się” zamiast cichego zejścia do 32k; Q4_K_M (−1044 MiB) jako jedyny dopuszczalny zamiennik |
| 5090: ovh i prędkość niezmierzone, sm_120 + driver ≥ 570 | błąd szacunku ~±300 MiB | Q6_K ma zapas 1286 MiB; build sm_120 sprawdzony lokalnie (F0.1) |
| hosty 3090 z limitem mocy (200/220 W, `31-3090.md:28-29`), wolny HF (26 KB/s) | stracony czas, fałszywe t/s | `hostcheck.sh box` w 5 min, rezerwa 2 × 0.3 h w budżecie |
| oferty znikają / zmieniają cenę (3060 i 3080 w kampanii 31) | inna cena | `hostcheck.sh offer` tuż przed `up.sh`; zapasowe oferty w §5.1 |
| przełączniki niebitowe (KVQ, GDN MMA) zmieniają tekst | spór o bezstratność | bramka KLD vs CPU fp32 (jak `31-4060ti.md:88-89`) |
| 9B nie jest „do pracy” mimo KLD ≈ 0 | płacimy za kartę bez modelu | faza 3 dopiero po J2 na CPU i zgodzie użytkownika; brak wynajmu na 3060 bez zmiany decyzji |
| kredyt kończy się w połowie | brak finału (2026-10-20) | budżet z rezerwą, strażnik kredytu co 30 min, finał T/T' na początku okna, twarde `--hours` + samozniszczenie |
| prefill 128k/200k jest długi (3090: ~3 min na 128k) | godziny rosną | prompt cache (`--cache-ram`, cache share), jeden haystack na serię needle, harmonogram w §5.4 |
| korpus 128k/200k nie istnieje | brak obciążeń | F0.2 przed wynajmem |
| LFM2.5: max kontekst 131072, KLD Q4/Q5 ✗ | — | wykluczony z tej kampanii; Q6_K tylko do pomiaru KLD w przyszłości |

## 9. Źródła

`product/research/27-3090-final.md:160,187-188,198-207,211,232-234`; `31-3090.md:21-29,44,66`; `31-4070ti.md:44-47,178,180`;
`31-3060-3080.md:10,35,42,62,78,146`; `31-5060ti.md:15,40,43,66`; `31-4060ti.md:15,33-34,59-64,87-89,95`; `29-4060ti.md:70`;
`16e-kwanty-kld.md:133-144`; `09-chmura-5060ti.md:174-179`; `qwen-opt/bench-final/queue-logs/fb-qwen-T-p1.log:1`;
logi buforów w §1.2; nagłówki GGUF: HF `unsloth/Qwen3.8-27B-GGUF`, `agentionai/Qwen3.8-27B-AP-GGUF`,
`ukisai/Swift-1.5-Qwen3.8-27B-GSQ-RCO-GGUF`, `Kujira/Underdog-Saluki-27B-1.0-MTP-GGUF`, `ConwayResearch/Underdog-Saluki-27B-1.0`,
`prism-ml/Ternary-Bonsai-2-27B-gguf`, `LiquidAI/LFM2.5-24B-A2B-GGUF`, `unsloth/Qwen3.5-9B-GGUF` (range requests 2026-10-20);
oferty: `vastai search offers` 2026-10-20 17:33 UTC; kredyt: `vastai show user` 2026-10-20.
