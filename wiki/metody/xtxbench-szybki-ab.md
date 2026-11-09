---
typ: metoda
tags: [metody, pomiar, rx-7900-xtx, ab, kolejka]
aktualizacja: 2026-11-09
zrodlo: ~/qwen-opt/xtxbench/README.md, xtxbench.py, selftest.py; ~/KERNEL/qwen-opt/xtxbench/; ~/KERNEL/qwen-opt/patches/xtxbench/0001-runtime-switch-hook-GGML_HIP_RUNTIME_SWITCH_FILE.patch
status: do-sprawdzenia
---
# xtxbench: szybki A/B silnika produkcyjnego XTX (cel ~10 min na wariant zamiast 40–120)

**Harness A/B dla produkcji (`run-topka.sh uncensored`) mierzy decode z migawek kontekstu 1,7k/94k/199k (T=0, md5 tekstu) i prefill 4k/32k, z adaptacyjną regułą stopu: szum raz na sesję, jedna para A→B, ABBA tylko przy wyniku niejednoznacznym; CPU self-test 7/7 OK, walidacja na GPU nie odbyła się (koniec testów 2026-11-08), więc oszczędność czasu jest na razie szacunkiem.**

Dlaczego testy były długie (stan przed): każdy przebieg od nowa wczytywał 199k (~6–7 min × 4 ABBA), restart serwera na każde ramię (1,5–2 min), spec_sweep 6 × 3 seedy w każdym ramieniu przy szumie < 0,1%, a kompilacje lądowały w oknie GPU.

Projekt:
- **Migawki kontekstu:** `--slot-save-path`, prefill 1,7k/94k/199k raz na model+silnik+flagi (klucz: sha modelu, sha binarki, flagi), każde ramię `action=restore` i 256 tokenów decode. Równoważność restore vs świeży prefill (stan rekurencyjny GDN) trzeba udowodnić w pierwszym przebiegu GPU (`--prove`).
- **Bez restartu:** łatka `GGML_HIP_RUNTIME_SWITCH_FILE` (plik czytany przed przechwyceniem grafu) przełącza nazwane switche między zapytaniami; binarki i flagi wymagają restartu, więc ramiona są grupowane (P, N, ewentualnie P).
- **Poziomy:** `t0` kernel (`test-backend-ops` ± perf), `t1` jeden start na binarkę + migawki + prefill 4k/32k + md5 + spec_sweep 1 seed, `t2` pełna walidacja przed wdrożeniem (seedy 1,2,3, fill 255k, prefill 128k/255k).
- **Reguła stopu:** szum = |A − A′| / A raz na sesję; |Δ| ≥ max(5 × szum, 0,5%) ze stałym znakiem → decyzja od razu; |Δ| ≤ szum i brak zysku w t0 → KILL; inaczej dokładane B→A. Raport podaje liczbę przebiegów i minuty.
- **Twarde zasady:** tylko w kolejce GPU, eco 2200, nic nie kompiluje (binarka starsza od źródeł = odmowa), restore `run-topka.sh` z kontrolą health/n_ctx.

## Stan / do wznowienia
`run-jobs.sh ~/qwen-opt/xtxbench/validate.jobs` (t1 baseline vs baseline + dowód restore); potem przepiąć na xtxbench joby fa-d256, kvq-once2b, mtpw, cachesave, l1tok (A2+C).

## Powiązane
- [[metody/_hub|metody]]
- [[pomiar-abba]]
- [[lekcja-cpuheavy-w-jobie-kolejki]]
- [[2026-11-08-kvq-once-profil]]
