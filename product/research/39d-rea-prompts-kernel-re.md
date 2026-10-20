# 39d: REA-Prompts („Kernel analysis”) i nasz program RE kerneli GPU: ocena, paczka promptów, pierwsze 3 cele

Data: 2026-10-20. Autor: podagent Res39dReaPrompts. Tylko CPU: bez GPU, wynajmu i podagentów.

Źródła:
- `JoasASantos/REA-Prompts` @ `390f0c1` (2026-10-20 13:29 −0300), klon `/tmp/res-reaprompts/` (jeden plik `README.md`, 744 linie);
- API GitHub (metadane repo i commitów);
- npm `rea-agents`;
- `madewithrea.com/prompts`;
- lokalny klon hipfire `~/qwen-opt/re/engines/hipfire/src` @ `bfb90b9` (= HEAD upstreamu 2026-10-14, sprawdzone API);
- nasze drzewo topka `~/wt/topka-base` (`9056cea22`).

Delta względem R23a (rea), R23b/23c/23e (RE kerneli AMD/NV/silników), R23d (firmware MEC), R36 (budżet kroku). `[INFERENCE]` = wniosek bez pomiaru.

**Produkt tej pracy:** paczka promptów `~/KERNEL/qwen-opt/re/KERNEL-RE-PROMPTS.md`. Zawiera P0 (preambuła), P1–P5 (pięć zamówionych), P6–P7 (adaptacje z REA), kontrolę K0 dla `claims.json` i zestaw narzędzi.

## TL;DR

1. **Sekcja 9 „Kernel analysis” nie dotyczy kerneli GPU.** To 3 prompty o sterownikach Windows/Linux (`.sys`/`.ko`, IOCTL, `copy_from_user`) (`README.md:387-420`). W całym README jest 0 wystąpień słów GPU, CUDA, HIP, ISA i shader. Oficjalna galeria (15 promptów) nie wspomina ani kernela, ani GPU, ani sterownika. Samo REA w wersji 6.7.0 (nadal najnowszej na npm, 2026-10-18) nie otwiera ELF-ów AMDGPU ani CUDA (R23a). **Dla naszych celów sekcja 9 wnosi zero.**
2. **Realna metoda w kolekcji to 6 „tips” i kilka zwrotów:**
   - kubełki fakt / wniosek / niewiadoma;
   - dowód `file:line` przy każdym twierdzeniu;
   - analiza statyczna najpierw;
   - jedno pytanie na prompt;
   - artefakt na końcu;
   - „kilka zgodnych przykładów to nie dowód równoważności”;
   - „najmniejszy eksperyment rozróżniający hipotezy”.

   Reszta (55 promptów) to szablony „Use REA on <X>. Identify…”. **Deklaracja „every prompt asks … separate confirmed facts from hypotheses” jest fałszywa:** taki zwrot ma 9/55 promptów, dowodu żąda 44/55. Wydajność pojawia się w 1/55 (port WASM), a numeryka w żadnym.
3. **Napisaliśmy własną paczkę** (P0–P7) z wejściami, formatem wyjścia (`result.md` + `claims.json`) i kontrolami mechanicznymi. Paczka działa z `ds-agent`, bo workerzy DeepSeek pracują tylko na plikach, a GPU zbiera Opus. Wbudowane są nasze lekcje:
   - GB/s > 926 = błąd;
   - czasy kerneli nie z przebiegu `--pmc`;
   - przerw taśmy nie bierzemy ze śladu PM4-off;
   - inna kolejność sum ≠ BIT;
   - koszt stały MMVQ to nie launch.
4. **Pierwsze 3 cele RE pod budżet XTX** (wszystkie mogą być BIT; razem realnie ~0.8–1.2 ms/krok ≈ +3–4.5%, czyli proza 96.1 → ~99–100 t/s; górna granica ~2.3 ms → ~105 t/s):
   - **(1)** fuzje małych operacji hipfire na gfx1100, w tym technika `wavegrid`, która rozkłada pracę na więcej CU przy zachowaniu tej samej arytmetyki; pula 1.19 ms;
   - **(2)** GDN w weryfikacji: `gated_delta_net_f32_batch_seq` + `dflash_gdn_pre` (5 uruchomień → 1); pula 0.65–0.82 ms;
   - **(3)** nasze własne MMVQ n=5 na małych kształtach: ~0.40 ms/krok to „kernel ponad wzorzec”, a tylko ~0.21 ms to wzorzec R=4→R=1.
5. **Obalone przy okazji:** split-K/multi-wave tier weryfikacji hipfire na gfx1100 (`ks4_lds`, `mw_lds`) **nie przenosi się do nas**:
   - autor sam pisze, że nie jest bitowy (relL2 ≤ 1e-5);
   - leczy niedobór fal ich kafla WMMA 16×16, którego nasze MMVQ nie ma (1280 fal na 5120 wierszy);
   - przy nagrywaniu taśmy (Redline) wraca do bazowego kernela.

## 1. Twierdzenia i werdykty

| # | twierdzenie | źródło | próba obalenia | potwierdzenie z innej strony | werdykt |
|---|---|---|---|---|---|
| C1 | „prompts … from native binaries, firmware and **kernels**” | `README.md:3` | §9 = sterowniki OS: „driver binary: .sys / .ko”, „IOCTL”, „copy_to_user” (`:389-420`) | grep README: GPU 0, CUDA 0, HIP 0, ISA 0, shader 0; galeria madewithrea: kernel 0, GPU 0, driver 0 | **prawda, ale „kernel” = jądro OS**; dla GPU 0 |
| C2 | „Every prompt asks the agent to separate *confirmed facts* from *hypotheses* and to cite evidence” | `:37` | policzone na 55 blokach ```text: hypothes/unknown/inferenc w **9**; z „confirm/fact” 11 | evidence/cite/address/prove w 44/55 | **fałsz** (cytowanie ~80%, kubełki ~16–20%) |
| C3 | „Demand evidence … stops the agent from confabulating” | `:729` | brak mechanicznej kontroli: cytat może nie istnieć albo nie dowodzić; R23a: koperta `rea` daje sha256 artefaktu, nie weryfikację tezy | nasza K0 łapie nieistniejące ścieżki i numery linii, GB/s ponad sufit, zły kubełek (test na danych syntetycznych: 4/4 błędy wykryte) | **częściowo**: zmniejsza, nie zatrzymuje |
| C4 | Workflowy `verify_reconstruction`, `audit_residual_unknowns`, `compare_application_versions` | `:202,701,682` | czy istnieją w rea? | `~/qwen-opt/re/rea/src/docs/mcp-prompts.md:12-15` (prompty MCP rea) | **prawda**, tylko że bez GPU |
| C5 | REA nadaje się do kerneli GPU (sugestia z C1) | `:3` | npm `rea-agents` latest = 6.7.0 (2026-10-18), ta sama wersja co w R23a; whitelist `e_machine` bez EM_AMDGPU/EM_CUDA (R23a §0) | R23a: `unsupported ELF architecture` na naszym `.co`, Kuna: „no SLEIGH language” | **fałsz** |
| C6 | Popularność jako sygnał jakości (907★, 126 forków) | API GitHub | repo utworzone 2026-10-19 22:20Z, 4 commity (1 PR dodaje reklamę madewithrea), w API brak pliku LICENSE (README deklaruje MIT) | autor: konto z 2017, 321 repo | **nie jest sygnałem** `[INFERENCE: viral, < 1 doby]` |
| C7 | §9 przydatne dla naszego KFD/amdgpu (IOCTL → PM4) | – | sterownik amdgpu/KFD to źródło GPL w drzewie Linuksa; R23d czytał źródła v6.8 + ROCr, a binarny RE `.ko` nic nie dodaje | wiki `mec-fw-dispatch-aql-gfx11` (odpowiedzi z firmware + źródeł) | **fałsz dla nas** |
| C8 | §10 „Patch diffing” i §4 „Validate a clone” jako metoda | `:456-466,196-207` | metoda ogólna, ale to dokładnie nasze ryzyka: kernel zmieniony poza zakresem łatki, równoważność z kilku przykładów | nasza historia: GDN fast `0b7b073b` ≠ `c4708318` (inna kontrakcja FMA), WMMA i zamaskowane wiersze | **prawda jako metoda** → P2 krok 2, P5 |
| H1 | hipfire: tier weryfikacji gfx1100 split-K (`ks2/4/8_lds`) | `kernels/src/gemm_mq4g256v2_residual_wmma_gfx1100_ksplit_lds.hip:9-27`; `gemm.rs:37000-37037,37701-37711` | „fp32 association differs from the base kernel so bit-exactness is NOT claimed (parity gate: relL2 <= 1e-5)” (`:26-27`); motywacja: „base kernel (one wave32 per 16x16 tile) launches too few waves to cover 96 CUs” (`gemm.rs:37000-37002`); wyłączony przy `replay.is_recording()` (`:37014`, „Only Redline tape recording keeps the base contract”, `:37007`) | nasze MMVQ n=5: 1 fala na blok, 4 wiersze → 1280 fal na 5120 wierszy (24r) | **prawda u nich, nie przenosi się**: inny problem, stratny wg naszej definicji |
| H2 | hipfire: `fused_rmsnorm_mq_rotate_wavegrid` zachowuje arytmetykę bazowego bloku 256 wątków i rozkłada 8 fal na 8 CU (ostatni przybyły robi tę samą redukcję 8 wartości przez scratch globalny) | `kernels/src/fused_rmsnorm_mq_rotate_wavegrid.gfx1100.hip:7-14` | sam autor: „gfx1100 K=2048 experiment”; zysku nie podaje | technika nie zmienia drzewa redukcji, więc BIT przy tym samym przypisaniu `[INFERENCE]`; do sprawdzenia P5 | **prawda (kod); zysk nieznany** |
| H3 | hipfire: `dflash_gdn_pre_capture_gfx1100` składa 5 uruchomień preambuły GDN w 1 (replay 3 → 1) | `kernels/src/dflash_gdn_pre.gfx1100.hip:7-17` | u nas preambuła GDN częściowo już w prologu (łatka 0013, prolog l2-norm `gated_delta_net.cu:14`) | budżet 36: GDN 48 + ssm_conv 48 uruchomień = 0.98 ms | **prawda u nich; nasza delta do policzenia (cel 2)** |
| H4 | hipfire: `gated_delta_net_f32_batch_seq` (stan fp32, 32 wątki × 32 kafle = 1024 wątki na głowicę) jest 4–5× szybszy od ich jednotokenowego (128 wątków na głowicę) dla batcha weryfikacji | `kernels/src/gated_delta_net_f32_batch_seq.hip:10-20` | to porównanie z ICH kernelem jednotokenowym; nasz ma `__launch_bounds__(128, 2)` i własny podział kolumn (`gated_delta_net.cu:20-21,56-67`) | – | **UNKNOWN dla nas** → cel 2 |

## 2. Jakość kolekcji: metoda kontra wata

| element | ocena | co z tym robimy |
|---|---|---|
| kubełki fakt / wniosek / niewiadoma | **metoda** (tylko 9/55 promptów jej używa) | P0 reguła 1 + pole `bucket` w `claims.json` |
| dowód przy każdym twierdzeniu | **metoda**, ale bez kontroli | P0 reguła 2 + K0 (ścieżki, linie, wyjścia komend) |
| static first / „do not execute” | **metoda**; u nas to podział Opus (GPU) / DeepSeek (CPU) | wejścia GPU zbiera Opus, worker analizuje |
| jedno pytanie na prompt | **metoda** | P0 reguła 7 |
| artefakt na końcu (SPEC.md, harness) | **metoda** | `result.md` + `claims.json` o stałym schemacie |
| „few examples ≠ equivalence” (§4) | **metoda**, kluczowa dla bitowości | P5: ncols ≠ 5, ogony wierszy, zależność od N |
| „smallest experiment that distinguishes hypotheses” (§10) | **metoda** | P3 R5, P7 |
| „Use REA on <X>. Identify format, entry points, strings…” (§3, 7, 8, 11) | **wata** dla GPU: rea nie czyta AMDGPU/CUDA | P6 tylko dla hosta x86-64 |
| §9 sterowniki, §12–14 anti-cheat/DMA/cracking | poza zakresem | – |
| ramy prawne („only software you own”) | ogólnik; nasze zasady są ostrzejsze i konkretne (wiki `re-vendorow-zasady`) | P0 reguła 6 |

Czego REA nie ma w ogóle, a co RE kerneli wydajnościowych musi mieć:
- **normalizacja na bajt** (liczby instrukcji na 256 wag, a nie na trip);
- **sufit pasma i sufit wzorca**;
- **zamknięcie bilansu** czasu kroku;
- **klasy strat** (BIT / DIST / LOSSY);
- **rozdział pomiaru od analizy** (`--pmc` serializuje kernele, PM4-off zawyża granice).

Wszystko to jest w P0–P5.

## 3. Mapa naszych celów RE na prompty

| cel | rodzaj | status prawny (wiki `re-vendorow-zasady`) | narzędzia | prompt |
|---|---|---|---|---|
| hipfire (Apache-2.0/MIT), tqLLM (Apache-2.0), NInfer (Apache-2.0), exllamav3 | źródło + ISA z offline buildu | wolno kompilować i deasemblować | `hipfire_src.py`, `hip_s.sh`, `cu_res.sh`, `isa_*`, `sass_*` | P1, P2 |
| rocBLAS/hipBLASLt/MIOpen CK/AOTriton | `.co`/kpack + YAML | MIT, otwarte; R23b zrobione | `kpack_extract`, `tensile_lib`, `isa_profile` | P2 (tylko porównanie), P3 |
| cuBLAS/cuBLASLt | zamknięte | tylko `-res-usage`, nazwy, czasy | `sass_mix.py` na metadanych | P3 (black-box) |
| firmware MEC/MES (R23d, wiki `rs64-firmware-re`, `mec-fw-dispatch-aql-gfx11`) | RS64 = RV64 | wąskie pytania interop o nasze PM4, zrzuty nigdy w repo | `fwparse.py`, `rs64kb.py` (lokalnie) | P6 (wariant firmware, pytanie interop) |
| nasze MMVQ / GDN / FA / norm (wiki `isa-kstat`, `podrecznik-gpu`) | `.s` z naszego drzewa | nasze | `hip_s.sh`, `isa_kstat`, `isadiff`, `gdnemu`, ATT | P2, P3, P5 |
| ślady kroku (rocprofv3, host-gap) | pomiar | – | `vc_trace.py`, `burst_decomp.py`, `hg_parse.py` | P4 |
| `.so` obcych silników (heurystyki dispatchu) | host x86-64 | interop / open source | `rea … --provider kuna`, `kuna` | P6 |

## 4. Pierwsze 3 cele RE (największy oczekiwany zysk dla XTX)

Arytmetyka z budżetu 36: krok 27.38 ms, 2.63 tok/krok, 96.1 t/s. Każde 0.1 ms to +0.37%.

| # | cel | pula (36) | sufit | realnie `[INFERENCE]` | klasa | wysiłek | prompt + wejścia |
|---|---|---:|---:|---:|---|---|---|
| 1 | **Fuzje małych operacji hipfire gfx1100:** `fused_rmsnorm_mq_rotate_{wavegrid,vecsum}`, `gated_norm_mq_rotate`, `attention_flash_q8_0_reduce_gated_mq_rotate_dec`, `fused_silu_mul_mq_rotate_f16` vs nasze `rms_norm` (209 uruch.) + gated/quantize/fwht (145) | 0.79 + 0.40 = 1.19 ms | 1.19 ms → +4.5% | 0.3–0.5 ms → **+1.1–1.9%** (= L12 z R36, nie sumować) | BIT, jeśli redukcja RMS zachowa przypisanie (technika `wavegrid` H2) | 3–5 dni | P1 (pkt 6 „fusions”) + P5 |
| 2 | **GDN weryfikacji:** `gated_delta_net_f32_batch_seq.hip`, `dflash_gdn_pre.gfx1100.hip`, `conv1d_silu_split_*` vs nasze `gated_delta_net.cu` + `ssm-conv.cu` (48 + 48 uruch.) | 0.98 ms; podłoga 0.16 (odczyt stanu 151 MB) – 0.33 ms (odczyt + zapis) | 0.65–0.82 ms → +2.4–3.1% | 0.3–0.4 ms → **+1.1–1.5%** | BIT tylko przy identycznej kontrakcji FMA (lekcja GDN fast: 94 vs 83 FMA zmieniło md5); stan fp32 bez zmian | 3–5 dni | P1 + P2 (D5 inwentarz FMA) + P5 (`gdnemu`) |
| 3 | **Nasze MMVQ n=5 na małych kształtach** (Q5_K/Q6_K 5120×6144, Q4_K 10240×5120, k/v 1024×5120; 91 uruch./krok): ISA + ATT własnego kernela vs `readceil` | 2.83 ms czasu tych uruchomień; strata vs R=1: **0.61 ms**, z tego ~0.40 „kernel ponad wzorzec R=4” i ~0.21 „wzorzec R=4 → R=1” | 0.61 ms → +2.3% | 0.2–0.3 ms → **+0.7–1.1%** | BIT, jeśli zmiana nie rusza kolejności sum; inaczej DIST, i to tylko wspólnie dla n=1 i n=5 | 1–2 tyg. | P2 + P3 (+ ATT) |

Wyliczenie dla celu 3 (24r, wzór bytes = rows·K·bpw/8):

| uruchomienie | n/krok | MB | µs dziś | wzorzec R=4 | R=1 | µs nad wzorcem R=4 ×n | µs R4→R1 ×n |
|---|---:|---:|---:|---:|---:|---:|---:|
| Q5_K 5120×6144 | 38 | 21.63 | 33.0 | 768 → 28.2 | 829 → 26.1 | 182 | 80 |
| Q6_K 5120×6144 | 20 | 25.80 | 39.6 | 768 → 33.6 | 829 → 31.1 | 120 | 50 |
| Q4_K 10240×5120 | 14 | 29.49 | 41.6 | 789 → 37.4 | 832 → 35.4 | 59 | 28 |
| k/v 1024×5120 (Q5_K) | 19 | 3.60 | ~10.5 | 421 → 8.6 | 652 → 5.5 | 37 | 59 |
| **razem** | 91 | | 2828 µs | | | **~0.40 ms** | **~0.21 ms** |

Dla Q6_K i Q4_K wzorzec pochodzi z najbliższego zmierzonego przypadku Q5_K tego samego kształtu wierszy (`readceil.sum.txt` ma tylko Q5_K). Wniosek `[INFERENCE]`: dwie trzecie straty siedzi w samym kernelu (aktywacje q8_1, rozpakowanie, redukcja, epilog), a nie w geometrii siatki. Stąd najpierw ATT i P2 naszego kernela, a dopiero potem geometria R=1/2 ze współdzielonymi aktywacjami. To byłaby naprawa przyczyny porażki RPB=1.

**Razem 1+2+3 realnie 0.8–1.2 ms/krok → 26.2–26.6 ms → 99–100.5 t/s prozy.** Cel 1 to dźwignia L12, a cel 3 częściowo nakłada się z L7 (dataflow). Nie sumować z R36 §4.

**Odrzucone cele RE (po sprawdzeniu w tej pracy):**
- hipfire `ks*_lds` / `mw_lds` (H1);
- hipfire GEMV n=1 (R23e: 138 VALU na 32 wagi wobec naszych 61);
- vendorzy AMD (R23b: brak lepszego GEMV dla N = 1..16).

**Na później:**
- NVIDIA: P1 na weryfikacyjnym GEMV NInfer/tqLLM (sm_86/sm_120). Otwarte różnice z R23c (trigger PDL, `LDG.E.EF`, ładowania 128-bit) są już znane, więc RE ma sens dopiero po ich zamknięciu.
- Mac: lokalnie nie mamy narzędzi do deasemblacji Metal/AIR `[INFERENCE]`, więc P1 tylko w trybie źródłowym.
- Produkt: paczka jest wewnętrzna i nie zmienia produktu.

## 5. Co dotyczy nas (ranking)

| # | rzecz | zysk | wysiłek | bezstratność |
|---|---|---|---|---|
| 1 | Cel RE 1 (fuzje gfx1100 hipfire + `wavegrid`) | +1.1–1.9% prozy, podobnie czat | 3–5 dni po RE (RE 1 dzień DS) | BIT (do dowodu P5) |
| 2 | Cel RE 2 (GDN weryfikacji) | +1.1–1.5% | RE 1 dzień DS, kod 3–5 dni | BIT możliwy, ryzyko FMA |
| 3 | Cel RE 3 (nasze MMVQ małe kształty: ATT + P2) | +0.7–1.1% | ATT 10 min GPU + 1 dzień analizy, kod 1–2 tyg. | BIT albo DIST (wspólnie n=1/n=5) |
| 4 | Paczka P0–P7 + K0 jako standard dla DS-workerów | 0 t/s; mniej fałszywych wniosków | gotowe | – |
| 5 | `rea`/Kuna dla hosta (P6) | 0 t/s; diagnostyka | gotowe (R23a) | – |

## 6. Eksperymenty XTX (≤ 10 min GPU każdy, kolejka GPU)

**X1 (cel 3): ATT naszego MMVQ n=5 w modelu.**
- Batch 5 tokenów w `llama-bench` uruchamia MMVQ ncols=5 na tych samych wagach `[INFERENCE: ne11 ≤ 8 → MMVQ]`.
- Komenda:
  ```
  GGML_HIP_PM4=0 LD_LIBRARY_PATH=$HOME/llama-topka/bin:$HOME/llama-topka/lib:/opt/rocm/core-10.0/lib \
  flock /tmp/gpu.lock flock /tmp/quiet.lock timeout -k 10 280 /opt/rocm/core-10.0/bin/rocprofv3 --att \
    --att-target-cu 1 --att-simd-select 0 --kernel-include-regex 'mul_mat_vec_q' --kernel-iteration-range '[400-403]' \
    -d /tmp/att-mmvq5 -o run -- $HOME/llama-topka/bin/llama-bench -m ~/models/Qwen3.8-27B-UD-Q4_K_XL.gguf \
    -ngl 99 -fa 1 -ctk q4_0 -ctv q4_0 -p 5 -n 0 -b 5 -ub 5 -r 3
  python3 ~/wt/lfmmoe-prof/attsum.py /tmp/att-mmvq5
  ```
- Odczyt: udział `s_waitcnt vmcnt`, wydawania VMEM, prologu i epilogu dla dispatchu z siatką 1280 × 1 (5120 wierszy). Siatkę trzeba potwierdzić w wyniku, bo indeks iteracji jest zgadywany.
- **Kill:** prolog + epilog < 15% czasu fali i VMEM-issue < 20%. Wtedy kernel jest już na wzorcu i zostaje tylko geometria (−0.21 ms).

**X2 (cel 1): górna granica fuzji norm.** `flock /tmp/gpu.lock flock /tmp/quiet.lock ~/qwen-opt/hipfire/ub.sh` (`GGML_HIP_UB_SKIP_NORM=1`, tg128 ABBA, wynik niepoprawny, tylko czas). Przebieg jest plain (n=1), więc wynik przeskalować do weryfikacji wg liczby uruchomień.
- **Kill:** < 0.3 ms/krok (próg L12).

**X3 (cel 2): bajty GDN na krok.**
- Komenda:
  ```
  GGML_HIP_PM4=0 flock /tmp/gpu.lock flock /tmp/quiet.lock /opt/rocm/core-10.0/bin/rocprofv3 \
    --pmc FETCH_SIZE WRITE_SIZE GRBM_GUI_ACTIVE --kernel-include-regex 'gated_delta|ssm_conv' --output-format csv \
    -d /tmp/gdnpmc -o run -- <komenda llama-server z ~/qwen-opt/vcost/prof_block.sh>
  ```
  plus jedno żądanie prozy 128 tok. (`vc_client.py`).
- Czasy brać z istniejącego `vcost/prof-gv1/off`, bo `--pmc` serializuje kernele.
- **Kill:** (FETCH + WRITE) / czas ≥ 740 GB/s (80% sufitu) przy bajtach ≈ model. Wtedy kernel jest na paśmie i zostają tylko fuzje uruchomień.

**X4 (CPU, DeepSeek, 0 GPU): RE celów 1 i 2 według paczki.** Każdy worker w osobnym katalogu `~/qwen-opt/re/work/<slug>/`, z `task.md` złożonym z P0 + P1:
- `gdn-verify`: hipfire `gated_delta_net_f32_batch_seq.hip` + `dflash_gdn_pre.gfx1100.hip` vs `~/wt/topka-base/ggml/src/ggml-cuda/{gated_delta_net,ssm-conv}.cu`, kształt: weryfikacja 5 tokenów, 48 h × 128²;
- `norm-fuse`: `fused_rmsnorm_mq_rotate_wavegrid.gfx1100.hip`, `gated_norm_mq_rotate.gfx1100.hip` vs nasze `norm.cu` + `quantize.cu` (K = 5120).

Uruchomienie: `~/qwen-opt/tools/ds-agent re-<slug> ~/qwen-opt/re/work/<slug> ~/qwen-opt/re/work/<slug>/task.md 45m`, następnie K0.

## Do bazy wiedzy

- **REA-Prompts §9 „Kernel analysis” = sterowniki OS (IOCTL), nie GPU.** W całej kolekcji 0 wzmianek o GPU/CUDA/ISA. Metodę (kubełki, dowód, static first, „few examples ≠ equivalence”) przenieśliśmy do `qwen-opt/re/KERNEL-RE-PROMPTS.md`. Źródło: R39d.
- **Paczka promptów RE kerneli** P0–P7 (konkurent na bajt, diff ISA, roofline z liczników, narzut launch/host, audyt bitowości, dispatch w binarce, niewiadome) z kontrolą K0 dla `claims.json`, gotowa dla `ds-agent`. Źródło: R39d.
- **Liczniki gfx11 dla rooflinu** (`derived_counters.xml`, sekcja `<gfx11>`):
  - `FETCH_SIZE` = Σ `GL2C_EA_RDREQ_{32..128}B` (ruch L2 → fabric; trafienia w Infinity Cache też się liczą `[INFERENCE]`);
  - `WAVE_ISSUE_WAIT`, `WAVE_DEP_WAIT`, `TA_BUSY_avr`, `L2CacheHit`;
  - `--pmc` serializuje kernele, więc czasy brać z osobnego przebiegu. Źródło: R39d.
- **hipfire tier weryfikacji gfx1100 (`ks*_lds`, `mw_lds`) nie przenosi się:**
  - autor sam deklaruje brak bitowości (relL2 ≤ 1e-5);
  - leczy niedobór fal ich kafla WMMA 16×16;
  - wyłączony przy nagrywaniu taśmy Redline (`gemm.rs:37000-37014`, `ksplit_lds.hip:26-27`). Źródło: R39d.
- **hipfire `wavegrid`:** rozkłada 8 fal bloku na 8 CU, a ostatni przybyły robi tę samą redukcję. Arytmetyka bez zmian, więc kandydat na bitowe fuzje norm (`fused_rmsnorm_mq_rotate_wavegrid.gfx1100.hip:7-14`). Źródło: R39d.
- **MMVQ n=5 na małych kształtach:** ~0.40 ms/krok to „kernel ponad wzorzec R=4”, a ~0.21 ms to wzorzec R=4 → R=1 (91 uruch./krok, dane 24r). Najpierw ATT własnego kernela. Źródło: R39d.

Wiersze do `wiki/ZRODLA.md`:

Sekcja „Repozytoria kerneli, DSL i narzędzia”:

| źródło | wersja | raport, notatka | werdykt | następnym razem |
|---|---|---|---|---|
| REA-Prompts (github.com/JoasASantos/REA-Prompts) | `390f0c1` 2026-10-20 | [R39d](../product/research/39d-rea-prompts-kernel-re.md) | §9 to sterowniki OS; metoda przeniesiona do paczki promptów. | czy doszły prompty GPU/ISA |
| rea (rea-agents) **2×** | 6.7.0 (npm latest 10-20) | R23a, R39d | Nadal bez EM_AMDGPU/EM_CUDA. | czy dodali AMDGPU |

Sekcja „Silniki i serwery inferencji” (uzupełnienie hipfire):

| źródło | wersja / data | raport, notatka | werdykt (≤12 słów) | kluczowe liczby | następnym razem sprawdź |
|---|---|---|---|---|---|
| hipfire: kernele weryfikacji gfx1100 (ks/mw, wavegrid, gdn_pre, f32_batch_seq) | `bfb90b9` 10-14 | R39d | Split-K stratny i nie nasz problem; fuzje i GDN warte RE. | ks: relL2 ≤ 1e-5; gdn_pre 5 → 1 uruch. | pomiary perf-checkpoints dla `wavegrid` |
