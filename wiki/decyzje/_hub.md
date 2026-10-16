---
typ: hub
tags: [decyzje, hub]
aktualizacja: 2026-10-16
zrodlo: wiki/tools/wiki.py index
status: aktualne
---
# Decyzje użytkownika

**Decyzje i korekty użytkownika z datą; mają pierwszeństwo przed każdą inną notatką.**

Gdy notatka w innym folderze przeczy decyzji, wygrywa decyzja (a notatkę trzeba poprawić). Jedna notatka = jedna decyzja, nazwa `RRRR-MM-DD-krotko`.

Wróć: [[index|Strona główna]]. Lista niżej jest generowana przez `python3 tools/wiki.py index`; nie edytuj jej ręcznie.

<!-- AUTO:START -->
## Notatki (8)

- [[2026-10-12-rocm-domyslny|2026-10-12: ROCm stałym backendem]] — ROCm jest stałym backendem domyślnym; dalsze optymalizacje robimy pod HIP/ROCm, a Vulkan zostaje tylko jako opcja (`run-llm.sh … vulkan`).
- [[2026-10-14-lfm-kv-q8|2026-10-14: LFM używa KV q8_0 (decyzja użytkownika)]] — Użytkownik zdecydował, że LFM2.5 działa z KV cache q8_0 (`run-llm.sh lfm`), mimo kosztu prędkości względem q4_0.
- [[2026-10-15-zakaz-gpu-w-nocy|2026-10-15: czasowy zakaz pracy na GPU]] — Ok. 00:45 użytkownik zakazał pracy na GPU, ok. 02:00 pozwolił znowu; w tym czasie agenci pracowali offline (ISA, emulacja, dry-run).
- [[2026-10-15-czat-na-web-ui-llama|2026-10-15: czat na web UI z llama.cpp, model open core]] — Ekran czatu produktu powstaje na web UI z llama.cpp (MIT); kod w modelu open core (łatki silnika otwarte, baza profili i orkiestrator zamknięte).
- [[2026-10-15-karty-kupujemy|2026-10-15: popularne karty kupujemy, rzadkie wynajmujemy]] — Budżet na karty jest: najpopularniejsze karty kupujemy, a rzadkie i drogie (3090, 4090, 5090) wynajmujemy na Vast.
- [[2026-10-15-linux-i-analiza-platformy|2026-10-15: rozwój na Linuksie, obowiązkowa analiza platformy]] — Rozwijamy i testujemy na Linuksie (bez testów na Windowsie teraz), ale każda optymalizacja ma obowiązkowy krok „analiza platformy” dla Windows i macOS.
- [[2026-10-16-prosta-baza-wiedzy|2026-10-16: prosta baza wiedzy w KERNEL/wiki]] — Użytkownik: „po prostu baza wiedzy; wszystko ma być dokładnie, ale bez przesady”, każda kategoria w osobnym folderze, widoczna w Obsidianie.
- [[2026-10-09-limit-mocy-odlozony|Limit mocy GPU odłożony (na prośbę użytkownika)]] — Optymalizacja limitu mocy (np. −20% mocy kosztem ≤5% t/s) została odłożona na prośbę użytkownika; karta pracuje z limitem 285 W.
<!-- AUTO:END -->
