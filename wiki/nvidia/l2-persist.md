---
typ: nvidia
tags: [nvidia, cache, l2]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/21b-gpu-perf-zasoby.md:202-213,281-289; https://docs.nvidia.com/cuda/cuda-programming-guide/04-special-topics/l2-cache-control.html
status: do-sprawdzenia
---
# L2 persisting window (NVIDIA) dla danych czytanych co token

**`cudaDeviceSetLimit(cudaLimitPersistingL2CacheSize, …)` + `accessPolicyWindow` (Persisting/Streaming) przypina w L2 dane czytane w każdym tokenie; strumień wag raz na token przy LRU nie trafia nigdy, ale część głowy LFM (215 MB) już tak: 5090 (60 MB) +1.7%, 4090 +2%, 5060 Ti +1.1%, 3090 0 (`[SZACUNEK]`, raport 21b, 2026-10-19).**

Qwen: 60 MB / 16.5 GB ≈ 0.36%, wyjątek blok MTP czytany 4× na krok (~1% na 5090). Ryzyko: set-aside zmniejsza L2 dla FA (kvq czyta drugi kafel z L2) – mierzyć przy 32k. Na XTX odpowiednika nie ma (MALL niesterowalny z HIP). E3: przełącznik `GGML_CUDA_L2_PERSIST=MB`, kill < +0.7% LFM d0 albo regresja d32k > 0.5%.

## Powiązane
- [[nvidia/_hub|NVIDIA]]
- [[karty-nvidia-parametry]]
- [[lekcja-prefetch-mall-xtx]]
