---
typ: narzedzie
tags: [narzedzia, pomiar, proces]
aktualizacja: 2026-11-25
zrodlo: ~/KERNEL/tools/perf/ (perf, perf-remote.sh, spill_audit.sh, ledger.py, profiles/bonsai25.env); [[metoda-nib-level-up]]
status: aktualne
---
# tools/perf: pętla optymalizacji jedną komendą (K-161)

**`tools/perf PROFIL WORKTREE BAZA` buduje silnik poza blokadą GPU, robi audyt spillów względem bazy, a w jednym jobie kolejki: test-backend-ops, md5 greedy, KLD 40×512, księgę µs/token z rocprof (delta do bazy) i ABBA czatu + kopii; na końcu jedno podsumowanie.**

- Wzór: Nib (spill audit, księga czasu, oracle w pętli), [[metoda-nib-level-up]].
- `spill_audit.sh BUILD [--out F] [--base F]`: każdy kernel gfx1100 z obiektów ggml-hip; błąd tylko przy nowym albo większym spillu/scratch względem bazy (fork już ma kernele ze spillami).
- `ledger.py STATS N [BASE_STATS N]`: µs/token, udział, wywołania/token, delta per kernel.
- Profile w `tools/perf/profiles/` (model, argumenty serwera i spekulacji, env produkcji, filtry test-backend-ops); pierwszy: `bonsai25.env`.
- Stan 2026-11-25: napisane i sprawdzone składniowo; pierwszy bieg na karcie czeka na włączenie jaroserverai (offline od 04:27). Maya (silnik ik2) potrzebuje osobnego profilu z `ik2_kernels_test` i rep2.

## sweep.sh: warianty w jednym serwerze (K-163, 2026-11-25)
- `sweep.sh PROFIL BUILD_BIN "NAZWA=WART,..." ...`: jeden llama-server z `GGML_HIP_RUNTIME_SWITCH_FILE`, dla każdego wariantu R par (baza, wariant) krótkiej próby (T=0 160 tok., T=0,7 200 tok.), wynik i sekundy na wariant.
- Pierwszy bieg (Bonsai 2.5, `~/wt/topka-rt` = topka-k157 + hak + przełączniki runtime, PM4, MTP n2, ctx 262k): serwer gotowy w 21 s, **14 s na wariant** (2 pary), 10 wariantów w ok. 2,5 min. Wcześniej ten sam pomiar kosztował 30–45 min na wariant.
- Ablacja przełączników (wyłączenie → zmiana T=0 / T=0,7): K157_GDN_AB_F −3,4% / −7,8%, MMVQ_PAIR −3,5% / −3,5%, BZ_FWHT_Q8 −3,6% / −3,0%, K157_NORM_FWHT −2,6% / −1,8%, K155_MMVF_SPLIT −2,1% / −1,4%, BZ_NORM_FWHT −1,3% / −1,2%; K157_FWHT_DPP, K157_GDN_TAIL, K157_MMVF_THIN, BZ16 w szumie (±1%) dla krótkiego czatu. Szum próby: baza T=0,7 116–121 t/s między parami (±2%), więc krótka próba tylko jako sito, zwycięzcy idą do pełnego A/B.

## Liczniki rocprofv3 na gfx1100 zwracają 0 (K-160, 2026-11-25)
- `rocprofv3 --pmc FETCH_SIZE`, `GL2C_EA_RDREQ_{32,64,96,128}B_sum` i `GL2C_HIT_sum/MISS_sum` (ROCm core-10.0, HSA 1.21, gfx1100) zbierają się bez błędu, ale każdy kernel ma wartość 0; `TCC_*` w ogóle nie istnieją na tej karcie (nazwy L2 to `GL2C_*`). Pasma z liczników nie zmierzymy; zostaje model bajtów (rozmiar wag / czas kernela) i mikrobench pełnego kroku. Skrypt: `qwen-opt/bonsai25/k160-dram.sh`.

## Powiązane
- [[metoda-nib-level-up]]
- [[kol]]
- [[playbook-optymalizacji]]
