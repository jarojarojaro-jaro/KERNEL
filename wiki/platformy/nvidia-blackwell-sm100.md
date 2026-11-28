---
typ: platforma
tags: [platformy, nvidia, blackwell, sm100, playbook, serwer]
aktualizacja: 2026-11-28
zrodlo: qwen-opt/skill-io/karty.json:194-203; wiki/modele/inkling-2-mini.md:65,79,95-101; wiki/ekosystem/megakernel-zoo.md:13-31; wiki/stos/sm-86-89-120.md; wiki/testy/2026-11-19-k118-nvidia-pelna-moc.md; wiki/testy/2026-11-28-k207-ablacja-zamiast-lora.md; wiki/optymalizacje/jak-przyspieszylismy-nvidia.md
status: aktualne
---
# NVIDIA Blackwell sm_100 (B200, GB200): playbook topki

**Na B200 i GB200 nie mamy własnego pomiaru (brak pomiaru, 2026-11-28); cudze liczby pokazują, że przy batch 1 te karty są daleko od sufitu pasma (Inkling 2 Mini na GB200 3,85 ms/krok przy sufecie ~0,4 ms), więc kolejność to: narzut kerneli i fuzje, potem spekulacja, a pasmo na końcu.**

sm_100 to inna architektura niż RTX 50 (sm_120): ma tcgen05/TMEM, wgmma, 2-CTA i TMA multicast, których sm_120 nie ma ([[sm-86-89-120]]), więc kernele B200 nie przenoszą się na RTX i odwrotnie tylko część.

## Dzień pierwszy
- **Dostęp:** brak w Colab (T4, L4, G4, A100, H100); wynajem tylko za zgodą JARO.
- **Sterownik i CUDA:** CUDA ≥ 12.8 jak na RTX; wersję sterownika i CUDA zapisać przy wyniku.
- **Bramka pełnej mocy:** moc ≥ 85% domyślnej, temperatura < 80 °C; B200 nie ma progu w `karty.json → mem_clock_mhz`, trzeba go dopisać przed `hostguard.sh`.
- **Bramka CPU:** llama-bench tg256 z użyciem GPU ≥ 85% (`runk204.sh`) i odrzucanie EPYC Zen2 (na 5060 Ti: 99% w llama-bench, serwer 2,1–2,6× wolniejszy, [[2026-11-28-k207-ablacja-zamiast-lora]]). GB200 ma CPU Grace (ARM): build bez flag x86 i `GGML_NATIVE=OFF`.
- **Build:** tylko `-DCMAKE_CUDA_ARCHITECTURES=100a`; bez 120 (inne SASS).
- **Sufit pasma:** t/s ≤ pasmo ÷ bajty na token, ze spekulacją × tok./krok. B200 8000 GB/s, 180 GB (`karty.json:194-203`) ÷ 10,34 GB ≈ 774 t/s dla GSQ IQ3_XXS; GB200 ~8 TB/s ([[inkling-2-mini]]).
- **Sanity (cudze):** Inkling 2 Mini bez spekulacji na B200 68 → 111 t/s z fuzjami Unsloth (b12649-mix); Qwen3.8-27B na B200 SGLang 9,52 ms/token, megakernel 8,44 → 7,17 ms ([[megakernel-zoo]]). Nasz pierwszy przebieg powinien się w tym zmieścić.

## Kolejność optymalizacji
1. **Upstream z fuzjami + grafy CUDA:** przy batch 1 krok zjada narzut uruchomień (Inkling ~7700 kerneli na token); fuzje Unsloth dały 1,63× na B200.
2. **Przepis RTX:** pin, MTP n3, KV q4_0, `--spec-draft-n-ubatch 64`; na RTX MTP +50–63% ([[jak-przyspieszylismy-nvidia]]), na B200 brak pomiaru.
3. **V(n) (`llama-bench -p 1,2,3,5 -ub 5 -n 0 -r 5`):** decyduje o długości draftu; na Ampere 1,59, na Adzie 1,26 ([[2026-11-19-k118-nvidia-pelna-moc]]).
4. **Spekulacja szeroka (DFlash2, DSpark, DSpine b16):** przy niskim V(n) długie drafty się opłacają; na RTX DFlash2 +5,2% czat nad MTP.
5. **Fork + `kvq` + lean + lookup W16:** kod CUDA ogólny, przenosi się; zysk brak pomiaru. Kontekst przy 180 GB nie ogranicza, lean ma tu małe znaczenie.
6. **`--ablate-lora` (K-207)** i fit ub/ctx DSpark przenoszą się bez zmian.
7. **Megakernel / trwały kernel:** jedyna droga blisko sufitu; prior art tylko H100/B200 ([[megakernel-zoo]]), koszt agenta ~63 h.

## Testy
- `qwen-opt/cloud/hostguard.sh` (po dopisaniu B200), `~/qwen-opt/cloud/nvq3/runk204.sh`, `k204.py` (szukanie `-c`).
- `qwen-opt/nib/wall.py` (4 prompty × T=0 / 0,7), `spec_sweep.py` + `copy_prompts.json` (`mvs`), `qwen-opt/cloud/ink1/xbench.py`.
- `qwen-opt/long_ctx_bench.py`, igła `qwen-opt/cloud/needle.py` / `~/k134/k202srv.py` przy 95%.
- `md5cmp.py`, `qwen-opt/tools/kld_gate.py compare`, `qwen-opt/nib/refusal.py`.

## Kiedy topka jest gotowa
Pełny stos zmierzony na hoście po obu bramkach; pełny natywny kontekst modelu z igłą 5/5 przy 95% + 700 tok.; md5 / `kld_gate` PASS; wall, szczyt pamięci, CPU i W zapisane; wynik porównany z cudzymi liczbami tej samej miary; wiersz w [[TOPKI]].

## Pułapki
- Cudze liczby z B200/GB200 to często TP, batch > 1 albo sam forward przy 4K: przeliczać na batch 1 i nasz wall.
- Akceptacja z prac na H100/B200 nie przenosi się na inne karty ([[lekcja-akceptacja-h100-nie-przenosi-sie]]).
- Znane z RTX: ładowanie z 0,6 GiB wolnego i OOM przy pierwszym długim prefillu, KV draftera q4 zużywa więcej VRAM, `p_min` ≥ 0,1 wyłącza DSpark, LoRA −17–33%, reaper zabija pracującą instancję po jednym „offline”.

## Rodzaje modeli
- **Dense 27B GDN (Qwen3.8):** kwant wyższy (Q6_K/Q8), potem V(n), drafty, megakernel.
- **MoE A2B/A3B (LFM, Qwen3.6-35B):** batch 1 to narzut kerneli; fuzje i sampler przed spekulacją.
- **Ternarny (Bonsai):** bez sensu jako topka na 180 GB.
- **Inkling (pętlowe MoE):** fuzje (Unsloth 68 → 111 t/s), potem DSpark; GB200 3,85 ms/krok to granica vLLM ze wszystkimi fuzjami.

## Powiązane
- [[TOPKI]]
- [[inkling-2-mini]]
- [[megakernel-zoo]]
- [[nvidia-hopper-sm90]]
- [[sm-86-89-120]]
