---
typ: kernel
tags: [kernele, mtp, graf]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/NOTES.md:236-239,277; ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:95,105; ~/KERNEL/product/research/patch-manifest.json (0020, 0030)
status: aktualne
---
# Draft MTP jako jeden graf (0020) i własny scheduler (0030)

**Cztery osobne przebiegi głowicy MTP zastąpione jednym rozwiniętym grafem z argmax i get_rows na GPU; łańcuch draftu dostał też własny scheduler, żeby nie przebudowywać grafów co krok.**

**0020 (c90db29c6, 2026-10-12):** 4 przebiegi draftu (42 kernele, ~1.19 ms każdy) → jeden graf 104 kerneli; +180 MiB VRAM (kopia 64k wierszy `token_embd`). Drafty bitowo identyczne, tok/krok bez zmian. Qwen UD 36.39 → 35.67 ms/krok, 88.1 t/s (raport 07 podaje 86.4 → 88.0); Uncensored 33.79 ms/krok, 90.4 t/s. Catch-up nie złączony: jego praca GPU chowa się już za próbkowaniem na CPU (zysk 0.2 ms za cenę zmiany draftów). Wymaga 0004 (słownik draftu). Wyłącznik: brak (build).

**0030 (K3, 2026-10-13):** łańcuch draftu MTP na osobnym schedulerze: 31.89 → 31.59 ms. Bitowe. Wyłącznik `LLAMA_MTP_CHAIN_SCHED`.

Kod hosta/llama, niezależny od GPU: przenosi się na każdy backend (rodzina F2 w raporcie 07).

## Powiązane
- [[kernele/_hub|Kernele]]
- [[argmax-dpp]]: argmax w drafcie
- [[glowica-mtp]]
- [[latki-hostowe]]
- [[qwen3-8-27b]]
