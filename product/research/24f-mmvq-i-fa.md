# 24f — MMVQ (n=1 szeroki loader, klif Q4_K n=5, Q6_K b128) i FA D=256 w prefillu

Gałąź `opt-mmvq2` (`~/wt/mmvq2`, z `topka` 2821e1303), commit 9be6076d5. Domyślne zachowanie bez zmian. Narzędzia i ISA: `~/wt/mmvq2-tools/` (`isa_s.sh`, `loopwait.py`, `mk_isa_tu.py`, `fa_variants.sh`, `sessA.sh`, `altbuild.sh`).

## Werdykt

**Wszystkie wyniki są statyczne (ISA, gfx1100). Pomiarów na GPU nie ma**: sesja A (greedy md5, tg128 ABBA) była w kolejce na lock, gdy Main zatrzymał całą pracę na GPU. Żaden punkt nie jest więc adoptowany. Każdy czeka na pomiar ABBA.

| # | temat | wynik statyczny | stan |
|---|---|---|---|
| 1 | MMVQ n=1 na loaderze buforowym (`GGML_HIP_MMVQ_N1_WIDE`) | Q4_K: 18 → 12 ładowań/it.; przy `=2` pętla bez `vmcnt(0)` (min `vmcnt(7)`), 36 → 52 VGPR, nadal 16 fal | zakodowane, domyślnie wyłączone; **niezmierzone** |
| 2 | Q4_K ncols=5: 140 VGPR → ≤120 | `waves_per_eu(12)` + `amdgpu_num_vgpr(120)`: **119 VGPR, 12 fal, 0 scratch**. Sam `waves_per_eu` tego nie daje | przepis znany, kod nie wprowadzony; **niezmierzone** |
| 3 | Q6_K b128 dla 2–6 kolumn (`MMVQ_Q6K_NI=4`) | n=4: 98 → 95 VGPR, 12 → 16 fal; n=5/n=6: b64 → b128, fale bez zmian (5/7); n=2: 84 → 103 VGPR, 16 → 12 fal | zmienia kolejność sum (nie bitowo); **niezmierzone** |
| 4 | `flash_attn_ext_f16<256,256,32,2>` | Prefill Qwena na XTX naprawdę wybiera ten kernel (GQA 6 → ncols2=2, ncols1=32). W topce: **256 VGPR, 220 spillowanych, 512 B scratch, 314 `scratch_load` w pętli KV**. Żaden wariant configu nie usuwa spilli. `nbatch_fa=32`: scratch 512 → 192 B | **udziału nie zmierzono** (profil był w sesji B) |

## Liczby (ISA, `isa_kstat.py` + komentarze kompilatora `; NumVgprs/; Occupancy`)

**(1) MMVQ n=1, n1_rows=2, bez fuzji** (ładowania statycznie w kernelu; „pętla” = steady state z `loopwait.py`):

| kernel | VGPR / fale | b128 / b32 / sub | `vmcnt` w pętli |
|---|---|---|---|
| Q4_K domyślny | 36 / 16 | 0 / 12 / 6 global | 17 → … → **0** w każdej iteracji |
| Q4_K `WIDE=1` | 39 / 16 | 2 / 8 / 2 buffer | → 0 |
| Q4_K `WIDE=2` (ping-pong + bariery) | 52 / 16 | 6 / 24 / 6 (prolog + 2 it.) | **min 7**, brak `vmcnt(0)` |
| Q5_K domyślny / `=2` | 43 / 16 → 64 / 16 | 0/16/6 → 6/36/6 | → 0 / (przed barierami jeszcze 0) |
| Q6_K domyślny / `=2` | 30 / 16 → 43 / 16 | 0/8/6 → 0/18/12 (+6 b64) | → 0 / (j.w.) |
| Q4_K z fuzją gate: domyślny → `=2` | 40 → 81 / 16 | 0/21/12 → 12/39/6 | → 0 / min 12 |

- Bitowo: x i y idą przez te same lany i w tej samej kolejności sum co `vec_dot_q4/5/6_K_q8_1`. Przy `=2` lany za końcem wiersza pomijają dodawanie przez select (`valid ? tmp+d : tmp`). Bitowej równości na GPU nie sprawdzono.
- Właściwego b128 na `qs` przy n=1 nie da się uzyskać bitowo: wątek upstream czyta 2 inty oddalone o 16 B. b128 obejmuje tylko nagłówek dm+scales.
- Lekcja ISA: (a) przepisanie `w = wn` w pętli wymusza `vmcnt(0)`, bo kompilator kopiuje rejestry. (b) Ping-pong z dywergentnym `break` daje to samo, bo LLVM przesuwa prefetch pod `break`. (c) Pomaga dopiero jednolita dla fali liczba iteracji (`readfirstlane`) plus `asm volatile("":::"memory")` i `__builtin_amdgcn_sched_barrier(0)` po prefetchu.

**(2) Q4_K ncols=5 / 6:**

| wariant | n=5 VGPR / fale / scratch | n=6 |
|---|---|---|
| topka (`MMVQ_R3_WAVES_KQ=10`) | 140 / 10 / 0 | 142 / 10 / 0 |
| `waves_per_eu` 12 | 121 / **10** / 0 | 119 / 12 / 0 |
| `waves_per_eu` 13 albo 14 | 93 / 16 / 0 (ściśnięte; komentarz w kodzie mówi, że to wolniej) | 119 / 12 |
| **12 + `amdgpu_num_vgpr(120)`** | **119 / 12 / 0** | 120 / 12 / **20 B scratch** (limit tylko dla n=5) |

**(4) FA `<256,256,32,2,false>` (ncols=64), warianty `GGML_HIP_FA256_N64_CFG` (nthreads, occ, nbatch_fa, K2, V2, combine, stages, Q_in_reg):**

| config | VGPR | scratch B | VMEM b128 | LDS ops |
|---|---|---|---|---|
| topka `256,2,64,64,64,64,1,false` | 256 | 512 | 96 | 2192 |
| A `…,32,64,64,64,…` (nbatch_fa 32) | 256 | **192** | 48 | 1455 |
| B `…,64,32,32,32,…` | 256 | 484 | 96 | 2320 |
| C `…,32,32,32,32,…` | 256 | 384 | 48 | 1583 |
| D `128,…` (4 fale) | 256 | 812 | 192 | 3527 |

Spille siedzą w pętli KV: 314 `scratch_load` / 51 `scratch_store` na głębokości 1, przy 320 WMMA. W `cf397468e` przeniesiono już Q do LDS, a spill został. Akumulator VKQ (8 kafli × 8 VGPR) nie jest więc jedyną przyczyną; resztę daje rozwinięta pętla po DV=256 i hoisting ładowań z LDS `[INFERENCE]`. Udział FA w prefillu ~26% przy 94k pochodzi z wcześniejszych pomiarów (`qwen-opt/research/v2/rr-prefill-kv.md:199-203`), nie z tego testu.

## Adopt / kill

- **Nic nie adoptuję.** Kod jest domyślnie wyłączony, więc greedy md5 przy off nie może się zmienić: ścieżka off to ta sama instancja szablonu, `n1_wide=0`. Topki nie przebudowywać.
- Nic nie zabijam, bo nic nie zmierzyłem. Kryteria kill z 23b obowiązują dalej: (1) kernel < 3% szybszy albo plain tg128 < +0.7%; (2) weryfikacja < +1%; (3) < +0.5% spec_sweep; (4) wariant A wolniejszy w pp4096 / pp512@d32k.

## Nie zrobione (GPU wstrzymane)

1. Sesja A (`~/wt/mmvq2-tools/sessA.sh`, binarki `~/wt/mmvq2/build-hip/bin` są gotowe): greedy md5 Qwen plain+MTP przy `WIDE=2` (oczekiwane c4708318 / 6f14e814), plain przy `WIDE=1`, LFM przy `WIDE=2` (894e56e4). Do tego tg128 ABBA 0/2/1/2/0 dla Qwena i LFM (`taskset -c 2-5`).
2. Profil FA (`fa_prof.sh`: pp4096 i pp512@d32k pod rocprofv3) oraz `prof_sum.py`, żeby poznać udział `<256,256,32,2>`.
3. Alternatywna biblioteka z wariantem A FA i `MMVQ_Q6K_NI=4` (`altbuild.sh` przekompilowuje tylko `mmvq.cu.o` i instancję FA i linkuje `~/wt/mmvq2-alt/lib`). Przerwana po pauzie; rbuild zwrócił „/root/bf/repo.git does not appear to be a git repository”.
4. Klif n=5 jako przełącznik w kodzie (`amdgpu_num_vgpr` per typ/ncols) i Q5_K n=5. Q6_K `NI=4` wymagałby parametru szablonu, bo dziś to makro globalne.

## Do bazy wiedzy

- gfx1100: samo `amdgpu_waves_per_eu(1,12)` nie gwarantuje 12 fal. Q4_K n=5 dostaje 121 VGPR (10 fal). Działa dopiero `amdgpu_num_vgpr(120)` razem z `waves_per_eu(12)`: 119 VGPR, 12 fal, 0 spilli. Przy 13 lub 14 falach kompilator skacze do 93 VGPR.
- `; Occupancy` kompilatora uwzględnia też maksimum z `waves_per_eu`: przy samym `num_vgpr(120)` i limicie 10 fal pokazuje 10.
- Prefetch w pętli HIP: kopiowanie `w = wn` daje `vmcnt(0)`. Ping-pong potrzebuje jednolitej dla fali liczby iteracji (bez dywergentnego `break`) oraz `asm volatile("":::"memory")` + `sched_barrier(0)`, inaczej LLVM przesuwa ładowania z powrotem pod użycie.
- MMVQ n=1 nie może bitowo przejść na b128 dla `qs` (lane czyta int i int+16 B). Wąskie gardło bitowego wariantu to liczba instrukcji i `vmcnt`, a nie szerokość.
- `flash_attn_ext_f16<256,256,32,2>` to kernel prefillu Qwena na XTX: 220 VGPR spillu, 512 B scratch, spille w pętli KV. `nbatch_fa=32` zmniejsza scratch do 192 B; zmiana nthreads albo K2/V2 nie pomaga.
