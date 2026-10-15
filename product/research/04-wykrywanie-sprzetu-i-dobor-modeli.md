# 04 — Wykrywanie sprzętu, estymacja pamięci/prędkości i dobór modeli

Data: 2026-10-15. Autor: agent R4HwModels (research only, bez użycia GPU).
Konwencje: GB = 10⁹ B, GiB/MiB = 2³⁰/2²⁰ B. `[INFERENCE]` = wniosek własny, niezweryfikowany źródłem.
„(>12 mies.)" = źródło starsze niż 12 miesięcy, możliwie nieaktualne.

---

## 1. TL;DR

- **Wykrywanie sprzętu trzeba robić dwuwarstwowo.** Warstwa 1 to szybki „inwentarz" z natywnych API bez uprawnień admina:
  - Windows: DXGI/DXCore + NVML/ADLX/Level Zero + Vulkan + SMBIOS;
  - Linux: sysfs + NVML + Vulkan;
  - macOS: sysctl + Metal.

  Warstwa 2 to „capability probe": ładujemy backendy ggml w podprocesie i czytamy `ggml_backend_dev_props`, potem robimy 3–10 s mikro-benchmarku. Tak robi Ollama: w 2026 przeszła na runner-based discovery z timeoutem 30 s, a na Windows 90 s z powodu skanowania DLL przez Defendera ([ollama discover/runner.go](https://github.com/ollama/ollama/blob/main/discover/runner.go)).
- **Każde pojedyncze źródło potrafi kłamać.**
  - WMI `AdapterRAM` to uint32, więc ucina VRAM do 4 GB ([SO](https://stackoverflow.com/questions/68274009/wmi-win32-videocontroller-ram-4gb-limit)).
  - Referencyjny Strata wypisał „Ryzen 9 3950X (no AVX2)" i „RTX 4080, 32.0 GB VRAM". Zen 2 ma AVX2, a 4080 ma 16 GB ([Strata #159](https://github.com/Niko1221/Strata/issues/159)).
  - Ollama pokazywała 0 GB VRAM na GTX 10xx po aktualizacji sterownika ([#14280](https://github.com/ollama/ollama/issues/14280)).

  Wniosek: każdą wartość krzyżowo weryfikujemy co najmniej dwoma API i pomiarem.
- **llama.cpp ma już własny „fit".** `--fit` jest domyślnie włączony, z marginesem 1024 MiB i minimalnym kontekstem 4096. Narzędzie `llama-fit-params` i wydruk `common_memory_breakdown_print` dają dokładny podział model/context/compute ([tools/fit-params](https://github.com/ggml-org/llama.cpp/tree/master/tools/fit-params); `common/common.h:494-499` w `~/llama-master`). Nasz estymator powinien z tego korzystać, a nie liczyć od zera.
- **Wzór pamięci sprawdziłem ręcznie na naszych logach.**
  - Qwen3.8-27B UD-Q4_K_XL przy 204 800 ctx z KV q4_0 i MTP: przewidziane **22 593 MiB**, projekcja llama.cpp **22 569 MiB** (+0,1%).
  - LFM2.5-24B-A2B Q5_K_M przy 131 072 ctx z KV q8_0: przewidziane **17 996 MiB**, llama.cpp **17 997 MiB**.
  - Naiwny wzór „wagi + KV" myli się o 5–10%. Gubi snapshoty stanów rekurencyjnych (748 MiB), logity w buforze compute (485 MiB) i kontekst draftu (1 068 MiB).
- **Prędkość decode najlepiej opisuje model dwuczłonowy:** `t_tok ≈ B_tok/(η_bw·BW) + N_kern·t_gap`. Sam roofline `BW/B_tok` się nie sprawdza.
  - Dla gęstego Qwena η wychodzi 0,61–0,67 (tg128 34,8–38,6 t/s, przy suficie 57 t/s).
  - Dla MoE LFM z ~2B aktywnych η wynosi zaledwie 0,31 na upstreamie (169 t/s) i 0,55 po naszych 70 łatkach (295 t/s), bo ten model jest ograniczony liczbą kernel launchy.
  - Stała llmfit η = 0,55 ([how-it-works](https://raw.githubusercontent.com/AlexsJones/llmfit/main/docs/how-it-works.md)) przeszacowuje upstream LFM o 75%, a niedoszacowuje Qwena o 14–22%.
- **Istniejące estymatory są zgrubne.** Najlepsze opublikowane dopasowanie (arXiv 2609.14864, metadane GGUF i roofline z kalibrowanymi współczynnikami) ma MAPE decode 13–36% i prefill do 108% ([arXiv](https://arxiv.org/abs/2609.14864)). W produkcie estymata ma tylko ograniczyć wybór. O wyborze decyduje pomiar na maszynie użytkownika, który i tak pokazujemy jako baseline.
- **Domyślne modele (późny 2026), wszystkie Apache-2.0** ([HF API](https://huggingface.co/api/models?author=Qwen)):

  | Pamięć | Model domyślny | Rozmiar |
  |---|---|---|
  | 4 GB / CPU | Qwen3.5-4B Q4_K_M | 2,74 GB |
  | 8 GB | Qwen3.5-9B Q4_K_M | 5,68 GB |
  | 12 GB | Gemma 4 12B Q4/Q6 | 7,4–9,8 GB |
  | 16 GB | Qwen3.8-27B UD-Q3_K_XL (jakość) albo gpt-oss-20b MXFP4 (prędkość) | 13,15 / 12,11 GB |
  | 24 GB | Qwen3.8-27B UD-Q4_K_XL | 17,56 GB |
  | 32 GB | Qwen3.8-27B Q6/Q8 | — |
  | Mac/APU 128 GB | gpt-oss-120b albo Qwen3.5-122B-A10B | — |

  Qwen3.8 27B to wg Artificial Analysis najlepszy otwarty model 4–40B ([AA small](https://artificialanalysis.ai/models/open-source/small)). Po polsku warto mieć opcję Bielik-11B-v3 (Apache-2.0, PLCC 71,83%; [arXiv 2601.11579](https://arxiv.org/abs/2601.11579)).
- **Udziały w rynku:**
  - Steam 09/2026: NVIDIA ~76%, AMD ~16,7%, Intel ~7% ([virtwave, wtórne](https://www.virtwave.com/industry-news/steam-statistics)).
  - Steam, VRAM: 16 GB 27,21%, 8 GB 26,71%, 12 GB 13,06%, 24 GB 5,50%, 32 GB 1,41% ([Steam HW Survey](https://store.steampowered.com/hwsurvey/Steam-Hardware-Software-Survey-Welcome-to-Steam)).
  - Wśród osób, które zgłosiły sprzęt na Hugging Face, Apple to **~25%** (NVIDIA ~65%, AMD ~10%; [HF hardware](https://huggingface.co/hardware), moje zliczenie). Na Steamie macOS ma 1,92%.
- **Priorytet celów:**
  1. NVIDIA RTX 30/40/50 z 8–16 GB na Windows (CUDA).
  2. Apple Silicon (Metal).
  3. NVIDIA 24–32 GB (3090/4090/5090).
  4. AMD RDNA3/RDNA4 (nasza przewaga, Vulkan + ROCm).
  5. APU z unified memory (Strix Halo, DGX Spark).
  6. CPU-only jako fallback (AVX2 ma 95,95% maszyn, AVX-512 ma 27,46%).
  7. Intel Arc.

---

## 2. Ustalenia

### 2.1 Wykrywanie sprzętu bez uprawnień administratora

#### 2.1.1 Windows

| Co | API (bez admina) | Uwagi / pułapki | Źródło |
|---|---|---|---|
| Lista adapterów, VRAM dedykowany, pamięć współdzielona | DXGI `IDXGIFactory6::EnumAdapterByGpuPreference` → `DXGI_ADAPTER_DESC1/3`: `VendorId`, `DeviceId`, `SubSysId`, `DedicatedVideoMemory`, `SharedSystemMemory` (SIZE_T, czyli 64 bit), `AdapterLuid`, flaga `SOFTWARE` | iGPU raportuje mały carve-out z BIOS jako „dedicated", a resztę jako shared. To dla iGPU nie jest limit. `SharedSystemMemory` ≈ ½ RAM (WDDM). | [DXGI_ADAPTER_DESC1](https://github.com/MicrosoftDocs/sdk-api/blob/docs/sdk-api-src/content/dxgi/ns-dxgi-dxgi_adapter_desc1.md) |
| Ile wolno zająć teraz | `IDXGIAdapter3::QueryVideoMemoryInfo(LOCAL/NON_LOCAL)` → `Budget`, `CurrentUsage` | To jest budżet od OS dla procesu. Po jego przekroczeniu zaczyna się „stuttering". To właściwa wartość „free". | [QueryVideoMemoryInfo](https://learn.microsoft.com/en-us/windows/win32/api/dxgi1_4/nf-dxgi1_4-idxgiadapter3-queryvideomemoryinfo), [DXGI_QUERY_VIDEO_MEMORY_INFO](https://learn.microsoft.com/en-us/windows/win32/api/dxgi1_4/ns-dxgi1_4-dxgi_query_video_memory_info) |
| iGPU vs dGPU, NPU | DXCore: `DXCoreAdapterProperty::IsIntegrated` (12), `DedicatedAdapterMemory` (7); filtr `DXCORE_ADAPTER_ATTRIBUTE_D3D12_GENERIC_ML` daje GPU+NPU, a odjęcie `D3D12_GRAPHICS` zostawia same NPU | Zapytania o atrybuty to iloczyn, nie suma, więc trzeba robić osobne zapytania. Starsze sterowniki nie raportują GENERIC_ML, wtedy fallback na `CORE_COMPUTE`. Heurystyka „<1 GiB dedicated = iGPU" myli się na AMD/Qualcomm. | [DXCore GUIDs](https://learn.microsoft.com/en-us/windows/win32/dxcore/dxcore-adapter-attribute-guids), [Chromium NPU](https://issues.chromium.org/issues/341947682) (>12 mies.), [tasksmack #1263](https://github.com/mgradwohl/tasksmack/issues/1263) |
| NVIDIA: dokładny VRAM, sterownik, CC, szyna | NVML (`nvml.dll` w `System32` przy sterownikach DCH, czasem w `Program Files\NVIDIA Corporation\NVSMI`): `nvmlDeviceGetMemoryInfo_v2` (total/free/used/**reserved**), `nvmlSystemGetDriverVersion`, `nvmlDeviceGetCudaComputeCapability`, `nvmlDeviceGetMemoryBusWidth` + max mem clock | `_v2` wydziela pamięć zarezerwowaną; stara wersja zmniejszała o nią total. Biblioteka ładowana dynamicznie. | [NVML Device Queries](https://docs.nvidia.com/deploy/nvml-api/latest/api/group__nvmlDeviceQueries.html), [nvmlMemory_v2_t](https://docs.nvidia.com/deploy/nvml-api/615/api/structnvmlMemory__v2__t.html), [wine-nvml](https://github.com/Saancreed/wine-nvml) (>12 mies.) |
| AMD: VRAM, typ pamięci, rodzina ASIC | ADLX `IADLXGPU::TotalVRAM`, `VRAMType`, `ASICFamilyType`, `Type`, `IsExternal` | Wymaga sterownika Adrenalin. ADLX SDK ma własną licencję (PDF w repo). | [IADLXGPU](https://gpuopen.com/manuals/adlx/adlx-sdk-references/adlx-interfaces/gpu/iadlxgpu/), [ADLX GitHub](https://github.com/GPUOpen-LibrariesAndSDKs/ADLX) |
| Intel Arc / iGPU | Level Zero `zeDeviceGetMemoryProperties`; Sysman `zesInit` → `zesDeviceEnumMemoryModules`/`zesMemoryGetState` | `ZES_ENABLE_SYSMAN` jest przestarzałe od 1.16, zamiast tego `zesInit()`. Free memory przez Sysman bywa niedostępne (llama.cpp SYCL [#28239](https://github.com/ggml-org/llama.cpp/issues/28239), Arc Pro B60 [#993](https://github.com/intel/compute-runtime/issues/993)). | [Sysman Programming Guide](https://oneapi-src.github.io/level-zero-spec/level-zero/latest/sysman/PROG.html) |
| Uniwersalnie, wszyscy vendorzy | Vulkan: `vkEnumeratePhysicalDevices` → `deviceType`; `vkGetPhysicalDeviceMemoryProperties2` + `VK_EXT_memory_budget` (`heapBudget`/`heapUsage`); `VK_EXT_pci_bus_info` do sparowania z DXGI/NVML | ggml-vulkan liczy *total* jako sumę stert `DEVICE_LOCAL`, a dla iGPU *wszystkich* stert. *free* = budget − usage, jeśli rozszerzenie jest dostępne. | [VK_EXT_memory_budget](https://docs.vulkan.org/refpages/latest/refpages/source/VK_EXT_memory_budget.html); kod: `~/llama-master/ggml/src/ggml-vulkan/ggml-vulkan.cpp:15226-15256` |
| Wersja sterownika | NVML / ADLX / `VkPhysicalDeviceDriverProperties`; WMI `Win32_VideoController.DriverVersion` | **Nie używać `AdapterRAM` z WMI** (uint32, ucina do 4 GB). Obejście z rejestru: `HardwareInformation.qwMemorySize`. | [Win32_VideoController](https://learn.microsoft.com/en-us/windows/win32/cimwin32prov/win32-videocontroller), [SO 4GB](https://stackoverflow.com/questions/68274009/wmi-win32-videocontroller-ram-4gb-limit) (>12 mies.), [MS Q&A](https://learn.microsoft.com/en-us/answers/questions/2202526/loop-through-and-read-adapters) |
| CPU: AVX2/AVX-512/AVX-VNNI/AMX | Bezpośredni `CPUID` + `XGETBV` (stan YMM/ZMM/AMX włączony przez OS), np. crate `raw-cpuid` | `IsProcessorFeaturePresent` zna tylko flagi do `PF_AVX512F` (SDK 19041) i odbija to, co włączył kernel. W VM bywa mylący. | [IsProcessorFeaturePresent](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-isprocessorfeaturepresent), [bun #19003](https://github.com/oven-sh/bun/pull/19003) |
| RAM: rozmiar i prędkość | `GlobalMemoryStatusEx`; SMBIOS typ 17 przez `GetSystemFirmwareTable('RSMB')` albo WMI `Win32_PhysicalMemory.ConfiguredClockSpeed` (w praktyce MT/s) i `SMBIOSMemoryType` | Bez admina. `MemoryType` w CIM daje 0 dla DDR4/DDR5, trzeba brać `SMBIOSMemoryType`. **SMBIOS zawiera numery seryjne**, więc nie wolno ich wysyłać. | [GetSystemFirmwareTable](https://learn.microsoft.com/en-us/windows/win32/api/sysinfoapi/nf-sysinfoapi-getsystemfirmwaretable), [Win32_PhysicalMemory](https://learn.microsoft.com/en-us/windows/win32/cimwin32prov/win32-physicalmemory) |
| Laptop / bateria | `GetSystemPowerStatus` (`BatteryFlag & 128` = brak baterii, `ACLineStatus`); `Win32_SystemEnclosure.ChassisTypes` (8/9/10/14 = laptop) | Vendorzy nie wypełniają ChassisTypes konsekwentnie. UPS może wyglądać jak „bateria". | [MS: laptops](https://learn.microsoft.com/en-us/previous-versions/system-center/configuration-manager-2003/cc180825(v=technet.10)) (>12 mies.), [Win32_SystemEnclosure](https://powershell.one/wmi/root/cimv2/win32_systemenclosure) |
| Pułapka: NVIDIA „Sysmem Fallback" | Od sterownika 536.40 przepełnienie VRAM po cichu trafia do shared RAM: brak OOM, za to spowolnienie 5–30×. Od 546.01 da się to wyłączyć w panelu. | Nie znalazłem publicznego API do odczytu tej opcji `[INFERENCE: prawdopodobnie NVAPI DRS]`. Bronimy się budżetem z marginesem oraz detekcją wzrostu `NON_LOCAL CurrentUsage` i spadku t/s. | [NVIDIA KB 5490](https://nvidia.custhelp.com/app/answers/detail/a_id/5490/~/system-memory-fallback-for-stable-diffusion) (>12 mies.), [runaihome 2026](https://runaihome.com/blog/shared-gpu-memory-slow-local-ai-sysmem-fallback-fix-2026/) |
| Pułapka: AMD APU | Strix Halo: Variable Graphics Memory do 96 GB na 128 GB RAM. Ustawienie z Adrenalina zmienia wartość „dedicated" w DXGI. | llama.cpp Vulkan widział na Ryzen 395 RAM systemowy zamiast dedykowanej puli ([#16832](https://github.com/ggml-org/llama.cpp/issues/16832), >12 mies.). | [AMD VGM FAQ](https://www.amd.com/en/blogs/2025/faqs-amd-variable-graphics-memory-vram-ai-model-sizes-quantization-mcp-more.html) (>12 mies.) |

#### 2.1.2 Linux

| Co | Źródło danych (bez roota) | Uwagi | Źródło |
|---|---|---|---|
| Enumeracja PCI | `/sys/bus/pci/devices/*/{class,vendor,device,subsystem_*}`, symlink `driver` (amdgpu/nvidia/i915/xe/nouveau), `current_link_speed/width` | Szerokość linku PCIe ma znaczenie przy MoE offload (§2.2.5). | standard sysfs `[INFERENCE: brak jednego dokumentu]` |
| AMD VRAM/GTT | `/sys/class/drm/cardN/device/mem_info_vram_total`, `mem_info_vis_vram_total`, `mem_info_gtt_total`, `*_used` | Na APU kluczowy jest **GTT** (Strix Halo: limit TTM `pages_limit`, AMD zaleca mały carve-out i duży GTT). | [kernel amdgpu driver-misc](https://docs.kernel.org/gpu/amdgpu/driver-misc.html), [ROCm Strix Halo](https://rocmdocs.amd.com/en/develop/how-to/system-optimization/strixhalo.html) |
| AMD arch (gfx) | `/sys/class/kfd/kfd/topology/nodes/*/properties` (`gfx_target_version`) | U nas `gfx1100` ([SPEC](../../qwen-opt/SPEC-QWEN27B.md)). | `[INFERENCE: sprawdzone lokalnie tylko co do istnienia KFD]` |
| ROCm używalny? | `/dev/kfd` i `/dev/dri/renderD*` z prawem RW (grupy `render`/`video`), biblioteka `libamdhip64.so` | Instalator Ollamy dopisuje użytkownika do grup render/video ([log w #16591](https://github.com/ollama/ollama/issues/16591)). | jw. |
| AMD: uśpienie | runtime PM/BACO: przy bezczynności VRAM migruje do GTT i spada do 4,4 t/s zamiast 92 | Nasz własny bug ([NOTES §usypianie](../../qwen-opt/NOTES.md)). Mikro-benchmark wykrywa takie anomalie. | lokalne |
| NVIDIA | `libnvidia-ml.so.1` (NVML), `/proc/driver/nvidia/version` | `nouveau` daje tylko ścieżkę Vulkan (NVK). | [NVML](https://docs.nvidia.com/deploy/nvml-api/latest/api/group__nvmlDeviceQueries.html) |
| Intel | Level Zero (Sysman wymaga reguł udev dla nie-roota, poza częścią zapytań) | | [Sysman security](https://oneapi-src.github.io/level-zero-spec/level-zero/latest/sysman/PROG.html) |
| RAM/CPU | `/proc/meminfo` (MemAvailable), `/proc/cpuinfo` flags (`avx2`, `avx512f`, `amx_tile`), `/sys/class/dmi/id/chassis_type`, `/sys/class/power_supply/BAT*` | **SMBIOS typ 17 (prędkość RAM) jest root-only** (`/sys/firmware/dmi/tables/DMI`, tryb 0400), więc przepustowość RAM trzeba zmierzyć. AMX wymaga `arch_prctl(ARCH_REQ_XCOMP_PERM, XFEATURE_XTILEDATA)`. | [tasksmack #1515](https://github.com/mgradwohl/tasksmack/issues/1515), [Oracle AMX](https://blogs.oracle.com/linux/intel-amx-with-uek) (>12 mies.) |

#### 2.1.3 macOS (Apple Silicon)

| Co | API | Uwagi | Źródło |
|---|---|---|---|
| Chip, RAM, rdzenie | `sysctl hw.memsize`, `machdep.cpu.brand_string` („Apple M4 Pro"), `hw.perflevel0/1.physicalcpu` (P/E), `hw.model`, `hw.optional.arm.FEAT_*` | ggml ma osobne warianty CPU `apple_m1`, `apple_m2_m3` (I8MM), `apple_m4` (SME). | `~/llama-master/ggml/src/CMakeLists.txt:542-544` |
| Budżet GPU | Metal `MTLDevice.recommendedMaxWorkingSetSize`, `hasUnifiedMemory`, `maxBufferLength` | W praktyce ~66–75% RAM. Apple podaje: 32 GB daje 21 GB, 64 GB daje 48 GB. llama.cpp traktuje *free* jako `recommendedMaxWorkingSetSize` minus własne alokacje. | [Apple docs](https://developer.apple.com/documentation/metal/mtldevice/recommendedmaxworkingsetsize), [Apple tech talk](https://developer.apple.com/videos/play/tech-talks/10580/) (>12 mies.), [unsloth PR #13319](https://github.com/unslothai/unsloth/pull/13319) |
| Podniesienie limitu | `sudo sysctl iogpu.wired_limit_mb=…` | Wymaga sudo, więc **nie robić tego w aplikacji konsumenckiej**; najwyżej porada w trybie zaawansowanym. Pułapka: mmap całego pliku liczy się do working set ([#29465](https://github.com/ggml-org/llama.cpp/issues/29465), [#24510](https://github.com/ggml-org/llama.cpp/issues/24510)). | [devnote](https://github.com/ivanopcode/devnote-override-macos-metal-vram-cap) |
| Przepustowość | Brak API, więc tabela po wariancie chipa (M4 Max: 410 albo 546 GB/s zależnie od binu) albo pomiar | Wariant zależy od liczby rdzeni GPU (`system_profiler SPDisplaysDataType`, ~1 s) `[INFERENCE: także IOKit „gpu-core-count"]`. | [Apple M4 Pro/Max](https://www.apple.com/newsroom/2024/10/apple-introduces-m4-pro-and-m4-max/) (>12 mies.), [M5 Pro/Max](https://www.apple.com/newsroom/2026/03/apple-introduces-macbook-pro-with-all-new-m5-pro-and-m5-max/) |
| Bateria | IOKit `IOPSCopyPowerSourcesInfo` `[INFERENCE]` | Optymalizacja „na noc" powinna wymagać zasilania z sieci. | — |

#### 2.1.4 Gotowe biblioteki (stan na 2026-10-15, crates.io API)

| Biblioteka | Wersja / data | Co daje | Ocena dla nas |
|---|---|---|---|
| `sysinfo` (Rust) | 0.39.6 / 2026-07-09 | CPU, RAM, OS, procesy; **bez GPU** | Baza dla CPU/RAM. |
| `nvml-wrapper` | 0.13.0 / 2026-08-31 | Pełne NVML, ładowane dynamicznie | Tak, dla NVIDIA. |
| `wgpu` | 30.0.1 / 2026-08-22 | `AdapterInfo` (nazwa, vendor, device, typ, driver) | **Brak rozmiaru VRAM** `[INFERENCE z API AdapterInfo]`. Za mało. |
| `ash` | 0.38.0 (Vulkan 1.3.281) / 2024-04 | Surowy Vulkan: sterty, budget, pci_bus_info | Tak (stary release, ale stabilny). |
| `windows` | 0.62.2 / 2025-10 | DXGI, DXCore, WMI, SMBIOS | Tak. |
| `objc2-metal` | 0.3.2 / 2025-10 | Metal | Tak. |
| `raw-cpuid` | 11.6.0 / 2025-09 | CPUID | Tak. |
| `amdgpu-sysfs` | 0.22.0 / 2026-10-03 | sysfs AMD (Linux) | Opcjonalnie. |
| `all-smi` | 0.27.1 / 2026-10-11 | Monitoring wielu vendorów (NVML, Level Zero…) | Do podejrzenia, nie jako zależność. |
| hwloc (C) 2.x | — | OS devices: `CUDAGlobalMemorySize`, `RSMIVRAMSize/RSMIGTTSize`, `LevelZeroMemorySize`, `OpenCLGlobalMemorySize` | Ciężka zależność; crate `hwloc2` jest z 2020. [hwloc attrs](https://www.open-mpi.org/projects/hwloc/doc/v2.8.0/a00365.php) (>12 mies.) |
| `llmfit-core` (Rust, MIT) | 1.1.17 / 2026-10-08, 37 955★ | Parsuje `nvidia-smi`, `rocm-smi`, `system_profiler`; tabela ~80 GPU z przepustowością | Kruche, bo zależy od obecności CLI. Do nauki, nie do kopiowania. [README](https://github.com/AlexsJones/llmfit) |

#### 2.1.5 Jak raportuje urządzenia llama.cpp/ggml

- `ggml_backend_dev_props` zawiera: `name`, `description`, `memory_free`, `memory_total`, `type` (CPU/GPU/IGPU/ACCEL), `device_id` (PCI bus id `"0000:c1:00.0"`) i `caps` (`~/llama-master/ggml/include/ggml-backend.h:164-181`). PCI bus id to klucz do sparowania z NVML, DXGI i sysfs.
- Backend CPU ma warianty ładowane według wykrytych cech: x86 od `x64` przez `haswell` (AVX2), `skylakex`, `icelake`, `zen4` aż po `sapphirerapids` (AMX); ARM od `armv8.0` do `armv9.2` (SME) (`CMakeLists.txt:494-544`). Wybór wariantu robi sam ggml, więc nie musimy tego duplikować.
- Wartości „free" per backend:
  - Vulkan: budget − usage;
  - CUDA/HIP: `cudaMemGetInfo` `[INFERENCE]`;
  - Metal: `recommendedMaxWorkingSetSize` minus własne alokacje.
- Fit: `common_params_fit_impl` w ~0,3–1,2 s rzutuje zużycie i redukuje kontekst, potem przenosi ekspertów MoE na CPU (`-ot …exps=CPU`) aż do marginesu 1024 MiB ([fit-params README](https://github.com/ggml-org/llama.cpp/tree/master/tools/fit-params)). Ta sama logika wypisuje u nas `memory breakdown` (`~/qwen-opt/k3/logs_verbose.log:17-24`).

#### 2.1.6 Przepustowość pamięci: tabela vs mikro-benchmark

| Metoda | Plusy | Minusy |
|---|---|---|
| Tabela po modelu GPU (spec. producenta) | Natychmiast, bez obciążania GPU | Warianty laptopowe (TGP, zegar pamięci), biny Apple (M4 Max 410/546), iGPU zależne od RAM (1 vs 2 kanały). Ollama, Strata i llmfit przez takie błędy wykrywania podawały nonsensowne dane. |
| Wyliczenie z API | NVML: szerokość szyny × max zegar pamięci; CUDA 13: `cudaDevAttrMemoryClockRate` (pole `memoryClockRate` usunięte z `cudaDeviceProp`); HIP props; sysfs `pp_dpm_mclk` | Mnożniki DDR/GDDR6X/GDDR7 trzeba znać per typ. Vulkan nie ma takiej właściwości `[INFERENCE]`. [CUDA 13.0 notes](https://developer.nvidia.com/blog/whats-new-and-important-in-cuda-toolkit-13-0/) |
| Mikro-benchmark odczytu (≥1 GiB bufor, 1–3 s, rozgrzewka 200 ms) | Mierzy realny stan: PCIe x4, oszczędzanie energii, VRAM w GTT, laptop na baterii | Musi pokonać cache (96 MB Infinity Cache na 7900 XTX, SLC Apple). Odczyt-redukcja jest lepszy niż kopia. |
| **Krótki `tg` właściwym modelem** (32–64 tokeny) | To jest dokładnie metryka, którą pokazujemy jako baseline | Wymaga pobrania modelu, ale i tak to robimy. |

Zweryfikowane wartości referencyjne (GB/s):

| Urządzenie | GB/s | Urządzenie | GB/s |
|---|---|---|---|
| RTX 5090 | 1792 | RTX 4090 | 1008 |
| RX 7900 XTX | 960 | RTX 3090 | 936 |
| RTX 5070 | 672 | RX 9070 XT | 640 |
| Arc B580 | 456 | RTX 5060 Ti | 448 |
| RTX 4060 | 272 | M5 Max | 614 |
| M4 Max | 546 / 410 | M5 Pro | 307 |
| M4 Pro | 273 | DGX Spark | 273 |
| Ryzen AI Max+ 395 | ~256 | M5 | 153 |

Źródła: [RTX 50](https://www.runpod.io/articles/guides/nvidia-rtx-5090), [tomshardware 5070/5060Ti](https://www.tomshardware.com/pc-components/gpus/rtx-5070-vs-rtx-5060-ti-16gb) (>12 mies.), [Intel B580](https://www.intel.com/content/www/us/en/products/sku/241598/intel-arc-b580-graphics/specifications.html), [AMD 7900 XTX: 960 GB/s, 123 TFLOPS FP16 matrix](https://www.amd.com/en/support/downloads/drivers.html/graphics/radeon-rx/radeon-rx-7000-series/amd-radeon-rx-7900-xtx.html), [Apple M5 Pro/Max](https://www.apple.com/newsroom/2026/03/apple-introduces-macbook-pro-with-all-new-m5-pro-and-m5-max/), [M5 153](https://www.parallels.com/blogs/apple-m5-chip/), [DGX Spark](https://www.pny.com/dgx-spark), [Strix Halo](https://www.cpu-monkey.com/en/cpu-amd_ryzen_ai_max_plus_395).

**Rekomendacja:** tabela służy do *wstępnej* rekomendacji przed pobraniem. Potem mierzymy (3 s) i porównujemy z tabelą. Gdy pomiar wynosi < 50% tabeli, pokazujemy diagnozę (PCIe, oszczędzanie energii, spill do RAM).

---

### 2.2 Estymacja pamięci i prędkości

#### 2.2.1 Wagi per quant

Bajty na wagę w llama.cpp:

| Typ | Bajty/wagę |
|---|---|
| Q4_0 / Q4_K | 0,5625 (4,5 bpw) |
| IQ4_XS | 0,53 (4,25 bpw) |
| Q5_K | 0,6875 |
| Q6_K | 0,8203 |
| Q8_0 | 1,0625 |
| MXFP4 | 0,53 |

Te wartości wynikają z rozmiaru bloku; `[INFERENCE]` dla IQ4_XS/MXFP4. Miksy „_M"/„UD-" mają realnie 4,7–5,1 bpw. Najprościej czytać rozmiary tensorów z nagłówka GGUF; HF obsługuje Range requests, więc wystarczy kilka MB.

Rzeczywiste rozmiary plików ([HF API](https://huggingface.co/api/models/unsloth/Qwen3.8-27B-GGUF?blobs=true)):

| Model | Wariant | Rozmiar | bpw |
|---|---|---|---|
| Qwen3.8-27B (27,78B) | UD-Q4_K_XL | 17,56 GB | 5,06 |
| Qwen3.8-27B | Q8_0 | 29,05 GB | 8,37 |
| Qwen3.5-9B (9,65B) | Q4_K_M | 5,68 GB | 4,71 |

**Rozmieszczenie w llama.cpp:**
- `token_embd` zawsze zostaje na CPU (`llama-model.cpp:1638-1640`).
- Przy wiązanej głowicy (LFM) tensor jest duplikowany na GPU jako `output`.

Nasze GGUF (zmierzone `gguf-py`):

| Model | Wagi na GPU | Na CPU |
|---|---|---|
| Qwen | 16,833 GB = **16 053 MiB** (log: 16 053,22) | 0,715 GB = 682 MiB (log: 682,03) |
| LFM | 17,021 GB = **16 233 MiB** (log: 16 232,83) | — |

#### 2.2.2 KV cache: wzory

| Architektura | Bajty na token kontekstu | Przykład |
|---|---|---|
| MHA/GQA | `Σ_attn-layers n_kv_heads·(d_k+d_v)·b` | Qwen3.8-27B: 16 warstw attn × 4 głowy × (256+256) → **64 KiB/tok f16, 18 KiB q4_0**; LFM2.5-24B: 10 × 8 × (64+64) → 20 KiB f16 |
| Kwanty KV | b = 2 (f16), 1,0625 (q8_0), 0,5625 (q4_0) | — |
| MLA (DeepSeek) | Tylko K: `n_layer·(kv_lora_rank+d_rope)·b`, w llama.cpp brak tensora V (`has_v = !is_mla`, `llama-kv-cache.cpp:163,231`) | DeepSeek-V3 (61 × 576 × 2) ≈ 70 KB/tok `[INFERENCE z configu V3]` |
| SWA / iSWA (Gemma, gpt-oss) | Warstwy SWA mają rozmiar `min(n_ctx, n_swa·n_seq + n_ubatch)` zaokrąglony do 256; reszta pełne n_ctx; `--swa-full` wyłącza oszczędność | `llama-kv-cache-iswa.cpp:73`; DSA (DeepSeek V4) analogicznie (`llama-kv-cache-dsa-iswa.cpp:53`) |
| Hybrydy rekurencyjne (GDN, Mamba-2, shortconv) | Stała na sekwencję, niezależna od n_ctx: GDN `H_v·d_k·d_v·4 B` + conv `(K−1)·C·4 B` na warstwę; przy spekulacji × (1 + n_rs_seq) snapshotów | Qwen: 48 × (48·128·128·4 + 3·10240·4) = **149,6 MiB**; z 4 snapshotami ×5 = **748 MiB** (log: context 4348 = 3600 KV + 748) |

**Wniosek produktowy:** hybrydy (Qwen3.5+/3.8, LFM, Nemotron-H) mają KV 3–4× mniejszy niż gęste GQA. Dlatego na 16–24 GB można dać długi kontekst. Estymator musi znać typ warstw (z GGUF: `full_attention_interval`, tablica `head_count_kv`).

#### 2.2.3 Bufory compute i narzut runtime

- `n_outputs_max` = `n_batch` (domyślnie), a graf jest rezerwowany na `n_outputs = min(n_ubatch, n_outputs_max)` (`llama-context.cpp:254,695`). Logity zajmują więc `n_vocab·n_ubatch·4 B` w buforze compute GPU:
  - Qwen (vocab 248 320, ub 512): **485 MiB**;
  - LFM (128 000): **250 MiB**.
- Część zależna od kontekstu (maska/FA scratch) dopasowana z naszych logów to 1,2 KiB (LFM) do 2,95 KiB (Qwen) na token kontekstu przy ub=512. Qwen: 533 MiB przy 8192, 1100 MiB przy 204 800.
- Narzut runtime/sterownika („unaccounted"): 242 MiB (ROCm, log LFM). Odczyt urządzenia dla Qwen ROCm to 23,2 GB vs 22 569 MiB z llama.cpp. Na Windows dochodzi pamięć kompozytora na GPU z monitorem `[INFERENCE]`. Dlatego zawsze bierzemy **bieżące free/budget**, a nie total.

#### 2.2.4 Test wzoru na 3 punktach z NOTES (ręcznie)

**Wzór pamięci:** `M = W_gpu + KV + RS·(1+n_rs_seq) + n_vocab·n_ub·4 + β·n_ctx + [draft: KV_d + C_d] + O_rt`

**Punkt 1 — Qwen3.8-27B UD-Q4_K_XL, RX 7900 XTX 24 GB, ROCm, ctx 204 800, KV q4_0, MTP n=4**

| Składnik | Wzór | MiB | Log llama.cpp (`k3/logs_verbose.log`) |
|---|---|---|---|
| Wagi GPU | GGUF − token_embd | 16 053 | 16 053 |
| KV | 16·2·1024·0,5625·204 800 | 3 600 | 3 600 |
| Stany GDN | 149,6 × 5 | 748 | (w „context" 4 348) |
| Compute | 485 + 48 + 2,95 KiB·204 800 | 1 124 | 1 100 |
| Draft MTP: KV f16 1 warstwa | 1·2·1024·2·204 800 | 800 | 800 |
| Draft compute | (z logu) | 268 | 268 |
| **Suma** | | **22 593** | **22 569** (projekcja fit), urządzenie: **23 200** (SPEC ROCm), 22 300 (Vulkan) |

Naiwnie (wagi + KV + 1 stan + logity) wychodzi 20 288 MiB, czyli −10%: brakuje snapshotów, części compute zależnej od ctx i kontekstu draftu.

**Punkt 2 — LFM2.5-24B-A2B Q5_K_M, ctx 131 072** (`~/wt/lfm2-prof/kvvram.q8_0.log`)

| Wariant | Wagi | KV | RS | Compute | Suma (wzór) | llama.cpp | Urządzenie |
|---|---|---|---|---|---|---|---|
| KV q8_0 | 16 232 | 10·2·512·1,0625·131 072 = 1 360 | 0,5 | 404 (250 logity + 1,2 KiB·ctx) | **17 996** | **17 997** | 18 239 (+242 runtime) |
| KV q4_0 | 16 232 | 720 | 0,5 | ~404 | 17 356 (+242 = 17 598) | — | NOTES: „17,8 GB" (−1,1%) |

**Punkt 3 — prędkość (decode, prefill, spekulacja)**

`B_tok` (bajty czytane na token) liczę tak:
- Qwen: wagi GPU − warstwa MTP (351 MB, nieużywana bez spekulacji) + odczyt i zapis stanów GDN (2×157 MB) = **16,80 GB**;
- LFM: 1,78 GB (eksperci 4/64 + shortconv + głowica + gęste + atencja; [NOTES §LFM](../../qwen-opt/NOTES.md)).

| Pomiar (NOTES/SPEC) | Roofline BW/B_tok | Zmierzone | η = zmierzone/roofline | llmfit (`BW/rozmiar×0,55`) |
|---|---|---|---|---|
| Qwen decode tg128, Vulkan | 960/16,80 = **57,2 t/s** | 38,6 | **0,67** | 30,1 (−22%) |
| Qwen decode tg128, ROCm | 57,2 | 34,8 | **0,61** | 30,1 (−14%) |
| LFM tg128 upstream e60eff95f | 960/1,78 = **539 t/s** | 169,3 | **0,31** | ~296 (+75%) |
| LFM tg128 fork, 70 łatek + PM4 | 539 | 294,8 | **0,55** | ~296 (0%, przypadkiem) |
| Qwen prefill pp4096 (ROCm) | FLOP/tok ≈ 2·24,35B + 0,8 GFLOP attn ≈ 49,5 GFLOP | 1 044 → 1 123 t/s | **0,42–0,45** z 123 TFLOPS | `null` bez danych TFLOPS |
| LFM prefill pp4096 | ≈ 4,6 GFLOP/tok (~2,2B aktywnych) | 6 124 t/s | **0,23** | — |
| Qwen MTP n=4 (spekulacja) | — | 108,8 t/s = 3,02 tok/krok ÷ 27,80 ms/krok | — | brak modelu |

**Wniosek: potrzebny model dwuczłonowy.** `t_tok ≈ B_tok/(η_bw·BW) + N_kern·t_gap`. Z naszych pomiarów:
- t_gap ≈ 2,5–3,2 µs w HIP graph, a 0,46–0,86 µs przy PM4 replay.
- N_kern ≈ 2 000 dla Qwena i 721 → 305 dla LFM.

Dla Qwena (ROCm) daje to 28,7 ms = 6,4 ms przerw + 22,3 ms czytania, czyli efektywnie 752 GB/s (η_bw 0,78). NOTES potwierdzają, że mmvq czyta z 81–88% piku. Dla LFM (fork, 198 t/s) wychodzi 5,05 ms = ~1,3 ms przerw + ~3,8 ms pracy.

Model dwuczłonowy wyjaśnia oba przypadki i wskazuje, co da się przyspieszyć:
- **η_bw** przez tuning kerneli;
- **N_kern·t_gap** przez fuzje i replay grafu.

To jest naturalny język dla ekranu „przed → po" w optymalizacji nocnej.

**Spekulacja:** `t/s ≈ τ/(t_verify(k) + k·t_draft)`, gdzie τ to średnia liczba przyjętych tokenów na krok. τ zależy od języka i typu tekstu (u nas proza PL ~59 t/s vs kod EN ~105). Nie da się jej przewidzieć a priori, trzeba zmierzyć.

#### 2.2.5 MoE offload: matematyka

- **Decode** przy ekspertach na CPU: `t_tok ≈ B_gpu/(η_g·BW_gpu) + B_cpu_aktywne/(η_c·BW_RAM) + N·t_gap + 2·n_layers·t_sync` `[INFERENCE: t_sync ~10–50 µs, niezmierzone]`.

  Przykład `[INFERENCE, założenia jawne]`: Qwen3.6-35B-A3B UD-Q4_K_M (22,13 GB) na RTX 4060 8 GB (272 GB/s) + DDR5-5600 2×64 bit (89,6 GB/s teor.). Zakładam aktywne ~1,9 GB/token, z czego 1,2 GB ekspertów w RAM przy η_c = 0,65. Wychodzi 3,2 ms + 20,6 ms, czyli sufit ~42 t/s, realnie 25–35 t/s.
- **Prefill:** dla batchy ≥ 32 llama.cpp przesyła wagi z CPU na GPU (`GGML_OP_OFFLOAD_MIN_BATCH`, domyślnie 32; `ggml-cuda.cu:7354`, `ggml-vulkan.cpp:16173`). Prefill jest wtedy ograniczony przez **PCIe**: ~20 GB ekspertów / ~13 GB/s (PCIe 4.0 x8, RTX 4060 `[INFERENCE: spec z pamięci]`) ≈ 1,6 s na ubatch, czyli ≤ 320 t/s przy ub=512. Większy `-ub` (2048–4096) amortyzuje ten koszt.

  Wniosek: **odczyt szerokości linku PCIe to istotna część wykrywania.**

#### 2.2.6 Istniejące narzędzia i ich trafność

| Narzędzie | Metoda | Trafność / znane problemy |
|---|---|---|
| **llama.cpp `--fit` / `llama-fit-params`** | Rezerwacja grafu „no_alloc" na prawdziwym modelu; margines 1024 MiB; przenoszenie ekspertów na CPU | Dokładne co do MiB (nasz log: projekcja 22 569 MiB). Bugi przy ręcznym `-ngl 99` ([#21801](https://github.com/ggml-org/llama.cpp/issues/21801), [#19437](https://github.com/ggml-org/llama.cpp/issues/19437)). |
| **gguf-parser-go** (gpustack) | Parsuje GGUF zdalnie, liczy RAM/VRAM na urządzenie, eksperymentalnie „MAX TPS" z `--device-metric "<FLOPS>;<BW>"` | Odwzorowuje logikę llama.cpp, ale musi gonić zmiany architektur `[INFERENCE]`. [README](https://github.com/gpustack/gguf-parser-go) |
| **llmfit** (Rust, MIT, ~38k★) | Tabela ~80 GPU; `BW/size × 0,55`; MoE z aktywnych parametrów; fit-levels wg wykorzystania puli (≤60% Perfect, ≤85% Good, ≤98% Marginal); społecznościowe benchmarki i mediany LocalMaxxing | U nas −22%…+75% (tabela wyżej). Uczciwie oznacza `estimate_confidence` (measured/calibrated/estimated). Sami przyznają, że fallback MoE był ~2,6× za nisko dla gpt-oss-120b. [how-it-works](https://raw.githubusercontent.com/AlexsJones/llmfit/main/docs/how-it-works.md) |
| **arXiv 2609.14864** (2026-09) | Roofline z metadanych GGUF, współczynniki per kwant | Decode MAPE 13,1 / 14,4 / 36,1%, liczenie z total params 49–55%, prefill 18–108%. „Fitted efficiencies are not universal." [arXiv](https://arxiv.org/abs/2609.14864) |
| **HF Hardware compatibility** | Panel na stronach GGUF/MLX wg sprzętu zapisanego w profilu; API `hardwareItems` | Tylko „czy zmieści się dany kwant"; metodologia nieopisana. [HF docs](https://huggingface.co/docs/hub/hardware) |
| **LM Studio guardrails** | Od 0.3.27 estymata uwzględnia ctx, FA i vision; `lms load --estimate-only` | Zgłoszenia, że ostrzeżenie OOM się nie pojawia ([#1753](https://github.com/lmstudio-ai/lmstudio-bug-tracker/issues/1753)). [0.3.27](https://lmstudio.ai/blog/lmstudio-v0.3.27) (>12 mies.) |
| **Ollama** | Scheduler: free − GpuOverhead − MinimumMemory, warstwami | Regresje: 0.30.0 ładował ministral-3:14b w 45 GB zamiast 29 GB, bo FA wyłączone na CC 6.x ([#16591](https://github.com/ollama/ollama/issues/16591)); Windows 0.20.x „memory layout cannot be allocated" dla modeli >10 GB ([#15352](https://github.com/ollama/ollama/issues/15352)); 0 GB VRAM na GTX 10xx ([#14280](https://github.com/ollama/ollama/issues/14280)). |
| **apxml VRAM calculator** | Wagi × bajty, KV dla MHA/GQA/MLA, roofline | Strona deklaruje walidację na vLLM/TRT-LLM, nie na llama.cpp. [apxml](https://apxml.com/tools/vram-calculator) |

---

### 2.3 Katalog modeli i rekomendacje

#### 2.3.1 Stan rynku otwartych modeli (październik 2026)

Dane z HF API: daty, parametry, licencje.

- **Qwen:**
  - Qwen3.8-27B (27,78B, Apache-2.0, 2026-08-05);
  - Qwen3.6-35B-A3B (Apache, 2026-04);
  - Qwen3.5-0.8B/2B/4B/9B (Apache, 2026-02);
  - Qwen3.5-122B-A10B (Apache);
  - **Qwen3.8-Flash-Next** (125B, 6B aktywnych, plus 51B n-gram embedding i 4B MTP; **Qwen Community License 1.0**; [karta](https://huggingface.co/Qwen/Qwen3.8-Flash-Next)).
- **Google Gemma 4:** E2B, E4B, 12B (2026-06), 26B-A4B (3,8B aktywnych), 31B. **Apache-2.0** ([blog](https://blog.google/innovation-and-ai/technology/developers-tools/gemma-4/), [model card](https://ai.google.dev/gemma/docs/core/model_card_4)). Oficjalne GGUF Q4_0 QAT.
- **OpenAI:** gpt-oss-20b (20,91B) i gpt-oss-120b (116,83B), Apache-2.0 (2025-08, >12 mies., ale wciąż aktualne).
- **Mistral:**
  - Mistral Small 4 119B-A6.5B (Apache, 256k, języki m.in. **pl**; [karta](https://huggingface.co/mistralai/Mistral-Small-4-119B-2603));
  - Ministral 3 14B (Apache);
  - Devstral Small 2 24B (Apache wg Mistrala).
- **LiquidAI:** LFM2.5-24B-A2B (2026-10-12), LFM2.5-8B-A1B (8,3B/1,5B aktywnych; języki bez pl), LFM2.5-2.6B. **LFM Open License v1.0**: komercyjnie tylko poniżej 10 mln USD rocznego przychodu ([LICENSE](https://huggingface.co/LiquidAI/LFM2.5-24B-A2B/blob/main/LICENSE)).
- **NVIDIA:**
  - Nemotron 3.5 Lightning 30B-A3B;
  - **Nemotron 3.5 Bolt 74B-A9B-24GB**: GGUF IQ2 z QAT, zaprojektowany na < 24 GB przy 128K ctx, licencja OpenMDW-1.1 ([karta](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Bolt-74B-A9B-24GB-GGUF)).
- **GLM:** GLM-4.7-Flash (31B, MIT), GLM-5.3-Flash (321B, MIT).
- **DeepSeek:** V4.x (MIT, ≥ 700B, poza zasięgiem konsumenckim).
- **IBM Granite 4.2** (3B/8B/30B, Apache).
- **MiniCPM5-2B** (Apache).
- **Meta Llama:** brak nowych otwartych wydań od Llamy 4 (2025-04) ([HF org](https://huggingface.co/meta-llama)), więc niski priorytet.
- **Microsoft Phi:** ostatni Phi-4-reasoning-vision-15B (2026-01).
- **Polskie modele:**
  - Bielik-11B-v3.0 i Bielik-Minitron-7B-v3 (Apache-2.0; safetensors `gated=auto`, GGUF niegatowane);
  - PLLuM-4B/12B (Apache; [CYFRAGOVPL](https://huggingface.co/CYFRAGOVPL)).

**Ranking jakości:**
- Artificial Analysis: „Qwen3.8 27B (xhigh/medium) to najlepsze otwarte modele Small 4–40B"; w Tiny ≤4B prowadzą K2 Horizon 3.7B i MiniCPM5-2B ([AA small](https://artificialanalysis.ai/models/open-source/small), [AA tiny](https://artificialanalysis.ai/models/open-source/tiny)).
- LocalMaxxing: Qwen3.8-27B-GGUF to najczęściej testowany model (579 runów; [LocalMaxxing](https://www.localmaxxing.com/en)).

#### 2.3.2 Tabela tier → model

Rozmiary to GGUF z HF API (GB dziesiętne). „Budżet" = pamięć na wagi, KV i compute.

| Tier (przykładowy sprzęt, BW) | Domyślny (czat PL/EN) | Kodowanie / agent | Rozumowanie | Wizja | Polski (opcja) | Szybki wariant |
|---|---|---|---|---|---|---|
| **CPU-only, 8–16 GB RAM** (DDR4-3200 2ch 51 GB/s; DDR5-5600 89,6) | Qwen3.5-4B Q4_K_M **2,74** | — | Qwen3.5-4B (thinking) | Qwen3.5-4B / Gemma 4 E4B Q4_K_M 4,98 | Bielik-Minitron-7B-v3 Q4_K_M 4,50 | LFM2.5-8B-A1B Q4_K_M 5,16 (1,5B aktywnych); MiniCPM5-2B Q4_K_M 1,56 |
| **4 GB VRAM** (GTX 1650, 5,13% Steam) | Qwen3.5-4B Q4_K_M 2,74 (krótki ctx) | — | — | — | — | MiniCPM5-2B |
| **6–8 GB** (RTX 4060 272 GB/s, 3060 Ti, 4060 Laptop) | Qwen3.5-9B Q4_K_M **5,68** / UD-Q4_K_XL 5,97 | Qwen3.5-9B | Qwen3.5-9B | Gemma 4 E4B Q6_K 7,07 | Bielik-11B-v3 Q4_K_M 6,72 (ciasno) | MoE offload: Qwen3.6-35B-A3B (eksperci w RAM, ≥ 32 GB RAM) |
| **12 GB** (RTX 5070 672, 3060 12G 360) | Gemma 4 12B UD-Q4_K_XL **7,37** / Q6_K 9,79 (Apache, obraz i audio, 256k) | Ministral-3-14B Q4_K_M 8,24 | Qwen3.5-9B Q8_0 9,53 | Gemma 4 12B | Bielik-11B-v3 Q6_K 9,16 | gpt-oss-20b MXFP4 12,11 (częściowy offload) |
| **16 GB** (RTX 5060 Ti 448, 5070 Ti 896, 9070 XT 640) | **Qwen3.8-27B UD-Q3_K_XL 13,15** (jakość; KV tylko 18 KiB/tok q4_0) | Devstral Small 2 Q4_K_M 14,33 | gpt-oss-20b MXFP4 12,11 | Gemma 4 26B-A4B UD-Q3_K_XL 12,91 | Bielik-11B-v3 Q8_0 11,87 | gpt-oss-20b, Gemma 4 26B-A4B, LFM2.5-24B-A2B Q4_K_M 14,53 (licencja) |
| **24 GB** (3090 936, 4090 1008, 7900 XTX 960) | **Qwen3.8-27B UD-Q4_K_XL 17,56** (nasz flagowiec: 109 t/s z MTP) | Qwen3.6-35B-A3B UD-Q4_K_M 22,13 / MXFP4_MOE 21,71 | Qwen3.8-27B | Gemma 4 31B UD-Q4_K_XL 18,82; Nemotron 3.5 Bolt 74B-A9B-24GB | Bielik-11B-v3 Q8_0 + długi ctx | LFM2.5-24B-A2B Q5_K_M 17,03 (295 t/s u nas); Gemma 4 26B-A4B UD-Q5_K_M 21,15; GLM-4.7-Flash UD-Q4_K_XL 17,52 (MIT) |
| **32 GB** (RTX 5090 1792, R9700 32 GB) | Qwen3.8-27B UD-Q6_K 21,98 (albo Q8_0 29,05 z krótkim ctx) | Qwen3.6-35B-A3B UD-Q5_K_M 26,46 | jw. | Gemma 4 31B Q6_K 25,20 | — | Qwen3.6-35B-A3B |
| **Apple 16 GB** (budżet GPU ~10,7–12 GB; M4 120, M5 153) | Qwen3.5-9B Q4_K_M 5,68 | Qwen3.5-9B | Qwen3.5-9B | Gemma 4 12B Q4_K_M 7,12 | Bielik-Minitron-7B | LFM2.5-8B-A1B |
| **Apple 24–36 GB** (M4 Pro 273, M5 Pro 307) | Qwen3.8-27B UD-Q4_K_XL (od 32 GB) / Gemma 4 26B-A4B | Qwen3.6-35B-A3B Q4 (36 GB) | gpt-oss-20b | Gemma 4 26B-A4B | Bielik-11B-v3 Q8_0 | gpt-oss-20b |
| **Apple 48–64 GB** (M4 Max 410/546) | Qwen3.8-27B Q8_0 29,05 | Qwen3.6-35B-A3B Q8_0 36,9 | Qwen3.8-27B | Gemma 4 31B Q8_0 33,15 | — | Qwen3.6-35B-A3B |
| **Apple 96–128 GB / Strix Halo 128 / DGX Spark** (614 / 256 / 273) | gpt-oss-120b MXFP4 63,39 | Qwen3.5-122B-A10B UD-Q4_K_XL 77,03 | Qwen3.8-Flash-Next UD-Q3_K_XL 89,99 (licencja Qwen Community) | Mistral Small 4 UD-Q4_K_M 73,76 (z pl) | Mistral Small 4 | gpt-oss-120b (5,1B aktywnych `[INFERENCE: z karty OpenAI]`) |

Rozmiary i licencje: [HF API](https://huggingface.co/api/models/unsloth/Qwen3.8-27B-GGUF?blobs=true) dla repozytoriów `unsloth/*`, `ggml-org/gpt-oss-*`, `LiquidAI/*`, `speakleash/*`, `ibm-granite/*`, `openbmb/*` (zapytanie z 2026-10-15). Budżety Apple wynikają z reguły ~66–75% RAM ([Apple](https://developer.apple.com/videos/play/tech-talks/10580/)).

Szybkości orientacyjne z modelu z §2.2.4 (`[INFERENCE]`, η_bw·efekt przerw ≈ 0,6 dla gęstych):
- Qwen3.5-9B Q4_K_M na RTX 4060: ~30 t/s;
- Gemma 4 12B UD-Q4_K_XL na RTX 5070: ~60 t/s;
- Qwen3.8-27B UD-Q3_K_XL na 5060 Ti: ~22 t/s;
- Qwen3.8-27B UD-Q4_K_XL na 3090: ~35 t/s bez MTP.

#### 2.3.3 Jakość vs kwantyzacja

- **4-bit to złoty środek.** Gemma 3 27B, MMLU 5-shot (Unsloth): BF16 71,5; Q8_0 71,60; Q6_K 71,87; Q5_K_M 71,77; UD-Q4_K_XL 71,47; Q4_K_M 71,23; Q3_K_XL 70,87; Q2_K_XL 68,70; IQ1_M 48,10 ([Unsloth D2.0](https://unsloth.ai/docs/basics/dynamic-3.0-ggufs)).
- **KLD lepiej rozróżnia kwanty.** Qwen3.5: Unsloth Q4_K_M ma KLD mean 0,0192 przy 18,49 GB, a UD-Q4_K_XL 0,0137 przy 19,17 GB ([Unsloth Qwen3.5 benchmarks](https://unsloth.ai/docs/models/qwen3.5/gguf-benchmarks), via [HN](https://news.ycombinator.com/item?id=47192505)).
- **Dynamic 3.0 (2026-09/10, Qwen3.8-27B):** „>10% top-1 lepiej przy tym samym rozmiarze". Pod UD-Q2_K_XL następuje gwałtowny spadek „Divergence-300@32" z ~25% do 8–10%; 1-bit nie nadaje się do tool callingu ([Unsloth D3.0](https://unsloth.ai/docs/basics/dynamic-3.0-ggufs)). To deklaracje twórcy kwantów, nie niezależny pomiar.
- **Llama-3.1-8B:** PPL F16 7,32 vs Q3_K_S 8,96 ([arXiv 2601.14277](https://arxiv.org/abs/2601.14277)).
- **Uwaga metodologiczna.** W „silent zone" (ΔlogPPL ≤ 0,04, KLD ≲ 0,064) PPL i KLD w ogóle nie rankują kwantów (korelacja ~0) ([arXiv 2606.19558](https://arxiv.org/html/2606.19558)). Z kolei „flips": do 13,6% zmienionych odpowiedzi przy prawie równej dokładności ([arXiv 2407.09141](https://arxiv.org/abs/2407.09141), >12 mies.). Wniosek: wybieramy największy kwant mieszczący się w budżecie, a jakość pilnujemy własnym KLD-gate i zestawem zadań. Tak robimy już dziś (NOTES: KLD 0,0042–0,0067 dla łatek nie-bitowych).
- **Kwantyzacja KV też kosztuje.** U nas KV q8_0 vs f16 daje KLD 0,044 i ratio PPL 1,0026–1,0138 ([NOTES runda 3](../../qwen-opt/NOTES.md)). Estymator powinien pokazywać kwant KV jako parametr jakości, nie tylko pamięci.

#### 2.3.4 Licencje: redystrybucja i linkowanie

| Licencja | Modele | Pobieranie z HF przez aplikację | Hostowanie własnych kwantów / derywatów |
|---|---|---|---|
| Apache-2.0 | Qwen3.5/3.6/3.8-27B, Gemma 4, gpt-oss, Mistral Small 4 / Ministral 3, Granite 4.2, Bielik v3, PLLuM 4B/12B, MiniCPM5 | OK | OK: kopia licencji, NOTICE, informacja o zmianach |
| MIT | GLM-4.7/5.3-Flash, DeepSeek V4 | OK | OK |
| Qwen Community 1.0 | Qwen3.8-Flash-Next | OK | Produkty > 100 mln MAU lub > 20 mln USD miesięcznego przychodu muszą pokazywać nazwę; MaaS wymaga osobnej licencji ([cellcog, wtórne](https://cellcog.ai/blog/qwen3-8-flash-next/)) `[do weryfikacji w LICENSE]` |
| LFM Open License v1.0 | LFM2.5-* | OK | Prawa komercyjne tylko poniżej progu 10 mln USD rocznego przychodu ([LICENSE](https://huggingface.co/LiquidAI/LFM2.5-24B-A2B/blob/main/LICENSE)). Ryzyko, gdy *my* przekroczymy próg. |
| NVIDIA OpenMDW-1.1 / NVIDIA Open Model | Nemotron 3.5 | OK | „ready for commercial use" ([karta](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Bolt-74B-A9B-24GB-GGUF)) `[treść do weryfikacji]` |
| Llama 3.x Community | Llama-PLLuM 8B/70B | Repozytoria Mety są gated (potrzebny token HF) | Atrybucja i AUP `[INFERENCE: znane warunki, >12 mies.]` |

**Praktyka:** katalog domyślny buduję tylko z repozytoriów niegatowanych na licencjach Apache/MIT. Wszystkie wymienione GGUF mają `gated=False`; wyjątkiem są safetensors Bielika (`gated=auto`).

#### 2.3.5 Źródła rankingów jakości

- **Artificial Analysis Intelligence Index v4.x.** Kategorie Tiny/Small; rankuje warianty reasoning ([AA](https://artificialanalysis.ai/models/open-source/small)). Najlepszy wybór do domyślnego rankingu.
- **LMArena („Arena"), tekst.** Najlepszy otwarty to Kimi K3 z 1488 ([llmrun, wtórne](https://llmrun.dev/benchmark/lmarena-text)). Dotyczy dużych modeli, mało przydatne dla tierów lokalnych.
- **Open LLM Leaderboard (HF)** jest zarchiwizowany (2025); brak bezpośredniego następcy ([thundercompute](https://www.thundercompute.com/blog/best-open-source-llms)).
- **Lokalne ewaluacje na kwantach:** LocalMaxxing (GSM8K, HellaSwag, Terminal-Bench 2.1, HumanEval+ dla konkretnych GGUF) ([LocalMaxxing](https://www.localmaxxing.com/en)).
- **Polski:** PLCC (Bielik-11B-v3 71,83%; [arXiv 2601.11579](https://arxiv.org/abs/2601.11579)), LLMzSzŁ ([arXiv 2501.02266](https://arxiv.org/html/2501.02266v1), >12 mies.). **Brak świeżych wyników PLCC dla Qwen3.8/Gemma 4**, więc to luka do wypełnienia własnym pomiarem.

---

### 2.4 Udziały sprzętu

#### 2.4.1 Steam Hardware & Software Survey, wrzesień 2026 ([Steam](https://store.steampowered.com/hwsurvey/Steam-Hardware-Software-Survey-Welcome-to-Steam))

**System i CPU:**

| Kategoria | Udział |
|---|---|
| Windows (w tym Win 11: 71,34%, Win 10: 23,61%) | 95,03% |
| macOS | 1,92% |
| Linux | 3,05% |
| CPU Intel / AMD (Windows) | 52,59% / 47,41% ([processormfg](https://store.steampowered.com/hwsurvey/processormfg/)) |
| AVX2 | 95,95% |
| AVX-512F | 27,46% |
| AVX512-VNNI | 27,56% |

**RAM:** 32 GB 42,22%, 16 GB 37,82%, 64 GB 3,71%, 8 GB 6,47%.

**VRAM:**

| VRAM | Udział |
|---|---|
| 16 GB | 27,21% |
| 8 GB | 26,71% |
| 12 GB | 13,06% |
| 24 GB | 5,50% |
| 6 GB | 5,12% |
| 4 GB | 5,13% |
| 10–11 GB | 2,74% |
| 20–22 GB | 2,43% |
| 32 GB | 1,41% |
| 64 GB (nowa pozycja) | 0,50% |
| ≤ 3 GB (głównie iGPU) | 8,93% |

**Top GPU:** RTX 5070 5,86%, RTX 5060 4,20%, RTX 5060 Ti 3,87%, RTX 4060 3,72%, RTX 3060 3,54%, RTX 4060 Laptop 3,35%. Pozostałe istotne: RX 9070 XT 1,35%, RX 7900 XTX 0,42%, RTX 4090 0,65%, RTX 5090 0,38%, RTX 3090 0,32%, Intel Arc 0,24%.

**Vendor GPU:** NVIDIA 75,97%, AMD 16,67%, Intel 7,01% ([virtwave](https://www.virtwave.com/industry-news/steam-statistics), wtórne).

**Język:** polski 1,49%.

#### 2.4.2 Użytkownicy zainteresowani lokalnym AI

**Hugging Face „What the community is running"** ([HF hardware](https://huggingface.co/hardware)). Zliczyłem widoczne karty; liczby to deklaracje użytkowników i mogą się dublować.

| Podział | Udział |
|---|---|
| NVIDIA | ~391k (64,8%) |
| Apple Silicon | ~150k (**24,9%**) |
| AMD | ~62k (10,3%), w tym ~9,7k APU (Ryzen AI Max+ 395: 7k) |

| VRAM dyskretnych | Udział |
|---|---|
| ≤ 6 GB | 9,1% |
| 8 GB | 16,3% |
| 10–12 GB | 17,9% |
| 16 GB | 24,0% |
| 20–24 GB | 14,3% |
| 32–48 GB | 8,3% |
| > 48 GB | 10,0% |

Top karty: RTX 3060 12GB 26k, 3090 21k, 5090 19k, 4090 19k. Apple: M4 33%, M1 22%, M5 17%. DGX Spark/GB10: 11k.

**LocalMaxxing** (2 757 użytkowników, 8 928 runów; [LocalMaxxing](https://www.localmaxxing.com/en), [hardware](https://www.localmaxxing.com/en/hardware), moje zliczenie 87 grup):
- dyskretne GPU 77% użytkowników, unified memory 21%, CPU-only 2%;
- Apple tylko ~7% (entuzjaści benchmarków).
- Najwięcej użytkowników: RTX 3090 (52), RTX 5090 (34), GB10 (30), RTX PRO 6000 (28), Arc Pro B70 (19), Ryzen AI Max 395 (17), RX 7900 XTX (15).

**llmfit** przyjmuje społecznościowe benchmarki jako PR-y; pliki leżą w katalogach per sprzęt ([community README](https://github.com/AlexsJones/llmfit/tree/main/llmfit-core/data/community)). Dobry wzorzec dla naszego „uploadu wyników".

**LocalScore** (Mozilla Builders) ma ranking per akcelerator na stałych modelach, np. Llama 3.2 1B Q4_K_M: RTX 4090 382 t/s generowania, 25 538 t/s prefill ([localscore.ai](https://www.localscore.ai/)). Nie publikuje udziałów sprzętu, więc nie da się z niego policzyć rynku. Przydaje się tylko jako referencja prędkości.

#### 2.4.3 Lista celów z priorytetami

| # | Cel | Uzasadnienie (udziały) | Backend |
|---|---|---|---|
| 1 | NVIDIA RTX 30/40/50, 8–16 GB, Windows | Steam: NVIDIA ~76%; VRAM 8+12+16 GB = 67%; top 6 GPU to RTX 50/40/30 | CUDA (fallback Vulkan) |
| 2 | Apple Silicon M1–M5, 16–128 GB | HF: ~25% sprzętu „AI"; tanio dostępne 64–128 GB | Metal (rozważyć MLX) |
| 3 | NVIDIA 24–32 GB (3090/4090/5090) | HF: 3090+4090+5090 ≈ 59k; LocalMaxxing: top 2 | CUDA |
| 4 | AMD RDNA3/RDNA4 (7900 XTX/XT, 9070 XT, 7800 XT, 9060 XT) | Steam AMD ~16,7%; HF ~10%; **nasz know-how** | Vulkan + ROCm/HIP |
| 5 | APU/unified: Strix Halo, DGX Spark, laptopy z iGPU | HF: GB10 11k, AI Max+ 395 7k; Steam: iGPU ≈ 9% | Vulkan/HIP (AMD), CUDA (Spark) |
| 6 | CPU-only | AVX2 95,95%; fallback dla laptopów bez dGPU | ggml-cpu (warianty) |
| 7 | Intel Arc (B580, Pro B60/B70) | Steam Arc 0,24%; LocalMaxxing B70: 19 użytkowników | SYCL/Vulkan |

---

## 3. Co to znaczy dla naszego produktu

### 3.1 Plan detekcji per OS (z fallbackami)

Wspólny schemat jest trzyetapowy.

**(A) Inwentarz w < 300 ms, w procesie aplikacji, bez ładowania silnika.**

**(B) Capability probe w podprocesie** (izolacja crashy, timeout 30 s, a 90 s przy pierwszym uruchomieniu na Windows):
- `ggml_backend_load_all()`;
- dla każdego urządzenia `ggml_backend_dev_get_props` (free/total, typ, PCI id);
- parowanie z (A) po PCI bus id;
- przy konflikcie wygrywa wartość z ggml dla „czy uruchomimy", a z (A) dla nazwy i sterownika.

**(C) Pomiar w 3–10 s:**
- odczyt pamięci ≥ 1 GiB;
- `tg` 32 tokeny wybranym modelem po pobraniu.

Odchylenie > 50% od tabeli oznacza diagnozę.

**Windows (kolejność, każde z fallbackiem):**
1. DXGI/DXCore. Lista adapterów, LUID, vendor/device id, `IsIntegrated`, `DedicatedVideoMemory`/`SharedSystemMemory`, budżet z `QueryVideoMemoryInfo`, NPU przez GENERIC_ML.
2. Biblioteka vendora (dynamicznie, opcjonalnie):
   - NVML: VRAM v2, sterownik, CC, szyna, PCIe;
   - ADLX: TotalVRAM, VRAMType;
   - Level Zero: pamięć.

   Gdy brak, przechodzimy do kroku 3.
3. Vulkan. Sterty + budget, `driverID`, `driverInfo`, `deviceType`, rozszerzenia (coopmat, int dot). Gdy brak `vulkan-1.dll`, zostaje tylko DXGI, a GPU uznajemy za „nieobsługiwane, CPU".
4. CPU: CPUID + XGETBV. Hybrydy P/E przez `GetLogicalProcessorInformationEx`.
5. RAM: `GlobalMemoryStatusEx` + SMBIOS typ 17 przez `GetSystemFirmwareTable`. Fallback: WMI `Win32_PhysicalMemory`, a jeśli i to zawiedzie, pomiar przepustowości.
6. Zasilanie: `GetSystemPowerStatus`; obudowa z SMBIOS typ 3 / `ChassisTypes`.
7. Ochrona przed sysmem fallback: limit = budżet − 1 GiB, monitoring `NON_LOCAL CurrentUsage` w trakcie.
8. Czego nie używać:
   - WMI `AdapterRAM`;
   - parsowania `nvidia-smi`/`rocm-smi` (llmfit tak robi, a te CLI często nie istnieją).

**Linux:**
1. sysfs PCI + driver.
2. AMD: `mem_info_vram_total`/`mem_info_gtt_total`, KFD topology (gfx). Sprawdzenie dostępu do `/dev/kfd` i `renderD*`; gdy brak, Vulkan i komunikat „dodaj do grupy render" (bez sudo w aplikacji).
3. NVIDIA: NVML. Fallback: Vulkan.
4. Intel: Level Zero. Fallback: Vulkan.
5. RAM: `/proc/meminfo`; prędkość tylko z pomiaru (SMBIOS jest root-only).
6. Wykrycie usypiania GPU (BACO): pomiar < 10% oczekiwanego oznacza ostrzeżenie (nasz przypadek 4,4 vs 92 t/s).
7. WSL2: obecność `/dev/dxg` `[INFERENCE]`, ścieżka CUDA przez WSL.

**macOS:**
1. sysctl: chip, RAM, P/E.
2. Metal: `recommendedMaxWorkingSetSize` jako budżet; **nie** podnosimy `iogpu.wired_limit_mb`.
3. Wariant chipa (liczba rdzeni GPU) mapujemy na tabelę przepustowości, potem robimy pomiar.
4. Optymalizacja nocna wymaga AC (IOPowerSources).

**Prywatność:**
- Do backendu wysyłamy tylko kategorie: model GPU, VRAM, sterownik, chip, RAM.
- **Nigdy:** numery seryjne z SMBIOS, UUID z NVML/ADLX `UniqueId`, nazwa hosta.

### 3.2 Estymator: specyfikacja

1. **Wejście:** nagłówek GGUF (range-fetch; typy warstw, `head_count_kv[]`, ssm/conv dims, rozmiary tensorów i ich placement), ctx, typ KV, n_ub, spekulacja.
2. **Pamięć:** wzór z §2.2.4 z rezerwą: β = 3 KiB/tok ctx przy ub=512, narzut runtime 0,25–0,6 GiB, margines 1 GiB jak w `--fit`.
3. **Weryfikacja przed startem:** `llama_params_fit` (w podprocesie) daje wartość dokładną.
4. **Prędkość:**
   - decode: `B_tok/(η_bw·BW) + N_kern·t_gap`;
   - prefill: `2·N_active·tokens/(η_pf·peak)`.

   Startowe η z naszej kalibracji: η_bw 0,78–0,9 dla dobrych kerneli; t_gap 2,5–3,2 µs (grafy), 0,5–0,9 µs (PM4); η_pf 0,45 dla gęstych i 0,23 dla małych MoE na RDNA3. Wynik pokazujemy jako **przedział** z etykietą pewności (wzorem: llmfit `estimate_confidence`), potem zastępujemy go pomiarem.
5. **MoE offload:** estymator musi znać PCIe gen/width oraz przepustowość RAM. Prefill z ekspertami w RAM jest ograniczony przez PCIe, decode przez RAM.

**Kalibracja z 3 punktów NOTES:**

| Punkt | Wynik wzoru |
|---|---|
| Pamięć Qwen | +0,1% vs llama.cpp |
| Pamięć LFM | 0,0% (q8_0), −1,1% (q4_0) vs odczyt |
| Decode Qwen | sam roofline × 0,55 (llmfit) daje −14…−22%; model dwuczłonowy z η_bw = 0,78 i 2 000 kerneli × 3,2 µs odtwarza 34,8 t/s |
| Decode LFM | roofline × 0,55 trafia w nasz fork, ale +75% vs upstream; model dwuczłonowy (3,8 ms pracy + 1,3 ms przerw) odtwarza 198 t/s |

### 3.3 Katalog: zasady

- **Domyślnie** model z licencją Apache/MIT, z niegatowanego repozytorium, w największym kwancie mieszczącym się w ~85% budżetu (próg „Good" z llmfit). W polu wyboru: czat / kod / rozumowanie / wizja / polski.
- **Polski:** dla tierów ≤ 12 GB proponujemy Bielik obok Qwena. Przed wydaniem trzeba **samemu zmierzyć PLCC i nasz `quick_quality.py` PL** na Qwen3.8/Gemma 4/Bielik, bo publiczne dane są nieaktualne.
- **Hybrydy (Qwen3.8, LFM, Nemotron-H) są naszym atutem.** Mały KV pozwala na długi kontekst na 16–24 GB. Nasze łatki (MTP, kvq FA, PM4) są pod nie strojone. W tierach 16–24 GB promujemy je jako modele domyślne.
- **LFM2.5:** świetna szybkość, ale licencja z progiem 10 mln USD. Dajemy go jako opcję „szybki", nie jako domyślny, do czasu opinii prawnej.

### 3.4 Ryzyka

- Fałszywe wykrycie (przykłady z Strata i Ollama) prowadzi do złej rekomendacji i pierwszego wrażenia „nie działa". Mitygacja: wielokrotne źródła i pomiar.
- Windows NVIDIA sysmem fallback to ciche 5–30× wolniej. Mitygacja: budżet z marginesem i alarm w trakcie działania.
- Estymaty prędkości dla MoE mogą być błędne nawet ±75%. Mitygacja: pokazujemy przedziały i szybko podmieniamy je pomiarem.
- Licencje (LFM, Qwen Community) i gated repo mogą zablokować plug-and-play.
- Szybkość wydawania modeli: katalog trzeba aktualizować co 4–8 tygodni. W 2026 Qwen wydał 3.5 → 3.6 → 3.8 w ~6 miesięcy (HF API). Katalog powinien być zdalnym manifestem, a nie wkompilowaną listą (llmfit wkompilowuje, więc użytkownik musi aktualizować binarkę).

### 3.5 Pytania otwarte

1. Czy `llama_params_fit` zadziała na GGUF pobranym tylko w części (sam nagłówek)? To dałoby dokładną estymatę bez pobierania wag. `[INFERENCE: wymaga testu]`
2. AMD na Windows i Linux: redystrybuować runtime HIP/ROCm (rozmiar, licencja) czy domyślnie tylko Vulkan? Nasze dane: ROCm szybszy w prefill (1,2–1,4×), Vulkan szybszy w decode przy krótkim kontekście.
3. Jak programowo odczytać ustawienie NVIDIA „Sysmem Fallback Policy" (NVAPI DRS?) `[INFERENCE]`.
4. Czy zbierać (opt-in) wyniki pomiarów do wspólnej bazy, jak llmfit i LocalMaxxing, żeby kalibrować η per GPU i model? Kwestie RODO i anonimizacji.
5. Jakość polska Qwen3.8 / Gemma 4 / Mistral Small 4 vs Bielik v3: brak aktualnych danych PLCC.
6. Interpretacja progu przychodu w LFM Open License dla dystrybutora aplikacji vs użytkownika końcowego (do prawnika).

---

## 4. Źródła

### Lokalne
- `~/KERNEL/qwen-opt/SPEC-QWEN27B.md` (VRAM 22,3/23,2 GB, tg128 38,6/34,8, pp4096 1044)
- `~/KERNEL/qwen-opt/NOTES.md` (LFM: 17,8 GB, tg 169→295, B_tok 1,8 GB, MTP 108,8 t/s, KLD KV)
- `~/qwen-opt/k3/logs_verbose.log` (memory breakdown Qwen)
- `~/wt/lfm2-prof/kvvram.q8_0.log` (memory breakdown LFM)
- `~/llama-master`:
  - `common/common.h:494-499`, `common/arg.cpp:2896-2952` (fit);
  - `ggml/include/ggml-backend.h:164-181`;
  - `ggml/src/ggml-vulkan/ggml-vulkan.cpp:15226-15256, 16173`;
  - `ggml/src/ggml-cuda/ggml-cuda.cu:7354`;
  - `ggml/src/CMakeLists.txt:494-544`;
  - `src/llama-model.cpp:1638-1640`;
  - `src/llama-kv-cache.cpp:163,231`;
  - `src/llama-kv-cache-iswa.cpp:73`;
  - `src/llama-context.cpp:254,695`.
- GGUF zmierzone `gguf-py`: `~/models/Qwen3.8-27B-UD-Q4_K_XL.gguf`, `~/models/lfm/LFM2.5-24B-A2B-Q5_K_M.gguf`.

### Windows / API
- https://learn.microsoft.com/en-us/windows/win32/api/dxgi1_4/nf-dxgi1_4-idxgiadapter3-queryvideomemoryinfo
- https://learn.microsoft.com/en-us/windows/win32/api/dxgi1_4/ns-dxgi1_4-dxgi_query_video_memory_info
- https://github.com/MicrosoftDocs/sdk-api/blob/docs/sdk-api-src/content/dxgi/ns-dxgi-dxgi_adapter_desc1.md
- https://learn.microsoft.com/en-us/windows/win32/dxcore/dxcore-adapter-attribute-guids
- https://issues.chromium.org/issues/341947682 (>12 mies.)
- https://github.com/mgradwohl/tasksmack/issues/1263 , https://github.com/mgradwohl/tasksmack/issues/1515
- https://learn.microsoft.com/en-us/windows/win32/cimwin32prov/win32-videocontroller
- https://stackoverflow.com/questions/68274009/wmi-win32-videocontroller-ram-4gb-limit (>12 mies.)
- https://learn.microsoft.com/en-us/answers/questions/2202526/loop-through-and-read-adapters
- https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-isprocessorfeaturepresent
- https://github.com/oven-sh/bun/pull/19003
- https://learn.microsoft.com/en-us/windows/win32/api/sysinfoapi/nf-sysinfoapi-getsystemfirmwaretable
- https://learn.microsoft.com/en-us/windows/win32/cimwin32prov/win32-physicalmemory
- https://powershell.one/wmi/root/cimv2/win32_systemenclosure
- https://learn.microsoft.com/en-us/previous-versions/system-center/configuration-manager-2003/cc180825(v=technet.10) (>12 mies.)
- https://nvidia.custhelp.com/app/answers/detail/a_id/5490/~/system-memory-fallback-for-stable-diffusion (>12 mies.)
- https://runaihome.com/blog/shared-gpu-memory-slow-local-ai-sysmem-fallback-fix-2026/

### Vendor APIs
- https://docs.nvidia.com/deploy/nvml-api/latest/api/group__nvmlDeviceQueries.html
- https://docs.nvidia.com/deploy/nvml-api/615/api/structnvmlMemory__v2__t.html
- https://github.com/Saancreed/wine-nvml (>12 mies.)
- https://developer.nvidia.com/blog/whats-new-and-important-in-cuda-toolkit-13-0/ (>12 mies.)
- https://gpuopen.com/manuals/adlx/adlx-sdk-references/adlx-interfaces/gpu/iadlxgpu/
- https://github.com/GPUOpen-LibrariesAndSDKs/ADLX
- https://oneapi-src.github.io/level-zero-spec/level-zero/latest/sysman/PROG.html
- https://github.com/ggml-org/llama.cpp/issues/28239
- https://github.com/intel/compute-runtime/issues/993
- https://docs.vulkan.org/refpages/latest/refpages/source/VK_EXT_memory_budget.html
- https://docs.kernel.org/gpu/amdgpu/driver-misc.html
- https://rocmdocs.amd.com/en/develop/how-to/system-optimization/strixhalo.html
- https://www.amd.com/en/blogs/2025/faqs-amd-variable-graphics-memory-vram-ai-model-sizes-quantization-mcp-more.html (>12 mies.)
- https://github.com/ggml-org/llama.cpp/issues/16832 (>12 mies.)
- https://blogs.oracle.com/linux/intel-amx-with-uek (>12 mies.)
- https://developer.apple.com/documentation/metal/mtldevice/recommendedmaxworkingsetsize
- https://developer.apple.com/videos/play/tech-talks/10580/ (>12 mies.)
- https://github.com/unslothai/unsloth/pull/13319
- https://github.com/ivanopcode/devnote-override-macos-metal-vram-cap
- https://github.com/ggml-org/llama.cpp/issues/29465 , https://github.com/ggml-org/llama.cpp/issues/24510
- https://www.open-mpi.org/projects/hwloc/doc/v2.8.0/a00365.php (>12 mies.)

### Specyfikacje sprzętu
- https://www.amd.com/en/support/downloads/drivers.html/graphics/radeon-rx/radeon-rx-7000-series/amd-radeon-rx-7900-xtx.html
- https://www.runpod.io/articles/guides/nvidia-rtx-5090
- https://www.tomshardware.com/pc-components/gpus/rtx-5070-vs-rtx-5060-ti-16gb (>12 mies.)
- https://www.intel.com/content/www/us/en/products/sku/241598/intel-arc-b580-graphics/specifications.html (>12 mies.)
- https://www.techspot.com/specs/gpu/281792-nvidia-geforce-rtx-4060.html (>12 mies.)
- https://www.apple.com/newsroom/2024/10/apple-introduces-m4-pro-and-m4-max/ (>12 mies.)
- https://www.apple.com/newsroom/2026/03/apple-introduces-macbook-pro-with-all-new-m5-pro-and-m5-max/
- https://www.parallels.com/blogs/apple-m5-chip/
- https://www.pny.com/dgx-spark
- https://www.cpu-monkey.com/en/cpu-amd_ryzen_ai_max_plus_395

### Estymatory, silniki, bugi
- https://github.com/ggml-org/llama.cpp/tree/master/tools/fit-params
- https://github.com/ggml-org/llama.cpp/issues/21801 , https://github.com/ggml-org/llama.cpp/issues/19437
- https://github.com/ollama/ollama/blob/main/discover/runner.go
- https://github.com/ollama/ollama/issues/14280 , https://github.com/ollama/ollama/issues/15352 , https://github.com/ollama/ollama/issues/16591
- https://github.com/AlexsJones/llmfit , https://raw.githubusercontent.com/AlexsJones/llmfit/main/docs/how-it-works.md , https://github.com/AlexsJones/llmfit/tree/main/llmfit-core/data/community
- https://github.com/Niko1221/Strata/issues/159
- https://github.com/gpustack/gguf-parser-go
- https://arxiv.org/abs/2609.14864
- https://huggingface.co/docs/hub/hardware
- https://lmstudio.ai/blog/lmstudio-v0.3.27 (>12 mies.) , https://github.com/lmstudio-ai/lmstudio-bug-tracker/issues/1753
- https://apxml.com/tools/vram-calculator

### Modele, licencje, jakość
- https://huggingface.co/api/models?author=Qwen (oraz zapytania API dla google, LiquidAI, mistralai, openai, nvidia, zai-org, deepseek-ai, speakleash, CYFRAGOVPL, ibm-granite, meta-llama, microsoft; 2026-10-15)
- https://huggingface.co/Qwen/Qwen3.8-Flash-Next
- https://cellcog.ai/blog/qwen3-8-flash-next/
- https://blog.google/innovation-and-ai/technology/developers-tools/gemma-4/ , https://ai.google.dev/gemma/docs/core/model_card_4 , https://ai.google.dev/gemma/docs/releases
- https://huggingface.co/mistralai/Mistral-Small-4-119B-2603
- https://huggingface.co/LiquidAI/LFM2.5-24B-A2B/blob/main/LICENSE , https://huggingface.co/LiquidAI/LFM2.5-8B-A1B
- https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Bolt-74B-A9B-24GB-GGUF
- https://huggingface.co/openbmb/MiniCPM5-2B
- https://huggingface.co/meta-llama , https://huggingface.co/CYFRAGOVPL
- https://arxiv.org/abs/2601.11579 (Bielik 11B v3) , https://arxiv.org/html/2604.10799v1 , https://arxiv.org/html/2501.02266v1 (>12 mies.)
- https://unsloth.ai/docs/basics/dynamic-3.0-ggufs , https://unsloth.ai/docs/models/qwen3.5/gguf-benchmarks , https://news.ycombinator.com/item?id=47192505
- https://arxiv.org/abs/2601.14277 , https://arxiv.org/html/2606.19558 , https://arxiv.org/abs/2407.09141 (>12 mies.)
- https://artificialanalysis.ai/models/open-source/small , https://artificialanalysis.ai/models/open-source/tiny
- https://llmrun.dev/benchmark/lmarena-text
- https://www.thundercompute.com/blog/best-open-source-llms

### Udziały rynkowe
- https://store.steampowered.com/hwsurvey/Steam-Hardware-Software-Survey-Welcome-to-Steam
- https://store.steampowered.com/hwsurvey/processormfg/
- https://store.steampowered.com/hwsurvey/videocard/
- https://www.virtwave.com/industry-news/steam-statistics (wtórne)
- https://huggingface.co/hardware
- https://www.localmaxxing.com/en , https://www.localmaxxing.com/en/hardware
- https://www.localscore.ai/
