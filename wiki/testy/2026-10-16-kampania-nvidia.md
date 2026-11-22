---
typ: test
tags: [testy, nvidia, chmura, faza-0]
aktualizacja: 2026-11-22
zrodlo: ~/qwen-opt/cloud/PLAN-TESTOW.md:1-6,51-71,162-178; ~/KERNEL/product/research/09-chmura-3090.md:3-7,176-185; ~/KERNEL/product/research/09-chmura-5060ti.md:3-5,189-191,205-212; ~/KERNEL/product/research/09-chmura-3060.md:3-5,225-231; ~/KERNEL/product/research/09-chmura-3090.md:40-72,201-233; ~/KERNEL/product/research/09-chmura-5060ti.md:59-89,214-256; ~/KERNEL/product/research/09-chmura-3060.md:64-127,233-275; ~/qwen-opt/cloud/results/{3090,5060ti,3060}-20261016/scorecard.json; ~/KERNEL/product/research/14-nemotron-3090.md:216-231
status: aktualne
model: qwen3-8-27b
karta: rtx-3090
wyniki:
  - qwen3-8-27b | rtx-3090 | 78.0 t/s | dekod MTP T=1; UD-Q4_K_XL fork (A1 63.3) | 2026-10-16
  - lfm2-5-24b-a2b | rtx-3090 | 263.9 t/s | dekod T=1; Q5_K_M fork (A1 176.0) | 2026-10-16
  - qwen3-8-27b | rtx-5060-ti | 51.66 t/s | dekod MTP T=1; UD-Q3_K_XL fork (A1 37.32) | 2026-10-16
  - lfm2-5-24b-a2b | rtx-5060-ti | 207.86 t/s | dekod T=1; Q4_K_M fork (A1 144.47) | 2026-10-16
  - saluki | rtx-3060 | 23.4 t/s | dekod T=1; IQ2-mix fork (A1 22.3) | 2026-10-16
  - bonsai | rtx-3060 | 35.5 t/s | dekod T=1; Q2_0 repack fork (A1 33.1) | 2026-10-16
---
# 2026-10-16: pierwsza kampania na kartach NVIDIA (Vast)

**Faza 0 E2/E4 zakończona: trzy karty (RTX 3090, 5060 Ti, 3060) równolegle, ≈ $2.77 z $5; łatki budują się i działają na NVIDIA, dają ×1.4–2.0 na Qwen/LFM, ale greedy nie jest bitowo równy upstreamowi.**

Konfiguracje: A0 upstream tylko `-m`, A1 najlepsze flagi upstream, A2 fork z flagami A1 (+ słownik draftu i IQ4_XS dla Qwena), A2-safe fork z 31 przełącznikami = 0, profil per arch. Etapy: test-backend-ops → greedy md5 na świeżych serwerach → bisekcja i diff węzłów → llama-bench ABCDDCBA → spec_sweep ABBA → nsys.

Kryteria (PLAN-TESTOW): S1 kompilacja – tak na sm_86 i sm_120 (sm_89 nietestowane, brak karty); S2 testy op – tak na sm_86, na sm_120 2 FAIL tolerancji w opie forka `GATED_DELTA_NET_PROLOGUE`; S3 greedy A2 = A1 – `DIFF-BUILD`, wytłumaczony łatkami z listy (0001/0002, 0013), KLD na 3060 na poziomie szumu; S4 ms/krok A2 ≤ A1 + 1% – tak, z zapasem; S5 liczby do ekranu wyniku – tak (`scorecard.json` dla 3 kart); S6 koszt ≤ $8 i żadna instancja po terminie – tak.

Koszt: 3090 ≈ $0.90, 5060 Ti ≈ $1.05, 3060 ≈ $0.82.

Incydenty: pierwsza instancja 3090 odrzucała klucz SSH (zniszczona po ~9 min); na 5060 Ti nadpisanie działającego skryptu przez `scp` przerwało fazę pomiaru; pierwsza seria sweepów na 5060 Ti odrzucona przez pułapkę `-fit on`. Szczegóły liczb: [[testy/2026-10-16-kampania-nvidia]].

## Ze scalonej notatki: Wyniki NVIDIA z chmury (2026-10-16, finalne)

Pierwsza runda na trzech kartach NVIDIA zakończona: nasz silnik daje ×1.4–2.0 względem domyślnego llama.cpp na modelach z MTP lub dużym udziałem hosta (Qwen, LFM) i tylko +5–7% na 2-bitowych 27B bez MTP; greedy md5 forka różni się od upstreamu przez łatki bez przełącznika (0001/0002, 0013).

Decode t/s (spec_sweep, 6 promptów × 3 seedy, T=1, ABBA; A0 = upstream tylko `-m`, A1 = najlepsze flagi upstream, „nasz” = fork z profilem):

| karta, model | A0 | A1 | nasz | ×A0 / ×A1 |
|---|---|---|---|---|
| 3090, Qwen3.8-27B UD-Q4_K_XL | 39.0 | 63.3 | 78.0 | 2.00 / 1.23 |
| 3090, LFM2.5 Q5_K_M | 180.2 | 176.0 | 263.9 | 1.46 / 1.50 |
| 5060 Ti, Qwen3.8-27B UD-Q3_K_XL | 28.07 | 37.32 | 51.66 | 1.84 / 1.38 |
| 5060 Ti, LFM2.5 Q4_K_M | 147.69 | 144.47 | 207.86 | 1.41 / 1.44 |
| 3060, Saluki 27B IQ2-mix | 22.1 | 22.3 | 23.4 | 1.05 / 1.05 |
| 3060, Bonsai 2 27B (Q2_0 repack) | — | 33.1 | 35.5 | +7% vs upstream |
| 3090 (druga instancja), Nemotron 3.5 Bolt 74B-A9B IQ2_XXS + DFlash | 87.2 | 131.4 | 141.1 | 1.62 / 1.07 |

- Poprawność: test-backend-ops 3090 19253/19253, 5060 Ti 19251/19253 (2 FAIL tolerancji prologu GDN). Greedy md5 forka ≠ upstream na każdym modelu, także z 31 przełącznikami = 0; przyczyny: MMVQ multi-kolumna 0001/0002 (LFM: build bez multi = md5 upstream) i fuzja prologu GDN 0013 (Qwen). KLD fork vs upstream na 3060: na poziomie szumu (PASS). Na Q4_0 i NVFP4 fork = upstream bitowo.
- Profile: Ampere `GGML_CUDA_MMVQ_N1_ROWS=2` + `GATE_UP_Q8` off; Blackwell `GATE_UP_Q8=0`, `Q8_IDS=0`, bez N1_ROWS.
- Zysk na NVIDIA pochodzi głównie z warstwy hosta (sampler bez wolnych ścieżek, słownik draftu, koszt kroku MTP), nie z kerneli; fuzje tną kernele ~2× (Qwen 1956 → 795/token na 3090), ale grafy CUDA i tak ukrywały większość przerw.
- Ollama 0.40.5 z domyślnymi ustawieniami (3090): Qwen 39.0, LFM 180.5 t/s, czyli tyle co A0.
- Koszt Vast: 3090 ≈ $0.90, 5060 Ti ≈ $1.05, 3060 ≈ $0.82; wszystkie instancje zniszczone.

## Powiązane
- [[testy/2026-10-16-kampania-nvidia]]
- [[narzedzia/skrypty-chmury]]
- [[cuda-compat]]
- [[karty/vast-ai]]
- [[lekcja-nadpisanie-dzialajacego-skryptu]]
