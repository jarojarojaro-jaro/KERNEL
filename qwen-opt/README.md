# qwen-opt — Qwen3.8-27B na RX 7900 XTX (ROCm): 59 → 88 t/s przy 200k kontekstu

Wyniki, diagnoza i wyniki negatywne: [`NOTES.md`](NOTES.md). Research i plan dalszych prac: [`research/`](research/) (`research/v2/roadmap.md`).

Stan (2026-10-12, ROCm, ctx 204800, KV q4_0, MTP n=4 + słownik draftu 64k, limit mocy 285 W, 6 promptów PL/EN × 3 seedy, T=1):

| Model | t/s | ms/krok |
|---|---|---|
| Qwen3.8-27B UD-Q4_K_XL | 88.1 | 35.7 |
| Qwen3.8-27B-Uncensored Q4_K_M (orcarouter) | 90.4 | 33.8 |

Generowanie przy wypełnionym kontekście (Qwen, T=0): 1.7k 106.9 t/s, 29.5k 85.5 t/s, 94k 77.7 t/s. Prefill 750–910 t/s do 30k, 660 t/s przy 94k.

## Zawartość

| Plik | Co |
|---|---|
| `patches/llama.cpp-amd-opt/*.patch` | zmiany w llama.cpp (na upstream `e60eff95f`): kernele HIP mmvq 2–8 kolumn, cache q8_1, `--spec-draft-vocab`, kernel FA dla KV q4_0 (RDNA3), fuzje kerneli HIP (MMVQ+residual, prolog GDN, SSM_CONV+snapshoty, q8_1 w producentach, IMROPE/FWHT), draft MTP jednym grafem; łatki Vulkan (opcjonalny backend) |
| `run-llm.sh` | start serwera: `run-llm.sh [qwen\|uncensored\|saluki] [mtp\|dflash\|none] [rocm\|vulkan]` (domyślnie qwen, mtp, rocm); env: `CTX`, `PORT`, `HOST`, `EFFORT` (myślenie, domyślnie low), `DRAFT_N`, `VISION=1`, `EXTRA_ARGS` |
| `gpu-power.sh`, `gpu-powercap.service` | status/monitor mocy i temperatur; usługa systemd: limit 285 W + brak usypiania karty (inaczej model ląduje w RAM i działa ~4 t/s) |
| `gpu-keepawake/` | trzymanie karty wybudzonej bez roota (używane przez `run-llm.sh`) |
| `spec_sweep.sh`, `spec_sweep.py` | pomiar t/s i ms/krok na 6 promptach PL/EN (restart serwera per konfiguracja) |
| `long_ctx_bench.py`, `cache_bench.py` | prefill/decode przy 2k–100k kontekstu; scenariusze cache promptu |
| `mtp-train/` | douczanie głowicy MTP: ekstraktor stanów, lustro PyTorch, analiza akceptacji, plan fazy 2 |
| `tools/fusion/` | skrypty pomiarowe fuzji (A/B, rocprofv3, greedy) |
| `draft_vocab_qwen38.txt`, `build_draft_vocab.py` | ranking tokenów dla `--spec-draft-vocab` |
| `prof_serve.sh`, `trace_breakdown.py` | profil rocprofv3 pod obciążeniem serwera |
| `serve_bench.py`, `quick_quality.py`, `greedy_check.sh`, `mmvq-bench/` | starsze narzędzia pomiarowe (9 października) |

Skrypty zakładają układ katalogów: `~/qwen-opt`, `~/llama-master`, `~/llama-opt`, `~/models`.

## Odtworzenie od zera (Ubuntu 24.04, ROCm 10.0 w `/opt/rocm/core-10.0`, bez sudo)

```bash
# 1. llama.cpp z łatkami
git clone https://github.com/ggml-org/llama.cpp ~/llama-master && cd ~/llama-master
git checkout -b amd-opt e60eff95f
git am ~/KERNEL/qwen-opt/patches/llama.cpp-amd-opt/*.patch

# 2. build ROCm (gfx1100)
cmake -B build-hip -DGGML_HIP=ON -DGPU_TARGETS=gfx1100 -DCMAKE_BUILD_TYPE=Release -DLLAMA_CURL=OFF \
      -DGGML_HIP_GRAPHS=ON -DGGML_HIP_NO_VMM=ON -DCMAKE_PREFIX_PATH=/opt/rocm/core-10.0 \
      -DCMAKE_HIP_COMPILER=/opt/rocm/core-10.0/lib/llvm/bin/clang++
cmake --build build-hip -j8 && cmake --install build-hip --prefix ~/llama-opt
# biblioteki ROCm nie są w ld.so.conf: LD_LIBRARY_PATH=~/llama-opt/lib:/opt/rocm/core-10.0/lib

# 3. modele
uv tool install 'huggingface_hub[cli,hf_xet]'
# ~/models/Qwen3.8-27B-UD-Q4_K_XL.gguf — główny model (unsloth)
# ~/models/orca/Qwen3.8-27B-Uncensored-Q4_K_M.gguf — orcarouter (repo HF bramkowane; ten sam plik jest w rejestrze Ollama orcarouter/qwen3.8-27b-uncensored:q4_K_M)
hf download z-lab/Qwen3.8-27B-DFlash2-GGUF Qwen3.8-27B-DFlash2-Q4_K_M.gguf --local-dir ~/models/draft
cp ~/KERNEL/qwen-opt/draft_vocab_qwen38.txt ~/models/draft/

# 4. moc i usypianie karty (root, raz)
sudo cp ~/KERNEL/qwen-opt/gpu-powercap.service /etc/systemd/system/ && sudo systemctl enable --now gpu-powercap.service

# 5. start
mkdir -p ~/qwen-opt && cp -r ~/KERNEL/qwen-opt/* ~/qwen-opt/ && ~/qwen-opt/run-llm.sh
```

Backend Vulkan (opcjonalny, szybszy tylko przy krótkich promptach): Mesa RADV z .deb + LunarG SDK w `~/vk`, build `build-vk` z `-DGGML_VULKAN=ON`, binaria w `~/llama-opt-vk/bin`; szczegóły w historii tego pliku i w `NOTES.md`.

## Kontrola po buildzie

```bash
cd ~/llama-master && LD_LIBRARY_PATH=~/llama-opt/lib:/opt/rocm/core-10.0/lib \
  build-hip/bin/test-backend-ops -b ROCm0 -o 'MUL_MAT,FLASH_ATTN_EXT,GATED_DELTA_NET,SSM_CONV'   # wszystkie OK
cd ~/qwen-opt && python3 -m venv .venv && SEEDS=1,2,3 ./spec_sweep.sh "DRAFT_N=4"           # ~88 t/s, ~35.7 ms/krok
```
