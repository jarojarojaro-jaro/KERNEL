# DeepSeek-V4.1-Flash w Stracie (GSQ-RCO) — stan na 2026-10-24

Źródła: klon Niko1221/Strata z 2026-10-24 (`docs/DEEPSEEK41.md`, `docs/release-notes-0.2.4*.md`, README), karta HF ISTA-DASLab, llama.cpp discussion #28766.

## Co wyszło
- **Strata 0.2.4** (2026-10-23) + hotfixy 0.2.4.1/0.2.4.2 (2026-10-24): DeepSeek V4.1-Flash w Terminalu (`strata launch`), osobny silnik `strata-dsv41` (port z Project Maya `maya-ds4`, MIT). Desktopowa apka jeszcze bez DeepSeeka; Mac i Strix Halo „later”.
- Model: DeepSeek-V4.1-Flash-1017, MoE 763B (40 warstw, 384 ekspertów/warstwę, 6 aktywnych) + tablica n-gram **Engram** 111 GB (IQ4_NL) czytana rzadko z RAM/SSD.
- Kwanty **GSQ-RCO od ISTA-DASLab** (HF: `ISTA-DASLab/DeepSeek-V4.1-Flash-1017-GSQ-RCO-GGUF`, MIT): każdy tensor ma własny typ (GSQ = kwantyzacja per tensor, RCO = dobór typów pod budżet rozmiaru).

| Zestaw | bpw | backbone | pobranie (z Engram 111 GB + DSpark 8 GB) | jakość |
|---|---|---|---|---|
| IQ1_M | 1.75 | 121 GB | 239 GB | ppl +21%, KL 0.217; 98.7% zadań bazowego (AIME25/GPQA/LCB) |
| **IQ2_XXS** | 2.00 | 138 GB | 257 GB | ppl +15.5%, KL 0.170; 100% zadań bazowego |
| IQ2_XS | 2.25 | 155 GB | 274 GB | ppl +7.3%, KL 0.107 (najbliższy oryginału) |

## Zmierzone prędkości (zestaw 2.00, dane autorów Straty)
| PC | odpowiedź | prompt |
|---|---|---|
| RTX 5070 12 GB + 64 GB RAM + NVMe 3.6 GB/s (Ryzen 5 7600) | ~4.7–5 tok/s | 121 (4K) – 231 tok/s (8K) |
| RTX 3060 12 GB + 46 GB RAM (Linux) | 8–10 tok/s (kod 9.9, agent 7.8) | 149 tok/s (8K) |
| 1× Radeon AI PRO R9700 32 GB, IQ2_XS | ~11–15 tok/s | — |
| 4× R9700 + 251 GB RAM | 31 tok/s (55–69 z DSpark); README: 48 (2.00) / 80 (2.25) | 505 (8K) – 818 (32K) |

Poza Stratą: port do llama.cpp na RTX 5090 + 125.7 GiB RAM ze streamingiem ekspertów z NVMe: 5.1 tok/s nowa treść / 21 tok/s z cache (discussion #28766). Mainline llama.cpp **nie wspiera V4.1** (stan 2026-10-23 wg karty HF).

## Jak to działa i co limituje
- Eksperci: ile się zmieści w VRAM, reszta liczona na CPU „w miejscu” z RAM; co nie mieści się w RAM — z SSD (wolno). Store w RAM sam się dobiera; profile „gorących” ekspertów w pakiecie.
- Na 12 GB kartach z 46–64 GB RAM większość czasu tokena to czekanie na SSD i CPU. **Więcej RAM = większy store = szybciej.** Kernele CPU: AVX-512 (Zen 4/5) vs AVX2; na Zen 4 AVX-512 dało +25% decode.
- DSpark (drafter 8 GB, Unsloth): auto; na 12 GB kartach domyślnie off (+2–13% gdy on na 3060), na CPU-bound PC bez zysku.
- Kontekst domyślnie 8192 (`--context` więcej), thinking domyślnie on (budżet 32768), API OpenAI/Anthropic, tool calls (DSML→tool_calls). Brak `--parallel` i obrazów w tej wersji.

## Uruchomienie (Linux, NVIDIA RTX 30/40/50)
```sh
curl -fsSL https://github.com/Niko1221/Strata/releases/latest/download/install.sh -o install.sh && sh install.sh
strata launch --model ist-das-2.00bpw --plan     # pokaże, co gdzie trafi na tym PC, nic nie pobiera
strata launch --model ist-das-2.00bpw            # pobiera 257 GB (resume, SHA-256), silnik strata-dsv41-0.1.49-linux-x86_64-cuda-cuda13.tar.gz, start
strata launch --tune quick                        # 5–10 min, próbuje DSpark/wątki CPU
```
Wymagania: karta ≥12 GB, 46–64 GB+ RAM, NVMe z 257 GB wolnego. Pliki muszą leżeć na NVMe (Engram czytany per token).

## RTX 5060 Ti 16 GB
Pakiet CUDA 13 obejmuje RTX 30/40/50; testowane przez autorów: 3060, 5070, A4000. 5060 Ti nie jest wymieniona przy DeepSeeku (jest w benchmarkach społeczności dla Qwena). sm_120 jak 5070 → powinno działać; do potwierdzenia.
