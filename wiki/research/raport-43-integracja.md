---
typ: research
tags: [research, topka, produkcja]
aktualizacja: 2026-10-21
zrodlo: ~/KERNEL/product/research/43-integracja-2026-10-20.md:1-73
status: aktualne
---
# Raport 43: integracja topki 2026-10-20/21 – zainstalowana f9b84bcfa

**Zainstalowana topka `f9b84bcfa` = safe-special + ckpt-vram + safe-io + latency-tmpl + latency; md5 c4708318/6f14e814/894e56e4 on == off, mvs 433.8 t/s, start Qwen 39.8 → 6.5 s; mmvq-big odrzucony.**

- Etapy: 481254bd3 → c5ba24f8f → f9b84bcfa; rollback kopiami `~/llama-topka.<commit>`.
- Etapy 4–5 (GDN bank, Q5K big_rows, spec-route) zbudowane, bez bramki – GPU zatrzymane ~04:00.

## Powiązane
- [[research/_hub|research]]
- [[raporty-2026-10-20-21]]
- [[REKORDY]]
- [[opoznienia-ttft]]
