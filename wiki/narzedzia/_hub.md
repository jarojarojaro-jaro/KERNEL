---
typ: hub
tags: [narzedzia, hub]
aktualizacja: 2026-10-16
zrodlo: wiki/tools/wiki.py index
status: aktualne
---
# Narzędzia

**Nasze skrypty i narzędzia: do czego służą, jak je uruchomić, gdzie lądują wyniki.**

Większość leży w `qwen-opt/` i `qwen-opt/tools/` (repo KERNEL) oraz `~/qwen-opt/` na serwerze. Harness chmurowy: [[chmura/_hub|Chmura]].

Wróć: [[index|Strona główna]]. Lista niżej jest generowana przez `python3 tools/wiki.py index`; nie edytuj jej ręcznie.

<!-- AUTO:START -->
## Notatki (4)

- [[greedy-check|greedy.sh / greedy_check.sh — bramka md5]] — Skrypty uruchamiają świeży serwer i zapisują tekst greedy (T=0) w trybie plain i MTP; md5 musi się zgadzać z bazą, żeby łatka była „bitowo identyczna”.
- [[run-llm-sh|run-llm.sh — start produkcyjnego serwera]] — Jeden skrypt, który uruchamia zoptymalizowany llama-server na RX 7900 XTX z naszymi ustawieniami dla każdego modelu.
- [[serve-bench|serve_bench.py i quick_quality.py — pierwsze narzędzia (2026-10-09)]] — Pierwszy benchmark end-to-end projektu i szybki test jakości; dziś zastąpione przez spec_sweep, ale ich wyniki (59.2 → 92 t/s) są punktem startowym.
- [[spec-sweep|spec_sweep — główny pomiar t/s i ms/krok]] — Standardowy benchmark projektu: restartuje serwer dla każdej konfiguracji i mierzy t/s, ms/krok, tokeny na krok i akceptację draftu na stałym zestawie promptów PL/EN.
<!-- AUTO:END -->
