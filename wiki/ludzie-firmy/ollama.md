---
typ: firma
tags: [ludzie-firmy, konkurencja]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/01-konkurencja.md:19,49; ~/KERNEL/product/research/06-produkt-ux-prawo-biznes.md:17; ~/KERNEL/product/research/03-silniki-i-stack.md:38,40; ~/KERNEL/product/research/09-chmura-3090.md:165-174; ~/KERNEL/product/research/15c-nowe-silniki.md:56,445
status: aktualne
---
# Ollama

**Najpopularniejsza aplikacja do lokalnych LLM i główny punkt odniesienia „przed” (65 M$ Series B w lipcu 2026).**

Dokładny pomiar pamięci przed załadowaniem, runner-based discovery z timeoutem; instalator ~1,5 GB. W trackerze 190 issues ze „slow” w tytule i 165 z etykietą `amd`. Seria CVE przy API na sieci. Pierwszy pomiar tym samym skryptem (RTX 3090, Ollama 0.40.5, domyślne ustawienia, ten sam GGUF, 2026-10-16): Qwen3.8-27B 39.0 t/s, LFM2.5 180.5 t/s – tyle co upstream llama.cpp z samym `-m`; prefill w Ollamie był szybszy przy ~2k tokenów. Na XTX pomiaru Ollamy nadal brak (E1). Wyjście fazy 1: ≥1.3× wobec Ollamy z domyślnymi ustawieniami.

Baza porównania Magnitude (raport 15c) to Ollama v0.35.1 z domyślnymi ustawieniami; według Magnitude drafter Ollamy dla Gemma „drafted very few tokens” na Macu przy 64k (Gemma 4 31B 8.6 t/s).

## Powiązane
- [[ludzie-firmy/_hub|ludzie-firmy]]
- [[lm-studio]]
- [[jan]]
- [[raport-01-konkurencja]]
- [[produkt-roadmapa]]
- [[raport-09-chmura-3090]]
- [[magnitude]]
