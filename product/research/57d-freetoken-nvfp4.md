# 57d. FreeToken (@Andy_ShuoYang) i NVFP4: co z tego dla RDNA3

Źródło: bio badacza (współtwórca GSQ-RCO): „@Andy_ShuoYang (FreeToken / NVFP4)”. Czytałem pracę arXiv 2608.16157 (całą), repo `FlashML-org/FreeToken` (płytki klon `cc4aa08`, 2026-10-20, w `~/qwen-opt/research/freetoken`) z kodem NVFP4 (CPU `cpu_moe/kernels/nvfp4.cpp`, łata do ggml, `kernel/aot_models.py`) i `docs/install_amd.md`. Wpisy X znam tylko ze snippetów wyszukiwarki. Bez GPU. W KB już są: `wiki/nvidia/nvfp4.md`, symulacja skali globalnej (`eksperymenty/2026-10-16-nvfp4-skala-globalna-sim.md`), raport 09 (5060 Ti) i 39f. Tu dopisuję tylko nowe rzeczy.

## 1. Co to jest

**FreeToken** to otwarty (Apache-2.0) silnik serwujący **MoE z offloadem ekspertów** na sprzęt konsumencki: od laptopa z 8 GB po RTX PRO 6000. Pełna pula ekspertów leży w RAM hosta, a VRAM jest elastycznym cache LRU ekspertów. Do tego aplikacja desktopowa (Windows/Linux, flashml.ai), API OpenAI i Anthropic oraz >20 modeli MoE. „NVFP4” w bio oznacza, że FreeToken serwuje głównie checkpointy NVFP4 (NVIDIA ModelOpt, RedHatAI, RadixArk) i ma własne ścieżki NVFP4 na GPU (Marlin W4A16, b12x na Blackwell, łata do ggml MMVQ) oraz na CPU (AVX2/AVX-512/VNNI). **Nie jest to nowy format ani nowa metoda kwantyzacji.**

## 2. Kto / skąd

Shuo Yang (doktorant 2. roku na UC Berkeley, Sky Computing Lab / LMSYS, <https://andy-yang-1.github.io/>). Współautorzy: Kurt Keutzer, Song Han (MIT), Matei Zaharia, Ion Stoica i Chenfeng Xu (UT Austin). Organizacja na GitHubie: FlashML-org. Repo: ~14.7k gwiazdek. Najwięcej commitów robi `jason-fxz` (Xiaoze Fan). Praca złożona 17.08.2026.

## 3. Jak działa technicznie

**Planowanie (praca §3):**

- **Prefill:** podwójny bufor całych warstw. Gdy GPU liczy warstwę *l*, przez PCIe płynie komplet ekspertów warstwy *l+1*, bo w długim prefillu i tak trafia się prawie w każdego eksperta. Prefill staje się ograniczony przez PCIe: 64.4 GB puli w ~1.2 s na chunk 8k przy 52.7 GB/s.
- **Decode:** globalny LRU ekspertów, wspólny dla wszystkich warstw, z wpisami (warstwa, ekspert). Chybienia dzieli **polityka q\***: `q* = m·B_P/B_H`. *m* to liczba chybień, *B_P* to zmierzone pasmo PCIe, *B_H* to zmierzone pasmo kernela CPU. *q\** ekspertów ładuje się do cache i liczy na GPU, reszta liczy się na CPU równolegle. Zawsze jest ≥ 1 wypełnienie cache. Wyniki częściowe są sumowane dokładnie, bez aproksymacji.
- **Graf:** cała logika cache (deduplikacja, klasyfikacja, wybór K ofiar LRU jednym przebiegiem, przepisanie ID na sloty) działa w kernelu GPU wewnątrz przechwyconego grafu CUDA. Gałąź CPU też jest w grafie: host-function node plus pinned I/O.
- **„Semantic anchors”:** checkpointy stanu rekurencyjnego (GDN/KDA) zakotwiczone na granicach tokenów specjalnych (koniec `<think>`, tool call, tool output, tura). Gdy harness agenta wytnie myślenie albo stare wyniki narzędzi, wznowienie startuje z najbliższej kotwicy. W kodzie (`kvcache/hybrid_radix_cache.py:56-60`) widzę radix tree z jednym snapshotem GDN na węźle i snapshoty na granicach ×`CHUNK_SIZE`, wyrównanych do stron. Miejsca, gdzie kotwice ustawia się na tokenach specjalnych, grepem nie znalazłem `[niezweryfikowane w kodzie]`.
- **Elastyczna pamięć:** podział VRAM między KV a sloty ekspertów zmienia się w bezpiecznych punktach bez restartu. Format FTW układa wagi od razu w layout banków, a pinowanie następuje po wczytaniu.
- **PLE na NVMe** (wpis X 2095579850367262872, snippet): token dotyka tylko 16 wierszy tablicy PLE 51 GB, więc FreeToken czyta je z NVMe (0.1–0.4 ms) `[niezweryfikowane]`. Mia (57c) robi to samo z tablicą n-gram 26.8 GiB.

**NVFP4 w kodzie:**

- **Format:** kody e2m1 (2 na bajt, młodszy nibble pierwszy), skala na blok **16** w fp8-e4m3, skala globalna fp32 **per wiersz wyjściowy** (`nvfp4.cpp:8-12`). Razem 4 + 8/16 = **4.5 bpw** plus pomijalny fp32 na wiersz. Czyli tyle samo bajtów co Q4_0 (blok 32, skala fp16).
- **Marlin / b12x:** przy przepakowaniu skala globalna jest „wtapiana” w wektory alpha na GPU (`aot_models.py:94-97`).
- **CPU W4A8:** e2m1 × 2 to liczby całkowite {0, 1, 2, 3, 4, 6, 8, 12}, więc nibble → int8 przez LUT (`_mm_shuffle_epi8`), a potem iloczyn VNNI z int8 aktywacjami kwantyzowanymi per blok 16 (absmax/127). Współczynnik ×0.5 siedzi w skali (`nvfp4.cpp:46-50,153-177`). To ten sam trik, którego ggml używa dla MXFP4/NVFP4 (`kvalues_mxfp4`) w `ggml_vec_dot_nvfp4_q8_0`.
- **Łata do ggml (`kernel/csrc/ggml/freetoken.patch`, `VERSION`):** MMVQ NVFP4 mnoży wynik przez **per-ekspertową skalę fp32 w epilogu** (`x_scale[channel_x * stride]`, `gate_scale`). Natywny FP4 MMA jest domyślnie wyłączony (`GGML_CUDA_FP4_MMA`, tylko sm_120a). Na kartach bez FP4 NVFP4 to więc zwykły **LUT → int8 → dp4a**.
- **ROCm:** jest eksperymentalnie, z RDNA3 `gfx1100-1103` i RDNA4 na liście, ROCm 7.14, PyTorch 2.11. NVFP4 Marlin/b12x, FlashInfer i sgl_kernel **nie działają** na ROCm, są tylko fallbacki (`docs/install_amd.md`, issue #541).

## 4. Liczby (praca, pomiary autorów, tylko MoE z offloadem)

| Model | Sprzęt | FreeToken | Najlepszy baseline | Uwagi |
|---|---|---|---|---|
| Qwen3.6-35B-A3B BF16 | RTX 5090 (serwer, 6 wątków CPU) | 77–83 t/s | 1.8–2.3× mniej | 4 obciążenia agentowe |
| DeepSeek-V4-Flash MXFP4 | RTX 5090 | 22–25 t/s | 1.5–1.9× mniej | |
| Qwen3.6-35B NVFP4 | RTX 4060 Laptop 8 GB, PCIe x8 | 39.3 t/s | 1.8× mniej | |
| Qwen3.6-35B BF16 | **RTX 3090** (PCIe4, B_H 56.7 GB/s) | — | FreeToken **1.3×** baseline | wartość bezwzględna tylko na wykresie |
| GLM-5.2 753B NVFP4 | RTX PRO 6000 96 GB | 14.9 t/s | llama.cpp 7.3 | TTFT 7.5 vs 7.8 s |

Dalsze wyniki:

- Miss rate przy cache = 37% puli Qwen3.6: LRU 16%, KTransformers 41%, statyczny podział llama.cpp 62%.
- Wyłączenie double buffering: prefill −19…−26%.
- Najgorszy TTFT < 44 s; baseline'y > 150 s (llama.cpp 232 s).
- Wpis X (snippet): „3–4× szybszy decode i 6–30× szybszy prefill niż Ollama” `[niezweryfikowane]`.

Brak liczb dla modeli dense i brak liczb jakości (formaty są bitowo identyczne między silnikami).

## 5. Licencja / dostępność

Kod: Apache-2.0, PyPI `freetoken`, aplikacja desktopowa na flashml.ai. Wagi pochodzą od dostawców checkpointów (NVIDIA, RedHatAI, RadixArk). Część kodu skopiowana z SGLang, vLLM, FlashInfer, FLA i llama.cpp (ggml w `kernel/csrc/ggml`).

## 6. Co z tego dla nas (XTX bez FP4, 3090 bez FP4, Qwen3.8-27B dense)

Rdzeń FreeToken, czyli offload ekspertów i q\*, **nie dotyczy** Qwen3.8-27B dense ani Orki, bo całe wagi mieszczą się w 24 GB. Przenośne są trzy rzeczy:

| # | Pomysł | Dla | Zysk (szacunek) | Wysiłek | Uwagi |
|---|---|---|---|---|---|
| 1 | **Kotwice checkpointów GDN na granicach `</think>` / tool call / tool output** zamiast (albo obok) checkpointów co N tokenów | XTX, 3090, Orca w omp | TTFT tury agenta po wycięciu thinkingu: zamiast re-prefillu tysięcy tokenów wznowienie od kotwicy. Przy ~2–4k t/s prefillu i 2–8k tokenów to 1–3 s na turę `[INFERENCE]`. Koszt: 94–180 ms na checkpoint (R35, 32b) | 1–2 dni (`server`: przy tokenie specjalnym wymusić `slot` checkpoint; LRU checkpointów) | Bezstratny. Najpierw zmierzyć na logach omp, jak często szablon Qwen3.8 obcina historię (`[niezweryfikowane]`, że obcina reasoning) |
| 2 | **Mikroskalowanie typu FP4 w formacie int dla KV: blok 16 + skala 8-bit (e4m3 albo ue8m0/int8 log)** zamiast q4_0 (blok 32 + fp16) | XTX (KV q4_0), 3090 | **te same 4.5 bpw**, czyli 0 kosztu w pasmie. Drobniejsze bloki zwykle obniżają błąd kwantyzacji K, co daje wyższą jakość przy tym samym rozmiarze `[INFERENCE]` | CPU-sim 0.5 dnia (KLD na zrzutach K/V); kernel FA dequant 2–3 dni | Najpierw symulacja na prawdziwych K/V jak w 2026-10-16. Dekodowanie: 16-elem. LUT/`v_dot4` lub mnożenie skali w FA. Jeśli sim < 10% redukcji błędu, odrzucić |
| 3 | **Skala globalna fp32 per wiersz/tensor wtopiona w epilog MMVQ** (jak łata FreeToken do ggml) | ścieżka NVFP4 w GGUF | nasza sim: −22–35% błędu wag NVFP4, ale **NVFP4 RTN nadal o 12–17% gorszy od Q4_0** | 0.5 dnia | Ma sens tylko wtedy, gdy będziemy wczytywać **QAD** NVFP4 od NVIDIA (`nvidia/Qwen3.8-27B-NVFP4`, 20.15 GB), bo QAD to inna jakość niż RTN. Test: KLD QAD-NVFP4→GGUF vs UD-Q4_K_XL na CPU. Na XTX dekodowanie e2m1 → int8 LUT → `v_dot4_i32_i8` kosztuje tyle co MXFP4 w upstream |
| 4 | LUT e2m1×2 → int8 + iloczyn int8 (W4A8) | XTX/3090 | 0 dla nas: nasze MMVQ już robi int8 dp4a na Q4_K; to tylko potwierdza, że FP4 bez sprzętu = int4 z LUT | — | Nie dotyczy, chyba że pkt 3 przejdzie |
| 5 | Prefill z double-bufferingiem całych warstw, q\* | — | — | — | Nie dotyczy (dense, mieści się w VRAM). Wraca, jeśli kiedyś Qwen3.8-Flash-Next 125B-A5B na XTX + RAM; wtedy FreeToken ma **eksperymentalny gfx1100** i warto go po prostu uruchomić jako baseline |

## 7. Do bazy wiedzy

- FreeToken (Berkeley/MIT, Shuo Yang, Stoica, Zaharia, Song Han): silnik MoE z offloadem; Apache-2.0; arXiv 2608.16157.
- Polityka q\* = m·B_P/B_H: chybienia ekspertów dzielone między wypełnienie cache przez PCIe a liczenie na CPU, według zmierzonych pasm.
- Globalny LRU ekspertów: miss 16% vs 62% statycznego podziału llama.cpp przy 37% puli w VRAM (Qwen3.6-35B).
- Logika cache ekspertów działa na GPU w grafie CUDA; gałąź CPU też w grafie (host node).
- Kotwice checkpointów GDN na granicach tokenów specjalnych (think/tool) pod agentowe edycje kontekstu. Kandydat do naszego `server`.
- NVFP4 = e2m1 + e4m3 na 16 + fp32 per wiersz = 4.5 bpw, tyle co Q4_0. Bez sprzętu FP4 sprowadza się do LUT → int8 → dp4a/VNNI.
- FreeToken łata ggml MMVQ: per-ekspertowa skala NVFP4 w epilogu; natywny FP4 MMA wyłączony domyślnie.
- FreeToken ma eksperymentalny ROCm (gfx1100–1103, gfx1200/1201, ROCm 7.14), bez ścieżek NVFP4 Marlin/b12x.
- Tablice PLE/n-gram (Qwen3.8-Flash-Next) czytane z NVMe per token, 16 wierszy/token `[niezweryfikowane]`.
- CompWatch: dodane `FlashML-org/FreeToken` (tier B).

## 8. Źródła

- <https://arxiv.org/abs/2608.16157> (HTML v1: §3.1–3.2, §4.1–4.2, §5, tab. 1)
- <https://github.com/FlashML-org/FreeToken> (`python/freetoken/kernel/csrc/cpu_moe/kernels/nvfp4.cpp`, `kernel/aot_models.py`, `kernel/csrc/ggml/freetoken.patch`, `kvcache/hybrid_radix_cache.py`, `docs/install_amd.md`)
- <https://github.com/FlashML-org/FreeToken/issues/541> (AMD roadmap)
- <https://www.flashml.ai/changelog/>
- <https://andy-yang-1.github.io/>
- <https://www.infoq.com/news/2026/08/freetoken-local-inference>
- X: <https://x.com/Andy_ShuoYang/status/2090856976880472439>, <https://x.com/Andy_ShuoYang/status/2090856978428145761>, <https://x.com/Andy_ShuoYang/status/2095579850367262872> (tylko snippety)
