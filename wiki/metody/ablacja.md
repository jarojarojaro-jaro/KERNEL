---
typ: metoda
tags: [metody, profilowanie, prefill]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/research/qwen-round5.md:17-25,58-60; ~/KERNEL/qwen-opt/STATUS-NEXT.md:26-27
status: aktualne
---
# Ablacja zamiast zgadywania

**Wyłączamy kolejne części kernela w specjalnym buildzie i patrzymy, ile czasu znika; to pokazuje, co naprawdę ogranicza kernel.**

Przykład: MMQ (prefill) Qwen3.8-27B, Qwen runda 5, 2026-10-15. Build `-DGGML_MMQ_ABLATION` (ISA produkcji bez zmian, bo `ablate` to constexpr 0), bity `GGML_MMQ_ABLATE`: 1 = kafel x ładowany raz, 2 = kafel y raz, 4 = bez vec_dot, 8 = bez barier. Llama-bench pp4096 całego modelu, `-r 2`:

| tryb | t/s |
|---|---|
| normalny | 1094 / 1085 |
| x raz | 1173 (+7.6%) |
| y raz | 1131 (+3.8%) |
| bez ładowań | 1219 (+11.9%) |
| bez barier | 1173 (+7.6%) |
| bez vec_dot | 3254 (3.0×) |

Wniosek: ~66% czasu prefillu to vec_dot MMQ (WMMA + epilog skal), ładowania ~11%, bariery ~7%. Prefetch kafli dałby najwyżej ~12% i tylko bez utraty obłożenia (podwójny bufor y kosztował 3 → 2 bloki/WGP i −2.6% pp4096). Praca poszła w tańszy epilog: łatka 0070, +2.2% pp4096.

## Powiązane
- [[metody/_hub|Metody]]
- [[mmq-epilog]]
- [[qwen-runda-5]]
- [[sufit-pasma-i-mapa-czasu]]
- [[playbook-optymalizacji]]
