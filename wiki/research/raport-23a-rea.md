---
typ: research
tags: [research, reverse-engineering, narzedzia]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/23a-rea.md:1-111
status: aktualne
---
# Raport 23a: morluto/rea („Reverse Engineer Anything”) – bez wsparcia GPU

**rea (rea-agents 6.7.0, MIT, TypeScript/Node) to orkiestrator MCP/CLI dla agentów wokół zewnętrznych silników (Hopper, Ghidra, IDA, Kuna, JADX, Rizin, GDB, objdump, Frida…) z wynikiem jako Evidence JSON (sha256, provenance, ograniczenia); kodu GPU nie obsługuje – whitelist `e_machine` (`src/domain/elfFixedHeader.ts:69-91`) nie zna EM_AMDGPU 224 ani EM_CUDA 190, brak PTX/SASS/fatbin (raport 23a, CPU, 2026-10-19).**

- Przydatność: niska–umiarkowana, tylko po stronie hosta x86-64: `ggml_cuda_should_use_mmq` z 81 MB `libggml-hip.so` zdekompilowane przez Kuna w 8.06 s / 533 MB RSS (stała `0xc000` = próg `smpbo` 48 KiB, bitmaska typów MMQ `0x78000ff7dcc`).
- Trik: `REA_OBJDUMP_COMMAND=/opt/rocm/core-10.0/llvm/bin/llvm-objdump` deasembluje hsaco gfx1100, ale limit wyjścia 16 MiB (mmvq TU ma 99 MB tekstu). Inne limity: `inspect-binary-layout` ≤ 32 MiB, MCP ≤ 10 MiB.
- Dojrzałość: 0.2.0 (2026-07-12) → 6.7.0 (2026-10-18), ~340 tys. linii TS, tempo wskazuje na kod generowany przez agentów; liczniki gwiazdek (324 tys. w 3 mies.) nieprawdopodobne – nie sygnał jakości.
- **Nie zarejestrowano jako MCP** (`rea setup --client omp` zmieniłby `~/.omp/agent/mcp.json` i dodał skill) – decyzja Main 2026-10-19; użycie ad hoc: `rea … --provider kuna` albo wprost `kuna` (instalacja user-local w `~/.local/opt/`). Dla ISA GPU zostają `llvm-objdump`/roc-obj i `cuobjdump`/`nvdisasm`, ekstrakcja: [[hip-fatbin-extract]].

## Powiązane
- [[research/_hub|research]]
- [[smokinggun]]
- [[gdnemu-isadiff]]
