---
typ: firma
tags: [ludzie-firmy, konkurencja, nvidia]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/15c-nowe-silniki.md:28-33,82-91,188-208,382
status: do-sprawdzenia
---
# Actual Computer (silnik „e”, relay)

**Firma z silnikiem „e” (host w asemblerze AArch64 + cubiny sm_103a, tylko DGX Station GB300) i relayem na AWS Nitro; na sprzęcie konsumenckim uruchamia vendored llama.cpp albo silnik „malibu”.**

- Deklaracje (własny `e bench`, warunki nieopublikowane): Nemotron 3.5 Super VL FP8 455 t/s przy 1 strumieniu i 8,046 t/s przy 128; sufit bez spekulacji ~452 / 4,469 t/s przy 7.1 TB/s, więc wynik wymaga MTP.
- Darmowo 100M tokenów/dzień przez relay (= 1,157 t/s non-stop).
- Do przejęcia: „output bitwise spec off” (batch-invariance jako wymaganie), `--spec-copy` (kopia z kontekstu wpięta w MTP), budżet czasu kroku i wycena kolejki, relay z atestacją TEE.
- Antywzorce: device-code login autoryzujący kod bez kliknięcia, instalatory `curl|bash` i `irm|iex` bez sumy i podpisu, telemetria OTLP domyślnie włączona.
- Zamknięty kod, ~3 osoby.

## Powiązane
- [[ludzie-firmy/_hub|ludzie-firmy]]
- [[magnitude]]
- [[firma-nvidia]]
- [[raport-15c-nowe-silniki]]
- [[app-prototyp-desktop]]
