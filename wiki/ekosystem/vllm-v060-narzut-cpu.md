---
typ: ekosystem
tags: [ekosystem, serwowanie, host, vllm, enigma]
aktualizacja: 2026-11-24
zrodlo: https://vllm.ai/blog/2024-09-05-perf-update (vLLM v0.6.0, 2024-09-05); ~/KERNEL/product/research/66e-anatomia-serwowania-tqllm.md:8-9,19,61-75,186; ~/KERNEL/app/engine/src/server/api.ts:104-124
status: aktualne
---
# vLLM v0.6.0: jak znaleźli 62% czasu na CPU i co z tego wynika dla topki i Enigmy

**Profil vLLM v0.5 (Llama 3 8B, 1×H100) pokazał, że GPU liczy tylko 38% czasu, a serwer HTTP zabiera 33%, a planowanie 29%; trzy zmiany (osobny proces API, planowanie kilku kroków naraz, przetwarzanie wyjścia o krok później) dały ×1,8–2,7 przepustowości bez żadnego nowego kernela.**

## Co zrobili (blog, PR-y)
- **Proces API osobno od silnika** (PR #6883, ZMQ): przy strumieniowaniu 8B robi token co 13 ms, więc front musi wysłać 76 obiektów/s na klienta; w jednym procesie API i silnik walczyły o GIL.
- **Planowanie wielu kroków** (#7000, `--num-scheduler-steps 10`): +28% przepustowości 70B na 4×H100, ale kosztem nierównego strumienia (tokeny przychodzą paczkami) i wyższego TTFT przy małym ruchu — sami to piszą.
- **Wyjście o krok później** (#7049): detokenizacja i stop-stringi kroku n liczone w trakcie kroku n+1; TPOT 70B −8,7%, koszt: czasem jeden krok za dużo.
- Pula obiektów Pythona (+24%), kopie bez blokowania, szybka ścieżka samplera dla prostych żądań.

## Nasz odpowiednik
- **Topka (llama-server):** L1 w wątkach HTTP, L2–L4 w jednym wątku, IPC na krok 0; zmierzona przerwa GPU 410 µs/krok (~1,5% z 27,3 ms) przy krótkim kontekście (66e:8). Nasza wersja „przetwarzania wyjścia” to parser czatu O(n²) w wątku HTTP (0,07 → 0,52 ms/token) — [[strumien-on-wyrocznia]].
- **Enigma:** dokłada proces Bun `/v1/*` → llama-server (`api.ts:104-124`), czyli dokładnie warstwę, którą vLLM wydzielił. Przy jednym kliencie to tanie; nikt nie zmierzył jej przy kilku agentach naraz.

## Czego się uczymy
- Metoda: zanim ruszysz kernele, podziel czas kroku na GPU / planowanie / front. My mamy na to `split_latency.py` z 66e i pomiar przerwy GPU; w Enigmie takiego podziału brak.
- Każde przyspieszenie hosta ma koszt dla użytkownika (paczki tokenów, TTFT). Ocenę robimy na TTFT i płynności strumienia, nie tylko na t/s.
- Dla Enigmy: pomiar narzutu proxy Bun przy 1/4/8 równoległych strumieniach przed dodaniem kolejnych funkcji do proxy `[INFERENCE: dziś niezmierzone]`.

## Powiązane
- [[strumien-on-wyrocznia]]
- [[inference-stack]]
- [[lekcja-obciazenie-cpu]]
- [[raport-66-synteza]]
