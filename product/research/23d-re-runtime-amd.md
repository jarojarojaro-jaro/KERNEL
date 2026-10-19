# 23d. Co dzieje się przy jednym launchu na gfx1100: HIP → CLR → AQL → firmware MEC, a nasza taśma PM4

Analiza tylko na CPU (19.10). Źródła: CLR/ROCr `rocm-systems` develop `55754a0`, Linux v6.8, tinygrad, firmware MEC `gc_11_0_0_mec.bin` z `/lib/firmware`, zdeasemblowany (RS64 = RV64). Narzędzia i wyniki z poprzedniej próby leżą w `~/qwen-opt/re/runtime/` (`rs64kb.py`, `fw/mec.kb.S` z nazwami rejestrów). Na GPU nic nie uruchamiano. Uzupełnia raport 17 §9 i niczego w nim nie powtarza.

## 0. Werdykt

- **Firmware potwierdza H1′.** Ścieżka AQL w MEC (`mec.kb.S:58396-58439`) czyści w RSRC1 z deskryptora bity PRIORITY, PRIV, bit 22, BULKY i CDBG_USER (maska `0xe4aff3ff`). Potem ustawia **PRIV z flagi kolejki w firmware** (`tp+0x2d8` bit 2). Handler `DISPATCH_DIRECT` (`:52843-52849`) zapisuje tylko DIM, START i inicjator, a RSRC1 bierze taki, jaki jest. Fale taśmy dostają więc PRIV wyłącznie od nas. `GGML_HIP_PM4_WA≥1` jest właściwą poprawką.
- **Dwie nowe różnice wobec AQL (przekazane do Pm4Fix):**
  - inicjator AQL to `0x1065 | CS_W32<<15`, czyli ORDER_MODE=1, USE_THREAD_DIMENSIONS, bit 12 i **bez** ORDERED_APPEND_ENBL (ten bit tylko warunkowo, z flagi wewnętrznej). Potwierdza to część WA=2;
  - AQL ustawia `COMPUTE_PGM_HI |= 0x100` (bit 8, nieopisany w nagłówku gfx11).

  Obie różnice mają niskie ryzyko, bo tinygrad i kfdtest działają bez nich.
- **Koszt launchu:** podłoga AQL 2.08 µs wynika z pracy firmware na każdy pakiet: czyta deskryptor kernela z pamięci (4 odczyty: `ld 0/0x1c/0x20/0x28(a7)`), składa user SGPR i ustawia sygnał/EOP. Taśma podaje gotowe wartości w IB, stąd jej 0.46–0.86 µs `[INFERENCE z kodu + pomiary]`. Na ścieżce HIP nie da się obejść żadnego z tych kroków flagami środowiska.

## 1. Stan dispatchu: AQL (firmware) vs taśma (`hip-pm4.cu` @ `b7fb3fe85`)

| rejestr / stan | AQL: co robi MEC fw (linie `mec.kb.S`) | taśma | różnica, ryzyko |
|---|---|---|---|
| `PGM_LO/HI` | `(KD+entry)>>8`, `>>40` **\| 0x100** (58396-58405) | `>>8`, `>>40` (`hip-pm4.cu:934`) | bit 8 HI brak; **niskie/nieznane** |
| `PGM_RSRC1` | `KD.rsrc1 & 0xe4aff3ff`, PRIV = flaga kolejki (58411-58437) | z KD; PRIV tylko przy `WA≥1` (:935) | **PRIV: wysokie (CWSR)**; reszta bez różnicy, kompilator daje tam 0 |
| `PGM_RSRC2` | `(KD & 0x1fbf) \| TRAP_PRESENT(kolejka)<<6 \| LDS_SIZE=ceil(pkt.group_segment/512)<<15`; LDS >64 KiB → błąd (58407-58448) | z KD, podmieniony LDS_SIZE, TRAP_PRESENT=0 | EXCP_EN w AQL zawsze 0, u nas z KD (0); TRAP_PRESENT: KFD ma `trap_en=0` na 11.0.0, więc bez różnicy |
| `PGM_RSRC3` | `KD+0x2c` (58406-58410) | z KD | brak |
| `NUM_THREAD_X/Y/Z` | z pakietu (58381-58383) | blockDim | brak |
| `DISPATCH_PKT_ADDR` | tylko z flagą kolejki `0x40` (58384-58394) | nie | kernele z dispatch_ptr odrzucamy; brak |
| user SGPR | kolejno według `kernel_code_properties`: V# scratch (4), dispatch ptr (2), queue ptr (2), kernarg (2), dispatch id (2), flat scratch (2), private size (1) (58500-58675) | V# `0,0,0,0` (jeśli kernel go deklaruje) + kernarg lo/hi | zgodne dla przyjmowanych kerneli |
| `TMPRING_SIZE` / scratch | z `amd_queue_t.compute_tmpring_size` i SRD od ROCr (`amd_aql_queue.cpp:1771-2026`) | 0; kernele ze scratch odrzucane | brak |
| `RESTART_X/Y/Z` | firmware; wewnętrzny dispatch fw je zeruje (41198-41200) | 0 przy `WA=2` | brak przy WA=2 |
| `DISPATCH_INITIATOR` | `0x1065 \| W32<<15`, ORDERED_APPEND tylko warunkowo (58677-58684) | `0x800d` (W32, FORCE_START, **ORDERED_APPEND**); WA=2: `0x8005` | ORDER_MODE=0 u nas: niskie (tinygrad też 0); ORDERED_APPEND: WA=2 |
| granica | bariera AQL + EOP/sygnał | `CS_PARTIAL_FLUSH` + `ACQUIRE_MEM` (GCR 0x380) | brak (17 §9.1) |
| IB | n/d | vendor PM4_IB, polityka 3; WA=2: 0 | kosmetyka |
| VMID, SH_MEM, TBA/TMA, CWSR | MQD / KFD / MES per kolejka | to samo, ta sama kolejka AQL | brak |

Dla porównania, wewnętrzny dispatch samego firmware (`41164-41212`) ustawia PRIV=1, `RESTART=0`, inicjator `0x8045`. AMD we własnym kodzie robi więc to samo co `WA=2` plus ORDER_MODE.

## 2. Ścieżka launchu i koszty

| etap | co się dzieje (źródło) | koszt (pomiar u nas) |
|---|---|---|
| `hipLaunchKernel` → `ihipLaunchKernel` | `hip_platform.cpp:685` → `ihipModuleLaunchKernel` `hip_module.cpp:699`; komenda trafia do VirtualGPU | CPU, nie mierzono osobno |
| kernargi | `allocKernArg` z puli (`rocvirtual.cpp:2713`), `nontemporalMemcpy` (:5021); przy large BAR readback-sentinel (:5027-5042); przy grafie `getGraphKernArg` (:5013) | kernargi w pamięci hosta: **+1 µs/dispatch** |
| pakiet AQL | `submitKernelInternal` (:4783): wymiary, `kernarg_address`, `group_segment_size = lds + dynamic` (:5117-5123); nagłówek z barierą i acquire agent (`adjustHeader` :1637) | — |
| zapis do ringu + doorbell | `dispatchGenericAqlPacket` (:1542): rezerwacja slotu, `writePacketToRingBuffer`, **na Linuksie doorbell przy każdym pakiecie** (`IS_LINUX`, :1610) | — |
| graf HIP | przechwycone pakiety (:1693-1712) kopiowane hurtem `dispatchAqlPacketBatchFlat` (:1753), jeden doorbell na partię | graf 2.53–2.75 µs/kernel; przerwa w trace 3.2–3.4 µs |
| firmware MEC, pakiet AQL | odczyt KD, sanityzacja RSRC, user SGPR, inicjator, EOP/sygnał (§1) | **podłoga 2.08 µs** dla każdego wariantu AQL |
| taśma PM4 | jeden pakiet vendor, potem w IB `SET_SH_REG`, `DISPATCH_DIRECT`, partial flush i acquire | **0.46–0.86 µs/granicę** |
| ewikcja kolejek | KFD REMOVE_QUEUE/ADD_QUEUE przez MES, restore po 1 ms (SVM/userptr) albo 100 ms (TTM) (17 §9.2) | zatrzymuje wszystkie kolejki procesu |

Pomiary: `wiki/metody/mikrobench-granicy-kernela.md`, `wiki/rocm/hip-graph-narzut.md`.

## 3. Wywłaszczenie (to, czego nie ma w 17)

- Ścieżka wznowienia w MEC (`mec.kb.S:6163-6233`):
  - ustawia `CP_SUSPEND_CNTL`, zeruje `CP_HQD_SUSPEND_CNTL_STACK_DW_CNT`, przepisuje `CNTL_STACK`/`WG_STATE` offsets, ustawia `CP_MQD_CONTROL`;
  - **ponownie zapisuje zapamiętany `DISPATCH_INITIATOR`** (czyści bit 13 TUNNEL, gdy nie ma SHADER_EN).

  Przerwany dispatch taśmy wraca więc z naszym inicjatorem, również z ORDERED_APPEND_ENBL przy `WA<2`. Fale bez PRIV=1 wracają też bez obejścia CWSR. `[INFERENCE: kontekst wywołania nie w pełni zrekonstruowany]`
- MES nie robi SUSPEND/RESUME dla KFD. Wywłaszczenie to REMOVE_QUEUE (CWSR zapisuje fale do ctx-save z MQD), a przywrócenie to ADD_QUEUE (17 §9.2).

## 4. Działania (ranking)

| # | działanie | zysk / cel | ryzyko | test i kryterium stopu |
|---|---|---|---|---|
| 1 | `GGML_HIP_PM4_WA=2` (Pm4Fix, S4/S6 z 17 §9.5) | koniec resetów GPU | niskie | S4: ≥1000 ewikcji w taśmie, 0 faultów; pierwszy fault → stop, PM4 off |
| 2 | tylko jeśli S4 da fault: `WA=3` = WA=2 + ORDER_MODE (bit 6) + `PGM_HI\|=0x100` | pełna zgodność z AQL | niskie | to samo S4; fault → opcja 5 z 17 (kolejka PM4 KFD) |
| 3 | `HSA_USE_SVM=0` / `GPU_PINNED_MIN_XFER_SIZE` (17 S3) | mniej ewikcji = mniej zatrzymań wszystkich kolejek | niskie | S3: ewikcje SVM ≈ 0, TTFT ≤ +20% |
| 4 | dalej fuzje kerneli (każdy kernel mniej to −2.1…−3.3 µs na AQL, −0.5…−0.9 µs w taśmie) | jedyna dźwignia, gdy PM4 jest off | brak | ABBA t/s, md5 bez zmian |
| 5 | kernargi zawsze w VRAM (już tak jest) | +1 µs, gdyby się to zmieniło | — | — |

Odpadają: flagi grafu HIP (`DEBUG_HIP_GRAPH_BATCH_SIZE`, segmenty, `DEBUG_CLR_DOORBELL_SKIP`, który na Linuksie nie działa: `IS_LINUX` zawsze dzwoni). Pomiar dał szum, a podłogę 2.08 µs wyznacza firmware. Zdejmowanie `ACQUIRE_MEM` między dispatchami daje +12% jako górną granicę, ale całość się wiesza (16a).

## 5. Do bazy wiedzy

| folder | tytuł | treść |
|---|---|---|
| `rocm/` | `mec-fw-dispatch-aql-gfx11.md` | Firmware MEC gfx11 przy pakiecie AQL robi tak: RSRC1 = KD & `0xe4aff3ff`, PRIV z flagi kolejki (obejście CWSR); RSRC2 = KD & `0x1fbf` \| TRAP_PRESENT \| LDS z pakietu (512 B/granula, limit 64 KiB); `PGM_HI\|=0x100`; inicjator `0x1065\|W32<<15`; user SGPR w kolejności AMDGPUUsage. `DISPATCH_DIRECT` nie dotyka RSRC1. Linie w `~/qwen-opt/re/runtime/fw/mec.kb.S` (58370-58684, 52843, 41164-41212). |
| `rocm/` | aktualizacja `gfx11-pm4-dispatch-priv.md` | Dowód z firmware: PRIV dla AQL ustawia MEC, dla PM4 nikt. Dodatkowe różnice: ORDER_MODE, `PGM_HI` bit 8 (kandydaci na WA=3). |
| `rocm/` | aktualizacja `hip-graph-narzut.md` | Na Linuksie CLR dzwoni doorbellem przy każdym pakiecie (`rocvirtual.cpp:1610`); `DEBUG_CLR_DOORBELL_SKIP` nie działa. Graf kopiuje pakiety hurtem (`dispatchAqlPacketBatchFlat`). Podłoga 2.08 µs to praca firmware na pakiet (odczyt KD, user SGPR, EOP). |
| `narzedzia/` | `rs64-firmware-re.md` | Jak deasemblować CP/MES gfx11: nagłówek v2 (`fwparse.py`), capstone RV64C, propagacja znanych bitów do nazw rejestrów (`rs64kb.py`); apertura SH: indeks rejestru ×4 od `0x1_0002_0000_0000`. |
