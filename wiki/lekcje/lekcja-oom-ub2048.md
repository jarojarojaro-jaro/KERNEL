---
typ: lekcja
tags: [lekcje, pamiec]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/NOTES.md:218
status: aktualne
---
# -ub 2048 przy ctx 204800 kończy się OOM

**Większy micro-batch daje +3% prefillu w llama-bench, ale serwer z kontekstem 204800 przekracza 24.5 GB VRAM przy pierwszym długim prompcie; zostajemy przy ub 512.**

Test A7 z 2026-10-12. Lekcja ogólna: wynik llama-bench trzeba potwierdzić w docelowej konfiguracji serwera (pełny kontekst).

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[2026-10-12-cache-promptu-i-a7]]
- [[kwanty-gguf]]
- [[rx-7900-xtx]]
