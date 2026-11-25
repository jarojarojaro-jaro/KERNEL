---
typ: ekosystem
tags: [ekosystem, moe, offload, rust, hip, vulkan]
aktualizacja: 2026-11-25
zrodlo: github.com/RustingStudio/RustingStrata v1.3.3 (HEAD `6b88a33e`, 2026-11-25) README, docs/BENCHMARKS.md:14-25,49-72,279-304, docs/HIP.md:1-60; panel JARO 2026-11-25 (x.com/swarogan/status/2125574368772161620)
status: aktualne
---
# RustingStrata (RustingStudio): silnik w Ruście dla MoE większych niż VRAM

**Silnik GGUF w czystym Ruście (bez ggml, bez kroku C++), osobny projekt Vasyla Trefilova, a nie Strata Niko1221. Kernele CUDA kompilowane w locie przez NVRTC, te same na Vulkanie, a od niedawna eksperymentalnie na HIP przez hiprtc. Przewaga nad llama.cpp jest wyłącznie przy modelach MoE, które nie mieszczą się w VRAM: eksperci liczą się równolegle na CPU i GPU, a rozmieszczenie ekspertów dopasowuje się do zaobserwowanego routingu. Na modelach mieszczących się w karcie nie ma przewagi, więc dla naszej produkcji na XTX (wszystko w VRAM) nie wnosi szybkości. Wnosi wzór dla Enigmy na karty 8 do 16 GB.**

## Liczby autora (RTX 3060 12 GB, Ryzen 5 7600X, 32 GB RAM, greedy)
| model, plik | RustingStrata | llama.cpp (strojony `-ncmoe`, `--moe-cache-mib`) |
|---|---|---|
| Qwen3.6-35B-A3B UD-Q5_K_M 25,2 GiB, dekod po 4K | 80,5 (75,1–82,0) | 64,4 (58,8–66,0) |
| Qwen3.6-35B-A3B UD-Q2_K_XL 11,7 GiB, dekod po 4K | 113,4 | 66,5 |
| UD-Q2_K_XL z MTP `--mtp 1`, krótki / po 4K | do 160 / 152 | MTP u nich wolniejsze |
| Qwen3.6 UD-Q3_K_M z MTP | 108,0 (akceptacja 90%) | 101,1; PolyStrata 113,3 |
| Inkling 2 Mini IQ4_NL 17,6 GB, dekod 0,5k / 32k | 35,8 / 23,6 | 31,1 / 22,3 |

- Tweet o „160 t/s” to UD-Q2_K_XL (2-bitowy kwant, ok. 11,7 GiB, prawie cały w VRAM) z MTP przy krótkim prompcie. Przy Q5_K_M zysk to +25%, nie +70%.
- Zgodność greedy z llama.cpp 98–99% (20 promptów × 32 tokeny). Rozmieszczenie ekspertów zmienia się między biegami, a kernele CPU i GPU zaokrąglają inaczej, więc wynik T=0 nie jest powtarzalny bit w bit. Z `--fixed-experts --mtp 0` HIP daje bitowo to samo co Vulkan (docs/HIP.md).
- HIP uruchomiony na RX 9070 XT (gfx1201, ROCm 7.2.3). Qwen3.6-35B-A3B UD-Q4_K_XL: pp4096 2993 vs Vulkan 2325, dekod 209–219 tok/s z MTP 3. gfx1100 nie był testowany.

## Co z tego bierzemy
- **Enigma (karty 8–16 GB):** równoległe liczenie ekspertów na CPU i GPU plus rozmieszczenie ekspertów według zaobserwowanego routingu to dokładnie brakujący element z [[magnitude]] („Enigma bez offloadu MoE”). Test na XTX z modelem, który się nie mieści: K-172.
- **Metoda:** każdą liczbę podają jako zakres i dokładają zastrzeżenia (cache stron, rozgrzewka). Ta sama kultura pomiaru co nasza.

## Powiązane
- [[strata]]
- [[magnitude]]
- [[qwen3-6-35b-a3b]]
- [[inkling-2-mini]]
