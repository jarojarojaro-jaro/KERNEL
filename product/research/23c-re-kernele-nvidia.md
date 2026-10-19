# 23c — RE kerneli NVIDIA (cuBLAS/cuBLASLt, FlashInfer, Marlin, exllamav3, FA2) vs nasz ggml-cuda

Data: 2026-10-19. Tylko CPU (cuobjdump/nvdisasm z Tritona, nvcc 12.8). Bez pomiarów GPU.

## Werdykt
Dekodowanie u vendorów nie ma „magicznej” instrukcji, której nam brakuje. Są trzy konkretne różnice w gorącym `mul_mat_vec_q` (MMVQ):
1. **Brak triggera PDL.** W SASS jest `ACQBULK` (`griddepcontrol.wait`), ale nie ma `PREEXIT` (`launch_dependents`). Potwierdza to 21b §3.2 już na poziomie binarki.
2. **Brak cache hintów przy strumieniu wag.** cuBLASLt gemvx ma średnio ~89 `LDG.E.EF` na kernel, a exllamav3 czyta wagi przez `LDG.E.EF`. Nasze MMVQ ma 0 hintów.
3. **Wagi ładowane 32-bitowo.** Dla Q4_K jest ok. 55 `LDG.E` (32 b) na kernel, zero `LDG.E.128`. Vendorzy też często tak robią (exl3: 73 LDG.32), więc to najsłabsza z trzech różnic.

Do ścieżki decode nie ma co brać: cp.async/LDGSTS, `.L2::256B`, LDSM ani split-K/stream-K. Te mechanizmy mamy już w MMQ i FA-mma (LDGSTS 71/kernel). W GEMV przy batch 1 opłaca się to tylko w Marlinie, który ma kafelki MMA.

## Tabela (średnio na funkcję; sm_120a, w nawiasie sm_86)
| kernel | n | regs med | LDG.32 | LDG.128 | EF hint | LDGSTS | MMA | PRMT/LOP3 | PREEXIT/ACQBULK | źródło |
|---|---|---|---|---|---|---|---|---|---|---|
| nasz MMVQ Q4_K | 20 | 111 (100) | 55.8 | 0 | 0 | 0 | 0 | 4.4/46.8 | **0**/1.0 | `csv/ggml_sm_120a.csv`, `ggml_sm_86.csv` |
| nasz MMVQ wszystkie | 654 | 87 (80) | 34.2 | 0 | 0 | 0 | 0 | 17.8/54.3 | 0.1/0.7 | jw. |
| nasz MMVF | 352 | 40 | 15.8 | 0 (LDG.64 19) | 0 | 0 | 0 | — | 1.0/1.0 | jw. |
| nasz FA vec | 48 | 236 (201) | 4 | 20.6 | 0 | 0 | 0 | 78/57 | 1.0/0.8 | jw. (LDL 7.9 = spill) |
| cuBLASLt gemvx (fp16) | 288 | 128 | 1.5 | 0 | **89.2** | 0 | 0 | 0/11 | 0/0 | `csv/lt_gemvx_…746.sm_120.csv` |
| FlashInfer decode (fp16 KV) | 42 | 71 (64) | 11.8 | 1.3 | 0 | 12.0 | 0 | 47/144 | 1.0/1.0 | `csv/fi_decode_sm120a.csv` |
| exllamav3 gemm/gemv | 1197 | 128 | 72.9 | 1.0 | 3.2 | 12.1 | 16.5 | 52/412 | 0/0 | `csv/exl3_sm_120.csv` |
| exl3 gemv k4 (pojedynczy) | 1 | — | — | — | 16 `LDG.E.EF` | 0 | 16 HMMA | 56/115 + 64 IDP.4A.U8 | 0/0 | `sass/exl3_gemv_k4_sm120.sass` |
| Marlin sm120 k8 | 1 | — | — | 4 | 0 | 43 `LDGSTS.BYPASS.128` | tak | — | 0/0 | `sass/marlin_sm120_k8.sass` (split-K przez `ATOM`/`REDG` + lock) |
| vLLM gptq/awq (sm_86) | 49 | 71 | 9.5 | 2.9 | 0 | 0 | 0.5 | 26/102 | — | `csv/vllm_C_sm_86.csv` |

Mapowanie PTX→SASS ustalone na kernelach kalibracyjnych (`calib/calib.cu`, `calib_sm{86,120a}.sass`):
- `ld.global.L1::evict_first` → `LDG.E.EF`; `evict_last` → `.EL`; `L1::no_allocate` → `.NA`; `.nc` → `.CONSTANT`;
- `L2::256B` → `.LTC256B`; `prefetch.global.L2` → `CCTL.E.PF2`;
- `griddepcontrol.launch_dependents` → `PREEXIT`; `griddepcontrol.wait` → `ACQBULK`; `cp.async.bulk.prefetch.L2` → `UBLKPF.L2` (tylko sm_120a);
- `cp.async…L2::128B` → `LDGSTS.E.BYPASS.LTC128B.128`.

Liczniki policzył `~/KERNEL/tools/re/sass_mix.py`. Agregację zrobił skrypt `~/qwen-opt/re/nv/csv/nvsum.py`; jego wynik jest w `csv/nvsum.out`.

## Kandydaci (ranking dla 3090 / 5060 Ti / 5090)
| # | zmiana | karty | szac. | koszt | kryterium kill |
|---|---|---|---|---|---|
| 1 | `ggml_cuda_pdl_lc()` na starcie gęstego MMVQ + `prefetch.global.L2` (lub `UBLKPF`) pierwszych wag przed `pdl_sync` (= 21b E1) | 5060 Ti, 5090 (sm_90+; 3090 nie ma PDL) | 21b: +1–4.5% / +3–11% LFM `[SZACUNEK]` | 1–2 dni | <+1% tg na 5060 Ti przy md5 bez zmian |
| 2 | `ld.global.L1::evict_first` (lub `L1::no_allocate`) na wagach MMVQ, `evict_last` na wektorze q8_1 (wzorzec cuBLASLt i exl3) | wszystkie | `[INFERENCE]` 0–2%: hint dotyczy L1, a ruch decode to głównie DRAM | 0.5 dnia | <+0.5% lub regres na 3090 |
| 3 | prefetch L2 w pętli MMVQ poza DGX Spark dla 2–8 kolumn (= 21b E4; upstream GB10 +2.9…6.2%) | 3090, 5060 Ti | 0…+3% weryfikacji `[SZACUNEK 21b]` | 0.5 dnia | <+1% przy 4–5 kolumnach |
| 4 | szersze ładowanie wag Q4_K (64/128 b na wątek, mniej LDG na bajt) | wszystkie | `[INFERENCE]` niepewne; exl3 też używa 32 b | 1–2 dni | brak zysku w ncu `dram__throughput` |
| 5 | FA vec: spill (LDL ~8/kernel, 236 regs na sm_120a) | 5060 Ti/5090, długi kontekst | `[INFERENCE]` mały | 1 dzień | brak LDL po zmianie i <1% |

Odrzucone: split-K/stream-K w MMVQ (Marlin robi to atomikami dla małych N×duże K; nasze MMVQ i tak ma siatkę ≥ wierszy); TMA/`UTMALDG` (brak w gemvx i decode kernelach sm_120 z cuBLASLt 12.8); LDSM/HMMA w GEMV batch 1 (exl3 używa HMMA tylko do redukcji).

## Do bazy wiedzy
- SASS MMVQ (sm_120a) zawiera `ACQBULK` bez `PREEXIT`: PDL działa tylko po stronie czekania. Źródło: `~/qwen-opt/re/nv/csv/ggml_sm_120a.csv`, `sass/ggml_mmvq_q4k_n1_sm120a.sass`.
- cuBLASLt 12.8.5 gemvx (sm_86 i sm_120) czyta strumień przez `LDG.E.EF` (~89 na kernel) i nie ma PDL ani prefetchu L2. Źródło: `csv/lt_gemvx_*`.
- exllamav3 1.6.3: gemv k4 = `LDG.E.EF` + `IDP.4A.U8` + HMMA do redukcji. Źródło: `sass/exl3_gemv_k4_sm120.sass`.
- Mapowanie PTX→SASS (EF/EL/NA/LTC256B/PREEXIT/ACQBULK/UBLKPF/CCTL.E.PF2). Źródło: `~/qwen-opt/re/nv/calib/`.
- Narzędzie: `~/KERNEL/tools/re/sass_mix.py` (CSV z miksem instrukcji i regs/smem z `cuobjdump -res-usage`).
