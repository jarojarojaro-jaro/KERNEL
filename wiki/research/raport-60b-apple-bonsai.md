---
typ: research
tags: [research, spekulacja, gdn, apple, konkurs]
aktualizacja: 2026-10-24
zrodlo: ~/KERNEL/product/research/60b-apple-engines-bonsai.md:TL;DR,6,7
status: aktualne
---
# Raport 60b: oMLX, Locals, konkurs Bonsai 2 9B, Flapping Airplanes

**Konkurs Bonsai 2 9B (llama.cpp CUDA, weryfikacja DFlash 16 wierszy) potwierdza naszą ścieżkę – leniwe cofanie GDN, fuzje, 4-bitowy draft już mamy; nowe i tanie: sito głowicy draftu, L2 evict_first na 3090, taśma delt GDN, audyt sufitu wzorca (każde ≤ +2%) (2026-10-24, tylko CPU).**

- oMLX: Lightning MTP = MTP głębokości k z adaptacją z pomiaru; CED = Causal Encoder-Decoder DeepSeek V4.1; nie dotyczy Qwen3.8-27B.
- Locals: przełom złożoności dotyczy gramatyki, nie DeltaNet; kernel GDN w jednym launchu (+1.9%) już mamy.
- Drzewo 15 węzłów w W16: 122 → 113 rund; dla nas tylko na ścieżce DFlash2, która po polsku przegrywa z MTP.
- Flapping Airplanes: megakernele, $1B seria A; blog CUDA: wstęp dla początkujących.
- 6 pomysłów w `product/DO-PRZETESTOWANIA.md`.

## Powiązane
- [[research/_hub|research]]
- [[bonsai-fast-contest]]
- [[omlx]]
- [[locals]]
- [[flapping-airplanes]]
- [[gdn-replay]]
