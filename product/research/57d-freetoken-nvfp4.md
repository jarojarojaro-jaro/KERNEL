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

## 9. Dodatek 2026-10-21: KV blok 16 + skala 8-bit vs q4_0 (pomysł #2)

**Status: niewykonane, bo nie mamy zrzutów K/V.**

- `kb search "kv dump"` nic nie zwraca. W `~/qwen-opt` i `~/KERNEL` nie ma plików z K/V: `prose-accept/*.npz` to cechy akceptacji draftów, nie K/V. Lokalnie są tylko GGUF-y (bez BF16 safetensors 27B), a na hoście nie ma numpy.
- Zgodnie z poleceniem przerywam na tym etapie. **Jak zdobyć zrzuty (CPU, ~30–60 min):**
  1. `cpuheavy --quiet cmake --build` CPU-only `llama-eval-callback` z `~/wt/topka-int/examples/eval-callback` (osobny katalog build, nie współdzielony worktree).
  2. Zmienić callback, żeby zapisywał surowe fp32 tensorów `Kcur-<il>` (po RoPE) i `Vcur-<il>` dla 16 warstw pełnej uwagi (4 głowy KV × 256) do `.bin` oraz `Qcur-<il>` do metryki uwagi.
  3. Uruchomić `-ngl 0 -c 2048` na UD-Q4_K_XL dla 3 promptów (proza E0, kod, chat), po ~1–2k tokenów każdy.
  4. Skrypt (numpy w venv): q4_0 (blok 32, skala fp16, symetryczny −8..7) kontra „q4_b16” (blok 16, skala e4m3 oraz int8-log2, te same 4.5 bpw). Metryki: MSE/rel-err rekonstrukcji K i V, błąd logitów `QKᵀ/√d` i KL softmaxu uwagi per głowa, osobno dla K i V.
  5. Kryterium: wdrażać tylko przy spadku błędu uwagi (KL) o ≥ 10%.
- Werdykt ≥ 10%: **nieznany** `[niezweryfikowane]`.

## 10. Dodatek 2026-10-21 (2): pomiar KV blok 16 + skala 8-bit vs q4_0 na prawdziwych K/V

**Setup (CPU, bez GPU, bez pobierania):**

- Osobny worktree `~/qwen-opt/research/kvdump-wt` (topka-int `cf927413b`).
- `examples/eval-callback` przerobiony na zrzut fp32 `Qcur/Kcur/Vcur` po RoPE i normie. Build CPU przez `cpuheavy`, 2 wątki.
- Model `~/models/Qwen3.8-27B-UD-Q4_K_XL.gguf`, 16 warstw pełnej uwagi (3, 7, …, 63), Hq = 24, Hk = 4, dim 256.
- Dwa prompty: proza (1054 tok.) i kod C++ (1377 tok.).
- Skrypt `kvq_compare.py`: symulacja kwantyzacji w numpy; KL uwagi kauzalnej z GQA (tylko K~) i błąd wyjścia uwagi (K~ i V~ naraz).

**Formaty (wszystkie 4.5 bpw):**

- `q4_0`: ggml, blok 32, skala fp16;
- `b16_e4m3`: blok 16, kody int4 jak w q4_0, skala e4m3 względem globalnej fp32 per (warstwa, głowa);
- `b16_u8`: blok 16, skala uint8 liniowo względem maksimum per (warstwa, głowa);
- `nvfp4`: blok 16, kody e2m1, skala e4m3 i skala globalna.

| prompt | format | relMSE K | relMSE V | KL uwagi | błąd wyjścia | ΔKL vs q4_0 |
|---|---|---|---|---|---|---|
| proza | q4_0 | 1.079e-2 | 1.072e-2 | 1.835e-2 | 8.93e-3 | 0 |
| proza | b16_e4m3 | 7.61e-3 | 7.75e-3 | 1.384e-2 | 6.45e-3 | **−24.6%** |
| proza | b16_u8 | 7.34e-3 | 7.52e-3 | 1.242e-2 | 5.90e-3 | **−32.3%** |
| proza | nvfp4 | 8.69e-3 | 8.63e-3 | 1.662e-2 | 7.26e-3 | −9.4% |
| kod | q4_0 | 1.091e-2 | 1.069e-2 | 1.977e-2 | 8.38e-3 | 0 |
| kod | b16_e4m3 | 7.69e-3 | 7.75e-3 | 1.519e-2 | 6.12e-3 | **−23.1%** |
| kod | b16_u8 | 7.42e-3 | 7.51e-3 | 1.362e-2 | 5.63e-3 | **−31.1%** |
| kod | nvfp4 | 8.67e-3 | 8.65e-3 | 1.828e-2 | 7.05e-3 | −7.5% |

b16_e4m3 i b16_u8 mają niższe KL niż q4_0 w **16/16 warstw** na obu promptach. nvfp4 wygrywa w 10/16.

**Werdykt: tak, KL uwagi spada o ≥ 10% przy tych samych 4.5 bpw.** Wariant e4m3 daje −23…−25%, wariant uint8 −31…−32%. Prawdziwy NVFP4 (e2m1) daje tylko −7…−9%, poniżej progu. Zysk bierze się z bloku 16 i int4, nie z kodów FP4.

**Zastrzeżenia:**

1. Skala globalna per głowa liczona po całej sekwencji jest niekauzalna. W prawdziwym cache trzeba ją ustalić z góry (kalibracja per warstwa/głowa) albo per wiersz (per token × głowa, 256 elementów), co kosztuje +32 bity na 256 elementów, czyli +0.125 bpw. Wtedy zysk może być mniejszy `[INFERENCE]`.
2. Tylko 2 prompty po ~1k tokenów i wagi Q4_K_XL. KL dotyczy pojedynczej warstwy uwagi, nie KLD całego modelu.
3. Przed kernelem trzeba zmierzyć KLD/PPL end-to-end z symulowanym formatem (np. fake-quant K/V w CPU) oraz wariant z globalem per wiersz.

**Następny krok:** wariant „per-row global” w `kvq_compare.py` (30 min CPU). Jeśli nadal ≥ 10%, zaprojektować typ KV `q4_b16` dla FA (dequant: int4 × u8 × fp32 per wiersz). Wysiłek 2–3 dni na XTX.

## 11. Dodatek 2026-10-21 (3): warianty kauzalne (wdrażalne w cache)

Skrypt `~/qwen-opt/research/kvdump-wt/kvq_causal.py`, te same zrzuty co w §10. Warianty:

- `row_*`: skala globalna fp32 per wiersz (token × głowa KV, 256 elementów), **4.625 bpw**;
- `calib_*`: stała skala per (warstwa, głowa KV) skalibrowana na **drugim** prompcie (proza ↔ kod), skale obcinane do zakresu kodu, **4.5 bpw**.

| eval / kalibracja | format | relMSE K | relMSE V | KL uwagi | błąd wyjścia | ΔKL vs q4_0 | warstwy lepsze |
|---|---|---|---|---|---|---|---|
| proza / kod | q4_0 | 1.079e-2 | 1.072e-2 | 1.835e-2 | 8.93e-3 | 0 | – |
| proza / kod | row_e4m3 | 7.55e-3 | 7.70e-3 | 1.326e-2 | 6.23e-3 | **−27.7%** | 16/16 |
| proza / kod | row_u8 | 7.33e-3 | 7.47e-3 | 1.240e-2 | 5.88e-3 | **−32.4%** | 16/16 |
| proza / kod | calib_e4m3 | 7.61e-3 | 7.77e-3 | 1.377e-2 | 6.40e-3 | **−24.9%** | 16/16 |
| proza / kod | calib_u8 | 7.34e-3 | 7.53e-3 | 1.246e-2 | 5.95e-3 | **−32.1%** | 16/16 |
| kod / proza | q4_0 | 1.091e-2 | 1.069e-2 | 1.977e-2 | 8.38e-3 | 0 | – |
| kod / proza | row_e4m3 | 7.63e-3 | 7.70e-3 | 1.470e-2 | 6.01e-3 | **−25.7%** | 16/16 |
| kod / proza | row_u8 | 7.41e-3 | 7.47e-3 | 1.361e-2 | 5.60e-3 | **−31.1%** | 16/16 |
| kod / proza | calib_e4m3 | 7.69e-3 | 7.76e-3 | 1.533e-2 | 6.17e-3 | **−22.5%** | 16/16 |
| kod / proza | calib_u8 | 7.42e-3 | 7.52e-3 | 1.364e-2 | 5.65e-3 | **−31.0%** | 16/16 |

**Werdykt: próg ≥ 10% spełniony we wszystkich wariantach kauzalnych**, w każdej warstwie. Kalibracja przenosi się między prozą a kodem prawie bez straty: −0.1…−3 p.p. wobec skali per wiersz.

**Zastrzeżenie do wariantu u8:** symulacja zachowuje znak skali bloku (ggml-style `d = m/−8`, gdzie *m* to element o największym module ze znakiem), a samo uint8 znaku nie ma. Do wdrożenia są więc dwie opcje:

- **e4m3**, które ma bit znaku (zmierzone: −22.5…−27.7%);
- u8 z kodami symetrycznymi `amax/7` (−7..7), czyli bez znaku `[niezweryfikowane]`; prawdopodobnie między e4m3 a u8.

**Rekomendacja: `calib_e4m3`** (4.5 bpw, zmierzone −22…−25% KL, rozmiar bloku identyczny z q4_0).

### Notatka projektowa: typ KV `q4_b16` dla FA na gfx1100 (bez implementacji)

**Layout.** Blok 32 elementów, 18 B, **tyle samo co `block_q4_0`**:

```c
typedef struct { uint8_t s[2]; uint8_t qs[16]; } block_q4_b16; // s[0]: elem 0-15, s[1]: elem 16-31, e4m3
```

- Nibble jak w q4_0: bajt *j* low = element *j*, high = element *j+16*. Pod-blok 0 to młodsze nibble, pod-blok 1 starsze, więc istniejący `shift` w kernelu **sam wybiera skalę**: `s[shift != 0]`.
- Skala globalna fp32 per (warstwa, głowa KV) w osobnym małym tensorze, statycznym, skalibrowanym offline jak w §11, np. jako metadane GGUF albo plik obok. Rozmiar: 16 warstw × 4 głowy × 2 (K, V) × 4 B = 512 B.
- Strides, wyrównanie (`ggml_cuda_memcpy_1<…,2>`) i `n_ctx` × bajty bez zmian, więc budżet VRAM KV jest **identyczny** jak dla q4_0.

**KQ (`vec_dot_fattn_vec_KQ_q4_0`, `fattn-common.cuh:149-177`).**

- Dziś na każdy `int` (4 bajty, 8 nibbli, połowa wybierana `shift`): load, shift, and, `dp4a`, a potem `d_fp16 · (sumi·Q_d − 8/QI8_1·Q_sum32)`.
- W `q4_b16` dwie połówki bloku mają różne skale, więc korekta „−8” potrzebuje **sumy Q per 16**, a nie per 32. Dwie opcje:
  - (a) przy kwantyzacji Q (raz na kernel) zapisać `Q_ds` jako (d, sum_lo16, sum_hi16). Pętla wewnętrzna ma wtedy tyle samo instrukcji co q4_0; zamiast `v_cvt_f32_f16` jest odczyt bajtu e4m3 i konwersja przez LUT w LDS albo `v_cvt` przez bit-manipulację, ~3–4 VALU `[INFERENCE]`. Koszt: +1 float `Q_ds` na każdą iterację `k_KQ_0` na wątek, co przy D = 256 daje **+4…8 VGPR** `[INFERENCE]`;
  - (b) zostawić `Q_ds` i liczyć `dp4a(0x01010101, u)` w pętli: **+1 `v_dot4` na int**, 0 VGPR.
- Skala globalna jest stała per głowa, więc mnożymy przez nią **raz po pętli** (0 kosztu w pętli).
- Pętla KQ dla D = 256 przy 1 tokenie zapytania jest ograniczona pasmem (K 144 B/wiersz), więc +1 VALU na 8 elementów powinno się schować `[INFERENCE]`. Zacząć od (b), bo nie rusza VGPR.
- Uwaga: gfx1100 nie ma sprzętowego FP8 cvt, więc e4m3 → f32 to kilka VALU albo LUT 256 × f32 w LDS (1 KB). Tańszy byłby wariant u8 z kodami symetrycznymi (`v_cvt_f32_ubyte{0,1}`, 1 instrukcja), ale trzeba go najpierw zmierzyć (zob. zastrzeżenie).

**V (`dequantize_V_q4_0`, `:409-450`).**

- Zamiana `d = x[ib].d` na `d = g_head · e4m3(x[ib].s[shift])`; reszta (vsub4 i mnożenie half2) bez zmian.
- `sched_group_barrier` na HIP (`:422`) zostaje. Odczyt skali to bajt zamiast półsłowa, ten sam bufor bloku, bez dodatkowego VMEM.

**Zapis (set_rows / cpy f32 → q4_b16).** Per 16 elementów: *m* = element o największym module ze znakiem, `d = m/−8`, `s = e4m3(d/g)` (ze znakiem), kody `clip(floor(x/(s·g) + 8.5), 0, 15)`. Kalibracja *g*: `g = max_t |d| / 448` per (warstwa, głowa) na korpusie kalibracyjnym, z zapasem ×2 na outliery (do sprawdzenia, bo obcinanie ≥ 448 jest w symulacji).

**Plan i koszt.**

1. KLD/PPL całego modelu z fake-quant K/V na CPU (eval-callback, zapis zmodyfikowanego K/V), ~0.5 dnia.
2. Typ ggml + quantize + `vec_dot`/`dequantize_V` (wariant b), ~1.5 dnia.
3. Gate na XTX: KLD vs q4_0 (oczekiwany spadek) i t/s E0 ±1% (oczekiwane 0, bo te same bajty).

Razem **2–3 dni**. Zysk: jakość KV przy tym samym rozmiarze, bez zysku t/s.
