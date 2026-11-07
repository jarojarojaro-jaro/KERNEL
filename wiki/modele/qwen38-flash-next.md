---
typ: model
tags: [modele, qwen, moe, flash-next]
aktualizacja: 2026-11-07
zrodlo: ~/KERNEL/product/research/66f-flash-next-dobor-kwantu-xtx.md; ~/KERNEL/product/research/66a-strata-maya.md:23-116; https://huggingface.co/unsloth/Qwen3.8-Flash-Next-GGUF; https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF; https://unsloth.ai/docs/basics/dynamic-3.0-ggufs/dynamic-3.1-ggufs.md; https://github.com/Niko1221/Strata (setup.py:3710-3723, docs/MODELS.md:119-134)
status: do-sprawdzenia
---
# Qwen3.8-Flash-Next (125B MoE, 6B aktywnych, zapowiedź architektury Qwen4)

**Na XTX 24 GB + 62.72 GiB DDR4 najlepszy kwant przy tym rozmiarze to Unsloth v3.1 UD-IQ3_XXS (83.6 GB, KLD ~0.052 vs ~0.065 GSQ IQ3_S według stronniczego wykresu Unsloth), w Stracie albo w llama.cpp master ≥ b11330 z MTP; GSQ-RCO IQ3_S zostaje bezpieczną alternatywą w Stracie (raporty 66f i 66a, 2026-11-07).**

- 48 warstw: 36 GDN + 12 QSA (2 głowice KV × 256), 512 ekspertów top-10 + 1 współdzielony, n-gram 51B (shard 28.8 GB, może zostać na SSD), MTP 4B, kontekst 262 144; KV przy 262k ok. 7.2 GB f16.
- **llama.cpp:** `qwen4exp` + MTP w master od b11330 (#29761). Gałąź `danielhanchen` (#28243) zamknięta bez scalenia. Ryzyko: livelock ładowania na HIP #29149. Topka nie ma `qwen4exp`.
- **Strata, dwie reguły RAM:** ISTA trzyma wszystkich ekspertów w RAM przy „eksperci + ~10 GB” (IQ3_S: 50 GB, „with little else open”). Unsloth wymaga „eksperci + 16 GiB”, inaczej budżet RAM − 24 GB (~40 GB) i reszta z SSD. Obie liczby są prawdziwe, dotyczą różnych rodzin. U nas UD-IQ3_XXS brakuje 0.13 GiB, więc ~8 GiB ekspertów z SSD, chyba że wymusimy budżet. UD-IQ4_XS: ~17 GiB z SSD.
- **GSQ-RCO:** GSQ (Gumbel-Softmax PTQ) + RCO (typ per tensor pod budżet). IQ3_S średnia z zadań 93.26 vs BF16 93.12 (małe próby = parytet). Na 27B „task-lossless” przeczą nasze pomiary: E1 KLD-PL 1.77 × UD-Q3_K_XL, MTP −3% ([[2026-10-18-e1-kwanty-27b-kld]]).
- **Unsloth vs GSQ przy 83.6 GB:** odzysk 99.9 vs 99.0%, zadania remis. Wspólnego protokołu KLD nie ma, więc rzetelne porównanie jakości to pytanie otwarte.
- XTX w Stracie (społeczność): IQ3_S 62.3 t/s przy DDR5 96 GB; u nas `[INFERENCE]` ~35–55 t/s, wolniej niż 27B, ale lepiej w zadaniach agentowych (DeepSWE 58.7 vs 42.2).

## Powiązane
- [[modele/_hub|modele]]
- [[strata]]
- [[raport-66-synteza]]
- [[kwanty-gguf]]
- [[lekcja-kld-protokoly]]
- [[ista-daslab]]
- [[llama-moe-cache-mib]]
- [[tqllm]]
- [[raport-21n-strata-gyro]]
