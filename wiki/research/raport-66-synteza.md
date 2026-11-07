---
typ: research
tags: [research, synteza, konkurencja, kernele]
aktualizacja: 2026-11-07
zrodlo: ~/KERNEL/product/research/66-SYNTEZA.md; 66a-strata-maya.md; 66b-1cat-tokenspeed.md; 66c-hyperkernel-megakernele.md; 66d-saber-engine-rdna.md; 66e-anatomia-serwowania-tqllm.md; 66f-flash-next-dobor-kwantu-xtx.md
status: aktualne
---
# Raport 66: Strata 0.2.12, Maya, 1Cat, TokenSpeed, Hyperkernel, Saber, tqLLM, Flash-Next

**Pakiet nie przynosi przełomu, ale trzy niezależne silniki (1Cat, Saber, tqLLM) pokazują, jak czytać KV raz na weryfikację (plan #8: 199k 74.5 → 77–83 t/s `[SZACUNEK]`); bramką jest 20-minutowy ślad kroku przy 199k, a nowy tani kandydat to Q6_K w MMQ (prefill +1.5…5%, bitowo) (2026-11-07).**

- Top 5 (bezstratne): ślad kroku przy 1.7k/94k/199k (bramka), [[kv-raz-na-weryfikacje]] (+3…11% przy 199k), przegląd podziałów `kvq` (FA 0…−10%), [[mmq-q6k-skale-lds]] (pp +1.5…5%), [[glowica-draftu-rerank]] (+1…3%).
- Maska KQ na hoście kosztuje ~1% przy 199k, a nie 2–6 ms ([[maska-kq-host-dlugi-ctx]]).
- Megakernel: [[hyperkernel]] to tylko binaria B300; pomiar x54 dał +0.24% ([[raport-54-mniej-granic]], [[budzet-megakernela-qwen-xtx]]).
- Nowe notatki: [[prog-draftu-od-kosztu-wiersza]], [[drzewo-weryfikacji-gdn-wy]], [[siatka-checkpointow-gdn]], [[strumien-on-wyrocznia]], [[lekcja-tps-z-zalozonej-akceptacji]], [[lekcja-flaga-bez-dowodu-dzialania]], [[1cat-vllm]], [[tokenspeed]], [[saber-engine]].
- Flash-Next: korekta llama.cpp (MTP w master) i reguł RAM Straty; kwant UD-IQ3_XXS ([[qwen38-flash-next]]).
- Ranking 20 pozycji z bramkami i numerami planu 63: [synteza](../../product/research/66-SYNTEZA.md).

## Powiązane
- [[research/_hub|research]]
- [[raport-63-synteza]]
- [[raport-24h-kv-jeden-przebieg]]
- [[strata]]
- [[project-maya]]
- [[tqllm]]
- [[ZRODLA]]
