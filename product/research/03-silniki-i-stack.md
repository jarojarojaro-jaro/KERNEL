# 03: Silniki inferencji i stack technologiczny „aplikacji”

Stan na 2026-10-15. Metoda:
- **Web:** README, wydania i LICENSE na GitHubie, dokumentacja producentów, PyPI, arXiv, benchmarki.
- **Lokalne klony:** `~/research/Strata` (fetch 2026-10-15, HEAD `296b59d2`, tag `v0.1.44.1`) i `~/research/TensorFold` (HEAD `c7137bb3`, tagi `v1.0.11` i `v1.0.0-beta.6`).
- **Nasze wcześniejsze notatki:** `~/KERNEL/qwen-opt/research/{strata,tensorfold,repos}`.
- **Nasz fork:** `~/llama-master`, tylko odczyt.

Nic nie było budowane ani uruchamiane na GPU.

Oznaczenia:
- `[INFERENCE]` to wniosek, którego nie sprawdziłem w źródle.
- `[STALE?]` to źródło starsze niż 12 miesięcy.
- `[SEC]` to źródło wtórne (blog lub agregator), gdy pierwotnego nie znalazłem.
- Wielkości artefaktów zmierzyłem przez `gh api`, czyli z metadanych wydań, w dniu raportu.

---

## 1. TL;DR

1. **Bazą powinien zostać llama.cpp, ale jako cienki „overlay”, a nie twardy fork.** Upstream wydaje ok. 24 buildy `bNNNN` dziennie. Od tego miesiąca ma też linię semver (v0.7.0 z 2026-10-15). Nasz fork stoi na b11528 z 2026-10-09: 70 commitów, 69 plików, +11 401/−803 linii. W ciągu 6 dni upstream (143 commity) zmienił **33 z tych 69 plików**, w tym `mmvq.cu`, `mmq.cu`, `ggml-cuda.cu`, `gated_delta_net.cu` i `ggml-vulkan.cpp`. Twardy fork per architektura nie przetrwa takiego tempa bez stałego etatu na rebase.
2. **Własny runtime (Strata, TensorFold, hipfire) daje rekordy, ale tylko dla wąskiego zestawu modeli.**
   - TensorFold kwalifikuje 7 par model/platforma.
   - Strata to w praktyce silnik jednego modelu (Qwen3.8-Flash-Next) plus osobny driver Qwen3.6.
   - hipfire działa tylko na AMD.

   Nasz produkt obiecuje „dowolny model, dowolne GPU”, więc własny runtime ma sens najwyżej jako opcjonalny „turbo-silnik” dla 1–2 flagowych modeli, i to później.
3. **Upstreaming tylko ręcznie i selektywnie.** Polityka AI w llama.cpp zakazuje „automated commits or PR submissions (may result in contributor ban)” oraz pisanych przez AI opisów PR. Woli też prostsze zmiany („90% of the job”). Pętla agentowa nie może więc sama wysyłać PR-ów. Upstreamujemy ogólne poprawki, a ciasno strojone kernele per architektura trzymamy u siebie.
4. **Żaden silnik spoza rodziny ggml nie pokrywa NVIDIA + AMD + Intel + Apple na Windows, Linux i macOS jednym binarium.**
   - ExLlamaV3: Python i NVIDIA, ROCm wstępnie.
   - vLLM i SGLang: Linux, ciężkie.
   - mistral.rs: na Windows tylko CPU.
   - TensorRT-LLM: Windows wycofany.
   - MLX: tylko Apple.
   - ORT GenAI z Windows ML: format ONNX, a EP MIGraphX AMD „not supported for GenAI”.

   Jedynym kandydatem na drugi backend jest **MLX na Macu**: +21–87% decode względem llama.cpp Metal przy małych i średnich modelach.
5. **Dystrybucja.** Vulkan llama.cpp waży **31 MB** na Windows i nie potrzebuje runtime'u poza sterownikiem. CUDA to 147–254 MB binarki plus **373–404 MB** DLL runtime'u (sam `cublasLt64_13.dll` ma 470 MB po rozpakowaniu). ROCm to 183–654 MB na rodzinę gfx. Ollama ma przez to instalator 1,5 GB. Lemonade (AMD) ma **10 MB** i backendy dociąga po wykryciu sprzętu. Wzorzec dla nas: mały instalator z Vulkan/Metal/CPU, a paczki per vendor pobierane po detekcji.
6. **Rdzeń w Rust**, silnik jako osobny proces potomny (izolacja crashy, jak Jan 0.8.5). **GUI w Tauri 2**: 3–15 MB, minisign w updaterze, sidecar. Na Linuksie WebKitGTK sprawia problemy, więc tam najpierw TUI i CLI, GUI w drugiej kolejności. **TUI w ratatui.** Electron to sensowna alternatywa, jeśli zespół jest TS-owy (LM Studio, TensorFold i AnythingLLM na nim stoją), ale kosztuje 130–590 MB instalatora i 150–400 MB RAM.
7. **Daemon z API OpenAI, Anthropic i opcjonalnie Ollama na 127.0.0.1**, z losowym tokenem, sprawdzaniem nagłówka `Host` (DNS rebinding) i bez `0.0.0.0` domyślnie. Ollama zebrała w tej konfiguracji serię CVE i dziesiątki tysięcy instancji wystawionych do internetu.
8. **Strata ma już mini-wersję naszej „nocnej optymalizacji”.** `--calibrate` trwa 15–30 min, zachowuje ustawienie tylko przy zysku >3% i zapamiętuje je per PC i model. Do tego tabele `arch_defaults` (domyślnie tylko bitowo dokładne przełączniki) i `BENCH.bat` z raportami społeczności. Nasz produkt musi zrobić to samo, tylko szerzej i z bramką md5/KLD na maszynie użytkownika.
9. **Jedynym realnym nośnikiem „kernel tuningu na maszynie użytkownika” bez toolchaina są runtime-kompilowane, sparametryzowane kernele.** Mowa o specialization constants w Vulkanie, hipRTC i NVRTC. Nowe kernele z agentów powinny powstawać w naszym backendzie i trafiać do użytkownika jako podpisane paczki silnika per architektura. `[INFERENCE]`
10. **Code signing jest wykonalny dla firmy z UE.** Apple kosztuje $99 rocznie. Azure Artifact Signing kosztuje od $9.99 miesięcznie, ale **osoby prywatne kwalifikują się tylko w USA i Kanadzie**, więc potrzebna jest spółka. EV nie daje już natychmiastowej reputacji w SmartScreen.

---

## 2. Ustalenia

### 2.1 Punkt odniesienia: nasz fork vs upstream

| Metryka | Wartość | Źródło |
|---|---|---|
| Baza forka | `b11528` (2026-10-09), `git describe` = `b11528-70-gf61994f58` | `~/llama-master` |
| Nasza delta | 70 commitów, 69 plików, +11 401 / −803 linii; 70 plików `.patch` w `patches/llama.cpp-amd-opt/` | `git diff --shortstat b11528 HEAD` |
| Najczęściej łatane pliki | `test-backend-ops.cpp` (23 patche), `ggml-cuda.cu` (23), `mmvq.cu` (21), `common.cuh` (12), `llama-graph.cpp` (9) | statystyka z `*.patch` |
| Upstream dziś | `b11671` i `v0.7.0` (2026-10-15) | https://github.com/ggml-org/llama.cpp/releases/tag/v0.7.0 |
| Delta upstream od naszej bazy | 143 commity w 6 dni; z 69 plików, które łatamy, upstream zmienił **33** | `gh api compare b11528...b11671` (lista plików ucięta na 300, więc to dolna granica) |

Wniosek liczbowy: pełny rebase raz w tygodniu dotyka mniej więcej połowy naszych plików. To potwierdza, że każdy kolejny patch per architektura podnosi koszt utrzymania liniowo. `[INFERENCE]`

### 2.2 Strata i TensorFold dziś a nasze notatki

| | **Strata** (Niko1221/Strata) | **TensorFold** (ashhart/TensorFold) |
|---|---|---|
| Licencja | MIT (części i modele mają własne licencje) | Apache-2.0 (silnik); `app/` ma osobny LICENSE; NOTICE i MIT dla części Mia AI Lab |
| Popularność (2026-10-15) | **25 414 ★**, 2 621 forków, 984 issues | 1 329 ★, 246 forków, 188 issues |
| Tempo | **622 commity w 7 dni**; v0.1.44 (10-13), v0.1.44.1 (10-14) | **1 220 commitów w 7 dni**; silnik v1.0.9–1.0.11 w 2 dni; app beta.5/.6 |
| Architektura | Własny silnik C++/CUDA/HIP (+SYCL, +Metal). Z ggml wzięty tylko `third_party/ggml/ggml-common.h` (bloki kwantów GGUF) i host MMQ do prefillu | Własny silnik w **Zig 0.17**, jedna binarka; kernele Metal i CUDA; HIP tylko jako szkielet w `main` |
| Modele | Qwen3.8-Flash-Next (125B MoE, offload ekspertów VRAM/RAM/SSD) oraz osobny driver Qwen3.6-35B-A3B | „Qualified models”: 7 par model × platforma (Nemotron 3.5 Lightning, Qwen3.8 Flash Next, GLM-5.3(-Flash), Qwen3.5-2B, Qwen3.8-27B + DFlash2) |
| HW | NVIDIA RTX 20–50, AMD RX 6800–9070/R9700 (Windows i Linux). Eksperymentalnie P40/V100, Arc, Mac M1–M5, Strix Halo | Metal M1–M5. CUDA: GB10, RTX 3090 (sm_86), RTX PRO 6000 / RTX 50 (sm_120) |
| Dystrybucja | `START-HERE.bat` / `setup.sh` instaluje prebuilt zip. Zipy na Windows: **CPU 148 MB, CUDA12 215 MB, HIP 604 MB** (HIP z DLL ROCm 10.2.0a20260930 z TheRock dla gfx1100 i gfx1201; użytkownik instaluje tylko sterownik Adrenalin) | Archiwum silnika **4–5 MB** (runtime CUDA osobno, wg RUNBOOK); Homebrew; `curl … \| sh`; **app Electron (Mac), DMG 131 MB (beta.5) / 270 MB (beta.6)** |
| UX dla nietechnicznych | Instalator pyta o model, rozmiar, kontekst i obrazy, a Enter przyjmuje rekomendację. Web UI na `127.0.0.1:8080` (Chat, Monitor, About). **„Let your AI set it up”**: wklejasz link do agenta kodującego i on postępuje według `docs/AI_SETUP.md`. Jest serwer MCP. `BENCH.bat` generuje raport do udostępnienia | Aplikacja z rekomendacją modelu po chipie i pamięci, pobieraniem, metrykami tok/s, lokalnym API z kluczem na sesję. Dochodzą „Workers” i agent kodujący |
| Autotuning | **`--calibrate`** (od 0.1.19): mierzy 4 grupy ustawień (`--pcie-frac`, `--spec-min-p`, `--pool-workers`, `--adapt-*`) w 15–30 min. Ustawienie zostaje tylko przy zysku >3%, zapisane per PC i model, przeżywa aktualizacje. Na Windows tylko NVIDIA | Brak samostrojenia. Głębokość draftu wyceniana kosztem mierzonym przy starcie (z naszych notatek) |
| Aktualizacje | `UPDATE.bat` | **Podpisany feed Ed25519 + SHA-256**, klucz publiczny wkompilowany. Squirrel.Mac staging. Pinned Developer ID i notaryzacja. Wymagany stan bezczynności przed restartem |

Źródła wiersza Strata:
- https://github.com/niko1221/strata
- `docs/DETAILS.md:489-505` (calibrate)
- `docs/AMD_HIP.md:65-84`
- `tools/hip/package_windows.py:1-50`
- wydanie v0.1.44.1: https://github.com/Niko1221/Strata/releases/tag/v0.1.44.1

Źródła wiersza TensorFold:
- https://github.com/ashhart/TensorFold
- https://tensorfold.dev/
- https://raw.githubusercontent.com/ashhart/TensorFold/main/app/docs/app-updates.md
- https://raw.githubusercontent.com/ashhart/TensorFold/main/app/README.md
- https://github.com/ashhart/TensorFold/releases

**Co się zmieniło od naszych notatek** (`strata/update-v0.1.44.md`, `tensorfold/update-v1.0.11.md`):
- **Strata.** v0.1.44.1 zapowiadano wcześniej jako poprawki CUDA 12.1, Metal M2 i Pascal bez AVX2. Teraz ma prebuilt zipy dla Windows, w tym HIP z ROCm z TheRock. Silnik na Windows/AMD wymaga więc od użytkownika tylko sterownika, a koszt wynosi 604 MB.
- **TensorFold.** Wyszła aplikacja „TensorFold” na Electron, z modułem agentowym. Silnik 1.0.11 nadal nie ma HIP w `main`. W naszych notatkach było, że stos HIP społeczności (#617/#621/#631) czeka od 1.0.7. W `README` 1.0.11 jest wprost: „Without [drafter] the 27B decodes plain, which is slower than mlx_lm” oraz „prompt processing trails mlx_lm”.
- **Lekcja dla produktu (oba projekty).** Rekordy t/s przychodzą z silników „pod model”, a skala produktu z prostego instalatora i rekomendacji. Strata ma 25k gwiazdek przy jednym modelu, bo instalacja to podwójne kliknięcie. `[INFERENCE]`

### 2.3 Rodzina llama.cpp / ggml

**Upstream llama.cpp (ggml-org)**
- **Licencja i popularność:** MIT, ok. 131k ★. https://github.com/ggml-org/llama.cpp
- **Rytm wydań:**
  - Nightly `bNNNN`: ok. 170 numerów w 7 dni (b11500 z 2026-10-08, b11669 z 2026-10-15). https://github.com/ggml-org/llama.cpp/releases/expanded_assets/b11500
  - **Linia semver:** v0.6.0 ok. 2026-10-05 `[SEC]`, **v0.7.0 2026-10-15** (przypina b11669 i ggml v0.27.0). https://github.com/ggml-org/llama.cpp/releases/tag/v0.7.0
- **Backendy:** CPU, CUDA, HIP, Vulkan (coopmat/coopmat2), SYCL, Metal, OpenCL (Adreno), CANN, MUSA, WebGPU, Hexagon, OpenVINO („in progress”), zDNN, ZenDNN, RPC. https://github.com/ggml-org/llama.cpp
- **Co nowego w v0.7.0:**
  - chunked GDN na CUDA/HIP;
  - Vulkan: coopmat2 z harmonogramem L2-aware i aktywacje bf16;
  - HIP: kafle MMQ 64 wierszy na RDNA3.5;
  - `--moe-cache-mib` (do ok. 2,2× decode przy offloadzie ekspertów);
  - spekulacja LiliCorr;
  - **domyślny port serwera 9931** zamiast 8080.

  https://github.com/ggml-org/llama.cpp/releases/tag/v0.7.0
- **Serwer:**
  - `llama-server` z API OpenAI i web UI (osobny tarball ok. 3 MB), a od v0.7.0 także Models Manager w UI.
  - **Router mode:** start bez modelu, `--models-dir`, `--models-max` (LRU), `--models-autoload`.
  - https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md
- **C API (`llama.h`) nie jest zamrożone.** v0.6.0 wprowadziło `llama_batch_ext` / `llama_process()`, a v0.7.0 zmienia kolejne pola. https://github.com/ggml-org/llama.cpp/releases/tag/v0.7.0
- **DFlash i MTP są już w mainline** (w v0.7.0 dochodzi MTP dla GLM5-Next).
- **Governance:** ggml.ai dołączyło do Hugging Face 2026-02-20, z deklarowaną autonomią techniczną. https://huggingface.co/blog/ggml-joins-hf
- **Polityka AI:** „AI-generated code is allowed… Undisclosed AI usage may result in… ban”. Zakazane są: „Automated commits or PR submissions (may result in contributor ban)” oraz pisane przez AI opisy PR, commity i odpowiedzi. „A simpler change that does 90% of the job is often preferable”. **„Private forks are exempt.”**
  - https://github.com/ggml-org/llama.cpp/blob/master/CONTRIBUTING.md
  - https://github.com/ggml-org/llama.cpp/blob/master/AGENTS.md
- **Prebuilt artefakty b11669:** tabela w §2.6.

**ik_llama.cpp** (ikawrakow)
- MIT.
- Fork z 2024-06, „last synced with upstream in August 2024” `[STALE?]`, czyli rozjazd jest trwały.
- Ma kwanty IQK i trellis (KT), MLA, fused delta-net, MTP i DFlash.
- **Pełnoprawne są tylko CPU (AVX2+/NEON) i CUDA (Turing+)**; ROCm, Vulkan i Metal nie są obsługiwane.
- Wydajność CPU pp do 3,27× `[STALE?]`.
- https://github.com/ikawrakow/ik_llama.cpp
- https://github.com/ikawrakow/ik_llama.cpp/discussions/164

Dla nas to przykład, że trwały fork daje przewagę na CPU i MoE, ale traci pokrycie sprzętu.

**hipfire** (Kaden-Schutt → warpfront)
- Rust + HIP, bez ggml. Tylko AMD (CDNA, RDNA1–4, XDNA2 NPU dla prefillu).
- Własne kwanty MQ3–MQ6/MFP4, własny replay PM4 („Redline”) i własny emiter ISA („PeaceMaker”).
- Apache-2.0, części MIT. v0.4.2 (ok. 2026-10-14), wydania co tydzień. OpenAI daemon na :11435.
- https://github.com/Kaden-Schutt/hipfire
- https://raw.githubusercontent.com/warpfront/hipfire/master/LICENSE

Liczby na 7900 XTX (z naszej notatki `repos/30-hipfire.md`):
- AR 50,8–54,3 t/s;
- MTP 76,4;
- DFlash 307,9 t/s na jednym prompcie kodu;
- pp8192 ok. 3000 (W4A4, stratny).

Nasz MTP to 104–109 t/s na mieszance promptów.

**Lucebox** (Luce-Org)
- C++17, serwer OpenAI na własnym forku ggml (`lucebox-ggml@luce-dflash`, z naszej notatki `repos/22-lucebox.md`). Apache-2.0, ok. 2,9k ★.
- CUDA 12+ (sm_61–121) i HIP 7+ (RDNA3/3.5/4).
- **DFlash2 na R9700: 208,1 t/s na Qwen3.8-27B, 3,8× llama.cpp z tym samym drafterem.**
- https://github.com/Luce-Org/lucebox

**DFlash** (Z Lab, arXiv 2602.06036, ICML 2026)
- Drafter blokowo-dyfuzyjny generuje cały blok w jednym forward, warunkowany cechami targetu.
- >6× bezstratnie, do 2,5× lepiej niż EAGLE-3.
- Obsługują go vLLM speculators i llama.cpp mainline.
- https://arxiv.org/abs/2602.06036
- https://github.com/z-lab/dflash

**Ollama**
- v0.40.5 (2026-10-14), MIT, Go.
- Własny „new engine” (ollamarunner, Go na ggml) plus llamarunner (cgo do llama.cpp) jako fallback `[SEC]`. MLX na Apple od 0.19 `[SEC]`.
- **Instalator Windows 1 511 MB**; ROCm to osobny zip (244 MB Windows, 1 003 MB Linux).
- Niezależny pomiar: Ollama dwa razy wolniejsza od upstream llama.cpp na L40S (20,0 vs 39,1 t/s). https://computingforgeeks.com/ollama-vs-vllm-vs-llama-cpp/
- Pozostałe źródła:
  - https://github.com/ollama/ollama/releases
  - https://github.com/ollama/ollama/issues/9959
  - https://jonathanding.github.io/llm-learning/en/articles/ollama-architecture/

**LM Studio**
- Licencja własnościowa. Electron.
- **Silniki llama.cpp (CUDA, Vulkan, ROCm, CPU) i MLX jako „Runtime Extension Packs” pobierane na żądanie**, z `lms runtime get/select/update` i automatycznym czyszczeniem LRU.
- Headless daemon `llmster` od 0.4.0. Instalator Windows 587 MB `[SEC]`.
- Źródła:
  - https://lmstudio.ai/docs/cli/runtime/runtime
  - https://lmstudio.ai/blog/lmstudio-v0.3.16
  - https://lmstudio.ai/docs/developer/core/headless
  - https://www.techspot.com/downloads/7719-lm-studio.html

**Jan**
- Tauri + Rust, v0.8.6 (2026-10-09). Licencja wg API GitHuba „NOASSERTION”.
- **W 0.8.5 odwrócono decyzję:** llama.cpp (0.5.0, b11146) jest teraz w instalatorze zamiast pobierania na starcie. Działa w osobnym procesie roboczym („an engine crash no longer takes the app down”).
- Na Windows i Linux: NVIDIA dostaje CUDA 13, **wszystko inne Vulkan**. Opcja CUDA 11/12 dla Pascala zniknęła, ROCm nie ma wcale.
- Instalator x64 530 MB, DMG 95 MB.
- https://github.com/janhq/jan/releases/tag/v0.8.5

**Lemonade (AMD)**
- Apache-2.0, C++. v2026.42.1 (2026-10-14). **`lemonade.msi` 10,3 MB, „minimal” 6,7 MB.**
- „**Embeddable Lemonade** is a portable binary you can package into your own application… auto-optimizes for your user's PC”, w paczkach 5–7 MB.
- Backendy: llamacpp (system, metal, cuda, vulkan, rocm, cpu), `llamacpp-hrx` (gfx1100/1151, Linux), FLM i ryzenai-llm (NPU XDNA2), vLLM (gfx1151), whisper.cpp, SD.
- Buildy ROCm per rodzina GPU (`lemonade-sdk/llamacpp-rocm`): Windows gfx110X 506 MB, gfx1151 183 MB, gfx120X 654 MB.
- To najbliższy istniejący analog naszego produktu po stronie AMD.
- https://github.com/lemonade-sdk/lemonade
- https://github.com/lemonade-sdk/llamacpp-rocm/releases

**Inne:**
- **KoboldCpp:** AGPL-3.0; exe 612 MB (CUDA), 111 MB (bez CUDA). https://github.com/LostRuins/koboldcpp/releases
- **llamafile:** Apache-2.0, ożywiony przez mozilla-ai. llama.cpp jako submoduł plus katalog patchy; limit 4 GB exe na Windows. https://github.com/mozilla-ai/llamafile
- **GPT4All:** MIT, ostatnie wydanie v3.10.0 z 2025-02, faktycznie EOL. https://github.com/nomic-ai/gpt4all/discussions/3649

| Projekt | Licencja | HW | API do osadzenia | Tempo | Wydajność / uwaga |
|---|---|---|---|---|---|
| llama.cpp | MIT | CUDA, HIP, Vulkan, SYCL, Metal, OpenCL, CANN, MUSA, WebGPU, Hexagon, CPU | C API (zmienne), `llama-server` (OpenAI, router, UI) | ok. 24 buildy dziennie; semver co ok. 10 dni | baza; DFlash, MTP i MoE-cache w mainline |
| ik_llama.cpp | MIT | CPU, CUDA | `llama-server` | ciągłe, bez tagów | CPU/MoE szybszy; brak AMD/Apple |
| hipfire | Apache-2.0 (+MIT) | tylko AMD | Rust CLI + daemon OpenAI | co tydzień | DFlash 308 t/s (1 prompt), AR ok. 51 t/s na XTX |
| Lucebox | Apache-2.0 | CUDA 12+, HIP 7+ | serwer OpenAI, Docker | aktywny | DFlash2 3,8× llama.cpp (R9700) |
| Strata | MIT | NVIDIA, AMD (+eksp. Intel, Mac) | serwer OpenAI/Anthropic, MCP | ok. 90 commitów dziennie | silnik jednego modelu MoE z offloadem |
| TensorFold | Apache-2.0 | Metal, CUDA (sm_86, sm_120, GB10) | serwer OpenAI/Anthropic | ok. 170 commitów dziennie | 7 kwalifikowanych par model × HW |
| Ollama | MIT | CUDA, ROCm (add-on), Metal/MLX, CPU | REST + OpenAI, Go | co 1–3 tyg. | instalator 1,5 GB; bywa wolniejsza od upstream |
| LM Studio | własnościowa | llama.cpp (CUDA, Vulkan, ROCm, CPU) + MLX | `lms`, `llmster`, REST, SDK JS/Py | częste 0.4.x | runtime packs na żądanie |
| Jan | „NOASSERTION” | CUDA 13, Vulkan, Metal | OpenAI :1337 | aktywny | bundled engine, bez ROCm |
| Lemonade | Apache-2.0 | ROCm, Vulkan, CUDA, Metal, NPU, CPU | OpenAI/Anthropic/Ollama, embeddable binary | co tydzień | instalator 10 MB |
| KoboldCpp | AGPL-3.0 | CUDA, Vulkan, ROCm, CPU | API Kobold + OpenAI | 2–3 tyg. | copyleft blokuje osadzanie |

### 2.4 Silniki spoza ggml

**ExLlamaV3** (turboderp)
- MIT. v1.6.0 (2026-10-07), potem 1.6.1 i 1.6.2.
- Format EXL3 oparty na QTIP.
- **„Preliminary ROCm support (ROCm 10 only, gfx1100+)”**.
- Windows: wheel ok. 108 MB plus `triton-windows`. Brak Apple i brak CPU. Tylko Python, bez C API `[INFERENCE]`.
- Serwer TabbyAPI jest na **AGPL-3.0**.
- ExLlamaV2 zarchiwizowany 2026-03-21.
- https://github.com/turboderp-org/exllamav3/releases/tag/v1.6.0
- https://github.com/theroyallab/tabbyAPI/

Benchmark RTX 5090, Gemma-4-12B, porównanie przy tym samym rozmiarze pliku (https://atomic.chat/blog/guides/exl3-vs-gguf):
- **prefill 4 077 vs 1 795 t/s** (EXL3 4.0 bpw vs Q5_K_M), czyli EXL3 wygrywa;
- **decode 113,1 vs 130,1 t/s**, czyli wygrywa GGUF;
- KLD: EXL3 4.0 bpw 0,0248 vs Q4_K_M 0,0398.

**MLC-LLM / WebLLM**
- Apache-2.0, kompilator TVM. CUDA, ROCm, Vulkan, Metal, OpenCL, iOS i Android.
- Tylko nightly wheels. Wymaga kompilacji per target i nie czyta GGUF `[INFERENCE]`.
- WebLLM v0.2.85 (2026-09) jest aktywnie rozwijany, MLC-core umiarkowanie.
- Stary benchmark producenta: 4090 204,8 vs 151,1 t/s (Llama2-7B) `[STALE?]`.
- https://github.com/mlc-ai/mlc-llm
- https://llm.mlc.ai/docs/install/mlc_llm
- https://github.com/mlc-ai/llm-perf-bench

**mistral.rs**
- MIT, Rust. v0.9.4 (2026-09-24), wydanie z łatkami CVE na path traversal i SSRF.
- Prebuilt: CUDA (Ampere+, Linux), Metal, CPU. **Na Windows tylko CPU. Brak ROCm i Vulkan.**
- Crate `mistralrs` do osadzenia, ISQ, `mistralrs tune`.
- https://docs.mistralrs.dev/reference/hardware-support/
- https://github.com/EricLBuehler/mistral.rs/releases/tag/v0.9.4

**candle** (HF)
- Apache-2.0/MIT `[INFERENCE]`. 0.11.0 (2026-06).
- CPU, CUDA, Metal, WASM. ROCm tylko w PR #3424/#3801, Vulkan tylko w forkach.
- To framework, nie silnik.
- https://lib.rs/crates/candle-core
- https://github.com/huggingface/candle/pull/3801

**PowerInfer / SmallThinker**
- MIT.
- Zysk do 11,7× tylko na modelach rzadkich ReLU `[STALE?]`. Repo przeniesione do Tiiny-AI, silnik praktycznie uśpiony.
- SmallThinker-4B-A0.6B: 79 t/s na OnePlus 13.
- https://github.com/Tiiny-AI/PowerInfer
- https://arxiv.org/html/2507.20984v2

**KTransformers**
- Apache-2.0. Hybryda CPU/GPU dla wielkich MoE (AMX, AVX-512, AVX2), integracja z SGLang.
- Decode 1,25–1,76× llama.cpp. Python. Docelowo stacje robocze ze 128 GB+ RAM.
- https://github.com/kvcache-ai/ktransformers

**vLLM / SGLang**
- vLLM v0.31.0 (2026-10-05): **brak natywnego Windows**, RDNA4 bez FP8 (fallback).
- Single-stream na Qwen3.8-27B 4-bit: 4090 54,3 vs 49,5 t/s, 5090 85,7 vs 77,8 t/s względem llama.cpp. Na 4090 MTP w vLLM kończył się OOM.
- RX 9070 XT: vLLM ROCm 48 vs llama.cpp Vulkan 62 t/s.
- SGLang v0.5.21, Linux.
- Dla jednego użytkownika na desktopie: nie. To silniki serwerowe.
- Źródła:
  - https://computingforgeeks.com/ollama-vs-vllm-vs-llama-cpp/
  - https://digtvbg.com/blog/llama-server-vulkan-rdna4-vllm-rocm-benchmark/
  - https://github.com/vllm-project/vllm/issues/28649

**Telefony (pod nasz wątek MiniCPM):**
- **LiteRT-LM** (Apache-2.0): v0.17.1, C API od v0.16, GPU przez ML Drift (OpenCL, Metal, WebGPU), NPU. Głównie Gemma. https://github.com/google-ai-edge/LiteRT-LM
- **ExecuTorch** (BSD-3): 1.0 GA 2025-10, Vulkan coopmat, QNN, CoreML. https://github.com/pytorch/executorch
- **MNN-LLM** (Apache-2.0): Hexagon od 3.6.1; w pracy CPU decode 2,3× llama.cpp. https://github.com/alibaba/mnn, https://arxiv.org/pdf/2506.10443

| Silnik | Licencja | HW | Osadzanie | vs llama.cpp (consumer) | Dopasowanie do nas |
|---|---|---|---|---|---|
| ExLlamaV3 (+TabbyAPI) | MIT (+AGPL) | NVIDIA, ROCm wstępnie | Python | prefill 2,2–2,5× szybciej, decode 13% wolniej | niskie (Python, NVIDIA) |
| MLC-LLM / WebLLM | Apache-2.0 | wszystko przez TVM + WebGPU | Python, SDK mobilne, npm | stare +35% `[STALE?]` | niskie (kompilacja per GPU) |
| mistral.rs | MIT | CUDA, Metal, CPU | crate Rust | dane producenta, data center | niskie (brak AMD, Windows tylko CPU) |
| candle | Apache/MIT | CPU, CUDA, Metal | crate Rust | n/d | klocek, nie silnik |
| PowerInfer | MIT | CUDA, ROCm, CPU | C++ | tylko modele ReLU | brak |
| KTransformers | Apache-2.0 | CUDA, ROCm, XPU + AMX | Python | 1,25–1,76× (duże MoE) | nisza |
| vLLM / SGLang | Apache-2.0 | Linux CUDA/ROCm | Python/HTTP | +9–12% NVIDIA, −23% RDNA4 | brak (Windows) |
| LiteRT-LM / ExecuTorch / MNN | Apache / BSD | telefony, NPU | C/C++ | n/d | tylko wątek mobilny |

### 2.5 Stosy producentów sprzętu

**NVIDIA**
- **TensorRT-LLM:** natywny Windows wycofany od v0.18.0 („will be completely removed”). https://nvidia.github.io/TensorRT-LLM/release-notes.html
- **TensorRT for RTX 1.7:**
  - licencja własnościowa; `tensorrt-rtx` 1.7.1.116 z 2026-10-14;
  - AOT 20–30 s, potem JIT na GPU <5 s, z cache;
  - libs ok. 83–90 MB;
  - **brak natywnego wdrożenia LLM**: LLM działa tylko jako EP pod Windows ML / ORT GenAI, na CC ≥ 8.6;
  - silniki nie są forward-compatible.

  https://docs.nvidia.com/deeplearning/tensorrt-rtx/latest/architecture/architecture-overview.html, https://pypi.org/project/tensorrt-rtx/
- **Wkład NVIDIA w llama.cpp:** CUDA Graphs, FA, MoE +35%. Na IFA 2026 deklaracja „do 1,9×” na 5090.
  - https://developer.nvidia.com/blog/optimizing-llama-cpp-ai-inference-with-cuda-graphs
  - https://blogs.nvidia.com/blog/local-ai-ifa-next-gen-agents-nv-pair-rtx-spark/

  Wniosek: NVIDIA sama optymalizuje upstream, więc na NVIDIA nasza przewaga z kernel tuningu będzie mniejsza niż na AMD i Intelu. `[INFERENCE]`

**Microsoft**
- **onnxruntime-genai:** MIT, 0.18.0 (2026-10-14), wydania co ok. 2 tygodnie, wheel 4–15 MB plus ORT. https://github.com/microsoft/onnxruntime-genai
- **DirectML:** w trybie „sustained engineering”. https://learn.microsoft.com/en-us/windows/ai/directml/dml-get-started
- **Windows ML:**
  - GA 2025-09-23 `[STALE?]`;
  - **EP pobierane na żądanie** (Win 11 24H2+);
  - NVIDIA TensorRT-RTX (RTX 30+), Intel OpenVINO, Qualcomm QNN, AMD VitisAI (NPU), WebGPU (eksperymentalne);
  - AMD MIGraphX (RDNA3+) jest „**not supported for GenAI scenarios today**”.

  https://learn.microsoft.com/en-us/windows/ai/new-windows-ml/supported-execution-providers
- **Foundry Local:** SDK MIT, CLI na licencji własnościowej; v2.0.1; zbudowany na ORT i GenAI. https://github.com/microsoft/foundry-local

  Model dostarczania „EP per vendor przez Windows Update” jest ciekawy, ale wymaga modeli ONNX, a na AMD dGPU nie obsługuje LLM.

**Intel**
- **OpenVINO 2026.4** (2026-09-16): MTP, DFlash na GPU, INT4 KV.
- **2026.1 dodało backend OpenVINO dla llama.cpp**: zip 84–95 MB.
- IPEX-LLM zarchiwizowany 2026-01-28.
- Na Arc Pro B70 po Mesa 26.1 Vulkan ≥ SYCL: tg 76,0 vs 77,3, pp512 1 225 vs 939, 8 strumieni 170 vs 100 t/s. Autor rekomenduje Vulkan.
- Źródła:
  - https://docs.openvino.ai/2026/about-openvino/release-notes-openvino.html
  - https://www.phoronix.com/news/OpenVINO-2026.1-Released
  - https://github.com/intel/ipex-llm/wiki/
  - https://jonathanmann.tech/blog/intel-arc-b70-llama-cpp-benchmarks/

**Apple MLX**
- MIT. `mlx` 0.32.4 / `mlx-lm` 0.32.1 (2026-10-14/15), mlx-swift 0.31.6. `mlx-metal` 42–74 MB.
- Decode vs llama.cpp Metal:
  - M3 Ultra, Qwen3.5-9B: 107,5 vs 77,8 t/s;
  - M4 Max, Qwen3-8B: +21%;
  - 35B-A3B: 130 vs 89 t/s.
- llama.cpp ma 1,7–2,2× szybszy prefill. Na bazowym M4 i przy 27B+ przewaga MLX znika.
- Źródła:
  - https://pypi.org/project/mlx/
  - https://terminalbytes.com/ollama-vs-llama-cpp-vs-mlx-mac-2026/
  - https://blog.starmorph.com/blog/apple-silicon-llm-inference-optimization-guide
  - https://github.com/vicnaum/local-llm-bench-m4-32gb/blob/main/results/engine_comparison.md

**ZLUDA**
- Apache-2.0 OR MIT, wersja 6.
- Od 2026-06 „**no longer commercially funded… back to being my weekend project**”. Na Windows i tak potrzebuje bibliotek ROCm.
- Dla llama.cpp (natywny HIP i Vulkan) bezcelowe, a do tego to ryzyko prawne i supportowe. `[INFERENCE]`
- https://vosen.github.io/ZLUDA/blog/zluda-update-q1q2-2026/

**AMD ROCm na Windows**
- **HIP SDK 7.2 na Windows:** RX 9070/9060, R9700, RX 7900/7800/7700, W7900–W7700, Ryzen AI Max i AI 300/400. https://rocm.docs.amd.com/projects/install-on-windows/en/latest/reference/system-requirements.html
- **TheRock:**
  - „Since ROCm 7.14, ROCm is built and released through TheRock”;
  - nightly 10.x dla Linux i **natywnego Windows**;
  - paczki per gfx: core ok. 700 MB, biblioteki ok. 100 MB, device-gfx1100 ok. 50 MB.

  https://github.com/ROCm/TheRock/blob/main/README.md, https://github.com/ROCm/TheRock/blob/main/RELEASES.md
- **Rozmiar dla llama.cpp HIP:** upstream zip ROCm 10.0 dla Windows waży 245 MB. Po rozpakowaniu `ggml-hip.dll` ma **947 MB** (fatbin wszystkich archów), `amd_comgr.dll` 116 MB. https://github.com/ggml-org/llama.cpp/releases/tag/b11236
- **Adrenalin 26.1.1 „AI Bundle”:** 34 GB, w środku PyTorch, ComfyUI, Ollama i LM Studio. https://www.club386.com/amd-adrenalin-edition-26-1-1-driver-ai-bundle/
- **Ryzyko sterownika:** Adrenalin 26.5.1+ po ok. 15 s bezczynności wypycha model z VRAM do RAM (R9700). https://github.com/ggml-org/llama.cpp/discussions/23443
- **Licencje:** per komponent. rocBLAS i hipBLASLt są na MIT, rocSOLVER na BSD-2, comgr na Apache-2.0 z wyjątkiem LLVM. Strata dołącza je z NOTICE (`tools/hip/package_windows.py`). https://rocm.docs.amd.com/en/latest/about/license.html

**Vulkan i coopmat**
- **7900 XTX, b8497, Linux:** Vulkan RADV tg128 **174,6** vs ROCm 7.2 **143,8** t/s (+21%). ROCm wygrywa pp512 bez FA (3 976 t/s). ROCm crashował przy 32K. https://github.com/ggml-org/llama.cpp/issues/20934
- **RTX 5090:** CUDA vs Vulkan pp512 14 073 vs 10 382, tg128 290 vs 264. https://llmrequirements.com/cuda-vs-vulkan-llama-cpp
- **coopmat2:** tylko NVIDIA, sterownik 575+ `[STALE?]`. https://www.phoronix.com/news/NVIDIA-Vulkan-AI-ML-Success
- **AMD:** int8 coopmat (KHR) dla RDNA3/4 jest w llama.cpp. https://freenode.net/article/llama-cpp-speeds-amd-rdna3-4-inference-with-vulkan-int8-coopmat
- **Pułapki:**
  - bez `GL_EXT_integer_dot_product` w glslc podczas builda ścieżka MMVQ się wyłącza (ok. 10× wolniej). https://github.com/chaosmonkies/llamacpp-vulkan-intel-arc-slow-quant
  - AMDVLK porzucony, RADV jest oficjalny na Linuksie `[STALE?]`. https://www.phoronix.com/news/AMDVLK-Discontinued
- **Scoreboard:** https://github.com/ggml-org/llama.cpp/discussions/10879
- Nasz fork ma już patche Vulkan dla RDNA (0006–0008: small-M matvec, MMVQ dla K-quantów, integer-dot).

| Stos | OS | GPU | Licencja / redystrybucja | Rozmiar do wysłania | vs llama.cpp | Osadzanie |
|---|---|---|---|---|---|---|
| llama.cpp CUDA | Win, Linux | NVIDIA CC ≥ 7.5 (CUDA 13), starsze CUDA 12 | MIT + CUDA EULA Att. A | 147 MB + 404 MB runtime | baza | C API |
| llama.cpp HIP | Win, Linux | RDNA2–4, Strix Halo | MIT + licencje ROCm per komponent | 183–654 MB per rodzina | tg ok. 20% wolniej niż Vulkan na XTX | C API |
| llama.cpp Vulkan | Win, Linux (+Android) | AMD, NVIDIA, Intel | MIT, tylko sterownik | **31 MB** | XTX +21% tg vs ROCm; 5090 −10% tg vs CUDA | C API |
| llama.cpp Metal | macOS | Apple | MIT | 11,6 MB | baza na Macu | C API |
| MLX | macOS | Apple | MIT | 42–74 MB | +21–87% decode (≤ ok. 30B), wolniejszy prefill | C++, Swift, C |
| TRT-RTX (WinML/ORT) | Win, Linux | RTX 30+ dla LLM | własnościowa | ok. 90 MB + ORT | brak niezależnych danych | C++ (LLM tylko przez EP) |
| ORT GenAI + WinML | Win 11 24H2+ | EP per vendor | MIT + licencje EP | 4–15 MB + EP | brak danych | C/C++, C# |
| OpenVINO | Win, Linux | Intel CPU, iGPU, Arc, NPU | Apache-2.0 | 81–95 MB | Vulkan ≥ SYCL na B70 | C/C++ |
| ZLUDA | Win, Linux | AMD | Apache/MIT | + ROCm | n/d | — |

### 2.6 Dystrybucja backendów GPU: rozmiary i licencje

**Prebuilt llama.cpp b11669, Windows x64** (https://github.com/ggml-org/llama.cpp/releases/expanded_assets/b11669):

| Artefakt | Rozmiar |
|---|---|
| CPU | 18,6 MB |
| **Vulkan** | **30,7 MB** |
| macOS arm64 (Metal) | 11,6 MB |
| SYCL | 142 MB |
| OpenVINO | 94,8 MB |
| CUDA 12.4 | 254 MB, plus cudart 12.4: 373 MB |
| CUDA 13.4 | 147 MB, plus cudart 13.4: 404 MB |
| ROCm 10.0 (HIP) | 246 MB |

**Instalatory produktów:**

| Produkt | Instalator | Model backendów | Źródło |
|---|---|---|---|
| Ollama 0.40.5 | Windows **1 511 MB**, DMG 204 MB, ROCm jako add-on | wszystko w paczce | https://github.com/ollama/ollama/releases |
| LM Studio 0.4.24 | Windows 587 MB `[SEC]` | runtime packs na żądanie | https://lmstudio.ai/docs/cli/runtime/runtime |
| Jan 0.8.6 | Windows 530 MB, DMG 95 MB | od 0.8.5 bundled (CUDA 13 + Vulkan), bez ROCm | https://github.com/janhq/jan/releases/tag/v0.8.5 |
| Lemonade 2026.42.1 | **MSI 10,3 MB** | pobierane po detekcji; ROCm per rodzina gfx | https://github.com/lemonade-sdk/lemonade |
| KoboldCpp 1.123 | 612 MB (CUDA) / 111 MB (nocuda) | warianty exe | https://github.com/LostRuins/koboldcpp/releases |
| Strata 0.1.44.1 | zip 148 / 215 / 604 MB (CPU / CUDA12 / HIP) | `setup.py` wybiera po detekcji | https://github.com/Niko1221/Strata/releases |
| TensorFold 1.0.11 | silnik 4–5 MB; app DMG 131–270 MB | runtime CUDA osobno | https://github.com/ashhart/TensorFold/releases |

**Licencje i wersje:**
- **CUDA EULA (13.3), Attachment A:** `cudart`, `cublas` i `cublasLt` wolno redystrybuować jako część aplikacji. https://docs.nvidia.com/cuda/pdf/EULA.pdf
- `cublasLt64_13.dll` waży **470 MB**, `cublasLt64_12.dll` 452 MB po rozpakowaniu. https://github.com/ggml-org/llama.cpp/releases/tag/b11236
- **CUDA 13 porzuca Maxwell, Pascal i Volta** (CC < 7.5). R580 to ostatnia gałąź sterownika dla tych kart. GTX 10xx wymaga więc osobnej paczki CUDA 12. https://developer.nvidia.com/blog/whats-new-and-important-in-cuda-toolkit-13-0/

### 2.7 Aplikacja: GUI, TUI, język rdzenia, daemon, release engineering

**GUI**

**Tauri 2.12.3** (2026-09; v3 w alpha):
- MIT/Apache-2.0. https://v2.tauri.app/blog/tauri-2.12/
- **Updater:** `tauri-plugin-updater` z podpisem minisign (Ed25519). Utrata klucza oznacza koniec aktualizacji dla zainstalowanych kopii. https://v2.tauri.app/plugin/updater/
- **Sidecar** (`externalBin`) do dołączania binarek. https://v2.tauri.app/develop/sidecar/
- **Linux (WebKitGTK):**
  - pełny rdzeń CPU w idle na NVIDIA (https://github.com/phase-rs/phase/issues/8614);
  - render na CPU po `WEBKIT_DISABLE_DMABUF_RENDERER=1` (https://github.com/xnmp/tauri-explorer/issues/1057);
  - AppImage 18 → 94 MB (https://hackernoon.com/six-months-with-tauri-the-benefits-and-the-bill).

**Electron 44.7.2:**
- MIT. Puste aplikacje ok. 296–320 MB `[STALE?]` (https://github.com/Elanis/web-to-desktop-framework-comparison).
- Idle RAM 150–400 MB `[SEC]` (https://tech-insider.org/tauri-vs-electron-desktop-app-framework-2026/).
- Auto-update przez Squirrel i electron-updater (blockmap delta).
- LM Studio na Electronie zwolnił na macOS 26. https://github.com/lmstudio-ai/lmstudio-bug-tracker/issues/1144

**Pozostałe:**
- **Wails 2.14** (MIT): 10–30 MB.
- **Flutter** (BSD-3): 20–80 MB, 80–200 MB RAM, brak wbudowanego updatera. https://rustify.rs/articles/rust-tauri-vs-flutter-2026
- **Qt 6:** LGPLv3 albo komercyjna. Small-business $618/rok (≤1 M przychodu). https://www.qt.io/development/qt-for-small-business
- **Natywne (SwiftUI/WinUI 3):** dwa kody UI. Sparkle i WinSparkle `[INFERENCE]`.

**Kto na czym:**
- Electron: LM Studio, AnythingLLM, Cherry Studio, Chatbox, Msty, Pinokio, AMD GAIA UI, TensorFold app.
- Tauri: Jan.
- Go + natywny WebView2/WKWebView + Inno Setup: Ollama.
- Qt/QML: GPT4All.
- https://ollama.com/blog/new-app
- https://www.phoronix.com/news/AMD-GAIA-0.17-Agent-UI

**TUI**
- **ratatui** 0.30.2: MIT, 23k ★. https://ratatui.rs/highlights/v030/
- **Bubble Tea** v2.1.0 (2026-10-08): MIT, 45k ★, używa go Crush od Charm. https://pkg.go.dev/charm.land/bubbletea/v2
- **Textual** 8.2.8: MIT, wymaga Pythona. https://github.com/Textualize/textual/releases

**Język rdzenia w praktyce:**
- Ollama: Go + cgo.
- llama-swap: Go, zip 21 MB.
- Lemonade: C++.
- Jan: Rust/Tauri.
- Strata: C++ silnik + Python serwer/instalator.
- TensorFold: Zig + Electron.
- Rust bindings: **`llama-cpp-2` 0.1.160 (2026-10-15)** jest aktywny, `edgenai/llama_cpp-rs` martwy. https://github.com/utilityai/llama-cpp-rs

**Daemon i bezpieczeństwo**

Domyślne porty:

| Usługa | Port |
|---|---|
| Ollama | `127.0.0.1:11434`, bez auth; CORS przepuszcza 127.0.0.1 i 0.0.0.0 |
| LM Studio | 1234 |
| Jan | 1337 |
| llama-server | 9931 (od v0.7.0) |
| Strata, TensorFold | 8080 |

https://docs.ollama.com/faq

CVE Ollamy:
- CVE-2024-28224 (DNS rebinding);
- CVE-2024-37032 „Probllama” (path traversal);
- CVE-2026-7482 „Bleeding Llama” (OOB read GGUF przez `/api/create`, poprawka w 0.17.1).
- https://nvd.nist.gov/vuln/detail/cve-2024-28224
- https://nvd.nist.gov/vuln/detail/CVE-2024-37032
- https://nvd.nist.gov/vuln/detail/CVE-2026-7482

Ekspozycja w internecie:
- Cisco: 1 139 endpointów (2025-09), w tym 214 bez auth `[STALE?]`. https://blogs.cisco.com/security/detecting-exposed-llm-servers-shodan-case-study-on-ollama
- Kwiecień 2026: 25 036 instancji. https://research.opena2a.org/reports/april-2026-exposure-sweep

TensorFold app robi to dobrze: API tylko na loopbacku, port i klucz losowane przy każdym starcie, headless odmawia startu z bind innym niż 127.0.0.1.

**Code signing**
- **Apple:** $99 rocznie plus notaryzacja przez `notarytool`. https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution
- **Azure Artifact Signing:**
  - Basic $9.99/mies. (5 000 podpisów), Premium $99.99/mies.;
  - organizacje z UE kwalifikują się, **osoby prywatne tylko z USA i Kanady**;
  - wymaga płatnej subskrypcji Azure i nie daje EV.
  - https://azure.microsoft.com/en-us/products/artifact-signing
  - https://learn.microsoft.com/en-us/azure/artifact-signing/quickstart
  - https://learn.microsoft.com/en-us/azure/artifact-signing/faq
- **SmartScreen:** EV i OV budują reputację tak samo. https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation

**CI i aktualizacje**
- **GitHub-hosted GPU runners:** Linux $0.052/min, Windows $0.102/min, tylko plany Team/Enterprise, **brak AMD**. https://docs.github.com/en/billing/reference/actions-runner-pricing
- **llama.cpp:** GPU testuje na self-hosted runnerach (`ci-self-hosted-{cuda,metal,vulkan}`), a buildy release robi w GitHub Actions, w tym Windows ROCm. https://github.com/ggml-org/llama.cpp/tree/master/.github/workflows
- **Velopack** (Rust): instalator i updater z deltami dla Windows, macOS i Linux, v1.2.0. https://github.com/velopack/velopack, https://crates.io/crates/velopack
- **Strata:** przy każdym zipie zapisuje `BUILD.json` (backend, archy, wersje ROCm i hipBLASLt) i `SHA256.txt`. https://github.com/Niko1221/Strata/releases/tag/v0.1.44.1

---

## 3. Co to znaczy dla naszego produktu

### 3.1 Strategia silnika

| Opcja | Na czym polega | Pokrycie modeli / HW | Koszt utrzymania | Zgodność z naszą metodą (md5/KLD, env off-switch) | Ryzyko | Kto tak robi | Werdykt |
|---|---|---|---|---|---|---|---|
| **A. Twardy fork + per-arch patch sety** (status quo) | Nasz `llama-master` z 70+ commitami; per arch kolejne patche | Pełne, dziedziczone z upstream w chwili forka | **Wysoki i rosnący liniowo.** 33 z 69 plików zmienione upstream w 6 dni; każdy nowy model upstream wymaga rebase | Pełna | Utknięcie na starej bazie, jak ik_llama.cpp (sync 2024-08) i Ollama (2× wolniej od upstream na L40S) | ik_llama.cpp, KoboldCpp, Lucebox | ❌ jako cel; ✔ tylko jako laboratorium agentów |
| **B. Upstream-first** | Wszystko do ggml-org, produkt na czystym upstream | Pełne, zawsze świeże | Niski po merge'u | Upstream przyjmuje zmiany bitowo neutralne, ale woli prostotę („90% of the job”) | **Polityka AI:** zakaz automatycznych PR i opisów pisanych przez AI; recenzja trwa; per-arch micro-tuning raczej odrzucany | NVIDIA (CUDA Graphs, FA, MoE) | ✔ dla zmian ogólnych; ❌ jako jedyna droga, bo produkt traci przewagę |
| **C. Własny runtime** | Silnik pisany od zera pod model lub rodzinę | **Wąskie:** 1–7 modeli (Strata, TensorFold), tylko AMD (hipfire) | Bardzo wysoki: każdy nowy model to nowy driver; Strata ma 622, TensorFold 1 220 commitów tygodniowo | Pełna i najlepsza: TensorFold ma kontrakt „drafted == plain” | Brak modeli day-0; „dowolny model” niemożliwy | Strata, TensorFold, hipfire | ❌ teraz; ⚠ później jako opcjonalny turbo dla 1–2 flagowych modeli |
| **D. Vendor runtime jako backend** (MLX, ORT GenAI/WinML, TRT-RTX, OpenVINO) | Osobny backend per platforma | MLX: Apple. ORT: modele ONNX. TRT-RTX: RTX 30+ | Średni na backend: inne formaty i konwersje | Słaba: nie kontrolujemy kerneli | Rozjazd formatów (GGUF vs ONNX vs MLX) | LM Studio (MLX), Ollama (MLX), Foundry Local (ORT) | ✔ **tylko MLX na Macu**, na późniejszym etapie |
| **E. Hybryda „thin overlay”** (rekomendacja) | Baza to **tag semver llama.cpp (v0.x)**. Nasze zmiany jako małe, izolowane patch-sety per backend/arch, każdy z env off-switch. Ogólne zmiany upstreamujemy ręcznie. Strojone parametry trzymamy w danych (tabele per arch/GPU/model), nie w kodzie | Pełne (upstream) + nasze przyspieszenia tam, gdzie zmierzone | **Średni, kontrolowany:** rebase raz na wydanie semver (ok. 10 dni), CI odpala md5/KLD gate per arch; patch, który nie przechodzi, jest wyłączany, nie blokuje wydania | Pełna: to dokładnie nasza metoda (off-switch, md5, KLD, A/B) | Dyscyplina: limit „budżetu patchy”, upstreaming jako stały proces | LM Studio, Jan i Lemonade częściowo (bez kernel tuningu); Strata `arch_defaults` jako wzór danych | ✔ **wybrana** |

**Szczegóły rekomendacji E:**
1. **Dwie warstwy optymalizacji.** Rozdział jest kluczowy dla obietnicy „zostaw na noc”.
   - **Warstwa runtime (na maszynie użytkownika, bez kompilatora).** Parametry istniejące w buildzie: tablice wierszy MMVQ per arch, wybór ścieżek kerneli przez env, `ubatch`, typy KV, parametry spekulacji (głębokość, `p_min`, blok DFlash), wątki, MoE cache, flash-attn on/off, Vulkan vs HIP vs CUDA. To odpowiednik Strata `--calibrate`, tylko szerszy. Każdy kandydat przechodzi bramkę greedy-md5 (lub KLD dla zmian numeryki) **lokalnie** przed zapisaniem.
   - **Warstwa kodu (w naszym backendzie, nie u użytkownika).** Nowe kernele i patche z pętli agentowej, na naszym sprzęcie i wynajmowanym (vast.ai, RunPod). Użytkownik dostaje je jako **podpisane paczki silnika per arch** (np. `engine-hip-gfx1100-<ver>`).
   - Kompilacja CUDA/HIP na maszynie użytkownika wymaga wielogigabajtowego toolchaina, więc odpada. Wyjątek to kernele kompilowane w runtime (Vulkan specialization constants, hipRTC, NVRTC), które pozwalają stroić tile i unroll lokalnie. `[INFERENCE: trzeba sprawdzić redystrybucję NVRTC w EULA i rozmiar hipRTC]`
2. **Baza na tagach semver, nie na nightly.** v0.6.0 → v0.7.0 w ok. 10 dni. Rebase per wydanie, z automatycznym raportem, które patche przestały się nakładać.
3. **Budżet patchy.** Patch, który przez N wydań nie zostanie zupstreamowany, a nie daje ≥X% na żadnej z docelowych architektur, jest usuwany. To nasza zasada „keep only real wins” przeniesiona na koszt utrzymania.
4. **Upstreaming.** Ręcznie, przez człowieka rozumiejącego zmianę, z ujawnieniem użycia AI, a opis PR pisze człowiek. Zgodnie z polityką ggml-org (`AGENTS.md`), bo inaczej grozi ban dla kontrybutora.
5. **Później (faza 3).** Opcjonalny „turbo-silnik” per flagowy model. Strata i TensorFold pokazują, że na Qwen3.8-27B i MoE da się wycisnąć dużo więcej: Lucebox DFlash2 208 t/s na R9700 i hipfire DFlash 308 t/s na prompcie kodu. Robimy go tylko wtedy, gdy dane z produktu pokażą, że ten model dominuje u użytkowników.

### 3.2 Język rdzenia / daemona

| Opcja | Za | Przeciw | Przykłady |
|---|---|---|---|
| **Rust** (rekomendacja) | Natywny dla Tauri i ratatui; jeden język GUI-backend + TUI + daemon; bezpieczeństwo pamięci (parsing GGUF i HTTP to wektor CVE, patrz Ollama i mistral.rs); aktywne `llama-cpp-2`; Velopack i minisign w Rust | Wolniejsza iteracja niż Go; bindingi do C++ wymagają dyscypliny | Jan, hipfire |
| Go | Szybka iteracja; Bubble Tea; sprawdzone w Ollama | cgo komplikuje cross-compile i Windows; brak dobrego GUI (Ollama robi własny webview) | Ollama, llama-swap |
| C++ | Ten sam język co silnik; zero FFI | Bezpieczeństwo serwera HTTP i parserów; wolniejsze tworzenie UI | Lemonade, KoboldCpp |
| TS (Electron) | Najszybsze UI; ogromny ekosystem | 130–590 MB instalatora, 150–400 MB RAM; daemon w Node to słaby wybór na długo działającą usługę | LM Studio, TensorFold app |

**Rekomendacja.** Daemon w Rust. Silnik (`llama-server` z naszego overlay albo nasz cienki host na `libllama`) działa **jako osobny proces potomny**, nie w procesie daemona. Daje to izolację crashy (jak Jan 0.8.5), podmianę paczki silnika bez restartu daemona i różne buildy per GPU. FFI do `libllama` nie jest potrzebne, dopóki wystarcza HTTP plus własne endpointy diagnostyczne. To też chroni przed niestabilnym C API.

### 3.3 GUI

| Framework | Instalator (sam shell) | RAM idle | Auto-update | Podpisywanie | Linux | Aplikacje LLM | Ocena dla nas |
|---|---|---|---|---|---|---|---|
| **Tauri 2** | **3–15 MB** (AppImage do ok. 94 MB z WebKitGTK) | 30–100 MB | `tauri-plugin-updater` (minisign Ed25519), wbudowany | bundler: Authenticode, notarize | ⚠ WebKitGTK: idle CPU na NVIDIA, render na CPU | Jan | ✔ **rekomendacja** (Win/mac) |
| Electron 44 | 120–300 MB | 150–400 MB | Squirrel / electron-updater (delta blockmap) | electron-builder (dojrzałe) | ✔ (Chromium w paczce) | LM Studio, AnythingLLM, Cherry, Msty, GAIA, TensorFold | ✔ alternatywa, jeśli priorytetem jest tempo UI i spójność Linuksa |
| Qt 6 / QML | ok. 30–60 MB `[INFERENCE]` (GPT4All 709 MB z silnikiem) | niski | Qt Installer Framework | DIY | ✔ | GPT4All (EOL) | ⚠ LGPL/komercja $618+/rok; wolniejszy rozwój UI |
| Flutter | 20–80 MB | 80–200 MB | brak, DIY / Velopack | DIY | ✔ | — | ⚠ brak ekosystemu LLM-desktop |
| Natywne (SwiftUI + WinUI 3) | najmniejsze | najniższy | Sparkle / WinSparkle `[INFERENCE]` | natywne | osobny UI (GTK) | — | ❌ 2–3 kody UI dla małego zespołu |
| Wails 2 (Go) | 8–30 MB | 25–120 MB | DIY | DIY | WebKitGTK (jak Tauri) | — (Ollama ma własny webview) | ⚠ tylko przy rdzeniu w Go |

**Rekomendacja:**
- Tauri 2 na Windows i macOS, z frontendem w TS (React lub Svelte). Daemon i silnik jako sidecar albo osobna usługa.
- Linux: najpierw TUI i CLI plus web UI daemona w przeglądarce, Tauri GUI jako „beta”. Grupa docelowa (nietechniczni) siedzi głównie na Windows i Macu. `[INFERENCE]`
- Budżet instalatora: **<40 MB** (shell + daemon + Vulkan 31 MB lub Metal 12 MB + CPU 19 MB). Model i paczki GPU dochodzą po detekcji.

### 3.4 TUI

- **ratatui**, przy rdzeniu w Rust: jeden kod domenowy z daemonem. Nasz istniejący monitor TUI (`~/KERNEL/monitor/`) jest punktem wyjścia dla ekranu „benchmark / optymalizacja trwa”. `[INFERENCE: nie czytałem jego kodu w tym raporcie]`
- **Bubble Tea v2**, jeśli rdzeń byłby w Go.
- **Textual** odpada, bo wymaga Pythona w dystrybucji.

### 3.5 Model procesów i API

```
app-gui (Tauri) ─┐
app-tui/cli ─────┼─► appd (Rust, user service) ── HTTP 127.0.0.1:<port>, token
inne aplikacje ──┘      │   /v1/chat/completions, /v1/responses, /v1/messages, /v1/models
                        │   (opcjonalnie /api/* zgodne z Ollama, bo wiele narzędzi zna tylko Ollamę)
                        ├─► engine worker(s): llama-server z naszej paczki (per GPU/arch), restart przy crashu
                        ├─► tuner (nocny job, niski priorytet, limity temp./mocy, przerwanie na aktywność użytkownika)
                        └─► updater (manifest Ed25519 → pobranie → weryfikacja → canary md5/KLD → przełączenie A/B)
```

- **Bezpieczeństwo:**
  - bind tylko do 127.0.0.1;
  - token per instalacja (dla aplikacji zewnętrznych wyświetlany w GUI);
  - walidacja `Host` i `Origin` (DNS rebinding, CVE-2024-28224), CORS domyślnie zamknięty;
  - endpointy „create/pull” bez dowolnych ścieżek (Probllama);
  - fuzzing parsera GGUF (Bleeding Llama);
  - tryb LAN tylko świadomie, z kluczem (tak robi Strata).
- **Port:** własny i unikalny, z fallbackiem. Nie 8080, 1234, 1337, 11434 ani 9931.
- **Usługa:** proces użytkownika z autostartem (Windows: tray, macOS: LaunchAgent, Linux: `systemd --user`), a nie usługa systemowa. Unika to UAC i root, a strojenie i tak działa przy zalogowanym użytkowniku. `[INFERENCE]`
- **Kompatybilność z ekosystemem:** OpenAI (chat + Responses) i Anthropic Messages to dziś standard (Strata, TensorFold, Lemonade). Emulacja `/api/*` Ollamy zwiększa zasięg, bo wiele integracji zna tylko Ollamę. Robi to Lemonade.

### 3.6 Packaging backendów GPU

**Plan dystrybucji:**

| Paczka | Kiedy | Rozmiar (szacunek z artefaktów upstream) | Uwagi |
|---|---|---|---|
| Base: app + daemon + CPU + **Vulkan** (Win/Linux) albo **Metal** (mac) | zawsze | ok. 40–60 MB | działa od razu na każdym GPU; daje „baseline speed” bez czekania |
| NVIDIA CUDA 13 | wykryto NVIDIA CC ≥ 7.5 i sterownik R580+ | ok. 150 MB build + ok. 400 MB runtime (cuBLAS/cuBLASLt) | runtime jako osobna, współdzielona i cache'owana paczka; rzadko się zmienia |
| NVIDIA CUDA 12 | Pascal, Volta, stary sterownik | ok. 250 + 373 MB | inaczej Vulkan (Jan tak zrobił) |
| AMD HIP per rodzina (gfx110X, gfx1151, gfx120X, gfx103X) | wykryto Radeon z listy ROCm | 183–654 MB (Lemonade), 604 MB (Strata, 2 archy) | **budowane z TheRock tylko dla danej rodziny**; fatbin wszystkich archów ma 947 MB |
| Intel | Arc / iGPU | Vulkan z base; SYCL (142 MB) opcjonalnie | dane z B70: Vulkan ≥ SYCL |
| Apple | M-series | Metal w base; **MLX jako opcja** (42–74 MB) | MLX zależnie od rozmiaru modelu |

- **Pobieranie:** po detekcji, w tle, z wznowieniem. Manifest podpisany Ed25519 wskazuje pliki content-addressed (sha256). Zasada „pobierz, sprawdź, przełącz”: nowa paczka staje się domyślna dopiero po lokalnym teście poprawności i A/B prędkości względem Vulkana. To nasza metoda w terenie.
- **Mniejsze buildy CUDA** przez ograniczenie `CMAKE_CUDA_ARCHITECTURES` per paczka. Do sprawdzenia, czy nasze ścieżki MMQ/MMVQ pozwalają pominąć cuBLASLt (470 MB). `[INFERENCE: wymaga pomiaru, bo prefill dużych batchy używa cuBLAS]`
- **Licencje:** CUDA tylko pliki z Attachment A, „as part of your application”. ROCm z plikami licencji i NOTICE (gotowy wzór: `tools/hip/package_windows.py` w Stracie). Unikamy AGPL (KoboldCpp, TabbyAPI) i ZLUDA.
- **AMD na Windows:** kładziemy `amdhip64_7.dll` i `amd_comgr.dll` obok exe. Strata #468/#461: DLL z niektórych sterowników w System32 crashowały w zestawieniu z bundlowanymi bibliotekami. Monitorujemy też bug eviction w Adrenalin 26.5.1+.

### 3.7 Auto-update, reprodukowalność, CI

- **Dwa kanały aktualizacji:**
  - aplikacja: Tauri updater (minisign) albo Velopack (delta);
  - silnik: własny manifest Ed25519 + SHA-256, klucz publiczny wkompilowany, feed nie do nadpisania przez env. To wzór z TensorFold `app-updates.md`.

  Silnik ma sloty A/B i automatyczny rollback, gdy po aktualizacji md5-canary lub tok/s spadnie poniżej poprzedniego wyniku na tej maszynie.
- **Reprodukowalność:**
  - toolchainy przypięte w kontenerach (wersja nvcc, data nightly TheRock, commit glslc z `GL_EXT_integer_dot_product`);
  - `BUILD.json` przy każdej paczce (jak Strata);
  - atestacje provenance (SLSA, GitHub artifact attestations lub Sigstore) `[INFERENCE: nie sprawdzałem szczegółów w tym raporcie]`.

  Bitowej reprodukowalności fatbinów nie obiecujemy. Obiecujemy **reprodukowalność wyników**: te same md5 greedy na referencyjnym GPU.
- **Macierz CI:**
  - kompilacja na GitHub-hosted runnerach (Windows, Ubuntu, macOS) dla każdej paczki;
  - GPU-testy (md5 gate, KLD gate, A/B tok/s) na self-hosted: nasza 7900 XTX plus wynajmowane NVIDIA (vast.ai, RunPod), plus Mac mini dla Metal i MLX;
  - GitHub GPU runners nie mają AMD.

  Minimalna macierz:

  | Wymiar | Wartości |
  |---|---|
  | NVIDIA | Ampere, Ada, Blackwell |
  | AMD | RDNA3, RDNA4, Strix Halo |
  | Intel | Arc B |
  | Apple | M-series |
  | Backendy | Vulkan oraz natywny dla każdej z powyższych |

### 3.8 Rekomendowany stack w skrócie

| Warstwa | Wybór | Alternatywa | Dlaczego |
|---|---|---|---|
| Silnik | llama.cpp **thin overlay** na tagach semver; per-arch paczki silnika; tuning w danych | MLX na Macu (faza 2); turbo-silnik per model (faza 3) | pokrycie „dowolny model i GPU” bez etatu na rebase |
| Rdzeń/daemon | **Rust**; silnik jako proces potomny | Go (wzór Ollama) | jeden język GUI/TUI/daemon, bezpieczeństwo parserów |
| GUI | **Tauri 2** + TS | Electron | instalator <40 MB, minisign, sidecar |
| TUI/CLI | **ratatui** | Bubble Tea | ten sam kod domenowy |
| API | OpenAI (chat + Responses) + Anthropic Messages (+ Ollama `/api`) na 127.0.0.1 z tokenem | — | standard rynku; lekcje z CVE Ollamy |
| Dystrybucja | base Vulkan/Metal/CPU, paczki CUDA/HIP po detekcji | wszystko w paczce (Ollama, 1,5 GB) | wzór Lemonade (10 MB) i LM Studio |
| Update | Tauri updater / Velopack + manifest silnika Ed25519, A/B + canary | electron-updater | weryfikacja poprawności jako część aktualizacji |
| Podpis | Apple Developer ID ($99/rok) + Azure Artifact Signing (spółka w UE) | OV cert | individual poza USA/CA nie kwalifikuje się |
| CI | GH-hosted build + self-hosted GPU (nasze + wynajem) | — | brak AMD w GH GPU runners |

### 3.9 Ryzyka

1. **Tempo upstreamu.** Patch-set per arch rozjeżdża się co tydzień (33 z 69 plików w 6 dni). Mitigacja: budżet patchy, rebase per semver, automatyczne wyłączanie patchy, które nie przechodzą bramki.
2. **NVIDIA sama optymalizuje llama.cpp** („do 1,9×” na 5090), więc nasz margines na NVIDIA może być mały. Największa przewaga będzie na AMD, Intel i może Apple. To trzeba uwzględnić w komunikacji „60 → 110 t/s”, żeby nie obiecywać tego na każdej karcie. `[INFERENCE]`
3. **Sterowniki AMD na Windows:** DLL w System32 i eviction VRAM w Adrenalin 26.5.1+. HIP na Windows to wciąż „beta-jakość” poza RDNA3/4. Vulkan jako bezpieczny fallback.
4. **Bezpieczeństwo daemona.** Każdy lokalny serwer LLM jest celem (historia Ollamy, CVE w mistral.rs).
5. **Podpisy.** Utrata klucza updatera oznacza „martwe” instalacje (dokumentacja Tauri), więc klucze trzymamy w HSM lub KMS z kopią offline.
6. **Polityka AI w llama.cpp.** Agentowy pipeline nie może automatycznie wysyłać PR-ów.
7. **Licencja Jana „NOASSERTION”.** Nie kopiujemy jego kodu bez weryfikacji licencji.

### 3.10 Otwarte pytania

1. Czy `llama-server` z router mode wystarczy jako proces silnika, czy potrzebujemy własnego hosta na `libllama` (stany spekulacji, nasze endpointy diagnostyczne)? Decyzję podjąć po prototypie.
2. Które z naszych 70 patchy są czysto runtime-parametryzowalne (tabele wierszy, wybór ścieżki), a które wymagają kodu? Od tego zależy, ile da „optymalizacja na noc” bez pobierania nowej paczki.
3. Czy redystrybucja NVRTC i hipRTC (runtime kompilacja kerneli) jest dozwolona i opłacalna rozmiarowo (EULA, rozmiar DLL)? `[INFERENCE: niesprawdzone]`
4. Czy na NVIDIA stosujemy MMQ-only bez cuBLASLt, żeby zmniejszyć paczkę o ok. 450 MB? Wymaga pomiaru prefillu.
5. MLX na Macu: przy jakim rozmiarze modelu przełączać się z llama.cpp na MLX? Dane rozbieżne (+87% na 0,6B, parytet przy 27B+).
6. Czy budujemy własne paczki ROCm z TheRock (jak Strata i Lemonade), czy bierzemy gotowe z `lemonade-sdk/llamacpp-rocm` (MIT) jako bazę? To drugie skraca start, ale wiąże nas z ich cyklem.

---

## 4. Źródła

**Lokalne**
- `~/KERNEL/qwen-opt/research/strata/{README,update-v0.1.44}.md`
- `~/KERNEL/qwen-opt/research/tensorfold/{README,update-v1.0.11}.md`
- `~/KERNEL/qwen-opt/research/repos/{22-lucebox,30-hipfire}.md`
- `~/llama-master` (git, tylko odczyt)
- `~/KERNEL/qwen-opt/patches/llama.cpp-amd-opt/`
- `~/research/Strata`:
  - `docs/DETAILS.md`
  - `docs/AMD_HIP.md`
  - `tools/hip/package_windows.py`
- `~/research/TensorFold`:
  - `app/build/engine.json`
  - `.zig-version`

**Strata / TensorFold**
- https://github.com/niko1221/strata
- https://github.com/Niko1221/Strata/releases/tag/v0.1.44.1
- https://github.com/ashhart/TensorFold
- https://github.com/ashhart/TensorFold/releases
- https://tensorfold.dev/
- https://raw.githubusercontent.com/ashhart/TensorFold/main/app/docs/app-updates.md
- https://raw.githubusercontent.com/ashhart/TensorFold/main/app/README.md

**Rodzina llama.cpp**
- https://github.com/ggml-org/llama.cpp
- https://github.com/ggml-org/llama.cpp/releases/tag/v0.7.0
- https://github.com/ggml-org/llama.cpp/releases/tag/b11671
- https://github.com/ggml-org/llama.cpp/releases/expanded_assets/b11669
- https://github.com/ggml-org/llama.cpp/releases/expanded_assets/b11500
- https://github.com/ggml-org/llama.cpp/releases/tag/b11236
- https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md
- https://github.com/ggml-org/llama.cpp/blob/master/CONTRIBUTING.md
- https://github.com/ggml-org/llama.cpp/blob/master/AGENTS.md
- https://github.com/ggml-org/llama.cpp/tree/master/.github/workflows
- https://github.com/ggml-org/llama.cpp/issues/20934
- https://github.com/ggml-org/llama.cpp/discussions/10879
- https://github.com/ggml-org/llama.cpp/discussions/23443
- https://github.com/ggml-org/ggml/releases/tag/v0.27.0
- https://huggingface.co/blog/ggml-joins-hf
- https://explainx.ai/blog/llama-cpp-decision-model-support-2026
- https://github.com/ikawrakow/ik_llama.cpp
- https://github.com/ikawrakow/ik_llama.cpp/discussions/164
- https://github.com/Kaden-Schutt/hipfire
- https://raw.githubusercontent.com/warpfront/hipfire/master/LICENSE
- https://github.com/warpfront/hipfire/releases/tag/v0.4.0
- https://github.com/Luce-Org/lucebox
- https://arxiv.org/abs/2602.06036
- https://github.com/z-lab/dflash
- https://github.com/ollama/ollama/releases
- https://github.com/ollama/ollama/issues/9959
- https://jonathanding.github.io/llm-learning/en/articles/ollama-architecture/
- https://ollama.com/blog/new-app
- https://docs.ollama.com/faq
- https://lmstudio.ai/docs/cli/runtime/runtime
- https://lmstudio.ai/blog/lmstudio-v0.3.16
- https://lmstudio.ai/docs/developer/core/headless
- https://www.techspot.com/downloads/7719-lm-studio.html
- https://github.com/janhq/jan
- https://github.com/janhq/jan/releases/tag/v0.8.5
- https://github.com/lemonade-sdk/lemonade
- https://github.com/lemonade-sdk/llamacpp-rocm/releases
- https://github.com/LostRuins/koboldcpp/releases
- https://github.com/mozilla-ai/llamafile
- https://github.com/nomic-ai/gpt4all/discussions/3649
- https://github.com/utilityai/llama-cpp-rs

**Inne silniki**
- https://github.com/turboderp-org/exllamav3/releases/tag/v1.6.0
- https://github.com/turboderp-org/exllamav2
- https://github.com/theroyallab/tabbyAPI/
- https://atomic.chat/blog/guides/exl3-vs-gguf
- https://github.com/mlc-ai/mlc-llm
- https://llm.mlc.ai/docs/install/mlc_llm
- https://github.com/mlc-ai/llm-perf-bench
- https://docs.mistralrs.dev/reference/hardware-support/
- https://github.com/EricLBuehler/mistral.rs/releases/tag/v0.9.4
- https://lib.rs/crates/candle-core
- https://github.com/huggingface/candle/pull/3801
- https://github.com/Tiiny-AI/PowerInfer
- https://arxiv.org/html/2507.20984v2
- https://github.com/kvcache-ai/ktransformers
- https://github.com/vllm-project/vllm/releases
- https://github.com/vllm-project/vllm/issues/28649
- https://computingforgeeks.com/ollama-vs-vllm-vs-llama-cpp/
- https://digtvbg.com/blog/llama-server-vulkan-rdna4-vllm-rocm-benchmark/
- https://github.com/google-ai-edge/LiteRT-LM
- https://github.com/pytorch/executorch
- https://github.com/alibaba/mnn
- https://arxiv.org/pdf/2506.10443

**Stosy producentów**
- https://nvidia.github.io/TensorRT-LLM/release-notes.html
- https://docs.nvidia.com/deeplearning/tensorrt-rtx/latest/architecture/architecture-overview.html
- https://pypi.org/project/tensorrt-rtx/
- https://developer.nvidia.com/blog/optimizing-llama-cpp-ai-inference-with-cuda-graphs
- https://blogs.nvidia.com/blog/local-ai-ifa-next-gen-agents-nv-pair-rtx-spark/
- https://github.com/microsoft/onnxruntime-genai
- https://learn.microsoft.com/en-us/windows/ai/directml/dml-get-started
- https://learn.microsoft.com/en-us/windows/ai/new-windows-ml/supported-execution-providers
- https://github.com/microsoft/foundry-local
- https://docs.openvino.ai/2026/about-openvino/release-notes-openvino.html
- https://www.phoronix.com/news/OpenVINO-2026.1-Released
- https://github.com/intel/ipex-llm/wiki/
- https://jonathanmann.tech/blog/intel-arc-b70-llama-cpp-benchmarks/
- https://pypi.org/project/mlx/
- https://terminalbytes.com/ollama-vs-llama-cpp-vs-mlx-mac-2026/
- https://blog.starmorph.com/blog/apple-silicon-llm-inference-optimization-guide
- https://github.com/vicnaum/local-llm-bench-m4-32gb/blob/main/results/engine_comparison.md
- https://vosen.github.io/ZLUDA/blog/zluda-update-q1q2-2026/
- https://rocm.docs.amd.com/projects/install-on-windows/en/latest/reference/system-requirements.html
- https://github.com/ROCm/TheRock/blob/main/README.md
- https://github.com/ROCm/TheRock/blob/main/RELEASES.md
- https://rocm.docs.amd.com/en/latest/about/license.html
- https://www.club386.com/amd-adrenalin-edition-26-1-1-driver-ai-bundle/
- https://llmrequirements.com/cuda-vs-vulkan-llama-cpp
- https://www.phoronix.com/news/NVIDIA-Vulkan-AI-ML-Success
- https://freenode.net/article/llama-cpp-speeds-amd-rdna3-4-inference-with-vulkan-int8-coopmat
- https://github.com/chaosmonkies/llamacpp-vulkan-intel-arc-slow-quant
- https://www.phoronix.com/news/AMDVLK-Discontinued
- https://docs.nvidia.com/cuda/pdf/EULA.pdf
- https://developer.nvidia.com/blog/whats-new-and-important-in-cuda-toolkit-13-0/

**Aplikacja / release engineering**
- https://v2.tauri.app/blog/tauri-2.12/
- https://v2.tauri.app/plugin/updater/
- https://v2.tauri.app/develop/sidecar/
- https://github.com/phase-rs/phase/issues/8614
- https://github.com/xnmp/tauri-explorer/issues/1057
- https://hackernoon.com/six-months-with-tauri-the-benefits-and-the-bill
- https://tech-insider.org/tauri-vs-electron-desktop-app-framework-2026/
- https://github.com/Elanis/web-to-desktop-framework-comparison
- https://github.com/lmstudio-ai/lmstudio-bug-tracker/issues/1144
- https://rustify.rs/articles/rust-tauri-vs-flutter-2026
- https://www.qt.io/development/qt-for-small-business
- https://www.phoronix.com/news/AMD-GAIA-0.17-Agent-UI
- https://ratatui.rs/highlights/v030/
- https://pkg.go.dev/charm.land/bubbletea/v2
- https://github.com/Textualize/textual/releases
- https://nvd.nist.gov/vuln/detail/cve-2024-28224
- https://nvd.nist.gov/vuln/detail/CVE-2024-37032
- https://nvd.nist.gov/vuln/detail/CVE-2026-7482
- https://blogs.cisco.com/security/detecting-exposed-llm-servers-shodan-case-study-on-ollama
- https://research.opena2a.org/reports/april-2026-exposure-sweep
- https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution
- https://azure.microsoft.com/en-us/products/artifact-signing
- https://learn.microsoft.com/en-us/azure/artifact-signing/quickstart
- https://learn.microsoft.com/en-us/azure/artifact-signing/faq
- https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation
- https://docs.github.com/en/billing/reference/actions-runner-pricing
- https://github.com/velopack/velopack
- https://crates.io/crates/velopack
