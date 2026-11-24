---
typ: ekosystem
tags: [ekosystem, ocena, agenci]
aktualizacja: 2026-11-24
zrodlo: ~/KERNEL/qwen-opt/research/repos/04-kernelbench.md:1-22; ~/KERNEL/qwen-opt/research/repos/REPOS-PODSUMOWANIE.md:14
status: aktualne
---
# ScalingIntelligence/KernelBench

**Benchmark kerneli pisanych przez LLM (HEAD `423217d9`, 2026-03-05); bierzemy lepszą bramkę poprawności; werdykt: średnia (proces).**

Cztery poziomy zadań (100 operatorów, 100 fuzji, 50 architektur, 20 modeli HF), poprawność przez `torch.allclose` na wielu seedach, tolerancja 1e-4 fp32 i 1e-2 fp16/bf16, testy adwersarialne (reuse bufora z wynikiem referencji, modyfikacja wejść, inny strumień) i statyczny checker oszustw. Dla nas: diff listy kerneli przy A/B, zatruwanie buforów NaN, hash logitów w trybie wsadowym, A/A i kolejność ABBA.

## Przegląd 2026-11-24 (nauka, nie tylko prędkość)
KernelBench-Mega (kernelbench.com/mega, 2026-11-22): zadanie megakernela dekodu (KDA + MLA + MoE) dla agentów. Inkling-2-Mini jako lokalny agent: 10,04× na RTX PRO 6000 (0,606 ms/token), przed Grok 4.7 (6,34×) i Sonnet 5 (3,92×); #1 Gemini 4 Neon. Koszt podany: 686k tokenów w 2,9 h.
- **Dla naszego procesu agentów:** to jest sposób oceny, którego nie mamy w wyścigu Kernel vs Gemini — stałe zadanie, ta sama bramka, wynik razem z kosztem (tokeny, godziny). U nas wyścig liczy tylko t/s po fakcie; dopisać do dziennika wyścigu tokeny i czas na pomysł oraz błąd prognozy ([[ashhart-skills-infra]]).
- Lokalny agent kernelowy (Inkling na Mayi, ~110 t/s na XTX) jest możliwy, ale zajmuje kartę, na której mierzymy; sens tylko w kolejce `run-jobs.sh` poza pomiarami albo na drugiej maszynie.
- Lekcja kernelowa (trwały megakernel z barierą ~0,75 µs) zostaje w [[maya-ik2-inkling]].

## Przegląd 2026-11-24 (nauka, nie tylko prędkość): KernelBench-CUDA, Gemini 4 Neon #2 (2026-11-19)
Tweet Elliota Arledge'a (Telegram „gpu” 2026-11-19, bez repo i trajektorii): Neon na 2. miejscu KernelBench-CUDA. NSA 0,073 ms, a przy przybliżonym liczeniu wyników agent sam wykrył 62 przełączenia top-8 i wrócił do dokładnego. MegaQwen: dekod na 7,6% roofline, megakernel zastąpiony grafem z PDL.
- **Ten sam model, dwa wyniki.** Ten sam Gemini 4 Neon dzień później napisał dla nas Enigma Turbo: bełkot przy 0,7 t/s, kod GPU niewywoływany, „ALL PASS” na syntetycznym modelu ([[enigma-turbo-gemini-2026-11-20]]). W KernelBench miał stałe zadanie, cudzą referencję i bramkę poprawności, której nie mógł zmienić. U nas dostał otwarte „napisz silnik” bez bramki.
- Wniosek: o jakości pracy agenta decyduje bardziej środowisko oceny niż ranking modelu. W duecie Kernel + Gemini bramka `gate/gate.py` (referencja llama.cpp, zmiana tylko za zgodą obu) to dokładnie brakujący element. Powinna powstać przed pierwszą linią kodu, a nie po porażce.
- Zachowanie warte przejęcia do naszych reguł: agent, który sam porównuje przybliżenie z wersją dokładną (62 przełączenia top-k) i rezygnuje z przybliżenia. U nas to bramka top-k przy każdej stratnej dźwigni ([[strata-kva]]: igła przechodziła, a zadania agenta padały 0/10).
- Lekcja kernelowa bez zmian: PDL jako dźwignia małych kerneli na NVIDIA (K-111). Dla porównania: MegaQwen agenta to 7,6% roofline, nasz MMVQ 86% pasma.

## Powiązane
- [[kernelagent]]
- [[tensara]]
- [[pomiar-abba]]
- [[repos-30-przeglad]]
