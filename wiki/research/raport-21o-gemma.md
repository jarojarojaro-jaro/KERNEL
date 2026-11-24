---
typ: research
tags: [research, spekulacja, mtp, gemma]
aktualizacja: 2026-10-20
zrodlo: ~/KERNEL/product/research/21o-gemma-ai.md:6-9,18,65-96; ~/KERNEL/product/research/26-kolejka-gpu-wieczor.md:12
status: aktualne
---
# Raport 21o: techniki Gemma 4 (gemma.ai) a nasz MTP

**Klastrowa głowica Gemmy nie zastąpi słownika 64k (−4…−11% trafień d1); hybryda 64k + klastrowy ogon OOV dała offline +0.92% tok/krok, a na GPU −1.5% t/s – odrzucona (2026-10-19, kolejka 26).**

- Wierna Gemmie głowica (2048 klastrów, top-32, ~5.9k wierszy) traci 4–11% trafień d1 (`21o:6,18`).
- Hybryda (commit `cfc463dc1`, `LLAMA_MTP_TAIL`): offline k=8 +0.92% tok/krok przy ~1 GB VRAM, wersje tanie +0.33…+0.41% (`21o:65-76`).
- Pomiar GPU (kolejka wieczorna): 111.0/110.9 → 109.4/109.2 t/s, −1.5% → odrzucone (`26:12`, [[raport-26-kolejka-gpu]]).
- Nasz MTP nie współdzieli KV z celem; zysk z przeuczenia mały (`21o:8`).
- Produkt: Qwen3.8-27B zostaje flagowcem 24 GB, Gemma 4 dla 8/12 GB; K=V w globalnych warstwach Gemmy da −50% KV globalnego (`21o:9`).

## Przegląd 2026-11-24 (nauka, nie tylko prędkość)

- Werdykt w rejestrze mówił tylko o klastrowej głowicy. Raport ma więcej dla produktu i serwowania (`product/research/21o-gemma-ai.md:9,15,22-23,49-53`):
- **Katalog:** Gemma 4 weszła do Enigmy w trzech rozmiarach (`app/engine/data/catalog.json:1187,1269,1351`: 31B, 26B-A4B, 12B), zgodnie z planem tierów 8/12/16 GB z raportu.
- **K=V w globalnych warstwach Gemmy 4:** llama.cpp trzyma K i V osobno, choć V = rms_norm(K); trzymanie jednego daje dla 31B przy 64k −2.68 GB i +6.8…11.8% t/s (arytmetyka, `21o:15`). Nikt tego nie zrobił (`rg 'K=V' wiki` = tylko ten raport), a to zysk dla klientów z Gemmą w katalogu, nie dla Qwena na XTX.
- **Serwowanie:** usuwanie myśli z historii (zalecenie Gemmy) unieważnia cache prefiksu od pierwszej przyciętej tury (`21o:23`). To samo dotyczy naszej topki i proxy aplikacji przy pracy agentowej — szablon czatu decyduje o trafieniach cache.
- **Budżet tokenów obrazu** 1120 → 280 to −75% prefillu obrazu (`21o:22`) — domyślna wartość w UX, gdy dodamy wizję.
- **Dokumentacja:** gemma.ai ma osobną stronę na każde środowisko (llama.cpp, vLLM, Ollama, MLX…) i wizualne przewodniki po MTP — wzór dla pomocy Enigmy.
- Co bierzemy: K=V jako kandydat silnikowy dla Gemmy w katalogu; test trafień cache przy szablonach z przycinaniem myśli.

## Powiązane
- [[research/_hub|research]]
- [[raporty-2026-10-19-20]]
- [[2026-10-19-tokeny-spoza-slownika-draftu]]
- [[raport-24b-draft-pelny-slownik]]
- [[glowica-mtp]]
- [[raport-26-kolejka-gpu]]
