---
typ: lekcja
tags: [lekcje, determinizm, nvidia, md5]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/09-chmura-3090.md:63-85,199; ~/KERNEL/product/research/09-chmura-3060.md:109-127; ~/KERNEL/product/research/09-chmura-5060ti.md:45-57,187,198
status: aktualne
---
# Nasze „bit w bit” było zawsze względem naszego poprzedniego buildu

**Kampania NVIDIA pokazała, że greedy md5 forka różni się od upstreamu w trybie plain także z 31 przełącznikami = 0, przez łatki bez przełącznika: MMVQ multi-kolumna 0001/0002 i fuzję prologu GDN 0013; nasza bramka „bitowo identyczne” zawsze porównywała z poprzednim buildem forka, nie z upstreamem.**

- Dowód (3090): build forka z `-DMMVQ_DISABLE_MULTI` daje dla LFM md5 upstreamu `949a753b`; Qwen bez multi nadal ≠ upstream przez 0013. Na 3060 pierwszy różny tensor to `qkv_mixed` warstwy 0 (5 kolumn). Łatka 0043 jest na NVIDIA no-opem, a rotacja KV wykluczona.
- To nie błąd: multi-kolumna przyspiesza weryfikację MTP (bez niej pp5 Qwena −8%), a KLD fork vs upstream na 3060 jest na poziomie szumu (Saluki 0.000650 vs szum 0.000612).
- Na plikach Q4_0 i NVFP4 fork = upstream bitowo (ścieżka K-quantów nie jest dotknięta).
Reguły: w produkcie i na landingu nie obiecywać „wynik identyczny z llama.cpp”, tylko „identyczny z poprzednią wersją w tym samym trybie” plus bramkę KLD względem upstreamu; przed produktem dodać przełącznik dla 0001/0002 i bramkę KLD na NVIDIA.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-spekulacja-zmienia-numeryke]]
- [[lekcja-bit-exact-attention]]
- [[zgodnosc-bitowa-md5]]
- [[mmvq-multikolumnowe]]
- [[nvidia-wyniki-2026-10-16]]
