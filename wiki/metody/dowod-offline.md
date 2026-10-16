---
typ: metoda
tags: [metody, proces, gpu-okno]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/research/qwen-round5.md:7,80-85; ~/KERNEL/qwen-opt/research/round6/gdn-bitwise.md:3-4,142-184; ~/KERNEL/qwen-opt/research/round6/test-tooling.md:5,107-127; ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:37,277,292
status: aktualne
---
# Praca offline przed oknem GPU

**Gdy GPU jest zajęte albo zakazane, przygotowujemy zmiany do końca bez niego (kompilacja, ISA, emulacja, dry-run) i zostawiamy gotowe komendy na okno GPU.**

- 2026-10-15 ok. 00:45 użytkownik zakazał pracy na GPU, ok. 02:00 znów pozwolił (qwen-round5). Rundy 5 i 6 powstały w dużej części offline.
- Commity bez pomiaru oznaczamy **UNMEASURED** w wiadomości (np. 0066–0070, commity rundy 5); mierzymy je później i dopisujemy wynik.
- Dowody offline: diff ISA, symboliczny emulator ([[emulator-isa]]), kompilacja wszystkich wariantów tunera, testy `--dry-run` / `--fake` (`loo.py`, `kld_canary.sh`, `kt.py`).
- Każdy raport kończy się listą „Pending GPU commands” z dokładnymi komendami: locki `flock /tmp/gpu.lock flock /tmp/quiet.lock`, sprawdzenie `pgrep -f "llama-server.*--port 8080"`, bloki ≤ 5 min z przerwami.

Efekt na GPU 2026-10-15: GDN fast potwierdzony bitowo przy pierwszym podejściu (67/67 testów, md5 = baza); epilog MMQ (0070) zmierzony i scalony (+2.2% pp4096).

## Powiązane
- [[metody/_hub|Metody]]
- [[serializacja-gpu]]
- [[emulator-isa]]
- [[runda-6]]
- proces-zakaz-gpu
