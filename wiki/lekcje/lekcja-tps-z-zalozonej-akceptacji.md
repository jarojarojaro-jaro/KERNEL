---
typ: lekcja
tags: [lekcje, pomiar, spekulacja, konkurencja]
aktualizacja: 2026-11-07
zrodlo: ~/KERNEL/product/research/66b-1cat-tokenspeed.md:23-42,62-70; ~/KERNEL/product/research/66c-hyperkernel-megakernele.md:34-41; ~/KERNEL/product/research/63-SYNTEZA.md (#6 LithosAI)
status: aktualne
---
# t/s producenta = czas rundy × założona akceptacja

**Liczby 1Cat v1.5.2 (27B: 487 / 1224 / 268 t/s) to zmierzony czas rundy razy założone 5.9 tokenu na rundę (akceptacja 70%); zmierzone wyniki zależą od tekstu: HumanEval 84% → 619 t/s, MT-Bench 43% → 386, chiński tekst 22% → 215 (raport 66b, 2026-11-07).**

Ten sam wzorzec wcześniej: LithosAI 2116 t/s = 6 / 2.83 ms przy założonych 75% (63). Pokrewne: AgentX wymusza długość akceptacji w silnikach bazowych, a Hyperkernel liczy na prawdziwej akceptacji, której nie podaje (66c). TokenSpeed: „580 vs 377 t/s” monokernela, a własny wpis CI podaje 443.

Lista kontrolna przed porównaniem:
1. Czy tokeny na rundę są zmierzone, czy przeliczone („按接受率 70% 折算”)?
2. Jaki tekst i temperatura? Kod przy T=0 daje 2–3× więcej niż proza.
3. Czy baza jest uruchomiona przez autora, czy przepisana z cudzego wykresu?
4. Czy liczba z marketingu zgadza się z CI albo plikami w repo?

Normalizujemy przez czas rundy i bajty na krok, nie przez t/s.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-akceptacja-h100-nie-przenosi-sie]]
- [[lekcja-benchmark-kopia]]
- [[yasakani]]
- [[1cat-vllm]]
- [[raport-66-synteza]]
