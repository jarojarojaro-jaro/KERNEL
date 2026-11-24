---
typ: ekosystem
tags: [ekosystem, kwanty, nauka]
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

## Przegląd 2026-11-24 (nauka, nie tylko prędkość)

- Werdykt „na 24 GB nie dotyczy” patrzył tylko na XTX. Tymczasem nasz **produkt już używa GSQ-RCO**: katalog Enigmy daje Qwen3.8-27B `GSQ-IQ3_XXS` (`ISTA-DASLab/Qwen3.8-27B-GSQ-RCO-GGUF`, plik `-mtp`) na karty 16 GB: 4060 Ti, 5060 Ti, 5080 (`app/engine/src/server/catalog/index.ts:222-236`, `app/engine/data/catalog.json:562-564`).
- Zmierzone w kampanii 67 na prawdziwych kartach: 5060 Ti 229 376 tokenów kontekstu i 43.4 t/s (enigma-cuda-lean), 5080 81.6 t/s; UD-Q3_K_XL na 5060 Ti mieścił tylko 98 304 tokeny, poniżej minimum 131 072 (`catalog/index.ts:231-243`). To dzięki temu plikowi 16 GB w ogóle dostaje 27B z długim kontekstem.
- Napięcie do pamiętania: w niezależnym KLD IQ3_S od ISTA wypadł gorzej niż UD-IQ3_S (0.0665 vs 0.0470, R15e), a dla IQ3_XXS własnego KLD nie mamy. Wybór w katalogu wynika z pamięci, nie z jakości.
- Konkurencja na tych samych plikach: Strata też domyślnie bierze GSQ-RCO (R57b TL;DR 3), a pobrania 27B to 1.29 M — klienci 12–16 GB to duży rynek.
- Czego uczy RCO: dobór typu kwantu per tensor pod dokładny budżet bajtów to dokładnie problem „optimize” w Enigmie (zmieścić model + KV w VRAM klienta). EAR (SLQ) to zrozumiała dla użytkownika metryka „ile tokenów zgodnych z pełnym modelem”.
- Co bierzemy: KLD i jakość-mini dla `GSQ-IQ3_XXS` przed dalszym polecaniem (to już jest K-030 w [[KOLEJKA-TESTOW]], status „czeka na decyzję”); EAR obok KLD w raporcie aplikacji; CompWatch na nowe tiery ISTA, bo każdy dotyczy katalogu.

## Powiązane
- [[conway-research]]
- [[unsloth]]
- [[saluki]]
- [[kwanty-gguf]]
- [[raport-15e-kwantyzacja-nowa]]
- [[swift-1-5]]
- [[raport-57a-gsq-rco]]
