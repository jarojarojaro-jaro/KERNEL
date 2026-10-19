---
typ: meta
tags: [meta, rekordy, wyniki]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/BENCHMARKI-PRZED-PO-2026-10-19.md:1-131; ~/KERNEL/qwen-opt/STATUS-NEXT.md:5-13; ~/KERNEL/qwen-opt/NOTES.md:322,331,339,354,368,375,397; ~/qwen-opt/spec_sweep.jsonl (wiersze podane w tabelach); ~/KERNEL/product/research/16b-lookup-tail.md; ~/KERNEL/product/research/16f-xtx-szybkie.md; ~/KERNEL/product/research/16j-magnitude-vulkan-xtx.md; ~/KERNEL/product/research/16d-magnitude-vs-nasz.md; ~/KERNEL/product/research/16c-kvq-cuda.md; ~/KERNEL/product/research/16e-kwanty-kld.md; ~/KERNEL/product/research/14-nemotron-3090.md; ~/KERNEL/product/BENCHMARKI-NVIDIA-2026-10-16.md
status: aktualne
---
# Rekordy: najlepsze zmierzone wyniki

**Najlepsza zmierzona liczba dla każdej pary (karta, model, obciążenie, metryka), z datą, warunkami, źródłem `plik:wiersz` i informacją, czy działa w produkcji (`~/llama-opt`, `amd-opt` @ `f61994f58`, 70 łatek, PM4 włączone).**

Zasada (decyzja użytkownika 2026-10-19): **każdy nowy najlepszy wynik trafia tu od razu** – liczba, data, warunki (skrypt, T, kontekst, flagi, build/commit), źródło i status produkcji ([[KONWENCJE]]). Pełne porównanie przed → po: [[benchmarki-przed-po-2026-10-19]].

Legenda „prod.”: **tak** = ten build i flagi to dziś `run-llm.sh`; **nie** = gałąź/flaga poza produkcją; **był** = zmierzone na produkcji, ale warunki już nieodtwarzalne. Uwaga: raport 17 zaleca `GGML_HIP_PM4=0` – wtedy obowiązują liczby „bez PM4” (Qwen MTP 103.7, Uncensored 109.9, LFM 259.3 t/s, `NOTES.md:375`); decyzja otwarta ([[otwarte-decyzje-produktu]]).

Skrypty: **spec_sweep** = serwer, 6 promptów PL/EN × 3 seedy (1–3), T=1, 400 tok., świeży serwer, mediana; **long_ctx_bench** = serwer, MTP n=4, T=0, 256 tok.; **llama-bench** = `-fa 1 -p 4096 -n 128 -r 2`, KV jak w `run-llm.sh`; **xbench** = workload MagnitudeVs (sweep, copy 64k, code-edit 4 pliki, TTFT); **copy_bench** = zestawy `copy`/`mvs`/`long` ([[zestaw-copy-mvs]]).

## RX 7900 XTX – Qwen3.8-27B UD-Q4_K_XL (ROCm, KV q4_0, MTP n=4 + słownik 64k, głowica IQ4_XS)

| obciążenie / metryka | rekord | data | warunki | źródło | prod. |
|---|---|---|---|---|---|
| spec_sweep, mediana | **109.0 t/s**, 27.74 ms/krok | 2026-10-15 | `run-llm.sh qwen` (ctx 204800), label `final-qwen` | `STATUS-NEXT.md:10`; `spec_sweep.jsonl:189` | tak |
| spec_sweep per prompt | pl-proza 99.8, pl-tech 118.6, **pl-kod 125.3**, en-chat 87.8, en-tech 108.1, en-code 110.0 t/s | 2026-10-15 | j.w. | `spec_sweep.jsonl:189` | tak |
| spec_sweep, run 4 bit-exact (porównanie) | prod 107.7 / 107.6, nowe drzewo 109.0, bitexact 108.3 t/s | 2026-10-17 | `365af3e5e`, ABBA | `12-bit-exact-spekulacja.md:325` | nie (bitexact) |
| spec_sweep, wariant poza produkcją | DRAFT_N=6: 111.0 (pl-kod 124.7); DRAFT_N=5: 111.7 | 2026-10-13/14 | przed PM4, inne n | `spec_sweep.jsonl:113,86` | nie |
| decode MTP, prompt 1.7k (T=0) | **130.2 t/s** | 2026-10-14 | long_ctx_bench, przed PM4, KV draftu q4_0 | `NOTES.md:331` | był (nie powtarzane po PM4) |
| decode MTP 6.6k / 29.5k / 94k | 118.5 / 105.2 / **100.6 t/s** | 2026-10-14 | j.w. | `NOTES.md:331` | był |
| decode MTP, prompt 27 327 tok. | 113.2 t/s (nowe drzewo), prod 111.85 | 2026-10-17 | `365af3e5e`, T=0, 256 tok. | `12-bit-exact-spekulacja.md:326` | prod 111.85 tak |
| code-edit (`mvs`), T=0 | **400.9 t/s** (14.0–14.4 tok/krok) | 2026-10-18 | copy_bench, `LLAMA_SPEC_LOOKUP=3 W=16`, `lookup-tail` @ `586f1d596` | `16b-lookup-tail.md:13-17,102` | nie |
| code-edit (`mvs`), T=1 | 375.8 t/s | 2026-10-18 | j.w. | `16b-lookup-tail.md:103` | nie |
| code-edit bez lookupu | 170.0 t/s (xbench), 166.2 (`mvs`) | 2026-10-18 | MTP4, ctx 67584 / produkcja | `16j-magnitude-vulkan-xtx.md:46`; `16b:13` | tak |
| copy 64k (xbench) | 141.2 t/s | 2026-10-18 | MTP4, ctx 67584 | `16j-magnitude-vulkan-xtx.md:45` | tak |
| copy (zestaw `copy`), T=0 | 355.0 t/s | 2026-10-19 | W16, seria po naprawie wentylatorów | `16b-lookup-tail.md:104` | nie |
| edycja ~30k (`long`), T=0 | 373.5 t/s | 2026-10-19 | W16 | `16b-lookup-tail.md:106` | nie |
| tg128 bez spekulacji | **43.2 t/s** (później ABBA: 43.25 / 43.11 bisekcja, 43.17 / 42.91 run 4) | 2026-10-15 | llama-bench | `STATUS-NEXT.md:10`; `12-bit-exact-spekulacja.md:305,323` | tak |
| prefill pp4096 | **1123.2 t/s** (A/B łatki 0070); pomiar finalny 1115 | 2026-10-15 | llama-bench | `NOTES.md:397`; `STATUS-NEXT.md:10` | tak |
| prefill serwera 1.7k / 6.6k / 29.5k / 94k | 818 / **985** / 945 / 766 t/s | 2026-10-14 | long_ctx_bench | `NOTES.md:331` | był |
| TTFT 94k | **123 s** | 2026-10-14 | long_ctx_bench | `NOTES.md:322` | był |
| prefill ~16k (xbench) | 988 t/s | 2026-10-18 | ctx 67584 | `16j-magnitude-vulkan-xtx.md:48` | tak |
| start nowej sesji agenta po obcym zapytaniu | **1612 ms** (z 8019) | 2026-10-18 | `LLAMA_SERVER_CACHE_SHARE_MIN=1024`, `quickwins` @ `50c3a2f2a` | `16f-xtx-szybkie.md:168-169` | nie |
| wznowienie sesji 53k z SSD | 2.51 s (zamiast ~61.5 s prefillu) | 2026-10-18 | slot save/restore | `16f-xtx-szybkie.md:199` | nie (mechanizm upstream, bez wrappera) |

## RX 7900 XTX – Qwen3.8-27B Uncensored Q4_K_M

| obciążenie / metryka | rekord | data | warunki | źródło | prod. |
|---|---|---|---|---|---|
| spec_sweep, mediana | **115.5 t/s**, 26.68 ms/krok | 2026-10-15 | `run-llm.sh uncensored`, label `final-uncensored` | `STATUS-NEXT.md:11`; `spec_sweep.jsonl:190` | tak |
| spec_sweep per prompt | pl-proza 100.9, pl-tech 123.6, pl-kod 128.3, en-chat 94.4, en-tech 119.4, en-code 111.5 | 2026-10-15 | j.w. | `spec_sweep.jsonl:190` | tak |
| tg128 / pp4096 | 44.0 / 1109 t/s | 2026-10-15 | llama-bench | `STATUS-NEXT.md:11` | tak |
| prefill serwera 6.6k / 29.5k / 94k | 956 / 941 / 762 t/s | 2026-10-14 | long_ctx_bench | `NOTES.md:322` | był |

## RX 7900 XTX – LFM2.5-24B-A2B (ROCm, KV q8_0, ctx 131072)

| obciążenie / metryka | rekord | data | warunki | źródło | prod. |
|---|---|---|---|---|---|
| spec_sweep (`lfm none`), Q5_K_M | **293.8 t/s** (r4); finalny pomiar 293.7, 3.41 ms/token | 2026-10-14 / 15 | `run-llm.sh lfm` | `spec_sweep.jsonl:172,191`; `STATUS-NEXT.md:12` | tak |
| tg128 / llama-bench przy 0 | 294.8 t/s (głębokość 0); finalny tg128 289.7 | 2026-10-14 / 15 | llama-bench | `NOTES.md:375`; `STATUS-NEXT.md:12` | tak |
| tg przy 98k | **213.0 t/s** | 2026-10-14 | llama-bench, KV q8_0 | `NOTES.md:375` | tak |
| prefill pp4096 | **7148 t/s** (`-b/-ub 2048`); produkcja (ub 512) 6175 | 2026-10-18 | llama-bench `-r 3` | `16f-xtx-szybkie.md:12,59`; `STATUS-NEXT.md:12` | 7148 nie, 6175 tak |
| prefill pp16384 | 6680 t/s (ub 2048) | 2026-10-18 | j.w. | `16f-xtx-szybkie.md:59` | nie |
| TTFT 2k / 8k / 32k | 331 / 1251 / 5690 ms (ub 2048); produkcja 366 / 1473 / 6676 ms | 2026-10-18 | serwer, świeże prompty | `16f-xtx-szybkie.md:67-69` | nie / tak |
| xbench Q4_K_M: sweep / copy 64k / code-edit | 323.0 / 247.3 / 312.0 t/s | 2026-10-18 | ten sam plik co Magnitude (Q4_K_M) | `16j-magnitude-vulkan-xtx.md:59-61` | flagi tak, plik Q4_K_M nie |
| prefill 64k (xbench) | 14.6 s; ~16k 6026 t/s | 2026-10-18 | j.w. | `16j-magnitude-vulkan-xtx.md:63-64` | j.w. |
| start sesji agenta po obcym zapytaniu | 166 ms (`LFM2_MSG_SPANS=1`), 230 ms (`CACHE_SHARE_MIN`) | 2026-10-18 | `quickwins` | `16f-xtx-szybkie.md:169-170` | nie |

**LFM2.5 Uncensored AD-Q5_K_M:** spec_sweep **267.3 t/s**, 3.74 ms/token (2026-10-15, `STATUS-NEXT.md:13`, prod. tak); tg128 / pp4096 264.3 / 6291 (tamże); llama-bench tg128 z `GGML_HIP_MOE_GU_BLOCK` 268.27 t/s (2026-10-18, `16g-lfm-moe-pasmo.md:88`, prod. nie).

## NVIDIA (chmura; fork z profilem karty)

| karta / model | obciążenie / metryka | rekord | data | warunki | źródło | prod. |
|---|---|---|---|---|---|---|
| 3090 / Qwen 27B Q4_K_XL | spec_sweep | **78.0 t/s** (A0 38.9) | 2026-10-16 | kampania NVIDIA, `cuda-3090-opt` | `BENCHMARKI-PRZED-PO:96` (`NV:28-36`) | gałąź CUDA |
| 3090 / Qwen | code-edit / copy 64k (xbench) | 121.1 / **94.0 t/s** (fork + DFlash2); MTP 105.2 / 69.3 | 2026-10-16 | ABBA | `16d-magnitude-vs-nasz.md:66-67` | nie (DFlash2) |
| 3090 / Qwen | MTP przez serwer @59k | **89.75 t/s** (kvq) | 2026-10-16 | `kvq-cuda` @ `f08dc78bb` | `16c-kvq-cuda.md:120` | nie |
| 3090 / Qwen | tg64 @64k | 39.14 t/s (kvq); z wyjątkiem n=1 (`678473a27`) 27.40 | 2026-10-16 / 18 | llama-bench, KV q4_0 | `16c-kvq-cuda.md:9,212` | nie |
| 3090 / Qwen | prefill 64k (xbench) | 888 t/s; TTFT 2k 1.68 s | 2026-10-16 | `cuda-3090-opt` | `16d-magnitude-vs-nasz.md:68` | gałąź CUDA |
| 3090 / LFM Q5_K_M | spec_sweep | **263.9 t/s** | 2026-10-16 | kampania NVIDIA | `BENCHMARKI-PRZED-PO:97` | gałąź CUDA |
| 3090 / LFM Q4_K_M | xbench sweep / code-edit; pp 2k / 16k | **291.6** / 280.4 t/s; **7907 / 7995** t/s | 2026-10-16 | `cuda-3090-opt`, `-b/-ub 2048` | `16d-magnitude-vs-nasz.md:70,72-73` | gałąź CUDA |
| 3090 / LFM | tg64 @64k | 208.12 t/s (kvq) | 2026-10-16 | `kvq-cuda` | `16c-kvq-cuda.md:9` | nie |
| 3090 / Nemotron 3.5 Bolt 74B-A9B IQ2_XXS | spec_sweep (DFlash) | **141.1 t/s** (A0 87.2); tg128 96.7 | 2026-10-16 | `nemotron-3090` | `14-nemotron-3090.md:77-83` | gałąź |
| 3090 / Nemotron | tg przy 0 / 32k / 64k (bez spekulacji) | tuned q8_0 91.4 / 79.9 / 69.4 t/s; przy 64k lepszy upstream z KV f16: 82.5 | 2026-10-16 | KV q8_0 vs f16 | `14-nemotron-3090.md:95-97` | gałąź |
| 5060 Ti / Qwen 27B Q3_K_XL | spec_sweep | **58.0 t/s** (xbench sweep, 16d); kampania 51.66 | 2026-10-16 | `cuda-v070-5060ti` @ `0488cba76` | `16d-magnitude-vs-nasz.md:74`; `BENCHMARKI-PRZED-PO:98` | gałąź CUDA |
| 5060 Ti / Qwen Q3_K_XL | code-edit / copy (xbench) | 98.2 / 52.0 t/s | 2026-10-16 | j.w. | `16d-magnitude-vs-nasz.md:74` | gałąź CUDA |
| 5060 Ti / Qwen Q3_K_XL | tg64 @64k | 25.69 t/s (kvq, KV q8_0) | 2026-10-16 | `kvq-cuda`, sm_120 | `16c-kvq-cuda.md:11` | nie |
| 5060 Ti / LFM Q4_K_M | spec_sweep | **207.86 t/s**; xbench (ctx 32k) 205.1 | 2026-10-16 | kampania / 16d | `BENCHMARKI-PRZED-PO:99`; `16d:75` | gałąź CUDA |
| 5060 Ti / LFM QAD-Q4_0 | serwer | **226.8 t/s** | 2026-10-16 | md5 = upstream | `BENCHMARKI-PRZED-PO:100` | gałąź CUDA |
| 5060 Ti / LFM Q4_K_M | pp4096 | **6587 t/s** (`-ub 2048`) | 2026-10-16 | llama-bench | `BENCHMARKI-PRZED-PO:99` | gałąź CUDA |
| 5060 Ti / LFM | tg64 @64k | 155.77 t/s (kvq) | 2026-10-16 | `kvq-cuda` | `16c-kvq-cuda.md:11` | nie |
| 5060 Ti / Qwen3.5-9B | sweep / code-edit / copy 64k | 121.0 / 239.0 / 128.1 t/s; prefill 64k 2343 t/s | 2026-10-16 | 1 runda | `16d-magnitude-vs-nasz.md:110-114` | gałąź CUDA |
| 3060 / Saluki 27B IQ2 | spec_sweep / z MTP Kujiry | 23.4 / **33.1 t/s** (170 W) | 2026-10-16 / 18 | kampania / E1 host B | `BENCHMARKI-PRZED-PO:101`; `16e-kwanty-kld.md:247` | gałąź CUDA |
| 3060 / Bonsai 27B | serwer | **44.9 t/s** (Prism PTQ1_0); nasz Q2_0 35.5 | 2026-10-18 / 16 | fork Prism / nasz | `16e-kwanty-kld.md:249`; `BENCHMARKI-PRZED-PO:102` | nie (Prism) / gałąź |
| 3060 / Swift IQ3_XXS-mtp (W3) | MTP n=2 | 25.15 t/s (host 120 W) | 2026-10-18 | E1 host A | `16e-kwanty-kld.md:239` | nie |

## Jak dopisywać
1. Nowy wynik lepszy od wiersza w tabeli (ta sama karta, model, obciążenie, metryka i porównywalne warunki) → podmień liczbę, zostaw poprzednią w nawiasie albo w nowym wierszu „wariant”, dopisz datę, warunki, `plik:wiersz` i status prod.
2. Nowa para (karta, model, obciążenie, metryka) → nowy wiersz.
3. Wpis w [[log]] i wiersz w [[AUDYT]].

## Powiązane
- [[index|Strona główna]]
- [[benchmarki-przed-po-2026-10-19]]
- [[stan-2026-10-15]]
- [[nvidia-wyniki-2026-10-16]]
- [[otwarte-decyzje-produktu]]
