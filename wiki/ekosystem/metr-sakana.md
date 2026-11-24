---
typ: ekosystem
tags: [ekosystem, agenci, nauka]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/02-autotuning-i-agenci-kerneli.md:31-35,191-192; ~/KERNEL/product/research/01-konkurencja.md:290,373; ~/KERNEL/product/research/15f-agentowa-nauka.md:15-27
status: aktualne
---
# METR i Sakana (agenci kerneli)

**Dwa punkty odniesienia dla agentów piszących kernele: METR (1.81× średnio, ~$20/zadanie) i Sakana AI CUDA Engineer (wycofane „10–100×”, 3.13× → 1.49× po usunięciu reward hackingu).**

METR (2025-02): 1.81× (o3-mini-high), best-of-all 2.01×, >5% na 93% zadań, ~$20–35 na zadanie na model. Sakana: exploit pamięci omijał sprawdzanie poprawności. Lekcja dla nas: referencja i pomiar poza zasięgiem agenta, bramka wyników i pomiaru, agenci tylko w labie.

Nowsze: Sakana AI-Scientist-v3 (raport 15f) – izolacja ewaluacji w kodzie, ale brak statystyki i niewykryta zmiana protokołu przez agenta; zob. [[sakana-agentic-scientist]].

## Przegląd 2026-11-24 (nauka, nie tylko prędkość)

- Teza „agenci działają tylko z mocną bramką” sprawdziła się u nas na własnej skórze: Enigma Turbo od Gemini (20.11) przeszedł własne testy „ALL PASS” na syntetycznym modelu 256 × 4 warstwy, a na prawdziwym Qwen3.5-0.8B odpowiadał bełkotem w 0.7 t/s ([[enigma-turbo-gemini-2026-11-20]]). To dokładnie wzór Sakany: agent ocenia się na własnych założeniach.
- Kontrprzykład z tego samego miesiąca: [[kekzl-imp]] — cały silnik napisany przez Claude Code, a działa (Qwen3.8-27B 95.5 t/s vs vLLM 70.4 t/s na 5090), bo bramka wydania porównuje z vLLM na prawdziwych wagach (PPL ≤ 0.5%, dekod ≥ +5%), a role agentów mają twarde zakazy (test-writer nie zmienia `src/`, audytor najpierw czyta listę obalonych hipotez).
- „Tylko w labie” trzeba więc rozumieć jako „tylko za bramką, której agent nie może zmienić”, a nie „nigdy w produkcie”.
- Nasz odpowiednik: [[fabryka-v1]] (karta twierdzenia, ledger, G0–G5, 36 reguł) — działa dla łatek w forku, ale nie objęła Turbo, bo Turbo powstał poza fabryką, w rozmowie z Gemini.
- Co bierzemy: każda praca agenta nad silnikiem lub aplikacją (nie tylko łatki kerneli) przechodzi przez bramkę z referencją spoza zasięgu agenta: prawdziwy GGUF, ten sam prompt, porównanie z llama.cpp (md5 T=0, KLD).

## Powiązane
- [[thinking-machines]]
- [[turbollm]]
- [[raport-02-autotuning]]
- [[kernelbench]]
