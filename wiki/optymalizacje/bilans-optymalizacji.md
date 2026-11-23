---
typ: optymalizacja
tags: [optymalizacje, speedupy, werdykty, tabela]
aktualizacja: 2026-11-22
zrodlo: wiki/tools/tabele.py (pola frontmattera notatek)
status: aktualne
---
# Bilans optymalizacji: przyjęte, w toku, odrzucone (tabela z notatek)

**Każda technika, kernel i łatka z werdyktem, zyskiem, kartą, modelem i dowodem; generuje tools/tabele.py.**

<!-- TABELE:START -->
Wygenerowano 2026-11-23 przez `tools/tabele.py` z pól `technika`, `werdykt`, `zysk`, `dowod` (89 technik); poprawiaj notatkę techniki, nie tę tabelę.

## Przyjęte (w produkcji albo w przepisie) (35)

| technika | zysk | karta | model | K | dowód | notatka |
|---|---|---|---|---|---|---|
| argmax DPP (0026) | 16.8 → 4.3 µs na wywołanie | rx-7900-xtx | qwen3-8-27b |  | [[2026-10-13-k2-male-kernele]] | [[argmax-dpp]] |
| attn prep + FWHT (0019, 0057, 0058) | LFM 4.043 → 3.907 ms/token (0057), 3.928 → 3.879 (0058) | rx-7900-xtx | lfm2-5-24b-a2b |  | [[lfm-runda-3]] | [[attn-prep-fwht]] |
| cache MTP + CKPT_VRAM=2 (TTFT) | start 38.5 → 6.55 s; tura agenta 687/579 → 197 ms | rx-7900-xtx | qwen3-8-27b |  | ~/KERNEL/product/research/45-opoznienia.md | [[opoznienia-ttft]] |
| cache q8_1 i producenci q8_1 (0003, 0015, 0049, 0056) | +2–4% e2e (0003); 37.73 → 37.04 ms (0015) | rx-7900-xtx | qwen3-8-27b |  | ~/KERNEL/qwen-opt/NOTES.md | [[cache-q8-1]] |
| checkpointy GDN w VRAM (LLAMA_CKPT_VRAM=2) | TTFT 2k −22%, S2-turn2 687 → 197 ms | rx-7900-xtx | qwen3-8-27b |  | [[raport-38-ckpt-vram]] | [[raport-38-ckpt-vram]] |
| chuda rezerwa grafu kontekstu draftu MTP | bufor MTP 1081,23 → 40,28 MiB, kontekst 262 144 (+28%) | rx-7900-xtx | qwen3-8-27b |  | [[raport-65-vram-rezerwa-mtp]] | [[raport-65-vram-rezerwa-mtp]] |
| clamp q8_1 do ±65504 (0023) | poprawka poprawności, bitowo bez zmian | rx-7900-xtx | qwen3-8-27b |  | ~/KERNEL/qwen-opt/NOTES.md:259 | [[clamp-q8-1]] |
| conv lag (0038) | draft 8 krok 40.8 → 37.2 ms, draft 12 45.7 → 41.1 ms | rx-7900-xtx | qwen3-8-27b |  | [[2026-10-14-t1-t2-draft]] | [[conv-lag]] |
| draft MTP jednym grafem (0020) + scheduler (0030) | 36.39 → 35.67 ms/krok (0020); 31.89 → 31.59 ms (0030) | rx-7900-xtx | qwen3-8-27b |  | ~/KERNEL/qwen-opt/NOTES.md:236-239 | [[mtp-draft-graf]] |
| epilog MMQ VOPD (0070) | +2.2% pp4096 (1099.5 → 1123.2 t/s) | rx-7900-xtx | qwen3-8-27b |  | ~/KERNEL/qwen-opt/research/round6/mmq-epilogue.md | [[mmq-epilog]] |
| FA kvq (0011, 0055, 0058) | serwer 94k decode 43.0 → 70.9 t/s (+65%) | rx-7900-xtx | qwen3-8-27b | K-125 | [[2026-11-19-k125-k001-xtx]] | [[fattn-kvq]] |
| fuzje GDN (0027, 0028, 0045) | 0028 ~0.33 ms/krok; 0045 pp2048 1082 → 1108 (+2.4%) | rx-7900-xtx | qwen3-8-27b |  | ~/KERNEL/qwen-opt/NOTES.md:263-266 | [[gdn-fuzje-k2]] |
| fuzje MoE LFM (0049, 0051, 0053, 0056) | −0.565 ms/token (5.067 → 3.973 ms/token) | rx-7900-xtx | lfm2-5-24b-a2b |  | [[lfm-runda-2]] | [[fuzje-lfm-moe]] |
| fuzje shortconv LFM (0050, 0054, 0062) | −0.366 ms/token (~22% zysku LFM) | rx-7900-xtx | lfm2-5-24b-a2b |  | ~/KERNEL/qwen-opt/NOTES.md | [[lfm-shortconv]] |
| fuzje weryfikacji Qwena A3–A6 | 41.7 → 36.38 ms/krok (74.8 → 86.4 t/s) | rx-7900-xtx | qwen3-8-27b |  | [[2026-10-12-fuzje-a3-a6]] | [[fuzje-weryfikacji]] |
| GDN replay (S4, 0033–0036) | GDN 793 → 638 µs/weryfikację; VRAM stanów 748 → 195 MiB | rx-7900-xtx | qwen3-8-27b |  | ~/KERNEL/qwen-opt/NOTES.md:290-295 | [[gdn-replay]] |
| kafle MMQ i FA prefill (0040–0045) | prefill 94k 668 → 767 t/s | rx-7900-xtx | qwen3-8-27b |  | ~/KERNEL/qwen-opt/NOTES.md:320-324 | [[prefill-mmq-fa]] |
| kvq-mma (FA na KV q4_0/q8_0, CUDA) | 5060 Ti tg@64k Qwen +24.6%, LFM +30.0% | rtx-5060-ti | qwen3-8-27b |  | [[2026-10-16-kvq-cuda]] | [[fa-kv-kwantyzowane-cuda]] |
| MMVQ MoE gate+up blok (GGML_HIP_MOE_GU_BLOCK) | mikrobench −7% (24.16 → 22.32 µs) | rx-7900-xtx | lfm2-5-24b-a2b |  | [[2026-10-18-lfm-moe-pasmo]] | [[mmvq-moe-gate-up-blok]] |
| MMVQ n=1 2 wiersze na blok (0052, 0064) | LFM 4.610 → 4.509 ms/token (+2.2%); Uncensored 3.933 → 3.706 ms (+6.1%); 3090 LFM +8.5% | rx-7900-xtx | lfm2-5-24b-a2b |  | [[raport-09-chmura-3090]] | [[mmvq-n1-wiersze]] |
| MMVQ wielokolumnowe (0001, 0002, 0021, 0022) | Qwen MTP 68.6 → 82.3 t/s; K1 35.67 → 33.17 ms/krok | rx-7900-xtx | qwen3-8-27b |  | ~/KERNEL/qwen-opt/NOTES.md:38-47 | [[mmvq-multikolumnowe]] |
| op GGML_OP_GUMBEL_MAX | koszt +0.11 ms/krok (27.74 → 27.85) w wersji 2 | rx-7900-xtx | qwen3-8-27b |  | ~/KERNEL/product/research/16k-sprzezone-probkowanie.md | [[gumbel-max]] |
| para MMVQ jedną siatką (0024) | K2 33.17 → 32.14 ms/krok | rx-7900-xtx | qwen3-8-27b |  | ~/KERNEL/qwen-opt/NOTES.md:260 | [[para-mmvq]] |
| PM4 replay (0060, 0061, 0063) | LFM 3.887 → 3.424 ms/token; Qwen MTP 103.7 → 108.8 t/s | rx-7900-xtx | lfm2-5-24b-a2b |  | ~/KERNEL/qwen-opt/research/lfm-decode-round4.md | [[pm4-replay]] |
| przełączniki luk hosta (YIELD_FAST=2, PM4_MIN_DISPATCH=16, PM4_LAZY_EXEC=1) | czat T=1 113,8 → 117,9 t/s | rx-7900-xtx | qwen3-8-27b |  | [[raport-24o-luki-hosta]] | [[raport-24o-luki-hosta]] |
| przyrostowy cache tokenizacji (LLAMA_SERVER_TOK_CACHE) | tokenizacja+szablon 25,5 ms (14k) / 137,3 ms (91k) → 0,5–2,5 ms na turę |  | qwen3-8-27b |  | [[raport-24i-sciezka-agenta]] | [[raport-24i-sciezka-agenta]] |
| rms_norm·mul(+q8_1) z redukcjami DPP (0025) | 5,87 → 4,51 µs przy 5120 kolumnach | rx-7900-xtx |  |  | [[rmsnorm-dpp]] | [[rmsnorm-dpp]] |
| sprzężone próbkowanie draftu (Gumbel-max) | +3,5% T=1 (107,6 → 111,4 t/s) | rx-7900-xtx | qwen3-8-27b |  | [[raport-24p-sprzezone-t1]] | [[sprzezone-probkowanie-draftu]] |
| sprzężone próbkowanie draftu (LLAMA_SPEC_COUPLED) | +3,5% T=1 (107,6 → 111,4 t/s) | rx-7900-xtx | qwen3-8-27b |  | [[raport-24p-sprzezone-t1]] | [[raport-24p-sprzezone-t1]] |
| szybka ścieżka samplera (0031, 0048, 0065–0069) | narzędzia omp Qwen MTP 104,8 → 113,2 t/s, LFM 254,2 → 294,3 | rx-7900-xtx |  |  | [[sampler-fast-path]] | [[sampler-fast-path]] |
| słownik draftu 64k + draft IQ4_XS (0004, 0032) | 0004 +7.5% (64k); 0032 netto +1–3% t/s | rx-7900-xtx | qwen3-8-27b |  | ~/KERNEL/product/research/16f-xtx-szybkie.md:94-115 | [[latki-spekulacji]] |
| TOPK_MOE_NP2 + MMVQ_N1_IQ2 (CUDA) | tg128 91.1 → 96.7 (+6.1%); IQ2_LUT −2.4% odrzucone | rtx-3090 | nemotron-3-5-bolt-74b-a9b |  | ~/KERNEL/product/research/14-nemotron-3090.md | [[nemotron-kernele-cuda]] |
| weryfikacja draftu top-128 na GPU (LLAMA_GPU_VERIFY) | +2,4% mvs (410,4 → 420,1 t/s) | rx-7900-xtx | qwen3-8-27b |  | [[raport-24m-weryfikacja-gpu]] | [[raport-24m-weryfikacja-gpu]] |
| WMMA small-N weryfikacja 9–16 kolumn (0037) | n=9 49,2 → 32,1 ms, n=16 51,0 → 35,0 ms | rx-7900-xtx | qwen3-8-27b |  | [[wmma-small-n]] | [[wmma-small-n]] |
| łatki hostowe (0029, 0047, 0059) | K3 32.14 → 30.97 ms/krok (97.8 → 101.5 t/s); 0047 102.6 → 104.2 t/s | rx-7900-xtx | qwen3-8-27b |  | [[2026-10-13-k3-host]] | [[latki-hostowe]] |

## Odrzucone (z powodem w notatce) (28)

| technika | zysk | karta | model | K | dowód | notatka |
|---|---|---|---|---|---|---|
| adaptacyjna spekulacja (bramka ogona, głębokość MTP) | bramka ogona ≤ +0,5%; głębokość adaptacyjna zmienia greedy md5 | rx-7900-xtx | qwen3-8-27b |  | [[raport-24q-adaptacyjna-spekulacja]] | [[raport-24q-adaptacyjna-spekulacja]] |
| bariera tylko LDS (GGML_HIP_LDS_BARRIER) | w szumie (pp4096 1133.2 → 1129.7 t/s, czat 102.5 → 102.4) | rx-7900-xtx | qwen3-8-27b |  | ~/KERNEL/product/research/26-kolejka-gpu-wieczor.md:10 | [[bariera-lds-rdna3]] |
| bezstratna kompresja entropijna wag GGUF | kodek 0–0,9% bajtów/token (bramka 8%) |  |  |  | [[raport-24t-entropia-wag]] | [[raport-24t-entropia-wag]] |
| cache sesji na dysku (slot save/restore) | restore 53k 23–24× szybciej niż prefill (Qwen 2.51 s vs ~61.5 s); decyzja KV tylko w RAM | rx-7900-xtx | qwen3-8-27b |  | [[2026-10-19-kv-tylko-w-ram]] | [[cache-sesji-na-dysku]] |
| drugi bank stanu GDN | E0 −0,4% (v1/v2); v3 nierozstrzygnięty | rx-7900-xtx | qwen3-8-27b |  | [[raport-48-norma-gdn-bank]] | [[raport-48-norma-gdn-bank]] |
| drzewa draftu MTP i temperatura draftu | drzewo statyczne +1,2%, dynamiczne +3,9…4,7% (próg +6%) |  | qwen3-8-27b |  | [[raport-24s-drzewa-proza]] | [[raport-24s-drzewa-proza]] |
| FA D=256 prefill bez spilli (sched_barrier) | +0,84% pp512@d32k, +0,40% pp16384 | rx-7900-xtx | qwen3-8-27b |  | [[raport-24v-prefill-fa]] | [[raport-24v-prefill-fa]] |
| FLy stratna weryfikacja | +8.2% u autorów (MI355X), zmienia wyjście |  | qwen3-8-27b |  | [[2026-11-05-tylko-bezstratne]] | [[fly-stratna-weryfikacja]] |
| fuzja RMS norm do MMVQ (ogon producenta) | page fault + mode1 reset GPU, matvec różny 13/216 | rx-7900-xtx |  |  | [[raport-24l-fuzja-norm]] | [[raport-24l-fuzja-norm]] |
| fuzje ATTN_PREP_MT i KVQ_FWHT_GATE (mniej granic dispatchy) | proza +0,24% (szum), mvs 0,0% (428,49 → 428,55 t/s) | rx-7900-xtx | qwen3-8-27b |  | [[raport-54-mniej-granic]] | [[raport-54-mniej-granic]] |
| GDN fast (DPP) | +0.15% tg128, pp512 +0.7% (szum) | rx-7900-xtx | qwen3-8-27b |  | ~/KERNEL/qwen-opt/research/round6/gdn-bitwise.md | [[gdn-fast]] |
| jeden przebieg KV w fattn-kvq dla weryfikacji MTP | sufit +3,0…6,6% e2e przy 94k, ≤ 2,3% przy 32k (cel +8%) | rx-7900-xtx |  |  | [[raport-24h-kv-jeden-przebieg]] | [[raport-24h-kv-jeden-przebieg]] |
| kontroler szerokości draftu | T2 103.6 vs 102.7 t/s (nic); kontroler 5/8/16 wynik zerowy | rx-7900-xtx | qwen3-8-27b |  | [[2026-10-18-kontroler-szerokosci-zerowy]] | [[kontroler-szerokosci-draftu]] |
| KV raz na weryfikację (GGML_HIP_KVQ_ONCE) | FA −6.1% przy 199k (próg −10%), e2e 199k +1.79% | rx-7900-xtx | qwen3-8-27b |  | [[2026-11-08-kvq-once-profil]] | [[kv-raz-na-weryfikacje]] |
| lookup kontekstowy bez draftera (LFM) | +17% copy W8 (288,2 → 334,7 t/s), tekst T=0 ≠ plain | rx-7900-xtx | lfm2-5-24b-a2b |  | [[raport-24d-lfm-lookup]] | [[raport-24d-lfm-lookup]] |
| małe kernele weryfikacji (rms_norm, FA kvq, GDN) | sufit ≤ 0,26 ms/krok, brak zwycięzcy | rx-7900-xtx | qwen3-8-27b |  | [[raport-51-male-kernele]] | [[raport-51-male-kernele]] |
| MMQ Q6_K skale przez b128 | 0,0% (pp4096 1000,7 → 1000,6) | rx-7900-xtx | qwen3-8-27b |  | [[2026-11-07-q6k-mmq-skale]] | [[mmq-q6k-skale-lds]] |
| MMVQ n=1 szeroki loader (wide=2) | −1,0% tg128 (40,86 → 40,41 t/s) | rx-7900-xtx | qwen3-8-27b |  | [[raport-24f-mmvq-fa]] | [[raport-24f-mmvq-fa]] |
| MMVQ n=5 duże kształty (pipelining Q4_K + 8 fal) | −15% mikrobench 17408×5120, ABBA bez zysku | rx-7900-xtx | qwen3-8-27b |  | [[raport-46-mmvq-big]] | [[raport-46-mmvq-big]] |
| MMVQ n=5 RPB=1 | −3,0% (27,98 → 28,80 ms/krok) | rx-7900-xtx | qwen3-8-27b |  | [[raport-24r-mmvq-pasmo]] | [[raport-24r-mmvq-pasmo]] |
| obłożenie MMVQ n=5 (GGML_HIP_MMVQ_OCC) | −0,5% spec_sweep (111,4 → 110,8 t/s), serializacja −6,4% | rx-7900-xtx | qwen3-8-27b |  | [[raport-24n-mmvq-n5]] | [[raport-24n-mmvq-n5]] |
| osobny kernel rms_norm × w + quantize q8_1 | ≈ 0,012 ms/krok (próg 0,25 ms) | rx-7900-xtx | qwen3-8-27b |  | [[raport-24u-norm-quant]] | [[raport-24u-norm-quant]] |
| PAIR2 para MMVQ dla mieszanych typów | +0,4% czat T=1 (115,1 → 115,6 t/s) | rx-7900-xtx | qwen3-8-27b |  | [[raport-24w-pair2]] | [[raport-24w-pair2]] |
| pełna głowica draftu dla OOV | −0.51% (W=16), −2.40% (stała pełna głowica), sufit |  | qwen3-8-27b |  | ~/KERNEL/product/research/24b-draft-pelny-slownik.md | [[raport-24b-draft-pelny-slownik]] |
| router ogon lookupu / DFlash2 / MTP | sufit wyroczni +1,1% (T=0) / +2,0% (T=1), próg +8% |  |  |  | [[raport-24j-router]] | [[raport-24j-router]] |
| Strata KVA (prefill przez stan późnych warstw) | stratne; decode −11% na R9700 | radeon-ai-pro-r9700 |  |  | [[strata-kva]] | [[strata-kva]] |
| Vulkan RDNA matvec i MMVQ (0006–0010) | −5,2% ms/krok (43,73 → 41,46), backend poza domyślną ścieżką | rx-7900-xtx |  |  | [[vulkan-mmvq]] | [[vulkan-mmvq]] |
| wiele zapytań -np 2/4 | −5…−17% single; fan-out wall 258.0 → 287.4 s (+11%) | rx-7900-xtx | qwen3-8-27b |  | ~/KERNEL/product/research/24c-wiele-zapytan.md | [[raport-24c-wiele-zapytan]] |

## W toku (26)

| technika | zysk | karta | model | K | dowód | notatka |
|---|---|---|---|---|---|---|
| AGR lookup zgodny z MTP | +3.7% t/s agent, +0.6% czat (symulacja) |  | qwen3-8-27b |  | ~/KERNEL/product/research/21c-copy-paste-lm.md | [[agr-lookup-zgodny-z-mtp]] |
| AKV drop + repozycjonowanie KV | −27.7% kosztu API u autorów (GPT-OSS-120B); repos odpada u nas (IMROPE) |  | qwen3-8-27b |  | ~/KERNEL/product/research/60d-serving-kernels-cache.md | [[akv-cache-agentow]] |
| DCQ (błąd stanu GDN w stracie kwantyzacji) | brak pomiaru u nas; dowody autora słabe |  | qwen3-8-27b |  | ~/KERNEL/product/research/60c-quant-and-3090-engines.md | [[dcq-kotwica-stanu-gdn]] |
| drzewo weryfikacji GDN (forma WY) | +7.8% w symulacji Sabera; nasz sufit dynamiczne +3.9…4.7% |  | qwen3-8-27b |  | ~/KERNEL/product/research/66d-saber-engine-rdna.md | [[drzewo-weryfikacji-gdn-wy]] |
| głowica draftu gruba + rerank top-K | niezmierzone; cel odzyskać −2–3% akceptacji IQ4_XS | rx-7900-xtx | qwen3-8-27b |  | ~/KERNEL/product/research/66d-saber-engine-rdna.md | [[glowica-draftu-rerank]] |
| kandydat 0071 GGML_HIP_MOE_GU_BLOCK | LFM +0,33% / Uncensored +1,39% | rx-7900-xtx | lfm2-5-24b-a2b |  | [[seria-amd-opt]] | [[seria-amd-opt]] |
| L2 persisting window (CUDA) | niezmierzone (szacunek) |  | lfm2-5-24b-a2b |  | ~/KERNEL/product/research/21b-gpu-perf-zasoby.md | [[l2-persist]] |
| maska KQ na GPU/w czasie draftu | maska 0.25 ms na graf przy 199k (~1.1% kroku), niezmierzone e2e |  | qwen3-8-27b |  | ~/KERNEL/product/research/66e-anatomia-serwowania-tqllm.md | [[maska-kq-host-dlugi-ctx]] |
| megakernel Qwen | sufit ~4 ms/krok (+12%) wg szacunku, niezmierzone | rx-7900-xtx | qwen3-8-27b |  | ~/KERNEL/product/research/66c-hyperkernel-megakernele.md | [[budzet-megakernela-qwen-xtx]] |
| MMVQ IQ4_XS n=5 ryp2 | para ffn −3,7%, down+residual −6,8% | rx-7900-xtx | qwen3-8-27b |  | [[raport-50d-mmvq-iq4xs]] | [[raport-50d-mmvq-iq4xs]] |
| MMVQ n=5 ogon k/v 1024 wierszy | szac. −0,03 ms/krok, bez bramki | rx-7900-xtx | qwen3-8-27b |  | [[raport-49-mmvq-ogon-1024]] | [[raport-49-mmvq-ogon-1024]] |
| MMVQ Q4_K n=5 kernel strumieniowy | plain −3…−6%, pary −10…−21% (mikrobench) | rx-7900-xtx | qwen3-8-27b |  | [[raport-50a-mmvq-q4k]] | [[raport-50a-mmvq-q4k]] |
| MMVQ Q5_K n=5 big_rows | −1,3…−3,5% na 8192–34816 wierszach | rx-7900-xtx | qwen3-8-27b |  | [[raport-50b-mmvq-q5k]] | [[raport-50b-mmvq-q5k]] |
| MMVQ Q6_K n=5 potok ping-pong | szac. −0,15 ms/krok, bramki nieuruchomione | rx-7900-xtx | qwen3-8-27b |  | [[raport-50c-mmvq-q6k]] | [[raport-50c-mmvq-q6k]] |
| PDL trigger w MMVQ (CUDA sm_90+) | niezmierzone (szacunek) | rtx-5060-ti | lfm2-5-24b-a2b |  | ~/KERNEL/product/research/21b-gpu-perf-zasoby.md | [[pdl-mmvq-trigger]] |
| PFlash tryb stratny długich dokumentów | niezmierzone (pilot etap C) | rx-7900-xtx |  |  | [[tryb-stratny-pflash]] | [[tryb-stratny-pflash]] |
| prefetch L2 w MMVQ (CUDA) | u nas niezmierzone; GB10 Q6_K +6.19% |  |  |  | ~/KERNEL/product/research/21b-gpu-perf-zasoby.md | [[mmvq-prefetch-l2]] |
| profil kosztu weryfikacji W16 vs MTP4 | krok W16 35,61 ms vs MTP4 29,62 ms (+20%) | rx-7900-xtx | qwen3-8-27b |  | [[raport-24k-koszt-weryfikacji]] | [[raport-24k-koszt-weryfikacji]] |
| próg draftu p-min od kosztu wiersza | u Straty +9.3% (1383 sloty); u nas niezmierzone |  | qwen3-6-35b-a3b |  | ~/KERNEL/product/research/66a-strata-maya.md | [[prog-draftu-od-kosztu-wiersza]] |
| rank-1 edycja down_proj warstwy 63 | −35,5% mediana myślenia (26 254 → 16 930 tokenów), przeciek </think> 11/32 |  | astra-stop |  | ~/KERNEL/product/research/69c-astra-stop.md | [[astra-stop]] |
| routing profili spekulacji (LLAMA_SPEC_ROUTE) | brak pomiaru (ABBA padło) | rx-7900-xtx | qwen3-8-27b |  | [[raport-44-spec-route]] | [[raport-44-spec-route]] |
| shortlist w głowicy draftu MTP (LLAMA_DRAFT_SHORTLIST) | bramka recall nie przeszła (40,8% ridge K=1024), VRAM +536 MiB | rx-7900-xtx | qwen3-8-27b |  | [[raport-53-draft-shortlist]] | [[raport-53-draft-shortlist]] |
| siatka checkpointów GDN, junction, fallback odtwarzania | niezmierzone |  |  |  | [[siatka-checkpointow-gdn]] | [[siatka-checkpointow-gdn]] |
| strumień O(n) z wyrocznią zamiast parsera O(n²) | parser 0,07 → 0,52 ms/token przy 1k → 12,8k (do usunięcia) |  |  |  | [[strumien-on-wyrocznia]] | [[strumien-on-wyrocznia]] |
| trwała siatka MoE bez PM4 | strata PM4-off 293,7 → 259,3 t/s do odzyskania | rx-7900-xtx | lfm2-5-24b-a2b |  | [[trwala-siatka-bez-pm4]] | [[trwala-siatka-bez-pm4]] |
| wspólny początek promptu i chude checkpointy | niezmierzone |  |  |  | [[wspolny-poczatek-promptu]] | [[wspolny-poczatek-promptu]] |
<!-- TABELE:END -->

## Powiązane
- [[optymalizacje/_hub|Speedupy i optymalizacje]]
- [[KOLEJKA-TESTOW]]
- [[wyniki-negatywne]]
