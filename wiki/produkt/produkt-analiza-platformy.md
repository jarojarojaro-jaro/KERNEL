---
typ: produkt
tags: [produkt, plan, platforma]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/PLAN.md:252-268
status: aktualne
---
# Analiza platformy (PLAN §4.5)

**Każda łatka, profil i ustawienie dostaje rubrykę „gdzie działa i co się zmienia” na Linux / Windows / macOS; wynik idzie do manifestu jako predykat (np. `os: [linux]`, `runtime: rocr`).**

- AMD: Linux amdgpu + ROCr/KFD (PM4 możliwe); Windows HIP SDK na PAL, nie ROCr → PM4 i łatki zależne od ROCr nie działają; WSL2 (ROCm 10.1 preview) cicho pomija pakiet PM4 → 0060 wyłączać bez `/dev/kfd`.
- NVIDIA na Windows: „Sysmem Fallback” po cichu do RAM (5–30× wolniej); TDR 2 s.
- Usypianie: Linux BACO (4.4 vs 92 t/s) → keepawake; Windows plany zasilania; macOS App Nap.
- Pamięć: Windows Defender skanuje pliki modeli; macOS pamięć zunifikowana.
- Co się przenosi: Linux wszystko; Windows łatki hostowe, sampler, spekulacja, kernele HIP/CUDA bez ROCr/PM4, Vulkan; macOS łatki hostowe, sampler, spekulacja.

## Powiązane
- [[produkt/_hub|produkt]]
- [[produkt-fabryka]]
- [[produkt-platformy-i-lab]]
- [[analiza-platformy]]
- [[raport-08-platforma]]
