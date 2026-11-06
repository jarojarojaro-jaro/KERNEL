---
typ: narzedzie
tags: [narzedzia, monitor, tui]
aktualizacja: 2026-11-06
zrodlo: ~/KERNEL/monitor/README.md:18-33,89-99,114-129; ~/KERNEL/monitor/*.py (wc -l: reactor.py 1467, razem 3087)
status: aktualne
---
# REACTOR (monitor terminalowy)

**Pełnoekranowy monitor GPU/CPU/LLM w terminalu dla serwera z RX 7900 XTX, w czystym Pythonie 3.12 (tylko stdlib) z 24-bitowymi kolorami ANSI.**

Pokazuje: GPU z sysfs/hwmon amdgpu (obciążenie, VRAM, temperatury, moc względem limitu 285 W, zegary, PCIe, DPM, procesy KFD), CPU (16 wątków, Tctl, NVMe), procesy, I/O i LLM z fazą na żywo: `PREFILL 1006 t/s · 8 648 tok · 94%` z paskiem i ETA (linie `prompt processing` z logu, co ubatch, gdy prefill > 3 s), `DECODE` z t/s liczonym co 0,25 s z `n_decoded` z `GET /slots` (≤ 4 Hz, timeout 100 ms, tylko w trakcie żądania), `IDLE` z ostatnim promptem. Dane co 0,25 s, wykresy ~2 min (punkt co 0,5 s). Skrót `~/.local/bin/reactor`.

Płynność przez SSH (2026-11-06): renderer różnicowy na komórkach, kontrola przepływu sondą DSR `ESC[5n` (kolejka tty przez SSH jest pusta, zaległość siedzi w buforach sshd), tryb `ssh-lite` przy `SSH_CONNECTION` (4 fps, 3 odcienie torusa). Pomiar 200x55, 10 s, przy pracującym serwerze: 1,79–1,81 MB → **267–280 KB**, CPU 3,0–3,3% → 2,6–2,9%; emulowany terminal 40 KB/s: zaległość do 30 s → zmiana na ekranie po 0,07–0,10 s. Lokalnie 1,82–1,88 MB → 0,95–1,0 MB, CPU 5,9–6,9%. PLAN: wygląd TUI produktu na bazie REACTOR-a.

## Powiązane
- [[narzedzia/_hub|narzedzia]]
- [[gpu-keepawake]]
- [[wiki-py]]
- [[amdgpu-moc-i-termika]]
- [[produkt-dla-kogo-i-ekrany]]
