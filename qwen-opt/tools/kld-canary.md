# KLD canaries: does the KLD gate catch real damage?

Setup (the same as `~/wt/lfm3-prof/kld.sh`): LFM2.5-24B-A2B Q5_K_M, wikitext-2 test, `-c 16384 -b 16384 -ub 1 --chunks 3
-ngl 99 -fa on` (ubatch 1 = the decode kernels; 24573 scored tokens), reference `~/wt/lfm3-prof/ref.kld` = f16-KV logits.
Every run is `llama-perplexity --kl-divergence-base ref.kld --kl-divergence` from the installed build (`BIN`, default
`~/llama-opt/bin`). Gates compare a candidate log with a baseline log. Both logs must use the same reference.

## Gate (`kld_gate.py compare BASE.log CAND.log`)

Values parsed from the log: mean KLD ± SE, 99.9 % KLD, same top p ± SE, RMS Δp, PPL(Q)/PPL(base), PPL(base), number of chunks.

- **ERROR**: a log is incomplete, or PPL(base) or the chunk count differs between the two logs (different ref.kld or text).
- **IDENTICAL**: every number in the chunk table and in the three statistics sections is equal. Bitwise-equal
  numerics produce this; the gate's floor for them is 0.
- **PASS**, if all of these hold (k = 2, tail ratio 1.25):
  - `KLD_c - KLD_b <= k * sqrt(se_b² + se_c²)`
  - `top_c - top_b >= -k * sqrt(se_b² + se_c²)` (same top p, in %)
  - `KLD99.9_c <= 1.25 * KLD99.9_b`
- **FAIL**: any of the conditions above is false.

RMS Δp and the PPL ratio are printed but not gated. Exit codes: 0 PASS/IDENTICAL, 1 FAIL, 2 ERROR.

Thresholds, checked against the real logs in `~/wt/lfm3-prof`, with q8_0 vec as the baseline:

| candidate | dKLD (sd) | d same top (sd) | 99.9 % ratio | verdict |
|---|---|---|---|---|
| q8_0 kvq (accepted) | +0.000025 (+0.01) | +0.097 % (+0.40) | 1.029 | PASS |
| q8_0 vec, run 2 | 0 | 0 | 1.000 | IDENTICAL |
| q4_0 kvq | +0.084188 (+26.8) | -7.033 % (-24.8) | 1.679 | FAIL (all three) |

A 2 sd threshold leaves room for numerically different but equivalent kernels such as kvq. At this
sample size it is 0.005 KLD, about 11 % of the q8_0 floor. The SEs come from two separate runs, but both runs score
the same tokens. Their errors are positively correlated, so the true SE of the difference is smaller and the test is
conservative. As a result, a real bug that adds less than about 0.005 KLD passes. The canaries measure where that limit
lies. The 99.9 % quantile rests on about 25 tokens, which makes it noisy (kvq: x1.03). The 1.25 ratio flags tail-only
damage that the mean does not show. q4_0 reaches x1.68.

## Canaries (`kld_canary.sh list`)

Each canary is compared with `baseline`, which is the installed build with production q8_0 KV. `baseline` itself is
compared with `ANCHOR` (`kld_q8kvq.log`, the accepted incumbent). Expected outcomes:

- **PASS**: PASS or IDENTICAL is accepted.
- **IDENTICAL**: only IDENTICAL is accepted.
- **FAIL**: the gate must detect the damage.
- **PROBE**: the outcome is only reported. These canaries measure sensitivity and do not affect the exit code.

| variant | change | expected |
|---|---|---|
| baseline | `-ctk q8_0 -ctv q8_0` | PASS vs ANCHOR |
| baseline2 | the same command again | IDENTICAL (determinism) |
| ctl_vec | `GGML_HIP_KVQ_Q8=0` (old q8_0 vec kernel, known 0.044171) | PASS |
| kv_q4 | `-ctk q4_0 -ctv q4_0` (known 0.128359) | FAIL |
| kv_k8v4 / kv_k4v8 | `-ctk q8_0 -ctv q4_0` / `-ctk q4_0 -ctv q8_0` (vec kernel with f16 K/V fallback; FA_QUANTS has no mixed pairs) | FAIL, magnitude reported |
| moe_k3 | `--override-kv lfm2moe.expert_used_count=int:3` (GGUF: 4) | FAIL |
| eps_x100 | `--override-kv lfm2moe.attention.layer_norm_rms_epsilon=float:1e-3` (GGUF: 1e-5) | PROBE |
| rope_p1 / rope_p5 | `--rope-freq-base 10100000` / `10500000` (GGUF `lfm2moe.rope.freq_base` 1e7) | PROBE |
| wdown_p0.5 / p2 / p10 | `blk.10.ffn_down_exps.weight` (Q6_K, all 64 experts) x1.005 / x1.02 / x1.10 | PROBE / PROBE / FAIL |
| wattn_p0.5 / p2 / p10 | `blk.10.attn_output.weight` (Q5_K) x1.005 / x1.02 / x1.10 | PROBE / PROBE / FAIL |
| q4km | `llama-quantize --allow-requantize` Q5_K_M -> Q4_K_M | PROBE |
| q3km | the same, -> Q3_K_M | FAIL |

`kld_canary.sh` exits 1 if a FAIL canary passes or a PASS/IDENTICAL control does not. It exits 2 if a log is missing
or broken.

Model facts (GGUFReader): arch `lfm2moe`, 40 blocks. Attention is in blocks 2, 6, …, 38 (`head_count_kv` array). There
are 64 experts, 4 used per token, sigmoid gating, and no `output.weight` (tied to `token_embd`, Q6_K).

## Weight damage (`perturb_gguf.py SRC DST --tensor REGEX --delta D [--verify]`)

The tool copies the GGUF and multiplies the fp16 block scales of the matched tensors by (1+D). Only these fields change:

| type | block size | scale fields |
|---|---|---|
| Q8_0 | 34 B | `d` at offset 0 |
| Q4_K | 144 B | `d` at 0, `dmin` at 2 |
| Q5_K | 176 B | `d` at 0, `dmin` at 2 |
| Q6_K | 210 B | `d` at 208 |

Scaling `dmin` as well keeps `x = d*sc*q - dmin*m` exactly proportional. `--verify` checks the following:

- every byte outside the scale fields is identical, across the whole file;
- the least-squares factor of the dequantized values is within 1e-3 of (1+D);
- the maximum error is at most 4e-3 · max|x|.

`test_perturb_gguf.py` tests the tool on a small fake GGUF built with GGUFWriter. It covers Q8_0, Q4_K, Q5_K, Q6_K and
F32, deltas 0.005, 0.02, 0.10 and -0.05, and checks that unsupported or missing tensors and an existing destination
are refused. Each copy is 17 GB, and the tool keeps at least 10 GiB free. In `all` mode a variant's copy is written
just before its run and deleted after its log is complete, so only one copy exists at a time.

## Usage

```
kld_canary.sh --dry-run all            # print every command (prep, GPU runs, gate); nothing runs
kld_canary.sh prep [VARIANT...]        # CPU only: model copies -> ~/models/lfm/canary (flock -s quiet.lock, nice 10)
kld_canary.sh run  [VARIANT...]        # GPU; resumes: skips RESULTS/<v>.log that parse; failures -> <v>.err.log
kld_canary.sh gate [VARIANT...]        # table: variant | expected | mean KLD | dKLD/sd | 99.9% | same top | verdict | OK/UNEXPECTED
kld_canary.sh all                      # per variant: prep -> run -> delete copy; then gate
PY=$HOME/qwen-opt/.venv-kt/bin/python  # numpy + pyyaml; gguf-py from GGUF_PY (~/llama-master/gguf-py), read-only
```

Every GPU run uses this command:

```
env [ENV] LD_LIBRARY_PATH=$BIN:$BIN/../lib:/opt/rocm/core-10.0/lib flock /tmp/gpu.lock flock /tmp/quiet.lock kld_canary.sh _guarded timeout 900 $BIN/llama-perplexity …
```

`_guarded` runs while both locks are held. It refuses to start if `pgrep -f 'llama-server.*--port 8080'` finds a
process. The script also checks this before each run and pauses 45 s between runs. Logs go to `~/qwen-opt/kld-canary/`.
The environment variables `BIN MODEL KLD_DIR REF TEXT ANCHOR RESULTS CANARY_MODELS CHUNKS TIMEOUT PAUSE KEEP_MODELS
GATE_K GATE_TAIL` override the defaults.

Time [INFERENCE from the reference logs]: about 5.5 min per run plus the 45 s pause, so 18 variants take about 2 h.
Prep adds 6 copies of 17 GB with verification and 2 requantizations. llama-quantize runs with `HIP_VISIBLE_DEVICES=-1`
so that it does not open the GPU. This is a precaution and has not been tested.

If the installed build's f16 path differs from the build that wrote ref.kld, the baseline still works: all canaries
share the same reference. In that case, the baseline row shows ERROR (different PPL(base)) against ANCHOR. To fix
this, write a new reference elsewhere and run with `REF=<new.kld> ANCHOR=`. An empty ANCHOR turns the baseline row
into an ungated BASE row. Do not overwrite `~/wt/lfm3-prof/ref.kld`.
