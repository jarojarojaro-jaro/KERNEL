---
typ: hub
tags: [platformy, hub]
aktualizacja: 2026-11-28
zrodlo: wiki/tools/czesci.py; wiki/tools/wiki.py index
status: aktualne
---
# Platformy: playbooki

**Playbook na dzień, w którym dostajemy sprzęt: build, sufit pasma, kolejność optymalizacji, testy, pułapki.**

Wróć: [[index|Strona główna]]. Lista niżej jest generowana przez `python3 tools/wiki.py index`; nie edytuj jej ręcznie.

<!-- AUTO:START -->
## Notatki (14)

- [[amd-cdna3-gfx942|AMD CDNA3 gfx942 (MI300X): playbook]] — Datacenterowy CDNA3 z wave64 i MFMA; nie jest rynkiem produktu, służy do sanity-checku wspólnego kodu HIP z darmowego kredytu, a u nas wciąż brak pomiaru.
- [[amd-rdna3-gfx1100|AMD RDNA3 gfx1100 (RX 7900 XTX): playbook]] — Nasza karta domowa: ROCm 10.0, jądro 6.8, taśma PM4, fork „topka” i silnik Maya; tu powstała cała kolejność optymalizacji, którą przenosimy na inne Radeony.
- [[amd-rdna4-gfx1201|AMD RDNA4 gfx1201 (RX 9070 XT, Radeon AI PRO R9700): playbook]] — Ten sam Navi48 z 640 GB/s (16 GB w 9070 XT, 32 GB w R9700); u nas brak pomiaru, a nasze kernele WMMA z gfx1100 trzeba tu portować, więc kolejność zaczyna się od logiki hosta i spekulacji.
- [[amd-strix-halo-gfx1151|AMD Strix Halo gfx1151 (Ryzen AI Max): playbook]] — APU RDNA3.5 z pamięcią zunifikowaną do 128 GB i 256 GB/s; kernele gfx11 przechodzą prawie bez zmian, ale pasmo jest prawie 4× niższe niż na XTX, więc spekulacja i MoE ważą tu najwięcej. U nas brak pomiaru.
- [[apple-silicon-mlx-metal|Apple Silicon (M1–M5): Metal w llama.cpp, MLX, oMLX]] — Na Macu dekod ogranicza pasmo pamięci zunifikowanej, ale weryfikacja draftu na M1–M4 jest ograniczona obliczeniami, więc topka to krótki draft (n1–2) aż do M5; własnego pomiaru na Macu nie mamy (stan 2026-11-28).
- [[intel-arc-xe2|Intel Arc B580 i Xe2 (SYCL, Vulkan)]] — Arc B580 (Xe2, 12 GB, 456 GB/s) ma sufit dekodu Qwen3.8-27B z MTP 82 t/s, ale się w nim nie mieści Q4_K_M. Na Intelu llama.cpp zostawia ok. 3,6 × prędkości względem vLLM XPU. Własnego pomiaru nie mamy (stan 2026-11-28).
- [[nvidia-ada-sm89|NVIDIA Ada sm_89 (RTX 4060 Ti, 4070, 4080 SUPER, 4090, L4): playbook topki]] — Na Adzie weryfikacja kilku wierszy jest tańsza niż na Ampere (V(5)/V(1) = 1,26 na 4080 SUPER), więc MTP n4 zostaje; topki: 4090 101,27 t/s przy 262 144 (fork+kvq+lean), 4060 Ti Inkling + DSpark 48,58 / 48,99 t/s przy 283 648 (2026-11-07 / 2026-11-27).
- [[nvidia-ampere-sm86|NVIDIA Ampere sm_86 (RTX 3060, 3070, 3080, 3090): playbook topki]] — Na Ampere topkę robi fork CUDA z MTP n2, `kvq`, lean i lookup W16 (3090: 79,97 t/s przy 262 144, [[final-recipes-nvidia]], 2026-11-07); największy hamulec to droga weryfikacja kilku wierszy (V(5)/V(1) = 1,59 na 3090) i procesor hosta, nie karta.
- [[nvidia-blackwell-sm100|NVIDIA Blackwell sm_100 (B200, GB200): playbook topki]] — Na B200 i GB200 nie mamy własnego pomiaru (brak pomiaru, 2026-11-28); cudze liczby pokazują, że przy batch 1 te karty są daleko od sufitu pasma (Inkling 2 Mini na GB200 3,85 ms/krok przy sufecie ~0,4 ms), więc kolejność to: narzut kerneli i fuzje, potem spekulacja, a pasmo na końcu.
- [[nvidia-blackwell-sm120|NVIDIA Blackwell sm_120 (RTX 5060 Ti, 5070, 5080, 5090): playbook topki]] — Na sm_120 topki to 5090 Qwen3.8-27B fork+kvq+lean 148,57 t/s przy 262 144 (2026-11-07) i 5060 Ti Inkling 2 Mini + DSpark 66,45 / 61,97 t/s przy 262 144 na upstreamie, a z naszym `--ablate-lora` 88,45 / 90,78 t/s (2026-11-28); PDL i FP4 są, ale dekod zysku z nich nie dał.
- [[nvidia-hopper-sm90|NVIDIA Hopper sm_90 (H100, H200): playbook topki]] — Na H100 nie mamy własnego pomiaru (brak pomiaru, 2026-11-28); punkt odniesienia z zewnątrz to Qwen3.8-27B bf16 na vLLM z DSpark k=7: 86,1 tok/s przy c=1 (InferenceX, 2026-10-19), a nasz pierwszy krok to przeniesienie przepisu RTX i pomiar V(n), bo akceptacja i koszt szerokości z H100 nie przenoszą się na inne karty.
- [[procedura-nowy-model-znana-karta|Procedura: nowy model na znanej karcie]] — Kroki od pobrania do wdrożenia, spisane z kampanii Inklinga na XTX (K-133…K-208, 2026-11-21…28). Główną liczbą jest wall czatu z drafterem przy pełnym kontekście.
- [[procedura-znany-model-nowa-karta|Procedura: znany model na nowej karcie]] — Kroki przeniesienia znanej topki na kartę, na której jej jeszcze nie mierzyliśmy. Wzór: K-201, K-204, K-207 i nvq5 (Inkling i Qwen na 5060 Ti / 4060 Ti, 2026-11-27…28). Każdy krok porównujemy z obecnym przepisem na tym samym hoście.
- [[rodzaje-modeli|Rodzaje modeli: kolejność pracy i nasze dowody]] — Każdy rodzaj modelu ma inny składnik, który dominuje w kroku. Pierwsze dźwignie wybieramy po zmierzonym zysku, a główną liczbą jest zawsze czat z pełnym stosem spekulacji.
<!-- AUTO:END -->
