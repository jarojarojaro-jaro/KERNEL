---
typ: metoda
tags: [metody, pomiar, rx-7900-xtx, ab, kolejka]
aktualizacja: 2026-11-09
zrodlo: ~/qwen-opt/xtxbench/runs/1109-004040-t1-aa-validate/summary.txt, results.jsonl, xtxbench.log; ~/qwen-opt/xtxbench/README.md, xtxbench.py, selftest.py; ~/KERNEL/qwen-opt/xtxbench/; ~/KERNEL/qwen-opt/patches/xtxbench/0001-runtime-switch-hook-GGML_HIP_RUNTIME_SWITCH_FILE.patch
status: aktualne
---
# xtxbench: szybki A/B silnika produkcyjnego XTX (cel ~10 min na wariant zamiast 40–120)

**Harness A/B dla produkcji (`run-topka.sh uncensored`) mierzy decode z migawek kontekstu 1,7k/94k/199k (T=0, md5 tekstu) i prefill 4k/32k, z adaptacyjną regułą stopu. Walidacja na GPU 2026-11-09 (A/A na `~/llama-topka`): pomiar czasu działa — szum 0,02–0,15% decode, 0,03–0,33% prefill, decyzja NULL, 3,9 min na wariant (+17,5 min raz na silnik na migawki) zamiast ~38 min starą metodą; md5 po restore zależy od tego, czy to pierwsze żądanie na świeżym serwerze (wyciek stanu, fałszywy KILL w A/A) — poprawione: werdykt md5 tylko z pierwszego restore po starcie serwera.**

Dlaczego testy były długie (stan przed): każdy przebieg od nowa wczytywał 199k (~6–7 min × 4 ABBA), restart serwera na każde ramię (1,5–2 min), spec_sweep 6 × 3 seedy w każdym ramieniu przy szumie < 0,1%, a kompilacje lądowały w oknie GPU.

Projekt:
- **Migawki kontekstu:** `--slot-save-path`, prefill 1,7k/94k/199k raz na model+silnik+flagi (klucz: sha modelu, sha binarki, flagi), każde ramię `action=restore` i 256 tokenów decode. Równoważność restore vs świeży prefill (stan rekurencyjny GDN) trzeba udowodnić w pierwszym przebiegu GPU (`--prove`).
- **Bez restartu:** łatka `GGML_HIP_RUNTIME_SWITCH_FILE` (plik czytany przed przechwyceniem grafu) przełącza nazwane switche między zapytaniami; binarki i flagi wymagają restartu, więc ramiona są grupowane (P, N, ewentualnie P).
- **Poziomy:** `t0` kernel (`test-backend-ops` ± perf), `t1` jeden start na binarkę + migawki + prefill 4k/32k + md5 + spec_sweep 1 seed, `t2` pełna walidacja przed wdrożeniem (seedy 1,2,3, fill 255k, prefill 128k/255k).
- **Reguła stopu:** szum = |A − A′| / A raz na sesję; |Δ| ≥ max(5 × szum, 0,5%) ze stałym znakiem → decyzja od razu; |Δ| ≤ szum i brak zysku w t0 → KILL; inaczej dokładane B→A. Raport podaje liczbę przebiegów i minuty.
- **Twarde zasady:** tylko w kolejce GPU, eco 2200, nic nie kompiluje (binarka starsza od źródeł = odmowa), restore `run-topka.sh` z kontrolą health/n_ctx.

## Walidacja GPU (2026-11-09, `validate.jobs`, 22,4 min, run `1109-004040-t1-aa-validate`)

A = B = produkcja `~/llama-topka`, B na osobnym serwerze (restore między procesami), eco 2200, n_ctx 262 144.

| Pomiar | baseline (A) | teraz (B) | % | szum A/A |
|---|---|---|---|---|
| decode 1,7k | 129,23 t/s | 129,33 t/s | +0,08% | 0,03% |
| decode 94k | 104,75 t/s | 104,78 t/s | +0,03% | 0,02% |
| decode 199k | 93,33 t/s | 93,78 t/s | +0,48% | 0,15% |
| prefill 4k | 930,74 t/s | 929,25 t/s | −0,16% | 0,33% |
| prefill 32k | 865,61 t/s | 865,33 t/s | −0,03% | 0,03% |
| md5 prefill 4k / 32k | 99442e94 / 7e1321b3 | to samo | = | – |
| md5 greedy czat (świeży prefill) | d36768ee | d36768ee | = | – |

- **Czas:** wariant 3,9 min, sesja 1,0 min, raz na silnik 17,5 min (migawki 94k 140 s, 199k 384 s + dowód), stara metoda ~38,2 min. Werdykt timingowy NULL — poprawny dla A/A.
- **md5 decode z migawek — FAIL:** pierwszy restore na świeżym serwerze (B1, A2) daje md5 świeżego prefillu (3f26f79c / 90aca3e8 / 05fa2a47), kolejne restore na tym samym serwerze (A0, A0′, B2) inne (1,7k i 94k powtarzalnie 3dd78584 / fbe67aba, 199k za każdym razem inne); pojedyncze zimne żądanie (inny podział prefillu) daje jeszcze inne md5. Stan slotu/draftu MTP przecieka między żądaniami, więc A/A zwróciło fałszywy „KILL (md5 changed)”. Poprawka poniżej.
- Smoke runtime-switch pominięty (`~/wt/xtxbench/build-hip` nie zbudowany).

## Próg adopcji (decyzja użytkownika 2026-11-09)
Pojedyncza zmiana jest warta testu tylko przy oczekiwanym zysku **≥ 3–5% decode lub prefill albo ≥ 1 s na turę agenta**; ułamki procenta nie są celem. Test A/A (szum) to kalibracja harnessu, nie wynik optymalizacji.

## Poprawka (2026-11-09, tylko CPU)
- **Znalezisko:** drugi restore slotu na tym samym serwerze rozjeżdża się ze świeżym prefillem (wyciek stanu między żądaniami); prawdopodobnie kontekst draftu MTP / stan rekurencyjny nie jest w pełni resetowany przy restore (por. upstream #30574, port w topka-q63 0003). Może dotyczyć sesji agenta odtwarzających wpisy cache — pozycja otwarta w syntezie 68.
- **xtxbench:** md5 T=0 werdyktu tylko z pierwszej rundy po świeżym starcie serwera każdego ramienia (`md5_fresh`), porównywane też z dowodem „świeży prefill + decode”; późniejsze restore tylko dla t/s. `--var-switch` (jeden serwer): „md5: n/a (same-server)”, `md5_na` w result.json — potrzebne osobne ramię ze świeżym startem. Fake serwer selftestu modeluje wyciek; selftest CPU 7/7 OK. Ponowna interpretacja walidacji: B1 i A2 (pierwsze restore) = świeży prefill na 1,7k/94k/199k → dowód PASS.

## Stan / do wznowienia
- `mtpw.jobs` anulowany (oczekiwany KILL); kolejne joby t1 korzystają z poprawionej reguły md5.
- Smoke runtime-switch czeka na build `~/wt/xtxbench/build-hip`.

## Powiązane
- [[metody/_hub|metody]]
- [[pomiar-abba]]
- [[lekcja-cpuheavy-w-jobie-kolejki]]
- [[2026-11-08-kvq-once-profil]]
