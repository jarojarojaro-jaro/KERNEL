# Strata: speculative decoding, verify windows, sampling, host orchestration, caching

Repo `~/research/Strata` (Niko1221/Strata). Paths are relative to the repo root; short hashes are commits; `#N` = github.com/Niko1221/Strata issue or PR N. "Paper" = docs/paper/Strata-Paper.pdf. [INFERENCE] marks my own reasoning, not something the repo shows.

## 0. Overall loop (serial, single GPU): what one round is

`src/program/generate.cpp:11958-12173` (serve loop; the CLI loop at ~13000+ is the same):
1. **Pick T**: `T = S_mtp` (default 4). With `--spec-min-p p`, extend while `dprob[T-1] >= p` (`:11960-11963`). First window after a prompt: T=1 (`:11964`).
2. **Prompt lookup override**: the suffix drafter proposes k tokens. It is considered only if its first token equals the MTP's first draft (`sbuf[0] == drafts[0]`, `:11972`). `DraftPolicy::choose` then decides (`:11973`).
3. **Optional lookup chain** after the MTP drafts (`--lookup-chain`, opt-in, `:11979-11991`).
4. `Verifier::run(T, window, p, ...)`: one captured graph for this T, plus a per-layer host doorbell service when experts miss VRAM (`src/core/verify.cpp:2136-2365`).
5. Acceptance: `a` = the longest prefix where `window[i+1] == outv[i]` (`:12069`). Greedy and the default sampled mode are exact-match.
6. `Verifier::commit(a+1)`: a captured commit graph replays the GDN recurrence for the kept rows. Asynchronous: no host sync (`verify.cpp:2497-2530`).
7. Emit tokens, then `mtp.draft(T, outv, p, a, ...)`: catch-up plus a draft chain on the drafter's own stream (`src/core/mtp.cpp:1274-1406`).
8. `policy.observe(...)` with the measured round time (`:12163-12168`).

Instrumentation is built in. `STRATA_DECODE_TIMING=1` prints per-window verify (GPU-reach wait, per-layer host, plan, actq, jobs, CPU, stage), commit/emit, draft, and per-layer CPU/VRAM/PCIe entries (`generate.cpp:12180-12191`). `STRATA_VERIFY_PROFILE=1` stamps `%globaltimer` inside the captured graph. `STRATA_VERIFY_NODES=1` prints a kernel histogram per window graph (4a50d4ce). `STRATA_DUMMY_NODES=k` adds k empty nodes per layer to measure what one node costs (7fc02cb5, `verify.cpp:1075`).

Paper Table 5 (RTX 5070, Ryzen 5 7600, 4K context): one round of Q2_0 is 34.3 ms = GPU 14.6 + CPU experts 13.4 + drafting 2.0 + other 4.3, at 3.23 tokens/round. Drafting is about 6% of a round.

---

## 1. MTP draft head

**What it is** (`include/strata/core/mtp.hpp:1-19`):
- The model's own one-layer MTP (vLLM `qwen4_exp`), validated in `tools/mtp_probe.py`, where greedy drafts at steps 1-3 were accepted at 0.89 / 0.86 / 0.85.
- Weights are fetched separately from the BF16 checkpoint (5 GB; paper §3.3). The large projections are Q8_0 through multi-column MMVQ, the experts 2-bit, all 512 experts kept in VRAM (708 MB).
- **MTP attention is dense** over the cells it attends to. That equals the model's sparse selection below 2,051 cells. Speculative cells "never touch indexer state and are simply overwritten when their positions are processed again". The rollback for the draft KV is therefore implicit: positional overwrite, no undo.
- Cell convention: cell i pairs the main model's final residual at position i with the token at i+1.

**Draft round** (`MtpDrafter::draft`, `mtp.cpp:1274`):
- One "round" graph per T = catch-up over the verified cells (their K/V from the window's final residuals), then draft 0. One "step" graph per chain step j.
- **Catch-up only to the accepted row**: `T = a + 1`, so the K/V of rejected rows is not written (3fd0460b, #783 PR-i; `STRATA_MTP_CATCHUP_ALL=1` restores the old behaviour).
- **The layer's front runs once** for T rows. The rest (attention from q, MLP, mixer, head) runs for one row only (ca833116, from eddoursul's fork, "F7").
- Multi-token router/combine and the batched K/V append are shared with the verify window (868f2ef0, 44ffa86c).
- **Early-exit chain on the host**: with `min_p > 0` the host launches step j only while `p_{j-1} >= min_p`. It spins with `_mm_pause` on the mapped `h_out_[j]` (initialised to -1) and calls `cudaStreamQuery` only every 1024 spins (`mtp.cpp:1360-1394`). With min_p = 0 all steps are launched back to back and the host reads each draft as it lands (`:1325-1359`). Each draft's PLE (n-gram embedding) rows are prefetched from SSD as soon as that draft is known.
- **Context-end clamp**: `max_steps = min(max_t-1, max_drafts, max_cells - (p+a))` (e85567b6). Before this, requests that fit ended with "ran out of context".

**Reduced output head (draft vocabulary)**:
- The draft logits are computed only over `rt/draft_vocab.bin` (int32 ids). The original English/code subset has **40,525 ids** (paper §3.3; DETAILS.md:128-144). Where it came from: `[INFERENCE]` the Splash / ninfer / HyperQwen line, credited at paper refs [7,8]. The repo has no tool for the original build.
- #137 (RTX 5070 Ti, IQ3_XXS): the shipped subset held only 27 of 55,328 Han tokens. Full head vs subset on Chinese answers: 76.8 → 87.7 tok/s (+14%), drafts accepted 56/121 → 127/188.
- Fix e227683e (v0.1.27): the subset grows to **106,299 ids** with all CJK. CJK answers +15-38% (Q2_0, RTX 5070), English −1-2%. The head costs about 180 MiB of VRAM (DETAILS.md:128-131); eef24117 then reserves that VRAM in the expert-cache sizing.
- `tools/draft_vocab.py` adds whole Unicode scripts, or `--corpus` tokens up to 99% coverage of a corpus.
  - `--draft-vocab cyrillic`: 58,963 ids. Russian/Ukrainian answers went from 1.4 to 2.1 tokens/round, 83 → 109 tok/s on an RTX 5090.
  - `--draft-vocab fr` (#597): 46,211 ids. French acceptance 0.51 → 0.60, English 0.61 → 0.63, code 0.77 → 0.78, RTX 5090 141 → 158 tok/s.
- The size trade-off, measured: on an RTX 4090D, `STRATA_MTP_FULL_HEAD=1` (all 248,320 rows) raised acceptance 86% → 90% at 6K but decode fell 228.0 → 223.2 (−2.1%) (#2227). For English, the smaller head wins; across languages, coverage wins.
- `--mtp-q4` (e35a061f, 2c697fda; opt-in): Q4_0 copies of the draft projections and the head subset. RTX 5070 IQ3_XXS: draft ms/window 2.55 → 2.23 (q4), 2.13 (en subset), 1.91 (both); tokens/step 2.64 → 2.63 / 2.67 / 2.57.
- `--mtp-hnorm stream` (2312c83b): one RMS norm per hyper-connection stream (llama.cpp's graph) instead of one pooled norm (vLLM's). #2227 (RTX 4090D): acceptance 82 → 86%, decode +3.7% at 6K and +2.3% at 70K, neutral at 120K. Not the default yet. Lesson: whichever convention matches the head's training matters for acceptance.
- Diagnostics:
  - `STRATA_MTP_TOP2=1`: at a rejected draft, was the drafter's runner-up the target? #2227: **0 of 14**. Rejections are not near-misses, so tree/2-branch drafts would not pay.
  - `STRATA_SPEC_DEPTH=1`: acceptance by depth (0ab663fc).

**MTP KV window (`--mtp-window`, default 32,768)**:
- The drafter attends to the last 32,768 cells only (`generate.cpp:572`; `mtp.cpp:329-360`). With KV streaming its K/V is a ring of window + 4·max_t + 64 cells.
- MTP prefill skips cells the window can never reach: `first_needed = prompt_len - window - 64` (`mtp.cpp:1171-1172`).
- Paper: "keeps drafting cheap at 262K".
- docs/STRIX_HALO.md:127: `--mtp-window 8192` gave 64K output +3.5%, 32K −0.4%.
- MTP prompt pass: batched through the prompt kernels (E-9, a402eefd, v0.1.26): "prompts up to 32K 4-10% faster". An 8-row grouping attempt (−6% of the draft pass's time) was reverted (45d857c7 → 86c904ca).

**MTP acceptance by context (tokens per verify window = accepted + 1)**:
- Paper Table 4 (RTX 5070; columns 1K / 4K / 32K / 64K / 128K / 262K):
  - Q2_0: 2.71 / 3.23 / 3.11 / 2.80 / 2.65 / 2.46
  - IQ2_XS: 3.25 / 3.28 / 2.53 / 2.72 / 2.44 / 2.42
  - IQ3_XXS: 3.63 / 3.24 / 2.78 / 2.88 / 2.42 / –
- bench/results/2026-10-01-community-2x-rtx-pro-4500: acceptance 69% / 70% / 68% / 55% at 1K / 4K / 32K / 128K.
- #2227 (4090D): 82% at 6K, 81% at 70K, about 89% on 120K needle prompts.
- Paper finding 12: Q2_0 falls from about 95 to 56 tok/s at 262K, partly from lower acceptance and partly from fewer cached experts.
- Speculation is worth **1.6-1.8x** on the 12 GB MoE box (paper finding 2: 47-57 → 82-92 tok/s at 4K). It is less than in-VRAM engines report because each extra window row routes to its own CPU experts.
- Fully GPU-resident MoE (bench/results/2026-10-06-community-rtxpro-v0140, RTX PRO 6000): Q4_K_XL 129.9 → 257.6 tok/s with MTP T4 (**1.98x**); Q8_0 82.6 → 140.2 (1.70x).

## 2. Draft-length choices and the adaptive logic

- **Defaults**: setup writes `--spec 4 --spec-min-p 0.5` (setup.py:5621). The engine default `spec_min_p` is 0 (`generate.cpp:592`). With suffix drafting on (default `--suffix-draft 3`), `o.spec` grows by 2 (to 6) for lookup windows while the MTP keeps 4 (`generate.cpp:2504-2515`). The graph cap is `kVerifyMaxT = 8`.
- **Confidence gate (p ≥ 0.5)**: a draft enters the window only while the drafter's own top probability is at least `spec_min_p` (paper §3.3). Calibration sweeps 0.3 / 0.5 / 0.7 and keeps a value only if it is >3% faster in an interleaved re-measurement (`tools/calibrate.py:7-9,38-39`, c1afbdac).
- **What was measured for the gate and width**:

  | Setup | Result |
  |---|---|
  | A770 (docs/A770_SPEED_SPEC.md:241-247) | min-p 0.0 → 10.4 tok/s (acceptance 52%); 0.5 → 12.0 (68%); 0.7 → 11.6 (93%). 0.5 kept |
  | RX 7900 XTX, IQ3_S (#744) | min-p 0.70 = 63.1 vs 57.0 (+10%, adopted by that user). The later re-file (#1297) found the defaults fastest: 67.1 vs 65.0 / 66.1 |
  | Z840 + RTX 3090 Ti (bench/results/2026-10-03-community-z840-rtx3090ti:99) | 0.30: 63.9, 0.50: 64.9, **0.70: 70.9** |
  | 2x 6900 XT split | `--spec 3 --spec-min-p 0.7 --pipeline-windows 2`: +11-20% |
  | Intel B70 (docs/INTEL.md:293-294) | spec 2: 33.6, spec 4: 41.6-43.5, spec 6: 35-37; min-p 0.3-0.7 within noise |
  | Arc (docs/INTEL.md:785-787) | spec 6 vs 4: +6.5% on code (84% vs 90% accepted), −1.5% on prose |
  | 2x RTX PRO 4500 | spec 3/4/5/6: 114.8 / 122.2 / 132.4 / 116.2 on short code; at 4K-32K the spread is about 3-5% (noise). Spec 6 lowers acceptance to 67% from 74-76% |
  | #137 (5070 Ti) | spec 2 ≈ spec 4 (76.2 vs 76.8) |
  | RX 6800 | spec 6 worse (55% acceptance); min-p 0.7 about even |

- Why the gate pays on Strata: an extra row costs real CPU expert work. The prior shape in `src/spec/draft_policy.cpp:12` is cost(T)/cost(1) = 1, 1.35, 1.70, 2.05, 2.45, 2.85, 3.25, 3.6 on the RTX 5070, "+10 ms per token with every missed expert on the CPU". The pre-release cost model (`include/strata/spec/controller.hpp`, "23 Sep measurements") had dense-only ratios of 1.0, 1.05, 1.3, 1.45, 1.85, 2.2, 2.6, 3.0, 3.3 for n = 1..9, but distinct experts grow 1 → 1.7 → 2.31 → 2.88 ... `[INFERENCE]` For a dense model with flat row cost the gate matters much less, which is consistent with our p_min null result.
- **`Controller`** (`src/spec/controller.cpp`): the plan-era optimizer, maximizing E[tokens]/T(step) over none / lookup / MTP with a parametric cost model and per-position EMA acceptance (prior 0.86). It is compiled and unit-tested but **not called by the engine**; `DraftPolicy` plus the min-p rule replaced it.
- **`DraftPolicy`** (`include/strata/spec/draft_policy.hpp`, `src/spec/draft_policy.cpp`), used for lookup vs MTP and for chaining:
  - Learns online the **measured round time per window size** (EMA α 0.1). Unseen sizes are scaled from seen ones through the prior shape.
  - MTP: tokens committed per window size (EMA α 0.05). Lookup: acceptance q per match-length bucket (<6, <12, <24, ≥24), with decayed counts (0.97) and priors 0.75 / 0.88 / 0.93 / 0.96 worth 4 observations.
  - It takes a lookup window only if `E(k)/cost(k+1)` beats the MTP's by a margin of 3%.
  - Exploration: an unmeasured size is probed up to 3 times when q ≥ 0.85. A size not measured for 300 rounds is re-probed (#1252, 48d2e6ca: one slow stretch had priced a size out forever; 71eaee17 does the same for chains).
  - Header note: taking lookup whenever it proposed more than the MTP "lost 2-8% on ordinary text".
- **Side effect** (#1928, open): the policy reacts to wall-clock round times, and CPU expert rounding depends on window shape. So greedy output varied between fresh engines (12-15 of 16 runs identical). `STRATA_IQ_MT_MIN=1` (batch-invariant CPU kernels) makes it 16/16. Lesson: any adaptive window policy needs batch-invariant kernels to stay reproducible.

## 3. Prompt-lookup / n-gram drafting and how it combines with MTP

- **SuffixDrafter** (`src/spec/suffix_drafter.cpp`):
  - A hash of every trigram of the history (prompt plus accepted output) maps to its 4 most recent end positions (open addressing, load ≤ 0.5).
  - `propose` finds the longest backward match (min 3, max 64) among those 4 and returns the tokens that followed. The continuation may run into the current suffix (periodic text).
  - `propose_after` matches with extra (draft) tokens appended but not indexed; this is how lookup-chain works.
- **Combination rule** (v0.1.7, bbe8944e): a lookup window replaces the MTP window only when (a) the lookup's first token equals the MTP's first draft and (b) DraftPolicy expects more tokens/ms. Lookup windows can be up to `--spec + 2` long.
  - Measured: "Code edits +6-11%, other text unchanged, verified output identical" (bbe8944e; DETAILS.md:1877-1879; bench `2026-09-27-spec` is cited but not in the tree).
  - No MTP (`serve` without `--mtp`): lookup-only plus one token per round, and the drafter's 0.7-1 GiB goes to the expert cache (DETAILS.md:146-149; 3216d271).
- **`--lookup-chain K`** (2312c83b, 5e0c43ba, opt-in): after the MTP drafts, the drafter matches context plus drafts and appends up to K continuation tokens to the same window (max 8). Chain length comes from `DraftPolicy::chain`: maximize `(E(t_mtp) + p_mtp·(c + c² + … + c^k)) / cost(t_mtp + k)`, with p_mtp = product of the draft probabilities and c the chained-draft acceptance by bucket.
  - Strix Halo: a verify row costs about 9 ms on a 61 ms window. Chaining every 3+ match (49% accepted) gave +6.4% tokens/step for +7% window time, a net loss, so the policy was added.
  - #2227: ±0.05%, with 1-4 of about 148 windows carrying a chain.
  - RTX PRO 6000 Q4: MTP + ngram 255.4 vs MTP 257.6 (−0.8%); ngram-only 133.8 vs none 129.9 (+3%). Not a copy-heavy workload.
- `DraftSource` interface (`include/strata/spec/draft_source.hpp`, `src/spec/draft_source.cpp`): several sources, the longest match wins.
- Rejected or alternative drafters:
  - DFlash standalone block drafter (#1426, open): MTP 83.6 vs DFlash 73.4-76.0 tok/s (RTX 4070 Ti SUPER). The available Flash-Next DFlash checkpoint has lower acceptance than MTP (#1161).
  - DFlash2 RFC (#366, #347) closed; there is no compatible checkpoint.
  - The owner's gate for any new drafter: "default path stays byte-identical (opt-in until it's measured), and a drafter has to show a real acceptance and speed gain on the existing MTP setup" (#347).
  - Agent-style multi-ngram stacking (llama.cpp ngram-mod / ngram-map-k4v, #1161): discussion only.

## 4. Verify window machinery

- **One captured CUDA/HIP graph per window size T** (1..8). Two variants per T: `exec_[T]` with host doorbells, and `exec_nr_[T]` all-resident. A separate commit graph. All captured lazily on the first `run(T)` (`verify.cpp:1846-1971`, `run` at 2147) or up front by `capture_all` for pipelining.
- Paper §3.2: "the whole 48-layer pass is one captured CUDA graph per window size, so the host never waits on a synchronizing driver call".
- VRAM per capture is "some tens of MiB" (DETAILS.md:645-648). 0f931943 logs free VRAM before each capture.
- **Per-token kernels batched over window rows** (#109 / 4a50d4ce, v0.1.23):
  - "the window is launch-latency bound: ~3-5 µs per small kernel"; about 450 extra graph nodes per token were removed.
  - Batched: router GEMV and top-10, the shared-expert gate, bf16 casts, the MoE combine, QSA norm+RoPE, q/gate split, output gate.
  - Measured on RTX 3090: 80.1 → 88.6 tok/s (+10.6%), bit-identical.
- More node cuts:
  - #783 series (v0.1.40): batched K/V and indexer append (44ffa86c), fused per-head RMSNorm+RoPE (088e8a82, *off on HIP* until parity), parallel resident plan (fe4de5de), multi-token GR (STRATA_NO_MULTI_GR).
  - gfx12: host-flag waits folded into the copy that follows, −2 nodes/layer (7fc02cb5). "A dependent kernel costs ~2.4 µs in a gfx1201 graph whatever it does" (`verify.cpp:225-228`). The GDN conv and a/b projections fused (`STRATA_FUSE_CONVAB`) measured −0.3% on gfx1201 and stays opt-in (`verify.cpp:249`).
- **Zero-doorbell (all-resident) graph** (#646 / a36be1db, v0.1.39; be7889ed opt-in, then default with #871 guards 6f7f6805):
  - When every routed expert is in VRAM, the window is recorded without the per-layer host step: no doorbell publish, no 3× `wait_flag_ge` per layer, no plan copy from mapped memory. A 128-thread device kernel (`resident_plan`) does the planning.
  - The host just launches and syncs (`verify.cpp:2183-2193`).
  - #646 on 2x RTX 3090, bit-exact, combined with kernel work: +39-72% tok/s.
  - `refresh_ar()` switches graphs when residency changes (`verify.cpp:1827-1844`). A −1 slot raises a device plan-error flag.
- **Split window (`--spec-split`)**: two token groups, so one group's CPU experts overlap the other's GPU work. Exact but **−7%** (85.8 vs 91.8 tok/s at 4K, paper finding 5): dense weights are read twice and groups share fewer experts. Also worse on the A770 (9.9-10.3 vs 11.7-12.6).
- **Pipelined windows** (bfa532e9, layer split only):
  - Window K+1 runs on stage 0 while stage 1 verifies K. The MTP chain is teacher-forced on K's drafts (`chain_launch`, 8ba583fe) and an agreement gate theta = 0.2 decides launches.
  - On a wrong guess, stage 0 restores GDN from a snapshot and replays K's commit.
  - #1656 (4x RX 7900 XT): +14% at 4K, +27% at 32K.
  - `[INFERENCE]` Not applicable to one GPU, since GPU time is the bottleneck.
- **Non-finite guard** (#879, f332a855): every window checks its head logits in a small kernel into mapped flags, read after the existing sync. A flagged window emits nothing and the session is dropped.

## 5. Rollback of recurrent (GDN) state after rejected drafts

**Mechanism: "don't write, then replay the kept prefix"** (not snapshots):
- In the window, `gdn_step_norm_multi` runs the recurrence "from the untouched state over tokens [0, te)" (`verify.cpp:1162-1176`). The state is read into registers and outputs for all T tokens are produced; **the state in memory is not written** (n_keep = nullptr), except for T=1 self-commit.
- The per-token recurrence inputs stay in per-layer buffers: post-conv qkv `h_L_` and `qkv_L_`, `gate_L_`, `beta_L_`, each `MT × C`.
- **Commit graph** (`capture_commit`, `verify.cpp:1973-2043`). The host writes `n_keep`, `n_keep-1` and the kept positions into mapped `h_commit_` (`commit`, `:2497-2503`); the graph copies them to the device first. Per GDN layer it then runs:
  - `gdn_conv_commit` (conv history advanced by n_keep);
  - `gdn_step_norm_multi(..., n_keep)`, which replays n_keep tokens and writes the state (outputs dropped via `t_out_begin = MT`, S26). A state-only kernel `gdn_step_commit_kernel` uses 192 blocks of 128 threads and no output projection (`verify_kernels.cu:169-219`, #646).
- Per QSA layer: the indexer tail is restored from a snapshot and only kept cells are appended. The PLE history is restored the same way.
- K/V is positional: rejected cells are overwritten later (same as the MTP head).
- **One-token windows commit themselves** (352cad8f, CUDA only; HIP keeps the commit graph). The graph's GDN step writes the state with n_keep = 1, so no commit graph runs and the draft round "runs alone instead of beside the commit's kernels, which read and write each GDN layer's 3 MB state".
- **Async commit** (a1e4fb4c, #284, v0.1.32): `commit` no longer syncs. The next window follows on the same stream; the drafter (own stream) reads only final rows and its own K/V. A `commit_done_` event is waited on only before touching the session from elsewhere (`verify.cpp:2510-2521,2532-2540`).
  - Saved about 0.45 ms of `cudaStreamSynchronize` per round: IQ2_XS 128.6 → 135.8 tok/s (+5.6%), same tokens.
- Pipelined (layer-split) mode does keep GDN snapshots: "the two GDN snapshots on the first card", restored on a wrong guess (bfa532e9).
- Exactness tests: forced wrong drafts and rollbacks give output identical to plain greedy (paper §3.3; `STRATA_SPEC_FORCE`-style hooks; `--spec-follow` / `--window-hashes`, ac131a3a).

## 6. Sampling at T > 0 and the sampler on GPU

- **Greedy**: argmax inside the window graph into mapped `h_out_`.
  - A multi-block argmax per row (`argmax_rows`, up to 128 blocks of 4,096 logits) and a split `row_top_prob` for the draft's top probability (3e4aa1d6) on sm80-89.
  - Cluster kernels on sm90+ (0.1.36: with QSA cluster block selection, Q2_0 4K 89 → 93.5, 128K 64.5 → 76.4 tok/s).
  - HIP keeps the older kernels.
- **Sampled**: sampling runs after the window's sync, as host-launched kernels (not captured, so parameters stay per request) (`verify.cpp:2301-2341`).
  - Row t draws `Philox(seed, pos0 + t)`: tied to position, so a seed replays the same text whatever the drafts were (bbe8944e, 7546c36d).
  - Sampled requests default to top_k = 20; top_k is capped at 64 candidates (DETAILS.md:1254).
- **Sampler kernel evolution**:
  - One thread per token → one block per token (8f3c21dc, v0.1.7): sampled decode 1.50 → **42.7** tok/s (greedy 54).
  - 64 vocabulary chunks (#185): about 12%.
  - Split top_k (#197, 05d4cb11, v0.1.29): 4,096-logit blocks, warp-level top-k in registers, then a one-warp merge and tail. "Sampled answers up to 40% faster with the same tokens."
  - The sampler's double-precision tail moved to float on Intel Arc (FP64 emulated: 451 → 20 µs per row).
- **Penalties per verify row** (de71982b, v0.1.19): each row gets its own history (consumed + x + preceding drafts, `penalty_rows`, `generate.cpp:12027-12037`). Penalized requests run 1-11% slower because the drafter guesses without penalties (DETAILS.md:1251-1254). Penalty counts are kept as a shared bitmap (b819fe69).
- **Logit bias** (dcc6f756, docs/LOGIT_BIAS.md): applied in verify for every row of the window, never to the draft. A dense vocab vector is uploaded once per change; a restrictive list may reduce acceptance.
- **Default under sampling**: exact match against the target's sample, with the drafter proposing its argmax.
- **Coupled drafts** (`STRATA_SPEC_COUPLED=1` / `--coupled-draft`, 3b4230a1, v0.1.30, opt-in): the drafter samples with the request's own chain (top_k / top_p / min_p / temp / penalties) and **the same Philox uniform** the verifying row will use (counter = MTP cell + 1). Output for a seed is unchanged.
- **Gumbel-max picks** (`STRATA_SPEC_GUMBEL=1`, 6381df34, #1281): pick `argmax p_i/E_i`, where E is exponential noise hashed from (seed, counter, token id). A token gets the same noise on both sides, so draft and target agree on shared candidates.
  - Strix Halo, UD-Q4_K_XL, T = 1.0: acceptance 52.8 → 59.9%, tokens/window 2.65 → 2.88, **41.1 → 44.9 tok/s (+9%)**.
  - RTX 3060: acceptance 62.1 → 66.9 (coupled) → 68.0% (+Gumbel), but decode within noise (DETAILS.md:114-126).
- **Rejection sampling** (`STRATA_SPEC_PROB=1`, 33356f72, v0.1.40.2, opt-in):
  - Draft sampled from q; the drafter writes q's (id, prob) list. Accept with min(1, p/q), else sample the residual max(0, p − q).
  - Lookup and chain rows are point masses: accept with p(d), and the residual excludes d. This avoids the "no q means q = 0" bug class (llama.cpp #29924).
  - Tests: `spec_prob_test` (2M trials per case, χ² at 99.9%) and `spec_verify_parity`.
  - **No speed gain**: RTX 3060, 10 interleaved pairs at T 0.3 / 0.7 / 1.0 gave default 42.4 / 43.2 / 43.3, coupled 40.6 / 42.4 / 43.3, rejection 41.0 / 42.6 / 42.6. "Drafts kept per round fell at 0.3 and rose by about 5 points at 1.0, which the cost of the longer sampled windows ate" (DETAILS.md:1260).
  - **Gate bug #2028 (open)**: gating `--spec-min-p` on the *drawn* draft's q selects draws by their own q and biases output toward the drafter's favourite: P(A) = p(A)(2 − q(A)), measured +4.1 points (z 3.0). The fix is to gate on q's top probability (`STRATA_SPEC_PROB_GATE=top`), which depends only on the context.

## 7. Host-overhead reduction (doorbells, mapped memory, spins, syncs, pinning)

- **Doorbell**: a 1-thread kernel inside the graph writes the layer's activations, expert ids and weights to mapped pinned memory, then `__threadfence_system()`, then a volatile increment of `seq`. On HIP there is an extra fence *after* the store (`elementwise.cu:186-215,311-327`).
  - The host spins `while (*seq < want) _mm_pause()` and calls `cudaStreamQuery` only every 1024 spins / 2 ms to detect a dead graph (`verify.cpp:2195-2231`).
  - The host runs the CPU experts and raises flags. On the GPU, `wait_flag_ge` (one thread spinning on a mapped volatile word) resumes the graph (`verify_kernels.cu:1051-1054`).
- **Lessons recorded in code comments** (`elementwise.cu:186-208`):
  - The ring value must be incremented on the device. Passing `h_seq + 1` from the host at capture "rings 1 on every replay".
  - The missing fence "was costing ~10 ms per token on the host side". The host compensated with `cudaEventQuery` every spin, and "a 10-22 µs driver call per iteration is a very expensive substitute for one fence instruction".
  - **RDNA4**: a plain store to mapped pinned memory stays in L2 until the stream syncs (0/100 rings seen). Volatile, a system-scope atomic, or a fence after the store: 100/100 (70e24f43, 0f1390bd #697).
- **No driver calls in the hot loop**:
  - The PCIe share is issued without host CUDA calls inside a window (#31, v0.1.14).
  - `Verifier::service` returns before any CUDA call while nothing has rung (6b392641). The pipelined loop called cudaGetDevice / cudaSetDevice millions of times a second and stalled inside the driver.
  - The end-of-window wait **stays a blocking `cudaStreamSynchronize`**: "a cudaStreamQuery poll here cost IQ3_S ~3% decode (a core calling the driver beside the expert workers)" (`verify.cpp:2279-2286`, 5865998a).
  - The MTP draft steps instead spin on mapped output words (`mtp.cpp:1339-1350`).
  - `(void) cudaStreamQuery(stream)` right after each graph launch flushes the WDDM batch.
- **Host callbacks are expensive**: the adaptive-tier "landed" signal moved from `cudaLaunchHostFunc` to a 4-byte D2H copy into a pinned int that the host polls (25e0a2ef, v0.1.43.1). The host function cost about 7 ms/window with the pool's spinning workers on a 20-core desktop: RTX 3060 46.5 vs 56.5 tok/s.
- **Thread placement**:
  - The pool pins one worker per physical core and the host thread pins itself to a reserved core (#501).
  - `--host-core last` (07610895): on Windows GPU interrupts go to core 0 and the host saw rings 30-110 µs late at p99.
  - `--aux-cpus auto` (91f1e85d, v0.1.42): all other engine threads (adaptive tier, prefill helpers, PLE reader, watchdog, stdin, CUDA driver threads swept from /proc/self/task) move to SMT siblings or spare cores. 2x 3080 + Xeon: solo 72.1 → 79.7 tok/s (+10.5%), host involuntary context switches 43.8k → 3.9k, rare >100 µs doorbell-to-flag stalls 7-8 of 12 requests → 0-1 (DETAILS.md:1749-1785).
  - **Callback-thread warm-up** (0e20d9ae): a lazily created CUDA host-callback thread inherited the host's one-CPU affinity and competed with the spinning verifier (#1975). RTX 5090 / 9950X: 142.82 → 207.75 tok/s.
- **Spin vs sleep elsewhere**:
  - The CPU pool sleeps between requests (be0e0c94, #4).
  - The pool's 20 ms spin-before-sleep within a request: #921 found `STRATA_POOL_SPIN_US=100` gives +7 to +11% TG and −70 to −82% CPU on GPU-heavy dual 4090s (47/48 pairs). The owner requires 10+ interleaved pairs before changing defaults; still open.
  - Prefill stager threads sleep on Linux (#1057: ~10x prompt speed on DGX Spark), spin on Windows (+1.2%).
  - UMWAIT parking (#2174, open): −3.1% ms/window.
- **HIP-specific**:
  - Cross-stream fork/join inside graphs costs more than it saves. The shared-expert fork is off on HIP: R9700 62.9 vs 43.4 tok/s with the fork; RX 6800 Windows 42.5 → 56.4 (#816, `verify.cpp:184-191`). Exceptions: gfx1151 +1.8-6.7%; 2x RX 6900 XT Linux showed fork-on 5-13% faster.
  - The drafter's side stream is not created on HIP (#1240), except gfx103x, where it restored prompt speed (#2056).
  - The one-token self-commit and norm+rope fusion are CUDA-only until HIP parity.
- **Overlap of drafter and verifier**: the commit overlaps the draft (above). On the A770, overlapping the draft with verify (`--spec-split` there) hurt.
- **Short prompt parts through decode windows** (470b3d7c, `--short-read 64`): the batched prompt path has about 300 ms fixed cost plus about 180 ms of cache refill, so parts of ≤ 64 tokens go through verify windows S tokens at a time (~16 ms/token). Before this, a one-word follow-up waited about 1.4 s.

## 8. --batch / batch-MTP (docs/BATCHING.md)

- `--batch N` / `"parallel": N`: every window carries one row per conversation, so dense weights and shared experts are read once.
  - Single 12 GB card: it buys waiting time, not speed. Aggregate −9 to −24%, because slot sessions (0.56 GiB each) shrink the expert cache (BATCHING.md:224-244).
  - 4x16 GB layer split, 8 requests: 360 tok/s total (#559).
- `--batch-mtp` (c8c79b17, #846, opt-in): one MTP proposal per slot; slot drafters share weights and own their K/V ring (50 MiB each).
  - 2x 3080 layer split: 77.3 → 89.2 aggregate (+15.4%, 95% CI +12.5 to +17.9%); one stream alone unchanged.
  - 2x R9700 with all experts in VRAM: 80.2 → 62.7 (−21.9%, 0/5 pairs faster). It "pays only when the experts do not all fit".
  - #1010 (up to 3 drafts per slot inside 8 rows): 2 lanes of code 71.6 → 84.3, prose 75.2 → 72.6.
  - #969: N = 2 +30.4% decode; N = 8 non-MTP wins.
  - #1524 (open, wider 8/12/16-row windows): 1.31-2.07x at c = 4.
- Exactness per slot requires `STRATA_IQ_MT_MIN=1`, `--pcie-frac 0` and a frozen tier: kernel rounding depends on row grouping (BATCHING.md:182-208).
- `[INFERENCE]` Not relevant to a single user.

## 9. Conversation / prompt cache and GDN checkpoints

- **Core** (42810ee8, v0.1.3, PR #10):
  - The live session plus up to 6 checkpoints in RAM.
  - A checkpoint = "the state that cannot be rewound": 36 GDN recurrences and conv histories, 12 QSA indexer tails, PLE history, about **118 MB**. **K/V is not copied** (positional), so resuming = restore the recurrent state + set the length.
  - Taken at the last `<|im_start|>` of each prompt (the prompt is read in two parts there) and every 16K fresh tokens. Used only on an exact token-and-image prefix.
  - The oldest (system-prompt root) checkpoint is kept for good; the rest rotate LRU.
  - Root checkpoint at the end of the system prompt when it is ≥ 2,048 tokens (0.1.20, PR #62 / #65).
  - Claude Code billing stamps pinned so the prefix matches (#965).
  - `"strata_checkpoint": false` for one-shot requests (#861).
- **Async checkpoint copy-out** (#203): replaces `cudaDeviceSynchronize` plus pageable memcpy (~370 ms of GPU idle per mid-prompt checkpoint on 2x 3090) with stream-ordered `cudaMemcpyAsync` to pinned staging (~10 ms of copy engine) and a thread that moves it.
- **Message-boundary checkpoint** (docs/MESSAGE_BOUNDARY_CACHE.md, `STRATA_CACHE_MESSAGE_BOUNDARY=1`, opt-in): when an agent edits only its last user message, a checkpoint at the previous turn boundary (prefix ≥ 8,192, tail ≤ 1,024). Combined with 32K chunks, the first edit went 17.2 → 11.5 s (−33%). Not an isolated measurement.
- **Tail checkpoint** (docs/PROMPT_CACHE_TAIL.md, `--prompt-cache-tail`): one extra checkpoint at the first chunk boundary within one chunk of the prompt's end, evicted first, without re-chunking. A checkpoint grid that re-chunked failed its numerical gate. No speed number.
- **Pinned shared prefix** (docs/RESEARCH_RUNS.md, `strata_prefix` / `pin=N`, 0.1.40.2): document Q&A.
  - P100, 64K document: questions 2-5 went 48.6 s → 0.35-0.53 s TTFT.
  - 262K: questions 2-20 at 0.53 s median when a turn boundary falls at the document's end; 55.5 s each through the API without it (re-read up to 16K from the periodic checkpoint).
  - R3: K/V cells in VRAM are worth nothing per GiB (34.05 → 34.92 tok/s from 4K → 64K resident cells); experts are.
- **Parking** (`--conversation-cache-mib/-slots`): alternating conversations keep full snapshots (running state, checkpoints, used K/V pages, draft K/V) in bounded host RAM. A 9,276-token conversation restored in 51 ms on a 4-GPU split, with the same tokens (DETAILS.md:973-1000). Session files: SAVE / RESTORE (#668).
- `--kv-grow` elastic K/V (9e3dbfe7): VMM 2 MiB chunks grow with context, so no graph is recaptured (addresses fixed). Emulated 16 GB card: 3,396 → 5,719 expert slots, short chat 100 → 115 tok/s.
- **KV_PREFETCH** (docs/KV_PREFETCH.md, opt-in): uploads of streamed (RAM-resident) KV for the next attention layer overlap prefill compute. Prefill −5.3% at 32K, −4.1% at 64K; nothing at 8K or in decode.
- **VRAM_ELASTIC** (docs/VRAM_ELASTIC.md, NVIDIA-only): the expert cache in 512 MiB VMM segments, shrinkable with `POST /v1/vram` (RTX 5070 decode 44 → 33 tok/s with 4.3 GiB given back, 78 ms call).
- **LOGIT_BIAS**: see §6.
- **Crossover** (#2045, RTX 3070, IQ3_S): for fresh long inputs (48-128K) MTP-off finished 1,000-token requests 39.7-47.5% sooner. MTP adds prefill cost (the drafter's prompt pass) and decode gains repay it only near output ≈ input / 6. `[INFERENCE]` The MoE MTP layer is heavy (512 experts); for a dense model it is about 1 / 65 of a forward pass.

## 10. How the author works here (spec / host slice)

- **Cost model before code**: `controller.hpp` was built from "23 Sep" measurements (MMVQ multi-column ratios, distinct-expert growth, CPU extra-token cost) before release, then replaced by an online-learned policy fed with *measured* round times (DraftPolicy). Priors exist so the policy can start, and they are overwritten after a few observations.
- **Exactness as a hard gate**:
  - Every speed change states "same tokens" or "bit-identical". Anything that changes output (coupled, Gumbel, rejection sampling, route skips) ships opt-in.
  - Parity tests exist per kernel (`sampler_parity`, `kv_steps_parity`, `spec_verify_parity`) plus tests that force wrong drafts.
  - Diagnostics are env-gated (`STRATA_MTP_FULL_HEAD`, `MTP_TOP2`, `SPEC_DEPTH`, `DUMP_FIRST_LOGITS`, `STATE_HASH`, `LOGPOS`).
- **Measurement protocol**: interleaved A/B pairs (≥5-10, medians, "N of M pairs faster"); one binary with env-only arms; ms/window decomposition rather than tok/s alone; counters (drafts offered/accepted, windows by size) alongside every speed number. Calibration keeps a setting only if >3% better on re-measurement.
- **Negative results are written down with numbers**: spec-split −7%, lookup-whenever-longer −2-8%, Foresight slots, full draft head −2.1%, rejection sampling no gain, DFlash slower than MTP, HIP stream forks, `--spec-split` on Arc, cudaStreamQuery polling −3%, STRATA_HC_Q8 revert, E-8 revert.
- **Platform-specific defaults**: HIP / gfx12 / gfx103x / Windows each get their own switches after measurement on the actual card (fork off on HIP, fused waits on gfx12, side stream on gfx103x only).
- **Root-causing**: the doorbell fence story (a driver call that "worked" only by flushing), the SYCL spin bug (acceptance 4% → 62% once the draft wait actually waited, 76e1cd2e), #1928 output nondeterminism traced to two interacting documented rules.

---

## Transfer candidates (our setup: 1x RX 7900 XTX gfx1100, Ryzen 7 5700X AVX2, dense Qwen3.8-27B hybrid 48 GDN + 16 full-attention, MTP n = 4, 88-90 t/s, step 35.7 ms, verify 31 ms incl. ~3.2 ms of kernel-boundary gaps)

Ordered roughly by expected value for us.

1. **Replay commit instead of per-token GDN state snapshots** (§5).
   - Mechanism: the verify window reads the GDN state and does not write it. It keeps per-token inputs (post-conv qkv, gate, beta: ~T × C floats per layer). A small commit graph replays n_keep tokens with a state-only kernel; T = 1 windows write directly.
   - Strata gain: not isolated. The state-only commit kernel came with #646 (+39-72% combined); one-token self-commit was a fork port with no number.
   - Why for us: `[INFERENCE]` if our SSM snapshot path writes a full state per draft row (48 layers × T × ~3 MB, ~0.7 GB per window at T = 5, about 0.75 ms at 960 GB/s), the replay costs about 1 extra state read+write per layer (~0.3 ms). Worth measuring first how many bytes our snapshots actually write per window.
2. **Cut graph nodes; measure node cost directly** (§4, §7).
   - Mechanism: batch per-token kernels over window rows (#109: +10.6% on a 3090), fold flag waits and copies into the following kernel (−2 nodes/layer on gfx12), and add `STRATA_DUMMY_NODES=k` empty nodes per layer to measure µs per node.
   - Strata: ~2.4 µs per dependent node on gfx1201; "3-5 µs per small kernel" on CUDA.
   - Why: our ~970 nodes × 3.3 µs ≈ 3.2 ms. Each node removed per layer (×64 layers) saves about 0.2 ms ≈ 0.6% of a step. The dummy-node probe gives our exact marginal cost cheaply.
3. **Avoid cross-stream fork/join inside HIP graphs** (§7).
   - Mechanism: keep the decode/verify graph a single linear stream on HIP.
   - Strata: R9700 43.4 → 62.9 tok/s with the fork off; RX 6800 Windows 42.5 → 56.4.
   - Why: any multi-stream branches in our llama.cpp graph (shared-weight side work, MTP side branches) may cost more than they overlap on gfx1100. Audit and A/B. Caveat: 2x RX 6900 XT Linux was the exception, fork-on 5-13% faster.
4. **Async commit and no host sync between verify, commit and draft** (§5).
   - Mechanism: commit on the same stream, no `StreamSynchronize`; the drafter reads only the final rows; an event is waited on only when the session is touched elsewhere.
   - Strata: +5.6% (IQ2_XS, 128.6 → 135.8) by removing ~0.45 ms per round.
   - Why: our step has ~4.7 ms outside verify. Any host sync between verify readback, KV/state commit and MTP chain launch is pure gap. Check with a timeline.
5. **Host spin on mapped memory instead of `hipStreamSynchronize`, done correctly** (§7).
   - Mechanism: the last kernel writes its result or flag to host-mapped pinned memory with a volatile store plus `__threadfence_system()` (HIP: also a fence *after* the store); the host spins with `_mm_pause`, no driver calls.
   - Strata: a missing fence cost ~10 ms/token; driver polling cost 10-22 µs per call and −3% decode. Strata keeps a blocking sync only where polling competed with its CPU expert workers.
   - Why: we have no CPU expert pool, so `[INFERENCE]` spinning on the argmax/token flag (and MTP draft outputs) could shave sync latency on ROCm per round. Measure ROCm sync latency first.
6. **Pin the decode host thread; move every other thread off its core; no host callbacks** (§7).
   - Mechanism: `--aux-cpus`-style placement (HTTP server, tokenizer, ggml threadpool and HIP runtime threads elsewhere), callback threads warmed before pinning, `hipLaunchHostFunc` replaced by tiny D2H flag copies.
   - Strata: +10.5% (Xeon + 2x 3080; host context switches 43.8k → 3.9k); 142.8 → 207.8 tok/s from callback warm-up (5090); 7 ms/window removed by dropping a host function (3060).
   - Why: the 5700X has 8 cores and plenty of spares. Cheap to try with taskset/affinity and an interleaved A/B. Gains are likely smaller for us (no spinning worker pool), but rare >100 µs preemptions of the host thread hit every round.
7. **Windowed MTP attention (`--mtp-window`)** (§1).
   - Mechanism: the MTP head attends only to the last 32K (or 8K) cells; its prefill skips earlier cells.
   - Strata: Strix Halo 8K window, 64K output +3.5%, 32K −0.4%; paper: "keeps drafting cheap at 262K".
   - Why: we lose 88 → 78 t/s by 94K context and run 204,800 context. If our MTP head attends to the full context at q4_0, capping it at 8-32K bounds both draft cost and MTP KV memory. Check that acceptance holds at long context (Strata's drops somewhat anyway).
8. **Prompt-lookup windows layered on MTP, gated by "MTP agrees on token 1" + a measured-cost policy** (§2-3).
   - Mechanism: a trigram suffix index; a lookup window replaces the MTP window only when its first token equals MTP draft 0 and E[tokens]/measured-cost(T) beats MTP by 3%; lookup windows up to T + 2 (or wider).
   - Strata: code edits +6-11%, other text unchanged. Naively taking longer lookups lost 2-8%.
   - Why: this pairs with our K4 plan (verify width 9-16). Wide windows mostly pay on copied stretches (agentic edits), and the online cost table answers "is width 12 worth it here" per machine.
9. **Quantize the MTP head projections and output subset to 4-bit** (§1).
   - Strata: draft ms per window 2.55 → 2.23 (−13%) with tokens/step unchanged (2.64 → 2.63); with the smaller vocab subset, 1.91 ms.
   - Why: if our MTP chain costs ~3-4 ms per step, a Q4 head plus our 64K vocab could take ~0.3-0.5 ms off. Acceptance must be re-measured.
10. **Check MTP head conventions against training (norm per stream vs pooled) and the vocabulary subset's language coverage** (§1).
    - Strata: hnorm stream raised acceptance 82 → 86% (+2.3-3.7% decode); the CJK subset gave +14-38% on CJK; the full head +4 points acceptance but −2.1% speed.
    - Why: our 64K reduced vocab was built for some corpus. Run `draft_vocab.py --stats`-like coverage checks per language. Our pre-norm and fc conventions vs the reference implementation are cheap to A/B.
11. **Measure before building tree/branch drafts** (§1).
    - Strata: `STRATA_MTP_TOP2` found the runner-up was the target 0 of 14 times at rejections.
    - Why: before any tree-verify work, log the top-2 hit rate at rejected positions. If ≈ 0, skip it.
12. **Sampled requests: coupled drafts with the same RNG uniform (+ Gumbel)** (§6).
    - Strata: acceptance +5-7 points at T = 1.0; +9% speed on Strix Halo, noise on a 3060; full rejection sampling gave no gain. Gate on q's *top* probability, not the drawn one (#2028 bias).
    - Why: only if users run T > 0. Cheap if our sampler is already counter-based (Philox(seed, pos)), which also makes output independent of drafting.
13. **Conversation checkpoints = recurrent state only (KV positional), placed at turn boundaries + every 16K + a pinned system-prompt root, copied out asynchronously** (§9).
    - Strata: follow-ups 0.35-0.53 s instead of 48-55 s; async copy-out removes ~370 ms GPU idle per checkpoint; message-boundary checkpoint −33% first-edit time for agents.
    - Why: a policy port onto our llama.cpp prompt cache and checkpoints. For us, GDN state size is roughly 48 layers × ~3 MB `[INFERENCE]`; its RAM cost is small.
14. **Calibrate the draft floor and width per machine with interleaved re-measurement and a >3% keep threshold** (§2).
    - Strata: min-p 0.7 gave +9-10% on some boxes and nothing on others.
    - Why: we saw p_min null. `[INFERENCE]` For a dense model the per-row cost is flat (Strata's dense-only ratios were 1.0 / 1.05 / 1.3 / 1.45 / 1.85 for 1-5 rows), so fixed T with no gate is expected to win. Re-check only if K4 makes wide windows cheaper or dearer.
15. **Batch-invariant kernels for reproducible A/B** (#1928).
    - Strata: greedy output varied with window shape because of multi-token vs single-token rounding.
    - Why: our multi-column MMVQ (2-8 cols) vs 1-col may round differently. Exact-token A/B gates need either invariance or this caveat attached to every comparison.

Not transferable: doorbell/CPU expert pool, PCIe share, expert cache/adaptive tier, pipelined layer-split windows (one GPU, GPU-bound), `--batch-mtp` (single user), elastic VRAM (NVIDIA VMM only), short-read path (`[INFERENCE]` our dense prefill has no 300 ms fixed cost).
