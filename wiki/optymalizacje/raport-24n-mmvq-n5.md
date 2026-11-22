---
typ: optymalizacja
tags: [optymalizacje, mmvq, obłożenie, wynik-negatywny]
aktualizacja: 2026-10-20
zrodlo: ~/KERNEL/product/research/24n-mmvq-n5.md:7-12,62-68,79-83
status: aktualne
technika: obłożenie MMVQ n=5 (GGML_HIP_MMVQ_OCC)
werdykt: odrzucone
zysk: −0,5% spec_sweep (111,4 → 110,8 t/s), serializacja −6,4%
dowod: raport-24n-mmvq-n5
model: qwen3-8-27b
karta: rx-7900-xtx
wyniki:
  - qwen3-8-27b | rx-7900-xtx | 111.4 t/s | spec_sweep baza | 2026-10-20
  - qwen3-8-27b | rx-7900-xtx | 110.8 t/s | spec_sweep MMVQ_OCC | 2026-10-20
  - qwen3-8-27b | rx-7900-xtx | 104.3 t/s | spec_sweep MMVQ_OCC serializacja | 2026-10-20
---
# Raport 24n: obłożenie MMVQ n=5 (`GGML_HIP_MMVQ_OCC`) – kill

**Więcej fal nie przyspiesza MMVQ n=5: przy zachowanych ładowaniach w locie spec_sweep 111.4 → 110.8 t/s (−0.5%), przy serializacji ładowań 104.3 t/s (−6.4%); bitowo identyczne (2026-10-20).**

- Hipoteza z 24f (klif 140 → 119 VGPR da 12 fal i zysk) obalona (`24n:12`).
- Q5_K (47% bajtów) nie ma czystego wariantu 12 fal – kompilator serializuje `vmcnt(0)` (`24n:80`).
- Pułapka narzędziowa: `mmvq_bench` ma DT_RPATH na `~/llama-opt/lib`, więc `LD_LIBRARY_PATH` jest ignorowany – stare porównania `kbench.sh` do sprawdzenia (`24n:81`).
- Wzorzec `grep "Backend .*: OK"` nigdy nie łapie kolorowanego wyjścia test-backend-ops (`24n:83`).
- Następny krok: struktura pracy, nie obłożenie → [[raport-24r-mmvq-pasmo]].

## Powiązane
- [[raporty-2026-10-19-20]]
- [[raport-24f-mmvq-fa]]
- [[raport-24r-mmvq-pasmo]]
- [[mmvq-multikolumnowe]]
- [[lekcja-wyrazna-wygrana-albo-nic]]
