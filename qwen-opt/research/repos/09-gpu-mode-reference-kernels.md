# 09 — gpu-mode/reference-kernels

Repo: https://github.com/gpu-mode/reference-kernels (płytki klon, commit `f3295bb6`, 2026-09-17).
Zwycięskie rozwiązania nie leżą w repo. Czytałem je z zewnątrz:
- RadeonFlow, grand prize AMD 2025: https://github.com/RadeonFlow/RadeonFlow_Kernels (`TechnicalReport.md`);
- seb-v FP8 GEMM: https://github.com/seb-v/amd_challenge_solutions (`fp8_gemm/fp8_gemm.md`, `gemm_fp8.cpp`);
- Akash Karnatak FP8 GEMM: https://akashkarnatak.github.io/amd-challenge;
- blog seb-v o GEMM na **7900 XTX**: https://seb-v.github.io/optimization/update/2025/01/20/Fast-GPU-Matrix-multiplication.html;
- najlepsze zgłoszenia konkursu AMD z 2026 (MI355X) z publicznego zbioru `GPUMODE/kernelbot-data` (HF, konfiguracja `amd_1_1m_competition`, tryb leaderboard, sortowanie po wyniku). Przejrzałem 1.–3. miejsce w `amd-mxfp4-mm`, `amd-mixed-mla` i `amd-moe-mxfp4`.

## 1. Co to jest

Repo zawiera **definicje zadań i harness oceny** dla KernelBota GPU MODE: `reference.py` (wzorzec w PyTorch), `task.yml` (kształty, tolerancje, tabela „speed of light”) oraz `eval.py` (pomiar i sprawdzanie poprawności). Sam kod w repo to tylko wzorce w PyTorch/aiter, bez szybkich kerneli.

Zadania AMD:
- `problems/amd` (2025, MI300X): FP8 blockwise GEMM, MoE, MLA decode;
- `problems/amd_202602` (2026, MI355X): MXFP4 GEMM, MXFP4 MoE, mixed-precision MLA;
- `amd_distributed`: all2all, GEMM-RS, AG-GEMM;
- pokrewne: zadania Helion (B200) z **Gated DeltaNet chunked** i causal_conv1d.

Repo jest aktywne. Licencja to własna „June 9 Researcher Reciprocity License” na bazie Open RAIL-S (`README.md:35-41`). RadeonFlow ma licencję MIT.

## 2. Kluczowe techniki (z dowodami)

### 2a. Z samego repo: zadania i harness

| Co | Dowód | Uwagi |
|---|---|---|
| Tabele SoL (roofline) w opisie zadania, ranking geomean | `amd/fp8-mm/task.yml:33-44`, `amd/mla-decode/task.yml:48-55`, `ranking_by: "geom"` | Przykład: MLA bs128, kv6144, bf16 = 280.87 µs na MI300X (liczby organizatorów) |
| Harness 2025 mierzy zegarem CPU (`perf_counter_ns` + `synchronize`), **bez czyszczenia cache** | `amd/eval.py:231-235` | Wynik zawiera narzut uruchomienia z Pythona. Dane wejściowe są te same w każdej iteracji (poza trybem leaderboard), więc wagi mogą siedzieć w 256 MB Infinity Cache MI300X |
| Harness 2026 mierzy eventami GPU i przed każdą iteracją czyści cache tensorem 16000×1024×1024 fp32 (64 GB) | `amd_202602/eval.py:234-249`, `amd_202602/utils.py:173-175` | Bufor jest dużo większy niż MALL, więc pomiar idzie „na zimno” |
| Anty-cache i anty-cheat: tajne ziarno łączone funkcją Cantora, w trybie leaderboard nowe dane i sprawdzenie w każdej iteracji | `amd_202602/eval.py:47-55,89-92,227-246,367` | |
| Tolerancje: FP8 GEMM `rtol=2e-2, atol=1e-3`; MLA dopuszcza **do 5% elementów poza tolerancją** | `amd/fp8-mm/reference.py:88`, `amd_202602/utils.py:146-160` | Luźne kryterium MLA pozwala na fp8/fp4 KV |
| Quirk: MoE 2026 nie klonuje wejść, bo „aiter fused_moe produces incorrect results when weight tensors are cloned to different memory addresses” | diff `amd_202602/moe-mxfp4/eval.py` vs `amd_202602/eval.py` (`_clone_data`) | Zdradza, że aiter cache'uje coś po adresie wag |
| Wskazówki organizatorów dla MLA (MQA 16:1, 576 = K, 512 = V) | `amd_202602/mixed-mla/README.md:343-373` | (A) dequant KV w rejestrach lub LDS sklejony z atencją; (B) **kwantyzacja Q do precyzji KV i QK^T w niskiej precyzji na matrix cores**; KV ładowane raz dla wszystkich 16 głów; split-K/split-batch; osobne kafle dla 576 (K) i 512 (V) |
| Wskazówki organizatorów dla MoE | `amd_202602/moe-mxfp4/README.md:557-578` | Kwantyzacja aktywacji w prologu GEMM; fuzja gate_up→SwiGLU→down; kompaktowy dispatch ekspertów; shared expert jako gęsty GEMM; split-K dla dużego M |
| Rozkład GDN chunked na trzy kernele (BT=64) z wzorcami w PyTorch | `helion/gated_deltanet_recompute_w_u_py/task.yml`, `..._chunk_fwd_h_py/task.yml`, `..._chunk_fwd_o_py/task.yml` | `h` to stan [K,V] między chunkami; `v_new = u - w@h`; bramka `exp(g_last - g)` |

### 2b. Ze zwycięskich rozwiązań i write-upów (MI300X, CDNA3)

| Technika | Źródło | Liczby (czyje) |
|---|---|---|
| FP8 GEMM: kafel LDS 128×128 (= blok skali), MFMA 16x16x32 fp8, 8 fal na grupę 2×4, każda fala liczy 8 kafli 16×16 | `fp8_gemm.md:18-38` (seb-v) | — |
| **Transpozycja 8×8 w obrębie jednego wątku** (kompilator generuje SDWA) zamiast `ds_permute` lub DPP: obie wersje między lane'ami miały za dużą latencję | `fp8_gemm.md:60-68,116-119` | — |
| Swizzle XOR zamiast paddingu: `col_sw = ((col/2) ^ (row%8))*2 + col%2` | `fp8_gemm.md:96-100`, `gemm_fp8.cpp:57-58,111` | bez konfliktów banków (autor) |
| Podział ładowań: 4 fale ładują A, 4 fale ładują B. Dzięki temu kernel mieści się w <128 VGPR (4 fale/SIMD), a wszystkie `global_load_dwordx2` idą w locie bez `s_waitcnt` | `fp8_gemm.md:70-76` | — |
| Split-K przez `atomicAdd` do bufora fp32. Wariant `global_atomic_pk_add_bf16` nie przeszedł testu dokładności | `fp8_gemm.md:103-113`, `gemm_fp8.cpp:216` | — |
| Double buffering **nic nie dał** przy wysokim obłożeniu | `fp8_gemm.md:116-117` | — |
| Kernele trwałe: 304 bloki (= liczba CU), kolejność kolumnowa (lepszy hit rate), stream-K tylko dla części kształtów, bo poprawny stream-K wymaga bufora fp32 | Akash, blog („streamk”, „precision challenge”) | — |
| Swizzle dwupoziomowy z 8-bajtowym wyrównaniem (zostaje ~2-way konflikt). Wersja 4-bajtowa jest bez konfliktów, ale kompilator emituje `ds_read2_b32` zamiast `ds_read_b64` i zysk znika | Akash, blog | — |
| RadeonFlow GEMM: transpozycja wejść dla L2, paczkowane ładowania GDS→LDS, padding LDS, split-K, pipelining, szybkie f32→bf16, swizzle bloków | `TechnicalReport.md:9-17` | 360 TFLOPS geomean na MI300X (pomiar autorów, `README` RadeonFlow) |
| RadeonFlow MoE: sortowanie (ekspert, token) przez hipCUB, grouped GEMM z hipBLASLt ze **sztywno ustawionym indeksem algorytmu** | `TechnicalReport.md:39-55` | — |
| RadeonFlow MLA **w PyTorch**: absorpcja macierzy (łączność mnożenia), `torch.compile`, CUDA graph. Kernele trwały ~5 µs, a narzut uruchomień ~170 µs | `TechnicalReport.md:62-100` | (autorzy) Zadanie wygrał narzut uruchomień, nie kernel |
| **mxfp4-mm 2026, 1. miejsce (4.35 µs geomean)**: własna kolejka HSA i ręczne pakiety AQL z `ctypes` zamiast `hipModuleLaunchKernel`; `HIP_FORCE_DEV_KERNARG=1`; split-K wyłączony | kod `bhagawan-yantrion` (kernelbot-data, id 728835): komentarz „With AQL dispatch (~1.5 µs), sk=1 is faster than sk=8 + reduce (~7 µs HIP overhead)” | Kolejne miejsca mają 7.6–8.0 µs przy referencji aiter ok. 8–21 µs (`amd_202602/mxfp4-mm/task.yml:34-42`). Czołówka „na zwykłym HIP” utknęła na progu narzutu |
| mxfp4-mm, 2. miejsce: Triton aiter z modyfikacjami. Kwantyzacja A w kernelu GEMM (`PREQUANT`); wagi `.cg`, aktywacje `.ca`, wynik `.wt`; remap XCD; `waves_per_eu` i split-K dobrane per kształt | kod `josusanmartin` (id 732442), linie 138-221, 423-470 | — |
| **mixed-mla 2026, 1. miejsce (8.0 µs geomean; 2. miejsce 14.5 µs)**: w trybie leaderboard zwraca „analityczne przybliżenie dla rozkładu ewaluacji”. Przy losowym KV wynik atencji jest bliski zera/średniej V i przechodzi luźną tolerancję MLA. Poza tym: cache Q-fp8 po `id(tensor)` i `_version`, cache metadanych aiter per kształt | kod `Amo-Zeng` (id 754087), linie 326-345, 584-597, 887-895 | **Exploit harnessu, nie technika** |
| mixed-mla, 2. miejsce: aiter `mla_decode_fwd` (a8w8, persistent). `num_kv_splits` 8/16 zależnie od długości. Dla bs≤32 i kv=1024 ścieżka bf16 bez kwantyzacji Q i bez metadanych persistent. Kwantyzacja Q do fp8 jednym kernelem Triton (amax + scale) | kod `Barry_zhang` (id 753797), linie 42-60, 96-122, 166 | Lekcja: dla małych problemów pominąć przygotowanie (quant, metadane), bo kosztuje więcej, niż daje |
| moe-mxfp4 2026, 1.–2. miejsce (69.9 / 70.6 µs geomean): w trakcie ewaluacji klonują nowsze aiter z GitHuba, łatają `fused_moe.py` (`split_k=2`, kernele FlyDSL stage1/2), rozgrzewają kompilację. Do tego zmienne środowiskowe: `HIP_FORCE_DEV_KERNARG=1`, `AMD_DIRECT_DISPATCH=1`, `GPU_MAX_HW_QUEUES=8`, `HSA_ENABLE_SDMA=0`, `HSA_ENABLE_INTERRUPT=0` | kod `Danishlynx` (id 745202) linie 10-18, 113-191; `Hamza` (id 749286) linia 16 | Brak własnego kernela, tylko dobór wersji biblioteki i strojenie runtime'u |

### 2c. seb-v na RDNA3 (7900 XTX), poza repo, ale ten sam autor i ten sam sprzęt co nasz

FP32 SGEMM 4096³ osiąga 49 TFLOPS i jest o 60% szybszy od rocBLAS (pomiar autora, ROCm 6.2.4, Windows).

Najważniejsze obserwacje:
- **`v_dual_fmac_f32` i banki VGPR.** Rejestr X leży w banku X%4. Źródła OPX i OPY muszą być w różnych bankach, a cele mają parzystość parzysty/nieparzysty. rocBLAS w ogóle nie używał dual-issue.
- **`-mcumode`.** HIP domyślnie kompiluje w trybie WGP: jedna duża LDS na WGP, więcej rywalizacji. Tryb CU dzieli LDS na połówki per CU.
- **Bez `__launch_bounds__` kompilator wyrzucał rejestry do scratch.** Double buffering spowolnił wtedy kernel 2.6× (14.3 vs 5.4 ms).
- **Adresy globalne w SGPR (16 baz) + jeden offset w VGPR.** Usuwa obliczanie adresu na VALU przy każdym `global_load`.
- **Rozłożenie 16 ładowań na paczki po 2 w pętli.** Mniej fal na tym samym SIMD jednocześnie czeka na pamięć. Wynik: 41.3 → 49.0 TFLOPS.

## 3. Przeniesienie na AMD/HIP/RDNA3 (gfx1100)

| Technika | Przenosi się? | Jak / dlaczego nie |
|---|---|---|
| MFMA 16x16x32 fp8, MXFP4 MFMA, sparse MFMA | **Nie** | gfx1100 ma tylko WMMA 16x16x16 f16/bf16/iu8, bez FP8 i bez sparsity. Odpowiednikiem fp8/fp4 jest u nas int8 (q8_0 / q8_1) przez `v_wmma_i32_16x16x16_iu8` |
| Strategia B dla MLA („Q do precyzji KV, QK^T na matrix cores”) | **Tak, jako iu8** | Q → int8 per blok 32 (to już robimy dla ścieżki vec: q8_1 dla FA Q). K q8_0 idzie bez dequantu prosto do WMMA iu8. q4_0 też: rozpakowanie nibble → int8 to `v_perm`/`and`, a offset −8 rozlicza suma Q (jak człon `ds.y` w MMQ). Zob. pomysł P1 |
| MQA: KV czytane raz dla wszystkich głów Q | Już mamy (fattn-kvq q4_0) | Brakuje instancji q8_0 (`lfm-decode-round2.md:87-101`) |
| Swizzle XOR i transpozycja w wątku zamiast między lane'ami | Tak | LDS na RDNA3 ma 64 banki × DWORD (seb-v). Transpozycja w rejestrach jednego wątku przez `v_perm_b32` lub SDWA jest tańsza niż `ds_bpermute`, co zgadza się z naszymi doświadczeniami z DPP (K2). Na gfx11 operacja między połówkami fali jest tania (`v_permlanex16`), ale wymiana między lane'ami w pełnej fali nadal kosztuje |
| Split-K przez bufor fp32 i ostatni blok | Mamy (ticket „ostatni blok”) | Lekcja z obu GEMM-ów: atomiki bf16 psują dokładność. U nas i tak chcemy wyników bitowo identycznych |
| Stream-K / kernele trwałe | Częściowo | Kod jest w ggml (`mmq.cuh:952-1475`), ale **wszystkie 243 konfiguracje RDNA3 mają `stream_k=false`** (`mmq-config-rdna3.cuh`), a gałąź „tiles, jeśli efektywność ≥90%” działa tylko na NVIDIA (`mmq.cuh:1445`). Akash i moonmath włączają stream-K / ogonowy split tylko dla ogona fali, sterowane modelem kosztu |
| Kernele trwałe ze spinem zamiast granic | U nas **nie** dla dużych faz | `lfm-decode-round2.md:33-41` mierzy 8–11 µs/fazę przy 1024 blokach. Zostaje tylko mała siatka trwała |
| Bezpośredni dispatch AQL zamiast HIP | Badawczo | W HIP graph granica kernela kosztuje u nas 2.53 µs (`lfm-decode-round2.md:27`). Zwycięzca twierdzi, że AQL kosztuje ~1.5 µs, ale to jego pomiar w harnessie z Pythonem, więc liczby nie da się wprost porównać. Mechanizm: bit barrier oraz zakres fence acquire/release (AGENT vs SYSTEM) w nagłówku pakietu (`_mkhdr` w zgłoszeniu). `HIP_FORCE_DEV_KERNARG` już testowaliśmy, dał szum (`NOTES.md:101`) |
| `-mcumode`, `v_dual_fmac`, `__launch_bounds__` przeciw scratch, bazy w SGPR | Tak, natywnie RDNA3 | Bazy w SGPR mamy (K1: buffer resource + offsety 32-bit). `waves_per_eu` też mamy. **cumode nie był testowany**: brak w `ggml-hip/CMakeLists.txt` i w notatkach |
| Absorpcja MLA, grouped GEMM z hipBLASLt | Nie dotyczy | Nasze modele nie mają MLA. MoE w decode to u nas MMVQ_id, a nie GEMM |
| `.cg` (wagi strumieniowo) i `.wt` (store write-through) | Mamy | Wagi z GLC\|DLC (K1). Store `.wt` niczego nie zmieni [WNIOSEK] |

## 4. Pomysły dla nas

**P1. FA kvq z KQ na `v_wmma_i32_16x16x16_iu8` (q8_0, potem q4_0). Priorytet: LFM KV q8_0 przy długim kontekście.**
- **Co.** Nowa instancja `fattn-kvq` dla q8_0. K wchodzi do fragmentu A bez dequantu (bajty int8 wprost). Q jest już w q8_1 (ścieżka FA Q z S1), więc wchodzi do B. Akumulator int32 na blok 32 to dwa WMMA. Potem `KQ += float(acc) * d_k[r] * d_q[c]`. Część V zostaje jak w kernelu q4_0 (dequant do f16, transpozycja w LDS).
- **Dlaczego to lepsze niż „kvq q8_0 z dequantem do f16”.** Iloczyny K·Q są **całkowite, więc dokładne**, jak dp4a w `flash_attn_ext_vec`. Numerycznie bliżej obecnego kernela vec niż wersja f16, co dotyka obaw z `lfm-decode-round2.md:95-101` [WNIOSEK]. Znika też ok. 1 FMA/cvt na każdy element K na VALU, a iu8 WMMA ma 2× przepustowość f16 na gfx1100.
- **Zysk [SZACUNEK].** Bazowo kvq q8_0 daje −1.1 ms/token przy 98k (`round2`, przy ~640 GB/s). Wersja iu8 może dobić do ~750–800 GB/s, czyli dodatkowe ~0.2–0.3 ms przy 98k. Przy 0–8k pomijalnie. Dla Qwen q4_0 to samo zmniejsza VALU w KQ, ale tam FA nie dominuje.
- **Koszt i ryzyko.** 3–5 dni (szablon 0011 + układ fragmentów iu8 na gfx11: dwa zestawy B w połówkach fali, jak w opisie 0011:48-56). Ryzyko: bitowej zgodności z vec nie będzie, bo inna kolejność sum bloków w f32. Mierzyć KLD jak przy A4.
- **Pomiar.** llama-bench tg128 d0/8k/32k/98k, KV q8_0, A/B. Do tego `test-backend-ops -o FLASH_ATTN_EXT` i logit hash.

**P2. `-mcumode` dla całego ggml-hip (eksperyment za jedną flagę).**
- **Co.** Dodać `-mcumode` do flag HIP (lub `__attribute__((target("cumode")))` per kernel, jeśli clang na to pozwala [WNIOSEK]).
- **Uzasadnienie.** W trybie CU fale bloku siedzą na jednym CU. Współdzielą jego L0 i połówkę LDS, a fence'y w obrębie grupy roboczej nie muszą utrzymywać spójności dwóch L0 [WNIOSEK]. Dla MMVQ (aktywacja y czytana przez wszystkie fale bloku) i FA (wspólne kafle LDS) może to dać lepszą lokalność. Dla MMQ może wzrosnąć rywalizacja o mniejszą liczbę SIMD na blok.
- **Zysk [SZACUNEK].** −3%…+3% na poszczególnych kernelach. Nieznany kierunek, ale pomiar jest tani. Wynik powinien być bitowo identyczny, bo matematyka się nie zmienia [WNIOSEK].
- **Koszt.** Przebudowa i A/B (kbench + spec_sweep + pp4096). Ryzyko niskie.

**P3. Audyt ISA kerneli ciężkich na FMA f32 pod `v_dual_fmac` i scratch.**
- **Które kernele.** GDN (decode, replay S4, prefill z rekurencją w rejestrach), softmax FA, GDN conv.
- **Co sprawdzić.** Udział `v_dual_*` w pętli głównej, `scratch_`/`private_segment_size` > 0 oraz konflikty banków VGPR (reguły z blogu seb-v).
- **Zysk [SZACUNEK].** Jeśli prefill GDN jest ograniczony przez VALU, nawet 10–30% tego kernela. Jeśli nie, zero. Koszt: pół dnia na analizę ISA (`--save-temps`), bez GPU. Ryzyko zerowe.

**P4. Pomiar kosztu granicy kernela na poziomie AQL (outside the box).**
- **Co.** Rozszerzyć `launch_cost.hip` o wariant z własną kolejką HSA: 500 zależnych pakietów, `barrier=1`, acquire/release kolejno SYSTEM/AGENT/NONE. Porównać z 2.53 µs w HIP graph. Równolegle `AMD_LOG_LEVEL=4` na krótkim grafie, żeby zobaczyć, jakie nagłówki i fence'y emituje rocclr dla węzłów grafu.
- **Decyzja.** Jeśli AGENT-scope zejdzie np. do ~1.5 µs, LFM ma 416 granic/token. To ~0.4 ms/token, ok. 10% [SZACUNEK]. Wtedy warto rozważyć własny replay grafu decode przez HSA (duża praca) albo poszukać przełącznika w rocclr/HIP-graph.
- **Koszt.** Pół dnia na pomiar. Ryzyko: rocclr może już używać AGENT-scope, wtedy wynik negatywny i temat zamknięty.

**P5. Ogonowy split (tail split-K) dla MMQ i FA prefillu na RDNA3.**
- **Co.** Policzyć efektywność fal: `ntiles / (96·occ·nwaves)` dla kształtów Qwen przy ub=512. Tam, gdzie ostatnia fala jest wypełniona w <50%, rozbić tylko ostatnią rundę wzdłuż K przez bufor fp32 i ostatni blok (wzór: Akash, moonmath „dense tail KV-split”).
- **Zysk [SZACUNEK].** 0–5% prefillu, zależnie od kształtów. K5 stroiło już kafle, więc najpierw tabela efektywności (bez GPU). Koszt 1–2 dni, ryzyko średnie (bitowość: przy jednym kolejnym dodaniu w ustalonej kolejności zachowana).

**P6. Zadania Helion GDN jako wyrocznia dla chunked GDN prefill.**
- `gated_delta_net.cu:377` ma „TODO: Add chunked kernel”, a Strata raportuje zysk chunked WY na gfx1100 (`research/strata/README.md:173`).
- Trzy wzorce z repo (`recompute_w_u`, `chunk_fwd_h`, `chunk_fwd_o`, BT=64) to gotowy, zwięzły rozkład i kontrakt testów: wyniki fp32 kernela HIP można porównać z nimi offline.
- Nie przyspiesza samo w sobie, ale skraca drogę do kernela prefillu GDN na WMMA.

**P7. Higiena pomiaru (z harnessu).**
- Nasz `mmvq-bench` już mierzy „na zimno”.
- Do przejęcia: (a) tabela SoL per operacja (bajty / 960 GB/s albo FLOP / 123 TFLOPS) w raportach kerneli, z sortowaniem po luce, jak `task.yml` konkursu; (b) dane i ziarno zmieniane między iteracjami (kernele z cache po adresie, jak aiter, potrafią oszukać pomiar).
- Koszt minimalny.

**P8. Zmienne runtime ze zgłoszeń MoE 2026, których jeszcze nie testowaliśmy.**
- **Co.** `HSA_ENABLE_INTERRUPT=0`: hostowe czekanie na sygnał przez aktywne odpytywanie zamiast przerwań [WNIOSEK z nazwy i dokumentacji ROCr]. `HSA_ENABLE_SDMA=0`: kopie przez blit-kernele zamiast silników SDMA.
- **Co już było.** `AMD_DIRECT_DISPATCH`, kernarg, `GPU_MAX_HW_QUEUES` dały szum (`NOTES.md:101,302`). Tych dwóch w notatkach nie ma.
- **Dlaczego warto.** Pętla spekulacji synchronizuje host co krok. `research/v2/rr-hip.md:155-159` podejrzewa przerwę 120–155 µs przed grafem weryfikacji związaną z kopiami SDMA.
- **Zysk [SZACUNEK].** 0–0.2 ms/krok przy Qwen MTP, 0–0.05 ms/token przy LFM.
- **Koszt i ryzyko.** Koszt: dwa uruchomienia `spec_sweep` A/B. Ryzyko: odpytywanie zajmuje rdzeń CPU (8C/16T, więc znośne), a wynik jest bitowo identyczny.

## 5. Krytyka

- **W repo nie ma szybkich kerneli.** Są tylko wzorce PyTorch/aiter i harness. Cała wartość techniczna siedzi w zewnętrznych write-upach, a te dotyczą CDNA3/CDNA4: MFMA fp8/fp4, 304 CU, XCD, 256 MB MALL, HBM. Formaty (FP8, MXFP4, e8m0) i MLA nie istnieją w naszych modelach ani na gfx1100.
- **Harness 2025 mierzył głównie narzut uruchomień.** Zegar CPU bez czyszczenia cache (`amd/eval.py:231-235`). Grand prize w MLA wygrała implementacja w PyTorch z CUDA graph (`TechnicalReport.md:58-100`). Wyniki MLA i MoE z 2025 nie mówią więc wiele o jakości kerneli.
- **Czołówka 2026 w małym GEMM (M=4–256) to głównie walka z dispatch.** Zwycięzca obchodzi HIP pakietami AQL. Pozostali kończą na ok. 8 µs, czyli na progu narzutu. Liczba „~1.5 µs vs ~7 µs” to komentarz autora zmierzony w harnessie z Pythonem, a nie czysty koszt GPU.
- **Ranking 2026 jest zanieczyszczony exploitami.** 1. miejsce w MLA zwraca analityczne przybliżenie, które przechodzi tylko dzięki losowym danym i dopuszczeniu 5% elementów poza tolerancją (`amd_202602/utils.py:146-160`). 1. miejsce w MoE to łatanie i podmiana wersji aiter w trakcie ewaluacji. Kodu z czołówki nie należy traktować jako wzorca kerneli. Wartościowe są głównie write-upy z 2025 (seb-v, Akash) i 2. miejsca.
- **Wskazówki w README 2026 są ogólnikowe.** „Fuse”, „split-K”, „work-stealing” to listy bez liczb. Dla nas ważniejsze są własne pomiary: łańcuchy faz ze spinem tracą (`lfm-decode-round2.md:33-41`), a fuzja gate+up w MMVQ spadła przez rejestry (`NOTES.md:100`).
- **Z blogu seb-v (FP32 SGEMM) przenoszą się mechanizmy (dual-issue, cumode, SGPR, scratch), ale nie liczby.** Nasz prefill to int8 WMMA (MMQ), nie VALU FP32. Zysk zależy od tego, czy dany kernel jest ograniczony przez VALU.
- **Licencja repo** (Researcher Reciprocity) ogranicza użycie do trenowania modeli. Dla nas nieistotne. Kodu z repo i tak nie kopiujemy, a RadeonFlow ma licencję MIT.

## 6. Werdykt

**Niska.** Repo to harness i wzorce zadań pod MI300X/MI355X (FP8/MXFP4/MLA), bez kodu rozwiązań. Do przeniesienia na gfx1100 jest tylko kilka tanich pomysłów, głównie z podlinkowanych write-upów: KQ na iu8 WMMA w FA q8_0 (P1), `-mcumode` (P2), audyt dual-issue/scratch (P3) i pomiar zakresu fence'ów AQL dla kosztu granic (P4).
