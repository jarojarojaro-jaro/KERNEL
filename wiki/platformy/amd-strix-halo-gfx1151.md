---
typ: platforma
tags: [platformy, amd, rdna3-5, gfx1151, strix-halo, apu]
aktualizacja: 2026-11-28
zrodlo: wiki/karty/strix-halo.md; wiki/stos/rdna3-gfx1100.md:21; wiki/lekcje/lekcja-enigma-apu-jako-karta.md; wiki/lekcje/lekcja-dense-szybszy-od-moe-ze-spekulacja.md; wiki/platformy/amd-rdna3-gfx1100.md
status: aktualne
---
# AMD Strix Halo gfx1151 (Ryzen AI Max): playbook

**APU RDNA3.5 z pamięcią zunifikowaną do 128 GB i 256 GB/s; kernele gfx11 przechodzą prawie bez zmian, ale pasmo jest prawie 4× niższe niż na XTX, więc spekulacja i MoE ważą tu najwięcej. U nas brak pomiaru.**

Topki: [[TOPKI]]. Wzorzec kolejności: [[amd-rdna3-gfx1100]].

## Dzień pierwszy
- Dostęp: GigaGPU Ryzen AI Max+ 395 (£299/mies.), faza 3 produktu ([[strix-halo]]).
- ROCm 10.0 jak na XTX; jądro zapisać z hosta (brak pomiaru). Pamięć: minimalne VRAM w BIOS, alokacje z GTT, limit `ttm.pages_limit` / `amd-ttm`, inaczej ROCm widzi połowę ([[strix-halo]]).
- PM4: `GGML_HIP_PM4=0` do czasu osobnego testu (taśma tylko gfx1100; pamięć UMA przez GPUVM to inny teren dla page faultów). Wariant `=1` tylko z `WA=2 GUARD=1 HSA_USE_SVM=0` ([[lekcja-pm4-zawsze-jawnie]]).
- Build `-DAMDGPU_TARGETS=gfx1151`; u nas `rbuild` + `cpuheavy`. Bramki części łatek obejmują już gfx115x (0022, 0040, 0060, 0070), ale nic nie mierzono ([[strix-halo]]).
- Zegary fabryczne; limit mocy APU dzielony z CPU.
- Sufit pasma: 256 GB/s ze specyfikacji, ok. 212 GB/s zmierzone (llm-tracker).
- Sanity (cudze): ROCm o 20,6% szybszy w pp i 24,6% wolniejszy w tg niż Vulkan (Qwen3-Coder-30B-A3B, 08/2026); `GGML_HIP_ROCWMMA_FATTN=ON` −41% przy pp8192; `ROCBLAS_USE_HIPBLASLT=1` ok. 3× pp ([[strix-halo]]).

## Kolejność optymalizacji
1. Spekulacja MTP + słownik 64k / drafter (XTX ×2,5): przy 212 GB/s gęsty 27B Q4 plain da ok. 13 t/s (szacunek z pasma), więc spekulacja to podstawa.
2. Logika hosta: sampler fast path, K-020.
3. FA kvq (XTX +65% przy 94k), MMVQ wielokolumnowe, FA D256, K-012, K-047: WMMA gfx11 = RDNA3.5, przenoszą się po sprawdzeniu bramek gfx115x i strojeniu kafli pod 40 CU zamiast 96.
4. Maya: K-200, K-185, K-158s, K-206 są gfx11, powinny działać; brak pomiaru.
5. PM4 dopiero po testach stabilności.
Infinity Cache: 32 MiB (MALL) wg specyfikacji producenta; mniej niż 96 MiB na XTX, więc KV długiego kontekstu idzie z DRAM.

## Testy
- Te same skrypty co na XTX: `spec_sweep.py`, `long_ctx_bench.py`, `nib/wall.py` ABBA, `k202srv.py` igły, `IK2_K158_BENCH=1` ([[spec-sweep]]).
- `test-backend-ops` na kształtach produkcji, md5 T=0 vs upstream na tej samej maszynie, KLD ([[bramka-kld-kanarki]]).
- Pomiar pasma przed wszystkim (sufit 212 vs 256 GB/s).

## Kiedy topka jest gotowa
Pełny stos ze spekulacją, KV q4, pełny kontekst (128 GB mieści każdy nasz model z pełnym kontekstem), igły 5/5, md5/KLD PASS, wall bez regresji, wpis w [[REKORDY]].

## Pułapki
- APU to nie karta z własnym VRAM: aplikacja liczyła prędkość z niewłaściwego pasma ([[lekcja-enigma-apu-jako-karta]]).
- rocWMMA FA szkodzi; nie włączać bez A/B.
- FMA contraction przy przestrajaniu kafli ([[lekcja-fma-kontrakcja-bitowa-zgodnosc]]); mikrobench nie decyduje ([[lekcja-mikrobench-klamie]]).

## Rodzaje modeli
- MoE A2B/A3B: bez spekulacji MoE jest tu najszybsze (czyta mało wag), ale z draftem gęsty odrabia ([[lekcja-dense-szybszy-od-moe-ze-spekulacja]]); duże MoE (np. 125B, 53,8 t/s wyjścia u Straty) mieszczą się tylko tu.
- Gęsty 27B / GDN hybrid: spekulacja konieczna.
- Ternary: najmniej bajtów na token, naturalny kandydat.
- Inkling: ok. 3,3 GB wag na token ([[inkling-2-mini]]), Maya z drafterem i pełnym 1M kontekstu.

## Powiązane
- [[strix-halo]]
- [[rdna3-gfx1100]]
- [[lekcja-enigma-apu-jako-karta]]
- [[amd-rdna3-gfx1100]]
