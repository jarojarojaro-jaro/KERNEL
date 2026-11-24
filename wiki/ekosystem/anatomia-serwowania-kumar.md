---
typ: ekosystem
tags: [ekosystem, serwowanie, vllm, sglang, enigma, host]
aktualizacja: 2026-11-24
zrodlo: ~/KERNEL/product/research/66e-anatomia-serwowania-tqllm.md:16-26,61-94; hiraditya.github.io, „Anatomy of an LLM Serving Engine” (część 1, 2026-10-28/11-01; vLLM 0.32.0 `5df63a7`, SGLang 0.5.22 `baa9bef`) i „A Request's Life in vLLM V1” (część 2, 2026-11-02)
status: aktualne
---
# Anatomia silnika serwującego (Kumar): 5 warstw vLLM i SGLang na tle llama-server i Enigmy

**Seria dzieli serwer na 5 warstw (L1 HTTP/szablon/tokenizacja, L2 harmonogram, L3 KV, L4 wykonanie, L5 klaster) i pokazuje, gdzie vLLM i SGLang tną je na procesy; u nas llama-server ma L1–L4 w jednym procesie, więc IPC na krok = 0, ale Enigma dokłada proces proxy Bun, a sam pomiar opóźnień według warstw jest u nas niemożliwy, bo nie zbieramy metryk.**

## Fakty z serii (66e:16-26)
- vLLM przy TP=1: 2 procesy (API server + EngineCore), hop ZMQ + msgpack; przy TP≥2 `SchedulerOutput` co krok przez pamięć współdzieloną. SGLang: scheduler, KV i executor w jednym procesie na GPU, detokenizer osobno, `event_loop_overlap` liczy wynik kroku N−1 na CPU w czasie kroku N.
- vLLM wykrywa stop-string dopiero w API serverze, więc rdzeń może puścić jeden krok za dużo.
- **Metoda pomiaru bez łatek:** różnice `_sum`/`_count` histogramów Prometheus między dwoma scrape'ami przy jednym żądaniu w locie dzielą czas klienta na rdzeń, front + IPC i HTTP + detokenizację (`split_latency.py`).
- **Część 2:** pythonowy API server vLLM ma sufit ~37 000 strumieniowanych tokenów/s, czyli **27 µs CPU na token**; front w Ruście ~12 µs. Zmierzone z mock-engine vLLM (prefill natychmiast, losowe tokeny), bez GPU.
- Autor nie uruchamiał nic na GPU; jedyna liczba wydajności w części 1 to cudzy profil vLLM 0.6.0 (HTTP 33%, harmonogram 29%, GPU 38%).

## Porównanie warstwa po warstwie (66e:63-75)
| warstwa | vLLM / SGLang | topka (llama-server) | Enigma |
|---|---|---|---|
| L1 | osobny proces, IPC co żądanie | wątki HTTP; parser czatu PEG O(n²): 0,07 → 0,52 ms/token przy 1k → 12,8k (R39c) | **dodatkowy proces Bun** (`app/engine/src/server/api.ts:104-124`), strumień przepuszczany; koszt na chunk niezmierzony |
| L2–L4 | EngineCore / proces schedulera | jeden wątek `server_context`, IPC na krok = 0; GPU stoi 410 µs/krok (R37) | jak topka, ale upstream bez naszych łatek L1 |
| L5 | llm-d, Model Gateway | brak (jeden użytkownik) | brak |
| metryki | Prometheus w każdej warstwie | brak `--metrics` w `qwen-opt/run-topka.sh` z repo (keepera na serwerze nie sprawdzałem) | brak `--metrics` w `engine.ts` i `data/engines.json` |

## Czego uczy nas
1. **Nasz parser przy długiej odpowiedzi kosztuje ~20× więcej CPU na token niż cały pythonowy front vLLM** (520 vs 27 µs przy 12,8k). Python nie jest problemem; problemem jest O(n²). Poprawka: [[strumien-on-wyrocznia]].
2. **Bez metryk nie da się podzielić opóźnienia na warstwy.** Metoda Kumara działa tylko z histogramami. Pierwszy punkt listy z [[inference-stack]] (`--metrics` + metryki proxy) jest też warunkiem tego pomiaru, także dla TTFT, który dziś liczymy tylko z `prompt_ms` serwera ([[reward-hacking-inferencji]], G5).
3. **Mock-engine jako narzędzie:** sufit frontu zmierzony bez GPU. To ten sam pomysł co symulator silnika do testów Enigmy (punkt 3 w [[inference-stack]]). Mock mierzy jednak tylko front; poprawności silnika nie zastąpi, czego dowodzi Enigma Turbo, która przechodziła testy na syntetycznym modelu ([[enigma-turbo-gemini-2026-11-20]]).
4. **Proxy Bun w Enigmie** to odpowiednik API servera vLLM. Pomiar: ten sam strumień 12k tokenów bezpośrednio z llama-server i przez proxy, zegar klienta, ~10 min.

## Powiązane
- [[strumien-on-wyrocznia]]
- [[maska-kq-host-dlugi-ctx]]
- [[latki-hostowe]]
- [[lekcja-obciazenie-cpu]]
- [[tokenspeed]]
- [[inference-stack]]
