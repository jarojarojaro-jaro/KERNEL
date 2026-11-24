---
typ: ekosystem
tags: [ekosystem, vllm, kv, rdna3, odrzucone]
aktualizacja: 2026-11-05
zrodlo: ~/KERNEL/product/research/63c-amd-rocm-llamacpp.md:21-23,203-227,359-368; https://github.com/vllm-project/vllm/pull/59774 (vLLM v0.33.0 `4ba787e`, 2026-11-01)
status: aktualne
---
# vLLM `ROCM_OCTAVE`: natywny KV 3/4-bit na gfx1100

**vLLM v0.33.0 (PR #59774) ma KV 3-bitowy dla gfx1100 i gfx942: k3v3 = 216 B na slot przy head 256, czyli 75% naszego q4_0; produkcyjnie na 7900 XTX od 2026-10-02.**

- Mechanizm: losowe znaki + Walsh–Hadamard, kodebook Lloyd-Max N(0,1) na 3 bitach, skala zachowująca normę, `v_perm_b32` jako LUT; QK prefillu na int8 WMMA.
- Na 4× XTX z Qwen3.8-27B: 4.6× więcej tokenów niż fp16, NLL przy 380k +0.00086…0.0015 nata. „Least-squares scale” dawała 2–3× wyższe NLL.
- Dla nas: −1.1 GiB KV przy 262k (droga do 262k na 24 GB).
- **Odrzucone 2026-11-05**: inny kwant KV zmienia wyjście ([[2026-11-05-tylko-bezstratne]]).
- Z tego samego wydania bezstratne: TRITON_ATTN +18% na RDNA3 z 32-bitowego adresowania buforów (PR #60084) → mikroeksperyment buffer loads w [[fattn-kvq]].

## Przegląd 2026-11-24 (nauka, nie tylko prędkość)
Wiersz w [[ZRODLA]] zamknął vLLM 0.33 zdaniem „Octave i FLy stratne”. Dla labu to prawda, ale vLLM to też drugi silnik serwujący na naszej karcie, więc warto patrzeć warstwa po warstwie (63c:203-227, 63d:299-313):
- **Silnik na XTX:** vLLM 0.33 ma ROCm 10.0 domyślnie (#58761), koła ROCm budowane 4–7× szybciej (#63105) i natywny KV 3/4-bit dla gfx1100. Autorzy Octave testowali na 4× XTX z Qwen3.8-27B, czyli na tej samej karcie i modelu co nasza topka. Nasze llama.cpp nie ma tak dużej pojemności KV na 24 GB.
- **Metoda kwantyzacji:** skalę wybrali po końcowej metryce (NLL przy 380k), a nie po błędzie najmniejszych kwadratów. Skala „least-squares” była 2–3× gorsza w NLL. Ta sama lekcja co nasza bramka KLD ([[bramka-kld-kanarki]]): mały błąd rekonstrukcji to jeszcze nie jakość.
- **Produkt:** w vLLM FLy (#53987) i Octave to przełączniki opt-in z opisaną ceną jakości. Enigma może kiedyś pokazać użytkownikowi podobny „tryb szybki” (63d E5: +5…8% t/s przy T=1 `[SZACUNEK]`), ale tylko jako jawny wybór i z bramką jakości PL. W labie dalej obowiązuje [[2026-11-05-tylko-bezstratne]].
- **Porządek w konfiguracji:** flaga `--monokernel` zastąpiła zmienną `VLLM_ROCM_MONO_DECODE`. U nas topkę sterują zmienne środowiska (16 `export LLAMA_*`/`GGML_*` w `qwen-opt/run-topka.sh`). To wzór na czas, gdy przełącznik wchodzi do produktu.

## Powiązane
- [[vllm-monokernel]]
- [[fattn-kvq]]
- [[raport-63-synteza]]
