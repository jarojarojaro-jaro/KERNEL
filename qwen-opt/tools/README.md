# Narzędzia: LOO łatek, kanarki KLD, Kernel Tuner

Trzy narzędzia do fork-a `amd-opt` @ c36fd2c87 (65 łatek na e60eff95f, instalacja `~/llama-opt`). Bez GPU działają
wszystkie tryby `--dry-run` / fake. Każda komenda GPU poniżej sama bierze `flock /tmp/gpu.lock flock /tmp/quiet.lock`,
odmawia startu, gdy `pgrep -f 'llama-server.*--port 8080'` coś znajduje, i używa portów 18433–18499.
Kopia w `~/KERNEL/qwen-opt/tools/` (bez `kt/build/`).

## 1. Leave-one-out łatek: `loo.py`

Klasyfikacja (`loo/loo-plan.md`, `loo/loo-plan.json`, przełączniki sprawdzone w źródle na HEAD):

| klasa | liczba |
|---|---|
| wyłącznik env w runtime (`GGML_HIP_*`, `LLAMA_*`) | 27 |
| wyłącznik CLI w runtime (0004 `--spec-draft-vocab`, 0032 `--spec-*-type`) | 2 |
| tylko build (revert + przebudowa) | 22: 8 revertuje się czysto (7 na ścieżce domyślnej), 14 ma konflikty |
| nie-szybkościowe (Vulkan 5, poprawki 3, opt-in 2, narzędzia/testy/refaktor/higiena 4) | 14 |

```
python3 loo.py plan                          # CPU: klasyfikacja + test revertów (git merge-tree)
python3 loo.py run --dry-run --rounds 2      # pokazuje bloki GPU (<= 5 min, 45 s przerwy)
python3 loo.py run --fake && python3 loo.py report --results loo/loo-results.fake.jsonl   # test statystyk
python3 loo.py builds                        # generuje loo/loo-builds.sh (CPU, -j4, flock -s quiet.lock)
```

GPU (wznawialne, wyniki w `loo/loo-results.jsonl`, ukończone próby pomijane):
```
cd ~/qwen-opt/tools
python3 loo.py run --kind env --rounds 2     # 27+2 łatek, ABBA, llama-bench tg128 + serwer (Qwen MTP n=4, LFM), ~3.8 h + przerwy
python3 loo.py report                        # średnie, sparowany 95% CI, flagi NEUTRAL / REMOVAL FASTER
loo/loo-builds.sh                            # CPU: ref + 7 czystych revertów do ~/wt/loo-bins/<NN>
python3 loo.py run --kind build --rounds 2 && python3 loo.py report
```

## 2. Kanarki bramki KLD: `kld_canary.sh` (+ `kld_gate.py`, `perturb_gguf.py`, opis `kld-canary.md`)

Bramka: KLD vs `~/wt/lfm3-prof/ref.kld` (LFM2.5, wikitext-2, 3×16k, ub 1). PASS gdy ΔKLD ≤ 2σ, Δsame-top ≥ −2σ i
KLD 99.9% ≤ 1.25× bazy; IDENTICAL gdy wszystkie liczby równe. Kanarki: KV q4_0 i mieszane, eksperci 4→3, eps×100,
rope +1/+5%, skala wag jednej warstwy ×1.005/1.02/1.10 (kopie GGUF z `perturb_gguf.py`), requant Q4_K_M/Q3_K_M;
kontrole: baza ×2 (determinizm) i `GGML_HIP_KVQ_Q8=0`.
```
./kld_canary.sh list ; ./kld_canary.sh --dry-run all            # bez GPU
python3 kld_gate.py compare ~/wt/lfm3-prof/kld_q8vec1.log ~/wt/lfm3-prof/kld_q4.log   # FAIL (test na prawdziwych logach)
```
GPU (~2 h, wznawialne, wyniki w `~/qwen-opt/kld-canary/`):
```
./kld_canary.sh run baseline baseline2 ctl_vec kv_q4 kv_k8v4 kv_k4v8 moe_k3 eps_x100 rope_p1 rope_p5 && ./kld_canary.sh gate
./kld_canary.sh all        # + kopie wag (prep CPU, 17 GB każda, kasowane po użyciu) i requant
```
Wyjście ≠ 0, gdy któryś kanarek FAIL przechodzi albo baza/kontrola nie przechodzi.
Uwaga: `llama-quantize` (prep q4km/q3km) ładuje runtime HIP — uruchamiać w oknie GPU.

## 3. Kernel Tuner: `kt/kt.py` (venv `~/qwen-opt/.venv-kt`)

Jądra (prawdziwe szablony z ggml, drzewo `~/wt/tools6` = amd-opt + hak `MMVQ_TUNE_NWARPS_N1`):
`mmvq_n1` (Q4_K/Q5_K/Q6_K/Q8_0, 39 kształtów z obu GGUF), `moe_gate_up` i `moe_down` (LFM), `gdn` (Qwen: decode i
weryfikacja MTP z replay). Parametry: NWARPS {1,2,4,8} × ROWS {1,2,4}; GDN: CPW {1,2,4,8,16} × NUM_WARPS {1,2,4}.
```
P=~/qwen-opt/.venv-kt/bin/python; cd ~/qwen-opt/tools/kt
$P kt.py shapes        # kształty z GGUF -> shapes.json
$P kt.py space         # przestrzenie, konfiguracje produkcyjne
$P kt.py compile --all # CPU: 53 warianty gfx1100 + VGPR/SGPR/LDS/occupancy (~17 min, -j4)
$P kt.py isacheck      # CPU: jądra harnessu w konfiguracji produkcyjnej == ISA produkcji
$P kt.py fake          # CPU: referencje numpy, weryfikacja, wstrzyknięty błąd musi zostać wykryty
$P kt.py stub          # stub C dla Kernel Tunera (g++)
$P kt.py table --fake  # format tabeli: kt-table-gfx1100.fake.{json,inc}
$P kt.py tune --dry-run
```
GPU (sam bierze locki przez re-exec; wyniki `kt/results/*.json`, potem tabela):
```
$P kt.py tune --kernel gdn && $P kt.py tune --kernel moe_down && $P kt.py tune --kernel moe_gate_up
$P kt.py tune --kernel mmvq_n1 --shape 17        # pojedynczy kształt (Qwen ffn gate/up Q5_K); bez --shape: wszystkie 39
$P kt.py table          # kt-table-gfx1100.{json,inc}; domyślnie tylko konfiguracje bitowo równe produkcji (--any: wszystkie)
```
Każda konfiguracja: tolerancja vs float64 (CPU) + osobny test bitowy względem konfiguracji produkcyjnej.
