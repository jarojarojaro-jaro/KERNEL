---
typ: firma
tags: [ludzie-firmy, modele]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/04-wykrywanie-sprzetu-i-dobor-modeli.md:313,373; ~/KERNEL/product/research/06-produkt-ux-prawo-biznes.md:51; ~/KERNEL/product/research/10-post-training.md:279; ~/KERNEL/product/research/01-konkurencja.md:131; ~/KERNEL/product/research/09-chmura-5060ti.md:177,186,277-278
status: aktualne
---
# LiquidAI

**Twórca rodziny LFM, w tym naszego drugiego modelu LFM2.5-24B-A2B (2026-10-12), na licencji LFM Open License v1.0 z progiem 10 mln USD przychodu.**

Rodzina: LFM2.5-24B-A2B, LFM2.5-8B-A1B (bez polskiego), LFM2.5-2.6B. Licencja: prawa komercyjne tylko poniżej 10 mln USD rocznego przychodu i dotyczy każdego komercyjnego użytkownika, także naszych klientów B2B → LFM w katalogu jako opcja „najszybszy”, nie domyślny. Liquid ma też model decyzyjny d1 (3B) i przejął aplikację Apollo.

Oficjalny `LFM2.5-24B-A2B-GGUF` zawiera wariant QAD-Q4_0 (quantization-aware distillation, 13.58 GB); na RTX 5060 Ti to najlepszy kompromis: KLD jak Q4_K_M, 226.8 t/s w naszym silniku i md5 identyczne z upstreamem. Oficjalny FP8 ma 24.8 GB.

## Powiązane
- [[ludzie-firmy/_hub|ludzie-firmy]]
- [[qwen-alibaba]]
- [[unsloth]]
- [[lfm2-5-24b-a2b]]
- [[produkt-prawo]]
