---
typ: model
tags: [modele, agent, katalog, enigma]
aktualizacja: 2026-11-24
zrodlo: ~/KERNEL/product/research/67b-wybor-modeli-nvidia.md:97,112; ~/KERNEL/product/research/watch/2026-11-22.md:57; ~/KERNEL/app/engine/src/server/catalog/score.ts:1-5; https://huggingface.co/Nanbeige/Nanbeige4.3-33B
status: do-sprawdzenia
model: nanbeige4-3-33b
rozmiar: 33B
---
# Nanbeige4.3-33B: gęsty model agentowy, który pokazuje, że Enigma liczy prędkość zamiast czasu zadania

**Gęsty model (Llama, 52 warstwy) z AA v5 20,4 (Qwen3.8-27B 20,1) i Terminal-Bench 4.0 30% wobec 6% Qwena, ale z 44% większą liczbą tokenów na zadanie i KV 58,5 KB/token przy q4_0 (3,2× Qwen); na 24 GB mieści Q4_K_M tylko do 64k (R67b, 2026-11-07).**

- **Liczby (R67b:97):** Apache-2.0; SWE-Pro 60,3 vs 61,7 (karta modelu); 5090: Q4_K_M 184k, IQ4_XS 212k; bez MTP. LocalMaxxing 2026-11-21: R9700, Nanbeige4.3-33B-Base Q5_K_S z ngram-mod 239,4 t/s (niezweryfikowane, jeden przebieg).
- **Lekcja dla katalogu Enigmy:** ocena modelu to jakość × kwant × użyteczność prędkości `sqrt(min(t/s, 60)/60)` (`score.ts:1-5`). Nie ma w niej tokenów na zadanie: model, który mówi o 44% dłużej, kończy zadanie agenta o tyle później przy tych samych t/s. Dla zadań agentowych liczy się czas do wyniku (tokeny na zadanie ÷ t/s) i trafność, nie same t/s.
- **Lekcja dla pamięci:** gęsty model z 8 głowami KV × 52 warstwy zjada kontekst szybciej niż hybryda GDN Qwena; nasz model pamięci w katalogu to uwzględnia, a sam wynik AA tego nie pokazuje.
- **Nie zmierzone u nas:** ani jakość na naszych zadaniach agentowych, ani prędkość na XTX.

## Powiązane
- [[modele-katalogowe]]
- [[qwen3-8-27b]]
- [[enigma-uczciwy-benchmark]]
