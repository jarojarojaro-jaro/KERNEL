---
typ: metoda
tags: [metody, jakosc, benchmark, gsm8k, mmlu-pro, bfcl, poprawnosc]
aktualizacja: 2026-11-09
zrodlo: ~/KERNEL/qwen-opt/jakosc-mini/{run.py,code_eval.py,bfcl_ast_checker.py,local.sh,fetch-data.sh}; ~/KERNEL/qwen-opt/jakosc-mini/subsets/s20261109/manifest.json
status: aktualne
---
# jakość-mini: 290 pytań jakości dla dowolnego modelu za llama-server

**Stały zestaw 290 pytań (5 kategorii) przez `/v1/chat/completions` z szablonem serwera, T=0, ścisłe parsery, trafność z 95% CI Wilsona, tokeny i czas na odpowiedź.**

| kategoria | n | źródło (rewizja HF) | ocena |
|---|---|---|---|
| GSM8K | 50 | openai/gsm8k test `740312ad` | ostatnie `Answer: <liczba>`, potem `\boxed{}` |
| MMLU-Pro | 140 = 10 × 14 dziedzin | TIGER-Lab/MMLU-Pro test `b189ec76` | `answer is (X)` (regex oficjalny), potem `Answer: X`, `\boxed{X}`; bez losowania litery |
| PL | 50 | CohereLabs/Global-MMLU `pl` test `0e619dbe` | `Odpowiedź: X` |
| HumanEval+ | 30 | evalplus 0.3.1, HumanEvalPlus v0.1.10 | `sanitize` + testy base i plus w piaskownicy z [[evalplus-jakosc-kodu]] |
| BFCL v3 | 8 simple + 6 multiple + 6 parallel | gorilla-llm/BFCL `61fc0608` | tylko `tool_calls`; checker AST BFCL (gorilla `6ea57973`, skopiowany) |

- **PL:** Global-MMLU ma konfigurację `pl` (14 042 pytań MMLU, tłumaczenie maszynowe z poprawkami społeczności; `pl` nie ma w ludzkim Global-MMLU-Lite), więc zadania SpeakLeash nie były potrzebne.
- **Podzbiory:** `run.py subsets --seed 20261109`, `random.Random("<seed>:<kategoria>")`, zamrożone w `subsets/s20261109/` z sha256 (gen odmawia przy zmianie), prompty zapisane w podzbiorze. Parsery czytają tylko `content`, nigdy myślenia; brak dopasowania = błąd.
- **Narzędzia BFCL** jak `convert_to_tool` dla modeli OSS (`.` → `_`, typy OpenAPI, dopisek „Python 3 syntax”).

## Uruchomienie
- Nasz GPU (kolejka): `./local.sh --profile uncensored --port 8098 --effort low --label qwen-unc all` (gen + restore :8080 → piaskownica → raport); zmienne `run-llm.sh` (CTX, KV, ROCM_DIR…) przechodzą.
- Inny host (np. Vast): `python run.py gen --base-url http://HOST:PORT --model-label X --effort low`, potem `run.py code-eval RUN [--no-scope]` i `run.py report RUN` (venv z evalplus + pandas).
- Wynik: `runs/<label>-<effort>-s<seed>/summary.{md,json}`, `answers.jsonl` (z myśleniem), `scored.jsonl`, `<kategoria>.stats.jsonl` (timings llama-server; prędkość: `/usr/bin/python3 ~/qwen-opt/speed_real.py RUN --md RUN/speed.md`).
- `--reuse-humaneval DIR` bierze HumanEval+ z biegu EvalPlus tego samego serwera (sprawdza `model_path`, szablon, n_ctx i prompt każdego zadania), brakujące generuje.

Pierwszy pomiar: [[2026-11-09-jakosc-mini-qwen-unc]].

## Ograniczenia
- Małe n (Wilson przy 80% trafności): n=50 → 67.0–88.8%, n=20 → 58.4–91.9%, dziedzina MMLU-Pro n=10 → 49.0–94.3%, całość n=290 → 75.0–84.2%. Wyniki per dziedzina są orientacyjne; różnice kategorii < ~10 pp między modelami są w szumie.
- Zero-shot zamiast 5-shot MMLU-Pro; GSM8K bez few-shot. Porównywalne tylko w obrębie jakość-mini.
- Checker parallel BFCL dopasowuje zachłannie (jak upstream): przy niejednoznacznym `possible_answer` kolejność wywołań może dać fałszywy błąd.

## Powiązane
- [[metody/_hub|Metody]]
- [[evalplus-jakosc-kodu]]: pełne HumanEval+/MBPP+
- [[bramka-kld-kanarki]]
- [[modele/qwen3-8-27b-uncensored|Qwen3.8-27B-Uncensored]]
- [[2026-11-09-decyzje-runda-69]]
