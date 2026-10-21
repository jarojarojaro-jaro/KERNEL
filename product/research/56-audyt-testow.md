# 56. Audyt testów optymalizacji szybkości przed kolejką poranną (2026-10-21)

Zakres: pliki zadań MorningRun po `td.jobs` (s53m, lc-morning, g50c, g49c, smallops/morning, r7, i43-morning, g50b-morning) i wszystkie wołane skrypty. GPU nieużywane przez audyt. Kopie zmienionych plików: `*.bak` obok oryginału.

## Sprawdzone bez uwag

- Przełączniki istnieją w binarkach (`strings` libów) i w kodzie (`git grep getenv`), nazwy zgodne z jobs/raportami, domyślnie off:
  `LLAMA_DRAFT_SHORTLIST{,_FACTORS,_K}` (ca7d71228), `GGML_HIP_ATTN_PREP_MT`, `GGML_HIP_KVQ_FWHT_GATE` (a2800bf81), `GGML_HIP_MMVQ_Q6K_BIG_ROWS` (5bd79bc23, domyślnie 0), `GGML_HIP_MMVQ_Q4K_STREAM`, `GGML_HIP_MMVQ_IQ4XS_BIG_ROWS` (c6225c656), `GGML_HIP_MMVQ_Q5K_BIG_ROWS` (fd7dff630, int5, int6), `LLAMA_GDN_BANK` (int4–6), `LLAMA_SPEC_ROUTE` (int6).
- Worktree build-hip celowo: draft-shortlist, launch-cut, mmvqbig @ fd7dff630 (HEAD zgodny z raportami).
- `fix-runpath --check` = 0 i brak `/wt/` w ldd: mmvq-ring-int/inst, topka-int4/5/6, llama-topka.9056cea22.
- PM4: każde ramię e2e/md5 ustawia `PM4=1 WA=2 GUARD=1 HSA_USE_SVM=0` (p100_arm, p100_md5, int_md5, s53d, sr_gate, sr_arm, hg_arm), mikrobenche i test-backend-ops `PM4=0`, prof_block `PM4=0` inline.
- Kolejność ABBA A B B A (r7: palindrom A Q I B | B I Q A), te same seedy/porty/tryby w obrębie pliku; i43c (kumulatywne) — ten sam zestaw env produkcji z run-topka.sh, różnią się tylko mierzone pozycje.
- smallops/morning: same mikrobenche PM4=0, binarki obecne.

## Problemy i poprawki

| plik | problem | poprawka | status |
|---|---|---|---|
| `mmvq-q6k/inst`, `mmvqbig3/inst`, `mmvqbig/inst` | RUNPATH libów w `/wt/…/build-hip` (`fix-runpath --check` = 1, ldd ładował libki worktree). run-topka/run-llm dają `LD_LIBRARY_PATH=$ROCM_DIR/lib`, którego te instalacje nie mają → ramiona ABBA g50c/g49c jechałyby na bieżącym buildzie worktree (dla `mmvqbig/inst` = fd7dff630 zamiast 69f14108b) | `fix-runpath.py` na 3 instalacjach (10/8/8 wpisów), `--check` = 0, 0 ścieżek `/wt/` w ldd | naprawione |
| `draft-shortlist/s53d.sh` + `s53m.jobs` | `s53m-chk` kończył się zawsze `exit 0`, nic nie sprawdzał; ABBA bez bramki; plain md5 przy shortliście nie sprawdzany w tym pliku; stare wyniki `on-*` z wczoraj w `md5/` | s53d: czyści stare `on-*`, r1 robi plain+mtp; asercje plain `c4708318`, MTP `5f5b378f`, r1 == r2, GV0 == GV1 → `md5/GATE_PASS`; near-tie z `nt_gap.py` (JSON w logu); stop serwera 45 s. Ramiona wymagają `GATE_PASS` | naprawione |
| `xtxroadmap/prose_sum.py` + jobs s53m, lc-morning, g50c, g49c, g50b-morning | Etykiety `…-A1/B1/B2/A2`: `arm_of` zdejmuje tylko końcowe `a-d`, więc A1 i A2 były osobnymi ramionami (porównanie z bazą `A` puste, brak dryfu A1/A2). Sprawdzone na x48: „fewer than 2 instances of base arm A” | Etykiety → `Aa/Ba/Bb/Ab`. prose_sum dodatkowo drukuje dryf bazy (pierwsza → ostatnia instancja, ms/krok, INVALID > 1%) i host z `<label>.server.log` (INVALID > 7 ms) | naprawione |
| `xtxroadmap/p100_arm.sh` (prosethink, s53m) | etykieta `LABEL-think` → `arm_of` dawał ramiona `Aa-think`, mieszane z prozą pod tym samym prefiksem | etykieta `think-LABEL`; podsumowanie: prefiks `think-s53m-` | naprawione |
| `draft-shortlist/logs/prose.jsonl` | 4 częściowe wiersze `s53m-A1` z przerwanego biegu przed restartem | przeniesione do `prose.s53m-aborted.jsonl` (kopia `prose.jsonl.bak`) | naprawione |
| `mmvqbig3/g49c.jobs` | ABBA kumulatywne (A = `mmvqbig/inst` 69f14108b, B = `mmvqbig3/inst`), bramka md5 tylko dla B | bramka także dla A (`mmvq49a`), timeout 900 → 1800 s, ramiona wymagają obu PASS | naprawione |
| `mmvq-ring-int/r7.jobs` | bramka przez marker FAIL: md5 zabite timeoutem nie wykonuje `|| touch FAILr7` → ABBA bez bramki | markery `r7-{qwen,lfm}.PASS` (kasowane w r7-tbo), ramiona wymagają obu PASS i braku FAILr7 | naprawione |
| `queue/i43-morning.jobs` | to samo dla i43f/i43g (FAIL/FAILg); i43c (int6 vs 9056cea22) bez żadnej bramki md5 | markery `i43{f,g}-{qwen,lfm}.PASS` + `mkdir -p /tmp/integ`; i43c wymaga `/tmp/x44/GATE_PASS` z i43h-sr-gate (int6 off == c4708318/6f14e814) w tym samym pliku | naprawione |
| `hostgap/hg_arm.sh` (i43*-chat) | stop: SIGTERM bez czekania na bezczynność, po 20 s `kill -9` (także przy timeoucie w trakcie generacji) | wzorzec z raportu 55: bezczynne `/slots`, jeden SIGTERM, 45 s, SIGKILL na końcu | naprawione |
| `fusion/greedy.sh`, `xtxlab/sr_gate.sh` | SIGTERM → po 30 s SIGKILL (serwer bezczynny, ale okno krótsze niż 45 s z raportu 55) | 45 s | naprawione |
| `xtxlab/sr_arm.sh` (i43h) | etykiety `i43h-A1/B1/B2/A2` — ten sam problem z `arm_of`, jeśli podsumowanie idzie przez prose_sum | bez zmian: sr_arm nie pisze prose.jsonl, wyniki czyta się per etykieta (reason/spec_sweep/copy_bench) | uwaga |
| i43f-chat, i43g-chat, i43c-chat-* | pojedyncze ramiona (nie ABBA), hg_arm bez `YIELD_FAST/MIN_DISPATCH/LAZY_EXEC` (tak samo w obu chat-old/new) | bez zmian — informacyjne, nie decyzyjne | uwaga |

Stan /tmp po restarcie: każdy marker używany przez ramiona (`/tmp/p100-gate/*.PASS`, `/tmp/x44/GATE_PASS`, `/tmp/integ/*`, `draft-shortlist/md5/GATE_PASS`) jest tworzony przez joba-bramkę w tym samym pliku i kasowany na jego początku.

Ważność ABBA: host w logu każdego ramienia (`context lookup … host N ms`, p100_arm) i w prose_sum; dryf bazy w prose_sum. Timeouty: ramiona 420–900 s (prose+mvs seedy 1–2 / 1–3 / 1–4), bramki 900–1800 s.
