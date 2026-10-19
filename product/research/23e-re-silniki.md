# 23e. RE kerneli konkurencyjnych silników (decode) – werdykt

Data: 2026-10-19. Tylko CPU (kompilacja ISA/SASS, czytanie kodu i dokumentów). Notatki z dowodami: `~/qwen-opt/re/engines/{hipfire,tqllm,magnitude,strata-tf}/NOTES.md`.

## Werdykt
**Żaden konkurent nie ma lepszej pętli GEMV niż nasza.** Przewaga hipfire (54.3 vs 43.2 t/s na XTX) wynika głównie z mniejszej liczby bajtów (format 4.25 bpw) i fuzji, a nie z ISA. Do przeniesienia są dwa tanie pomysły dla GDN (stan Q8, rollback przez replay) oraz jeden tylko dla NVIDIA (MMVQ_IL).

## Liczby
| pomiar | hipfire | nasz | źródło |
|---|---|---|---|
| tg 27B XTX | 54.3 t/s, krok 19.67 ms | 43.2 t/s, 23.15 ms | 30-hipfire.md:75; REKORDY (tg128) |
| bajty/token | ~14.3 GB (plik 14.99 GB, 4.25 bpw) | 16.83 GB | hipfire CHANGELOG (H2); REKORDY |
| narzut ponad ideał przy 960 GB/s | 4.8 ms | 5.6 ms | obliczenie |
| pętla GEMV n=1 (32 wagi/lane) | 138 VALU, 8×b128 (x fp32) + 4×b32 | 61 VALU (8 v_dot4), 9×b32 + 3×d16 | isa_mix na `hipfire/isa/s/gemv_mq4g256v2.s` oraz `magnitude/ours/mmvq_q4k.s` |
| VGPR / fale | 76 / 16 | 16 fal | `hipfire/isa/kstat.txt` |
| redukcja | ds_bpermute×4 + swizzle | ds_bpermute×5 | j.w. |
| stan GDN | int8 + skale | fp32 | `gdn_q8_compact3_b2` (kstat) |

Rozbicie różnicy 3.5 ms: ~2.7 ms to bajty (2.5 GB mniej), ~0.8 ms to rzeczy spoza GEMV (fuzje rmsnorm+rotate w prologu, qkvza w jednym GEMV, moe_down+combine+rmsnorm, conv1d+silu+qknorm). Kernargi PM4 w VRAM (+7.2% u nich) już mamy (wiki/rocm/pm4.md:17).

## Ranking działań (arytmetyka)
1. **GDN: rollback przez replay zamiast snapshotów (Strata)** – do K snapshotów po 151 MB [INFERENCJA: 48 warstw GDN × 48 h × 128² × 4 B] ≈ 0.6 GB/krok → ≤0.63 ms z 27.7 ms ≈ **do +2% MTP**. Bitowo możliwe. Test: rocprof kroku weryfikacji. Kryterium porzucenia: zysk < 0.3 ms.
2. **GDN: stan Q8 (hipfire)** – 302 MB → ~76 MB r+w na token ≈ −0.24 ms ≈ **+1% tg** (więcej, jeśli łączone z 1). Ryzyko jakości: wymagany KLD. Kryterium porzucenia: ΔKLD > 0.005 albo < +0.7%.
3. **Fuzje poza GEMV (hipfire)** – górna granica ~0.8 ms ≈ +3.5% tg. Najpierw porównać listę kerneli na token z ich listą (603 dispatchy dla modelu MoE). Kryterium porzucenia: rocprof pokazuje < 0.3 ms w małych kernelach.
4. **MMVQ_IL (Strata), tylko NVIDIA** – +4.2% sm_86 i +1.3–2.2% sm_120 (strata/method.md:103). Na XTX nie dotyczy (K1 używa b128+DPP).
5. Format ~4.25 bpw – największy efekt (~+15% tg), ale to decyzja jakościowa i kwantyzacyjna, nie kernel. Poza zakresem tego raportu.

Odrzucone: tqLLM (plain 77% pasma = parytet), HyperQwen (GEMV = Marlin), Magnitude (na XTX przegrywa 1.4–2.2×, 16j:10-13), TensorFold (HIP zamrożony), Maya (brak pomiarów XTX, 21g). Mirai i inferrous: lokalnie brak kodu kerneli.

## Do bazy wiedzy
- hipfire GEMV MQ4G256V2: 1 wiersz na falę32, x w fp32, 138 VALU na 32 wagi/lane, 76 VGPR, 16 fal; nie jest lepsza w ISA od naszego q4_K (61 VALU) – `~/qwen-opt/re/engines/hipfire/NOTES.md`.
- Różnica 54.3 vs 43.2 t/s: ~2.7 ms z bajtów (14.3 vs 16.83 GB), ~0.8 ms z fuzji; narzut 4.8 vs 5.6 ms – j.w.
- Stan GDN Q8 oszczędza ~0.24 ms/token (~1% tg) na 27B – j.w.
- Rollback GDN przez replay: ≤0.63 ms/krok MTP4 (≤2%) – `~/qwen-opt/re/engines/strata-tf/NOTES.md`.
- Magnitude, tqLLM, HyperQwen: brak kerneli decode do przeniesienia – NOTES w `~/qwen-opt/re/engines/`.
