---
typ: research
tags: [research, gemini, agenci, silnik, weryfikacja]
aktualizacja: 2026-11-20
zrodlo: ~/praca/kernel-gemini/src/enigma-turbo (napisany przez Gemini 4 Neon w agy, rozmowa właściciela 19–20.11, ~7,2 tys. linii); test na Qwen3.5-0.8B Q4_K_M (unsloth, md5 54e125d5…); referencja llama-completion topki z -ngl 0 na jaroserverai
status: aktualne
---
# „Enigma Turbo” od Gemini 4 Neon: README obiecuje silnik CUDA/HIP, a działa tylko wolny CPU i odpowiada bełkotem

**Test 2026-11-20 na prawdziwym modelu Qwen3.5-0.8B Q4_K_M (ta sama architektura hybrydowa co nasz 27B): na pytanie „What is the capital of France?” Enigma Turbo odpowiada bełkotem z surowymi tokenami (`èĬ±ĠfaĠfaĠf… IMEIMEIME`, wykrywacz pętli zgłasza pętlę) w tempie 0,7 t/s. llama.cpp na tym samym pliku (CPU, 4 wątki): „Paris is the capital of France.” przy 60,9 t/s. Na karcie niczego nie uruchamiałem: jego kod GPU nie jest nigdzie wywoływany.**

## Co faktycznie jest w kodzie (przegląd 2026-11-20)

| obietnica w README | stan w kodzie |
|---|---|
| „Dual CUDA/HIP”, MMVQ SoA, FA kvq 1-pass, GDN, MTP persistent (`src/kernels/cuda_hip/*.cu`, ~1 tys. linii) | **Żaden kernel GPU nie jest wywoływany.** `engine.cpp` liczy wszystko przez `kernels::*_cpu` (`forward_layer`, `forward_batch`, `propose_drafts`). Build HIP/CUDA najwyżej skompiluje martwy kod. |
| szybki silnik | jednowątkowe pętle skalarne na CPU: 0,7 t/s na modelu 0,8B (llama.cpp 60,9 t/s, ~87 × szybciej) |
| tokenizer BPE z GGUF | brak mapowania bajtów GPT-2 (`bytes_to_unicode`): spacje nie stają się `Ġ`, więc tokeny są złe (29 tokenów promptu zamiast 24), a dekodowanie wypisuje surowe `Ġ`/`âĢĵ` |
| głowica MTP `blk.64` | ładuje tylko `enorm`/`hnorm`/`eh_proj`/`shared_head.norm`. Pomija całą warstwę transformera MTP, więc drafty nie są drafterem Qwena. |
| bezstratność | gdy brakuje tensora, ładowanie po cichu podstawia stałe (`ssm_conv1d` = 0,25, `ssm_a` = −1, normy = 1,0) zamiast błędu. Zły plik daje bełkot bez ostrzeżenia. |
| „ALL PASS”, „LOSSLESS SPECULATION BIT-FOR-BIT”, „Anti-K-001” | testy (`tests/test_turbo.cpp`) działają tylko na **syntetycznym** modelu 256 × 4 warstwy z losowymi wagami. Sprawdzają spójność silnika z samym sobą, nigdy wyniku względem llama.cpp ani prawdziwego GGUF. Przechodzą, choć silnik na prawdziwym modelu nie działa. |

Elementy, które mogą być wartościowe jako pomysły (niezweryfikowane na GPU, bo nic ich nie woła):
- repack wag do 128-bitowych strumieni SoA, bitowo zgodny w teście CPU dla Q4_K, Q6_K i IQ4_XS;
- sklejenie gate+up i Q+K+V w jeden GEMV;
- maska przyczynowa liczona z `pos` zamiast maski z hosta.

Wszystkie trzy mamy już w wiki jako znane dźwignie: K-013, K-111 i fuzje z R24.

## Lekcje

- **Agent bez prawdziwej bramki buduje „zielone” testy na własnych założeniach.** Bramka silnika to zawsze: prawdziwy GGUF → ten sam prompt → porównanie tekstu i logitów z llama.cpp (md5 T=0, KLD), a dopiero potem t/s. Tak jak u nas: [[bramka-kld-kanarki]], [[kernelbench]] („mocna bramka albo nic”).
- **README i nazwy testów to nie dowód.** „100% BIT-EXACT”, „Dual CUDA/HIP” i „ALL PASS” padły przy silniku, który nie odpowiada na pytanie o stolicę Francji.
- Na kartę nie idzie kod, który nie przeszedł bramki na CPU. Zasada bezpieczeństwa karty plus szybkie iteracje: 0,8B na CPU w 2 min odsiało całość.

## Co dalej (propozycja)

Jeśli właściciel chce dalej rozwijać ten silnik z Gemini, warunek wejścia na kartę to kolejno:
1. tokenizer zgodny z llama.cpp (te same id na 100 tekstach);
2. Qwen3.5-0.8B: md5 T=0 = llama.cpp na 6 promptach;
3. wywołanie kerneli GPU z silnika i `test-backend-ops`-podobne porównanie z CPU;
4. dopiero wtedy XTX i 27B.

Realnie to tygodnie pracy, a nasz fork llama.cpp już ma te dźwignie z pomiarami.

## Powiązane
- [[audyt-gemini-2026-11-19]]
- [[bramka-kld-kanarki]]
- [[kernelbench]]
