---
typ: repo
tags: [repo, online-lse]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/research/repos/20-keops.md:1-9,68,131-133; ~/KERNEL/qwen-opt/research/repos/REPOS-PODSUMOWANIE.md:30
status: aktualne
---
# getkeops/keops

**Biblioteka symbolicznych redukcji map-reduce na GPU (HEAD `ef72bc90`, 2026-06-24), prekursor online-LSE; werdykt: niska.**

Formuła jest drzewem symbolicznym kompilowanym przez NVRTC, macierz M×N nie jest materializowana. Kernele skalarne, bez WMMA, bez AMD, D<100. Wszystko, co pasuje do naszych kerneli, już mamy. Pomysły: combine atencji (i FWHT) w ogonie ostatniego bloku oraz pomiar kopii logitów do hosta (Q5), każdy wart ~0.3–1.5%. Arytmetyka z raportu: Qwen 29 ms/krok, więc 1 ms ≈ 3.4% t/s; LFM 4.10 ms/token, więc 0.1 ms ≈ 2.4%.

## Powiązane
- [[repo/_hub|repo]]
- [[falkon]]
- [[flashinfer]]
- [[ms-na-krok]]
- [[repos-30-przeglad]]
