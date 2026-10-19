---
typ: hub
tags: [kernele, hub]
aktualizacja: 2026-10-16
zrodlo: wiki/tools/wiki.py index
status: aktualne
---
# Kernele

**Nasze kernele i fuzje w llama.cpp: co robią, ile dały, klasa poprawności i wyłącznik env.**

Klasy poprawności: *bitowo identyczne* (te same logity / greedy md5) albo *zmiana numeryki* (bramka KLD). Łatki, w których siedzą: [[latki/_hub|Łatki]].

Wróć: [[index|Strona główna]]. Lista niżej jest generowana przez `python3 tools/wiki.py index`; nie edytuj jej ręcznie.

<!-- AUTO:START -->
## Notatki (29)

- [[argmax-dpp|Argmax z DPP (0026)]] — Argmax po słowniku w drafcie MTP: 16 ładowań w locie i wymiana między lane'ami przez DPP zamiast pamięci LDS; 16.8 → 4.3 µs na wywołanie.
- [[cache-q8-1|Cache q8_1 aktywacji i „producenci” q8_1]] — MMVQ potrzebuje wejścia skwantyzowanego do q8_1; zamiast osobnego kernela kwantyzacji przed każdym matvec, kwantyzujemy raz i najlepiej już w kernelu, który to wejście produkuje.
- [[clamp-q8-1|Clamp (d, sum) bloków q8_1 do ±65504 (0023, poprawka)]] — Poprawka poprawności (S1): pola d i sum każdego bloku q8_1 są przycinane do zakresu fp16 (±65504) we wszystkich miejscach, które piszą q8_1.
- [[mtp-draft-graf|Draft MTP jako jeden graf (0020) i własny scheduler (0030)]] — Cztery osobne przebiegi głowicy MTP zastąpione jednym rozwiniętym grafem z argmax i get_rows na GPU; łańcuch draftu dostał też własny scheduler, żeby nie przebudowywać grafów co krok.
- [[mmq-epilog|Epilog MMQ w parach VOPD (0070)]] — Prefill Q4_K/Q5_K na RDNA3: konwersje skal i akumulatora przepisane tak, żeby wszystkie operacje epilogu szły w parach VOPD; +2.2% pp4096 Qwena, bitowo identycznie.
- [[fattn-kvq|FA `kvq`: atencja dekodowania na skwantyzowanym KV]] — Kernel flash attention (RDNA3, WMMA), który czyta KV q4_0 lub q8_0 bez konwersji do F16 i liczy całą grupę GQA oraz do 8 tokenów w jednym przejściu; od 2026-10-16 także port CUDA (Ampere+).
- [[gdn-fuzje-k2|Fuzje GDN Qwena (0027, 0028, 0045)]] — Mniejsze fuzje wokół warstwy Gated DeltaNet: bramkowana norma wyjścia, SSM_CONV razem z alpha/beta i normalizacja q/k w prefillu.
- [[fuzje-weryfikacji|Fuzje kroku weryfikacji Qwena (A3–A6)]] — Seria fuzji z 2026-10-12, która zmniejszyła liczbę kerneli weryfikacji Qwena z 2156 do 972 i skróciła krok z 41.7 do 36.38 ms.
- [[fuzje-lfm-moe|Fuzje MoE dla LFM2.5 (0049, 0051, 0053, 0056)]] — Cztery fuzje dekodowania pojedynczego tokenu w warstwach MoE (64 ekspertów, 4 aktywne): łącznie −0.565 ms/token, ok. 34% zysku kampanii LFM.
- [[lfm-shortconv|Fuzje shortconv LFM2 (0050, 0054, 0062)]] — LFM2.5 ma 30 warstw krótkiej konwolucji (shortconv); trzy łatki wciągają mnożenia i samą konwolucję do sąsiednich kerneli: łącznie −0.366 ms/token (~22% zysku LFM).
- [[gdn-fast|GDN fast (Gated DeltaNet, DPP) — nie scalony]] — Szybszy kernel rekurencji Gated DeltaNet Qwena (redukcje DPP zamiast ds_bpermute, nakładanie tokenów t/t+1); bitowo zgodny, ale zysk end-to-end w szumie, więc został na gałęzi `opt-gdn6`.
- [[gdn-replay|GDN z opóźnieniem: cofanie przez przeliczenie (S4)]] — Zamiast zapisywać snapshot stanu rekurencyjnego po każdym tokenie weryfikacji, cache trzyma zatwierdzony stan i bufory wierszy oczekujących, a następna weryfikacja przelicza przyjęte wiersze.
- [[conv-lag|Historia conv z opóźnieniem (T1, łatka 0038)]] — Stan konwolucji Qwena trzymany jak stan GDN w S4: okno wokół wierszy oczekujących zamiast snapshotów, co usunęło „klif” przy drafcie ≥ 8 tokenów.
- [[mmvq-n1-wiersze|MMVQ 1-kolumnowe: 2 wiersze na blok (0052, 0064)]] — Strojenie zwykłego matvec (dekodowanie bez spekulacji) pod gfx1100: blok liczy 2 wiersze zamiast jednego, najpierw dla K-quantów, potem także dla Q8_0.
- [[mmvq-moe-gate-up-blok|MMVQ MoE gate+up: blok jednej grupy q8_1 (`GGML_HIP_MOE_GU_BLOCK`)]] — `mul_mat_vec_q_moe_gate_up_q5k<8>`: blok 16 fal liczy 32 wiersze jednej grupy q8_1 (każdy wiersz jak kernel 2-wierszowy), wagi następnej iteracji ładuje przed bieżącym iloczynem, a ogon q8_1 idzie przez LDS i jedną barierę zamiast fence + atomika ticketu; bitowo identyczny z produkcją.
- [[mmvq-multikolumnowe|MMVQ wielokolumnowe (weryfikacja spekulacji)]] — Kernel matvec, który przy weryfikacji 2–8 tokenów rozpakowuje wagi raz i mnoży je przez wszystkie kolumny; podstawa całego przyspieszenia spekulacji MTP/DFlash na RX 7900 XTX.
- [[gumbel-max|Op `GGML_OP_GUMBEL_MAX` (draft MTP ze sprzężonym szumem)]] — Nowy op ggml (CPU `ggml-cpu/ops.cpp`, HIP/CUDA `ggml-cuda/gumbel-max.cu`) zastępuje `ggml_argmax` w grafie łańcucha MTP: top-k → top-p → min-p → /T + szum Philox4x32-10 kluczowany (seed, pozycja, token) na wierszu 65536 tokenów słownika draftu; wybiera bitowo to samo co CPU i łańcuch samplera celu.
- [[pamiec-stanu-gdn|Pamięć stanu GDN w Qwen3.8-27B]] — Połówkowy czas zaniku stanu GDN przy zerowym wejściu (2304 głowice = 48 warstw × 48): p50 25 tokenów, p90 1 010, p99 2 574, maksimum 18 132 – stan ma pamięć wykładniczą z długim ogonem (raport 21e, analiza wag na CPU, 2026-10-19).
- [[para-mmvq|Para MMVQ jedną siatką (0024)]] — Dwa MUL_MAT tego samego typu na tym samym wejściu (ffn up/gate, GDN qkv/z) liczone jednym uruchomieniem kernela zamiast dwóch.
- [[pdl-mmvq-trigger|PDL w MMVQ użyty tylko w połowie (CUDA sm_90+)]] — Gęsty `mul_mat_vec_q` woła `ggml_cuda_pdl_sync()` przed jakimkolwiek odczytem wag (`mmvq.cu:1530`) i nigdy nie woła triggera (`ggml_cuda_pdl_lc` jest tylko w `mul_mat_vec_q_moe`, `:1980`), więc PDL ukrywa dziś tylko launch i prolog, a nie rampę strumienia wag (raport 21b, 2026-10-19).
- [[mmvq-prefetch-l2|Prefetch L2 w pętli MMVQ: włączony tylko na DGX Spark]] — Upstream włącza prefetch L2 w pętli MMVQ tylko dla `GGML_CUDA_CC_DGX_SPARK` (`mmvq.cu:1703`); na GB10 przy 5 kolumnach dał Q4_K +2.89%, Q5_K +3.90%, Q6_K +6.19%, przy 1 kolumnie ~0, a teza „na kartach z większym pasmem nie pomaga” nie ma danych (raport 21b, 2026-10-19).
- [[prefill-mmq-fa|Prefill: kafle MMQ i FA (K5 + T3, 0040–0045)]] — Runda prefillu z 2026-10-14: lepszy wybór kafla MMQ, kafel FA bez spilli z bitową kolejnością chunków i lżejsza warstwa MTP dla wierszy promptu.
- [[pm4-replay|Replay grafu dekodowania jako bufor PM4 (0060, 0061, 0063)]] — Przechwycony graf HIP jest przebudowany w jeden bufor poleceń PM4 wysyłany jednym pakietem AQL na własnej kolejce ROCr; granica między kernelami spada z ~2.75 µs do ~0.46–0.86 µs.
- [[rmsnorm-dpp|rms_norm·mul(+q8_1) z redukcjami DPP (0025)]] — Rozwinięty kernel normy RMS dla 2048–8192 kolumn: wszystkie ładowania naraz i redukcje przez DPP; 5.87 → 4.51 µs przy 5120 kolumnach.
- [[sampler-fast-path|Szybka ścieżka samplera (0031, 0048, 0065–0069)]] — Sampler wybiera top-k bez sortowania całego słownika (128k LFM / 248k Qwen); kolejne łatki usunęły sytuacje, w których klient (web UI, kary, gramatyka narzędzi) po cichu wracał na wolną ścieżkę.
- [[vulkan-mmvq|Vulkan RDNA: matvec i MMVQ (0006–0010)]] — Pięć łatek backendu Vulkan (RADV) z 2026-10-12, zanim ROCm został stałym backendem; dziś poza domyślną ścieżką.
- [[attn-prep-fwht|Wejście atencji jednym kernelem i rotacja Hadamarda (0019, 0057, 0058)]] — Przy rotowanym KV (FWHT) przygotowanie q/k/v i zapis do cache robi jeden kernel zamiast pięciu, a rotację wyjścia wykonuje combine atencji.
- [[wmma-small-n|WMMA small-N: weryfikacja 9–16 tokenów (K4, 0037)]] — Kernel WMMA iu8 (RDNA3) dla weryfikacji 9–16 kolumn, gdzie wielokolumnowe MMVQ (2–8) już nie sięga.
- [[nemotron-kernele-cuda|Łatki CUDA dla Nemotron 3.5 Bolt: TOPK_MOE_NP2, MMVQ_N1_IQ2, IQ2_LUT]] — Trzy przełączniki z gałęzi `nemotron-3090`: fuzja topk-moe dla nietypowych liczb ekspertów (−280 kerneli/token, zmienia bity), IQ2_XXS w ścieżce 2 wierszy na blok (bitowo neutralna) i LUT siatki IQ2 w pamięci współdzielonej (wynik negatywny).
<!-- AUTO:END -->
