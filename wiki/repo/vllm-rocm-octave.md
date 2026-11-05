---
typ: repo
tags: [repo, vllm, kv, rdna3, odrzucone]
aktualizacja: 2026-11-05
zrodlo: ~/KERNEL/product/research/63c-amd-rocm-llamacpp.md:21-23,203-227,359-368; https://github.com/vllm-project/vllm/pull/59774 (vLLM v0.33.0 `4ba787e`, 2026-11-01)
status: aktualne
---
# vLLM `ROCM_OCTAVE`: natywny KV 3/4-bit na gfx1100

**vLLM v0.33.0 (PR #59774) ma KV 3-bitowy dla gfx1100 i gfx942: k3v3 = 216 B na slot przy head 256, czyli 75% naszego q4_0; produkcyjnie na 7900 XTX od 2026-10-02.**

- Mechanizm: losowe znaki + Walsh–Hadamard, kodebook Lloyd-Max N(0,1) na 3 bitach, skala zachowująca normę, `v_perm_b32` jako LUT; QK prefillu na int8 WMMA.
- Na 4× XTX z Qwen3.8-27B: 4.6× więcej tokenów niż fp16, NLL przy 380k +0.00086…0.0015 nata. „Least-squares scale” dawała 2–3× wyższe NLL.
- Dla nas: −1.1 GiB KV przy 262k (droga do 262k na 24 GB).
- **Odrzucone 2026-11-05**: inny kwant KV zmienia wyjście ([[2026-11-05-tylko-bezstratne]]).
- Z tego samego wydania bezstratne: TRITON_ATTN +18% na RDNA3 z 32-bitowego adresowania buforów (PR #60084) → mikroeksperyment buffer loads w [[fattn-kvq]].

## Powiązane
- [[repo/_hub|repo]]
- [[vllm-monokernel]]
- [[fattn-kvq]]
- [[raport-63-synteza]]
