---
typ: lekcja
tags: [lekcje, profilowanie]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/NOTES.md:374; ~/KERNEL/qwen-opt/research/lfm-decode-round4.md:98-99,208
status: aktualne
---
# rocprofv3 nie widzi dispatchy PM4

**Po łatce 0060 kernele idą taśmą PM4 i rocprofv3 ich nie widzi; profilujemy z `GGML_HIP_PM4=0` albo przez `GGML_HIP_PM4_DEBUG=3`.**

Przy `GGML_HIP_PM4=0` ISA kerneli jest ta sama, zmienia się tylko sposób wysyłki. `PM4_DEBUG=3` wypisuje linie `pm4trace` (czas od końca poprzedniego do końca bieżącego dispatchu). ATT też nie zobaczy taśmy (szacunek raportu 13).

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[pm4-replay]]
- [[rocprof]]
- [[pm4]]
