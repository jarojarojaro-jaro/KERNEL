---
typ: ekosystem
tags: [ekosystem, agenci, proces]
aktualizacja: 2026-11-24
zrodlo: ~/KERNEL/qwen-opt/research/repos/21-ako4all.md:1-14,196-200; ~/KERNEL/qwen-opt/research/repos/REPOS-PODSUMOWANIE.md:31
status: aktualne
---
# TongmingLAIC/AKO4ALL i AKO4X

**Protokół dla agenta optymalizującego kernele (commit `bbd0e1c`, 2026-09-15), nie kod kerneli; werdykt: średnia (proces).**

Jeden `SKILL.md` (175 linii) dla Claude Code, szablony `HINTS.md`/`ITERATIONS.md`, evaluator w stylu KernelBench; pętla profil → edycja → bench → log → commit. AKO4X dokłada kampanie wielorundowe ze świeżym sub-agentem dziedziczącym archiwum wariantów. Dla nas: test leave-one-out całego stosu 54 łatek (zrobione, zob. LOO), archiwum per rodzina kerneli z pułapkami „Why/WHEN”, rozdział sygnału (szybki pomiar) od werdyktu (spec_sweep z przeplatanym A/B).

## Przegląd 2026-11-24 (nauka, nie tylko prędkość)
Werdykt „średnia: protokół agenta, nie kod” był zły z perspektywy naszej pracy agentów: protokół to dokładnie to, czego nam brakowało.
- **Co dawał 10-16** (`qwen-opt/research/repos/21-ako4all.md:9-14,198-203`): dziennik iteracji `ITERATIONS.md` i archiwum pułapek „Why/WHEN” per rodzina kerneli, świeży podagent na rundę dziedziczący archiwum wariantów, retrospektywa z bramką dowodową dla briefów, LOO całego stosu łatek.
- **Co z tego zrobiliśmy:** tylko LOO ([[loo]]). Dziennik ślepych uliczek z blokadą powtórek i prognozą przed pomiarem bierzemy dopiero 24.11 z TensorFold ([[ashhart-skills-infra]], port `optimization-ledger`): ta sama idea, 5 tygodni później. TideLM `docs/gotchas.md` (134 sekcje) był trzecim przykładem ([[raport-28-moe-offload]]). Nasze [[wyniki-negatywne]] to tekst w NOTES, którego agent nie musi sprawdzić przed startem.
- **Ich słabości też uczą:** bramka dowodowa przyjęła 35 z 35 decyzji, a A/B uruchamia B, potem A, bez przeplotu i bez A/A (`21-ako4all.md:181-188`). Bramka, która nic nie odrzuca, nie jest bramką; to samo co testy Enigma Turbo, które przechodziły przy bełkocie ([[enigma-turbo-gemini-2026-11-20]]).
- **Porównanie z naszym wyścigiem Kernel + Gemini:** zawodnik zaczyna od briefu, a wyniki rund trafiają do STAN-PRAC i wiki jako tekst; archiwum wariantów i pułapek, które nowy zawodnik musi przeczytać, nie ma `[INFERENCE]`.
- Bierzemy: dziennik rund z pułapkami „Why/WHEN” jako obowiązkowe wejście każdego nowego podagenta optymalizacji (razem z dziennikiem z [[ashhart-skills-infra]]), i miarę bramki: ile odrzuciła.

## Powiązane
- [[kernelagent]]
- [[atrex-kernel-agent]]
- [[loo]]
- [[repos-30-przeglad]]
