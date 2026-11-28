---
typ: meta
tags: [topki, rejestr, karty, modele]
aktualizacja: 2026-11-28
zrodlo: wiki/REKORDY.md; wiki/produkt/final-recipes-nvidia.md; ~/qwen-opt/topki/xtx/*.sh (jaroserverai); qwen-opt/cloud/nvq3/results; testy K-202..K-210
status: aktualne
---
# TOPKI: najszybszy pełny stos każdej pary karta × model

**Jeden wiersz = jedna topka: najszybszy działający pełny stos (spekulacja, kwant, KV, fuzje, build, env, pełny kontekst) z komendą startu do skopiowania; główna liczba to zawsze czat ze spekulacją (decyzja JARO 2026-11-28).**

Zasady: pytanie „topka X na Y” = odpowiedź z tej tabeli (komenda, liczba, data), bez testów. Nowy najlepszy pełny stos trafia tu w tej samej turze co pomiar. Brak pełnego stosu = wpis w [[KOLEJKA-TESTOW]]. Playbooki nowego sprzętu: [[procedura-znany-model-nowa-karta]], [[procedura-nowy-model-znana-karta]], [[rodzaje-modeli]]; platformy: [[nvidia-ampere-sm86]], [[nvidia-ada-sm89]], [[nvidia-hopper-sm90]], [[nvidia-blackwell-sm120]], [[nvidia-blackwell-sm100]], [[amd-rdna3-gfx1100]], [[amd-rdna4-gfx1201]], [[amd-cdna3-gfx942]], [[amd-strix-halo-gfx1151]], [[apple-silicon-mlx-metal]], [[intel-arc-xe2]].

## AMD

Główna liczba = czat t/s z pełnym stosem (spekulacja + kwant + KV + fuzje + build + env + pełny kontekst). Liczba bez spekulacji nigdy nie jest główna. Skrypty: **wall.py** = 4 prompty (code, tech, pl, json) × 300 tok., mediana, T=0 i T=0,7; **spec_sweep** = 6 promptów PL/EN × 3 seedy, T=1, 400 tok.; **copy_bench** = zestawy `mvs`/`copy`/`short`; **K-147 bench** (Maya) = `copy` 582 tok., `edit` 583 tok., `python_edit` 886 tok., wyniki dokładne. Liczb z różnych skryptów nie porównujemy wprost. Ścieżki `~/…` są na jaroserverai.

### RX 7900 XTX

gfx1100, 24 GB, 960 GB/s (zmierzone 926 GB/s, `qwen-opt/skill-io/karty.json:54`). Czat :8080 wstaje zawsze z modelem z `~/qwen-opt/topki/xtx/ACTIVE` (2026-11-28: `qwen-uncensored`, `ps` pokazuje tylko `~/llama-topka-k047/bin/llama-server` na 127.0.0.1:8080). Zmiana modelu: `echo <model> > ~/qwen-opt/topki/xtx/ACTIVE && ~/qwen-opt/tools/topka-restart.sh` ([[topki]]).

| model | czat t/s (pełny stos) | kopia/kod t/s | prefill t/s | kontekst | komenda startu | commit/build | data | źródło | status | vs poprzednia / vs llama.cpp+spec |
|---|---|---|---|---|---|---|---|---|---|---|
| **Qwen3.8-27B Uncensored Q4_K_M** (ACTIVE) | **126,3** T=0 / 129,3 T=0,7 (wall.py, `qwen-uncensored.sh` na porcie testowym, ctx 262 144, PM4 WA=2, MTP n4 + lookup W16) | 434,8 (copy_bench `mvs` T=0; build qprep-spec 50ca29355, przed K-012/K-047) | fill 255k: 492,0 (prompt ~255 tys. tok.); pp512 1013 (llama-bench, bez spekulacji, PM4=0) | 262 144, KV q4_0, KV draftu q4_0 | `~/qwen-opt/tools/topka-start.sh qwen-uncensored` (produkcja :8080); osobno: `PORT=18080 ~/qwen-opt/topki/xtx/qwen-uncensored.sh` [^xtx-qwen-unc] | `~/llama-topka-k047` = k047 24aa8b3a3 (k183e + K-047) | 2026-11-28 (czat); 2026-11-25 (kopia, fill); 2026-11-27 (pp512) | `~/qwen-opt/k209/res/summary.txt:40-47` (ramię P); `KOLEJKA-TESTOW.md:668`; `KOLEJKA-TESTOW.md:618`; `~/qwen-opt/k199/k199.md` (wiersz qwen-prod FA on) | produkcja | vs poprzednia (`~/llama-topka-k183e`): wall +0,3…+0,4% we wszystkich 8 kategoriach (`REKORDY.md:276`, 2026-11-26). vs llama.cpp upstream 4c3c5810f + MTP: czat spec_sweep T=1 55,8 vs topka 111,4 (×2,00), `mvs` 84,7 vs 434,9 (×5,13) (`product/WYNIKI-XTX-2026-10-19.md:66,68`, 2026-10-19) |
| **Qwen3.8-27B UD-Q4_K_XL** | 120,58 T=1 (spec_sweep, ctx 204 800); **wall.py: brak pomiaru** | 433,8 (copy_bench `mvs` T=0, topka f9b84bcfa) | pp4096 1125,3 (llama-bench, topka f2217bac7); fill 255k przy ctx 262 144: 467,5 | 204 800, KV q4_0 (262 144 wchodzi z zapasem 336 MiB, nie w topce) | `PORT=18080 ~/qwen-opt/topki/xtx/qwen.sh` [^xtx-qwen-ud] | `~/llama-topka` = topka-q70 3191b25f4 (nie k047) | 2026-11-05 (czat); 2026-10-21 (kopia); 2026-10-19 (pp4096) | `REKORDY.md:147`; `REKORDY.md:129`; `product/WYNIKI-XTX-2026-10-19.md:42`; `REKORDY.md:167` | gotowa | vs poprzednia: spec_sweep 117,9 → 120,58 (`REKORDY.md:147`). vs llama.cpp upstream 4c3c5810f + MTP: czat spec_sweep T=1 60,1 vs topka 114,8 (×1,91), `mvs` 89,1 vs 419,9 (×4,71) (`product/WYNIKI-XTX-2026-10-19.md:44,46`, 2026-10-19) |
| **Inkling 2 Mini Uncensored AD-Q4_K** (Maya) | **152,4** T=0 / 149,0 T=0,7 (wall.py, bin-k207, ctx 440 320, MTP drafter); konfiguracja produkcyjna bin-k207p przy 557 056: T=0 153,9; LocalMaxxing reasoning-v1 T=0 320 tok.: 157,4 | copy 453,9, edit 377,2, python_edit 387,6 (K-147 bench, `maya-atomic.json`) | 128k: 2083 (bin-k200p); 546k: 916 | 557 056, KV q4 (drafter 131 072 pozycji; plan dopuszcza do 604 160) | `PORT=18796 ~/qwen-opt/topki/xtx/inkling.sh`; na :8080: `echo inkling > ~/qwen-opt/topki/xtx/ACTIVE && ~/qwen-opt/tools/topka-restart.sh` [^xtx-ink-ad] | Maya `~/k134/bin-k207p/maya-ik2` (drzewo `~/k134/wt-k207` aff3385b) | 2026-11-28 | `~/k134/k207/wall.txt:25,30`; `~/k134/k208/summary.txt:9,15`; `~/k134/k210/summary.txt:14,19,24`; `~/k134/k202/summary-a.txt:22`; `~/k134/k207/summary.txt:16` | gotowa (topka; nie ACTIVE) | vs poprzednia (bin-k200p, 425 984): wall 151,9 / 149,0 → 152,4 / 149,0, kontekst 425 984 → 557 056 (`~/k134/k207/wall.txt:6,11`). vs llama.cpp `inkling-opt` dd9a3f0 + DSpark n7, KV q4_0, ctx 16 384: kopie 95,2, T=0,7 28,0 (xbench, inny skrypt, `REKORDY.md:221`, 2026-11-23) |
| **Inkling 2 Mini GSQ-RCO IQ3_S bez cenzury** (Maya, 1M) | **104,2** T=0 / 101,3 T=0,7 (wall.py, ctx 1 048 576); dekod przy 128k 73,0–75,6, przy 360k 58,1 | brak pomiaru | brak pomiaru | 1 048 576, KV q4 (drafter 131 072) | `PORT=18796 ~/qwen-opt/topki/xtx/inkling-1m.sh`; na :8080: `echo inkling-1m > ~/qwen-opt/topki/xtx/ACTIVE && ~/qwen-opt/tools/topka-restart.sh` [^xtx-ink-1m] | Maya `~/k134/bin-k203p/maya-ik2` (`~/k134/wt-k203` e03e1d4a) | 2026-11-28 (00:02) | `~/k134/k203/summary-k206.txt:63-64`; `~/k134/k203/summary-k206b.txt:57-58,61` | gotowa | vs poprzednia (typy dokładne bez K-206): 67,8 / 65,4 (`~/k134/k203/summary-b.txt:51-52`). vs llama.cpp b12803 + DSpark przy 512k: 51,4 / 52,0 (wall.py, `~/qwen-opt/k205/res.txt:5,10`; 1M w llama.cpp tylko bez DSpark, `KOLEJKA-TESTOW.md:108`) |
| **Ternary Bonsai 2.5 27B Uncensored Q2_0** | **145,8** T=0,7 / 146,6 T=0 (wall.py, top-k 20 / top-p 0,95, MTP n2 + lookup W16 + słownik draftu 64k, ctx 262 144) | 446,4 (copy_bench `short` T=0) | topka-k157: brak pomiaru; pp512 przy d32k 726,0 (llama-bench, `~/wt/k025`, inny build) | 262 144, KV q4_0, KV draftu q4_0 | `PORT=18080 ~/qwen-opt/topki/xtx/bonsai.sh`; na :8080: `echo bonsai > ~/qwen-opt/topki/xtx/ACTIVE && ~/qwen-opt/tools/topka-restart.sh` [^xtx-bonsai] | `~/wt/topka-k157` 5225c0963 (K-157 Gemini) | 2026-11-25 | `~/qwen-opt/queue/logs/dsp-mtp2.log:8,13`; `wiki/modele/bonsai-2-5-uncensored.md:102`; `KOLEJKA-TESTOW.md:599` | gotowa | vs poprzednia (topka-best): czat T=0,7 106,5–108,0 (xbench, inny skrypt, `bonsai-2-5-uncensored.md:99`). vs llama.cpp: fork prism 910442b Q2_0 MTP n2 T=0,7 77,5–77,7, upstream Q2_0 MTP n3 65,8 (xbench, `bonsai-2-5-uncensored.md:46,48`) |
| Inkling 2 Mini NVFP4-Mixed (Nib) | 150,6 T=0,7 / 169,0 T=0 (wall.py, DSpark MTP, KV q4_0, Quest 224); z LoRA AtomicChat (bez cenzury): 147,3 / 156,6 | brak pomiaru | brak pomiaru | 262 848, KV q4_0 | `cd ~/models/nib && HIP_VISIBLE_DEVICES=0 ~/wt/nib-unc/build/nib serve -m ~/models/nib/Inkling-2-Mini-NVFP4-Mixed.gguf --host 127.0.0.1 --port 18796 --slots 1 -c 262848 --kv-type q4_0 --sparse-pages 224 --mtp ~/models/nib/mtp.safetensors --no-vision` (+ `--lora ~/models/inkling/Inkling-2-Mini-Uncensored-LoRA.gguf` dla wersji bez cenzury) | Nib Chromadera 2e16cf0; `nib-unc` 018d0fc+eb07c8f | 2026-11-25 | `~/qwen-opt/nib/out/nib.txt:81,86`; `REKORDY.md:256-257`; `~/qwen-opt/nib/nib-unc-ab.sh:13-14,17-18` | gotowa, poza produkcją (decyzja JARO: inne wagi, NVFP4) | Maya tego dnia 112,5 / 112,8 (`nib.txt:61,66`); dziś Maya AD 152,4 / 149,0 |
| Inkling 2 Mini UD-Q4_K_XL (z cenzurą, Maya 1.1.73) | kopie 112,7, T=0,7 80,7, długi 2k 80,0 (drafting on, bez draftera) | brak pomiaru | brak pomiaru | brak danych | `~/k134/maya-unsloth-on.json` przez Maya `serve/server.py` (`~/k134/mayaserve.sh`, linia zakomentowana) | Maya 1.1.73 | 2026-11-23 | `REKORDY.md:237` | brak pełnego stosu (stos K-137…K-207 tylko dla AD) | Strata 0.1.66 + DSpark: kopie 100,6–109,6, T=0,7 60,6, page fault przy długim prompcie (`REKORDY.md:237`) |
| LFM2.5-24B-A2B Q5_K_M | 274,1 T=1 (spec_sweep, bez draftera; MoE bez głowicy MTP); rekord run-llm.sh 293,7 | copy lookup W8 334,7, W16 312,4, bez lookupu 288,2 | pp4096 7148 (ub 2048) | 131 072, **KV q8_0** (poza regułą JARO q4–q6) | `PORT=18080 ~/qwen-opt/run-topka.sh lfm` (plik usunięty z `~/models/lfm`) | topka f2217bac7 | 2026-10-19 (czat), 2026-10-18 (pp) | `product/WYNIKI-XTX-2026-10-19.md:106`; `REKORDY.md:60,63`; `testy/najlepsze-wyniki.md:104-106` | brak pełnego stosu (brak draftera, lookup nieprzyjęty, brak pliku) | vs llama.cpp upstream: 146,8 → 274,1 (×1,87) (`WYNIKI-XTX-2026-10-19.md:106`) |
| LFM2.5-24B-A2B Uncensored AD-Q5_K_M | 250,7 T=1 (spec_sweep, bez draftera); rekord 267,3 | brak pomiaru | pp4096 6291 | 131 072, KV q8_0 | `PORT=18080 ~/qwen-opt/run-topka.sh lfm-uncensored` (plik usunięty) | topka f2217bac7 | 2026-10-19 | `product/WYNIKI-XTX-2026-10-19.md:127`; `REKORDY.md:70` | brak pełnego stosu | vs llama.cpp upstream: 143,9 → 250,7 (×1,74) |
| Flint 40B-A2.5B NVFP4 | brak pomiaru | brak pomiaru | brak pomiaru | max fit (`~/qwen-opt/flint/ctx-max`) | `PORT=18080 ~/qwen-opt/run-topka.sh flint` (plik brak, w `~/models/flint` tylko README) | `~/qwen-opt/flint/inst` | – | `~/qwen-opt/run-topka.sh:49-54` | brak pełnego stosu | – |

Bez żadnego pomiaru na XTX (brak pliku na dysku, decyzja JARO 2026-11-26 „nie pobieramy”, [[2026-11-26-bez-pobierania-modeli]]): Qwen3.6-35B-A3B (serwer w K-025 nie wstał, `KOLEJKA-TESTOW.md:597`), Gemma 4, Nemotron 3.5 Bolt 74B-A9B, Gyro-Coder, Swift 1.5, Qwen3.5-9B, Qwen3.8-Flash-Next.

Bez spekulacji (tylko porównawczo, nie topka): Qwen Uncensored tg128 42,4 vs upstream b12803 37,2; Qwen UD 41,0 vs 36,1; Inkling IQ3_S upstream 52,6; Bonsai topka-k157 76,9 (`~/qwen-opt/k199/k199.md`, 2026-11-27; `bonsai-2-5-uncensored.md:102`).

[^xtx-qwen-unc]: `~/qwen-opt/topki/xtx/qwen-uncensored.sh:9-19`: `TOPKA_CTX=262144`, `ROCM_DIR=~/llama-topka-k047`, `GGML_HIP_K047=1`, `GGML_HIP_K012=1`, `LLAMA_SERVER_CACHE_EVICT=cost`, `LLAMA_SERVER_CACHE_THIN=4`, `LLAMA_SERVER_CACHE_PREFIX=2`, potem `exec ~/qwen-opt/run-topka.sh uncensored`. `run-topka.sh:87-117` dokłada: `GGML_HIP_PM4=1 GGML_HIP_PM4_WA=2 GGML_HIP_PM4_GUARD=1 HSA_USE_SVM=0`, `LLAMA_SPEC_LOOKUP=3 LLAMA_SPEC_LOOKUP_W=16`, `LLAMA_SERVER_CACHE_SHARE_MIN=1024`, `LLAMA_GPU_VERIFY=1`, `LLAMA_SPEC_COUPLED=1`, host-gap (`LLAMA_SERVER_YIELD_FAST=2 GGML_HIP_PM4_MIN_DISPATCH=16 GGML_HIP_PM4_LAZY_EXEC=1`), `DRAFT_N=4`, `GGML_HIP_FA_D256_VAR=83`, `LLAMA_SERVER_CACHE_HUGE=1`, `LLAMA_MTP_REQUANT_CACHE=~/.cache/llama-mtp`, `LLAMA_SERVER_SAFE_SPECIAL=1 LLAMA_SERVER_SAFE_TOOLS=1 LLAMA_TOKENIZE_PAR=8 LLAMA_CKPT_VRAM=2 LLAMA_CHAT_NATIVE=1 LLAMA_CHAT_LATE_SYSTEM=1`. `run-llm.sh:68,99-102,126` składa: `llama-server -m ~/models/orca/Qwen3.8-27B-Uncensored-Q4_K_M.gguf -ngl 999 -fa on -ctk q4_0 -ctv q4_0 -c 262144 -np 1 --jinja --cache-ram 40960 --reasoning-effort low --spec-type draft-mtp --spec-draft-n-max 4 --spec-draft-vocab ~/models/draft/draft_vocab_qwen38.txt --spec-draft-vocab-n 65536 --spec-draft-head-type iq4_xs --spec-mtp-type iq4_xs -ctkd q4_0 -ctvd q4_0`. Skryptu nie wolno wołać na :8080 wprost (`qwen-uncensored.sh:8`); produkcję podnosi `tools/topka-start.sh` (keeper, restart, `@reboot`).

[^xtx-qwen-ud]: `~/qwen-opt/topki/xtx/qwen.sh:4-5`: `TOPKA_CTX=204800`, `exec ~/qwen-opt/run-topka.sh qwen`. Te same przełączniki co [^xtx-qwen-unc], ale bez `ROCM_DIR`, więc silnik to domyślny `~/llama-topka` (topka-q70 3191b25f4, `~/llama-topka/ENGINE`), bez K-012, K-020, K-006, K-047. Plik `~/models/Qwen3.8-27B-UD-Q4_K_XL.gguf`, `-c 204800` (`run-llm.sh:31,67`).

[^xtx-ink-ad]: `~/qwen-opt/topki/xtx/inkling.sh:5-7` startuje `serve/server.py --engine maya --config ~/k134/maya-atomic.json`. `maya-atomic.json:2-55`: `exe ~/k134/bin-k207p/maya-ik2`, `--model ~/models/inkling/Inkling-2-Mini-Uncensored-AD-Q4_K.gguf --max-context 557056 --drafting on --draft ~/models/inkling/mtp.safetensors`; env: `IK2_KV=q4`, kernele HIP `IK2_HIP_COMB=1 EXPV=1 FUSE=1 MVF16=1 PCONV=1 LGD=2 LGR=1 NT=15`, okno sufiksowe `IK2_SUFFIX=128`, drafter K-158 (`IK2_K158_DGRAPH CONF GSORT SFXDS VATT VEXP VMVF16 VROUTE VQKV VCOMB EARLY DQ8 HSL GATE GATE_DEFER =1`, `IK2_K158_HSL_FILE=~/models/nib/draft_shortlist.bin`, `POLICY=0`, `CMIN=0`, `IK2_K_CONF=0.75`), K-185 (`IK2_K185_GEXP LGB DONLINE EMAG =1`), `IK2_K158R_QS=0.7`, K-158s (`IK2_K158S=1 IK2_K158S_TLOOK=0.8`), K-200 (`IK2_K200=1`), `IK2_DRAFT_CTX=131072`. Czat właściciela na :18796 podnosi też `~/k134/mayaserve.sh` (ta sama konfiguracja, blokuje :8080 do 12 h).

[^xtx-ink-1m]: `~/qwen-opt/topki/xtx/inkling-1m.sh:6-9` startuje Mayę z `~/k134/maya-iq3s-1m.json:2-56`: `exe ~/k134/bin-k203p/maya-ik2`, `--model ~/models/inkling/gsq-rco/Inkling-2-Mini-GSQ-RCO-IQ3_S.gguf --max-context 1048576 --drafting on --draft ~/models/inkling/mtp.safetensors`; env jak AD plus `IK2_ABLATE=~/models/inkling/Inkling-2-Mini-Uncensored-LoRA.gguf` (rzut kierunku zamiast cenzury), `IK2_DRAFT_CTX=131072`. KL vs llama.cpp na tym samym pliku 0,0019 (`~/k134/k203/summary-b.txt:18`).

[^xtx-bonsai]: `~/qwen-opt/topki/xtx/bonsai.sh:5-14`: `TOPKA_CTX=262144`, `~/wt/topka-k157/build-hip/bin/llama-server`, env `GGML_HIP_K157_MMVF_THIN=0 GGML_HIP_PM4=1 GGML_HIP_PM4_WA=2 GGML_HIP_PM4_GUARD=1 HSA_USE_SVM=0 GGML_HIP_FA_D256_VAR=83 LLAMA_SPEC_LOOKUP=3 LLAMA_SPEC_LOOKUP_W=16 LLAMA_GPU_VERIFY=1 LLAMA_SPEC_COUPLED=1 LLAMA_SERVER_YIELD_FAST=2 GGML_HIP_PM4_MIN_DISPATCH=16 GGML_HIP_PM4_LAZY_EXEC=1 LLAMA_SERVER_CACHE_SHARE_MIN=1024`; `llama-server -m ~/models/bonsai25/Ternary-Bonsai-2.5-27B-Uncensored-Q2_0-mtp.gguf -ngl 999 -fa on -ctk q4_0 -ctv q4_0 -c 262144 -np 1 --jinja --spec-type draft-mtp --spec-draft-n-max 2 -ctkd q4_0 -ctvd q4_0 --spec-draft-vocab ~/models/draft/draft_vocab_qwen38.txt --spec-draft-vocab-n 65536 --temp 0.7 --min-p 0`. Pomiar 145,8 szedł przez `~/qwen-opt/bonsai25/drafter-gate.sh:19,51` (ten sam build i ctx; czy z `MMVF_THIN=0`, nie sprawdzone).

### RX 9070 XT

RDNA4 gfx1201, 16 GB, 640 GB/s (`qwen-opt/skill-io/karty.json:64`). Nie mamy karty (zakup planowany); nasz stos nie ma kerneli WMMA gfx12 ani PM4 dla RDNA4. Wszystkie liczby niżej są obce.

| model | czat t/s (pełny stos) | kopia/kod t/s | prefill t/s | kontekst | komenda startu | commit/build | data | źródło | status | vs poprzednia / vs llama.cpp+spec |
|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3.8-27B | brak pomiaru | brak pomiaru | brak pomiaru | – | – | – | – | – | brak pełnego stosu | – |
| Inkling 2 Mini | brak pomiaru | brak pomiaru | brak pomiaru | – | – | – | – | – | brak pełnego stosu | – |
| Qwen3.6-35B-A3B UD-Q4_K_XL | brak naszego pomiaru; obcy: RustingStrata HIP, MTP 3: dekod 209–219 | brak pomiaru | obcy: pp4096 2993 (Vulkan 2325) | brak danych | – | RustingStrata (ROCm 7.2.3) | ≤ 2026-11-25 (data notatki) | `wiki/ekosystem/rustingstrata.md:23` | brak pełnego stosu | – |
| Qwen3.5-9B Q6_K | brak naszego pomiaru; obcy: llama.cpp Vulkan 62 (bez spekulacji), vLLM FP8 48 | brak pomiaru | brak pomiaru | brak danych | – | – | ≤ 2026-10-16 (data notatki) | `wiki/modele/modele-katalogowe.md:16` | brak pełnego stosu | – |

### Radeon AI PRO R9700

RDNA4 gfx1201 (Navi48 jak 9070 XT), 32 GB, 640 GB/s; do wynajęcia w Hostkey za €0,471/h ([[radeon-ai-pro-r9700]]). Nasz pomiar: brak. Liczby obce, do celu i sufitu (27B ~4 bity przy 640 GB/s: ≤ 380 t/s przy 8 tok./krok, [[zwiad-2026-11-17]]).

| model | czat t/s (pełny stos) | kopia/kod t/s | prefill t/s | kontekst | komenda startu | commit/build | data | źródło | status | vs poprzednia / vs llama.cpp+spec |
|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3.8-27B | brak naszego pomiaru; obce: hipfire 0.3.1 MQ4V2 + DFlash2 n=16: 111,6 (LocalMaxxing, verified); Lucebox UD-IQ4_XS + DFlash2 blok 16, T=0, HumanEval: 208,1 (AR 32,3) | brak pomiaru | brak pomiaru | brak danych | – | hipfire 0.3.1 / Lucebox | 2026-09-15 / ≤ 2026-11-25 | `product/research/watch/2026-10-20.md:30`; `wiki/ekosystem/lucebox.md:12` | brak pełnego stosu | llama.cpp bez spekulacji 29,7–30,9 (`radeon-ai-pro-r9700.md:20`); kyuz0 Radiance 594,7 odrzucone jako niefizyczne (`zwiad-2026-11-17.md:16-17`) |
| Inkling 2 Mini | brak naszego pomiaru; obce: Lucebox z DSpark T=1: 143,5 (AR 81,7, prefill 3628); nib gfx1201 NVFP4 bez spekulacji 97,6 (niezweryfikowane) | brak pomiaru | obcy: 3628 (Lucebox) | brak danych | – | Lucebox / nib fork messerli-wallace | 2026-11-23 / 2026-11-28 | `wiki/ekosystem/lucebox.md:34`; `wiki/research/zwiad-2026-11-28.md:15` | brak pełnego stosu | nasz XTX AD 152,4 / 149,0 przy 960 GB/s |
| Qwen3.6-35B-A3B UD-Q4_K_XL | brak naszego pomiaru; obcy: llama.cpp RADV + MTP n=3: 172,2 (przy 65 536: 151,2); Strata 117,8 | brak pomiaru | brak pomiaru | brak danych | – | llama.cpp Vulkan RADV / Strata 0.1.45 | 2026-09-02 / 2026-10-19 | `product/research/watch/2026-11-14.md:297`; `wiki/ekosystem/strata.md:16` | brak pełnego stosu | Strata 117,8 vs llama.cpp 82 (bez spekulacji) |
| Nanbeige4.3-33B-Base Q5_K_S | brak naszego pomiaru; obcy: ngram-mod 239,4 (jeden przebieg, niezweryfikowane) | brak pomiaru | brak pomiaru | brak danych | – | llama.cpp | 2026-11-21 | `wiki/modele/nanbeige4-3-33b.md:14` | brak pełnego stosu | – |

### MI300X

CDNA3 gfx942, 192 GB, 5300 GB/s (`qwen-opt/skill-io/karty.json:84`); dostęp tylko przez AMD Developer Cloud ($100 kredytu na 30 dni, zakaz usług dla osób trzecich) albo RunPod $2,39/h ([[amd-dev-cloud]]). Żadna para model × MI300X nie była mierzona, ani przez nas, ani w źródłach wiki.

| model | czat t/s (pełny stos) | kopia/kod t/s | prefill t/s | kontekst | komenda startu | commit/build | data | źródło | status | vs poprzednia / vs llama.cpp+spec |
|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3.8-27B | brak pomiaru | brak pomiaru | brak pomiaru | – | – | – | – | – | brak pełnego stosu | – |
| Inkling 2 Mini | brak pomiaru | brak pomiaru | brak pomiaru | – | – | – | – | – | brak pełnego stosu | – |

### Strix Halo

RDNA3.5 gfx1151 (Radeon 8060S), do 128 GB UMA, 256 GB/s (ok. 212 zmierzone, llm-tracker); dostęp: GigaGPU £299/mies. ([[strix-halo]]). Nasz pomiar: brak; część naszych bramek RDNA3 obejmuje gfx115x, ale nic nie było uruchomione.

| model | czat t/s (pełny stos) | kopia/kod t/s | prefill t/s | kontekst | komenda startu | commit/build | data | źródło | status | vs poprzednia / vs llama.cpp+spec |
|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3.8-27B | brak naszego pomiaru; obce: lemonade ROCm nightly przy 4k 17,43 (Vulkan 16,79), bez spekulacji; tensorfold 75 łącznie przy 16 strumieniach | brak pomiaru | brak pomiaru | 4k (lemonade) | – | llama.cpp ROCm nightly / tensorfold v1.2.5 | 2026-11-20 / 2026-11-09 | `wiki/ekosystem/lemonade.md:16`; `wiki/ekosystem/tensorfold.md:31` | brak pełnego stosu | – |
| Inkling 2 Mini | brak naszego pomiaru; obcy: Unsloth llama.cpp 24 → 33 bez spekulacji (model z kontekstu K-138, [INFERENCE]) | brak pomiaru | brak pomiaru | brak danych | – | Unsloth b12649-mix | 2026-11-23 | `KOLEJKA-TESTOW.md:1080` | brak pełnego stosu | – |
| Qwen3.8-Flash-Next UD-IQ4_XS (Strata) | brak naszego pomiaru; obcy: 53,8 przy 8K | brak pomiaru | obcy: ok. 1293 przy 8K | 8K | – | Strata | ≤ 2026-10-16 (data notatki) | `wiki/karty/strix-halo.md:20` | brak pełnego stosu | – |
| Gyro-Coder TQ2_T | brak naszego pomiaru; obcy: Vulkan + MTP, 11–22 na strumień przy 2 strumieniach; KLD do Q8_0 0,118 | brak pomiaru | brak pomiaru | 2048 (KLD) | – | fork agentionai llama.cpp 9aa51ce (Vulkan) | 2026-10-24 | `wiki/modele/gyro-coder.md:18-19` | brak pełnego stosu | – |

## NVIDIA

**Topka = najszybszy zmierzony pełny stos (spekulacja, kwant, KV, build, env, maksymalny kontekst) dla pary karta × model. Główna liczba to zawsze czat z pełnym stosem. Liczba bez spekulacji nigdy nie jest główna.**

Jak czytać tabele:
- Dwie metryki, nie mieszać:
  - **wall** = mediana 4 promptów (kod, tech, pl, json) × 300 tok., T=0 / T=0,7 (K-204, K-207, nvq5);
  - **T1** = mediana `spec_sweep` 6 promptów × seed 1 × 400 tok., T=1 (kampania 67c).
- **Pełny kontekst** = największy `-c`, który przeszedł fill (prompt ctx−640 + 128 tok.) albo igły przy 95% głębokości.
- **Prefill**: z filla (`pp` w `nv67c-summary.txt`, jaroserverai `~/qwen-opt/cloud/results/`), chyba że podano inną długość.
- **Status**:
  - `produkcja` = to, co dziś poleca aplikacja Enigma i strona ([[final-recipes-nvidia]], wiersze „Enigma dziś”);
  - `gotowa` = zmierzony pełny stos, niewdrożony. Dotyczy też silników Enigmy (`enigma-cuda-fork` kvqlean, `enigma-cuda-lean`, `enigma-cuda-prism`), które final-recipes oznacza „po publikacji archiwów”;
  - `brak pełnego stosu` = brakuje spekulacji albo pełnego kontekstu.
- Buildy silników (`app/engine/data/engines.json`):
  - upstream pin `b11856`;
  - `enigma-cuda-lean` = `b12110lean 55933253f`;
  - `enigma-cuda-prism` = `prism-b12128 d7b2896`;
  - `enigma-cuda-fork` = `kvqlean 2a261101b+007a6f813` (binarka `llama-kvqleana` bez AVX2 dla wszystkich kart, K-127);
  - `enigma-cuda-inkling` = oficjalny `b12811`;
  - K-207: `b12811 + k207-ablate f7040f25e` (nasz build, `version-k207.txt`: build 239).
- Przy hoście 5060 Ti: procesor hosta zmienia dekod tej samej karty 2–2,6× (EPYC 7402 vs Ryzen). Porównujemy tylko na tym samym hoście ([[2026-11-28-k207-ablacja-zamiast-lora]]).

Wspólne komendy (flagi z `final-recipes-nvidia.md:12`). `<…>` to plik z repo HF podanego w final-recipes.
- **FORK** (env + flagi `enigma-cuda-fork`):
  ```
  GGML_CUDA_KVQ=1 LLAMA_SPEC_LOOKUP=3 LLAMA_SPEC_LOOKUP_W=16 LLAMA_GPU_VERIFY=1 LLAMA_SERVER_CACHE_SHARE_MIN=1024 \
  llama-kvqleana -m <model> -ngl 999 -fa on -ctk q4_0 -ctv q4_0 -c <ctx> -ub <ub> --jinja \
    --spec-type draft-mtp --spec-draft-n-max 4 -ctkd q4_0 -ctvd q4_0 \
    --spec-draft-vocab draft_vocab_qwen38.txt --spec-draft-vocab-n 65536 \
    --spec-draft-head-type iq4_xs --spec-mtp-type iq4_xs
  ```
- **LEAN** (`enigma-cuda-lean`):
  ```
  llama-server -m <model> -ngl 999 -fa on -ctk q4_0 -ctv q4_0 -c <ctx> -ub 256 --jinja \
    --spec-type draft-mtp --spec-draft-n-max 2 --spec-draft-n-ubatch 64 -ctkd q4_0 -ctvd q4_0
  ```
- **PIN+MTP** (upstream b11856):
  ```
  llama-server -m <model> -ngl 999 -fa on -ctk q4_0 -ctv q4_0 -c <ctx> -ub <ub> --jinja \
    --spec-type draft-mtp --spec-draft-n-max 3 --spec-draft-n-ubatch 64
  ```
- **INK** (Inkling 16 GB, K-204; `-c` i adapter w wierszu):
  ```
  llama-server -m Inkling-2-Mini-GSQ-RCO-IQ3_S.gguf -md dspark-Inkling-2-Mini-Q8_0.gguf \
    -ngl 99 -ngld 99 -fit off -fa on -ctk q4_0 -ctv q4_0 -c <ctx> -ub 128 -b 128 -np 1 --jinja \
    --spec-type draft-dspark --spec-draft-n-max 2 --spec-draft-p-min 0 \
    <--lora | --ablate-lora> Inkling-2-Mini-Uncensored-LoRA.gguf
  ```
  Bez `-ctkd/-ctvd`: KV draftera q4 pada przy 270k (`2026-11-27-k204-enigma-16gb-inkling.md:37`).

### RTX 5090

32 GB, 1792 GB/s (`qwen-opt/skill-io/karty.json`), host 575 W.

| model | czat t/s (full stack, warunki) | kopia/kod t/s | prefill t/s (długość) | kontekst | komenda startu | commit/build | data | źródło | status | vs poprzednia / vs llama.cpp+spec |
|---|---|---|---|---|---|---|---|---|---|---|
| **Inkling 2 Mini UD-Q4_K_XL bez cenzury (topka)** | **175,62 / 163,06** wall, DSpark n2 + `--ablate-lora`, i7-14700K | copy-cpp 220,5 / copy-py 185,3 | 451 (776k w igle) | **819 200** (igła 5/5 przy 776 090) | `llama-server -m Inkling-2-Mini-UD-Q4_K_XL.gguf -ngl 99 -fit off -fa on -ctk q4_0 -ctv q4_0 -c 819200 -ub 128 -b 128 -np 1 --jinja --ablate-lora Inkling-2-Mini-Uncensored-LoRA.gguf -md dspark-Inkling-2-Mini-Q8_0.gguf -ngld 99 --spec-type draft-dspark --spec-draft-n-max 2 --spec-draft-p-min 0` | b12811 + k207-ablate f7040f25e | 2026-11-28 | `qwen-opt/cloud/nvq3/results/TOPKI-NV-2026-11-28.md` | gotowa | vs Qwen fork 148,57 (+18%); fork przy 262 144 OOM |
| **Qwen3.8-27B UD-Q6_K (topka)** | **148,57** T1, fork+kvq+lean, MTP n4 + słownik 64k + lookup W16 | brak pomiaru | brak pomiaru (fill PASS, dekod w fillu 167) | 262 144 (peak 28 232 MiB) | FORK z `-m Qwen3.8-27B-UD-Q6_K.gguf -c 262144 -ub 512` | kvqlean 2a261101b+007a6f813 | 2026-11-07 | `final-recipes-nvidia.md:23`; `REKORDY.md:189` | gotowa | +45,4% vs produkcja 102,19; +47,4% vs pick na tym samym hoście 100,90 (llama.cpp pin + MTP n3) |
| Qwen3.8-27B UD-Q6_K | 102,19 T1, pin MTP n3 ubd 64 (bez MTP 62,49) | brak pomiaru | 1 130 (fill 261 504) | 262 144 (peak 28 592) | PIN+MTP z `-m Qwen3.8-27B-UD-Q6_K.gguf -c 262144 -ub 1024` | b11856 | 2026-11-07 | `final-recipes-nvidia.md:22`; `nv67c-summary.txt:245` | produkcja | +63,5% vs bez MTP; pin vs b12110 ABBA 99,8 vs 91,7 (`REKORDY.md:194`) |
| Qwen3.6-35B-A3B Q5_K_XL | 319,5 spec_sweep T=1 (6 × 3 seedy), MTP n2 | brak pomiaru | 3 060 (fill) | 262 144 | `llama-server -m Qwen3.6-35B-A3B-Q5_K_XL.gguf -ngl 999 -fa on -ctk q4_0 -ctv q4_0 -c 262144 --jinja --spec-type draft-mtp --spec-draft-n-max 2` (dokładne `-ub` brak w notatce) | b12110 | 2026-11-07 | `REKORDY.md:178`; `2026-11-07-kampania-nvidia-vast.md:26` | gotowa | +30,6% vs bez MTP 244,6 |
| Inkling 2 Mini | brak pomiaru | – | – | – | – | – | – | – | brak pełnego stosu | do kolejki |

### RTX 4090

24 GB, 1008 GB/s (`karty.json`), host z limitem 250/450 W.

| model | czat t/s (full stack, warunki) | kopia/kod t/s | prefill t/s (długość) | kontekst | komenda startu | commit/build | data | źródło | status | vs poprzednia / vs llama.cpp+spec |
|---|---|---|---|---|---|---|---|---|---|---|
| **Inkling 2 Mini UD-Q4_K_XL bez cenzury (topka)** | **126,43 / 103,56** wall, DSpark n3 + ablacja, EPYC 7R13 | copy-cpp 147,0 / copy-py 139,0 | 556 (349k w igle) | **368 640** (igła 5/5) | `llama-server -m Inkling-2-Mini-UD-Q4_K_XL.gguf -ngl 99 -fit off -fa on -ctk q4_0 -ctv q4_0 -c 368640 -ub 128 -b 128 -np 1 --jinja --ablate-lora Inkling-2-Mini-Uncensored-LoRA.gguf -md dspark-Inkling-2-Mini-Q8_0.gguf -ngld 99 --spec-type draft-dspark --spec-draft-n-max 3 --spec-draft-p-min 0` | b12811 + k207-ablate f7040f25e | 2026-11-28 | `qwen-opt/cloud/nvq3/results/TOPKI-NV-2026-11-28.md` | gotowa | vs Qwen fork 101,27 (+25%) |
| **Qwen3.8-27B UD-Q4_K_XL (topka)** | **101,27** T1, fork+kvq+lean, MTP n4 + słownik 64k + lookup W16 | brak pomiaru | 987 (fill 261 504) | 262 144 (peak 23 852) | FORK z `-m Qwen3.8-27B-UD-Q4_K_XL.gguf -c 262144 -ub 256` | kvqlean 2a261101b+007a6f813 | 2026-11-07 | `final-recipes-nvidia.md:30`; `REKORDY.md:191`; `nv67c-summary.txt:149` | gotowa | +32,5% vs llama.cpp pin + MTP n3 76,44 |
| Qwen3.8-27B UD-Q4_K_XL | 76,44 T1, pin MTP n3 (bez MTP 46,94) | brak pomiaru | 945 (fill 261 504) | 262 144 (peak 24 028) | PIN+MTP z `-m Qwen3.8-27B-UD-Q4_K_XL.gguf -c 262144 -ub 256` | b11856 | 2026-11-07 | `final-recipes-nvidia.md:29`; `nv67c-summary.txt:176` | produkcja | +62,8% vs bez MTP |
| Qwen3.8-27B UD-Q4_K_XL, `-np 2` | agregat 94,35 (2 żądania), b12110 MTP n3 | – | – | 65 536 | brak pełnej komendy w notatce | b12110 | 2026-11-07 | `REKORDY.md:193` | brak pełnego stosu (65k) | +36% vs `-np 1` 69,46 |
| Inkling 2 Mini | brak pomiaru | – | – | – | – | – | – | – | brak pełnego stosu | do kolejki |

### RTX 3090

24 GB, 936 GB/s (`karty.json`). Hosty 340–418 W. Procesor hosta zmienia dekod o ok. 27% (`2026-11-26-nvq3.md:21`).

| model | czat t/s (full stack, warunki) | kopia/kod t/s | prefill t/s (długość) | kontekst | komenda startu | commit/build | data | źródło | status | vs poprzednia / vs llama.cpp+spec |
|---|---|---|---|---|---|---|---|---|---|---|
| **Inkling 2 Mini UD-Q4_K_XL bez cenzury (topka)** | **95,09 / 84,40** wall, DSpark n2 + ablacja, Ryzen 5 3600 | brak (test kopii zwrócił 0) | 340 (326k w igle) | **344 064** (igła 5/5; 376 832 startuje, igła nie) | `llama-server -m Inkling-2-Mini-UD-Q4_K_XL.gguf -ngl 99 -fit off -fa on -ctk q4_0 -ctv q4_0 -c 344064 -ub 128 -b 128 -np 1 --jinja --ablate-lora Inkling-2-Mini-Uncensored-LoRA.gguf -md dspark-Inkling-2-Mini-Q8_0.gguf -ngld 99 --spec-type draft-dspark --spec-draft-n-max 2 --spec-draft-p-min 0` | b12811 + k207-ablate f7040f25e | 2026-11-28 | `qwen-opt/cloud/nvq3/results/TOPKI-NV-2026-11-28.md` | gotowa | vs Qwen fork 79,97 (+19%) |
| **Qwen3.8-27B UD-Q4_K_XL (topka)** | **79,97** T1, fork+kvq+lean (`kvqleana`), MTP n4 + słownik 64k + lookup W16, host 340 W bez AVX2 | 270,5 (kopia, fork MTP n2, Ryzen 5900X, 2026-11-26) | 487,1 (fill 262k, fork MTP n2, 2026-11-26); 420 (głęboki 130k → 262k) | 262 144 (peak 23 706) | FORK z `-m Qwen3.8-27B-UD-Q4_K_XL.gguf -c 262144 -ub 256` | kvqlean 2a261101b+007a6f813 | 2026-11-07 | `final-recipes-nvidia.md:30`; `REKORDY.md:206`; `2026-11-26-nvq3.md:14`; `2026-11-26-nvq-3090.md:20`; `2026-11-09-qwen-warp-vs-fork-3090.md:32` | gotowa | +30,1% vs llama.cpp pin + MTP n3 61,49 (przy 245 760); K-129: na Ampere n2 ≥ n4 (`2026-11-19-k118-nvidia-pelna-moc.md`), przepis ma n4 |
| Qwen3.8-27B UD-Q4_K_XL | 61,49 T1, pin MTP n3 (bez MTP 40,93) | brak pomiaru | 542 (fill 245 120) | 245 760 (peak 23 448) | PIN+MTP z `-m Qwen3.8-27B-UD-Q4_K_XL.gguf -c 245760 -ub 256` | b11856 | 2026-11-07 | `final-recipes-nvidia.md:29`; `nv67c-summary.txt:99` | produkcja | +50,2% vs bez MTP |
| OrcaCyber-Nano-1.0 (qwen35, MTP wbudowane) | 79,2 przy 262k (głębokość 29k), MTP n2 + kvq-mma; 89,6 T=1 przy 32k (host 310 W) | brak pomiaru | brak pomiaru | 262 144 (23,3 GiB) | brak pełnej komendy w notatce | fork kvq-mma | 2026-10 (raport 56) | `raport-56-orca-3090.md:10,62,70` | gotowa | +90% vs goły upstream 38,3; +20,7% vs kvq=0 przy 262k |
| Qwen3.8-27B GSQ IQ3_XXS-mtp | 89,5 / 79,6 T=0 / T=1, fork kvqlean MTP n2, 418 W | brak pomiaru | 1 386 (~11k) | 8 192 (przy 95,6k: 71,8) | FORK z `--spec-draft-n-max 2 -c 8192 -ub 256` | kvqlean | 2026-11-19 | `2026-11-19-k118-nvidia-pelna-moc.md:31` | brak pełnego stosu (ctx 8 192) | n2 vs n4 T=1 +7,9% |
| Qwen3.8-27B UD-Q4_K_XL (cuda-topka2, stary) | 93,3 spec_sweep T=1, lookup W16 + share + GPU verify | 348,9 (mvs) | brak pomiaru | 204 800, ale OOM od ~55,6k | brak pełnej komendy | cuda-topka2 2a261101b | 2026-10-19 | `REKORDY.md` (wiersz 3090 / Qwen 27B Q4_K_XL `27-3090-final.md:20,59`) | brak pełnego stosu (kontekst ≤ 55k) | +24% vs upstream MTP 75,3 |
| Nemotron 3.5 Bolt 74B-A9B IQ2_XXS | 141,1 spec_sweep T=1, DFlash n_max 5 | brak pomiaru | brak pomiaru | bez draftera mieści 256K; z drafterem brak w notatce | brak pełnej komendy | gałąź `nemotron-3090` | 2026-10-16 | `karty/rtx-3090.md:33`; `REKORDY.md` (`14-nemotron-3090.md:77-83`) | brak pełnego stosu (kontekst z drafterem niezmierzony) | +61,8% vs A0 87,2 |
| LFM2.5-24B-A2B Q5_K_M | 263,9 spec_sweep, profil Ampere (MoE, bez drafta) | 280,4 (code-edit, Q4_K_M) | 7 907 / 7 995 (2k / 16k, Q4_K_M) | brak w notatce | brak pełnej komendy | `cuda-3090-opt` 3da7a02ec | 2026-10-16 | `karty/rtx-3090.md:26`; `REKORDY.md` (`16d-magnitude-vs-nasz.md:70,72-73`) | brak pełnego stosu (bez spekulacji, ctx nieznany) | +46,5% vs A0 180,2 |
| Inkling 2 Mini | brak naszego pomiaru; obcy punkt: UD-Q4_K_XL + DSpark 210,2 (reasoning-v1, T=0) | – | – | – | – | – | 2026-11-28 | `KOLEJKA-TESTOW.md:88` (K-208) | brak pełnego stosu | do kolejki |
| Swift 1.5 INT4 (obcy silnik qwen-warp) | 125,6 czat, DFlash2 W4A16 (fork na tym hoście 82,7) | 221,3 (kopia), 136,4 (kopia 64k) | 512 (130k → 262k) | 262 144 (krótki T=0 121,2; 262k T=0 68,3) | – (qwen-warp 689901c) | qwen-warp | 2026-11-27 | `2026-11-27-nvq4.md` (K-071); `2026-11-09-qwen-warp-vs-fork-3090.md:24,28` | brak pełnego stosu (inny silnik i wagi, jakość niezmierzona) | odniesienie: +52% vs nasz fork na tym samym hoście |

### RTX 5080

16 GB, host 250/360 W.

| model | czat t/s (full stack, warunki) | kopia/kod t/s | prefill t/s (długość) | kontekst | komenda startu | commit/build | data | źródło | status | vs poprzednia / vs llama.cpp+spec |
|---|---|---|---|---|---|---|---|---|---|---|
| **Inkling 2 Mini GSQ-RCO IQ3_S bez cenzury (topka)** | **138,68 / 142,34** wall, DSpark n2 + ablacja, i5-14400F | 156,0 | 1412,5 (32k, ub 128) | **247 808** (igła 5/5) | `llama-server -m Inkling-2-Mini-GSQ-RCO-IQ3_S.gguf -ngl 99 -fit off -fa on -ctk q4_0 -ctv q4_0 -c 247808 -ub 128 -b 128 -np 1 --jinja --ablate-lora Inkling-2-Mini-Uncensored-LoRA.gguf -md dspark-Inkling-2-Mini-Q8_0.gguf -ngld 99 --spec-type draft-dspark --spec-draft-n-max 2 --spec-draft-p-min 0 -ctkd q4_0 -ctvd q4_0` | b12811 + k207-ablate f7040f25e | 2026-11-28 | `qwen-opt/cloud/nvq3/results/TOPKI-NV-2026-11-28.md` | gotowa | vs Qwen GSQ MTP n3 na tym samym hoście 127,12 / 117,70 (+9% / +21%) |
| Qwen3.8-27B GSQ IQ3_XXS-mtp, MTP n3 (upstream) | 127,12 / 117,70 wall | 133,3 | 1791,1 (32k, ub 256) | 196 608 (igła 5/5) | `llama-server -m Qwen3.8-27B-GSQ-RCO-IQ3_XXS-mtp.gguf -ngl 99 -fit off -fa on -ctk q4_0 -ctv q4_0 -c 196608 -ub 256 -b 256 -np 1 --jinja --spec-type draft-mtp --spec-draft-n-max 3 --spec-draft-p-min 0` | b12811 | 2026-11-28 | `qwen-opt/cloud/nvq3/results/TOPKI-NV-2026-11-28.md` | gotowa | vs lean 81,62 (inny skrypt) |
| **Qwen3.8-27B GSQ IQ3_XXS-mtp (topka)** | **81,62** T1, lean MTP n2, KV draftu q4_0 | brak pomiaru | 832 (fill 216 448) | 217 088 (peak 15 632) | LEAN z `-m Qwen3.8-27B-GSQ-RCO-IQ3_XXS-mtp.gguf -c 217088` | b12110lean 55933253f | 2026-11-07 | `final-recipes-nvidia.md:39`; `nv67c-summary.txt:222` | gotowa | +38,8% vs produkcja 58,81; upstream MTP n3 przy tym ctx: OOM |
| Qwen3.8-27B GSQ IQ3_XXS-mtp | 58,81 T1, bez spekulacji | brak pomiaru | 909 (fill 208 256) | 208 896 (peak 14 562) | `llama-server -m Qwen3.8-27B-GSQ-RCO-IQ3_XXS-mtp.gguf -ngl 999 -fa on -ctk q4_0 -ctv q4_0 -c 208896 -ub 256 --jinja` | b11856 | 2026-11-07 | `final-recipes-nvidia.md:37`; `nv67c-summary.txt:233` | produkcja (brak pełnego stosu: bez spekulacji) | +13,0% vs stary pick 52,05 |
| Qwen3.8-27B GSQ IQ3_XXS-mtp, fork | 93,94 T1, fork KVQ=0, MTP n4 | brak pomiaru | 1 294 (fill 64 896) | 65 536 | FORK z `GGML_CUDA_KVQ=0 … -c 65536 -ub 256` | kvq | 2026-11-07 | `nv67c-summary.txt:212` | brak pełnego stosu (65k) | +15,1% vs lean 81,62 przy pełnym ctx |
| Qwen3.6-35B-A3B IQ4_XS | 83,4, MTP n2, 12 warstw ekspertów w RAM | brak pomiaru | brak pomiaru | 131 072 | brak pełnej komendy | b12110 | 2026-11-07 | `REKORDY.md:179` | brak pełnego stosu (131k) | +12% vs bez MTP 74,4 |
| Inkling 2 Mini IQ3_S | brak pomiaru | – | – | – | – | – | – | `2026-11-28-k207-ablacja-zamiast-lora.md:33` | brak pełnego stosu | do kolejki |

### RTX 4080 SUPER

16 GB, host 278/280 W. Jeden wynajem (K-118).

| model | czat t/s (full stack, warunki) | kopia/kod t/s | prefill t/s (długość) | kontekst | komenda startu | commit/build | data | źródło | status | vs poprzednia / vs llama.cpp+spec |
|---|---|---|---|---|---|---|---|---|---|---|
| **Inkling 2 Mini GSQ-RCO IQ3_S bez cenzury (topka)** | **119,36 / 109,05** wall, DSpark n3 + ablacja, Xeon E5-2680 v4 | 139,7 | 1204,7 (32k, ub 128) | **254 976** (igła 5/5; 271 360 OOM na pierwszym zapytaniu) | `llama-server -m Inkling-2-Mini-GSQ-RCO-IQ3_S.gguf -ngl 99 -fit off -fa on -ctk q4_0 -ctv q4_0 -c 254976 -ub 128 -b 128 -np 1 --jinja --ablate-lora Inkling-2-Mini-Uncensored-LoRA.gguf -md dspark-Inkling-2-Mini-Q8_0.gguf -ngld 99 --spec-type draft-dspark --spec-draft-n-max 3 --spec-draft-p-min 0 -ctkd q4_0 -ctvd q4_0` | b12811 + k207-ablate f7040f25e | 2026-11-28 | `qwen-opt/cloud/nvq3/results/TOPKI-NV-2026-11-28.md` | gotowa | vs Qwen GSQ MTP n3 99,83 / 95,37 (+20%) |
| Qwen3.8-27B GSQ IQ3_XXS-mtp | 107,3 / 91,2 T=0 / T=1 (`bench.py` 6 promptów), fork kvqlean MTP n4; n2 105,5 / 92,3 | brak pomiaru | 1 862 (~11k); 1 338 (95,6k) | 8 192 (95,6k: MTP n2 73,7) | FORK z `-m Qwen3.8-27B-GSQ-RCO-IQ3_XXS-mtp.gguf -c 8192 -ub 256` | kvqlean (wydanie 2026-11-07) | 2026-11-19 | `2026-11-19-k118-nvidia-pelna-moc.md:33`; `karty/rtx-4080-super.md` | brak pełnego stosu (ctx 8 192) | +93% vs plain 55,7 |
| Inkling 2 Mini IQ3_S | brak pomiaru | – | – | – | – | – | – | – | brak pełnego stosu | do kolejki |

### RTX 5060 Ti

16 GB, 448 GB/s (`karty.json`).

| model | czat t/s (full stack, warunki) | kopia/kod t/s | prefill t/s (długość) | kontekst | komenda startu | commit/build | data | źródło | status | vs poprzednia / vs llama.cpp+spec |
|---|---|---|---|---|---|---|---|---|---|---|
| Inkling 2 Mini GSQ-RCO IQ3_S bez cenzury, drugi host | 85,62 / 88,47 wall, DSpark n2 + ablacja, Ryzen 7 5700X | copy 108,1 / edit 100,8 | 721,9 (32k ub 128) / 939,2 (ub 256) | 262 144 (igła 5/5 przy 248 452) | jak topka | b12811 + k207-ablate f7040f25e | 2026-11-28 | `qwen-opt/cloud/nvq3/results/TOPKI-NV-2026-11-28.md` | pomiar uzupełniający | topka 88,45 / 90,78 (Ryzen 9700X) zostaje |
| **Inkling 2 Mini GSQ-RCO IQ3_S bez cenzury (topka)** | **88,45 / 90,78** wall T=0 / T=0,7, `--ablate-lora` + DSpark Q8_0 n2, p_min 0, ub 128; Ryzen 7 9700X, 180/180 W; odmowy 0/5 | 88,0 (prompt `code`, T=0) | brak pomiaru z ablacją (z LoRA: 632 przy 32k ub 128) | 262 144 (VRAM 15 594 / 15 664) | `llama-server -m Inkling-2-Mini-GSQ-RCO-IQ3_S.gguf -md dspark-Inkling-2-Mini-Q8_0.gguf -ngl 99 -ngld 99 -fit off -fa on -ctk q4_0 -ctv q4_0 -c 262144 -ub 128 -b 128 -np 1 --jinja --spec-type draft-dspark --spec-draft-n-max 2 --spec-draft-p-min 0 --ablate-lora Inkling-2-Mini-Uncensored-LoRA.gguf` | b12811 + k207-ablate f7040f25e (build 239) | 2026-11-28 | `REKORDY.md:306`; `2026-11-28-k207-ablacja-zamiast-lora.md:23`; `qwen-opt/cloud/nvq3/results/qwenbench-nvq3-5060tia-11281705/run.log:10,19,29`; `…/logs/k207-ablate.cmd:1` | gotowa | +15,5% / +27,5% vs llama.cpp + DSpark + LoRA na tym samym hoście (76,58 / 71,22); +33,1% vs produkcja 66,45 (inny host) |
| Inkling 2 Mini IQ3_S + LoRA bez cenzury | 66,45 / 61,97 wall, DSpark n2, ub 128, Ryzen 5 7600, 180 W (9900X: 74,5 / 69,6) | brak pomiaru | 632 (32k, ub 128); 268 (248k w 925 s) | 262 144 (igły 5/5 przy 95%, peak 15 698) | INK z `-c 262144 --lora Inkling-2-Mini-Uncensored-LoRA.gguf` | b12811 | 2026-11-27 | `final-recipes-nvidia.md:36`; `2026-11-27-k204-enigma-16gb-inkling.md:15-18,23-30` | produkcja (Linux, `enigma-cuda-inkling`) | +104% vs poprzednia produkcja Qwen GSQ 32,50 (ten sam host) |
| Inkling 2 Mini IQ3_S (z cenzurą) | 82,7 / 79,3 wall, DSpark n3 | brak pomiaru | brak pomiaru | 16 384 | brak pełnej komendy | b12811 | 2026-11-27 | `2026-11-27-nvq5.md:17` | brak pełnego stosu (16k) | +26% vs Qwen fork MTP n2 65,5 |
| Qwen3.8-27B GSQ IQ3_XXS-mtp | 49,44 T1, fork+kvq+lean MTP n4 | 198,8 (kopia, fork n3, 2026-11-26, ctx krótki) | brak pomiaru | 196 608 (peak 15 416; 229 376 crash) | FORK z `-m Qwen3.8-27B-GSQ-RCO-IQ3_XXS-mtp.gguf -c 196608 -ub 256` | kvqlean | 2026-11-07 | `final-recipes-nvidia.md:40`; `REKORDY.md:207`; `2026-11-26-nvq-5060ti.md` | gotowa (alternatywa) | +13,9% vs lean 43,40 |
| Qwen3.8-27B GSQ IQ3_XXS-mtp, lean | 43,40 T1, lean MTP n2 | brak pomiaru | 393 (fill 228 736) | 229 376 (peak 15 762) | LEAN z `-c 229376` | b12110lean 55933253f | 2026-11-07 | `final-recipes-nvidia.md:39`; `nv67c-summary.txt:182` | gotowa (alternatywa) | +38,1% vs plain 31,42 |
| LFM2.5-24B-A2B Q4_K_M | 139,48 T1, w całości w VRAM, bez drafta | brak pomiaru | brak pomiaru | 131 072 (KV q8_0, peak 15 820) | `llama-server -m LFM2.5-24B-A2B-Q4_K_M.gguf -ngl 999 -fa on -ctk q8_0 -ctv q8_0 -c 131072 -ub 512 --jinja` | b12110 | 2026-11-07 | `final-recipes-nvidia.md:41` | brak pełnego stosu (bez spekulacji; KV q8_0) | – |

### RTX 4060 Ti

16 GB, 288 GB/s ([[rtx-4060-ti]]), host 150/165 W.

| model | czat t/s (full stack, warunki) | kopia/kod t/s | prefill t/s (długość) | kontekst | komenda startu | commit/build | data | źródło | status | vs poprzednia / vs llama.cpp+spec |
|---|---|---|---|---|---|---|---|---|---|---|
| **Inkling 2 Mini GSQ-RCO IQ3_S bez cenzury (topka)** | **71,91 / 69,65** wall, DSpark n2 + ablacja, Threadripper 2950X | copy 86,5 / edit 81,2 | 627,4 (32k ub 128) / 813,6 (ub 256) | **262 144** (igła 5/5; 283 648 OOM ze spekulacją) | `llama-server -m Inkling-2-Mini-GSQ-RCO-IQ3_S.gguf -ngl 99 -fit off -fa on -ctk q4_0 -ctv q4_0 -c 262144 -ub 128 -b 128 -np 1 --jinja --ablate-lora Inkling-2-Mini-Uncensored-LoRA.gguf -md dspark-Inkling-2-Mini-Q8_0.gguf -ngld 99 --spec-type draft-dspark --spec-draft-n-max 2 --spec-draft-p-min 0 -ctkd q4_0 -ctvd q4_0` | b12811 + k207-ablate f7040f25e | 2026-11-28 | `qwen-opt/cloud/nvq3/results/TOPKI-NV-2026-11-28.md` | gotowa | vs LoRA na tym samym hoście 49,09 / 50,13 (+46% / +39%) |
| **Inkling 2 Mini IQ3_S + LoRA bez cenzury (topka)** | **48,58 / 48,99** wall T=0 / T=0,7, DSpark Q8_0 n2, ub 128, Threadripper 2950X, 150/165 W; odmowy 0/5 | brak pomiaru | 497 (32k, ub 128); 232 (269k w 1 159 s) | 283 648 (igły 5/5 przy 95%, peak 15 955) | INK z `-c 283648 --lora Inkling-2-Mini-Uncensored-LoRA.gguf` | b12811 | 2026-11-27 | `final-recipes-nvidia.md:36`; `2026-11-27-k204-enigma-16gb-inkling.md:23-30` | produkcja (Linux) | +103% vs poprzednia produkcja Qwen GSQ 23,94 (ten sam host); `--ablate-lora` niezmierzone → do kolejki |
| Qwen3.8-27B GSQ IQ3_XXS-mtp, lean | 36,30 T1, lean MTP n2 | brak pomiaru | 261 (fill 228 736) | 229 376 (peak 15 736) | LEAN z `-c 229376` | b12110lean 55933253f | 2026-11-07 | `final-recipes-nvidia.md:39`; `nv67c-summary.txt:105` | gotowa (alternatywa) | +51% vs plain 24,02 |
| Qwen3.8-27B UD-IQ4_XS | 50,8 czat T=1, T' (cuda-topka2 + COUPLED) | 188,6 (mvs) | brak pomiaru | 32 768 | brak pełnej komendy | cuda-topka2 2a261101b | 2026-10-20 | `REKORDY.md:137` | brak pełnego stosu (32k) | +31,9% vs U1 |
| LFM2.5 QAD-Q4_0 | 149,4 spec_sweep T=1, GPU verify | brak pomiaru | brak pomiaru | brak w notatce | brak pełnej komendy | cuda-topka2 | 2026-10-20 | `REKORDY.md:119` | brak pełnego stosu | +30,6% vs U0 114,4 |

### RTX 4070 Ti

12 GB.

| model | czat t/s (full stack, warunki) | kopia/kod t/s | prefill t/s (długość) | kontekst | komenda startu | commit/build | data | źródło | status | vs poprzednia / vs llama.cpp+spec |
|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3.8-27B UD-Q2_K_XL | 93,3 czat T=1 (T, cuda-topka2); T' +6,81% | 295,0 (mvs) | brak pomiaru | 36 864 (KV q4_0) | brak pełnej komendy | cuda-topka2 | 2026-10-20 | `REKORDY.md:138` | brak pełnego stosu (36k) | +42% vs U1 65,5 (upstream MTP) |

### RTX 5070

12 GB, Steam 6,15% (#1) ([[inne-karty-nvidia]]).

| model | czat t/s (full stack, warunki) | kopia/kod t/s | prefill t/s (długość) | kontekst | komenda startu | commit/build | data | źródło | status | vs poprzednia / vs llama.cpp+spec |
|---|---|---|---|---|---|---|---|---|---|---|
| **Inkling 2 Mini GSQ-RCO IQ2_S bez cenzury (topka)** | **130,97 / 127,42** wall, DSpark n2 + ablacja, Ryzen 9 7900X | copy 162,7 / edit 155,3 | 971,4 (32k ub 128) / 1259,6 (ub 256) | **155 648** (igła 5/5; 172 032 startuje, igła nie) | `llama-server -m Inkling-2-Mini-GSQ-RCO-IQ2_S.gguf -ngl 99 -fit off -fa on -ctk q4_0 -ctv q4_0 -c 155648 -ub 128 -b 128 -np 1 --jinja --ablate-lora Inkling-2-Mini-Uncensored-LoRA.gguf -md dspark-Inkling-2-Mini-Q8_0.gguf -ngld 99 --spec-type draft-dspark --spec-draft-n-max 2 --spec-draft-p-min 0 -ctkd q4_0 -ctvd q4_0` | b12811 + k207-ablate f7040f25e | 2026-11-28 | `qwen-opt/cloud/nvq3/results/TOPKI-NV-2026-11-28.md` | gotowa | Bonsai PTQ1_0 prism MTP n2 137,50 / 131,41 przy 208 896, ale bez igły i kopii |
| – | brak pomiaru (host 175/250 W odrzucony w K-118) | – | – | – | – | – | 2026-11-19 | `2026-11-19-k118-nvidia-pelna-moc.md` | brak pełnego stosu | do kolejki |

### RTX 4070

12 GB, host 200 W.

| model | czat t/s (full stack, warunki) | kopia/kod t/s | prefill t/s (długość) | kontekst | komenda startu | commit/build | data | źródło | status | vs poprzednia / vs llama.cpp+spec |
|---|---|---|---|---|---|---|---|---|---|---|
| **Bonsai 2 27B PTQ1_0-mtp-lean (topka)** | **94,73** T1, prism MTP n2 ubd 64 | brak pomiaru | 504 (fill 208 256) | 208 896 (peak 11 163) | `llama-server -m Ternary-Bonsai-2-27B-PTQ1_0-mtp-lean.gguf -ngl 999 -fa on -ctk q4_0 -ctv q4_0 -c 208896 -ub 256 --jinja --spec-type draft-mtp --spec-draft-n-max 2 --spec-draft-n-ubatch 64` | prism-b12128 d7b2896 | 2026-11-07 | `final-recipes-nvidia.md:50`; `nv67c-summary.txt:143` | gotowa | +91,6% vs produkcja 49,43 |
| Bonsai 2 27B Q2_0 | 49,43 T1 (przy 65 536), bez spekulacji | brak pomiaru | 477 (fill 195 968) | 196 608 (fill PASS) | `llama-server -m Ternary-Bonsai-2-27B-Q2_0.gguf -ngl 999 -fa on -ctk q4_0 -ctv q4_0 -c 196608 -ub 256 --jinja` | upstream (b12110 w pomiarze, pin b11856 w aplikacji) | 2026-11-07 | `final-recipes-nvidia.md:49`; `nv67c-summary.txt:127` | produkcja (brak pełnego stosu: bez spekulacji) | – |
| LFM2.5-24B-A2B UD-IQ3_XXS | 179,32 T1, w całości w VRAM | brak pomiaru | 2 602 (fill 130 432) | 131 072 (KV q8_0, peak 10 525) | `llama-server -m LFM2.5-24B-A2B-UD-IQ3_XXS.gguf -ngl 999 -fa on -ctk q8_0 -ctv q8_0 -c 131072 -ub 512 --jinja` | b12110 | 2026-11-07 | `final-recipes-nvidia.md:51`; `nv67c-summary.txt:132` | brak pełnego stosu (bez spekulacji) | – |
| Underdog Saluki 27B IQ2-mix | 44,35 T1 bez MTP (z MTP n1 39,8, inny host) | brak pomiaru | 554 (fill 150 912) | 151 552 (peak 11 201) | `llama-server -m Saluki-27B-IQ2-mix.gguf -ngl 999 -fa on -ctk q4_0 -ctv q4_0 -c 151552 -ub 256 --jinja` | b11856 | 2026-11-07 | `REKORDY.md:200`; `nv67c-summary.txt:139` | brak pełnego stosu | – |
| Inkling 2 Mini IQ2_S / IQ3_S | brak pomiaru | – | – | – | – | – | – | – | brak pełnego stosu | do kolejki |

### RTX 3060

12 GB, 360 GB/s (`karty.json`), host 140/170 W.

| model | czat t/s (full stack, warunki) | kopia/kod t/s | prefill t/s (długość) | kontekst | komenda startu | commit/build | data | źródło | status | vs poprzednia / vs llama.cpp+spec |
|---|---|---|---|---|---|---|---|---|---|---|
| **Inkling 2 Mini GSQ-RCO IQ2_S bez cenzury (topka)** | **59,57 / 60,97** wall, DSpark n2 + ablacja, ub 64, Xeon E5-2680 v3 | copy 78,2 / edit 68,6 | 407,7 (32k ub 128) / 507,3 (ub 256) | **188 416** (igła 5/5) | `llama-server -m Inkling-2-Mini-GSQ-RCO-IQ2_S.gguf -ngl 99 -fit off -fa on -ctk q4_0 -ctv q4_0 -c 188416 -ub 64 -b 64 -np 1 --jinja --ablate-lora Inkling-2-Mini-Uncensored-LoRA.gguf -md dspark-Inkling-2-Mini-Q8_0.gguf -ngld 99 --spec-type draft-dspark --spec-draft-n-max 2 --spec-draft-p-min 0 -ctkd q4_0 -ctvd q4_0` | b12811 + k207-ablate f7040f25e | 2026-11-28 | `qwen-opt/cloud/nvq3/results/TOPKI-NV-2026-11-28.md` | gotowa | bez spekulacji 60,6 (host Haswell ogranicza; Bonsai prism 58,31) |
| **Bonsai 2 27B PTQ1_0-mtp-lean (topka przy pełnym ctx)** | **58,31** T1, prism MTP n2 | brak pomiaru | brak pomiaru | 204 800 (peak 11 015; n1 maks. 229 376) | jak 4070, `-c 204800` | prism-b12128 d7b2896 | 2026-11-07 | `final-recipes-nvidia.md:50`; `REKORDY.md:210` | gotowa | +80,9% vs produkcja 32,23 |
| Bonsai 2 27B Q2_0 | 32,23 T1 (przy 65 536), bez spekulacji | brak pomiaru | 273 (fill 195 968) | 196 608 | jak 4070 Q2_0, `-c 196608` | upstream b12110 / pin b11856 | 2026-11-07 | `final-recipes-nvidia.md:49`; `nv67c-summary.txt:34` | produkcja (brak pełnego stosu: bez spekulacji) | – |
| Inkling 2 Mini IQ2_S (z cenzurą) | 59,5 / 53,4 wall + DSpark (bez: 51,8 / 54,3), Threadripper PRO 3945WX 170 W | brak pomiaru | brak pomiaru | 16 384 (IQ3_S + DSpark tylko 8 192: 60,3 / 55,4) | brak pełnej komendy | b12811 | 2026-11-27 | `2026-11-27-nvq5.md:18-19` | brak pełnego stosu (16k, z cenzurą) | +78% vs Bonsai Q2_0 33,4 (64k) |
| LFM2.5-24B-A2B UD-IQ3_XXS | 102,47 T1, w całości w VRAM | brak pomiaru | brak pomiaru | 131 072 (KV q8_0, peak 10 463) | jak 4070 LFM | b12110 | 2026-11-07 | `final-recipes-nvidia.md:51` | brak pełnego stosu (bez spekulacji) | – |
| Qwen3.8-27B UD-Q2_K_XL | 38,6 czat T=1 (T', draft n 3) | 153,1 (mvs) | brak pomiaru | 36 864 | brak pełnej komendy | cuda-topka2 | 2026-10-20 | `REKORDY.md:135` | brak pełnego stosu (36k) | – |
| Qwen3.8-27B GSQ IQ3_XXS-mtp | 34,0 / 31,8 T=0 / T=1, fork MTP n2, 144 W | brak pomiaru | 484 (~11k) | 8 192 | FORK z `--spec-draft-n-max 2 -c 8192` | kvqlean | 2026-11-19 | `2026-11-19-k118-nvidia-pelna-moc.md:32` | brak pełnego stosu (8k) | – |

### RTX 2080 Ti

11 GB, sm_75, host 250 W. Wydany fork CUDA nie ma kodu sm_75 i pada (`no kernel image`), prism tak ([[google-colab]], K-069).

| model | czat t/s (full stack, warunki) | kopia/kod t/s | prefill t/s (długość) | kontekst | komenda startu | commit/build | data | źródło | status | vs poprzednia / vs llama.cpp+spec |
|---|---|---|---|---|---|---|---|---|---|---|
| **Qwen3.5-9B Q6_K MTP n2 (topka)** | **92,27 / 89,69** wall, Xeon E5-2680 v4 | 104,7 | 1378,4 (32k, ub 128) | **204 800** (igła 5/5) | `llama-server -m Qwen3.5-9B-Q6_K-mtp.gguf -ngl 99 -fit off -fa on -ctk q4_0 -ctv q4_0 -c 204800 -ub 128 -b 128 -np 1 --jinja --spec-type draft-mtp --spec-draft-n-max 2 --spec-draft-p-min 0` | b12811 + k207-ablate (sm_75) | 2026-11-28 | `qwen-opt/cloud/nvq3/results/TOPKI-NV-2026-11-28.md` | gotowa | vs Bonsai prism 77,96 (+18%); Inkling IQ2_S 71,2 przy 49 152 |
| **Bonsai 2 27B PTQ1_0-mtp-lean (topka)** | **77,96** T1, prism MTP n2, ub 512 | brak pomiaru | brak pomiaru | 155 648 (peak 10 151; n1 maks. 196 608 PASS) | jak 4070, `-c 155648 -ub 512` | prism-b12128 d7b2896 | 2026-11-07 | `final-recipes-nvidia.md:58`; `REKORDY.md:211` | gotowa | +97% vs produkcja 39,57 |
| Bonsai 2 27B Q2_0 | 39,57 T1, bez spekulacji | brak pomiaru | 374 (fill 130 432) | 131 072 (peak 10 243) | jak 4070 Q2_0, `-c 131072` | b11856 (min. b11555) | 2026-11-07 | `final-recipes-nvidia.md:57`; `nv67c-summary.txt:22` | produkcja (brak pełnego stosu: bez spekulacji) | – |

### RTX 3080

10 GB, host 260/320 W.

| model | czat t/s (full stack, warunki) | kopia/kod t/s | prefill t/s (długość) | kontekst | komenda startu | commit/build | data | źródło | status | vs poprzednia / vs llama.cpp+spec |
|---|---|---|---|---|---|---|---|---|---|---|
| **Qwen3.5-9B Q6_K MTP n2 + ngram (topka)** | **134,11 / 132,28** wall, i7-4770K | 794,8 | 2665,1 (32k, ub 128) | **114 688** (igła 5/5) | `llama-server -m Qwen3.5-9B-Q6_K-mtp.gguf -ngl 99 -fit off -fa on -ctk q4_0 -ctv q4_0 -c 114688 -ub 128 -b 128 -np 1 --jinja --spec-type draft-mtp,ngram-mod --spec-draft-n-max 2 --spec-draft-p-min 0 --spec-ngram-mod-n-min 48 --spec-ngram-mod-n-max 64` | b12811 + k207-ablate f7040f25e | 2026-11-28 | `qwen-opt/cloud/nvq3/results/TOPKI-NV-2026-11-28.md` | gotowa | vs produkcja bez spekulacji 85,20 (+57%); Inkling IQ2_S 101,8 tylko przy 49 152 |
| Qwen3.5-9B Q6_K | 85,20 T1, bez spekulacji | brak pomiaru | 2 048 (fill 191 872) | 192 512 (peak 9 345) | `llama-server -m Qwen3.5-9B-Q6_K.gguf -ngl 999 -fa on -ctk q4_0 -ctv q4_0 -c 192512 -ub 512 --jinja` | b11856 | 2026-11-07 | `final-recipes-nvidia.md:64`; `nv67c-summary.txt:62` | produkcja (brak pełnego stosu: bez spekulacji) | – |
| Qwen3.8-27B UD-IQ2_XXS + przeszczep MTP | 74,5 czat T=1 (T', COUPLED, draft n 2) | 271,8 (mvs) | brak pomiaru | 32 768 | brak pełnej komendy | cuda-topka2 | 2026-10-20 | `REKORDY.md:134` | brak pełnego stosu (32k) | +11,0% vs T |
| LFM2.5-24B-A2B Q4_K_M | 40,83 T1, `--n-cpu-moe 20` | – | – | 131 072 (KV q8_0) | `llama-server -m LFM2.5-24B-A2B-Q4_K_M.gguf -ngl 999 -fa on -ctk q8_0 -ctv q8_0 -c 131072 -ub 512 --n-cpu-moe 20 --jinja` | b12110 | 2026-11-07 | `final-recipes-nvidia.md:65` | brak pełnego stosu | – |

### RTX 3070

8 GB, host 220 W.

| model | czat t/s (full stack, warunki) | kopia/kod t/s | prefill t/s (długość) | kontekst | komenda startu | commit/build | data | źródło | status | vs poprzednia / vs llama.cpp+spec |
|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3.5-9B Q4_K_M | 66,90 T1, bez spekulacji | brak pomiaru | 1 359 (fill 150 912) | 151 552 (peak 7 251) | `llama-server -m Qwen3.5-9B-Q4_K_M.gguf -ngl 999 -fa on -ctk q4_0 -ctv q4_0 -c 151552 -ub 512 --jinja` | b11856 | 2026-11-07 | `final-recipes-nvidia.md:71`; `nv67c-summary.txt:48` | produkcja (brak pełnego stosu: bez spekulacji) | b12110 −8% |
| LFM2.5-24B-A2B Q4_K_M | 8,92 T1, `--n-cpu-moe 26` | – | – | 131 072 | jak 3080 z `--n-cpu-moe 26` | b12110 | 2026-11-07 | `final-recipes-nvidia.md:72` | brak pełnego stosu | – |

## Karty centrów danych i chmury

### L4

24 GB, 72 W. Colab ([[google-colab]]).

| model | czat t/s (full stack, warunki) | kopia/kod t/s | prefill t/s (długość) | kontekst | komenda startu | commit/build | data | źródło | status | vs poprzednia / vs llama.cpp+spec |
|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3.8-27B GSQ IQ3_XXS-mtp | 37,50 dekod T=0, 128 tok. (1,7k); 29,98 (94k); 25,03 (199k); fork MTP n2 + lookup W16 | brak pomiaru (`--spec-default` na upstream: kopia 133,07 przy 16k) | 515 (1,7k); 354 (94k); 171 (199k) | 204 800 (15,7 GB, nie maks. dla 24 GB) | FORK z `--spec-draft-n-max 2 -c 204800 -ub 256 -np 1` | `enigma-cuda-fork` z wydania 2026-11-07 | 2026-11-24 | `research/colab-kolejka-2026-11-24.md:111,157-159` | brak pełnego stosu (kontekst niemaksymalny) | upstream b12110 MTP n3 przy 32k: 31,24 |

### T4

16 GB, sm_75, 70 W. Colab.

| model | czat t/s (full stack, warunki) | kopia/kod t/s | prefill t/s (długość) | kontekst | komenda startu | commit/build | data | źródło | status | vs poprzednia / vs llama.cpp+spec |
|---|---|---|---|---|---|---|---|---|---|---|
| model z testu K-069 (`m.gguf`, z notatki nie wynika który) | tg128 9,14 (`llama-bench`, bez spekulacji); fork: crash `no kernel image` | – | pp512 302,3 | 4 096 | `llama-bench -m m.gguf -ngl 999 -fa 1 -ctk q4_0 -ctv q4_0 -p 512 -n 128 -r 3` | b12110 (PTX) | 2026-11-24 | `research/colab-kolejka-2026-11-24.md:41` | brak pełnego stosu | – |

### A40

48 GB. RunPod, tylko pilot MTP.

| model | czat t/s (full stack, warunki) | kopia/kod t/s | prefill t/s (długość) | kontekst | komenda startu | commit/build | data | źródło | status | vs poprzednia / vs llama.cpp+spec |
|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3.8-27B UD-Q4_K_XL (głowica MTP oryginalna) | 78,9 / 78,7 spec_sweep, MTP n4 (ABBA ramię A) | – | – | brak w notatce | brak | gałąź `mtp-train` | 2026-10-16 | `testy/2026-10-16-mtp-pl-pilot.md:15` | brak pełnego stosu | douczona głowica 78,3 / 78,5 (bez zysku) |

### A100

80 GB SXM, 2039 GB/s (`karty.json`). Brak pomiaru: są tylko sufity `ceiling.py` ([[skill-io-sufity]]).

| model | czat t/s (full stack, warunki) | kopia/kod t/s | prefill t/s (długość) | kontekst | komenda startu | commit/build | data | źródło | status | vs poprzednia / vs llama.cpp+spec |
|---|---|---|---|---|---|---|---|---|---|---|
| – | brak pomiaru | – | – | – | – | – | – | [[skill-io-sufity]] | brak pełnego stosu | – |

### H100

80 GB SXM, 3350 GB/s (`karty.json`). Brak naszego pomiaru. Karty centrów danych mają sens przy współbieżności, nie c1 (`skill-io-sufity.md:118`).

| model | czat t/s (full stack, warunki) | kopia/kod t/s | prefill t/s (długość) | kontekst | komenda startu | commit/build | data | źródło | status | vs poprzednia / vs llama.cpp+spec |
|---|---|---|---|---|---|---|---|---|---|---|
| – | brak pomiaru | – | – | – | – | – | – | [[skill-io-sufity]] | brak pełnego stosu | – |

## Inne platformy

### Arc B580

12 GB, Xe2. Brak podaży godzinowej z rootem ([[arc-b580-i-mac]]).

| model | czat t/s (full stack, warunki) | kopia/kod t/s | prefill t/s (długość) | kontekst | komenda startu | commit/build | data | źródło | status | vs poprzednia / vs llama.cpp+spec |
|---|---|---|---|---|---|---|---|---|---|---|
| – | brak pomiaru | – | – | – | – | – | – | [[arc-b580-i-mac]] | brak pełnego stosu | – |

### Apple Mac (M4)

Mac mini M4 16 GB. Scaleway €0,22/h, minimum 24 h ([[arc-b580-i-mac]]).

| model | czat t/s (full stack, warunki) | kopia/kod t/s | prefill t/s (długość) | kontekst | komenda startu | commit/build | data | źródło | status | vs poprzednia / vs llama.cpp+spec |
|---|---|---|---|---|---|---|---|---|---|---|
| – | brak pomiaru (cudze: Gyro-S na Mac mini M4 32 GB 9,1 t/s, `product/research/57b-strata-qwen38-flash.md:84`) | – | – | – | – | pin b11856 (`upstream-macos-arm64-metal`) | – | `app/engine/data/engines.json` | brak pełnego stosu | – |

### Google TPU

| model | czat t/s (full stack, warunki) | kopia/kod t/s | prefill t/s (długość) | kontekst | komenda startu | commit/build | data | źródło | status | vs poprzednia / vs llama.cpp+spec |
|---|---|---|---|---|---|---|---|---|---|---|
| – | brak pomiaru (tylko zwiad TorchTPU) | – | – | – | – | – | – | `product/research/39e-torchtpu.md` | brak pełnego stosu | – |

## Pomiary do zrobienia
- K-212 · Qwen3.8-27B UD-Q4_K_XL na XTX: topka na silniku k047 i wall.py zamiast spec_sweep
- K-213 · Qwen3.8-27B UD-Q4_K_XL na XTX: pełny kontekst 262 144 z KV FA q4_0 bez kopii (K-022, −977 MiB)
- K-214 · Qwen3.8-27B Uncensored na XTX: kopia/kod i prefill na obecnej topce k047
- K-215 · Qwen3.8-27B Uncensored na XTX: LocalMaxxing reasoning-v1 z drafterem (porównanie z Inklingiem 157,4)
- K-216 · Inkling AD-Q4_K (Maya) na XTX: wall.py T=0,7 i prefill 128k na bin-k207p przy 557 056
- K-217 · Inkling IQ3_S 1M (Maya) na XTX: kopia/kod (K-147 bench) i prefill 128k/512k
- K-218 · Bonsai 2.5 na XTX: wall.py na `bonsai.sh` dokładnie i prefill topka-k157
- K-219 · Radeon AI PRO R9700 (Hostkey): pierwsza topka RDNA4, Qwen3.8-27B i Inkling 2 Mini
- K-220 · RX 9070 XT: topka po zakupie karty
- K-221 · Strix Halo i MI300X: sanity-check stosu HIP (bez topki produkcyjnej)
- K-222 · XTX: modele bez pliku na dysku (LFM2.5, Flint, Qwen3.6-35B-A3B, Gemma 4, Nemotron, Swift, Qwen3.5-9B)
- K-223 · RTX 5080: topka Inklinga (IQ3_S + `--ablate-lora` + DSpark n2, pełny kontekst)
- K-224 · RTX 4060 Ti: `--ablate-lora` zamiast LoRA przy 283 648
- K-225 · RTX 5060 Ti: prefill, kopia i głębia topki z `--ablate-lora`
- K-226 · RTX 3090: Inkling 2 Mini z pełnym stosem (DSpark + ablacja, pełny kontekst) vs topka Qwena
- K-227 · RTX 4090: Inkling 2 Mini z pełnym stosem
- K-228 · RTX 5090: Inkling 2 Mini z pełnym stosem + prefill fork
- K-229 · RTX 3060: Inkling IQ2_S + DSpark + ablacja przy maksymalnym kontekście
- K-230 · RTX 4070 i RTX 5070: topka 12 GB (Inkling IQ2_S + DSpark vs Bonsai prism)
- K-231 · RTX 4080 SUPER: pełny kontekst i Inkling
- K-232 · RTX 3080 / 3070 / 2080 Ti: spekulacja dla kart 8–11 GB
- K-233 · L4 (Colab): fork przy maksymalnym kontekście
- K-234 · Apple Mac mini M4: pierwszy pomiar (Metal, pin b11856)

## Powiązane
- [[REKORDY]]
- [[topki]]
- [[final-recipes-nvidia]]
- [[rodzaje-modeli]]
- [[lekcja-mierz-z-drafterem]]
