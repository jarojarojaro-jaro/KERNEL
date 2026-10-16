---
typ: narzedzie
tags: [narzedzia, sterownik, baco]
aktualizacja: 2026-10-16
zrodlo: ~/qwen-opt/gpu-keepawake/keepawake.cpp:1-12; ~/qwen-opt/run-llm.sh:97-99; ~/KERNEL/qwen-opt/NOTES.md:122-126
status: aktualne
---
# gpu-keepawake (trzymanie GPU w stanie aktywnym)

**12-liniowy program HIP, który trzyma kontekst KFD, żeby runtime PM amdgpu nie uśpił karty (BACO); uruchamiany przez `run-llm.sh`, gdy runtime suspend jest włączony.**

Działanie: `hipFree(nullptr)` tworzy kontekst, potem `pause()` w pętli; KFD bierze referencję `pm_runtime` dla każdego związanego procesu. `run-llm.sh` startuje go w tle z `LD_LIBRARY_PATH=/opt/rocm/core-10.0/lib`, gdy wykryje włączone usypianie. Rozwiązanie bez roota zamiast `power/control=on`. Bez tego model działał 4.4 zamiast 92 t/s.

## Powiązane
- [[narzedzia/_hub|narzedzia]]
- [[run-llm-sh]]
- [[reactor-monitor]]
- [[baco-runtime-suspend]]
- [[amdgpu-moc-i-termika]]
