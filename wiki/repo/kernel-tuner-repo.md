---
typ: repo
tags: [repo, autotuning]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/research/repos/26-kernel-tuner.md:1-12,172-176; ~/KERNEL/qwen-opt/research/repos/REPOS-PODSUMOWANIE.md:36
status: aktualne
---
# KernelTuner/kernel_tuner

**Pythonowy framework autotuningu (commit `8e71bbf`, 2026-10-08, v1.5.0) jako silnik przeszukiwania tablic per kształt; werdykt: średnia.**

Kompiluje każdą konfigurację z `tune_params`, sprawdza poprawność, mierzy i chodzi po przestrzeni jedną z ok. 20 strategii (brute force, BO, GA, SA…), ma cache i tryb symulacji. Backend HIP i natywny pomiar nie pasują do naszych kerneli, ale przez furtkę `lang="C"` z naszym buildem i pomiarem „na zimno” daje drogę do strojenia per kształt: realnie 1–3% i więcej przy długim kontekście. Nasze użycie opisuje metoda i narzędzie `kt/`.

## Powiązane
- [[repo/_hub|repo]]
- [[mixbench]]
- [[tilelang]]
- [[kernel-tuner]]
- [[repos-30-przeglad]]
