# 24u — Samodzielny kernel rms_norm×w + quantize q8_1 (GGML_HIP_NORMQ): STOP, zysk ≈ 0

Data: 2026-10-20. Bez gałęzi, bez buildu, bez czasu GPU. Werdykt oparty na śladzie `~/qwen-opt/vcost/prof/off` (rocprofv3, topka, MTP n=4, prompt mvs-pad.cu, 104 kroki, 31.23 ms/krok, analiza 96 kroków).

## Werdykt

**STOP przed implementacją. Szacowany zysk ≤ 0.012 ms/krok, a próg wynosił 0.25.** Założenie zlecenia było nieaktualne: w topce rms_norm×w i kwantyzacja q8_1 **już są jednym launchem**.
- `rms_norm_mul_f32_unrolled<NV>` (norm.cu) przyjmuje argument `q8` i w tym samym kernelu zapisuje F32 oraz bloki q8_1 (`quantize_q8_1_group<true>`: qs, d, suma).
- Bufor q8_1 wskazuje `ggml_cuda_q8_1_producer_target` (ggml-cuda.cu, cache q8_1 MMVQ, domyślnie włączony). Konsument MMVQ trafia w cache i pomija swój `quantize_q8_1`.
- Mul przez wagę też jest w tym kernelu. Po normie nie ma osobnego `k_bin_bcast`.

Kernel z opisu zadania (jeden launch, F32 + q8_1, ta sama kolejność redukcji) istnieje i jest bitowo zgodny z drogą bez fuzji. Nie ma czego oszczędzać.

## Rozkład w śladzie (ms na krok, launche na krok)

| Kernel | ms/krok | launche/krok | mediana µs | co to jest |
|---|---|---|---|---|
| `rms_norm_mul_f32_unrolled<5>`, 5 wierszy | 0.59 | 132 | 4.48 | norma×w + q8_1 w jednym launchu (weryfikacja n5) |
| `rms_norm_mul_f32_unrolled<5>`, 1 wiersz | 0.08 | 20 | 4.60 (p10 2.16) | to samo w krokach draftu MTP |
| `rms_norm_mul_rope_f32<256,…,256>` | 0.175 | 41 | 2.84 / 5.08 | q/k norm + rope + FWHT |
| `rms_norm_mul_silu_gate_f32<128>` | 0.086 | 48 | 1.80 | bramkowana norma GDN + q8_1 |
| **suma „rms_norm" z tabeli 24k** | **0.93** | 241 | | |
| `k_set_rows_quant<block_q4_0>` | 0.183 | 42 | 4.36 | zapis KV q4_0, **nie** aktywacje q8_1 |
| `quantize_q8_1` | 0.011 | 6 | 2.04 | 5× po `concat_cont`, 1× po `k_get_rows_float` (wejście MTP), **żaden po normie** |
| `k_get_rows_kq` (dequantize_q4_K) | 0.009 | 3 | 2.9 | get_rows embeddingów |
| **suma „quantize" z tabeli 24k** | **0.20** | | | |

- „quantize 0.20 ms" w 24k to klasa z `vc_trace.py`. Wzorzec `quantize` łapie `k_set_rows_quant` (mangled `quantize_f32_q4_0_block`) i `dequantize_q4_K`, zanim zadziała wzorzec `set_rows`/`get_rows`. Kwantyzacja aktywacji do q8_1 kosztuje tylko 0.011 ms/krok.
- Następca normy: 141/152 to `mul_mat_vec_q` (q8_1 z cache). Pozostałe to druga norma (5), `concat_cont` (5) i `k_get_rows_float` (1) w wejściu MTP (enorm/hnorm → concat → eh_proj). Tam kwantyzuje się wynik concat, nie normy.
- Górna granica zysku z fuzji czegokolwiek z pozostałymi `quantize_q8_1`: 6 × 2.04 µs ≈ **0.012 ms/krok** plus przerwy hosta (obszar OptHostGap).

## Gdzie naprawdę idzie 0.93 ms normy (obserwacja, nie zmiana)

Norma 5-wierszowa trwa 4.48 µs (mediana) za dużym MMVQ (129/132 przypadków) i 2.72 µs za małym kernelem (`h2d_scatter`, inna norma). Norma 1-wierszowa: 5.68 µs za dużym MMVQ, 2.36 µs za małym. Inne krótkie kernele też płacą za dużym MMVQ, ale mniej: `unary_gated_op` 2.80 µs (za małym 2.12). Dolna granica krótkiego kernela w tym śladzie to ~1.6–1.8 µs (`rms_norm_mul_silu_gate_f32<128>`, `fwht_cuda`).

- Mechanizm kary „po dużym MMVQ" (+1.8 µs dla normy) jest nieznany z samego śladu. [INFERENCE] Kandydaci:
  - zimne TLB/L2 dla bufora aktywacji i wag normy po strumieniu wag;
  - wygaszanie zegara po fazie pamięciowej.
- Samodzielny kernel tego nie usunie, bo ścieżka krytyczna (load → redukcja → zapis) jest ta sama. Usunąć to może tylko likwidacja granicy kernela, a ogon producenta jest odrzucony w 24l. Prolog normy w konsumencie MMVQ n5 jest nieopłacalny: każdy blok czyta cały wektor wejścia (5×5120 F32 = 100 KB z L2 na blok), co przy ~10³ bloków daje ruch L2 rzędu ×10 wag macierzy.

## Działania

- Bez gałęzi `norm-quant`, worktree i przełącznika `GGML_HIP_NORMQ`: nie ma kodu do napisania. Topka bez zmian. Czas GPU: 0.
- Poprawić etykietę w `vc_trace.py`: `set_rows`/`get_rows` przed `quantize`. Inaczej „quantize" w tabelach kosztu kroku myli zapis KV z kwantyzacją aktywacji.
- Jeśli wracać do norm: najpierw tani pomiar mechanizmu kary 1.8 µs po dużym MMVQ. Przykład: kernel z pustą normą za MMVQ w mikrobenchmarku, z wagami normy w cache i bez. Ewentualny zysk ≤ 132 × 1.8 µs ≈ 0.24 ms/krok przy założeniu, że da się zbić karę do zera.
- `k_set_rows_quant` q4_0 (42 launche, 0.183 ms/krok) to osobny temat, którego nikt nie trzyma. Fuzja zapisu K do `rms_norm_mul_rope` daje ≤ 21 × 4.4 µs ≈ 0.09 ms/krok, czyli też poniżej 0.25.

## Do bazy wiedzy

- W topce norma×w → MMVQ to **jeden launch** z zapisem q8_1 (`rms_norm_mul_f32_unrolled<NV>` / `rms_norm_f32<…,true>` z `q8`, `rms_norm_mul_silu_gate_f32`, `ggml_cuda_q8_1_producer_target`). Wyłącza się to przez `GGML_HIP_NORM_FAST=0` (wariant unrolled) albo przez brak bufora cache q8_1. W kroku MTP zostaje 6 `quantize_q8_1`, wszystkie w wejściu MTP (concat/get_rows).
- Klasa „quantize" w `vc_trace.py` = głównie `k_set_rows_quant` (KV q4_0), nie aktywacje.
- Krótkie kernele uruchamiane bezpośrednio po dużym MMVQ trwają dłużej (norma 5 wierszy: 4.48 vs 2.72 µs; 1 wiersz: 5.68 vs 2.36 µs). Koszt normy w kroku to w ~40% ta kara, a nie praca kernela.
- Skrypt do tej analizy (następcy/poprzednicy kernela i mediany czasów w zależności od poprzednika) da się odtworzyć z `vc_trace.py`: wyznaczenie kroków jak tam, potem `seg[s0+1:s1+1]` i grupowanie po `(nazwa, Grid_Size_X)`.
