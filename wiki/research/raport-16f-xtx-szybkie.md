---
typ: research
tags: [research, xtx, serwer]
aktualizacja: 2026-10-18
zrodlo: ~/KERNEL/product/research/16f-xtx-szybkie.md:1-239
status: aktualne
---
# Raport 16f: szybkie zyski na XTX (ubatch LFM, typ bloku MTP, hak MTP, cache agenta, cache na SSD)

**Agent XtxQuickWins (gałąź `quickwins` od `amd-opt` @ `f61994f58`): dwie wygrane do produkcji (LFM `-ub 2048` +17% prefillu, łatka cache agenta −80% startu sesji), IQ4_XS bloku MTP potwierdzony, hak MTP i pinned staging przegrywają, cache sesji na SSD wykonalny już dziś.**

| E | wynik | notatka |
|---|---|---|
| E1 | LFM ub 2048: pp +17–18%, TTFT −15% | [[2026-10-18-lfm-ubatch-2048]] |
| E2 | IQ4_XS 113.2 vs Q6_K 109.4 t/s (5 seedów) | [[latki-spekulacji]] |
| E3 | hak MTP ≤ 2.6% TTFT; checkpointy ~200 ms | [[2026-10-18-hak-mtp-i-checkpointy]] |
| E4 | `CACHE_SHARE_MIN`: Qwen 8019 → 1612 ms | [[2026-10-18-cache-promptu-agenta]] |
| E5 | restore z SSD 2.51 s vs prefill ~61.5 s | [[cache-sesji-na-dysku]] |

Propozycje do `run-llm.sh` (`-b 2048 -ub 2048` dla LFM, `LLAMA_SERVER_CACHE_SHARE_MIN=1024` po scaleniu `50c3a2f2a`) czekają na decyzję użytkownika ([[otwarte-decyzje-techniczne]]). Korekty: 15d L4 (TTFT −5–7%) zawyżone dla XTX; offline +0.45% tok/krok Q6_K z pilota 11 nie przenosi się. Lekcje: [[lekcja-5-seedow]], [[lekcja-nie-odtwarzac-lockow]].

## Powiązane
- [[research/_hub|research]]
- [[raport-15d-prefill-dlugi-kontekst]]
- [[raport-11-mtp-pl-pilot]]
- [[lfm-czulosc-na-podzial-batcha]]
