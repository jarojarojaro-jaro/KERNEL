---
typ: eksperyment
tags: [eksperymenty, vulkan, mmvq]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/NOTES.md:162-170
status: nieaktualne
---
# 2026-10-12 (rano): Vulkan krok po kroku

**Ostatnia runda pod Vulkan przed przejściem na ROCm: łatki MMVQ Vulkan skróciły krok o ~5%, adaptacyjna długość draftu nie dała nic.**

Warunki: Vulkan, ctx 204800, 285 W, 6 promptów × 3 seedy, T=1, A/B naprzemiennie 2×.

- Adaptacyjna długość draftu (iloczyn pewności, `--spec-draft-p-cum`, n_max 7/6): najlepsze 80.5 vs 80.3 t/s — usunięte.
- Small-M matvec (ssm_alpha/beta q8_0 m=48): 13.6 → 8.6 µs na wywołanie (~0.5 ms/krok), commit 68e163cf4.
- MMVQ Vulkan (afbb23886, 81e5fb913, f6e5de112, 6c7801bf6): matvec 6 kolumn q5_K 665 → 699, iq4_xs 579 → 663, q4_K 614 → 690 GB/s; Q6_K przez MMVQ (lm_head n=6 1.9 → 1.3 ms).
- ms/krok (serwer): Qwen UD 43.73 → 41.46 (−5.2%), Uncensored 41.93 → 39.92 (−4.8%), powtarzalne co do 0.3 ms.
- Numeryka Q6_K: KLD 0.0042 względem poprzedniej wersji, w granicach szumu batch 6 vs 512 (0.0036); PPL 6.2226 → 6.2099.
- `-bs` (losowanie celu na GPU): pomiar zepsuty obciążeniem CPU, do powtórki.
- GPU w trakcie: 284 W, junction 87°C (max 90).

Status `nieaktualne`: tego samego dnia ROCm został stałym backendem.

## Powiązane
- [[eksperymenty/_hub|Eksperymenty]]
- [[vulkan-mmvq]]
- [[2026-10-12-rocm-vs-vulkan]]
- [[ms-na-krok]]
- [[rocm-vs-vulkan]]
