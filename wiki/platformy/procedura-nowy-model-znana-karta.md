---
typ: platforma
tags: [platformy, procedura, topka, nowy-model]
aktualizacja: 2026-11-28
zrodlo: wiki/modele/inkling-2-mini.md; wiki/KOLEJKA-TESTOW.md:84-109 (K-203, K-206, K-207, K-208); wiki/log.md:724-886; wiki/decyzje/2026-11-27-zawsze-pelny-kontekst.md; wiki/lekcje/lekcja-mierz-z-drafterem.md; wiki/lekcje/lekcja-maya-16k-kontekstu.md; wiki/stos/topki.md; ~/KERNEL/qwen-opt/cloud/SOP-DOBOR-I-POMIARY.md:40-55
status: aktualne
---
# Procedura: nowy model na znanej karcie

**Kroki od pobrania do wdrożenia, spisane z kampanii Inklinga na XTX (K-133…K-208, 2026-11-21…28). Główną liczbą jest wall czatu z drafterem przy pełnym kontekście.**

## Kroki
1. **Licencja i źródło.** Zapisz licencję (Inkling: Apache 2.0, LFM: limit 10 M$ przychodu) i pochodzenie pliku: oficjalny GGUF, Unsloth czy AtomicChat ([[inkling-2-mini]]). Sprawdź, czy silnik zna architekturę. Inkling wymagał PR #32695.
2. **Pobranie i miejsce na dysku.** Model, drafter (DSpark, DFlash2, MTP w pliku) i wersja bez cenzury. Plik bez cenzury pochodzi z ablacji albo LoRA ([[uncensored-ablacja-kierunku]]). Bez pliku na dysku topki nie ma.
3. **Rodzaj i plan.** Ustal rodzaj według [[rodzaje-modeli]]: co dominuje krok i jakie są pierwsze dźwignie. Policz sufit `ceiling.py` ([[skill-io-sufity]]).
4. **Baseline upstream.** `llama-bench` tg/pp i `wall.py` na tym samym pliku. Inkling stock: tg64 26,9, pp512 1333 t/s.
5. **Punkt odniesienia z zewnątrz.** Szukaj tylko wpisów verified, przy tej samej T i na tym samym pliku. Maya plain 93,6 vs nasze 49,5 pokazało, że trzeba zmienić silnik, a nie stroić kernele.
6. **Pełny stos spekulacji od razu.** Drafter albo MTP, lookup, sweep długości (`spec_sweep.py`, n1/n2/n4) przy T=0 i T=0,7. Bez draftera tylko jako wzorzec md5 ([[lekcja-mierz-z-drafterem]]).
7. **KV q4_0** (najwyżej q6) i FA. Zmierz `kld_gate.py compare` wobec KV f16. KV draftera domyślne: q4 dla draftera OOM-owało w K-204.
8. **Pełny kontekst.** Szukaj największego `-c`, który startuje z drafterem. Na Inklingu `IK2_DRAFT_CTX` ogranicza tylko drafter (557 056). Potem `needle.py`: igły 5/5 przy 95% głębokości z 700 tokenami odpowiedzi. Szczyt VRAM + 512 MiB ≤ VRAM. Lekcja: Maya stała na 16k przez tydzień ([[lekcja-maya-16k-kontekstu]]).
9. **Bramka md5 i KLD.** md5 T=0 z drafterem = bez draftera = poprzednia produkcja. K-208 tak znalazł okna sufiksowe, które nie były bitowe. Okna weryfikacji bitowo = dekod. KL z ramieniem podłogi, bo Inkling IQ3_S reaguje na zaburzenie 1e-5 KL 0,002–0,009 ([[zgodnosc-bitowa-md5]], [[bramka-kld-kanarki]]).
10. **Odmowy, jeśli model jest bez cenzury.** 5 promptów: oczekiwane 0/5 ([[2026-11-28-k207-ablacja-zamiast-lora]]). Ablacja wpieczona albo `--ablate-lora` zamiast LoRA w locie (+41%).
11. **Optymalizacje po kolei według zysku** z [[rodzaje-modeli]]. Każda zmiana: ABBA ×2, md5, przełącznik env (wyłącznik). KILL zapisz z powodem w [[wyniki-negatywne]].
12. **Pomiar wall i prefill.** `wall.py` (4 prompty × 300 tokenów: kod, tech, pl, json; mediana T=0 i T=0,7), dekod przy 32k/90k/maks., prefill 2k/32k/maks., a dla porównania z zewnątrz format LocalMaxxing (K-208: 157,4 z drafterem, 111,3 bez).
13. **Wpis w [[TOPKI]] w tej samej turze co pomiar.** Skrypt `~/qwen-opt/topki/<karta>/<model>.sh`, wiersz w tabeli [[topki]]: build, env, kontekst, liczba.
14. **Wpis w [[REKORDY]]** z datą, ścieżką logu i kolumną „w produkcji”.
15. **Wdrożenie.** `ACTIVE` + `topka-restart.sh`, smoke md5 wdrożenia = pomiar, keeper żyje. Zmiana modelu czatu wymaga decyzji JARO.

## Typowe czasy (Inkling)
Pierwszy pomiar 2026-11-21, Maya z drafterem w produkcji 2026-11-25, pełny kontekst dopiero 2026-11-27 po decyzji JARO. Krok 8 ma być przed krokiem 11, nie po nim.

## Powiązane
- [[procedura-znany-model-nowa-karta]]
- [[rodzaje-modeli]]
- [[decyzje/2026-11-27-zawsze-pelny-kontekst]]
- [[inkling-2-mini]]
- [[TOPKI]]
