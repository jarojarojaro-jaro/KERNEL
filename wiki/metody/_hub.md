---
typ: hub
tags: [metody, hub]
aktualizacja: 2026-10-16
zrodlo: wiki/tools/wiki.py index
status: aktualne
---
# Metody pracy

**Jak pracujemy i myślimy: playbook profil → hipoteza → łatka → bramka → pomiar ABBA.**

Każda optymalizacja przechodzi bramkę poprawności, zanim liczy się jej zysk. Narzędzia, które to realizują: [[narzedzia/_hub|Narzędzia]].

Wróć: [[index|Strona główna]]. Lista niżej jest generowana przez `python3 tools/wiki.py index`; nie edytuj jej ręcznie.

<!-- AUTO:START -->
## Notatki (20)

- [[ablacja|Ablacja zamiast zgadywania]] — Wyłączamy kolejne części kernela w specjalnym buildzie i patrzymy, ile czasu znika; to pokazuje, co naprawdę ogranicza kernel.
- [[analiza-platformy|Analiza platformy (obowiązkowy krok)]] — Każda łatka, profil i ustawienie dostaje rubrykę „gdzie działa i co się zmienia” na Linux / Windows / macOS; bez niej nie trafia do produktu (decyzja z 2026-10-15).
- [[bramka-kld-kanarki|Bramka KLD z kanarkami]] — Zmianę numeryki przepuszczamy tylko, gdy KLD względem referencji f16-KV mieści się w 2σ bazy, a celowo zepsute warianty („kanarki”) bramka musi odrzucić.
- [[fabryka-v1|Fabryka v1: role, ledger, kaskada bramek]] — Propozycja raportu 15f: fabryka przepisów jako role z rozdzielonymi uprawnieniami, karta twierdzenia zapisywana przed pomiarem, `ledger.jsonl` z łańcuchem hashy pisany tylko przez deterministyczny weryfikator i kaskada bramek G0–G7.
- [[kernel-tuner|Kernel Tuner: strojenie parametrów kerneli]] — Przeszukujemy parametry prawdziwych kerneli ggml (warpy, wiersze na blok) i przyjmujemy tylko konfiguracje bitowo równe produkcji.
- [[kontroler-szerokosci-draftu|Kontroler szerokości draftu (wzorzec Magnitude)]] — Magnitude (`draft_control.rs`, domyślnie włączony) co rundę wybiera parę (wydraftowane, zweryfikowane) o największej liczbie tokenów na sekundę z drabinki szerokości wypełniających klasy wierszy 2/4/8/16; u nich propozycji/krok waha się od 0.23 (9B pl-proza) do 6.75 (27B pl-kod).
- [[loo|Leave-one-out łatek (LOO)]] — Wyłączamy po jednej łatce i mierzymy, czy bez niej jest wolniej; łatka bez mierzalnego zysku jest kandydatem do usunięcia.
- [[mikrobench-granicy-kernela|Mikrobenchmark granicy kernela]] — Zanim zainwestujemy w fuzje albo nowy sposób wysyłania pracy, mierzymy, ile kosztuje sama granica między kernelami na danym stosie.
- [[ms-na-krok|ms/krok jako główna metryka spekulacji]] — Przy dekodowaniu spekulacyjnym t/s = (tokeny na krok) / (czas kroku); kernel zmienia tylko czas kroku, więc to ms/krok mierzy łatkę, a t/s miesza ją z losowością tekstu.
- [[playbook-optymalizacji|Playbook optymalizacji]] — Każda optymalizacja przechodzi tę samą pętlę: sufit → profil → hipoteza z budżetem → łatka z wyłącznikiem → bramka poprawności → przeplatane A/B → wpis w NOTES.
- [[pomiar-abba|Pomiar: przeplatane A/B (ABBA) na ms/krok]] — Porównania robimy w jednej binarce, przeplatając warianty (ABBA), na metryce ms/krok, z kilkoma seedami i promptami; pojedynczy przebieg nic nie dowodzi.
- [[dowod-offline|Praca offline przed oknem GPU]] — Gdy GPU jest zajęte albo zakazane, przygotowujemy zmiany do końca bez niego (kompilacja, ISA, emulacja, dry-run) i zostawiamy gotowe komendy na okno GPU.
- [[serializacja-gpu|Serializacja GPU między agentami]] — Wielu agentów dzieli jedną kartę, więc każdy pomiar bierze locki, używa własnego portu i sprząta po sobie serwery.
- [[sprzezone-probkowanie-draftu|Sprzężone próbkowanie draftu (coupled sampling)]] — Magnitude losuje każdą propozycję draftu z tym samym ziarnem i pozycją co próbka celu (Gumbel-max na Philox4x32-10 kluczowany pozycją i tokenem), więc przy równych rozkładach draft i cel wybierają ten sam token także przy T=1; metoda bezstratna i przenośna 1:1.
- [[sufit-pasma-i-mapa-czasu|Sufit pasma i mapa czasu kroku]] — Zanim cokolwiek zmienimy, liczymy, ile bajtów musi przeczytać krok (sufit pasma) i gdzie naprawdę idzie czas (profil rocprofv3 w modelu).
- [[emulator-isa|Symboliczny emulator ISA (dowód bitowości offline)]] — Gdy GPU było niedostępne, bitowość nowego kernela GDN udowodniliśmy, emulując symbolicznie skompilowane ISA gfx11 i porównując grafy operacji float z bazą.
- [[wyniki-negatywne|Wyniki negatywne zapisujemy z liczbami]] — Każda próba, która nie dała zysku, trafia do NOTES z liczbami i powodem, żeby nikt nie wracał do niej bez nowego pomysłu.
- [[wylacznik-w-kazdej-latce|Wyłącznik w każdej łatce]] — Każda łatka z prędkością ma przełącznik `GGML_HIP_*=0` / `LLAMA_*=0`, który przywraca starą ścieżkę w tej samej binarce, więc A/B nie miesza zmiennej „inny build”.
- [[zestaw-odlozony|Zestaw odłożony i klątwa zwycięzcy]] — Decyzje konfiguracji spekulacji wybrane na 6 promptach spec_sweep nie przenoszą się na prompt odłożony (przewaga +2.22% → −4.34%, zmiana znaku w 3/5 przypadków), więc twierdzenia o konfiguracji wymagają zapieczętowanego zestawu promptów spoza selekcji.
- [[zgodnosc-bitowa-md5|Zgodność bitowa (greedy md5, hash logitów)]] — Zmiana „bitowo identyczna” musi dać ten sam tekst greedy (md5) na świeżym serwerze i te same logity co baza w tym samym trybie.
<!-- AUTO:END -->
