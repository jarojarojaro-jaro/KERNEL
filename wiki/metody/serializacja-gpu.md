---
typ: metoda
tags: [metody, proces, agenci]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/tools/README.md:3-5; ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:256,269,276; ~/KERNEL/qwen-opt/NOTES.md:160,300; ~/KERNEL/qwen-opt/run-llm.sh:13,31
status: aktualne
---
# Serializacja GPU między agentami

**Wielu agentów dzieli jedną kartę, więc każdy pomiar bierze locki, używa własnego portu i sprząta po sobie serwery.**

Konwencja (tools/README, raport 07):
- `flock /tmp/gpu.lock` (wyłączność GPU) i `flock /tmp/quiet.lock` (brak obciążenia CPU w trakcie pomiaru; kompilacje biorą go jako współdzielony, `flock -s`);
- przed startem: `pgrep -f 'llama-server.*--port 8080'` musi być puste (8080 to domyślny port `run-llm.sh`, czyli serwer do codziennej pracy);
- porty pomiarowe 18433–18499;
- `spec_sweep.sh` dobija serwer SIGKILL po 15 s.

Dlaczego: 2026-10-10 llama-server z DFlash wisiał na SIGTERM, nowy serwer dzielił VRAM ze starym i MTP dał 5.6 t/s; 2026-10-13 serwer agenta K4 zostawiony na porcie 8097 trzymał VRAM i zepsuł pomiar Uncensored (zabity).

## Powiązane
- [[metody/_hub|Metody]]
- [[dowod-offline]]
- [[pomiar-abba]]
- [[spec-sweep]]
- proces-sprzataj-serwery
