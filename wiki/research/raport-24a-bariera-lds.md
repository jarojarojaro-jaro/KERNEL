---
typ: research
tags: [research, bariery, hip, wynik-negatywny]
aktualizacja: 2026-10-20
zrodlo: ~/KERNEL/product/research/24a-bariera-lds.md:7-13,26-31,48-52; ~/KERNEL/product/research/26-kolejka-gpu-wieczor.md:10
status: aktualne
---
# Raport 24a: bariera tylko-LDS (`GGML_HIP_LDS_BARRIER`)

**ISA potwierdza zniknięcie `buffer_gl0_inv` w zamienionych barierach (mmq 90/90), ale ABBA w kolejce wieczornej wyszło w szumie (pp4096 1133.2/1127.9 off vs 1129.7/1127.8 on) – odrzucone (2026-10-19).**

- Gałąź `lds-barrier` (`949c4ecd2` + poprawka `94e4c92c8`), maska per miejsce `GGML_HIP_LDS_BARRIER_MASK` (`24a:3,18`).
- Pierwsza wersja abortowała każdy proces: `__attribute__((used))` na `static __constant__` zostawia symbol LOCAL i `hipMemcpyToSymbol` robi abort (`24a:7-13`).
- Bramka 26: MUL_MAT 540/540, FA 740/740, md5 bez zmian; LFM 6124.8/6125.9 vs 6149.4/6128.1, czat 102.5 vs 102.4 (`26:10`).
- Wniosek: bariery nie są wąskim gardłem na XTX ([[bariera-lds-rdna3]]). Reguła: [[lekcja-wyrazna-wygrana-albo-nic]].

## Powiązane
- [[research/_hub|research]]
- [[raporty-2026-10-19-20]]
- [[bariera-lds-rdna3]]
- [[raport-23b2-bariery-lds]]
- [[lekcja-wyrazna-wygrana-albo-nic]]
- [[wyniki-negatywne]]
