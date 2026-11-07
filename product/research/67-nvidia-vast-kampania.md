# 67: Kampania NVIDIA na Vast (Enigma) — wyniki i finalne zestawy (2026-11-07)

**W trzech godzinach na 17 wynajętych kartach zmierzyliśmy konfiguracje CUDA od 2080 Ti do 5090. Na 24 GB pełny kontekst 262 144 z MTP działa i daje +67,6% na 4090 i +44,7% na 5090; na 16 GB warianty 27B z MTP wywalają się przy pierwszym długim prompcie, więc Enigma potrzebuje zapasu ≥0,7 GiB ponad to, co widać po załadowaniu. Kampania zatrzymana przez użytkownika po wydaniu $3,47 z $10,51; zero maszyn zostało w chmurze.**

Wszystkie liczby: mediana `spec_sweep` (6 promptów PL/EN × seedy 1–3, T=1), silnik upstream b11856 (pin Enigmy) i b12110, KV q4_0, `-fa` włączone. „P0” = dokładnie to, co Enigma uruchamia dziś (bez spekulacji), „P4” = dzisiejszy kandydat Enigmy (MTP n=4), „N{n}u” = MTP n z `--spec-draft-n-ubatch 64`.

## 1. Finalne zestawy per klasa (stan wiedzy po kampanii)

| Klasa | Karta | Model, kwant | ctx | MTP | Wynik: dziś → teraz | Weryfikacja |
|---|---|---|---|---|---|---|
| 32 GB | 5090 | Qwen3.8-27B **UD-Q6_K** | **262 144** | n=2 | 60,0 → **86,9 t/s** (+44,7%) | fill 261 504 tok. OK (dec 14,3 → 49,9), soak OK, szczyt 28 446/32 109 MiB |
| 32 GB | 5090 | **Qwen3.6-35B-A3B** Q5_K_XL (MoE) | **262 144** | n=2 | 244,6 → **319,5 t/s** (+30,6%) | fill 261 504 tok. przy prefillu 3 060 t/s, dec 145,5, soak OK |
| 24 GB | 4090 | Qwen3.8-27B **UD-Q4_K_XL** | **262 144** | n=3, ub 256 | 47,2 → **79,1 t/s** (+67,6%) | fill 261 504 tok. OK (dec 25,9 → 47,3), soak OK, szczyt 24 036/24 082 MiB |
| 24 GB | 4090 | Qwen3.8-27B **UD-Q4_K_M** | **262 144** | n=2–4, ub 512 | 49,8 → **78,0–79,5 t/s** (+57–59%) | load 23 598 MiB, 1,1 GiB zapasu |
| 24 GB | 3090 | Qwen3.8-27B UD-Q4_K_XL | 245 760 (model) / 262 144 (zmierzone na 4090) | n=3, ub 256 | ~47 → ~79 t/s `[INFERENCE]` | 3090 z ramieniem forka nie zdążyła (host padł) |
| 16 GB | 5080 | **ISTA GSQ IQ3_XXS-mtp** | **208 896** | bez MTP | 62,7 (pin) → 63,0–63,8 (b12110) | fill 208k? nie zmierzony na 5080; IQ3_XXS na 5060Ti/4060Ti fill OK |
| 16 GB | 5060 Ti | ISTA GSQ IQ3_XXS-mtp | **200 704** | bez MTP | 33,3 | fill 200 064 tok. OK, prefill 470 t/s |
| 16 GB | 4060 Ti | ISTA GSQ IQ3_XXS-mtp | **217 088** | bez MTP | 23,7 | fill 216 448 tok. OK, prefill 259 t/s |
| 12 GB | 4070 | **Underdog Saluki 27B + MTP** | **151 552** | n=1 | 39,8 | fill 135 168 i **151 552** OK, dec 17,9/16,8, soak OK |
| 12 GB | 3060 (105 W) | Saluki-MTP | 135 168 | n=1 | 19,6 | tylko pomiar prędkości |
| 10 GB | 3080 | **LFM2.5-24B Q4_K_M**, KV q8_0, `--n-cpu-moe` | 131 072 (limit modelu) | brak draftera | 20,1 → 20,4 | pomiar ABBA |
| 8 GB | 3070 | LFM2.5-24B Q4_K_M, KV q8_0, eksperci w RAM | 131 072 | brak | 7,1 | – |

**MTP n per model:** 27B na 24 GB → **n=3** (4090: n1 67,0 / n2 76,8 / n3 79,1); 27B na 32 GB → **n=2** (n1 80,6 / n2 86,8 / n3 83,8 / n4 79,5). Dziś Enigma ma sztywne n=4. Na 16 GB MTP z 27B nie wchodzi (patrz §3).

## 2. Co dała zmiana silnika (b11856 → b12110)

| Karta | P0 b11856 | N0 b12110 | Δ |
|---|---:|---:|---:|
| 3060 | 35,24 | 35,31 | +0,2% |
| 3070 (Qwen3.5-9B) | 32,69 | 30,11 | **−8%** (prefill 1 809 → 1 618 t/s) |
| 3080 | 67,98 | 69,29 | +1,9% |
| 4070 | 52,22 | 52,83 | +1,2% |
| 4090 | 46,87 | 47,10 | +0,5% |
| 5060 Ti | 28,74 | 28,78 | +0,1% |
| 5080 | 55,00 | 55,35 | +0,6% |
| 5090 | 60,18 | 60,17 | 0% |

ABBA na 5060 Ti (28,74/28,80) i 5080 (55,0/55,4) potwierdza szum. **md5 greedy zmienia się między buildami**, więc to inna ścieżka liczenia, nie błąd — adoptujemy b12110 dla całej linii poza 3070 `[do decyzji: 3070 zostaje na pinie albo b12110 z −8%]`.

## 3. Znaleziony błąd: zapas na pierwszy długi prompt na kartach 16 GB

Zmierzone: 27B UD-Q3_K_XL + MTP przy 135 168 i 131 072 nie ładuje się na 5060 Ti / 5080 / 4060 Ti pod żadnym wariantem (brakuje 0,5–1 GiB). ISTA IQ3_XXS-mtp **ładuje się** przy 200–217k z 0,5–0,66 GiB wolnego po `nvidia-smi`, a potem **wywala się przy pierwszym prefillu 4 096 tokenów** (`launch_mul_mat_q`, doładowanie kerneli CUDA). Wniosek: planer musi zostawiać **≥0,7 GiB ponad załadowany model**; dodatkowo limit to suma CUDA, nie `nvidia-smi` (5090 32 109, 4090 24 082, 3090 24 126, 4060 Ti 15 947 MiB).

**Poprawki w Enigmie (commit w tym samym dniu):**
- `memory.ts`: model pamięci upstream MTP (stan × (n+1): 299/598/748 MiB dla n 1/3/4; KV draftu w f16 = 1024 MiB przy 262k; compute draftu z `--spec-draft-n-ubatch`; bez wzrostu forka),
- `optimize.ts`: `--spec-draft-n-max` z klasy karty (domyślnie 3) + `--spec-draft-n-ubatch 64`, batch 256 w kandydatach,
- `catalog/index.ts`: dokładny zmierzony odstęp `nvidia-smi` → CUDA per karta (2080 Ti 447 … 5090 498 MiB), dodatkowy zapas 300 MiB na doładowanie kerneli, oraz „zmierzone plany” (4090 linux 262 144 ub 256, 4090 Q4_K_M 262 144 ub 512, 5090 262 144), których estymata nie może odrzucić.
- Efekt w planerze: 4090 262 144 (było 152–160k), 5090 262 144, 3090 245 760.

## 4. Parametry, które nic nie dają (wyniki negatywne)

| Test | Wynik |
|---|---|
| próg pewności draftu `p-min` 0,5 / 0,8 | gorzej wszędzie, gdzie zmierzono: 16 GB MoE 5080 83,4 → (n1p5 80,9, n1p8 76,4); 3080 Gemma 120,2 → 113,5 / 109,9; 4070 Gemma 101,5 → 101,3 / 96,4 |
| `-ctkd q4_0` bez portu lean | +0,9–1,5 GiB kopii f16 (dzisiejszy upstream i tak trzyma KV draftu w f16) |
| rezerwa draftu rośnie z ctx×ub | 648 MiB przy 262k / ub 1024 → `--spec-draft-n-ubatch 64` zbija do 40 MiB, wyjście bez zmian |

## 5. Co się nie udało zmierzyć (do wznowienia)

- **Bonsai 2 27B**: silnik PrismML (paczka CUDA `prism-b12128`), plik PTQ1_0 i skrypt doszczepiający głowicę MTP są gotowe, ale **nie ruszyły na karcie** (agent przerwany limitem API). Nasz stary pomiar 44,9 t/s (3060, build `prism-b10777`) wciąż jest jedynym.
- **3090 + fork cuda-topka2** (raport 27: 93,3 t/s przy T=1) — host padł przed testem; to jedyna ścieżka do wyższego t/s niż 79 na 4090.
- **kernel `kvq` na CUDA** (`~/wt/nv-4060ti-kvq @ 007a6f813`, `GGML_CUDA_KVQ=1`): wcześniejsze +25–37% przy 64k; build pod sm_89/sm_120 nie zdążył.
- **port lean** (`b12110-lean`, commit 55933253f, patch `patches/nv67-lean-reserve/`) — zbudowany, nieuruchomiony; obiecuje −1,3 GiB + KV draftu 1024→288 MiB, czyli 262k na 16 GB.
- **Gemma 4 12B** — model odrzucony przez użytkownika; pomiary zostają w danych jako punkt odniesienia (4070 262 144: 52,2 → 101,5 t/s przy n4; 3060 105 W: 35,2 → 55,5).
- 2080 Ti: wynajęty host miał obcy proces 2,2–7 GB na karcie (monitor), więc wszystkie konkurencje pamięci padły; potrzebny host bez pulpitów.

## 6. Koszt

Kredyt na start (2026-11-06): **$10,51** → po kampanii **$7,04**, czyli **$3,47** na 17 maszyn (od $0,056 do $0,24/h; najdroższe 4090 $0,46/h i 5090 $0,48/h). Wszystkie maszyny skasowane, `vastai show instances` = 0. Wyniki: `~/qwen-opt/cloud/results/nv67-*/`, logi i komendy: `~/KERNEL/qwen-opt/cloud/nv67/`.

## Powiązane
- [[raport-67b-wybor-modeli-nvidia]]
- [[raport-67c-nvidia-backlog-testow]]
- [[raport-27-3090-final]], [[raport-56-orca-3090]], [[raport-29-4060ti]]
- [[2026-11-07-kampania-nvidia-vast]]
