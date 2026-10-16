# 11. Pilot MTP-PL: douczanie głowicy MTP Qwen3.8-27B na naszym Q4 (RunPod A40, 2026-10-16)

## TL;DR

- **Wynik negatywny.** Douczona głowica MTP (`blk.64.*`) nie daje istotnego zysku tok/krok. Jest w granicach ±2% od głowicy fabrycznej: PL-proza +2,3% przy n=4 (pojedyncza próbka), reszta klas 0 do −3%. Offline na held-out: 0,0% (all), +0,5% PL.
- **Bramka offline przeszła, ale zapas jest u wyroczni, nie u głowicy.** Na PL-prozie fabryczna głowica ma 3,01 tok/krok przy n=4, a wyrocznia greedy 3,81 (+27%). Trzy przebiegi treningowe przy 0,5–1,7 M tokenów nie zbliżyły głowicy do wyroczni: najlepszy dał +0,2% offline. Głowica Qwena jest już w swoim optimum dla tej skali danych i tego celu.
- **Pień nietknięty.** Greedy md5 bez spekulacji jest identyczne dla oryginału i nowego pliku. Bajty poza tensorami `blk.64.*` zweryfikowano porównaniem bajt po bajcie: 0 różnic.
- **Koszt własny: $2,14** (pod A40 secure $0,59/h + dysk 150 GB, 3,50 h). Pod **usunięty** (`podTerminate`, potwierdzone w API: poda nie ma na liście konta). Saldo konta po pilocie $5,83; w tym czasie działał też pod użytkownika `phoneuse-stage1`, którego nie dotykałem.
- **Rekomendacja:** nie skalować do 10 M tokenów w tej formie. Test na 7900 XTX (komendy w §7) jest tylko potwierdzeniem, nie warunkiem decyzji.

## 1. Co zrobiono

Pipeline zbudowano i przetestowano najpierw lokalnie na CPU: Qwen3.5-0.8B z natywnym MTP oraz 27B Q4 na CPU (parytet). Dopiero potem uruchomiono poda.

| Krok | Narzędzie | Gdzie |
|---|---|---|
| Ekstraktor: h_nextn celu (fp16), top-20 logitów teachera + logsumexp, greedy łańcuchy draftu MTP ścieżką produkcyjną (`llama_set_mtp_draft_chain`, słownik 64k, IQ4_XS) | `tools/mtp-extract` (nowe narzędzie, osobna binarka) | gałąź `mtp-train` (worktree `~/wt/mtptrain`, commit 532fd1057 na `cuda-v070`) |
| Lustro PyTorch grafu `graph_mtp`, rekurencja K=5 z wiernym układem KV łańcucha (prefiks z par teacher-forced + własne K/V kroków 2..k) | `mtp/model.py` | `~/qwen-opt/mtp-train/` |
| Metryka offline: S_k = P(pierwsze k draftów przyjęte) przy T=1, tok/krok = 1 + Σ S_k, wyrocznia = argmax celu w słowniku 64k | `mtp/metrics.py`, `eval_offline.py` | jw. |
| Trening FastMTP: K=5, β=0,65, strata 0,9·TV + 0,1·CE na top-20 samplera produkcyjnego (top-k 20, top-p 0,95, min-p 0,05, T=1), zamrożone embeddingi i głowica draftu (IQ4_XS jak w produkcji) | `train.py` | jw. |
| Zapis: kwantyzacja do typów z pliku przez `ggml_quantize_chunk` (ctypes), nadpisanie bajtów w kopii, weryfikacja bajt po bajcie; łatka z samą głowicą; sidecar MTP-only | `writeback.py` | jw. |
| RunPod: klient GraphQL, lokalny watchdog (deadline 9 h, limit własnego kosztu $5,90, podłoga salda $1,50), samozniszczenie na podzie po 9 h 10 min | `cloud/rp.py`, `cloud/watchdog.sh`, `cloud/pod/selfdestruct.sh` | `~/qwen-opt/mtp-train/cloud/` |

**Typ przechowywania głowicy (zweryfikowane w GGUF):**
- `attn_q`, `attn_output`, `ffn_{gate,up,down}`, `nextn.eh_proj`: **Q6_K**;
- `attn_k`, `attn_v`: **Q8_0**;
- normy: F32;
- razem 351 008 768 B.

Fork **nie** trzyma IQ4_XS w pliku. `--spec-mtp-type iq4_xs` i `--spec-draft-head-type iq4_xs` rekwantyzują tensory przy ładowaniu (`llama_model_requant_mtp`, Q6_K → f32 → IQ4_XS, bez imatrix). Zapis zachowuje Q6_K/Q8_0/F32, a ewaluację prowadzono z emulacją tej rekwantyzacji.

**Bramka parytetu** (lustro PyTorch vs llama.cpp, te same h celu, KV f32):

| Model | Względny błąd logitów kroku 1 (mediana / max) | Zgodność argmax kroku 1 | Zgodność tokenów łańcucha K=4 |
|---|---|---|---|
| Qwen3.5-0.8B bf16 (CPU) | 0,34% / 0,56% | 98,4% | 91,7% (różnice tylko przy remisach logitów, margines 0,002–0,016) |
| Qwen3.8-27B Q4_K_XL (CPU) | 2,0% / 5,5% (szum aktywacji q8_K w matmulach CPU) | 98,4% | 98,3% |
| 27B, A40, cały held-out | — | — | tok/krok z łańcuchów llama.cpp 3,268 vs lustro 3,266 (all, n=4) |

## 2. Dane (manifest i licencje)

Pliki: `~/qwen-opt/mtp-train/data/prompts/MANIFEST.json`, `ds_train.jsonl.stats.json`. Prompty i odpowiedzi: `pod-results/data/gen_*.jsonl`.

| Zbiór | Źródło (rewizja) | Licencja | Użycie |
|---|---|---|---|
| WildChat-1M PL/EN | allenai/WildChat-1M @7d6490e4 | ODC-BY-1.0 | pierwsza tura użytkownika (toxic=False, redacted=False); do suplementu także pierwsza odpowiedź |
| oasst2 pl | OpenAssistant/oasst2 @179dd21f | Apache-2.0 | prompty startowe; do suplementu najwyżej oceniona odpowiedź |
| aya PL | CohereLabs/aya_dataset @f9ea0458 | Apache-2.0 | `inputs` (+ `targets` w suplemencie) |
| kod | bigcode/self-oss-instruct-sc2-exec-filter-50k @356bb069 | ODC-BY-1.0 | `instruction` (+ `response` w suplemencie) |
| PLLuMIC | pelcra/PLLuMIC | CC-BY-SA-4.0 | **nieużyty**: repo gated, brak tokena HF na maszynie |

Wolumen danych:

| Zestaw | Sekwencje | Tokeny (w tym odpowiedzi) | Skład |
|---|---|---|---|
| held-out val (on-policy) | 159 | 148 450 (120 902) | pl 66, en 42, kod 33 oraz 6 promptów `spec_sweep` × 3 seedy |
| train on-policy | 481 | 389 787 (334 634) | odpowiedzi naszego Q4: A40, reasoning low, sampler GGUF, T=1, ≤1024 tok |
| suplement off-policy | 2 997 | 1 317 337 (849 111) | odpowiedzi z datasetów, teacher top-20 z naszego Q4; szablon bez myślenia |

Generacja na A40 była wolna: `llama-server -np 32` dawał ~100–140 tok/s odpowiedzi. Dlatego on-policy jest tylko 0,39 M tokenów, a suplement off-policy dobija do 1,7 M.

## 3. Bramka offline (głowica fabryczna, held-out on-policy, IQ4_XS emulowane)

`S_k` = P(pierwsze k draftów przyjęte), `cond` = warunkowa akceptacja na głębokości k, wyrocznia = greedy argmax celu (sufit dla draftera greedy).

| Klasa | Pozycje | cond d1..d5 | tok/krok n=4 | tok/krok n=5 | wyrocznia n=4 | zapas wyroczni |
|---|---|---|---|---|---|---|
| all | 120 107 | 0,808 / 0,769 / 0,762 / 0,769 / 0,783 | 3,266 | 3,551 | 3,960 | +21% |
| pl | 52 506 | 0,789 / 0,735 / 0,723 / 0,728 / 0,745 | 3,092 | 3,320 | 3,870 | +25% |
| pl-proza (heurystyka) | 9 956 | 0,773 / 0,719 / 0,711 / 0,721 / 0,740 | 3,009 | 3,220 | 3,812 | +27% |
| en | 34 828 | 0,755 / 0,715 / 0,710 / 0,719 / 0,740 | 2,954 | 3,157 | 3,690 | +25% |
| code | 32 773 | 0,895 / 0,865 / 0,849 / 0,841 / 0,839 | 3,877 | 4,340 | 4,392 | +13% |
| sweep pl-proza | 3 057 | 0,700 / 0,646 / 0,622 / 0,601 / 0,594 | 2,601 | 2,702 | 3,455 | +33% |
| sweep en-chat | 1 027 | 0,692 / 0,620 / 0,635 / 0,620 / 0,661 | 2,560 | 2,672 | 3,363 | +31% |

**Decyzja bramki:** zapas na PL-prozie +27–33% (≥ +5%), więc pilot kontynuowano.

Zgodność z produkcją: offline sweep pl-proza 2,60 vs online na A40 2,65; en-chat 2,56 vs 2,43. Na XTX użytkownik mierzył 2,76 / 2,43.

Efekt uboczny: emulowana rekwantyzacja bloku MTP do IQ4_XS kosztuje ok. −0,45% tok/krok offline. Głowica fabryczna w precyzji przechowywania daje 3,281 (bf16 w treningu), a z IQ4_XS 3,266.

## 4. Trening

| Przebieg | Dane | lr / epoki / kroki | Strata | val tok/krok n=4 (bf16, start 3,2810) |
|---|---|---|---|---|
| train1 (zapisany, benchmark) | on-policy + off-policy, 1,71 M tok | 5e-5 cosine, 2 ep., 220 kroków × 16k tok, 2 980 tok/s | 0,9 TV + 0,1 CE | spadek do 3,235 po 25 krokach, potem 3,274 na końcu (**−0,2%**); najlepszy = start |
| train2 | tylko on-policy 0,39 M | 1e-5, 3 ep., 77 kroków | 0,9 TV + 0,1 CE | **3,2880 (+0,21%)** |
| train3 | tylko on-policy 0,39 M | 1e-5, 3 ep., 77 kroków | CE | 3,2816 (+0,02%) |

Wnioski:
- Strata TV/CE spada (0,317 → 0,307), ale akceptacja greedy prawie się nie rusza. Głowica Qwena była trenowana wielokrokowo na dużo większym korpusie, a 0,4–1,7 M tokenów jej nie przesuwa.
- Dane off-policy (odpowiedzi z datasetów bez bloku myślenia) wyraźnie szkodzą na starcie (3,281 → 3,235).
- Do zapisu i benchmarku użyto **ostatniego** checkpointu train1, bo najlepszy według val był identyczny z fabrycznym. Benchmark sprawdza więc, czy predykcja offline pokrywa się z pomiarem online.

## 5. Zapis do GGUF

- `writeback.py build`: kopia pliku, 15 tensorów `blk.64.*` skwantowanych do Q6_K/Q8_0/F32 przez `ggml_quantize_chunk`. Bajty poza zakresami tych tensorów: **0 zmienionych**.
- Bazowy sha256 `3f227079…b8c01e`, zgodny z HF unsloth @4ca72078 i lokalnym plikiem. Nowy sha256 `bb8a501b36475dcfc93a9023003e4dc677d722fd039a09625fcf602a7ea8fbf5`, identyczny po odtworzeniu lokalnym.
- Artefakty:
  - `~/models/draft-exp/Qwen3.8-27B-UD-Q4_K_XL-mtpPL.gguf`: pełny plik, zbudowany lokalnie z łatki (`writeback.py apply` sprawdza sha bazy);
  - `~/qwen-opt/mtp-train/out/Qwen3.8-27B-UD-Q4_K_XL-mtpPL.mtp-head.gguf`: 362 MB, sama głowica i metadane;
  - sidecar MTP-only (token_embd + output_norm + output + `blk.64.*`, 2,12 GB): fork ładuje go przez `-m oryginał -md sidecar --spec-type draft-mtp`. Sprawdzone na 0,8B: takie same statystyki draftu jak plik łatany. Kosztuje jednak +1,76 GB VRAM na zduplikowane embd/output. Można go odtworzyć lokalnie: `writeback.py apply ... --sidecar PLIK`.

## 6. Pomiar na podzie (A40, `cuda-v070`+narzędzie, CUDA 12.8, KV q4_0, 64k vocab, IQ4_XS, reasoning low)

`spec_sweep`: 6 promptów × 3 seedy, T=1, 400 tokenów, świeży serwer na przebieg, kolejność ABBA. A = oryginał, B = nowa głowica. Powtórzenia A/A i B/B dały identyczne tok/krok, więc przebiegi są deterministyczne przy stałym seedzie.

| n | Głowica | median t/s | ms/krok | pl-proza | pl-tech | pl-kod | en-chat | en-tech | en-code |
|---|---|---|---|---|---|---|---|---|---|
| 4 | A | 78,9 / 78,7 | 38,75 / 38,82 | 2,65 | 3,28 | 3,50 | 2,43 | 3,02 | 3,10 |
| 4 | B | 78,3 / 78,5 | 38,87 / 38,83 | **2,71** (+2,3%) | 3,25 (−0,9%) | 3,47 (−0,9%) | 2,41 (−0,8%) | 2,97 (−1,7%) | 3,13 (+1,0%) |
| 5 | A | 76,9 / 76,8 | 42,53 / 42,43 | 2,77 | 3,49 | 3,77 | 2,52 | 3,21 | 3,33 |
| 5 | B | 75,9 / 75,6 | 42,39 / 42,52 | 2,77 (0%) | 3,44 (−1,4%) | 3,70 (−1,9%) | 2,48 (−1,6%) | 3,12 (−2,8%) | 3,32 (−0,3%) |

Tok/krok per prompt (pl-proza, t/s): A n=4 68,5 / 68,2, B n=4 69,7 / 69,7. ms/krok bez zmian, bo typy kwantów są te same.

**Offline, ścieżka produkcyjna** (łańcuchy llama.cpp na held-out, co 3. pozycja, 40 088 startów):

| Klasa | A n=4 | B n=4 | A n=5 | B n=5 |
|---|---|---|---|---|
| all | 3,268 | 3,265 | 3,553 | 3,549 |
| pl | 3,095 | 3,111 | 3,323 | 3,344 |
| en | 2,962 | 2,945 | 3,167 | 3,146 |
| code | 3,871 | 3,855 | 4,331 | 4,307 |

Ten sam wzorzec co online: PL +0,5%, EN −0,6%, kod −0,4%.

**Greedy md5** (T=0, 2 prompty × 400 tok, bez myślenia):
- plain A = plain B = `7f63dec872e319cb24d57f7ea46d773b`. Pień nietknięty.
- MTP A = MTP B = `80259112e1944dc177becfa1bfcd309a`.

Przy greedy weryfikacji wyjście nie zależy od draftów co do treści. Może się jednak legalnie różnić, bo inne drafty zmieniają szerokość batcha weryfikacji, a więc kolejność redukcji i numerykę kerneli. W tym teście różnica nie wystąpiła. Plain ≠ MTP, co jest znane w tym forku z tego samego powodu.

## 7. Test końcowy na 7900 XTX (do uruchomienia przez rodzica, gdy GPU będzie wolne)

Plik jest już gotowy w `~/models/draft-exp/`. `run-llm.sh` ma model na sztywno, więc serwer B trzeba uruchomić ręcznie z identycznymi flagami:

```bash
cd ~/qwen-opt
# A = oryginał (run-llm.sh), B = nowa głowica; ABBA, n=4 (produkcja ROCm) i n=5
srvB() { LD_LIBRARY_PATH=$HOME/llama-opt/lib:/opt/rocm/core-10.0/lib $HOME/llama-opt/bin/llama-server \
  -m $HOME/models/draft-exp/Qwen3.8-27B-UD-Q4_K_XL-mtpPL.gguf -ngl 999 -fa on -ctk q4_0 -ctv q4_0 -c 204800 -np 1 \
  --jinja --cache-ram 16384 --reasoning-effort low --host 127.0.0.1 --port 8080 --log-file logs/mtpPL.log \
  --spec-type draft-mtp --spec-draft-n-max ${1:-4} --spec-draft-vocab $HOME/models/draft/draft_vocab_qwen38.txt \
  --spec-draft-vocab-n 65536 --spec-draft-head-type iq4_xs --spec-mtp-type iq4_xs -ctkd q4_0 -ctvd q4_0 & }
wait_up() { until curl -sf localhost:8080/health >/dev/null; do sleep 1; done; }
for n in 4 5; do
  DRAFT_N=$n ./run-llm.sh qwen mtp rocm & wait_up; .venv/bin/python spec_sweep.py --label "A n=$n" --seeds 1,2,3; pkill -f 'llama-server.*--port 8080'; sleep 5
  srvB $n; wait_up; .venv/bin/python spec_sweep.py --label "B n=$n" --seeds 1,2,3; pkill -f 'llama-server.*--port 8080'; sleep 5
  srvB $n; wait_up; .venv/bin/python spec_sweep.py --label "B n=$n" --seeds 1,2,3; pkill -f 'llama-server.*--port 8080'; sleep 5
  DRAFT_N=$n ./run-llm.sh qwen mtp rocm & wait_up; .venv/bin/python spec_sweep.py --label "A n=$n" --seeds 1,2,3; pkill -f 'llama-server.*--port 8080'; sleep 5
done
# greedy md5: plain musi być identyczne (pień nietknięty)
for M in Qwen3.8-27B-UD-Q4_K_XL.gguf draft-exp/Qwen3.8-27B-UD-Q4_K_XL-mtpPL.gguf; do
  LD_LIBRARY_PATH=$HOME/llama-opt/lib:/opt/rocm/core-10.0/lib $HOME/llama-opt/bin/llama-server -m $HOME/models/$M -ngl 999 -fa on \
    -ctk q4_0 -ctv q4_0 -c 8192 -np 1 --port 18433 --no-webui > /dev/null 2>&1 & until curl -sf localhost:18433/health >/dev/null; do sleep 1; done
  curl -s localhost:18433/v1/chat/completions -H 'Content-Type: application/json' -d '{"messages":[{"role":"user","content":"Napisz krótkie opowiadanie o latarniku i sztormie."}],"max_tokens":400,"temperature":0,"chat_template_kwargs":{"enable_thinking":false}}' | jq -r .choices[0].message.content | md5sum
  pkill -f 'llama-server.*18433'; sleep 5
done
```

Oczekiwanie (z A40 i offline): PL-proza 0 do +2%, pozostałe klasy 0 do −3%. Kryterium akceptacji z §1.3 dokumentu 10 (pl-proza ≥ +10%) **nie zostanie spełnione**.

## 8. Koszt i infrastruktura

| Pozycja | Wartość |
|---|---|
| Pod | A40 48 GB secure (SE), $0,59/h + dysk 150 GB (~$0,02/h) |
| Czas | 02:18–05:48, 3,50 h → **$2,14** |
| Usunięcie | `podTerminate` i potwierdzenie przez listę podów; lokalny watchdog odnotował „pod is gone” o 05:48:29 |
| Rozkład czasu | build CUDA 30 min (cgroup 7,65 CPU); generacja 1 h 30 min; ekstrakcja 40 min; trening 21 min + 2 × 10 min; ewaluacja, zapis i łańcuchy 20 min; bench 35 min |

Lekcje praktyczne:
- `llama-server` w kontenerze RunPod domyślnie bierze `nproc` = 96 wątków przy limicie 7,65 CPU. Trzeba ustawić `-t 6 -tb 6`.
- `-np 32` na A40 daje tylko ~100–140 tok/s odpowiedzi; generacja on-policy to wąskie gardło.
- Łańcuchy MTP obok serwera generacji kosztują ~11 ms/łańcuch i spowalniają generację 6×.
- Bug forka (tylko CPU): `--spec-mtp-type` z buforami CPU_REPACK kończy się segfaultem. Obejście: `--no-repack`. Na GPU nie występuje.

## 9. Co dalej (jeśli w ogóle)

- **Nie** skalować tego treningu do 10 M tokenów. Brak sygnału przy 0,4 M on-policy (+0,2%) i szkodliwość off-policy nie wróżą dużego zysku. Zapas wyroczni (+21–33%) jest realny, ale ta pojedyncza głowica jednowarstwowa go nie wybiera.
- Realny, tani mikro-zysk: blok MTP w Q6_K zamiast IQ4_XS daje +0,45% tok/krok offline. Trzeba go zważyć z ms/krok draftu na XTX.
- Większy zapas leży raczej w probabilistycznym drafcie przy T=1 (sufit 1,0 na głębokość). To wymaga głowicy kalibrowanej TV na dużo większych danych on-policy, a generacja jest tu wąskim gardłem (§8).

## Pliki

- Kod: `~/qwen-opt/mtp-train/{mtp/,train.py,eval_offline.py,parity.py,writeback.py,gen_data.py,tok_ds.py,make_shard.py,prep_prompts.py,prep_ds.py}`, `cloud/` (RunPod) i `cloud/pod/` (skrypty poda).
- Narzędzie C++: gałąź `mtp-train` (`tools/mtp-extract`).
- Wyniki: `~/qwen-opt/mtp-train/pod-results/` (eval/*.json, bench/sweep.txt i spec_sweep.jsonl, greedy-md5.txt, logi, train_log.jsonl, config.json, dane gen_*.jsonl).
