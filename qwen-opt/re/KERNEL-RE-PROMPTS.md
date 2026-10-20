# KERNEL-RE-PROMPTS: prompty do reverse engineeringu kerneli GPU (v1, 2026-10-20)

Paczka dla inżynierów Opus i workerów DeepSeek (`~/qwen-opt/tools/ds-agent`). Powstała z raportu 39d (`~/KERNEL/product/research/39d-rea-prompts-kernel-re.md`).

Z kolekcji REA-Prompts (JoasASantos, `390f0c1`) wzięliśmy tylko metodę: trzy kubełki FACT/INFERENCE/UNKNOWN, dowód przy każdym twierdzeniu, analizę statyczną przed uruchomieniem, jedno pytanie na prompt, artefakt na końcu i zasadę „kilka zgodnych przykładów to nie dowód równoważności”. Sekcja 9 „Kernel analysis” w REA dotyczy jąder systemów operacyjnych (sterowniki `.sys`/`.ko`, IOCTL), a nie kerneli GPU. Wszystko, co dotyczy GPU, jest tutaj nowe.

Prompty są po angielsku, bo DeepSeek i reguły `ds-agent` są po angielsku. Opisy są po polsku.

## 0. Jak używać

**Podział pracy.** Opus zbiera wejścia wymagające GPU (ślady rocprofv3, liczniki, md5) w kolejce GPU (`flock /tmp/gpu.lock flock /tmp/quiet.lock …`). Worker DeepSeek dostaje tylko pliki i robi analizę na CPU: `ds-agent` zabrania GPU, uruchamiania serwera i pushowania.

**Katalog roboczy:** `~/qwen-opt/re/work/<slug>/`, w nim:
- `in/`: wejścia, wyłącznie kopie lub symlinki;
- `out/`: `result.md` + `claims.json`;
- `task.md`: preambuła P0 + jeden prompt P1–P7 z wypełnionymi `<…>`.

```bash
S=<slug>; W=~/qwen-opt/re/work/$S; mkdir -p $W/in $W/out
# złożyć task.md: P0 + Px z wypełnionymi <…> (np. sed z mapy wartości albo ręcznie)
~/qwen-opt/tools/ds-agent re-$S $W $W/task.md 45m      # wynik: ~/qwen-opt/ds/out/re-$S.md, log: ~/qwen-opt/ds/logs/re-$S.log
python3 - $W/out/claims.json <<'E'                       # kontrola K0 (każdy prompt): dowody istnieją, liczby w granicach
import json, os, sys
W = os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[1])))   # ścieżki względne = względem katalogu roboczego
P = lambda s: os.path.join(W, os.path.expanduser(s))
bad = 0
for c in json.load(open(sys.argv[1])):
    for e in c.get("evidence", []):
        if e["kind"] == "file":
            p, _, l = e["ref"].rpartition(":")
            p = P(p)
            if not os.path.isfile(p) or (l.split("-")[0].isdigit() and int(l.split("-")[0]) > sum(1 for _ in open(p, errors="ignore"))):
                print("MISSING", c["id"], e["ref"]); bad += 1
        if e["kind"] == "cmd" and not os.path.exists(P(e.get("out", ""))):
            print("NO-OUTPUT", c["id"], e.get("cmd")); bad += 1
    if c.get("unit") == "GB/s" and isinstance(c.get("value"), (int, float)) and c["value"] > 926:
        print("ABOVE-CEILING", c["id"], c["value"]); bad += 1
    if c["bucket"] not in ("FACT", "INFERENCE", "UNKNOWN"):
        print("BAD-BUCKET", c["id"]); bad += 1
print("K0", "FAIL" if bad else "PASS", bad)
E
```

**Zasady przyjęcia wyniku (dla Opusa):**
- najpierw K0, potem kontrole konkretnego promptu;
- liczbę FACT bez dowodu traktujemy jak INFERENCE;
- wniosek „szybsze” bez arytmetyki względem budżetu kroku odrzucamy.

Limity: ≤ 3 workery na inżyniera jednocześnie (`ds-agent`), kompilacje ISA przez `hip_s.sh`/`cu_res.sh` (ten sam `flock /tmp/cpuheavy.lock`, `nice -n 19`, rdzenie 0–3).

**Narzędzia** (wszystkie CPU):

| narzędzie | do czego |
|---|---|
| `~/KERNEL/tools/re/hip_s.sh SRC OUT.s [flags]` | offline `.s` gfx1100 z HIP (`ARCH=` zmienia cel) |
| `~/KERNEL/tools/re/hipfire_src.py REPO CONST [--replace A B] [--prepend T]` | dokładne źródło, które JIT hipfire podaje hipcc |
| `~/KERNEL/tools/re/hip_fatbin_extract.py LIB.so OUTDIR --filter mul_mat_vec_q` | code object z naszego `.so`; dalej `/opt/rocm/llvm/bin/llvm-objdump -d --no-show-raw-insn --symbolize-operands` |
| `~/KERNEL/tools/re/isa_kstat.py FILE.s [REGEX]` | VGPR/SGPR/LDS/scratch/fale + statyczny miks |
| `~/KERNEL/tools/re/isa_mix.py FILE REGEX --loops` | miks per pętla (pętla = cel późniejszej gałęzi wstecz) |
| `~/KERNEL/tools/re/isa_profile.py --kernel REGEX --json OUT CO…` | profil code objectu: bity cache, `s_clause`, najgorętsza pętla |
| `~/KERNEL/qwen-opt/research/round6/gdn-isa-tools/isadiff.py BASE.s NEW.s` | każdy kernel bazy bajtowo identyczny w NEW |
| `…/gdn-isa-tools/gdnemu.py`, `gdncmp.py` | symboliczny emulator wave32: dowód bitowości offline ([[emulator-isa]]) |
| `~/KERNEL/tools/re/cu_res.sh SRC OUTDIR sm_86`, `sass_mix.py`, `sass_loop.py` | strona NVIDIA (SASS, `ptxas -v`) |
| `~/qwen-opt/vcost/vc_trace.py DIR`, `~/qwen-opt/xtxroadmap/burst_decomp.py DIR` | rozbicie śladu rocprofv3 na kroki i serie |
| `~/qwen-opt/hostgap/hg_parse.py LOG --min-steps 30` | ślad host-gap ścieżki produkcyjnej (taśmy PM4 włączone) |
| `~/qwen-opt/mmvqbw/readceil.hip` + `readceil_sum.py` | sufit wzorca odczytu dla danej siatki |
| `~/qwen-opt/mmvq-bench/mm_dump2` | FNV wyjścia MUL_MAT per (typ, ncols) między dwoma buildami |
| `llama-bx-diff` (gałąź `batch-invariant`) | pierwszy węzeł grafu, w którym weryfikacja ≠ plain |

---

## P0. Preambuła (wklejać przed każdym promptem)

```text
ROLE: You are a GPU kernel reverse-engineering analyst for a llama.cpp fork tuned for single-user decode
(batch 1, speculative verify of 5 rows) of Qwen3.8-27B (hybrid: 48 Gated-DeltaNet + 16 attention layers [verify
against the GGUF/config if it matters], MTP draft head, GGUF UD-Q4_K_XL = mixed Q4_K/Q5_K/Q6_K) on an AMD
RX 7900 XTX (gfx1100, RDNA3, wave32, 96 CUs, 1536 VGPR per SIMD lane, 96 MB Infinity Cache, 960 GB/s nominal,
926 GB/s MEASURED read ceiling) and on NVIDIA sm_86/sm_120.

FIXED CONTEXT (report 36, prose T=1, MTP n=4, PM4 tapes on):
  step 27.38 ms = verify tape 24.50 (of which MMVQ n=5 21.79: ~2.4 ms fixed per-launch cost over 340 launches,
  ~1.95 ms small-shape bandwidth loss; rms_norm 0.79, GDN+ssm_conv 0.98, flash-attn 0.50,
  gated/quantize/fwht 0.40) + MTP draft 2.28 + GPU top-k 0.11 + host gap 0.49. 2.63 tokens/step = 96.1 t/s.
  Bytes per verify pass 16.83 GB; physical floor 18.17 ms; today 66% of ceiling.
  Every 1 ms saved per step = +3.8% t/s. Report every speed claim as ms/step saved AND % t/s.

EVIDENCE RULES (hard):
1. Put every claim into exactly one bucket: FACT (proven by a cited file:line, disassembly line, or a command
   whose output you saved), INFERENCE (reasoned, not measured: say from what), UNKNOWN (say what would decide it).
2. Every number carries its source: `path:line`, or the exact command plus the saved output path under out/.
   Recompute every derived number with the formula shown (bytes = rows*K*bpw/8, GB/s = bytes/us/1e3, ...).
3. Static analysis only. You have NO GPU: never run llama-server, benchmarks, rocprof or anything touching
   /dev/kfd. Heavy CPU commands under `nice -n 19`, at most 4 threads.
4. Sanity bounds: any GB/s > 926 on gfx1100 is a methodology error (usually bytes per token instead of bytes per
   pass, or Infinity Cache hits counted as DRAM). Static instruction counts are per loop TRIP; normalize per
   byte of weights or per 256 weights before comparing kernels; state the trip count you assumed.
5. Losslessness vocabulary: BIT = same bits as the baseline build in the same mode (greedy md5 + logit hash);
   DIST = same sampling distribution, different bits (new md5 reference needed); LOSSY = changes the model or
   logits beyond rounding (KLD gate). Adoption requires BIT or a justified DIST. A different float summation
   order (split-K, other reduction tree, atomics, FMA contraction, f16 instead of q8_1 activations) is NOT BIT.
6. Legal: open-source code (hipfire, tqLLM, NInfer, exllamav3, llama.cpp, CK, rocBLAS/hipBLASLt sources and
   YAML) may be compiled and disassembled. Closed vendor binaries (cuBLAS etc.) only metadata (`-res-usage`,
   symbol names) and black-box timings. Firmware (linux-firmware MEC/MES): only narrow interoperability
   questions about how OUR PM4 packets are handled; never copy dumps into the repo or outputs.
7. One question per task. Do not widen the scope; list tempting side questions under "Next".
8. "A few matching examples" never proves equivalence: say what class of inputs was NOT covered.

OUTPUT (both files, in <WORKDIR>/out/):
- result.md: TL;DR (<= 5 lines), the tables requested by the task, "Transfer to us" with ms/step arithmetic,
  "Residual unknowns" (what would settle each), "Next" (<= 3 items).
- claims.json: list of {"id","claim","bucket","value","unit","evidence":[{"kind":"file","ref":"path:line"} |
  {"kind":"cmd","cmd":"...","out":"out/<file>"}]}. Every number in result.md tables must appear here.
Finish with a 10-line report: files written, top finding, the single check the engineer should run first.
```

---

## P1. RE kernela decode konkurenta: dlaczego jest szybszy na bajt

**Kiedy:** konkurent ma wyższe t/s albo GB/s na tym samym kształcie, a chcemy wiedzieć, czy różnica bierze się z bajtów, z pętli, z siatki czy z fuzji.

**Wejścia (przygotowuje Opus albo worker na CPU):**
- `in/src/`: klon konkurenta z hashem commita. Dla hipfire: `~/qwen-opt/re/engines/hipfire/src` @ `bfb90b9`.
- `in/theirs.s`: ich kernel skompilowany offline.
  - hipfire: `hipfire_src.py REPO CONST > k.hip && hip_s.sh k.hip theirs.s <flagi z compiler.rs>`. Flagi z NOTES hipfire to `-O3 -fuse-cuid=none -mcode-object-version=6`.
  - NVIDIA: `cu_res.sh SRC in/ sm_86`.
- `in/ours.s`: nasz odpowiednik.
  - Albo `hip_s.sh` na źródle z `~/wt/topka-base` (topka `9056cea22`),
  - albo code object z `libggml-hip.so` przez `hip_fatbin_extract.py` + `llvm-objdump`.
- `in/shapes.md`: kształty z budżetu (24r): Q5_K 5120×6144 (38 uruch., 33.0 µs, 655 GB/s), Q6_K 5120×6144 (20, 39.6 µs), Q4_K 10240×5120 (14, 41.6 µs), k/v 1024×5120 (19, 9.6–11.5 µs, ~370 GB/s), para ffn Q5_K 34816×5120 (17, 148.8 µs, 823 GB/s).
- Opcjonalnie `in/their-bench.md`: ich liczby z cytatem (plik i linia albo URL).

```text
TASK P1 — Why is <COMPETITOR> <KERNEL_SYMBOL> faster per byte than our <OUR_KERNEL> for <SHAPE CLASS, e.g.
"verify N=5, M x K = 5120 x 6144">?
Inputs: in/src (commit <HASH>), in/theirs.s, in/ours.s, in/shapes.md, optional in/their-bench.md.
Steps:
1. Dispatch: find where their runtime selects this kernel for N=<N>, M=<M>, K=<K> on gfx1100 (file:line of the
   condition, every env/flag that changes it, defaults). If another kernel would run for our shape, say so and stop.
2. Bytes: their weight format (bytes per 256 weights incl. scales/zero-points), activation format (f32/f16/q8_1)
   and its bytes per pass, output/epilogue traffic. Compute bytes per launch for EACH shape in in/shapes.md for
   them and for us. Split any advantage into (a) fewer bytes and (b) same bytes moved faster.
3. Per-byte mechanics of the hot loop (use isa_mix.py --loops and isa_kstat.py on both .s files):
   VMEM loads per trip by width and kind (global/buffer, b32/b64/b128/d16), bytes per VMEM instruction,
   VALU per weight, dot/WMMA per weight, s_waitcnt pattern (draining vmcnt(0) every trip vs rolling vmcnt(N>0)),
   LDS staging and barriers (and whether a barrier emits buffer_gl0_inv), cache-policy bits (glc/slc/dlc),
   VGPR -> waves/SIMD, scratch/spills.
4. Grid geometry for each shape: blocks, waves per block, rows per wave, K-split per wave, waves in flight per CU,
   bytes in flight per SIMD (Little's law: ~4.7 KB/SIMD needed at 0.9 TB/s with ~1 us latency [INFERENCE from
   report 23b]), and the tail: fraction of the launch where < 50% of CUs are busy (blocks mod (96 x resident
   blocks per CU)).
5. Numerics: accumulation type, reduction order (lanes, waves, LDS, atomics, split-K), activation quantization,
   their own correctness gate (e.g. "relL2 <= 1e-5"). Classify transfer as BIT / DIST / LOSSY for OUR path.
6. Fusions: what neighbouring ops (norm, residual add, rotate/FWHT, gate) they fold into prologue/epilogue, and the
   launches/bytes this removes per step for our model.
Output tables:
 T1 dispatch (condition, file:line, flags); T2 bytes per launch per shape (them/us, formula);
 T3 hot-loop diff (metric, theirs, ours, per-256-weights normalization, evidence);
 T4 grid/tail per shape; T5 numerics + loss class; T6 transferable mechanisms ranked by ms/step ceiling
 (ceiling = sum over our launches of (our_us - bytes/target_GBps), target = readceil value for that grid or
 926 x 0.9; say which).
Kill rule inside the task: if (a) explains >= 80% of the gap, say "format, not kernel" and rank only (b)-items.
```

**Kontrole (Opus):**
1. Wybór kernela: otworzyć cytowany `file:line` warunku. Sprawdzić, czy domyślne flagi naprawdę go wybierają: hipfire ma dziesiątki przełączników env (`feature_flags.rs`), a ścieżki „exact gfx1100” różnią się od „gfx11”.
2. Bajty: przeliczyć jedną liczbę ręcznie, np. Q5_K 5120×6144 = 21.63 MB → 655 GB/s przy 33.0 µs.
3. Normalizacja: porównania instrukcji muszą być na 256 wag albo na KB wag. Gołe liczby na trip się nie liczą.
4. Klasa strat: jeśli worker pisze BIT przy innej kolejności sum, wynik odrzucić. Przykład: hipfire ks-split sam deklaruje „bit-exactness is NOT claimed (parity gate: relL2 <= 1e-5)” (`kernels/src/gemm_mq4g256v2_residual_wmma_gfx1100_ksplit_lds.hip:24-27`).
5. Sufit z T6 ≤ pula w budżecie: MMVQ ~4.35 ms ponad podłogę, małe operacje 2.67 ms.

**Pułapki z bazy:**
- „Szybszy” kernel bywa szybszy tylko przez mniej bajtów: hipfire 54.3 vs 43.2 t/s to ~2.7 ms bajtów i ~0.8 ms fuzji (23e).
- RPB=1 podnosi czysty odczyt, a prawdziwy kernel traci 3%, bo aktywacje rozpakowuje każdy wiersz osobno (24r).
- Mechanizm konkurenta leczy czasem problem, którego my nie mamy. Ich split-K na gfx1100 powstał, bo ich bazowy kernel WMMA (1 fala na kafel 16×16) „launches too few waves to cover 96 CUs” (`crates/rdna-compute/src/gemm.rs:37000-37002`). Nasze MMVQ ma ~1280 fal na 5120 wierszy. Do T6 brać tylko mechanizmy, których przyczyna występuje u nas, i to z liczbą.
- Sprawdzić, czy mechanizm działa w ich trybie produkcyjnym. Ten sam tier w nagrywaniu taśmy (Redline) wraca do kontraktu bazowego (`gemm.rs:37007,37014`).

---

## P2. Diff ISA dwóch kerneli (VGPR, LDS, waitcnt, instrukcje pamięci)

**Kiedy:**
- łatka zmienia kernel i chcemy wiedzieć, co zmieniło się w ISA (bramka przeciw spillom, regresjom i przypadkowym zmianom kolejności FMA);
- porównanie nasz vs konkurent przy tej samej klasie kształtu.

**Wejścia:**
- `in/a.s` i `in/b.s`: ten sam kompilator i te same flagi, jeśli to możliwe. Plik `.s` z `hip_s.sh` ma metadane `.amdhsa_*`, a `.dis` z `llvm-objdump` ich nie ma.
- `in/regex.txt`: wzorce symboli, po jednym na linię, w parach A ↔ B.
- `in/context.md`: co zmienia łatka (diff źródła) albo skąd pochodzą pliki.

```text
TASK P2 — ISA diff of <KERNEL A> (in/a.s) vs <KERNEL B> (in/b.s) for <PURPOSE: patch gate | competitor compare>.
Steps:
1. Provenance: compiler version line, target (.amdgcn_target), flags if recoverable, code-object version. If they
   differ, every later difference is tainted: mark them INFERENCE.
2. Identity: run isadiff.py a.s b.s; list kernels that are byte-identical and those that changed. For a patch gate,
   any changed kernel NOT named in in/context.md is a red flag: report it first.
3. Resources per pair (isa_kstat.py): VGPR, SGPR, LDS static/dynamic, scratch (any >0 = spill), waves/SIMD
   (gfx1100: floor(1536/roundup(VGPR,24)), cap 16), workgroup size.
4. Hot loop per pair (isa_mix.py --loops; hot = backward-branch body with most VMEM): per trip and per 256 weights:
   VMEM loads by width/kind, bytes per VMEM instruction, SMEM loads, LDS ops, barriers (+ buffer_gl0_inv after
   them), s_waitcnt list in program order with counters (show the vmcnt sequence, e.g. "17,..,0" vs "11,11,11"),
   VALU split (dot4/fma/cvt/bfe/perm/dpp), VOPD v_dual_*, s_clause, s_delay_alu, cache-policy bits.
5. Float-op inventory for numerics: counts of v_fma*/v_mul*/v_add* (f32 and f16), v_dot*, wmma, conversions
   (cvt to/from f16/bf16), DPP/permlane/bpermute/swizzle reductions, atomics; denorm mode fields.
   Any change here is a candidate bit difference: hand it to P5.
6. Predict, do not claim: for each difference state the expected runtime effect and the counter that would show
   it (e.g. "fewer VMEM issues -> lower WAVE_ISSUE_WAIT / TA_BUSY_avr", "VGPR 250 -> 5 waves: Little's law
   bytes in flight X KB/SIMD").
Output tables: D1 provenance; D2 identity (identical/changed/new/removed); D3 resources; D4 hot-loop diff with
normalization; D5 float-op inventory; D6 predicted effects with the confirming counter or ATT metric.
```

**Kontrole (Opus):**
1. Uruchomić `isa_kstat.py` na jednym z plików i porównać trzy liczby z D3.
2. Każdy kernel spoza `context.md` w D2 jako „changed”: zatrzymać łatkę do wyjaśnienia (np. inna kontrakcja FMA dała md5 `0b7b073b` zamiast `c4708318`, wiki `zgodnosc-bitowa-md5`).
3. Każde twierdzenie z D6 o szybkości: wymagany pomiar (P3) albo ATT. Diff ISA wydajności nie dowodzi.

**Pułapki:**
- `llvm-objdump` przez `rea` ucina wynik na 16 MiB (23a). Używać gołego `llvm-objdump` albo `.s`.
- Liczba `s_waitcnt` nic nie mówi bez wartości liczników. Rolling `vmcnt(11)` w hipBLASLt wymaga etapu w LDS i 256 VGPR (23b).

---

## P3. Pozycja na rooflinie z liczników rocprof

**Kiedy:** chcemy wiedzieć, czy kernel lub klasa kerneli stoi na paśmie, wzorcu, wydawaniu, opóźnieniu czy koszcie stałym uruchomienia, zanim ktoś zacznie przepisywać arytmetykę.

**Wejścia (GPU zbiera Opus, ≤ 10 min, kolejka GPU):**
- `in/trace.csv`: czasy bez liczników, z produkcyjnej konfiguracji. Na przykład `~/qwen-opt/vcost/prof_block.sh off` (rocprofv3 `--kernel-trace`, `GGML_HIP_PM4=0`, prompt mvs), albo istniejący `~/qwen-opt/vcost/prof-gv1/off`.
- `in/pmc.csv`: liczniki z osobnego przebiegu, bo `--pmc` serializuje kernele i zawyża czasy:
  ```
  GGML_HIP_PM4=0 /opt/rocm/core-10.0/bin/rocprofv3 --pmc FETCH_SIZE WRITE_SIZE GRBM_GUI_ACTIVE \
     --kernel-include-regex '<REGEX>' --output-format csv -d /tmp/pmc -o run -- <ta sama komenda llama-server co w prof_block.sh>
  ```
  Drugi przebieg (osobno, bo liczniki się nie mieszczą): `--pmc WAVE_ISSUE_WAIT WAVE_DEP_WAIT TA_BUSY_avr L2CacheHit`. Nazwy pochodzą z `/opt/rocm/core-10.0/share/rocprofiler-sdk/derived_counters.xml`, sekcja `<gfx11>`. Na gfx11 `FETCH_SIZE` = Σ `GL2C_EA_RDREQ_{32,64,96,128}B` × rozmiar, czyli ruch L2 → fabric.
- `in/shapes.csv`: kernel, typ, wiersze, K, ncols, uruchomień na krok. Źródło: GGUF i budżet z raportu 36.
- `in/readceil.sum.txt`: sufit wzorca dla tych siatek (`~/qwen-opt/mmvqbw/logs/readceil.sum.txt`).

```text
TASK P3 — Roofline position of <KERNEL CLASS / REGEX> in <MODE: verify n=5 | draft n=1 | plain> on gfx1100.
Inputs: in/trace.csv (timing, no counters), in/pmc*.csv (counters, serialized run), in/shapes.csv,
in/readceil.sum.txt. Constants: ceiling 926 GB/s (measured, 96.5% of 960 nominal); Infinity Cache 96 MB.
Steps:
1. Join: map each pmc row to a trace row by kernel name + grid + order; report unmatched rows.
2. Model bytes per launch from shapes (weights rows*K*bpw/8 + activations + outputs; GDN: state read + write).
   Q4_K 4.5, Q5_K 5.5, Q6_K 6.5625, Q8_0 8.5, IQ4_XS 4.25 bpw.
3. Measured bytes = (FETCH_SIZE + WRITE_SIZE) KB * 1024. Ratio measured/model: 0.95-1.10 OK; > 1.2 over-fetch
   (re-reads, partial lines, duplicate activation loads); < 0.9 cache-served (L2/Infinity Cache) or wrong model.
   Note: on gfx11 FETCH_SIZE counts GL2->fabric traffic, so Infinity Cache hits still count as fetch
   [INFERENCE from the counter definition]; weights (GB/step) cannot be MALL-resident, small tensors can.
4. Achieved GB/s = model bytes / median duration from trace.csv (NOT pmc durations). % of 926. % of the
   readceil pattern ceiling for the same grid.
5. Fixed-cost fit across shapes of one kernel family: t = t0 + bytes/BW (least squares on median durations,
   >= 4 shapes). Report t0 (us), BW (GB/s), residuals. Compare with report 24r: t0 ~7-9 us, BW 837-873 GB/s.
6. Classify each kernel: BW-BOUND (>= 85% of 926), PATTERN-BOUND (near readceil for its grid but readceil itself
   < 85%), ISSUE-BOUND (WAVE_ISSUE_WAIT high, TA_BUSY_avr high, many small VMEM per byte), LATENCY-BOUND
   (WAVE_DEP_WAIT high, TA_BUSY low, few bytes in flight), FIXED-COST-BOUND (duration < ~3 x t0).
   Each class must cite the numbers that put it there.
7. Floor per kernel = bytes/926; loss = measured - floor; sum the losses per class and check closure against the
   class total in the budget (report 36 table) within 2%.
Output: R1 join report; R2 per-kernel table (launches/step, bytes, us, GB/s, %926, %readceil, measured/model,
class); R3 fixed-cost fit; R4 loss buckets (ms/step) with closure; R5 one lever per bucket with its ceiling.
```

**Kontrole (Opus):**
1. Wartości GB/s powyżej 926 to błąd, najczęściej bajty na token zamiast na przebieg (`lekcja-bledny-roofline`).
2. Suma strat z R4 ≈ czas klasy w budżecie, tolerancja 2%.
3. Czasy muszą pochodzić z przebiegu bez `--pmc`.
4. Przy klasyfikacji PATTERN-BOUND: czy `readceil` miał tę samą siatkę (bloki × fale × wiersze na falę)? Jeśli nie, potrzebny nowy przypadek w `readceil.hip`.

**Pułapki:**
- Ślad z `GGML_HIP_PM4=0` ma koszt AQL (podłoga 2.08 µs na pakiet) zamiast 0.46–0.86 µs granicy taśmy. Do rooflinu wystarczą czasy kerneli, ale przerw z niego nie bierzemy (P4).
- Mikrobench kłamie: zimny cache, inny wzorzec. Liczby końcowe pochodzą z modelu (`lekcja-mikrobench-klamie`).

---

## P4. Narzut uruchomień i hosta w śladzie

**Kiedy:** ms/krok > Σ czasów kerneli albo podejrzewamy przerwy hosta, granice kerneli lub koszt stały uruchomień.

**Wejścia:**
- `in/hg.parse.txt`: ślad ścieżki produkcyjnej z taśmami PM4. `~/qwen-opt/hostgap/hg_trace.sh <ARM>` (`LLAMA_HOSTGAP_TRACE`, kolejka GPU), potem `hg_parse.py LOG --min-steps 30`.
- `in/trace.csv` + `in/burst.txt`: ślad rocprofv3 (`prof_block.sh`, `GGML_HIP_PM4=0`) + `burst_decomp.py DIR`.
- Opcjonalnie `in/hipapi.csv`: `rocprofv3 --kernel-trace --hip-runtime-trace` dla strony CPU.
- `in/wall.txt`: ms/krok bez profilera (`SUMMARY-sweep` albo `spec_sweep`) do zamknięcia bilansu.

```text
TASK P4 — Where does step time go outside kernel bodies in <MODE> (<CONFIG: env flags, draft n, lookup>)?
Inputs: in/hg.parse.txt (production, PM4 tapes), in/trace.csv + in/burst.txt (rocprofv3, PM4 OFF),
optional in/hipapi.csv, in/wall.txt (unprofiled ms/step).
Steps:
1. Step segmentation: a step = between two LM-head launches (largest grid); bursts split at GPU idle >= 40 us;
   roles: GPU top-k, MTP catch-up + draft chain, target verify. State the rule you used and its failure cases.
2. Gap taxonomy with median and p90 per step, separately per source:
   (a) intra-tape kernel boundaries (from PM4 trace if available; PM4-off traces show AQL cost, >= 2.08 us/packet,
       and must not be used for production boundary cost);
   (b) inter-tape host gaps (sampler, acceptance, input building) - tape.l.idle_before in hg;
   (c) profiler-induced inflation: profiled wall vs unprofiled wall;
   (d) in-kernel fixed cost (ramp/tail) - NOT a launch gap: estimate from P3-style t0 fit or readceil.
3. Attribute each host gap to code if hipapi or host marks allow (function names / hg marks), else UNKNOWN.
4. Closure: unprofiled wall = sum(GPU busy of tapes) + sum(inter-tape gaps) within 1% (report 36 closes to 0.01 ms).
   If it does not close, list the residual and its candidates.
5. Levers: for each gap class the known lever (PM4 already on; ZOS-lite inputs-ahead; GPU top-k; fusion to remove
   launches; dataflow tail-overlap) with ms/step ceiling and loss class (all of these are BIT if arithmetic is
   unchanged).
Output: H1 segmentation rule + counts; H2 budget table (item, ms/step, % step, source line); H3 gap distribution
per class (median, p90, n); H4 closure; H5 lever ranking.
```

**Kontrole (Opus):**
1. Sprawdzić H4 z liczbą z `in/wall.txt`.
2. Przerwa w taśmie wzięta ze śladu PM4-off → odrzucić.
3. Koszt stały MMVQ (~7–9 µs × 340) zaliczony jako „launch overhead” → odrzucić. Kernel nie czeka tam na host, tylko ma rampę i ogon siatki (24r). Dźwignią jest geometria siatki, nie PM4.

---

## P5. Audyt bitowości kernela względem referencji

**Kiedy:**
- przed ABBA każdej łatki kernela, która ma być BIT;
- przy przenoszeniu techniki od konkurenta (P1 T5);
- gdy md5 się rozjeżdża.

**Wejścia:**
- `in/src.diff`: diff źródła łatki;
- `in/base.s`, `in/new.s`: `hip_s.sh` na obu drzewach z tymi samymi flagami;
- `in/gates.md`: dotychczasowe wyniki bramek, jeśli są (`mm_dump2` FNV, `test-backend-ops`, md5 plain i MTP na świeżym serwerze, `llama-bx-diff`).

Bazy md5 z wiki `zgodnosc-bitowa-md5`: plain `c4708318…`, MTP `6f14e814…`. Porównujemy MTP z MTP, a bazą jest poprzedni build forka.

```text
TASK P5 — Bit-exactness audit of <PATCH/KERNEL> against <BASELINE BUILD/COMMIT> in modes <plain n=1 | verify n=5 |
draft>. Target class claimed by the author: <BIT | DIST>.
Static part (you):
1. isadiff.py base.s new.s: list changed kernels; every changed kernel must be justified by in/src.diff.
2. For each changed kernel, enumerate every source of float-result change:
   - accumulation order: lane mapping of K, DPP/bpermute/swizzle reduction tree, cross-wave LDS reduction order,
     split-K, atomics (any float atomic = nondeterministic order = not BIT);
   - FMA contraction: compare counts of v_fma/v_mul/v_add (P2 D5); different counts = different rounding;
   - precision: accumulator type, activation format (q8_1 vs f16 vs f32), conversions and rounding mode,
     denorm mode (.amdhsa_float_denorm_mode_*), approximate intrinsics (v_rcp/v_rsq/v_exp/v_log);
   - data-dependent paths: masked/padded rows or lanes that still feed arithmetic (lesson: -inf masked KV rows
     changed WMMA results until zeroed), uninitialized LDS/scratch, tails when rows % R != 0 or ncols != 5;
   - batch dependence: does the result for row j / column c depend on N (ncols) or on which other rows are in
     the launch? Verify==plain requires that it does not.
3. Verdict per kernel: BIT-PROVEN (identical ISA, or identical float DAG by gdnemu-style reasoning), BIT-LIKELY
   (no change source found, dynamic gates pending), DIST (order changes, distribution preserved), LOSSY.
4. Write the exact dynamic gates the engineer must run, with pass criteria (below), choosing only the relevant ones.
Output: B1 changed-kernel list with justification; B2 change-source table (kernel, source, evidence line, effect);
B3 verdicts; B4 gate list (command, expected result, what a failure would mean).
```

**Bramki dynamiczne (Opus, kolejka GPU):**

| bramka | komenda / switch | PASS |
|---|---|---|
| op-level | `test-backend-ops -o MUL_MAT` (+ zmienione opy) na nowym buildzie | 0 FAIL |
| MMVQ hash | `LD_LIBRARY_PATH=<build>/lib ~/qwen-opt/mmvq-bench/mm_dump2` dla obu buildów, `diff` | identyczne FNV dla typów Q4_K, Q5_K, Q6_K, IQ4_XS, Q8_0 … × ncols 1..8 × wiersze 1024/1021 |
| verify == plain | `llama-bx-diff` (gałąź `batch-invariant`), regex `l_out` | „verify batch == plain for all positions” |
| greedy md5 | świeży serwer na każdy przebieg, plain i MTP, oba porównane z poprzednim buildem forka | md5 = baza |
| logity | hash FNV pełnych logitów 64 kroków przy głębokości 0 i 3000 | identyczne |
| DIST | KLD gate (`~/qwen-opt/tools/kld_gate.py`) + nowa referencja md5 | KLD ≤ szum upstreamu |

**Kontrole (Opus):**
1. Werdykt BIT przy zmienionej kolejności sum (split-K, inne drzewo, atomiki) → odrzucić.
2. BIT-PROVEN wymaga albo identycznego ISA, albo przejścia `gdnemu`/`gdncmp`. Same testy dynamiczne dają co najwyżej BIT-LIKELY. Lista w B4 musi obejmować ncols ≠ 5 i ogony wierszy.

---

## P6. Heurystyki dispatchu w zamkniętej lub obcej binarce hosta

Adaptacja REA §3 „Function deep-dive” (jedyny sensowny przypadek użycia `rea`, raport 23a).

**Kiedy:** chcemy wiedzieć, jakie progi i gałęzie naprawdę są w binarce (`.so` innego silnika, build vendora, nasz build o niepewnych flagach).

**Wejścia:** `in/lib.so`, nazwa lub adres funkcji, opcjonalnie źródło dla porównania. Narzędzie: `rea decompile in/lib.so <ADDR> --provider kuna` albo `kuna` wprost (instalacja user-local z 23a). Tylko host x86-64, bo `rea` 6.7.0 nie zna EM_AMDGPU ani EM_CUDA.

```text
TASK P6 — Recover the dispatch rule of <FUNCTION/ADDRESS> in in/lib.so (<what it selects: kernel variant,
tile, path>). Static only. Steps: decompile; list every constant compared and map it to a meaning (type ids,
device capability thresholds, shape thresholds, env lookups); if source is given, map each branch to source
lines and report branches that were compiled out or differ. Output: S1 rule in plain words; S2 constant table
(address, value, meaning, evidence); S3 differences vs source; S4 the minimal input set that exercises each branch.
Legal: only for open-source builds or interoperability; closed vendor libraries: names/metadata only.
```

**Kontrola:** jedna stała z S2 sprawdzona w `objdump -d` pod podanym adresem.

---

## P7. Wznowienie śledztwa: rezydualne niewiadome

Adaptacja REA §16.

```text
TASK P7 — Review <WORKDIR>/out of previous tasks <LIST>. Build a table of every UNKNOWN and INFERENCE claim,
what single observation would settle it, its cost class (CPU-minutes / GPU <= 10 min / GPU > 10 min / code change),
and the ms/step at stake (from the budget). Rank by (ms at stake) / (cost). Do not re-run analyses; propose.
Output: U1 table; U2 the top 3 next tasks written as ready-to-paste P1-P6 prompts with inputs filled in.
```

---

## Mapa: REA-Prompts → ta paczka

| REA (sekcja) | co bierzemy | co odrzucamy |
|---|---|---|
| Tips 1–6, §2 „Explain one feature” | jedno pytanie; FACT/INFERENCE/UNKNOWN; dowód `file:line`; static first; artefakt na końcu | wymaganie „REA” jako narzędzia (brak GPU) |
| §4 „Validate a clone” | „few examples ≠ equivalence” → P5 B4 i kontrola ogonów | `verify_reconstruction` (rea, bez GPU) |
| §10 „Patch diffing” | „where else does the same pattern exist without the fix” → P2 krok 2 (kernele zmienione poza zakresem) | wątek bezpieczeństwa |
| §10 „Crash triage” | „smallest experiment that distinguishes hypotheses” → P3 R5, P7 | — |
| §3 „Function deep-dive” | P6 (host x86-64) | — |
| §7 Firmware | tylko pytania interop o nasze PM4 (wiki `mec-fw-dispatch-aql-gfx11`) | triage obrazów, OTA, sekrety |
| §9 Kernel analysis | nic: to sterowniki OS i IOCTL | całość |
| §5, 6, 8, 11–14 | nic | całość |
