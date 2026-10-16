---
typ: decyzja
tags: [decyzje, backend]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/NOTES.md:190-191
status: aktualne
---
# 2026-10-12: ROCm stałym backendem

**ROCm jest stałym backendem domyślnym; dalsze optymalizacje robimy pod HIP/ROCm, a Vulkan zostaje tylko jako opcja (`run-llm.sh … vulkan`).**

Zapis w NOTES (sekcja „Decyzja (2026-10-12)”) po pomiarze całego czasu odpowiedzi, w którym ROCm wygrał poza krótkimi promptami. Od tej decyzji łatki Vulkan (0006–0010) mają status historyczny.

## Powiązane
- [[decyzje/_hub|decyzje]]
- [[rocm-vs-vulkan]]
- [[2026-10-12-rocm-vs-vulkan]]
- [[vulkan-mmvq]]
