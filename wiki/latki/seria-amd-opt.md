---
typ: latka
tags: [latki, amd-opt, historia]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/patches/llama.cpp-amd-opt/ (70 plików); ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:53,155,157-172; ~/KERNEL/qwen-opt/STATUS-NEXT.md:5; ~/KERNEL/qwen-opt/README.md:1-40; ~/KERNEL/product/research/16h-fabryka-v1.md:51-58
status: aktualne
---
# Seria łatek amd-opt (0001–0070)

**70 commitów nałożonych liniowo na upstream llama.cpp `e60eff95f` (2026-10-09); gałąź `amd-opt` @ `f61994f58`, zainstalowana w `~/llama-opt`.**

| łatki | runda / data | temat |
|---|---|---|
| 0001–0005 | 2026-10-09 | MMVQ 2–8 kolumn, cache q8_1, słownik draftu, higiena |
| 0006–0010 | 2026-10-12 | Vulkan RDNA (dziś opcja) |
| 0011 | 2026-10-12 | FA `kvq` dla KV q4_0 |
| 0012–0019 | A3–A6, 2026-10-12 | fuzje weryfikacji Qwena; 0018 = cherry-pick upstream #30103 |
| 0020 | 2026-10-12 | draft MTP jednym grafem |
| 0021–0028 | K1, K2, 2026-10-13 | MMVQ RDNA3, clamp q8_1, para MMVQ, DPP |
| 0029–0032 | K3, S2, 2026-10-13 | host, sampler, draft IQ4_XS |
| 0033–0038 | S4, K4, T1, 2026-10-13 (daty autora commitów; wpis T1 w NOTES pod 2026-10-14) | lag/replay GDN i conv, WMMA 9–16 |
| 0039–0047 | T2, K5, T3, S3, 2026-10-14 | adaptacyjny draft (opt-in), prefill, okno MTP (negatywne), host |
| 0048–0064 | LFM rundy 1–4, 2026-10-14 | MoE, shortconv, kvq q8_0, PM4 replay |
| 0065–0069 | 2026-10-15 | sampler bez wolnych ścieżek |
| 0070 | runda 6, 2026-10-15 | epilog MMQ |

Model docelowy (raport 07): Qwen 0001–0047 (bez 5 łatek Vulkan), LFM 0048–0064, oba 0065–0069, Qwen prefill 0070. Odtworzenie: `git am patches/llama.cpp-amd-opt/*.patch` na `e60eff95f` (README; uwaga: README wciąż mówi o 59 zmianach).

Łatka 0070 (2026-10-16): karta fabryki `2026-10-17-mmq-epi-0070` zarejestrowana (ledger seq 1), czeka na ~20 min GPU; R29 = build CUDA na `amd-opt` (naprawione w `cuda-compat` `57e0bdfe4`); zob. [[fabryka-cli]].

## Powiązane
- [[latki/_hub|Łatki]]
- [[patch-manifest]]
- [[klasyfikacja-latek]]
- amd-opt
- [[kernele/_hub|Kernele]]
- Rodziny: [[mmvq-multikolumnowe]] (0001–0002, 0021–0022), [[vulkan-mmvq]] (0006–0010), [[fattn-kvq]] (0011, 0055, 0058), [[fuzje-weryfikacji]] (0012–0019), [[clamp-q8-1]] (0023), [[para-mmvq]] (0024), [[sampler-fast-path]] (0031, 0048, 0065–0069), [[gdn-replay]] (0033–0036), [[pm4-replay]] (0060–0061), [[mmq-epilog]] (0070)
- [[latki-hostowe]], [[latki-spekulacji]], [[latki-oczekujace]], [[latki-do-upstreamu]], [[wylaczniki-env]]
