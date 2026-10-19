---
typ: metoda
tags: [metody, fabryka, agenci, rsi]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/21h-rsi.md:364-482; ~/KERNEL/product/research/21i-rsi-inference-bench.md:231-274; ~/KERNEL/product/research/21j-flameox.md:255-269
status: do-sprawdzenia
---
# Pętla RSI-F: samodoskonalenie fabryki bez trenowania wag (projekt)

**Przeniesienie RSI na naszą pracę nad silnikiem: tylko werdykt `CONFIRMED` z fabryki staje się materiałem; świeży Rewriter pisze z niego playbook, Recenzent sprawdza przeciek, a do `skills/` trafia tylko playbook, z którym świeży Replayer powtórzył zysk na innym celu (raport 21h, 2026-10-19).**

- Role ponad [[fabryka-v1]]: Proponent (hipotezy z budżetem µs), Rewriter, Recenzent przecieku (0 8-gramów z diffu, jak R36), Replayer; krytyk = kalibracja przewidywań i reguły, dziedziczone między cyklami.
- Artefakty: `factory/queue.jsonl`, `factory/skills/<id>.md` (`source_ledger`, `status` reproduced/transferred, `expires`), `factory/trajectories/*.jsonl.zst`.
- Metryki meta z ramieniem kontrolnym bez `skills/`: `CONFIRMED` na godzinę GPU, minuty GPU na `CONFIRMED`, odsetek `INVALID` z winy agenta, |zmierzone / przewidziane|, odsetek playbooków `transferred`.
- Bramki bezpieczeństwa H0–H11 (kodem, nie promptem): agenci nie dotykają GPU poza `factory verify`; `gpu-guard`; PM4=0; kwarantanna sha256 builda po pierwszym faultcie; `journalctl -k` ze wszystkich bootów; ≤ 60 min GPU/dobę i ≤ 15 h/30 dni; zakaz zmian zegarów, napięć i limitów mocy; :8080 nietknięty.
- Przepustowość: 16–60 werdyktów/miesiąc – pętla podnosi tylko trafność, nie znajdzie mnożników strukturalnych (MTP, lookup).

Pilot: [[2026-10-19-plan-retro-rsr-0070]] (P0 + P1, decyzja użytkownika w [[otwarte-decyzje-techniczne]]).

Uzupełnienia z RSI-Inference Bench (21i): [[zmiany-fabryki-z-21i]] (VOID, acceptance floor, guards, reward, worktree bez historii) i benchmark regresji [[aob-v1]].

MCP flameoxa łamie H0 (20 narzędzi capture bez trybu tylko-analiza) – nie podłączać; dowody dla Replayera przez `evidence_id` z `factory preserve` ([[raport-21j-flameox]]).

## Powiązane
- [[metody/_hub|Metody]]
- [[fabryka-cli]]
- [[playbook-optymalizacji]]
- [[2026-10-19-bezpieczenstwo-sprzetu]]
