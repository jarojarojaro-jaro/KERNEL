---
typ: ekosystem
tags: [ekosystem, serwowanie, agenci, strata, produkt, nvidia]
aktualizacja: 2026-11-24
zrodlo: https://github.com/DevDock-AI/Speedy (fork Straty, licencja osobista/niekomercyjna, push 2026-11-22) — README.md (sekcje „Why Speedy”, „Quality, measured”, „Speed”, „Under the hood”); Telegram „gpu” 2026-11-19
status: aktualne
---
# Speedy (DevDock-AI, fork Straty): serwer, który naprawia typowe błędy lokalnego modelu w pracy agenta

**Prędkość to w Speedy połowa. Druga połowa to warstwa serwera między agentem a modelem: przerywa pętle, naprawia wywołania narzędzi, pilnuje budżetu myślenia i zwalnia slot po zawieszonym kliencie. Topka i Enigma tej warstwy nie mają wcale.**

## Co robi serwer (README, „Under the hood”)
- **Budżet rozumowania:** domyślnie wysiłek `medium` i 32K tokenów myślenia. Przy 60% i 80% budżetu model dostaje przypomnienie, żeby kończył, a miejsce na odpowiedź jest zarezerwowane, więc odpowiedź nie urywa się przed treścią.
- **Wyłącznik pętli agenta:** powtarzane wywołania, edycje tam i z powrotem i puste zapisy dostają notkę z następnym krokiem. Gdy agent dalej to robi, narzędzia edycji są wstrzymane.
- **Wywołania narzędzi:** nazwa sprawdzana z listą zadeklarowaną przez klienta, zepsute wywołanie generowane ponownie, typy argumentów poprawiane. Wywołanie sprzeczne z tym, co model właśnie zapowiedział, jest wybierane od nowa.
- **Ciągłość cache:** myślenie odtwarzane między turami, więc rozmowa z narzędziami idzie dalej z cache zamiast czytać wszystko od nowa.
- **Strażnicy:** zawieszone ciało żądania albo klient, który przestał czytać, zwalniają slot.
- **Instalacja:** domyślnie strojony profil jednej karty, sprawdzenie, czy wybrany kontekst mieści się w VRAM, największy kwant, który mieści się w całości, i aktualizacje, które doprowadzają stare instalacje do tych samych ustawień.
- API OpenAI i Anthropic (OpenCode, Claude Code, Codex CLI).

## Jak mierzą jakość
- 24 prawdziwe zadania agenta przez OpenCode na prawdziwym serwerze: 24/24 w 13,3 min, wcześniej 21–24/24 w ~20 min. Trudniejsze: 9/11 (84/86 sprawdzeń).
- 24/24 poprawnych wywołań narzędzi, igła ~214K 48/48, IFBench 81,0 wobec 81,3 z karty BF16 (różnica w szumie ±2,3).
- Zmiana silnika wchodzi tylko po A/B w tym samym oknie i bramce: porównanie token po tokenie z referencją, bramka kodu, igła. Uczciwie piszą, że agentowe zestawy to jeden przebieg, „kierunek, nie ranking”.

## Prędkość (dla porządku)
- Flash-Next 125B MoE (nie nasz model), RTX 3080 20 GB, eksperci w RAM (~128 GB): UD-Q4_K_XL 115–122 t/s, Q2_0 146–168 t/s. Z drugą kartą 155–216 t/s.

## Porównanie z naszym odpowiednikiem
- **Topka (:8080) i proxy Enigmy** (`app/engine/src/server/api.ts:104`) przepuszczają żądania bez zmian. Nasz serwer ma tylko bezpieczne parsowanie znaczników narzędzi (`LLAMA_SERVER_SAFE_TOOLS`, `~/praca/llama-duo/common/chat.h:330`), ale nie naprawia wywołań i nie przerywa pętli. Pętle agenta, zepsute wywołania i urwane myślenie łapiemy ręcznie: MMLU-Pro zapętlił się do 32 768 tokenów ([[skill-io-przeglad]]), a odzysk tool-calli ze Straty 0.2.8 (92,9 → 98,3%) czeka od R63a jako „pomysł do serwera” ([[strata]]).
- **Enigma Chat** odsyła historię bez `reasoning_content` (`app/engine/src/ui/components/Chat.svelte:40`), czyli bez ciągłości myślenia, którą Speedy włącza domyślnie (to samo w [[colibri]]).
- **Jakość mierzą na zadaniach agenta przez prawdziwego klienta.** Enigma mierzy tylko t/s i md5. Topka ma bramki KLD i md5, ale nie ma stałego zestawu zadań agenta.

## Co bierzemy
1. Wyłącznik pętli i naprawę wywołań narzędzi jako warstwę proxy Enigmy (bez zmian w silniku; każde zachowanie z wyłącznikiem, żądanie klienta wygrywa jak u nich).
2. Budżet myślenia z przypomnieniami i rezerwą na odpowiedź dla Qwena z myśleniem.
3. Strażnika slotu dla klienta, który przestał czytać.
4. Zestaw zadań agenta przez prawdziwego klienta (OpenCode albo omp) jako bramkę każdej zmiany serwera.

## Powiązane
- [[strata]]
- [[colibri]]
- [[inference-stack]]
- [[lekcja-uczymy-sie-nie-tylko-predkosc]]
