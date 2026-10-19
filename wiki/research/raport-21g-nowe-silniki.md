---
typ: research
tags: [research, konkurencja, silniki]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/21g-nowe-silniki.md:1-430; ~/KERNEL/product/research/21g-notatki/
status: aktualne
---
# Raport 21g: nowe silniki – inferrous, TensorFold 1.1.0, Project Maya 1.1.14–1.1.15, Strata v0.1.44.1–v0.1.45

**Przegląd czterech silników (tylko CPU: kod, release notes, issues, ISA): AMD dalej jest nasze (TensorFold zamroził HIP, Maya nie mierzy XTX), na NVIDIA TensorFold z Qwen3.8-27B + DFlash2 wymaga przeplatanego A/B z naszym forkiem, a najlepszy tani, bitowy pomysł do przeniesienia to bariera tylko LDS na RDNA (Strata #3064).**

Ranking pomysłów: 1) [[bariera-lds-rdna3]] (1–2 dni, bitowo); 2) przełącznik pełnej głowicy draftu przy tokenie spoza 64k (TF #1011; najpierw pokrycie na CPU, kill < 5% okien); 3) wiele slotów dla równoległych agentów omp (kill: łącznie < ×1.2 przy N=2); 4) LFM na 12 GB: `--moe-cache-mib` + rozgrzewka z profilu + auto-off MTP; 5) prefetch L2 w oknach latencyjnych na sm_120 (LFM 5060 Ti ≈ +9% `[INFERENCE]`); dalej autotuning na różnych macierzach, md5-baseline per wersja ROCm/CUDA, pierwszy token przed draftami.

Do produktu: przełącznik „bez przyspieszenia” (przed → po wobec tuned upstream z md5/KLD), paragon ze ścisłym schematem + „Udostępnij wynik”, profile per model, API Anthropic `/v1/messages`, kalibracja zostawiająca funkcję tylko tam, gdzie wygrywa, natywny polski. Wyróżniki: AMD natywnie dla dowolnego GGUF, bit-exact domyślnie, porównanie z tuned upstream, gotowe binarki.

Notatki: [[inferrous]], [[tensorfold]], [[project-maya]], [[strata]], [[lekcja-bit-exact-wobec-siebie]], [[llama-moe-cache-mib]].

## Powiązane
- [[research/_hub|research]]
- [[raport-15c-nowe-silniki]]
- [[raport-21a-dspine]]
- [[produkt-ryzyka]]
