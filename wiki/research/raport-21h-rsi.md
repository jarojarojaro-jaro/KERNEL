---
typ: research
tags: [research, rsi, agenci, post-training]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/21h-rsi.md:1-581; https://arxiv.org/abs/2610.22192
status: aktualne
---
# Raport 21h: Terminal-RSI (Tencent Hunyuan) i RSI jako metoda

**„RSI” w Terminal-RSI (arXiv 2610.22192) to dwa cykle expert iteration (rozwiązania przechodzące ukryte testy → przepisane demonstracje → SFT) + PPO, z decyzjami ludzi między cyklami; kierunek wyniku jest realny (Qwen3.8-27B TB 2.1 51.7 → 86.5%, TB 4.0 0 → 19.84%), ale pokazany zbyt korzystnie; dla nas: adoptować i zmierzyć RSR-27B (E1), a RSI przenieść na fabrykę bez trenowania wag (pętla RSI-F).**

Weryfikacja (§3, analiza CPU agenta ResRSI):
- Przyrosty RSR-2 → RPR-2 (+2.38 / +1.95 / +3.00 pp) w szumie (SE 3.6–5.0 pp); SWR100 3 → 6/100 p = 0.50; LHTB 0 → 5/46 p = 0.056.
- Część wartości nie jest Mean@3 na nominalnym n: TB 4.0 19.84% = 25/126 (2 przebiegi), Hard 69.50% = 139/200, TB 2.1 51.70% nie pasuje do 89 zadań, TB 3.0 16.95% pasuje do 10/59, nie do 70.
- Brak ablacji TB-GAE i dziedziczenia krytyka; w pierwszej fazie RL zwykłe GAE γ = λ = 1. Nagrodę SPR zaprojektowano na widzianych danych, checkpoint (krok 18; krok 20 −2.4…−3.0 pp) wybrano na teście ([[zestaw-odlozony]]).
- Kontaminacja nieaudytowana; 2 z 6 benchmarków własne. Kosztu brak – szacunek ~1.5–2.5 tys. H100-h, ~$3–9k `[SZACUNEK]`; pełne RSI (≥ 0.86 TB stanu aktora i krytyka) poza naszym zasięgiem.

Kąt 1 (jakość w produkcie): [[rsr-27b]] + eksperyment [[2026-10-19-plan-e1-rsr27b]] (~$40–70, decyzja użytkownika); własne „RSI-lite” (SFT na zweryfikowanych trajektoriach Qwena) ~$150–300 pilot; nie trenować na sesjach omp z Claude (ToS `[INFERENCE]`). Kąt 2: [[petla-rsi-f]], pilot [[2026-10-19-plan-retro-rsr-0070]].

## Powiązane
- [[research/_hub|research]]
- [[raport-15f-agentowa-nauka]]
- [[raport-10-post-training]]
- [[tencent-terminal-rsi]]
- [[lekcja-verified-to-nie-poprawny]]
