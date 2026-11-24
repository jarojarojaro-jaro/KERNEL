---
typ: ekosystem
tags: [ekosystem, kwanty, rocm]
aktualizacja: 2026-11-24
zrodlo: ~/KERNEL/product/research/15e-kwantyzacja-nowa.md:211-214,447,518; ~/KERNEL/product/research/15c-nowe-silniki.md:362
status: do-sprawdzenia
---
# ExLlamaV3 (EXL3)

**Silnik z formatem EXL3 pochodnym od QTIP (trellis), z ROCm in-tree od 2026-10 i obsługą Qwen3.8-27B; w niezależnym teście przy ~140k kontekstu wypadł najlepiej end-to-end.**

- Wersja v1.6.2 (`4c842731`). Qwen3.8-27B 4.0 bpw na gfx1100 ~15 t/s decode (PR #283 `[NIEZWERYFIKOWANE]`).
- Test xenodeve (4070S + 5060 Ti, 9 przebiegów, ~140k kontekstu): EXL3 4.0 bpw ukończył 6/6 zadań kodowych, GSQ IQ3_S-MTP 5/6, NVFP4 3/6; GSQ i NVFP4 psuły tajski przy długim kontekście.
- Kontekst z raportu 15c: na 3090 w LocalMaxxing EXL3 242.1 / 169.6 t/s.
Dla nas: odniesienie jakości przy długim kontekście; silnik Python/NVIDIA-first, nie baza produktu.

## Przegląd 2026-11-24 (nauka, nie tylko prędkość)
Źródło: kwanty Inkling-2-Mini SAGE-REXL3 (vcruz305, 2026-11-21, https://huggingface.co/vcruz305/Inkling-2-Mini-SAGE-REXL3-4.23bpw).
- Werdykt z 23.11 („EXL3 działa tylko na CUDA”) był błędny wobec naszej własnej notatki: ExLlamaV3 ma ROCm w drzewie od 2026-10 (wyżej, raport 15e). Czy działa architektura `inkling2_loop` na ROCm — niesprawdzone.
- 4,23 bpw: 15,03 GB z MTP, top-1 98,33%, KLD 0,0088 względem oryginału (float64, cały słownik); UD-Q4_K_XL GGUF 17,63 GB. Porównanie nie jest jabłka do jabłek (inna referencja), metoda SAGE nieopublikowana.
- **Dla Enigmy (katalog):** karta modelu podaje tabelę „karta → maksymalny kontekst” z bajtami KV na token (Q4: 8704 B/token, +draft 9792) i stałym narzutem. To dokładnie to, co liczy nasz planer pamięci (`app/engine/CONTRACT.md`, `planFor`), ale u nich widzi to użytkownik przed pobraniem. Bierzemy: taką tabelę na stronie modelu w aplikacji.
- Dla kart NVIDIA 16 GB 15 GB EXL3 mieści się z kontekstem, a UD-Q4_K_XL (17,6 GB) nie; Enigma ma dziś tylko silniki llama.cpp, więc tego użytkownika obsługujemy gorszym kwantem (IQ3/IQ4_XS).
- Lekcja do naszej bramki KLD: porównujemy zawsze do tej samej referencji; autor sam przyznał, że jego „+4 pkt top-1” to inna referencja — u nas KLD AtomicChat liczony do BF16, a Unsloth do Q8.

## Powiązane
- [[ik-llama-cpp]]
- [[tqllm]]
- [[raport-15e-kwantyzacja-nowa]]
- [[kwanty-gguf]]
