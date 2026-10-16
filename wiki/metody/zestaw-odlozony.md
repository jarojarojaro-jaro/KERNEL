---
typ: metoda
tags: [metody, pomiar, spekulacja]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/15f-agentowa-nauka.md:22,84,139-147,184-194; ~/KERNEL/product/research/16h-fabryka-v1.md:73
status: aktualne
---
# Zestaw odłożony i klątwa zwycięzcy

**Decyzje konfiguracji spekulacji wybrane na 6 promptach spec_sweep nie przenoszą się na prompt odłożony (przewaga +2.22% → −4.34%, zmiana znaku w 3/5 przypadków), więc twierdzenia o konfiguracji wymagają zapieczętowanego zestawu promptów spoza selekcji.**

- Eksperyment E-C (leave-one-prompt-out na `spec_sweep.jsonl`):

| sesja | konfiguracje | przewaga na selekcji | na odłożonym | zmiana znaku |
|---|---|---|---|---|
| 2026-10-10, DRAFT_N × P_MIN | 7 | +2.22% | −4.34% | 3/5 |
| 2026-10-12, P_CUM | 6 | +1.65% | +3.77% | 2/6 |
| 2026-10-12, Vulkan N 3/4/5 | 3 | +0.38% | −0.28% | 2/6 |

- t/s per prompt w jednej konfiguracji rozciąga się od 58 do 96, więc różnice 1–2% na 6 promptach to szum selekcji.
- Literatura: „Winner’s Curse” (arXiv 2610.09239) – wynik na zbiorze selekcji przewyższa odłożony o 13–20 pkt przy 16 elementach i 1–5 pkt przy 256; AlphaEvolve dzieli kształty kerneli na treningowe i ewaluacyjne.
Reguła: `factory/sealed/` (≥ 4 prompty z innych domen, hash w ledgerze), raport podaje obie liczby, a t/s rozbija na tok/krok ÷ ms/krok. Mała próba – to wskaźnik, nie dowód.

**Stan 2026-10-16:** zestaw `sealed-v1` istnieje (`factory/sealed/prompts.jsonl`, sha256 `1e6c3a4b…` przypięty w `fk/sealed.py`): 10 promptów (5 new-writing / 5 copy-edit, 4 PL / 6 EN, 4 edycje agentowe); werdykt na nim, spec6 obok ([[fabryka-cli]]).

## Powiązane
- [[metody/_hub|Metody]]
- [[pomiar-abba]]
- [[fabryka-v1]]
- [[lekcja-jeden-prompt]]
- [[raport-15f-agentowa-nauka]]
