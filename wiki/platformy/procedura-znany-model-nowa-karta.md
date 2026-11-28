---
typ: platforma
tags: [platformy, procedura, topka, nowa-karta]
aktualizacja: 2026-11-28
zrodlo: ~/KERNEL/qwen-opt/cloud/SOP-DOBOR-I-POMIARY.md:25-70; wiki/testy/2026-11-27-k204-enigma-16gb-inkling.md; wiki/testy/2026-11-28-k207-ablacja-zamiast-lora.md; wiki/testy/2026-11-27-nvq5.md; wiki/testy/skill-io-sufity.md:95-104; wiki/decyzje/2026-11-27-zawsze-pelny-kontekst.md; wiki/stos/topki.md
status: aktualne
---
# Procedura: znany model na nowej karcie

**Kroki przeniesienia znanej topki na kartę, na której jej jeszcze nie mierzyliśmy. Wzór: K-201, K-204, K-207 i nvq5 (Inkling i Qwen na 5060 Ti / 4060 Ti, 2026-11-27…28). Każdy krok porównujemy z obecnym przepisem na tym samym hoście.**

## Kroki
1. **Licencja i dostęp.** Sprawdź licencję modelu (bez zmian) i warunki dostępu do karty: Vast godzinowo, dedyk miesięczny (Arc), Mac z 24 h minimum. Budżet zapisz przed startem (K-204: 0,41 $, K-207: 0,045 $).
2. **Sufit i dopasowanie offline.** `ceiling.py` / `karty.py` (sufit MTP) i `fitcalc.py --draft … --depth` (największy `-c` z drafterem). Kwant wybieramy tak, żeby się zmieścić, a nie dla prędkości: 16 GB → IQ3_S / IQ3_XXS ([[skill-io-sufity]]).
3. **Bramka jakości przed wynajmem.** J1 KLD (wiki ≤ 0,05, czat ≤ 0,07) i J2 na CPU. Odmowy dla pliku bez cenzury też można sprawdzić na CPU.
4. **Wybór hosta.** `vastai search` + `hostcheck.sh`. Na karcie `llama-bench` z wykorzystaniem GPU ≥ 85%. Uwaga: bramka tg256 nie łapie wolnego CPU na ścieżce serwera. EPYC 7402 był 2,1–2,6 × wolniejszy od Ryzena przy tym samym tg ([[2026-11-28-k207-ablacja-zamiast-lora]]). Do pomiarów bezwzględnych bierz Ryzena.
5. **Pobranie i build.** Model, drafter i wersja bez cenzury. Build dla architektury karty (sm_86/89/120, gfx…, SYCL, Metal). `test-backend-ops` dla opów spekulacji.
6. **Baseline = obecny przepis tej klasy kart** na tym samym hoście i tym samym skrypcie. K-204: Qwen GSQ IQ3_XXS 32,5 t/s przy 200 704.
7. **Pełny stos spekulacji.** Sweep długości draftu i `p_min`. K-204: DSpark n2 66,5, n3 58,4, n4 52,9, bez draftera 51,4; `p_min` ≥ 0,1 wyłącza drafter.
8. **Pełny kontekst.** Szukaj maksimum po `-ub` (K-204: ub 128 → 262 144 zamiast 216 064 przy ub 512, prefill −35%). KV q4_0. KV draftera domyślne. `needle.py` przy 95% głębokości z 700 tokenami odpowiedzi: 5/5. Zapisz szczyt VRAM.
9. **Bramka md5 i KLD.** md5 T=0 z drafterem = bez draftera. KL nowego ramienia wobec ramienia podłogi ([[bramka-kld-kanarki]]).
10. **Odmowy (model bez cenzury):** 0/5. Porównaj ablację z LoRA, bo LoRA w locie kosztowała 17–33% dekodu ([[2026-11-27-k204-enigma-16gb-inkling]]).
11. **Strojenie karty.** Najpierw przełączniki runtime, potem kernele. Offload MoE: `-ncmoe` sweep (5060 Ti `-ncmoe 3` 60,0 t/s, pula ekspertów −55%, [[2026-11-27-nvq5]]). Dźwignie kernelowe stroimy od nowa na każdą architekturę ([[skill-io-dzwignie]]).
12. **Pomiar wall i prefill.** `wall.py` (mediana 4 promptów × 300 tokenów, T=0 i T=0,7), dekod przy 64k/128k/maks., prefill 32k przy trzech `-ub` i prefill maks. Moc, zegar pamięci i CPU hosta zapisz w warunkach.
13. **Wpis w [[TOPKI]] w tej samej turze co pomiar.** Wiersz karta × model w [[topki]] i przepis w [[final-recipes-nvidia]] (status: kandydat, dopóki JARO nie zdecyduje).
14. **Wpis w [[REKORDY]]** z hostem, datą, logiem i statusem produkcji.
15. **Sprzątanie i wdrożenie.** Instancje zniszczone, `STOP` ustawiony. Uwaga na reaper: zniszczył pracującą 5060 Ti po jednym odczycie „offline”. Zmiana modelu w Enigmie tylko decyzją JARO (2026-11-28: Inkling dla 16 GB).

## Najczęstsze błędy
- Liczba bez draftera podana jako główna.
- Kontekst skrócony po cichu.
- Pomiar na wolnym hoście podany bezwzględnie zamiast jako stosunek.
- Porównanie z przepisem z innego hosta.

## Powiązane
- [[procedura-nowy-model-znana-karta]]
- [[rodzaje-modeli]]
- [[rtx-5060-ti]]
- [[2026-11-27-k204-enigma-16gb-inkling]]
- [[TOPKI]]
