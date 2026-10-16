---
typ: metoda
tags: [metody, platformy, windows]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/PLAN.md:27-29,252-267; ~/KERNEL/product/research/08-analiza-platformy-latek.md:1-45
status: aktualne
---
# Analiza platformy (obowiązkowy krok)

**Każda łatka, profil i ustawienie dostaje rubrykę „gdzie działa i co się zmienia” na Linux / Windows / macOS; bez niej nie trafia do produktu (decyzja z 2026-10-15).**

Rozwijamy i testujemy na Linuksie, ale klienci są głównie na Windowsie (PLAN §0 pkt 5, §4.5). Wynik zapisujemy jako predykat w manifeście łatki, np. `os: [linux]`, `runtime: rocr`; daemon włącza łatkę tylko tam, gdzie predykat jest spełniony.

Najważniejsze ustalenia pierwszej analizy (raport 08, 70 łatek, „na papierze”):
- HIP na Windows działa na PAL, nie na ROCr, więc **0060 (PM4 replay) i 0061 nie działają na Windows**; 0060 dodaje bezwarunkowe `find_package(hsa-runtime64 REQUIRED)`, co [SZACUNEK raportu] łamie build HIP na Windows.
- Kod uznany za „tylko RDNA3” bywa aktywny szerzej: wielokolumnowe MMVQ z 0001/0002, loadery 0021, kernele 0025/0026 nie mają strażnika arch.
- Przełączniki `GGML_HIP_*` czyta też build CUDA (domyślnie włączone).
- Na każdą platformę bez zmian przenosi się sampler i UI (0048, 0065–0069).
- rocprofv3 nie istnieje na Windows, więc playbook profilowania tam nie działa.

## Powiązane
- [[metody/_hub|Metody]]
- [[playbook-optymalizacji]]
- raport-08-platforma
- [[patch-manifest]]
- [[pm4-replay]]
