---
typ: narzedzie
tags: [narzedzia, pm4, soak]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/pm4_soak.py:1-22; ~/KERNEL/qwen-opt/NOTES.md:376
status: aktualne
---
# pm4_soak.py (test wytrzymałościowy serwera)

**Soak test działającego llama-server: wiele zapytań czatu o mieszanej długości, powtarzane zapytania greedy muszą się zgadzać, follow-upy ćwiczą cache promptu; kod wyjścia 1 przy błędzie lub rozjeździe.**

Zapytania greedy idą z `cache_prompt=false`, bo prompt odtworzony z cache nie jest bitowo powtarzalny (inne porcjowanie prefillu). Prompty PL i EN (B-tree, opowiadanie, LRU cache w Pythonie, TCP vs UDP, tabela stolic). Użyty do bezpieczeństwa PM4 (0060): ~4 min na model (LFM, LFM Uncensored, Qwen MTP), długości 256–2048 tok., bez zawieszeń i błędów. Uruchomienie: `pm4_soak.py --port N [--seconds 240]`.

## Powiązane
- [[narzedzia/_hub|narzedzia]]
- [[det-probe]]
- [[samp-ab]]
- [[pm4-replay]]
- [[lfm-runda-4-pm4]]
