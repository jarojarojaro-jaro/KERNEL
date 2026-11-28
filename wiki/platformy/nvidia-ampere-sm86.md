---
typ: platforma
tags: [platformy, nvidia, ampere, sm86, playbook]
aktualizacja: 2026-11-28
zrodlo: qwen-opt/skill-io/karty.json:114-133,164-173,353-366; qwen-opt/cloud/hostguard.sh:1-8; ~/qwen-opt/cloud/nvq3/runk204.sh:6-7,92-101; wiki/produkt/final-recipes-nvidia.md; wiki/testy/2026-11-19-k118-nvidia-pelna-moc.md; wiki/testy/2026-11-26-nvq3.md; wiki/testy/2026-11-27-nvq4.md; wiki/testy/2026-11-27-nvq5.md; wiki/REKORDY.md:76-85,112-113,134-136,195; wiki/optymalizacje/jak-przyspieszylismy-nvidia.md; wiki/optymalizacje/latki-na-nvidia.md; wiki/stos/cuda-stos.md
status: aktualne
---
# NVIDIA Ampere sm_86 (RTX 3060, 3070, 3080, 3090): playbook topki

**Na Ampere topkę robi fork CUDA z MTP n2, `kvq`, lean i lookup W16 (3090: 79,97 t/s przy 262 144, [[final-recipes-nvidia]], 2026-11-07); największy hamulec to droga weryfikacja kilku wierszy (V(5)/V(1) = 1,59 na 3090) i procesor hosta, nie karta.**

A100 to sm_80 (osobny build `80`, 2039 GB/s, 80 GB, `karty.json:164-173`): u nas brak pomiaru, łatki sm_86 (`MMVQ_N1_ROWS=2`) trzeba na nim zmierzyć od nowa.

## Dzień pierwszy
- **Sterownik i CUDA:** obraz `nvidia/cuda:12.8.1-devel-ubuntu24.04`, sterowniki na 3090 615.71.09 i 580.173.02 ([[cuda-stos]]); `hostguard.sh` wymaga `cuda_max_good>=12.8`.
- **Bramka pełnej mocy** (`hostguard.sh hg_check`): `power.limit` ≥ 85% domyślnego, `clocks.max.mem` ≥ 85% z `karty.json:353-366` (3060 7501, 3080 9501, 3090 9751 MHz → progi 6376 / 8076 / 8288), temperatura w spoczynku < 80 °C. `summ.py` oznacza LIMITED, gdy zegar spada dopiero pod obciążeniem (3090 w K-114: 5001 MHz) ([[lekcja-vast-tylko-pelna-moc]]).
- **Bramka CPU:** `runk204.sh` mierzy medianę użycia GPU w `llama-bench tg256` (≥ 85%). To nie wystarcza: EPYC 7402 (Zen2) daje 99% w llama-bench, a ścieżka serwera ze spekulacją jest 2,1–2,6× wolniejsza ([[2026-11-28-k207-ablacja-zamiast-lora]]). Na 3090 procesor zmienia dekod o ~27% (Broadwell 69,0 vs Ryzen 87,6, [[2026-11-26-nvq3]]). Hosty EPYC Zen2 odrzucać, zapisywać `cpu.txt`.
- **Build:** tylko `-DCMAKE_CUDA_ARCHITECTURES=86` ([[cuda-stos]]: 3090 fork 787 s), `GGML_NATIVE=OFF`; host bez AVX2 → wariant `kvqleana` (K-127: ta sama prędkość).
- **Sufit pasma:** t/s ≤ pasmo ÷ bajty na token (wagi + KV), ze spekulacją × tok./krok. 3090 936 GB/s (`karty.json:124`) ÷ 10,34 GB (GSQ IQ3_XXS) ≈ 90,5 t/s; 3060 360 GB/s (`karty.json:114`) ≈ 34,8 t/s. 3070 i 3080: pasma brak w `karty.json`.
- **Sanity (K-118, pełna moc, bez spekulacji):** 3090 52,2 t/s (58% pasma), prefill ~11k 1386 t/s; 3060 20,8 t/s, prefill 484 t/s. Mniej niż ~50% sufitu → zły host.

## Kolejność optymalizacji
1. **MTP upstream, `--spec-draft-n-max` dobrane:** 3090 40,93 → 61,49 t/s (+50,2%) przy 245 760 ([[REKORDY]]:195).
2. **Fit kontekstu:** `--spec-draft-n-ubatch 64` (648 → 40 MiB rezerwy), `ub 256`, limit z `cudaMemGetInfo`, nie `nvidia-smi` (313–498 MiB różnicy) ([[jak-przyspieszylismy-nvidia]]).
3. **Fork + `kvq` + lean** (przenosi się 1:1 z AMD): 3090 61,5 → 80,0 t/s przy 262 144. `kvq` sam w krótkim kontekście −4…−5%, zysk w pamięci.
4. **n2 zamiast n4 na sm_86:** T=1 +7,9% (3090), +4,3% (3060) (K-118, K-129).
5. **Lookup W16 + share + GPU verify (`cuda-topka2`):** 3090 78,0 → 93,3 t/s T=1, kopia `mvs` 348,9 t/s ([[REKORDY]]:112-113).
6. **Przełączniki sm_86:** `GGML_CUDA_MMVQ_N1_ROWS=2` +7–8,5%; `GATE_UP_Q8` off; nie wyłączać grafów (−6,9%) ([[latki-na-nvidia]]).
7. **DFlash2 (silnik warp):** +5,2% czat, +12,9% kopia 64k nad warp MTP; warp 126,7 t/s czat na 3090 ([[2026-11-27-nvq4]], [[2026-11-26-nvq3]]); do topki tylko z pełnym kontekstem i igłą.
8. **prism (Bonsai PTQ1_0 + MTP):** 3060 22,2 → 58,3 t/s (×2,6).
9. DSpark i `--ablate-lora` (K-207) przenoszą się bez zmian (llama.cpp); na 3060 Inkling IQ2_S + DSpark 59,5 / 53,4 przy ctx 16k ([[2026-11-27-nvq5]]); pełny kontekst: brak pomiaru.
- Odrzucone: cp.async w MMVQ (−4,7%, K-131), `p-min` > 0.

## Testy
- `hostguard.sh` → `runk204.sh` (bramka CPU) → `k204.py <karta>` (największe `-c`, które startuje i zostawia zapas po rozgrzewce).
- Prędkość: `qwen-opt/nib/wall.py PORT TAG` (kod, tech, pl, json × T=0 / 0,7), `spec_sweep.py` + `copy_prompts.json` (`mvs`/kopia), `qwen-opt/cloud/ink1/xbench.py` (czat, kopia, prefill 2k/8k).
- Kontekst: `qwen-opt/long_ctx_bench.py --depths`, igła `qwen-opt/cloud/needle.py` / `~/k134/k202srv.py` przy 95%.
- Jakość: `md5cmp.py` (T=0 vs upstream), `qwen-opt/tools/kld_gate.py compare`, `refusal.py` dla modeli bez cenzury.

## Kiedy topka jest gotowa
Pełny stos zmierzony na hoście przechodzącym obie bramki; największy kontekst przechodzi igłę 5/5 przy 95% + 700 tok. odpowiedzi; md5 albo `kld_gate` PASS wobec upstreamu; wall 4 × T=0/0,7 i szczyt VRAM zapisane; jedno polecenie startu i wiersz w [[TOPKI]].

## Pułapki
- Ładuje się z 0,5–0,66 GiB wolnego, pada na pierwszym długim prefillu: liczy się tylko fill.
- `-march=native` → `Illegal instruction` bez AVX2 ([[lekcja-paczka-march-native]]).
- KV draftera q4 zużywa więcej VRAM (18,7 vs 17,3 MiB/1k); `p_min` ≥ 0,1 wyłącza DSpark; LoRA w czasie działania −17–33% ([[2026-11-27-k204-enigma-16gb-inkling]]).
- vast-reaper zabił pracującą instancję po jednym „offline”; `pkill -f` zabił `cmake`.

## Rodzaje modeli
- **Dense 27B GDN (Qwen3.8):** kolejność jak wyżej; 24 GB → UD-Q4_K_XL, 12 GB → Bonsai/prism.
- **MoE A2B/A3B:** najpierw zmieścić wszystko w VRAM (LFM UD-IQ3_XXS 3060 102,47 t/s), potem sampler (`LLAMA_SAMPLER_FAST_TOPK`) i fuzje; 10/8 GB z `--n-cpu-moe` to tylko 40,83 / 8,92 t/s.
- **Ternarny (Bonsai):** od razu prism PTQ1_0 + MTP n2.
- **Inkling (pętlowe MoE):** DSpark n2, ub 128, `--ablate-lora`; limitem jest liczba kerneli, nie pasmo ([[inkling-2-mini]]).

## Powiązane
- [[TOPKI]]
- [[final-recipes-nvidia]]
- [[sm-86-89-120]]
- [[2026-11-19-k118-nvidia-pelna-moc]]
- [[rtx-3090]]
