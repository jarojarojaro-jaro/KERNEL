# 32c — SAGE-EXL3 1.62 bpw (DeepSeek-V4.1-Flash-1017 na 1× Spark) i cuteafd AFD (1 GPU + 4× Spark)

Data: 2026-10-20. Tylko CPU: klony płytkie w `/tmp/res-sage/`, `/tmp/res-afd/`; nagłówki safetensors pobrane zakresami bajtów (bez wag).
Źródła i wersje:
- karta HF `vcruz305/DSV4.1-Flash-1017-SAGE-EXL3-1.62bpw`, sha `c852150e` (2026-10-20). Recepta przypina `2a605935`; historia repo była już kilka razy nadpisywana;
- recepta `vcruz305/DSV4.1-Flash-1017-EXL3-Spark-recipe` `b4c890a1` (2026-10-20);
- exllamav3 v1.6.3 `a3bfbfd` (2026-10-17);
- `turboderp/Qwen3.8-27B-exl3` `d23340a1`;
- cuteafd v3.0.0/v3.0.1 `9098781` (2026-10-18);
- strona Turquoise Bay „hub-vs-switch” (pomiar 18–19.10);
- baza porównawcza `justincasey/DeepSeek-V4.1-Flash-1017-4x-DGX-Spark` `fa77c26` (2026-10-18).

Delta wobec KB: EXL3 był w R03/R15e/R18/R23c, ale **ścieżki SC (self-calibrated, per-tensor alokacja bitów: `sc_measure.py`/`sc_optimize.py`, `doc/optimize.md`), wykresu KLD Qwen3.8-27B EXL3 vs GGUF ani gotowych kół ROCm** baza nie miała. SAGE, cuteafd i hub-and-spoke są nowe.

## TL;DR

1. **SAGE nie jest opublikowaną metodą.** Karta mówi wprost „The method is not published”. To nie nowy format. To EXL3 (trellis QTIP, upstream) z **alokacją K per tensor per ekspert**.
   - Policzyłem z nagłówków 46 080 tensorów trellis ekspertów: K1 55%, K2 34%, K3 11%, K4 2%; średnio ~1.6 bita.
   - Ekspertów „zimnych” (najrzadziej routowanych, lista z recepty) jest 1 418. Mają średnie K 1.25, a reszta 1.64. Alokacja jest więc ważona częstością routingu.
   - Upstream exllamav3 ma już jawny odpowiednik dla modeli gęstych (`sc_optimize.py`: `kld(t,K)=S_t·rfn_t(K)^α`, greedy). SAGE wygląda na jego wariant MoE `[INFERENCE]`.
2. **Wierność 1.62 bpw jest zawyżona doborem metryk:**
   - dane „held-out” nieopisane;
   - zero metryk zadaniowych;
   - punktem odniesienia jest **już 4-bitowa** oficjalna wersja FP4, nie BF16;
   - mediana KL 0.00019 jest bezużyteczna (rozkład dwumodalny, mediana leży w masie pewnych tokenów; nawet szum bf16 Qwena ma średnią 0.00045);
   - średnia 0.098 i top-5 overlap 81% to realne uszkodzenie, zwłaszcza że DeepSeek zaleca T=1.0.
   - Siostrzana paczka tego samego autora (DERISKED 1.61 bpw) podaje mean KLD **0.193** i KLD kodu **0.103**, a SAGE kodu 0.0186. Protokół nie jest stabilny między kartami.
3. **Pamięć i prędkość: liczby prawdziwe, ale „mieści się w 128 GB” tylko częściowo.**
   - Całość paczki to 304 GiB, w tym 188.8 GiB tablic Engram (FP8) czytanych z NVMe.
   - Rezydentnie zajmuje ~107–110.5 GiB. Nawet to nie mieści się pod vLLM: 1 418 ekspertów (8.59 GiB) czytanych jest z NVMe przez ATS/page cache.
   - Decode 35.5 t/s to greedy, `ignore_eos`, plain completions, DSpark k=5, 4.7 tok/krok. Bez draftu było 13.4.
   - Prefill 1 189 t/s zmierzono na tekście „logowym” (mało ekspertów). Prawdziwy tekst daje **~720 t/s** (wg samego README).
   - Rachunek roofline (§2.3) potwierdza wiarygodność: ~50% sufitu pasma.
4. **cuteafd „+36% prefill / +21% decode vs same Sparki”: porównanie silnika z silnikiem, a nie wartość dodanej GPU.**
   - Baza to SGLang TP4 (bez opublikowanych danych).
   - Strojony stos vLLM na tych samych 4 Sparkach, w ringu bez switcha i bez dodatkowych NIC (justincasey r6w), robi prefill 6 505 t/s @128K i 5 507 @512K. Interpolacja do 200K daje ≈6.3K.
   - cuteafd z RTX 5090 robi 6 272 t/s @200K, czyli **parytet**.
   - Teza sieciowa (2× używany ConnectX-5 100G ≈ switch 400G) jest prawdziwa, ale trywialna: łącze pracuje w ~11–15% (11 Gb/s z 98). Decode zależy od opóźnienia, a ruch na krok to dziesiątki KB/warstwę.
5. **Dla nas:** ani SAGE, ani AFD nie poprawia 24 GB (XTX 114.8 t/s, Q4_K_XL + MTP). **Jedyna wartościowa rzecz to dane EXL3-SC dla Qwen3.8-27B** (wykres turboderpa, ten sam trace i harness dla GGUF):
   - SC 4.0 bpw ≈ jakość UD-Q4_K_XL przy −24% bajtów;
   - SC 3.0 bpw ≈ UD-Q3_K_XL przy −25% bajtów.
   - To dokładnie ta luka, przez którą PLAN-NV-V2 pisze „16 GB: brak modelu 27B spełniającego próg” (Q3_K_XL przy 131k nie mieści się o ~1.3 GB).
   - Warto to zmierzyć naszym protokołem 16e. Są dwie drogi: (a) EXL3 jako drugi silnik dla 12/16 GB, albo (b) **tani transfer alokacji SC do GGUF** przez `llama-quantize --tensor-type`.

## 1. Tabela tez

| # | Teza | Źródło | Werdykt | Dowód |
|---|---|---|---|---|
| 1 | „SAGE, our own mixed-precision method for EXL3” | karta HF | **potwierdzone (opis), metoda nieopublikowana** | karta: „The method is not published”. Nagłówki: ekspert/projekcja ma własne K∈{1,2,3,4}; head K8 (`head.trellis [320,8080,128]`); MTP-eksperci też EXL3 |
| 2 | SAGE ≠ zwykły EXL3 | karta | **częściowo** | Format i kernele to upstream EXL3. Upstream ma od v1.4.x per-tensor alokację SC (`ex3/doc/optimize.md:1-80`, `sc_optimize.py:16-36`). Nowe w SAGE: granulacja per ekspert (46 080 tensorów) i K1. Korelacja z częstością routingu: zimni eksperci K̄=1.252 vs reszta 1.640 (moje liczenie: `qh.json` × `configs/cold-alias-selection.json`). Sam fork `vcruz305/exllamav3@909ad85` dodaje mixed-K unified MoE kernel |
| 3 | „1.62 bpw” | karta | **potwierdzone dla ekspertów routowanych** | 102.38 GiB / 543.6 G parametrów (40×384×3×5120×2304) = 1.618 bpw. Całość bez Engram: 115.3 GiB; z Engram: 304.1 GiB (nagłówki 17 shardów) |
| 4 | „~112.9 GiB GPU-resident, single 128 GB device” | karta | **częściowo** | README: „All-experts-resident does not fit under vLLM”. Rezerwacja 110.5 GiB z 121.7, MemAvailable 3–4 GiB. 1 418 ekspertów + embedding (8.59 GiB) mmapowane z NVMe; każdy krok czyta ~8 MiB z dysku. Pierwszy boot po buildzie trwa 1.5–3× dłużej. Engram (189 GiB) zawsze z NVMe |
| 5 | Top-1 94.52%, mean KL 0.0982, p50 0.00019 vs „official FP8/FP4” | karta | **niezweryfikowalne / mylące** | Brak zbioru, skryptu i liczby tokenów. Punkt odniesienia to wersja z ekspertami FP4, nie BF16. Przy dwumodalnym rozkładzie KL (wykres hist. turboderpa: pik przy 1e-6 i drugi przy 1e-3…1e-1) mediana mierzy tylko pewne tokeny. Top-5 overlap 81.16% < top-1 94.52% oznacza, że ogon się przestawia, a przy T=1.0 (zalecenie DeepSeek) próbkujemy właśnie z ogona. „General” KL 0.2245 / top-1 89.9% to poziom IQ2 dla modeli gęstych |
| 6 | Kategorie code 99.08% / KL 0.0186 | karta | **podejrzane** | Mediana kodu 4e-6 sugeruje tekst o bardzo niskiej entropii, np. wygenerowany przez sam model wzorcowy `[INFERENCE]`. Siostrzany DERISKED 1.61 bpw (ten sam autor, ~ten sam rozmiar) podaje dla kodu KL **0.103**, a ogólnie 0.193 ([karta](https://huggingface.co/vcruz305/DSV4.1-Flash-1017-DERISKED-EXL3-1.61bpw)). Różnica 2–5× przy tej samej klasie paczki znaczy, że protokół nie jest porównywalny |
| 7 | Zadania (pass rate) | — | **brak** | Ani karta, ani recepta. Recepta: „Pack-level quality figures are on the model card. This recipe did not re-run them”; jej TF-check to 32 pozycje (bramka kernela, 1 token = 3.1 pkt) |
| 8 | Decode 35.5 t/s na 1× Spark (vLLM) | README recepty | **potwierdzone, ale best case** | bench7: `temperature 0`, `ignore_eos`, 512 tok, plain `/v1/completions` (`bench/bench7.py:72-73`). 130–137 ms/krok × 4.7 tok/krok; bez draftu 13.4 t/s. Akceptacja „waha się 3.4–5.5 między runami” (`ENGINEERING_NOTES.md:201-203`) |
| 9 | Prefill 1 189 t/s, 229K kontekstu | README | **częściowo** | Przy 229K: 1 147–1 179 t/s na **wypełniaczu logowym** („log lines route to fewer experts”). Prawdziwy tekst: 533 (1.6K) – 963 (24K), „Use ~720 tok/s as the real-text figure”. Retrieval pojedynczej igły przy 225K/520K: tak (słaby test). KV 1 GiB bf16 wystarcza na 760K tokenów przy 229K dzięki kompresji CSA/SWA-128 V4.1 |
| 10 | Roofline GB10 dla 35.5 t/s | moje | **wiarygodne** | §2.3: sufit ~63 t/s przy 4.7 tok/krok; zmierzone ~55% sufitu, zgodnie z „116 GB/s achieved against ~270” (`ENGINEERING_NOTES.md:174`) |
| 11 | exllamav3 wspiera Qwen3.8-27B (hybryda GDN) | README exllamav3 | **potwierdzone** | `Qwen3_5ForConditionalGeneration` ✓ (README:230), BC_GDN (`doc/env_vars.md` „Gated-delta-net (Qwen3-Next/3.5…)”), MTP `qwen3_5_mtp.py`, DFlash2 i SAM n-gram |
| 12 | exllamav3 na ROCm/gfx1100 | release v1.6.3 | **potwierdzone (działa), prędkość nieznana** | Koła `exllamav3-1.6.3+rocm10.0.torch2.13.0-cp31{2,3,4}`. Ścieżki RDNA: fdot2 GEMV, WMMA int8, tablica WMMA gfx1100, `EXL3_GRAPHS=0` na ROCm. Brak liczb t/s dla 7900 XTX (KB: ~15 t/s historycznie, `qwen-opt/research/tensorfold/kernels.md:237`) |
| 13 | EXL3-SC Qwen3.8-27B: lepsza jakość/bajt niż GGUF | wykres [turboderp](https://huggingface.co/turboderp/Qwen3.8-27B-exl3) | **potwierdzone w ich protokole; do sprawdzenia w naszym** | Mean KLD do BF16 na self-generated trace (19 016 wej. + 45 930 wyj. tokenów), x = GiB wag bez embeddingów: SC 3.0 H4 **0.0257 @~9.1** vs UD-Q3_K_XL 0.0209 @12.1 vs UD-Q2_K_XL 0.0587 @9.5; SC 4.0 H5 **0.0062 @~12.2** vs UD-Q4_K_XL 0.0051 @16.0 vs IQ4_XS 0.0101 @13.9. Zwykły EXL3 (bez SC) też wygrywa z GGUF przy tym samym rozmiarze. Obciążenie: kalibracja SC i trace ewaluacyjny pochodzą z tego samego rozkładu (self-generated, rozłączne prompty) |
| 14 | cuteafd: AFD (attention+KV na GPU, eksperci na Sparkach) | README cuteafd | **potwierdzone** | Rust + CuTe/CUDA; RoCE wprost do pamięci GPU; „Each remote expert layer is one round trip”. ROCm brak (grep: 0 trafień w kodzie) |
| 15 | „+36% prefill, +21% decode @200K vs Sparks alone” | strona hub-vs-switch | **mylące (silnik vs silnik)** | Baza: „SGLang TP4, measured on the switch”, bez danych i konfiguracji. justincasey r6w (vLLM, ring, te same 4 Sparki, **0 dodatkowych NIC**): 6 622 / 6 505 / 5 507 t/s @32K/128K/512K, czyli ≈6.3K @200K wobec 6 272 w cuteafd. Decode C1 prose 65.1 vs cuteafd 1K prose 70.1, 200K 60.5 (justincasey nie mierzył decode na głębokości) |
| 16 | 2× używany ConnectX-5 Ex (hub-and-spoke) = switch 400G | strona | **potwierdzone, ale trywialne** | Prefill hub +2–5% od 16K (25/25 punktów), decode +1.6% (szum). Przewaga hubu to brak strat incastu na źle ustawionym switchu (Gen5 x8, bez PFC, 6.7 M zdarzeń out-of-sequence). Autorzy piszą to sami. Łącze 100G pracuje w ~11% |
| 17 | 0.32 MB/token/Spark, 11 Gb/s/łącze | strona | **spójne** | 6 272 tok/s × 0.32 MB = 2.0 GB/s ≈ 16 Gb/s w obu kierunkach; wejście do koordynatora 11 Gb/s (powrót większy niż wysyłka, BF16 vs FP8) |

## 2. Rachunki

### 2.1 Rozmiar DS-V4.1-Flash-1017 (z nagłówków safetensors)

| część | oficjalne FP8/FP4 | SAGE 1.62 |
|---|---:|---:|
| eksperci routowani (40 × 384, 543.6 G param.) | 268.95 GiB (MXFP4) | **102.38 GiB** |
| eksperci MTP/DSpark (3 × 128) | 6.72 | 2.78 |
| reszta (attention FP8, hc, gate, norm) | 5.52 | 5.52 |
| shared expert FP8 | 1.32 | 1.32 |
| embed / head | 1.23 / 1.23 | 1.23 / 0.62 (K8) |
| vision + MTP-reszta | 0.77 + 0.66 | 0.77 + 0.66 |
| **Engram** (2 tablice, NVMe) | 188.83 | 188.83 |
| **suma** | 475.24 GiB | **304.12 GiB** |

Model jest „Flash” z nazwy, ale ma ~560 G parametrów i ~15 G aktywnych na token: 8.5 G routowanych + ~6.5 G gęstych.
Bez Engram to 115.3 GiB ≈ 1.75 bpw średnio. Kompresja wobec wersji wzorcowej: eksperci 4.25 → 1.62 bpw (×2.6).

### 2.2 Pamięć na 1× Spark (121.7 GiB widoczne)

- 110.5 GiB rezerwacja, ~3 GiB page cache na zimnych ekspertów, 0.5 GiB podłogi guardu.
- 1 GiB KV wystarcza na 1.83× jednego żądania 524K (kompresja V4.1).
- Bez aliasu zimnych ekspertów boot pada (+4.6 GiB transientu).
- Wniosek: to **ręcznie wyważona konfiguracja na granicy OOM**: memory guard, sysctl, restart po każdym buildzie. Nie jest to „mieści się”.

### 2.3 Roofline decode na GB10 (273 GB/s)

- Część gęsta czytana co krok: attention ~5.9 GB + shared 1.42 + head 0.67 → **~8.0 GB**.
- Ekspert: 3 × 5120 × 2304 × 1.62/8 = 7.17 MB. Token: 6 ekspertów × 40 warstw = **1.72 GB**.
- 1 wiersz: 9.7 GB / 273 = 35.6 ms, czyli **sufit 28 t/s bez spekulacji** (zmierzone 13.4 przed tile-K).
- Weryfikacja 6 wierszy (k=5): oczekiwana liczba różnych ekspertów na warstwę 384·(1−(1−6/384)^6) = 34.6, więc 34.6 × 7.17 MB × 40 = 9.9 GB. Do tego 8.0 GB gęstej części: 17.9 GB, czyli 65.6 ms + drafter 9.2 ms = 74.8 ms → 4.7/0.0748 = **~63 t/s sufitu**.
- Zmierzone 130–137 ms/krok (~35 t/s), czyli ~50–55% sufitu. Wynik wiarygodny. Szybciej się nie da bez innego kernela MoE, bo autor sam pokazuje łańcuch zależności per K-slice.

### 2.4 Sieć AFD (cuteafd, DS-V4.1)

- Prefill: 0.32 MB/token/Spark × 6 272 t/s = 2.0 GB/s ≈ 16 Gb/s w obu kierunkach. Łącze 100G (zmierzone 98 Gb/s RDMA write) jest zajęte w **~11–16%**.
- Decode C1: krok weryfikuje ~5–6 wierszy. 0.32 MB / 40 warstw ≈ 8 KB/warstwę/token/Spark, więc ~48 KB/warstwę/krok:
  - serializacja 48 KB @ 98 Gb/s = 3.9 µs;
  - plus RTT RoCE ~3–5 µs `[INFERENCE]`;
  - razem ~8 µs × 40 warstw ≈ **0.3 ms/krok**, przy kroku ~50 ms (60 t/s, ~3 tok/krok) to **<1%**.
- Nawet 10 GbE (39 µs serializacji/warstwę) kosztowałoby ~1.7 ms/krok (~3%).
- Wniosek: przepustowość łącza jest tu nieistotna. Liczą się straty pakietów (go-back-N) i opóźnienie. Teza „100G = 400G” to skutek tego, że łącze stoi w 85% bezczynne.

## 3. Co z tego stosuje się u nas (ranking)

| # | Pomysł | Gdzie | Szacowany zysk | Wysiłek |
|---|---|---|---|---|
| 1 | **Zmierzyć EXL3-SC Qwen3.8-27B (SC_3.00bpw_H4, SC_4.00bpw_H5) naszym protokołem 16e (KLD-wiki / czat PL do BF16)** | 12/16 GB NVIDIA, potem XTX | **Jakość/bajt.** Jeśli wykres turboderpa się przeniesie, to przy jakości ≈Q3_K_XL (J1) wagi na GPU spadają z ~12.3 GB (AP-Q3_K_XL bez token_embd) do ~10.0–10.8 GB (SC 3.0–3.25; embedding bf16 2.54 GB exllamav3 trzyma na CPU). Odzysk ~1.5–2.3 GB to ~85–130k tokenów przy g≈14–18 KB/token. **16 GB: z „brak modelu” (51k) na ≥131k z J1** `[INFERENCE]`. 12 GB: SC 3.0 (~10 GB) mieści się z małym kontekstem, czyli pierwszy 27B z J1 na 4070 Ti / 3060 `[INFERENCE]` | pomiar: 1 h CPU (pobranie 13–17 GB), 10 min GPU; produkt: drugi silnik (Python, TabbyAPI to AGPL; samo exllamav3 to MIT) |
| 2 | **Transfer alokacji SC do GGUF**: odczytać per-tensor K z `quantization_config.json` turboderpa (707 wpisów; SC 3.0: K2 2.55 G, K3 19.25 G, K4 3.78 G, K5 0.02 G parametrów) i odwzorować na `llama-quantize --tensor-type` (K2→Q2_K/IQ2_S, K3→Q3_K/IQ3_S, K4→Q4_K/IQ4_XS, K5→Q5_K, K6→Q6_K) | nasza ścieżka GGUF, wszystkie karty | Niepewny. Wzorzec SC: k/v_proj w górę (K4–5), q_proj w dół (K2–3). SC vs zwykły EXL3 daje −23…−30% KLD przy równym rozmiarze, ale UD/AP już robią alokację per warstwa, więc realnie **0–15% KLD** albo **~5–10% bajtów** przy tym samym KLD `[INFERENCE]`. Na 16 GB 0.7–1.3 GB to +40–80k kontekstu. Na 24 GB mniej bajtów to decode szybszy o ~3–6% (pasmo) `[INFERENCE]` | 1 dzień CPU (skrypt mapujący + kwantyzacja), 10 min GPU na KLD |
| 3 | **Self-generated imatrix**: imatrix z `cal_trace.safetensors` turboderpa (250 × 2048 tokenów; prompty z 19 języków, ten sam tokenizer Qwen3.8) zamiast tekstu ogólnego | GGUF | `doc/optimize.md` (Rationale 2): kalibracja na własnym, szablonowanym wyjściu modelu przenosi się lepiej. U nas zysk na czacie PL/kodzie: nieznany, może kilka–kilkanaście % KLD-czat `[INFERENCE]` | imatrix na XTX z Q8_0: 512k tokenów ≈ 8–10 min GPU |
| 4 | Alokacja per ekspert ważona częstością routingu (lekcja SAGE) | tylko modele MoE (Flash-Next itp.) | Dla gęstego 27B nic. Dla MoE na 24 GB + CPU zimni eksperci mogą zejść do 1–2 bitów. **Blokada strukturalna w GGUF:** `ffn_*_exps` to jeden tensor 3D z jednym typem ggml, więc typy per ekspert wymagają rozbicia tensora | duży; poza rdzeniem |
| 5 | qbench (exllamav3 `eval/qbench.py`) jako harness: ma silnik `llamacpp`, cache logitów, podłogę szumu bf16, histogramy per token | narzędzia jakości | Porównywalność EXL3↔GGUF w jednym protokole; raportowanie podłogi szumu przy KLD | 0.5 dnia |
| 6 | SAM frozen-corpus n-gram drafter (`util/build_sam.py`, korpus 100 MB SWE-smith/Magicoder) | spekulacja | Mamy lookup kontekstowy i `ngram-cache` (statyczny) w llama.cpp. Zamrożony korpus ogólny może pomóc w kodzie agentowym; na czacie nic `[INFERENCE]` | niski priorytet |

## 4. Co się nie stosuje i dlaczego

- **1.62 bpw dla gęstego Qwen3.8-27B:** na wykresie turboderpa SC 1.6 bpw ma KLD **0.40**, a 2.2 bpw 0.088. Trik 1–2 bitów działa tylko dlatego, że w MoE z 384 ekspertami top-6 większość ekspertów jest rzadko używana, a błąd rzadkiego eksperta rzadko trafia w token. Gęsta FFN takiej ulgi nie ma. „Near-Q4 przy 2.5–3 bpw”: **fałsz** dla 27B. SC 3.0 = jakość Q3_K_XL (0.0257 vs Q4_K_XL 0.0051, 5× gorzej). Q4_K_XL wymaga ~4.15 bpw SC (interpolacja log-liniowa 4.0 → 5.0).
- **EXL3 jako silnik na 24 GB:**
  - u nas XTX 114.8 t/s (Q4_K_XL, MTP, GPU verify, coupled sampling);
  - exllamav3 na gfx1100 dawał historycznie ~15 t/s;
  - na NVIDIA (5090, Gemma-4-12B) EXL3 4.0 decode 113 vs GGUF Q5_K_M 130 przy 1.37× więcej bajtów w GGUF. Kernel EXL3 osiąga ~0.63× efektywnego pasma GGUF na bajt (`03-silniki-i-stack.md:231-233`);
  - mniejszy plik nie zwróci straty kernela.
  - Plus prefill: EXL3 wygrywa 2.3× (tamże), ale to nie jest nasza metryka.
- **Kernel trellis w naszym forku dla szybkości:** dekodowanie trellis to ~4.5 instrukcji/wagę (`ENGINEERING_NOTES.md:107-110`). Na 3060/4060 Ti, które już są compute-bound w IQ, prędkość spadnie. To zgadza się z R15e #7 (10–20 osobodni, prędkość niepewna).
- **AFD w domu (CPU+GPU, 2 GPU, Mac+PC) dla Qwen3.8-27B:**
  - Model jest gęsty i mieści się na 24 GB, więc AFD nie ma czego rozdzielać.
  - Gęsta FFN na CPU: ~10.5 GB/token przy Q4 na DDR5 2-kanał (~80 GB/s) to ~130 ms/token, ~7.6 t/s, gorzej niż Q3 w całości na GPU.
  - 2 GPU: layer split to 1 transfer/krok. AFD to 2 × 64 warstw = 128 transferów × ~10 µs (PCIe przez hosta) ≈ 1.3 ms/krok, czyli ~5% straty przy kroku 27 ms, bez zysku w single-stream (AFD zyskuje na mikrobatchach ping-pong i współbieżności).
  - Mac+PC przez TB/10GbE: ~30–100 µs/warstwę × 64 ≈ 2–6 ms/krok, czyli −7…−20%.
  - Dla MoE na jednym hoście AFD **już mamy**: `-ot exps=CPU` / `--cpu-moe` to dokładnie attention na GPU i eksperci na CPU (R28).
- **cuteafd / Sparki:** sprzęt klasy $4k × 4 + RTX 5090 + Threadripper to nie nasza grupa docelowa. Tylko CUDA (CuTe), zero ROCm i Metal.
- **16 GB Mac:** exllamav3 i cuteafd nie mają Metala. Nic z tego raportu nie dotyczy Maca.
- **Fork vcruz305 (mixed-K unified MoE, tile-K 16, W2 warp-private stages):** to sm_121 (GB10) i MoE. Lekcje metodyczne są dobre i zgodne z naszymi: parytet przed pomiarem czasu, mikrobench ≠ model, „ms/krok jest stabilną osią, tok/s nie”. Kodu dla nas brak.

## 5. Odpowiedź na pytanie 3: czy coś z tego bije nasze podejście?

| klasa sprzętu | wynik |
|---|---|
| 24 GB AMD (XTX) / NVIDIA (3090/4090) | **Nie.** Nasz fork (MTP + lookup + GPU verify) wygrywa prędkością decode. EXL3 daje lepszą jakość/bajt, ale Q4_K_XL i tak się mieści. Ewentualny zysk to tylko #2/#3 (alokacja i imatrix w GGUF) |
| 16 GB NVIDIA (4060 Ti / 5060 Ti) | **Potencjalnie tak, pod względem dopasowania.** EXL3-SC ~3.0–3.25 bpw może dać jakość J1 przy ≥131k, czego nasz GGUF dziś nie daje. Prędkość nieznana (patrz E2). Do pomiaru |
| 12 GB NVIDIA (3060 / 4070 Ti) | **Potencjalnie tak:** pierwszy 27B z J1 (SC 3.0 ≈ 10 GB wag), krótki kontekst `[INFERENCE]` |
| 16 GB AMD | jak 16 GB NVIDIA, ale prędkość exllamav3 na RDNA niezmierzona i historycznie słaba |
| 16 GB Mac | **Nie dotyczy** (brak Metala) |
| Spark / 128 GB unified | SAGE realnie pozwala odpalić 560B-MoE na 1× Spark (~35 t/s greedy, ~720 t/s prefill), kosztem jakości: mean KL 0.1 do wersji FP4, brak zadań. Nie nasz rynek; do katalogu tylko jako ciekawostka |

## 6. Następne kroki (eksperymenty GPU ≤10 min; przygotowanie na CPU)

Przygotowanie (CPU, bez GPU):
```
nice -n 19 hf download turboderp/Qwen3.8-27B-exl3 --revision SC_3.00bpw_H4 --local-dir ~/m/q38-sc3   # 13.45 GB, rev 86b95530
nice -n 19 hf download turboderp/Qwen3.8-27B-exl3 --revision SC_4.00bpw_H5 --local-dir ~/m/q38-sc4   # 16.7 GB, rev 4acd9ad5
pip install exllamav3-1.6.3+rocm10.0.torch2.13.0-cp312-cp312-linux_x86_64.whl   # z release v1.6.3; torch 2.13 ROCm 10.0
```
- **E1 (XTX, ROCm, ~10 min): prędkość.**
  - Polecenie: `python eval/perf.py -m ~/m/q38-sc4 -max_length 32768 -dr 3`, potem to samo dla `q38-sc3`.
  - Odczyt: decode 100-tok na kilku głębokościach i prefill.
  - Porównanie z naszym plain Q4_K_XL bez MTP na XTX (`spec_sweep` plain). Kryterium: jeśli EXL3-SC4 plain < 0.8 × nasz plain, EXL3 odpada jako silnik na AMD.
- **E2 (5060 Ti / 4060 Ti wynajęte lub lokalne, CUDA, ~10 min):**
  - to samo `perf.py`, plus `python eval/spec_decode.py -m ~/m/q38-sc3 -single 'Chat*' -temp`, żeby zobaczyć MTP;
  - sprawdzić, ile kontekstu mieści się w 16 GB z cache k4v4: `examples/chat.py ... -cache 131072` z kwantyzacją cache i notowaniem szczytu VRAM;
  - kryterium: ≥131k i ≥20 t/s po 64k (J3/J4).
- **E3 (XTX, ~10 min): jakość naszym protokołem.**
  - Teksty 16e (wiki + czat PL) jako `test_data` w qbench.
  - Wzorzec: `turboderp SC_6.00bpw_H6` jako proxy BF16 (KLD 0.0006 do BF16 na ich trace) albo nasze logity BF16 z 16e, jeśli są w cache.
  - Modele: SC3, SC4, AP-Q3_K_XL (engine `llamacpp`).
  - Kryterium: SC3 KLD-wiki ≤ 0.05 i KLD-czat ≤ 0.07 (J1).
- **E4 (CPU 1 dzień + XTX 10 min): transfer alokacji SC do GGUF.**
  - Skrypt: `quantization_config.json` (SC_3.00bpw_H4 i SC_4.00bpw_H5) → lista `--tensor-type <nazwa_gguf>=<typ>` (mapowanie nazw HF→GGUF: `linear_attn.in_proj_qkv` → `attn_qkv`, `mlp.down_proj` → `ffn_down` itd.).
  - Kwantyzacja z naszego BF16 GGUF z imatrix AP.
  - KLD 16e w porównaniu z AP-Q3_K_XL przy równym rozmiarze pliku. Kryterium: −10% KLD-czat albo −0.7 GB przy tym samym KLD.
- **E5 (XTX ~10 min): imatrix z self-generated trace.** Zdekodować `cal_trace.safetensors` do tekstu (tokenizer Qwen3.8), `llama-imatrix -m Q8_0.gguf -f trace.txt -c 2048`, kwantyzacja Q3_K_XL z tym imatrix, KLD 16e vs AP-Q3_K_XL.

Kolejność: E3 → E4/E5 (tanie, nasza ścieżka) → E1/E2 tylko jeśli E3 da J1 przy ≤11 GB.

## 7. Do bazy wiedzy (proponowane wiersze ZRODLA)

| źródło | wersja / commit | data | werdykt | co sprawdzić następnym razem |
|---|---|---|---|---|
| SAGE-EXL3 (vcruz305; HF `DSV4.1-Flash-1017-SAGE-EXL3-1.62bpw`, recepta `DSV4.1-Flash-1017-EXL3-Spark-recipe`) | karta `c852150e` (recepta przypina `2a605935`; historia HF nadpisywana), recepta `b4c890a1`, fork `vcruz305/exllamav3@909ad85` | 2026-10-20 | Metoda nieopublikowana: EXL3 z K per ekspert (K1 55%), ważone routingiem. 1.62 bpw tylko eksperci; paczka 304 GiB (189 GiB Engram z NVMe). 1× Spark ~35 t/s greedy, prefill ~720 t/s na prawdziwym tekście. Wierność do FP4, nie BF16; brak zadań; DERISKED 1.61 tego autora ma 2× gorszy mean KL | Czy autor opublikuje metodę i zbiór; czy pojawią się metryki zadaniowe; T=1 akceptacja |
| exllamav3 ścieżka SC (`sc_trace/sc_measure/sc_optimize`, `doc/optimize.md`, `eval/qbench.py`) + koła ROCm | v1.6.3 `a3bfbfd` (koła `+rocm10.0.torch2.13.0`) | 2026-10-20 | Per-tensor alokacja bitów z czułości (szum LDLQ, greedy); qbench ma silnik `llamacpp`; RDNA: fdot2/WMMA int8, gfx1100 tablice | Prędkość na gfx1100 (E1); czy SC dotarło do MoE („untested on sparse models”) |
| turboderp/Qwen3.8-27B-exl3 (SC_* i zwykłe; wykres KLD vs GGUF) | `d23340a1`; SC_3.00bpw_H4 `86b95530`, SC_4.00bpw_H5 `4acd9ad5` | 2026-10-20 | SC 3.0 ≈ UD-Q3_K_XL przy −25% bajtów; SC 4.0 ≈ UD-Q4_K_XL przy −24%; obciążenie: kalibracja = rozkład ewaluacji | E3 (nasz protokół 16e), E4 (transfer alokacji do GGUF) |
| cuteafd (github.com/tpurtell/cuteafd) | v3.0.1 `9098781` | 2026-10-20 | AFD: attention/KV na RTX, eksperci na Sparkach po RoCE; CUDA/CuTe tylko. „+36%/+21%” to porównanie z SGLang TP4; strojony vLLM na samych 4 Sparkach daje parytet prefill | Czy pojawi się porównanie z r6w/justincasey; Qwen gęsty na RTX (bez Sparków) – prędkość |
| Turquoise Bay „hub-vs-switch” (services.turquoisebay.ai/share/hub-vs-switch.html) | pomiar 18–19.10 | 2026-10-20 | Prawda, ale trywialna: łącze 100G w ~11%; wygrana hubu to brak strat incastu na źle ustawionym switchu | — (temat zamknięty) |
| justincasey/DeepSeek-V4.1-Flash-1017-4x-DGX-Spark (spark-ds41f r6w, ring bez switcha) | `fa77c26` | 2026-10-20 | Baza porównawcza: 4× Spark, prefill 6.5K @128K, decode C1 65–94 t/s; korupcja w trybie thinking 9/13 offsetów (otwarte) | Decode na głębokości 200K; rozwiązanie korupcji thinking |

## Źródła (pliki i linie)

- `/tmp/res-sage/recipe/README.md`: pamięć, prefill (tabele „Measured prefill”, „Measured long context”), „All-experts-resident does not fit”.
- `/tmp/res-sage/recipe/docs/ENGINEERING_NOTES.md:44-59` (pamięć), `:101-110` (kernel), `:166-181` (atrybucja kroku), `:201-203` (rozrzut akceptacji).
- `/tmp/res-sage/recipe/bench/bench7.py:72-73` (`temperature 0`, `ignore_eos`).
- Nagłówki safetensors: `/tmp/res-sage/{qh,uph}.json` (skrypt `hdr.py`, analiza `an.py`).
- `/tmp/res-sage/ex3/doc/optimize.md:1-200`, `sc_optimize.py:16-36`, `eval/qbench.py:11-35`, `doc/env_vars.md:10-34,320-329`, `exllamav3/exllamav3_ext/rocm/wmma_gemm.cuh:16-47`, README:230-232.
- `/tmp/res-afd/cuteafd/README.md`, `docs/models/deepseek_v41.md:1-60`.
- `/tmp/res-afd/jc/bench/records/2026-10-18-autoresearch/summary.md`.
- Strona: https://services.turquoisebay.ai/share/hub-vs-switch.html; karty HF jak w nagłówku.
