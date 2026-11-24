---
typ: hub
tags: [metody, hub]
aktualizacja: 2026-11-22
zrodlo: wiki/tools/wiki.py index
status: aktualne
streszczono: 2026-11-22
---
# Metody pracy

**Jak pracujemy i myślimy: playbook profil → hipoteza → łatka → bramka → pomiar ABBA.**

<!-- Jarvo:STRESZCZENIE -->
Jak pracujemy: sufit przed pracą (bajty/token ÷ pasmo, [[skill-io-sufity]]), jedna zmiana naraz i ABBA ([[pomiar-abba]]), bramka KLD/md5 przed przyjęciem, test jednego pomysłu na karcie ≤ 10 min, wynik zawsze baseline → teraz → przyrost.
<!-- /Jarvo:STRESZCZENIE -->

Każda optymalizacja przechodzi bramkę poprawności, zanim liczy się jej zysk. Narzędzia, które to realizują: [[narzedzia/_hub|Narzędzia]].

Wróć: [[index|Strona główna]]. Lista niżej jest generowana przez `python3 tools/wiki.py index`; nie edytuj jej ręcznie.

<!-- AUTO:START -->
## Notatki (27)

- [[ablacja|Ablacja zamiast zgadywania]] — Wyłączamy kolejne części kernela w specjalnym buildzie i patrzymy, ile czasu znika; to pokazuje, co naprawdę ogranicza kernel.
- [[analiza-platformy|Analiza platformy (obowiązkowy krok)]] — Każda łatka, profil i ustawienie dostaje rubrykę „gdzie działa i co się zmienia” na Linux / Windows / macOS; bez niej nie trafia do produktu (decyzja z 2026-10-15).
- [[bramka-kld-kanarki|Bramka KLD z kanarkami]] — Zmianę numeryki przepuszczamy tylko, gdy KLD względem referencji f16-KV mieści się w 2σ bazy, a celowo zepsute warianty („kanarki”) bramka musi odrzucić.
- [[lektury-dekod-podstawy|Cztery podstawowe lektury o dekodzie LLM (i co z nich już stosujemy)]] — Kanon „od pierwszych zasad” dla dekodu: arytmetyka inferencji (kipply), Flash-Decoding, gpt-fast i oryginalna praca o spekulacji; wszystkie cztery mechanizmy są już u nas w użyciu, więc to lista do nauki i wdrażania nowych osób, nie źródło nowych dźwigni.
- [[fabryka-v1|Fabryka v1: role, ledger, kaskada bramek]] — Propozycja raportu 15f: fabryka przepisów jako role z rozdzielonymi uprawnieniami, karta twierdzenia zapisywana przed pomiarem, `ledger.jsonl` z łańcuchem hashy pisany tylko przez deterministyczny weryfikator i kaskada bramek G0–G7.
- [[kernel-tuner|Kernel Tuner: strojenie parametrów kerneli]] — Przeszukujemy parametry prawdziwych kerneli ggml (warpy, wiersze na blok) i przyjmujemy tylko konfiguracje bitowo równe produkcji.
- [[skill-io-publikacja|Kwalifikacja i publikacja wg skill-io (publishing.md) a nasze wdrożenia topki i Enigmy]] — Przepis jest coś wart tylko wtedy, gdy ktoś inny go odbuduje i dostanie ten sam wynik (`publishing.md:3`). Nasze wdrożenia spełniają przypinanie, bramkę md5 i dowód „kopia = najlepsze”. Brakuje pełnego zestawu 6 bramek akceptacji (narzędzia w obie strony, igła przy 85% okna, rozdzielenie myślenia) i budowania produkcji z czystego checkoutu przypiętego commita.
- [[loo|Leave-one-out łatek (LOO)]] — Wyłączamy po jednej łatce i mierzymy, czy bez niej jest wolniej; łatka bez mierzalnego zysku jest kandydatem do usunięcia.
- [[najpierw-baza-kb|Najpierw baza: `kb search` / `kb facts` przed pytaniem i pomiarem]] — Zasada od 2026-10-19 (`AGENTS.md`, wiersz 8, i `~/AGENTS.md`): zanim agent zapyta albo zacznie mierzyć, szuka w bazie – `kb search <pytanie>` albo `kb facts <pytanie> [--max|--min]` – i odpowiada liczbą z `plik:linia`; `wiki.py search` deleguje do `kb` (`KB_NO_DELEGATE=1` przywraca stare).
- [[physics-floor-check|Physics-floor check: czas kernela ≥ bajty / pasmo]] — Każdy zmierzony czas kernela porównać z fizyczną podłogą (bajty do przeczytania / szczytowe pasmo); wynik szybszy niż podłoga to błąd pomiaru, nie rekord – u nas tak wyszedł raport „1075 GB/s, 112% peaku”, który przy MTP był ~400 GB/s (propozycja raportu 21b #8, wzorem KernelGuard i SOL-ExecBench, 2026-10-19).
- [[playbook-optymalizacji|Playbook optymalizacji]] — Każda optymalizacja przechodzi tę samą pętlę: sufit → profil → hipoteza z budżetem → łatka z wyłącznikiem → bramka poprawności → przeplatane A/B → wpis w NOTES.
- [[podrecznik-gpu|Podręcznik optymalizacji GPU (wejście dla nowego agenta)]] — Decode przy batch 1 to strumień bajtów: Qwen3.8-27B plain czyta 16.82 GB/krok przy 75.7% pasma XTX, LFM2.5 1.777 GB/token przy 54%; vendorzy i konkurenci nie mają lepszej pętli GEMV niż nasza wielokolumnowa, najsłabsza gorąca ścieżka to MMVQ n=1, a największą dźwignią na XTX jest bezpieczne PM4 (raport 23f, synteza raportów RE, 2026-10-19).
- [[dowod-offline|Praca offline przed oknem GPU]] — Gdy GPU jest zajęte albo zakazane, przygotowujemy zmiany do końca bez niego (kompilacja, ISA, emulacja, dry-run) i zostawiamy gotowe komendy na okno GPU.
- [[skill-io-pulapki|Pułapki silników i sprzętu wg skill-io (gotchas.md) a nasze lekcje]] — Z 32 pułapek 9 przerobiliśmy sami, każdą z własną lekcją. Na nasz stos (llama.cpp, ROCm, AMD dyskretna) nowe są dwie: wolne KV q8_0 przy modelach z małą liczbą warstw KV (jest w naszym wyborze q4_0 + `kvq`) i wyciek grafów HIP w ExLlama na ROCm. Reszta dotyczy vLLM/SGLang/Intel/Apple albo pamięci zunifikowanej.
- [[petla-rsi-f|Pętla RSI-F: samodoskonalenie fabryki bez trenowania wag (projekt)]] — Przeniesienie RSI na naszą pracę nad silnikiem: tylko werdykt `CONFIRMED` z fabryki staje się materiałem; świeży Rewriter pisze z niego playbook, Recenzent sprawdza przeciek, a do `skills/` trafia tylko playbook, z którym świeży Replayer powtórzył zysk na innym celu (raport 21h, 2026-10-19).
- [[re-vendorow-zasady|Reverse engineering bibliotek producentów: tylko metadane i black-box]] — Zasada z raportu 21l (rekomendacja, nie porada prawna, 2026-10-19): kody vendorów badamy tylko przez metadane i pomiary black-box; deasemblujemy wyłącznie nasze własne binarki i otwarte biblioteki.
- [[reward-hacking-inferencji|Reward hacking w optymalizacji inferencji: wzorce i nasze luki]] — Znane hacki to: praca na bocznym strumieniu poza timerem, pusty pierwszy chunk SSE (TTFT < 3 ms), cache wyników po adresie wskaźnika, liczenie wywołań do wykrycia fazy pomiaru, niższa precyzja przy luźnej tolerancji i podmiana modelu pod kanoniczną nazwą (InferenceBench, Overshoot, wafer, GPU MODE; 2026-11-05).
- [[serializacja-gpu|Serializacja GPU między agentami]] — Wielu agentów dzieli jedną kartę, więc każdy pomiar bierze locki, używa własnego portu i sprząta po sobie serwery.
- [[skill-io-przeglad|Skill „inference-optimisation” (Sybil Solutions): wspinaczka po prędkości serwera LLM — przegląd i lekcje]] — Agentowy przepis na strojenie serwera LLM na dowolnym sprzęcie. Sześć kroków: policz sufit, zmieniaj jedną rzecz, mierz między kontrolami, loguj także porażki, bramkuj igłami w długim kontekście, publikuj z czystego przypiętego buildu (`README.md:13-20`). Robimy to samo od miesiąca. Najcenniejsze dla nas są sufity jako stała kolumna raportu oraz bramki, których nie mamy: igły, round trip narzędzi, flaga pętli.
- [[ashhart-skills-infra|Skille ashhart (TensorFold): co z nich bierzemy do pomiarów, wyścigu i serwowania]] — Skrypty są krótkie i robią to, co opisują, ale ich wartość to metoda: prognoza liczbowa przed budową, tani „kill-probe”, werdykt A/B w kolejności B,C,C,B z podłogą szumu, dziennik ślepych uliczek i bramki zasobów kernela. Na naszych danych dały dwa twarde wyniki: dzisiejsze „+3–7%” z fuzji było do przewidzenia jako +0,8% (zmierzone +0,6%), a nasz serwer Qwen ma zdrowy cache prefiksu i poprawne wywołania narzędzi.
- [[emulator-isa|Symboliczny emulator ISA (dowód bitowości offline)]] — Gdy GPU było niedostępne, bitowość nowego kernela GDN udowodniliśmy, emulując symbolicznie skompilowane ISA gfx11 i porównując grafy operacji float z bazą.
- [[weaponized-curiosity|Weaponized Curiosity: skill badań i autoresearchu dla agentów, porównany z naszym wyścigiem]] — To sam proces w Markdownie (Codex, Claude Code), bez kerneli; 23.11 oceniłem go jako „to, co już robimy”, ale pomiar 24.11 pokazał, że trzech jego elementów nie mamy: zamrożonego ewaluatora z rezerwą na walidację, budżetu prób zapisanego przed startem i dziennika prób, który blokuje powtórki.
- [[wyniki-negatywne|Wyniki negatywne zapisujemy z liczbami]] — Każda próba, która nie dała zysku, trafia do NOTES z liczbami i powodem, żeby nikt nie wracał do niej bez nowego pomysłu.
- [[wylacznik-w-kazdej-latce|Wyłącznik w każdej łatce]] — Każda łatka z prędkością ma przełącznik `GGML_HIP_*=0` / `LLAMA_*=0`, który przywraca starą ścieżkę w tej samej binarce, więc A/B nie miesza zmiennej „inny build”.
- [[dowod-z-profilu|Zasady uczciwego dowodu z profilu]] — Każde podsumowanie trace'u/profilu musi mówić, ile pokrywa: liczba wierszy razem, zachowanych i wyciętych (z oknem w ns), liczba kolejek i strumieni, union-busy vs sum-busy (różnica > 0.1% → ostrzeżenie); pusty selektor albo 0 dopasowań to INCOMPLETE z kodem ≠ 0, a profil z `GGML_HIP_PM4` ≠ 0 jest odrzucany (P2 z raportu 21j, 2026-10-19).
- [[zgodnosc-bitowa-md5|Zgodność bitowa (greedy md5, hash logitów)]] — Zmiana „bitowo identyczna” musi dać ten sam tekst greedy (md5) na świeżym serwerze i te same logity co baza w tym samym trybie.
- [[zmiany-fabryki-z-21i|Zmiany fabryki v1 i RSI-F z RSI-Inference Bench (propozycja)]] — Dwanaście mechanizmów z benchmarku Apple przełożonych na karty i bramki naszej fabryki; najwyżej w priorytecie: werdykt `VOID` oddzielony od `INVALID`, audyt promptów Implementera (każde „nie wolno X” ma regułę z fixture'em albo znika) i worktree bez historii przed P2 (raport 21i, 2026-10-19).
<!-- AUTO:END -->
