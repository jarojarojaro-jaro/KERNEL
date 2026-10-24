---
typ: repo
tags: [repo, cache, serwer, gdn]
aktualizacja: 2026-10-24
zrodlo: ~/KERNEL/product/research/60d-serving-kernels-cache.md:139-166,220-223; https://sglang.io/blog/hicache; https://www.lmsys.org/blog/2026-08-11-unified-radix-cache/; https://github.com/sgl-project/sglang/pull/33639
status: aktualne
---
# SGLang HiCache + Unified Radix Cache: cache prefiksów GPU/CPU/storage z modelami hybrydowymi

**Cache prefiksów w trzech poziomach (HBM → DRAM → 3FS/Mooncake) ze stanem rekurencyjnym (Mamba/GDN) i stanem draftu MTP; L3 daje 9.4K → 145.5K tok/s efektywnego wejścia przy ~98% trafień (DeepSeek-V4-Flash, 4× H200), a backup snapshotu na końcu wspólnego prefiksu podnosi odzyskanie 1/10 → 10/10 (Qwen3-Next-80B, #33639) (raport 60d, 2026-10-24).**

- Mechanizmy:
  - host w układzie „page-first”;
  - kernele I/O do 3× nad `cudaMemcpyAsync`;
  - ładowanie KV warstwami równolegle z liczeniem;
  - prefetch best-effort / wait-complete / timeout;
  - write-through(-selective) / write-back;
  - draft packed lub sidecar (#30393);
  - buffer-only (#34798).
- URC: jedno drzewo z komponentami FULL/SWA/MAMBA; `session_id` zmienia kolejność eviction.
- U nas (llama-server):
  - `--cache-ram` trzyma pełny stan slotu;
  - współdzielenie sesji to kopia 2.3 GB, ~1.1 s ([[2026-10-18-cache-promptu-agenta]]);
  - `prompt_cache_key` jest ignorowany.
- Pomysły z raportu 60d: pinned staging wpisu, lekki wpis „prefiks systemowy” z checkpointem GDN na granicy, eviction według `prompt_cache_key`. Razem szacowane 1.6 → ~0.5 s na start sesji `[INFERENCE]`. L3 odpada ([[2026-10-19-kv-tylko-w-ram]]).

## Powiązane
- [[repo/_hub|repo]]
- [[lucebox]]
- [[cache-sesji-na-dysku]]
- [[raport-38-ckpt-vram]]
- [[raport-60d-serving-kernels-cache]]
