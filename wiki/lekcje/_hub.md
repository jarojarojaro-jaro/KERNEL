---
typ: hub
tags: [lekcje, hub]
aktualizacja: 2026-10-16
zrodlo: wiki/tools/wiki.py index
status: aktualne
---
# Lekcje

**Lekcje z błędów i pułapek: co poszło źle, jak to rozpoznać, jak uniknąć.**

Lekcje procesowe (z korekt użytkownika) mają prefiks `proces-`.

Wróć: [[index|Strona główna]]. Lista niżej jest generowana przez `python3 tools/wiki.py index`; nie edytuj jej ręcznie.

<!-- AUTO:START -->
## Notatki (5)

- [[lekcja-oom-ub2048|-ub 2048 przy ctx 204800 kończy się OOM]] — Większy micro-batch daje +3% prefillu w llama-bench, ale serwer z kontekstem 204800 przekracza 24.5 GB VRAM przy pierwszym długim prompcie; zostajemy przy ub 512.
- [[determinizm-fma|Determinizm: kontrakcja FMA i świeży serwer]] — Bity zmieniają się z trzech powodów: kompilator łączy mnożenie z dodawaniem w FMA, weryfikacja batcha liczy inaczej niż N=1, a llama.cpp nie jest deterministyczny w obrębie jednego serwera.
- [[lekcja-pdl-sm120|PDL na Blackwell: kernel musi czekać na poprzednika]] — Na sm_120 llama.cpp startuje kernele wcześniej (PDL); nowy kernel bez `ggml_cuda_pdl_sync` może czytać dane, zanim poprzedni skończy.
- [[pm4-niewidoczne-w-rocprof|rocprofv3 nie widzi dispatchy PM4]] — Po łatce 0060 kernele idą taśmą PM4 i rocprofv3 ich nie widzi; profilujemy z `GGML_HIP_PM4=0` albo przez `GGML_HIP_PM4_DEBUG=3`.
- [[baco-runtime-suspend|Usypianie karty (BACO) wyrzuca model z VRAM]] — Bez aktywności amdgpu usypia kartę po 5 s (runtime PM/BACO) i przenosi VRAM do RAM; model działa wtedy przez PCIe: 4.4 zamiast 92 t/s.
<!-- AUTO:END -->
