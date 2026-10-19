---
typ: rocm
tags: [rocm, pm4, rdna3, cwsr]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/17-gpu-page-fault.md:218-232,249-292
status: aktualne
---
# Własny dispatch PM4 na GFX11 musi ustawić `COMPUTE_PGM_RSRC1.PRIV=1`

**Na GFX11 (w tym gfx1100) każdy własny `DISPATCH_DIRECT` musi ustawić `COMPUTE_PGM_RSRC1.PRIV=1` (bit 20) – obejście błędu CWSR DEGFX11_12113; firmware CP robi to sam tylko dla pakietów AQL, więc taśma PM4 kopiująca RSRC1 z deskryptora kernela startuje fale z PRIV=0 (raport 17 §9, 2026-10-19).**

Źródła: F. Kuehling (AMD) o tinygrad – „The GFXv11 GPU line requires a workaround to set COMPUTE_PGM_RSRC1.PRIV=1 … it requires this workaround in its PM4-based dispatch” (gist); kfdtest `Dispatch.cpp#L146-L154` i commit `507637e`; tinygrad `ops_amd.py#L288-L289`; KFD dla GC 11.0.0–11.0.3 dodaje kolejki z `trap_en = 0` (`kfd_dbg_has_cwsr_workaround`).

Inne różnice naszej taśmy wobec kfdtest/tinygrad: inicjator z ORDERED_APPEND_ENBL (bit 3; sterownik ostrzega o złych wave ID po suspend/resume), niezerowane `COMPUTE_RESTART_X/Y/Z`, polityka cache IB 3 (nieudokumentowana), DISPATCH_DIRECT w IB pakietu vendor kolejki AQL (kombinacja nietestowana przez AMD). Prototyp `GGML_HIP_PM4_WA=1/2` (`b7fb3fe85`).

## Powiązane
- [[rocm/_hub|ROCm]]
- [[pm4-replay]]
- [[kfd-ewikcja-kolejek-gfx11]]
- [[lekcja-wlasny-pm4-musi-robic-to-co-firmware]]
