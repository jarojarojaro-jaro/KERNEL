# topka-q70 (production on RX 7900 XTX since 2026-11-09)

Base: topka-q63 `c0576e3e8` (patches in `../topka-q63/`). Branch `topka-q70` = base + 3 commits:

| patch | commit | what |
|---|---|---|
| 0001 | 3152b0bfa | cachesave: upstream #30137 port (shared checkpoints, no zero-fill of state buffers) + `LLAMA_SERVER_CACHE_HUGE=1` (huge pages + buffer reuse for prompt-cache entries) |
| 0002 | 6f4ae4198 | cachesave compile fix (`common_checkpoint_update/load` take `common_state_data`) |
| 0003 | 3191b25f4 | fa-d256: RDNA3 FA D=256 prefill variants under `GGML_HIP_FA_D256_VAR` (cherry-pick of 32292cc0a; default 0 in code) |

Apply:

```sh
git checkout -b topka-q70 c0576e3e8
git am /path/to/qwen-opt/patches/topka-q70/*.patch
cmake --build build-hip -j
```

Env defaults are set by the launcher (`qwen-opt/run-topka.sh`), not in code:
- `GGML_HIP_FA_D256_VAR=83` for the qwen/uncensored profiles only (tuned for KV q4_0; f16 KV is -2.4%, so lfm/flint keep 0).
- `LLAMA_SERVER_CACHE_HUGE=1` for all profiles.
Override with `GGML_HIP_FA_D256_VAR=0` / `LLAMA_SERVER_CACHE_HUGE=0`; outputs are bit-identical either way.

Measured (final mode eco 2200, Uncensored Q4_K_M, KV q4_0, ctx 262144): 255k fill 466.3 -> 492.5 t/s (+5.6%),
agent thread-switch turn median 13 413 -> 12 029 ms (-10.3%), md5 identical. Deploy scripts: `qwen-opt/deploy-q70/`.
Wiki: `wiki/eksperymenty/2026-11-09-wdrozenie-topka-q70.md`.
