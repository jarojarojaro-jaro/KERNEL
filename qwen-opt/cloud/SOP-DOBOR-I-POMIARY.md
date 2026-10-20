# SOP: dobór modelu do karty i pomiary na Vast (A–Z)

Wersja 1, 2026-10-20. Obowiązuje każdą kampanię kart (NVIDIA i inne). Pierwsze użycie: `product/PLAN-NV-V2.md`.
Brief inżyniera: `ENGINEER-PROMPT.md`; brief robotnika DeepSeek: `DEEPSEEK-WORKER-PROMPT.md`.
Narzędzia w tym katalogu (kopia robocza: `cp ~/KERNEL/qwen-opt/cloud/{fitcalc.py,hostcheck.sh,needle.py} ~/qwen-opt/cloud/`).

Zasada nadrzędna: **na kartę idzie tylko model, który jest używalny do pracy**. Jeśli żaden kandydat nie przechodzi
wszystkich bramek J1–J4, raport mówi „ta karta: brak modelu spełniającego próg” i karty nie wynajmujemy.
Każda liczba w raporcie ma źródło `plik:linia` albo znacznik `[SZACUNEK]` / `[INFERENCE]`.

## 1. Analiza karty (lokalnie, bez kosztów)

- [ ] VRAM całkowity w MiB, jak go pokazuje `nvidia-smi` (np. 3090 24576, 5060 Ti 16311, 4060 Ti 16380, 4070 Ti 12282).
- [ ] Pasmo pamięci (GB/s), architektura (`sm_86/89/120`), domyślny limit mocy (spec producenta).
- [ ] Preset w `fitcalc.py --cards`. Brak presetu → dodaj z `ovh = 120 + 2.8 × liczba SM` jako `[SZACUNEK]`.
- [ ] Czy na Vast są oferty spełniające filtr (§5.1). Brak ofert → karta odpada przed dalszą analizą (zapisz w raporcie).

## 2. Lista kandydatów

- [ ] Źródła: `wiki/modele/` (tylko modele obsługiwane przez nasz silnik), repozytoria HF z `models.tsv`, `16e-kwanty-kld.md`.
- [ ] Dla każdej rodziny wszystkie kwanty od najwyższego do najniższego (np. unsloth UD-Q6_K_M … UD-IQ2_XXS, agentionai AP-*).
- [ ] Odrzuć z powodu: licencji (np. Swift < US$1M przychodu — tylko za zgodą), braku wsparcia w naszym forku (typy prywatne),
      decyzji użytkownika (`wiki/decyzje/`) — zapisz którą decyzję stosujesz.
- [ ] Zanotuj: MTP w pliku (`nextn_predict_layers`), kontekst treningowy (`context_length` — LFM2.5 ma 131072).

## 3. Rachunek pamięci (przed wynajmem)

```
fitcalc.py <plik|URL|repo:plik[,shard2...]> --card <karta> [--arm T|U1|plain] [--ub 512] [--kv q4_0] [--ctx 131072,204800]
           [--draft <mtp-*.gguf|drafter>] [--n-cpu-moe N] [--ram-bw 70] [--depth 0,65536,131072]
```
Czyta tylko nagłówek GGUF (range request). Model i walidacja: `product/PLAN-NV-V2.md` §1 (błąd części statycznej ≤ 16 MiB,
szczyt przeszacowany o 2–339 MiB przy g = 18 KB/token). iSWA (Gemma 4, gpt-oss, Mellum), MLA, MoE z ekspertami w RAM,
drafter w osobnym pliku i szacunek decode t/s: `product/research/33-modele-na-karty.md` §1 (t/s 0.75–1.21× pomiarów).

- [ ] Dla każdego kandydata: max `-c` „pewny” (ub 512, g preset) i „górny” (`--ub 256 --g 14000`).
- [ ] Kandydat przechodzi J3-plan, jeśli **pewny max `-c` ≥ 131072**. Tylko „górny” ≥ 131072 → kandydat drugiego wyboru,
      wymaga testu wypełnienia jako pierwszego kroku na karcie.
- [ ] KV: Qwen q4_0 (cel i draft), LFM q8_0 (decyzja). Ramię wiążące: T (największe zużycie).
- [ ] Kontekst 200k wybieraj, gdy mieści się bez zejścia o kwant (bez kosztu jakości); inaczej 131072.

## 4. Bramki używalności (twarde; kandydat, który nie przechodzi, nie jest oferowany)

| bramka | próg | gdzie mierzyć | uzasadnienie |
|---|---|---|---|
| **J1 jakość** | KLD do BF16 (protokół 16e: 20 × 2048, wiki + czat PL) **wiki ≤ 0.05 i czat ≤ 0.07**; w protokole „do własnego Q8_0, wikitext ctx 512” ≤ 0.05 | lokalnie na CPU (`llama-perplexity --kl-divergence-base`), albo wartość z 16e/E1; brak pomiaru → interpolacja w tej samej rodzinie tylko gdy plik jest większy od zmierzonego, który przechodzi | U3/A3 (Q3_K_XL, 13.15 GB) to najniższy zmierzony tier z same-top PL ≥ 91.9% (`16e-kwanty-kld.md:135-136`); IQ3_S ma 1.9× KLD |
| **J2 zadania** | 3 czaty PL + 3 EN (T=1) spójne, poprawny język, bez pętli; 3 edycje kodu: diff się stosuje i test przechodzi | najpierw CPU (krótkie prompty), potem na karcie ramię T | KLD nie łapie pętli i błędów językowych (Bonsai po polsku) |
| **J3 kontekst** | `-c ≥ 131072`; szczyt VRAM po pełnej sekwencji (§7) + 512 MiB ≤ VRAM; 0 błędów; `needle.py --tokens <c>` 5/5 i 0 zmyśleń (także 200k, jeśli wybrany) | na karcie | 32k „to nie kontekst do pracy” (decyzja 2026-10-20) |
| **J4 prędkość** | decode po 64k, T=1, ramię T (lub T') ≥ 20 t/s; TTFT przy 32k raportowany | na karcie | ~1–2k tokenów odpowiedzi myślącego modelu ≤ 100 s; 20 t/s = goły upstream na 3060 (`31-3060-3080.md:10`) |

- [ ] J1 i J2-CPU zrobione **przed** wynajmem. Wynik w tabeli kandydatów (zmierzone / szacunek ze źródłem).
- [ ] Wybór: najwyższa jakość (J1) wśród kandydatów z pewnym `-c ≥ 131072`; remis → większy kontekst.
- [ ] Żaden kandydat → „ta karta: brak modelu spełniającego próg”, koniec procedury dla tej karty.

## 5. Wybór hosta

### 5.1 Wyszukiwanie (read-only)
```
vastai search offers 'gpu_name=<GPU> num_gpus=1 gpu_ram>=<V> reliability>0.98 verified=true rentable=true
  direct_port_count>=1 disk_space>=60 inet_down>=300 cuda_vers>=12.8 inet_down_cost<=0.002 inet_up_cost<=0.002
  cpu_cores_effective>=4 cpu_ram>=24 geolocation notin [CN]' --storage 60 -o dph_total --raw
```
- [ ] Sortuj po `dph_total × h + GB_pobrania × inet_down_cost` (lekcja: transfer był 55% kosztu kampanii 2026-10-20).
- [ ] `hostcheck.sh offer <id> <GB_pobrania> <h>` → RESULT PASS (verified, rel > 0.98, transfer ≤ $0.002/GB, driver ≥ 570,
      RAM ≥ 24 GB). Drukuje koszt GPU + dysk + transfer i ×1.3.
- [ ] Zapisz 1–2 oferty zapasowe.

### 5.2 Wynajem
- [ ] `up.sh <id> --download-gb <GB> --hours <h> --disk <model+35, min 60> --label <kampania>-<karta>-<data> --go`
      (odmawia hostów z płatnym transferem > $0.002/GB; uruchamia lokalny watchdog i samozniszczenie na instancji).
- [ ] Zawsze podawaj id instancji jawnie (wiele boxów naraz: `state/current` jest współdzielony).

### 5.3 Bramka boxa (pierwsze 5 minut, przed pobraniem modelu)
```
hostcheck.sh box https://huggingface.co/<repo>/resolve/main/<plik>.gguf <GB>
```
- [ ] `nvidia-smi -q -d POWER`: Current Power Limit == Default Power Limit. Inaczej **zniszcz od razu** (3090 przy 200 W: SM 405–480 MHz).
- [ ] HF ≥ 25 MB/s na 1 GiB z pliku modelu. Inaczej zniszcz (2026-10-20: 26 KB/s).
- [ ] Dysk ≥ model + 30 GB, RAM ≥ 24 GB, kwota CPU (`-t` = kwota), PCIe pod obciążeniem (x1 → `LLAMA_GPU_VERIFY=1` obowiązkowo, odnotuj).
- [ ] Driver ≥ 570 i `nvidia-smi` w kontenerze (driver 565 + CUDA 12.8 po cichu liczy na CPU).
- [ ] FAIL → `down.sh <id> --go`, następna oferta z §5.1. Każdy nieudany host w raporcie (id, powód, koszt).

## 6. Staging (raz na kartę)

- [ ] Jeden plik modelu, pobrany na boxie z HF (nie ze stacji: upload ~0.45 MB/s), sprawdzony sha256 (HF LFS / `models.tsv`).
- [ ] Źródła: `git archive` gałęzi + `git diff` (rozpakowywać z `tar -m`, inaczej ninja nie przebuduje).
- [ ] Buildy: upstream (commit bazowy kampanii) i nasza gałąź, `-DCMAKE_CUDA_ARCHITECTURES=<sm>`, ccache, `-j` ≤ kwota.
- [ ] **Nigdy nie mierzyć w trakcie buildu** (skrypty czekają na brak `nvcc|cc1plus|ninja`).
- [ ] Gałąź skompilowana lokalnie dla danego `sm` przed wynajmem (CUDA 12.8 w `~/opt/cuda-12.8`).

## 7. Test wypełnienia (J3 VRAM) — pierwszy pomiar na karcie

- [ ] Ramię T przy docelowym `-c` i ub. Sekwencja na jednym serwerze: 512 → 16k T=0 → 16k T=1 → 64k → (c − 1.2k) T=0 →
      drugi prompt (c − 1.2k) innym tekstem T=1 → czat 400 tok. `nvidia-smi --query-gpu=memory.used` co 0.2 s.
- [ ] PASS: 0 błędów (`out of memory`, `failed to allocate`, `decode() failed`, HTTP 5xx), szczyt + 512 ≤ VRAM.
- [ ] To samo dla U1 (U1 zużywa mniej; musi przejść przy tym samym `-c`).
- [ ] Zapisz: VRAM po załadowaniu, szczyt, prompt, `-c`, ub, log serwera z liniami buforów (`-lv` info).
- [ ] Porównaj z `fitcalc` (część statyczna ±50 MiB; inaczej wyjaśnij przed dalszymi pomiarami).
- [ ] FAIL → kolejno: `-ub 256`, `GGML_CUDA_KVQ=1`, kwant niżej **tylko jeśli nadal przechodzi J1**. Nigdy nie schodzić poniżej 131072.

## 8. Protokół U0 / U1 / T

- [ ] Ramiona (wszystkie przy tym samym modelu i `-c`, poza U0):
  - U0 = upstream `llama-server -m <plik>` (domyślny fit; zapisz jego n_ctx; obciążenia ponad jego kontekst = „—”);
  - U1 = upstream `-fit off -ngl 99 -t <kwota> -fa on -ctk q4_0 -ctv q4_0 -c <c> -ub <ub> -np 1 --jinja --cache-ram 8192
    --reasoning-effort low --spec-type draft-mtp --spec-draft-n-max 4 -ctkd q4_0 -ctvd q4_0`;
  - T = nasza gałąź z flagami U1 + `--spec-draft-vocab draft_vocab_qwen38.txt --spec-draft-vocab-n 65536
    --spec-draft-head-type iq4_xs --spec-mtp-type iq4_xs`, env `LLAMA_SPEC_LOOKUP=3 LLAMA_SPEC_LOOKUP_W=16
    LLAMA_SERVER_CACHE_SHARE_MIN=1024 LLAMA_GPU_VERIFY=1`; nowe przełączniki domyślnie off;
  - model bez MTP: U0 i T (lookup), bez U1.
- [ ] Obciążenia: czat T=1 (spec_sweep 6 promptów × 3 seedy × 400 tok); edycja kodu mvs T=0 (4 × 1024) + zestaw edit;
      decode po 16k / 64k / 128k (+200k) przy T=0 i T=1, 256 tok; prefill 32k i 128k z TTFT; VRAM.
- [ ] ABBA: U0 U1 T | T U1 U0, świeży serwer na ramię; p1 seedy 1–3, p2 seedy 4–6. Taskset na jednym węźle NUMA/CCX.
- [ ] Bramka poprawności przed pomiarem T: test-backend-ops (TOP_K, GET_ROWS, SUM_ROWS, GUMBEL_MAX, GATED_DELTA_NET,
      MUL_MAT typów modelu); md5 22 wierszy `LLAMA_GPU_VERIFY=0` == `=1`; gałąź z przełącznikami off == baza.
- [ ] Bramki jakości na karcie: J2 (ramię T) i J3 needle przy `-c` (ramię T); J4 z wiersza „decode po 64k T=1”.
- [ ] Tabela: średnia [p1 / p2], ms/krok, tok/krok, CI95 T vs U1.

## 9. Pętla optymalizacji

- [ ] Lista pomysłów z poprzednich raportów karty/architektury (np. `31-*`), uszeregowana po oczekiwanym zysku × prawdopodobieństwie.
- [ ] Każdy pomysł: przełącznik env domyślnie off; ≤ 10 min GPU; ABBA A B B A na świeżych serwerach (czat T=1 6 × 2 seedy
      + mvs T=0); CI95 bootstrap po parach.
- [ ] Przyjęcie: CI95 zmiany t/s wyklucza 0 **albo** ms/krok spada na każdym prompcie; plus bramka:
  - bitowy → md5 22/22 = baza;
  - niebitowy (np. GDN MMA, KVQ) → KLD vs referencja CPU fp32 nie gorszy niż baza (± 1σ);
  - konfiguracja (głębokość draftu, słownik) → statyczna na kartę, nowe md5 referencyjne, deterministyczność, GV0 == GV1.
- [ ] Kod piszą robotnicy DeepSeek (`ds-agent`, brief wg `DEEPSEEK-WORKER-PROMPT.md`); inżynier tylko kieruje, mierzy, scala.
- [ ] Mikrobenchmark ≠ zysk w serwerze (lekcja RPB=8 na 4070 Ti): przyjmuje się wyłącznie po ABBA w serwerze.
- [ ] Finał: T' vs T ABBA na tym samym binarnym, potem pełne U0/U1/T/T'. **Najpierw T i T'** — na początku okna kredytu.

## 10. Raport (`product/research/<nr>-<karta>.md`)

```
# <nr> — <karta>: <model> <kwant>, -c <c>, KV q4_0 — U0/U1/T/T'
Data, inżynier, gałąź (commit), skrypty, wyniki (ścieżki).
## Werdykt            (tabela U0/U1/T/T': czat T=1, mvs, decode 16k/64k/128k, prefill/TTFT 32k/128k, VRAM; T' = przełączniki)
## Bramki J1–J4       (wartości, źródła, PASS/FAIL)
## Sprzęt i host      (oferta, $/h, limit mocy = domyślny, PCIe pod obciążeniem, CPU/kwota, driver, HF MB/s, nieudane hosty)
## Wybór modelu i -c  (tabela fitcalc vs zmierzone: załadowanie, szczyt, zapas; sekwencja wypełnienia)
## Baseline           (ABBA, tabela [p1/p2], CI95)
## Profil             (gdzie idzie krok; tylko jeśli mierzony)
## Pomysły            (#, hipoteza, robotnik/brief, bramka, ABBA, werdykt)
## Finał T' vs T
## Koszt              (z faktur: GPU, dysk, transfer; vs plan)
## Nie zmierzone      (powód)
## Do bazy wiedzy
```

## 11. Wiki

- [ ] `wiki/karty/<karta>.md` — model, kwant, `-c`, VRAM, t/s U0/U1/T/T' z datą i warunkami.
- [ ] `wiki/eksperymenty/<data>-<temat>.md` — każdy przyjęty i odrzucony pomysł (liczby, CI, bramka).
- [ ] `wiki/lekcje/` — nowe pułapki (host, harness, kernel).
- [ ] `wiki/decyzje/` — tylko polecenia użytkownika (cytat, data).
- [ ] `python3 tools/wiki.py index`, commit `wiki: …`.

## 12. Zniszczenie i rozliczenie

- [ ] `down.sh <id> --go`; `vastai show instances` nie zawiera instancji (zrzut do raportu).
- [ ] Po 15–60 min: `vastai show invoices-v1 --charges -s <data>` → pozycje gpu / disk / bwd tej instancji.
- [ ] Tabela w raporcie: plan vs faktura (GPU, dysk, transfer, suma); różnica > 20% → lekcja.
- [ ] Kredyt po zniszczeniu (`vastai show user`).

## 13. Budżet i warunki stopu

- [ ] Budżet karty = GPU + dysk + transfer z §5 × 1.3 + rezerwa na 1–2 złe hosty (0.3 h każdy). Suma kampanii znana przed doładowaniem.
- [ ] Twardy limit czasu boxa (`--hours`) = plan × 1.1.
- [ ] Co 30 min `vastai show user`: kredyt < 1.3 × koszt pozostałych godzin wszystkich boxów → natychmiast finał T/T', bez nowych pomysłów.
- [ ] Stop pomysłu: > 10 min GPU, błędne wyjście (bez powtórek na GPU — debug na CPU), brak zysku w ABBA.
- [ ] Stop karty: FAIL J1–J4 bez dopuszczalnej poprawki, 2 nieudane hosty z rzędu, koniec okna.
