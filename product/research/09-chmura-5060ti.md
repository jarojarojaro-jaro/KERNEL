# 09 — Chmura: RTX 5060 Ti 16 GB (Blackwell sm_120), Faza 0

Data: 2026-10-16. Instancja Vast `56178373` (oferta 54073756, Australia, reliability 0.998), obraz `nvidia/cuda:12.8.1-devel-ubuntu24.04`.
Surowe wyniki: `~/qwen-opt/cloud/results/5060ti-20261016/` (bench.sh: `lb/`, `greedy/`, `tbo/`, `sweep/`; kampania: `opt/`), skrypty: `~/qwen-opt/cloud/runs/5060ti/`.
Kod: gałąź `cuda-v070-5060ti` (worktree `~/wt/5060ti-opt`) od `cuda-v070` @ `7a538d96f`.

## 1. Odcisk sprzętu

| pole | wartość |
|---|---|
| GPU | NVIDIA GeForce RTX 5060 Ti, Blackwell, compute capability 12.0 (build `sm_120a`), 16311 MiB, VBIOS 98.06.39.00.79 |
| sterownik / CUDA | 580.173.02 (CUDA 13.0 max), toolkit w obrazie nvcc 12.8.93 |
| PCIe | gen 4 ×8 (karta ×16-capable, slot ×8) |
| limit mocy | 180 W (default = max = 180 W) |
| zegary max | SM 3090 MHz, pamięć 14001 MHz (GDDR7 28 Gb/s → 448 GB/s) |
| host | AMD EPYC 7502 (64 wątki widoczne), **limit cgroup 7.68 CPU**, 251 GB RAM, Linux 5.15 |
| persistence mode | włączony |

Uwaga do hosta: `nproc` = 64, ale kontener ma limit CFS 7.68 CPU. llama.cpp bez `-t` bierze 32 wątki → przy pracy CPU (np. warstwa MTP na CPU) wątki są dławione przez cgroup. Dlatego wszystkie konfiguracje A1+ mają `-t 8` (A0 zostaje „jak użytkownik”, bez `-t`).

## 2. Metoda

- Buildy: upstream `v0.7.0` (`620d222`) i fork `cuda-v070` (`7a538d9`), oba `-DCMAKE_CUDA_ARCHITECTURES=120` (→ `120a`), Release, 501 s / 503 s na 8 wątkach. Trzecie drzewo `opt` = `cuda-v070-5060ti` (moje przełączniki, przyrostowo przez ccache).
- Poprawność: greedy md5 (T=0, 2 prompty × 400 tok, `enable_thinking=false`), **każdy przebieg na świeżym serwerze**; `test-backend-ops -b CUDA0` na forku.
- Szybkość: `spec_sweep.py` (6 promptów PL/EN, T=1, 400 tokenów), kolejność ABBA (A0 A1 A2 A2s A3 A3 A2s A2 A1 A0), mediany per prompt; `llama-bench` z rundami ABCDDCBA lub on/off/off/on.
- Definicje trybów (jak w zadaniu):
  - **A0** — upstream, `llama-server -m X` (domyślny `-fit`, KV f16, bez spekulacji, domyślne wątki);
  - **A1** — upstream, najlepsze flagi: `-fit off -ngl 99 -t 8 -fa on -ctk q8_0 -ctv q8_0 -c 32768 -np 1`, dla Qwena `--spec-type draft-mtp --spec-draft-n-max 4 -ctkd q8_0 -ctvd q8_0`;
  - **A2-kod** — fork, dokładnie flagi A1 (sam wpływ kodu łatek);
  - **A2** (= „nasz silnik”, w danych `A3`) — fork, flagi A1 + `--spec-draft-vocab draft_vocab_qwen38.txt --spec-draft-vocab-n 65536 --spec-draft-head-type iq4_xs --spec-mtp-type iq4_xs`;
  - **A2-safe** (`A2s`) — fork, flagi A1, wszystkie 31 przełączników z `fork-switches.tsv` = 0.

## 3. Poprawność

**test-backend-ops (fork, CUDA0, sm_120 z PDL):** 19251/19253 OK. Dwa FAIL-e to tylko op forka `GATED_DELTA_NET_PROLOGUE(w_type=q4_K, …, n_tokens=6/8)`: ERR 5.05e-4 i 9.44e-4 przy progu 5.0e-4 (tolerancja numeryczna fuzji prologu GDN, nie błąd pamięci; reszta, w tym wszystkie fuzje MoE/norm/rope/FA, przechodzi). `tbo/fork.txt`.

**Greedy md5 (świeże serwery, T=0, 2 prompty × 400 tok)** — `greedy/summary.tsv`, `opt/greedy.tsv`:

| model | tryb | upstream ×2 | fork ×2 | fork-safe | werdykt |
|---|---|---|---|---|---|
| Qwen3.8-27B Q3_K_XL | plain | 33de84afe124 ×2 | 0e05ac358a1b ×2 | 0e05ac358a1b | DIFF-BUILD |
| Qwen3.8-27B Q3_K_XL | MTP | 4b276b2a5645 ×2 | 5ff7869359bf ×2 | 5ff7869359bf | DIFF-BUILD |
| LFM2.5-24B Q4_K_M | plain | 317556627d00 ×2 | 54d36afa388a ×2 | 54d36afa388a | DIFF-BUILD |

Obie binarki są deterministyczne. Fork różni się od upstream **także przy wszystkich 31 przełącznikach = 0**, czyli winna jest łatka bez przełącznika (pierwsza różnica po ~20 tokenach). Bisekcja md5 (dodałem kill-switche w gałęzi `cuda-v070-5060ti`):

| wariant (drzewo `opt`) | Qwen plain | LFM plain | wniosek |
|---|---|---|---|
| fork (domyślnie) | 0e05ac358a1b | 54d36afa388a | |
| `GGML_HIP_Q8_PRODUCER=0` (producenci q8_1 w norm/GLU/unary) | 0e05ac358a1b | 54d36afa388a | bitowo bez zmian → nie winny |
| `GGML_HIP_GDN_L2=0 GGML_HIP_GDN_AB=0` (+safe) | d3199f6e3127 | — | prolog GDN zmienia bity Qwena, ale ≠ upstream → drugie źródło |
| upstream `GGML_CUDA_DISABLE_FUSION=1` | 33de84afe124 | 7cbd244269af | |
| fork safe + `GGML_CUDA_DISABLE_FUSION=1` | 75069a4bba1c | f947586be361 | ≠ upstream także bez żadnych fuzji |

Wniosek: na NVIDIA są **co najmniej dwa** niebitowe źródła: (1) fuzja prologu GDN (`8dd58b02f`/`7e0de3f22`, tylko Qwen; jej komentarz mówi wprost o innej kolejności sum częściowych) oraz (2) zmiana w ścieżce **bez fuzji**, wspólna dla obu modeli. Łatka FA 0043 (`52699b082`, kolejność chunków K) jest na NVIDIA no-opem (`nbatch_K2 = 128 = DKQ/2` w tabelach Ampere+). Cloud3090 potwierdził to samo na sm_86 i wykluczył też fold rotacji KV (`LLAMA_ATTN_ROT_DISABLE=1` po obu stronach nadal ≠) oraz robi per-node hash przez `llama-eval-callback`; na tej karcie zabrakło czasu na zejście niżej. Do naprawy przed produktem: przełącznik dla winnej łatki bez switcha + bramka KLD. **Plain A2 ≠ A1 to dziś prawdziwy dług poprawności na NVIDIA** (różnica rzędu kolejności sumowania, ale nie bitowa).

MTP (A2 vs A2-safe): md5 identyczne (5ff7869359bf) — przełączniki nie zmieniają wyjścia spekulacji. Profil NVIDIA (`GATE_UP_Q8=0`, `Q8_IDS=0`) i `GGML_CUDA_MMVQ_N1_ROWS=2` są **bitowo równe** forkowi (plain i MTP).

## 4. Tabele A0 / A1 / A2 / A2-safe

`spec_sweep` 6 promptów × 3 seedy (T=1, 400 tok), ABBA (A0 A1 A2 A2s A3 A3 A2s A2 A1 A0), mediana per prompt, średnia rund; prefill z `llama-bench` (r=5, ABCDDCBA, po 10 próbek). Surowe: `opt/sweep/spec_sweep.jsonl` (`main.*`), `lb/`.

**Qwen3.8-27B UD-Q3_K_XL (12.24 GiB, MTP w pliku)**

| tryb | decode t/s | ms/krok | tok/krok | akcept. | tg128 (llama-bench) | pp512 | pp4096 | md5 plain |
|---|---|---|---|---|---|---|---|---|
| A0 upstream `-m` | 28.04 | 35.66 | 1.00 | — | 28.75 | 1057.6 | 1043.3 | 33de84afe124 |
| A1 upstream + MTP | 37.25 | 68.36 | 2.55 | 0.392 | 28.58 | 1053.3 | 1038.4 | 33de84afe124 |
| A2-kod (fork, flagi A1) | 43.53 | 57.30 | 2.49 | 0.378 | 28.94 | 1049.6 | 1035.9 | 0e05ac358a1b |
| A2-safe | 41.88 | 59.49 | 2.49 | 0.378 | 29.29 | 1034.6 | 1021.1 | 0e05ac358a1b |
| **A2 (fork + draft vocab 64k + iq4_xs head)** | **50.94** (4 rundy) | **48.58** | 2.48 | 0.374 | — | — | — | MTP: 5ff7869359bf |
| A2 + profil NVIDIA | 51.67 | 47.92 | 2.48 | 0.374 | 29.63 | 1031.6 | — | = A2 |

**LFM2.5-24B-A2B Q4_K_M (13.53 GiB)**

| tryb | decode t/s | ms/token | tg128 | pp512 | pp4096 | md5 plain |
|---|---|---|---|---|---|---|
| A0 upstream `-m` | 147.63 | 6.77 | 198.36 | 4205.8 | 4223.8 | 317556627d00 |
| A1 upstream (q8_0 KV, FA, `-t 8`) | 144.46 | 6.92 | 196.68 | 4213.6 | 4203.6 | 317556627d00 |
| **A2 (fork, flagi A1)** | **189.08** (4 rundy) | 5.30 | 200.54 | 4245.0 | 4236.7 | 54d36afa388a |
| A2-safe | 146.75 | 6.81 | 195.26 | 4206.4 | 4199.8 | 54d36afa388a |
| A2 + profil NVIDIA | **207.81** | **4.81** | 211.07 | 4160.4 | — | = A2 |

Obserwacje:
- **Qwen**: z ms/krok 68.36 (A1) → 48.58 (A2): −29%; z tego build-only (A2-safe vs A1) 68.36 → 59.49, przełączniki 59.49 → 57.30, draft vocab + głowica iq4_xs 57.30 → 48.58. tok/krok prawie równe (2.55 vs 2.48) — zysk to koszt kroku, nie akceptacja.
- **LFM**: zysk A1 → A2 to +31% decode w serwerze, ale tylko +2% w `llama-bench` (kernele). Źródło to **sampler**: `LLAMA_SAMPLER_FAST_TOPK=0` → 207.7 → 165.5 t/s, `LLAMA_SAMPLER_FAST_PENALTIES=0` → 207.5 → 165.5 (GGUF LFM ma repeat_penalty 1.05, który w upstreamie wymusza pełne sortowanie 65k kandydatów na CPU). Ten zysk zależy od CPU hosta (tu 7.68 vCPU EPYC 7502).
- Prefill: fork ≈ upstream (±1%); A2-safe −1.6% w pp4096 Qwena.

**Pułapka upstream na 16 GB:** A1 z `-fit on` (jak w harnessie) dawał **7.7 t/s** (MTP wolniejsze od A0!): serwer 760% CPU, GPU 0–14%. Test 1 promptu: `-fit on -t 32` 6.3, `-t 8` 14.0, `-fit off -ngl 99 -t 8` **31.8 t/s**; `--backend-sampling` nie pomaga (14.5). Fork z `-fit on` nie ma problemu (45.5). Na 3090 (24 GB) Cloud3090 tego nie widzi → `-fit` przy ciasnym VRAM zostawia część pracy MTP na CPU. Dlatego A1 = `-fit off -ngl 99 -t 8`.

## 5. Przełączniki forka na sm_120

`llama-bench` tg128/pp512, on/off/off/on × r=3 (`opt/lb.jsonl`, `sw.*`), oraz serwer (`hsw.*`). Δ = off vs on; **ujemna = przełącznik pomaga**.

| przełącznik | LFM tg128 | Qwen tg128 | werdykt na 5060 Ti |
|---|---|---|---|
| `GGML_HIP_GATE_UP_Q8` | **+5.34%** | **+2.38%** | **szkodzi** → wyłączyć |
| `GGML_HIP_Q8_IDS` | **+4.99%** | — | **szkodzi** → wyłączyć |
| `GGML_HIP_ATTN_PREP` | −1.88% | +0.09% | pomaga (LFM) |
| `GGML_HIP_CONV_MUL` | −1.32% | — | pomaga |
| `GGML_HIP_NORM_FAST` | −1.11% | −0.65% | pomaga |
| `GGML_HIP_NORM_ROUTER` | −1.00% | — | pomaga |
| `GGML_HIP_INPROJ_CONV` | −0.78% | — | lekko pomaga |
| `GGML_HIP_MOE_DOWN_REDUCE` | −0.37% | −0.06% (kontrola) | neutralny |
| `GGML_HIP_MMVQ_PAIR` | −0.18% | −0.15% | neutralny |
| `GGML_HIP_GDN_CONV_AB` | −0.07% (kontrola) | −0.37% | neutralny |
| `GGML_HIP_NORM_GATE` | — | −0.15% | neutralny |
| `GGML_HIP_INPUT_BATCH` | +0.79% | +0.02% | neutralny |
| razem wszystkie GPU (`GPU_ALL`, serwer) | 208.2 → 197.2 t/s (−5.3%) | | pomagają razem |
| `LLAMA_SAMPLER_FAST_TOPK` (serwer) | 207.7 → 165.5 (−20%) | | **duży zysk** |
| `LLAMA_SAMPLER_FAST_PENALTIES` (serwer) | 207.5 → 165.5 (−20%) | | **duży zysk** |
| cały sampler (6 przełączników) | 208.4 → 166.6 | 59.25 → 58.31 (MTP, 200 tok) | |
| `LLAMA_ASYNC_INPUTS` (serwer) | 208.2 → 205.0 (−1.5%) | 59.12 → 59.22 | pomaga na LFM |
| `LLAMA_MTP_CHAIN_SCHED` | | 59.08 → 58.78 (−0.5%) | lekko pomaga |
| `LLAMA_GDN_REPLAY`, `LLAMA_CONV_LAG`, `LLAMA_KV_MASK_FAST`, `LLAMA_SPEC_LAZY_SAVE` | | ±0.1% | neutralne |

No-op na NVIDIA z kodu (bramka RDNA/HIP): `GGML_HIP_MMVQ_N1_ROWS`, `GGML_HIP_MMVQ_N1_Q8_0`, `GGML_HIP_MMQ_EPI`, `GGML_HIP_KVQ_Q8`, `GGML_HIP_KVQ_FWHT` (kvq tylko HIP), `GGML_HIP_CONV_ROWS4`, `GGML_HIP_PM4`; `GGML_HIP_ARGMAX_FAST` działa tylko przy greedy (llama-bench go nie woła). Rozrzut pp512 LFM w tym teście był 10–17% (szum), więc wnioski tylko z tg.

**Profil NVIDIA (sm_120)**: `GGML_HIP_GATE_UP_Q8=0 GGML_HIP_Q8_IDS=0` (Qwen: tylko `GATE_UP_Q8=0`) — bitowo równy forkowi. Weryfikacja ABBA: LFM tg128 200.20 → 211.07 (+5.4%), serwer 196.5 (rundy przeplecione) → 207.8 t/s (+5.8%); Qwen tg128 28.96 → 29.63 (+2.3%), serwer MTP 51.7 vs 51.6/51.8 (neutralnie). Obie łatki to „producent pisze q8_1 dla konsumenta + atomowy ticket”: na RDNA3 oszczędzały kernel, na NVIDIA (CUDA graphs + PDL, tani osobny `quantize_q8_1`) ticket/bariera kosztuje więcej niż zysk.

## 6. Co zoptymalizowałem (kod) i efekt

Gałąź `cuda-v070-5060ti` (`~/wt/5060ti-opt`), każdy commit z przełącznikiem:
1. `GGML_CUDA_MMVQ_N1_ROWS=2|4` — ścieżka „2/4 wiersze na warp” (bitowa) z RDNA3 udostępniona na NVIDIA dla Q4_K/Q5_K/Q6_K/Q8_0/Q4_0/Q3_K/IQ4_XS/IQ3_S/NVFP4, domyślnie wyłączona. md5 = fork (plain i MTP). **Wynik negatywny na sm_120**: LFM tg128 211.47 → 205.78 (−2.7%, ABBA 4+4), Qwen 29.69 → 29.18 (−1.7%). Na 3090 (sm_86) Cloud3090 zmierzył ten sam commit: **+8.4% LFM, +7.2% Qwen** → przełącznik ma sens tylko z predykatem per-arch (Ampere tak, Blackwell nie).
2. `GGML_HIP_GDN_L2`, `GGML_HIP_GDN_AB`, `GGML_HIP_Q8_PRODUCER` — kill-switche do bisekcji md5 (wynik w §3); domyślnie włączone, bez wpływu na szybkość.

Sprawdzone i odrzucone na tej karcie: `--backend-sampling`/`--spec-draft-backend-sampling` (upstream, +4%, nie rozwiązuje problemu `-fit`). Wartości `-t`: dla MTP upstream `-t 8` ≫ domyślne 32 (kontener).

## 7. Długi kontekst (llama-bench tg64 przy głębokości `-d`, base/fork ABBA, `-fa on`, KV q8_0)

| model | build | d=0 | 8k | 32k | 64k |
|---|---|---|---|---|---|
| Qwen3.8 Q3_K_XL | upstream | 28.2 | 27.2 | 23.6 | 20.1 |
| Qwen3.8 Q3_K_XL | fork | 28.9 | 27.6 | 23.9 | 20.2 |
| LFM2.5 Q4_K_M | upstream | 192.2 | 178.6 | 143.1 | 112.5 |
| LFM2.5 Q4_K_M | fork | 198.8 | 181.1 | 145.8 | 114.7 |

64k mieści się w 16 GB dla obu modeli (KV q8_0). Zysk forka maleje z długością (+2.5% → +0.5% Qwen, +3.4% → +2.0% LFM): przy długim kontekście dominuje FA, którego fork na NVIDIA nie zmienia (kvq jest tylko HIP). Prefill pp4096: tabela §4 (Qwen ~1040, LFM ~4220 t/s przy `-ub 512`).

## 8. Profil kroku dekodowania (nsys 2025.1.3, llama-bench tg64, `--cuda-graph-trace=node`)

Liczby na token = instancje / 65 (64 tokeny + rozgrzewka; przybliżenie). `opt/nsys.*_cuda_gpu_kern_sum.csv`.

| | kerneli/token | czas GPU/token | ściana (llama-bench) | luka host/launch | top kernele |
|---|---|---|---|---|---|
| LFM upstream | **908** | 5.52 ms | — | — | MMVQ Q4_K (×3 warianty) 66.8%, Q6_K 18.3%, quantize_q8_1 5.4% (181/tok), rms_norm 4.2%, router mul_mat_vec_f 2.9%, topk_moe 1.4% |
| LFM fork + profil | **435** | 4.79 ms | 5.53 ms (180.9 t/s pod profilerem) | ~0.74 ms (13%) | MMVQ Q4_K 55.9%, Q6_K 11.8%, `moe_down_reduce` Q6_K/Q4_K 18.2%, `norm_router_topk` 3.6%, quantize_q8_1 2.2% (89/tok), `rms_norm_mul_unrolled` 2.0%, `ssm_conv_fused` 1.5% |
| Qwen fork + profil | **837** | 34.24 ms | 35.3 ms (28.36 t/s) | ~1 ms (3%) | MMVQ IQ4_XS 35.9%, IQ3_S 29.3%, Q5_K 6.8%, IQ3_XXS 7.6%, IQ2_S 2.7%, Q4_K 4.8% |

Porównanie z XTX (NOTES.md): LFM na XTX ~721 kerneli/token, granica kernela 2.75 µs (graf HIP) / 0.46–0.86 µs (PM4), 3.40 ms/token. Na 5060 Ti fuzje forka **połowią liczbę kerneli (908 → 435)**, a luka host/launch to ~0.74 ms/token przy 435 kernelach (≈1.7 µs/kernel z CUDA graphs + PDL) — dlatego PM4-podobna sztuczka nie ma tu odpowiednika ani dużego pola. Qwen jest czysto ograniczony pasmem: 13.1 GB wag / 34.2 ms = **~383 GB/s ≈ 85% z 448 GB/s**; zostaje ~15% sufitu, wyłącznie w MMVQ typów IQ.

## 9. Strojenie konfiguracji (llama-bench, `opt/lb.jsonl` `tune.*`)

| pokrętło | Qwen | LFM | wniosek |
|---|---|---|---|
| `-ub` dla pp4096 (256/512/1024/2048) | 1018 / 1030 / **1043** / 1028 | 2781 / 4217 / 5737 / **6587** | **LFM: `-b 2048 -ub 2048` +56% prefill** (MoE: większy ubatch = mniej przejść po ekspertach); Qwen płasko |
| FA off/on (KV f16) | tg 28.8 / 29.1, pp512 1022 / 1027 | tg 194.8 / 199.5, pp512 4010 / 4146 | FA on |
| CUDA graphs off/on | 28.87 / 29.04 | 198.9 / 203.2 (+2.2%) | graphs on (domyślne) |
| `-t` 1/2/4/8/16 (tg, pełny offload) | 29.0 wszędzie | 203.1/200.1/199.4/202.6/200.0 | bez znaczenia w llama-bench; w serwerze MTP upstream z `-fit on` kluczowe (§4) |
| MTP `--spec-draft-n-max` 3/4/5 (fork+extras+profil, 2 seedy) | **52.81** / 51.67¹ / 48.79 t/s; tok/krok 2.45/2.48/2.51; akcept. 0.488/0.374/0.308 | — | n=3 ≥ n=4 (+2%¹), n=5 gorsze |

¹ n=4 z osobnej serii ABBA (3 seedy) — porównanie orientacyjne, nie przeplecione.

## 10. LFM2.5 Q5_K_M z offloadem ekspertów

Q5_K_M (15.86 GiB) nie mieści się w całości: `--n-cpu-moe 2/3/4` → OOM przy ładowaniu (`-ngl 999`, KV q8_0), **`--n-cpu-moe 6 -t 8`: tg128 120.9 t/s, pp512 2040 t/s** (1 przebieg, `opt/lb.jsonl` `q5.*`). Q4_K_M w całości na GPU: 211.1 t/s (profil) / pp512 4160. **Q4_K_M jest ~1.75× szybszy w dekodowaniu i 2× w prefillu**; Q5 daje lepszą jakość (KLD 0.124 vs 0.201, §11), ale na 16 GB nie opłaca się dla interaktywnego czatu.

## 11. Formaty FP4 / QAD — szybkość i jakość na tej karcie

Szybkość (llama-bench r=3 ×2, serwer ABBA 2 seedy, `fmt.*`); KLD vs Q8_0 tego samego modelu na tej karcie (`llama-perplexity` wikitext-2, ctx 512, 20 chunków; referencja z offloadem przez `-fit on`), `opt/kld.txt`.

| model / plik | GB | tg128 upstream → fork | pp512 / pp4096 (fork) | serwer A1 → A2 t/s | KLD | same top-p | PPL(Q)/PPL(Q8) | md5 plain base vs fork |
|---|---|---|---|---|---|---|---|---|
| Qwen UD-Q3_K_XL | 13.15 | 28.75 → 28.94 | 1050 / 1036 | 37.3 → 50.9 (MTP) | **0.0265** | 92.8% | 1.020 | różne (GDN) |
| Qwen NVFP4-MTP-VERY-LOW | 14.86 | 26.02 → 26.62 | **1730 / 1747** | A1 OOM¹; greedy MTP fork 54.0/34.9 | 0.0865 | 85.6% | 1.073 | różne (GDN) |
| LFM Q4_K_M | 14.53 | 198.4 → 200.5 | 4245 / 4237 | 144.5 → 189.1 (→ 207.8 profil) | 0.2008 | 79.8% | 0.968 | różne |
| LFM QAD-Q4_0 (Liquid, oficjalny) | 13.58 | 212.8 → **231.7** | 4494 / 4615 | 164.5 → **226.8** | 0.2029 | 79.2% | 0.869 | **identyczne** (6a26ac10f05a) |
| LFM NVFP4 (WhiskyAKM) | 13.58 | 197.9 → 201.8 | **7270 / 7663** | 156.0 → 198.0 | **1.1826** | 54.3% | 1.857 | **identyczne** (5866e6943e8b) |
| LFM Q5_K_M (offload `-ncmoe 6`) | 17.03 | — / 120.9 | 2040 / — | — | 0.1241 | 84.5% | 0.979 | — |

¹ upstream `-fit off -ngl 99` z 14.86 GB + MTP: OOM przy buforach obliczeniowych (260 MiB).

Wnioski:
- **Natywne FP4 tensor core działają w prefillu**: NVFP4 daje +65–69% (Qwen) i +71–81% (LFM) pp względem K-quantów. W dekodowaniu (MMVQ, batch 1) NVFP4 nie pomaga — decyduje liczba bajtów (Qwen NVFP4 jest większy od Q3_K_XL, więc wolniejszy).
- **Jakość dostępnych GGUF-ów NVFP4 jest słaba**: Qwen NVFP4 VERY-LOW ma 3.3× większy KLD niż UD-Q3_K_XL przy większym pliku; LFM NVFP4 (WhiskyAKM) jest praktycznie zepsuty (KLD 1.18, PPL ×1.86). Nie do produktu.
- **Najlepszy kompromis dla LFM na NVIDIA: oficjalny QAD-Q4_0** — KLD jak Q4_K_M (0.203 vs 0.201), lepszy PPL na wikitext, mniejszy plik, decode serwera **226.8 t/s** (fork, bez profilu; +38% vs upstream) i **bitowo zgodny z upstream** (ścieżka Q4_0 nie dotyka niebitowej łatki K-quant).
- Z md5: na Q4_0 i NVFP4 fork = upstream bitowo, na Q4_K_M nie → nieprzełączalna różnica LFM leży w ścieżce **K-quantów** (MMVQ/MMQ Q4_K/Q6_K) — to zawęża bisekcję z §3.

## 12. Koszt

Instancja `56178373`: 2026-10-16 00:57:43 → 06:12:06 UTC = **5.24 h × $0.1998/h (GPU + 150 GB dysku) ≈ $1.05**; transfer $0/TB (pobrano ~110 GB z HF). Limit karty $1.80 — nie przekroczony. Timery: watchdog lokalny i samozniszczenie przesunięte o +1 h o 04:47 UTC (GPU zajęte, saldo $7.89), niewykorzystane. Instancja zniszczona przez `down.sh`, `vastai show instances` jej nie pokazuje (saldo konta po zniszczeniu $7.40, wspólne z innymi kartami).

## 13. Rekomendacje dla produktu (RTX 5060 Ti / Blackwell sm_120)

1. **Łatki**: włączyć wszystkie fuzje forka **oprócz** `GGML_HIP_GATE_UP_Q8` i `GGML_HIP_Q8_IDS` (predykat `backend: cuda` → domyślnie 0; `runs/5060ti/profile-5060ti.env`). Sampler `LLAMA_SAMPLER_FAST_*` to największy pojedynczy zysk dla LFM (+25%). `GGML_CUDA_MMVQ_N1_ROWS` **wyłączony na sm_120** (na sm_86 włączyć — wynik Cloud3090).
2. **Flagi domyślne Qwen3.8-27B (UD-Q3_K_XL)**: `-fit off -ngl 99 -t <CPU> -fa on -ctk q8_0 -ctv q8_0 -c 32768 --spec-type draft-mtp --spec-draft-n-max 3 -ctkd q8_0 -ctvd q8_0 --spec-draft-vocab draft_vocab_qwen38.txt --spec-draft-vocab-n 65536 --spec-draft-head-type iq4_xs --spec-mtp-type iq4_xs`. **Nie używać `-fit on` z MTP na 16 GB**.
3. **Flagi domyślne LFM2.5-24B**: plik **QAD-Q4_0** (lub Q4_K_M), `-fit off -ngl 99 -fa on -ctk q8_0 -ctv q8_0 -b 2048 -ub 2048`, profil env z pkt 1. Q5_K_M z offloadem — nie (−43% decode).
4. **Przed produktem naprawić**: niebitowa łatka bez przełącznika w ścieżce K-quant + prolog GDN (§3) — dodać przełącznik, bramka KLD; do tego czasu twierdzenie „wynik identyczny z llama.cpp” jest prawdziwe tylko dla Q4_0/NVFP4.
5. **Co uczciwie napisać na landing page** (decode, czat 6 promptów × 3 seedy, T=1, ta sama karta i plik):
   - Qwen3.8-27B: „**28 → 51.7 tok/s (×1.84)** względem `llama-server -m`, **×1.38** względem najlepszych flag upstream (MTP)”; tylko tryb spekulacyjny, wynik nie jest bitowo identyczny z upstream (inny dobór tokenów przy T>0 jest i tak losowy; przy T=0 różnica numeryczna §3).
   - LFM2.5-24B (Q4_K_M): „**148 → 208 tok/s (×1.41)**, **×1.44** względem najlepszych flag upstream”; z QAD-Q4_0: „164.5 → 226.8 tok/s (×1.38), wynik identyczny z llama.cpp”.
   - Prefill: „do +56% szybsze przetwarzanie promptu dla LFM (`-ub 2048`)” — to flaga, nie łatka; uczciwie przypisać konfiguracji.
6. **Teza raportu 08 („na NVIDIA osiągalne tylko ~14–16% zysku z XTX”) — częściowo obalona**: kernelowo tak (llama-bench +1–2% fork, +5% z profilem; Qwen jest na 85% pasma), ale end-to-end w serwerze fork daje +31% (LFM) i +37% (Qwen MTP) nad upstream A1, bo zyski hosta (sampler, MTP draft vocab, koszt kroku spekulacji) nie zależą od GPU.

## 14. Wyniki negatywne

- `GGML_CUDA_MMVQ_N1_ROWS=2/4`: −2.7% / −15% LFM, −1.7% Qwen (bitowo OK) — Blackwell woli 1 wiersz/blok przy 4 warpach.
- `GGML_HIP_GATE_UP_Q8`, `GGML_HIP_Q8_IDS`: szkodzą na NVIDIA (§5).
- Upstream `--backend-sampling` / `--spec-draft-backend-sampling`: +4% w zepsutej konfiguracji `-fit on`, nie naprawia jej.
- NVFP4 GGUF-y społeczności: szybki prefill, zła jakość (§11).
- Pierwsza seria sweepów bench.sh (A1 z `-fit on`, domyślne wątki) odrzucona jako niereprezentatywna (7.7 t/s); zachowana w `sweep/spec_sweep.jsonl`.
- Incydent: nadpisanie `plan.sh` podczas działania (`scp` na ten sam i-węzeł) przerwało fazę `hostsw` Qwena po 2 przełącznikach; powtórzona w `plan2.sh hostspec`. Nauczka: nowe pliki zamiast nadpisywania działających skryptów.

## 15. Karta wyniku dla aplikacji

Źródło: `results/5060ti-20261016/scorecard.json` (generator `runs/5060ti/scorecard.py`, specyfikacja `scorecard-spec.json`). Decode = mediana z t/s per prompt (każdy = średnia 3 seedów) ze wszystkich rund ABBA, w nawiasie min–max; prefill z llama-bench; TTFT = mediana 3 żądań z promptem 2016–2030 tokenów (`cache_prompt=false`, max_tokens=1) na świeżym serwerze, rundy A0 A1 OURS OURS A1 A0; VRAM z `nvidia-smi` po załadowaniu. Tokeny/słowo zmierzone tokenizerem modelu na stałym akapicie: Qwen EN 1.13 / PL 2.41, LFM EN 1.16 / PL 2.50 (zamiast założonych 1.17 / 2.69). „Czas odpowiedzi 500 słów” = sam decode (bez TTFT). Ollama nie mierzona. TTFT/VRAM profilu NVIDIA = kolumna A2 (profil nie zmienia prefillu ani pamięci). Profil NVIDIA dla Qwena zawiera MTP n=4 (n=3 dałoby ~+2%, §9).

### qwen38-27b-q3

| | A0 typowa aplikacja | A1 najlepsze flagi upstream | A2 nasz silnik (fork + draft vocab) | nasz profil NVIDIA (A2 + GATE_UP_Q8=0) |
|---|---|---|---|---|
| decode t/s (mediana [min–max]) | 28.07 [27.85–28.1] | 37.32 [33.97–42.84] | 50.8 [48.24–59.92] | 51.66 [49.64–59.88] |
| tok/krok | 1.0 | 2.55 | 2.48 | 2.48 |
| prefill t/s pp512 / pp4096 | 1048.2 / 1043.8 | 1040.8 / 1038.3 | 1040.8 / 1035.9 | 1031.6 / — |
| TTFT ~2k tokenów (ms) | 2421 | 2690 | 2707 | 2707 |
| czas odpowiedzi 500 słów EN | 20.2 s | 15.2 s | 11.2 s | 11.0 s |
| słowa/s EN | 24.7 | 32.9 | 44.8 | 45.5 |
| czas odpowiedzi 500 słów PL | 42.9 s | 32.3 s | 23.7 s | 23.3 s |
| słowa/s PL | 11.6 | 15.5 | 21.1 | 21.4 |
| VRAM (GiB) | 13.92 | 14.27 | 14.47 | 14.47 |
| md5 | referencja upstream (plain) | plain = upstream (A0 nie porównywane: inny KV) | plain ≠ A1 (DIFF-BUILD, łatki bez przełącznika) | = A2 (bitowo) |
| przebiegi (rundy×6 promptów×seedy) | 36 | 36 | 72 | 36 |

×speedup A0 typowa aplikacja→nasz profil NVIDIA (A2 + GATE_UP_Q8=0): **1.84×**; ×speedup A1 najlepsze flagi upstream→nasz profil NVIDIA (A2 + GATE_UP_Q8=0): **1.38×**

### lfm25-24b-q4

| | A0 typowa aplikacja | A1 najlepsze flagi upstream | A2 nasz silnik | nasz profil NVIDIA (A2 + GATE_UP_Q8=0 Q8_IDS=0) |
|---|---|---|---|---|
| decode t/s (mediana [min–max]) | 147.69 [146.53–150.16] | 144.47 [139.95–146.6] | 190.99 [178.06–197.21] | 207.86 [206.69–209.14] |
| tok/krok | 1.0 | 1.0 | 1.0 | 1.0 |
| prefill t/s pp512 / pp4096 | 4147.8 / 4220.5 | 4162.3 / 4209.7 | 4146.1 / 4235.4 | 4160.4 / — |
| TTFT ~2k tokenów (ms) | 547 | 538 | 530 | 530 |
| czas odpowiedzi 500 słów EN | 3.9 s | 4.0 s | 3.0 s | 2.8 s |
| słowa/s EN | 126.9 | 124.2 | 164.2 | 178.7 |
| czas odpowiedzi 500 słów PL | 8.5 s | 8.7 s | 6.5 s | 6.0 s |
| słowa/s PL | 59.1 | 57.8 | 76.4 | 83.1 |
| VRAM (GiB) | 14.54 | 14.18 | 14.19 | 14.19 |
| md5 | referencja upstream (plain) | plain = upstream (A0 nie porównywane: inny KV) | plain ≠ A1 (DIFF-BUILD, łatki bez przełącznika) | = A2 (bitowo) |
| przebiegi (rundy×6 promptów×seedy) | 36 | 36 | 72 | 36 |

×speedup A0 typowa aplikacja→nasz profil NVIDIA (A2 + GATE_UP_Q8=0 Q8_IDS=0): **1.41×**; ×speedup A1 najlepsze flagi upstream→nasz profil NVIDIA (A2 + GATE_UP_Q8=0 Q8_IDS=0): **1.44×**

Z czego bierze się zysk (A0 → nasz):
- **Qwen3.8**: flagi upstream (MTP + `-fit off -ngl 99 -t 8`) 28.07 → 37.32 (×1.33); nasze łatki (build-only + przełączniki) 37.32 → 43.5 (×1.17); draft vocab 64k + głowica iq4_xs 43.5 → 50.8 (×1.17); profil NVIDIA 50.8 → 51.7 (×1.02).
- **LFM2.5**: flagi upstream nic nie dają (A1 144.5 < A0 147.7: q8_0 KV); cały zysk to łatki: sampler fast top-k (~+25%), fuzje GPU (+5%), profil NVIDIA (+5–6%).

## Formaty „zoptymalizowane pod NVIDIA” (NVFP4 / MXFP4 / FP8) — research

Stan na 2026-10-16 (HF API, rewizje przypięte w `runs/5060ti/models.tsv`).

**Qwen3.8-27B**
| repo | format | rozmiar | runtime | mieści się w 16 GB? |
|---|---|---|---|---|
| [nvidia/Qwen3.8-27B-NVFP4](https://huggingface.co/nvidia/Qwen3.8-27B-NVFP4) | ModelOpt, mieszane NVFP4 (MLP, lm_head) + FP8 (attention, linear-attention), safetensors | 21.9 GB | vLLM / SGLang, testowane na GB300 | **nie** |
| [unsloth/Qwen3.8-27B-NVFP4](https://huggingface.co/unsloth/Qwen3.8-27B-NVFP4) | NVFP4 safetensors + osobny `model_mtp.safetensors` | 22.6 + 0.85 GB | vLLM | **nie** |
| [Qwen/Qwen3.8-27B-FP8](https://huggingface.co/Qwen/Qwen3.8-27B-FP8) | FP8 safetensors | 30.9 GB | vLLM / SGLang / TRT-LLM | **nie** |
| [amd/Qwen3.8-27B-Quark-AWQ-MXFP4](https://huggingface.co/amd/Qwen3.8-27B-Quark-AWQ-MXFP4) | Quark MXFP4 safetensors (AMD) | 19.8 GB | vLLM (ROCm) | **nie** |
| [esatapedico/Qwen3.8-27B-NVFP4-MTP-GGUF](https://huggingface.co/esatapedico/Qwen3.8-27B-NVFP4-MTP-GGUF) | **GGUF NVFP4 z głowicą MTP**, warianty 14.9–33 GB | VERY-LOW 14.86 GB | llama.cpp | **tak (VERY-LOW)** — zmierzony |
| [cdiamond/Qwen3.8-27B-iMatrix-NVFP4-MTP-GGUF](https://huggingface.co/cdiamond/Qwen3.8-27B-iMatrix-NVFP4-MTP-GGUF) | GGUF NVFP4 + MTP, imatrix | 17.1 GB | llama.cpp | nie (tylko z offloadem) |

Zmierzony plik `Qwen3.8-27B-NVFP4-MTP-VERY-LOW.gguf`: 448 tensorów NVFP4 (13.7 GB), `token_embd` i `nextn.eh_proj` Q2_K, `output` Q3_K, `nextn_predict_layers=1`. Czyli NVFP4 „na wszystkim”, ale z bardzo słabą głowicą wyjściową — porównanie jakości tylko przez KLD.

**LFM2.5-24B-A2B**
| repo | format | rozmiar | runtime | 16 GB? |
|---|---|---|---|---|
| [LiquidAI/LFM2.5-24B-A2B-FP8](https://huggingface.co/LiquidAI/LFM2.5-24B-A2B-FP8) | oficjalny FP8, safetensors | 24.8 GB | transformers / vLLM | nie |
| [LiquidAI/LFM2.5-24B-A2B-GGUF](https://huggingface.co/LiquidAI/LFM2.5-24B-A2B-GGUF) `QAD-Q4_0` | **oficjalny Q4_0 po quantization-aware distillation** | 13.58 GB | llama.cpp | **tak** — zmierzony |
| [WhiskyAKM/LFM2.5-24B-A2B-NVFP4-GGUF](https://huggingface.co/WhiskyAKM/LFM2.5-24B-A2B-NVFP4-GGUF) | GGUF NVFP4 (imatrix), `token_embd` Q6_K | 13.58 GB | llama.cpp | **tak** — zmierzony |
| [kaushikvira/LFM2.5-24B-A2B-nvfp4-gguf](https://huggingface.co/kaushikvira/LFM2.5-24B-A2B-nvfp4-gguf) | GGUF NVFP4 bez imatrix, 0 pobrań | 13.64 GB | llama.cpp | tak (pominięty, duplikat bez imatrix) |
| [FP8Enjoyer/LFM2.5-24B-A2B-MXFP4](https://huggingface.co/FP8Enjoyer/LFM2.5-24B-A2B-MXFP4), `cloudnathan5/…-NVFP4-W4A4`, `primitive-ai/…-NVFP4A16`, `mlx-community/…` | safetensors (vLLM/compressed-tensors) lub MLX | 13–14 GB | vLLM / MLX | — (nie llama.cpp) |

Organizacja `nvidia/` **nie publikuje** wariantu LFM2.5; dla Qwen3.8-27B publikuje tylko checkpoint ModelOpt pod vLLM/SGLang (21.9 GB, nie mieści się w 16 GB i nie ma GGUF).

**Wsparcie w llama.cpp v0.7.0 na sm_120** (sprawdzone w źródle tagu):
- typy `GGML_TYPE_MXFP4` (39) i `GGML_TYPE_NVFP4` (40) są w ggml; CMake zamienia `120` na `120a`, bo instrukcje FP4 tensor core nie są forward-compatible (`ggml/src/ggml-cuda/CMakeLists.txt`);
- **natywne FP4 MMA tylko w prefillu (MMQ)**: `mmq.cu` wybiera `GGML_PREC_Q4` (aktywacje kwantyzowane do FP4, ścieżka W4A4) dla NVFP4/MXFP4, gdy `blackwell_mma_available(cc)`; inaczej W4A8 (aktywacje q8_1). Historia: natywne MXFP4 na Blackwell — [PR #17906](https://github.com/ggml-org/llama.cpp/pull/17906); akumulacja NVFP4 w MMQ — [PR #29857](https://github.com/ggml-org/llama.cpp/pull/29857); wymuszenie W4A8 dla warstw NVFP4_W4A16 — [PR #24364](https://github.com/ggml-org/llama.cpp/pull/24364); kwantyzacja NVFP4 w llama-quantize — [PR #26556](https://github.com/ggml-org/llama.cpp/pull/26556);
- **dekodowanie (1 token) idzie przez MMVQ (dp4a, bez tensor core)** — dla FP4 liczy się tylko liczba bajtów wag (NVFP4 = 4.5 b/wagę, tyle co Q4_0), nie FP4 TC.

Ścieżka „prawdziwie NVIDIA” (TensorRT-LLM / vLLM + ModelOpt NVFP4) na tej karcie: Qwen3.8-27B NVFP4 nie mieści się (21.9 GB > 16 GB). Dla LFM2.5 checkpointy NVFP4 13–14 GB zmieściłyby się, ale wymagają: vLLM ≥ z obsługą `lfm2_moe` + compressed-tensors NVFP4 na sm_120 (kernele CUTLASS FP4 dla GeForce Blackwell), osobnego obrazu (~10 GB), ~1–2 h integracji i innej ścieżki produktu (Python/vLLM zamiast jednego binarnego llama-server). `[SZACUNEK]`: zysk głównie w prefillu i przy batchu > 1; dla jednego użytkownika (decode, batch 1) ograniczeniem jest pasmo 448 GB/s, więc 4.5-bitowe wagi dają ten sam sufit co Q4_0/NVFP4 GGUF.
