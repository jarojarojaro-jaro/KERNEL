# auto-gpu-kernel (Dogacel)

- Repo: https://github.com/Dogacel/auto-gpu-kernel
- Raport: `archive/report.pdf` w repo („Auto GPU Kernel: Autonomous Kernel Discovery for DeepSeek Sparse Attention”, Doğaç Eldenk, Northwestern)
- Wynik: **#1 w MLSys 2026 FlashInfer AI Kernel Generation Contest**, ścieżka DSA (DeepSeek Sparse Attention), sub-track „Full-Agent” (zero człowieka w pętli). Średnie przyspieszenie **34.93×** względem baseline'u FlashInfer na **NVIDIA B200**.
- Przeanalizowane: 2026-10-03

## TL;DR

To **nie jest kompilator ani autotuner** w klasycznym sensie. To **harness dla agenta AI** (Claude), który w pętli
pisze kernel w Tritonie → sprawdza poprawność → mierzy → zapisuje wynik → następna iteracja.
Cała „magia” to dyscyplina eksperymentów, a nie sprytny algorytm przeszukiwania.

Teza autora: *wąskim gardłem autonomicznego pisania kerneli nie jest model, tylko zarządzanie eksperymentami
(rzetelny pomiar + pamięć o tym, co już próbowano).*

## Architektura

Dwa narzędzia CLI (Python, `pyproject.toml` → pakiet `kbench`):

| Narzędzie | Rola |
|---|---|
| `kbench` | Walidacja poprawności, benchmarki, historia wyników, paired A/B. Backendy: `local` (Linux + GPU), `modal`, `fal` (chmurowe GPU). |
| `kopt` | Pętla agenta. Odpala agenta [OMP / oh-my-pi](https://github.com/can1357/oh-my-pi) przez RPC, jedna iteracja = jeden prompt `/skill:optimize`. Pilnuje budżetu ($), liczby iteracji i wykrywa „zawieszenie” (3 iteracje bez zalogowanego eksperymentu → stop). Ma `kopt watch` (podgląd w przeglądarce). |

Dwa tryby:
1. **FlashInfer** – gotowe definicje kerneli + trace'y z konkursu (`flashinfer-ai/mlsys26-contest` na HF).
2. **Dowolne repo git** – piszesz `task.toml` po ludzku (cel, jak mierzyć, jak walidować), a agent w pierwszej
   „setup turn” sam generuje `harness/validate.py` i `harness/benchmark.py`. Potem optymalizuje.

Jest przykład **MLX attention na Apple Silicon** (`examples/mlx-attention`, `configs/mlx_attention.toml`) –
naiwne attention ~2.7 ms vs `mx.fast` ~0.9 ms na M4 Pro. Agent ma napisać fused kernel Metal przez
`mx.fast.metal_kernel`. **To jest najbliższe „lokalnemu AI” – da się odpalić na Macu bez chmury.**

## Pętla jednej iteracji (`/skill:optimize`)

1. **Assess** – czytaj kernel, `summary.md` (tabela wszystkich eksperymentów), `LESSONS.md` (trwałe wnioski). Nigdy nie ufaj pamięci z kontekstu.
2. **Plan** – JEDNA zmiana. Progresja: PyTorch → tiled Triton → fused → tuning tile'i → inne tilingi.
3. **Implement**
4. **Validate** – `kbench bench --quick` (2 workloady: najmniejszy + największy, łapie błędy kształtów).
5. **Measure** – `kbench bench --stride 2` (połowa workloadów). Różnice <5% → paired A/B na tej samej maszynie.
6. **Log** – `experiments/exp_N/` (snapshot kernela, `result.md`, `bench.log`) + wiersz w `summary.md`. Logujemy też porażki.
7. **Decide** – wygrana ≥5% → zostaw; marginalne → A/B; regresja → revert.

### Sub-agenty (komunikują się tylko przez pliki na dysku, nie przez rozmowę)
- **profiler** – instrumentuje kernel `torch.cuda.Event`-ami, mówi, która faza zżera czas → `profile.md`.
- **workload-inspector** – analizuje *dane wejściowe* (rozkład batch size, długości sekwencji, ile paddingu) → `workload_profile.md`.
- **research** – świeży kontekst, czyta tylko artefakty, diagnozuje plateau i pisze plan następnego eksperymentu.

## Kluczowe zasady (każda dodana, bo agent ją kiedyś złamał)

- **Tylko absolutne latencje.** Latencja referencji skacze 20–30% między VM-ami → ratio „speedup” kłamie.
- **Jedna optymalizacja na iterację** – inaczej nie wiadomo, co dało zysk.
- **Paired A/B** dla różnic <5%: oba warianty na tej samej maszynie, jeden po drugim.
- **Zero oszukiwania benchmarku** – zakaz CUDA graphs, memoizacji wyników itp.
- **Zostań w Tritonie** (Gluon dopiero po 15–20 iteracjach bez postępu).
- **Brak dostępu do internetu** dla agenta.

## Co agent faktycznie odkrył (sparse attention, 54 eksperymenty)

Progresja „new best”:

| Exp | Zmiana | Latencja |
|---|---|---|
| 1 | Fused Triton, online softmax, 1 program na token | 0.100 ms |
| 2 | **Split-K / flash-decoding** (8 splitów + kernel combine) | 0.024 ms (**4.2×**) |
| 6 | Dynamiczna granica pętli – pomija padding | 0.022 ms |
| 7–8 | Równoległy combine po wymiarze D | 0.020 ms |
| 9 | BLOCK_N=128 | 0.016 ms |
| 11 | **Hybrid dispatch**: osobny kernel dla T≤2, split+combine dla T≥3 | 0.016 ms |
| 15 | Split+combine w **jednym launchu** przez atomową barierę w kernelu | 0.016 ms |
| 26 | **Stride-partition** – split `s` bierze pozycje `s, s+8, s+16…` zamiast ciągłego bloku | 0.016 ms (duży zysk na małych) |

Finał: sparse attention **0.010 ms**, TopK indexer **0.016 ms**.

### Największe wygrane NIE były mikro-tuningiem
1. **Specjalizacja pod dane.** ~połowa trace'ów ma mniej ważnych tokenów niż K=2048 → top-k jest zbędne,
   wynik to po prostu lista ważnych ID. Agent wpadł na to dopiero po dodaniu `workload-inspector`.
2. **Split-K (flash-decoding)** – przy małym batchu 1 CTA/token = 147 z 148 SM-ów stoi bezczynnie.
3. **Mniej launchy** – każdy launch na B200 to ~8 µs; przy kernelach rzędu 10–20 µs to ogromny koszt.
4. **Fused radix top-k** w Tritonie zamiast `torch.topk` + osobnego remapu.

### Ciekawe lekcje techniczne (z `LESSONS.md`)
- `if` w gorącej pętli Tritona psuje pipelining (`num_stages`) → zamiast tego policz granicę pętli z góry.
- Online softmax: `exp2(-inf - -inf) = NaN` → guard, gdy cały blok to padding.
- Softmax w bazie 2 (`exp2`/`log2`, scale × log2e) – szybsza ścieżka.
- Nie skaluj Q w bf16 (cast→mul→cast) – utrata precyzji; skaluj logity w fp32.
- `tl.static_range(N)` przy dużym N rozdmuchuje kod/rejestry → regresja 5×.
- Kernel combine na jednym CTA = serial bottleneck; diagnoza: czas płaski względem `num_warps` i T.

## Wnioski autora o językach i modelach

- Testowane: CUDA, CuTeDSL, Triton, Gluon, Helion. **Triton wygrał nie dlatego, że najszybszy, tylko że najłatwiejszy
  dla agenta** – krótkie edycje, mało błędów kompilacji. W CUDA agent tonął w cyklu kompiluj–naprawiaj i zapominał o celu.
- Claude Opus 4.7 vs DeepSeek-V3 w tej samej pętli: DeepSeek potrzebował wielokrotnie więcej iteracji, utykał na składni.
  „Poniżej pewnego progu zdolności modelu higiena eksperymentów nie pomoże.”
- Czego agent NIE znalazł sam: akumulatory w bf16 zamiast fp32, reużycie buforów zamiast `torch.empty` co wywołanie,
  dopasowanie tile'i do natywnego MMA Blackwella (tcgen05 64×64×128).
- Folder `archive/fable/` – późniejsze wyniki (nowszy model) na 5 kernelach, m.in. MoE FP8 i GDN (Gated DeltaNet);
  tu agent przepisał części do Gluona (cp.async, mma_v2), czego wcześniejszy model nie dawał rady.

## Czy to nam się przyda do lokalnego AI?

**Plusy:**
- Metodologia (absolutne latencje, A/B, jedna zmiana naraz, log wszystkiego) jest uniwersalna – warto ją przyjąć
  w naszych własnych eksperymentach, nawet ręcznych.
- Tryb „dowolne repo” można teoretycznie skierować na np. llama.cpp / MLX / własny kod inferencji.
- Przykład MLX działa na Macu lokalnie.

**Minusy / ograniczenia:**
- Kernele z konkursu są pod **B200 (datacenter)** i pod bardzo specyficzne kształty DeepSeek-V3.2 – na konsumenckie GPU
  nie przeniosą się 1:1.
- Wymaga agenta OMP + klucza API do modelu → **każda iteracja kosztuje** (tokeny). Pętla ma `--budget`.
- Tryb FlashInfer bez lokalnego GPU wymaga Modal/FAL (płatne chmurowe GPU).
- Zysk 34.93× jest względem baseline'u referencyjnego konkursu, a nie względem najlepszych ręcznych kerneli.

## Do sprawdzenia dalej
- [ ] Odpalić przykład `mlx-attention` (jeśli jest Mac z Apple Silicon).
- [ ] Przeczytać kod finalnego `sparse_fused.py` linijka po linijce – dobra lekcja flash-decodingu.
- [ ] Flash-decoding / split-K – osobna notatka (to kluczowa technika dla decode przy batch=1, czyli lokalnie).
- [ ] Online softmax – osobna notatka.
