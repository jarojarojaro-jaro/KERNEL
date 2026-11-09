# 69: Synteza — DSpine-27B, qwen-warp/TensorFold, Astra-Stop, sterownik AMD a SSD (2026-11-09)

**Żadna pozycja z tej rundy nie jest pewnym zyskiem dla XTX w final mode: DSpine-27B ma dodatni zakres tylko na klasie „nowy kod” przy ctx ≤ 16k (en-code +9…+57%, mieszanka agentowa +0…+4%) i rozstrzyga go dopiero tani test τ na GPU (T1, pobranie 1,26 GB); qwen-warp 0.8.0 daje Enigmie NVIDIA najmocniejszy publiczny punkt odniesienia dla 27B na 3090, a TensorFold dalej nic dla gfx1100; Astra-Stop to zmiana zachowania modelu (nie bezstratna), tania do sprawdzenia (0 pobrań, LoRA 90 KB gotowa), ale z przeciekiem `</think>` do odpowiedzi (11/32); błąd Adrenalina nie dotyczy naszego serwera i jest tematem UX Enigmy (nigdy nie radzić wyłączania ReBAR).**

Raporty: [69a](69a-dspine-27b.md) (DSpine-27B, port llama.cpp), [69b](69b-tensorfold-qwen-warp.md) (TensorFold i qwen-warp, delty), [69c](69c-astra-stop.md) (Astra-Stop, skrypty w [69c-skrypty/](69c-skrypty/)), [69d](69d-amd-sterownik-ssd.md) (AMD Adrenalin `atieclxx`). Całość na CPU i w sieci: bez GPU, bez buildów, bez pobierania wag. Zyski to szacunki z raportów (model V(w, ctx) z `wiki/metody/koszt-szerokosci-weryfikacji.md`), nie pomiary.

**Próg adopcji (decyzja użytkownika 2026-11-09):** testujemy tylko zmiany z oczekiwanym zyskiem ≥ 3–5% decode lub prefill albo ≥ 1 s na turę agenta; ułamki procenta odrzucamy bez pomiaru. Zmiany zachowania (Astra-Stop) i tematy UX (Adrenalin) nie są optymalizacjami szybkości i podlegają osobnej decyzji.

## Werdykt per temat

| temat | werdykt | dlaczego | klasa zmiany |
|---|---|---|---|
| **DSpine-27B** (Tencent, 11-07; port Ajay9o9 `d493f84`) | **kandydat tylko jako drafter klasy „nowy kod” (≤ 16k), po T1; nie zastąpi MTP4 ani ogona W16; nie jako domyślny drafter Enigmy** | krok DSpine na XTX 37,5–43,5 ms przy 2k ⇒ potrzeba τ 1,39–1,62× MTP4; PL i proza −40…−67%; okno SWA 8192 (τ spada poza oknem, v1: −35% przy 13k); port to 323 linie samego grafu, u nas ~1–2 dni `[INFERENCE]` zamiast 5–7; liczby autora (3090) od zaniżonej bazy AR 28,2 t/s, bez MTP | bezstratna (rozkładowo; T=0 te same tokeny modulo numeryka szerokiej weryfikacji) |
| **qwen-warp 0.8.0** (`689901c`) | **referencja dla Enigmy 3090, nic do XTX** | DFlash2 w jednym grafie CUDA: kod ×1,51, czat ×1,34, ale tury agenta z kopiowaniem −31% i przy 262k na 24 GB się nie mieści; multiuser 441 t/s przy 8 klientach; różnica ×1,5–2 w dekodzie wobec naszego forka 3090 `[INFERENCE]`, warunki nieporównywalne | – |
| **TensorFold v1.2.3–1.2.5** (`abc39af1`) | **nic do adopcji** | gfx1100 nadal nieuruchamiany; HIP rośnie tylko na gfx1151/gfx1201; DFlash2 na HIP ładowany, ale nieużywany; spine w stylu DSpine w ich treningu ±0,002 kontroli | – |
| **Astra-Stop** (HF `27c08370`, replikacja `f732402`) | **zmiana zachowania, nie bezstratna; decyzja użytkownika (§ decyzje, pkt 2)** | rank-1 ×2 na `blk.63.ffn_down` wzdłuż odczytu `</think>` (cos 0,9998); replikacja Q4_K_M bez MTP: mediana myślenia −35,5% (xhigh, pelikan), matematyka bez zmian, ale `</think>` w treści 11/32; przy naszym `low` niezmierzone; ortogonalne do kierunku Uncensored (cos 0,014) | zmiana rozkładu wyjścia |
| **AMD Adrenalin `atieclxx`** | **serwer: nie dotyczy; Enigma Windows+AMD: karta ostrzeżenia oparta na pomiarze** | typowo 0,3–1,5 MB/s zapisu hosta (26–130 GB/dzień, 2,6–13× nasz budżet KV 10 GB/dzień); wersje 26.6.4–26.10.2; „26.11.1” niepotwierdzone; obejście „wyłącz ReBAR” — nigdy nie radzić | UX, 0 t/s |

## Testowalne pozycje (wszystkie czekają na decyzję użytkownika)

| # | pozycja | oczekiwany zysk | test | kill | pobranie | status |
|---|---|---|---|---|---|---|
| D1 | **DSpine T1**: τ per klasa na XTX bez portu (fork Ajaya pod HIP, cel bazowy UD-Q4_K_XL, ramię MTP4 w tym samym buildzie) | rozstrzyga −67…+57% per klasa; en-code +9…+57%, pl-kod −14…+33%, mieszanka agentowa +0…+4% `[INFERENCE]` | `spec_sweep` 6 klas T=1 + T=0 + `mvs`, tok/krok i ms/krok per klasa; ramiona n 7 i probabilistic | τ_DSpine/τ_MTP4 < 1,55 na en-code **i** pl-kod → kill portu | **1,26 GB** (Q4_K_M draftera) | czeka na decyzję (pkt 1) |
| D2 | DSpine T2–T4: D(ctx), port do topki za flagą + kontroler „kod”, VRAM przy dużym ctx | jak D1, tylko klasa kod ≤ 16k | po pozytywnym D1 (69a §5) | D(2k) > 10 ms; < +10% na kodzie przy 8k; OOM przy 196k → profil kod ≤ 131k | 0 | zależne od D1 |
| A1 | **Astra-Stop T1–T2**: LoRA ładuje się w topce, skala 0 = bez zmian; koszt skali 1 | 0 (bramka); koszt −0,03…−0,04% t/s `[SZACUNEK]` | serwer z `--lora …,--lora-init-without-apply`; md5 greedy przy skali 0; `spec_sweep` ABBA 0 vs 1 | crash / inny md5 przy 0; t/s < −1% albo akceptacja MTP < −1 pp | 0 (adapter 90 KB) | czeka na decyzję (pkt 2) |
| A2 | **Astra-Stop T3–T4**: replikacja (xhigh, z MTP) i efekt przy `low`/`medium` | xhigh: mediana myślenia −30…−36% (pelikan: ~9,3k tokenów ≈ 79 s na odpowiedź przy 118 t/s `[INFERENCE]`); `low`: 0…−10% `[SZACUNEK]` | `pelican_ab.py` 16 vs 16; 20 zadań `tasks.py` {low, xhigh} × {0, 1} + `medium` bez edycji | mediana < −20% lub p ≥ 0,05 (xhigh); przy `low` > −5% tokenów → bez wartości dla produkcji; pass −≥ 2/40 | 0 | czeka na decyzję (pkt 2) |
| A3 | **Astra-Stop T5–T7**: KLD bez myślenia, przeciek `</think>` w agentach, strażnik „drugie `</think>` zabronione” | T7 usuwa przeciek, koszt ~0 (host) | KLD na korpusach 16e; skan 50 zadań agentowych z narzędziami + HTML/JSX; T7 = zmiana w `reasoning-budget.cpp` + build | KLD > 2× podłoga Q8; ≥ 1 zepsute wywołanie narzędzia lub przeciek > 2%; T7: przeciek > 0 albo zmiana md5 bazy | 0 | czeka na decyzję (pkt 2) |
| W1 | **qwen-warp vs nasz fork na wynajętym 3090** (ta sama sesja, ABBA, 340/350 W) | 0 dla produktu; kalibruje zapas ×1,5–2 na 3090 `[INFERENCE]` | `serve.py --profile long --max-model-len 262144 --prompt-lookup 0` vs fork kvqlean; prompty 67c (czat, mvs, kopia 64k, 190k); t/s i TTFT | warp < 1,15× forka przy równym ctx → zamykamy temat portu | 19,48 GB (Swift-1.5 INT4, na wynajmie) | czeka na decyzję (pkt 3) |
| W2 | DFlash2 ≤ 64k na 3090 (warp) na naszym replayu agentowym | ich dane: czat ×1,07–1,34, agent −31%; u nas −10…+10% `[INFERENCE]` | ten sam replay co `spec_sweep`, oba drafty | replay < +5% albo kopia 64k gorsza od MTP | 3,85 GB (na wynajmie) | po W1 |
| W3 | 16-wierszowe przejście po wagach (dwa kafle n8) w MMVQ forka CUDA | kilka % na `mvs` na 3090 `[INFERENCE]` | microbench MUL_MAT n=8/16 + `spec_sweep` | < +3% `mvs` | 0 | do zlecenia po W1 |
| E1 | **Karta „Dysk / sterownik GPU” w hardware scanie Enigmy** (Windows+AMD) + test ReBAR on/off | 0 t/s; wiarygodność ostrzeżenia, dane do UX | wynajęty Windows+AMD: czas ładowania Q4_K_M 27B i pp/tg przy ReBAR on/off; licznik PDH `atieclxx` vs resmon | różnica < 5% we wszystkim → w UX tylko informacja; licznik nie widzi zapisów → tylko miękki komunikat po wersji | 0 | czeka na decyzję (pkt 4) |
| Q1 | **Mini-zestaw jakości** (lm-eval: GSM8K/MATH, EvalPlus: HumanEval+/MBPP+, BFCL: wywołania narzędzi) jako bramka dla zmian zachowania i stratnych | 0 t/s; umożliwia decyzje typu Astra-Stop, kwanty, drafty PL | najpierw A/A (ten sam model, 2 seedy) dla rozrzutu, potem Uncensored vs Astra-Stop | rozrzut A/A większy niż różnica, którą chcemy wykrywać → zestaw za mały | zbiory danych, dziesiątki MB | czeka na decyzję (pkt 5) |
| G1 | **Dynamiczna głębokość draftu MTP** (luka Gumbela, 68b #1) z bramką „wymuszanie tokenów + KLD” zamiast md5 (68b #2) | +3,9% ogółem (czat PL +4,8%), sesja agentowa +2…3% `[INFERENCE]`; tylko z wczesnym wyjściem z łańcucha draftu | `spec_sweep` ABBA `LLAMA_SPEC_DEPTH_GAP=0/2`, T=1, seedy 1..8; `long_ctx_bench` 1,7k/94k/199k | bramka nie rozdziela wadliwego od bezstratnego; zysk < 3% | 0 | czeka na decyzję (pkt 6) |

## Decyzje dla użytkownika
1. **Pobranie draftera DSpine (1,26 GB, `aj9o9/Qwen3.8-27B-DSpine-b16-GGUF`, Q4_K_M) pod test T1** (D1). Build forka Ajaya pod HIP (CPU ~15–25 min) i ~1 sesja GPU. Bez T1 temat zostaje zamknięty na wniosku „tylko kod ≤ 16k, zysk na mieszance +0…+4%”, czyli poniżej progu adopcji dla ruchu agentowego.
2. **Astra-Stop** (zmiana zachowania, nie bezstratna; 69c §7):
   - (a) **nic nie robić** — zostać przy `--reasoning-effort low` (domyślne, dopóki T3–T6 nie przejdą);
   - (b) **opt-in per żądanie przez LoRA** (skala 1 lub 0,5, domyślnie wyłączona) — rekomendacja raportu, ale dopiero po T1–T6 i najlepiej z T7;
   - (c) **wpiec na stałe** (splice error-feedback do kopii GGUF, 16,8 GB na dysku) — raport odradza;
   - (d) **tylko strażnik `</think>`** (T7) niezależnie od Astry — poprawność formatu, bez zysku szybkości.
   Plan testów T1–T7 (A1–A3 wyżej): ~4–5 h XTX za T1–T6, T7 wymaga buildu.
3. **Test qwen-warp vs nasz fork na wynajętym 3090** (W1; pobranie 19,48 GB na wynajmie). Bez niego różnica ×1,5–2 zostaje `[INFERENCE]`.
4. **Karta ostrzeżenia sterownika AMD w Enigmie** (E1): pomiar 30 s zapisów `atieclxx`, próg ≥ 0,2 MB/s, bez automatycznych akcji, „nie wyłączaj ReBAR”; wersja z poprawką wpisywana dopiero po release notes AMD.
5. **Mini-zestaw jakości** (Q1): pobranie zbiorów lm-eval/EvalPlus/BFCL (dziesiątki MB) jako stała bramka dla zmian zachowania.
6. **Dynamiczna głębokość draftu MTP** (G1, z 68b): zgoda na zmianę bramki md5 → „wymuszanie tokenów + KLD” dla zmian polityki draftu.

## Wyniki negatywne i korekty tej rundy
- „DSpine 94–132 t/s” nie występuje w żadnym źródle; „1,75× nad DFlash2” liczone od DFlash2 z blokiem 8 na wolnej ścieżce MMQ (Ampere); „3,3×” to SGLang przy współbieżności 8, nie batch 1 (69a §1.3).
- DSpine-27B ma SWA 8192 we wszystkich 5 warstwach: KV draftu ~47 MB zamiast 1,18 GB z 21a (69a §1.1).
- Naiwny splice Astry w już skwantyzowany Q6_K daje 1,76× zamiast 2× (69c §4.2).
- Numer sterownika z poprawką „26.11.1” niepotwierdzony (69d).

## Powiązane
- [68-SYNTEZA](68-SYNTEZA.md), [21a-dspine](21a-dspine.md), [62-weight-space-programming](62-weight-space-programming.md), [67-nvidia-vast-kampania](67-nvidia-vast-kampania.md)
- `wiki/research/raport-69-synteza.md`, `wiki/modele/drafter-dspine.md`, `wiki/modele/astra-stop.md`, `wiki/produkt/amd-adrenalin-zapisy-ssd.md`
