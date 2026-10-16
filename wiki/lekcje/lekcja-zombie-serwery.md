---
typ: lekcja
tags: [lekcje, gpu, proces]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:256,269; ~/KERNEL/qwen-opt/NOTES.md:160,300; ~/KERNEL/qwen-opt/tools/loo.py:9-11
status: aktualne
---
# Zombie serwery i współdzielony VRAM

**DFlash wisiał na SIGTERM, a wynik MTP spadł do 5.6 t/s; serwer agenta K4 na porcie 8097 trzymał VRAM.**

Reguły: SIGKILL po 15 s, locki (`/tmp/gpu.lock`, `/tmp/quiet.lock`), osobne porty dla agentów (np. 18433–18499 w `loo.py`), `pgrep` przed startem i odmowa pracy, gdy działa serwer użytkownika na porcie 8080. Te zasady siedzą w `loo.py` i `kld_canary.sh`.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-obciazenie-cpu]]
- [[lekcja-wolna-sciezka-samplera]]
- [[loo-py]]
- [[serializacja-gpu]]
