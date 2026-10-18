# 16g — Pasmo kerneli MoE LFM2.5 na RX 7900 XTX (gate_up / down / gęste projekcje)

Stan: **WERSJA ROBOCZA, praca wstrzymana 2026-10-18 (restart serwera).** Brakuje: ABBA llama-bench (3 z 12 przebiegów), greedy md5 i spec_sweep z nowym przełącznikiem. Wszystko inne poniżej jest zmierzone.

Worktree `~/wt/lfmmoe`, gałąź `opt-lfmmoe` od `amd-opt` @ f61994f58, commit `6ccf30b33` (WIP). Narzędzia i surowe wyniki: `~/wt/lfmmoe-prof/` (kopia przebiegów z /tmp w `frozen/`).

## Kryterium zabicia (ustalone przed pomiarem in-model)
Zmiana zostaje, jeśli llama-bench tg128 ABBA (3 rundy, KV q8_0) daje ≥ +0.7% t/s (≈ połowa przewidywanych −49 µs/token) przy niezmienionych hashach logitów i greedy md5 `894e56e4`. Inaczej: wynik negatywny, przełącznik domyślnie wyłączony albo commit wycofany.

## 1. Profil per kernel (ten build = produkcja, PM4 trace `GGML_HIP_PM4_DEBUG=3` i rocprofv3 z `GGML_HIP_PM4=0`)
Bajty z nagłówka GGUF (aktywni eksperci 4/64). „PM4” = koniec poprzedniego dispatchu → koniec tego (z granicą); „rp” = czas samego kernela. Źródło: `~/wt/lfmmoe-prof/base_tr_1.txt`, `base_rp_1.txt`.

| kernel | MB | wywołań/token | PM4 µs | GB/s | rp µs | GB/s | ideał 900 GB/s µs | narzut µs/token |
|---|---|---|---|---|---|---|---|---|
| eksperci gate+up Q5_K (fuzja SWIGLU + q8_1) | 17.30 | 38 | 25.72 | 673 | 25.16 | 688 | 19.22 | 247 |
| in_proj+conv Q5_K 6144×2048 | 8.65 | 29 | 14.60 | 593 | 14.28 | 606 | 9.61 | 145 |
| eksperci down Q5_K + ważenie + residual | 8.65 | 19.8 | 13.04 | 663 | 12.68 | 682 | 9.61 | 68 |
| eksperci down Q6_K + ważenie + residual | 10.32 | 16.8 | 15.12 | 683 | 14.76 | 699 | 11.47 | 61 |
| głowica Q6_K 128000×2048 | 215.04 | 1 | 240.64 | 894 | 238.40 | 902 | 238.93 | 2 |
| out_proj / attn_output Q5_K 2048×2048 (+ADD) | 2.88 | 39 | 5.56 | 519 | 5.16 | 559 | 3.20 | 92 |
| gęste gate+up Q5_K 2×11776×2048 | 33.16 | 2 | 43.10 | 769 | 42.82 | 774 | 36.85 | 13 |
| gęste down Q6_K 2048×11776 | 19.78 | 2 | 26.68 | 742 | 26.60 | 744 | 21.98 | 9 |
| attn q Q5_K 2048×2048 `[INFERENCE: klasa po siatce]` | 2.88 | 11 | 6.00 | 481 | 5.68 | 508 | 3.20 | 31 |
| attn k Q5_K 512×2048 | 0.72 | 15 | 3.24 | 222 | 2.88 | 250 | 0.80 | 37 |
| attn v Q6_K 512×2048 | 0.86 | 5 | 3.92 | 219 | 3.60 | 239 | 0.96 | 15 |
| **suma matvec** | | | **2644** | | | | **1926** | **718** |

Zgadza się z 15a (narzut 698 µs). Największe pozycje: gate+up ekspertów 247 µs, in_proj+conv 145, out_proj 92, down 129.

ATT (thread trace) działa na gfx1100 w ROCm 10.0 (`rocprofv3 --att --att-target-cu 1 --att-simd-select 0 --kernel-include-regex … --kernel-iteration-range …`, `GGML_HIP_PM4=0`; skrypt `att_model.sh`, parser `attsum.py`). Wyniki in-model (jeden SIMD jednego CU, mediany fal):
- gate+up: 16 fal, prolog 1.6k cykli, ładowania 37.9k, po ostatnim ładowaniu 4.3k; **85% latencji w `s_waitcnt vmcnt`** → ograniczenie latencją pamięci (za mało ładowań w locie na falę), nie ALU (VALU 7.5%);
- down Q5_K/Q6_K: 33–43% latencji to samo wydawanie instrukcji VMEM (kolejka żądań pełna: dużo małych ładowań `b32`/`d16`), 37–45% `s_waitcnt vmcnt`;
- in_proj+conv: 75–83% `s_waitcnt vmcnt`.
W mikrobenchu ATT pokazał koszt ogona q8_1 w gate+up: `s_waitcnt_vscnt` (fence) 1.7k cykli + powrót atomika ticketu 2.6k cykli na falę.

Liczniki pod `amd-smi set --perf-level STABLE_STD`: pominięte — `/sys/class/drm/card0/device/power_dpm_force_performance_level` jest `-rw-r--r-- root` (bez sudo się nie da, a zmiana poziomu zakłóciłaby pomiary innych agentów).

## 2. Dlaczego gate+up i down nie dobijają do pasma (mikrobench `moebench.hip`)
Replika kerneli produkcji (te same `vec_dot_*_q8_1`, linie, kolejność sum, butterfly), kształty LFM, zimne wagi (losowi eksperci z 6 warstw), rocprofv3, czasy kerneli, 3 osobne procesy (`rep.sh`, `rp_r6_{1,2,3}.txt`; µs):

| wariant gate+up (17.30 MB, 4 eksperci) | proces 1 | 2 | 3 | bitowo |
|---|---|---|---|---|
| replika produkcji: 2 wiersze/falę, 768×4 bloków po 1 fali, ogon q8 z ticketem | 24.16 | 23.64 | 24.04 | = |
| to samo bez ogona q8 | 23.46 | 22.56 | 24.00 | — |
| prefetch surowych wag następnej iteracji | 23.04 | 23.16 | 23.00 | tak |
| 16 fal/blok = 32 wiersze = 1 grupa q8, ogon z LDS (bez fence/ticketu) | 23.32 | 23.48 | 23.24 | tak |
| **16 fal/blok + prefetch** | **22.32** | **22.52** | **22.28** | **tak** |
| 16 fal/blok + wszystkie ładowania na start | 22.28 | 22.28 | 22.24 | tak |
| 16 fal/blok, pętla rozwinięta bez prefetchu | 24.28 | 24.26 | 24.24 | tak |
| idealny odczyt tym samym wzorcem (2 wiersze × gate/up, 768×4 bloków, ładowania 16 B) | 24.40 | 22.36 | 24.44 | — |
| idealny odczyt, 4 wiersze/blok (384×4) | 19.68 | 19.68 | 19.68 | — |
| idealny odczyt ciągły, 768 / 3040 / 3072 bloków | 20.3 / 20.1 / 21.8–23.9 | | | — |

Wcześniejsze rundy (`mb3.txt`, `rp4`, `rp5`): 1, 3, 4, 8 wierszy na falę, 2–8 fal na blok bez zmiany ogona — wszystkie wolniejsze albo równe 2 wierszom (4 wiersze bez ogona 23.80 vs 22.64; 4 wiersze z prefetchem 35.9 — za dużo VGPR); ładowania 16 B przez LDS 40–52 µs (bariera co iterację; odrzucone).

Wnioski:
1. **Sufitem jest wzorzec dostępu, nie arytmetyka q8_1 ani gather.** Ten sam wzorzec bez żadnych obliczeń (2 wiersze gate + 2 up po 1408 B na blok, 3072 fale) czyta 17.30 MB w 22.4–24.4 µs, bimodalnie jak „slow mode” z rundy 4 (3072 jednofalowe bloki = pełna pojemność GPU). 4 wiersze na blok: 19.68 µs stabilnie (879 GB/s). Kernel liczący przy 4 wierszach traci jednak na latencji łańcucha zależności i rejestrach.
2. Ogon q8_1 (fence + atomik + ponowne czytanie grupy) kosztuje ~0.6–1 µs na wywołanie; prefetch ~1 µs. Razem z blokiem jednej grupy q8: −1.5…−1.7 µs (−7%).
3. Za mało bloków na eksperta / ogon fali: nie — 4 eksperci × 768 bloków wypełniają GPU z nawiązką; problemem jest zbyt dużo krótkich strumieni, nie za mało pracy.
4. Down: replika produkcji Q5_K 11.64 µs vs idealny odczyt 10.4–10.6 (≈90% sufitu wzorca). Ekspert na falę (4 fale/blok, LDS): 11.56 (bez zysku). Dla Q6_K produkcja ma **2 fale na wiersz** (`calc_nwarps` RDNA3 Q6_K = 2), więc wariant „ekspert na falę” (13.16 vs moja replika 1-falowa 14.12) nie jest bitowy wobec produkcji; wersja bitowa (8 fal/blok) niezbudowana, sufit ≤ 1 µs × 16.8 ≈ 17 µs/token (0.5%).

## 3. Implementacja: `GGML_HIP_MOE_GU_BLOCK` (commit 6ccf30b33, domyślnie wł., `=0` wyłącza)
`mul_mat_vec_q_moe_gate_up_q5k<8>` w `mmvq.cu`: RDNA3, jeden token, Q5_K, K = 2048, SWIGLU bez biasów, z kopią q8_1 (GGML_HIP_GATE_UP_Q8). Blok 16 fal liczy 32 wiersze jednej grupy q8_1 (każdy wiersz jak kernel 2-wierszowy), surowe wagi następnej iteracji ładowane przed bieżącym iloczynem, wynik grupy przez LDS i jedną barierę, bez fence i ticketu. Inne typy i kształty idą starą drogą.

Weryfikacja: hashe logitów 64 kroków bez zmian przy obu ustawieniach (`frozen/check1.txt`): LFM d0 `a7ce25b73f887fed`, d3000 `b47452b9380b665b`, Uncensored d0 `f74300e3142a5535`; taśma PM4 nadal 304 dispatche/token.

In-model, PM4 trace, 2 procesy na ustawienie (`frozen/lfm_sw{0,1}_{1,2}.txt`):

| | GU_BLOCK=0 proc. 1 | proc. 2 | GU_BLOCK=1 proc. 1 | proc. 2 |
|---|---|---|---|---|
| gate+up µs/wywołanie | 25.36 | 27.24 (slow mode) | 24.84 | 25.00 |
| out_proj (1024 bloki) µs | 5.48 | 5.48 | 5.76 | 5.84 |
| down Q5_K / Q6_K µs | 12.92 / 14.92 | 13.00 / 14.96 | 13.12 / 15.00 | 13.20 / 15.12 |
| taśma µs/token | 3190 | 3268 | 3227 | 3259 |

Nowy kernel usuwa bimodalność gate+up między procesami (25.4/27.2 → 24.8/25.0), ale inne kernele zwalniają (out_proj +0.3 µs × 39) — ten sam objaw co przy 3 wierszach w rundzie 4 (hipoteza: limit 285 W). Na 2 procesach wynik taśmy jest niejednoznaczny. ABBA llama-bench: przerwane po 3 przebiegach (A 285.44, B 288.92 / 291.23 t/s) — za mało, nie liczyć.

## 4. LFM Uncensored
Ten sam przełącznik obejmuje 33 warstwy z gate/up Q5_K (5 warstw Q6_K idzie starą drogą). Hash logitów bez zmian. Pomiar prędkości: czeka na ABBA.

## 5. Do dokończenia po restarcie
Komendy w `~/KERNEL/STAN-PRAC.md` (sekcja XtxLfmMoe): ABBA 3 rundy LFM + 2 Uncensored, greedy md5, spec_sweep ABBA, test-backend-ops MUL_MAT/MUL_MAT_ID, decyzja wg kryterium.

## Do bazy wiedzy
(do uzupełnienia po pomiarach; patrz wersja końcowa)
