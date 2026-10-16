---
typ: metoda
tags: [metody, pomiar, spekulacja]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/NOTES.md:142,166-168,286; ~/KERNEL/qwen-opt/research/strata/README.md:178-179; ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:220,232
status: aktualne
---
# ms/krok jako główna metryka spekulacji

**Przy dekodowaniu spekulacyjnym t/s = (tokeny na krok) / (czas kroku); kernel zmienia tylko czas kroku, więc to ms/krok mierzy łatkę, a t/s miesza ją z losowością tekstu.**

- NOTES 2026-10-12: przy 3 seedach t/s zależy bardziej od wylosowanego tekstu (tok/krok) niż od kernela; ms/krok jest miarą wiarygodną.
- Krótszy draft podnosi procent akceptacji, ale nie prędkość (NOTES 2026-10-10, sweep MTP).
- Przykład: draft MTP w IQ4_XS skrócił krok (30.97 → 29.76 ms), ale akceptacja spadła ~2–3% (3.063 → 3.008 tok/krok), więc netto t/s tylko +1–3% (NOTES S2).
- Budżet hipotezy liczymy w ms/krok i przeliczamy na t/s; arytmetyka z analizy Straty: przy kroku 35.7 ms i 3.16 tok/krok każda zaoszczędzona 1 ms/krok to ≈ +2.9% t/s.

W raportach podajemy obie liczby: ms/krok (dla łatki) i t/s (dla użytkownika), plus tok/krok, żeby było widać, czy zmieniła się akceptacja.

## Powiązane
- [[metody/_hub|Metody]]
- [[pomiar-abba]]
- [[spec-sweep]]
- [[glowica-mtp]]
- strata
