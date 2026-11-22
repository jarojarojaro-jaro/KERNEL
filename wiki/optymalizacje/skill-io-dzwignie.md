---
typ: optymalizacja
tags: [optymalizacje, dzwignie, spekulacja, prefill, cache, skill-io]
aktualizacja: 2026-11-17
zrodlo: ~/kernel/zrodla/inference-optimisation-skill @ fda968e — references/levers.md:1-87, SKILL.md:112-140 (kolejność dźwigni, gdy dźwignia zawodzi); nasze liczby: [[REKORDY]], notatki eksperymentów w Powiązanych
status: aktualne
---
# Dźwignie wg skill-io (levers.md): każda z naszym statusem i spodziewanym zyskiem na XTX

**Ze 29 dźwigni stosujemy 19. Pięć nas nie dotyczy (MoE, torch, pamięć zunifikowana). Trzy odrzuca reguła „tylko bezstratnie”. Częściowo zrobione są dwie: długość draftu per kontekst (czeka na decyzję o bramce, K-008/K-046) i rozmiar chunku prefillu (K-048, K-106). Kolejność dźwigni z SKILL.md (`:112-133`): cache JIT → grafy → spekulacja → współbieżność i KV → prefill → wątki i kafle → praca nad kernelem.**

| dźwignia (levers.md) | ich dowód | u nas | spodziewane na XTX |
|---|---|---|---|
| cache JIT/kompilacji (`:12`) | start 113 → 43 s | tak: kernele HIP AOT; cache requantu MTP 39,8 → 6,5 s | 0 (start 6,1 s) |
| mmap wolny (`:15`), 1 worker kompilacji (`:16`) | 26 min → s | n/d (llama.cpp, bez torch) | 0 |
| TTFT krótki = harmonogram + 1 przebieg (`:17`) | – | tak: K-003, szablon 0,8 ms, tokenizacja 0,3 ms, reszta to checkpointy GDN | ~0,1 s/żądanie (koszt checkpointów) |
| grafy dekodu (`:21-24`) | 14,4 → 28,4 t/s | tak: taśma PM4 + grafy HIP; PM4 +6,4% przy 1,7k ([[pm4-replay]]) | wykorzystane |
| przycięta głowica draftu (`:26-28`) | +27% (512/1940 bloków) | tak: słownik 64k IQ4_XS | wykorzystane |
| długość draftu per współbieżność/kontekst (`:29-32`) | B390 128k: 1 draft 29,6 vs 3: 15,5 | częściowo: n=4 stałe; DRAFT_N=3 proza +4,3%; dynamiczna +3,9% | +3,9…4,8% (K-008, decyzja właściciela) |
| akceptacja per głębokość (`:33`) | 14% na głęb. 2 | zmierzone: PL 0,64 / 0,46 / 0,35 / 0,30 | – |
| spekulacja może przegrać (`:34-36`) | M4 6,35 → 3,25 | u nas zawsze wygrywa (plain 43 vs 120 t/s); lookup neutralny (K-002) | 0 |
| weryfikacja atencją typu dekod (`:37`) | 75,7 → 82,6 t/s | tak: `kvq` ([[fattn-kvq]]) | nowy układ +1,5…3% przy ≥ 94k (K-012) |
| próbkowanie na GPU (`:38`) | +10% c1 | tak: `LLAMA_GPU_VERIFY=1`; NVIDIA fork T=1 traci 7–13% | Enigma NVIDIA (K-004) |
| mniej bajtów na wagę (`:39`) | AWQ-INT4 > FP8 na Ampere | **odrzucone**: zakaz zmiany kwantu | – |
| wątki/split-K per karta (`:40-42`) | 48,5 → 56,9 | tak: sweep wariantów FA (83), MMQ w kolejce (K-009) | prefill +2…4% |
| fuzja pod grafami nic nie daje (`:43`) | 3 × 0% | potwierdzone u nas (LaunchCut, x54 → K-092) | 0 |
| typ KV (`:44-46`) | q8_0 45,4 → 27,0 t/s przy 16 z 64 warstw KV | KV q4_0 + `kvq` szybkie; FA83 na f16 −2,4% | – |
| sloty stanu hybrydy (`:50-52`) | 1 → N żądań | `-np 2` na XTX odrzucone; NVIDIA `-np 4` + MTP nie startuje (K-061) | n/d (1 użytkownik) |
| pula KV N × ctx + soak (`:53`) | 4 × 256K | 1 × 262 144, soak S6 1205 żądań | – |
| cache prefiksów jawnie, `cached_tokens` > 0 (`:54-56`) | TTFT 36 → 0,45 s | tak: cache-ram 40960, CACHE_SHARE_MIN, cachesave; tura 13,4 → 12,0 s | wykorzystane; dalej K-006 |
| pamięć poza alokatorem (`:57`) | OOM | tak: lean reserve 1,07 → 0,08 GiB | – |
| zapas ≥ 1,5 GB (`:58`) | livelock | **ryzyko**: szczyt 23 398 z 24 560 MiB, czyli ~1,1 GiB zapasu | – |
| chunk prefillu vs blokada dekodu (`:62-64`) | stall 7,1 → 1,95 s za −4% | ub 512; wpływ na drugi wątek niezmierzony | K-106 |
| szybsza biblioteka atencji (`:65-67`) | +7…18% | tak: FA D256 wariant 83, +5,8% przy 128k | wykorzystane |
| int8/fp8 prefill (`:68`) | 1,89×, NLL +0,17% | **odrzucone** (stratne) | – |
| MoE: progi paddingu (`:69-72`) | +7…22% | n/d (gęsty 27B) | – |
| profil po etapach (`:73`) | GEMM 40% już na sufitcie | tak: 24v (FA 53% fillu 255k), MMQ 63–81% prefillu | – |
| test bitowy per M (`:77-79`) | „−4%” kernel dawał złe wyniki | tak: `test-backend-ops` + md5 | – |
| czytać ISA (`:80`) | LM head 4,05 → 1,72 ms | tak: `isa.sh`, FA83 spill 220 VGPR → 0 | – |
| płoty pamięci na nowych GPU (`:81`) | Xe3 | n/d | – |
| odrzucone na Xe: prefetch, LUT, async (`:82-87`) | 0 / gorzej | u nas też KILL: PM4-PDL, prefetch L2 MMVQ | – |

**Reguła „gdy dźwignia zawodzi”** (SKILL.md `:136-140`):
- Fuzja nic nie daje pod grafami → czas siedzi w głównych kernelach.
- Wyższa akceptacja nie daje t/s → draft kosztuje za dużo; mierzyć czas kroku.
- Dziwny wynik → najpierw podejrzewać pomiar.

U nas to samo wychodzi z sufitów: luka 26,9 vs 19,2 ms/krok leży w kernelach i drafcie, nie w akceptacji (K-111).

## Dźwignie na AMD i NVIDIA (zakres: obie firmy, 2026-11-17)

**Jednostki macierzowe** (strony producentów, sufity w [[skill-io-sufity]]):
- **RDNA3:** WMMA, wave32, FP16 = INT8.
- **RDNA4:** WMMA z FP8, INT8 = 2 × FP16.
- **CDNA2/3/4:** MFMA, wave64; FP8 od CDNA3, MXFP4/6 na CDNA4.
- **NVIDIA:** `mma.sync` (Ampere/Ada/Blackwell GeForce), `wgmma` (Hopper), `tcgen05` (B200). FP8 od Ady, FP4 na Blackwellu. GeForce liczy FP16 z akumulacją FP32 o połowę wolniej.

**Cache i biblioteki:**
- Cache ostatniego poziomu: Infinity Cache (RDNA2 128 MB, XTX 96 MB, 9070 XT 64 MB, MI355X 256 MB) kontra L2 (3090 6 MB, 4090 72 MB, 5090 96 MB).
- Biblioteki: rocBLAS/hipBLASLt + CK/aiter kontra cuBLAS/cuBLASLt + FlashAttention 2/3/4.

| dźwignia | AMD | NVIDIA | różnica | zysk (zmierzony / spodziewany) |
|---|---|---|---|---|
| grafy dekodu | grafy HIP; taśma PM4 tylko nasza i tylko gfx1100 | grafy CUDA domyślnie w llama.cpp, dojrzałe | PM4 nie przenosi się na RDNA4/CDNA bez testu; na NVIDIA odpowiednikiem są grafy CUDA | XTX PM4 +6,4% (1,7k); NVIDIA już w bazie |
| MTP + przycięta głowica draftu 64k | tak (topka) | tak (fork kvqlean) | niezależna od architektury | XTX wykorzystane; NVIDIA upstream MTP n2 v1.0.0 +3,8% (K-103) |
| długość draftu per kontekst | n4 stałe | n3 (upstream) / n2 (lean) | zależna od pasma: słabsza karta → krótszy draft (`levers.md:34`) | sweep per karta; 5060 Ti (448 GB/s) najbardziej wrażliwa |
| weryfikacja atencją dekodu (`kvq`) | gfx1100 | fork na sm_86/89/120 | ten sam kod, różne kafle | fork (kvq + lean) vs upstream: 3090 61,5 → 80,0 t/s (+30%), 4090 76,4 → 101,3 (+32%) |
| próbkowanie na GPU | `GPU_VERIFY=1` działa | fork traci 7–13% przy T=1 (qwen-warp nie traci) | brak dokładnego próbkowania spekulacyjnego na GPU w ścieżce CUDA forka, nie ograniczenie sprzętu | NVIDIA +7…13% do odzyskania (K-004) |
| natywne formaty (FP8/FP4) | FP8: RDNA4, CDNA3/4; MXFP4: CDNA4 | FP8: Ada, Hopper, Blackwell; NVFP4: Blackwell | 3090 i XTX bez FP8 | zakaz zmiany kwantu; dotyczy tylko wyboru kwantu w Enigmie |
| wątki i kafle per karta | wave32 (RDNA) vs wave64 (CDNA); LDS 64 KB, CDNA4 160 KB | warp 32; smem ~100 KB (sm_86/89/120), 228 KB (sm_90) | warianty FA/MMQ strojone pod gfx1100 nie pasują do CDNA ani NVIDIA | per karta +2…10% (`levers.md:40-42`: 48,5 → 56,9) |
| szybsza biblioteka atencji | FA w llama.cpp (rocWMMA), CK/aiter na CDNA | FA w llama.cpp (mma), FA3 Hopper, FA4 Blackwell | na RDNA3 nie ma FA3/FA4 | XTX FA83 +5,8% przy 128k |
| prefill INT8 (MMQ q8_1) | RDNA3 bez zysku INT8 nad FP16 | GeForce INT8 = 4 × FP16 (akum. FP32) | ścieżka INT8 to domyślna arytmetyka llama.cpp, nie zmiana kwantu | NVIDIA sufit 2,3 × XTX; niezmierzone (K-112) |
| cache prefiksów, lean reserve, chunk prefillu, profil po etapach | tak | tak | niezależne od architektury | jak na XTX |
| fuzja pod grafami | ~0 (LaunchCut, x54) | ~0 wg skill-io (`levers.md:43`) | – | 0 |

**Lekcja:** dźwignie bajtowe (spekulacja, głowica, `kvq`, cache) przenoszą się między firmami 1:1. Dźwignie kernelowe (warianty, PM4, kafle) trzeba stroić od nowa na każdą architekturę, bo różnią się wave32/64, LDS/smem i typami danych jednostek macierzowych.

## Dźwignie na Apple, Intel i Tenstorrent + czego brakuje naszemu silnikowi (2026-11-17)

**Stan upstream llama.cpp** (`9581154`, 2026-11-17, grep w `ggml/src`, klon w `~/kernel/zrodla/llama.cpp-upstream`). Op GATED_DELTA_NET (warstwy GDN Qwena) oraz SSM_CONV i FLASH_ATTN_EXT mają:
- CUDA/HIP, Metal, SYCL, Vulkan, OpenVINO i OpenCL;
- **backendu Tenstorrent i Gaudi nie ma.**

Upstream ma też `--backend-sampling` (`common/arg.cpp:2286`), czyli próbkowanie w grafie ggml.

**Jednostki i biblioteki:**
- **Apple:** `simdgroup_matrix` 8×8 (M1–M4), Neural Accelerators w rdzeniu GPU (M5, Metal 4 tensor API); threadgroup memory 32 KB; MLX/MLX-LM.
- **Intel:**
  - XMX (Xe-HPG 1024-bit, Xe2/Xe3 2048-bit; INT8 = 2 × FP16);
  - SLM 64–128 KB na Xe-core, sub-group 16/32;
  - oneAPI/SYCL (oneMKL, oneDNN), Vulkan z `VK_KHR_cooperative_matrix`, OpenVINO;
  - IPEX-LLM [INFERENCE: status projektu sprawdzić przed użyciem].
- **Tenstorrent:** Tensix z kafelkiem 32 × 32, 1,5 MB SRAM L1 na rdzeń, NoC, formaty BFP8/BFP4 (`bfloat8_b`, `bfloat4_b`); stos TT-Metalium → TT-NN → tt-transformers / fork vLLM; kompilator tt-mlir.

| dźwignia skill-io | Apple | Intel | Tenstorrent |
|---|---|---|---|
| grafy dekodu | Metal: bufory komend kodowane co token, brak „replay” jak w CUDA; MLX `mx.compile` | grafy SYCL (`ext_oneapi_graph`); skill-io B70: 14,4 → 28,4 t/s z grafami XPU (`levers.md:22`) | Metal Trace (zapis i odtwarzanie programu) = odpowiednik grafów, w tt-transformers obowiązkowy dla dekodu |
| MTP + przycięta głowica | działa (backend-agnostyczne); **na M1–M4 tylko n1–2** (weryfikacja ograniczona obliczeniami, [[skill-io-sufity]]); M5 n3–4 | działa; B70 przycinanie +27% (`levers.md:27`) | brak MTP dla Qwen3.8 w tt-transformers [INFERENCE] |
| weryfikacja atencją dekodu (`kvq`) | Metal ma FA z KV q4_0 (87 trafień w grepie, ścieżka `vec` dla małych N) — sprawdzić, czy N=5 idzie ścieżką dekodu | SYCL: FA z KV q4_0 tylko częściowo (2 trafienia); Vulkan: brak trafień → ryzyko wolnej weryfikacji | własny kernel atencji w TT-NN |
| próbkowanie na GPU | `--backend-sampling` w upstream [INFERENCE: działa na Metal] | j.w. (SYCL/Vulkan) | na urządzeniu w tt-transformers |
| wątki i kafle per karta | simdgroup 32, TG mem 32 KB: kafle z CUDA nie pasują | sub-group 16 vs 32, SLM; skill-io: WG=1 w kernelu SYCL kosztował × 7,8 (`gotchas.md:42`), 4096 → 1024 wątków +17% | siatka rdzeni 8 × 10 / 13 × 10, podział macierzy na rdzenie (sharding L1) |
| prefill INT8 | M1–M4 bez zysku (FP16 = INT8); M5 Neural Accelerators [INFERENCE: INT8 nie potwierdzone] | XMX INT8 = 2 × FP16 (MMQ/DPAS) | BFP8 / LoFi = szczyt 664 (p150) |
| fuzja | ~0 pod grafami (ogólne) | 3 × 0% na B390 (`levers.md:43`) | fuzja op-ów w TT-NN ma znaczenie, bo każde wyjście idzie przez DRAM/L1 [INFERENCE] |
| cache prefiksów, cachesave, lookup | backend-agnostyczne (server/common) | j.w. | w forku vLLM: prefix caching vLLM |
| pamięć | pamięć zunifikowana: limit wired, MemAvailable kłamie (`methodology.md:46`) | iGPU: to samo; dyskretne ≥ 1,5 GB zapasu, bo livelock na Arc (`levers.md:58`) | DRAM 12–32 GB na chip, n300 = 2 × 12 |

**Czego brakuje naszemu silnikowi (fork topka/Enigma), żeby ruszył i wygrywał:**

| element naszego silnika | gdzie dziś | Apple (Metal) | Intel (SYCL / Vulkan) | Tenstorrent |
|---|---|---|---|---|
| baza: Qwen3.8 (GDN + MTP) w llama.cpp | upstream | **działa** (ops są) | **działa** (ops są) | **brak backendu ggml.** Potrzebny port modelu do tt-transformers (GDN, MTP) i konwersja wag na BFP4/BFP8, czyli zmiana formatu wag (u nas zakazane jako dźwignia prędkości) |
| `kvq` (weryfikacja N ≤ 16 jako dekod) | ggml-cuda (CUDA + HIP) | port do `ggml-metal` (MSL) | port do `ggml-sycl` i Vulkan (GLSL) | n/d |
| FA D256 wariant 83, PM4, lean reserve | HIP / CUDA | n/d (PM4 tylko AMD); odpowiednik: strojenie kafli FA Metal | strojenie FA SYCL/Vulkan pod XMX | n/d |
| dokładne próbkowanie spekulacyjne (`GPU_VERIFY`) | łatki w `common/sampling.cpp`, `speculative.cpp` na ops ggml | sprawdzić na Metal [INFERENCE: powinno działać, jeśli ops są] | j.w. | n/d |
| słownik draftu 64k, lookup W16, cachesave | common/server | działa bez zmian [INFERENCE] | działa bez zmian [INFERENCE] | trzeba przepisać w forku vLLM |
| harness i bramki (spec_sweep, bench.py, igły) | OpenAI API | działa | działa | działa (serwer vLLM) |

**Lekcja:**
- Najtaniej rozszerzyć się na Apple i Intela, bo upstream już tam działa. Brakuje „tylko” naszych kerneli `kvq` i strojenia FA na Metal i SYCL/Vulkan.
- Tenstorrent i Gaudi to inny silnik (TT-NN / vLLM), czyli osobny projekt, a nie port.
- Testu na tych kartach nie mamy jak zrobić: brak sprzętu, a na Vast nie ma Apple/Intel/Tenstorrent. Zostaje wiedza i przygotowany kod.

## Powiązane
- [[skill-io-przeglad]]
- [[skill-io-sufity]]
- [[KOLEJKA-TESTOW]]
- [[2026-11-08-fa-d256-prefill]]
- [[final-recipes-nvidia]]
- [[2026-11-14-k002-k003-k013-xtx]]
