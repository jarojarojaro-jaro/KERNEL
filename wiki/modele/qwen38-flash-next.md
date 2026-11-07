---
typ: model
tags: [modele, qwen, moe, flash-next]
aktualizacja: 2026-11-06
zrodlo: ~/KERNEL/product/research/66f-flash-next-dobor-kwantu-xtx.md; https://huggingface.co/unsloth/Qwen3.8-Flash-Next-GGUF; https://github.com/Niko1221/Strata/blob/main/docs/MODELS.md
status: do-sprawdzenia
---
# Qwen3.8-Flash-Next (125B MoE, 6B aktywnych, zapowiedź architektury Qwen4)

**Na XTX 24 GB + 62 GB DDR4 najlepiej Strata + GSQ-RCO IQ3_S (54.8 GB + 28.8 GB tabeli n-gramów na SSD); najwyższy mieszczący się kwant to Unsloth v3.1 UD-IQ4_XS (93.7 GB, tylko llama.cpp), a UD-Q4_K_XL (111.3 GB) się nie mieści (raport 66f, 2026-11-06).**

- 48 warstw: 36 GDN + 12 QSA (2 głowice KV × 256), 512 ekspertów top-10 + 1 współdzielony, n-gram 51B, MTP 4B, kontekst 262 144.
- KV przy 262k ok. 7.2 GB f16 (tylko 12 warstw uwagi), więc pełny kontekst bez kwantyzacji KV jest realny.
- Unsloth Dynamic v3.1 (2026-11-04): top-1 / KLD — IQ4_XS 89.6 / 0.084, Q3_K_XL 88.3 / 0.107, Q4_K_XL 92.3 / 0.047.
- Tabela n-gramów (shard 28.8 GB IQ4_NL) czytana losowo kilkoma wierszami na token, może zostać na SSD; do podmiany Q5_1 / Q8_0 / BF16.
- llama.cpp: arch `qwen4exp` upstream, MTP tylko w gałęzi `danielhanchen/llama.cpp:qwen4exp/mtp`; na HIP livelock ładowania #29149 (łatka z buforem pośrednim). Nasz fork topka go nie obsługuje.
- XTX w Stracie (społeczność): IQ3_S 62.3 t/s, DDR5 96 GB; u nas DDR4 → szac. 40–55 t/s, wolniej niż nasz czat 27B (95–217 t/s), ale lepsze benchmarki agentowe (DeepSWE 58.7 vs 42.2).

## Powiązane
- [[modele/_hub|modele]]
- [[strata]]
- [[gyro-coder]]
- [[llama-moe-cache-mib]]
- [[tqllm]]
- [[qwen3-8-27b-uncensored]]
- [[raport-21n-strata-gyro]]
