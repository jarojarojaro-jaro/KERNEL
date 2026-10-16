---
typ: narzedzie
tags: [narzedzia, kld, bramka]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/tools/kld_gate.py:1-18; ~/KERNEL/qwen-opt/tools/kld_canary.sh:1-14; ~/KERNEL/qwen-opt/tools/perturb_gguf.py:1-16; ~/KERNEL/qwen-opt/tools/kld-canary.md:15-59
status: aktualne
---
# Bramka KLD i kanarki (kld_gate.py, kld_canary.sh, perturb_gguf.py)

**Trzy narzędzia: `kld_gate.py` porównuje dwa logi `llama-perplexity --kl-divergence`, `perturb_gguf.py` robi celowo uszkodzone kopie GGUF, a `kld_canary.sh` sprawdza, że bramka łapie prawdziwe szkody.**

- Bramka (k=2, tail 1.25): PASS iff ΔKLD ≤ k·√(se_B²+se_C²), Δsame-top ≥ −k·√(…) i KLD99.9_C ≤ 1.25·KLD99.9_B; IDENTICAL, gdy wszystkie liczby równe; kody 0/1/2.
- Kalibracja na logach LFM: q8_0 kvq ΔKLD +0.000025 → PASS; q4_0 kvq +0.084188 → FAIL (wszystkie trzy). Próg 2 sd ≈ 0.005 KLD, ok. 11% podłogi q8_0, więc błąd < ~0.005 KLD przejdzie.
- `perturb_gguf.py` skaluje tylko skale fp16 bloków (Q8_0, Q4_K, Q5_K, Q6_K) o (1+delta), reszta bajtowo identyczna; `--verify`.
- Kanarki (LFM2.5 Q5_K_M, wikitext-2, 3 × 16384 tok., ubatch 1): kv_q4, moe_k3, wdown/wattn ×1.10 muszą FAIL; ×1.005/×1.02 jako PROBE.

## Powiązane
- [[narzedzia/_hub|narzedzia]]
- [[loo-py]]
- [[samp-ab]]
- [[bramka-kld-kanarki]]
- [[2026-10-14-lfm-kv-q8]]
