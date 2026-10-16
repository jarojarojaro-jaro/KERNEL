# KERNEL: instrukcje dla agentów

- Baza wiedzy projektu: `wiki/` (Obsidian, Markdown z [[linkami]]). Zanim zaczniesz zadanie, przeczytaj `wiki/index.md` i pasujące notatki: `python3 wiki/tools/wiki.py search <słowa>`.
- Decyzje użytkownika w `wiki/decyzje/` są wiążące i mają pierwszeństwo przed resztą notatek.
- Liczby w notatkach mają datę i źródło (`zrodlo:`); przed użyciem w ważnej decyzji sprawdź źródło. `status: do-sprawdzenia` = niepotwierdzone.
- Repo jest publiczne: nigdy nie zapisuj sekretów (kluczy API, tokenów), adresów IP, e-maili ani sald.
- Podagenci tylko czytają wiki. Po zakończonym zadaniu w raporcie zaproponuj, które notatki dodać lub poprawić; główny agent je aktualizuje według `wiki/KONWENCJE.md` i uruchamia `python3 wiki/tools/wiki.py index && python3 wiki/tools/wiki.py lint` (0 błędów).
- Notatki po polsku, terminy techniczne po angielsku.
