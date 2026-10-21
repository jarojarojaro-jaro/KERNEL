---
base_model:
- Qwen/Qwen3.8-Flash-Next
base_model_relation: quantized
license: other
license_name: qwen-community-1.0
library_name: gguf
pipeline_tag: image-text-to-text
tags:
- gguf
- qwen3.8-flash-next
- qwen4exp
- experimental
- agentionai
---

<img src="gyro-header.png" alt="AgentionAI — Gyro 3.8 Flash Next" width="100%">

# Qwen3.8-Flash-Next Gyro — GGUF

**Qwen3.8-Flash-Next (125B MoE) on one GPU: 27.6 GiB for a 32 GB card, 35 GiB for 48 GB, 50 GiB for 64 GB.**

| Headline | Detail |
|---|---|
| **221 tok/s** | on one RTX 5090 (Gyro-S, fully VRAM-resident, Strata); 218 tok/s with the MTP draft in agentionai/llama.cpp |
| **98% of Q4 accuracy at half the memory** | MMLU-Pro: Gyro-M 80.0 vs 81.4 for our 67 GiB AP-Q4_K_XL, in 35 GiB |
| **30 / 30 LiveCodeBench problems** | Gyro-M, given room to reason (128k tokens); 90% at a 64k limit |
| **New: Gyro-L for 64 GB** | KLD 0.146 in 50.2 GiB: ahead of ggml-org IQ4_NL (0.200, 68.2 GiB) and AtomicChat Q4_K_M (0.228, 52.3 GiB) |
| **Updated Gyro-S, same size** | KLD 0.401, 0 loops in a 45-run loop stress test; ahead of ISTA IQ2_XS with 24% less memory |
| **0 loops in 10 long-reasoning runs** | Gyro-M; a well-known 2-bit quant looped 7 times and finished only 6 |
| **Updated Gyro-M, same size** | KLD 0.291: ahead of ISTA-DASLab IQ3_XXS (0.311) with 20% less memory and unsloth UD-Q2_K_XL (0.334) with 25% less; 0 loops in a 45-run loop stress test |

The best quality per GiB at every size we ship. Gyro-S fits a 32 GB card: 27.64 GiB of weights, 28.8 GiB at 64k
context, up to 128k context.

## Pick your file

| Your hardware | File | GPU memory (weights) |
|---|---|---:|
| 32 GB card (RTX 5090, R9700) | **`Qwen3.8-Flash-Next-Gyro-S-TQ1_0.gguf`** | 27.64 GiB |
| 48 GB (one card or 2×24), 64 GB unified memory | **`Qwen3.8-Flash-Next-Gyro-M-TQ2_0.gguf`** | 34.98 GiB |
| 16–24 GB card | Gyro-S with `--n-cpu-moe N`, or Strata's expert cache | |
| Strix Halo / unified memory, 64 GB+ | either | |
| 64 GB unified memory (Strix Halo): more quality | **`Qwen3.8-Flash-Next-Gyro-L-TQ3_0.gguf`** | 50.21 GiB |

Abliterated Gyro-S and Gyro-M: [agentionai/Qwen3.8-Flash-Next-Gyro-abliterated-Huihui-GGUF](https://huggingface.co/agentionai/Qwen3.8-Flash-Next-Gyro-abliterated-Huihui-GGUF).
The routed experts are stored in a rotated basis with our own rotor code (Agention Precision Rotor, APR). The
`TQ1_0` / `TQ2_0` / `TQ3_0` in the names is only a size class for the Hub: **stock llama.cpp cannot load these files.**

## Quality

KL divergence and top-1 agreement against the unsloth Q8_0 source, held-out corpus of 2026 technical writing and
code (`-c 2048`, 60 chunks). GPU memory = GPU-resident weights; the n-gram table stays on disk.

| File | GPU memory | KLD ↓ | top-1 ↑ |
|---|---:|---:|---:|
| **Gyro-S** (updated 2026-10-10) | **27.64 GiB** | **0.401** | **75.29%** |
| **Gyro-M** (updated 2026-10-11) | **34.98 GiB** | **0.291** | **78.75%** |
| **Gyro-L** (new 2026-10-12) | **50.21 GiB** | **0.146** | **83.87%** |
| ISTA-DASLab GSQ-RCO IQ2_XS | 36.52 GiB | 0.420 | 74.22% |
| ISTA-DASLab GSQ-RCO IQ3_XXS | 43.80 GiB | 0.311 | 77.68% |
| unsloth UD-Q2_K_XL | 46.63 GiB | 0.334 | 76.61% |
| AtomicChat AD-4.27bpw Q4_K_M | 52.26 GiB | 0.228 | 80.58% |
| ggml-org IQ4_NL | 68.21 GiB | 0.200 | 81.29% |
| Agention AP-Q4_K_XL (reference) | 67.38 GiB | 0.107 | 85.52% |

**Long reasoning without loops.** One-shot coding prompt (a voxel pagoda scene), 10 seeds: looping traces
**Gyro-M 0/10** (first release), ISTA IQ2_XS 7/10; updated Gyro-S 2/20 (20 seeds, `--min-p 0.05`; both runs still finished); updated Gyro-M 0/5 (5 seeds, `--min-p 0.05`).
Loop stress test (45 runs of prompts that provoke runaway generation, `--min-p 0.05`): updated Gyro-S 0 loops, updated Gyro-M 0 loops. MMLU-Pro: Gyro-M 80.0, Gyro-S 78.1 (both first release), AP-Q4_K_XL 81.4,
all within noise at our 70-question sample. LiveCodeBench v6 (30-problem subset, one seed): Gyro-M 90% at a 64k
token limit and 30/30 when its long answers get 128k; Gyro-S 67% at 64k, 83% at 128k (both first release; not re-run on the updates).

## Speed

Decode at batch size 1, tok/s:

| Hardware | Engine | Gyro-S decode | Gyro-S prefill | Gyro-M decode |
|---|---|---:|---:|---:|
| RTX 5090, 32 GB | llama.cpp fork main, CUDA | **113** (MTP: JSON 210, code 180, copy 218) | ~3,000 (pp2048) | |
| RTX 5090, 32 GB | Strata `rc1` (release candidate) | prose **140**, code 209, JSON 221 | 4,883 (16k prompt) | prose 114 |
| RTX A6000, 48 GB | llama.cpp fork main, CUDA | 57.4 | 740 (pp2048) | 52.3 |
| Radeon AI PRO R9700, 32 GB | llama.cpp fork, Vulkan | 57.8 (code with MTP: 70.6) | 1,246 (pp512) | |
| AMD Strix Halo | llama.cpp fork, Vulkan | 31.7 (MTP: code 50, JSON 55) | | 26.4 |

RTX 5090 rows: Ryzen 9 9950X host; decode tg128 or greedy content-type prompts with the MTP draft; llama.cpp fork main from 2026-10-04.

## Quick start

```bash
hf download agentionai/Qwen3.8-Flash-Next-Gyro-GGUF Qwen3.8-Flash-Next-Gyro-S-TQ1_0.gguf \
  mtp-Qwen3.8-Flash-Next-draft.gguf mmproj-F16.gguf --local-dir ~/models

# AMD (and Intel) GPUs
docker run --rm -it --device /dev/dri --group-add "$(getent group render | cut -d: -f3)" \
  -v ~/models:/models -p 8080:8080 agentionai/agention-llama:server \
  -m /models/Qwen3.8-Flash-Next-Gyro-S-TQ1_0.gguf -ngl 999 -fa on --jinja --ngram-on-disk \
  -c 65536 -ctk q8_0 -ctv q8_0 --temp 1.0 --top-p 0.95 --top-k 20 --min-p 0.05 \
  --mmproj /models/mmproj-F16.gguf
```

**Gyro-L:** use `Qwen3.8-Flash-Next-Gyro-L-TQ3_0.gguf` in place of the Gyro-S file (pull the image again first).

**NVIDIA:** replace `--device /dev/dri --group-add ...` with `--gpus all -e NVIDIA_DRIVER_CAPABILITIES=all`
(Vulkan), or build [agentionai/llama.cpp](https://gitlab.com/agentionai-group/llama.cpp) with `-DGGML_CUDA=ON` for full speed.

**Strata** (NVIDIA; release candidate):

[Strata](https://github.com/agentionai/Strata/tree/rc2) is the fastest way to run Gyro on an RTX 5090, and its expert
cache keeps the most-used experts on the GPU, which makes 24 GB cards practical. One script sets everything up:

```bash
git clone -b rc2 https://github.com/agentionai/Strata && cd Strata
tools/gyro_setup.sh --model S --backend cuda --cuda-arch 120   # RTX 50 series; 89 = RTX 40, 86 = RTX 30 / A6000
```

The script builds Strata against our llama.cpp fork, downloads the model, packs it, prepares the MTP draft head and
prints the command that starts the server: web chat at http://127.0.0.1:8080, OpenAI-compatible API at
`http://127.0.0.1:8080/v1`. Use `--model M` for Gyro-M. RTX 50-series cards need CUDA 13. AMD support is experimental.
Manual steps and more numbers: [docs/GYRO.md](https://github.com/agentionai/Strata/blob/rc2/docs/GYRO.md).

Measured with Strata (tok/s, prose / JSON / code): RTX 5090 **140 / 221 / 209**.

## Recommended settings

- Sampling: `--temp 1.0 --top-p 0.95 --top-k 20 --min-p 0.05` (Qwen's thinking settings plus min-p).
- Keep `--ngram-on-disk` (fast direct reader, Linux and Windows), with the model on fast NVMe. Older Windows builds: leave it out, and the table is read on demand (`--lazy-mode on`).
- MTP draft: `--spec-type draft-mtp -md mtp-Qwen3.8-Flash-Next-draft.gguf --spec-draft-n-max 6 --spec-draft-n-min 2 --spec-draft-mtp-vocab 32768`
  (adds ~3.75 GiB: on a 32 GB card, 24k context with the draft, 128k without, or the draft on a second GPU).
  The draft was updated on 2026-10-05 to upstream llama.cpp's tensor names (weights unchanged): it needs
  agentionai/llama.cpp main or the container from 2026-10-05 or later; older builds fail to load it, so update.
- Container images from before 2026-10-09 could answer HTTP 500 when several requests run at once with the MTP draft:
  pull the current `agentionai/agention-llama:server` from Docker Hub (on an older image, add `-e LLAMA_GRAPH_SLOTS=0`).
  The image is mirrored on Docker Hub while `ghcr.io/agentionai/agention-llama` is not being updated.
- CUDA builds from before 2026-10-04 could crash with several long prompts at once: update agentionai/llama.cpp (on an older build, `GGML_CUDA_TQ_MMQ=0` or `--parallel 1`).

## Changelog

- **2026-10-13: Gyro-L file updated** with an 8-bit n-gram table: same GPU memory (50.21 GiB), KLD 0.146 (held-out), 0.027 (code).
  The table stays on disk; the download is now 108 GB. Download the file again.
- **2026-10-12: Gyro-L added** (`Qwen3.8-Flash-Next-Gyro-L-TQ3_0.gguf`, 50.21 GiB GPU weights).
  Needs the `agentionai/agention-llama:server` container from 2026-10-12 or later, or a current build of
  [agentionai/llama.cpp](https://gitlab.com/agentionai-group/llama.cpp) main; older builds cannot load it. Tested on Strix Halo (Vulkan).
- **2026-10-11: Gyro-M updated.** Same file name, size, format and speed; better weights from an improved encode.
  KLD 0.291 (held-out), 0.066 (code); 0 loops in a 45-run loop stress test.
  Download the file again; the first release stays available as revision `ae0277db`.
- **2026-10-10: Gyro-S updated.** Same file name, size, format and speed; better weights from an improved encode.
  KLD 0.401 (held-out), 0.109 (code); 0 loops in a 45-run loop stress test.
  Download the file again; the first release stays available as revision `aba94138`.

## Status

Experimental: the format and kernels may still change, and the files will be re-published when they do. Runs on
[agentionai/llama.cpp](https://gitlab.com/agentionai-group/llama.cpp) (Vulkan, CUDA) and Strata; tested on Linux with
Strix Halo, R9700, RTX 5090, RTX A6000 and RTX 3090. Coming: Gyro Signal (shorter answers, no extra loops).
The weights come from our own encoder and calibration, which we are not publishing at this stage.

## Credits

Tensor format: trellis-coded quantization with Hadamard rotation, in the family of QTIP (Tseng et al., 2024). Encoder, trellis types and kernels: AgentionAI. Base model: Qwen/Qwen3.8-Flash-Next. Runtimes: llama.cpp, Strata.


### Support AgentionAI

These quants are released freely. If they save you VRAM or make Qwen more useful, you
can buy me a coffee or some GPU time and sponsor continued quantization and benchmarking on
[GitHub](https://github.com/sponsors/agentionai). AgentionAI is a one-person team and can use your help.
