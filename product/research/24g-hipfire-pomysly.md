# Raport 24g: pomysły z hipfire (kwant ~4.25 bpw, fuzje małych kerneli, stan GDN int8)

Data: 2026-10-19. XTX (gfx1100), Qwen3.8-27B UD-Q4_K_XL, build topka (PM4=0). Nocny przebieg w chmurze przepadł (pod
zamknięty, wyników nie zebrano); część powtórzona lokalnie, resztę uciął użytkownik (decyzje niżej).

## Werdykt

| # | Pomysł | Status | Wynik |
|---|---|---|---|
| 1 | IQ4_XS / IQ4_NL / Q4_K_S zamiast UD-Q4_K_XL (KLD vs Q8_0) | **porzucony (decyzja użytkownika: nie zmieniamy kwantów)** | brak pomiaru; łącze ~1 MB/s (Q8_0 29 GB ≈ 8 h), lokalnie brak Q8_0/BF16 |
| 2 | Fuzje małych kerneli (norm+rotate w prologu GEMV, qkvza jednym GEMV, moe_down+combine) | **otwarte, próg 0.3 ms spełniony tylko przez normy (górna granica)** | pomiar ABBA przerwany (pauza GPU) |
| 3 | Stan GDN w int8 (symulacja fake-q8 per kolumna) | **KILL** | wiki: KLD 0.0234 ± 0.0028 (próg ≤ 0.005), top-1 94.72 % |

## Liczby

Profil dekodu (rocprofv3 kernel-trace, llama-bench -p 0 -n 64, KV q4_0, topka; 48 tokenów po odcięciu 25 %; pod
profilerem 37.7 t/s, czasy przerw zawyżone):

| Pozycja | launche/token | µs/token | µs/launch |
|---|---:|---:|---:|
| razem (wall) | 808 | 25 908 | — |
| busy | | 22 648 | |
| MMVQ (wszystkie typy) | 362 | 20 420 | 45–69 |
| poza MMVQ | 446 | 2 228 | |
| przerwy (profiler) | | 3 260 | |
| rms_norm_mul_f32_unrolled (+q8_1) | 129 | 685 | 5.31 |
| flash_attn_ext_kvq + combine | 32 | 485 | |
| gated_delta_net_cuda | 48 | 351 | 7.30 |
| gdn_conv_ab | 48 | 175 | 3.65 |
| rms_norm_mul_rope | 32 | 170 | 5.30 |
| set_rows q4_0 (KV) | 32 | 123 | 3.85 |
| unary_gated_op | 41 | 100 | 2.44 |
| rms_norm_mul_silu_gate | 48 | 78 | 1.63 |
| fwht (rotacja) | 32 | 41 | 1.28 |

Odwzorowanie listy hipfire na nasz graf:
- **rmsnorm+rotate w prologu GEMV**: normy 685 + 170 µs + fwht 41 µs = ~0.9 ms/token górnej granicy (bez kosztu prologu,
  który każda grupa GEMV musiałaby powtórzyć na 5120 elementach). Jedyny kandydat ≥ 0.3 ms.
- **qkvza jednym GEMV**: oszczędza tylko launch + ogon na warstwę GDN (48 × ~2–3 µs ≈ 0.1–0.15 ms) i wymaga jednego
  typu kwantu, a UD-Q4_K_XL miesza typy w tych tensorach → **poniżej progu, kill**.
- **moe_down+combine+norm**: model gęsty → nie dotyczy. **conv1d+silu+qknorm**: już zrobione (gdn_conv_ab, 175 µs).

Pozycja 3: fake-q8 zaokrągla stan przed każdym tokenem (także w prefillu, więc ocena pesymistyczna), ale KLD jest 4.7×
ponad progiem — zysk przepustowości nie ma znaczenia. Plus użytkownik wykluczył zmiany stratne.

## Nie zrobione (GPU wstrzymane / decyzje)
- Test górnej granicy norm: przełącznik `GGML_HIP_UB_SKIP_NORM=1` (pomija 129 normy, zły wynik, tylko czas) zbudowany
  w ~/wt/hipfire, skrypt `~/qwen-opt/hipfire/ub.sh` (tg128, ABBA ×3, taskset 2-5); przebieg zabity przy pauzie GPU,
  zero danych. Jeśli różnica tg < 0.3 ms/token → kill fuzji prologu; jeśli ≥ → implementacja bitowo zgodna (ta sama
  kolejność sumy kwadratów co `rms_norm_mul_f32_unrolled`, kwantyzacja q8_1 w LDS), md5 greedy, test-backend-ops.
- KLD fq8 na plprose/chat/code/long (tylko wiki; przerwane po decyzji o porzuceniu).
- Cała pozycja 1 (prędkość, KLD, polski) — porzucona; pobrane kandydaty usunięte z dysku.

## Pliki
- Skrypty: `~/qwen-opt/hipfire/{kld_fq8.sh,kld_q.sh,prof.sh,kpt.py,speed.sh,ub.sh}`; profil `logs/kpt.txt`, `logs/hold1.log`.
- Niezacommitowane eksperymenty (fq8 + UB skip) w ~/wt/hipfire, kopia: `~/qwen-opt/hipfire/hipfire-fq8-ubskip-wip.patch`.
  Nic nie przyjęte, topka bez zmian.

## Do bazy wiedzy
- Qwen 27B dekod (XTX, topka): 808 kerneli/token, MMVQ 20.4 ms, poza MMVQ 2.23 ms w 446 launchach; normy rms·mul
  129×5.3 µs = 0.69 ms to największy blok małych kerneli.
- Stan GDN int8 (per kolumna absmax, jak gdn_q8 hipfire): KLD 0.0234 na wiki vs fp32 → odrzucone.
- Fuzja qkvza: < 0.15 ms/token górnej granicy na Qwen 27B → nieopłacalna; moe_down fuzja nie dotyczy modeli gęstych.
- Łącze serwera ~1 MB/s (także przy 8 połączeniach): pobrania > 5 GB nierealne bez zgody użytkownika.
