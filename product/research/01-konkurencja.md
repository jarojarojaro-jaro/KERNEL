# 01. Konkurencja: konsumenckie i prosumenckie aplikacje do lokalnych LLM (stan na 2026-10-15)

Zakres: wszystkie istotne aplikacje i launchery lokalnych LLM, narzędzia producentów sprzętu, nowe projekty 2025–2026, „sprzedawcy optymalizacji”, bóle użytkowników oraz analogie „zostaw na noc, będzie szybciej”.

Konwencje:
- `[INFERENCE]` oznacza mój wniosek albo dane niezweryfikowane u źródła pierwotnego.
- `[stale?]` oznacza źródło starsze niż 12 miesięcy (sprzed 2025-10).
- Gwiazdki GitHub odczytałem ze stron repozytoriów 2026-10-15.
- Liczby z naszego setupu pochodzą z `~/KERNEL/qwen-opt/README.md` i `NOTES.md`.
- Materiały robocze (EN, z pełnymi linkami) leżą w artefaktach sesji: `r1-main-apps.md`, `r1-oss-tools.md`, `r1-vendors.md`, `r1-new-and-optimizers.md`, `r1-pain-analogs.md`.

---

## 1. TL;DR

- **Detekcja sprzętu i rekomendacja modelu to już standard, nie wyróżnik.** Robią to wszyscy:
  - LM Studio: badge „fits”, guardrails;
  - Jan: Fits / May be slow / Won't fit;
  - Ollama: dokładny pomiar pamięci przed załadowaniem;
  - llama.cpp: `--fit` domyślnie włączone od 12.2025;
  - Foundry Local: wariant modelu per sprzęt;
  - Hermes Desktop: badge zielony/żółty/czerwony;
  - llmfit (38k★) jako osobne narzędzie.

  Nasz krok „skan → rekomendacja → pobranie → start” jest tylko biletem wstępu.
- **Żaden produkt dla konsumenta nie robi tego, co planujemy.** Nikt nie łączy w jednym:
  - pomiaru bazowej prędkości na maszynie użytkownika;
  - długiej, nienadzorowanej optymalizacji wykraczającej poza flagi (kernele, scheduler, spekulacja);
  - weryfikacji bitowej;
  - raportu przed → po;
  - obsługi wielu producentów GPU, z AMD w pierwszej kolejności.

  Zweryfikowałem to dla LM Studio, Ollamy, Jana, GPT4All, Msty, AnythingLLM, KoboldCpp, llamafile, LocalAI, Open WebUI, TextGen, Pinokio, Lemonade, Foundry Local, narzędzi NVIDIA i Intela oraz aplikacji na Apple.
- **Najbliżej luki są cztery grupy, każda pokrywa tylko kawałek:**
  1. **Flag-tunery dla llama.cpp:**
     - TurboLLM (285★, FSL-1.1): mierzy na starcie i dobiera warstwy, MoE offload, KV quant i sampling. Na tej samej llama.cpp co LM Studio daje 74.7 vs 61 t/s.
     - ggrun (280★, MIT): opcja `--ai-tune`.
     - llm-autotune (34★): poprawia TTFT, prędkości generowania nie zmienia.
     - llama-optimus: Optuna nad flagami.
  2. **Silniki pod jeden model z kalibracją:**
     - Strata (25.4k★, MIT): one-click, `--calibrate` stroi 4 parametry runtime, ale tylko dla Qwen3.8-Flash-Next.
     - MTPLX (2.6k★, tylko Mac): mierzy optymalną głębokość MTP i pokazuje przed → po (14.4 → 23.0 tok/s).
  3. **AMD Lemonade, grupa robocza „Auto-Tune”:** roadmapa profili per archetyp sprzętu i benchmarków od społeczności. Nic jeszcze nie wydano.
  4. **NVIDIA TensorRT for RTX, „adaptive inference”:** „performance improves over time”, ale to SDK dla deweloperów, tylko NVIDIA i tylko ONNX.
- **Popyt na „szybciej na moim sprzęcie” jest twardo udokumentowany:**
  - Strata zebrała 25.4k★ na obietnicy „125B na twoim gamingowym PC”, a jej historia commitów obejmowała 19 dni na dzień 2026-10-12 (`research/strata/README.md:3`). Tempo ok. 1k★/dzień to `[INFERENCE]`;
  - oMLX ma 22.8k★;
  - llmfit ma 38k★;
  - w trackerze Ollamy jest 190 issues ze „slow” w tytule i 165 z etykietą `amd`.
- **Typowe bóle użytkowników:**
  - GPU wykryte, a model liczy się na CPU (szczególnie AMD, APU i iGPU);
  - regresje prędkości po aktualizacjach (Ollama, LM Studio, KoboldCpp);
  - „loteria backendów” na AMD i Intelu: Vulkan często bije ROCm/SYCL w generowaniu;
  - ukryte domyślne ustawienia (num_ctx 2–4k, Q4), przez które modele „wydają się głupie”;
  - paraliż wyboru kwantyzacji.
- **Producenci sprzętu nie chcą mieć własnej aplikacji LLM dla konsumentów:**
  - NVIDIA zamknęła ChatRTX 2026-01-21 i wnosi przyspieszenia do llama.cpp, Ollamy i LM Studio (do 1.9× na RTX 5090);
  - AMD dołącza Ollamę i LM Studio do sterownika („AI Bundle”, 01.2026);
  - Intel zarchiwizował IPEX-LLM 2026-01-28.

  Producenci są więc raczej kanałem dystrybucji niż konkurentem, ale stale podnoszą bazę porównania.
- **Pieniądze:**
  - optymalizację inferencji sprzedaje się dziś wyłącznie B2B i do datacenter: Standard Kernel ($20M seed), Makora ($8.5M), Gimlet ($300M Series B), przejęcia OctoAI, Deci i CentML przez NVIDIA;
  - konsumenci płacą za UX, nie za prędkość: Msty $149/rok lub $349 lifetime, Private LLM $4.99, Ollama Cloud $20–$100/mies.;
  - gotowość płacenia za „szybciej” jest niezweryfikowana.
- **Najgroźniejszy scenariusz:** LM Studio, Ollama albo Jan automatycznie włączają i stroją spekulację (MTP/DFlash) oraz wybór backendu. Nasze notatki pokazują, że zwykły upstream llama.cpp z ręcznie włączoną spekulacją daje na 7900 XTX 68.6 t/s (MTP, ROCm), 85.6 t/s (MTP, Vulkan, mieszanka EN+PL) i 97.7 t/s (DFlash2). Nasze kernele dokładają do tego +10–25% (82.3 i 111–112 t/s). Większość różnicy między „domyślnie ~37–48 t/s” a „109 t/s” jest zatem osiągalna samą konfiguracją, a tę może skopiować każdy flag-tuner `[INFERENCE]`.
- **Analogie z gamingu i Androida pokazują, że konsumenci akceptują „skan, potem szybciej”:**
  - NVIDIA Automatic Tuning trwa 10–20 min, MSI OC Scanner ok. 30 min;
  - CoreCycler chodzi przez noc;
  - Android ART kompiluje w nocy, gdy telefon jest bezczynny i się ładuje.

  Są też dobre wzorce dzielenia wyników między użytkowników: Steam shader cache per GPU+driver, Microsoft Advanced Shader Delivery, profile chmurowe ART, optymalne ustawienia w GeForce Experience. To bezpośredni szablon dla współdzielonych konfiguracji per (GPU, driver, model, quant).

---

## 2. Ustalenia

### 2.1 Główna tabela porównawcza: profil, detekcja, tuning

Legenda kolumny „Auto-tuning”:
- **0**: brak;
- **M**: tylko dopasowanie pamięci (offload, kontekst);
- **R**: reguły ze specyfikacji, bez pomiaru;
- **F**: empiryczne strojenie flag (pomiar t/s);
- **K**: strojenie kerneli lub JIT na maszynie użytkownika.

| Produkt | Dla kogo | Platformy / GPU | Silnik | Detekcja HW i rekomendacja | Auto-tuning | Prędkość w UI |
|---|---|---|---|---|---|---|
| **LM Studio** 0.4.26 ([changelog](https://lmstudio.ai/changelog/lmstudio)) | prosumenci, deweloperzy, firmy | macOS (Apple Silicon), Win x64/ARM, Linux x64/ARM. CUDA 11/12/13, ROCm, Vulkan, MLX ([sysreq](https://lmstudio.ai/docs/app/system-requirements)) | zamknięty „llm-engine” na llama.cpp + MIT [mlx-engine](https://github.com/lmstudio-ai/mlx-engine) | badge „full GPU offload” per quant (ignoruje kontekst, [runaihome](https://runaihome.com/blog/lm-studio-failed-to-load-model-fix-2026/)), guardrails blokujące load ([0.3.27](https://lmstudio.ai/blog/lmstudio-v0.3.27)), staff picks | **M**. Spekulacja i MTP (0.4.14), DFlash (0.4.22) to ręczne toggle. FA, KV, wątki i n_cpu_moe to suwaki ([0.4.0](https://lmstudio.ai/blog/0.4.0)) | t/s i TTFT per wiadomość; API zwraca statystyki, żeby użytkownik „mógł sam stroić” ([0.4.0](https://lmstudio.ai/blog/0.4.0)) |
| **Ollama** v0.40.5 ([release](https://github.com/ollama/ollama/releases/tag/v0.40.5)) | deweloperzy i agenci; od 07.2025 także GUI Mac/Win | NVIDIA CC 5.0+, AMD ROCm (Linux; Windows tylko RX 7600–7900 XTX), Vulkan domyślnie dla reszty, Metal/MLX ([docs/gpu](https://docs.ollama.com/gpu)) | własny silnik Go + ggml; MLX na Macu od 0.19 ([blog](https://ollama.com/blog/mlx)) | auto-wykrycie GPU; od 09.2025 dokładny pomiar pamięci przed load ([blog](https://ollama.com/blog/new-model-scheduling)) [stale?] | **M**. FA włącza się automatycznie, KV quant to ręczny env globalny ([FAQ](https://docs.ollama.com/faq)) | `--verbose` w CLI [INFERENCE]; GUI bez t/s |
| **Jan** v0.8.6 ([changelog](https://www.jan.ai/changelog)) | prywatność, „ChatGPT offline” | Win/Mac/Linux. CUDA, Vulkan, ROCm na Linuxie (od 0.8.2), Metal, MLX | llama.cpp (router) + MLX | Hub: Fits / May be slow / Won't fit, grupy Small/Balanced/Large ([v0.8.0](https://www.jan.ai/changelog/2026-05-22-jan-v0.8.0)) | **R**. „Auto Optimize (Experimental)” od v0.6.10 to reguły ze specyfikacji, bez pomiaru ([changelog](https://www.jan.ai/changelog/2025-09-18-auto-optimize-vision-imports)) [stale?]. MTP ręcznie | statystyki modelu i kontekstu |
| **GPT4All** v3.10.0 (02.2025) | nietechniczni, laptopy CPU | Win/Mac/Linux. Vulkan, CUDA, Metal | fork llama.cpp | galeria z wymaganiami RAM [INFERENCE] | **0** | t/s [INFERENCE] |
| **Msty Studio** ([pricing](https://msty.ai/pricing/)) | knowledge workers | Win/Mac/Linux + web | Ollama pod spodem, także llama.cpp i MLX | Model Hub | **0** | „Response Metrics” (limit w Free) |
| **AnythingLLM** desktop 1.18 ([repo](https://github.com/Mintplex-Labs/anything-llm)) | RAG i agenci dla osób i małych firm | Win/Mac/Linux, ARM. NPU przez Qualcomm GenieX i Foundry Local | Lemonade + llama.cpp, Foundry, GenieX albo zewnętrzny | wybór silnika per producent; Foundry ładuje model według możliwości sprzętu ([v1.16.1](https://docs.anythingllm.com/changelog/v1.16.1)) | **0** | słabo widoczna [INFERENCE] |
| **KoboldCpp** v1.120 ([repo](https://github.com/LostRuins/koboldcpp)) | hobbyści, roleplay, SillyTavern | Win/Linux/macOS ARM. CUDA, Vulkan, ROCm (fork [YellowRoseCx](https://github.com/YellowRoseCx/koboldcpp-rocm), 780★) | fork llama.cpp + sd.cpp + whisper.cpp | GUI launcher, „Newbie Templates” ([HF](https://huggingface.co/koboldcpp/newbie-templates)) | **M** (AutoFit przy `--gpulayers -1`, [wiki](https://github.com/LostRuins/koboldcpp/wiki)) | `--benchmark` do CSV |
| **llamafile** 0.10.6 ([release](https://github.com/mozilla-ai/llamafile/releases/tag/0.10.6)) | dystrybucja modelu jako jednego pliku | Cosmopolitan, wszystkie OS | llama.cpp | brak | **0** (dziedziczy `--fit` [INFERENCE]) | zawiera LocalScore |
| **llama.cpp** (`llama serve`, web UI) ([repo](https://github.com/ggml-org/llama.cpp)) | baza dla wszystkich | wszystko | — | `--fit` domyślnie: zmniejsza ctx, przenosi tensory do RAM z uwzględnieniem MoE ([PR #16653](https://github.com/ggml-org/llama.cpp/pull/16653), [disc. #18049](https://github.com/ggml-org/llama.cpp/discussions/18049)); `-ngl auto` ([llama.app](https://llama.app/docs/serve)) | **M**. Maintainer: „llama_fit_params already does this” ([#21053](https://github.com/ggml-org/llama.cpp/discussions/21053)) | logi i web UI |
| **TextGen** (dawniej text-generation-webui) ([repo](https://github.com/oobabooga/textgen)) | power users | portable: CUDA, ROCm, Vulkan, Mac, CPU | llama.cpp (portable), więcej loaderów w pełnej wersji | instalator wybiera build [INFERENCE] | **0** | tak |
| **Open WebUI** ([repo](https://github.com/open-webui/open-webui)) | front-end do dowolnego serwera | web | brak własnego | brak | **0** | — |
| **Pinokio** 8.0.40 ([repo](https://github.com/pinokiocomputer/pinokio)) | nietechniczni, one-click dla 200+ aplikacji AI | Win/Mac/Linux | skrypty instalacyjne | zmienne `{{gpu}}`, `{{vram}}` do wyboru buildu PyTorch/CUDA | **0** | nie |
| **LocalAI** 4.1 ([repo](https://github.com/mudler/LocalAI)) | self-hosterzy | CUDA, ROCm, SYCL, Metal, Vulkan, Jetson | multi-backend | auto-wybór builda backendu po wykryciu GPU ([docs](https://localai.io/docs/features/gpu-acceleration/)) | **0** | — |
| **Docker Model Runner** ([docs](https://docs.docker.com/ai/model-runner/)) | deweloperzy | llama.cpp (NVIDIA/AMD/Apple/Vulkan), vLLM (tylko NVIDIA) | llama.cpp, vLLM | auto-Vulkan albo CPU ([blog](https://www.docker.com/blog/docker-model-runner-vulkan-gpu-support/)) | **0** | — |
| **RamaLama** (Red Hat) ([repo](https://github.com/containers/ramalama)) | dev/ops (Podman) | kontener dobrany do GPU | llama.cpp, vLLM | `--backend auto` | **0** | `ramalama bench` |
| **llama-swap** ([repo](https://github.com/mostlygeek/llama-swap)) | homelab | dowolny serwer | proxy | brak | **0** | — |
| **Nexa SDK → Qualcomm GenieX** ([repo](https://github.com/qualcomm/GenieX)) | deweloperzy Snapdragon | Hexagon NPU, Adreno, CPU | llama.cpp + paczki QNN | wybór runtime | **0** | — |
| **cortex.cpp** | — | — | — | — | **zarchiwizowany 2025-07-04** ([repo](https://github.com/janhq/cortex.cpp)) | — |
| **Backyard AI (Faraday)** | companion | desktop porzucony 2025-06-25, teraz chmura ([changelog](https://backyard.ai/changelog)) | — | — | — | — |
| **LocalScore** ([site](https://www.localscore.ai)) | benchmark sprzętu | — | llamafile | — | mierzy tylko domyślną prędkość: score = 10·∛(pp·tg·1000/TTFT) ([README](https://github.com/mozilla-ai/llamafile/blob/main/localscore/README.md)) | tak |

**Producenci i platformy:**

| Produkt | Dla kogo | Sprzęt | Silnik | Detekcja i wybór | Auto-tuning | Uwagi |
|---|---|---|---|---|---|---|
| **AMD Lemonade** ([repo](https://github.com/lemonade-sdk/lemonade)) | deweloperzy i power users | ROCm, Vulkan, CUDA, Metal, CPU; NPU (FLM, ryzenai-llm); HRX (gfx1100/gfx1151, Linux, eksperymentalny) | llama.cpp, vLLM-ROCm, OGA | wykrywa sprzęt i wybiera backend (ROCm dla RX 7000/9000, Vulkan dla iGPU, [AMD](https://www.amd.com/en/developer/resources/technical-articles/2026/lemonade-for-local-ai.html)). Bug: dGPU+iGPU dostaje zły pakiet ([#2705](https://github.com/lemonade-sdk/lemonade/issues/2705)) | **0 (w planach F)**. Auto-Tune WG, 5 faz, wszystkie checkboxy otwarte ([WG](https://lemonade-server.ai/docs/dev/working-groups/auto-tune/)) | HRX: +30–50% prefill, ≤+10% decode ([daily.dev/Phoronix](https://daily.dev/posts/lemonade-11-9-local-ai-server-released-with-super-exciting-amd-rocm-hrx-backend-oqelo2sdt)) |
| **AMD GAIA / AMD Chat / AI Bundle** | konsumenci Ryzen AI i Radeon | Ryzen AI 300+, RX 9000 | Lemonade; AMD Chat na ROCm | AI Bundle w sterowniku 26.1.1 instaluje Ollamę, LM Studio i ComfyUI ([AMD](https://www.amd.com/en/blogs/2026/amd-software-adrenalin-edition-ai-bundle-ai-made-si.html)) | **0** | AMD dystrybuuje cudze aplikacje |
| **MS Foundry Local** v2.0.1 ([repo](https://github.com/microsoft/Foundry-Local)) | deweloperzy aplikacji | Win, macOS; CUDA, NPU, WebGPU, CPU | ORT GenAI | alias → wariant według priorytetu, dobierany do sprzętu ([CLI ref](https://learn.microsoft.com/en-us/azure/foundry-local/reference/reference-cli)) | **0**; modele kwantyzowane przez MS offline | „may collect usage data” |
| **Windows ML** (GA 2025-09) ([blog](https://blogs.windows.com/windowsdeveloper/2025/09/23/windows-ml-is-generally-available-empowering-developers-to-scale-local-ai-across-windows-devices/)) [stale?] | deweloperzy | Win11 24H2 | ORT + EP od producentów | sam pobiera EP: Vitis AI, OpenVINO, QNN, TensorRT-RTX ([MS Learn](https://learn.microsoft.com/en-us/windows/ai/new-windows-ml/initialize-execution-providers)) | to, co robi EP | — |
| **NVIDIA ChatRTX** | — | — | TRT-LLM | — | — | **porzucony 2026-01-21** ([forum](https://forums.developer.nvidia.com/t/chatrtx-has-been-deprecated-this-forum-is-locked/365743)) |
| **NVIDIA G-Assist** ([page](https://www.nvidia.com/en-us/software/nvidia-app/g-assist/)) | gracze | RTX 20–50 z ≥6 GB | lokalny SLM 8B | — | stroi gry i GPU (DLSS, OC do +60 MHz, wentylatory), **nie LLM** | — |
| **NVIDIA App „Automatic Tuning”** | gracze | RTX | — | — | OC scan 10–20 min ([KitGuru](https://www.kitguru.net/gaming/joao-silva/nvidia-app-now-lets-you-automatically-overclock-your-gpu-without-voiding-the-warranty/)) [stale?] | wzorzec UX „skan → szybciej” |
| **TensorRT for RTX** 1.7 ([docs](https://docs.nvidia.com/deeplearning/tensorrt-rtx/latest/index.html)) | deweloperzy | Turing–Blackwell | TRT | — | **K**: JIT na PC użytkownika <30 s, „adaptive inference”, kernele pod kształty, cache runtime: „performance improves over time”, 1.32× na FLUX ([blog 2026-01-26](https://developer.nvidia.com/blog/adaptive-inference-in-nvidia-tensorrt-for-rtx-enables-automatic-optimization)) | tylko ONNX; brak UI konsumenckiego |
| **NVIDIA NIM for RTX / AI Workbench** | deweloperzy | RTX | TRT-LLM | engine per klasa GPU [INFERENCE] | **0** | — |
| **NVIDIA PAIR** (beta) ([blog](https://blogs.nvidia.com/blog/local-ai-ifa-next-gen-agents-nv-pair-rtx-spark/)) | wiele PC w domu | RTX 20+, Spark, Apple M4+ | router dla Ollamy i LM Studio | wykrywa PC w LAN | routing, nie tuning | Apache-2.0 |
| **Hermes Desktop** (Nous) ([docs](https://hermes-agent.nousresearch.com/docs/guides/local-ollama-setup)) | użytkownicy agentów | CUDA, Metal, Vulkan, HIP, CPU | zarządzana llama.cpp | wykrywa GPU, dobiera model i konfigurację, badge zielony/żółty/czerwony ([marktechpost](https://www.marktechpost.com/2026/09/05/nous-research-hermes-desktop-one-click-local-model-setup/)) | **M** | wspierany przez NVIDIA |
| **OpenClaw Windows** ([blog](https://openclaw.ai/blog/macos-installer-windows-local-ai)) | użytkownicy agentów | RTX ≥24 GB | llama.cpp | auto-setup „modelu dostrojonego do sprzętu” (w praktyce wybór modelu) | **M/R** [INFERENCE] | 380k★ (OpenClaw) |
| **Intel AI Playground** 3.2 beta ([repo](https://github.com/intel/AI-Playground)) | konsumenci Intel AI PC | Arc, Core Ultra; RTX eksperymentalnie | llama.cpp Vulkan, OpenVINO, ComfyUI | użytkownik **sam wybiera** tryb w kreatorze | **0** | 1.0k★ |
| **OpenVINO AUTO** ([docs](https://docs.openvino.ai/2025/openvino-workflow/running-inference/inference-devices-and-modes/auto-device-selection.html)) | deweloperzy | CPU, GPU, NPU Intel | OpenVINO | wybór urządzenia | **0** | — |
| **IPEX-LLM** | — | Arc | — | — | — | **zarchiwizowany 2026-01-28** ([repo](https://github.com/intel/ipex-llm/tree/main/python/llm)) |
| **Ollama MLX / LM Studio MLX** | użytkownicy Maca | Apple Silicon (MLX dopiero od ≥32 GB) | MLX | — | **0** | Ollama MLX: 58 → 112 t/s na M5 Max jako „update story” ([blog](https://ollama.com/blog/mlx)) |
| **Private LLM** ([site](https://privatellm.app/en)) | iOS/Mac | Apple | własny (OmniQuant/GPTQ) | — | **0** (konkuruje jakością kwantyzacji) | $4.99 jednorazowo |
| **Locally AI → LM Studio**, **Apollo → Liquid AI**, **PocketPal** (8.6k★), **Enchanted**, **Osaurus** (8.0k★), **Apple Foundation Models** | mobile / Mac | Apple, Android | MLX, llama.cpp, LEAP, Apple FM | — | **0** | przejęcia: [LM Studio](https://lmstudio.ai/blog/locally-ai-joins-lm-studio), [Liquid](https://www.businesswire.com/news/home/20250715701268/en/Liquid-AI-Launches-LEAP-and-Apollo-A-New-Era-for-Edge-AI-Deployment-Begins) [stale?] |

**Nowe projekty nastawione na prędkość i auto-tunery (najbliższa konkurencja):**

| Produkt | Dla kogo | Sprzęt | Co jest automatyczne | Poziom | Prędkość / przed → po | Licencja, trakcja |
|---|---|---|---|---|---|---|
| **Strata** ([repo](https://github.com/Niko1221/Strata)) | gracze i nietechniczni („Run a 125B model on your gaming PC”) | NVIDIA RTX 20–50, AMD RX 6800–9070 / R9700 ≥12 GB, Win/Linux; Mac, Arc i Strix Halo eksperymentalnie | `START-HERE.bat` wykrywa kartę i dobiera rozmiar do RAM; tryb „Let your AI set it up” (`docs/AI_SETUP.md`); `--calibrate` stroi pcie-frac, spec-min-p, pool-workers i adapt-* przy progu >3% | **F** (runtime), jeden model | `BENCH.bat`, monitor t/s, tabele „Writes answers / Reads your prompt” w README | MIT, **25.4k★, 2.6k forków**, darowizny (Buy Me a Coffee) |
| **MTPLX** ([repo](https://github.com/youssofal/MTPLX), [site](https://mtplx.com/)) | Mac, agenci kodujący | tylko Apple Silicon | skan sprzętu → model → pobranie → pomiar każdej głębokości MTP przy przypiętych wentylatorach; zapisuje tylko, jeśli bije baseline (`mtplx tune --retune`) | **F** (jedna gałka) | **przed → po w UI**: 16 GB M4 mini 14.4 → 23.0 tok/s; Forge: „227.1 to 296.1, 1.30x” | OSS, darmowy, 2.6k★ |
| **TurboLLM** ([repo](https://github.com/mohitsoni48/TurboLLM)) | power users z forkami, Claude Code | Win/Mac/Linux, NVIDIA/AMD/Vulkan | „Auto-benchmark on load”: warstwy, MoE `--n-cpu-moe`, KV quant pod docelowy ctx, sampling z HF; dowolny fork llama.cpp, budowany w aplikacji z git URL | **F** | t/s mierzone na maszynie w liście modeli; 74.7 vs 61 t/s vs LM Studio (RTX 5070 Ti, 200K ctx); 2.2× z forkiem TurboQuant | FSL-1.1 (Apache-2.0 po 2 latach), 285★, 1,644 commitów. **Telemetria domyślnie WŁĄCZONA, w tym benchmarki** |
| **ggrun** ([repo](https://github.com/raketenkater/ggrun)) | power users, multi-GPU, MoE | Linux, Win, Mac; llama.cpp i ik_llama.cpp | plan rozmieszczenia z GGUF i pomiaru PCIe (`detect --bandwidth`); `--ai-tune` mierzy „safe flag variants” i zapamiętuje zwycięzcę; `--spec auto`; `recommend` | **F** | Qwen3.6-27B Q5_K_M: Ollama 22.8 / llama.cpp `--fit` 24.3 / ggrun 37.4 tok/s (3 różne GPU, 22.06.2026) | MIT, 280★, v3.2.11 |
| **llm-autotune** ([repo](https://github.com/tanavc1/local-llm-autotune)) | Ollama, LM Studio, MLX | Mac, Win, Linux | middleware: num_batch, dokładny rozmiar KV, pinowanie promptu | **F** (lekki) | TTFT −39%; generowanie **bez zmian (±2%)**, co autor uczciwie przyznaje | MIT, 34★ |
| **llama-optimus** ([repo](https://github.com/BrunoArsioli/llama-optimus)) | deweloperzy | llama.cpp | Optuna nad batch, ubatch, threads, ngl, `-ot`, FA, KV | **F** | przed → po w CLI | 60★ |
| **neurall/llama.cpp „autotune”** ([release](https://github.com/neurall/llama.cpp/releases/tag/release-b11648-282c52964)) | entuzjaści | — | strojenie online: margines cache ekspertów, budżety DDR, wątki | **F** | RTX 4060: 52 → 58 t/s | fork |
| **TensorFold** ([repo](https://github.com/ashhart/TensorFold)) | Mac, Spark, RTX | Metal, CUDA | rekomendacje sprzętowe, metryki na żywo; kombinacje model × sprzęt kwalifikowane ręcznie | **0** | dokładna spekulacja (bit-exact) | Apache-2.0, 1.3k★ |
| **oMLX** ([repo](https://github.com/jundot/omlx)) | agenci na Macu | Apple | prekompilowane kernele Metal, KV na SSD | **0** | TTFT z cache | Apache-2.0, 22.8k★ |
| **Lucebox** ([repo](https://github.com/Luce-Org/lucebox)) | entuzjaści + kupujący sprzęt | CUDA, ROCm | silnik strojony przez producenta pod sprzedawany box (Zero 495) | vendor pre-tune | — | Apache-2.0, 2.9k★ |
| **Mirai uzu** ([site](https://trymirai.com/)) | deweloperzy iOS/Mac | ANE + GPU | — | **0** | — | $10M seed ([TechCrunch](https://techcrunch.com/2026/02/19/co-founders-behind-reface-and-prisma-join-hands-to-improve-on-device-model-inference-with-mirai/)) |
| **llmfit** ([repo](https://github.com/AlexsJones/llmfit)) / **FitMyLLM** ([metodologia](https://www.fitmyllm.com/methodology)) / **llamaperf** ([site](https://llamaperf.com/)) | „co mi pójdzie i jak szybko” | — | estymacja: FitMyLLM fituje t/s = fixed + bytes/(BW·0.868), błąd 5.5% na 58 punktach NVIDIA; AMD, Apple i Intel niemierzone | estymacja | llamaperf: 1,841 raportów społeczności | llmfit 38.0k★; FitMyLLM ma płatne raporty z wynajętych GPU |

Ręcznie strojone silniki pod jeden GPU (Basalt, Radiance dla 2×R9700, strixite dla Strix Halo, PolyStrata, NInfer-V100X2) to „ręczna wersja” naszego produktu. Żaden nie ma autotunera ([llamaperf](https://llamaperf.com/), `r1-new-and-optimizers.md` §3c).

### 2.2 Tabela biznesowa: cena, licencja, telemetria, trakcja

| Produkt | Model biznesowy / cena | Licencja | Telemetria | Trakcja / finansowanie |
|---|---|---|---|---|
| LM Studio | aplikacja darmowa, także do pracy (od 2025-07-08, [blog](https://lmstudio.ai/blog/free-for-work)); Enterprise „contact us”; Bionic (płatna chmura); iOS (przejęte Locally AI) | zamknięta; `lms` i mlx-engine MIT | polityka: tylko wyszukiwanie, pobieranie i update check ([privacy](https://lmstudio.ai/app-privacy)); audyt firm trzecich widział wysyłkę wersji, OS, GPU i nazw modeli ([local-llm.net](https://www.local-llm.net/blog/local-ai-privacy-audit/)) | „millions of downloads”, ~$19.3M (2025, źródło wtórne, [topreviewed](https://topreviewed.ai/companies/element-labs-inc)) |
| Ollama | lokalnie za darmo; Cloud Pro **$20/mies.**, Max **$100**, Team **$500** ([pricing](https://ollama.com/pricing)) | MIT | brak w runtime; update check ([insiderllm](https://insiderllm.com/guides/local-ai-privacy-guide/)) | 183.3k★; **$65M Series B (2026-07-09), razem $88M; 8.9M devów/mies.; 14 osób** ([TechCrunch](https://techcrunch.com/2026/07/09/popular-open-source-ai-developer-tool-ollama-raises-65m-grows-to-nearly-9m-users/)) |
| Jan (Menlo Research) | darmowy | Apache-2.0 wg stron trzecich; API GitHuba podaje NOASSERTION | analytics opt-in ([docs](https://www.jan.ai/local-server/settings)); źródła są sprzeczne | 45.0k★ |
| GPT4All (Nomic) | darmowy; lejek do Nomic Platform | MIT | opt-in datalake [INFERENCE] [stale?] | 77.4k★, **porzucony** (ostatni release 2025-02-25, [#3605](https://github.com/nomic-ai/gpt4all/issues/3605)) |
| Msty Studio | Free / **Aurum $149/os./rok** / **Lifetime $349** / Teams od 5 stanowisk ([pricing](https://msty.ai/pricing/)) | zamknięta | niezweryfikowana | brak danych |
| AnythingLLM | desktop darmowy; hosting **$50/$99 mies.** ([pricing](http://anythingllm.com/pricing)) | MIT | **PostHog domyślnie włączony (opt-out)** ([docs](https://docs.anythingllm.com/installation-desktop/privacy)); zgłoszenie, że łączy się nawet po opt-out ([#5496](https://github.com/Mintplex-Labs/anything-llm/issues/5496)) | 67.2k★ |
| KoboldCpp | darmowy | AGPL-3.0 | brak udokumentowanej [INFERENCE] | 12.0k★ |
| llamafile | darmowy (Mozilla.ai) | Apache-2.0 | brak [INFERENCE] | 26.3k★ |
| Open WebUI | Enterprise wyceniany indywidualnie; >50 użytkowników albo white-label wymaga licencji ([license](https://docs.openwebui.com/license/)) | BSD-3 + klauzula brandingowa (od 04.2025, już nie OSI) | anonimowa wyłączona domyślnie | 155.8k★; Series B 07.2026, ~$88M (źródło wtórne, [Caplight](https://www.caplight.com/company/openwebui)) |
| TextGen | darmowy | AGPL-3.0 [INFERENCE] | „no telemetry” | 47.7k★ |
| Pinokio | darmowy, bootstrapped | MIT | — | 8.3k★ |
| LocalAI | darmowy | MIT [INFERENCE] | — | 49.6k★ |
| Lemonade (AMD) | darmowy | Apache-2.0 | brak widocznej | 5.9k★ |
| Foundry Local (MS) | darmowy | MIT (SDK) [INFERENCE] | „may collect usage data” ([README](https://github.com/microsoft/Foundry-Local)) | 2.6k★ |
| Intel AI Playground | darmowy | MIT | — | 1.0k★ |
| Private LLM | **$4.99 jednorazowo** | zamknięta | — | — |
| Strata | darmowy + darowizny | MIT | — | 25.4k★ |
| TurboLLM | darmowy dla osób i firm na własny użytek; zakaz konkurencyjnego produktu; Ko-fi, Sponsors | FSL-1.1 → Apache-2.0 | **on by default** (użycie + benchmarki + crashe), weryfikowalna w kodzie | 285★ |
| ggrun | darmowy | MIT | — | 280★ |
| Backyard AI | porzucił lokalny desktop na rzecz chmury $12/$35 mies. ([changelog](https://backyard.ai/changelog)) | zamknięta | — | sygnał, że czysty local trudno zmonetyzować [INFERENCE] |

### 2.3 Detekcja sprzętu i rekomendacja: stan sztuki

Poziomy dojrzałości w kolejności rosnącej:
1. **Wybór backendu i wariantu per producent:** Foundry Local (alias → wariant CUDA albo NPU), Windows ML (pobiera EP), Lemonade (ROCm vs Vulkan według reguły), RamaLama, LocalAI, Docker Model Runner, Pinokio.
2. **Statyczne badge dopasowania:** LM Studio („full GPU offload possible”, ignoruje kontekst), Jan (Fits / May be slow / Won't fit), Hermes (zielony/żółty/czerwony), HF „hardware compatibility” ([docs](https://huggingface.co/docs/hub/hardware)), llmfit, canitrun, apxml.
3. **Pomiar pamięci przed załadowaniem:** Ollama new scheduling (gemma3:12b przy 128k na 4090 z 52 → 85.5 tok/s dzięki pełnemu offloadowi, [blog](https://ollama.com/blog/new-model-scheduling) [stale?]); llama.cpp `--fit` na wirtualnych alokacjach, trwa 1.5–20 s ([#18049](https://github.com/ggml-org/llama.cpp/discussions/18049)); KoboldCpp AutoFit; LM Studio guardrails (estymacja często błędna, [#1631](https://github.com/lmstudio-ai/lmstudio-bug-tracker/issues/1631)).
4. **Rekomendacja oparta na zmierzonej prędkości:** w lokalnej aplikacji praktycznie nie istnieje. Najbliżej są ggrun `recommend` (estymaty kalibrowane pomiarem PCIe) i FitMyLLM (estymata fitowana na pomiarach z wynajętych GPU, tylko NVIDIA).

Słabości rynku:
- badge LM Studio ignorują kontekst;
- `--fit` stroi tylko pamięć: „Use --fit to make the model fit — not to magically optimize it” ([bswen](https://docs.bswen.com/blog/2026-03-15-llamacpp-optimization-speed/));
- Vulkan nie raportuje dokładnie VRAM bez uprawnień ([Ollama docs](https://docs.ollama.com/gpu));
- detekcja dGPU+iGPU się myli (Lemonade [#2705](https://github.com/lemonade-sdk/lemonade/issues/2705)).

### 2.4 Automatyczne strojenie wydajności: kto co stroi

| Pokrętło | Kto stroi automatycznie (2026-10) | Uwagi |
|---|---|---|
| Offload, split, kontekst (pamięć) | llama.cpp `--fit`, Ollama, KoboldCpp, LM Studio, Hermes, ggrun | rozwiązane i darmowe |
| MoE expert offload (`--n-cpu-moe`, `-ot`) | `--fit` (heurystyka dense-first), TurboLLM (benchmark), ggrun (model PCIe) | duże zyski przy brakującym VRAM |
| Wątki, batch, ubatch | llama-optimus, ggrun `--ai-tune`, llm-autotune (num_batch), neurall fork | narzędzia CLI dla technicznych |
| Flash attention | Ollama (auto-on), LM Studio (suwak) | prawie standard |
| KV quant | TurboLLM (pod docelowy ctx); reszta ręcznie (Ollama env globalny; Jan próbował domyślnego q8_0 i się wycofał) | wpływa na jakość, więc potrzebna bramka KLD |
| Wybór backendu (ROCm vs Vulkan vs SYCL) | statyczne reguły (Lemonade, RamaLama); **nikt nie wybiera na podstawie pomiaru** | duży problem na AMD i Intelu (§2.5) |
| Spekulacja (draft, MTP, DFlash) | MTPLX (głębokość MTP, Mac); ggrun `--spec auto` („validated profile”); Strata (spec-min-p); **LM Studio, Jan i llama.cpp tylko ręcznie** | **największa dźwignia, a dla mas nieruszona** |
| Kernele, graf, JIT | TensorRT-RTX adaptive inference (NVIDIA, ONNX, SDK); AMD HRX (gotowe kernele, nie autotune) | **u konsumenta LLM: nikt** |
| Weryfikacja poprawności po strojeniu | TensorFold (kontrakt bitowy, ale bez strojenia per maszyna); ggrun (bramki „admission/replay”) | **nikt nie łączy strojenia z bramką bitową lub KLD** |

### 2.5 Bóle użytkowników

**Liczby z GitHuba** (wyszukiwarka issues, 2026-10-15, open + closed; `r1-pain-analogs.md` §1a):

| Zapytanie | Liczba |
|---|---|
| ollama/ollama, etykieta `amd` | 165 |
| ollama/ollama, „slow” w tytule | 190 |
| ollama/ollama, „not using GPU” w tytule | 53 |
| ollama/ollama, wzmianka `num_ctx` | 769 |
| ollama/ollama, etykieta `performance` | 65 |
| ggml-org/llama.cpp, „ROCm” w tytule | 216 |
| lmstudio-bug-tracker, „slow” w tytule | 23 |
| janhq/jan, „slow” w tytule | 14 |

**Cytaty.** Reddit rzadko daje się pobrać bezpośrednio, dlatego większość cytatów pochodzi z GitHub issues i Hacker News. Wątki redditowe są tam, gdzie były dostępne.

| # | Kategoria | Cytat (dosłowny) | Link | Data |
|---|---|---|---|---|
| 1 | „to jest wolne” / regresja | „New Ollama Engine Causes Severe Performance Degradation (10x Slower)” | [ollama#11060](https://github.com/ollama/ollama/issues/11060) | 2025-06 [stale?] |
| 2 | nie używa GPU | „ollama ps shows 100% on GPU VRAM, but CPU/RAM is actually being used” | [ollama#10445](https://github.com/ollama/ollama/issues/10445) | 2025-04 [stale?] |
| 3 | nie używa GPU | „Model is not running on GPU， but "ollama ps" show 100% GPU” | [ollama#12261](https://github.com/ollama/ollama/issues/12261) | 2025-09 [stale?] |
| 4 | niewykorzystany VRAM | „Ollama Fails to Fully Utilize RTX 3060 VRAM with gemma3:27b (Only Uses 7GB out of 12GB” | [ollama#9818](https://github.com/ollama/ollama/issues/9818) | ~2025-03 [stale?] |
| 5 | AMD nie działa | „ROCm: AMD Radeon RX 7700S (gfx1102) is not used for inference despite being detected” | [ollama#11557](https://github.com/ollama/ollama/issues/11557) | 2025-07 [stale?] |
| 6 | AMD → CPU | „RX 9060 XT reports 0 VRAM, only runs on CPU” | [ollama#12602](https://github.com/ollama/ollama/issues/12602) | 2025-10-13 |
| 7 | APU po cichu na CPU | „gfx1151 (Radeon 8050S) silently falls back to CPU on Linux despite rocminfo detecting GPU” | [ollama#13589](https://github.com/ollama/ollama/issues/13589) | 2025-12-30 |
| 8 | AMD na Windows | „ROCm llama.cpp with 9070xt on Windows 11.” | [lmstudio#2358](https://github.com/lmstudio-ai/lmstudio-bug-tracker/issues/2358) | 2026-09-02 |
| 9 | Vulkan vs ROCm | „All ROCm variants show similar or worse performance than Vulkan” (7900 XTX: tg128 Vulkan ~167–177 vs ROCm ~129–144 t/s) | [llama.cpp#20934](https://github.com/ggml-org/llama.cpp/issues/20934) | 2026-03-24 |
| 10 | AMD, stabilność | „gfx1201 R9700 ROCm 7.14 llama.cpp generation hang, MES queue failure … Vulkan passes” | [ROCm#6630](https://github.com/ROCm/legacy-rocm-build/issues/6630) | ~2026-09 |
| 11 | iGPU/APU | „Vulkan regression on AMD Strix Halo UMA … model loads on GPU but inference shows no GPU compute” | [llama.cpp#24734](https://github.com/ggml-org/llama.cpp/issues/24734) | 2026-06-17 |
| 12 | iGPU laptop | „gfx1103 (Radeon 780M / RDNA3 iGPU) missing from rocBLAS TensileLibrary — HIP backend crashes on warmup” | via [llama.cpp#20934](https://github.com/ggml-org/llama.cpp/issues/20934) | 2026-03 |
| 13 | Intel Arc | „SYCL backend not working on Intel Arc B580 (Windows 10), only Vulkan works” | [llama.cpp#20169](https://github.com/ggml-org/llama.cpp/issues/20169) | 2026-03-06 |
| 14 | Intel Arc | „Low performance on MoE models - SYCL is slower than VULKAN (A770)” | [llama.cpp#19918](https://github.com/ggml-org/llama.cpp/issues/19918) | 2026-02-26 |
| 15 | ukryte domyślne ctx | „Shipping with 2k default context window … Totally made a lot of people think local LLMs are dumb as rocks.” | [HN 49402232](https://news.ycombinator.com/item?id=49402232) | 2026-08-23 |
| 16 | ukryte domyślne ctx | „Chat history and embedding truncation happens silently with no user-visible indication” | [ollama#14259](https://github.com/ollama/ollama/issues/14259) | ~2026-02 |
| 17 | ukryte domyślne ctx | „num_ctx prompt truncation limit is silently half the configured value” | [ollama#17427](https://github.com/ollama/ollama/issues/17427) | ~2026-08 |
| 18 | ukryte domyślne ctx | „Ollama num_ctx Truncated 287 of 400 Prompts and Never Told Me” | [dev.to](https://dev.to/ji_ai/ollama-numctx-truncated-287-of-400-prompts-and-never-told-me-4fi4) | ~2026-10 |
| 19 | Ollama wolniejsza od llama.cpp | „There's a massive difference in speed between Ollama and llama.cpp” (53.5 vs 32.5 t/s) | [ollama#14861](https://github.com/ollama/ollama/issues/14861) | 2026-03-15 |
| 20 | build ma znaczenie | „compiled it with specific compilation options for my GPUs … and the same model ran twice as fast” | [HN 49402232](https://news.ycombinator.com/item?id=49402232) | 2026-08-22 |
| 21 | jakość „gorsza” (Q4 domyślnie) | „people end up saying "I tried running Qwen 3.8 27b locally and it was dumb" while Ollama would default to a Q4” | [HN 49402232](https://news.ycombinator.com/item?id=49402232) | 2026-08-22 |
| 22 | kontekst spowalnia | TTFT Ollamy rośnie z 0.74 s do 52.71 s przy promptach od 471 do 33,057 tokenów | [ollama#14861](https://github.com/ollama/ollama/issues/14861) | 2026-03-15 |
| 23 | wolno przy małym VRAM | „Then I ran then Qwen 3.8 27b and while it was super slow (4t/s)” | [HN 49402232](https://news.ycombinator.com/item?id=49402232) | 2026-08-23 |
| 24 | za techniczne | „they just say "download it" and act like anyone that can't get it running is an idiot” | [HN 49402232](https://news.ycombinator.com/item?id=49402232) | 2026-08-23 |
| 25 | za techniczne | „It took him two hours of passing errors to Claude for the endpoint to start working” | [HN 49402232](https://news.ycombinator.com/item?id=49402232) | 2026-08-23 |
| 26 | Vulkan/CUDA, zły build | „the winget version of llama.cpp is for Vulkan, and I needed a different one … It doubled my speed.” | [HN 49402232](https://news.ycombinator.com/item?id=49402232) | 2026-08-23 |
| 27 | który model, który quant | „this is currently the confusing part of running local models for newbies … there are often dozens” | [HN 47865612](https://news.ycombinator.com/item?id=47865612) | ~2026 |
| 28 | który quant | „Q4_K_M vs Q4_K_S confused me for months.” | [r/ollama](https://www.reddit.com/r/ollama/comments/1vm1l4h/q4_k_m_vs_q4_k_s_confused_me_for_months_the_file) | 2026-08-12 |
| 29 | które narzędzie | „Beginner confused about Ollama vs LM Studio vs llama.” | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1wiikc2/beginner_confused_about_ollama_vs_lm_studio_vs) | 2026 |
| 30 | regresja (LM Studio) | „llama.cpp runtime 2.21 fails Metal tensor-API check — Neural Accelerators unused, 2–3× prefill lost” | [lmstudio#2040](https://github.com/lmstudio-ai/lmstudio-bug-tracker/issues/2040) | ~2026-06 |
| 31 | regresja (LM Studio) | „MLX Runtime 1.8.1 slower and causes repeated output on Qwen3.6” | [lmstudio#1917](https://github.com/lmstudio-ai/lmstudio-bug-tracker/issues/1917) | 2026 |
| 32 | regresja (KoboldCpp, AMD) | „AMD Vulkan, on 1.104 I get around 4x generation speed compared to 1.105.4” | [koboldcpp#1920](https://github.com/LostRuins/koboldcpp/issues/1920) | 2026-01-14 |
| 33 | ciche CPU (KoboldCpp) | „Reloaded model falls back to CPU-only” (RX 7700 XT) | [koboldcpp#2190](https://github.com/LostRuins/koboldcpp/issues/2190) | 2026-05-05 |
| 34 | AMD niedociążone | „In Koboldcpp the generation process takes 10 minutes, while in ComfyUI it takes only 25” | [koboldcpp#2381](https://github.com/LostRuins/koboldcpp/issues/2381) | 2026-08-04 |
| 35 | crash po aktualizacji | „CUDA error: the provided PTX was compiled with an unsupported toolchain.” | [ollama#17116](https://github.com/ollama/ollama/issues/17116) | 2026-07-10 |
| 36 | 7900 XTX, setup | „RX 7900 XTX (gfx1100) … ~0.8 tok/s decode, GPU at 100% / ~320 W” | [Strata#590](https://github.com/Niko1221/Strata/issues/590) | 2026-10-03 |
| 37 | OOM / pamięć | „Ollama is kind of dumb when it comes to memory overload protections” | [HN 44837130](https://news.ycombinator.com/item?id=44837130) | ~2025-08 [stale?] |
| 38 | estymata pamięci błędna | guardrails LM Studio często mylą się co do dopasowania, a CLI nie ma override | [lmstudio#1631](https://github.com/lmstudio-ai/lmstudio-bug-tracker/issues/1631) | 2026 |
| 39 | DGX Spark | „bought powerful hardware, but drowning in configs” | [NV forum](https://forums.developer.nvidia.com/t/moving-from-mac-to-nvidia-bought-powerful-hardware-but-drowning-in-configs/356374) | 2026 |
| 40 | producent przyznaje problem | „users either guess, look up Reddit threads, or ask an LLM” (AMD Lemonade, uzasadnienie Auto-Tune) | [Lemonade WG](https://lemonade-server.ai/docs/dev/working-groups/auto-tune/) | 2026 |

**Wnioski z bólów** `[INFERENCE]`:
1. Najczęstszy jest ból „czy w ogóle jestem na GPU i czy to jest maksimum”. Użytkownik nie ma punktu odniesienia. Mierzony baseline i dowód „liczysz na GPU” sam w sobie jest wartością.
2. Regresje po aktualizacjach zdarzają się w każdej aplikacji. Brakuje strażnika, który po aktualizacji silnika automatycznie przemierzy prędkość i zostawi szybszy wariant.
3. Na AMD i Intelu backend trzeba wybierać pomiarem, nie regułą: Vulkan wygrywa decode, ROCm wygrywa prefill (#9, #13, #14).
4. Ukryte domyślne ustawienia (ctx, Q4) psują postrzeganą jakość. Nasz produkt nie może dorzucać do tego cichego KV quant bez bramki jakości.
5. Społeczność sama robi ręczne buildy per GPU:
   - [llama.cpp_build_7900XTX](https://github.com/salvatoretrimarchi/llama.cpp_build_7900XTX);
   - [arc-llama](https://pypi.org/project/arc-llama/0.4.0) („Auto-detects your card, picks safe SYCL defaults”);
   - forki z llamaperf: Basalt, Radiance, strixite.

   Popyt na „wersję pod moją kartę” istnieje, a podaż jest ręczna.

### 2.6 Kto już sprzedaje „optymalizację”

| Firma / projekt | Co optymalizuje | Klient | Cena / model | Finansowanie | Dla konsumenta? | Strojenie per maszyna? |
|---|---|---|---|---|---|---|
| Standard Kernel ([blog](https://standardkernel.com/blog/announcing-our-seed-round-is-kernel-generation-solved/)) | kernele CUDA/PTX generowane przez AI (+6.0% geomean nad cuBLAS na H100) | floty AI | sprzedaż bezpośrednia | $20M seed (03.2026) | nie | per workload i sprzęt (DC) |
| Makora, dawniej Mako ([site](https://mako.dev/)) | generowanie i autotuning kerneli, NVIDIA + AMD MI300X | operatorzy inferencji | plany **$20 i $200/mies.** (oba „Sold Out”); Azure Marketplace | $8.5M (08.2025, [Cornell](https://news.cornell.edu/stories/2025/08/mako-faculty-led-startup-based-cornell-tech-raises-85-million)) [stale?] | nie | tak (per urządzenie) |
| Luminal ([TC](https://techcrunch.com/2025/11/17/luminal-raises-5-3-million-to-build-a-better-gpu-code-framework/)) | kompilator z superoptymalizacją | deweloperzy i chmura | OSS + chmura | $5.3M seed | nie | przeszukiwanie per sprzęt |
| Herdora (YC) ([fondo](https://fondo.com/blog/herdora-launches)) | PyTorch → kernele, 1.5–5× | zespoły ML | SaaS i usługi | YC | nie | per klient |
| RightNow AI ([site](https://www.rightnowai.co/)) | edytor kodu GPU z AI | deweloperzy kerneli | subskrypcja | $540k | nie | nie |
| Gimlet Labs ([finsmes](https://www.finsmes.com/2026/09/gimlet-labs-raises-300m-in-series-b-funding-at-3-billion-valuation.html)) | mapowanie agentów na heterogeniczny krzem | enterprise | chmura | **$300M Series B przy wycenie $3B** (09.2026) | nie | w swojej chmurze |
| Pruna AI ([pricing](https://www.pruna.ai/pricing)) | „smash”: kwantyzacja, pruning, kompilacja; dziś sprzedaje własne szybkie modele obrazowe przez API | deweloperzy | per obraz lub sekundę | $6.5M seed [stale?] | nie | nie |
| TheStage AI ([app](https://app.thestage.ai/)) | automatyczny optymalizator modeli per GPU | deweloperzy | $0 / **$20** / $150 / Enterprise | $4.5M [stale?] | nie | per docelowy GPU |
| Qualcomm AI Hub, MS Olive, MLC-LLM/TVM | kompilacja i strojenie per urządzenie (AI Hub profiluje na prawdziwych urządzeniach w chmurze) | deweloperzy | darmowe | vendor | nie | tak, ale u dewelopera |
| Sakana AI CUDA Engineer ([TC](https://techcrunch.com/2025/02/21/sakana-walks-back-claims-that-its-ai-can-dramatically-speed-up-model-training/)) [stale?] | agentowe kernele CUDA | research | — | — | nie | **wycofane deklaracje**: agent „oszukiwał” benchmark |
| Przejęcia | OctoAI → NVIDIA (~$165M, 2024), Deci → NVIDIA (~$300M, 2024), CentML → NVIDIA (~$400M, 06.2025), Neural Magic → Red Hat | — | — | — | — | sygnał: optymalizację inferencji kupują platformy ([geekwire](https://www.geekwire.com/2024/chip-giant-nvidia-acquires-octoai-a-seattle-startup-that-helps-companies-run-ai-models/), [betakit](https://betakit.com/nvidia-acquires-canadian-ai-efficiency-startup-centml/)) [stale?] |
| FitMyLLM ([methodology](https://www.fitmyllm.com/methodology)) | nie optymalizuje, sprzedaje **raporty pomiarowe** z wynajętych GPU | konsumenci i SMB | płatne raporty (JSON płatny w raporcie, darmowy wg metodologii; sprzeczność) | — | tak | nie |

Konsumentowi nikt nie sprzedaje „twój GPU, szybciej”. Po stronie konsumenckiej optymalizację robią pojedynczy maintainerzy darmowego OSS: Strata, MTPLX, TensorFold, Lucebox, TurboLLM, ggrun. Lucebox monetyzuje przez sprzedaż sprzętu „tuned for the hardware” ([lucebox.com](https://www.lucebox.com/)).

### 2.7 „Zostaw na noc, będzie szybciej”: analogie

| Analogia | Co robi | Czas | UX | W tle / w nocy? | Typowy zysk | Wyniki dzielone między użytkownikami? |
|---|---|---|---|---|---|---|
| NVIDIA App Automatic Tuning ([KitGuru](https://www.kitguru.net/gaming/joao-silva/nvidia-app-now-lets-you-automatically-overclock-your-gpu-without-voiding-the-warranty/)) [stale?] | skan OC konkretnego egzemplarza, bez utraty gwarancji | 10–20 min | jeden przycisk, PC bezczynny | minuty | kilka % FPS [INFERENCE] | nie |
| MSI Afterburner OC Scanner ([MSI](https://www.msi.com/blog/msi-afterburner-overclocking-undervolting-guide)) | skan krzywej V/F + test | ~30 min | przycisk i pasek postępu | półbezczynny | umiarkowany | nie |
| GeForce Experience „optimal settings” ([howtogeek](https://www.howtogeek.com/803375/why-you-should-use-geforce-experience-to-optimize-games/)) | chmurowa baza ustawień per konfiguracja GPU/CPU/rozdzielczość | natychmiast | przycisk „Optimize” | nie | cel 40–60 fps | **tak, centralnie per konfiguracja** (lab NVIDIA) |
| AMD Adrenalin Auto Undervolt / OC ([AMD](https://amd.com/en/resources/support-articles/faqs/DH3-020.html)) | one-click undervolt lub OC | ~1 min | jeden klik | nie | perf/W | nie |
| PBO2 Curve Optimizer + **CoreCycler** ([overclock.net](https://www.overclock.net/threads/corecycler-tool-for-testing-curve-optimizer-settings.1777398/)) [stale?] | test stabilności per rdzeń | 1–12 h, **typowo przez noc** | skrypt, „sprawdź rano” | **tak** | niższy V przy tej samej mocy | społeczność dzieli wartości per chip |
| Intel 200S Boost ([Tom's](https://www.tomshardware.com/pc-components/cpus/we-tested-intels-unreleased-200s-boost-feature-7-percent-higher-gaming-performance-thanks-to-memory-overclocking-now-covered-by-the-warranty)) | profil BIOS objęty gwarancją | natychmiast | toggle | nie | ~7% w grach | preset producenta |
| Intel XTU AI Assist ([Intel](https://www.intel.com/content/www/us/en/support/articles/000096983/processors.html)) | model AI proponuje OC | ~45 s | przycisk | nie | „95% accuracy” | model trenowany centralnie [INFERENCE] |
| Steam shader pre-caching + Fossilize ([GOL](https://www.gamingonlinux.com/2020/05/steam-beta-adds-vulkan-shader-processing/)) [stale?] | pobiera i kompiluje cache pipeline'ów w tle | minuty na grę | „Processing Vulkan shaders” | **tak** | brak stutteru | **tak: cache per GPU + driver od innych użytkowników** |
| Microsoft Advanced Shader Delivery ([TPU](https://www.techpowerup.com/340173/microsofts-advanced-shader-delivery-slashes-first-run-load-times-by-up-to-85), [DirectX blog](https://devblogs.microsoft.com/directx/advanced-shader-delivery-expands-public-preview-with-amd/)) | chmura kompiluje PSDB per sprzęt i driver, pobierane z grą | sekundy zamiast minut | niewidoczne | w chmurze | −85…95% czasu kompilacji | **tak, per sprzęt + driver** (AMD; NVIDIA i Intel od 10.2026) |
| **Android ART cloud profiles + bg-dexopt** ([AOSP](https://source.android.com/docs/core/runtime/configure/art-service), [blog](https://android-developers.googleblog.com/2019/04/improving-app-performance-with-art.html) [stale?]) | profile z pierwszych urządzeń → Play agreguje → dex2oat w tle, gdy telefon jest bezczynny i się ładuje | noc | niewidoczne, „rano szybciej” | **tak** | cold start −15% średnio, 30%+ w topowych aplikacjach; Baseline Profiles do 40% | **tak, agregacja z wielu urządzeń** |
| TVM Ansor ([TVM](https://tvm.apache.org/2021/03/03/intro-auto-scheduler)) [stale?] | przeszukiwanie harmonogramów tensorów | **godziny** (BERT 6 h, ResNet-50 10 h na 4090) | narzędzie deweloperskie | tak | 1.02–8.95× vs AutoTVM | logi można dzielić |
| torch.compile max-autotune ([HF](https://huggingface.co/docs/transformers/en/perf_torch_compile)) | benchmarkuje konfiguracje GEMM i Triton | sekundy–minuty | flaga | nie | do ~2× | lokalny cache |
| TensorRT engine / SD WebUI TRT ([repo](https://github.com/NVIDIA/stable-diffusion-webui-tensorrt)) | engine per GPU, checkpoint i rozdzielczość | 2–10 min | przycisk „Export engine” | jednorazowo | ~27% | nie (engine zależy od GPU) |
| TRT-RTX adaptive inference ([blog](https://developer.nvidia.com/blog/adaptive-inference-in-nvidia-tensorrt-for-rtx-enables-automatic-optimization)) | JIT kerneli pod kształty widziane w runtime | ciągle | niewidoczne | w trakcie użycia | 1.32× (FLUX) | cache musi się zgadzać z SKU i driverem |
| MIOpen Find + User PerfDb, hipBLASLt offline tuning ([MIOpen](https://rocm.docs.amd.com/projects/MIOpen/en/latest/conceptual/tuningdb.html), [hipBLASLt](https://rocm.blogs.amd.com/artificial-intelligence/hipblaslt_offline_tuning/README.html)) | autotune kerneli conv i GEMM; system PerfDb dostarczany przez producenta | „substantial amount of time” | wolny pierwszy start | jednorazowo | zależny | baza producenta |
| FFTW wisdom, ATLAS ([ATLAS](https://math-atlas.sourceforge.net/atlas_install/node45.html)) | pomiar przy instalacji, plany zapisane na dysk | długa instalacja | niewidoczne | przy instalacji | blisko optimum | pliki wisdom można dystrybuować |

Wnioski z analogii `[INFERENCE]`:
- Konsumenci akceptują trzy wzorce: krótki skan 10–30 min przy bezczynnym PC (NVIDIA, MSI), test przez noc w niszy entuzjastów (CoreCycler) i niewidoczną optymalizację w bezczynności (Android).
- Najlepiej pasuje połączenie: pierwszy, szybki etap jak NVIDIA Automatic Tuning, a nocny etap jak bg-dexopt z widocznym raportem rano.
- Gotowy szablon dzielenia wyników to Steam, ASD i ART. Wynik dostrajania liczy się raz dla (architektura GPU, driver, model, quant, wersja silnika), a pozostali go pobierają. Noc jest potrzebna tylko dla nowej kombinacji.
- Typowe zyski z konsumenckich auto-tunerów to od kilku do ~30%. Nasze ~1.8–2.8× względem domyślnych ustawień aplikacji jest wyraźnie wyżej, o ile da się to uczciwie wykazać (patrz §3.3).

### 2.8 Zagrożenia

| Zagrożenie | Dowód / sygnał | Prawdopodobieństwo (12 mies.) | Wpływ | Komentarz |
|---|---|---|---|---|
| **LM Studio, Ollama albo Jan automatycznie włączają spekulację i wybierają backend pomiarem** | LM Studio ma już MTP (0.4.14) i DFlash (0.4.22) jako toggle; Jan wykrywa MTP z metadanych GGUF; Ollama dostarcza modele z wbudowanymi drafterami (Nemotron 3.5 Bolt, [v0.40.5](https://github.com/ollama/ollama/releases/tag/v0.40.5)); Jan ma „Auto Optimize” | wysokie `[INFERENCE]` | **bardzo wysoki** | Upstream z ręczną spekulacją daje już 68.6–97.7 t/s na naszej karcie (`NOTES.md:38-48`). Zostaje nam przewaga kerneli (+10–25%) i AMD-specyficznych rzeczy |
| **Flag-tunery dojrzewają** (TurboLLM, ggrun) | TurboLLM: 1,644 commitów, telemetria benchmarków domyślnie włączona, czyli zbiera dane per GPU; ggrun `--spec auto` | wysokie | wysoki | TurboLLM wprost celuje w „performance layer for local LLMs” |
| **AMD Lemonade Auto-Tune** | 5-fazowa roadmapa: archetypy, profile pobierane zdalnie, `bench --submit`, strojenie adaptacyjne ([WG](https://lemonade-server.ai/docs/dev/working-groups/auto-tune/)); HRX z kernelami AMD | średnie (fazy 1–3) | wysoki na AMD | Oficjalny, darmowy kanał AMD na naszym głównym rynku. Zakres to tylko parametry, nie kernele |
| **NVIDIA wnosi przyspieszenia do llama.cpp, Ollamy i LM Studio** | +35% (MoE, CES 2026, [blog](https://blogs.nvidia.com/blog/rtx-ai-garage-ces-2026-open-models-video-generation/)); „up to 1.9x” na RTX 5090 ([IFA 2026](https://blogs.nvidia.com/blog/local-ai-ifa-next-gen-agents-nv-pair-rtx-spark/)); NVFP4 MMQ | pewne (już się dzieje) | wysoki na NVIDIA | Baza porównania na NVIDIA rośnie za darmo, więc nasz zysk przed → po na RTX będzie mniejszy niż na AMD |
| **NVIDIA lub AMD wypuszczają konsumencki „LLM Auto Tuning”** | NVIDIA ma wzorzec UX (Automatic Tuning) i technologię (TRT-RTX adaptive), G-Assist w NVIDIA App; AMD ma Adrenalin + Lemonade | niskie–średnie `[INFERENCE]` | bardzo wysoki | NVIDIA wycofała się z aplikacji czatu (ChatRTX), co osłabia ten scenariusz. Jeden toggle w NVIDIA App „optimize local AI” byłby jednak zabójczy na RTX |
| **Silniki pod jeden model** (Strata, Lucebox, MTPLX, TensorFold) | Strata 25.4k★, oMLX 22.8k★ | już są | średni | Dla popularnych modeli ręcznie strojony silnik może być szybszy niż nasz automat. Dla długiego ogona modeli i GPU nie ma ich nikt |
| **Agenci w aplikacjach** (Hermes, OpenClaw) przejmują onboarding | one-click lokalny model na RTX z pomocą NVIDIA ([IFA](https://blogs.nvidia.com/blog/local-ai-ifa-next-gen-agents-nv-pair-rtx-spark/)) | wysokie | średni | Użytkownik może nigdy nie otworzyć „aplikacji do LLM”, bo model przyjdzie z agentem. Szansa: być silnikiem pod nimi |
| **Erozja marży „samego local”** | Backyard porzucił desktop; LM Studio sprzedaje Bionic (chmura); Ollama sprzedaje Cloud | trwa | średni | Same aplikacje lokalne słabo się monetyzują |
| **Nazewnictwo** | Jan „Auto Optimize”, TurboLLM „auto-tuned to your GPU”, llm-autotune „autotune”, NVIDIA „performance improves over time” | — | niski–średni | Hasło „auto-tune” jest już zajęte i rozmyte. Trzeba komunikować mierzalny wynik i weryfikację |

---

## 3. Co to znaczy dla naszego produktu

### 3.1 Luka rynkowa

**Nikt nie oferuje użytkownikowi bez wiedzy technicznej aplikacji, która robi wszystkie te rzeczy naraz:**
1. mierzy uczciwy baseline na jego maszynie;
2. dobiera i weryfikuje konfigurację: backend, offload, KV, spekulację;
3. potem przez noc szuka dalszych zysków na poziomie kerneli, grafu i spekulacji dla jego pary GPU + model;
4. każdą zmianę bramkuje identycznością wyjścia (greedy md5) albo KLD;
5. pokazuje raport przed → po i pilnuje, żeby aktualizacje go nie zepsuły;
6. działa na NVIDIA, AMD, Intel i Apple, z AMD jako pierwszym obywatelem.

Kto jest blisko i czego mu brakuje:

| Kto | Co ma z listy | Czego brakuje |
|---|---|---|
| MTPLX | 1, kawałek 2 (jedna gałka), 5 (przed → po w UI) | tylko Mac, tylko spekulacja, brak kerneli |
| Strata | 1, kawałek 2, bramka bitowa w procesie deweloperskim | jeden model; kalibracja to flaga instalatora, nie produkt; u użytkownika brak kerneli |
| TurboLLM / ggrun | 1, 2 (flagi), dane z telemetrii (TurboLLM) | brak 3 i 4; odbiorca techniczny; brak przed → po dla laika |
| Lemonade Auto-Tune | ma przyszły kanał AMD i współdzielone profile | nic nie wydane; tylko parametry |
| TRT-RTX | ma technologię JIT kerneli „rosnących w czasie” | SDK, tylko NVIDIA i ONNX, nie GGUF/llama.cpp |

**Ocena:** luka jest realna, ale wąska w czasie. Część „konfiguracyjna” (spekulacja, backend, KV, offload) zostanie najpewniej skomodytyzowana w 6–12 miesięcy przez LM Studio, Jana, TurboLLM i Lemonade `[INFERENCE]`. Trwałą przewagę dają:
- poziom kerneli i scheduler (nasze +10–25% ponad upstream przy tej samej spekulacji na 7900 XTX, a na modelach MoE więcej: LFM 173 → 294 t/s);
- proces weryfikacji (bit-exact i KLD);
- baza wyników per (GPU, driver, model, quant).

### 3.2 Rekomendacje

1. **Pozycjonowanie: „zmierzone, zweryfikowane przyspieszenie twojego komputera”, nie „auto-tune”.** Hasło „auto” jest zajęte. Rdzeniem komunikacji powinien być raport:
   - „Twoja karta: 41 t/s → 108 t/s”;
   - „odpowiedzi identyczne bit w bit (12/12 testów)”;
   - „zmierzone 7 razy, mediana”.

   Lekcja z Sakana, która musiała wycofać deklaracje: weryfikacja to atut sprzedażowy.
2. **Dwa poziomy optymalizacji w produkcie:**
   - **Poziom 1, „Szybki skan” (5–20 min, jak NVIDIA Automatic Tuning):** pomiarowy wybór backendu (ROCm vs Vulkan vs CUDA vs SYCL), offload i MoE, KV z bramką KLD, włączenie i dobór spekulacji (MTP/DFlash, głębokość). Daje większość zysku i musi być darmowy, bo konkurenci zrobią go za darmo.
   - **Poziom 2, „Na noc” (godziny, jak bg-dexopt + CoreCycler):** agentowe kernele, scheduler i fuzje z naszego procesu. Tylko ten poziom jest trudny do skopiowania.
3. **Uczciwy baseline:** pokazywać dwa „przed”: domyślne ustawienia popularnej aplikacji (np. Ollama lub LM Studio) i najlepszy stock llama.cpp. Pierwsze sprzedaje, drugie chroni wiarygodność. Według `NOTES.md` na 7900 XTX: stock bez spekulacji ~37–39 t/s, stock z MTP 68.6–85.6, z DFlash2 97.7, nasz build 109–115.
4. **Współdzielona baza wyników jako fosa** (wzorzec Steam, ASD i ART): klucz (arch GPU, driver, wersja silnika, model, quant, ctx). Pierwszy użytkownik danej kombinacji „płaci nocą”, kolejni dostają wynik od razu. Uwaga: TurboLLM już zbiera benchmarki telemetrią domyślnie, a Lemonade planuje `bench --submit`, więc wyścig o dane już trwa.
5. **Najpierw AMD.**
   - Rynek jest najsłabiej obsłużony: Ollama ROCm na Windows tylko RDNA3, LM Studio z błędami ROCm, Jan z ROCm dopiero od 06.2026, HRX daje ≤10% decode.
   - Bóle AMD są najliczniejsze (165 issues `amd` w Ollamie).
   - Nasz wynik jest na AMD.
   - Drugi krok: NVIDIA RTX 30/40/50 z największym wolumenem, mimo że baza rośnie tam dzięki NVIDIA. Intel Arc to sierota po IPEX-LLM.
6. **Strażnik regresji:** po każdej aktualizacji silnika lub sterownika automatycznie przemierzyć prędkość i zostawić szybszy wariant. To odpowiedź na bóle #1, #30–#32 i #35, a nikt tego nie robi.
7. **Dowód „jesteś na GPU”:** w UI wprost wykorzystanie GPU i t/s od pierwszej minuty (bóle #2–#7, #33).
8. **Domyślne ustawienia bez pułapek:** nie obcinać kontekstu po cichu (Ollama ctx). KV quant tylko po bramce KLD i z informacją dla użytkownika.
9. **Dystrybucja:** być silnikiem pod agentami (Hermes, OpenClaw i inne) i trafić do kanałów producentów (AMD AI Bundle w Adrenalinie, RTX AI Garage) zamiast konkurować z nimi o ekran czatu. Zachować OpenAI/Anthropic API, bo to dziś standard (LM Studio, Ollama i TurboLLM go mają).
10. **Kotwice cenowe:**
    - konsumenci płacą $149/rok lub $349 lifetime za ładny UX (Msty) i $4.99 za aplikację mobilną (Private LLM);
    - narzędzia deweloperskie do optymalizacji kosztują $20/mies. (TheStage, Makora);
    - Ollama Cloud to $20/$100.

    Hipoteza do testu `[INFERENCE]`: darmowa aplikacja z poziomem 1, a poziom 2 (noc), priorytet w kolejce chmurowej i obsługa nowych modeli w dniu premiery w subskrypcji ok. $5–10/mies. albo jako jednorazowa opłata per GPU.
11. **Licencja:** wzór TurboLLM (FSL-1.1, po 2 latach Apache-2.0) chroni przed klonem komercyjnym przy zachowaniu weryfikowalności (telemetria w otwartym kodzie). Do rozważenia razem z decyzją o upstreamowaniu patchy (pytanie 2 w §3.4).

### 3.3 Ryzyka

- **Komodytyzacja części konfiguracyjnej** (§2.8, wiersz 1). Jeśli LM Studio automatycznie włączy MTP i dobierze backend, różnica „przed → po” na wielu kartach spadnie z ~2.5× do ~1.1–1.3× `[INFERENCE]`. Produkt musi wtedy nadal wygrywać kernelami.
- **Upstream zjada zyski.** NVIDIA i społeczność wnoszą do llama.cpp przyspieszenia podobne do naszych (graph replay, top-k, fuzje). Utrzymanie 70 łatek na ruchomej bazie jest kosztowne. Strata i TensorFold pokazują, że da się to robić tylko z bardzo dużą automatyzacją (ok. 87 commitów dziennie u TensorFolda).
- **Ogon sprzętu i modeli.** Nasz proces ma dowód na jednym GPU (7900 XTX) i trzech modelach. Każda nowa architektura modelu (GDN, MoE, MLA) i GPU (gfx12, sm_120, Arc, M5) to nowa przestrzeń. Noc u użytkownika może nie wystarczyć bez bazy wspólnej i chmury.
- **Zaufanie i bezpieczeństwo.** Agent kompilujący i uruchamiający kod na GPU użytkownika przez noc niesie ryzyko crashy sterownika (TDR), przegrzewania i zużycia energii. Gracze akceptują OC scan, bo producent daje gwarancję bezpieczeństwa. Nam potrzebne są limity mocy i temperatury oraz piaskownica.
- **Telemetria.** Wspólna baza wymaga wysyłki danych o sprzęcie. AnythingLLM dostaje krytykę za opt-out, TurboLLM broni się kodem źródłowym. Trzeba mieć jasny opt-in albo weryfikowalny kod.
- **Pomiar.** TensorFold i Strata udokumentowały pułapki: rampę zegara, ponowne przechwytywanie grafów, hałas współdzielonej maszyny. Konsumencki PC (przeglądarka, gry w tle) jest gorszym laboratorium niż nasz serwer. Raport przed → po musi mieć mediany, ABBA i regułę „brak werdyktu”.
- **Popyt na płacenie jest niesprawdzony.** Wszystkie konsumenckie projekty prędkościowe są darmowe (Strata utrzymuje się z darowizn).

### 3.4 Otwarte pytania

1. Jaka część naszego zysku na 7900 XTX jest powtarzalna automatycznie (konfiguracja vs kernele) dla **innych** modeli bez człowieka w pętli? Potrzebny eksperyment: poziom 1 (sam dobór flag i spekulacji) vs pełny stack na 3–5 modelach.
2. Upstreamować łatki czy trzymać je jako przewagę? Upstream podnosi bazę wszystkim, w tym konkurencji. Trzymanie oznacza koszt rebase i opinię „forka”.
3. Czy „noc” ma się dziać lokalnie, w chmurze na wynajętym GPU tej samej klasy (patrz raport R5 o cloud GPU), czy hybrydowo? Kernel zoptymalizowany na wynajętym 3090 jest ważny dla wszystkich 3090 z tym samym driverem i silnikiem `[INFERENCE]`.
4. Jaki jest właściwy klucz bazy wyników, żeby wyniki dało się przenosić (driver? wersja ROCm/CUDA? taktowania, limit mocy)?
5. Współpraca czy konkurencja z Lemonade (AMD)? Ich Auto-Tune WG szuka współpracowników (kontakt @mikkoph na Discordzie). Nasza baza profili mogłaby zasilić ich fazę 3–4.
6. Czy budować własną aplikację czatu, czy tylko silnik + optymalizator pod istniejące front-endy (Open WebUI, agenci, LM Studio jako klient OpenAI API)?
7. Jak zmierzyć gotowość do płacenia, zanim zbudujemy fazę 2? Na przykład landing z przed → po i listą oczekujących.

---

## 4. Źródła

**Aplikacje główne:**
- LM Studio: https://lmstudio.ai/changelog/lmstudio · https://lmstudio.ai/blog/0.4.0 · https://lmstudio.ai/blog/free-for-work · https://lmstudio.ai/blog/lmstudio-v0.3.27 · https://lmstudio.ai/docs/app/system-requirements · https://lmstudio.ai/app-privacy · https://lmstudio.ai/blog/locally-ai-joins-lm-studio · https://github.com/lmstudio-ai/lmstudio-bug-tracker/issues/1631 · https://github.com/lmstudio-ai/mlx-engine · https://www.local-llm.net/blog/local-ai-privacy-audit/ · https://topreviewed.ai/companies/element-labs-inc
- Ollama: https://github.com/ollama/ollama · https://github.com/ollama/ollama/releases/tag/v0.40.5 · https://docs.ollama.com/gpu · https://docs.ollama.com/faq · https://ollama.com/pricing · https://ollama.com/blog/new-model-scheduling · https://ollama.com/blog/mlx · https://techcrunch.com/2026/07/09/popular-open-source-ai-developer-tool-ollama-raises-65m-grows-to-nearly-9m-users/
- Jan: https://github.com/janhq/jan · https://www.jan.ai/changelog · https://www.jan.ai/changelog/2025-09-18-auto-optimize-vision-imports · https://www.jan.ai/changelog/2026-05-22-jan-v0.8.0
- GPT4All: https://github.com/nomic-ai/gpt4all · https://github.com/nomic-ai/gpt4all/issues/3605
- Msty: https://msty.ai/pricing/ · https://docs.msty.app/getting-started/gpus-support
- AnythingLLM: https://github.com/Mintplex-Labs/anything-llm · https://docs.anythingllm.com/changelog/v1.16.1 · https://docs.anythingllm.com/installation-desktop/privacy · http://anythingllm.com/pricing

**Narzędzia OSS:**
- llama.cpp: https://github.com/ggml-org/llama.cpp · https://github.com/ggml-org/llama.cpp/pull/16653 · https://github.com/ggml-org/llama.cpp/discussions/18049 · https://github.com/ggml-org/llama.cpp/discussions/21053 · https://llama.app/docs/serve · https://docs.bswen.com/blog/2026-03-15-llamacpp-optimization-speed/
- KoboldCpp: https://github.com/LostRuins/koboldcpp · https://github.com/LostRuins/koboldcpp/wiki · https://github.com/YellowRoseCx/koboldcpp-rocm
- llamafile i LocalScore: https://github.com/mozilla-ai/llamafile · https://blog.mozilla.ai/llamafile-returns/ · https://www.localscore.ai · https://github.com/mozilla-ai/llamafile/blob/main/localscore/README.md
- Pozostałe: https://github.com/mudler/LocalAI · https://localai.io/docs/features/gpu-acceleration/ · https://github.com/open-webui/open-webui · https://docs.openwebui.com/license/ · https://www.caplight.com/company/openwebui · https://github.com/oobabooga/textgen · https://github.com/pinokiocomputer/pinokio · https://github.com/mostlygeek/llama-swap · https://github.com/containers/ramalama · https://docs.docker.com/ai/model-runner/ · https://www.docker.com/blog/docker-model-runner-vulkan-gpu-support/ · https://github.com/qualcomm/GenieX · https://github.com/janhq/cortex.cpp · https://backyard.ai/changelog
- Estymatory: https://github.com/gpustack/gguf-parser-go · https://github.com/AlexsJones/llmfit · https://huggingface.co/docs/hub/hardware · https://www.fitmyllm.com/methodology · https://llamaperf.com/

**Producenci:**
- AMD: https://github.com/lemonade-sdk/lemonade · https://lemonade-server.ai/docs/dev/working-groups/auto-tune/ · https://www.amd.com/en/developer/resources/technical-articles/2026/lemonade-for-local-ai.html · https://github.com/lemonade-sdk/lemonade/issues/2705 · https://daily.dev/posts/lemonade-11-9-local-ai-server-released-with-super-exciting-amd-rocm-hrx-backend-oqelo2sdt · https://www.amd.com/en/blogs/2026/amd-software-adrenalin-edition-ai-bundle-ai-made-si.html · https://www.amd.com/en/products/software/adrenalin/amd-chat.html · https://amd-gaia.ai/docs/guides/agent-ui
- Microsoft: https://github.com/microsoft/Foundry-Local · https://learn.microsoft.com/en-us/azure/foundry-local/reference/reference-cli · https://github.com/microsoft/foundry-local/releases/tag/v2.0.1 · https://learn.microsoft.com/en-us/windows/ai/new-windows-ml/initialize-execution-providers · https://blogs.windows.com/windowsdeveloper/2025/09/23/windows-ml-is-generally-available-empowering-developers-to-scale-local-ai-across-windows-devices/
- NVIDIA: https://forums.developer.nvidia.com/t/chatrtx-has-been-deprecated-this-forum-is-locked/365743 · https://www.nvidia.com/en-us/software/nvidia-app/g-assist/ · https://docs.nvidia.com/deeplearning/tensorrt-rtx/latest/index.html · https://developer.nvidia.com/blog/adaptive-inference-in-nvidia-tensorrt-for-rtx-enables-automatic-optimization · https://blogs.nvidia.com/blog/rtx-ai-garage-ces-2026-open-models-video-generation/ · https://developer.nvidia.com/blog/open-source-ai-tool-upgrades-speed-up-llm-and-diffusion-models-on-nvidia-rtx-pcs/ · https://blogs.nvidia.com/blog/local-ai-ifa-next-gen-agents-nv-pair-rtx-spark/ · https://www.kitguru.net/gaming/joao-silva/nvidia-app-now-lets-you-automatically-overclock-your-gpu-without-voiding-the-warranty/
- Intel: https://github.com/intel/AI-Playground · https://github.com/intel/ipex-llm/tree/main/python/llm · https://docs.openvino.ai/2025/openvino-workflow/running-inference/inference-devices-and-modes/auto-device-selection.html
- Apple-side: https://privatellm.app/en · https://github.com/osaurus-ai/osaurus · https://github.com/a-ghorbani/pocketpal-ai · https://github.com/gluonfield/enchanted · https://machinelearning.apple.com/research/apple-foundation-models-2025-updates

**Nowi gracze i optymalizatory:**
- Silniki i aplikacje: https://github.com/Niko1221/Strata · https://github.com/youssofal/MTPLX · https://mtplx.com/ · https://mtplx.com/compare · https://github.com/ashhart/TensorFold · https://github.com/jundot/omlx · https://github.com/Luce-Org/lucebox · https://www.lucebox.com/ · https://trymirai.com/
- Flag-tunery: https://github.com/mohitsoni48/TurboLLM · https://github.com/raketenkater/ggrun · https://github.com/tanavc1/local-llm-autotune · https://github.com/BrunoArsioli/llama-optimus · https://github.com/neurall/llama.cpp/releases/tag/release-b11648-282c52964 · https://media.patentllm.org/news/hardware/llm-auto-tunes-llama-cpp-sass-latency-analysis-dlss-frame-ge-20260414
- Agenci z one-click lokalnym modelem: https://hermes-agent.nousresearch.com/docs/guides/local-ollama-setup · https://www.marktechpost.com/2026/09/05/nous-research-hermes-desktop-one-click-local-model-setup/ · https://openclaw.ai/blog/macos-installer-windows-local-ai · https://www.perplexity.ai/hub/blog/introducing-portable-computer-for-local-first-ai
- Firmy optymalizacyjne: https://standardkernel.com/blog/announcing-our-seed-round-is-kernel-generation-solved/ · https://mako.dev/ · https://news.cornell.edu/stories/2025/08/mako-faculty-led-startup-based-cornell-tech-raises-85-million · https://techcrunch.com/2025/11/17/luminal-raises-5-3-million-to-build-a-better-gpu-code-framework/ · https://fondo.com/blog/herdora-launches · https://www.rightnowai.co/ · https://www.finsmes.com/2026/09/gimlet-labs-raises-300m-in-series-b-funding-at-3-billion-valuation.html · https://www.pruna.ai/pricing · https://app.thestage.ai/ · https://techcrunch.com/2025/02/21/sakana-walks-back-claims-that-its-ai-can-dramatically-speed-up-model-training/ · https://www.geekwire.com/2024/chip-giant-nvidia-acquires-octoai-a-seattle-startup-that-helps-companies-run-ai-models/ · https://betakit.com/nvidia-acquires-canadian-ai-efficiency-startup-centml/

**Bóle użytkowników:**
- Ollama: https://github.com/ollama/ollama/issues/11060 · https://github.com/ollama/ollama/issues/10445 · https://github.com/ollama/ollama/issues/12261 · https://github.com/ollama/ollama/issues/9818 · https://github.com/ollama/ollama/issues/11557 · https://github.com/ollama/ollama/issues/12602 · https://github.com/ollama/ollama/issues/13589 · https://github.com/ollama/ollama/issues/14259 · https://github.com/ollama/ollama/issues/17427 · https://github.com/ollama/ollama/issues/14861 · https://github.com/ollama/ollama/issues/17116
- llama.cpp i ROCm: https://github.com/ggml-org/llama.cpp/issues/20934 · https://github.com/ggml-org/llama.cpp/issues/24734 · https://github.com/ggml-org/llama.cpp/issues/20169 · https://github.com/ggml-org/llama.cpp/issues/19918 · https://github.com/ROCm/legacy-rocm-build/issues/6630
- LM Studio i KoboldCpp: https://github.com/lmstudio-ai/lmstudio-bug-tracker/issues/2358 · https://github.com/lmstudio-ai/lmstudio-bug-tracker/issues/2040 · https://github.com/lmstudio-ai/lmstudio-bug-tracker/issues/1917 · https://github.com/LostRuins/koboldcpp/issues/1920 · https://github.com/LostRuins/koboldcpp/issues/2190 · https://github.com/LostRuins/koboldcpp/issues/2381
- Hacker News, Reddit i inne: https://news.ycombinator.com/item?id=49402232 · https://news.ycombinator.com/item?id=47865612 · https://news.ycombinator.com/item?id=44837130 · https://github.com/Niko1221/Strata/issues/590 · https://www.reddit.com/r/ollama/comments/1vm1l4h/q4_k_m_vs_q4_k_s_confused_me_for_months_the_file · https://www.reddit.com/r/LocalLLM/comments/1wiikc2/beginner_confused_about_ollama_vs_lm_studio_vs · https://dev.to/ji_ai/ollama-numctx-truncated-287-of-400-prompts-and-never-told-me-4fi4 · https://forums.developer.nvidia.com/t/moving-from-mac-to-nvidia-bought-powerful-hardware-but-drowning-in-configs/356374 · https://github.com/salvatoretrimarchi/llama.cpp_build_7900XTX · https://pypi.org/project/arc-llama/0.4.0

**Analogie:**
- Overclocking i undervolting: https://www.msi.com/blog/msi-afterburner-overclocking-undervolting-guide · https://www.howtogeek.com/803375/why-you-should-use-geforce-experience-to-optimize-games/ · https://amd.com/en/resources/support-articles/faqs/DH3-020.html · https://www.overclock.net/threads/corecycler-tool-for-testing-curve-optimizer-settings.1777398/ · https://www.tomshardware.com/pc-components/cpus/we-tested-intels-unreleased-200s-boost-feature-7-percent-higher-gaming-performance-thanks-to-memory-overclocking-now-covered-by-the-warranty · https://www.intel.com/content/www/us/en/support/articles/000096983/processors.html
- Shadery i kompilacja w tle: https://www.gamingonlinux.com/2020/05/steam-beta-adds-vulkan-shader-processing/ · https://www.techpowerup.com/340173/microsofts-advanced-shader-delivery-slashes-first-run-load-times-by-up-to-85 · https://devblogs.microsoft.com/directx/advanced-shader-delivery-expands-public-preview-with-amd/ · https://source.android.com/docs/core/runtime/configure/art-service · https://android-developers.googleblog.com/2019/04/improving-app-performance-with-art.html
- Autotuning kompilatorów i bibliotek: https://tvm.apache.org/2021/03/03/intro-auto-scheduler · https://huggingface.co/docs/transformers/en/perf_torch_compile · https://github.com/NVIDIA/stable-diffusion-webui-tensorrt · https://rocm.docs.amd.com/projects/MIOpen/en/latest/conceptual/tuningdb.html · https://rocm.blogs.amd.com/artificial-intelligence/hipblaslt_offline_tuning/README.html · https://math-atlas.sourceforge.net/atlas_install/node45.html

**Materiały wewnętrzne:**
- `~/KERNEL/qwen-opt/README.md`, `~/KERNEL/qwen-opt/NOTES.md:38-48` (baseline upstream vs nasze kernele);
- `~/KERNEL/qwen-opt/research/tensorfold/README.md`;
- `~/KERNEL/qwen-opt/research/strata/README.md`.
