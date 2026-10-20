# Wyniki RX 7900 XTX: upstream llama.cpp → topka (pomiar 2026-10-19)

Każdą liczbę zmierzono 2026-10-19 w jednej kolejce GPU (`~/qwen-opt/queue/run-jobs.sh`): te same skrypty, prompty i karta. Nie ma tu starych liczb, z wyjątkiem tabeli rekordu long_ctx, gdzie stary wiersz podano tylko dla porównania.

## Co porównujemy
| ramię | build | uruchomienie |
|---|---|---|
| **U0: upstream domyślny** | upstream master `4c3c5810f` (2026-10-19), ROCm gfx1100, zbudowany przez `rbuild` → `~/llama-upstream` | `llama-server -m MODEL` i nic więcej: `-fit` dobiera ctx, KV f16, bez spekulacji, myślenie domyślne |
| U1: upstream + flagi produkcji | to samo | flagi `run-llm.sh`: ctx 204800, KV q4_0, `-fa on`, `-np 1`, `--reasoning-effort low`, plus **własne MTP upstreamu** `--spec-type draft-mtp --spec-draft-n-max 4 -ctkd/-ctvd q4_0` |
| **T: topka** | `~/llama-topka` = gałąź topka `f2217bac7` | `~/qwen-opt/run-topka.sh MODEL` dokładnie jak u użytkownika: MTP n=4, słownik draftu 64k, głowica IQ4_XS, lookup W16, PM4 WA=2 + GUARD, `HSA_USE_SVM=0`, `LLAMA_GPU_VERIFY=1` |

**MTP w upstreamie:** upstream `4c3c5810f` obsługuje głowicę MTP Qwen3.8 z pliku GGUF (`--spec-type draft-mtp`). Daje ona 3.23 tok/krok (Qwen) i 3.14 tok/krok (Uncensored), więc ramię U1 to „upstream + MTP z najlepszą udokumentowaną flagą”.

**Metoda.** Wszystko przypięte do rdzeni `taskset -c 2-5`, każdy przebieg na świeżym serwerze.
- **llama-bench:** `-fa 1 -p 512,4096 -n 128 -r 3 -ngl 999`, KV q4_0. Topka dostaje środowisko PM4 z `run-topka.sh`. Rundy w kolejności U T T U.
- **Serwer:** dwa przejścia, pierwsze U0 U1 T, drugie T U1 U0 (A/B/B/A). W każdym przejściu kolejno:
  1. VRAM po załadowaniu (`amd-smi`, cała karta; przed startem zajęte 26 MiB);
  2. **czat**: `spec_sweep.py`, 6 promptów PL/EN × seedy 1,2,3, T=1, 400 tok.;
  3. **code-edit**: `copy_bench.py --set mvs`, T=0, 1024 tok.;
  4. **copy**: `copy_bench.py --set short`, T=0, 512 tok.;
  5. **~32k**: `fb_long.py`, zamrożony prompt `prompt32k.txt` (md5 `e9571514…`, z `long_ctx_bench.corpus`), T=0, 256 tok., bez myślenia i bez cache. TTFT mierzy klient (stream).
- **W tabelach:** średnia z 2 przejść lub rund; w nawiasie wartości pojedyncze.

**Skrypty:** `~/qwen-opt/bench-final/` (`final.jobs`, `fb_lb.sh`, `fb_arm.sh`, `fb_long.py`, `fb_summary.py`, `fb_lcb.sh`, `fb_lcb17.sh`). Kopia razem z logami jest w `KERNEL/qwen-opt/bench-final/`: `logs/` = `L/`, `queue-logs/` = `Q/fb-*`, wiersze `fb-lcb*` z `long_ctx.jsonl` w `logs/long_ctx-fb-lcb.jsonl`.

**Logi** (skróty `L/` = `~/qwen-opt/bench-final/logs/`, `Q/` = `~/qwen-opt/queue/logs/`):
- `L/lb.<model>.<U|T>.r<i>.jsonl`;
- `L/spec_sweep.jsonl`, `L/copy_bench.jsonl`, `L/long.jsonl`, `L/vram.jsonl` (numery linii podane przy liczbach);
- logi zadań `Q/fb-*.log`.

---

## 1. Qwen3.8-27B UD-Q4_K_XL

| metryka | upstream domyślny (U0) | **topka (T)** | zmiana T/U0 | upstream + MTP (U1) | log |
|---|---|---|---|---|---|
| prefill pp512 (llama-bench) | 1013.9 [1015.6 / 1012.2] | **1050.2** [1050.1 / 1050.2] | ×1.04 (+3.6%) | = U0 | `L/lb.qwen.{U.r1,T.r2,T.r3,U.r4}.jsonl` |
| prefill pp4096 | 1056.2 [1056.9 / 1055.5] | **1125.3** [1125.1 / 1125.5] | ×1.07 (+6.5%) | = U0 | j.w. |
| decode tg128 bez spekulacji | 35.25 [35.25 / 35.26] | **43.37** [43.37 / 43.37] | ×1.23 (+23.0%) | = U0 | j.w. |
| **czat** spec_sweep T=1, t/s | 35.8 [35.9 / 35.8] | **114.8** [114.8 / 114.9] | **×3.21** | 60.1 [60.0 / 60.2] (T/U1 ×1.91) | `L/spec_sweep.jsonl:1,6` / `:3,4` / `:2,5` |
| czat: ms/krok; tok/krok | 27.93; 1.00 | **27.65; 3.17** | −1.0%; ×3.17 | 53.70; 3.23 | j.w. |
| **code-edit** mvs T=0, t/s | 35.5 [35.5 / 35.5] | **419.9** [419.7 / 420.1] | **×11.8** | 89.1 [89.0 / 89.3] (T/U1 ×4.71) | `L/copy_bench.jsonl:1,11` / `:5,7` / `:3,9` |
| code-edit ms/krok | 28.17 | 33.78 | — | 55.50 | j.w. |
| **copy** T=0, t/s | 35.2 [35.3 / 35.2] | **406.6** [406.4 / 406.8] | **×11.6** | 87.0 [86.9 / 87.2] (T/U1 ×4.67) | `L/copy_bench.jsonl:2,12` / `:6,8` / `:4,10` |
| ~32k (29 510 tok.) prefill t/s | 923.1 [923.4 / 922.9] | **964.0** [964.5 / 963.6] | ×1.04 (+4.4%) | 885.1 | `L/long.jsonl:1,6` / `:3,4` / `:2,5` |
| ~32k TTFT | 32.41 s | **31.06 s** | −4.2% | 33.64 s | j.w. |
| ~32k decode t/s | 32.7 [32.7 / 32.6] | **111.6** [111.6 / 111.7] | **×3.41** | 49.5 (T/U1 ×2.25) | j.w. |
| VRAM serwera po załadowaniu | 23 141 MiB przy ctx **99 072** (fit, KV f16) | **23 333 MiB przy ctx 204 800** (KV q4_0) | +0.8%, za to 2.07× dłuższy kontekst | 23 200 MiB przy 204 800 | `L/vram.jsonl:1,6` / `:3,4` / `:2,5` |

**md5 przy T=0** (pole `md5` w `L/copy_bench.jsonl`; oba przejścia każdego ramienia dają to samo):
- mvs: wszystkie 3 ramiona identyczne, 4/4 pliki.
- copy: 5/6 identycznych; `hashline-pl` różni się między U0 a U1/T (U1 = T). U0 ma KV f16, U1 i T q4_0, więc różnicę tłumaczy typ KV [INFERENCE].
- Uncensored: mvs 4/4 identyczne we wszystkich ramionach; copy 4/6 wspólne, `strrep-en` i `hashline-pl` różnią się między ramionami.

## 2. Qwen3.8-27B Uncensored Q4_K_M

| metryka | upstream domyślny (U0) | **topka (T)** | zmiana T/U0 | upstream + MTP (U1) | log |
|---|---|---|---|---|---|
| prefill pp512 | 999.6 [1001.3 / 997.9] | **1041.9** [1042.2 / 1041.7] | ×1.04 (+4.2%) | = U0 | `L/lb.uncensored.{U.r1,T.r2,T.r3,U.r4}.jsonl` |
| prefill pp4096 | 1041.1 [1041.6 / 1040.7] | **1112.3** [1112.9 / 1111.7] | ×1.07 (+6.8%) | = U0 | j.w. |
| decode tg128 | 36.29 [36.32 / 36.25] | **44.24** [44.39 / 44.08] | ×1.22 (+21.9%) | = U0 | j.w. |
| **czat** spec_sweep T=1, t/s | 36.8 [36.9 / 36.8] | **111.4** [111.3 / 111.4] | **×3.03** | 55.8 [55.7 / 55.9] (T/U1 ×2.00) | `L/spec_sweep.jsonl:7,12` / `:9,10` / `:8,11` |
| czat: ms/krok; tok/krok | 27.14; 1.00 | **26.57; 2.96** | −2.1%; ×2.96 | 56.23; 3.14 | j.w. |
| **code-edit** mvs T=0, t/s | 36.6 [36.6 / 36.5] | **434.9** [433.3 / 436.6] | **×11.9** | 84.7 (T/U1 ×5.13) | `L/copy_bench.jsonl:13,23` / `:17,19` / `:15,21` |
| code-edit ms/krok | 27.36 | 32.83 | — | 58.18 | j.w. |
| **copy** T=0, t/s | 36.4 [36.4 / 36.3] | **418.3** [415.2 / 421.5] | **×11.5** | 82.5 (T/U1 ×5.07) | `L/copy_bench.jsonl:14,24` / `:18,20` / `:16,22` |
| ~32k (29 510 tok.) prefill t/s | 914.3 [914.9 / 913.8] | **958.5** [958.0 / 958.9] | ×1.05 (+4.8%) | 880.3 | `L/long.jsonl:7,12` / `:9,10` / `:8,11` |
| ~32k TTFT | 32.73 s | **31.25 s** | −4.5% | 33.82 s | j.w. |
| ~32k decode t/s | 33.5 [33.5 / 33.5] | **103.3** [106.8 / 99.8] | **×3.08** | 49.1 (T/U1 ×2.10) | j.w. (T: rozrzut 7% przy tej samej akceptacji 0.515) |
| VRAM serwera po załadowaniu | 23 141 MiB przy ctx **109 056** (fit, KV f16) | **22 619 MiB przy ctx 204 800** | −2.3%, a kontekst 1.88× dłuższy | 22 483 MiB przy 204 800 | `L/vram.jsonl:7,12` / `:9,10` / `:8,11` |

## 3. Rekord long_ctx_bench (Qwen, T=0, 256 tok.): stary wiersz vs dziś

Uruchomiony był niezmieniony `long_ctx_bench.py` na binarce topki, z flagami `run-llm.sh qwen` i środowiskiem topki, port 18704. Liczba tokenów promptu jest dziś identyczna z rekordem (1.7k / 6.6k / 29.5k / 94k). Że to te same prompty, wnioskuję tylko z liczby tokenów [INFERENCE]; korpus czyta `~/KERNEL/**/*.md`.

| prompt | rekord 2026-10-14 (MTP n=4), decode / prefill (`NOTES:331`) | **dziś, MTP n=4 (`LOOKUP=0`)** | **dziś, topka jak u użytkownika (W16)** | log |
|---|---|---|---|---|
| 1 714 tok. | 130.2 / 818 | **136.5** (+4.9%) / 781 (−4.5%) | 123.7 (−5.0%) / 753 | `~/qwen-opt/long_ctx.jsonl:69` / `:68`; `Q/fb-lcb17-qwen.log` |
| 6 565 tok. | 118.5 / 985 | 117.8 (−0.6%) / 946 | **121.6** (+2.6%) / 973 | `long_ctx.jsonl:65` / `:61`; `Q/fb-lcb-qwen.log` |
| 29 510 tok. | 105.2 / 945 | 105.0 (−0.2%) / 956 | **109.4** (+4.0%) / 965 | `:66` / `:62` |
| 94 181 tok. | 100.6 / 766 | 100.8 (+0.2%) / 768 | **105.6** (+5.0%) / 779 | `:67` / `:63` |
| 199 122 tok. (nowy punkt) | — | nie zmierzone (limit 900 s zadania) | **74.5** / 587 (prefill 339 s) | `:64` |

Wnioski:
- Krótki prompt (1.7k): sam MTP pobija dziś rekord (136.5 wobec 130.2). Lookup W16 kosztuje tu 9%, bo przy streszczaniu krótkiego tekstu ogon z kontekstu rzadko trafia (akceptacja 0.653 przy W16, 0.739 przy samym MTP).
- Od 6.6k tokenów W16 jest szybszy od samego MTP o 3–5%.

## 4. LFM2.5-24B-A2B Q5_K_M — **w kolejce**
Zadania `~/qwen-opt/bench-final/lfm.jobs` (llama-bench U T T U; serwer U0 U1 T / T U1 U0: czat + ~32k + VRAM) czekają na GPU. Tabela zostanie uzupełniona po przebiegu.

## 5. LFM2.5-24B-A2B Uncensored AD-Q5_K_M — **w kolejce**
Jak w punkcie 4 (`lfm.jobs`, zadania `fb-lb-lfmu`, `fb-lfmu-p1/p2`).

---

## Co dały 2 dni (Qwen; LFM po przebiegu kolejki)
1. **Czat ×3.0–3.2 względem domyślnego upstreamu** (35.8 → 114.8 t/s Qwen, 36.8 → 111.4 Uncensored) i **×1.9–2.0 względem upstreamu z jego własnym MTP**. Krok weryfikacji 4 draftów trwa u nas tyle, ile u upstreamu jeden token (27.7 vs 27.9 ms), a u upstreamu z MTP 53.7 ms.
2. **Edycja i kopiowanie kodu ×11.5–11.9** (35 → 407–435 t/s) dzięki ogonowi lookup W16. Wyjście przy T=0 jest identyczne z upstreamem (mvs 4/4 md5).
3. **Długi kontekst:** decode przy 29.5k ×3.1–3.4 (32.7 → 111.6 t/s), prefill +4–5%, TTFT −4%. Przy 94k decode 105.6 t/s, przy 199k 74.5 t/s.
4. **Bez spekulacji:** tg128 +22–23% (35.3 → 43.4), pp4096 +6.5–6.8%, pp512 +3.6–4.2%.
5. **Pamięć:** pełny kontekst 204 800 mieści się w 22.6–23.3 GB. Domyślny upstream w tej samej pamięci (`-fit`) dostaje tylko 99–109k kontekstu.
