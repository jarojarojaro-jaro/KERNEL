# 44. Routing profili spekulacji per żądanie (`LLAMA_SPEC_ROUTE`)

Data: 2026-10-21. Autor: podagent SpecRoute2 (wznowienie SpecRoute). Gałąź lokalna `spec-route` (`~/wt/specroute`, commit `38cfc7654`, baza topka `9056cea22`), instalacja `~/llama-specroute`.
`[INFERENCE]` = wniosek bez pomiaru.

## 0. Status

- Implementacja gotowa i zbudowana. **Bramka md5 i ABBA jeszcze NIE przeszły**: `x44.jobs` czeka w kolejce GPU za innymi plikami (zakolejkowane 00:16, o 01:03 nadal przed nim `g3p.jobs` itd.). Wyniki trafią do `~/qwen-opt/queue/logs/sr-*.log`, `/tmp/x44/`, `~/qwen-opt/xtxlab/logs44/`.
- Do czasu PASS bramki i wygranej ABBA nic nie idzie do IntegTopka2. Domyślnie przełącznik jest wyłączony (`LLAMA_SPEC_ROUTE` nieustawione = zachowanie produkcyjne).

## 1. Co robi

Po stronie CPU, raz na żądanie (`server_spec_route_classify`, log `spec route: profile …, depth …, classified in N us`), wybierana jest głębokość draftu MTP. Próbkowanie nie jest ruszane, więc wyjście pozostaje wyjściem modelu. Lookup (ogon kontekstowy) nie jest ograniczany głębokością.

| profil | warunek (auto) | głębokość MTP | źródło |
|---|---|---|---|
| edit | `tools` w żądaniu albo ≥512 B w blokach ``` w ostatnich 32 KiB promptu | 4 (+ lookup W16) | 35 E1 mvs |
| reason / code | T ≤ 0 | 5 | 35 E1 (+6.8% reasoning-v1) |
| chat | T > 0, thinking on | 4 | 35 E1 |
| prose | T > 0, thinking off | 3 | 40 §3.3 (+4.3%: 82.4 vs 79.0 t/s) |

- Thinking bierzemy wyłącznie z żądania (`chat_template_kwargs.enable_thinking` / sterowanie reasoningiem → `inputs.enable_thinking`, przekazywane jako `speculative.thinking`). Nie zgadujemy go z tekstu.
- Ręczne nadpisanie: pole żądania `"speculative.profile": auto|reason|code|chat|prose|edit`. Inna wartość daje błąd 400.
- Serwer musi wystartować z `--spec-draft-n-max 5` (`DRAFT_N=5`). Profil może głębokość tylko obniżyć: `min(depth, n_max)`.
- Zmiany: `common/speculative.{h,cpp}` (`draft_params.depth`, `n_draft()` w drafterze MTP), `tools/server/server-{common,context}.cpp`, `server-task.h`.

## 2. Bramki (`~/qwen-opt/xtxlab/sr_gate.sh`, `sr_arm.sh`, `~/qwen-opt/queue/x44.jobs`)

- md5 (T=0, 2 prompty, 400 tok, PM4 WA=2 + GUARD): off plain = c4708318, off n=4 = 6f14e814, on auto (reason n=5) = d71a2c04 (referencja n=5), on chat / edit = 6f14e814, on prose = off n=3. PASS tworzy `/tmp/x44/GATE_PASS`. Bez tego pliku ramiona ABBA nie wystartują.
- ABBA off|on|on|off na produkcyjnej konfiguracji topki (`run-topka.sh`). Mieszany workload: reason_bench (T=0, thinking), spec_sweep T=1 thinking on (chat), spec_sweep T=1 thinking off (prose), copy_bench mvs (edit).
- Wynik: **oczekuje na kolejkę**.

## 3. Zalecenia próbkowania z karty modelu (Qwen3.8-27B, README HF)

- Thinking: `temperature=1.0`, `top_p=0.95`, `top_k=20`, `min_p=0.0`, `presence_penalty=0.0`, `repetition_penalty=1.0`.
- Instruct / bez thinking: `temperature=0.7`, `top_p=0.80`, `top_k=20`, `min_p=0.0`, `presence_penalty=1.5`, `repetition_penalty=1.0`.
- `presence_penalty` można ustawiać w zakresie 0–2 przeciw zapętleniom. Wyższe wartości mogą mieszać języki.
- Benchmarki agentowe (SWE-bench Pro, DeepSWE) w karcie liczone przy T=1.0, top_p=0.95.
- Konsekwencja dla routingu `[INFERENCE]`: domyślny klient bez thinking ma T=0.7, nie 1.0. Wygrana n=3 z 40 §3.3 była mierzona przy T=1, więc przy T=0.7 z top_p=0.8 akceptacja powinna być wyższa i n=3 może mieć mniejszą przewagę. Warto to sprawdzić osobnym ramieniem przed uznaniem progu `T > 0 → prose` za ostateczny.
