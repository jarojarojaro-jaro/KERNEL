---
typ: research
tags: [research, kwanty, nvfp4, gsq]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/15e-kwantyzacja-nowa.md:1-62,273-287; ~/KERNEL/product/research/16e-kwanty-kld.md:267-292
status: aktualne
---
# Raport 15e: nowe formaty niskobitowe dla 27B na 12–16 GB

**GSQ-RCO jest „SOTA” tylko w wąskiej klasie, Swift 1.5 to fine-tune z niedouczoną głowicą MTP, CSF/QAD (NVFP4) są poza naszymi kartami, a największy zysk na 12 GB to MTP na istniejących 2-bitowych plikach.**

Raport 2026-10-16, bez GPU, trzy eksperymenty CPU.
- 2 bity nie są szumem, ale są wyraźnie stratne: ISTA GSQ-RCO IQ2_XS (8.42 GB) KLD do BF16 0.194 (ctx 512) / 0.204 (ctx 2048); UD-Q4_K_XL 0.012.
- GSQ-RCO IQ3_S (11.29 GiB) ma na wikitext gorszy KLD niż UD-IQ3_S tej samej wielkości (0.0665 vs 0.0470, protokół agentionai); trellis KTopt z ik_llama (10.31 GB) 0.043/0.066 vs GSQ IQ3_XXS 0.060/0.078.
- Swift 1.5 (UkisAI): RL/OPD fine-tune na krótsze myślenie (−41.9% średnio, −58.5% mediana tokenów GPQA-D przy +0.31 pp); alokacja kwantów 1:1 jak ISTA; głowica MTP bajtowo identyczna z Qwenem; licencja komercyjnie tylko < US$1M.
- „Nowa technika NVFP4”: CSF (bezstratna kompresja skal, 53–55% rozmiaru skal) i QAD (GPQA-D 91.5 vs 92.2) dla Flash-Next 96 GiB – nie dla 16/24 GB.
- Znalezisko: kwantyzator NVFP4 w ggml nie ma skali globalnej ani imatrix → 99.8–100% subnormalnych skal UE4M3; skala globalna obniża rel-MSE wag o 22–35% (symulacja CPU).
- Najlepszy zysk/koszt: Saluki z doszczepioną głowicą MTP (Kujira) na RTX 3080 12 GB 41.2 → 66.2 t/s (×1.61).
- Kompresja skal K-quantów odrzucona (sufit 2.19%).
- 16 GB: zostać przy UD-Q3_K_XL albo AP-Q3_K_XL (KLD held-out −19.5% przy tych samych bajtach).
Ranking: 1. MTP na 2-bitowych 27B, 2. AP zamiast UD, 3. Swift jako „krótkie myślenie” (warunkowo licencja), 4. naprawa kwantyzatora NVFP4. E1 ≈ $5–8 albo ≈ $1.5–2 + CPU (wymaga zgody).

Wynik E1/E3: [[raport-16e-kwanty-kld]] – H1 i H3 potwierdzone, H2 na granicy, kill GSQ 16 GB zadziałał, E3 zamknięte.

## Powiązane
- [[research/_hub|research]]
- [[swift-1-5]]
- [[kwanty-gguf]]
- [[saluki]]
- [[nvfp4]]
- [[lekcja-kld-protokoly]]
