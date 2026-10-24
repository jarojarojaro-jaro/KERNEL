---
typ: research
tags: [research, cache, serwer, kwanty]
aktualizacja: 2026-10-24
zrodlo: ~/KERNEL/product/research/60d-serving-kernels-cache.md:28-53,248-285
status: aktualne
---
# Raport 60d: Humming, SGLang HiCache, AKV, sonar #1788, Maya v1.1.21–1.1.26

**Dla XTX nic kernelowo nowego: Humming jest tylko CUDA i przy M=1 ma 60% pasma, sonar #1788 to all-reduce sm_120/P2P/TP=4, Maya to DeepSeek. Wartość jest w cache sesji agentów (HiCache): pinned staging wpisu `--cache-ram`, lekki wpis „prefiks systemowy” z checkpointem GDN i eviction według `prompt_cache_key`, szacunkowo start sesji 1.6 → ~0.5 s (2026-10-24).**

- AKV: repozycjonowanie RoPE niemożliwe przy IMROPE Qwena; drop tylko w warstwach atencji; najpierw test sufitu na transkryptach.
- sonar #1788: +12.7% dekodu na 4× RTX PRO 6000 (TP4, ≤8 wierszy BF16); nie dotyczy.
- Maya: na 2× XTX batchowanie kwantyzacji q8 nie dało nic (12.5 vs 13.1 t/s), bo gap launchu 3.3 µs przy ~2 µs pracy. Wzorzec all-reduce bez P2P przez copy engine.
- Testy T1–T7 w `~/KERNEL/product/DO-PRZETESTOWANIA.md`.

## Powiązane
- [[research/_hub|research]]
- [[humming]]
- [[sglang-hicache]]
- [[akv-cache-agentow]]
- [[project-maya]]
- [[opoznienia-ttft]]
