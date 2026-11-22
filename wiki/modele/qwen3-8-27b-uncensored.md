---
typ: model
tags: [modele, qwen, uncensored]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/sources/qwen3.8-27b.md:34-40; ~/KERNEL/qwen-opt/STATUS-NEXT.md:11; ~/KERNEL/qwen-opt/run-llm.sh:8; ~/KERNEL/qwen-opt/README.md:52; ~/KERNEL/qwen-opt/research/v2/rr-engines-drafters.md:180; ls ~/models (2026-10-16); ~/KERNEL/product/research/21e-kv-miedzy-modelami.md:96-104
status: aktualne
model: qwen3-8-27b-uncensored
rozmiar: 27B
kwant: Q4_K_M
karty: rx-7900-xtx
wyniki:
  - qwen3-8-27b-uncensored | rx-7900-xtx | 115.5 t/s | dekod MTP T=1; spec_sweep, KV q4_0 | 2026-10-15
  - qwen3-8-27b-uncensored | rx-7900-xtx | 1109 t/s | prefill pp4096 | 2026-10-15
  - qwen3-8-27b-uncensored | rx-7900-xtx | 44.0 t/s | dekod plain tg128 | 2026-10-15
---
# Qwen3.8-27B-Uncensored (OrcaRouter)

**Abliterowana wersja Qwen3.8-27B od OrcaRouter: usunięty „kierunek odmowy”, architektura bez zmian; u nas najszybszy wariant Qwena (115.5 t/s).**

- Repo `orcarouter/Qwen3.8-27B-Uncensored-GGUF` (Apache 2.0; repo HF bramkowane, ten sam plik jest w rejestrze Ollama `orcarouter/qwen3.8-27b-uncensored:q4_K_M`).
- Plik: `~/models/orca/Qwen3.8-27B-Uncensored-Q4_K_M.gguf` (15.66 GiB) + `mmproj-…-f16.gguf` (0.87 GiB); `VISION=1` w `run-llm.sh` dokłada mmproj.
- Głowica MTP w tym pliku jest w Q4_K (UD ma Q6_K/Q8_0) — fakt z parsowania GGUF (rr-engines-drafters).
- Wyniki (2026-10-15, spec_sweep 6×3, T=1, MTP, KV q4_0): **115.5 t/s**, 26.68 ms/krok, pp4096 1109, tg128 bez spekulacji 44.0.
- Te same kształty tensorów i kernele co bazowy model; abliteracja zwykle lekko pogarsza jakość, OrcaRouter nie podaje miar (KL, benchmarki).

Analiza wag (21e, 2026-10-19): to Qwen3.8-27B z jedną globalną ablacją kierunku we wszystkich writerach (s ≈ 1), F32 i `output.weight` bajtowo identyczne – [[uncensored-ablacja-kierunku]].

<!-- TABELE:START -->
## Wyniki z notatek (68)

Najlepszy wynik na metrykę z pól `wynik` notatek testów (tools/tabele.py, 2026-11-22); pełna tabela: [[najlepsze-wyniki]].

| karta | metryka | najlepszy | warunki | data | źródło |
|---|---|---|---|---|---|
| NVIDIA RTX 3090 [[rtx-3090]] | czat | **75.3 t/s** | cuda-topka2 | 2026-10-20 | [[raport-27-3090-final]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | bench.py skill-io c1 | **110,3 t/s** | T 0,6, 6 × 512 tok. | 2026-11-19 | [[2026-11-19-k109-k110-k106-xtx]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod 1,7k | **128,0 t/s** | SHORT_TAIL=32 (KILL, produkcja 135,4) | 2026-11-14 | [[2026-11-14-k104-krotki-ogon-promptu]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod 1,7k T=0 | **129,23 t/s** | xtxbench A/A, produkcja | 2026-11-09 | [[xtxbench-szybki-ab]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod 199k T=0 | **95.81 t/s** | KVQ_ONCE=1 (KILL, baza 94.12) | 2026-11-08 | [[2026-11-08-kvq-once-profil]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod 255k | **78,7 t/s** | MTP n=4 eco 2200 | 2026-11-06 | [[2026-11-06-ctx-262k-fit]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod 94k T=0 | **122.04 t/s** | KVQ_ONCE=1 (baza 120.97) | 2026-11-08 | [[2026-11-08-kvq-once-profil]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod HumanEval+ ważony | **174,2 t/s** | T=0, MTP n4 + lookup | 2026-11-09 | [[2026-11-09-evalplus-qwen-uncensored]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod MTP | **115,3 t/s** | PM4 replay | 2026-10-14 | [[pm4-replay]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod MTP n=4 T=1 | **105.0 t/s** | po T1, 28.28 ms/krok | 2026-10-14 | [[2026-10-14-t1-t2-draft]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod MTP n=5 T=1 | **108.4 t/s** | po T1 | 2026-10-14 | [[2026-10-14-t1-t2-draft]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod MTP T=1 | **115.5 t/s** | amd-opt spec_sweep | 2026-10-15 | [[rx-7900-xtx]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod mvs T=0 | **414.8 t/s** | topka lookup W16, PM4=0 | 2026-10-19 | [[2026-10-19-build-topka]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod plain tg128 | **44.0 t/s** |  | 2026-10-15 | [[qwen3-8-27b-uncensored]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod po fillu 222k | **86,3 t/s** | topka-q70 | 2026-11-19 | [[2026-11-19-k109-k110-k106-xtx]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod po fillu 255k | **73,6 t/s** | topka-q70 | 2026-11-09 | [[2026-11-09-wdrozenie-topka-q70]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod sesja omp 0–32k | **127,2 t/s** | final mode | 2026-11-06 | [[2026-11-06-sesja-uzytkownika-final-mode]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod sesja omp 128–160k | **95,8 t/s** | final mode | 2026-11-06 | [[2026-11-06-sesja-uzytkownika-final-mode]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod sesja omp ważone | **120,8 t/s** | final mode, do 139k | 2026-11-06 | [[2026-11-06-sesja-uzytkownika-final-mode]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod spec_sweep T=1 mediana | **118,3 t/s** | final mode | 2026-11-06 | [[2026-11-06-final-mode]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod T=0 1,7k | **131,2 t/s** | LLAMA_SPEC_LOOKUP=0 | 2026-11-14 | [[2026-11-14-k002-k003-k013-xtx]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod ważony evalplus | **162,0 t/s** | T=0 | 2026-11-09 | [[2026-11-09-evalplus-qwen-uncensored]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod ważony jakość-mini | **142.4 t/s** | T=0 | 2026-11-09 | [[2026-11-09-jakosc-mini-qwen-unc]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | FA na krok przy 199k | **11.32 ms** | rocprofv3, ONCE=0 | 2026-11-08 | [[2026-11-08-kvq-once-profil]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | fill 255k | **493,4 t/s** | FA D256 VAR 83, Q4_K_M, KV q4_0 (baza 466,3) | 2026-11-09 | [[2026-11-08-fa-d256-prefill]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | greedy 256 tok. | **106,4 t/s** | final mode | 2026-11-06 | [[2026-11-06-final-mode]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | HumanEval pass@1 | **97,6 %** | topka-q70, effort low, T=0 | 2026-11-09 | [[2026-11-09-evalplus-qwen-uncensored]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | HumanEval+ pass@1 | **92,7 %** | topka-q70, effort low, T=0 | 2026-11-09 | [[2026-11-09-evalplus-qwen-uncensored]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | jakość-mini 255/290 | **87.9 %** | topka-q70, effort low, T=0 | 2026-11-09 | [[2026-11-09-jakosc-mini-qwen-unc]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | krok Vulkan 0007–0010 | **39.92 ms** |  | 2026-10-12 | [[vulkan-mmvq]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | llama-bench pp d128k | **486,3 t/s** | VAR 83 (baza 459,5) | 2026-11-09 | [[2026-11-08-fa-d256-prefill]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | MBPP+ pass@1 | **80,2 %** | topka-q70, effort low, T=0 | 2026-11-09 | [[2026-11-09-evalplus-qwen-uncensored]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | MMLU-Pro 140 pytań | **82.1 %** | effort low | 2026-11-09 | [[2026-11-09-jakosc-mini-qwen-unc]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | MMVQ draftów na krok 1,7k | **1,93 ms** | ślad rocprofv3 | 2026-11-07 | [[2026-11-19-k111-k123-krok-xtx]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | MMVQ weryfikacji na krok 1,7k | **20,16 ms** | ślad rocprofv3, PM4 off, topka-q63 | 2026-11-07 | [[2026-11-19-k111-k123-krok-xtx]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | ms/krok MTP T=1 | **39.92 ms** | Vulkan łatki MMVQ | 2026-10-12 | [[2026-10-12-vulkan-krok-po-kroku]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | ms/krok spec_sweep T=1 | **26,86 ms** | eco 2200 (stock 26,32) | 2026-11-06 | [[2026-11-06-eco-szybki-bench]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | mvs | **434.9 t/s** | topka | 2026-10-20 | [[raport-wyniki-xtx-2026-10-19]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | pierwszy dekod K-001 | **130,7 t/s** | topka-q70 | 2026-11-19 | [[2026-11-19-k125-k001-xtx]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | pp4096 Q6K_WIDE (KILL, −0,01%) | **1000,6 t/s** | Q4_K_M, topka-q63, ABBA | 2026-11-07 | [[2026-11-07-q6k-mmq-skale]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | prefill 12k | **916,0 t/s** | eco 2200 (stock 1036,8) | 2026-11-06 | [[2026-11-06-eco-szybki-bench]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | prefill 130k | **650,8 t/s** | igły 3/3 | 2026-11-19 | [[2026-11-19-k109-k110-k106-xtx]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | prefill 222k | **527,0 t/s** | igły 3/3, topka-q70, KV q4_0 | 2026-11-19 | [[2026-11-19-k109-k110-k106-xtx]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | prefill 255k | **465,1 t/s** | topka-q63 eco 2200, KV q4_0 | 2026-11-06 | [[2026-11-06-ctx-262k-fit]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | prefill 32k | **865,61 t/s** | xtxbench A/A | 2026-11-09 | [[xtxbench-szybki-ab]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | prefill 4242 tok. przy 103k | **498,6 t/s** | final mode | 2026-11-06 | [[2026-11-06-sesja-uzytkownika-final-mode]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | prefill 94k | **762 t/s** | K5+T3 0040-0045 | 2026-10-14 | [[prefill-mmq-fa]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | prefill long 32k | **859,1 t/s** | topka-q70 | 2026-11-09 | [[2026-11-09-wdrozenie-topka-q70]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | prefill pp4096 | **1109 t/s** |  | 2026-10-15 | [[qwen3-8-27b-uncensored]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | prefill ~16k bench.py | **932,9 t/s** | topka-q70 | 2026-11-19 | [[2026-11-19-k109-k110-k106-xtx]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | prompt krótkiego żądania mediana | **139,1 ms** | AP_TIMING | 2026-11-14 | [[2026-11-14-k002-k003-k013-xtx]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | prompt krótkiej tury mediana | **148,5 ms** | SHORT_TAIL=32 (produkcja 148,7) | 2026-11-14 | [[2026-11-14-k104-krotki-ogon-promptu]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | spec_sweep | **115.5 t/s** | produkcja | 2026-10-19 | [[benchmarki-przed-po-2026-10-19]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | spec_sweep T=1 | **119,2 t/s** | VAR 83 | 2026-11-09 | [[2026-11-08-fa-d256-prefill]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | spec_sweep T=1 1 seed | **106.9 t/s** | topka | 2026-10-19 | [[2026-10-19-build-topka]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | spec_sweep T=1 mediana | **119,3 t/s** | topka-q70 | 2026-11-09 | [[2026-11-09-wdrozenie-topka-q70]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | tg128 | **268.27 t/s** | MOE_GU_BLOCK (=0 264.60) | 2026-10-18 | [[2026-10-18-lfm-moe-pasmo]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | tokenizacja mediana 82–119k | **6,6 ms** | TOK_CACHE+PARSE_INC (baza 14,0) | 2026-11-08 | [[2026-11-08-l1-tokenizacja-parser]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | top-1 zgodny kvq vs f16 | **97,595 %** | topka-q70 | 2026-11-19 | [[2026-11-19-k125-k001-xtx]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | tura agenta mediana | **12 441 ms** | #30137 + huge pages (A 13 413 ms) | 2026-11-09 | [[2026-11-08-cachesave-30137]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | tura agenta mediana 76–112k | **12 029 ms** | topka-q70 (baza 13 413) | 2026-11-09 | [[2026-11-09-wdrozenie-topka-q70]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | tura poza prefillem | **1 619 ms** | TOK_CACHE+PARSE_INC (baza 1 704) | 2026-11-08 | [[2026-11-08-l1-tokenizacja-parser]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | update cache | **437,9 ms** | #30137 + huge pages (A 1 321,7 ms) | 2026-11-09 | [[2026-11-08-cachesave-30137]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | V16 − V5 przy 2k | **7,1 ms** | llama-bench, PM4, VAR 83 | 2026-11-14 | [[2026-11-14-k002-k003-k013-xtx]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | V16 − V5 przy 32k | **10,1 ms** | llama-bench, PM4, VAR 83 | 2026-11-14 | [[2026-11-14-k002-k003-k013-xtx]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | VRAM szczyt 255k | **23367 MiB** | ctx 262144 | 2026-11-06 | [[2026-11-06-ctx-262k-fit]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | zapis wpisu cache | **266,6 ms** | #30137 + huge pages (A 1 055,5 ms) | 2026-11-09 | [[2026-11-08-cachesave-30137]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | średnie KLD kvq vs f16 | **0,003862 KLD** | wikitext-2 c 8192, ub 5 (standard 0,004522) | 2026-11-19 | [[2026-11-19-k125-k001-xtx]] |
<!-- TABELE:END -->

## Powiązane
- [[modele/_hub|Modele]]
- [[qwen3-8-27b]]
- orcarouter
- [[stan-2026-10-15]]
- [[kwanty-gguf]]
