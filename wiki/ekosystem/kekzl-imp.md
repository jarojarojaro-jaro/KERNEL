---
typ: ekosystem
tags: [ekosystem, silnik, nvidia, agenci, produkt, metodologia]
aktualizacja: 2026-11-24
zrodlo: https://github.com/kekzl/imp (README z komentarzami PROV, commit ed4422b7, 2026-10-31); https://github.com/kekzl/imp/blob/main/docs/GOAL.md; https://github.com/kekzl/imp/blob/main/AGENTS.md; ~/KERNEL/product/research/21b-gpu-perf-zasoby.md:82,117-118,147,334; ~/KERNEL/wiki/research/enigma-turbo-gemini-2026-11-20.md; ~/KERNEL/wiki/REKORDY.md:189,194
status: aktualne
---
# kekzl/imp: własny silnik jednej osoby, napisany w całości przez agenta, który działa — przeciwieństwo naszego Enigma Turbo

**imp to silnik C++/CUDA tylko dla jednej generacji kart (Blackwell `sm_120`), z serwerem OpenAI/Anthropic, czatem w przeglądarce i instalacją jednym `docker run`; każdą linię napisał Claude Code, a mimo to na RTX 5090 Qwen3.8-27B NVFP4 robi 95.5 t/s dla jednego użytkownika wobec 70.4 t/s vLLM 0.31.0 (bez spekulacji, ten sam plik, README, PROV `ed4422b7`). Różnica wobec naszej porażki z Enigma Turbo to nie talent, tylko bramki.**

## Jak to jest zbudowane (z repo)
- **Wąski cel:** jedna karta, jedna architektura, batch 1 jako „fundament nie do negocjacji”; jawna lista „czym imp nie jest” (multi-GPU, CPU, AMD, centrum danych) w `docs/GOAL.md`.
- **Bramka wydania (`check-release.sh`):** PPL w granicy 0.5% od vLLM na tym samym checkpoincie; dekod bez spekulacji ≥ 5% szybszy od vLLM na każdym modelu z listy „hero”, z każdego świeżego kontenera; zero synchronizacji hosta na gorącej ścieżce dekodu (pilnuje CI); zestawy zgodności API OpenAI i Anthropic; testy powierzchni agentowej (tool calls, JSON schema, kanał rozumowania, cache prefiksu, anulowanie).
- **Pochodzenie każdej liczby:** w README przy każdym wyniku jest komentarz `PROV` z commitem, datą, kartą, modelem, kwantem, komendą, liczbą powtórzeń i md5 harnessu.
- **Role agentów (`AGENTS.md`):** audytor tylko czyta i najpierw czyta `docs/audit/SETTLED.md` (lista już obalonych hipotez, bo 8 z 13 hipotez jednego audytu powtarzało rzeczy zamknięte); kernel-optimizer może ruszać tylko `src/compute`, musi zrobić A/B w tej samej sesji (≥ 3 próby); test-writer musi mieć niezależną wyrocznię i nie może zmieniać `src/`, żeby test przeszedł; benchmark-runner nie porównuje wyników z różnych dni.
- **Uczciwość:** „Not always ahead” w README (vLLM szybszy o 4.2% przy 32 użytkownikach z długimi promptami), `LIMITATIONS.md`, zaparkowana spekulacja z opisanym powodem (stan GDN przy weryfikacji).
- **Produkt:** obraz Docker, wbudowany czat, endpoint dla Claude Code/Codex, wybór modelu po karcie, model większy niż VRAM (eksperci w RAM, Flash-Next 91.8 t/s na 32 GB).

## Porównanie z naszymi odpowiednikami
| warstwa | imp | my |
|---|---|---|
| własny silnik | działa, bramka = vLLM + PPL na prawdziwych wagach | Enigma Turbo (Gemini, 20.11): testy tylko na syntetycznym modelu, na prawdziwym 0.8B bełkot i 0.7 t/s ([[enigma-turbo-gemini-2026-11-20]]) |
| silnik produkcyjny | własny | fork llama.cpp: 5090 UD-Q6_K 62.49 t/s bez MTP, 148.57 t/s z MTP n4 (`REKORDY.md:189,194`); inne kwanty (Q6_K ok. 6.6 bpw vs NVFP4 ok. 4.5 bpw), więc to nie jest pojedynek 1:1 |
| zakres sprzętu | tylko `sm_120` | XTX, 3090, 4090, 5090, 16 GB NVIDIA, APU — szerzej, więc każdy zysk kosztuje więcej |
| pochodzenie liczb | `PROV` przy każdej liczbie w README | REKORDY i ledger fabryki, ale nie w materiałach produktu |
| pamięć o obalonych hipotezach | `SETTLED.md`, obowiązkowa lektura audytora | [[ZRODLA]], [[wyniki-negatywne]], `kb search` — podobnie, ale bez przymusu w roli |

## Co bierzemy
1. Przy każdym własnym silniku (Turbo i następne) wejście na kartę tylko przez bramkę „prawdziwe wagi → ten sam prompt → porównanie z referencją” — dokładnie to, czego zabrakło w Turbo.
2. Komentarz pochodzenia (commit, karta, komenda, n) przy każdej liczbie na landingu i w README aplikacji.
3. Jawna lista „czego nie robimy” w CONTRACT Enigmy; imp wygrywa, bo robi jedną kartę.
4. Rola audytora z obowiązkiem przeczytania listy obalonych rzeczy przed hipotezami.
5. Z 21b nadal aktualne: lista „co nie ruszyło dekodu” (FP8 scores, warp specialization, TMA dla KV, `21b:117-118,147`) — cp.async jest już blisko szczytu pasma.

## Powiązane
- [[enigma-turbo-gemini-2026-11-20]]
- [[physics-floor-check]]
- [[metr-sakana]]
- [[inference-stack]]
- [[lekcja-uczymy-sie-nie-tylko-predkosc]]
