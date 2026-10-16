---
typ: eksperyment
tags: [eksperymenty, lfm, kv]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/NOTES.md:353-360; ~/KERNEL/qwen-opt/research/lfm-kv-q4-vs-q8.md; ~/KERNEL/qwen-opt/research/lfm-decode-round2.md
status: aktualne
---
# 2026-10-14: LFM runda 2 (0053–0054) i przejście na KV q8_0

**Użytkownik zdecydował, że LFM używa KV q8_0; fuzje routera MoE i shortconv w in_proj dały tg128 221.3 → 244.1 t/s, bitowo identycznie.**

Koszt KV q8_0 względem q4_0 (llama-bench tg128, przed łatką 0055): głębokość 0 +2.6%, 8k +5.0%, 32k +12.7%, 98k +30.1% (187 → 144 t/s); VRAM przy 131k 18.6 → 19.3 GB. Przyczyna: q8_0 nie miał kernela `kvq`, więc szedł generyczny `flash_attn_ext_vec`, czytający K/V raz na każdą głowę Q z grupy GQA (4×).

| łatka | zmiana | efekt |
|---|---|---|
| 0053 `GGML_HIP_NORM_ROUTER` | norma FFN + router F32 + top-k w jednym kernelu | 521 → 445 kerneli, 4.451 → 4.246 ms |
| 0054 `GGML_HIP_INPROJ_CONV` | shortconv wewnątrz kernela in_proj | 445 → 416 kerneli, 4.231 → 4.100 ms |

Wynik (KV q8_0, przeplatane z bcdf324d3): tg128 221.3 → 244.1 t/s (4.519 → 4.097 ms); serwer 217–223 → 238–243 t/s; Qwen bez zmian. Greedy md5 bez zmian (LFM q8_0 2c7ee8a2, Qwen plain c4708318, MTP 6f14e814); hash logitów 64 kroków równy przy głębokości 0 i 3000.

Pomiary kosztów uruchomień: granica w grafie HIP ~2.53 µs, bariera siatki w kernelu trwałym 0.5–0.8 µs. Zagadka: losowe spowolnienie gate+up 24.3 → 27.2 µs w części procesów (4/8 profili).

## Powiązane
- [[eksperymenty/_hub|Eksperymenty]]
- [[fuzje-lfm-moe]]
- [[kwanty-gguf]]
- [[lfm-runda-3]]
- [[2026-10-14-lfm-kv-q8]]
