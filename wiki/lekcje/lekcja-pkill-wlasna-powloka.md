---
typ: lekcja
tags: [lekcje, chmura, proces]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/16c-kvq-cuda.md:43,207-209; ~/KERNEL/product/research/16d-magnitude-vs-nasz.md:174; ~/KERNEL/product/research/16e-kwanty-kld.md:307
status: aktualne
---
# `pkill -f` przez ssh zabija własną powłokę; zadania GPU pod flock

**W E1 `pkill -f "bench.sh"` wysłane przez ssh dopasowało też własną powłokę zdalną i ją zabiło, a jeden przebieg perf nałożył się na llama-bench i trzeba go było wyrzucić z tabel (`perf/excluded/`) (2026-10-16).**

Reguły:
- `pkill -f` z wzorcem, który nie występuje w samej komendzie ssh (np. `pkill -f "[b]ench.sh"`) albo zabijanie po PID z pliku;
- każde zadanie GPU na instancji przez `flock /root/gpu.lock`; przebieg z nałożeniem powtarzać od zera.

Ten sam błąd w 16d: wzorzec pasował do linii `bash -c` z tym samym tekstem; pomogło kotwiczenie `^bash ./main.sh`.

E1 (2026-10-18): ten sam błąd rozbroił samozniszczenie instancji 3060 B (uzbrojone ponownie). Na zdalnej maszynie zabijać skryptem z pliku, nie wzorcem w linii ssh.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-zombie-serwery]]
- [[serializacja-gpu]]
- [[harness-chmurowy]]
