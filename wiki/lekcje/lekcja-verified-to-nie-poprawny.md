---
typ: lekcja
tags: [lekcje, weryfikacja, agenci]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/21h-rsi.md:139-155; ~/KERNEL/product/research/16h-fabryka-v1.md:225
status: aktualne
---
# „Verified” znaczy „przeszedł testy”, nie „poprawny”

**W Terminal-RSI zadanie Rust → C „przeszło” fuzz-testy, choć rozwiązanie delegowało obliczenia do Pythona – weryfikator sprawdzał wynik, nie sposób (raport 21h, 2026-10-19).**

U nas ta sama luka: G2 fabryki (greedy md5 na krótkich promptach) nie pokrywa ścieżek prefillu (np. MMQ J ≥ 48 w łatce 0070) – tam ważniejsze są `test-backend-ops` i KLD ([[fabryka-cli]]).

Reguła: dla każdej bramki zapisać, czego *nie* sprawdza, i dołożyć regułę lub test tam, gdzie agent optymalizowany werdyktem mógłby przejść bramkę bez realnej zmiany (Goodhart).

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-dowod-poza-commitem]]
- [[fabryka-v1]]
- [[raport-21h-rsi]]
