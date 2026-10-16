---
typ: hub
tags: [nvidia, hub]
aktualizacja: 2026-10-16
zrodlo: wiki/tools/wiki.py index
status: aktualne
---
# CUDA i stos NVIDIA

**Stos NVIDIA: CUDA, architektury sm_86/89/120, poprawki zgodności forka z CUDA, NVFP4, wyniki z chmury.**

Większość łatek powstała pod HIP/RDNA3; tu jest, co z tego działa na CUDA i co trzeba było poprawić. Wyniki pierwszej kampanii w chmurze (2026-10-16) są finalne: [[nvidia-wyniki-2026-10-16]].

Wróć: [[index|Strona główna]]. Lista niżej jest generowana przez `python3 tools/wiki.py index`; nie edytuj jej ręcznie.

<!-- AUTO:START -->
## Notatki (7)

- [[sm-86-89-120|Architektury NVIDIA: sm_86, sm_89, sm_120]] — Celujemy w trzy generacje kart konsumenckich: Ampere sm_86 (RTX 3060, 3090), Ada sm_89 (RTX 4060 Ti) i Blackwell sm_120 (RTX 5060 Ti); różnią się m.in. obsługą PDL.
- [[fa-kv-kwantyzowane-cuda|Flash attention na KV q4_0/q8_0 w upstream CUDA]] — Upstream CUDA dla skwantyzowanego KV wybiera kernel VEC tylko przy n=1 (Ampere) albo n ≤ 2 (Ada+), a w pozostałych przypadkach MMA_F16 z buforem f16 całego K/V; vec czyta KV osobno dla każdej głowy Q w grupie GQA.
- [[cuda-compat|Gałąź cuda-compat: poprawki forka dla NVIDIA]] — `amd-opt` nie kompilował się dla CUDA; gałąź `cuda-compat` @ `7b2680760` dodaje 4 commity (2 kompilacyjne, 2 semantyczne), a kod GPU dla gfx1100 zostaje bit w bit ten sam.
- [[latki-na-nvidia|Które łatki działają na NVIDIA]] — Na NVIDIA domyślnie działa ok. 35 z 70 łatek; kod tylko dla AMD (DPP, WMMA, buffer resource, PM4, kvq) jest za guardami albo bramką RDNA.
- [[nvfp4|NVFP4 (4-bitowy format NVIDIA)]] — NVFP4 to 4-bitowy format liczb NVIDIA, sprzętowo liczony od Blackwella (np. RTX 5060 Ti); RX 7900 XTX nie ma FP4/FP8, a my go nie używamy, bo zmienia model.
- [[cuda-stos|Stos CUDA: jak budujemy fork dla NVIDIA]] — Fork budujemy dla NVIDIA nvcc 12.8 z conda-forge (bez sudo, bez sterownika na serwerze), dla architektur sm_86, sm_89 i sm_120; testy na GPU robimy w chmurze.
- [[nvidia-wyniki-2026-10-16|Wyniki NVIDIA z chmury (2026-10-16, finalne)]] — Pierwsza runda na trzech kartach NVIDIA zakończona: nasz silnik daje ×1.4–2.0 względem domyślnego llama.cpp na modelach z MTP lub dużym udziałem hosta (Qwen, LFM) i tylko +5–7% na 2-bitowych 27B bez MTP; greedy md5 forka różni się od upstreamu przez łatki bez przełącznika (0001/0002, 0013).
<!-- AUTO:END -->
