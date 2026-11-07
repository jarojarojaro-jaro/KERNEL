---
typ: metoda
tags: [metody, serwer, host, parser]
aktualizacja: 2026-11-07
zrodlo: ~/KERNEL/product/research/66e-anatomia-serwowania-tqllm.md:61-75,117-123,186; tqLLM `tools/serve/session.hpp:982-1007` (9a9e7e5)
status: do-sprawdzenia
---
# Strumień O(n) z wyrocznią zamiast parsera O(n²)

**Wątek HTTP llama-server robi pełny `common_chat_parse` całego wygenerowanego tekstu dla każdego przyjętego tokenu (0.07 → 0.52 ms/token przy 1k → 12.8k tokenów, raport 39c), a przy MTP 2–4 razy na krok; tqLLM dokleja bajty raz, ponownie ogląda tylko niestabilny ogon, a stary algorytm zostawia jako wyrocznię testową (raport 66e, 2026-11-07).**

- Wzorzec tqLLM: `StreamWriter::update` (O(n) na odpowiedź) i `update_reference` (stary O(n²)); delty obu muszą być identyczne w testach.
- Punkt odniesienia: front vLLM w Pythonie ~27 µs CPU/token, w Ruście ~12 µs (Kumar, część 2).
- Pomysł dla topki: (a) jeden wynik częściowy na krok MTP zamiast na token, 0.5 d; (b) parser przyrostowy z wyrocznią, 2–3 d.
- Zysk: CPU wątku HTTP −50…75% od razu; dekod 0…+1% przy długich wyjściach przez mniejszą konkurencję o CPU `[INFERENCE]`.
- Bezstratne: te same tokeny, zmienia się tylko podział strumienia na delty; tekst końcowy i tool calle sprawdza test różnicowy.
- Bramka: 10 min GPU, `stream:true` vs `false`, 12k tokenów wyjścia, ms/krok na ostatnich 2k.
- Kontekst: llama-server ma L1–L4 w jednym procesie, więc IPC na krok = 0, a stop-stringi łapie w pętli głównej bez dodatkowego kroku.

## Powiązane
- [[metody/_hub|metody]]
- [[raport-39c-deepseek-deploy]]
- [[lekcja-obciazenie-cpu]]
- [[latki-hostowe]]
- [[tqllm]]
- [[raport-66-synteza]]
