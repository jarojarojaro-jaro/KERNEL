---
typ: platforma
tags: [platformy, apple, metal, mlx, spekulacja]
aktualizacja: 2026-11-28
zrodlo: wiki/testy/skill-io-sufity.md:136-165; wiki/optymalizacje/skill-io-dzwignie.md:78-115; ~/KERNEL/product/research/30-intel-apple-dostep.md:26-31,57-62,89-102,149; ~/KERNEL/product/research/60b-apple-engines-bonsai.md:1-80,144,260-269; wiki/ekosystem/omlx.md; wiki/research/zwiad-2026-11-19.md:12-30; wiki/optymalizacje/prog-draftu-od-kosztu-wiersza.md:22
status: aktualne
---
# Apple Silicon (M1–M5): Metal w llama.cpp, MLX, oMLX

**Na Macu dekod ogranicza pasmo pamięci zunifikowanej, ale weryfikacja draftu na M1–M4 jest ograniczona obliczeniami, więc topka to krótki draft (n1–2) aż do M5; własnego pomiaru na Macu nie mamy (stan 2026-11-28).**

## Pasmo i sufity na chip
Sufity Qwen3.8-27B Q4_K_M, KV q4_0, MTP n4 przy a = 3,2 (`ceiling.py`, [[skill-io-sufity]], 2026-11-17). Pasmo z newsroomu Apple, FP16 wyprowadzone (rdzenie × 128 ALU × 2 × zegar; M5 × 4 przez Neural Accelerators).

| chip | GB/s | FP16 TFLOPS | plain 2k | MTP 2k | prefill 4k |
|---|---|---|---|---|---|
| M1, M1 Pro/Max/Ultra, M2 (wszystkie) | brak w `karty.json` | – | – | – | – |
| M3 Max 40c | 400 | 14,3 | 25 | 72 | 137 |
| M4 Pro 20c | 273 | 8,1 | 17 | 49 | 78 |
| M4 Max 40c | 546 | 16,2 | 34 | 98 | 156 |
| M5 10c | 153 | ~16 | 9 | 28 | 158 |
| M5 Pro 20c | 307 | ~33 | 19 | 55 | 312 |
| M5 Max 40c | 614 | ~65 | 38 | 111 | 625 |

Pamięć użyteczna to ok. 75% RAM (`iogpu.wired_limit_mb`). llama.cpp bierze `recommendedMaxWorkingSetSize` za całą pamięć (21 845 MiB na 32 GiB, R30:62).

## Dzień pierwszy
1. Najpierw M1 Pro właściciela (0 zł), potem Enverge M5 Ultra na 1–2 h ($2,50/h, bez minimum). Scaleway M4 ma 24 h minimum z licencji Apple (R30:26-31,57).
2. Trzy buildy w osobnych katalogach: upstream, `cuda-topka2`, `metal-topka`: `cmake -B build -G Ninja -DGGML_METAL=ON -DCMAKE_BUILD_TYPE=Release` (R30:97).
3. Bramka ≤ 10 min: `test-backend-ops -b Metal -o TOP_K/GET_ROWS/SUM_ROWS/ARGSORT`, potem `gate_chat.py` z md5 przy `LLAMA_GPU_VERIFY=0` vs `1` (R30:98).
4. Obok: oMLX (MLX) z Lightning MTP na tym samym modelu jako konkurent.

## Kolejność optymalizacji
1. **Spekulacja krótka: MTP n1–2.** Na M1–M4 weryfikacja N = 5 to 256 GFLOP, czyli 63 ms obliczeń przy 59 ms bajtów na M4 Pro. Na XTX to 4 vs 17 ms. Cudzy pomiar: M4 6,35 → 3,25 t/s z 3 draftami (skill-io `levers.md:35`). Na M5 n3–4, bo obliczenia spadają do 8 ms przy 26 ms bajtów.
2. **Próg draftu `p_min` 0,5 na Metal** (reguła Straty, [[prog-draftu-od-kosztu-wiersza]]). Brak naszego pomiaru.
3. **Lookup W16 i słownik draftu 64k.** Są w common/server, więc przenoszą się bez zmian [INFERENCE]. Brak naszego pomiaru.
4. **Atencja wierszy draftu parami** (TensorFold): +24–29% dekodu z draftem przy 32k na M3 Ultra ([[zwiad-2026-11-19]]). To odpowiednik naszego `kvq`.
5. **KV q4_0 z FA na Metal.** Ścieżka `vec` istnieje (87 trafień w grepie). Trzeba sprawdzić, czy N = 5 idzie ścieżką dekodu ([[skill-io-dzwignie]]).
6. Kafle FA i MMQ pod simdgroup 32 i 32 KB pamięci threadgroup: kafle z CUDA nie pasują. Brak naszego pomiaru.

Sprzężone próbkowanie (`GUMBEL_MAX`) ma tylko CPU i CUDA, więc na Metal liczy się na CPU (R30:149).

## MLX i llama.cpp Metal
- **oMLX 0.7.2:** Lightning MTP, czyli łańcuch draft/verify z jedną synchronizacją hosta na cykl i adaptacyjną głębokością z parkowaniem MTP. Ma też snapshot GDN `(conv, ssm)` i DFlash. Wynik cudzy: M3 Ultra, Qwen3.6-27B greedy 42,8 → 55,1 t/s ([[omlx]]).
- **mlx.fast (Bonsai 2 9B, M5 Max):** 144,8 → 959,6 t/s (+471%), 9,5 tokenu na rundę. Drzewo 15 węzłów w 16-wierszowej weryfikacji i kafle wag po 1152 B (60b:144,204-206).
- **llama.cpp Metal:** nasze łatki host, sampler i spekulacja przenoszą się. Kerneli `kvq` i FA D256 trzeba portować do MSL ([[skill-io-dzwignie]]).
- Wybór silnika: oba na tym samym pliku i tym samym `wall.py`. Brak naszego pomiaru.

## Testy
`test-backend-ops -b Metal`, `gate_chat.py` (md5 T=0), `spec_sweep.py` (n1/n2/n4, T=0 i T=1), `copy_bench.py`, `long_bench.py`, `needle.py --tokens <c>` (5/5 przy 95% głębokości), `wall.py`, `kld_gate.py compare`. Narzędzia są w czystym Pythonie po HTTP, więc działają na macOS (R30:91).

## Kiedy topka jest gotowa
- Pełny stos: spekulacja + lookup + KV q4 + największy kontekst, który przechodzi igły.
- md5 T=0 z drafterem = bez draftera.
- Zapis w [[TOPKI]] i [[REKORDY]] w tej samej turze co pomiar.
- Odczyt na XTX ma 71–77% sufitu ([[skill-io-sufity]]). Na Macu celem jest ≥ 60% sufitu MTP z tabeli [INFERENCE].

## Pułapki
- `MemAvailable` kłamie przy pamięci zunifikowanej. Limit wired ustawia się ręcznie.
- Głęboki draft na M1–M4 spowalnia, a nie przyspiesza.
- Metal koduje bufory komend co token i nie ma replay jak grafy CUDA. Narzut hosta widać przy małych modelach.
- Scaleway i AWS mają 24 h minimum, więc koszt testu to doba.

## Rodzaje modeli
- Dense 27B: krótki MTP, lookup.
- MoE (Inkling, LFM): mało bajtów na token, więc dominuje liczba kerneli. oMLX 0.8.2 ma Inklinga, liczb brak ([[inkling-2-mini]]).
- Ternary Bonsai: mlx.fast jako wzorzec.

Szczegóły rodzajów: [[rodzaje-modeli]].

## Powiązane
- [[arc-b580-i-mac]]
- [[skill-io-sufity]]
- [[omlx]]
- [[raport-60b-apple-bonsai]]
- [[TOPKI]]
