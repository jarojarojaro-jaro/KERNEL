---
typ: platforma
tags: [platformy, intel, sycl, vulkan, spekulacja]
aktualizacja: 2026-11-28
zrodlo: wiki/karty/arc-b580-i-mac.md; wiki/testy/skill-io-sufity.md:145-165; wiki/optymalizacje/skill-io-dzwignie.md:85-115; ~/KERNEL/product/research/30-intel-apple-dostep.md:7,20-25,43-49,149; wiki/ekosystem/b70-cookbook.md; wiki/metody/skill-io-pulapki.md:66; wiki/optymalizacje/prog-draftu-od-kosztu-wiersza.md:22; wiki/modele/sensenova-loop-9b.md:35
status: aktualne
---
# Intel Arc B580 i Xe2 (SYCL, Vulkan)

**Arc B580 (Xe2, 12 GB, 456 GB/s) ma sufit dekodu Qwen3.8-27B z MTP 82 t/s, ale się w nim nie mieści Q4_K_M. Na Intelu llama.cpp zostawia ok. 3,6 × prędkości względem vLLM XPU. Własnego pomiaru nie mamy (stan 2026-11-28).**

## Sprzęt i sufity
Sufity: Qwen3.8-27B Q4_K_M, KV q4_0, MTP n4, a = 3,2 ([[skill-io-sufity]], 2026-11-17).

| karta | VRAM | GB/s | FP16 / INT8 TFLOPS | plain 2k | MTP 2k | prefill 4k INT8 | 262k? |
|---|---|---|---|---|---|---|---|
| Arc A770 | 16 | 560 | 131 / 262 | 35 | 101 | 2519 | nie |
| **Arc B580** | 12 | 456 | 116,5 / 233 | 28 | 82 | 2240 | nie |
| Arc Pro B60 (krzem B580) | 24 | 456 | brak w `karty.json` | – | – | – | – |
| Arc Pro B70 | 32 | 608 | 183,5 / 367 | 38 | 110 | 3528 | tak |
| Lunar Lake 140V (iGPU) | ~16 | 136,5 | 33,5 / 67 | 8 | 25 | 644 | nie |

- XMX daje INT8 = 2 × FP16, więc prefill ma sufit jak NVIDIA, a dekod niższy niż XTX.
- Jedyny pomiar 1:1 jest cudzy: B70, Q4_K_M, llama.cpp 25,0 t/s, czyli 66% sufitu bez spekulacji. Ten sam model w vLLM XPU (EXL3 4 bpw) robi 91,2 t/s (skill-io `README.md:31`).
- Sufit dla Loop-9B / Qwen3.8-27B na B580: 59 / 28 t/s bez spekulacji ([[sensenova-loop-9b]]).

## Dzień pierwszy
1. Dostęp: godzinowego Arca nie ma nigdzie (Vast 0 ofert `gpu_arch=intel`). Do wyboru GigaGPU B60 za £129/mies. (root) albo zakup B580 (~€270 używany), który zwraca się po ok. 2 mies. ([[arc-b580-i-mac]], R30:7,20-25).
2. Dwa buildy: `-DGGML_SYCL=ON` (oneAPI, Level Zero) i `-DGGML_VULKAN=ON`. Mierzymy oba (R30:49).
3. `test-backend-ops` dla TOP_K, GET_ROWS, SUM_ROWS, ARGSORT, GATED_DELTA_NET, SSM_CONV i FLASH_ATTN_EXT na obu backendach. Opy GPU verify są w `ggml-sycl` i `ggml-vulkan` (R30:149).
4. Model: 12 GB nie mieści Q4_K_M (16,6 GB), więc bierzemy kwant dobrany do pojemności (IQ3_XXS / IQ3_S jak w Enigmie 16 GB) albo MoE.

## Kolejność optymalizacji
1. **Grafy SYCL (`ext_oneapi_graph`):** cudzy pomiar B70 14,4 → 28,4 t/s z grafami XPU (skill-io `levers.md:22`).
2. **Spekulacja MTP z przyciętą głowicą:** cudzy pomiar B70 +27% z samego przycięcia (`levers.md:27`). DFlash2 + TensorFold: 128 t/s z wyjściem bajt w bajt ([[b70-cookbook]]).
3. **Próg draftu `p_min` 0,6 na SYCL** (reguła Straty, [[prog-draftu-od-kosztu-wiersza]]). Brak naszego pomiaru.
4. **Rozmiary work-group:** WG = 1 w kernelu kopiowania kosztował × 7,8, a zejście z 4096 do 1024 wątków dało +17% ([[skill-io-pulapki]]).
5. **FA z KV q4_0:** SYCL ma ją częściowo (2 trafienia w grepie), Vulkan wcale, więc weryfikacja może iść wolną ścieżką. Port `kvq`. Brak naszego pomiaru.
6. **Fuzje** pod grafami: 3 × 0% na B390 (`levers.md:43`). Robić na końcu albo wcale.

Lookup W16 i słownik draftu 64k są w common/server i przenoszą się bez zmian [INFERENCE]. `GUMBEL_MAX` ma tylko CPU i CUDA.

## Testy
`test-backend-ops` (oba backendy), `gate_chat.py` (md5 T=0 z drafterem i bez), `spec_sweep.py`, `copy_bench.py`, `long_bench.py`, `needle.py --tokens <c>`, `wall.py`, `kld_gate.py compare`, bateria dokładnych odpowiedzi z [[b70-cookbook]]. Plus `doctor.py`-podobna kontrola hosta: sterownik, Level Zero, zapas VRAM.

## Kiedy topka jest gotowa
- Wybrany backend (SYCL albo Vulkan) z pełnym stosem: spekulacja + lookup + KV q4 + maksymalny kontekst z igłami 5/5 przy 95% głębokości.
- md5 T=0 z drafterem = bez. Parytet zapisany przy każdej liczbie ze spekulacją (wzór B70: EXL3 + MTP3 zmienia odpowiedź greedy w 27% zadań).
- Wpis w [[TOPKI]] i [[REKORDY]] w tej samej turze co pomiar.

## Pułapki
- Livelock na Arc bez ≥ 1,5 GB zapasu VRAM (`levers.md:58`).
- Domyślny sub-group 16 vs 32. Kafle z CUDA i HIP nie pasują.
- Jeden strumień na dwóch kartach daje tylko 1,3–1,5 ×, a dwa serwery dają 2 × ([[b70-cookbook]]).
- Bez parytetu spekulacja „szybka” może zmieniać odpowiedzi.

## Rodzaje modeli
- Dense 27B: tylko kwant poniżej Q4 na 12 GB.
- MoE (Inkling IQ3_S 11,6 GB, Qwen3.6-35B z `--n-cpu-moe`): najlepszy kandydat na B580 [INFERENCE].
- Ternary Bonsai Q2_0 (5,99 GB): wymaga portu prism na SYCL. Brak naszego pomiaru.

Szczegóły rodzajów: [[rodzaje-modeli]].

## Powiązane
- [[arc-b580-i-mac]]
- [[b70-cookbook]]
- [[skill-io-dzwignie]]
- [[lekcja-dostep-intel-apple]]
- [[TOPKI]]
