# TensorFold issues and PRs: performance-relevant threads

Source: `gh issue list` / `gh pr list` on ashhart/TensorFold (2026-10-13): 235 issues (188 closed, 47 open, 121 authors),
552 PRs (97 merged, 351 closed, 104 open, 112 non-owner authors). Discussions disabled (HTTP 410). About 100 threads read in
full (body + all comments). Hardware named per row. "Python" = the frozen 0.6.x engine (#286); "native" = the Zig engine
(1.0.x). Closed-not-merged PRs are often landed re-authored (see the method file §6).

Legend for outcome: **landed** (in a release), **refused** (rule-based), **parked**, **moved** (tracked elsewhere),
**frozen** (closed because the Python engine is frozen), **open**.

## A. Qwen3.8-27B (our model)

| # | Title (short) | Key numbers / finding (hardware) | Outcome |
|---|---|---|---|
| [#7](https://github.com/ashhart/TensorFold/issues/7) | Independent run, M5 Max 128 GB, 27B + Nemotron | 27B+DFlash2 drafted vs serial: short answer 95.5 vs 25.4, code 118.3 vs 24.8, 300-word story 66.5 vs 24.3 tok/s; tokens/round 3.2-6.7; whole-file edit 349 tok/s. Drafted == serial on every request | closed as reference run |
| [#31](https://github.com/ashhart/TensorFold/issues/31) | M5 Air 32 GB: 0.3.4.1 halves shared-prefix throughput | 2,048-token cache grid lost the shared prefix; decode unchanged | fixed in 0.3.5 (resume at start of new messages) |
| [#36](https://github.com/ashhart/TensorFold/issues/36), [#55](https://github.com/ashhart/TensorFold/issues/55) | M5 Pro 48 GB profile | warm 59.6 → 85.0 tok/s peak, avg 51 over 21 requests; cliff past ~35k ctx (evictions), swap wall ~58k (8.5 tok/s) | admission counts whole footprint (0.3.5); memory-limit env (0.3.6.2) |
| [#38](https://github.com/ashhart/TensorFold/issues/38) | DGX Spark, 27B exact concurrent serving | 48 shared-prefix prompts, 16 in flight: 156 tok/s in 28.8 GiB; owner's 0.3.6.2: 161.7 tok/s vs vLLM MTP=3 132.1, every reply equal to solo | landed (Python CUDA) |
| [#70](https://github.com/ashhart/TensorFold/issues/70) | M5 Pro 64 GB memory-class cells | full ladder to 139,922 tokens, llama.cpp@90c26fcd source as fixture | landed in README/recipe ("most complete run") |
| [#71](https://github.com/ashhart/TensorFold/issues/71) | 27B+DFlash2 64 GB: prompts >~100K not retained | drafter held 50 KB/token of taps in a lazy graph (5 layers × 5,120 halves) beside 64 KB/token KV | fixed 0.3.6.3 |
| [#72](https://github.com/ashhart/TensorFold/issues/72) | Long prefill stalls running decodes | 4 × 16K prompts: earlier streams drop to 1.0-2.8 tok/s | fixed: chunked fill, 2,048-token chunks with rounds between |
| [#100](https://github.com/ashhart/TensorFold/pull/100) | PR: 27B on AMD ROCm, R9700 (gfx1201, 640 GB/s) | DFlash2: 95.7-126.1 tok/s vs 33.9-34.2 plain; prefill 1,834-2,121 tok/s (2-16k); drafted round 37 ms with 12 verify rows, 29 ms decode matmuls at ~80% of 639 GB/s, GDN verify chain 1.3 ms, tree attention 0.8 ms; removed ~200 launches + 3 host syncs per drafted round; found ROCm unsorted `topk` and negative-offset buffer loads reading zeros | frozen; FP8 prompts made opt-in (code PPL +4.1% vs +0.03% bf16) |
| [#112](https://github.com/ashhart/TensorFold/issues/112) | RTX 5090: 27B+DFlash2 refused at startup | admission counted drafter at fp32 (7.17 GiB) vs loaded 4-bit (0.97 GiB) | fixed: loader and admission share one packing rule |
| [#113](https://github.com/ashhart/TensorFold/issues/113) | Spec-decoding questions (MTP+DFlash2, depth) | MTP as 2nd opinion on DFlash2: +3-12% accepted (chat), 0-6% (code), net −6-9% tok/s (dependent call); Flash Next MTP chain right at depth 1-6 with p = 0.81/0.60/0.51/0.38/0.25/0.14; DFlash2 verifies 16 rows (Mac), up to 128 (Spark) | answered |
| [#115](https://github.com/ashhart/TensorFold/pull/115) | PR: lone 27B stream widens copy windows to 128 rows | GB10: code +13-14%, edit 144 → 489+ tok/s; verify 12 rows 71.7 ms vs 128 rows 142.4 ms; 1.1 vs 6.0 ms per copied token | landed narrowed to GB10 (measured) and Macs |
| [#144](https://github.com/ashhart/TensorFold/pull/144) | PR: ROCm Strix Halo (gfx1151) 27B, GGUF fast prompts | Q8_1 W8A8 WMMA prompt route: 6/16 replies differ from exact route; drafted == serial 16/16 within each route; WMMA/bf16 verify "changed drafted replies and were not faster" | frozen; owner: speed feature can't change the reply → Q8_1 route refused; HIP fixes carried (64-bit lane masks, bf16 rounding, no FMA contraction in tree attention) |
| [#196](https://github.com/ashhart/TensorFold/pull/196) | PR: one-stream servers tile 8-slice projections 32 wide | 28 KB threadgroup partials → 1 threadgroup/core; +8% serial decode on M5 Max, same bits | frozen; native avoids by per-slice threadgroups |
| [#198](https://github.com/ashhart/TensorFold/pull/198) | PR: prompt GDN scan 1.39x (4 state rows/simdgroup) | 3.26 ms/layer per 2,048-token chunk (M5 Max), −3.6% prefill, mlx_lm's bits | frozen |
| [#247](https://github.com/ashhart/TensorFold/pull/247) | PR: 27B CUDA `--kv-dtype int8` | GB10: drafted round ~145 ms at ~100k vs ~106 ms at 3k (bf16 cache reads); int8 (Hadamard-32, -cq 8): −6% at 90k, −13% at 242k | **refused**: changes the reply |
| [#264](https://github.com/ashhart/TensorFold/pull/264) | PR: 27B on V100 (sm_70) | vs llama.cpp b11115 UD-Q4_K_M same card: serial 31.7 vs 33.0; drafted chat 57.4 vs 48.3, code 176.2 vs 90.8, 17k 51.8 vs **62.9** (llama.cpp MTP wins), 63k 46.6 vs 46.8; prefill 963/911/644 vs 738/775/569 (`-ub 2048`) | frozen |
| [#268](https://github.com/ashhart/TensorFold/pull/268) | PR: tree attention folds whole key groups | 16-row verify at 1.5x cache-read floor (vs 1.05x at 1 row); −5% at 90k, −9-10% at 242k (GB10) | landed 0.6.4; owner measured "about 3.5% at 90k"; long replies differ in last bits (sum order) |
| [#278](https://github.com/ashhart/TensorFold/issues/278) | M1-M4: >16-row window cliff | M4 Pro window ms: 1:64.2, 8:81.1, 16:156.4, 17:301.4, 32:306.4, 128:1202.2 | frozen; native keeps ≤16 rows |
| [#280](https://github.com/ashhart/TensorFold/issues/280) | DFlash2 acceptance vs target quant | reporter: collapse on 2-bit; owner: 43% (4-bit) vs 52% (oQ2), engine proposed 2.9 vs 7.8 rows/round because rows were dearer | closed (misread) |
| [#296](https://github.com/ashhart/TensorFold/issues/296) | Independent L40S run, 27B NVFP4/MLX | 1 user: TF 152 vs vLLM 96 (same DFlash2) vs llama.cpp b11364 UD-Q4_K_XL 71 (MTP 3); prefill 2k-32k: TF 3,362-4,644, vLLM 3,406-3,668, llama.cpp 2,325-2,467; 116/116 alone-equal, 136/136 serial-equal | reference run |
| [#323](https://github.com/ashhart/TensorFold/pull/323) | PR: opt-in 27B DeltaNet launch geometry, M2 Max | geometry search only among bit-equal candidates, ABBA blocks, small full-model gain stated plainly | frozen; praised as method |
| [#352](https://github.com/ashhart/TensorFold/pull/352), [#353](https://github.com/ashhart/TensorFold/pull/353) | PRs: bf16 head verify windows share weight loads; mma for K%64==0 | window rows staged 256 inputs at a time, one-row sum order kept → decode tripled on bf16-head checkpoint, same bits; #353 changes bits (stated) | frozen |
| [#520](https://github.com/ashhart/TensorFold/pull/520) | PR: Qwen3.5 family geometry from checkpoint; 27B served | 2B logits byte-identical; 49/49 cache checks on the 27B | closed: one path per model (27B got its own engine in 1.0.3) |
| [#527](https://github.com/ashhart/TensorFold/issues/527) | What bounds the 27B projection kernel | M5 Ultra: step 25 ms GPU (22.9 projections at ~660 GB/s) + 2.3 ms host state copy; stream-only kernel 1,080 GB/s; MMA→fma 65.9 → 31.6 µs ⇒ tensor-unit-bound; FP32 family +27% at 1 stream, half at 8; top-1 0.987, KL 1.8e-4 | **parked** (breaks row-count independence) |
| [#528](https://github.com/ashhart/TensorFold/pull/528) | PR: DeltaNet state commit on GPU | 151 MB/stream host memcpy → GPU copy: 36.0 → 38.7 tok/s (1 stream), 106-110 → 131-138 (8) | closed; native 27B already commits on GPU (`zig/src/families/qwen27/decode_round.zig:243-245`) |
| [#562](https://github.com/ashhart/TensorFold/issues/562), [#563](https://github.com/ashhart/TensorFold/pull/563) | 27B prompt chunks on M5 tensor units | 16.7K prefill 206 → ~620 tok/s, HumanEval 159/164 unchanged; proposed gate: FP64 per projection shape, worst column | not landed as is: row bits depended on chunk width (512 vs 32); owner wants every prompt row on the NAX path |
| [#568](https://github.com/ashhart/TensorFold/pull/568) | PR: DeltaNet state written in place | 8-stream 89 → 142 tok/s, 1-stream ~21 → ~23 tok/s (M5 Max), bits unchanged | closed (one path per model); idea carried to #711 |
| [#577](https://github.com/ashhart/TensorFold/issues/577) | Reuse after mid-context edits | nothing after the first edited token can be reused exactly; exact case: predictable template rewrites, native 27B pre-renders next turn | answered |
| [#578](https://github.com/ashhart/TensorFold/pull/578) | PR: 27B serves concurrent requests | 1 stream within 1.1% of main; sampled now drafts: 57-191 (M5 Max), 47-119 (M3 Ultra) vs 19-21; 8 streams 1.68x/1.79x aggregate; drafted == plain 8/8; 376 equal rows in `tf-qwen27-streams` | **landed 1.0.6** |
| [#588](https://github.com/ashhart/TensorFold/issues/588) | Native `seconds` included prefill | 8,478-token prompt: `seconds` 39.19 → 5.65 after fix | landed 1.0.5 |
| [#603](https://github.com/ashhart/TensorFold/issues/603) | Proposal: 27B EXL3 3.00bpw + DFlash2 on RTX 3090 native | asks gate before arithmetic | open; base = #608 |
| [#608](https://github.com/ashhart/TensorFold/pull/608) | PR: 27B CUDA native engine, every stream drafted | exact vs 0.6.6: 54/54 windows, 12/12 concurrency cells, level with 0.6.6 decode (GB10) | open: refused until glue kernels are own code (no Python-captured Triton) |
| [#643](https://github.com/ashhart/TensorFold/issues/643) | 27B on M6 32 GB: refused + 34.6 GiB | weights kept twice (file + repack) | fixed 1.0.8: 26.5 vs 44.2 GiB on M5 Max (−17.6 GiB) |
| [#711](https://github.com/ashhart/TensorFold/pull/711) | PR: accepted DeltaNet chain scans state in place | 48 layers × 3 MiB fp32 state: ~288 MiB r+w per token removed, one dependent dispatch/layer removed; same bits | open |
| [#712](https://github.com/ashhart/TensorFold/pull/712) | PR: decode attention without tail kernel/gate dispatch | per attention layer 7 dispatches/5 barriers → 4/3; head-dim halves on separate simdgroups; byte-identical | open |
| [#713](https://github.com/ashhart/TensorFold/pull/713) | PR: commit overlaps next draft; top-k over 16 threadgroups | split command buffer (picks vs keep); 15-row draft head over 98,592 columns used 15 cores → 16 spans + merge; 576 top-k cases byte-equal | open |
| [#747](https://github.com/ashhart/TensorFold/pull/747) | PR: 27B CUDA repeated-prompt TTFT | TTFT −86-90% on 4 workloads (GB10) via exact-prompt snapshots + first-logit reuse | open |

## B. Nemotron on CUDA (RTX 3090 / GB10 / RTX PRO 6000)

| # | Title (short) | Key numbers / finding | Outcome |
|---|---|---|---|
| [#136](https://github.com/ashhart/TensorFold/issues/136) | Choose MTP depth by expected tokens/ms | proposal: expected committed tokens(d) / (draft(d)+verify(d)) | **landed 0.6.5** (`bcb8f01c`): +6% one/two Sparks, +7% RTX PRO 6000 |
| [#139](https://github.com/ashhart/TensorFold/issues/139) | Minimum NVIDIA class (RTX 3090?) | 1.0.3: RTX 3090 drafted 252 (prose)/313 (code) tok/s, 194 plain; 1.44-1.69x llama.cpp's faster mode; prefill ~4,800 tok/s at 2k | landed 1.0.3 |
| [#592](https://github.com/ashhart/TensorFold/issues/592) | Receipt: RTX 3090, 1.0.4, 225 W vs 350 W | greedy code 543 → 644, prose 317 → 373 tok/s; prefill 2k 6,110 → 7,314; at 131k prompt decode 167 → 215 (+29%); 60/60 concurrent==solo | linked from CUDA recipe |
| [#597](https://github.com/ashhart/TensorFold/issues/597) | CUDA graphs: collectives inside graphs +10 µs; share captured steps | GB10 RoCE all-gather 15.9 eager vs 25.1 µs in-graph (1 row); split at collectives + relocatable plans: one stream +15-21% (Flash Next TP2); 161 graphs/9 sequences → −7-10% until restart | split → #593; per-sequence capture landed as #615 |
| [#615](https://github.com/ashhart/TensorFold/pull/615) | PR: non-own sequence captures its own graphs once | relocation version crashed 5/5 starts; reduced design clean | **landed 1.0.6** |
| [#627](https://github.com/ashhart/TensorFold/issues/627) | GB10: 1.0.3 decode −1.4% code / −3.0% prose vs 1.0.2 | own glue kernels per launch: add_moe_norm 3.84 → 20.0 µs, router 8.86 → 17.92, topk 3.55 → 7.94; swap to 1.0.2 set: +1.6/+3.5%; 2nd GB10 on 1.0.7 +0.8/+1.9%, "B led A in every round" | open; owner to tune "keeping each output at least as close to a float64 reference" |
| [#660](https://github.com/ashhart/TensorFold/pull/660) | PR: masked (grammar) windows replay graphs | 9,426 eager windows → 22 captures (~50 ms); grammar decode +4.4% plain, +1.0% drafted (GB10) | **landed 1.0.8** |
| [#670](https://github.com/ashhart/TensorFold/issues/670) | Prompt path chunk-invariant → drop 2,048 grid | byte-equal dumps at 17 cut patterns (GB10, RTX PRO 6000); agent loop warm TTFT 0.395 → 0.306 s; resumed turn re-reads median 61 vs 1,039 tokens; prefill 95 vs 188 ms | **landed 1.0.8** (`cc692e6f`, `3f4850c0`) after a no-extra-call design (first turn +60-140 ms otherwise) |
| [#768](https://github.com/ashhart/TensorFold/pull/768)-[#771](https://github.com/ashhart/TensorFold/pull/771) | PRs: batched MTP heads, draft pricing by head steps, per-stream conv/scan/attention in one launch, loads in flight | add_moe_norm 18.3 → 7.8 µs (5-row window); scan 24.4 → 17.9 µs; attn_chunk prefetch −7-12% at 112k; shared one-body version slowed lone stream 1.6-1.9% → separate copies | open |
| [#717](https://github.com/ashhart/TensorFold/pull/717) | PR: `tensorfold benchmark` in the native binary | community-v1 suite; cells fail when a repeat stops before 256 tokens (GB10, M4 Pro); GB10 Nemotron prefill 6.9k: 7,018-7,130 tok/s, two boxes within 2% | open |

## C. Flash Next / GLM / other families (method-relevant)

| # | Title (short) | Key numbers / finding | Outcome |
|---|---|---|---|
| [#22](https://github.com/ashhart/TensorFold/issues/22) | Independent run M5 Ultra, Flash Next | decode = wall difference between 32- and 512-token completions; acceptance 60-95% | reference run |
| [#27](https://github.com/ashhart/TensorFold/issues/27) | 0.3.4.1 faster short, slower long vs 0.2.0 (M3 Ultra) | greedy 109.0 → 119.4, code 128.6 → 140.0; long prompts slower; measured alternately, never concurrently | fixed in 0.3.5 |
| [#89](https://github.com/ashhart/TensorFold/issues/89) | Flash Next vs oMLX, M3 Ultra 512 GB | different quant (4 vs 8 bit) stated as "two deployments, not two engines"; MLX 0.32.3 broke prefill kernel (#88) | reference |
| [#250](https://github.com/ashhart/TensorFold/pull/250) | PR: `--mtp-cost` expected-time draft stop | GB10 EXL3: chain product overstates greedy acceptance ~2.5x; cost 0.15 −3.9% ms/token code, +0.9% prose; live round 5.6 ms longer than startup table (unpriced host time) | frozen; idea → Nemotron depth rule |
| [#252](https://github.com/ashhart/TensorFold/pull/252) | PR: read n-gram pages ahead | cold 24K prompts −55…−74%, same bits (page faults one at a time) | frozen |
| [#258](https://github.com/ashhart/TensorFold/issues/258), [#444](https://github.com/ashhart/TensorFold/issues/444) | EXL3 prompt path 670-800 tok/s | after #212/#283: ~1,700 tok/s, bit-identical; prompt-lookup drafter + MTP: wins on repetitive/chat, code a wash | frozen; native EXL3 to start from those kernels |
| [#259](https://github.com/ashhart/TensorFold/issues/259) | GLM CUDA round grows ~3 ms per 1K ctx | ~50 ms shallow → 468-537 ms at 138K; tok/round ~3.25; host-ahead mode 117 ms | frozen; slope is a native gate |
| [#274](https://github.com/ashhart/TensorFold/issues/274) | Batched prefill that keeps row-exactness? | bf16 lane ~750 tok/s vs mlx_lm >1,000 | owner: prompt chunks only need a fixed chunk plan (fresh==resumed); row-exact kernels are for verify/decode |
| [#317](https://github.com/ashhart/TensorFold/issues/317) | Flash Next GB10: 0.6.4 ~24% slower than 0.6.3 | 66.6 → 50.8 tok/s; "not reproducible" (same sha/rounds/accepted) → ramp at 128 tokens (41.8 vs 66.7) → root cause: graph slot swap after 5 distinct prompts, 17-18 recaptures ≈ 1.25 s/request; fix #337: requests 6-8 decode 11.95 → 6.09 s | fixed in #337 (frozen line); 0.6.3 rate = bar for native |
| [#406](https://github.com/ashhart/TensorFold/issues/406) | Mojo kernels for ROCm decode (R9700) | 27B+DFlash2: 48.0 → 44.8 ms/round at 61.5k (−6.6%), 62.9 → 56.4 at 123k (−10.5%); bit-identical; HIP runs agree within 0.1%; launch overhead 1.56 µs both | **refused** (one kernel language); tuning to backport to HIP |
| [#412](https://github.com/ashhart/TensorFold/issues/412) | ROCm RDNA4 R9700 stack | 27B Quark MXFP4 + DFlash2: prefill 2,869/2,651/2,138 tok/s (6.7K/30K/67K), decode chat 56, code 144-145; expandable segments corrupt memory on R9700; decode matmuls with 4 groups' loads in flight, same bits | moved to #426 |
| [#437](https://github.com/ashhart/TensorFold/pull/437) | PR: Kolibri router one-row bits | MLX bf16 matmul picks kernel by row count → 24/240 16-row windows differed; fix: 4 streams 111-117 → 179-195 tok/s | frozen; property required on native |
| [#447](https://github.com/ashhart/TensorFold/issues/447) | CUDA Flash Next cold prefill 1.4-1.5x slower than vLLM | 20,304 tok 12.5 vs 8.8 s; 80,576 tok 52.7 vs 36.1 s; decode level 47.2 vs 47.8; tile-table follow-up: all 12 tiles bit-equal, +4.3% at 1k, +1.0% at 8-16k | moved to #472 (vLLM parity is the bar) |
| [#457](https://github.com/ashhart/TensorFold/issues/457) | fp16 P·V closer to fp32 than fp32 P × bf16 V | M5 Ultra: 9.42 ms rel 1.43e-3 vs fp16 12.09 ms 8.63e-4; owner FP64 probe: both within ~2% of bf16-rounded exact; fp16 made 1.8-5.8% of words worse, 4-43% slower | **refused** ("no word gets worse" bar) |
| [#459](https://github.com/ashhart/TensorFold/issues/459) | Prefix cache stops matching at ≥3 concurrent | 540 → 0 cached tokens between 2 and 3 requests; one-token throughput −60% | acceptance case for #472 |
| [#606](https://github.com/ashhart/TensorFold/pull/606) | PR: opt-in continuous batching Flash Next Metal | 180 paired comparisons; chained MTP draft waits 256 → 84 | open: concurrency must be default path incl. sampling, not a flag |
| [#754](https://github.com/ashhart/TensorFold/issues/754) | Benchmark log vs llama.cpp on one Spark | Python 0.6.3 no-drafts: prefill 1,488 vs llama.cpp 185-233 tok/s; decode 20.0 vs 8.3-16.3; caveats: production box, unpinned llama.cpp build, one run per cell | open |

## D. AMD / HIP / ROCm (relevant to our RDNA3 box)

| # | Title (short) | Key numbers / finding | Outcome |
|---|---|---|---|
| [#389](https://github.com/ashhart/TensorFold/pull/389) | PR: ROCm MLX affine path RDNA2/RDNA3 (Python) | caps: RDNA2 vdot2 fp16; RDNA3/3.5 + bf16 dot2 + WMMA bf16; RDNA4 + fp8 WMMA. 890M review: `softmax_stats` race; GQA re-read K/V 8x; MTP verify ran one decode step per draft (slower than no drafts, 24 vs 29 tok/s) | frozen → #426 |
| [#426](https://github.com/ashhart/TensorFold/issues/426) | Proposal: native Zig HIP backend + 27B GGUF on gfx1151 | owner's boundary: first PR = admission + one exact matmul + "a test that fails when the bits move"; fast prefill math excluded | open tracker |
| [#463](https://github.com/ashhart/TensorFold/pull/463) | PR: model-free HIP runtime + exact affine row projection | gfx1151; row alone == row in batches 1-32; repeats and concurrent load identical; vs MLX Metal 2/4,032 outputs 1 ulp → no cross-backend claim | landed 1.0.5 (re-authored) |
| [#490](https://github.com/ashhart/TensorFold/pull/490) | PR: native HIP engine for Qwen3.5 MLX on RDNA2/RDNA3 | **W7800 (gfx1100, 48 GB, 180 W cap)**: 27B 4-bit decode 25.9 tok/s plain, prefill 629/593 (2k/8k); 27B 3-bit MTP 28.8 → 40.8 tok/s; matrix cores off: prefill 629 → 394, decode within 5%; V620 27B 4-bit 22.2. Review on a Radeon 890M (gfx1150, Qwen3.6-35B-A3B): under GPU contention 5/10 different greedy replies (`softmax_stats` race) → 30/30 equal after one barrier; GQA fix +42% decode at 7.6K. gfx1151 (Strix Halo) 27B: 12.6 tok/s 1 stream, prefill 297 | closed as reference; landing in slices (#617, #621, #631) |
| [#491](https://github.com/ashhart/TensorFold/issues/491) | Zig ROCm RDNA2/3/3.5/4 integration | every HIP PR run on W7800 (gfx1100) + V620 (gfx1030) before opening | open tracker |
| [#617](https://github.com/ashhart/TensorFold/pull/617), [#621](https://github.com/ashhart/TensorFold/pull/621), [#631](https://github.com/ashhart/TensorFold/pull/631) | PRs: HIP kernels, MLX affine products (dot2 + gfx11 WMMA tile), Qwen3.5/3.6 engine | gfx1201 dot2 GEMM tile 24-26 TFLOP/s at 512-4096 rows; K-parallel 5-7; disassembly of 235 (gfx1100) / 229 (gfx1030) tile kernels unchanged by refactor; owner copy scan vs MLX/vLLM/llama.cpp etc. clean | open (1.0.8+) |
| [#607](https://github.com/ashhart/TensorFold/pull/607), [#609](https://github.com/ashhart/TensorFold/pull/609), [#630](https://github.com/ashhart/TensorFold/pull/630) | PRs: gfx1030/gfx1100 build, caps table, events | no model on HIP yet | landed 1.0.6 / 1.0.8 |

## E. Measurement tooling and harness threads

| # | Title (short) | Finding | Outcome |
|---|---|---|---|
| [#432](https://github.com/ashhart/TensorFold/pull/432) | PR: reject incomplete cold-prefill measurements | `[DONE]` ignored, stream-close time substituted for missing first token, missing usage counted as 0; 7-case test | frozen on Python; Zig-branch copy kept |
| [#485](https://github.com/ashhart/TensorFold/pull/485) | PR: verify cache state, retain evidence | absent token hashes compared equal → false exactness pass; strict usage validation | **landed 1.0.3** (docs/cache-benchmarks.md) |
| [#548](https://github.com/ashhart/TensorFold/issues/548) | Zig CUDA ports: shared layers | NVFP4 staged expert prompt kernel 0.45x → 0.99-1.00x of MLX 4-bit prompts; `quant-ref` FP64 checks at 300 rows | open coordination |
| [#593](https://github.com/ashhart/TensorFold/issues/593) | GLM on native CUDA tracker | gate wording: decode slope with "the same selected tokens" | open |
| [#675](https://github.com/ashhart/TensorFold/issues/675) | Cooperative b4g32 lane projection fails FP64 check | sums prepared for K/64 groups regardless of group size; error 1.02 vs bound 0.0049; 68 layouts pass then fail | fixed #698; 115 layouts pass |
| [#286](https://github.com/ashhart/TensorFold/issues/286) | Landing next (board) | house rules; per-release landed lists | open board |

## F. Patterns across the threads

- **Every accepted perf PR carries the same receipt skeleton**: environment (commit, chip, OS, checkpoint revision),
  exactness table (drafted==plain, concurrent==solo, resumed==fresh, model-free device checks), speed A/B alternating builds
  with rounds, and "what I did not run". Examples: #568, #711, #713, #592, #627.
- **Owner restates numbers and their provenance** ("Those timings are yours. We have not re-run them", #447) and, when
  re-measured, publishes the owner's own figure (#268: 3.5% vs claimed 5%).
- **Regression disputes are resolved by invariants**: identical `sha`, `rounds`, `accepted` prove the tokens are the same, so
  the remaining difference must be time per round (#317, #627).
- **Precision refusals are the most frequent "negative result"** (#247, #144, #457, #100, #563, #527): TensorFold trades
  speed for exactness every time; our fork makes the opposite trade (q4_0 KV, q8_1 activations), so their accepted
  speed-ups are the subset that would also be bit-identical for us.
- **Gaps they themselves report vs llama.cpp on the same model**: V100 at 17k, llama.cpp's MTP 62.9 vs TF 51.8 tok/s
  (#264); L40S single user llama.cpp UD-Q4_K_XL MTP3 71 vs TF 152 (#296). For our box the closest comparable is
  W7800 gfx1100 at 180 W: 25.9 tok/s plain / 40.8 with MTP (3-bit) on their HIP engine (#490), far below our 88-90.
