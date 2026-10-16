---
typ: hub
tags: [nvidia, hub]
aktualizacja: 2026-10-16
zrodlo: wiki/tools/wiki.py index
status: aktualne
---
# CUDA i stos NVIDIA

**Stos NVIDIA: CUDA, architektury sm_86/89/120, poprawki zgodności forka z CUDA, NVFP4, wyniki z chmury.**

Większość łatek powstała pod HIP/RDNA3; tu jest, co z tego działa na CUDA i co trzeba było poprawić. Wyniki z chmury są w toku: patrz `status`.

Wróć: [[index|Strona główna]]. Lista niżej jest generowana przez `python3 tools/wiki.py index`; nie edytuj jej ręcznie.

<!-- AUTO:START -->
## Notatki (6)

- [[sm-86-89-120|Architektury NVIDIA: sm_86, sm_89, sm_120]] — Celujemy w trzy generacje kart konsumenckich: Ampere sm_86 (RTX 3060, 3090), Ada sm_89 (RTX 4060 Ti) i Blackwell sm_120 (RTX 5060 Ti); różnią się m.in. obsługą PDL.
- [[cuda-compat|Gałąź cuda-compat: poprawki forka dla NVIDIA]] — `amd-opt` nie kompilował się dla CUDA; gałąź `cuda-compat` @ `7b2680760` dodaje 4 commity (2 kompilacyjne, 2 semantyczne), a kod GPU dla gfx1100 zostaje bit w bit ten sam.
- [[latki-na-nvidia|Które łatki działają na NVIDIA]] — Na NVIDIA domyślnie działa ok. 35 z 70 łatek; kod tylko dla AMD (DPP, WMMA, buffer resource, PM4, kvq) jest za guardami albo bramką RDNA.
- [[nvfp4|NVFP4 (4-bitowy format NVIDIA)]] — NVFP4 to 4-bitowy format liczb NVIDIA, sprzętowo liczony od Blackwella (np. RTX 5060 Ti); RX 7900 XTX nie ma FP4/FP8, a my go nie używamy, bo zmienia model.
- [[cuda-stos|Stos CUDA: jak budujemy fork dla NVIDIA]] — Fork budujemy dla NVIDIA nvcc 12.8 z conda-forge (bez sudo, bez sterownika na serwerze), dla architektur sm_86, sm_89 i sm_120; testy na GPU robimy w chmurze.
- [[nvidia-wyniki-2026-10-16|Wyniki NVIDIA z chmury (stan 2026-10-16, w toku)]] — Pierwsza runda na Vast: fork buduje się i przechodzi testy op na RTX 3090, na RTX 5060 Ti padają 2 testy prologu GDN, a greedy md5 forka różni się od upstreamu na każdym modelu, także z wyłączonymi przełącznikami.
<!-- AUTO:END -->
