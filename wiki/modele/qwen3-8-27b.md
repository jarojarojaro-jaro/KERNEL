---
typ: model
tags: [modele, qwen, gdn]
aktualizacja: 2026-10-21
zrodlo: ~/KERNEL/sources/qwen3.8-27b.md:5-24; ~/KERNEL/qwen-opt/SPEC-QWEN27B.md:17-27; ~/KERNEL/qwen-opt/STATUS-NEXT.md:8-13; ~/KERNEL/qwen-opt/NOTES.md:6-13,331; ls ~/models (2026-10-16); ~/KERNEL/product/research/06-produkt-ux-prawo-biznes.md:50; ~/KERNEL/product/research/18-nastepna-fala.md:96-141; ~/KERNEL/product/research/37-proza-100.md:13; ~/KERNEL/product/research/43-integracja-2026-10-20.md:45-49
status: aktualne
model: qwen3-8-27b
rozmiar: 27B
kwant: UD-Q4_K_XL
karty: rx-7900-xtx
wyniki:
  - qwen3-8-27b | rx-7900-xtx | 120.54 t/s | dekod MTP T=1; spec_sweep, topka-q63 | 2026-11-05
  - qwen3-8-27b | rx-7900-xtx | 116.1 t/s | dekod po odtworzeniu slotu; topka-q63 | 2026-11-05
  - qwen3-8-27b | rx-7900-xtx | 492.5 t/s | fill 255k; topka-q70, Uncensored | 2026-11-09
  - qwen3-8-27b | rx-7900-xtx | 1115 t/s | prefill pp4096; amd-opt | 2026-10-15
  - qwen3-8-27b | rx-7900-xtx | 43.2 t/s | dekod plain tg128; amd-opt | 2026-10-15
  - qwen3-8-27b | rx-7900-xtx | 78.93 t/s | proza E0 | 2026-10-21
---
# Qwen3.8-27B (główny model)

**Gęsty hybrydowy model 27B (48 warstw Gated DeltaNet + 16 pełnej uwagi) z wbudowaną głowicą MTP; na RX 7900 XTX przyspieszony z 59.2 do 109 t/s.**

Architektura (`qwen35` w llama.cpp): 64 warstwy w układzie 3:1, hidden 5120, słownik 248 320, kontekst natywny 262 144, head dim atencji 256 (raport 13), 27.32 B parametrów. DeltaNet trzyma stały stan rekurencyjny, więc KV cache to ok. 1/4 klasycznego 27B. Głowica MTP `blk.64` (nextn) zostaje w GGUF. Wizja przez osobny `mmproj`.

Plik: `~/models/Qwen3.8-27B-UD-Q4_K_XL.gguf` (unsloth), 16.35 GiB, mieszane kwanty (Q5_K 7.9 GB, IQ4_XS 3.1, Q4_K 3.1, Q6_K 2.9, reszta 0.7).

Nasze ustawienia (`run-llm.sh qwen`): ROCm, ctx 204800, KV q4_0, MTP n=4, słownik draftu 64k, draft IQ4_XS, KV draftu q4_0, `EFFORT=low`.

Wyniki na XTX:
- start 2026-10-09 (stary build, MTP n=3): 59.2 t/s (serve_bench, mieszanka EN/PL, T=0);
- 2026-10-15 (`amd-opt`, spec_sweep 6×3, T=1): **109.0 t/s**, 27.74 ms/krok, pp4096 1115, tg128 bez spekulacji 43.2;
- długi kontekst (2026-10-14, T=0, przed PM4): 1.7k 130.2 / 29.5k 105.2 / 94k 100.6 t/s.

Licencja: Apache 2.0.

Bajty na krok (raport 18, nagłówek GGUF): MLP 10.62 GB (4.96 bpw), głowica Q6_K 1.043 GB (6.2%), plain razem 16.48 GB wag + stan GDN 151 MB f32 + KV q4_0 18 432 B/token; roofline plain 57.1 t/s przy 960 GB/s, zmierzone 43.2 = 75.7%; MTP @2k 71% roofline ([[raport-18-nastepna-fala]]).

## Aktualizacja 2026-10-21
- XTX: proza E0 78.93 t/s ([[metryka-prozy-e0]]); produkcja topka f9b84bcfa ([[raport-43-integracja]]); na 10–16 GB raport 33 woli [[qwen3-6-35b-a3b]].
- **Od 2026-11-05 produkcja = topka-q63 c0576e3e8** (MTP lean reserve + poprawki MTP upstream #30141/#31350/#31368/#30574; backup `~/llama-topka.f9b84bcfa`). ABBA vs f9b: spec_sweep T=1 120.51/120.58 → 120.54/120.57 t/s (0%), md5 long 32k 20bfd0bb identyczny, VRAM 23359 → 22319 MB (−1.0 GiB), akceptacja MTP po odtworzeniu slotu 0.41 → 0.60, decode po odtworzeniu 91.0 → 116.1 t/s (+27.6%). Cap LDS FA: no-op (runtime podaje 64 KB). Źródło: `~/qwen-opt/q63/logs/summary.txt`, `~/qwen-opt/q63/logs-dep/`.
- **Od 2026-11-09 produkcja = topka-q70** (topka-q63 c0576e3e8 + cachesave #30137/`LLAMA_SERVER_CACHE_HUGE=1` + FA D256 wariant 83; env domyślne w `run-topka.sh`, VAR 83 tylko qwen/uncensored; backup `~/llama-topka.c0576e3e8`). Final mode, Uncensored: tura agenta przy 76–112k 13 413 → 12 029 ms (−10.3%), fill 255k 466.3 → 492.5 t/s (+5.6%), spec_sweep 119.3 t/s bez zmian, md5 identyczne. [[2026-11-09-wdrozenie-topka-q70]].

<!-- TABELE:START -->
## Wyniki z notatek (157)

Najlepszy wynik na metrykę z pól `wynik` notatek testów (tools/tabele.py, 2026-11-22); pełna tabela: [[najlepsze-wyniki]].

| karta | metryka | najlepszy | warunki | data | źródło |
|---|---|---|---|---|---|
| NVIDIA RTX 3060 12 GB [[rtx-3060]] | czat T=1 T' | **38.6 t/s** | UD-Q2_K_XL, c 36864, COUPLED=1 | 2026-10-20 | [[raport-31-3060-3080]] |
| NVIDIA RTX 3060 12 GB [[rtx-3060]] | dekod MTP n2 T=0 | **34,0 t/s** | GSQ IQ3_XXS-mtp, kvqlean, 144 W | 2026-11-19 | [[2026-11-19-k118-nvidia-pelna-moc]] |
| NVIDIA RTX 3090 [[rtx-3090]] | code-edit | **348.9 t/s** | cuda-topka2 | 2026-10-20 | [[raport-27-3090-final]] |
| NVIDIA RTX 3090 [[rtx-3090]] | code-edit fork | **105.3 t/s** | 4.91 tok/krok, 46.6 ms/krok (Magnitude 141.9) | 2026-10-16 | [[2026-10-16-magnitude-rozklad-wygranej]] |
| NVIDIA RTX 3090 [[rtx-3090]] | copy 64k fork | **69.7 t/s** | 4.51 tok/krok (Magnitude 80.2) | 2026-10-16 | [[2026-10-16-magnitude-rozklad-wygranej]] |
| NVIDIA RTX 3090 [[rtx-3090]] | czat T=1 | **93.3 t/s** | cuda-topka2 lookup W16 + verify | 2026-10-20 | [[raport-27-3090-final]] |
| NVIDIA RTX 3090 [[rtx-3090]] | dekod | **78.0 t/s** | nasz silnik (A0 38.9) | 2026-10-19 | [[benchmarki-przed-po-2026-10-19]] |
| NVIDIA RTX 3090 [[rtx-3090]] | dekod 262k T=0 | **51.1 t/s** | fork kvqleana, UD-Q4_K_XL | 2026-11-09 | [[2026-11-09-qwen-warp-vs-fork-3090]] |
| NVIDIA RTX 3090 [[rtx-3090]] | dekod krótki T=0 | **82.9 t/s** | fork kvqleana, UD-Q4_K_XL, 350 W | 2026-11-09 | [[2026-11-09-qwen-warp-vs-fork-3090]] |
| NVIDIA RTX 3090 [[rtx-3090]] | dekod MTP | **78.0 t/s** | A2 | 2026-10-16 | [[rtx-3090]] |
| NVIDIA RTX 3090 [[rtx-3090]] | dekod MTP 59k | **89.75 t/s** | kvq CUDA (bez 70.33) | 2026-10-16 | [[2026-10-16-kvq-cuda]] |
| NVIDIA RTX 3090 [[rtx-3090]] | dekod MTP ctx 262 144 | **79,97 t/s** | UD-Q4_K_XL, fork+kvq+lean, fill PASS | 2026-11-07 | [[2026-11-07-kampania-nvidia-vast]] |
| NVIDIA RTX 3090 [[rtx-3090]] | dekod MTP n2 T=0 | **89,5 t/s** | GSQ IQ3_XXS-mtp, kvqlean, 418 W | 2026-11-19 | [[2026-11-19-k118-nvidia-pelna-moc]] |
| NVIDIA RTX 3090 [[rtx-3090]] | dekod MTP n2 T=0 przy 95,6k | **71,8 t/s** | ctx 139 264 | 2026-11-19 | [[2026-11-19-k118-nvidia-pelna-moc]] |
| NVIDIA RTX 3090 [[rtx-3090]] | dekod MTP T1 | **79,97 t/s** | fork+kvq+lean UD-Q4_K_XL 262 144 | 2026-11-07 | [[rtx-3090]] |
| NVIDIA RTX 3090 [[rtx-3090]] | dekod MTP T=1 | **93.3 t/s** | topka czat | 2026-10-19 | [[rtx-3090]] |
| NVIDIA RTX 3090 [[rtx-3090]] | dekod MTP@59k | **89,75 t/s** | kvq-mma | 2026-10-16 | [[fattn-kvq]] |
| NVIDIA RTX 3090 [[rtx-3090]] | dekod pick Enigmy ctx 245 760 | **61,49 t/s** | pin b11856 | 2026-11-07 | [[2026-11-07-kampania-nvidia-vast]] |
| NVIDIA RTX 3090 [[rtx-3090]] | kopia 64k | **245 t/s** | topka CUDA | 2026-10-19 | [[raport-24e-nvidia-runda]] |
| NVIDIA RTX 3090 [[rtx-3090]] | krok DFlash2 | **64 ms** |  | 2026-10-19 | [[raport-24j-router]] |
| NVIDIA RTX 3090 [[rtx-3090]] | krok MTP | **46.5 ms** |  | 2026-10-19 | [[raport-24j-router]] |
| NVIDIA RTX 3090 [[rtx-3090]] | mvs | **300.5 t/s** | UD-Q6_K_M | 2026-10-20 | [[raport-31-3090]] |
| NVIDIA RTX 3090 [[rtx-3090]] | prefill 130k → 262k | **420 t/s** | fork kvqleana | 2026-11-09 | [[2026-11-09-qwen-warp-vs-fork-3090]] |
| NVIDIA RTX 3090 [[rtx-3090]] | prefill 64k fork | **888 t/s** | (Magnitude 744) | 2026-10-16 | [[2026-10-16-magnitude-vs-fork]] |
| NVIDIA RTX 3090 [[rtx-3090]] | prefill ~11k | **1386 t/s** | kvqlean | 2026-11-19 | [[2026-11-19-k118-nvidia-pelna-moc]] |
| NVIDIA RTX 3090 [[rtx-3090]] | spec_sweep A2 | **78.0 t/s** | fork + słownik draftu, 300 W | 2026-10-16 | [[raport-09-chmura-3090]] |
| NVIDIA RTX 3090 [[rtx-3090]] | sweep T=1 fork | **65.7 t/s** | cuda-3090-opt (Magnitude 65.7, upstream 49.2) | 2026-10-16 | [[2026-10-16-magnitude-vs-fork]] |
| NVIDIA RTX 3090 [[rtx-3090]] | tg64 64k | **39.14 t/s** | kvq CUDA f08dc78bb, q4_0 (bez 28.61) | 2026-10-16 | [[2026-10-16-kvq-cuda]] |
| NVIDIA RTX 3090 [[rtx-3090]] | tg64@64k | **39,14 t/s** | kvq-mma f08dc78bb | 2026-10-16 | [[fattn-kvq]] |
| NVIDIA RTX 4060 Ti 16 GB [[rtx-4060-ti]] | code-edit | **170.9 t/s** | cuda-topka2 | 2026-10-20 | [[raport-29-4060ti]] |
| NVIDIA RTX 4060 Ti 16 GB [[rtx-4060-ti]] | czat T=1 | **35.4 t/s** | Q3_K_XL, cuda-topka2, 100 W | 2026-10-20 | [[raport-29-4060ti]] |
| NVIDIA RTX 4060 Ti 16 GB [[rtx-4060-ti]] | czat T=1 T' | **50.8 t/s** | UD-IQ4_XS, KV q4_0, 32k | 2026-10-20 | [[raport-31-4060ti]] |
| NVIDIA RTX 4060 Ti 16 GB [[rtx-4060-ti]] | dekod czat T=1 | **35.4 t/s** | UD-Q3_K_XL | 2026-10-20 | [[rtx-4060-ti]] |
| NVIDIA RTX 4060 Ti 16 GB [[rtx-4060-ti]] | dekod MTP n2 | **36,30 t/s** | ISTA IQ3_XXS-mtp lean, ctx 229 376 | 2026-11-07 | [[rtx-4060-ti]] |
| NVIDIA RTX 4060 Ti 16 GB [[rtx-4060-ti]] | dekod MTP n2 ctx 229 376 | **36,30 t/s** | ISTA IQ3_XXS-mtp, b12110lean, fill PASS | 2026-11-07 | [[2026-11-07-kampania-nvidia-vast]] |
| NVIDIA RTX 4060 Ti 16 GB [[rtx-4060-ti]] | dekod plain | **24,02 t/s** | ISTA ctx 217 088 | 2026-11-07 | [[rtx-4060-ti]] |
| NVIDIA RTX 4060 Ti 16 GB [[rtx-4060-ti]] | mvs T' | **188.6 t/s** | UD-IQ4_XS | 2026-10-20 | [[raport-31-4060ti]] |
| NVIDIA RTX 4080 SUPER [[rtx-4080-super]] | dekod MTP n4 T=0 | **107,3 t/s** | GSQ IQ3_XXS-mtp, kvqlean, 278 W | 2026-11-19 | [[2026-11-19-k118-nvidia-pelna-moc]] |
| NVIDIA RTX 4080 SUPER [[rtx-4080-super]] | prefill ~11k | **1862 t/s** | kvqlean | 2026-11-19 | [[2026-11-19-k118-nvidia-pelna-moc]] |
| NVIDIA RTX 5060 Ti 16 GB [[rtx-5060-ti]] | czat T=1 T | **62.6 t/s** | UD-IQ4_XS 32k, 150 W | 2026-10-20 | [[raport-31-5060ti]] |
| NVIDIA RTX 5060 Ti 16 GB [[rtx-5060-ti]] | dekod | **51.66 t/s** | nasz silnik (A0 28.07) | 2026-10-19 | [[benchmarki-przed-po-2026-10-19]] |
| NVIDIA RTX 5060 Ti 16 GB [[rtx-5060-ti]] | dekod MTP | **54,33 t/s** | fork+kvq+lean UD-Q3_K_XL ctx 98 304 | 2026-11-07 | [[rtx-5060-ti]] |
| NVIDIA RTX 5060 Ti 16 GB [[rtx-5060-ti]] | dekod MTP ctx 196 608 | **49,44 t/s** | ISTA IQ3_XXS-mtp, fork+kvq+lean | 2026-11-07 | [[2026-11-07-kampania-nvidia-vast]] |
| NVIDIA RTX 5060 Ti 16 GB [[rtx-5060-ti]] | dekod MTP n2 T=0 | **54,2 t/s** | GSQ IQ3_XXS-mtp, kvqlean, ctx 8192, 180 W | 2026-11-17 | [[2026-11-17-k114-nvidia-sufit]] |
| NVIDIA RTX 5060 Ti 16 GB [[rtx-5060-ti]] | dekod MTP n2 T=1 | **51,0 t/s** | GSQ IQ3_XXS-mtp, kvqlean, ctx 8192 | 2026-11-17 | [[2026-11-17-k114-nvidia-sufit]] |
| NVIDIA RTX 5060 Ti 16 GB [[rtx-5060-ti]] | dekod MTP n=2 | **51.7 t/s** | UD-Q3_K_XL 32k | 2026-10-18 | [[2026-10-18-e1-kwanty-27b-kld]] |
| NVIDIA RTX 5060 Ti 16 GB [[rtx-5060-ti]] | dekod MTP T=1 | **51.66 t/s** | UD-Q3_K_XL fork (A1 37.32) | 2026-10-16 | [[2026-10-16-kampania-nvidia]] |
| NVIDIA RTX 5060 Ti 16 GB [[rtx-5060-ti]] | dekod plain | **31,9 t/s** | GSQ IQ3_XXS-mtp, kvqlean | 2026-11-17 | [[2026-11-17-k114-nvidia-sufit]] |
| NVIDIA RTX 5060 Ti 16 GB [[rtx-5060-ti]] | mvs | **244.2 t/s** | UD-IQ4_XS | 2026-10-20 | [[raport-31-5060ti]] |
| NVIDIA RTX 5060 Ti 16 GB [[rtx-5060-ti]] | pp576 ub 16 | **306,41 t/s** | v1.0.0 (b11856 278,98) | 2026-11-14 | [[2026-11-14-k103-llamacpp-v1-nvidia]] |
| NVIDIA RTX 5060 Ti 16 GB [[rtx-5060-ti]] | prefill ~11k | **828 t/s** | GSQ IQ3_XXS-mtp, kvqlean | 2026-11-17 | [[2026-11-17-k114-nvidia-sufit]] |
| NVIDIA RTX 5060 Ti 16 GB [[rtx-5060-ti]] | spec_sweep T=1 MTP n2 | **45,62 t/s** | ISTA IQ3_XXS-mtp, v1.0.0, 150 W | 2026-11-14 | [[2026-11-14-k103-llamacpp-v1-nvidia]] |
| NVIDIA RTX 5060 Ti 16 GB [[rtx-5060-ti]] | spec_sweep T=1 MTP n3 | **40,32 t/s** | b12359, 160 W | 2026-11-14 | [[2026-11-14-k103-llamacpp-v1-nvidia]] |
| NVIDIA RTX 5060 Ti 16 GB [[rtx-5060-ti]] | sweep fork | **58.0 t/s** | Q3_K_XL (upstream 43.5) | 2026-10-16 | [[2026-10-16-magnitude-vs-fork]] |
| NVIDIA RTX 5060 Ti 16 GB [[rtx-5060-ti]] | tg64 64k | **25.69 t/s** | kvq CUDA, Q3_K_XL q8_0 (bez 20.61) | 2026-10-16 | [[2026-10-16-kvq-cuda]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | akceptacja głowicy MTP | **3.04 tok/krok** | UD-Q4_K_XL, amd-opt c90db29c6 | 2026-10-12 | [[2026-10-12-mtp-trening-faza1]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | bufor MTP ROCm0 | **40.28 MiB** |  | 2026-11-06 | [[raport-65-vram-rezerwa-mtp]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | code-edit | **419.9 t/s** | topka | 2026-10-20 | [[raport-wyniki-xtx-2026-10-19]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | copy 64k | **141.2 t/s** | ROCm MTP (Magnitude 63.7) | 2026-10-18 | [[2026-10-18-magnitude-vulkan-xtx]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | czat | **115.8 t/s** | PM4 WA=2 + GUARD (baza 110.8) | 2026-10-19 | [[raport-26-kolejka-gpu]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | czat T=1 | **115.6 t/s** | PAIR2 (było 115.1) | 2026-10-20 | [[2026-10-20-podsumowanie-nocy]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | czat T=1 baza | **115.1 t/s** |  | 2026-10-20 | [[raport-24w-pair2]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | czat T=1 PAIR2=1 | **115.6 t/s** |  | 2026-10-20 | [[raport-24w-pair2]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod 1.7k | **136.5 t/s** | sam MTP, LOOKUP=0 | 2026-10-20 | [[raport-wyniki-xtx-2026-10-19]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod 1.7k T=0 | **126.0 t/s** | K3 | 2026-10-13 | [[2026-10-13-k3-host]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod 94k | **70.9 t/s** | po kvq, MTP n=4 T=0 | 2026-10-12 | [[2026-10-12-cache-promptu-i-a7]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod 94k T=0 | **100.6 t/s** | KV draftu q4_0 | 2026-10-14 | [[2026-10-14-prefill-k5-t3]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod copy T=0 | **355.0 t/s** | W16 (MTP4 163.4) | 2026-10-18 | [[2026-10-18-lookup-ogon]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod deep 32630 tok. | **111.3 t/s** | Enigma | 2026-11-05 | [[enigma-uczciwy-benchmark]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod DFlash n=6 T=0 | **90.6 t/s** | Vulkan | 2026-10-10 | [[2026-10-10-sweep-mtp-dflash]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod DFlash n=6 T=1 | **71.9 t/s** | Vulkan | 2026-10-10 | [[2026-10-10-sweep-mtp-dflash]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod Enigma uczciwy bench | **97.8 t/s** | effort low (baseline 35.0) | 2026-11-05 | [[enigma-uczciwy-benchmark]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod long 30k T=0 | **373.5 t/s** | W16 (MTP4 156.7) | 2026-10-18 | [[2026-10-18-lookup-ogon]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod MTP | **113,2 t/s** | blok MTP IQ4_XS, 28.14 ms/krok | 2026-10-18 | [[latki-spekulacji]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod MTP 27k bitexact | **102.66 t/s** | (prod 111.77) | 2026-10-16 | [[2026-10-16-bit-exact]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod MTP budżet myślenia | **107.0 t/s** | sampler fast | 2026-10-15 | [[sampler-fast-path]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod MTP n=4 | **101.7 t/s** | K4 WMMA d3a0973ae | 2026-10-13 | [[2026-10-13-k4-i-hw-queues]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod MTP n=4 T=1 | **102.6 t/s** | po T1, 29.36 ms/krok | 2026-10-14 | [[2026-10-14-t1-t2-draft]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod MTP n=5 | **105.4 t/s** | K4 WMMA d3a0973ae | 2026-10-13 | [[2026-10-13-k4-i-hw-queues]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod MTP n=5 T=0 | **86.3 t/s** | Vulkan 285 W | 2026-10-10 | [[2026-10-10-sweep-mtp-dflash]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod MTP n=5 T=1 | **81.1 t/s** | Vulkan | 2026-10-10 | [[2026-10-10-sweep-mtp-dflash]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod MTP narzędzia omp | **113.2 t/s** | sampler fast | 2026-10-15 | [[sampler-fast-path]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod MTP reasoning_control | **109.5 t/s** | sampler fast (było 101.6) | 2026-10-15 | [[2026-10-15-sampler]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod MTP T=0 | **91.8 t/s** | Vulkan RADV + słownik 64k, n=5 | 2026-10-09 | [[2026-10-09-pierwsze-pomiary]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod MTP T=0.7 | **118.3 t/s** | COUPLED=1 (off 112.7) | 2026-10-18 | [[2026-10-18-sprzezone-probkowanie-mtp]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod MTP T=1 | **120.54 t/s** | spec_sweep, topka-q63 | 2026-11-05 | [[qwen3-8-27b]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod MTP T=1 bez sprzężenia | **107.6 t/s** |  | 2026-10-20 | [[raport-24p-sprzezone-t1]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod MTP T=1 SPEC_COUPLED=1 | **111.4 t/s** |  | 2026-10-20 | [[raport-24p-sprzezone-t1]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod mvs T=0 | **433.0 t/s** | topka-next coupled=1 + host-gap (było 420.2) | 2026-10-20 | [[2026-10-20-podsumowanie-nocy]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod mvs T=1 | **375.8 t/s** | W16 (MTP4 166.1) | 2026-10-18 | [[2026-10-18-lookup-ogon]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod plain tg128 | **43.2 t/s** | amd-opt | 2026-10-15 | [[qwen3-8-27b]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod po odtworzeniu slotu | **116.1 t/s** | topka-q63 | 2026-11-05 | [[qwen3-8-27b]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod serwer 94k | **70,9 t/s** | KV q4_0, kvq 0011 | 2026-10-12 | [[fattn-kvq]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod spec_sweep T=1 | **123,6 t/s** | stock, topka-q63 UD-Q4_K_XL | 2026-11-06 | [[2026-11-06-eco-sweep-sclk]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod ~32k | **111.6 t/s** | topka | 2026-10-20 | [[raport-wyniki-xtx-2026-10-19]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | energia | **2,07 J/token** | sclk 2200 (stock 2,27) | 2026-11-06 | [[2026-11-06-eco-sweep-sclk]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | fill 255k | **492.5 t/s** | topka-q70, Uncensored | 2026-11-09 | [[qwen3-8-27b]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | koszt haka MTP prefill 32k | **768 ms** | 2.2% TTFT | 2026-10-18 | [[2026-10-18-hak-mtp-i-checkpointy]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | krok B | **27.40 ms** |  | 2026-10-20 | [[raport-24o-luki-hosta]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | krok MTP4 mvs | **29.62 ms** |  | 2026-10-19 | [[raport-24k-koszt-weryfikacji]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | krok prozy T=1 | **27.38 ms** | 2.63 tok/krok, stara metryka | 2026-10-20 | [[raport-36-xtx-roadmap]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | krok spec_sweep RPB=1 | **28.80 ms** |  | 2026-10-20 | [[raport-24r-mmvq-pasmo]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | krok Vulkan 0007–0010 | **41.46 ms** | Qwen UD | 2026-10-12 | [[vulkan-mmvq]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | krok W16 mvs | **35.61 ms** |  | 2026-10-19 | [[raport-24k-koszt-weryfikacji]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | ms/krok MTP T=1 | **41.46 ms** | Vulkan łatki MMVQ | 2026-10-12 | [[2026-10-12-vulkan-krok-po-kroku]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | mvs | **433.8 t/s** | topka f9b84bcfa | 2026-10-21 | [[raport-43-integracja]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | mvs A | **428.49 t/s** |  | 2026-10-21 | [[raport-54-mniej-granic]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | mvs B ATTN_PREP_MT+KVQ_FWHT_GATE | **428.55 t/s** |  | 2026-10-21 | [[raport-54-mniej-granic]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | mvs bez GPU verify | **410.4 t/s** |  | 2026-10-19 | [[raport-24m-weryfikacja-gpu]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | mvs GPU verify | **420.1 t/s** | f2217bac7 | 2026-10-19 | [[raport-24m-weryfikacja-gpu]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | odczyt sesji 53k z SSD | **2,51 s** | slot-save-path, MTP | 2026-10-18 | [[cache-sesji-na-dysku]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | pasmo weryfikacji n=5 | **762 GB/s** |  | 2026-10-20 | [[raport-24r-mmvq-pasmo]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | pp4096 | **1123.2 t/s** | epilog MMQ 0070 (baza 1099.5) | 2026-10-15 | [[runda-6]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | pp4096 MMQ YDB=2 (wycofane, YDB=0 1097) | **1066 t/s** |  | 2026-10-15 | [[qwen-runda-5]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | pp5 d32768 bitexact | **133.8 t/s** | (prod 152.1) | 2026-10-16 | [[2026-10-16-bit-exact]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | prefill 128k | **708 t/s** | q63 | 2026-11-05 | [[2026-11-05-q63-topka]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | prefill 12k | **940 t/s** | sclk 2200 (stock 1030) | 2026-11-06 | [[2026-11-06-eco-sweep-sclk]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | prefill 29.5k | **943 t/s** | K5+T3 | 2026-10-14 | [[2026-10-14-prefill-k5-t3]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | prefill 32k | **969 t/s** | q63 | 2026-11-05 | [[2026-11-05-q63-topka]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | prefill 94k | **767 t/s** | K5+T3 0040-0045 | 2026-10-14 | [[prefill-mmq-fa]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | prefill Enigma | **1041 t/s** | kandydat enigma | 2026-11-05 | [[enigma-uczciwy-benchmark]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | prefill pp4096 | **1123,2 t/s** | MMQ epilog 0070 | 2026-10-15 | [[mmq-epilog]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | prefill zimny 27k | **31.9 s** | cache promptu domyślny | 2026-10-12 | [[2026-10-12-cache-promptu-i-a7]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | prompt 94k + 1000 tok. | **165 s** | ROCm (Vulkan 260 s) | 2026-10-12 | [[2026-10-12-rocm-vs-vulkan]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | proza E0 | **78.93 t/s** |  | 2026-10-21 | [[qwen3-8-27b]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | proza E0 T=1 | **78.93 t/s** | produkcja, thinking off | 2026-10-20 | [[metryka-prozy-e0]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | pytanie uzupełniające 27k | **0.7 s** | cache promptu | 2026-10-12 | [[2026-10-12-cache-promptu-i-a7]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | spec blok MTP IQ4_XS | **113.2 t/s** | 5 seedów (Q6_K 109.4) | 2026-10-18 | [[raport-16f-xtx-szybkie]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | spec_sweep | **109.0 t/s** | produkcja (fork 74.5) | 2026-10-19 | [[benchmarki-przed-po-2026-10-19]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | spec_sweep baza | **111.4 t/s** |  | 2026-10-20 | [[raport-24n-mmvq-n5]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | spec_sweep bitexact | **108.3 t/s** | 365af3e5e (prod 107.7) | 2026-10-16 | [[2026-10-16-bit-exact]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | spec_sweep MMVQ_OCC | **110.8 t/s** |  | 2026-10-20 | [[raport-24n-mmvq-n5]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | spec_sweep MMVQ_OCC serializacja | **104.3 t/s** |  | 2026-10-20 | [[raport-24n-mmvq-n5]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | spec_sweep qwen mtp T=1 | **108.82 t/s** | PM4 | 2026-10-14 | [[lfm-runda-4-pm4]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | spec_sweep T=1 | **120.50 t/s** | topka-q63 c0576e3e8 | 2026-11-05 | [[2026-11-05-q63-topka]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | spec_sweep T=1 1 seed | **105.1 t/s** | topka | 2026-10-19 | [[2026-10-19-build-topka]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | spec_sweep T=1 A | **113.8 t/s** |  | 2026-10-20 | [[raport-24o-luki-hosta]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | spec_sweep T=1 B przełączniki hosta | **117.9 t/s** |  | 2026-10-20 | [[raport-24o-luki-hosta]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | start serwera | **6.5 s** | topka f9b84bcfa (baza 39.8) | 2026-10-21 | [[raport-43-integracja]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | start sesji agenta | **1612 ms** | CACHE_SHARE_MIN=1024 (było 8019) | 2026-10-18 | [[2026-10-18-cache-promptu-agenta]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | sufit odczytu | **926 GB/s** |  | 2026-10-20 | [[raport-24r-mmvq-pasmo]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | sweep T=1 | **100.0 t/s** | ROCm MTP (Magnitude Vulkan 50.1) | 2026-10-18 | [[2026-10-18-magnitude-vulkan-xtx]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | szczyt VRAM fill 255k | **23367 MiB** |  | 2026-11-06 | [[raport-65-vram-rezerwa-mtp]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | T=0 reasoning | **154.2 t/s** | DRAFT_N=5 (baza 144.4) | 2026-10-20 | [[raport-35-xtx-eksperymenty]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | tg128 bitexact | **41.79 t/s** | 365af3e5e (prod 43.17) | 2026-10-16 | [[2026-10-16-bit-exact]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | tg128 wide off | **40.86 t/s** |  | 2026-10-20 | [[raport-24f-mmvq-fa]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | tg128 wide=2 | **40.41 t/s** |  | 2026-10-20 | [[raport-24f-mmvq-fa]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | trening MTP | **2.3 k tok/s** | bf16 K=4 T=2048, szczyt 12.1 GiB | 2026-10-12 | [[2026-10-12-mtp-trening-faza1]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | TTFT 32k MTP | **35050 ms** | (bez spekulacji 33619) | 2026-10-18 | [[2026-10-18-hak-mtp-i-checkpointy]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | tura agenta S2-turn2 | **197 ms** | CKPT_VRAM=2 | 2026-10-20 | [[raport-38-ckpt-vram]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | utworzenie checkpointu | **14.9 ms** | CKPT_VRAM=2 | 2026-10-20 | [[raport-38-ckpt-vram]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | V16 − V5 przy 2k | **6.40 ms** | llama-bench KV q4_0 | 2026-10-18 | [[koszt-szerokosci-weryfikacji]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | V16 − V5 przy 32k | **9.50 ms** | llama-bench KV q4_0 | 2026-10-18 | [[koszt-szerokosci-weryfikacji]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | V16 − V5 przy 64k | **12.45 ms** | llama-bench KV q4_0 | 2026-10-18 | [[koszt-szerokosci-weryfikacji]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | VRAM | **22319 MB** | lean reserve MTP (było 23360) | 2026-11-05 | [[2026-11-05-q63-topka]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | weryfikacja n=16 | **35.0 ms** | WMMA 0037 | 2026-10-13 | [[wmma-small-n]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | weryfikacja n=9 | **32.1 ms** | WMMA 0037 | 2026-10-13 | [[wmma-small-n]] |
<!-- TABELE:END -->

## Powiązane
- [[modele/_hub|Modele]]
- [[qwen3-8-27b-uncensored]]
- [[glowica-mtp]]
- [[gdn-replay]]
- [[stan-2026-10-15]]
