---
typ: rocm
tags: [rocm, profilowanie, rocprofv3]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/reports/Optymalizacja kerneli na AMD.md:49; ~/KERNEL/qwen-opt/NOTES.md:184,247-248,256,374; ~/KERNEL/product/research/13-rocm-10.1.md:16-19,30-33,62-95; ~/KERNEL/product/research/08-analiza-platformy-latek.md:44; ~/KERNEL/product/research/21j-flameox.md:144-170,244
status: aktualne
---
# rocprofv3 i profilowanie na gfx1100

**Profilujemy rocprofv3 (ROCprofiler-SDK): trace kerneli w prawdziwym modelu daje mapę czasu kroku; liczniki PMC zwracały u nas 0, a PM4 jest dla profilera niewidoczne.**

Jak używamy:
- `rocprofv3 --kernel-trace --stats` pod llama-bench lub serwerem (`prof_serve.sh`, `trace_breakdown.py`); przykład z 2026-10-12: GPU bezczynne 15.5% czasu w przerwach <5 µs między ~1200 kernelami na krok;
- decyzje bierzemy z profilu w modelu, nie z mikrobencha (mikrobench mylił się co do Q6_K i GLC|DLC).

Ograniczenia i ustalenia:
- **PM4:** rocprofv3 nie widzi dispatchy z taśmy PM4 (0060); profilujemy z `GGML_HIP_PM4=0` albo używamy `GGML_HIP_PM4_DEBUG=3` (pm4-niewidoczne-w-rocprof).
- **PMC = 0:** wg raportu 13 dokumentacja SDK wymaga na gfx11/gfx12 stabilnego stanu zasilania ustawionego przez `amd-smi set --perf-level STABLE_STD` (sudo); to prawdopodobna przyczyna zer, niesprawdzona.
- **ATT (thread trace)** działa na gfx1100 jako „trace-only” już w zainstalowanym 10.0 (`librocprof-trace-decoder.so.0.2.0`): latency/stall/idle per instrukcja. Zalecany następny krok (2–4 h).
- **PC sampling** i roofline Compute Profilera: tylko Instinct/APU, nie dla dyskretnego Radeona.
- **Windows:** rocprofv3 nie istnieje (TheRock: rocprofiler-sdk „Unsupported”).
- roctracer i rocprof v1/v2 nie są już utrzymywane.

21j (2026-10-19): `trace_breakdown.py` – sum-busy = union-busy na 5 trace'ach (overlap ≤ 0.01 ms); DuckDB 0.48 s vs Python 2.37 s na 158 MB CSV przy identycznych liczbach; zasady pokrycia: [[dowod-z-profilu]].

## Powiązane
- [[rocm/_hub|ROCm]]
- [[sufit-pasma-i-mapa-czasu]]
- [[amd-smi]]
- [[rocm-10-1]]
- [[pm4-replay]]
