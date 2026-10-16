---
typ: repo
tags: [repo, agenci, nauka]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/15f-agentowa-nauka.md:15-27,65-81,99-122
status: aktualne
---
# Sakana AI-Scientist-v3 (Agentic Scientist)

**Orkiestracja agentów do badań, w której kod wymusza izolację ewaluacji (harness, hashe, osobne kontenery), a naukę rozstrzyga LLM; brak jakiejkolwiek statystyki istotności.**

Repo `SakanaAI/AI-Scientist-v3` @ `2b8aa39` (2026-10-14, jedyny commit), paper arXiv 2610.18933.
- Wymuszone kodem: ewaluację robi harness po wyjściu agenta; ewaluator `:ro` z hashami; finalna ocena raz (`invocation.json` O_EXCL), kandydat i ewaluator w osobnych kontenerach `--network none`; agent ablacji dostaje tylko diff, zadanie i ewaluator z pustą pamięcią.
- Słabości: statystyka `{n, mean, std, min, max}`, `num_replications` 5, promocja `correct && score > best_before` bez marginesu (`campaign_loop.py:584-605`); walidator twierdzeń sprawdza tylko istnienie id źródła, nie liczby; w trybie bez harnessu można wypromować metryki zapisane przez agenta.
- Porażka z papieru: w 2 z 3 przebiegów Pi agent zmienił protokół ewaluacji (majority vote zamiast pass@1), niewykryte przez bramki.
- Inne: 2 workery osiągają szczyt 1 workera w < połowie czasu, 4 nie pomagają; korelacja recenzenta AI r = 0.44.
Dla nas: kopiować izolację i materializację workspace’u, nie promocję bez CI.

## Powiązane
- [[repo/_hub|repo]]
- [[kernelguard]]
- [[metr-sakana]]
- [[raport-15f-agentowa-nauka]]
- [[fabryka-v1]]
- [[lekcja-agent-zmienia-protokol]]
