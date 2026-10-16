---
typ: lekcja
tags: [lekcje, pomiar, cpu]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:276; ~/KERNEL/qwen-opt/NOTES.md:169; ~/KERNEL/product/research/09-chmura-3060.md:19; ~/KERNEL/product/research/14-nemotron-3090.md:22-23
status: aktualne
---
# Obciążenie CPU psuje pomiar

**Równoległe obciążenie CPU (np. kompilacja) zafałszowało pomiar `-bs`, który trzeba było powtórzyć; pomiary GPU robimy pod `quiet.lock` w osobnym oknie.**

Tryb awarii #15. Dekod LFM (~3.4 ms/token) ma dużą część pracy hosta (wysyłka, sampler), więc kompilacja w tle zmienia wynik. To samo na RTX 3060 (2026-10-16): pomiar w trakcie kompilacji dał Saluki 9.7 zamiast 22.5 t/s, więc liczby z tamtych okresów odrzucono. Na RTX 3090 z kwotą 4.6 CPU (Nemotron, 2026-10-16) sondy w trakcie buildu dały 19 zamiast 87 t/s, bo kwotę zajęły 24 procesy nvcc; binaria zbudowano lokalnie. Ta sama obawa dotyczyła słabego CPU na wynajętym 3090.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-zombie-serwery]]
- [[lekcja-slaby-cpu-3090]]
- [[serializacja-gpu]]
- [[latki-hostowe]]
- [[lekcja-limit-cpu-kontenera]]
