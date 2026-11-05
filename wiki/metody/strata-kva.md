---
typ: metoda
tags: [metody, prefill, stratne, odrzucone]
aktualizacja: 2026-11-05
zrodlo: ~/KERNEL/product/research/63d-atencja-spec-kwant.md:191-255; ~/KERNEL/product/research/63a-silniki-lokalne.md:93-122; https://github.com/Niko1221/Strata/blob/9f7d977/docs/KVA.md
status: aktualne
---
# Strata KVA: prefill przez sam stan późnych warstw

**`STRATA_KVA=1` (Strata 0.2.7): dla zimnego promptu ≥ 4096 tokenów warstwy powyżej podziału liczą tylko stan (K/V, rekurencja GDN, conv), a wejściem jest residual z granicy; ostatnie 2048 pozycji i decode są dokładne. To SwiftKV bez destylacji (2026-10-27).**

- Pomiary Straty: RTX 5070 +11% / +18% przy 14K / 30K; R9700 prompt +28%, ale decode −11% (akceptacja MTP 4.08 → 3.33 tok/rundę).
- Split 24 przechodził needle w każdym wariancie, a dawał 0/10 zadań agentowych. **Igła nie jest bramką**; szkody wykrywa ekstrakcja list rekordów i pętla agenta.
- U nas (podział na warstwie 48 z 64) ~−19…−22% TTFT ≥ 8k `[SZACUNEK]`.
- **Odrzucone 2026-11-05** ([[2026-11-05-tylko-bezstratne]]).

## Powiązane
- [[metody/_hub|metody]]
- [[strata]]
- [[latent-sparse-attention]]
- [[tryb-stratny-pflash]]
- [[raport-63-synteza]]
