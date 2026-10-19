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
## Notatki (33)

- [[aob-v1|`aob-v1` (AMD-Opt Bench): benchmark regresji RSI-F z naszej historii (projekt)]] — Własny benchmark w formacie Harbor-lite (`task.toml`, `instruction.md`, `environment/`, ukryte `tests/`, `solution/oracle.patch` + `null.patch`) z fabryką jako weryfikatorem i podziałem dev (łatki 0001–0047) / test (0048–0070 + negatywy); przy naszym budżecie GPU to test regresji i postępu RSI-F, nie leaderboard – przy 10 zadaniach SE ≈ 0.15 (raport 21i, 2026-10-19).
- [[ablacja|Ablacja zamiast zgadywania]] — Wyłączamy kolejne części kernela w specjalnym buildzie i patrzymy, ile czasu znika; to pokazuje, co naprawdę ogranicza kernel.
- [[agr-lookup-zgodny-z-mtp|AGR: wybór kandydata lookupu zgodnego z draftami MTP]] — Reguła bez treningu i bezstratna: spośród kandydatów lookupu (sufiks ≥ 2 albo ≥ 4 tokenów) zostawić tych, których pierwsze 4 tokeny kontynuacji równają się 4 draftom MTP, potem najdłuższy sufiks, potem najnowszy; w symulacji AGR2 daje +3.7% t/s na agencie (2/3 sufitu idealnego pointera) i +0.6% na czacie (raport 21c, 2026-10-19).
- [[analiza-platformy|Analiza platformy (obowiązkowy krok)]] — Każda łatka, profil i ustawienie dostaje rubrykę „gdzie działa i co się zmienia” na Linux / Windows / macOS; bez niej nie trafia do produktu (decyzja z 2026-10-15).
- [[bramka-kld-kanarki|Bramka KLD z kanarkami]] — Zmianę numeryki przepuszczamy tylko, gdy KLD względem referencji f16-KV mieści się w 2σ bazy, a celowo zepsute warianty („kanarki”) bramka musi odrzucić.
- [[fabryka-v1|Fabryka v1: role, ledger, kaskada bramek]] — Propozycja raportu 15f: fabryka przepisów jako role z rozdzielonymi uprawnieniami, karta twierdzenia zapisywana przed pomiarem, `ledger.jsonl` z łańcuchem hashy pisany tylko przez deterministyczny weryfikator i kaskada bramek G0–G7.
- [[kernel-tuner|Kernel Tuner: strojenie parametrów kerneli]] — Przeszukujemy parametry prawdziwych kerneli ggml (warpy, wiersze na blok) i przyjmujemy tylko konfiguracje bitowo równe produkcji.
- [[kld-po-polsku|KLD kwantów na polskim tekście (protokół 16e)]] — Referencja to prawdziwe BF16 (na 48 GB z `-fit on`, offload do RAM, 54–240 s na korpus), a ocena idzie na pięciu korpusach o stałych md5, w tym trzech polskich; KLD-PL/KLD-wiki pokazuje, czy kwant ma „angielski” imatrix.
- [[kontroler-szerokosci-draftu|Kontroler szerokości draftu (wzorzec Magnitude)]] — Magnitude (`draft_control.rs`, domyślnie włączony) co rundę wybiera parę (wydraftowane, zweryfikowane) o największej liczbie tokenów na sekundę z drabinki szerokości wypełniających klasy wierszy 2/4/8/16; u nich propozycji/krok waha się od 0.23 (9B pl-proza) do 6.75 (27B pl-kod).
- [[koszt-szerokosci-weryfikacji|Krzywa kosztu szerokości weryfikacji V(w, kontekst) na XTX]] — Pomiar E2 z 16b (`llama-bench -fa 1 -ctk q4_0 -ctv q4_0 -p 1,5,8,9,16 -n 0 -d …`, mediana powtórzeń 3–5, Qwen3.8-27B): V16 − V5 = 6.40 / 7.13 / 9.50 / 12.45 ms przy 2k / 8k / 32k / 64k – hipoteza 15b „≤ 12 ms przy 32k” potwierdzona (2026-10-18).
- [[ksztalt-ruchu-agentowego|Kształt ruchu agentowego wg śladów AgentX]] — Korpus AgentX v1.0 256k (393 sesje Claude Code, 06-2026): wejście p50 88 768 / p90 204 288 tokenów, wyjście p50 376 / p90 1845 – stosunek 117:1; limit kontekstu 128k zostawia 66.3% zapytań, 64k 35.3%; przy współdzieleniu prefiksów nietrafionych w cache jest radix 3.8%, lane 8.5%, single 20.6% wejścia (2026-10-19).
- [[loo|Leave-one-out łatek (LOO)]] — Wyłączamy po jednej łatce i mierzymy, czy bez niej jest wolniej; łatka bez mierzalnego zysku jest kandydatem do usunięcia.
- [[mikrobench-granicy-kernela|Mikrobenchmark granicy kernela]] — Zanim zainwestujemy w fuzje albo nowy sposób wysyłania pracy, mierzymy, ile kosztuje sama granica między kernelami na danym stosie.
- [[model-kosztu-weryfikacji-moe|Model kosztu weryfikacji MoE (LFM2.5)]] — Weryfikacja N tokenów w MoE czyta sumę ekspertów wszystkich N tokenów: przy niezależnym routingu u(N) = 64·(1 − (60/64)^N) ekspertów na warstwę, B(N) = 0.761 + 0.254·u(N) GB, T(N) ≈ 1.45 ms + B(N)/0.9 GB/ms; kalibracja T(1) = 3.42 ms vs zmierzone 3.40 (raport 18, 2026-10-19, `[SZACUNEK]`).
- [[ms-na-krok|ms/krok jako główna metryka spekulacji]] — Przy dekodowaniu spekulacyjnym t/s = (tokeny na krok) / (czas kroku); kernel zmienia tylko czas kroku, więc to ms/krok mierzy łatkę, a t/s miesza ją z losowością tekstu.
- [[najpierw-baza-kb|Najpierw baza: `kb search` / `kb facts` przed pytaniem i pomiarem]] — Zasada od 2026-10-19 (`AGENTS.md`, wiersz 8, i `~/AGENTS.md`): zanim agent zapyta albo zacznie mierzyć, szuka w bazie – `kb search <pytanie>` albo `kb facts <pytanie> [--max|--min]` – i odpowiada liczbą z `plik:linia`; `wiki.py search` deleguje do `kb` (`KB_NO_DELEGATE=1` przywraca stare).
- [[physics-floor-check|Physics-floor check: czas kernela ≥ bajty / pasmo]] — Każdy zmierzony czas kernela porównać z fizyczną podłogą (bajty do przeczytania / szczytowe pasmo); wynik szybszy niż podłoga to błąd pomiaru, nie rekord – u nas tak wyszedł raport „1075 GB/s, 112% peaku”, który przy MTP był ~400 GB/s (propozycja raportu 21b #8, wzorem KernelGuard i SOL-ExecBench, 2026-10-19).
- [[playbook-optymalizacji|Playbook optymalizacji]] — Każda optymalizacja przechodzi tę samą pętlę: sufit → profil → hipoteza z budżetem → łatka z wyłącznikiem → bramka poprawności → przeplatane A/B → wpis w NOTES.
- [[pomiar-abba|Pomiar: przeplatane A/B (ABBA) na ms/krok]] — Porównania robimy w jednej binarce, przeplatając warianty (ABBA), na metryce ms/krok, z kilkoma seedami i promptami; pojedynczy przebieg nic nie dowodzi.
- [[dowod-offline|Praca offline przed oknem GPU]] — Gdy GPU jest zajęte albo zakazane, przygotowujemy zmiany do końca bez niego (kompilacja, ISA, emulacja, dry-run) i zostawiamy gotowe komendy na okno GPU.
- [[petla-rsi-f|Pętla RSI-F: samodoskonalenie fabryki bez trenowania wag (projekt)]] — Przeniesienie RSI na naszą pracę nad silnikiem: tylko werdykt `CONFIRMED` z fabryki staje się materiałem; świeży Rewriter pisze z niego playbook, Recenzent sprawdza przeciek, a do `skills/` trafia tylko playbook, z którym świeży Replayer powtórzył zysk na innym celu (raport 21h, 2026-10-19).
- [[re-vendorow-zasady|Reverse engineering bibliotek producentów: tylko metadane i black-box]] — Zasada z raportu 21l (rekomendacja, nie porada prawna, 2026-10-19): kody vendorów badamy tylko przez metadane i pomiary black-box; deasemblujemy wyłącznie nasze własne binarki i otwarte biblioteki.
- [[serializacja-gpu|Serializacja GPU między agentami]] — Wielu agentów dzieli jedną kartę, więc każdy pomiar bierze locki, używa własnego portu i sprząta po sobie serwery.
- [[sprzezone-probkowanie-draftu|Sprzężone próbkowanie draftu (coupled sampling)]] — Magnitude losuje każdą propozycję draftu z tym samym ziarnem i pozycją co próbka celu (Gumbel-max na Philox4x32-10 kluczowany pozycją i tokenem), więc przy równych rozkładach draft i cel wybierają ten sam token także przy T=1; metoda bezstratna i przenośna 1:1.
- [[sufit-pasma-i-mapa-czasu|Sufit pasma i mapa czasu kroku]] — Zanim cokolwiek zmienimy, liczymy, ile bajtów musi przeczytać krok (sufit pasma) i gdzie naprawdę idzie czas (profil rocprofv3 w modelu).
- [[emulator-isa|Symboliczny emulator ISA (dowód bitowości offline)]] — Gdy GPU było niedostępne, bitowość nowego kernela GDN udowodniliśmy, emulując symbolicznie skompilowane ISA gfx11 i porównując grafy operacji float z bazą.
- [[wyniki-negatywne|Wyniki negatywne zapisujemy z liczbami]] — Każda próba, która nie dała zysku, trafia do NOTES z liczbami i powodem, żeby nikt nie wracał do niej bez nowego pomysłu.
- [[wylacznik-w-kazdej-latce|Wyłącznik w każdej łatce]] — Każda łatka z prędkością ma przełącznik `GGML_HIP_*=0` / `LLAMA_*=0`, który przywraca starą ścieżkę w tej samej binarce, więc A/B nie miesza zmiennej „inny build”.
- [[dowod-z-profilu|Zasady uczciwego dowodu z profilu]] — Każde podsumowanie trace'u/profilu musi mówić, ile pokrywa: liczba wierszy razem, zachowanych i wyciętych (z oknem w ns), liczba kolejek i strumieni, union-busy vs sum-busy (różnica > 0.1% → ostrzeżenie); pusty selektor albo 0 dopasowań to INCOMPLETE z kodem ≠ 0, a profil z `GGML_HIP_PM4` ≠ 0 jest odrzucany (P2 z raportu 21j, 2026-10-19).
- [[zestaw-odlozony|Zestaw odłożony i klątwa zwycięzcy]] — Decyzje konfiguracji spekulacji wybrane na 6 promptach spec_sweep nie przenoszą się na prompt odłożony (przewaga +2.22% → −4.34%, zmiana znaku w 3/5 przypadków), więc twierdzenia o konfiguracji wymagają zapieczętowanego zestawu promptów spoza selekcji.
- [[zestaw-copy-mvs|Zestawy kopii i edycji: `copy`, `mvs`, `long`]] — Trzy zestawy z 16b do mierzenia spekulacji na ruchu agentowym (kopia i edycja), uzupełniające `spec_sweep` (nowe pisanie): `copy` (6 promptów), `mvs` (4 pliki code-edit z MagnitudeVs) i `long` (~30k tokenów).
- [[zgodnosc-bitowa-md5|Zgodność bitowa (greedy md5, hash logitów)]] — Zmiana „bitowo identyczna” musi dać ten sam tekst greedy (md5) na świeżym serwerze i te same logity co baza w tym samym trybie.
- [[zmiany-fabryki-z-21i|Zmiany fabryki v1 i RSI-F z RSI-Inference Bench (propozycja)]] — Dwanaście mechanizmów z benchmarku Apple przełożonych na karty i bramki naszej fabryki; najwyżej w priorytecie: werdykt `VOID` oddzielony od `INVALID`, audyt promptów Implementera (każde „nie wolno X” ma regułę z fixture'em albo znika) i worktree bez historii przed P2 (raport 21i, 2026-10-19).
<!-- AUTO:END -->
