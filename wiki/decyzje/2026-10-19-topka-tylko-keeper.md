---
typ: decyzja
tags: [decyzje, topka, serwer, gpu]
aktualizacja: 2026-10-20
zrodlo: ~/AGENTS.md:13; ~/KERNEL/product/research/22-rsi-f.md:74-76,91
status: aktualne
---
# 2026-10-19: topkę (serwer użytkownika na :8080) restartuje tylko `topka-keeper.sh`

**Decyzja (2026-10-19): topkę uruchamia wyłącznie `~/qwen-opt/tools/topka-keeper.sh` (start, gdy blokada GPU wolna, i trzymanie blokady podczas ładowania); agenci mogą ją tylko zatrzymać wewnątrz własnej blokady GPU, nigdy uruchomić, a serwery testowe nigdy nie słuchają na 8080.**

- Przyczyna: fabryka RSI-F zatrzymała topkę przed czekaniem na lock, po ~65 min kolejki :8080 znów wstał, a przy wznowieniu topka padła z OOM, bo cudzy job zajął VRAM (`22:74-76`).
- Poprawka: `--stop-topka` tylko wewnątrz hold każdego bloku, fabryka nigdy nie wznawia topki (`22:91`).
- Powiązane zasady procesów: [[lekcja-zombie-serwery]], [[lekcja-pkill-wlasna-powloka]].

## Powiązane
- [[decyzje/_hub|decyzje]]
- [[raport-22-rsi-f]]
- [[lekcja-zombie-serwery]]
- [[lekcja-pkill-wlasna-powloka]]
- [[2026-10-19-bezpieczenstwo-sprzetu]]
