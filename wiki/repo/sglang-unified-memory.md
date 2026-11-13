---
typ: repo
tags: [repo, pamiec, serwer, gdn, telegram]
aktualizacja: 2026-11-13
zrodlo: https://www.lmsys.org/blog/2026-11-11-unified-memory/ (2026-11-11, SGLang `daa171846f`); https://x.com/ChengWan17/status/2120690586625990822 (Telegram „gpu”, 2026-11-13)
status: aktualne
---
# SGLang Unified Memory: jedna arena VRAM dla KV, okna SWA i stanu rekurencyjnego

**SGLang (`--enable-unified-memory`, eksperymentalne) zastępuje stały podział VRAM między pule (pełne KV, okno SWA, stan Mamby/GDN) jedną areną z kompaktowaniem i układem „jeden wpis na token” (KV celu i draftu razem). Zysk dotyczy tylko serwowania wielu żądań naraz: na jednej H200 przy 64–1024 współbieżnych żądaniach do +26% przepustowości i 1000 zamiast 618 żądań w locie. Przy domyślnych proporcjach różnica to szum: 5830 vs 5880 tok/s (2026-11-13).**

- **Werdykt dla nas: nie warto.** Topka obsługuje jeden slot: KV 262 144 tokenów i stan GDN rozmiaru stałego od startu. Nie ma tu żadnego suwaka proporcji, który dałoby się źle ustawić, więc nie ma pamięci uwięzionej w niewłaściwej puli. Dla decode i prefill pojedynczego strumienia wpływ jest 0%.
- **Do zapamiętania.** Wpis na token pakuje KV draftu obok KV celu. Ten sam pomysł mógłby kiedyś skrócić zarządzanie KV draftu MTP, ale nie przyspiesza. Jeśli kiedyś wróci temat wielu użytkowników na NVIDIA (K-061 w [[KOLEJKA-TESTOW]]), to odpowiednikiem w llama.cpp jest `-kvu` plus stały `n_seq_max`.
- Poprzednie źródło SGLang: [[sglang-hicache]].

## Powiązane
- [[repo/_hub|repo]]
- [[sglang-hicache]]
- [[KOLEJKA-TESTOW]]
- [[2026-10-19-kv-tylko-w-ram]]
