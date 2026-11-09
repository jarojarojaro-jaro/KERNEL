# L1 host: TOK_CACHE on SAFE_SPECIAL + parser once per step, incremental (66-SYNTEZA items 7, 8)

Branch `l1-tokparse` (off `topka-q63` c0576e3e8), worktree `~/wt/l1-tokparse`, HIP build `build-hip` (gfx1100,
no CUDA), CPU build `build-cpu` (tests). Production `~/llama-topka` untouched.

## Switches (all default off, outputs unchanged)
- `LLAMA_SERVER_TOK_CACHE=1`: works on the `SAFE_SPECIAL` path (chat prompts with plain ranges). Reuse is limited
  to boundaries before the first byte where the range lists differ, and occurrences inside a range are text, not
  boundaries. `=2` also tokenizes in full and logs `tokenize cache: MISMATCH` on any difference.
- `LLAMA_SERVER_PARSE_INC=1`: the stream parser is incremental (`common_chat_parse_inc`). The input is kept with the
  generation prompt in front, and `until()` scans resume (`common_peg_parse_memo`). `=2` is the oracle: every update
  is also parsed the old way, `PARSE_INC: MISMATCH` is logged, and the old result is used.
- `LLAMA_SERVER_STREAM_STEP=1`: one partial result per MTP step (all accepted tokens in one chunk). This applies to
  stream requests without `n_probs`.

## CPU evidence (2026-11-07)
- **`test-tok-cache`:** 257 requests from 2 real omp threads, up to 284k tokens, both threads interleaved, run
  single-threaded.
  - 0 mismatches.
  - At 90k+: full tokenization median 123–187 ms, cached 1.3–2.1 ms.
  - Built-in adversarial conversations (literal `<|im_start|>`, `<|im_end|>`, `<tool_call>` in messages, an edited
    earlier message, a shorter request): 0 mismatches.
- **`test-chat-stream-inc`:** 619 recorded Qwen3.8 outputs plus 618 cut short, 746k tokens.
  - Incremental token by token: every update equals the full re-parse (oracle mismatches 0), and the deltas equal
    the old ones.
  - Per step (MTP-like chunks): the final message, the tool calls and the streamed text are identical.
  - 574/574 tool calls parsed back as recorded.
  - Parser CPU: old per token 36.1 s, incremental per step 0.98 s (−97%).

## Expected gain
- **Agent turn at 90k+:** tens of ms. With `TOKENIZE_PAR=8` the full tokenization is the `ap tokenize` value in
  arm A, and it drops to about 2 ms.
- **Long stream outputs:** HTTP thread CPU −90% or more. Decode on the last 2k of a 12k stream: 0…+1% `[INFERENCE]`.

## Kill criteria (GPU job `l1tok.jobs`)
- Any `MISMATCH` in arm C, or any md5 / text md5 difference between A and B: reject.
- Replay: B tokenize median at 90k+ not at least 10 ms below A → item 7 adds nothing.
- Stream: if the A tail ms/token with stream=true is ≤ 0.3% above stream=false, the parser does not slow decode.
  Item 8 then stays only as CPU relief: deploy only if B is not slower.
- spec_sweep ms/step or greedy t/s of B worse than A beyond the A1/A2 spread: reject.
