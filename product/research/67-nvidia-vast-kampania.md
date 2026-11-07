# 67: Kampania NVIDIA na Vast (Enigma) — wyniki i finalne zestawy (2026-11-07)

**Wynik po 67c: fork+kvq+lean daje na 4090 262 144 przy 101,3 t/s (+32,5% vs pick Enigmy 76,4), lean daje 16 GB MTP przy 217–229k (+57–84% vs stary pick), a pin b11856 zostaje (5090 99,8 vs b12110 91,6). Część 1:** W trzech godzinach na 17 wynajętych kartach zmierzyliśmy konfiguracje CUDA od 2080 Ti do 5090. Na 24 GB pełny kontekst 262 144 z MTP działa i daje +67,6% na 4090 i +44,7% na 5090; na 16 GB warianty 27B z MTP wywalają się przy pierwszym długim prompcie, więc Enigma potrzebuje zapasu ≥0,7 GiB ponad to, co widać po załadowaniu. Kampania zatrzymana przez użytkownika po wydaniu $3,47 z $10,51; zero maszyn zostało w chmurze. Kampania 67c (wznowienie tego samego wieczoru, 11 hostów) domknęła wszystkie zaległości z §5.

Liczby części 1 (§3–§4): mediana `spec_sweep` (6 promptów PL/EN × seedy 1–3, T=1); liczby 67c (§1, §2, §5, §7): seed 1, silnik upstream b11856 (pin Enigmy) i b12110, KV q4_0, `-fa` włączone. „P0” = dokładnie to, co Enigma uruchamia dziś (bez spekulacji), „P4” = dzisiejszy kandydat Enigmy (MTP n=4), „N{n}u” = MTP n z `--spec-draft-n-ubatch 64`.

## 1. Finalne zestawy per klasa (stan po 67c)

Pomiar 67c: T1 = mediana `spec_sweep` (6 promptów × seed 1 × 400 tok., T=1); walidacja = fill (prompt ctx−640 + 128 tok. greedy) na dokładnie tych flagach, które uruchamia Enigma. „Dziś” = pick Enigmy przed kampanią (stary katalog z Gemmą, silnik pin b11856), „teraz” = nowy domyślny pick (katalog po 67c, silniki opublikowane), „z silnikiem Enigmy” = prism / lean / fork, działające u użytkownika dopiero po publikacji archiwów (§7.4). Peak = szczyt `nvidia-smi` w trakcie filla. Limity mocy hostów w §2.

| Klasa | Karta | Dziś (stary pick) | Teraz: pick domyślny, silnik | ctx | t/s dziś → teraz | Walidacja, peak MiB | Z silnikiem Enigmy (zmierzone) |
|---|---|---|---|---|---|---|---|
| 32 GB | 5090 | 27B UD-Q6_K bez MTP 62,49 | Qwen3.8-27B UD-Q6_K, MTP n3 ubd 64, ub 1024, pin b11856 | 262 144 | 62,49 → **102,19** (+63,5%) | PASS (dec 70,4), 28 592 | **fork+kvq+lean (`kvqlean`) ub 512: 148,57** (+47,4% vs pick 100,90 na tym samym hoście, ABBA 100,90/100,61), PASS (dec 167), 28 232 |
| 24 GB | 4090 (250 W) | 27B UD-Q4_K_XL bez MTP 46,94 | UD-Q4_K_XL, MTP n3, ub 256, pin | 262 144 | 46,94 → **76,44** (+62,8%) | PASS (dec 50,7), 24 028 | **fork+kvq+lean 101,27** (+32,5% vs pick, +115,7% vs dziś), PASS, 23 852 (po fillu 23 872) |
| 24 GB | 3090 (340 W) | 27B UD-Q4_K_XL bez MTP 40,93 | UD-Q4_K_XL, MTP n3, ub 256, pin | 245 760 | 40,93 → **61,49** (+50,2%) | PASS 245 120 tok. (dec 41,6), 23 448 | **fork+kvq+lean (`kvqleana`) UD-Q4_K_XL 262 144 ub 256: 79,97** (+30% vs pick, wyższy ctx), PASS, 23 706 (UD-Q4_K_M: 78,97, 22 662) |
| 16 GB | 5080 (250 W) | UD-Q3_K_XL 135 168 plain 52,05 | **ISTA GSQ IQ3_XXS-mtp** plain, ub 256, pin | 208 896 | 52,05 → **58,81** (+13,0%) | PASS, 14 562 (MTP n3: OOM) | **lean MTP n2 217 088: 81,62** (+56,8% vs dziś), PASS, 15 632 |
| 16 GB | 5060 Ti (160 W) | UD-Q3_K_XL 135 168 plain 27,48 | ISTA plain, ub 256, pin | 200 704 | 27,48 → **31,42** (+14,3%) | PASS, 14 230 | **lean MTP n2 229 376: 43,40** (+57,9%), PASS, 15 762; fork+kvq+lean 196 608: 49,44 (PASS, 15 416; 229 376 crash) |
| 16 GB | 4060 Ti | UD-Q3_K_XL 143 360 plain 19,78 | ISTA plain, ub 256, pin | 217 088 | 19,78 → **24,02** (+21,4%) | PASS, 14 566 (MTP n3: OOM) | **lean MTP n2 229 376: 36,30** (+83,5%), PASS, 15 736 |
| 12 GB | 4070 | Gemma 4 12B q8_0 262 144: 54,57 | **Saluki 27B IQ2-mix** plain, ub 256, pin | 151 552 | 54,57 → **44,35** (inny model: 27B zamiast 12B) | PASS (dec 19,5), 11 201; MTP n3 przy tym ctx: OOM | **prism Bonsai PTQ1_0-mtp-lean MTP n2 208 896: 94,73** (×2,14 vs Saluki), PASS (dec 61,3), 11 163 |
| 12 GB | 3060 (140 W) | Gemma 4 12B q8_0 262 144: 37,38 | Saluki 27B IQ2-mix plain, ub 256, pin | 135 168 | 37,38 → **22,23** (inny model) | PASS, 10 781 | **prism Bonsai PTQ1_0-mtp-lean MTP n2 204 800: 58,31** (×2,62 vs Saluki), PASS (dec 33,9), 11 015 |
| 11 GB | 2080 Ti | Gemma 4 12B q4_0 262 144: 52,16 | **Bonsai 2 27B Q2_0** (upstream), ub 256, pin | 131 072 | 52,16 → **39,57** (inny model) | PASS (dec 16,5), 10 243 | **prism Bonsai PTQ1_0-mtp-lean MTP n2 155 648 ub 512: 77,96** (+97% vs Q2_0), PASS, 10 151 |
| 10 GB | 3080 (260 W) | Gemma 4 12B q4_0 258 048: 68,11 | **Qwen3.5-9B Q6_K**, ub 512, pin | 192 512 | 68,11 → **85,20** (inny model) | PASS (dec 41,4), 9 345 | – |
| 8 GB | 3070 | Qwen3.5-9B Q4_K_M | bez zmian, ub 512, pin | 151 552 | **66,90** | PASS (dec 35,5), 7 251 | – |

Walidacja starego katalogu (Gemma, 7 kart) była w całości PASS: 4070 54,57, 3080 68,11, 3060 37,38, 2080 Ti 52,16 (wczorajszy OOM to obcy proces na hoście; dziś czysty host). Gemma odrzucona przez użytkownika → w katalogu `defaultPick:false`.

**MTP n per klasa:** 24 GB n=3 (4090 lean n2 79,73 vs n3 77,54 przy ub 512 – w szumie seed 1); 32 GB **n=3 na pinie** (5090 ABBA: pin n3 99,81/99,75, pin n4 89,70; wczorajsze „n=2” dotyczyło b12110). Lean na 16 GB: n=2 (n1 @200 704: 5080 75,09, 5060 Ti 41,74, 4060 Ti 34,29). Prism Bonsai: n=1 ≈ n=2 (4070 n2 94,81 vs n1 87,77; 3060 i 2080 Ti n1 lepsze o 2–3%).

## 2. Silnik: pin b11856 zostaje; limity mocy hostów

**5090, ten sam host, ABBA (Q6_K 262 144 ub 1024):** pin b11856 MTP n3 **99,81 / 99,75**, b12110 n3 91,58 / 91,86, b12110 n2 93,50, pin n4 89,70 → pin szybszy o ~8,8% z MTP na sm_120 (md5 różne między buildami). Wczorajsze 86,9 t/s (b12110 n2) to host z limitem 450 W. **Decyzja: Enigma zostaje na pinie b11856** (odwołuje „adoptujemy b12110” z pierwszej części kampanii); MTP n=3 na 5090. Plain na 16 GB: pin vs b12110 bez różnicy (5080 52,05 vs 52,50, 5060 Ti 27,48 vs 27,54, 4060 Ti 19,78 vs 19,80).

Pierwsza część kampanii (P0 b11856 vs N0 b12110, bez spekulacji):

| Karta | P0 b11856 | N0 b12110 | Δ |
|---|---:|---:|---:|
| 3060 | 35,24 | 35,31 | +0,2% |
| 3070 (Qwen3.5-9B) | 32,69 | 30,11 | **−8%** (prefill 1 809 → 1 618 t/s) |
| 3080 | 67,98 | 69,29 | +1,9% |
| 4070 | 52,22 | 52,83 | +1,2% |
| 4090 | 46,87 | 47,10 | +0,5% |
| 5060 Ti | 28,74 | 28,78 | +0,1% |
| 5080 | 55,00 | 55,35 | +0,6% |
| 5090 | 60,18 | 60,17 | 0% |

**Limity mocy hostów 67c (obecny/domyślny, `nvidia-smi`)** – bez nich wyniki między hostami są nieporównywalne (E2): 3090 340/390 W (Xeon E3-1245 v2 bez AVX2, PCIe 3), **4090 250/450 W**, 5090 575/575 W (wczorajszy 5090: 450/600 W), 5080 250/360 W, 5060 Ti 160/180 W, 4060 Ti 165/165 W, 4070 200/200 W, 3080 260/320 W, 3070 220/220 W, 3060 140/170 W (wczoraj 105 W), 2080 Ti 250/250 W (czysty host). Liczby 4090 są więc zaniżone względem karty na pełnej mocy.

## 3. Znaleziony błąd: zapas na pierwszy długi prompt na kartach 16 GB

Zmierzone: 27B UD-Q3_K_XL + MTP przy 135 168 i 131 072 nie ładuje się na 5060 Ti / 5080 / 4060 Ti pod żadnym wariantem (brakuje 0,5–1 GiB). ISTA IQ3_XXS-mtp **ładuje się** przy 200–217k z 0,5–0,66 GiB wolnego po `nvidia-smi`, a potem **wywala się przy pierwszym prefillu 4 096 tokenów** (`launch_mul_mat_q`, doładowanie kerneli CUDA). Wniosek: planer musi zostawiać **≥0,7 GiB ponad załadowany model**; dodatkowo limit to suma CUDA, nie `nvidia-smi` (5090 32 109, 4090 24 082, 3090 24 126, 4060 Ti 15 947 MiB).

**Poprawki w Enigmie (commit w tym samym dniu):**
- `memory.ts`: model pamięci upstream MTP (stan × (n+1): 299/598/748 MiB dla n 1/3/4; KV draftu w f16 = 1024 MiB przy 262k; compute draftu z `--spec-draft-n-ubatch`; bez wzrostu forka),
- `optimize.ts`: `--spec-draft-n-max` z klasy karty (domyślnie 3) + `--spec-draft-n-ubatch 64`, batch 256 w kandydatach,
- `catalog/index.ts`: dokładny zmierzony odstęp `nvidia-smi` → CUDA per karta (2080 Ti 447 … 5090 498 MiB), dodatkowy zapas 300 MiB na doładowanie kerneli, oraz „zmierzone plany” (4090 linux 262 144 ub 256, 4090 Q4_K_M 262 144 ub 512, 5090 262 144), których estymata nie może odrzucić.
- Efekt w planerze: 4090 262 144 (było 152–160k), 5090 262 144, 3090 245 760.

## 4. Parametry, które nic nie dają (wyniki negatywne)

| Test | Wynik |
|---|---|
| próg pewności draftu `p-min` 0,5 / 0,8 | gorzej wszędzie, gdzie zmierzono: 16 GB MoE 5080 83,4 → (n1p5 80,9, n1p8 76,4); 3080 Gemma 120,2 → 113,5 / 109,9; 4070 Gemma 101,5 → 101,3 / 96,4 |
| `-ctkd q4_0` bez portu lean | +0,9–1,5 GiB kopii f16 (dzisiejszy upstream i tak trzyma KV draftu w f16) |
| rezerwa draftu rośnie z ctx×ub | 648 MiB przy 262k / ub 1024 → `--spec-draft-n-ubatch 64` zbija do 40 MiB, wyjście bez zmian |

## 5. Zaległości z pierwszej części — wszystkie zmierzone w 67c

- **Bonsai 2 27B — zrobione.** Prism (paczka CUDA `prism-b12128-d7b2896`) @65 536 ub 256: 4070 upstream Q2_0 49,43 → prism Q2_0 53,75 → PTQ1_0 66,34 → PTQ1_0+MTP n1 87,77 / **n2 94,81**; 3060 (140 W) 32,23 → 36,19 → 46,87 → 60,02 / 58,60; 2080 Ti prism Q2_0 43,76 → PTQ1_0 61,18 → 76,88 / 74,52. Doszczep głowicy (`inst/graft_mtp.py`) i gotowy plik sudoingx `-mtp-lean.gguf` dają identyczne md5 → wystarcza gotowy plik. Max ctx (fill): upstream Q2_0 4070 196 608 (229 376 OOM), 3060 196 608, 2080 Ti 131 072 (163 840 OOM); prism PTQ1_0+MTP n1 4070 **229 376 PASS** (dec 57,6; 262 144 OOM), n2 208 896 PASS 94,73. 2080 Ti prism PTQ1_0+MTP n1 **196 608 PASS** (dec 38,4; 229 376 OOM), pick n2 155 648 ub 512 PASS 77,96 (peak 10 151). 3060 prism PTQ1_0+MTP n1 **229 376 PASS** (dec 33,4, peak 11 357; 262 144 OOM), pick n2 204 800 PASS 58,31.
- **3090 + fork — zrobione.** Paczka topka2 z `pkg/` jest zbudowana z `-march=native` → `Illegal instruction` na Xeonie E3 v2 (bez AVX2). Build lokalny `kvqa` (bez AVX2): UD-Q4_K_XL 262 144 ub 256 ładuje się (peak 24 028), T1 **66,26** (upstream b12110 MTP n3 61,82, pin 61,49), ale fill wywala się bez lean; UD-Q4_K_M 262 144 ub 512 crash. Fork KVQ=0 UD-Q4_K_M @65 536 ub 512: 82,72; fork+kvq bez lean 196 608 PASS 78,73 (peak 22 030); **fork+kvq+lean (`kvqleana`) UD-Q4_K_M 262 144 ub 256: PASS 261 504 tok., T1 78,97, peak 22 662** (+28% vs pick 61,49); **ten sam kwant co pick, UD-Q4_K_XL 262 144 ub 256: PASS, T1 79,97, peak 23 706** (+30%) – decyzja Main: z forkiem 3090 = XL 262 144. Fork `kvqa` @64k: `LLAMA_GPU_VERIFY=0` 81,78 vs 82,72, `MMVQ_N1_ROWS` 1/4 82,56/82,77 (szum, md5 identyczne).
- **kernel `kvq` na CUDA — zrobione.** 4090 @65 536 ub 512: fork KVQ=0 97,41 → **KVQ=1 100,56** (+3,3%), szczyt 20 260 → 19 790 MiB; bez kvq fork przy 204 800 wywala się w prefillu, z kvq PASS (23 728). 5080 @65 536 ub 256: KVQ=0 **93,94** vs KVQ=1 89,85 (**−4,4%** na sm_120; szczyt 13 610 → 12 842). 3090 (`kvqa`, UD-Q4_K_M @65 536 ub 512): KVQ=0 82,72 vs KVQ=1 78,80 (−4,7%, 1 seed), ale decode w fillu @64k 102,5 → 112,2 (+9,5%), szczyt 19 586 → 18 584 MiB. Wniosek: kvq daje głównie pamięć i długi kontekst; T1 +3% na sm_89, −4…−5% na sm_120 i sm_86.
- **port lean — zrobione.** b12110lean (`-ctkd/-ctvd q4_0`, `--spec-draft-n-ubatch 64`): 4090 UD-Q4_K_XL 262 144 **ub 512** n3 PASS 77,54 (peak 23 430; stock ub 512 OOM), n2 79,73. 16 GB ISTA + MTP n2: 5080 **217 088** PASS 81,62 (229 376 crash, ≥ 245 760 OOM), 5060 Ti **229 376** PASS 43,40, 4060 Ti **229 376** PASS 36,30 (245 760 crash na obu, 262 144 OOM). UD-Q3_K_XL + MTP n2 nawet z lean: 5080 OOM przy 163 840 / 147 456 / 131 072; 5060 Ti i 4060 Ti mieszczą 131 072 (40,37 / 31,54, fill PASS).
- **Gemma 4 12B — zrobione i odrzucone.** Dokładne picki starego katalogu PASS (4070 54,57, 3080 68,11, 3060 37,38, 2080 Ti 52,16); w katalogu `defaultPick:false`.
- **2080 Ti — zrobione.** Czysty host (0 obcych procesów): Gemma 262 144 PASS 9 733 MiB, nowy pick Bonsai Q2_0 131 072 PASS 39,57 / 10 243 MiB, prism PTQ1_0 MTP n1 76,88 @64k.

## 6. Koszt

Część 1 (2026-11-06/07): **$3,47** na 17 maszyn (od $0,056 do $0,24/h; najdroższe 4090 $0,46/h i 5090 $0,48/h). Część 67c: kredyt na start $6,89 → $1,89, czyli **$5,00** (w tym ok. $0,35 za obce instancje spoza kampanii, od ~19:40); wszystkie hosty kampanii skasowane; 11 hostów + buildfarm (Ryzen 3950X: ICE/segfault kompilatora, host zniknął → build lokalny) + drugi 5090. Wyniki: `~/qwen-opt/cloud/results/nv67-<host>-20261107/res-<card>/`, zestawienie `~/qwen-opt/cloud/results/nv67c-summary.txt`, karty/harness `~/qwen-opt/cloud/runs/nv67/` (`mk67c.py`, `inst/nv67.py`, `restart67c.sh`, `st67c.sh`, `sum67c.sh`).

## 7. Kampania 67c (wznowienie, 2026-11-07 wieczór)

Krótkie ramiona (decyzja użytkownika): bez soaków 30 min i bez osobnego kroku 4096; fill tylko dla finalnych przepisów i pytań o limit ctx.

### 7.1 Fork + kvq + lean na 4090: 262 144 przy 101,3 t/s

Fork = `cuda-topka2` 2a261101b + kvq 007a6f813, MTP n4, KV draftu q4_0, słownik draftu 64k, lookup W16. Łatki topka-q63 0001–0003 aplikują się czysto na fork CUDA; 0002 (lean reserve) zmienia tylko `src/llama-context.*`. Buildy lokalne (CUDA 12.8, sm_86/89/120, `GGML_NATIVE=OFF`): `kvq` (AVX2), `kvqa` (bez AVX2), `kvqlean` / `kvqleana` (+ 0002).

| 4090, UD-Q4_K_XL | ctx, ub | T1 | fill | peak MiB |
|---|---|---|---|---|
| upstream b12110 MTP n3 | 65 536, 512 | 76,13 | – | 19 004 |
| fork KVQ=0 | 65 536, 512 | 97,41 (+28%) | PASS, dec 144,2 | 20 260 |
| fork KVQ=1 | 65 536, 512 | 100,56 (+3,3%) | PASS, dec 148,7 | 19 790 |
| fork KVQ=1, `LLAMA_GPU_VERIFY=0` | 65 536, 512 | 97,77 (= KVQ=0 w md5) | – | 19 760 |
| fork KVQ=0 / KVQ=1 | 204 800, 512 | crash w prefillu / PASS | KVQ=1 dec 153,4 | 23 728 |
| fork KVQ=1 | 196 608, 256 | 101,05 | PASS | 23 238 |
| **fork+kvq+lean (`kvqlean`)** | **262 144, 256** | **101,27** | **PASS**, dec 138,4 | **23 852 / 23 872** |

+32,5% vs pick Enigmy (76,44) przy tym samym ctx; md5 = fork bez lean. Decode w fillu jest zawyżony przez lookup na powtarzanym korpusie. `GGML_CUDA_MMVQ_N1_ROWS` 1/2 na sm_89: 98,16 / 97,37 (szum). 3090 (`kvqleana`, UD-Q4_K_M 262 144 ub 256): **78,97**, fill PASS, peak 22 662 (+28% vs pick 61,49). 5060 Ti ISTA: 262 144 OOM, 229 376 crash, **196 608 PASS 49,44** (peak 15 416; lean upstream 229 376 daje 43,40 – fork szybszy o 14% przy mniejszym ctx); UD-Q3_K_XL: 163 840 OOM, 131 072 crash, 98 304 PASS 54,33. 5090 (`kvqlean`, UD-Q6_K 262 144 ub 512, KVQ=1): **T1 148,57**, fill PASS (prefill 1 112 t/s, dec 167), peak 28 232 MiB → +47,4% vs pick (100,90 na tym samym hoście).

### 7.2 Grupa A backlogu (flagi runtime, 1 seed; Δ < 3% = szum)

| test | 4090 (sm_89, XL 65 536 ub 512, MTP n3) | 5080 (sm_120, ISTA 65 536 ub 256, MTP n3) | wniosek |
|---|---|---|---|
| A1 KV q4_0 / q8_0 / f16 | 76,13 / 77,62 / 75,40 | 79,44 / 77,22 / 81,55 | szum; q4_0 zostaje (najmniej VRAM: 19 004 vs 21 726 MiB) |
| A5 `GGML_CUDA_DISABLE_GRAPHS=1` | 76,92 | 78,42 | szum, md5 identyczne |
| A6 `GGML_CUDA_GRAPH_OPT=1` | 77,60 | 78,30 | szum, md5 identyczne |
| A11 `-t` = kwota cgroup | 77,36 (`-t 6`) | 79,82 (`-t 9`) | szum, md5 identyczne |
| A13 `-np 2`, 2 żądania | **agregat 94,35 vs 69,46 (+36%)**; strumienie 55,4 / 48,4 vs 75,3 / 76,0 | **86,73 vs 65,31 (+33%)** | zysk tylko dla wielu równoległych zapytań |
| A7 `GGML_CUDA_PDL=0` | – (no-op na sm_89) | plain 58,92 → 58,09 (−1,4%), MTP 79,44 → 76,98 (−3,1%) | PDL zostaje włączone |

3090 (sm_86, UD-Q4_K_M 65 536 ub 512, b12110 MTP n3): KV q4_0 / q8_0 / f16 63,31 / 64,12 / 64,61; **`DISABLE_GRAPHS=1` 59,96 (−5,3%)**; GRAPH_OPT 62,74; `-t 8` 62,83 – grafy CUDA zostają włączone, reszta w szumie. `-np 2` na 3090: agregat **71,52 vs 54,98 (+30%)**, strumienie 43,3/38,1 vs 62,0/58,4.

### 7.3 LFM2.5-24B-A2B

- **12 GB w całości w VRAM** (4070, b12110, 131 072, KV q8_0, ub 512): UD-IQ3_XXS **179,32 t/s**, fill PASS (prefill 2 602 t/s, dec 87,6), peak 10 525; UD-Q3_K_XL OOM przy ładowaniu. 5060 Ti Q4_K_M w całości w VRAM (131 072, q8_0, ub 512): **139,48 t/s**, fill PASS, peak 15 820. 3060 (140 W) UD-IQ3_XXS w VRAM (131 072, q8_0, ub 512): **102,47 t/s**, fill PASS (prefill 1 417, dec 40,6), peak 10 463; UD-Q3_K_XL OOM przy ładowaniu. Saluki MTP n3 @135 168 na 3060: OOM przy ładowaniu.
- **`--n-cpu-moe`** Q4_K_M 131 072 q8_0: 3080 (10 GB) ncm 12–18 OOM, **ncm 20 40,83**, ncm 24 35,66; 3070 (8 GB) ncm 20–24 OOM, **ncm 26 8,92**, ncm 30 7,74.

### 7.4 Zmiany w Enigmie (`app/engine`, niezacommitowane; 200 testów pass)

- **Katalog:** Gemma 4 12B `defaultPick:false`; nowe kwanty/modele: `qwen38-27b` `GSQ-IQ3_XXS` (ISTA, Apache-2.0), `saluki-27b` IQ2-mix (CC BY-NC 4.0 → `license_conditional:cc-by-nc-4.0`, w UI „tylko niekomercyjnie”), `bonsai2-27b` Q2_0 (Apache-2.0, min. build b11555), `bonsai2-27b-mtp` PTQ1_0 (tylko silnik prism), LFM2.5 UD-IQ3_XXS / UD-Q3_K_XL (`lfm-open-1.0`, < $10M przychodu). GPU `rtx-2080-ti`. Zmierzone konfiguracje (VERIFIED) per karta i punkty kalibracji pamięci.
- **Picki domyślne:** 2080 Ti Bonsai Q2_0 131 072; 3060 Saluki 135 168; 4070 Saluki 151 552; 3070 Qwen3.5-9B Q4_K_M 151 552; 3080 Qwen3.5-9B Q6_K 192 512; 4060 Ti ISTA 217 088; 5060 Ti ISTA 200 704; 5080 ISTA 208 896; 3090 UD-Q4_K_XL 245 760 MTP; 4090 UD-Q4_K_XL 262 144 MTP; 5090 UD-Q6_K 262 144 MTP.
- **Silniki:** `enigma-cuda-lean` (b12110lean), `enigma-cuda-prism`, `enigma-cuda-fork` (`kvqleana` + słownik draftu) w `data/engines.json` jako `distribution:"local"` z `unpublishedAssets` (nazwy + sha256); profile MTP per silnik (lean n2, ubd 64, draft KV q4_0, limit 229 376; prism n2; fork n4 + env); `planOnlyMeasured` dla forka (tylko 4090).
- **Brakujący krok: upload archiwów na release** (`app/engine/CONTRACT.md`, „Silniki Enigma CUDA — brakujący krok”). Do tego czasu kandydat `enigma` kończy się `enigma_not_published:<id>`, a `bonsai2-27b-mtp` → `needs_engine:enigma-cuda-prism`; kolumna „z silnikiem Enigmy” w §1 to stan po publikacji.

## Powiązane
- [[raport-67b-wybor-modeli-nvidia]]
- [[raport-67c-nvidia-backlog-testow]]
- [[raport-27-3090-final]], [[raport-56-orca-3090]], [[raport-29-4060ti]]
- [[2026-11-07-kampania-nvidia-vast]]
