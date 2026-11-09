---
typ: model
tags: [modele, myslenie, edycja-wag, lora]
aktualizacja: 2026-11-09
zrodlo: ~/KERNEL/product/research/69c-astra-stop.md:9-40,46-52,58-78,82-98,139-183,207-233; ~/KERNEL/product/research/69c-skrypty/analyze_unc.json; https://huggingface.co/jarrodwatts/Qwen3.8-27B-Astra-Stop; https://github.com/notwitcheer/llm-bench-rig/tree/main/astra-stop
status: do-sprawdzenia
---
# Astra-Stop: rank-1 edycja, która skraca myślenie Qwen3.8-27B

**Jedna macierz `layers.63.mlp.down_proj` zmieniona wzorem `W' = (I + u uᵀ)W` (u = odczyt tokena `</think>` przez głowicę LM, cos 0.9998 na naszym GGUF): mediana myślenia −35.5% przy effort xhigh, ale `</think>` przecieka do odpowiedzi w 11/32 – to zmiana zachowania, nie bezstratna optymalizacja (2026-11-09).**

- **Edycja:** HF `jarrodwatts/Qwen3.8-27B-Astra-Stop` (`27c08370`, 11-04), `u.npy` 20 608 B, α = −1 (wzmocnienie ×2, nie ablacja), zmiana macierzy 1.4%. Znaleziona przez GPT-6 Astra w Codex (~$100 GPU); log odkrycia nieopublikowany. Przesłuch na inne tokeny ≤ 0.27 (głównie zamknięcia `</…`, `</tool_response>`).
- **Liczby:** autor (bf16, pelikan, n=16): mediana 27 346 → 17 156 (−37%); 694 zadania: −3% tokenów, trafność 95.2% = 95.2%. Replikacja witcheer (`f732402`, 5090, Q4_K_M, **bez MTP**, n=32, preregistracja): 26 254 → 16 930 (−35.5%, CI95 −74.5…−10.4%), czas próby −30%, SVG 32/32 → 31/32, matematyka 22/24 = 22/24.
- **Przeciek:** `</think>` w treści 0/32 → 11/32; jedyny zepsuty SVG to ten z `</think>`. Ryzyko dla XML tool calls ([[bezpieczenstwo-tokenow-specjalnych]]).
- **Z Uncensored:** tensor to Q6_K (73 113 600 B); cos(u, kierunek Orki r) = 0.014 – edycje się składają bez interakcji ([[uncensored-ablacja-kierunku]]).
- **Droga LoRA:** adapter rank-1 90 KB gotowy, skala per żądanie = siła edycji (1 = ×2, 0 = wyłączone), koszt ~0.03–0.04% `[SZACUNEK]`. Splice w Q6_K: naiwnie 1.76× zamiast 2×, z error-feedbackiem 2.005×.
- **Status:** przy produkcyjnym `low` niezmierzone; opcje (nic / opt-in LoRA / wpiec / tylko strażnik) i testy T1–T7 w [[raport-69-synteza]].

## Powiązane
- [[modele/_hub|Modele]]
- [[qwen3-8-27b-uncensored]]
- [[swift-1-5]]
- [[uncensored-ablacja-kierunku]]
- [[2026-11-05-tylko-bezstratne]]
- [[raport-69-synteza]]
