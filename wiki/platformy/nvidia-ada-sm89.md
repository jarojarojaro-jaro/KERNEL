---
typ: platforma
tags: [platformy, nvidia, ada, sm89, playbook]
aktualizacja: 2026-11-28
zrodlo: qwen-opt/skill-io/karty.json:134-143,353-366; qwen-opt/cloud/hostguard.sh:1-8; ~/qwen-opt/cloud/nvq3/runk204.sh:92-101; wiki/produkt/final-recipes-nvidia.md; wiki/testy/2026-11-19-k118-nvidia-pelna-moc.md; wiki/testy/2026-11-27-k204-enigma-16gb-inkling.md; wiki/karty/rtx-4060-ti.md:9; wiki/KOLEJKA-TESTOW.md:223,251; wiki/REKORDY.md:117,138,191-193; wiki/optymalizacje/jak-przyspieszylismy-nvidia.md
status: aktualne
---
# NVIDIA Ada sm_89 (RTX 4060 Ti, 4070, 4080 SUPER, 4090, L4): playbook topki

**Na Adzie weryfikacja kilku wierszy jest tańsza niż na Ampere (V(5)/V(1) = 1,26 na 4080 SUPER), więc MTP n4 zostaje; topki: 4090 101,27 t/s przy 262 144 (fork+kvq+lean), 4060 Ti Inkling + DSpark 48,58 / 48,99 t/s przy 283 648 (2026-11-07 / 2026-11-27).**

## Dzień pierwszy
- **Sterownik i CUDA:** CUDA 12.8 (`nvcc 12.8.93`, [[cuda-stos]]), upstream b12811 w K-204; `hostguard.sh` wymaga `cuda_max_good>=12.8`.
- **Bramka pełnej mocy** (`hostguard.sh hg_check`): moc ≥ 85% domyślnej, `clocks.max.mem` ≥ 85% z `karty.json:353-366` (4060 Ti 9001, 4070 10501, 4080 SUPER 11501, 4090 10501 MHz), < 80 °C. Uwaga na hosty z niskim limitem: 4090 w 67c chodziła na 250 z 450 W, 4060 Ti w raporcie 29 na 100 W ([[lekcja-limit-mocy-hosta]]).
- **Bramka CPU:** `runk204.sh` (llama-bench tg256, użycie GPU ≥ 85%) plus odrzucanie EPYC Zen2: na nim llama-bench pokazuje 99%, a serwer ze spekulacją jest 2× wolniejszy ([[2026-11-28-k207-ablacja-zamiast-lora]]). 4060 Ti w K-204 stała na Threadripperze 2950X.
- **Build:** tylko `-DCMAKE_CUDA_ARCHITECTURES=89`, `GGML_NATIVE=OFF`. Ada nie ma PDL ani TMA, ma FP8 ([[karty-nvidia-parametry]]).
- **Sufit pasma:** t/s ≤ pasmo ÷ bajty na token, ze spekulacją × tok./krok. 4090 1008 GB/s (`karty.json:134`) ÷ 10,34 GB ≈ 97,5 t/s bez spekulacji; 4060 Ti 288 GB/s ([[rtx-4060-ti]]) ≈ 27,9 t/s. 4070, 4080 SUPER, L4: pasma brak w `karty.json`.
- **Sanity:** 4080 SUPER bez spekulacji 55,7 t/s (78% pasma), prefill ~11k 1862 t/s (K-118); 4090 UD-Q4_K_XL bez MTP 46,94 t/s przy 262 144; 4060 Ti GSQ bez MTP 23,7 t/s przy 217 088 ([[REKORDY]]).

## Kolejność optymalizacji
1. **MTP upstream n3:** 4090 46,94 → 76,44 t/s (+62,8%) przy 262 144 ([[REKORDY]]:192).
2. **Fit:** `--spec-draft-n-ubatch 64`, `ub 256` (ub 512 to OOM na 4090), limit z `cudaMemGetInfo` ([[jak-przyspieszylismy-nvidia]]).
3. **Lean (łatka 0002 z AMD):** 4060 Ti 24,0 → 36,3 t/s (+51%) przy 229k.
4. **Fork + `kvq` + lean, MTP n4 + słownik 64k:** 4090 76,44 → 101,27 (+32,5%). Mikrokernel `kvq` na L4 5× szybszy od FA (nb2 191,5 → 37,7 µs, [[KOLEJKA-TESTOW]]:251).
5. **Długość draftu:** sm_89 zostaje n4 (4080 SUPER n2 vs n4 −1,7 / +1,2%); L4 pokazała n2 +6,9% T=1, więc przed topką zmierzyć n2/n3/n4 na tej karcie.
6. **Lookup W16 + share + GPU verify:** 4060 Ti 18,6 → 35,4 t/s T=1, kopia `mvs` 170,9 przy ctx 32k ([[REKORDY]]:117).
7. **DSpark (Inkling):** 4060 Ti 23,94 → 48,58 t/s przy 283 648 (+103%) wobec starego przepisu Qwen.
8. **`--ablate-lora` (K-207)** przenosi się (llama.cpp, nasz build); na 5060 Ti +15,5% / +27,5% nad LoRA; na Adzie brak pomiaru.
9. **prism (Bonsai PTQ1_0 + MTP n2):** 4070 94,73 t/s przy 208 896.

## Testy
- `hostguard.sh` → `runk204.sh` → `k204.py <karta>` (szukanie `-c`, wall, głębia, prefill ub 512/256/128).
- `qwen-opt/nib/wall.py` (4 prompty × T=0 / 0,7), `spec_sweep.py` + `copy_prompts.json` (`mvs`), `qwen-opt/cloud/ink1/xbench.py`.
- `qwen-opt/long_ctx_bench.py`, igła `qwen-opt/cloud/needle.py` / `~/k134/k202srv.py` przy 95%.
- `md5cmp.py`, `qwen-opt/tools/kld_gate.py compare`, `qwen-opt/nib/refusal.py`; V(n) przez `llama-bench -p 1,2,3,5 -ub 5 -n 0`.

## Kiedy topka jest gotowa
Pełny stos (spekulacja + kwant + KV q4 + fork/build) na hoście po obu bramkach; największy `-c` z igłą 5/5 przy 95% + 700 tok.; md5 albo `kld_gate` PASS; wall, szczyt VRAM, CPU i W zapisane; wiersz w [[TOPKI]]. Dziś 4080 SUPER (107,3 t/s n4 T=0) ma tylko diagnostykę przy ctx 8192, a L4 nie ma pomiaru t/s: to nie są topki.

## Pułapki
- 16 GB z MTP ładowało się z 0,5–0,66 GiB wolnego i padało przy pierwszym długim prompcie ([[lekcja-fit-mtp-16gb]]).
- KV draftera q4 (`-ctkd/-ctvd`) przy DSpark zużywa więcej VRAM i pada przy 270k; `p_min` ≥ 0,1 wyłącza DSpark; LoRA −17–33% ([[2026-11-27-k204-enigma-16gb-inkling]]).
- Reaper potrafi zabić pracującą instancję po jednym odczycie „offline”.

## Rodzaje modeli
- **Dense 27B GDN (Qwen3.8):** MTP → fit → fork/kvq/lean → lookup; 24 GB UD-Q4_K_XL, 16 GB GSQ IQ3_XXS.
- **MoE A2B/A3B (LFM, Qwen3.6-35B):** całość w VRAM (4070 LFM UD-IQ3_XXS 179,32 t/s), sampler, fuzje LFM; spekulacja daje mniej niż na dense ([[lekcja-dense-szybszy-od-moe-ze-spekulacja]]).
- **Ternarny (Bonsai):** prism PTQ1_0 + MTP n2 na 12 GB.
- **Inkling (pętlowe MoE):** na 16 GB IQ3_S + DSpark n2, ub 128; limit to narzut kerneli ([[inkling-2-mini]]).

## Powiązane
- [[TOPKI]]
- [[final-recipes-nvidia]]
- [[2026-11-27-k204-enigma-16gb-inkling]]
- [[sm-86-89-120]]
- [[rtx-4080-super]]
