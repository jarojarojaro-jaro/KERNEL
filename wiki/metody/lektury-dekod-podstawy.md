---
typ: metoda
tags: [metody, nauka, dekod, spekulacja]
aktualizacja: 2026-11-23
zrodlo: https://x.com/cheese_cakee_9/status/2123723211602891249 (2026-11-20; Telegram właściciela 2026-11-23); log.md 2026-11-19 (kipp.ly)
status: aktualne
---
# Cztery podstawowe lektury o dekodzie LLM (i co z nich już stosujemy)

**Kanon „od pierwszych zasad” dla dekodu: arytmetyka inferencji (kipply), Flash-Decoding, gpt-fast i oryginalna praca o spekulacji; wszystkie cztery mechanizmy są już u nas w użyciu, więc to lista do nauki i wdrażania nowych osób, nie źródło nowych dźwigni.**

1. [kipply: Transformer Inference Arithmetic](https://kipp.ly/transformer-inference-arithmetic/): dekod ograniczony pasmem (bajty wag ÷ pasmo), prefill obliczeniami. U nas: tabela sufitów [[skill-io-sufity]] i model kosztu kroku.
2. [Flash-Decoding (Tri Dao i in., 2023)](https://crfm.stanford.edu/2023/10/12/flashdecoding.html): podział długiego KV na kawałki liczone równolegle i redukcja na końcu, żeby przy batch 1 i długim kontekście zająć całą kartę. U nas: split-KV w FA llama.cpp (dekod przy 94k–255k).
3. [PyTorch gpt-fast](https://pytorch.org/blog/accelerating-generative-ai-2/): CUDA graphs, kwantyzacja int8/int4 wag, spekulacja i tensor parallel w ~1000 liniach. U nas: grafy HIP + taśma [[pm4-replay]]; kwantyzacji dla prędkości nie zmieniamy (zasada bezstratności).
4. [Leviathan i in., „Fast Inference from Transformers via Speculative Decoding”, arXiv 2211.17192](https://arxiv.org/abs/2211.17192): bezstratne próbkowanie z odrzuceniem — rozkład wyjścia identyczny jak bez spekulacji. To podstawa reguły, że raportujemy tylko wynik ze spekulacją ([[lekcja-tylko-wynik-ze-zgadywaniem]]); gdy drafter losuje zachłannie przy T>0, akceptacja spada (Inkling DSpark, poprawka r8).

## Powiązane
- [[podrecznik-gpu]]
- [[skill-io-sufity]]
- [[lekcja-tylko-wynik-ze-zgadywaniem]]
