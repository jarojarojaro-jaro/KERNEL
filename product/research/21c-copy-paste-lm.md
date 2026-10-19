# 21c: Copy-Paste Language Models (CPLM): czy to coś dla nas?

Autor: agent ResCopyPaste, 2026-10-19. Źródło główne: Godey & Artzi, *Copy-Paste Language Models*, arXiv:2610.19247v1, 13.10.2026 (https://arxiv.org/abs/2610.19247, pełny tekst: https://arxiv.org/html/2610.19247). Przeczytałem cały tekst z dodatkami A–H oraz PR do NanoGPT speedrun (https://github.com/KellerJordan/modded-nanogpt/pull/379). Wszystkie pomiary własne robiłem wyłącznie na CPU (`nice -n 19`). Skrypty i wyniki są w `~/KERNEL/product/research/21c-cplm/`.

## 0. Najważniejsze

1. **CPLM to nowa architektura wyjścia trenowana od pretrainingu, a nie optymalizacja inferencji.** Obok LM head dochodzi „Copy-Paste head”: pointer, czyli atencja z jednym zapytaniem po stanach ukrytych wcześniejszych pozycji. Do tego token bramki `<copy>` w słowniku i klucz `<sink>`. Model trenuje się od zera albo co najmniej z odblokowanym gradientem do backbone'u. Autorzy sami pokazują, że ~75% zysku daje gradient płynący przez CP head do backbone'u w czasie pretrainingu, a nie sama głowica na wyjściu: stop-gradient zostawia 0.008 z 0.031 nat (§H.1, Tab. 15). Doklejony bez treningu neural cache daje 0.00 PPL (§C.7, Tab. 9). **Dla Qwen3.8-27B i LFM2.5 nie możemy tego zastosować.**
2. **„Mitigates the LM head bottleneck” dotyczy treningu, nie szybkości dekodowania.** Chodzi o to, że gradient z V-wymiarowych logitów jest ściskany do D wymiarów i tracone jest >99% normy (§4.1, Fig. 6), oraz o niski rząd softmaksu. CPLM **dokłada** pracę przy dekodowaniu, bo pełny LM head nadal trzeba policzyć, a bramka `<copy>` pochodzi z jego softmaksu. Krok dekodowania jest wolniejszy o 1.0–3.8% (Tab. 6). U nas LM head to 1.043 GB z 16.83 GB czytanych na krok (6.2%). Tego CPLM nie zmniejsza, a nasz słownik draftu 64k jest ortogonalny.
3. **Twierdzenie „<3% narzutu” jest prawdziwe tylko dla przepustowości treningu przy 1.7B** (×0.969). Krok dekodowania traci do 3.8% (9B, B=128), pamięć treningu rośnie o 9.6% (1.7B). Wyniki jakościowe są rzetelne przy 135M (3 seedy), ale od 1.7B w górę mają jeden seed i skromny efekt. Średnia zero-shot poprawia się o +0.37…+0.84 pkt, z czego większość daje LAMBADA. Bez LAMBADA zostaje +0.30 / +0.33 / −0.10. Wyniki są dobre tam, gdzie backbone nie widzi kontekstu (SW-256, needle 14.3 → 99.4). Modele 9B i 30B były tylko nietrenowanymi atrapami do pomiaru czasu.
4. **Związek z naszym lookup tail:** to ta sama intuicja, czyli wskazać pozycję w kontekście i skopiować to, co po niej nastąpiło. CPLM kopiuje jednak tylko 1 token na krok, a my kopiujemy spany do 15 tokenów i weryfikujemy je bezstratnie. Czy pointer pomógłby nam jako drafter? Policzyłem na CPU wyrocznię dla „idealnego pointera” na naszym lookupie. Na czacie sufit wynosi +0.3…+1.0% t/s. Na wyjściach agenta wynosi +3.8% (idealny wybór wśród kandydatów 4-gram) albo +5.5% (start już od dopasowania 2-gram).
5. **Gdzie jest zysk bez trenowania czegokolwiek:** regułę „wybierz kandydata, którego kontynuacja zgadza się z 4 draftami MTP” (AGR2, opis w §5.2) można wdrożyć od ręki. W modelu daje **+3.7% t/s na agencie** (2/3 sufitu wyroczni) i +0.6% na czacie. Wyuczony pointer mógłby dołożyć najwyżej ~1.8 pp, więc go nie trenujemy. **Rekomendacja: nie adoptujemy CPLM. Robimy mały eksperyment AGR2 w `common_spec_lookup` z progiem kill (§6).** Drugi, słabszy pomysł to słownik draftu „64k ∪ tokeny kontekstu”, z sufitem +0.8…+1.7% tok/krok.

## 1. Co to jest, prostymi słowami

- Zwykły LM: stan ukryty h_t (wymiar D) mnożymy przez macierz LM head W (V×D), robimy softmax po V tokenach i dostajemy p_LM.
- CPLM dokłada drugą głowicę, która pokazuje palcem miejsce w kontekście (§2.2, równania 2–3):
  - q_t = W_Q h_t, k_τ = W_K h_τ (każde D×D);
  - α_t(τ) = softmax po pozycjach τ ≤ t;
  - p_CP(v) = Σ α_t(τ) po pozycjach, na których stoi token v.
- O tym, czy kopiować, decyduje dodatkowy token `<copy>` w LM head: c_t to jego prawdopodobieństwo (równanie 4).
- Gdy w kontekście nie ma czego kopiować, `<sink>` w softmaksie pointera oddaje masę LM head: s_t (równanie 6).
- Wynik to mieszanka p = (1−λ)·p_LM + λ·p_CP, gdzie λ = c_t(1−s_t) (równanie 7). Trening to zwykła cross-entropy, bez pomocniczej straty.
- Narzut parametrów: 2·D² + D. Przy 1.7B to 0.5% (App. B). Dla Qwena (D=5120) wyszłoby 52.4 M parametrów, czyli 0.19% z 27.32 B [arytmetyka własna].
- Przy inferencji trzeba cache'ować jeden klucz kopii na token, obok KV (App. B, „Inference”).
- **Rodzaj pracy:** zmiana architektury i rekomendacja do pretrainingu. Wszystkie wyniki pochodzą z modeli trenowanych od zera: 135M–1.7B, do 200B tokenów FineWeb-Edu, przepis SmolLM2 (§3.1, Tab. 4). Fine-tuning SFT i HotpotQA zawsze startuje z CPLM-owego base (§3.2, §3.4). Autorzy nie dodali nigdzie CP head do istniejącego, wytrenowanego modelu. Takie podejście (Chang et al. 2023) omawiają tylko w Related Work i oceniają jako słabsze (Tab. 8: partycje CP 16.19 vs CPLM 15.85 PPL przy 135M).

## 2. „LM head bottleneck”: co to znaczy i czy przyspiesza dekodowanie

### 2.1 Znaczenie w pracy

- **Wąskie gardło gradientu** (Godey & Artzi 2026, cytowane w §2.1 i §4.1): w backward gradient po V logitach rzutuje się przez Wᵀ do D wymiarów. Jeśli V ≫ D, ginie >99% normy (§4.1, Fig. 6 lewy).
- Ścieżka CP head ma macierz t×D zamiast V×D. Przy t ≪ V zachowuje do 85% normy na wczesnych pozycjach (§4.1).
- **Softmax bottleneck** (ekspresywność): niski rząd W ogranicza możliwe rozkłady (§2.1).
- Dowody, że zysk naprawdę pochodzi z gradientu:
  - stop-gradient zostawia ~25% efektu (§H.1, Tab. 15: −0.031 vs −0.008 nat);
  - na modelu bajtowym (V=257 < D=576) CPLM daje 0 (§H.2, Tab. 16: 0.6918 vs 0.6908 nat/bajt);
  - na zadaniu syntetycznym SpamLang vanilla przy V=512k ma 34% trafień, CPLM rozwiązuje je przy każdym V (§4.1).
- **Wniosek:** „mitigates” znaczy „lepiej uczy backbone”. Nie znaczy „liczy LM head taniej”.

### 2.2 Bajty i FLOP-y LM head u nas

Dane z nagłówka GGUF (`python3 15a-ggufls.py ~/models/Qwen3.8-27B-UD-Q4_K_XL.gguf`, wynik z 2026-10-19):

| tensor | typ | kształt | MB |
|---|---|---|---|
| `output.weight` (LM head) | Q6_K | 5120 × 248 320 | **1042.94** |
| `token_embd.weight` | Q4_K | 5120 × 248 320 | 715.16 (get_rows, nie czytamy całości) |

- Parametry LM head: 5120 × 248 320 = 1.271 G, czyli 4.65% z 27.32 B.
- Krok czyta 16.83 GB aktywnych bajtów (`15a-monokernel.md:154`). LM head to **6.2%**.
- Przy 960 GB/s czytanie trwa 1.09 ms, przy realnych ~850 GB/s 1.23 ms. Krok MTP4 ma 27.74 ms (wiki `modele/qwen3-8-27b.md`), więc LM head to ~4% czasu kroku.
- Obliczenia: 2 × 1.27 G = 2.5 GFLOP na wiersz. Przy 5 wierszach weryfikacji to 12.7 GFLOP, czyli pomijalnie mało, bo krok jest ograniczony pasmem.
- LFM2.5-24B-A2B: tied head Q6_K ma 215.0 MB z 1.777 GB/token, czyli **12.1%** (`15a-monokernel.md:121`). Tu LM head jest wyraźniejszym kosztem niż w Qwenie, ale CPLM tego nie zmienia.
- **Nasz trik 64k** (łatka 0004, `latki/latki-spekulacji.md`; wynik +7.5% t/s): głowica draftu liczy tylko 65 536 najczęstszych tokenów.
  - W IQ4_XS to 65 536 × 5120 × 136/256 B = **178 MB** na przebieg draftu.
  - Pełny słownik w IQ4_XS: 675 MB. Natywny Q6_K: 1043 MB.
  - To skraca *nasz* koszt LM head. CPLM idzie w przeciwną stronę: wymaga pełnego p_LM (bramka c_t to softmax po V ∪ {`<copy>`}).
- Jedyna „oszczędność” w CPLM: przy greedy można pominąć **atencję kopii** (nie LM head), gdy (1−c_t)(p1−p2) ≥ c_t (§C.6, „Remark on decoding cost”).
- **Odpowiedź: CPLM nie przyspiesza dekodowania. Spowalnia je o 1–4%.**

### 2.3 Narzut CPLM, gdyby Qwen go miał [arytmetyka własna]

- Cache kopii przy D=5120 w f16 zajmuje 10 240 B/token. Nasze KV Qwena (16 warstw atencji × 1024 × K,V) to 18 432 B/token w q4_0 albo 65 536 B/token w f16. Przy q4_0 cache kopii to **+56% KV**, bo hybryda GDN ma już małe KV.
- Przy 64k kontekstu dekodowanie czytałoby dodatkowo 671 MB, czyli +4.0% bajtów kroku.
- Autorzy pokazują jednak, że wymiar kopii 64 daje tę samą PPL (±0.02 przy 135M, §C.2). PR do speedrunu używa d=128. Przy d=64 i f16 to 128 B/token, czyli pomijalnie mało.
- Wpływ na sesję SSD E5 (16f): 53k tokenów × 10 KB = +0.54 GB do 2.28 GiB przy D=5120, albo +6.8 MB przy d=64.

## 3. Weryfikacja twierdzeń

| twierdzenie | co faktycznie zmierzono | werdykt |
|---|---|---|
| „negligible … overheads (<3%)” | Trening (B300, seq 4096): 1.7B ×0.969, 9B ×1.005, 30B ×0.991; pamięć ×1.096 / ×1.026 / ×1.017 (Tab. 5). Inferencja (B300, bf16, FlexAttention, CUDA graph, greedy 256 tok.): krok dekodowania ×1.018 (1.7B, 4k, B=1), ×1.017 (B=128), ×1.018 (16k, B=32), ×1.010 (9B, B=1), **×1.038** (9B, B=128), ×1.027 (9B, 16k); prefill ±1.3% (Tab. 6). | **Częściowo.** „3%” to przepustowość treningu 1.7B. Dekodowanie do 3.8%, pamięć treningu +9.6%. Modele 9B/30B to „untrained architectures” (App. B). |
| „extra time is essentially that of reading the cached copy keys” (App. B) | Przy B=1 cache kopii ma 0.02 GB wobec ~3.4 GB wag + 0.80 GB KV, więc bajty dają ~0.5%. Zmierzono 1.8%. Przy 9B: 0.03 GB wobec ~18.5 GB, czyli ~0.16%, a zmierzono 1.0%. | **Wątpliwe przy B=1.** Narzut to stały koszt dodatkowych kerneli, nie pasmo. U nas (ROCm, ~3.2 µs przerwy na kernel, `NOTES.md` „Kolejne kroki”) byłoby podobnie. |
| PPL lepsza na każdej skali i backbonie | 135M: 3 seedy, Δ −0.50/−0.87/−0.52 PPL przy std 0.02–0.04 (Tab. 7). 360M i 1.7B: jeden seed. | **Wiarygodne** przy 135M. Przy 1.7B kierunek ten sam, ale bez wariancji. |
| zero-shot +0.4–0.9 pkt (Tab. 1) | Średnie Δ: Full +0.61, SW +0.84, Hybrid +0.37. Bez LAMBADA: +0.30, +0.33, −0.10. Hybrid ARC-e −2.86. | **Efekt mały i niemal w całości z LAMBADA**, czyli zadania, w którym kopiuje się słowo z kontekstu. Nie jest to ogólny wzrost „inteligencji”. |
| 1.25× / 2× szybsza zbieżność | Krzywe walidacji „before LR decay” (Fig. 2). 2× dotyczy SW-256, gdzie vanilla nie widzi dalej niż 256 tokenów. | **Prawdopodobne dla Full/Hybrid (1.25×).** 2× to porównanie z kalekim baseline'em. Brak pomiaru po decay. |
| SFT +1.2–5.1 pkt średnio (Tab. 2) | pass@4 z 8 próbek (MATH lvl 1–2, n=861; GSM8K n=1319), pass@10 z 20 (HumanEval n=164, MBPP), IFEval. Δ Full: +3.6/+4.2/+0.7/+0.6/+1.8; Hybrid MBPP −1.6. | **GSM8K i MATH wiarygodne** (SE ~1.2–1.3 pp, Δ ~3σ). **HumanEval +0.7 to szum** (SE ~3.1 pp). Jeden seed. |
| long context +7.5 (synt.) / +4.1 (LongBench) | Bazowe modele 1.7B. Średnie LongBench 7–14 pkt, czyli blisko podłogi. Zysk głównie z TREC (+16/+29/+24.5, kopiowanie etykiet z demonstracji) oraz LCC/RepoBench (kod). Po SFT Δ maleje do +0.6/+2.7/+1.9, a TREC Full spada z 15.5 na 8.0 (Tab. 10, 11). Full po obu stronach pada od 16k: „CPLM does not move the failure point” (App. E). | **Wynik prawdziwy, ale dotyczy kopiowania**, a przy Full/Hybrid po SFT jest mały. |
| SW CPLM = Full przy 12× mniejszej pamięci | Przy 4k: KV Full 0.80 GB, SW-256 KV ≈ 0.80·256/4096 + cache kopii 0.02 GB, czyli ≈ 0.07 GB. Iloraz ×11.4 [arytmetyka własna] ≈ 12×. | **Arytmetyka się zgadza.** Iloraz rośnie z kontekstem. |
| needle: SW 14.3 → 99.4 | SW vanilla fizycznie nie widzi poza oknem (App. E). | **Prawdziwe, ale baseline jest z definicji ślepy.** Ciekawe głównie dla architektur SW/GDN. |
| NanoGPT speedrun −11.3% | PR #379: 36.009 ± 0.039 s vs 40.575 ± 0.024 s na tym samym węźle, 8 vs 13 runów, liczba kroków dobrana na tym węźle (ujawnione). PR ma status **open**. | **Uczciwie opisane, ale rekord nie jest jeszcze przyjęty** („improve on the prior record” w §1 wyprzedza merge). PR podaje też, że bez RMSNorm na q/k „pointer logits blow up on some seeds”. Tej informacji w pracy brakuje. |
| GDN też zyskuje (§C.5) | 135M, a GDN ma ~20% więcej parametrów niż arm atencji (autorzy sami to zaznaczają). | **Kierunek pozytywny dla hybryd GDN (jak Qwen3.8)**, ale tylko przy 135M i bez dopasowania parametrów. |

Czego brakuje:
- skali > 1.7B z treningiem;
- porównania z vanilla trenowanym na tylu tokenach, ile CPLM zaoszczędził;
- pomiaru na modelu z dużym słownikiem i dużym D. Qwen3.8 ma V/D = 248 320/5120 = 48.5, a ich 1.7B ma 24, 135M ma 85. Teoria wąskiego gardła mówi, że liczy się właśnie V/D, więc efekt „może” utrzymać się przy dużych modelach, ale nikt tego nie sprawdził.

## 4. Czy da się dodać copy head bez retreningu celu

### 4.1 Jako część rozkładu celu (zmiana p): nie

- Mieszanka zmienia rozkład modelu, więc nie jest bezstratna względem naszego Qwena.
- Zysk wymaga treningu backbone'u (§H.1).
- Autorzy dostroili neural cache (Grave 2017) na vanilla 1.7B i dostali optymalne γ ≤ 0.002, czyli PPL 9.17 → 9.17 (§C.7, Tab. 9).
- Wniosek: doklejony bez treningu pointer na wyjściu nie poprawia nawet jakości, a szybkości z definicji też nie.

### 4.2 Jako drafter: tak, ale z małym sufitem

- W spekulacji rozkład celu się nie zmienia: pointer tylko *proponuje* tokeny, a weryfikacja zostaje bez zmian, więc całość jest bezstratna.
- Dokładnie to robi nasz lookup tail (16b): sufiks 4–12 tokenów, do 64 kandydatów, przy remisie najnowszy. Ogon do W16 dokleja się, gdy wszystkie 4 drafty MTP równają się pierwszym tokenom lookupu przy dopasowaniu ≥ 6 (`16b-lookup-tail.md:27,32`).
- Różnice względem CPLM:
  - CPLM wskazuje *pozycję* wyuczonym zapytaniem i kopiuje 1 token. Rozszerzenie na spany to dopiero „future work” (§6 pracy).
  - Lookup wybiera pozycję regułą n-gramową, ale kopiuje span do 15 tokenów.
  - Wyuczony pointer mógłby (a) lepiej wybrać kandydata spośród wielu dopasowań, (b) zacząć kopię wcześniej, przy krótszym sufiksie.
- Ile to może dać, sprawdziłem w §5.1. Przypomnienie z lekcji `lekcja-mtp-juz-kopiuje.md`: P(MTP d1 | lookup d1) = 0.968, a na serwerze 0.995 (`16b:22`). Pozycje d1–d4 kopii MTP już pokrywa, więc pointer może dać zysk tylko w ogonie i w wyborze kandydata.

### 4.3 Spekulacyjne kopiowanie w literaturze

CopySpec (EMNLP 2025, https://aclanthology.org/2025.emnlp-main.1337) i Suffix Decoding (vLLM, https://docs.vllm.ai/en/latest/features/speculative_decoding/suffix) robią to samo co nasz lookup: regułę dopasowania bez treningu. CPLM nie wnosi do nich mechanizmu, bo nie robi spekulacji. Wnosi tylko argument, że wyuczone wskazanie pozycji jest lepsze od reguły.

## 5. Nasze pomiary (CPU, bez GPU)

### 5.1 Sufit „idealnego pointera” nad lookup tail

Skrypt `21c-cplm/oracle.py`. Dane:
- `gen_p1.jsonl`: 69 207 tokenów odpowiedzi Qwena, czat EN/PL;
- 40 losowych epok z 480 sesji omp: 1 250 132 tokenów wyjść. Strumienie odtworzone `15b-sim/extract_agent.py`; 82.2 M tokenów strumienia, 16.1 M tokenów wyjść.

Model kroku:
- MTP n=4 z profilem 0.779/0.565/0.404/0.293 (`15b-sim/results.txt:1`);
- koszt kroku 28.74 ms (`16b:19`) plus 6.40 ms za W16 przy 2k (`16b:20`), naliczany tylko wtedy, gdy ogon został użyty.

Polityki (wszystkie oprócz HYB wymagają, jak serwer, pełnego łańcucha MTP k=4):

| polityka | co robi |
|---|---|
| BASE | Reguła serwera: najdłuższy sufiks, potem najnowszy; dopasowanie ≥ 6. |
| ORA4 | Wyrocznia wybiera najlepszego z ≤ 64 kandydatów 4-gram. |
| ORA2 / ORA1 | Wyrocznia wybiera spośród ≤ 64 najnowszych dopasowań 2-gram / 1-gram (pointer startuje wcześniej). |
| **AGR4 / AGR2** | **Realizowalne, bez treningu.** Spośród kandydatów 4-gram / 2-gram zostawia tych, których 4 pierwsze tokeny kontynuacji równają się 4 draftom MTP. Potem najdłuższy sufiks, potem najnowszy. |
| ORA1-HYB | Wyrocznia może też zastąpić nieudany łańcuch MTP. |

Wyniki (modelowe t/s względem BASE):

| zestaw | tokeny | BASE tok/krok | ORA4 | ORA2 | ORA1 | **AGR4** | **AGR2** | ORA1-HYB |
|---|---|---|---|---|---|---|---|---|
| czat ALL | 69 207 | 3.05 | +0.3% | +0.7% | +1.0% | +0.2% | +0.6% | +4.9% |
| agent ALL | 1 250 132 | 3.34 | +3.8% | +5.5% | +4.2% | +2.3% | **+3.7%** | +29.8% |
| agent bash | 312 112 | 3.44 | +4.9% | +7.4% | +6.1% | +2.8% | +4.9% | +43.6% |
| agent edit-hashline | 229 277 | 3.63 | +6.0% | +8.3% | +6.7% | +3.8% | +5.4% | +51.8% |
| agent write | 411 785 | 3.17 | +1.6% | +2.5% | +1.6% | +1.2% | +1.9% | +14.5% |

Źródła: `21c-cplm/chat.txt:10`, `21c-cplm/agent.txt:3-7`.

Jak czytać:
- **Wyuczony pointer w roli wybierającego kandydata (ORA2) ma sufit +5.5% na agencie i +0.7% na czacie.**
- AGR2, który nie wymaga żadnego treningu, łapie +3.7 z tych 5.5 pp. Na pointer zostaje ≤ 1.8 pp, a to sufit przy idealnej wyroczni.
- ORA1-HYB (+30%) to artefakt modelu: zakłada, że łańcuch MTP jest niezależny od kopiowalności tekstu. W rzeczywistości na kopiach MTP i tak trafia 0.968–0.995. Na żywo nadpisywanie draftów MTP lookupem dało −0.9…−4% (`lekcja-mtp-juz-kopiuje.md:13`). Liczby HYB nie są obietnicą.

Ograniczenia:
- wyjścia agenta pisał Claude, nie Qwen (jak w 15b);
- profil MTP jest uśredniony;
- wyrocznie nie płacą za fałszywe ogony. AGR też nie, bo przy k<4 w modelu nie ma prawdziwych draftów.
- Na zestawie `mvs` ogon jest już przyjmowany w 96–99% (`16b:96,112`), więc na długich kopiach poprawa wyboru kandydata nie ma z czego rosnąć. Zysk leży w krótkich i średnich kopiach: bash, wywołania narzędzi, hashline (196 t/s, 6.24 tok/krok, `16b:109`).

### 5.2 Słownik draftu 64k a tokeny z kontekstu

Pomysł inspirowany CPLM i nie wymagający treningu: liczyć logity draftu dla 64k najczęstszych tokenów oraz dla tokenów już obecnych w kontekście. Skrypty `21c-cplm/oov.py` i `oov_steps.py`, ranking `~/models/draft/draft_vocab_qwen38.txt` (pierwsze 65 536).

| zestaw | tokeny spoza 64k | z tego obecne w kontekście |
|---|---|---|
| czat ALL | 2.83% | 33.8% |
| czat pl:proza | 4.96% | 21.6% |
| agent ALL | 0.93% | 75.6% |

Źródło: `21c-cplm/oov.txt:12,14,15`.

Sufit tok/krok, gdy łańcuch MTP jest ucinany na tokenie spoza słownika (`oov_steps.txt:2-8`):
- czat EN: 64k → 64k+ctx +0.97%;
- czat PL: +1.68%;
- agent: +0.77…+1.32%.

To górna granica, bo MTP na rzadkich tokenach trafia rzadziej niż średnio. Koszt jest pomijalny: ~4k dodatkowych wierszy × 2.7 KB w IQ4_XS ≈ 11 MB na przebieg draftu.

## 6. Plan adopcji

**A. CPLM jako architektura: NIE.** Wymaga pretrainingu: ich 1.7B to ~900 h B200 na run (§3.1), a Qwen3.8-27B trenował na rzędy wielkości więcej tokenów. Nie przyspiesza dekodowania (+1…4%), a zysk jakości przy ≤ 1.7B jest mały. Wracamy do tematu tylko wtedy, gdy jakiś dostawca wypuści model z CP head. Wtedy potrzebne będą:
- osobny cache kluczy kopii obok KV, także w zapisie sesji SSD (E5: +0.54 GB na 53k przy D=5120, ~0 przy d=64);
- weryfikacja liczona na mieszance p, a nie na p_LM;
- draft MTP może zostać na p_LM.

Kompatybilność z PM4, kvq i bit-exact: brak przeszkód, bo dochodzą tylko nowe, małe kernele [INFERENCE].

**B. AGR2: wybór kandydata lookupu zgodnego z draftami MTP. TAK, mały eksperyment.**
- Zmiana w `common/speculative.cpp` (`common_spec_lookup`):
  - dodać indeks 2-gramów obok 4-gramów; host kosztuje dziś ≤ 10 µs/krok (`16b:29`);
  - po wyliczeniu 4 draftów MTP przejrzeć ≤ 64 najnowszych kandydatów z sufiksem ≥ 2;
  - zostawić tych, których kontynuacja zaczyna się od 4 draftów; wybrać najdłuższy sufiks, potem najnowszy;
  - dokleić ogon do W16;
  - przełącznik `LLAMA_SPEC_LOOKUP_AGREE=1`.
- Weryfikacja się nie zmienia, więc metoda jest bezstratna (klasa DIST, tylko drafty). Przy T=0 tekst jest identyczny, z tym samym zastrzeżeniem co W16 poza `LLAMA_SPEC_BITEXACT` (`16b:142`).
- Nakład: ~0.5 dnia kodu i ~0.5 dnia A/B.
- Oczekiwany zysk z modelu: agent +3.7% t/s (115.0 → 119.3 modelowo, `agent.txt:7`), hashline +5.4%, czat +0.6%.
- Ryzyko: fałszywe ogony przy k<4, gdy wrong-drafty MTP zgadzają się z jakimś kandydatem 2-gram. Każdy taki ogon kosztuje +6.4 ms.
- **Eksperyment minimalny:** ABBA w jednej binarce (`metody/pomiar-abba.md`) na `mvs`, `copy` (w tym hashline-pl, `str_replace`) i `spec_sweep`, T=0 i T=1 z 3 seedami. Metryki: ms/krok i tok/krok oraz liczba ogonów i ich akceptacja z logu `LLAMA_SPEC_LOOKUP_LOG`.
- **Kill:** < +2% t/s na hashline i `str_replace` łącznie, **albo** > +0.5% ms/krok na `spec_sweep`, **albo** akceptacja ogonów AGR < 80% na czacie, **albo** zmiana md5 przy T=0 na W8 z `BITEXACT`.
- Bezpieczeństwo sprzętu: bez wpływu na SSD. Termika jak przy obecnym W16 (16b robiło pomiary po naprawie wentylatorów).

**C. Słownik draftu 64k ∪ kontekst: POTEM, niski priorytet.**
- Sufit +0.8…+1.7% tok/krok, ale wymaga dynamicznego zbioru wierszy w `ggml_set_rows` i stałego rozmiaru slotów (np. 64k + 4096) dla cache'a grafu. Nakład ~1–2 dni.
- Kill: < +1% t/s na `spec_sweep` PL przy ABBA. Wcześniejsze wyniki `--spec-draft-vocab` (16k −5%, 32k +7%, 64k +7.5%, 96k +6%) mówią, że większe pokrycie słownika samo w sobie mało daje, więc oczekiwania są niskie.

**D. Wyuczony pointer jako drafter: NIE.** Sufit wyroczni ponad AGR2 to ≤ 1.8 pp tylko na agencie, a trening na ukrytych stanach zamrożonego Qwena kosztowałby tyle co pilot MTP. Pilot MTP (11) nic nie dał.

## Do bazy wiedzy

- **Folder `research/`**, tytuł „Raport 21c: Copy-Paste Language Models (CPLM)”.
  - CPLM to architektura z pretrainingu (pointer po kontekście + bramka `<copy>` + `<sink>`), a nie optymalizacja inferencji.
  - Krok dekodowania ×1.010–1.038 (arXiv 2610.19247 Tab. 6); trening 1.7B ×0.969 i pamięć ×1.096 (Tab. 5).
  - Zysk w ~75% pochodzi z gradientu do backbone'u (stop-grad: −0.008 vs −0.031 nat, Tab. 15); doklejony neural cache daje 0 (Tab. 9).
  - Werdykt: nie adoptujemy.
- **Folder `lekcje/`**, tytuł „LM head bottleneck w pracach treningowych ≠ koszt LM head w dekodowaniu”.
  - Qwen3.8-27B `output.weight` Q6_K 1042.94 MB = 6.2% z 16.83 GB/krok (GGUF header, `15a-monokernel.md:154`).
  - LFM tied head 215 MB = 12.1% z 1.777 GB (`15a-monokernel.md:121`).
  - CPLM nie zmniejsza tego kosztu, dokłada 1–4%.
- **Folder `eksperymenty/`**, tytuł „2026-10-19: sufit pointera nad lookup tail (CPU)”.
  - Czat: ORA2 +0.7%, AGR2 +0.6% (`21c-cplm/chat.txt:10`).
  - Agent 1.25 M tokenów: ORA4 +3.8%, ORA2 +5.5%, AGR2 +3.7% (`21c-cplm/agent.txt:7`).
  - HYB +30% to artefakt modelu.
- **Folder `metody/`**, tytuł „AGR: wybór kandydata lookupu zgodnego z draftami MTP”.
  - Bez treningu i bezstratne; w modelu łapie 2/3 sufitu wyuczonego pointera.
  - Kill: < +2% t/s na hashline/str_replace albo > +0.5% ms/krok na `spec_sweep`.
- **Folder `eksperymenty/`**, tytuł „2026-10-19: tokeny spoza słownika draftu 64k”.
  - Czat 2.83% (z tego 33.8% w kontekście), agent 0.93% (75.6%) (`21c-cplm/oov.txt:14-15`).
  - Sufit „64k ∪ kontekst” +0.8…+1.7% tok/krok (`oov_steps.txt:2-8`).
