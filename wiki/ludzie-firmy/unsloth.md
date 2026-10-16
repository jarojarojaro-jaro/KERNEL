---
typ: firma
tags: [ludzie-firmy, modele, kwanty]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/04-wykrywanie-sprzetu-i-dobor-modeli.md:359-361; ~/KERNEL/product/research/10-post-training.md:339,358
status: aktualne
---
# Unsloth

**Autor kwantów GGUF „UD” (Unsloth Dynamic), z których korzystamy (Qwen3.8-27B UD-Q4_K_XL), oraz narzędzi do fine-tune/QLoRA.**

Benchmarki Unsloth z raportu 04: Qwen3.5 Q4_K_M KLD mean 0,0192 przy 18,49 GB vs UD-Q4_K_XL 0,0137 przy 19,17 GB; Dynamic 3.0 (2026-09/10, Qwen3.8-27B) „>10% top-1 lepiej przy tym samym rozmiarze”. Fine-tune: oficjalnie Qwen3.8-27B, eksport GGUF/NVFP4/FP8; torchao + Unsloth QAT odzyskuje do 66.9% degradacji INT4. Plan nauki: QLoRA Unsloth na Qwen3.5-2B.

## Powiązane
- [[ludzie-firmy/_hub|ludzie-firmy]]
- [[qwen-alibaba]]
- [[ista-daslab]]
- [[kwanty-gguf]]
- [[qwen3-8-27b]]
