---
typ: research
tags: [research, synteza, konkurencja, metodologia]
aktualizacja: 2026-11-05
zrodlo: ~/KERNEL/product/research/63-SYNTEZA.md; ~/KERNEL/product/research/63-WATKI.md; ~/KERNEL/product/research/63a-silniki-lokalne.md; 63b-colibri-maya-delta.md; 63c-amd-rocm-llamacpp.md; 63d-atencja-spec-kwant.md; 63e-metodologia-agenci.md
status: aktualne
---
# Raport 63: 44 wątki z pakietu 2026-11-03 (silniki, AMD, atencja, spekulacja, metodologia)

**Bezstratnie największy zysk leży w cache promptu agenta (`--cache-ram` 16384 → 40960 + chude checkpointy: tury 85–200 s → ~4–8 s), potem w długim kontekście (profil kroku przy 199k, jedno przejście KV); rekordy z pakietu po normalizacji to parytet albo reklama (2026-11-05).**

- Reguła [[2026-11-05-tylko-bezstratne]]: QSA, LSA, KVA, FLy, KV 3-bit, REAP i zmiany kwantów odrzucone bez rankingu.
- Nowe notatki: [[qwen-qsa-llama-cpp]], [[latent-sparse-attention]], [[rdna-fast]], [[yasakani]], [[qwen-warp]], [[colibri]], [[vllm-rocm-octave]], [[strata-kva]], [[fly-stratna-weryfikacja]], [[wspolny-poczatek-promptu]], [[reward-hacking-inferencji]], [[lekcja-rocm10-lds-128kb]], [[lekcja-gorzka-lekcja-tkcc]], [[lekcja-cache-ram-za-maly]], [[2026-11-05-termika-eco-test]].
- W toku: TopkaQuick63 (cap LDS, MTP lean reserve, poprawki MTP z upstream), EngineBenchFair (G1 benchmarku Enigmy). QSAPort zaparkowany.
- Plan 26 pozycji z wymaganiami (GPU / zgoda / $ / CPU): [synteza](../../product/research/63-SYNTEZA.md), rejestr [wątków](../../product/research/63-WATKI.md).

## Powiązane
- [[research/_hub|research]]
- [[raport-60d-serving-kernels-cache]]
- [[strata]]
- [[project-maya]]
- [[ZRODLA]]
