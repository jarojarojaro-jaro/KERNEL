---
typ: repo
tags: [repo, kwanty, rocm]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/15e-kwantyzacja-nowa.md:211-214,447,518; ~/KERNEL/product/research/15c-nowe-silniki.md:362
status: do-sprawdzenia
---
# ExLlamaV3 (EXL3)

**Silnik z formatem EXL3 pochodnym od QTIP (trellis), z ROCm in-tree od 2026-10 i obsługą Qwen3.8-27B; w niezależnym teście przy ~140k kontekstu wypadł najlepiej end-to-end.**

- Wersja v1.6.2 (`4c842731`). Qwen3.8-27B 4.0 bpw na gfx1100 ~15 t/s decode (PR #283 `[NIEZWERYFIKOWANE]`).
- Test xenodeve (4070S + 5060 Ti, 9 przebiegów, ~140k kontekstu): EXL3 4.0 bpw ukończył 6/6 zadań kodowych, GSQ IQ3_S-MTP 5/6, NVFP4 3/6; GSQ i NVFP4 psuły tajski przy długim kontekście.
- Kontekst z raportu 15c: na 3090 w LocalMaxxing EXL3 242.1 / 169.6 t/s.
Dla nas: odniesienie jakości przy długim kontekście; silnik Python/NVIDIA-first, nie baza produktu.

## Powiązane
- [[repo/_hub|repo]]
- [[ik-llama-cpp]]
- [[tqllm]]
- [[raport-15e-kwantyzacja-nowa]]
- [[kwanty-gguf]]
