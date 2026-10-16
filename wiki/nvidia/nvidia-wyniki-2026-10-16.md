---
typ: nvidia
tags: [nvidia, wyniki, chmura]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/09-chmura-3090.md:40-72,201-233; ~/KERNEL/product/research/09-chmura-5060ti.md:59-89,214-256; ~/KERNEL/product/research/09-chmura-3060.md:64-127,233-275; ~/qwen-opt/cloud/results/{3090,5060ti,3060}-20261016/scorecard.json
status: aktualne
---
# Wyniki NVIDIA z chmury (2026-10-16, finalne)

**Pierwsza runda na trzech kartach NVIDIA zakończona: nasz silnik daje ×1.4–2.0 względem domyślnego llama.cpp na modelach z MTP lub dużym udziałem hosta (Qwen, LFM) i tylko +5–7% na 2-bitowych 27B bez MTP; greedy md5 forka różni się od upstreamu przez łatki bez przełącznika (0001/0002, 0013).**

Decode t/s (spec_sweep, 6 promptów × 3 seedy, T=1, ABBA; A0 = upstream tylko `-m`, A1 = najlepsze flagi upstream, „nasz” = fork z profilem):

| karta, model | A0 | A1 | nasz | ×A0 / ×A1 |
|---|---|---|---|---|
| 3090, Qwen3.8-27B UD-Q4_K_XL | 39.0 | 63.3 | 78.0 | 2.00 / 1.23 |
| 3090, LFM2.5 Q5_K_M | 180.2 | 176.0 | 263.9 | 1.46 / 1.50 |
| 5060 Ti, Qwen3.8-27B UD-Q3_K_XL | 28.07 | 37.32 | 51.66 | 1.84 / 1.38 |
| 5060 Ti, LFM2.5 Q4_K_M | 147.69 | 144.47 | 207.86 | 1.41 / 1.44 |
| 3060, Saluki 27B IQ2-mix | 22.1 | 22.3 | 23.4 | 1.05 / 1.05 |
| 3060, Bonsai 2 27B (Q2_0 repack) | — | 33.1 | 35.5 | +7% vs upstream |

- Poprawność: test-backend-ops 3090 19253/19253, 5060 Ti 19251/19253 (2 FAIL tolerancji prologu GDN). Greedy md5 forka ≠ upstream na każdym modelu, także z 31 przełącznikami = 0; przyczyny: MMVQ multi-kolumna 0001/0002 (LFM: build bez multi = md5 upstream) i fuzja prologu GDN 0013 (Qwen). KLD fork vs upstream na 3060: na poziomie szumu (PASS). Na Q4_0 i NVFP4 fork = upstream bitowo.
- Profile: Ampere `GGML_CUDA_MMVQ_N1_ROWS=2` + `GATE_UP_Q8` off; Blackwell `GATE_UP_Q8=0`, `Q8_IDS=0`, bez N1_ROWS.
- Zysk na NVIDIA pochodzi głównie z warstwy hosta (sampler bez wolnych ścieżek, słownik draftu, koszt kroku MTP), nie z kerneli; fuzje tną kernele ~2× (Qwen 1956 → 795/token na 3090), ale grafy CUDA i tak ukrywały większość przerw.
- Ollama 0.40.5 z domyślnymi ustawieniami (3090): Qwen 39.0, LFM 180.5 t/s, czyli tyle co A0.
- Koszt Vast: 3090 ≈ $0.90, 5060 Ti ≈ $1.05, 3060 ≈ $0.82; wszystkie instancje zniszczone.

## Powiązane
- [[nvidia/_hub|NVIDIA]]
- [[latki-na-nvidia]]
- [[rtx-3090]]
- [[rtx-5060-ti]]
- [[rtx-3060]]
- [[raport-09-chmura-3090]]
- [[lekcja-md5-wzgledem-upstreamu]]
