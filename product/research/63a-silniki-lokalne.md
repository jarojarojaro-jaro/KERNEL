# 63a: silniki lokalne i wyścig Qwen3.8-27B (Strata 0.2.3–0.2.11, basalt, elpis, benchlab, YASAKANI, MegaCapybara, NInfer, ignis, mkyt, qwen-warp, TensorFold i konkurs cuda.fast/mlx.fast, gpu.nz)

Data: 2026-11-05. Agent R63aEngines. Pracowałem tylko na CPU: czytałem kod (klony w `~/src/research63/`), release notes, PR-y, posty X (przez `api.fxtwitter.com`), stronę benchlab i publiczne API LocalMaxxing (1 zapytanie). Nie dotykałem GPU ani serwera :8080, niczego nie pobierałem.

Konwencje:
- `[INFERENCE]` oznacza mój wniosek, którego nie zmierzyłem.
- „×BW→XTX” to liczba przeskalowana proporcjonalnie do pasma pamięci: 5090 1792 GB/s, 3090 936, XTX 960, więc 5090 ×0.536, a 3090 ×1.026. Pomijam różnice w L2, mocy i taktowaniu.
- „×bajty” to dodatkowa korekta o liczbę bajtów wag czytanych na krok. U nas to 16.83 GB/token (`wiki/ZRODLA.md:39`).
- Nasze liczby pochodzą z `wiki/REKORDY.md` i `product/WYNIKI-XTX-2026-10-19.md`.

## TL;DR

1. **Nie ma przełomu w algorytmie. Jest przełom w składaniu: mniej bajtów, głębszy draft i drzewo, wszystko na GPU w jednym grafie.** Wszystkie szybkie silniki dla 27B robią w dekodzie to samo:
   - mały format natywny dla karty: NVFP4 lub MXFP4 na Blackwellu, trellis/EXL3 3–4 bpw;
   - DFlash2 z 7–15 węzłami weryfikacji (łańcuch albo drzewo);
   - leniwe cofanie stanu GDN (to mamy jako S4);
   - graf CUDA z PDL, grupowane projekcje o tym samym wejściu, KV 3–4-bitowe.
   Kerneli istotnie lepszych od naszych per bajt nie znalazłem. mkyt i ignis podają ~73–100% pasma na GEMM, my mamy ~76% plain.
2. **YASAKANI 1220 t/s to klasa „kopiowanie/struktura”, nie pisanie.**
   - JSONL 160 wierszy i edycja pliku 4.7k tokenów (1241 t/s) to zadania o ~12 tokenach na krok `[INFERENCE]`.
   - Przy zalecanych ustawieniach Qwena (thinking, T=1) autor podaje medianę 381 t/s. Po przeskalowaniu na pasmo XTX to 204, a po korekcie bajtów (11.7 vs 16.8 GB) **~142 wobec naszych 114.8**.
   - Na edycji kodu po obu korektach wychodzi ~462 wobec naszych 433.8. To parytet.
   - Autor sam poprawił jedną liczbę (pętla greedy zawyżyła 424 → 303). Kodu jeszcze nie ma.
3. **Gdzie realnie odstajemy (po normalizacji):**
   - (a) **bardzo długi kontekst**: qwen-warp na 3090 dekoduje 94 t/s przy 262k i 102 przy 190k. Po przeskalowaniu to ~96–105 wobec naszych **74.5 przy 199k**;
   - (b) **świeży kod/struktura przy T=0**: DFlash2 plus drzewo plus głębokość 7–8 (MegaCapybara, mkyt, ignis, exl3 MTP-7);
   - (c) **bajty wag**: YASAKANI 12.4 GB przy KLD 0.021, ignis trellis 12.5 GiB. My nie zmieniamy kwantów, to decyzja użytkownika;
   - (d) **prefill na FLOP**: pp4096 1125 t/s to ~49% szczytu WMMA (R18 #15). Silniki na 3090 robią 1.2–1.9k t/s dzięki akumulacji fp16 albo gpu-unlock, a to nie przenosi się na RDNA3.
4. **Strata 0.2.3 → 0.2.11 (9 wydań, silnik 0.1.48 → 0.1.57): dla gfx1100 i dla gęstego 27B prawie nic.** Strata obsługuje tylko Flash-Next i DeepSeek. Paczkę RX 7900 „zbudowano, nie uruchomiono”.
   - KVA (0.2.7) to stratny prefill przez sam stan późnych warstw: +11–28% prefillu, ale −11% dekodu na R9700. Ciekawa idea, ryzykowna jakość.
   - **PR #4366 to lekcja metodologii**: ogłoszone +39% okazało się porównaniem ciepłego z zimnym, realnie +2–6%.
   - 0.2.10: DFlash2 domyślny (także gfx1100) i silnik „wszystkie karty” (TP) dla 2×A6000 / 4×R9700.
5. **Top 3 eksperymenty dla nas:**
   - (E1) `kvq` jednym przejściem po KV dla wszystkich kafli N×G w weryfikacji. qwen-warp potwierdził pułapkę i jej rozwiązanie. Oczekuję **+8–15% dekodu przy 94–199k**, bitowo;
   - (E2) profil „kod/T=0”: MTP n=6–7 z mniejszym słownikiem draftu. turboderp: MTP-7 vs MTP-4 = +22% na greedy html. Oczekuję +5–10% na tej klasie, 0 na czacie;
   - (E3) KV q4_0 z dokładnym pierścieniem f16 ostatnich 256 tokenów i 4 sinkami (qwen-warp). Głównie jakość agenta: tool-call z 4-bit KV 46% → 92–96% u nich. Najpierw pomiar u nas.

## 1. Tabela porównawcza (Qwen3.8-27B, 1 strumień, 1 karta)

| silnik (wersja) | karta | obciążenie, warunki | t/s | ×BW→XTX | ×bajty | nasz odpowiednik na XTX |
|---|---|---|---|---|---|---|
| YASAKANI fast 11.7 GB ([X](https://x.com/yasakani_dev/status/2117521489885090271)) | 5090, 600 W stock | JSONL 160 wierszy, greedy, thinking off | 1220 | 654 | ~455 | mvs (edycja kodu) T=0 **433.8** |
| YASAKANI fast | 5090 | edycja pliku 4 711 tok., greedy | 1241 | 665 | ~462 | mvs **433.8** |
| YASAKANI fast | 5090 | angielska proza, pierwsze 2000 tok. (po korekcie, [X](https://x.com/yasakani_dev/status/2117529802844610956)) | 303 | 162 | ~113 | 1.7k T=0 sam MTP4 **136.5** (inny prompt) |
| YASAKANI | 5090 | thinking, T=1, mediana 6 zadań | 381 | 204 | ~142 | spec_sweep T=1 **114.8** (PL/EN, bez thinking) |
| YASAKANI | 5090 | dekod przy 250k w kontekście | 152 | 81 | (KV dominuje) | 199k T=0 **74.5** |
| MegaCapybara 1.39 Tiny (pomiar YASAKANI, stock) | 5090 | kod / edycja / proza, greedy | 466 / 440 / 238 | 250 / 236 / 128 | ~202 / 191 / 103 | mvs 433.8; proza 136.5 |
| MegaCapybara (własne, +20% OC pamięci) | 5090 | kod, 1 agent, Tiny | 540 | 241 (×960/2150) | — | — |
| mkyt `eea3cbc` | 5090, 400 W | kod / JSON / proza | 386 / 500 / 258 | 207 / 268 / 138 | ~184 / 239 / 123 | — |
| mkyt | 5090 | bez spekulacji @73k | 87 | 46.6 | — | plain tg128 (krótki) 43.2 |
| ignis `df69a68` | 5090 | 8 promptów kodu (geomean) / przewidywalny kod / proza | 367 / 491 / 167 | 197 / 263 / 89.5 | (czytają więcej: NVFP4 18.1 GiB) | en-chat T=1 87.8, pl-proza 99.8 |
| NInfer (LocalMaxxing, oficjalne NVFP4) | 5090 | reasoning-v1 T=0 | 334 | 179 | — | szac. ~147 (R32f) |
| TensorFold 1.2.1 ([benchlab](https://benchlab.ironyaditya.xyz/posts/2026-11-03-engines-27b-3090/)) | 3090, 350 W | strona html 4000 tok. / krótkie | 170 / 95–102 | 174 / 97–105 | ~ | — |
| HyperQwen `f382342` (benchlab) | 3090 (gpu-unlock) | strona / krótkie | 180 / 119–130 | 185 / 122–133 | ~ | — |
| HyperQwen (README) | 3090, 250 W | cytowanie dokumentu 25k | 381 | 391 | ~ | copy T=0 406.6, mvs 433.8 |
| exl3 1.6.5 (turboderp w benchlab) | 3090 | strona greedy: DFlash2 / MTP-4 / MTP-7 | 166 / 129 / 157 | 170 / 132 / 161 | ~ | — |
| exl3 (turboderp) | 3090 | thinking, domyślne próbkowanie | 154 / 129 / 152 | 158 / 132 / 156 | ~ | spec_sweep 114.8 |
| llama.cpp v0.8.0 (benchlab) | 3090 | strona / krótkie | 97 / 71–73 | 99.5 / 73–75 | ~ | (nasza 3090 topka: czat T=1 93.3, mvs 348.9) |
| elpis `13e8b59` | 3090, 350 W | dekod geomean 1K/8K/32K/262K, greedy | 125.7 | 129 | ~ | 136.5 / 121.6 / 109.4 / 74.5 (1.7k/6.6k/29.5k/199k) |
| qwen-warp `146a654` | 3090, 350 W, Swift INT4 | dekod przy 190k / 262k | 102 / 94 | **105 / 96** | ~ | 199k **74.5** (262k nie serwujemy) |
| qwen-warp | 3090 | krótkie: kod / proza / matma | 172 / 110 / 172 | 176 / 113 / 176 | ~ | — |

Wniosek z tabeli:
- Na **edycji i kopii** jesteśmy w czołówce per pasmo (433.8). Przy korekcie bajtów wyprzedza nas tylko YASAKANI, i to minimalnie.
- Na **prozie przy T=1** mamy parytet z ignis i mkyt.
- Przegrywamy z **głębokimi draftami na greedy kodzie** i z qwen-warp przy **≥190k**.
- Zastrzeżenie: większość cudzych liczb to greedy z wyłączonym thinking, angielski, inne prompty. Nie są to nasze klasy (PL/EN, T=1). Te same prompty mierzył tylko benchlab (4 silniki na jednej 3090) i YASAKANI kontra MegaCapybara.

## 2. Strata: wydania 0.2.3–0.2.11 (delta od `011c9e60` v0.2.2, R57b)

Źródła: [release notes v0.2.3–v0.2.11](https://github.com/Niko1221/Strata/releases), klon `9f7d977d` (2026-11-05, `v0.2.11-3`).

| wydanie | silnik | co istotne | dla nas |
|---|---|---|---|
| [0.2.3](https://github.com/Niko1221/Strata/releases/tag/v0.2.3) | 0.1.48 | Strix Halo +6–19% dekodu (hyper-connection w 8 bitach, chunk 8192); DFlash2 opt-in; cache rozmów rozmiarowany z wolnej pamięci (40% powyżej podłogi, ≤ 8 GiB): drugi agent 91% reuse, tura 11 → 3 s | nic na gfx1100 |
| [0.2.4](https://github.com/Niko1221/Strata/releases/tag/v0.2.4) | 0.1.49 | DeepSeek-V4.1-Flash z SSD/RAM; prefill warstwami (16 → duże chunki); RDNA4 matrix-core prompt +36–49%; „pominięcie pracy ostatnich 20 warstw” w długim prompcie DeepSeek (99.5% top-1) | idea pominięcia ≈ KVA |
| [0.2.5](https://github.com/Niko1221/Strata/releases/tag/v0.2.5) | 0.1.50 | tryb „Faster” = 5 z 6 ekspertów (stratny); **ścieżka promptu wybierana z długości, nie z pomiaru czasu** (wcześniej to zmieniało odpowiedzi); rozgrzewka chunked pass w tle (−3.6 s na pierwszym prompcie R9700) | lekcja determinizmu, rozgrzewka mamy (R45) |
| [0.2.6](https://github.com/Niko1221/Strata/releases/tag/v0.2.6) | Qwen bez zmian | DeepSeek: wszyscy eksperci kopiowani do RAM, gdy się mieszczą (reguła z Maya) | nie |
| [0.2.7](https://github.com/Niko1221/Strata/releases/tag/v0.2.7) | 0.1.52/53 | **KVA** opt-in (§3); route prior na ≤ 12 GB NVIDIA (+15–37%, stratny, w 0.2.8 wyłączony z powodu powtórzeń); R9700 Qwen IQ3_S dekod 64.9 → 85.1 @32K; split-serve; prefill layer-major na 2 kartach (TTFT 32K 141.8 → 27.7 s) | KVA; layer-major dla wielu kart (Enigma) |
| [0.2.8](https://github.com/Niko1221/Strata/releases/tag/v0.2.8) | 0.1.54 | HIP okno weryfikacji 8 → 16 wierszy (bitowo); 4×R9700 32 żądania ×2.4; odzysk zepsutych tool-calli 92.9 → 98.3%; `DS4_FAT_ROWS` (PR #4366, §4) | odzysk tool-calli: pomysł do serwera |
| [0.2.9](https://github.com/Niko1221/Strata/releases/tag/v0.2.9) | 0.1.55 | Strix Halo prefill ×1.8; GDN prompt na tensor core (NVIDIA) +2–6%; równoległe żądania na NVIDIA ×1.45 przy 8 | nic na gfx1100 |
| [0.2.10](https://github.com/Niko1221/Strata/releases/tag/v0.2.10) | 0.1.56 | §5 | §5 |
| [0.2.11](https://github.com/Niko1221/Strata/releases/tag/v0.2.11) | 0.1.57 | split engine 4×R9700 +6.9% / +32.7% (8 użytk.); K-quant MMQ na NVIDIA dla UD-Q4/5/6_K_XL prefill +26–38% (KL 0.024–0.035); chunk 32768; FP16 cache wag przy parallel (bitowo, +4–7%); **route-tail-skip** na R9700 +6.18% dekodu (KL 0.077, stratne); naprawiony błąd prywatności (#2892: odpowiedź trafiała do złego żądania przy replikach) | lekcja: test „wymuszonego przekazania” pod współbieżność |

**gfx1100 w całym okresie:**
- Paczka „Linux RX 7900” była tylko zbudowana i nieuruchomiona (0.2.9, 0.2.10, 0.2.11).
- Jedyna zmiana mierzona na XTX to Windows HIP #4787: aliasy areny ekspertów kolidowały z pamięcią procesu, 5/70 złych startów → 0/110. Mierzył autor PR.

**Werdykt:** dla topki na XTX z gęstym 27B zero nowych kerneli. Strata jest konkurentem UX i wielu kart, nie decode 27B. **Akcja:**
- (1) dopisać do watch: `git log 9f7d977d..`, tylko HIP/gfx1100 i gęsty 27B;
- (2) przejrzeć logikę odzysku tool-calli z 0.2.8 (`#4427`, `#4077`) pod nasz `CHAT_NATIVE`. To osobny wątek produktu, bez GPU.

## 3. Strata KVA (0.2.7, `STRATA_KVA=1`)

Mechanizm ([docs/KVA.md](https://github.com/Niko1221/Strata/blob/9f7d977d220e9fdf2ec53cf2620cdadac1cfb24e/docs/KVA.md)):
- Zimny prompt ≥ 4096 tokenów czytany jest dokładnie przez warstwy 0–35.
- Dla późnych warstw 36–47 (z 48) KVA buduje **tylko stan rekurencyjny**: rekurencję GDN, historię conv i strony K/V oraz klucze indexera QSA. Pomija wyjście atencji, o-proj i całą połowę MoE.
- Wejście każdej późnej warstwy to residual z granicy („identity”). Projektor liniowy testowano i odrzucono: błąd ≥ 0.80.
- Ostatnie 2048 pozycji są liczone dokładnie.

Liczby z notatek:
- RTX 5070 IQ3_S: +11% przy 14K, +18% przy 30K.
- P100: +12% / +20%.
- R9700: prefill +28%, ale **dekod −11%** (3.33 vs 4.08 tok/krok: MTP gorzej trafia na przybliżonym kontekście).
- Jakość: split 24 gubił rekordy i psuł agentów (0/10). Split 36 daje 585/606 faktów (= dokładny odczyt), agent 6/10 (dokładny: 4 i 7).
- Liczby z wejścia (RTX 2000 Ada 913 → 1077, +14.2%) nie występują w release notes. Uznaję je za niezweryfikowane.

Jak autorzy do tego doszli:
- najpierw zrzut prawdziwych wejść warstw (`STRATA_KVA_CAPTURE`) i wyrocznia (`ORACLE`), która odtwarza wynik;
- potem próba projektora (porażka);
- potem przeszukanie granicy split z bramką agentową, a nie tylko z igłą: igła przechodziła zawsze, a agenci nie.
To dobry wzór: igła nie jest bramką.

Dla nas:
- Qwen3.8-27B ma 64 warstwy (48 GDN + 16 atencji, bez MoE).
- Pominięcie FFN i o-proj w ostatnich 25% warstw dla zimnego promptu daje górną granicę ~−20% FLOP prefillu `[INFERENCE]`, realnie +10–15% TTFT.
- Koszt to stratność (KL ~0.02 u nich) i spadek akceptacji MTP po długim prompcie.
- Nasza produkcja to agent z cache sesji: zimny odczyt zdarza się rzadko, tury idą z checkpointu.

**Werdykt:** pomysł wiarygodny, uczciwie opisany. Dla nas niski priorytet: stratny, a prefill zimny to głównie pierwszy kontakt z dokumentem. **Akcja:** zapisać jako L-kandydat „prefill stratny opt-in”. Eksperyment tylko po E1–E3:
- prototyp na CPU: zrzut wejść warstwy 48 i KL pierwszego tokenu na 3 dokumentach 16–30k (llama.cpp CPU, `nice`);
- kill, gdy KL > 0.02 albo zysk FLOP < 10%.

## 4. Strata PR #4366 (`DS4_FAT_ROWS`) – osobno

[PR #4366](https://github.com/Niko1221/Strata/pull/4366) (lyesrock; zamknięty bez merge, kod wszedł do 0.2.8 jako opt-in):
- Popularni eksperci DeepSeek w chunku dostają **jedną** dekwantyzację do FP16 i jeden `cublasGemmEx` zamiast dekwantyzacji co 64 wiersze w kaflach.
- Pierwsza wersja ogłaszała **+39%** (1400 → 1950 t/s przy 13K na 5090). Autor sam to sprostował: „compared a warmed on run against a single cold off run”.
- Po ABBA na świeżych bootach: +2–4% zimno, +4–6% ciepło, dekod bez zmian, 9–10/12 odpowiedzi greedy bajtowo równych (stock wobec siebie 9/12).
- Strata w 0.2.8 zostawiła to jako opt-in, bo zysk był poniżej ich progu domyślnego.

Dla nas:
- MoE w LFM2.5 mamy na MMQ, a prefill LFM 7148 t/s już jest szybki.
- Gęsty Qwen nie ma ekspertów. Analog „dekwantuj raz, GEMM fp16” przy pp4096 kłóci się z naszym MMQ int8, które jest szybsze od dekwantyzacji do f16 na RDNA3 (R23b, hipBLASLt nie jest lepszy).

**Werdykt:** technicznie bez znaczenia dla nas. **Wartość to lekcja metodologii:** +39% → +4% przez porównanie ciepłe/zimne. **Akcja:** dopisać ten przypadek do `lekcja-higiena-pomiaru` (integrator) jako przykład „ciepły vs zimny”. Reguła: ABBA na świeżych procesach, cache stron wyczyszczony, losowy prompt w każdym pomiarze.

## 5. Strata v0.2.10 – osobno

[v0.2.10](https://github.com/Niko1221/Strata/releases/tag/v0.2.10) (2026-11-02, silnik 0.1.56):

1. **DFlash2 domyślnym drafterem Flash-Next, także na gfx1100.** Zysk nad MTP:
   - Strix Halo +8.8–12%;
   - PRO 5000 +1.4–7.9%;
   - R9700 +4.2–6.6% (krótkie i długie odpowiedzi, próbkowanie aplikacji);
   - Arc A750 −2.6%.
   Na gfx1100 nie mierzono.
   W 0.2.11 przy wielu użytkownikach DFlash2 ≈ MTP (1 użytk. 146.8 vs 136.9, 8 użytk. 194 vs 190.6). Na split engine przy T=1 proza i agent DFlash2 wypada gorzej (128.7 vs 138.8; 145.0 vs 155.3).
   Wniosek: **DFlash2 wygrywa przy greedy kodzie i JSON, przy T=1 nie.** To zgodne z naszym R32f i R36 L5.
2. **Silnik „wszystkie karty” (sFNX, John Fink, MIT)**, czyli tensor parallel zamiast podziału warstw:
   - 2×A6000 edycja 195 → 377–394 t/s, proza 93 → 139–146;
   - 4×R9700 158 t/s dla 1 użytkownika, 350 przy 8;
   - AMD: sumy przez pamięć innych kart (peer) albo przez host, bez librccl −14% prefillu.
   Dla Enigmy (wiele kart) to kierunek produktowy, nie dla XTX solo.
3. **„128K na kartach 8 GB”**: to drabina degradacji zamiast odmowy startu.
   - Kolejne kroki: okno KV na karcie 20480 → 8192 → 4096, potem bez warstwy MTP, potem 16 slotów cache promptu, na końcu głowica w pinned RAM (dekod ×3 wolniej).
   - Flash-Next IQ3_S: 63–73 t/s, ale **na dużej karcie sztucznie ograniczonej** do 8 GB, z dużym RAM.
   - Prawdziwy 5070 ograniczony do ~8 GB: 17–27% wolniej niż pełna karta.
   - Prawdziwy Arc A750 8 GB: 12.7–14.8 t/s.
   - Teza „20+ t/s na 8 GB” jest prawdopodobna na NVIDIA z szybkim RAM, ale nie zmierzono jej na prawdziwej karcie 8 GB NVIDIA.

**Werdykt:**
- (1) potwierdza naszą tezę o klasach;
- (2) jest nieistotne dla XTX, istotne dla Enigmy;
- (3) to wzór UX: kontekst nigdy się nie kurczy, a każdy krok degradacji jest logowany jedną linią.

**Akcja:**
- Enigma: w rekomendatorze dodać jawną drabinę degradacji (KV window, drop MTP, głowica na host), zamiast obniżać ctx. To zadanie produktowe, bez GPU.
- XTX: nic.

## 6. basalt (jesdga95/basalt, fork Straty pod Blackwell)

[Repo](https://github.com/jesdga95/basalt) @ `dc047a7` (2026-11-04), v0.1.0 → v0.2.1, MIT. Tylko Flash-Next, tylko sm_120.

- **Twierdzenia z wejścia:** 6950/273/283 vs Strata 5250/164/182; 8 równoległych 451/489 vs 216/188. **W repo tego nie znalazłem**: brak w changelogach, README i `docs/community/benchmarks.json`.
- Tabela społeczności daje dla 5090 IQ3_S: dekod 374.8 t/s, prefill 16k 8859 t/s (`588a4776ed`, 500 W); 2×5090 NVFP4: dekod 553.6.
- Techniki (kod i dokumenty):
  - **Dokładna dwustopniowa głowica Q8_0 w płaszczyznach bitowych** ([two-stage-head.md](https://github.com/jesdga95/basalt/blob/dc047a7/docs/precision/two-stage-head.md)). Sito czyta bity 2..7 (2080/2720 B wiersza) z udowodnioną granicą 1.5·Σ|y|. Wiersze nad progiem K-tego są liczone dokładnie. 350 vs 439 µs na okno, czyli −20% głowicy, bitowo dla greedy i top-k ≤ 64.
  - Dla Q6_K jest wariant przybliżony: 2-bitowa kopia plus przeliczenie w marginesie 4. KLD +0.0022, czyli stratny w ogonie.
  - **„Mid chain”** ([unified-kernel.md](https://github.com/jesdga95/basalt/blob/dc047a7/docs/unified-kernel.md)): środek warstwy GDN (qkv+z, rekurencja, out-proj) w jednym trwałym launchu, bitowo. Commit GDN „dokańczany” w następnym oknie (finisher). L2 prefetch wag następnej warstwy, gdy kombinacja czeka na CPU.
  - Rozmowy na dysku (100K wraca w ~0.5 s), `--idle-sleep` (VRAM oddany, start 4 s zamiast 40.6 s).
  - Bramka jakości wobec BF16: na tych samych wagach Q8_0 basalt KLD 0.0200, llama.cpp 0.0325 ([0.2.1](https://github.com/jesdga95/basalt/blob/dc047a7/docs/changelog/0.2.1.md)).

Dla nas:
- Głowica dokładna w płaszczyznach działa dla Q8_0, bo sito traci tylko 2 z 8 bitów. Nasz Q6_K (1.043 GB/weryfikację, 1.23 ms z 27.38 ms kroku, R36) w podobnym układzie straciłby 2 z 6 bitów. Granica byłaby ~4× luźniejsza, a basalt sam pisze, że już 5 bitów z 8 daje 9.6% wierszy przy K=20.
- To zgodne z naszym R36 §3: certyfikat tylko dla klasy int8. Q6_K → Q8_0 plus sito czyta ~1.0 GB, czyli tyle samo co dziś.
- „Mid chain”: u nas narzut launchy zjada PM4 (−0.5…−0.9 µs na kernel). Zysk z trwałego launchu warstwy GDN szacuję poniżej 1% `[INFERENCE]` (R15a, R16a: trwałe kernele z barierami przegrywają z PM4).

**Werdykt:** wzorcowa inżynieria pod NVIDIA i MoE, dla XTX/27B nic nowego. Head-trick jest zamknięty dla Q6_K. **Akcja:**
- zanotować „głowica Q8_0 w płaszczyznach” jako opcję **dla LFM2.5**, jeśli jego głowica jest Q8_0. Sprawdzić typ `output.weight` w GGUF LFM na CPU (10 min). Q6_K → kill. Q8_0 → pilot CPU: ile wierszy przechodzi sito przy K=20 na stanach LFM.

## 7. elpis (gildrb/elpis): 262k na jednej 3090

[Repo](https://github.com/gildrb/elpis) @ `13e8b59` (2026-10-29), status „finished”.

- Stos: ExLlamaV3 1.5.0 + 54 łatki, EXL3 4.00 bpw (16.5 GB), DFlash2 z drzewem 8 wierszy, KV 3-bit (12 KiB/token), 262 144 natywnie.
- Wyniki ([RESULTS §11](https://github.com/gildrb/elpis/blob/13e8b59/bench/RESULTS.md)):
  - prefill geomean 1220.7 t/s, TTFT 262K 299.5 s;
  - dekod geomean 125.7 t/s, ms/rundę 25.4 (1K) → 45.6 (262K), wersja bezstratna 112.9 ms przy 262K;
  - GSM8K 205 t/s.
- Co dało zysk (zmierzone):
  - drzewo 8 wierszy: 3.39 → 3.89 tok/rundę;
  - **int8 Q·Kᵀ w weryfikacji** (3-bitowe kody K dokładnie jako int8, IMMA): −4.8% ms/rundę przy 262K;
  - prefill: fuzje i brak synchronizacji z hostem (977.9 → 1200), ping-pong K/V −3.8% TTFT 262K;
  - **350 W zamiast 250 W +32% t/s**. U nas karta zostaje fabrycznie, decyzja z 2026-10-20.
- Metoda:
  - każda zmiana idzie ścieżką „prawo → dowód (Bend/Lean) → pomiar”;
  - bramki R2/R3/D1 rejestrowane przed danymi, bootstrap blokowy;
  - int8 MLP odrzucony (R3 FAIL), mimo że prefill +19%;
  - spisane wszystkie odrzucone próby. Ciekawe: jeden graf całego celu −4.2%, okno draftu 8192 −28% tok/rundę, L2 prefetch = szum.

Dla nas:
- Ich dekod przy 262K (~45.6 ms/rundę, ~3.5–3.9 tok/rundę, więc ~80 t/s) ≈ nasze 74.5 przy 199k. Nasz KV q4_0 jest 4.5 bita, ich 3 bity.
- Nowość: int8 IMMA na QKᵀ w weryfikacji. Nasz `kvq` już liczy na WMMA z dekwantyzacją do f16. RDNA3 ma WMMA iu8 o tym samym tempie co f16, więc zysk jest raczej z bajtów niż z MMA `[INFERENCE]`.

**Werdykt:** najlepiej udokumentowana metoda w tej rundzie (pre-rejestracja, dowody, lista porażek). Szybkością na 3090 ≈ nasza topka na 3090 (93.3 T=1 vs ich lane ~162 greedy, inne prompty). **Akcja:**
- przejąć wzór „bramka rejestrowana przed pomiarem” do fabryki (R16h);
- kernelowo: §13 E1 (pojedyncze przejście KV) pokrywa ich wygraną przy 262K.

## 8. benchlab „engines-27b-3090” i HyperQwen (delta)

[Post](https://benchlab.ironyaditya.xyz/posts/2026-11-03-engines-27b-3090/) (2026-11-03, rerun 11-05):
- Jedna 3090 przy 350 W, odblokowana przez gpu-unlock (fp16 tensor 67.5 → 111 TFLOPS, więc prefill zawyżony wobec stock), 64K, greedy, thinking off.
- Wyniki (strona html 4000 tok.): HyperQwen 180, TensorFold 170, exl3 146, llama.cpp 97.
- Prefill 50K: 1632 / 478 / 1358 / 1171.
- LiveBench (180 pytań): 58.3 / 60.5 / 60.3 / 61.8, czyli szum. Autor sam to zaznacza.
- Najważniejsze: **turboderp poprawił exl3**. bsz1: DFlash2 166, MTP-4 129, **MTP-7 157**. Przy thinking i próbkowaniu: 154 / 129 / 152.
- Jego teza: natywne MTP jest stabilniejsze od DFlash2 na długim kontekście. Rzadka głowica wyjściowa (`-sdh 16384`) sprawia, że 7 autoregresyjnych tokenów MTP kosztuje prawie tyle co 7 równoległych DFlash2.
- Pierwsza wersja posta zawyżała przewagę HyperQwen (×2–7) przez wrapper serwera z blokadą i brak `-ambs`. To kolejna lekcja metodologii.

HyperQwen ([repo](https://github.com/syv-ai/HyperQwen) @ `6ab9bd0`, 163 commity od `95ee3b6`). Delta:
- port na vLLM 0.32;
- **PTH_FA=1**: kernel int8 KV (pth-flash-attn) domyślny na sm_86 przy MTP i długim kontekście, dekod +12.2% (~66k) / +14.0% (~100k);
- FA2 fp8-KV dla DFlash2 na długim kontekście: +27% przy ~100k;
- dopełnienie GEMM `in_proj_ba` przy 2–4 tokenach (klif cuBLAS);
- **port LSA** ([lsa/README](https://github.com/syv-ai/HyperQwen/blob/6ab9bd0/lsa/README.md)): TTFT −13% dopiero przy 137k, +19% wolniej przy 31k, dekod bez zmian. Temat dla R63d;
- cyrylicki słownik draftu.

**Werdykt:**
- benchlab: rzetelny, sam się koryguje; HyperQwen prowadzi na 3090 w greedy.
- HyperQwen: liczby 381/1035 bez zmian; nowość to KV int8/fp8 na długim kontekście (NVIDIA).

**Akcja:**
- (1) dopisać do klasy „kod T=0” eksperyment MTP-7 z rzadszą głowicą: E2;
- (2) na 3090 (chmura, przy najbliższej kampanii) zmierzyć topkę na promptcie benchlab (strona piekarni, greedy, thinking off), żeby mieć wspólny punkt z 4 silnikami. Koszt ~15 min wynajmu.

## 9. YASAKANI: analiza 1220 t/s

Źródła:
- [post 1](https://x.com/yasakani_dev/status/2117521489885090271) (2026-11-03);
- [korekta](https://x.com/yasakani_dev/status/2117529802844610956) i 3 grafiki (pobrane jako obrazy postu do odczytu, nie dane);
- treść przez `api.fxtwitter.com`.

Kodu, wag ani repozytorium nie ma („open source planowane”). Na GitHubie i HF nic nie znalazłem.

Twierdzenia i warunki:
- 5090 stock 600 W, Windows;
- 12 zadań z publicznego fixture NInfer plus własna edycja kodu (`textwrap`, zmiana nazwy zmiennej, cały plik) i długi JSONL (300 zamówień, 8192 tok.);
- greedy, thinking off, (tokeny − 1) / czas generacji;
- MegaCapybara 1.39 mierzony na tym samym PC (domyślny preset „1 rozmowa”, wykrywanie powtórzeń wyłączone po obu stronach).

**Jak 1220 jest fizycznie możliwe:**
- Format fast 11.7 GB. Krok plain przy ~80% z 1.79 TB/s ≈ 8.2 ms, weryfikacja 16 wierszy ≈ 9.5–10 ms.
- 1220 t/s × ~0.0095 s ≈ **11–12 tokenów na krok**.
- To możliwe tylko na tekście, który powtarza strukturę z kontekstu lub z siebie: JSONL z tymi samymi kluczami, plik przepisany 1:1. Mechanizm to lookup/n-gram albo DFlash2 z szerokim blokiem `[INFERENCE]`.
- Ten sam mechanizm daje nam mvs 433.8 przy 14 tok/krok (16b).

Kontrola po normalizacji:
- edycja kodu: 1241 × 0.536 × (11.7/16.83) ≈ **462 vs nasze 433.8**;
- proza po korekcie: 303 → 113 vs 136.5 (inny prompt);
- thinking T=1, mediana 381 → 204 → **142 vs 114.8**.

Wiarygodność:
- (+) uczciwa korekta pętli greedy: 424 → 303, „1.7×” → „1.3×”;
- (+) jawne ograniczenia: świeży kod ×1.04–1.08, chiński wolniej;
- (−) cudze liczby z innych PC i promptów;
- (−) pojedyncze przebiegi;
- (−) KLD liczony inaczej (WikiText-2/C4/FineWeb) niż u MegaCapybara (81 880 tokenów).

Format: 12.4 GB (~3.6 bpw średnio) przy KLD 0.021 to wynik klasy trellis (EXL3/QTIP). Lepszy od UD-Q3_K_XL (KLD 0.039, R16e) przy mniejszym pliku `[INFERENCE]`.

**Werdykt:** to nie jest nowy algorytm. To mniejszy format plus szeroka weryfikacja plus lookup na zadaniach strukturalnych. Po korekcie pasma i bajtów jesteśmy na parytecie na edycji. Na thinking T=1 przegrywamy ~1.24× (głębszy drafter, EN). **Akcja:**
- (1) dodać do watch konto `yasakani_dev` i repo po publikacji (kod formatu i weryfikacji);
- (2) ich zestaw „NInfer 12 zadań + edycja + JSONL” jest publiczny w NInfer. Uruchomić go na XTX jako wspólny punkt odniesienia (E4 w §13).

## 10. MegaCapybara 1.39–1.40 – osobno

[Repo](https://github.com/perkel666/MegaCapybara) @ `bdfc1b8`, [v1.39](https://github.com/perkel666/MegaCapybara/releases/tag/v1.39) (11-01), v1.40 (11-04). Tylko binarki („source code later”).

- 1.39 i 1.40 to poprawki: WebP, polityka prefillu w launcherze, U+FFFF, `0.0.0.0`. Silnik od 1.36/1.35 bez zmian szybkości.
- Technika z README i CHANGELOG:
  - wagi **MXFP4/MXFP6** natywne dla tensor core 5090;
  - DFlash2 plus **„draft forest”** (drzewo z 2. i 3. wyborem w miejscach niepewności, 1.35: +5% kod, +10% proza dla 1 agenta);
  - harmonogram pewności z DSpark (liczba draftów per rozmowa i runda);
  - wspólna pula stron KV 512 tokenów;
  - eviction „Belady” według kolejki (+20% obsłużonych tokenów promptu);
  - KV RAM i dysk.
- Liczby:
  - Tiny 12.70 GiB KLD 0.058: 537–540 t/s na kodzie przy **+20% OC pamięci** i własnym promptcie;
  - stock w pomiarze YASAKANI: 466 (kod), 440 (edycja), 238 (proza);
  - Medium 15.39 GiB KLD 0.030: 436.
- `giveen/Decapybara` ([repo](https://github.com/giveen/Decapybara)) to deklarowana „rekonstrukcja” (megakernel, mx_gemv…). Bez dowodu zgodności, uznaję ją za niewiarygodną `[INFERENCE]`.

**Werdykt:**
- Rekord „najszybszy na 5090” bierze się z OC i własnego promptu. Na stock w pomiarze YASAKANI przegrywa.
- Po normalizacji (kod 250, edycja 236, proza 128 →XTX) jest za nami na edycji (433.8). Na świeżym kodzie nie mamy porównania greedy.

**Akcja:**
- zanotować „draft forest” (drzewo tylko w niepewnych miejscach) jako wariant do R24s (drzewa dla prozy, ceny węzłów). Drzewa GDN u nas kosztują 10+ dni (R18), więc niski priorytet;
- watch na publikację kodu.

## 11. NInfer (delta od `a928f899`) – osobno

[Repo](https://github.com/Neroued/ninfer) @ `a754fcf3` (2026-11-02, master), 121 commitów od R32f. Zawartość:
- prawie wyłącznie GLM-5-Next i DGX Spark TP2 (MoE NVFP4/FP8, MLA kpool);
- dashboard i telemetria;
- poprawki serwera (zagłodzenie przy presji kontekstu);
- dokument wydajności 27B oznaczony jako „historyczna kampania”.

Na LocalMaxxing (zapytanie `leaderboard?hfId=Qwen3.8-27B&hardwareName=RTX 5090&since=2026-10-21`) po 10-21 nie ma nowego wpisu NInfer dla 27B. Najnowsze wpisy to tqLLM TQ_L 414/354 (10-27). Wyniki 334.4 (oficjalne NVFP4) i 510.7 (QAT, inny model) bez zmian.

Ekosystem:
- forki: `ninfer-5090-windows`, `ninfer-2080ti-22g`, `ninfer-v100`, `omp-ninfer`, `ninfer-kvmem-actkv`;
- z NInfer wyrosły ignis (§12) i wpływ na mkyt (trik MXFP8 z jednostkowymi skalami).

**Werdykt:** dla 27B nic nowego, NInfer przeszedł na duże MoE. **Akcja:** w watch zawęzić do `docs/performance/qwen3.8-27b.md` i `ops/` dla 27B. Pozostałe forki pominąć.

## 12. ignis (gpillon/ignis) – osobno

[Repo](https://github.com/gpillon/ignis) @ `df69a68` (2026-11-05), Apache-2.0. Rust plus C++/CUDA, przepisany od zera na kernelach NInfer, sm_86 i sm_120.

Liczby z README:
- 5090 NVFP4, DFlash2 7 draftów, greedy: 8 promptów kodu geomean 367, przewidywalny kod 491, proza 167, 8 linii 1065;
- prefill 9717 t/s przy 46K.

Techniki:
- **runda dla 1 linii to 1166 węzłów grafu, 15.81 ms, GEMM w 100% rooflinu, głowica 86%, przerwy 4.8%**;
- top-k draftera przepisany (3145 → 44 µs, **+21% dekodu**: dostawiony kernel był wąskim gardłem);
- KV „hq-e8-2b” 9216 B/token (×7.11 vs bf16, KLD +0.018–0.022);
- prefill atencji na skompresowanym KV bez płaszczyzn BF16 (+30–53%, −1.02 GB);
- embedding w pinned RAM (~1 µs na token);
- **wersja 16 GB**: trellis ~3 bpw 12.5 GiB (KLD 0.77× NVFP4, MMLU-Pro 65.84 vs 67.97 BF16), na 5090 ograniczonym do 16 GiB 416 t/s kod przy 8K.

Normalizacja: proza 167 → 89.5 na XTX, w przybliżeniu parytet z naszym en-chat 87.8 i poniżej pl-prozy 99.8 (inne T, inny język).

**Werdykt:** rzetelny (findings z A/B w `docs/findings`). Przewaga ignisa to format i DFlash2 na kodzie, nie proza. Lekcja „zmierz dostawiony kernel” jest uniwersalna. **Akcja:** u nas sprawdzić czas top-k i samplera w kroku. R36 podał top-k 0.11 ms z 27.38 ms, więc nie ma tu +21% `[INFERENCE]`. Nic do zrobienia. Wersję 16 GB (trellis 12.5 GiB) dopisać do argumentu „format” (§13 E5).

## 13. mkyt (mkyt/qwen3-27b-5090) – osobno

[Repo](https://github.com/mkyt/qwen3-27b-5090) @ `eea3cbc` (2026-11-03), MIT. C++/CUDA od zera, tylko 5090.

Liczby przy 400 W:
- kod / JSON / proza 386 / 500 / 258;
- 8 żądań 1395;
- TTFT 152K 23 s;
- KV 605 504 tokenów w 32 GB.

[decisions.md](https://github.com/mkyt/qwen3-27b-5090/blob/eea3cbc/docs/decisions.md) to najcenniejszy dokument rundy: każda decyzja ma pomiar i listę porzuconych wariantów.
- Dekod:
  - skinny GEMM `mma.sync` z pierścieniem `cp.async`: 1.3–1.67 TB/s;
  - graf + PDL „trigger first”: 33.5 → 11.9 ms;
  - ładunki niezależne od poprzednika wydawane przed wait;
  - porzucone: split-K przez klastry, opóźniony zapis stanu GDN, RMSNorm w pętli GEMM, ciągły prefetch L2.
- Weryfikacja atencji:
  - 48 kolumn (token, głowa) upakowane w 6 kafli n8 (512 → 384 MMA);
  - FP8 MMA na KV NVFP4: krok przy 131K −7.9%.
- Spekulacja:
  - DFlash2 łańcuch 8;
  - weryfikacja GDN bez zapisu stanu, następny krok przelicza przyjęte (= nasze S4);
  - draft w NVFP4 przy tej samej akceptacji;
  - **słownik draftu 128K** (64K psuł JSON);
  - **drzewa 2–4 ścieżek: +4–23% tok/krok, ale krok 14.1 → 15.7–20 ms, netto ~0**;
  - **lookup nie jest domyślny**: DFlash2 i tak przyjmuje 7.91/8 na przepisaniu pliku, a na JSON lookup obniżał akceptację;
  - **bez MTP**: w SGLang MTP wygrał tylko na japońskiej prozie (+17%).
- Wagi `gdnfp4`:
  - tylko projekcje GDN w NVFP4, atencja w FP8;
  - pełne NVFP4 psuło **równoległe tool-calle** (BFCL parallel 79 → 65.5%), przyczyną były projekcje atencji;
  - to cenny wynik jakościowy dla każdego 4-bit formatu.
- Nie zrobione: megakernel („po grafach i PDL kernele poza GEMM to ~1 ms z 11–12 ms”).

Dla nas:
- „Bez MTP, bo DFlash2 lepszy” u nich, a u nas odwrotnie na PL/T=1. Zgodne z ich własnym wynikiem dla japońskiej prozy: MTP wygrywa na prozie nieangielskiej.
- Wynik BFCL parallel to sygnał, by **mierzyć równoległe tool-calle** po każdej zmianie kwantu lub KV.

**Werdykt:** najlepszy wzór dokumentowania decyzji. Technicznie potwierdza nasze wybory (S4, brak megakernela, MTP dla prozy nieangielskiej). **Akcja:**
- (1) do fabryki i bramki jakości dodać BFCL parallel (albo nasz test równoległych tool-calli), szczególnie przy KV q4_0 (§13 E3);
- (2) „pakowanie kolumn GQA w kafle n8” odpowiada naszemu `kvq` (kafle 16 wierszy). Tu przechodzi w E1.

## 14. qwen-warp (tuan3w/qwen-warp): najwyższy dekod przy 262k na 3090

Repo nie było w wejściu. Znalazłem je przy wyszukiwaniu „cuda.fast”; ważne dla tezy „262k na 24 GB”.
[Repo](https://github.com/tuan3w/qwen-warp) @ `146a654` (2026-11-05), MIT.

- Model: Swift-1.5 INT4. Silnik: graf CUDA z fuzjami W4A16, MTP k ≤ 3 plus ogon prompt-lookup (do 8 wierszy).
- Dekod przy 32k / 100k / 190k / 262k: 124 / 115 / 102 / 94 t/s. Prefill 963 t/s przy 262k.
- **KV 4-bit** ([KV_CACHE.md](https://github.com/tuan3w/qwen-warp/blob/146a654/docs/KV_CACHE.md)):
  - rotacja Walsh–Hadamard 256, 16 poziomów z kompandowaną siatką, 4 skale log 8-bit na wektor (4.125 b/el.);
  - **dokładne fp16: 4 pierwsze tokeny i pierścień 256 ostatnich** (+34 MiB);
  - wzmocnienie dekodera 1.0075.
  - dKL vs bf16: 0.51% → **0.069%**;
  - **tool-call dla minimalnego schematu: 46% → 92–96%** (bf16 91%);
  - igła przy 100k: z „zawsze chybiona” na „zawsze trafiona”.
- Lekcja z ich portu: pierwsza wersja atencji była **15–20% wolniejsza przy 190k**, bo dekwantyzowała ten sam kafel raz na kafel zapytań w weryfikacji wielowierszowej. Naprawa: raz na grupę. To dokładnie nasz otwarty punkt R18 #5 („każdy kafel czyta K/V od nowa”, `ceil(6N/16)` przejść).

Normalizacja: 102 / 94 t/s × 1.026 ≈ **105 / 96 vs nasze 74.5 przy 199k** (XTX, T=0, W16). Nasze 94k 105.6 ≈ ich 100k 115 × 1.026 = 118.

**Werdykt:** najmocniejszy dowód, że mamy zapas przy ≥ 100k: ~+12% przy 100k i ~+35% przy 190–200k. Kierunek jest znany (jedno przejście KV, mniejsze bajty KV na token). **Akcja:** E1 i E3 w §17.

## 15. TensorFold 1.1.1–1.2.2 i konkurs cuda.fast / mlx.fast (Qwen3.8-27B)

TensorFold ([releases](https://github.com/ashhart/TensorFold/releases), HEAD `cde4fe7`, 2114 commitów v1.1.0 → v1.2.2):
- **HIP w końcu ruszył, ale pod gfx1151 (Strix Halo) i gfx1201**:
  - dekod atencji „cztery klucze na warp” przy długich zakresach: +7.5–18.9% dekodu na gfx1151 przy 32/64K (#1932);
  - węższe kafle dla 1–2 wierszy: +5% na 27B (#1855);
  - matrix-core prompt tile bez spillów: +24.5% przy 64k;
  - tabela strojenia RDNA4.
- gfx1100: tylko opcja clang 21, „nie uruchamiane na gfx1100” (1.2.0).
- HIP dalej odmawia `--drafter` (#1044), a tablica wyników nie publikuje ROCm.
- Benchlab (3090): pisanie 170 (drugie miejsce), prefill ×3 wolniejszy.

Konkurs Layr-Labs/Yukon: [cudafast-qwen38-27b-tf-engine](https://github.com/Layr-Labs/cudafast-qwen38-27b-tf-engine) @ `1af264e` (GB10) i [mlxfast-qwen38-27b-tf-engine](https://github.com/Layr-Labs/mlxfast-qwen38-27b-tf-engine) @ `28c5b13` (M5 Max), do 6.11.
- Wynik `prefill_gain^0.25 · decode_gain^0.75` wobec trybu serial, przy DFlash depth 1 z przypiętym drafterem i tą samą taśmą tokenów.
- **Prompt to `public-longcopy-gate-english-496`, czyli kopiowanie tekstu**. Prywatny prompt produkcyjny jest „podobny”. Tryb dekodu nagradza więc drzewo i kopię.
- Najlepsze wyniki: CUDA 2.759 (PR #650 i późniejsze), MLX 1.810.
- Bazowy krok DFlash depth-1 na GB10: ~22 ms/token ([#18](https://github.com/Layr-Labs/cudafast-qwen38-27b-tf-engine/pull/18)).
- Kto: prawie wyłącznie agenci (Claude Opus 5.5 w Claude Code, GPT-6.1 w Codex/omp), składający cudze kawałki z deklaracją zależności.

Zgłoszenia awansowane (CUDA):
- [#18/#21](https://github.com/Layr-Labs/cudafast-qwen38-27b-tf-engine/pull/21): kontekst 8192 zamiast 32768. Mniejsza alokacja KV w mierzonej fazie, a nie szybszy kernel: artefakt benchmarku;
- [#27](https://github.com/Layr-Labs/cudafast-qwen38-27b-tf-engine/pull/27): grupowany prompt GEMM dla projekcji z tym samym wejściem;
- [#50](https://github.com/Layr-Labs/cudafast-qwen38-27b-tf-engine/pull/50): przeliczenie zatwierdzonych wierszy GDN wpięte w skan następnej weryfikacji (= nasze S4);
- [#73](https://github.com/Layr-Labs/cudafast-qwen38-27b-tf-engine/pull/73): PDL dla kerneli klejących. Wynalezione przez wycinanie fragmentów w mikrobenchu: „removing the MMAs saved ~50%”, adresowanie po barierze;
- [#152](https://github.com/Layr-Labs/cudafast-qwen38-27b-tf-engine/pull/152): strumienie projekcji;
- [#161](https://github.com/Layr-Labs/cudafast-qwen38-27b-tf-engine/pull/161): **słownikowe kodowanie skal i biasów MLX** (12 bitów zamiast 2×bf16 na grupę, ~3% bajtów, +3.07% dekodu);
- [#650](https://github.com/Layr-Labs/cudafast-qwen38-27b-tf-engine/pull/650): głowica weryfikacji przez 2-bitową kopię z dokładnym przeliczeniem.
- Organizator podniósł sufit prefillu 2.0 → 3.0 ([#1785](https://github.com/Layr-Labs/cudafast-qwen38-27b-tf-engine/pull/1785)), bo 5 uczciwych runów odrzucono przez wolniejsze ramię kontrolne. „Box draw” (ten sam kod 2.481 vs 2.522 na różnych maszynach) decydował o awansie.

Dla nas:
- Słownikowe skale nie dotyczą K-quantów: skale Q4_K to ~0.5 bita na wagę, MLX affine g64 bf16 to ~1 bit.
- Grupowane projekcje, PDL i S4 już mamy (fuzje A3–A6, PM4, S4).
- Nowe dla nas: nic na XTX.

**Werdykt:** TensorFold na gfx1100 dalej w miejscu (AMD dalej nasze), ale idzie w RDNA3.5. Konkurs mierzy kopię na GB10: ciekawy jako zapis myślenia agentów, nie jako liczby. **Akcja:**
- (1) watch: TensorFold `zig/kernels/hip/decode/plan.hip` (#1932). gfx1151 to ten sam rodzaj ISA co gfx1100. Kiedy dojdą do gfx1100, porównać z `kvq`;
- (2) wzór agentowy „składaj opublikowane, niezależnie zmierzone kawałki z deklaracją zależności” przenieść do fabryki (R16h). Za to samo dostajemy ostrzeżenie: agenci w konkursie wygrywają na artefaktach fazy pomiaru (ctx 8192).

## 16. gpu.nz: tabela VRAM – osobno

[Strona](https://gpu.nz/en/guides/llm-vram-table), aktualizacja 2026-10-20. Qwen3.8-27B Q4_K_M: wagi 15.3 GiB, 17.2 GiB przy 8k, 18.7 GiB przy 32k, KV f16. Wzór: `tokens × full_attention_layers × 2 × kv_heads × head_dim × 2 B` + runtime 0.75 GiB + 512 × vocab × 4 B.

Sprawdzenie z naszym modelem (`product/PLAN-NV-V2.md:52`, R56):
- KV f16 na token: 16 warstw × 2 × 4 × 256 × 2 B = **65 536 B (64 KiB)**. Zgodne z nimi i z qwen-warp („bf16 64 KiB”).
- Przyrost 8k → 32k = 24 576 × 64 KiB = **1.50 GiB ✓**.
- Runtime: 0.75 + 512 × 248 320 × 4 B = 0.75 + 0.47 = 1.22 GiB. 15.3 + 0.5 + 1.22 = 17.0 wobec ich 17.2. Różnicę ~0.2 GiB tłumaczy stan GDN, którego nie pokazują: S 144 MiB + R 5.6 MiB, bufor RS z rollbackiem 252 MiB.

Czego tabela nie uwzględnia:
- (a) **warstwa MTP**: +1 KV layer (q4_0: +1152 B/token) i ~0.4–0.9 GB wag głowicy;
- (b) **bufory spekulacji**: u nas RS z rollbackiem 252 MiB; w silnikach z kopią stanu GDN per wiersz to 0.9 GiB na żądanie (mkyt);
- (c) bufor compute prefillu i konwersja K/V q4_0 → f16 w FA (~2 KiB/token/warstwę, przy 262k ~512 MiB, R59);
- (d) **zmierzony u nas nachylenie 29.1 KiB/token przy KV q4_0** (R56 §2) wobec teoretycznych 18.4. Nadmiar ~10.7 KiB/token jest niewyjaśniony (podejrzane bufory spekulacji/lookup).

Werdykt:
- Liczby gpu.nz dla f16 i krótkiego kontekstu są poprawne.
- Przy 262k zaniżają realne zużycie: f16 KV = 16 GiB, więc 262k nie mieści się na 24 GB. To mówią poprawnie dopiero przez wzór.
- Dla naszego q4_0 każdy estymator oparty tylko na wzorze myli się o ~2.7 GiB przy 262k (10.7 KiB × 262 144).

**Akcja (bez GPU):**
- (1) sprawdzić, czy estymator kontekstu w aplikacji Enigma (R04 §2.2, rekomendacje z R61) liczy 16 warstw + MTP i **zmierzone** nachylenie 29.1 KiB/token, a nie teoretyczne 18.4;
- (2) na CPU, czytając kod alokacji `llama-context`, ustalić źródło 10.7 KiB/token (R56 zostawił to otwarte). Jeśli to bufor lookup/spec rosnący z ctx, przyciąć go: to bezpośrednio wydłuża maksymalny kontekst na 24 GB.

## 17. Co z tego dla nas (ranking zysk / wysiłek)

| # | eksperyment | źródło idei | oczekiwany zysk | wysiłek | ryzyko | bramka / kill |
|---|---|---|---|---|---|---|
| **E1** | **`kvq`: jedno przejście po K/V dla wszystkich kafli N×G w weryfikacji** (dekwantyzacja kafla raz na grupę, nie raz na kafel zapytań) | R18 #5 (nasze, niezrobione); potwierdzenie: qwen-warp (−15–20% przy 190k przed poprawką), mkyt P4-14, elpis 3032 | **+8–15% dekodu przy 94–199k** (XTX), bitowo | ~5 dni | niskie (bitowo, md5) | long_ctx_bench 94k/199k ABBA; kill < +3% przy 94k |
| **E2** | **Profil „kod/T=0”: MTP n=6–7 z mniejszym słownikiem draftu (32k), opt-in według klasy** | turboderp: MTP-7 157 vs MTP-4 129 (+22%, greedy html, 3090), rzadka głowica 16k; nasze R35 (n=5 +6.8% reasoning T=0), R24q (n=6 +0.8% czat) | **+5–10% na kodzie/JSON przy T=0**, 0 ± 1% na czacie PL | 1–2 dni (słownik z CPU, lustro akceptacji R40 offline) + 20 min GPU | średnie: OOV słownika dla PL (64k chybia 4.96% pl-prozy) | najpierw CPU: lustro tok/krok n=4/64k vs n=7/32k; potem ABBA; kill: kod < +3% albo czat < −1% |
| **E3** | **KV q4_0 z dokładnym pierścieniem f16 (256 ostatnich) i 4 sinkami** w `kvq` (koszt +34 MiB) | qwen-warp (tool-call 46% → 92–96%, dKL 0.51 → 0.069%); mkyt (BFCL parallel wrażliwe na kwant) | jakość agenta (tool-calle, igła); szybkość ±0 | krok 0: pomiar 1 h GPU; implementacja 2–3 dni | niskie | krok 0: odsetek poprawnych tool-calli (200 prób) i dKL przy 32k, q4_0 vs f16. Kill, jeśli różnica < 3 pp i dKL < 0.1% |
| E4 | Wspólny punkt odniesienia: 12 zadań NInfer + edycja `textwrap` + JSONL (zestaw YASAKANI) na XTX | YASAKANI, NInfer fixture | wiedza (porównanie 1:1 z 5090) | 0.5 dnia + 15 min GPU | — | — |
| E5 | Mniejszy format wag (klasa trellis, 12.4–12.5 GB przy KLD ~0.02) | YASAKANI, ignis 16 GB, elpis EXL3 | **~+25–35% dekodu na każdej klasie** (−26% bajtów) `[INFERENCE]` | duży: nowy typ i kernele HIP (ik_llama KT częściowo) | **wymaga decyzji użytkownika** („nie zmieniamy kwantów”) | najpierw CPU: KLD istniejących GGUF ≤ 13 GB (57g) |
| E6 | Prefill stratny „KVA” (stan późnych warstw) dla zimnych promptów ≥ 16k | Strata 0.2.7 | TTFT −10…−15% `[INFERENCE]`, dekod MTP do −11% | 3–4 dni | wysokie (agenci, ekstrakcja) | pilot CPU na KL pierwszego tokenu; kill KL > 0.02 |
| E7 | Enigma: drabina degradacji pamięci zamiast cięcia ctx; estymator z nachyleniem 29.1 KiB/token | Strata 0.2.10, gpu.nz | UX na 8–16 GB | 1–2 dni (produkt) | niskie | — |

Formaty doświadczeń („baseline → teraz → przyrost %”):
- **E1:** long_ctx_bench T=0, 256 tok., topka. Baseline 94k **105.6** / 199k **74.5** t/s (`WYNIKI-XTX-2026-10-19.md:85-86`) → teraz ? → przyrost oczekiwany +8…+15%. Bitowo: md5 T=0 równe bazie.
- **E2:** (a) mvs T=0 baseline **433.8** → ? (oczekiwane 0…+3%); (b) klasa kod/JSON T=0 (E4 lub reasoning-v1) baseline do zmierzenia → ? (+5…+10%); (c) spec_sweep T=1 baseline **114.8** → ? (kill przy < −1%).
- **E3:** tool-call (minimalny schemat, 200 prób, 32k kontekstu przed pytaniem) baseline q4_0 = ? / f16 = ? → q4_0 + pierścień = ? → przyrost w pp. Szybkość: long_ctx 94k 105.6 → ? (oczekiwane ±1%).

Dla aplikacji Enigma na CUDA (5090/Blackwell):
- Rynek ma dziś 5+ silników z NVFP4/MXFP4 i DFlash2 (mkyt, ignis, NInfer, MegaCapybara, YASAKANI) na poziomie ~2× upstream llama.cpp.
- Nasza ścieżka CUDA na GGUF K-quantach nie dogoni ich na 5090 bez natywnego FP4 `[INFERENCE]`.
- To decyzja produktowa: albo przyjąć, albo integrować obcy silnik dla Blackwella (licencje MIT/Apache: mkyt, ignis).

## 18. Jak myślą autorzy (wspólne wzory)

1. **Najpierw roofline i rozkład kroku, potem kernel.** mkyt (fazy 0–7, każda decyzja z pomiarem), ignis (1166 węzłów grafu, 4.8% przerw), elpis (krok vs podłoga DRAM 51 → 65%).
2. **Porzucone próby są spisane.** mkyt „Not done”, elpis „Not kept”, Strata „Measured, not changed”. U nas jest podobnie (`wyniki-negatywne`).
3. **Bramki jakości specyficzne dla agentów:** równoległe tool-calle (mkyt), poprawność schematu (qwen-warp), agent loops plus ekstrakcja (Strata KVA). Igła nie wystarcza, przeszła we wszystkich wariantach Straty.
4. **Błędy pomiaru opisane publicznie:**
   - ciepłe vs zimne (PR #4366: +39% → +4%);
   - pętla greedy zawyża t/s (YASAKANI: 424 → 303);
   - wrapper serwera serializuje (benchlab: ×7 → ×1.2);
   - OC pamięci w rekordzie (MegaCapybara 540 vs 466 stock);
   - artefakty fazy (konkurs: ctx 8192).
5. **Agenci jako optymalizatorzy (konkurs Yukon):** setki zgłoszeń Claude Opus 5.5 i GPT-6.1, które składają cudze kawałki i ćwiczą mikrobench przez wycinanie fragmentów kernela. Wynik zależał od „losowania maszyny” (2.481 vs 2.522 ten sam kod). Potwierdza naszą zasadę ABBA i stałej maszyny.

## 19. Do ZRODLA (wersje badane)

| źródło | wersja / data | werdykt |
|---|---|---|
| Strata (github.com/Niko1221/Strata) | v0.2.3–v0.2.11 (silnik 0.1.48 → 0.1.57), klon `9f7d977d` 2026-11-05 | gfx1100 i gęsty 27B: nic; KVA stratny, DFlash2 domyślny, TP wiele kart |
| Strata PR #4366 (`DS4_FAT_ROWS`) | zamknięty, w 0.2.8 opt-in | +39% → +2–6% (ciepłe vs zimne); lekcja pomiaru |
| basalt (github.com/jesdga95/basalt) | `dc047a7` 2026-11-04, v0.2.1 | głowica Q8_0 w płaszczyznach dokładna; dla Q6_K nie; 6950/273 z wejścia nieznalezione |
| elpis (github.com/gildrb/elpis) | `13e8b59` 2026-10-29 (finished) | najlepsza metoda (pre-rejestracja, Bend); 262K 45.6 ms/rundę |
| benchlab engines-27b-3090 | post 2026-11-03, rerun 11-05 | rzetelny; turboderp: MTP-7 ≈ DFlash2 |
| HyperQwen (github.com/syv-ai/HyperQwen) | `6ab9bd0` 2026-11-03 (163 commity od `95ee3b6`) | KV int8/fp8 dla długiego kontekstu na NVIDIA, port LSA |
| YASAKANI (x.com/yasakani_dev 2117521489885090271, 2117529802844610956) | 2026-11-03, bez kodu | klasa kopii/struktury; po normalizacji parytet na edycji |
| MegaCapybara (github.com/perkel666/MegaCapybara) | v1.40 `bdfc1b8` 2026-11-04 (1.39 11-01), binarki | rekord przy OC; draft forest; brak kodu |
| NInfer (github.com/Neroued/ninfer) | master `a754fcf3` 2026-11-02 | dla 27B nic nowego (GLM/Spark) |
| ignis (github.com/gpillon/ignis) | `df69a68` 2026-11-05 | top-k draftera +21%; trellis 16 GB 12.5 GiB |
| mkyt (github.com/mkyt/qwen3-27b-5090) | `eea3cbc` 2026-11-03 | wzór decisions.md; BFCL parallel wrażliwe na kwant atencji |
| qwen-warp (github.com/tuan3w/qwen-warp) | `146a654` 2026-11-05 | 262k 94 t/s na 3090; KV rot.+pierścień; potwierdza E1 |
| TensorFold (github.com/ashhart/TensorFold) | v1.1.1–v1.2.2, HEAD `cde4fe7` 2026-11-05 | HIP rusza na gfx1151/1201, gfx1100 nie; drafter na HIP odmawiany |
| Konkurs cuda.fast / mlx.fast Qwen3.8-27B TF (Layr-Labs) | CUDA `1af264e`, MLX `28c5b13`, 2026-11-05; wynik 2.759 / 1.810 | prompt = kopia; techniki znane; wzór pracy agentów |
| gpu.nz llm-vram-table | 2026-10-20 | f16 zgodne z naszym modelem; pomija MTP, bufory spec, nasze +10.7 KiB/token |
| LocalMaxxing API (leaderboard 5090, Qwen3.8-27B, since 10-21) | 2026-11-05, 1 GET | tqLLM TQ_L 414/354 (10-27); NInfer bez nowych |

## Źródła

- Strata: https://github.com/Niko1221/Strata/releases (v0.2.3 … v0.2.11), https://github.com/Niko1221/Strata/blob/9f7d977d220e9fdf2ec53cf2620cdadac1cfb24e/docs/KVA.md , https://github.com/Niko1221/Strata/blob/9f7d977d220e9fdf2ec53cf2620cdadac1cfb24e/docs/AMD_HIP.md , https://github.com/Niko1221/Strata/pull/4366
- basalt: https://github.com/jesdga95/basalt (README, `docs/precision/two-stage-head.md`, `docs/unified-kernel.md`, `docs/changelog/0.1.0.md`, `0.2.0.md`, `0.2.1.md`, `docs/community/benchmarks.json`)
- elpis: https://github.com/gildrb/elpis (README, `bench/RESULTS.md` §4, §10–§13)
- benchlab: https://benchlab.ironyaditya.xyz/posts/2026-11-03-engines-27b-3090/ ; turboderp: https://x.com/turboderp_/status/2117949950839427117 , https://x.com/turboderp_/status/2117961106756899275
- HyperQwen: https://github.com/syv-ai/HyperQwen (README, `lsa/README.md`, `docs/optimizations.md`, `git log 95ee3b6..6ab9bd0`)
- YASAKANI: https://x.com/yasakani_dev/status/2117521489885090271 , https://x.com/yasakani_dev/status/2117529802844610956 (treść: https://api.fxtwitter.com/)
- MegaCapybara: https://github.com/perkel666/MegaCapybara (README, CHANGELOG), https://github.com/perkel666/MegaCapybara/releases/tag/v1.39 ; https://github.com/giveen/Decapybara
- NInfer: https://github.com/Neroued/ninfer (`git log a928f899..a754fcf3`)
- ignis: https://github.com/gpillon/ignis (README)
- mkyt: https://github.com/mkyt/qwen3-27b-5090 (README, `docs/decisions.md`)
- qwen-warp: https://github.com/tuan3w/qwen-warp (README, `docs/ARCHITECTURE.md`, `docs/KV_CACHE.md`)
- TensorFold: https://github.com/ashhart/TensorFold/releases (v1.1.1–v1.2.2), http://tensorfold.dev/guide
- Konkurs: https://github.com/Layr-Labs/cudafast-qwen38-27b-tf-engine (TASK.md, benchmark.json, `correctness_prompts/`, PR #18, #21, #27, #50, #73, #152, #161, #650, #1785), https://github.com/Layr-Labs/mlxfast-qwen38-27b-tf-engine (PR #166, #349, #1124)
- gpu.nz: https://gpu.nz/en/guides/llm-vram-table
- LocalMaxxing: https://www.localmaxxing.com/api/leaderboard?hfId=Qwen3.8-27B&hardwareName=RTX%205090&since=2026-10-21
- Nasze: `wiki/REKORDY.md:102-137`, `product/WYNIKI-XTX-2026-10-19.md:38-55,83-86`, `product/research/18-nastepna-fala.md` (#5, #15), `32f-ninfer-tqllm-dflash2.md`, `36-xtx-qwen-roadmap.md` §3, `56-orca-3090.md` §2, `product/PLAN-NV-V2.md:52`, `wiki/kernele/gdn-replay.md`, `wiki/kernele/fattn-kvq.md`
