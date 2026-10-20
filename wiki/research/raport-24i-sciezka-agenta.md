---
typ: research
tags: [research, agent, tokenizacja, serwer]
aktualizacja: 2026-10-20
zrodlo: ~/KERNEL/product/research/24i-sciezka-agenta.md:7-9,17-21,31,41-57,65-68
status: aktualne
---
# Raport 24i: ścieżka agenta – tokenizacja, szablon, graf decode

**Tokenizacja + szablon kosztują 25.5 ms przy 14k i 137.3 ms przy 91k tokenów na turę; przyrostowy cache tokenizacji (`LLAMA_SERVER_TOK_CACHE=1`) daje 0.5–2.5 ms na turę i 0/61 rozbieżności; żadna operacja grafu decode poza matvec/FA/GDN nie przekracza 2% kroku (2026-10-19).**

- Cache tokenizacji: podział na tokenach specjalnych, których nic nie nakrywa; Qwen ma 27 tokenów granicznych (`24i:26-28`). Adopt po smoke-teście serwera.
- Pominięcie renderu szablonu: 62.3 vs 62.9 ms – kill (`24i:35`).
- Graf decode (ślad mtp4): matmul 84.5%, kopie 3.8%, rms_norm 3.0%; stan konwolucji GDN ~1 ms/krok ≈ 0.9% zegara sesji – stop (`24i:41-57`).
- Kontekst: [[ksztalt-ruchu-agentowego]], [[lekcja-agent-prefill-nie-decode]].

## Powiązane
- [[research/_hub|research]]
- [[raporty-2026-10-19-20]]
- [[ksztalt-ruchu-agentowego]]
- [[lekcja-agent-prefill-nie-decode]]
- [[raport-21f-inferencex]]
