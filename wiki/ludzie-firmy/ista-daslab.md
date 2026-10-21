---
typ: firma
tags: [ludzie-firmy, kwanty, nauka]
aktualizacja: 2026-10-21
zrodlo: ~/KERNEL/product/research/10-post-training.md:332-336,416; ~/KERNEL/product/research/15e-kwantyzacja-nowa.md:82,99-128,237; ~/KERNEL/product/research/57a-gsq-rco.md
status: aktualne
---
# ISTA-DASLab

**Grupa z Institute of Science and Technology Austria, autorzy GSQ-RCO: PTQ, która dopracowuje publiczne GGUF K-quanty w tym samym formacie.**

GSQ: inicjalizacja GPTQ, potem Gumbel-Softmax po przypisaniach do siatki i skalach, warstwa po warstwie, optymalizator Lion; format zostaje GGUF K-quant. Przykład: Qwen3-8B Q2_K 50.03 → 56.28. RCO przydziela typ kwantu per tensor pod budżet rozmiaru. Narzędzie testowano na H100. Na tym zbudowano Saluki; Strata też używa GSQ-RCO.

Uzupełnienie (raport 15e): kod refinementu typów IQ nie jest na `main` – na gałęzi z GSVQ dla IQ-quantów MSE wag spadł o 2.6–2.7%, a KL end-to-end wzrósł o 1.9–4.2%; produkcyjna ścieżka dla Qwen3.8-27B GSQ-RCO jest nieopublikowana. RCO: softmax po typach kwantu, rzut gradientu na ograniczenie budżetu i DP plecakowe (`round_with_budget_dp`), wynik jako plik alokacji. Przy ~3.5 bpw KLD gorszy niż UD: IQ3_S 0.0519 (ctx 512) / 0.0665 (ctx 2048) vs UD-IQ3_S 0.0470. Wykres MTP ISTA (akceptacja 54.2%, ~100–118 t/s) bez ujawnionego GPU.

Uzupełnienie (raport 57a, 2026-10-21):
- **Ludzie:** współtwórca GSQ-RCO z biogramu na X to Michael Helcig (X `@mhelcig`, GitHub `helcig`; ETH Zürich CS, visiting EPFL, student ISTA). Jest pierwszym autorem RCO (2605.00649) i SLQ (2605.02404, COLM 2026), a GSQ współtworzył. Kod GSQ pisali głównie Dadgarnia i Tabesh.
- **Kod:** publiczne `IST-DASLab/GSQ@03fc164` nie zawiera kodu GGUF/K-quant na żadnej gałęzi. `RCO@9a1e09c` dobiera tylko bity INT dla HF. Pipeline GSQ-RCO GGUF jest nieopublikowany. `gptq-gguf-toolkit` (GPTQ → Q2_K…Q6_K, EvoPress, stitcher) nie ma licencji.
- **Przy 4 bitach zysk znika:** RCO Qwen3-8B 4.0 bit ma PPL FW 11.16, tyle samo co EvoPress (FP16 10.96). GSQ na GGUF daje Q3_K_M tylko +1.09 pkt. Tieru ≥ 4 bpw nie wydano. Plik IQ3_S ma `output.weight` w Q4_K.
- **SLQ:** EAR = Σmin(p,q) (zgodność tokenów, czyli akceptacja „kwant jako drafter BF16”). Accuracy jest płaskie do KL ≈ 0.01. Siatki symetryczne mają γ² większą wariancję. Qwen3.5-27B: TL 3.30 bpp, DL 5.19 bpp.
- **Inne:** 3Bit-GSQ Qwen3.8-27B (vLLM, compressed-tensors, 11.8 GB); Disaggregated Quantization (2609.26333) z prefillerem NVFP4 i ODP 1.78× TTFT w llama.cpp, co nie dotyczy XTX ani 3090.

## Powiązane
- [[ludzie-firmy/_hub|ludzie-firmy]]
- [[conway-research]]
- [[unsloth]]
- [[saluki]]
- [[kwanty-gguf]]
- [[raport-15e-kwantyzacja-nowa]]
- [[swift-1-5]]
- [[raport-57a-gsq-rco]]
