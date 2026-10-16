---
typ: rocm
tags: [rocm, rocr, runtime]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/research/lfm-decode-round4.md:18-57,83-90; ~/KERNEL/product/research/08-analiza-platformy-latek.md:14-21,47-68; ~/KERNEL/product/research/13-rocm-10.1.md:27,227-239; rocminfo (odczyt 2026-10-16)
status: aktualne
---
# ROCr (HSA runtime) i KFD

**ROCr to linuksowy runtime niskiego poziomu (HSA) pod HIP: kolejki AQL, sygnały, loader code objectów; rozmawia z jądrem przez `/dev/kfd`. Na nim stoi nasz replay PM4.**

Warstwy na Linuksie: HIP (CLR/ROCclr) → ROCr → libhsakmt → `/dev/kfd` → amdgpu. U nas ROCr 1.21 (rocminfo „Runtime Version 1.21”; 10.1 ma tę samą wersję 1.21.0, loader bez zmian).

Co z ROCr wykorzystujemy w łatce 0060 (PM4 replay):
- własna kolejka (`hsa_queue_create`), pakiet vendor AQL `AMD_AQL_FORMAT_PM4_IB`;
- rozszerzenie loadera (`hsa_ven_amd_loader_*`) do znalezienia deskryptorów kerneli `<name>.kd`;
- alokacja pamięci wykonywalnej (`HSA_AMD_MEMORY_POOL_EXECUTABLE_FLAG`) na bufor IB; bez tej flagi pierwsza próba dała page fault CPF.

Pomiar 2026-10-14: każdy pakiet AQL kosztuje w CP ≥ 2.08 µs niezależnie od bitu bariery; graf HIP używa już najlepszego poprawnego wariantu AQL (fence agent, kernargi w VRAM), stąd ~2.75 µs na granicę.

Gdzie ROCr nie ma:
- **Windows:** HIP działa na PAL, nie na ROCr (próba przełączenia, rocm-systems#8900, zamknięta bez merge 2026-10-04);
- **WSL2 (10.1 tech preview):** jest ROCr, ale przez `librocdxg` i `/dev/dxg`, bez `/dev/kfd`; pakiet PM4 jest domyślnie cicho pomijany.

## Powiązane
- [[rocm/_hub|ROCm]]
- [[pm4]]
- [[pm4-replay]]
- [[hip-na-windows]]
- [[wsl2-rocm]]
