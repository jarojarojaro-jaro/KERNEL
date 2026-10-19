---
typ: lekcja
tags: [lekcje, atencja, roofline]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/21m-declarative-attention.md:5-17,27
status: aktualne
---
# „Mniej odczytów KV” z prac serwerowych przeliczać na nasz krok batch 1

**Declarative Attention liczy zysk w modelu B200 przy dużym batchu, gdzie globalny odczyt KV to 86% kroku; u nas (batch 1, hybryda GDN – 16 z 64 warstw z pełną atencją, KV q4_0 + `kvq`) część kroku zależna od kontekstu to tylko 4.5% przy 29.5k i 14% przy 94k (raport 21m, 2026-10-19).**

Reguła: przed adopcją metody „czytaj mniej KV” policzyć jej sufit na naszym kroku (bajty wag dominują przy batch 1) i odjąć koszt dodatkowych tokenów; pokrewne: [[lekcja-agent-prefill-nie-decode]], [[lekcja-akceptacja-h100-nie-przenosi-sie]].

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[raport-21m-declarative-attention]]
- [[fattn-kvq]]
