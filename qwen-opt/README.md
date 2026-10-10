# qwen-opt — Qwen3.8-27B na RX 7900 XTX: 59 → 92 t/s przy 200k kontekstu

Wyniki i diagnoza: [`NOTES.md`](NOTES.md). Podsumowanie: [`../benchmarks/2026-10-09-rx7900xtx-qwen38-27b.md`](../benchmarks/2026-10-09-rx7900xtx-qwen38-27b.md).

## Zawartość

| Plik | Co |
|---|---|
| `patches/llama.cpp-amd-opt/*.patch` | nasze zmiany w llama.cpp (na upstream `e60eff95f`): kernele HIP mmvq dla 2–8 kolumn, cache q8_1, `--spec-draft-vocab` |
| `run-llm.sh` | start serwera: `run-llm.sh [qwen\|saluki] [mtp\|dflash\|none] [vulkan\|rocm]` |
| `draft_vocab_qwen38.txt` | ranking tokenów Qwen3.8 (EN+PL+kod) dla `--spec-draft-vocab` |
| `serve_bench.py` | pomiar end-to-end przez llama-server (`--lang en\|pl\|all`) |
| `quick_quality.py` | 10 krótkich pytań EN/PL do kontroli jakości |
| `build_draft_vocab.py` | odtwarza `draft_vocab_qwen38.txt` |
| `greedy_check.sh` | porównanie wyjść greedy dwóch buildów |
| `mmvq-bench/` | mikrobenchmark kerneli „na zimno" (`mmvq_bench.cpp`), bitowe porównanie (`mm_dump.cpp`), pętla eksperymentów (`exp.sh`), wyniki (`results/`) |
| `prof_serve.sh`, `trace_breakdown.py`, `kernel_bw.py` | profilowanie rocprofv3 |
| `e2e_exp.sh` | wariant makr → przebudowa → pomiar DFlash i MTP |
| `results.jsonl` | wszystkie pomiary end-to-end z 9 października |

Skrypty zakładają układ katalogów z maszyny: `~/qwen-opt`, `~/llama-master`, `~/llama-opt`, `~/llama-opt-vk`, `~/vk`, `~/models`.

## Odtworzenie od zera (Ubuntu 24.04, ROCm 10.0 w `/opt/rocm/core-10.0`, bez sudo)

```bash
# 1. llama.cpp z łatkami
git clone https://github.com/ggml-org/llama.cpp ~/llama-master && cd ~/llama-master
git checkout -b amd-opt e60eff95f
git am ~/KERNEL/qwen-opt/patches/llama.cpp-amd-opt/*.patch

# 2. build ROCm (gfx1100)
export PATH=/opt/rocm/core-10.0/bin:$PATH
HIPCXX=/opt/rocm/core-10.0/lib/llvm/bin/clang++ HIP_PATH=/opt/rocm/core-10.0 \
  cmake -B build-hip -DGGML_HIP=ON -DGPU_TARGETS=gfx1100 -DCMAKE_BUILD_TYPE=Release -DGGML_NATIVE=ON \
        -DLLAMA_CURL=OFF -DCMAKE_PREFIX_PATH=/opt/rocm/core-10.0
cmake --build build-hip -j16 && cmake --install build-hip --prefix ~/llama-opt
# biblioteki ROCm nie są w ld.so.conf: LD_LIBRARY_PATH=~/llama-opt/lib:/opt/rocm/core-10.0/lib

# 3. Vulkan w przestrzeni użytkownika: Mesa RADV z .deb + LunarG SDK
mkdir -p ~/vk/debs ~/vk/root ~/vk/icd && cd ~/vk/debs
apt-get download mesa-vulkan-drivers libvulkan1 libllvm20 libxcb-dri3-0 libwayland-client0 libx11-xcb1 \
  libxcb-present0 libxcb-xfixes0 libxcb-sync1 libxcb-randr0 libxcb-shm0 libxshmfence1
for d in *.deb; do dpkg -x $d ../root; done
cd ~/vk && curl -L -o vulkan_sdk.tar.xz https://sdk.lunarg.com/sdk/download/latest/linux/vulkan_sdk.tar.xz && tar xf vulkan_sdk.tar.xz
sed "s#\"libvulkan_radeon.so\"#\"$HOME/vk/root/usr/lib/x86_64-linux-gnu/libvulkan_radeon.so\"#" \
  root/usr/share/vulkan/icd.d/radeon_icd.json > icd/radeon_icd.json

# 4. build Vulkan (wersja SDK: 1.4.363.0)
cd ~/llama-master && export VULKAN_SDK=$HOME/vk/1.4.363.0/x86_64
cmake -B build-vk -DGGML_VULKAN=ON -DGGML_NATIVE=ON -DCMAKE_BUILD_TYPE=Release -DLLAMA_CURL=OFF \
  -DVulkan_INCLUDE_DIR=$VULKAN_SDK/include -DVulkan_LIBRARY=$VULKAN_SDK/lib/VulkanLoader/lib/libvulkan.so \
  -DVulkan_GLSLC_EXECUTABLE=$VULKAN_SDK/bin/glslc -DVulkan_GLSLANG_VALIDATOR_EXECUTABLE=$VULKAN_SDK/bin/glslangValidator
cmake --build build-vk -j16 --target llama-server llama-bench
mkdir -p ~/llama-opt-vk/bin && cp -a build-vk/bin/llama-server build-vk/bin/llama-bench build-vk/bin/*.so* ~/llama-opt-vk/bin/
cp ~/vk/icd/radeon_icd.json ~/llama-opt-vk/

# 5. modele
uv tool install 'huggingface_hub[cli,hf_xet]'
hf download z-lab/Qwen3.8-27B-DFlash2-GGUF Qwen3.8-27B-DFlash2-Q4_K_M.gguf --local-dir ~/models/draft
hf download ConwayResearch/Underdog-Saluki-27B-1.0 Underdog-Saluki-27B-1.0-IQ2-mix.gguf --local-dir ~/models
cp ~/KERNEL/qwen-opt/draft_vocab_qwen38.txt ~/models/draft/
# ~/models/Qwen3.8-27B-UD-Q4_K_XL.gguf — główny model

# 6. start
mkdir -p ~/qwen-opt && cp -r ~/KERNEL/qwen-opt/* ~/qwen-opt/ && ~/qwen-opt/run-llm.sh
```

## Kontrola po buildzie

```bash
cd ~/llama-master && LD_LIBRARY_PATH=/opt/rocm/core-10.0/lib \
  build-hip/bin/test-backend-ops test -b ROCm0 -o 'MUL_MAT,MUL_MAT_VEC_FUSION'   # oczekiwane: wszystkie OK
cd ~/qwen-opt && python3 -m venv .venv && .venv/bin/python serve_bench.py --lang all --label check \
  --bin ~/llama-opt-vk/bin/llama-server --env LD_LIBRARY_PATH=$HOME/llama-opt-vk/bin:$HOME/vk/1.4.363.0/x86_64/lib/VulkanLoader/lib:$HOME/vk/root/usr/lib/x86_64-linux-gnu \
  --env VK_ICD_FILENAMES=$HOME/llama-opt-vk/radeon_icd.json -- -m ~/models/Qwen3.8-27B-UD-Q4_K_XL.gguf \
  -ngl 999 -fa on -ctk q4_0 -ctv q4_0 -c 204800 --spec-type draft-mtp --spec-draft-n-max 5 \
  --spec-draft-vocab ~/models/draft/draft_vocab_qwen38.txt --spec-draft-vocab-n 65536            # ~92 t/s
```
