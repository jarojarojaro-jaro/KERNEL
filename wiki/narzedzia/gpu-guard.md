---
typ: narzedzie
tags: [narzedzia, gpu, bezpieczenstwo]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/qwen-opt/tools/gpu-guard.sh:1-45; ~/KERNEL/AGENTS.md:5
status: aktualne
---
# Strażnik GPU: `qwen-opt/tools/gpu-guard.sh`

**Skrypt odpytuje co 2 s log jądra i sensory XTX; przy zagrożeniu zabija wszystkie `llama-server` / `llama-bench` / `llama-perplexity` / `test-backend-ops` / `magnitude-engine` poza produkcją na :8080, zapisuje powód do `gpu-guard.log` i kończy się kodem 3, który budzi agenta głównego.**

Warunki zatrzymania:
- nowy w `journalctl -k`: page fault amdgpu, timeout ringu, `GPU reset begin`, „MES might be…”;
- hotspot ≥ 100 °C albo VRAM ≥ 98 °C;
- busy ≥ 50% przy wentylatorze < 2500 RPM przez 20 s.

Wczesne ostrzeżenie (bez zabijania, kod 4): VRAM ≥ 85 °C albo hotspot ≥ 90 °C – agent ma zareagować, zanim limity są blisko. Kill najpierw SIGTERM, po 3 s SIGKILL.

## Powiązane
- [[narzedzia/_hub|Narzędzia]]
- [[2026-10-19-bezpieczenstwo-sprzetu]]
- [[lekcja-wentylator-rdna3]]
- [[serializacja-gpu]]
