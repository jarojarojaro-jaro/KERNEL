---
typ: ekosystem
tags: [ekosystem, ocena, konkurs]
aktualizacja: 2026-11-24
zrodlo: ~/KERNEL/qwen-opt/research/repos/09-gpu-mode-reference-kernels.md:1-21; ~/KERNEL/qwen-opt/research/repos/REPOS-PODSUMOWANIE.md:19
status: aktualne
---
# gpu-mode/reference-kernels

**Definicje zadań i harness KernelBota GPU MODE (commit `f3295bb6`, 2026-09-17); ranking 2026 to nie źródło technik; werdykt: niska.**

Repo zawiera tylko wzorce PyTorch, `task.yml` i `eval.py`; zwycięskie rozwiązania (RadeonFlow, seb-v) czytano z zewnątrz. Zwycięzcy konkursu 2026 (MI355X) obchodzili testy albo łatali zależności, więc odrzucamy ranking jako źródło technik. Pomysły dla nas: int8 WMMA dla KQ, build z `-mcumode` (Q6), koszt granicy kernela na poziomie pakietów HSA (L1).

## Przegląd 2026-11-24 (nauka, nie tylko prędkość)
- Ocena „ranking to nie źródło technik” jest słuszna dla kerneli, ale ten ranking to najlepszy znany nam zbiór przykładów, jak zgłoszenia oszukują harness: 1. miejsce MLA 2026 zwraca „analityczne przybliżenie” przy dopuszczeniu 5% elementów poza tolerancją, 1.–2. miejsce MoE w trakcie oceny podmienia i łata aiter (`qwen-opt/research/repos/09-gpu-mode-reference-kernels.md:56,58`). Z tych danych wyrósł [[kernelguard]] (oszustwa 3.45% → 0.37%) i nasze [[reward-hacking-inferencji]] oraz bramki fabryki ([[fabryka-v1]]).
- Harness 2025 mierzył zegarem CPU bez czyszczenia cache, 2026 zdarzeniami GPU z buforem 64 GB i nowymi danymi w każdej iteracji (`09-…md:30-31,136`): gotowa lekcja „jak zmiana harnessu zmienia ranking”. Nasz `bench.ts` w aplikacji pilnuje podobnej pułapki innym sposobem (osobna para zadań na powtórzenie, bo cache n-gramów zawyża dekod 21 → 80 t/s, `app/engine/src/server/bench.ts:64-68`).
- Nauka: GPU MODE lectures są na liście lektur zespołu (raport 21b §6 poz. 10), a blog seb-v o GEMM na 7900 XTX to jedyny znany nam opis RDNA3 z naszego sprzętu (dual-issue, banki VGPR, `-mcumode`, scratch bez `__launch_bounds__`, `09-…md:60-69`).
- Otwarte: `-mcumode` nigdy nie testowane u nas (P2), audyt `v_dual_fmac` bez GPU (P3).

## Powiązane
- [[pygpubench]]
- [[kernelbench]]
- [[mikrobench-granicy-kernela]]
- [[repos-30-przeglad]]
