---
typ: ekosystem
tags: [ekosystem, spekulacja, lookup]
aktualizacja: 2026-11-24
zrodlo: ~/KERNEL/product/research/18-nastepna-fala.md:340-354; https://arxiv.org/abs/2411.04975
status: do-sprawdzenia
---
# SuffixDecoding / ArcticInference: globalne drzewa sufiksów

**Spekulacja bez modelu draftującego z drzew sufiksów budowanych z promptów i wcześniejszych wyjść (także między żądaniami); na workloadach agentowych do ×5.3, ×2.8 względem EAGLE-2/3 (arXiv 2411.04975, w vLLM jako „suffix”).**

Dla nas: pomysł #6 raportu 18 – globalny cache sufiksów między żądaniami, sesjami i agentami, ponad dzisiejszy lookup z kontekstu ([[2026-10-18-lookup-ogon]]); szacunek +5–15% na mieszance agenta, bramka: replay sesji omp ≥ 3%.

## Przegląd 2026-11-24 (nauka, nie tylko prędkość)

- Szacunek „+5–15%” powyżej jest nieaktualny: globalny cache sufiksów zmierzyliśmy w R68b na prawdziwej sesji omp. Korpus 400 wcześniejszych sesji (49.8 M tokenów) dokłada w ogonie poza zasięgiem MTP-4 tylko **0.1%** tokenów, a lookup z bieżącej sesji 9.1% (`product/research/68b-spekulacja-nowe.md:15,138-152`). Pomysł 18 #6: kill.
- Dlaczego u nich ×5.3, a u nas 0.1%: SuffixDecoding mierzono na powtarzalnych zadaniach wielu użytkowników (SWE-Bench, Text-to-SQL), gdzie odpowiedzi się powtarzają. U nas jeden użytkownik, różne zadania, a MTP i tak łapie krótkie frazy (P(MTP | lookup) = 0.97).
- Lekcja ogólna: zysk z drzewa sufiksów zależy od rodzaju ruchu, nie od algorytmu. W serwerze wielu klientów z tymi samymi zadaniami (np. firma z jednym agentem do SQL) mógłby wrócić `[INFERENCE]`.
- Nasz odpowiednik w silnikach: typ `suffix` jest już w ik_llama (`ik: common/suffix-tree.cpp:105-176`, `product/research/silniki-2026-11-20/llama-cpp-ik.md:41`), czyli w gałęzi, na której stoi Maya ik2; mainline ma `ngram-mod` (wspólna tablica 16 MB).
- Co bierzemy: zostajemy przy ogonie lookupu z bieżącej sesji; przy produkcie dla firm z powtarzalnym ruchem najpierw policzyć pokrycie `suffix_cov.py` na ich śladach.

## Przegląd 2026-11-24 (nauka, nie tylko prędkość): dwa nasze pomiary się nie zgadzają
- Rejestr ZRODLA mówił „każde podejście cytuje te same liczby (×5.3 agentowe)”: cztery podejścia (R02, Q:algorithms, Q:v2, R18) powtarzały liczbę z pracy, żadne nie liczyło na naszych logach. Liczyć zaczęliśmy dopiero w R68b (11-07) i K-019 (11-20).
- **Wyniki są sprzeczne i żaden nie jest rozstrzygający:**
  - R68b (`68b-spekulacja-nowe.md:138-152`): 1 prawdziwa sesja Qwena (101 odpowiedzi, 89 tys. tokenów liczonych regexem, nie BPE), korpus 400 sesji głównie innych modeli → w ogonie poza MTP-4 korpus dokłada 0,1%, kill.
  - K-019 ([[KOLEJKA-TESTOW]], wynik `qwen-opt/k019/wynik-2026-11-20.txt`): 190 sesji omp, 8,52 mln tokenów wyjścia (tokenizer Qwen3), model kroku z MTP n=4 → cache między sesjami +8,4%, razem z lookupem w sesji +15,9% t/s (modelowo). Ograniczenie: wyjścia pisał Claude, a podagenci powtarzają podobne teksty, więc to górna granica.
  - Różnią się metodą (pokrycie ogona vs model kroku), tokenizacją i korpusem. Kill z R68b opiera się na jednej sesji; +15,9% z K-019 na tekstach innego modelu. Rozstrzyga tylko krok 2 z K-019: XTX spec_sweep + replay agenta ABBA (kill < +1%).
- **Lekcja procesu:** cztery cytowania liczby z pracy to nie badanie, a dwa tanie pomiary offline dały sprzeczne wnioski, bo każdy zmierzył coś innego. Przy sprzeczności zapisujemy obie liczby z metodą, nie wybieramy wygodnej.
- **Warstwa serwowania:** SuffixDecoding to stan serwera wspólny dla wszystkich zapytań i sesji; topka trzyma lookup w kontekście jednego slotu. W vLLM metoda `suffix` jest wbudowana i ma testy (`tests/v1/e2e/spec_decode/ngram_suffix/` w klonie `~/research/engines/vllm` @ `6c6e159`, [[vllm]]).

## Powiązane
- [[mtplx]]
- [[agr-lookup-zgodny-z-mtp]]
