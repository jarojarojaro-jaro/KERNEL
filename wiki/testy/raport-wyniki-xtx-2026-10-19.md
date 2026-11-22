---
typ: test
tags: [testy, wyniki, rx-7900-xtx, topka]
aktualizacja: 2026-10-20
zrodlo: ~/KERNEL/product/WYNIKI-XTX-2026-10-19.md:8-14,43-52,63-74,78-89,103-111,141-150
status: aktualne
model: qwen3-8-27b
karta: rx-7900-xtx
wyniki:
  - qwen3-8-27b | rx-7900-xtx | 114.8 t/s | czat T=1; topka f2217bac7 (upstream 35.8) | 2026-10-20
  - qwen3-8-27b | rx-7900-xtx | 419.9 t/s | code-edit; topka | 2026-10-20
  - qwen3-8-27b | rx-7900-xtx | 111.6 t/s | dekod ~32k; topka | 2026-10-20
  - qwen3-8-27b-uncensored | rx-7900-xtx | 434.9 t/s | mvs; topka | 2026-10-20
  - lfm2-5-24b-a2b | rx-7900-xtx | 274.1 t/s | czat; topka (upstream 146.8) | 2026-10-20
  - qwen3-8-27b | rx-7900-xtx | 136.5 t/s | dekod 1.7k; sam MTP, LOOKUP=0 | 2026-10-20
---
# Wyniki RX 7900 XTX 2026-10-19/20: upstream → topka (ten sam skrypt, ABBA)

**Topka `f2217bac7` vs upstream `4c3c5810f` na XTX: Qwen czat T=1 35.8 → 114.8 t/s (×3.21; upstream z MTP 60.1), code-edit 35.5 → 419.9 (×11.8), ~32k decode 32.7 → 111.6 (×3.41); Uncensored czat 111.4, mvs 434.9; LFM czat 146.8 → 274.1 t/s (2026-10-19/20).**

- Ramiona: U0 domyślny upstream, U1 upstream + flagi produkcji + własne MTP, T = `run-topka.sh` (PM4 WA=2 + GUARD, GPU verify) (`WYNIKI:8-14`).
- Qwen VRAM T: 23 333 MiB przy ctx 204 800 vs U0 23 141 MiB przy 99 072 (`WYNIKI:52`).
- long_ctx_bench: sam MTP (`LOOKUP=0`) przy 1.7k 136.5 t/s (stary rekord 130.2); W16 wygrywa od 6.6k (94k: 105.6, 199k: 74.5) (`WYNIKI:82-86`).
- LFM: tg128 163.4 → 278.2 (×1.70), ~32k decode 126.4 → 250.7 (`WYNIKI:103-110`).
- Rekordy: [[REKORDY]]; poprzednie zestawienie [[benchmarki-przed-po-2026-10-19]].

## Powiązane
- [[raporty-2026-10-19-20]]
- [[REKORDY]]
- [[benchmarki-przed-po-2026-10-19]]
- [[rx-7900-xtx]]
- [[qwen3-8-27b]]
