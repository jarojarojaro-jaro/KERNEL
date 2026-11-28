---
typ: platforma
tags: [platformy, nvidia, hopper, sm90, playbook, serwer]
aktualizacja: 2026-11-28
zrodlo: qwen-opt/skill-io/karty.json:174-193; qwen-opt/cloud/hostguard.sh:1-8; wiki/karty/google-colab.md:13-18; wiki/research/raport-21f-inferencex.md:19; wiki/lekcje/lekcja-akceptacja-h100-nie-przenosi-sie.md; wiki/ekosystem/megakernel-zoo.md:13-25; wiki/modele/drafter-dflash.md:44; wiki/stos/sm-86-89-120.md; wiki/testy/2026-11-19-k118-nvidia-pelna-moc.md; wiki/optymalizacje/jak-przyspieszylismy-nvidia.md
status: aktualne
---
# NVIDIA Hopper sm_90 (H100, H200): playbook topki

**Na H100 nie mamy własnego pomiaru (brak pomiaru, 2026-11-28); punkt odniesienia z zewnątrz to Qwen3.8-27B bf16 na vLLM z DSpark k=7: 86,1 tok/s przy c=1 (InferenceX, 2026-10-19), a nasz pierwszy krok to przeniesienie przepisu RTX i pomiar V(n), bo akceptacja i koszt szerokości z H100 nie przenoszą się na inne karty.**

## Dzień pierwszy
- **Dostęp:** Colab H100 tylko z zapowiedzią kosztu ([[google-colab]]); wynajem tylko za zgodą JARO.
- **Sterownik i CUDA:** minimum jak na RTX (CUDA 12.8, `cuda_max_good>=12.8` w `hostguard.sh`); wersję sterownika zapisać przy wyniku.
- **Bramka pełnej mocy:** moc ≥ 85% domyślnej, temperatura < 80 °C; `karty.json → mem_clock_mhz` nie ma H100, więc próg zegara HBM trzeba dopisać przed użyciem `hostguard.sh` (dziś brak).
- **Bramka CPU:** llama-bench tg256 z użyciem GPU ≥ 85% (`runk204.sh`) plus odrzucanie EPYC Zen2: na RTX 5060 Ti EPYC 7402 dawał 99% w llama-bench i 2,1–2,6× wolniejszy serwer ze spekulacją ([[2026-11-28-k207-ablacja-zamiast-lora]]). Na H100 krok jest krótszy, więc narzut hosta waży jeszcze więcej.
- **Build:** tylko `-DCMAKE_CUDA_ARCHITECTURES=90a` (wgmma i TMA wymagają `a`); nie dokładać 86/89/120.
- **Sufit pasma:** t/s ≤ pasmo ÷ bajty na token, ze spekulacją × tok./krok. H100 SXM 3350 GB/s, 80 GB (`karty.json:174-183`) ÷ 10,34 GB (GSQ IQ3_XXS) ≈ 324 t/s; Qwen3.8-27B UD-Q4_K_XL czy Q6_K liczyć z rozmiaru pliku. H200 4800 GB/s, 141 GB (`karty.json:184-193`).
- **Sanity:** dekod bez spekulacji powinien dojść do ≥ 58–78% sufitu (tyle 3090 i 4080 SUPER w K-118); mniej → host albo narzut kerneli. Megakernel-zoo: Qwen3-8B na H100 88% sufitu pasma ([[megakernel-zoo]]).

## Kolejność optymalizacji
1. **Przepis RTX bez zmian:** pin, MTP n3, KV q4_0, `--spec-draft-n-ubatch 64`. Na RTX MTP dało +50–63% ([[jak-przyspieszylismy-nvidia]]); na H100 brak pomiaru.
2. **Kontekst:** na 80 GB pełny kontekst 27B mieści się z większym kwantem [INFERENCE: brak pomiaru fit]; wybierać większy kwant (jakość), sprawdzać KLD i fill.
3. **V(n) przez `llama-bench -p 1,2,3,5 -ub 5 -n 0 -r 5`:** autorzy DSpine mierzą weryfikację 16 tokenów ≈ 1,04× krok AR na H100, u nas na 3090 V(5)/V(1) = 1,59 ([[lekcja-akceptacja-h100-nie-przenosi-sie]]). Niskie V(n) → dłuższe drafty (n4+, DFlash2, DSpine b16).
4. **Fork + `kvq` + lean + lookup W16:** przenoszą się z RTX (kod CUDA ogólny), zysk na H100 brak pomiaru; lean daje głównie pamięć, tu mniej potrzebną.
5. **DFlash2 / DSpark / DSpine:** wyniki autorów DFlash są z H100 (Qwen3-4B, [[drafter-dflash]]); u nas DFlash2 +5,2% czat nad MTP na 3090.
6. **Kernele Hoppera (FA3, DeepGEMM, wgmma):** działają tylko tu, nie na RTX ([[sm-86-89-120]]); to dźwignia prefillu i wielu zapytań, przy batch 1 drugorzędna.
7. **`--ablate-lora` (K-207), DSpark ub/ctx fit:** przenoszą się bez zmian.

## Testy
- `qwen-opt/cloud/hostguard.sh` (po dopisaniu H100 do `karty.json`), `~/qwen-opt/cloud/nvq3/runk204.sh` (bramka CPU), `k204.py` (szukanie `-c`).
- `qwen-opt/nib/wall.py` (4 prompty × T=0 / 0,7), `spec_sweep.py` + `copy_prompts.json` (`mvs`), `qwen-opt/cloud/ink1/xbench.py`.
- `qwen-opt/long_ctx_bench.py`, igła `qwen-opt/cloud/needle.py` / `~/k134/k202srv.py` przy 95%.
- `md5cmp.py`, `qwen-opt/tools/kld_gate.py compare`, `qwen-opt/nib/refusal.py`.

## Kiedy topka jest gotowa
Pełny stos zmierzony na hoście po obu bramkach; pełny kontekst modelu z igłą 5/5 przy 95% + 700 tok.; md5 / `kld_gate` PASS; wall, szczyt VRAM, CPU i W zapisane; porównanie z 86,1 tok/s InferenceX na tej samej mierze; wiersz w [[TOPKI]].

## Pułapki
- Akceptacja i „τ wyższe o X%” z prac na H100 nie znaczą „t/s wyższe o X%” na innej karcie i odwrotnie.
- InferenceX mierzy losowe tokeny 1k/1k: nie to samo co nasz wall ([[raport-21f-inferencex]]).
- Na RTX: ładowanie z 0,6 GiB wolnego, a OOM na pierwszym długim prefillu; KV draftera q4 zużywa więcej VRAM; `p_min` ≥ 0,1 wyłącza DSpark; LoRA −17–33%. Na 80 GB rzadsze, ale fill i tak obowiązkowy.
- Colab i chmura: maszynę wyłączać po pracy; reaper potrafi zabić pracującą instancję po jednym „offline”.

## Rodzaje modeli
- **Dense 27B GDN (Qwen3.8):** większy kwant, potem V(n) i długość draftu.
- **MoE A2B/A3B:** batch 1 jest ograniczony narzutem kerneli, nie pasmem; najpierw fuzje i sampler, potem spekulacja.
- **Ternarny (Bonsai):** na 80 GB bez sensu jako topka, chyba że do porównań.
- **Inkling (pętlowe MoE):** ~7700 kerneli na token; zysk z pasma H100 zjada narzut uruchomień ([[inkling-2-mini]]); najpierw fuzje Unsloth / grafy, potem DSpark.

## Powiązane
- [[TOPKI]]
- [[lekcja-akceptacja-h100-nie-przenosi-sie]]
- [[raport-21f-inferencex]]
- [[nvidia-blackwell-sm100]]
- [[google-colab]]
