# 23a — morluto/rea („Reverse Engineer Anything”): ocena dla programu RE GPU

Autor: ResRea · data: 2026-10-19 · tryb: CPU-only (nice 19, taskset 0-3), zero GPU.
Artefakty (poza repo publicznym): `~/qwen-opt/re/rea/` (klon `src/`, wyjścia `out_*.json`, code object `co/036.gfx1100.co`, pełny dump `co/036.dis`).
Skrypt zachowany: `~/KERNEL/tools/re/hip_fatbin_extract.py`.

## TL;DR

- **rea to orkiestrator MCP/CLI dla agentów** (TypeScript/Node, MIT), który owija zewnętrzne silniki (Hopper, Ghidra, IDA, Kuna, JADX, JEB, Rizin/Cutter, GDB, GNU objdump, pwntools, Frida, Playwright, tshark…) i zwraca wyniki jako „Evidence” JSON z SHA-256 artefaktu, provenance i listą ograniczeń.
- **Zero wsparcia dla kodu GPU.** Brak AMDGPU/HSACO, PTX, SASS/cubin, fatbin. Whitelist `e_machine` w `src/domain/elfFixedHeader.ts:69-91` zna tylko x86, x86_64, mips, ppc, arm, hexagon, arm64, riscv — EM_AMDGPU (224) i EM_CUDA (190) kończą się `unsupported ELF architecture` (zweryfikowane na naszym code object, §1.3). Własny decompiler Kuna (SLEIGH) też odrzuca hsaco („no kuna SLEIGH language”).
- **Przydatność dla nas: niska–umiarkowana, tylko po stronie hosta x86-64** (heurystyki dispatchu, tablice wyboru kerneli, miejsca launchu, xrefs, stringi w zamkniętych `.so` silników/vendorów). Tam faktycznie działa: `ggml_cuda_should_use_mmq` z 81 MB `libggml-hip.so` zdekompilowane w 8,06 s / 533 MB RSS.
- Realnym „koniem roboczym” jest **Kuna** (Apache-2.0, pojedyncza binarka); rea dokłada głównie kopertę dowodową (sha256, limitations) i rejestrację MCP. Dla ISA GPU zostajemy przy `llvm-objdump`/roc-obj (AMD) i `cuobjdump`/`nvdisasm` (NV).
- Rekomendacja: **nie rejestrować rea globalnie jako MCP** (zmienia `~/.omp/agent/mcp.json` + instaluje skill — decyzja Main); używać CLI `rea … --provider kuna` lub wprost `kuna` ad hoc dla zadań hostowych. Instalacja user-local gotowa (§5).

## 0. Czym jest rea — fakty i weryfikacja twierdzeń

| Twierdzenie / cecha | Stan faktyczny | Dowód |
|---|---|---|
| „One MCP for reverse engineering across binaries, applications, runtime behavior” | Prawda w sensie orkiestracji: ~130 komend CLI (`rea --help`), serwer MCP (`rea mcp`), skill dla agentów (`.agents/skills/reverse-engineer-anything/SKILL.md`, wersja 42). Analiza natywna **wymaga zewnętrznego silnika** (Hopper/Ghidra/IDA/Kuna). | `docs/cli.md:73-121`, `rea providers --json` (out_providers.json) |
| Licencja | MIT (kod REA); narzędzia zewnętrzne na własnych licencjach; README wprost: komercyjne (IDA/Hopper/JEB) tylko legalnie. | `LICENSE`, README §License |
| „Analysis runs locally” | Brak telemetrii w kodzie: grep `posthog|telemetry|sentry|mixpanel` → jedynie komentarz „Hopper … telemetry” (lokalne diagnostyki, `src/hopper/HopperDiagnostics.ts:8`). Jedyne hosty HTTPS w kodzie niebędącym testami: github.com, hopperapp.com (download Hoppera, opt-in). | grep w `src/` |
| Obsługiwane cele natywne | ELF/PE/Mach-O dla x86/x86_64/arm/arm64/mips/ppc/riscv/hexagon; raw (6502, 68000); .NET, Go/Rust metadata, Android/APK, Electron/JS, WASM, EVM, firmware, pcap, SQLite. | `src/domain/elfFixedHeader.ts:69-91`, `docs/*.md` |
| GPU code objects / PTX / SASS / HSACO | **Brak.** Ani słowa „amdgpu/hsaco/ptx/cuda/rocm/gfx” w `src/` i `docs/` (jedyne trafienia „sass” = preprocesor CSS w `package-lock.json`). | grep (0 trafień) |
| Agent-driven workflow | Tak: MCP + skill; `rea setup --client omp --dry-run` planuje wpis do `~/.omp/agent/mcp.json` i skill do `~/.agents/skills/reverse-engineer-anything` (NIE zastosowano). Klient `omp` jest oficjalnie wspierany. | wynik dry-run (artifact w sesji) |
| Dojrzałość | v6.7.0 (2026-10-18); pierwsza wersja w CHANGELOG 0.2.0 z 2026-07-12; 38 wydań w ~14 tyg. (3.1.0→6.7.0 w 10 dni); 2113 plików TS, ~340 k linii bez testów, 565 plików testów; 3735 commitów. Tempo i objętość wskazują na kod w dużej mierze generowany przez agentów. Licznik 324 k gwiazdek / 82 k forków w ~3 mies. jest nieprawdopodobny — [INFERENCE] nie traktować jako sygnału jakości. | `CHANGELOG.md`, `git` (shallow clone 974487f) |
| Wymagania | Node ≥22.19 (instalowany ręcznie: brak node w systemie); Linux: `ps` procps; pwntools-provider wymaga `REA_PWNTOOLS_PYTHON` z pwntools 4.15.0/pyelftools 0.33/unicorn 2.1.2. | `package.json` engines, komunikat błędu (out_bl_*.json) |
| Twarde limity | `inspect-binary-layout` ≤ 32 MiB pliku; objdump/rizin: 16 MiB stdout+stderr (potem SIGKILL + `output_truncated`); MCP response budget 10 MiB. | out_bl_libggml-hip…json, `docs/reverse-engineering-tools.md` |

## 1. Czego się nauczyliśmy (eksperymenty CPU)

### 1.1 Ekstrakcja naszego code object
`libggml-hip.so.0.26.0` (81 851 752 B): sekcja `.hip_fatbin` = 0x3cdf098 B (≈63,9 MB) przy off 0x141000, zawiera **140 nieskompresowanych bundli** `__CLANG_OFFLOAD_BUNDLE__` (0 × `CCOB`), jeden na TU, wyłącznie `hipv4-amdgcn-amd-amdhsa--gfx1100`.
Nowy skrypt `~/KERNEL/tools/re/hip_fatbin_extract.py --filter mul_mat_vec_q` → jeden TU: `036.gfx1100.co`, 8 307 640 B (mmvq.cu).
Pełny `llvm-objdump -d`: 99 108 303 B tekstu, 862 symbole funkcji, **798 instancji `mul_mat_vec_q*`** (4,2 s CPU).

### 1.2 rea na hsaco — co zwraca
| Komenda | Wynik |
|---|---|
| `rea inspect-artifact co/036.gfx1100.co` | `unsupported_target`: „Cannot open artifact: unsupported ELF architecture.” (out_inspect-artifact.json) |
| `rea inspect-binary-layout` (pwntools) | `unsupported_target`: „Initial layout profile requires x86-64 ELF objects.” |
| `rea inspect-with-objdump … file_headers` (GNU objdump) | `architecture: UNKNOWN!`, format `elf64-little` — GNU binutils nie zna AMDGPU |
| `REA_OBJDUMP_COMMAND=/opt/rocm/core-10.0/llvm/bin/llvm-objdump rea inspect-with-objdump … disassemble` | **Działa jako wrapper** (llvm-objdump autodetekuje gfx1100 z e_flags): poprawny listing RDNA3, ale ucięty na 16 777 216 B → 198/798 kerneli mmvq (≈17 %), `signal: SIGKILL`, `output_truncated: true`. 2,39 s, 453 MB RSS. Zysk vs gołe llvm-objdump: tylko koperta sha256 `d366adb1…35f2`. |
| `kuna functions co/036.gfx1100.co` | „unsupported machine Unknown (no kuna SLEIGH language)” |

Przykładowy fragment z koperty (`out_llvm_dis.json`, raw_result.stdout) — prolog `mul_mat_vec_q_moe<type 41, ncols 2, true>` @0x1c0500: `s_clause 0x6` + 7 × `s_load_b{32,64,128,256}` kernargów, potem jeden `s_waitcnt lgkmcnt(0)` — informacja dostępna identycznie z `llvm-objdump`.

### 1.3 rea na hoście x86-64 — gdzie realnie pomaga
- `rea inspect-artifact libggml-hip.so` → ELF, sha256 `c24635e3…0443`, ale **„Artifact has no child container entries”** — nie widzi 140 offload bundli (graf artefaktów nie zna formatu clang-offload-bundle).
- `rea inspect-binary-layout libggml-hip.so` → odrzucone (>32 MiB). Na `libggml-base.so` (960 096 B): 1,55 s, 1,4 MB JSON (sekcje/segmenty/symbole/relokacje z offsetami plików) — ekwiwalent `readelf -a` z provenance.
- `rea decompile libggml-hip.so 0x4084ad0 --provider kuna` (Kuna 1.906, jobs=1, taskset 0-3): **8,06 s, 533 MB RSS**, pseudokod `ggml_cuda_should_use_mmq` z inwentarza 10 693 funkcji. Weryfikacja vs źródło (`~/llama.cpp/ggml/src/ggml-cuda/mmq.cu:259-319`):
  - `if (0x78000ff7dcc >> type & 1)` — bitmaska typów {2,3,6,7,8,10..14,16..23,39..42} = lista `case` (Q4_0…IQ4_XS, MXFP4, NVFP4, Q1_0, Q2_0);
  - `if (*(info + 0x18 + dev*0x48) < 0xc000) return 0;` = `smpbo < 48*1024` (stride `devices[]` = 0x48 B, `smpbo` @+0x18 w tym buildzie);
  - dalsze stałe (0x1000909, 0x100090c, 0x1001100, 0x1001150, 0x1001200 = progi `GGML_CUDA_CC_*` z offsetem AMD 0x1000000) pokazują, które gałęzie RDNA/CDNA faktycznie skompilowano.
  To jest właściwy przypadek użycia: **potwierdzenie „co naprawdę jest w binarce”** (stałe progowe, inlining, gałęzie po `#ifdef`) bez źródła lub gdy źródło/flagi buildu są niepewne.

## 2. Różnice vs nasz zestaw narzędzi / potrzeby programu RE

| Potrzeba programu | Nasze narzędzie dziś | rea | Werdykt |
|---|---|---|---|
| ISA gfx1100 (VGPR, LDS, waitcnt, mix instrukcji) | `llvm-objdump`, `.amdgpu.metadata`, CSV ResAwesomeRE (`21l-skrypty/ours-llama-opt-gfx1100.csv`, 7832 kerneli) | brak (odrzuca EM_AMDGPU; wrapper objdump tnie na 16 MiB) | **nie używać** |
| SASS/PTX (sm_86/89/120) | `cuobjdump`/`nvdisasm` (Triton bundle, CUDA 13.1), `ptxas` | brak | **nie używać** |
| Ekstrakcja code objects z host `.so` | `hip_fatbin_extract.py`, `kpack_extract.py`, `clang-offload-bundler` | nie widzi bundli | nie używać |
| Host-side dispatch/heurystyki zamkniętych silników i bibliotek (x86-64) | brak decompilera na serwerze (brak Ghidra/Java/IDA) | **Kuna przez rea**: decompile/function/xrefs/search/strings, Evidence z sha256 | **używać ad hoc** |
| Runtime host (CLR/ROCr/rocprofiler) | źródła otwarte | Kuna — tylko gdy binarka ≠ źródło | rzadko |
| Dowody z provenance (reguła evidence-first) | ręczne cytaty file:offset | koperta Evidence (sha256 przed/po, limitations, locations) | miły dodatek |
| PM4 / tape replay | własny `hip-pm4.cu`, dekodery | brak | nie dotyczy |

Wniosek: rea przyspiesza **wyłącznie** część „host-side” zadań ResEnginesBin/ResVendorNv/ResRuntimeAmd (np. jak zamknięty silnik wybiera kernel/tile dla danego M/N/K/arch). Zadania kernelowe (MMVQ/MMQ/FA/GDN/MoE ISA) — zero przyspieszenia.

## 3. Kandydaci (ranking) — zastosowania rea/Kuna w naszym programie

Uwaga: rea nie generuje kandydatów na zmiany kerneli GPU; poniżej usprawnienia procesu RE i jedna weryfikacja buildu. Eksperymenty są CPU-only (nic nie wymaga GPU).

| # | Kandydat | Oczekiwany zysk (arytmetyka) | Effort | Ryzyko | Minimalny eksperyment | Kill criterion |
|---|---|---|---|---|---|---|
| 1 | **Audyt „compiled-vs-source” heurystyk dispatchu w naszym `libggml-hip.so`** (`ggml_cuda_should_use_mmq`, `…_mmvf`, wybór mmvq/MoE, progi ne11) dla każdego buildu produkcyjnego | Wykrycie złej gałęzi/progu = bezpośrednio % decode/prefill; koszt ~10 s CPU/funkcję × ~10 funkcji ≈ 2 min/build; vs ręczne gdb/objdump ~30 min → oszczędność ~90 % czasu audytu | S (0,5 dnia: lista symboli + skrypt porównujący stałe z `GGML_CUDA_CC_*`) | niski (CPU, read-only) | `rea decompile … --provider kuna` dla 10 funkcji dispatchu; porównać stałe z nagłówkami `common.cuh` dla gfx1100 (0x1001100) | 0 rozbieżności w 3 kolejnych buildach → zostawić jako jednorazowy check, nie automatyzować |
| 2 | **Host-side RE zamkniętych/prebuild silników** (np. kernel-selection tables, tile heurystyki w binarkach .so konkurencji bez źródeł) przez ResEnginesBin | Każda odzyskana heurystyka (np. próg przełączenia GEMV→GEMM) = gotowy kandydat do A/B; czas od binarki do pseudokodu funkcji: ~10 s vs brak narzędzia dziś | S (instalacja gotowa) | średni: licencje (EULA NVIDIA/TRT zabraniają RE — sprawdzać per cel), jakość pseudokodu Kuna | jedna funkcja wyboru kernela w jednej binarce konkurencji; ręcznie potwierdzić 3 stałe w `llvm-objdump -d` | pseudokod nieczytelny / niezgodny z disasm w >1 z 3 stałych → używać tylko `kuna disassemble`/objdump |
| 3 | Koperta Evidence (sha256) jako format cytatów w raportach RE | jakościowy: powtarzalność cytatów; koszt ~0 | XS | niski | dołączać `evidence_id` + sha256 do cytatów z binarek hosta | nikt nie korzysta po 2 raportach → porzucić |
| 4 | Rejestracja rea jako MCP w omp dla wszystkich agentów | dostęp do ~130 narzędzi bez CLI; ale 0 dla GPU ISA | S | średni: zmiana globalnej konfiguracji, młody projekt (38 wydań/14 tyg., breaking 6.x), powierzchnia ataku | `rea setup --client omp --dry-run` (zrobione: plan = `~/.omp/agent/mcp.json` + skill) | **Nie robić bez decyzji Main**; domyślnie odrzucone |
| 5 | Patch rea: dodać EM_AMDGPU + provider llvm-objdump / rozbijanie fatbin | umożliwiłoby Evidence dla ISA; ale nasze skrypty już to robią | M–L (TS, 340 k LOC, kontrakty, testy) | wysoki koszt utrzymania przy tempie zmian upstream | — | odrzucone: brak przewagi nad `llvm-objdump` + CSV |

## 4. Do bazy wiedzy

- **rea (morluto/rea, rea-agents 6.7.0, MIT)** = orkiestrator MCP/CLI wokół Hopper/Ghidra/IDA/Kuna/JADX/Rizin/GDB/objdump/Frida; wynik = Evidence JSON (sha256, limitations). Lokalny, bez telemetrii.
- **Nie obsługuje GPU**: whitelist `e_machine` (`src/domain/elfFixedHeader.ts:69-91`) bez EM_AMDGPU 224 / EM_CUDA 190; brak PTX/SASS/fatbin; `inspect-artifact` nie widzi `.hip_fatbin`. Kuna (SLEIGH) też nie zna AMDGPU.
- Trik: `REA_OBJDUMP_COMMAND=/opt/rocm/core-10.0/llvm/bin/llvm-objdump` sprawia, że `inspect-with-objdump` deasembluje hsaco gfx1100 — ale limit 16 MiB (SIGKILL); mmvq TU = 99 MB tekstu → 17 %.
- `libggml-hip.so.0.26.0`: `.hip_fatbin` 63,9 MB, 140 nieskompresowanych bundli (1/TU), tylko gfx1100; mmvq TU = 8,3 MB code object, 798 instancji `mul_mat_vec_q*`. Ekstraktor: `~/KERNEL/tools/re/hip_fatbin_extract.py`.
- Host decompile działa: `ggml_cuda_should_use_mmq` (81 MB .so) w 8 s / 0,5 GB RSS przez Kuna; stała `0xc000` = próg `smpbo` 48 KiB, bitmaska typów MMQ `0x78000ff7dcc`, `ggml_cuda_device_info` stride 0x48 z `smpbo`@+0x18.
- Limity: `inspect-binary-layout` ≤32 MiB, objdump/rizin output ≤16 MiB, MCP ≤10 MiB.
- Dojrzałość: 0.2.0 (2026-07-12) → 6.7.0 (2026-10-18), ~340 k LOC TS; liczniki gwiazdek nieprawdopodobne — nie sygnał jakości.

## 5. Instrukcja użycia (rozesłana do ResVendorAmd, ResVendorNv, ResRuntimeAmd, ResEnginesBin)

Instalacja user-local (wykonana, CPU-only): Node v22.20.0 w `~/.local/opt/node`, `rea-agents@6.7.0` w `~/.local/opt/rea` (`npm i -g --prefix … --ignore-scripts --omit=optional`), Kuna 1.906 w `~/.local/opt/kuna/kuna-v1.906-linux-x86_64/kuna`, venv pwntools w `~/qwen-opt/re/rea/venv-pwn`.

```bash
export PATH=$HOME/.local/opt/node/bin:$HOME/.local/opt/rea/bin:$PATH UV_THREADPOOL_SIZE=4
export REA_KUNA_COMMAND=$HOME/.local/opt/kuna/kuna-v1.906-linux-x86_64/kuna REA_KUNA_JOBS=1
export REA_PWNTOOLS_PYTHON=$HOME/qwen-opt/re/rea/venv-pwn/bin/python   # tylko inspect-binary-layout (≤32 MiB)
# host x86-64: dekompilacja / funkcja / xrefs / wyszukiwanie
nice -n 19 taskset -c 0-3 rea decompile /abs/lib.so 0xADDR --provider kuna --json
nice -n 19 taskset -c 0-3 rea function  /abs/lib.so <symbol> --provider kuna --json
nice -n 19 taskset -c 0-3 rea xrefs     /abs/lib.so 0xADDR --provider kuna --json
# lub bez rea:
kuna decompile /abs/lib.so <func>;  kuna xrefs /abs/lib.so --to <sym>;  kuna strings /abs/lib.so --filter REGEX
# GPU ISA: NIE rea — tylko:
python3 ~/KERNEL/tools/re/hip_fatbin_extract.py <lib.so> <outdir> [--filter <kernel-substr>]
/opt/rocm/core-10.0/llvm/bin/llvm-objdump -d <outdir>/<n>.gfx1100.co
```

Nie zarejestrowano MCP (`rea setup --client omp` zmieniłby `~/.omp/agent/mcp.json` i dodał skill) — decyzja dla Main.
