---
typ: narzedzie
tags: [narzedzia, monitor, tui]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/monitor/README.md:1-25; ~/KERNEL/monitor/*.py (wc -l: reactor.py 1045, razem 2183)
status: aktualne
---
# REACTOR (monitor terminalowy)

**Pełnoekranowy monitor GPU/CPU/LLM w terminalu dla serwera z RX 7900 XTX, w czystym Pythonie 3.12 (tylko stdlib) z 24-bitowymi kolorami ANSI.**

Pokazuje: GPU z sysfs/hwmon amdgpu (obciążenie, VRAM, temperatury edge/junction/mem, moc względem limitu 285 W, zegary z oznaczeniem GFXOFF, PCIe, DPM, procesy KFD), CPU (16 wątków, Tctl, NVMe), procesy, I/O, LLM (model z linii poleceń, bieżące t/s z `print_timing … tg_3s` w `~/qwen-opt/logs/latest.log`, szczyt, średnia 2 min) i wykresy ~2 min (2 Hz). Pliki: `reactor.py` (1045 linii), `sensors.py`, `gfx.py`, `core3d.py`; skrót `~/.local/bin/reactor`. PLAN: wygląd TUI produktu na bazie REACTOR-a.

## Powiązane
- [[narzedzia/_hub|narzedzia]]
- [[gpu-keepawake]]
- [[wiki-py]]
- [[amdgpu-moc-i-termika]]
- [[produkt-dla-kogo-i-ekrany]]
