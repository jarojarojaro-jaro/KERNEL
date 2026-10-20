# Szablon briefu robotnika DeepSeek v4.1 Flash

Inżynier kopiuje ten szablon do `~/qwen-opt/ds/briefs/<karta>-<temat>-<n>.md`, wypełnia `<…>`, dokleja wspólną część
karty (`<karta>-common.md`) i uruchamia:
`setsid -f ~/qwen-opt/tools/ds-agent <karta>-<temat>-<n> <worktree> ~/qwen-opt/ds/briefs/task-<karta>-<temat>-<n>.md 45m`.
`ds-agent` sam dokleja reguły twarde (edycja tylko w worktree, bez GPU, bez wynajmu, bez push, `nice -n 19`, ≤ 4 wątki).
Brief piszemy po angielsku (robotnik), konkretnie: liczby, pliki, funkcje, komendy.

---

```markdown
# Brief: <switch / task name> — <one-line goal>

## Goal
Measured on <card, sm_XX> with <model + quant>, -c <ctx>, KV q4_0, <workload> (<date>, report <file:line>):
- <the number that motivates the task, e.g. "Q6_K MMVQ ncols=5 at K=5120 runs at 555 GB/s of 936 (148 regs, 12 warps/SM)">;
- <what was already tried and its result, so you do not repeat it>.
Hypothesis: <why the change should save X ms/step or Y MiB; the ceiling>.

## Change (worktree `<~/wt/branch-x>`, branch `<branch-x>`; edit only here)
1. <file:function — exact change>.
2. Behind an env switch `<GGML_CUDA_…>=<values>`, default off; default path must compile to identical PTX/code.
3. <tests to add or extend: test-backend-ops case, host-side emulation, hash of outputs>.

## Constraints
- Bit-exact: <yes — output identical for every value | no — then provide a KLD check plan against the CPU fp32 reference>.
- Do not touch: <files/paths>. Keep code that existed before byte-identical outside the switch.
- Compile check (no run): `cmake -S <worktree> -B /tmp/ds-<name> -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=<86|89|120>
  -DCMAKE_CUDA_COMPILER=$HOME/opt/cuda-12.8/bin/nvcc -DCUDAToolkit_ROOT=$HOME/opt/cuda-12.8 -DLLAMA_CURL=OFF -DGGML_CCACHE=OFF`
  then `nice -n 19 cmake --build /tmp/ds-<name> -j4 --target <ggml-cuda|test-backend-ops|llama-server>`; report ptxas
  registers/spills for the touched kernels (`-Xptxas -v` on the touched .cu); remove /tmp/ds-<name> at the end.
- Time box: <≤ 20 | ≤ 45> minutes. If blocked, stop and report what you found.

## Finish
One commit on `<branch-x>` (message: what, switch values, bit-exact or not, the motivating numbers).
Report (final answer):
- diff summary (files, functions, +/− lines);
- registers/spills table before/after for the touched instances;
- compile OK for sm_<XX> (command and result);
- exactly how the engineer verifies on the GPU: test-backend-ops filter, md5 gate, ABBA arms and env values.
```

---

Zasady dla inżyniera przy pisaniu briefu:
- Zawsze podaj liczbę z pomiaru i jej źródło; robotnik nie widzi raportów.
- Jeden brief = jedna hipoteza; warianty jako wartości jednego przełącznika.
- Zadania debugowe (np. błędne wyjście `GGML_CUDA_MMVQ_PIPE`): cel = test na CPU/hoście, który odtwarza błąd i pokazuje
  poprawkę; bez GPU.
- Po wyniku: czytasz diff, kompilujesz u siebie dla `sm` karty, dopiero potem GPU (≤ 10 min, ABBA, bramka).
