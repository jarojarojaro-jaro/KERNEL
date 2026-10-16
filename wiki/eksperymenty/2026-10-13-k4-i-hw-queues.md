---
typ: eksperyment
tags: [eksperymenty, wmma, spekulacja]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/NOTES.md:297-303
status: aktualne
---
# 2026-10-13: K4 (weryfikacja 9–16 tokenów) i GPU_MAX_HW_QUEUES

**Kernel WMMA dla 9–16 kolumn przyspieszył szeroką weryfikację, ale draft ≥ 8 dalej przegrywał przez osobny klif w SSM_CONV; zmienna `GPU_MAX_HW_QUEUES` (pomysł ze Straty) nic nie dała.**

K4 (d3a0973ae, łatka 0037):
- WMMA iu8 small-N (RDNA3) dla 9–16 kolumn (Q6_K od 7); n ≤ 8 bez zmian;
- llama-bench Qwen: n=9 49.2 → 32.1 ms, n=16 51.0 → 35.0 ms; ~0.43 ms na kolumnę;
- serwer: n=5 105.4 t/s średnio (czat/proza słabiej), n=4 101.7;
- n ≥ 8 przegrywa: `SSM_CONV_FUSED_MAX_SNAPSHOTS` 8 → ~470 dodatkowych kerneli cpy/concat na krok (naprawione w T1, [[conv-lag]]);
- pomiar Uncensored przerwany: serwer agenta K4 zostawiony na porcie 8097 trzymał VRAM (zabity).

GPU_MAX_HW_QUEUES (Strata #2305): 3 restarty na ramię (domyślnie, 1, 2, 4): 29.30–29.39 ms/krok we wszystkich; brak bimodalności czasu draftu u nas.

## Powiązane
- [[eksperymenty/_hub|Eksperymenty]]
- [[wmma-small-n]]
- [[2026-10-14-t1-t2-draft]]
- [[serializacja-gpu]]
- strata
