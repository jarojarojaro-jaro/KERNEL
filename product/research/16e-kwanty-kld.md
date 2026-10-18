# 16e: Nowe kwanty 27B na 12–16 GB: KLD, zadania i prędkość (eksperyment E1 z raportu 15e)

Data: 2026-10-16 (runda 1) i 2026-10-18 (runda 2, dokończenie po awarii omp). Projekt: `15e-kwantyzacja-nowa.md` §5 (E1 + E3).
Surowe dane: `~/qwen-opt/cloud/results/quantkld-20261016/`. Skrypty: `~/qwen-opt/quantkld/` (korpusy, `tasks.py`, `analyze.py`, `speed.py`, `tasks_report.py`, `lt_score.py`, `pod/*.sh`) i `~/qwen-opt/cloud/runs/quantkld/` (wynajem, `vast/e1.sh`, `vast/e2.sh`, `vast/t5090.sh`).

Oznaczenia ramion (jak w 15e §5):

| kod | plik | GB |
|---|---|---|
| U3 | unsloth UD-Q3_K_XL (nasz domyślny 16 GB) | 13.15 |
| A3 | agentionai AP-Q3_K_XL | 13.15 |
| U4 | unsloth UD-Q4_K_XL (tylko skala KLD) | 17.56 |
| I4 / I2 | ISTA GSQ-RCO IQ3_S / IQ2_S (`-mtp` do prędkości) | 11.77 / 9.26 |
| W4 / W3 / W2 / W1 | Swift-1.5 GSQ-RCO IQ3_S / IQ3_XXS / IQ2_S / IQ2_XS (`-mtp` do prędkości) | 11.77 / 10.09 / 9.26 / 8.42 |
| S0 / S1 | Underdog Saluki IQ2-mix / ten sam plik z głowicą MTP Kujiry | 7.90 / 8.35 |
| B0 / B1 | Ternary Bonsai 2: repack PQ2_0→Q2_0 (nasz fork) / Prism PTQ1_0 (fork Prism) | 7.62 / 5.95 |

## TL;DR

1. **16 GB: zostajemy przy Q3_K_XL. AP-Q3_K_XL (A3) to darmowa poprawka, a GSQ-RCO IQ3_S przegrywa.**
   - A3 to te same typy tensorów co U3 (porównałem wszystkie 866 tensorów: 0 różnic), czyli te same bajty i ta sama prędkość.
   - KLD A3 vs U3:
     - PL proza: remis (0.0319 vs 0.0321 ± 0.0007);
     - wiki: remis (0.0400 vs 0.0390);
     - czat PL: −12% (0.0559 vs 0.0635);
     - kod: −23% (0.0249 vs 0.0322);
     - długi kontekst PL: −4%.
   - ISTA I4 i Swift W4 mają KLD-PL 1.7–1.8 × U3 (0.057 / 0.055). Działa kill criterion „GSQ na 16 GB” (próg 1.5×).
   - Prędkość na 5060 Ti z MTP: I4 i W4 50.0 t/s, U3 51.7 t/s (−3%). Bez MTP GSQ jest +4% szybszy (30.3 vs 29.1). H3 potwierdzona.
2. **12 GB: MTP działa także na kwantach 2-bitowych, ale zysk jest mniejszy niż u społeczności.**
   - Saluki + głowica Kujiry na 3060 170 W: 23.0 → 33.1 t/s (×1.44, n=2). Społeczność na 3080 podawała ×1.61.
   - GSQ/Swift `-mtp` na 3060 120 W: ×1.49–1.53 (n=2). n=3 jest zawsze gorsze od n=2 (IQ są obliczeniowo ciężkie przy weryfikacji).
   - Kill „MTP na 12 GB” nie zadziałał (próg ×1.25).
3. **Jakość 12 GB (KLD do Qwen BF16, wiki / PL proza):**

   | ramię | KLD wiki | KLD PL proza |
   |---|---|---|
   | W3 | 0.119 | 0.108 |
   | W2 | 0.164 | 0.142 |
   | I2 | 0.164 | 0.155 |
   | W1 | 0.218 | 0.235 |
   | S0 (Saluki) | 0.257 | 0.320 |
   | B0 (Bonsai) | 0.352 | 0.508 |

   - Saluki i Bonsai tracą najbardziej właśnie na polskim: KLD-PL / KLD-wiki = 1.24 i 1.44, a GSQ 0.87–0.95.
   - Bramkę 12 GB z 15e (KLD-wiki ≤ 0.15 i t/s ≥ 1.25 × S0) przechodzi tylko **W3: Swift IQ3_XXS-mtp, 11.5 GB VRAM przy 16k, 25.2 t/s z MTP (×1.46 S0)**.
   - Wymaga to decyzji licencyjnej. Odpowiednik Apache to ISTA IQ3_XXS-mtp, z tą samą alokacją; nie mierzyłem go.
4. **Swift to w tekście prawie ten sam model co Qwen. Różni się zachowaniem w myśleniu.**
   - KLD Swift-Q8_0 do Qwen-Q8_0: wiki 0.0082, PL proza 0.0019. Podłoga Q8_0 vs BF16 to 0.0038 / 0.0006.
   - Dlatego oba widoki KLD Swifta (do własnego BF16 i do BF16 Qwena) różnią się o ≤ 5%, np. W4 wiki 0.0723 vs 0.0757.
   - Akceptacja MTP Swifta z niedouczoną głowicą Qwena jest taka sama jak u ISTA: W2/I2 0.55/0.53, W4/I4 0.55/0.55. Obawa z 15e się nie potwierdziła i E3 zamykamy.
5. **Zadania (20 promptów × 2 seedy, myślenie włączone, limit 8192):**
   - Swift zużywa ~19% mniej tokenów od ISTA tego samego tieru na parach, które oba skończyły:
     - W2/I2: 28 941 vs 35 900;
     - W4/I4: 28 376 vs 35 149.
   - Licząc ucięte pętle myślenia: −29…−32%.
   - Pass-rate nie spada: W2 0.95 vs I2 0.90, W4 1.00 vs I4 0.90.
   - Mediana per prompt nie spada (0.95–1.18). Zysk bierze się z rzadszych „zapętleń” myślenia (1 vs 4 ucięcia), a nie z krótszego myślenia w ogóle.
   - H2 (≥ 20%) na granicy; kill Swifta (< 15%) nie działa.
6. **Długi kontekst PL (2 × 16k): żaden kwant nie „psuje języka” skokowo.**
   - KLD-long / KLD-PL proza = 1.08–1.25 dla wszystkich ramion.
   - GSQ/Swift (1.14–1.18) nie wypadają gorzej niż UD (1.25).
7. **Najszybszy plik na 12 GB to nadal Bonsai PTQ1_0 na forku Prism** (44.9 t/s na 3060 170 W, md5 identyczne z raportem 09), ale ma najgorszą jakość (KLD-PL 0.51).
8. Wydatki:
   - runda 1: Vast ≈ $0.75, RunPod $1.87;
   - runda 2: Vast ≈ $0.91, RunPod $0.57.
   - Wszystkie instancje usunięte (§9).

## 1. Metoda

### 1.1 Referencja KLD: prawdziwe BF16, nie Q8_0
- **Wybór:** RunPod A40 / RTX A6000 48 GB za $0.59/h z `-fit on`.
  - BF16 Qwena (54.66 GB) nie mieści się w 48 GB, więc llama.cpp sam przenosi część warstw do RAM.
  - Bazowe logity liczą się 54–240 s na korpus.
- **Uzasadnienie:**
  - A100 80 GB kosztował na RunPod $1.19–1.79/h, a na Vast nie było ofert 80 GB poniżej $2/h.
  - Offload na 48 GB jest tańszy, a referencja pozostaje dokładnie BF16.
- Q8_0 jako referencja też byłoby w porządku. Zmierzona podłoga Q8_0 vs BF16 wynosi 0.0006–0.0038 (§2.1), czyli ≤ 10% najmniejszego efektu wśród ramion (U3).
- Referencja Swifta: `Swift-1.5-BF16.gguf` z `convert_hf_to_gguf.py` (llama.cpp v0.7.0) z safetensors `ukisai/Swift-1.5-Qwen3.8-27b@b4c84d42`.
- Referencja Qwena: unsloth BF16 GGUF `@4ca72078`, dwa shardy, sha256 sprawdzone przez aria2c.

### 1.2 Korpusy
md5 identyczne w obu rundach (`pod-final/res/corpora.md5`, `pod-r3/res/corpora.md5`).

| korpus | co | md5 | ocena |
|---|---|---|---|
| wiki | `wiki.test.raw` | 7c0137fc… | 20 × 2048 |
| plprose | FineWeb-2 `pol_Latn` test, przetasowany seed 0, 800k znaków | cae78980… | 20 × 2048 |
| chat | 36 promptów PL/EN (6 ze `spec_sweep` + 30 PL), odpowiedzi Qwen Q8_0 (T=0, bez myślenia), teacher-forced | 783d39ac… | 11 × 2048 |
| code | 103 prywatne pliki `.py`/`.sh` z `~/qwen-opt` (nie ma ich w danych treningowych), seed 0 | b2191461… | 20 × 2048 |
| long | „Lalka” t. 1 (Wolne Lektury), 160k znaków | a19a58a4… | 2 × 16384 |

- Komenda: upstream `llama-perplexity` v0.7.0 (`620d222`) z `-fa on -b 2048 -ub 1024`, `--kl-divergence-base` / `--kl-divergence`.
- Zmiana wobec 15e: 20 chunków zamiast 32, żeby zmieścić się w budżecie. Moje wartości wiki są o ~10–15% wyższe niż agentionai [A] (60 × 2048), np. U3 0.0390 vs 0.0337. Ranking jest ten sam.
- Powtarzalność między rundami i kartami (A40 → A6000):
  - U3 wiki: 0.038982 w obu rundach, co do cyfry;
  - PPL bazowe identyczne (wiki 6.0604, plprose 6.6993, chat 1.5681, code 2.6089, long 7.4730).

### 1.3 Zadania
- `tasks.py`: 8 zadań matematycznych z odpowiedzią liczbową (4 PL, 4 EN), 6 zadań kodu z testami (`merge_intervals`, `LFUCache`, `serialize/deserialize`, rzymskie, `top_k_words` z PL znakami, `min_window`) i 6 instrukcji PL z checkerem formatu.
- Ustawienia: T=0.6, top-p 0.95, top-k 20, myślenie włączone, limit 8192, seedy 1 i 2.
- Silnik: upstream v0.7.0, `-np 20`, KV q8_0.
  - Seed 1 dla W2/I2/W4/I4/S0 liczył A40.
  - Resztę (seed 2 tych ramion oraz U3, B0, W3 i W1 w obu seedach) liczył wynajęty RTX 5090.
- LanguageTool-pl 6.6 (lokalnie, CPU, `nice 19`) liczył błędy na 1000 słów w odpowiedziach PL (bez myślenia).

### 1.4 Prędkość
Nasz fork `cuda-v070` @ `7a538d9` z profilem NVIDIA (`GGML_HIP_GATE_UP_Q8=0`), `-fit off -ngl 99 -fa on -ctk/-ctv q8_0 -np 1`, `-t` = kwota CPU cgroup.
- MTP: `--spec-type draft-mtp --spec-draft-n-max 2|3` + nasze dodatki (słownik draftu 64k, głowica IQ4_XS).
- `spec_sweep`: 6 promptów × 2 seedy × 400 tokenów, ABBA P M2 M3 M3 M2 P, świeży serwer na rundę.
- `llama-bench`: pp4096, tg128, tg64 @ d16384.
- TTFT ~2k tokenów (`ttft.py`) i VRAM.

Hosty:

| host | karta | CPU | wątki | ctx | ramiona |
|---|---|---|---|---|---|
| 3060 A | RTX 3060, **limit mocy 120 W** (domyślnie 170) | EPYC 7662 | 15 | 16k | S1 I2 W2 W1 W3 B0 |
| 3060 B | RTX 3060 170 W, **ten sam host co raport 09** | E5-2698 v4 | 9 | 16k | S1 (kotwica) B0 B1 |
| 5060 Ti | RTX 5060 Ti 150 W | Ryzen 7 3700X | 7 | 32k | U3 I4 W4 |

- Dlaczego dwa hosty 3060: host A okazał się przycięty do 120 W, a S1 plain dał na nim 17.2 vs 23.0 t/s na hoście B.
- Porównania robię tylko w obrębie jednego hosta. S1 łączy oba hosty: plain ×1.34, MTP ×1.36.
- A3 nie był mierzony na karcie: identyczne typy tensorów dają identyczny graf `[INFERENCE]`. Plik ma też tę samą głowicę MTP (15 tensorów `blk.64`, Q8_0/Q6_K).

## 2. KLD

### 2.1 Widok „do Qwen3.8-27B BF16” (wszystkie ramiona)
Źródło: `kld-all/kld.md:9-24`.

| ramię | wiki | PL proza | czat PL | kod | długi PL 16k | 99% KLD PL | same-top PL | PPL(Q)/PPL(ref) wiki | PL/wiki | long/PL |
|---|---|---|---|---|---|---|---|---|---|---|
| Q8_0 (podłoga) | 0.0038 | 0.0006 | 0.0031 | 0.0010 | 0.0007 | 0.005 | 98.9% | 1.0005 | — | — |
| U4 | 0.0153 | 0.0073 | 0.0226 | 0.0086 | 0.0091 | 0.073 | 96.2% | 0.9925 | 0.48 | 1.25 |
| **U3** | 0.0390 | 0.0321 | 0.0635 | 0.0322 | 0.0401 | 0.306 | 91.9% | 1.0173 | 0.82 | 1.25 |
| **A3** | 0.0400 | **0.0319** | **0.0559** | **0.0249** | **0.0384** | 0.325 | 92.1% | 1.0191 | 0.80 | 1.20 |
| I4 | 0.0733 | 0.0569 | 0.0878 | 0.0416 | 0.0650 | 0.552 | 89.6% | 0.9910 | 0.78 | 1.14 |
| W4 | 0.0757 | 0.0554 | 0.0941 | 0.0459 | 0.0633 | 0.532 | 89.9% | 1.0620 | 0.73 | 1.14 |
| W3 | 0.1192 | 0.1076 | 0.1605 | 0.0864 | 0.1266 | 1.091 | 86.0% | 1.0414 | 0.90 | 1.18 |
| W2 | 0.1638 | 0.1420 | 0.1903 | 0.1222 | 0.1642 | 1.430 | 83.9% | 1.0431 | 0.87 | 1.16 |
| I2 | 0.1639 | 0.1550 | 0.2143 | 0.1147 | 0.1806 | 1.521 | 83.1% | 1.0351 | 0.95 | 1.17 |
| W1 | 0.2177 | 0.2353 | 0.3101 | 0.1698 | 0.2678 | 2.386 | 79.9% | 1.0787 | 1.08 | 1.14 |
| S0 Saluki | 0.2574 | 0.3196 | 0.3150 | 0.1913 | 0.3548 | 2.841 | 76.0% | 1.1141 | 1.24 | 1.11 |
| B0 Bonsai | 0.3516 | 0.5078 | 0.4369 | 0.2962 | 0.5482 | 4.169 | 72.2% | 1.3082 | 1.44 | 1.08 |

Błędy standardowe: wiki ±0.002–0.005, PL proza ±0.0007–0.006 (pełne w `kld-all/kld.md`).

Wnioski:
- **A3 vs U3 (te same bajty):**
  - A3 nie jest gorszy nigdzie poza szumem: wiki +0.001 przy ±0.0027.
  - Na czacie (−12%) i kodzie (−23%) jest wyraźnie lepszy, czyli imatrix „mixed-v2” agentionai przenosi się na nasze dane.
  - Na PL prozie jest remis. Kill „AP” (KLD-PL(A3) ≥ U3) nie działa, choć tylko o włos.
- **Ten sam tier, inny model:**
  - W2 vs I2: PL −8%, czat −11%, długi −9%, kod +6%.
  - W4 vs I4: PL −3%, czat +7%, kod +10%.
  - Swift nie jest ani lepszym, ani gorszym kwantem. Różnice mieszczą się w ±10% i zależą od domeny.
- **Polszczyzna:**
  - GSQ i UD tracą na PL prozie mniej niż na wiki (PL/wiki 0.73–0.95).
  - Saluki (1.24) i Bonsai (1.44) tracą więcej na polskim, więc ich imatrix/QAT jest „angielski”.
- **Czat** jest najtrudniejszym korpusem dla wszystkich kwantów IQ/K: KLD 1.3–2 × PL prozy.

### 2.2 Widok „Swift do własnego BF16” i odległość Swift–Qwen
Źródło: `kld-all/kld.md:2-7` (Swift Q8 do Qwen Q8), `kld-all/kld.md:26-33` (widok Swift), `pod-final/res/kld/qq8.*.log`.

| | wiki | PL proza | czat PL | kod | długi PL |
|---|---|---|---|---|---|
| W4 do Swift BF16 | 0.0723 | 0.0546 | 0.0895 | 0.0443 | 0.0626 |
| W3 do Swift BF16 | 0.1190 | 0.1074 | 0.1583 | 0.0854 | 0.1267 |
| W2 do Swift BF16 | 0.1659 | 0.1419 | 0.1883 | 0.1219 | 0.1647 |
| W1 do Swift BF16 | 0.2216 | 0.2368 | 0.3121 | 0.1714 | 0.2694 |
| **Swift Q8_0 do Qwen Q8_0** | **0.0082** | **0.0019** | — | — | — |
| (podłoga Qwen Q8_0 do Qwen BF16) | 0.0038 | 0.0006 | | | |

- Oba widoki różnią się o ≤ 5% (W4 wiki 0.0723 vs 0.0757, czat 0.0895 vs 0.0941). Odległość Swift–Qwen na tekście jest rzędu szumu Q8_0: same-top 97.9%, PPL wiki 6.17 vs 6.06.
- Mój wiki-KLD Swifta do własnego BF16 jest o ~15% wyższy niż deklaracja UkisAI (W2 0.166 vs 0.135, W4 0.072 vs 0.051). To kwestia protokołu: ich ctx 512 × 100, mój 2048 × 20.
- Wniosek: RL/OPD Swifta zmienia prawie wyłącznie zachowanie w trybie myślenia, a nie rozkład na zwykłym tekście. Tłumaczy to też, dlaczego głowica MTP Qwena działa na Swifcie bez strat (§4.3).

## 3. Zadania (20 promptów × 2 seedy)
Źródło: `tasks-all/tasks-report.json`, tabela z `tasks_report.py`.

| ramię | pass | mat. | kod | PL instr. | ucięte @8192 | śr. tokenów | mediana myślenia | t/s (karta docelowa) | śr. czas do odpowiedzi |
|---|---|---|---|---|---|---|---|---|---|
| W4 | **1.00** | 1.00 | 1.00 | 1.00 | 0 | 1057 | 314 | 50.0 (5060 Ti, MTP) | **21.1 s** |
| I4 | 0.90 | 1.00 | 0.67 | 1.00 | 3 | 1493 | 310 | 50.0 | 29.9 s |
| U3 | 0.88 | 1.00 | 0.58 | 1.00 | 5 | 1744 | 363 | 51.7 | 33.7 s |
| W2 | 0.95 | 1.00 | 0.83 | 1.00 | 1 | 1161 | 398 | 25.1 (3060 A, MTP) | 46.3 s |
| I2 | 0.90 | 1.00 | 0.67 | 1.00 | 4 | 1717 | 326 | 24.7 | 69.5 s |
| W3 | 0.90 | 1.00 | 0.67 | 1.00 | 3 | 1525 | 360 | 25.15 | 60.6 s |
| W1 | 0.88 | 1.00 | 0.58 | 1.00 | 3 | 1410 | 412 | 25.8 | 54.7 s |
| S0 | 0.85 | 0.94 | 0.58 | 1.00 | 5 | 1957 | 544 | 24.35 (S1 MTP) | 80.4 s |
| B0 | 0.95 | 1.00 | 0.92 | 0.92 | 2 | 1756 | 417 | 27.5 (3060 A, plain) | 63.8 s |

Pary (ten sam prompt i seed):

| para | sparowane | oba skończyły | tokeny (oba skończyły) | tokeny łącznie z uciętymi | mediana ilorazu per prompt |
|---|---|---|---|---|---|
| W2 vs I2 | 40 | 36 | 28 941 vs 35 900 (**−19.4%**) | −32.3% | 1.18 |
| W4 vs I4 | 40 | 37 | 28 376 vs 35 149 (**−19.3%**) | −29.2% | 0.95 |
| W1 vs I2 | 40 | 36 | −20.8% | −17.8% | 1.07 |
| W3 vs I2 (inny tier) | 40 | 35 | −9.1% | −11.2% | 1.06 |

Wnioski:
- n = 40 na ramię, więc różnice pass-rate rzędu 5–10 pp to 2–4 prompty, w praktyce szum. Cała różnica w pass-rate siedzi w kodzie, prawie zawsze jako ucięcie przy 8192 (`LFUCache`, `min_window`, rzymskie).
- Swift ma najmniej ucięć: W4 0, W2 1, wobec 3–5 u reszty.
- **„Krótsze myślenie” Swifta działa głównie przez obcinanie ogona.**
  - Mediana per prompt jest bez zmian albo wyższa (W2: 1.18).
  - Suma i średnia spadają o ~19–32%, bo Swift rzadziej się zapętla.
  - Deklaracja UkisAI (−58.5% mediany na GPQA-D) nie przenosi się na nasz zestaw.
- Mimo niższej jakości KLD Bonsai B0 ma pass 0.95. Zestaw 20 zadań jest za łatwy, żeby rozróżnić kwanty o KLD 0.16 i 0.35. Matematyka 1.00 prawie wszędzie, PL instrukcje 1.00 wszędzie poza B0.

LanguageTool-pl (`tasks-all/lt.json`): 11–12 odpowiedzi PL na ramię, ~550 słów.

| ramię | błędy/1k słów (wszystkie) | bez typografii/stylu |
|---|---|---|
| W4 | 4.3 | 4.3 |
| U3 | 7.4 | 7.4 |
| W2 | 8.0 | 3.2 |
| I4 | 8.7 | 3.5 |
| W1 | 13.0 | 3.7 |
| B0 | 13.6 | 11.9 |
| I2 | 15.5 | 10.3 |
| W3 | 16.1 | 11.5 |
| S0 | 21.7 | 8.3 |

- Liczby to 2–7 dopasowań na ramię, prawie wyłącznie `MORFOLOGIK_RULE_PL_PL` (słownik). To sygnał bardzo słaby.
- Saluki ma najwięcej uwag ogółem, a W3 najwięcej „gramatycznych”. Kryterium „LT ≤ Saluki” jest przy tej próbie nierozstrzygalne.

## 4. Prędkość

### 4.1 12 GB, 3060 A (120 W, EPYC 7662, 15 wątków, ctx 16k)
Źródło: `3060-hostA/speed.md`.

| ramię | plain t/s | MTP n=2 | MTP n=3 | ×plain | akcept. n2/n3 | tok/krok n2 | PL / EN (n2) | pp4096 | tg128 | tg@16k | VRAM MTP 16k | TTFT 2030 tok |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S1 Saluki | 17.2 | 24.35 | 22.9 | ×1.41 | 0.49 / 0.40 | 1.97 | 24.0 / 24.9 | 396 | 17.3 | 15.2 | 9.76 GB | 6.25 s |
| I2 | 16.6 | 24.7 | 23.5 | ×1.49 | 0.53 / 0.45 | 2.05 | 24.5 / 24.9 | 391 | 16.8 | 14.7 | 10.74 GB | 6.43 s |
| W2 | 16.5 | 25.1 | 23.7 | ×1.52 | 0.55 / 0.45 | 2.08 | 26.9 / 24.9 | 391 | 16.7 | 14.6 | 10.74 GB | 6.51 s |
| W1 | 17.0 | 25.8 | 25.1 | ×1.51 | 0.55 / 0.48 | 2.09 | 27.4 / 25.1 | 384 | 17.1 | 15.0 | 10.03 GB | 6.36 s |
| W3 | 16.4 | 25.15 | 23.5 | ×1.53 | 0.56 / 0.45 | 2.11 | 26.3 / 24.9 | 398 | 16.6 | 14.5 | **11.54 GB** | 6.23 s |
| B0 Bonsai Q2_0 | 27.4–27.5 (greedy) | — | — | — | — | — | — | 442 | 27.6 | 22.7 | — | — |

### 4.2 12 GB, 3060 B (170 W, host z raportu 09, 9 wątków, ctx 16k)
Źródło: `3060-hostB/speed.md`.

| ramię | plain t/s [min–max] | MTP n=2 | ×plain | pp4096 | tg128 | tg@16k | VRAM | TTFT 2030 tok | greedy md5 |
|---|---|---|---|---|---|---|---|---|---|
| S1 Saluki | 23.0 [23.0–23.0] | 33.1 [32.9–33.2] | ×1.44 | 557 | 23.2 | — | — | — | MTP `2aac36319f52` |
| B0 Bonsai Q2_0 (nasz) | 35.1 [34.9–35.3] | — | — | 611 | 35.3 | 28.9 | 7.98 GB | 3.86 s | `5c280885b7b2` (= host A) |
| **B1 Bonsai PTQ1_0 (Prism)** | **44.9** [44.8–44.9] | — | — | 591 | 44.2 | 35.1 | 6.41 GB | 3.96 s | `89fbea6c621f` (= raport 09) |

- Kotwica: S1 plain na hoście B to 23.0 t/s, a Saluki w raporcie 09 dało 23.4. B1 44.9 vs 44.8 i B0 35.1 vs 35.5 w raporcie 09, czyli host się powtarza.
- Szacunek W2/W3 z MTP na pełnym 3060 170 W: 25.1 × 1.36 ≈ **34 t/s** `[SZACUNEK: skala S1-MTP między hostami]`. To tyle co Bonsai Q2_0, przy 2–3× niższym KLD.

### 4.3 16 GB, 5060 Ti (ctx 32k, 7 wątków)
Źródło: `5060ti/speed.md`.

| ramię | plain | MTP n=2 | MTP n=3 | ×plain | akcept. n2/n3 | tok/krok n2 | pp4096 | tg128 | tg@16k | VRAM MTP 32k | TTFT 2030 tok |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **U3** | 29.1 | **51.7** | 51.6 | ×1.78 | 0.59 / 0.49 | 2.17 | 1000 | 29.1 | 26.1 | 14.80 GB | 2.77 s |
| I4 | 30.3 | 50.0 | 48.9 | ×1.65 | 0.55 / 0.44 | 2.09 | 986 | 30.4 | 27.1 | 14.10 GB | 2.83 s |
| W4 | 30.3 | 50.0 | 48.8 | ×1.65 | 0.55 / 0.44 | 2.09 | 986 | 30.4 | 27.1 | 14.10 GB | 2.83 s |

- U3 plain 29.1 jest zgodne z raportem 09 (28.9).
- U3 ma wyższą akceptację (0.59 vs 0.55), bo jego trunk jest bliżej BF16 (KLD 0.039 vs 0.073). Odrabia tym przewagę GSQ w czystym dekodzie.
- n=2 ≈ n=3 dla U3, a dla IQ3_S n=2 > n=3.

## 5. Hipotezy, bramki, kill criteria (15e §5)

| | kryterium | wynik | werdykt |
|---|---|---|---|
| H1 | GSQ/Swift `-mtp` z MTP ≥ 1.3 × S0-plain przy KLD ≤ Saluki | W2 25.1 / 17.2 = ×1.46, KLD 0.164 < 0.257 (host A) | **potwierdzona** |
| H2 | Swift: tokeny do odpowiedzi −20%, pass −≤3 pp | −19.3…−19.4% (pary skończone), −29…−32% z ucięciami; pass +5/+10 pp | **na granicy** (efekt ogona) |
| H3 | 16 GB: GSQ IQ3_S gorszy w KLD-PL, szybszy ≤ 10% | KLD-PL I4 1.77 × U3; plain +4%, MTP −3% | **potwierdzona** |
| bramka 12 GB | KLD-wiki ≤ 0.15, PL ≤ 1.3 × wiki, t/s ≥ 1.25 × S0, LT ≤ Saluki | W3: 0.119 / 0.90 / ×1.46 / LT nierozstrzygalne; W2, I2: 0.164 ✗ | **tylko W3** |
| bramka 16 GB | KLD-PL ≤ U3 + 10%, t/s ≥ U3 − 3% | A3: 0.0319 vs 0.0321, te same typy; I4/W4 ✗ | **A3 przechodzi** |
| kill Swift | redukcja < 15% albo pass −5 pp albo akceptacja W < 0.8 × I | 19%, pass bez spadku, akceptacja 1.0–1.04 × I | nie działa (zostaje bramka licencyjna) |
| kill MTP 12 GB | S1 < 1.25 × S0 | ×1.41 (A), ×1.44 (B) | nie działa |
| kill GSQ 16 GB | KLD-PL(I4) > 1.5 × U3 albo zysk t/s < 8% | 1.77× i −3% | **zadziałał**: zostajemy przy U3/A3 |
| kill AP | KLD-PL(A3) ≥ U3 | 0.0319 < 0.0321 (w granicach błędu) | nie działa (remis na PL, wygrana na czacie/kodzie) |
| E3 | akceptacja W2 ≥ 10% niższa niż I2 | 0.55 vs 0.53 (n2), 0.45 vs 0.45 (n3) | **zamknięte**: brak efektu, nic do douczania |

Rekomendacje:
1. **16 GB:**
   - Podmienić U3 → A3 po standardowej bramce na naszym forku: greedy md5 na świeżych serwerach, `kld_gate.py` na czacie PL vs U3, `spec_sweep` ABBA.
   - Zysk to −12% KLD na czacie i −23% na kodzie za te same bajty i tę samą prędkość. To krok z rankingu 15e §4.2 poz. 2.
2. **12 GB:**
   - Kandydatem jest IQ3_XXS-mtp: W3 zmierzony; ISTA IQ3_XXS-mtp (Apache) ma tę samą alokację i wymaga jednego przebiegu KLD + VRAM.
   - Zamiast Saluki (S0/S1): KLD-PL 0.108 vs 0.320, ta sama prędkość z MTP.
   - VRAM 11.54 GB przy 16k jest na granicy 12 GB. Przy 32k się nie zmieści `[INFERENCE: +KV ~0.6 GB]`.
3. **Swift jako tryb „mniej zapętleń”:**
   - Technicznie przechodzi (W4: 0 ucięć, pass 1.00, −29% tokenów).
   - Decyzja należy do użytkownika ze względu na licencję Swift OL 1.0 (< $1M przychodu rocznie).

## 6. Wyniki negatywne i zastrzeżenia
- MTP na 2-bitowych IQ na 3060 daje ×1.41–1.53, a nie ×1.61 jak u społeczności na 3080. n=3 jest zawsze gorsze od n=2, bo przy kwantach IQ weryfikacja trzech tokenów kosztuje (ms/krok rośnie).
- Zestaw 20 zadań nie rozróżnia kwantów o KLD 0.16–0.35: Bonsai 0.95, Saluki 0.85. Do decyzji używać KLD, zadań tylko do zachowania myślenia (długość, zapętlenia).
- LanguageTool na ~550 słowach/ramię to szum (2–7 dopasowań).
- Seed 1 zadań W2/I2/W4/I4/S0 policzył A40, seed 2 RTX 5090 (inna arytmetyka). Każda para W–I dzieli kartę w obrębie seeda.
- Host 3060 A miał limit mocy 120 W. Wartości bezwzględne z §4.1 nie nadają się do kart produktu, tylko do porównań między ramionami.
- KLD liczone na 20 chunkach, a nie na 32 jak w 15e. Błędy standardowe w tabeli; ranking ramion jest stabilny poza parami A3/U3 (wiki, PL) i W2/I2 (wiki).

## 7. Incydenty (lekcje operacyjne)
1. Bootstrap na wynajętej karcie (budowa forka + Prism na 9 vCPU) trwał ~25 min przy GPU 0%. Watchdog rodzica słusznie zgłosił „idle”. **Następnym razem: zbudować binarki sm_86/sm_120 lokalnie (RPATH `$ORIGIN`, jak w raporcie 14) i wypchnąć je przed wynajmem.**
2. `pq2_to_q2.py` wymaga `python3-numpy`, którego nie ma w obrazie CUDA ani w `bootstrap.sh`. Repack Bonsai padł dwa razy (runda 1 na 3060 A, runda 2 na 3060 B) i stracił ~2 min GPU.
3. cgroup v1 na hoście B: `cpu.max` nie istnieje, więc `nproc` = 80. Poprawione w `e2.sh` (odczyt `cfs_quota_us`), dało `-t 9`.
4. Osierocony `llama-server` (Saluki, `-np 20`) po zabiciu skryptu trzymał 18 GB na A40, przez co dwa serwery zadań (U3, B0) dostały OOM. Kill skryptu musi zabijać też serwer (`pkill -9 -f "llama-server.*<port>"`).
5. `pkill -f "<wzorzec>"` wysłany przez ssh zabija własną powłokę ssh, jeśli wzorzec występuje w linii komend. Przez to rozbroił się samozniszczenie na 3060 B (uzbrojone ponownie). Na zdalnej maszynie używać skryptu z pliku.
6. Pierwszy 5060 Ti (Vast, EPYC 7R32) ściągał z HF 1 MB/s. Usunięty po ~55 min, zamieniony na inny host: 12 MB/s → ok.
7. **Nadpisanie danych raportu 09:** po awarii omp collect instancji 3060 A zsynchronizował `/root/results/3060-20261016/` do lokalnego `results/3060-20261016/` (ta sama nazwa co run raportu 09).
   - Pliki `hw/*` i część `build/*` raportu 09 zostały zastąpione danymi hosta A.
   - Moje dane przeniosłem do `quantkld-20261016/3060-hostA/`, a opis szkody zostawiłem w `results/3060-20261016/NOTE-quantkld-overwrite.txt`.
   - **Lekcja:** katalog wyników na instancji musi mieć unikalną nazwę (etykieta instancji), nie `<klasa>-<data>`.

## 8. Koszty
| runda | Vast | RunPod |
|---|---|---|
| 1 (2026-10-16) | ≈ $0.75: 3060 A ~2.75 h × $0.105, 5060 Ti #1 ~0.9 h × $0.153, 5060 Ti #2 ~1.5 h × $0.217 `[SZACUNEK z czasów życia]` | $1.87 (A40, saldo 4.01 → 2.14) |
| 2 (2026-10-18) | ≈ $0.91: RTX 5090 1.1 h × $0.736, 3060 B 0.9 h × $0.11 `[SZACUNEK z czasów życia]` | $0.57 (A6000, saldo 2.14 → 1.57 po rozliczeniu) |

- Limity: runda 1 ≤ $1.40 Vast / $2.30 RunPod; runda 2 ≤ $1.50 Vast / $1.70 RunPod. Oba dotrzymane.
- Saldo Vast jest wspólne z innymi agentami, więc spadek kredytu nie równa się moim wydatkom.

## 9. Instancje (wszystkie usunięte)
- **Runda 1:**
  - Vast 56261367 (3060 A) usunął rodzic po awarii;
  - Vast 56261556 (5060 Ti #1) i 56267872 (5060 Ti #2) usunąłem sam;
  - RunPod `8vmy4do772t7s9` (A40) usunął rodzic.
- **Runda 2:**
  - Vast 56603490 (RTX 5090), usunięty 20:07;
  - Vast 56603675 (3060 B), usunięty 19:55;
  - RunPod `3sxmy94b4188c3` (A6000), zakończony 20:00.
- Lokalne watchdogi i timery systemd zatrzymane. `vastai show instances` nie zwraca żadnej etykiety `quantkld-*`; RunPod `pods: []`.

## 10. Pliki
- KLD: `quantkld-20261016/kld-all/` (wszystkie logi + `kld.json`, `kld.md`), z rund `pod-final/res/` (runda 1) i `pod-r3/res/` (runda 2).
- Zadania: `pod-final/res/tasks/` (seed 1, A40), `5090-tasks/tasks/` (reszta), podsumowanie `tasks-all/tasks-report.json`, `tasks-all/lt.json`.
- Prędkość: `3060-hostA/` (+ `speed.md`), `3060-hostB/`, `5060ti/`.
- Kod forka bez zmian. Eksperyment nie modyfikował silnika, więc nie ma commita z przełącznikiem. Skrypty w `~/qwen-opt/quantkld/` i `~/qwen-opt/cloud/runs/quantkld/` (`~/qwen-opt` nie jest repozytorium git).

## Do bazy wiedzy
- **eksperymenty / „2026-10-18-e1-kwanty-27b-kld”** (nowa):
  - KLD do Qwen BF16 (wiki / PL proza / czat / kod / long): U3 0.039/0.032/0.064/0.032/0.040; A3 0.040/0.032/0.056/0.025/0.038; I4 0.073/0.057; W4 0.076/0.055; W3 0.119/0.108; W2 0.164/0.142; I2 0.164/0.155; W1 0.218/0.235; Saluki 0.257/0.320; Bonsai 0.352/0.508.
  - Źródło: `~/qwen-opt/cloud/results/quantkld-20261016/kld-all/kld.md:9-24`; ten raport §2.1.
- **decyzje / „16 GB: AP-Q3_K_XL zamiast UD-Q3_K_XL (do bramki)”**:
  - te same typy (0/866 różnic), KLD czat −12%, kod −23%, PL remis;
  - GSQ IQ3_S odrzucony (KLD-PL 1.77 × U3, MTP −3%).
  - Źródło: raport §2.1, §4.3, §5; `5060ti/speed.md:3-5`.
- **modele / Swift 1.5** (aktualizacja):
  - Swift-Q8 do Qwen-Q8 KLD 0.0082 wiki / 0.0019 PL (podłoga Q8 0.0038/0.0006), czyli na tekście ≈ Qwen;
  - −19% tokenów w zadaniach przez mniej zapętleń (mediana bez zmian);
  - akceptacja MTP = ISTA (0.55 vs 0.53/0.55).
  - Źródło: `pod-final/res/kld/qq8.SQ8.*.log`, `tasks-all/tasks-report.json`, `3060-hostA/speed.md:3-7`.
- **karty / RTX 3060** (aktualizacja):
  - Saluki+MTP (Kujira) 23.0 → 33.1 t/s (×1.44, n=2);
  - Bonsai PTQ1_0 Prism 44.9, Q2_0 nasz 35.1 (host z 09, powtórzone);
  - GSQ/Swift IQ2–IQ3_XXS-mtp ×1.49–1.53 (host 120 W);
  - W3 VRAM 11.54 GB @16k.
  - Źródło: `3060-hostB/speed.md:3-5`, `3060-hostA/speed.md:3-8`.
- **karty / RTX 5060 Ti** (aktualizacja): U3 MTP 51.7 vs I4/W4 50.0 t/s, plain 29.1 vs 30.3. Źródło: `5060ti/speed.md:3-5`.
- **metody / KLD na PL** (nowa lub do istniejącej o KLD):
  - korpusy PL (FineWeb-2 seed 0, czat teacher-forced, „Lalka” 2×16k) z md5 jak w §1.2;
  - Saluki/Bonsai tracą więcej na PL (PL/wiki 1.24/1.44), GSQ/UD mniej (0.73–0.95);
  - long/PL 1.08–1.25, bez skoku.
- **lekcje** (nowe):
  - (a) binarki budować lokalnie przed wynajmem (25 min GPU idle);
  - (b) `bootstrap.sh` bez `python3-numpy` psuje repack Bonsai;
  - (c) cgroup v1: `cpu.max` brak, czytać `cfs_quota_us`;
  - (d) zabicie skryptu ≠ zabicie serwera (OOM od sieroty);
  - (e) `pkill -f` przez ssh zabija własną sesję;
  - (f) wynik na instancji pod nazwą `<klasa>-<data>` nadpisał lokalne dane raportu 09 (`results/3060-20261016/NOTE-quantkld-overwrite.txt`);
  - (g) host Vast z kartą przyciętą do 120 W (3060): sprawdzać `power.limit` w `hw/gpu.csv` przed porównaniem z innymi hostami.
- **chmura** (aktualizacja):
  - zadania z myśleniem na RTX 5090 trwają 2.5–5 min na ramię-seed (20 slotów), a na A40 13–25 min, więc 5090 jest tańszy na przebieg;
  - BF16 27B na 48 GB z `-fit on` daje bazę 54–240 s na korpus.
