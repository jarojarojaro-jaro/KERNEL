---
typ: research
tags: [research, kwanty, nauka]
aktualizacja: 2026-10-21
zrodlo: ~/KERNEL/product/research/57a-gsq-rco.md:7-20
status: aktualne
---
# Raport 57a: GSQ-RCO (ISTA-DASLab), autor i transfer na 24 GB

**GSQ-RCO = GSQ (Gumbel-Softmax PTQ) + RCO (typ per tensor pod dokładny budżet) → standardowy GGUF. Współtwórca z biogramu to Michael Helcig (ETH/ISTA/EPFL). Kod GGUF jest nieopublikowany, a przy ~4 bitach przewaga znika (RCO = EvoPress), więc dla UD-Q4_K_XL na XTX nie ma gotowego zysku (2026-10-21).**

- Do wzięcia: metryka EAR z SLQ (Σmin(p,q)) w naszym narzędziu KLD oraz ewentualnie eksperyment alokacji per tensor ograniczonej do typów z szybkim MMVQ (≤ +7% t/s `[INFERENCE]`, bramka kill).
- 3090: opcjonalnie punkt odniesienia `ISTA-DASLab/Qwen3.8-27B-3Bit-GSQ` w vLLM.

## Powiązane
- [[research/_hub|research]]
- [[ista-daslab]]
- [[raport-15e-kwantyzacja-nowa]]
- [[raport-16e-kwanty-kld]]
- [[kwanty-gguf]]
