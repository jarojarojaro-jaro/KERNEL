---
typ: research
tags: [research, telegram, kv-cache, kwantyzacja, llamacpp, upstream, mmq]
aktualizacja: 2026-11-14
zrodlo: https://pearlresearch.ai/research/blog/pearlquant (2026-11-12); https://x.com/WeinsteinOmri/status/2120888055556948106; https://huggingface.co/blog/ggml-org/llama-cpp-v1 (2026-11-13); https://github.com/ggml-org/llama.cpp/releases/tag/v1.0.0 (`b1b770d`, nightly b12359); https://github.com/ggml-org/llama.cpp/pull/31533; https://github.com/ggml-org/llama.cpp/pull/30541
status: aktualne
---
# Telegram 2026-11-14: PearlQuant (KV na kracie E8) i llama.cpp v1.0.0

**PearlQuant to stratna kompresja KV, dla nas odpada. llama.cpp v1.0.0 (b12359) przynosi dwie rzeczy ważne dla nas. Few-row MMQ #31533 przyspiesza weryfikację spekulacji Qwen3.8-27B na NVIDIA o +16,7…34,9% tok/s. Poprawka #30541 (kopia stanu dla skwantowanego KV) może wyjaśniać nasz wyciek przy restore slotu.**

- **PearlQuant.** Kwantyzacja wektorowa KV po 8 wartości (krata E8, losowa rotacja), średnio 3,2 bita na wartość. GLM-5.3 na 8× B200 przy 128 sesjach: p90 TTFT 144 → 7 s, +24% przepustowości. Werdykt: nie dla nas, bo KLD vs FP8 = 0,057, czyli zmienia odpowiedzi ([[2026-11-05-tylko-bezstratne]]). Do tego mamy już 262k na karcie, a zysk bierze się z wielu sesji naraz. Do K-079 w [[KOLEJKA-TESTOW]].
  - Warta skopiowania jest metoda oceny: KLD → benchmarki → cechy tekstu („Wait” na 1000 słów, ślepy sędzia = ten sam model), plus konfiguracje zepsute celowo jako kontrola pozytywna. Dopisane do K-007.
- **llama.cpp v1.0.0.**
  - Wersjonowanie semver (`libllama`/`libggml` 1.0.0, zmiany API tylko przy nowej głównej wersji) i usunięcie 35 przestarzałych funkcji.
  - Kernele i stan istotne dla nas:
    - #31533 few-row MMQ CUDA dla 2–24 kolumn. Z DFlash2 (7 draftów): 3090 Ti 57,6 → 77,7 tok/s, 5090 141,5 → 170,7, 80/80 rozmów szybciej, KLD jak master. Port HIP na RDNA3.5: 21 → 37 tok/s.
    - #30541: kopia stanu „on device” dla KV q4_0/q8_0 kopiowała 1/32 zakresu.
    - #31927, #32078, #32009/#32089, #31838.
  - FP8 KV jest stratne względem naszego q4_0 bit w bit.
  - Działania w kolejce:
    - K-103 (nowa): Enigma NVIDIA na v1.0.0;
    - K-013 w górę: port few-row na XTX; zmienia md5, więc potrzebna bramka K-007;
    - K-001: hipoteza #30541;
    - K-056: rebase na v1.0.0.

## Powiązane
- [[research/_hub|research]]
- [[KOLEJKA-TESTOW]]
- [[final-recipes-nvidia]]
- [[2026-11-08-kvq-once-profil]]
- [[lekcja-md5-wzgledem-upstreamu]]
