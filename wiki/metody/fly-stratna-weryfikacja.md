---
typ: metoda
tags: [metody, spekulacja, stratne, odrzucone]
aktualizacja: 2026-11-05
zrodlo: ~/KERNEL/product/research/63d-atencja-spec-kwant.md:303-313,432-437; https://github.com/vllm-project/vllm/pull/53987 (scalone 2026-10-19); arXiv 2511.22972
status: aktualne
---
# FLy: stratna weryfikacja z bramką entropii (vLLM)

**Odrzucony token draftu zostaje przyjęty, gdy entropia top-3 celu ≥ 0.3 i W następnych draftów przechodzi weryfikację; rozkład celu nie jest zachowany (vLLM PR #53987, 2026-10-19).**

- Qwen3.8-27B, MTP K=3, W=2, bs=1: MI355X 220.8 → 238.9 t/s (+8.2%), B300 199.0 → 209.6 (+5.3%); akceptacja 61.9 → 71.4%.
- Jakość: pojedyncze przebiegi pass@1 na 100 pytaniach, tylko angielski; autorzy: „not a quality guarantee”.
- U nas szacunek +5…8% na czacie T=1 przy taniej implementacji w ścieżce GPU verify.
- **Odrzucone 2026-11-05**: zmienia wyjście ([[2026-11-05-tylko-bezstratne]]). Bezstratne odpowiedniki zysku z akceptacji: lepsza głowica MTP i dobór n.

## Powiązane
- [[metody/_hub|metody]]
- [[glowica-mtp]]
- [[kontroler-szerokosci-draftu]]
- [[raport-63-synteza]]
