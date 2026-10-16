---
typ: latka
tags: [latki, upstream, llama-cpp]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:437-444,472; ~/KERNEL/product/PLAN.md:45-46,164-166
status: aktualne
---
# Kandydaci do upstreamu llama.cpp

**Ogólne łatki (sampler, host, clamp, cache q8_1) warto oddać do upstreamu, bo każda łatka tam to jedna mniej do rebase'owania; wyróżnikiem produktu zostają przepisy per (GPU, model).**

Lista z raportu 07 §3.1:
- sampler: 0031, 0048, 0066–0069;
- host pętli spekulacji: 0047;
- clamp q8_1: 0023;
- asynchroniczne i zbiorcze wejścia: 0029, 0059;
- cache i producenci q8_1: 0003, 0015.

Ograniczenia z PLAN:
- llama.cpp zakazuje automatycznych PR i opisów PR pisanych przez AI, więc upstream tylko ręcznie, przez człowieka;
- upstream zmienia się szybko (143 commity w 6 dni, 33 z naszych 69 plików zmienione) i od teraz wydaje wersje semver (v0.7.0), dlatego silnik ma być cienką nakładką na tagach semver z rebase raz na wydanie;
- budżet łatek: łatka, która przez N wydań nie weszła do upstreamu i nigdzie nie daje ≥3%, jest usuwana (pomiar przez [[loo]]).

Ryzyko dryfu: 70 łatek siedzi na jednym commicie z 2026-10-09, konflikty skupiają się w `mmvq.cu`, `ggml-cuda.cu` i `llama-memory-recurrent`.

## Powiązane
- [[latki/_hub|Łatki]]
- [[seria-amd-opt]]
- [[sampler-fast-path]]
- llama-cpp-upstream
- amd-opt-v070
