---
typ: metoda
tags: [metody, strojenie, kernel-tuner]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/tools/README.md:53-75; ~/KERNEL/qwen-opt/research/round6/test-tooling.md:7-11,72-105; ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:332,423-429
status: aktualne
---
# Kernel Tuner: strojenie parametrów kerneli

**Przeszukujemy parametry prawdziwych kerneli ggml (warpy, wiersze na blok) i przyjmujemy tylko konfiguracje bitowo równe produkcji.**

Harness (`tools/kt/kt.py`, gałąź `tools6` @ 4db68c6ab z hakiem `MMVQ_TUNE_NWARPS_N1`, którego build ggml nie definiuje):
- kernele: `mmvq_n1` (Q4_K/Q5_K/Q6_K/Q8_0, 39 kształtów z obu GGUF), `moe_gate_up` i `moe_down` (LFM, 64 ekspertów, 4 aktywne), `gdn` (Qwen: decode i weryfikacja MTP z replay);
- przestrzeń: MMVQ NWARPS {1,2,4,8} × ROWS {1,2,4}; GDN CPW {1,2,4,8,16} × NUM_WARPS {1,2,4};
- pomiar „na zimno”: kopie wag rotowane (256 MiB).

Sprawdzone offline:
- 53 warianty kompilują się dla gfx1100 w 1010 s (-j4);
- `isacheck`: w konfiguracji produkcyjnej harness ma ISA identyczne z produkcją;
- poprawność: tolerancja 2e-4·(|W|·|y|) względem float64, potem osobny test bitowy vs produkcja;
- przykład zasobów: GDN lag1 cpw16 = 256 VGPR i spill, do odrzucenia.

Wynik to tabela `kt-table-gfx1100.{json,inc}`. Strojenie na GPU **jeszcze nie wykonane**. W planie produktu to warstwa L2 „tuning lokalny” i sposób przenoszenia łatek na inne karty RDNA3 bez agenta.

## Powiązane
- [[metody/_hub|Metody]]
- [[mmvq-multikolumnowe]]
- [[gdn-fast]]
- [[emulator-isa]]
- [[rdna3-gfx1100]]
