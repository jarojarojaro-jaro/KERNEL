---
typ: lekcja
tags: [lekcje, pomiar, kod, xtx]
aktualizacja: 2026-11-19
zrodlo: fork topka ggml/src/ggml-cuda/common.cuh (ggml_cuda_env_switch); ~/KERNEL/qwen-opt/k125/ (run1-invalid na jaroserverai)
status: aktualne
---
# `ggml_cuda_env_switch` jest włączony, gdy zmiennej nie ma: nie używaj go do wyłączników

**K-125, 2026-11-19: dodałem wyłącznik `GGML_HIP_KVQ_OFF` przez `ggml_cuda_env_switch("GGML_HIP_KVQ_OFF")`. Ta funkcja zwraca `true`, gdy zmienna nie jest ustawiona (`env == nullptr || atoi(env) != 0`), bo służy do przełączników domyślnie włączonych. Skutek: kvq było wyłączone w obu ramionach, a porównanie wyszło „IDENTICAL” (KLD 0,004522 = 0,004522, ten sam czas 44,32 s/przebieg).**

- Wynik identyczny co do bitu dla dwóch różnych kerneli (inna numeryka: f16 Q i WMMA zamiast q8_1 i int8) to sygnał błędu w pomiarze, nie dowód bezstratności.
- Reguła: wyłącznik domyślnie wyłączony czyta się jawnie: `getenv(x) != nullptr && atoi(getenv(x)) != 0`.
- Reguła: w każdym A/B ramię musi się czymś mierzalnie różnić (czas, licznik kerneli albo log wyboru ścieżki). Brak różnicy oznacza, że trzeba sprawdzić, czy przełącznik w ogóle zadziałał, zanim zapisze się werdykt.
- Koszt: jeden przebieg kolejki (~6 min karty), wykryty przed zapisem wyniku.

## Powiązane
- [[KOLEJKA-TESTOW]]
- [[lekcja-glebokosc-zmienia-tekst]]
