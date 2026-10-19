---
typ: rocm
tags: [rocm, amdgpu, awarie]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/17-gpu-page-fault.md:62-76
status: aktualne
---
# Dekodowanie page faultu amdgpu (gfx11)

**Jak czytać wpisy `[gfxhub] page fault` i `sq_intr` w `journalctl -k` na RX 7900 XTX: pola `GCVM_L2_PROTECTION_FAULT_STATUS`, typy przerwań SQ i komunikaty MES (raport 17, 2026-10-19).**

- `GCVM_L2_PROTECTION_FAULT_STATUS`: bit 0 MORE_FAULTS, bity 4–7 PERMISSION_FAULTS (3 = brak PTE / niedozwolony), bit 8 MAPPING_ERROR, bity 9–15 CID (0x0a SQC data, 0x08 TCP, 0x04 CPF), bit 16 RW, bity 20–23 VMID. Przykłady: `0x00801431` = SQC data, odczyt, VMID 8; `0x00801031` = TCP.
- Wpisy `CB/DB (0x0)` ze STATUS 0 to artefakt: rejestr złapał już pierwszy fault.
- `sq_intr: error … type`: 0 EDC_FUE, 1 ILLEGAL_INST, 2 MEMVIOL, 3 EDC_FED; `priv` = fala w trap handlerze.
- VM fault → KFD ewikuje kolejki procesu; MES: msg 2 ADD_QUEUE, 3 REMOVE_QUEUE, 14 MISC, timeout ~128 ms, potem mode1 reset.
- Historia: `journalctl -k -b <n>` dla każdego bootu ([[lekcja-agent-nie-patrzyl-na-temperatury]]).

## Powiązane
- [[rocm/_hub|ROCm]]
- [[kfd-smi-eventy]]
- [[amdgpu-moc-i-termika]]
- [[2026-10-19-page-faulty-gpu-analiza]]
