# 21l — Reverse engineering kerneli GPU: co z awesome-reverse-engineering (i spoza niej) działa u nas

Data: 2026-10-19. Autor: podagenci ResAwesomeRE / ResAwesomeRE2. Tylko CPU, **zero GPU**. Skrypty, CSV i surowe wyniki: `21l-skrypty/`.
Oznaczenia: `[INFERENCE]` to wniosek, `[SZACUNEK]` to wycena, `[NIEZWERYFIKOWANE]` to rzecz niesprawdzona.

## 0. Werdykt

1. **Lista [morluto/awesome-reverse-engineering](https://github.com/morluto/awesome-reverse-engineering) (commit `2944962`) nie ma ani jednej pozycji GPU.** Grep `gpu|cuda|amdgpu|ptx|sass|shader|rocm|vulkan` daje tylko fałszywe trafienia. Pozycje sprawdzone, z wynikiem:
   - Ghidra: brak modułu AMDGPU i NVIDIA w `Ghidra/Processors`;
   - Capstone: brak `CS_ARCH_*` dla GPU;
   - REA: nie zna EM_AMDGPU ani EM_CUDA (raport [23a](23a-rea.md));
   - radare2 6.2.4: ma plugin `ptx` („sass”, sm_50–sm_110), ale ten sam kod sm_86 dekoduje inaczej niż nvdisasm (`lopc/brev` zamiast `IMAD.MOV/S2R`, niezależnie od `asm.cpu`). **Bezużyteczny**;
   - Compiler Explorer: CUDA/NVCC jest, języka HIP brak (`/api/languages`);
   - LIEF, Kaitai, ImHex, Construct, BinDiff, Frida, strace: tylko ogólne parsowanie ELF lub strona hosta, `llvm-readelf` robi to samo.
2. **Działający zestaw to narzędzia producentów i LLVM.** Każde z nich uruchomiłem lokalnie na CPU (tabela §1). Dały nowe liczby (§2), w tym jedną dźwignię dla verify MTP (A1) i offline'owy audyt taśmy PM4 dla raportu 17 (A2).

## 1. Narzędzia: działa na gfx1100 / konsumenckich NVIDIA?

| narzędzie | gfx1100 / sm_86–120 | co sprawdziłem (dowód) |
|---|---|---|
| `llvm-objdump --mcpu=gfx1100`, `llvm-readelf --notes`, `clang-offload-bundler` (ROCm LLVM) | tak / – | 7832 kernele z 140 obiektów `libggml-hip.so`; obsługa skompresowanych bundli CCOB (`co_stats.py`) |
| RGA 2.15 `-s bin --livereg --cfg` | tak (offline) | livereg MMVQ: `rga-livereg-mmvq-q4k-ncols5.txt`. Tryb SPIR-V to `-s vk-spv-offline` (README podaje błędną nazwę) |
| AMD machine-readable ISA XML + isa_spec_manager (MIT) | RDNA3 jest (`amdgpu_isa_rdna3.xml`, 1148 instrukcji, w paczce RGA) | dekoder do własnych narzędzi (bx-isa) |
| umr (zbudowany bez roota: `apt download` + `dpkg -x`) | tak, offline `-f gfx11_vm_test -df plik.bin` | dekoduje PM4, AQL i pola rejestrów gfx1100 (`umr-tape-wa*.txt`). **Nie** dekoduje słowa inicjatora `DISPATCH_DIRECT`; Mesa `ac_parse_ib.c` też nie ma dla niego `case` |
| rocprofv3 `--att` (thread trace) | tak, trace-only (wiki `narzedzia/att-gfx1100.md`) | stall na instrukcję; PMC=0, a PC sampling tylko Instinct/APU (wiki `rocm/rocprof.md`) |
| rocprof-compute (Omniperf) | **nie** (SoC: gfx90x/94x/950/115x/1250, bez gfx1100) | `rocprof_compute_soc/` w rocm-systems |
| ROCdbgapi/rocgdb | tak (gfx1100 w `architecture.cpp`) | debugger zmienia tryb trap/CWSR, więc zaburza H1′ z raportu 17 `[INFERENCE]` |
| moduł amdgpu: `vm_fault_stop`, `debug_evictions` (rw), `no_queue_eviction_on_vm_fault`, `cwsr_enable` | tak (`modinfo`) | parametry do testów S z raportu 17; wymagają roota |
| cuobjdump / nvdisasm / ptxas (CUDA 13.1, z wheela `triton`) | sm_86/89/120a | `-res-usage` na 7109 funkcjach sm_120a |
| NVBit 1.7 | SM 3.5–12.1 (README) | nieuruchamiany; licencja = EULA CUDA |
| CuAssembler / TuringAs / MaxAs | do sm_86 / sm_70–80 / Maxwell (archiwum) | sm_89/120 brak, więc **odrzucone** |

## 2. Liczby (CPU, statycznie)

| obiekt | wynik | źródło |
|---|---|---|
| nasze kernele gfx1100 (`~/llama-opt/lib/libggml-hip.so.0.26.0`) | 7832; prawdziwe spille w 165: 81 `flash_attn_ext_f16`, 25 `flash_attn_tile`, 8 `mask_to_KV_max`, 2 `fattn_vec`, 47 `mul_mat_q`, 1 MMVQ (Q2_K ncols=10), 1 rwkv; 2376 to stuby `NO_DEVICE_CODE` (40 VGPR, 16 B scratch, `s_swappc` do abort) | `ours-llama-opt-gfx1100.csv` |
| MMQ/MMVQ dla Q4_K/Q5_K/Q6_K | 67/67/56 kerneli, **0 spilli**; IQ4_XS (głowica): 2 spille (do 48 VGPR); najgorszy Q2_K mmq_x=48: 741 VGPR | j.w. |
| `flash_attn_ext_f16<256,256,…>` | 18 wariantów spilluje 179–318 VGPR (scratch 428–812 B) | j.w.; czy gfx1100 je wybiera: `[NIEZWERYFIKOWANE]` |
| **MMVQ Q4_K VGPR wg ncols** | 1: 26–53 · 2: 64–65 · 3: 76–77 · **4: 88–89 (16 fal/SIMD)** · **5: 140–141 (10 fal)** · 8: 190–191 | CSV; reguła fal = min(16, ⌊1536/⌈VGPR⌉₂₄⌋), zgodna z `; Occupancy` kompilatora i RGA („granularity 24”) |
| livereg MMVQ Q4_K ncols=5 | szczyt 136 żywych VGPR w bloku `v_dot4_i32_iu8` (l. 352–356), 208 linii ≥ 120; ISA 5220 B | `rga-livereg-mmvq-q4k-ncols5.txt` |
| hipBLASLt gfx1100 | 690 kerneli, 0 spilli, mediana 31 VGPR; small-N `MT64x16`/`MT32x16`: WMMA + `buffer_load_b128` + LDS; I8 `MT64x16x32`: 38× `v_wmma_i32_16x16x16_iu8`, 96 VGPR | `vendor-rocm-gfx1100.csv`, objdump |
| rocBLAS gfx1100 | 644 kerneli, 21 spilli (bf16 `MT64x1x64` GSU, 256 VGPR, spill 15) | j.w. |
| deskryptor MMVQ (`.kd`) | `rsrc1=0xe0af0011` → **PRIV=0**, `rsrc2` TRAP_PRESENT=0; taśma WA=2: PRIV=1, RESTART_X/Y/Z=0, IB CACHE_POLICY 3→0 | `pm4_synth_tape.py` + umr |
| nasz CUDA sm_120a (`~/wt/cuda-base`) | 7109 funkcji, LOCAL>0: **0**; MMVQ Q4_K ncols=1: 52–53 REG, ncols=5: 140 REG (≈14 warpów/SM `[SZACUNEK]`) | `cuobjdump -res-usage` |
| cuBLAS 12.8.5 sm_120 (tylko metadane) | 4623 funkcje, 103 gemv/dot, REG 32–120, LOCAL 0 | `cuobjdump -res-usage` |

## 3. Top 10 akcji (ranking: zysk × p / koszt)

| # | akcja | minimalny eksperyment | kill |
|---|---|---|---|
| A1 | **MMVQ ncols=5 ≤ 120 VGPR (10→12 fal) albo verify jako 4+1** | CPU: `__launch_bounds__`/`amdgpu_waves_per_eu(12)` dla ncols=5, `co_stats.py`, spill = 0. GPU: ABBA verify-step tg MTP n=4 | spill > 0 albo verify ≤ +2% |
| A2 | Audyt taśmy PM4 offline | `GGML_HIP_PM4_DUMP` (zrzut IB), potem `umr -O bits -df` w CI: PRIV=1, RESTART=0, polityka IB 0; inicjator sprawdzany własnym 10-liniowym checkiem | – (bramka, nie optymalizacja) |
| A3 | `co_stats.py` jako bramka builda | diff CSV przed/po łatce: spill/VGPR/fal per kernel (lekcja `lekcja-vgpr-limit-hak-spill`) | – |
| A4 | Które spillujące FA naprawdę działają | `rocprofv3 --kernel-trace` (PM4=0) + join z CSV | 0 trafień, więc temat zamknięty |
| A5 | ATT na MMVQ ncols=5 vs 4 | `rocprofv3 --att` na obu; stall `s_waitcnt vmcnt` vs zajętość | brak różnicy stall/fala |
| A6 | Wzorzec hipBLASLt small-N I8 WMMA dla szerokiego verify (≥16 tokenów) | regeneracja z otwartych YAML `navi31` (TensileLite, MIT, bez RE), bench N=8/16 vs MMVQ | wolniejsze przy N ≤ 16 |
| A7 | RGA livereg w pętli bx-isa | `rga -s bin --livereg` na każdym kandydacie, szczyt żywych VGPR → sterowanie zmianami | – |
| A8 | Test H1′ parametrami amdgpu (raport 17) | `debug_evictions=1` (rw w runtime) + S-testy; `cwsr_enable=0` jako test różnicujący (reboot, root) | decyzja usera |
| A9 | NVIDIA: `-res-usage` w CI dla sm_86/89/120 | jak A3 | – |
| A10 | NVBit tylko dla własnych binarek (licznik instrukcji MMVQ na 5060 Ti) | `instr_count` z NVBit na `llama-bench` | koszt > ATT-owy odpowiednik |

Odrzucone: Ghidra/IDA/BinNinja/Capstone/r2 dla GPU, CuAssembler/TuringAs/MaxAs, rocprof-compute na gfx1100, fuzzery z listy (dla kerneli fuzzerem jest u nas `test-backend-ops` + losowe kształty), deasemblacja cuBLAS i firmware MES.

## 4. Legalność (skrót, nie porada prawna)

- **AMD:** rocBLAS i hipBLASLt są na MIT, a ich logic YAML i źródła są otwarte, więc to nie RE. Firmware z linux-firmware (MES/ME/PFP) ma w licencji: *„No reverse engineering, decompilation, or disassembly of this Software is permitted”* (`/usr/share/doc/linux-firmware-amd-graphics/copyright`). Dekodowanie **własnych** pakietów PM4 nie dotyka firmware.
- **NVIDIA:** EULA CUDA §1.2 zabrania RE, dekompilacji i deasemblacji „any portion of the SDK” (cuBLAS w nią wchodzi). Zabrania też RE outputu w celu przeniesienia na platformę inną niż NVIDIA ([EULA](https://docs.nvidia.com/cuda/eula/index.html)). Deasemblacja naszych cubinów do strojenia na NVIDIA jest OK `[INFERENCE]`. Z cuBLAS bierzemy tylko metadane i pomiary black-box.
- **UE/PL:**
  - dyr. [2009/24/WE](https://eur-lex.europa.eu/eli/dir/2009/24/oj): art. 5(3) pozwala obserwować, badać i testować; art. 6 pozwala dekompilować wyłącznie dla interoperacyjności; art. 8 unieważnia sprzeczne postanowienia umów;
  - PL [uPrAut](https://api.sejm.gov.pl/eli/acts/DU/1994/83/text.html): art. 75 ust. 2 pkt 2–3; art. 76 („Postanowienia umów sprzeczne z art. 75 ust. 2 i 3 są nieważne”);
  - TSUE [C-406/10 SAS](https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:62010CJ0406): funkcjonalność nie jest chroniona;
  - TSUE [C-13/20 Top System](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A62020CJ0013): dekompilacja dla poprawy błędów jest dozwolona;
  - wniosek: profilowanie i testy cuBLAS są dozwolone mimo EULA. Deasemblacja „żeby nauczyć się trików” to nie interoperacyjność, więc jej unikamy `[INFERENCE]`.

## 5. Reprodukcja

- Statystyki kerneli: `21l-skrypty/co_stats.py OUT.csv libggml-hip.so|*.co|*.hsaco`.
- Synteza taśmy z deskryptora: `21l-skrypty/pm4_synth_tape.py HSACO SYM out.bin --wa N`.
- umr: `~/qwen-opt/research-src/umr/build/src/app/umr`, z `LD_LIBRARY_PATH=/tmp/re21l/debs/root/usr/lib/x86_64-linux-gnu`. Uwaga: `/tmp` jest ulotne, więc libpciaccess trzeba wtedy pobrać ponownie przez `apt download libpciaccess0`.
- RGA: `~/qwen-opt/research-src/rga-2.15.0.30/rga`.
- nvdisasm/cuobjdump: `~/qwen-opt/.venv-train/lib/python3.12/site-packages/triton/backends/nvidia/bin/`.

## Do bazy wiedzy

| folder | tytuł (plik) | co wpisać | liczby i źródło |
|---|---|---|---|
| `research/` | Raport 21l (`raport-21l-re-gpu.md`), nowa | awesome-RE: 0 pozycji GPU; działają LLVM/RGA/umr/ATT/cuobjdump | §0–§1 |
| `narzedzia/` | Statyczny audyt kerneli (`co-stats.md`), nowa | `co_stats.py`: VGPR/spill/fale na kernel; reguła fal gfx1100 min(16, ⌊1536/⌈V⌉₂₄⌋) | 7832 kerneli, 165 spilli, 2376 stubów; CSV 21l |
| `narzedzia/` | umr offline (`umr-offline-pm4.md`), nowa | budowa bez roota; `-f gfx11_vm_test -df`; nie dekoduje inicjatora | `umr-tape-wa*.txt` |
| `kernele/` | MMVQ: klif VGPR ncols 4→5 (aktualizacja strony MMVQ) | Q4_K: 89 → 140 VGPR, 16 → 10 fal; szczyt 136 żywych w bloku v_dot4 | CSV + RGA livereg |
| `lekcje/` | radare2 „sass” ≠ nvdisasm | dekoduje sm_86 błędnie, nie używać | §0 |
| `decyzje/` | RE vendorów: tylko metadane i black-box | EULA §1.2; licencja firmware AMD; art. 75–76 uPrAut | §4 |
