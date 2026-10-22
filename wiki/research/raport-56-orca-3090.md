---
typ: research
tags: [research, 3090, orca, qwen35, mtp, dflash2, kvq, mmvq]
aktualizacja: 2026-10-21
zrodlo: ~/KERNEL/product/research/56-orca-3090.md:1-130
status: zmierzone
---
# Raport 56: OrcaCyber-Nano-1.0 na RTX 3090 — 262k na KV q4_0, MTP n=2 72.8 t/s

**OrcaCyber-Nano-1.0 (qwen35, 65 bloków, MTP wbudowane) działa na wynajętej 3090 z pełnym kontekstem 262 144 przy KV q4_0 (23.3 GiB VRAM). q8_0 i f16 przy 256k nie wchodzą. Konfiguracja końcowa (MTP n=2 + kvq-mma): 89.6 t/s (T=1, 32k, host 310 W; 72.8 na VN) i 79.2 t/s przy 262k/29k, +90% vs goły upstream (38.3). DFlash2 przegrywa wszędzie. Sufit: GPU ~80% HBM, reszta to narzut hosta; przełączniki hosta neutralne.**

## Budżet kontekstu
- 262 144: OK z MTP (23 332 MiB) i z DFlash2 (23 170 MiB); q8_0 i f16 — brak miejsca (f16 chciał bufora KV 16 GiB).
- Load-only VRAM: 32k → 16 813, 64k → 17 740, 128k → 19 604, 256k → 23 332 MiB.
  **Slope 29.1 KiB/token**, intercept ~15.9 GiB. Teoretyczne KV q4_0 (16 warstw full-attn, blok MTP bez cache) to 18.4 KiB/token,
  więc ~10.7 KiB/token to inne bufory rosnące z ctx (do domknięcia).
- KV q4_0 jest ~13% wolniejszy w decode niż f16 przy tej samej głębokości (75.4 vs 86.5 t/s @14.7k), prefill identyczny
  (~920 t/s) — q4_0 kupuje 262k kosztem decode. q8_0 jest jeszcze wolniejszy (65.7), nie kandydat.

## Ranking (T=1, 32k, KV q4_0)
| config | t/s |
|---|---|
| fork + MTP n=2 | **72.8** |
| fork + MTP n=1 | 70.7 |
| fork + MTP n=4 | 66.4 |
| fork + DFlash2 n=2 | 57.2 |
| upstream + MTP n=4 | 51.7 |
| fork bez spekulacji | 40.4 |
| upstream bez spekulacji | 38.3 |

Przełączniki hosta (lookup/coupled/verify/ckpt/safe/head/vocab/p-min/ubatch/graph-opt) w granicach ±0.5% — obecne
domyślne są na optimum. **Równoległość:** `-np 2` z dwoma żądaniami daje 82.1 t/s agregatu vs 64.4 przy `-np 1`
(+27%), po 45-46 t/s na żądanie.

## Długi kontekst
TTFT przy 29 299 tokenach: 34 s (prefill 856 t/s), decode 63 t/s przy ctx 262k, VRAM 23.6 GiB. DFlash2 tam 46 t/s.
Prefill nie zależy od typu KV ani od ubatcha (ub512/1024/2048: 1000/1074/1007 t/s).

## Kernele
- `GGML_CUDA_MMVQ_N1_ROWS=2` (commit `6cf6ced`, w `topka` brak): tg128 40.32 → 43.43 (+7.7%) na jednym hoście,
  46.19 → 47.35 (+2.5%) na drugim; bitowo identyczne (test-backend-ops OK). Na serwerze z MTP bez zmian —
  hot spotem jest verify batch (ncols=3), nie ncols=1.
- `GGML_CUDA_MMVQ_MROWS=4` (verify batch): neutralne.
- `GGML_GDN_REPLAY=0` / `LLAMA_CONV_LAG=0`: brak zysku.
- **`GGML_CUDA_KVQ` (kvq-mma, `01d6c6955`) nie było w `topka`** — przeniesione na `orca-kvq`; szczegóły w raporcie 56.
- FA z KV q4_0 na CUDA nie używa szybkiego KVQ z RDNA3 (`fattn-kvq.cu` jest na AMD-owych builtinach) — na NVIDIA
  idzie `fattn-vec`, który czyta KV osobno dla każdej głowy Q (GQA 6×).
- `get_int_from_table_16` (IQ4_XS) na CUDA już używa `__byte_perm` — brak taniego zysku.

## Drugi host (QC): A/B kerneli i serwowania
Ten sam build: tg128 `N1_ROWS=0` 46.19 → `=2` 47.35 (+2.5%), `=4` 44.98. Serwer MTP n=2: 66.2 t/s (base),
61.6 (`N1_ROWS=2`), 66.1 (`MROWS=4`), 58.2/58.7 (`GDN_REPLAY=0`/`CONV_LAG=0` — dryf). **`-np 2`: 82.1 t/s agregatu
vs 64.4 przy `-np 1` (+27%)**. Prefill: ub512/1024/2048 = 1000/1074/1007 t/s (bez różnicy).
Wniosek: żaden przełącznik MMVQ/rollback nie rusza ścieżki z MTP — tam hot spotem jest verify batch i narzut hosta.

## kvq-mma na 3090 — ZMIERZONE: +14…+21% decode
`01d6c6955` przeniesione na `orca-kvq` (2d9f34d69). Host: EPYC 7K62, 3090 310 W.

| ctx | prompt | kvq=0 | kvq=1 | zysk |
|---|---|---|---|---|
| 32 768 | 23 452 | 75.1 t/s | **85.7 t/s** | **+14.1%** |
| 262 144 | 29 299 | 65.6 t/s | **79.2 t/s** | **+20.7%** |

Prefill bez zmian, VRAM z kvq niższy (23 364 vs 23 612 MiB @262k). Hosta z zablokowanym HF obszedł `HF_ENDPOINT=https://hf-mirror.com`.

**Bramka jakości przeszła:** PPL na stałym korpusie identyczne dla kvq=0/1 (3.8045 / 4.7035 / 3.0303, przeplot 0-1-1-0);
KL top-20 0.00100, top-1 100% (4 pozycje — API zwraca probs tylko dla próbkowanego tokenu). Greedy md5 różni się
(`7f24f92e` vs `4a688971`) — to ścieżka akceptacji spekulacji, nie rozkład celu.

Na hoście 310 W (ten sam config): sweep 32k kvq=1 **89.6 t/s** vs kvq=0 88.1; `-np 1` 76.3 t/s/żądanie,
**`-np 2` 88.0 agregatu** (+29% sumy decode).

**GDN chunked MMA (`62df1815b`) — zamknięte negatywnie.** Pierwszy pomiar: +10.5% pp2048, ale PPL = nan.
Przyczyna: topka normalizuje q/k **przed** kernelem (`l2_qk`, bufory pool + przekierowanie `q_d`/`k_d`), a hook
czytał surowe `src[0/1]`. Po poprawce (`orca-gdn2`, `729b77311`, hook bierze przekierowane wskaźniki i jest
wyłączony dla `keep_rs`) **PPL i md5 są identyczne**, ale pp2048 wraca do 1510 (kernel nie jest brany) — MMA
zapisuje jeden `state_out`, a topka buduje graf ze snapshotami (K>1). **Zysk wymaga dopisania obsługi wielu
slotów stanu w MMA**, nie da się go włączyć przełącznikiem. Druga próba (dopuszczenie grafu fused-cache)
dała pp2048 +3.8%, ale PPL = 130 547 / 261 085 / 171 804 — kernel czyta/pisze stan cache źle. **Wątek zamknięty
jako wymagający osobnej integracji** (cache + snapshoty + l2_qk), gałąź `orca-gdn2` wróciła do bezpiecznej bramki
`729b77311`, domyślnie off.

## TTFT przy pełnym 262k (kvq=1, ub512)
| tokeny promptu | TTFT | prefill | decode |
|---|---|---|---|
| 26 166 | 23.0 s | 1140 t/s | 77.5 t/s |
| 58 535 | 59.0 s | 993 t/s | 63.4 t/s |
| 117 002 | **149.7 s** | 782 t/s | 59.2 t/s |

ub1024 wchodzi (24 026 MiB, +1.8% prefill, ~550 MiB zapasu), ub2048 nie wchodzi → zostaje ub512.

## Ostatnia runda knobów (Oregon)
Powtarzalność produkcji: 90.4 / 88.5 / 88.9 t/s (**89.3 ±1.1%**). Zamknięte negatywnie: `LLAMA_SPEC_LOOKUP_W=32`
(−1.1% ABBA), `LLAMA_GPU_VERIFY_M` 32/64 (neutralne), `-np 4` (nie startuje z MTP), MMQ IQ4_XS occupancy 2
(**−11.5% prefill**, PPL bez zmian). TTFT @262k na tym hoście: 23.4k → 20.0 s, 58.5k → 61.7 s, 117k → **153.2 s**.
**Średnie: decode 78.7 t/s (n=17), prefill 1055 t/s (n=10), ctx 262 144.**

## Pułapki pomiarowe
- **Zimny page cache**: pierwszy prefill po starcie to ~3.8 mln page faultów (mmap): zmierzone 0.39-1.1 t/s na
  pierwszych 42 tokenach; ten sam serwer po rozgrzaniu 856-1000 t/s. Przed pomiarami trzeba `dd if=model of=/dev/null`.
- **Współdzielony host**: ten sam config daje 72.8 t/s (VN, Xeon 2682 v4) vs 66.2 (QC, Xeon 2695 v2), a w sesji
  wynik dryfuje ~8% w 15 min. Mikro-A/B tylko przeplatane; `test-backend-ops` na jednym z hostów nie inicjował CUDA.
- Greedy md5 zmienia się z trybem spekulacji (none `c39c9ee7`, MTP `fe9f5182`, DFlash2 `ef21082d`) — drafter nie jest
  bitowo neutralny przy T=0; do świadomej decyzji.

## Powiązane
- [[research/_hub|research]]
- [[raporty-2026-10-20-21]]
- [[mmvq-n1-wiersze]]
- [[fa-kv-kwantyzowane-cuda]]
- [[fattn-kvq]]
- [[vast-ai]]
