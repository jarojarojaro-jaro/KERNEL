---
typ: metoda
tags: [metody, pulapki, rocm, llamacpp, bezpieczenstwo, skill-io]
aktualizacja: 2026-11-17
zrodlo: ~/kernel/zrodla/inference-optimisation-skill @ fda968e — references/gotchas.md:1-58
status: aktualne
---
# Pułapki silników i sprzętu wg skill-io (gotchas.md) a nasze lekcje

**Z 32 pułapek 9 przerobiliśmy sami, każdą z własną lekcją. Na nasz stos (llama.cpp, ROCm, AMD dyskretna) nowe są dwie: wolne KV q8_0 przy modelach z małą liczbą warstw KV (jest w naszym wyborze q4_0 + `kvq`) i wyciek grafów HIP w ExLlama na ROCm. Reszta dotyczy vLLM/SGLang/Intel/Apple albo pamięci zunifikowanej.**

| pułapka (gotchas.md) | u nas |
|---|---|
| drugi silnik / zabłąkany bench na tym samym GPU połowi wynik albo psuje oba (`:7`) | tak: kolejka `run-jobs.sh` + `/tmp/gpu.lock`, orphan-guard |
| „device lost” → najpierw dziennik jądra (B70: AER, link PCIe, 8× w 3 dni) (`:8`) | tak: `run-jobs.sh` sprawdza dziennik po każdym jobie pod kątem faultów amdgpu |
| wymuszony stop w długim prefillu → page fault GPU (`:9`) | tak: jeden SIGTERM, 60 s, potem SIGKILL; [[lekcja-pm4-zamienia-fault-w-reset]] |
| duże obrazy wywalają enkoder wizji (`:10`) | n/d (bez wizji) |
| timeouty bramek/proxy 600 s ucinają testy długiego kontekstu; testować prosto w silnik, nie ponawiać po timeoucie (`:11`) | tak: testy bezpośrednio na porcie testowym |
| `pkill -f` zabija własną powłokę, `pgrep -f` czeka na siebie (`:12`) | tak: [[lekcja-pkill-wlasna-powloka]] |
| restart agenta zabija procesy dzieci → `setsid nohup`, wznawialność (`:13`) | tak, i to boleśnie: 2026-11-14 podagenci zginęli z końcem tury, a instancja Vast stała pusta |
| vLLM: cache prefiksów wyłączony dla hybryd, MTP wiele tokenów w kawałku, mmap wolny (`:17-21`) | n/d; odpowiednik u nas: `--cache-reuse` niebezstratny dla qwen35 (stan GDN) |
| SGLang: liczniki akceptacji tylko po zakończeniu, `--max-mamba-cache-size`, błędy backendu XPU (`:25-36`) | n/d |
| llama.cpp: KV q8_0 dużo wolniejsze przy małej liczbie warstw KV (`:40`) | wiedza: Qwen ma KV w 16 z 64 warstw; produkcja q4_0 z `kvq` |
| llama.cpp: MTP/draft poniżej bazowej prędkości na trudnych promptach (`:41`) | u nas nie: spekulacja zawsze ponad plain (43 → 120 t/s) |
| rozmiary work-group w kernelach backendu (SYCL WG=1 ×7,8) (`:42`) | ogólnie: sweepy wariantów kerneli ([[sweep-wariantow-kernela]]) |
| ExLlama na ROCm: grafy HIP wyciekały aż do crasha (`:46`) | nasza taśma PM4 to inny mechanizm; soak S6 1205 żądań bez wycieku |
| zajęte CPU kosztuje dekod GPU (107 → 75 t/s) (`:47`) | tak: `taskset`, cpuheavy, nice; serwer testowy na `taskset -c 2-5` |
| Intel Xe: topk segfault, płoty, OUT_OF_RESOURCES (`:51-54`) | n/d |
| pamięć zunifikowana niewidoczna dla cgroup; bateria −8…10% (`:55`) | n/d |
| Apple: głęboka spekulacja przegrywa na słabym paśmie (`:56`) | n/d (wiedza dla Enigmy na Mac) |
| Ampere bez FP8 → INT4 wygrywa (`:57`) | wiedza dla Enigmy NVIDIA (3090) |
| stan GDN w fp16 dawał „!!!” (`:58`) | u nas stan f32, bf16 odrzucone (stratne) |

**Lekcja ogólna:** ich lista pułapek pokrywa się z naszymi lekcjami z października. To potwierdza, że sztywne zasady karty (kolejka, jeden SIGTERM, dziennik jądra) są uniwersalne, a nie nasza nadgorliwość.

## Pułapki per firma (AMD i NVIDIA, 2026-11-17)

| firma, architektura | pułapka | źródło / nasza lekcja |
|---|---|---|
| AMD RDNA3 (gfx1100) | PM4 bez `GGML_HIP_PM4` ustawionego jawnie może zresetować kartę | [[lekcja-pm4-zamienia-fault-w-reset]] |
| AMD wszystkie | build musi zawierać właściwy target (`gfx1030`, `gfx1100`, `gfx1201`, `gfx90a`, `gfx942`, `gfx950`); kernel strojony pod wave32 RDNA nie działa optymalnie na wave64 CDNA | AMD ROCm docs; nasze warianty FA tylko gfx1100 |
| AMD ROCm (ExLlama) | grafy HIP wyciekały aż do crasha (`gotchas.md:46`) | nasze grafy HIP + PM4: soak S6 bez wycieku |
| AMD Radeon | „efektywne pasmo” ze strony producenta (XTX 3500 GB/s) to Infinity Cache, nie sufit dekodu | [[skill-io-sufity]] |
| NVIDIA GeForce | FP16 z akumulacją FP32 o połowę wolniej niż FP16/FP16 (3090 71 vs 142, 4090 165 vs 330) | whitepaper RTX Blackwell |
| NVIDIA Ampere | brak FP8; INT4 wygrywa przy ograniczeniu pasmem (`gotchas.md:57`) | dotyczy wyboru kwantu w Enigmie |
| NVIDIA Blackwell sm_120 | potrzebny CUDA ≥ 12.8 i build z `sm_120` | [[lekcja-build-cuda-0057-0070]] |
| NVIDIA na Vast | limit mocy hosta zaniża wynik (4090 250 W, 3090 340 W, 5060 Ti 160 W; 2026-11-17: 3090 250 z 420 W i pamięć 5001 z 9751 MHz → 23% sufitu, 3060 135 z 170 W) | [[lekcja-limit-mocy-hosta]], [[lekcja-limit-mocy-285w]], [[lekcja-vast-tylko-pelna-moc]]; bramka `qwen-opt/cloud/hostguard.sh`: limit mocy i zegar pamięci ≥ 85% fabrycznych, < 80 °C bez obciążenia (próg właściciela 2026-11-17) |
| NVIDIA na Vast | CPU hosta bez AVX2 (3090 → wariant `kvqleana`); limit CPU kontenera | [[lekcja-limit-cpu-kontenera]] |
| NVIDIA CUDA | kolejka uruchomień ma ~1024 kernele: na 4060 Ti po ~1040 wstawionych matmulach 512² host czeka na GPU (1000 → 1,74 ms, 1200 → 36,7 ms wstawiania); długie kroki bez grafu tracą „bieg do przodu” CPU | github.com/JINO-ROHIT/ml-systems-notes `cuda_stream_and_queue` (pomiar autora); dotyczy K-116 |
| SGLang 0.5.9 | radix cache na hybrydzie Mamba/GDN po cichu wyłącza overlap schedule: Qwen3.5-0.8B na A100 szybszy bez radix w prawie każdym scenariuszu (+9% z radix tylko przy identycznych promptach 2000 tok.) | j.w. `sglang/kv_cache` (pomiar autora); ważne dla K-119 (SenseNova w SGLang) |
| obie | zajęte CPU kosztuje dekod (107 → 75 t/s, `gotchas.md:47`); na Vast host współdzielony | przeplot A/B na tym samym hoście |

## Pułapki: Apple, Intel, Tenstorrent (2026-11-17)

| firma | pułapka | źródło |
|---|---|---|
| Apple M1–M4 | głęboka spekulacja przegrywa (M4 6,35 → 3,25 t/s przy 3 draftach): weryfikacja N=5 ograniczona obliczeniami | `gotchas.md:56`, `levers.md:35`; nasze liczenie w [[skill-io-sufity]] |
| Apple | limit pamięci GPU `iogpu.wired_limit_mb` (domyślnie ~75% RAM); pamięć niewidoczna w cgroup i MemAvailable | `gotchas.md:56`, `methodology.md:46` |
| Apple | Neural Accelerators (M5) wymagają nowej ścieżki Metal 4 (tensor API) — stare kernele `simdgroup_matrix` ich nie używają [INFERENCE] | Apple newsroom M5 |
| Intel XPU (PyTorch) | `torch.topk` segfault powyżej ~2–8K kolumn; split-K na Xe3 wymaga niekeszowanych zapisów i płotu; `UR_RESULT_ERROR_OUT_OF_RESOURCES` = za duże lub kawałkowe grafy | `gotchas.md:51-54` |
| Intel Arc | nadmierna alokacja pamięci urządzenia → livelock maszyny; trzymać ≥ 1,5 GB wolne | `levers.md:58` |
| Intel B70 | crashe „device lost” to były zrywy łącza PCIe (AER) — najpierw dziennik jądra | `gotchas.md:8` |
| Intel iGPU | bateria i profil zasilania −8…10% | `gotchas.md:55` |
| Intel SYCL (llama.cpp) | work-group 1 w kernelu kopiowania × 7,8 wolniej | `gotchas.md:42` |
| Tenstorrent | brak backendu ggml/llama.cpp w upstream (grep `ggml/src` 2026-11-17); GGUF K-quanty niewspierane, wagi trzeba przekonwertować na BFP4/BFP8 (inne liczby niż nasz plik) | [[skill-io-dzwignie]] |
| Tenstorrent n300 | 2 chipy po 12 GB: model 16,6 GB wymaga podziału tensorów (TP=2) po łączu Ethernet między chipami | specyfikacja Tenstorrent |

## Powiązane
- [[skill-io-przeglad]]
- [[lekcja-pkill-wlasna-powloka]]
- [[lekcja-pm4-zamienia-fault-w-reset]]
- [[lekcja-limit-mocy-hosta]]
- [[gpu-guard]]
