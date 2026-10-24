---
typ: research
tags: [research, kwanty, moe, konkurencja, rtx-3090]
aktualizacja: 2026-10-24
zrodlo: ~/KERNEL/product/research/60c-quant-and-3090-engines.md:42-66,232-253
status: aktualne
---
# Raport 60c: Gyro-Coder, tqLLM 1.2, DCQ, posty @superalesha, Nemotron-3.5-Bolt-E4B

**Nic z tej partii nie przyspiesza naszego Qwen3.8-27B na XTX (czat 95–104 t/s). Dla nas liczą się trzy tanie rzeczy: z DCQ wrażliwość `attn_qkv` w warstwach GDN (ramię do 57g), z tqLLM bramka `--np N` = `--np 1` oraz próg na pozycję draftu MTP (2026-10-24).**

- [[gyro-coder]]: Flash-Next przycięty do 256 z 512 ekspertów, eksperci w TQ2_T, 19.92 GiB GPU. Działa tylko w forku agentionai (Docker Vulkan). Python KLD 0.165, zadania 13/16. Od 10-24 format Gyro ma otwartą specyfikację (Apache-2.0).
- [[tqllm]] 1.2.x: kod otwarty, tylko CUDA. Flash-Next na 3090 daje 77.1 vs 47.2 t/s (Strata) po 128K, czat 96–103 t/s. Wymaga ≥ 64 GB RAM, więc „32 GB” z posta to nieprawda.
- [[dcq-kotwica-stanu-gdn]]: pomysł dobry, dowody słabe (n=20, JSON przeczy tabeli).
- „4.6×” @superalesha to zadanie cytowania 25K (82 → 382 t/s); czat ~133 t/s ([[hyperqwen]]). Wynik „574 t/s DeepSeek” pochodzi z 4× RTX Pro 6000, a źródło mówi 500+.
- [[nemotron-3-5-bolt-e4b]]: model telefon/edge; jako drafter Qwena odpada (inny słownik).

## Powiązane
- [[research/_hub|research]]
- [[raport-57a-gsq-rco]]
- [[raport-57g-quantalloc-ear]]
- [[raport-21n-strata-gyro]]
- [[rtx-3090]]
