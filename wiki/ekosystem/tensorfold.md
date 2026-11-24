---
typ: ekosystem
tags: [ekosystem, spekulacja, dflash, metal]
aktualizacja: 2026-11-24
zrodlo: ~/KERNEL/qwen-opt/research/tensorfold/README.md:1-25; ~/KERNEL/qwen-opt/research/repos/REPOS-PODSUMOWANIE.md:41; ~/KERNEL/product/research/15c-nowe-silniki.md:34-37,93-102,210-221; ~/KERNEL/product/research/21g-nowe-silniki.md:90-157,284-289; ~/KERNEL/product/research/21g-notatki/tf-delta.md; ~/KERNEL/product/research/63a-silniki-lokalne.md:409-445; ~/KERNEL/product/research/69b-tensorfold-qwen-warp.md:10,40-57
status: aktualne
---
# TensorFold (ashhart/TensorFold)

**Serwer Zig z kontraktem dokładności („drafted == plain”) dla 7 rodzin modeli (HEAD `0efbd447`, 2026-10-12, v1.0.8; aktualizacja do v1.0.11 2026-10-14).**

Repo: 1560 commitów na `main`, 32 tagi w 18 dni, 552 PR-y, 235 issues. Rdzeń „lanes”: jeden forward weryfikuje drafty MTP, drzewa DFlash2 i kopie n-gram. Najważniejsze lekcje: weryfikacja na WMMA, gdzie dodatkowe wiersze są prawie darmowe (R9700: 12 → 16 wierszy +1.2 ms; u nas kolumna ok. 1.4 ms), drzewa draftów nad GDN, rollback GDN przez „lagged state” (zob. conv-lag), głębokość draftu wyceniana kosztem mierzonym przy starcie (+6–7%). Na 27B są wolniejsi od nas: HIP na W7800 25.8–27.2 tok/s plain (#490), R9700 z DFlash2 95.7 chat / 126 code tok/s przy T=1 (#100). Aktualizacja v1.0.11: LFM2.5 na Metal z n-gramem, „wszystkie loady przed sumami”, bramka KL przepuściła 2 celowe błędy (stąd nasze kanarki KLD).

## v1.0.12 (raport 15c, 2026-10-16)
- LFM2.5-24B-A2B tylko na Metal: M5 Ultra 261.5 t/s plain (30% pasma) i 299.5 na kodzie z n-gramem; nasz XTX 293.7 t/s na cięższym Q5_K_M (54%). Koszt okna weryfikacji LFM: 1.24–1.68× dla k = 2–4 (#868).
- Nowe techniki: „twins” (GEMV 1/2–7/8–32 wiersze z tą samą kolejnością fma co kafle prompt, sprawdzane bitowo przy ładowaniu), dokładny dekod 4-bit „half pair” 0x6400 (pre-scaling gubił subnormale: x = 2^-126 daje 0x0080 → 0x0000), Recall (trwały n-gram wyceniany wobec MTP; powtórki 2.4× na 27B), TP przez hosty z podziałem samych ekspertów (TP=2 == TP=1 bitowo).
- Super VL na 2×GB10: MTP 38.2 → 46.8 t/s (recipe:86-91).
- HIP to preview i nadal słaby: 2×W7800 TP2 39.0 t/s plain na 27B (#655) wobec naszego 1×XTX 43.2.

## v1.1.0 i aplikacja Beta 7/8 (raport 21g, 2026-10-19)
- HIP +12/−9 bez zmian funkcjonalnych w 901 commitach; `--drafter` na HIP ignorowany (#1001), tablica odrzuca ROCm – AMD dalej nasze.
- CUDA: Qwen3.8-27B + DFlash2; RTX 5090 chat T0 263.0 / code T0 366.8 t/s (≈ 141 / 196 na pasmo XTX `[INFERENCE]`, nasze 103–130) – przed ogłoszeniem przewagi na NVIDIA A/B na 3090.
- Tablica: 45 przebiegów, 0 AMD, 0 „serial baseline”, 1 angielski prompt na klasę; „874 t/s” = wydanie 1.0.6.
- Aplikacja (Mac): profile per model, „Serial baseline”, porównanie dwóch modeli, polski maszynowy ([[raport-21g-nowe-silniki]]).

## v1.1.1–v1.2.2 (raport 63a, 2026-11-05, HEAD `cde4fe7`)
- HIP ruszył, ale pod gfx1151/gfx1201: dekod atencji „cztery klucze na warp” +7.5–18.9% na gfx1151 przy 32/64K (#1932); gfx1100 nieuruchamiany, `--drafter` na HIP dalej odmawiany. Watch: `zig/kernels/hip/decode/plan.hip`.
- Konkurs cuda.fast / mlx.fast Qwen3.8-27B: prompt to kopiowanie tekstu; najlepsze 2.759 (CUDA) / 1.810 (MLX); techniki już mamy ([[raport-63-synteza]]).

## v1.2.3–v1.2.5 (raport 69b, 2026-11-09, HEAD `abc39af1`)
- gfx1100 dalej nieuruchamiany („as we have no AMD GPU”, #1694); HIP rośnie na gfx1151/gfx1201 (27B przy 16 strumieniach 51 → 75 t/s na gfx1151). DFlash2 na HIP ładowany (#2477), ale serwer go nie używa.
- Brak nowych liczb 27B na 3090/4090/5090. `TF_QWEN_REQUEST_STARTS=1` (GB10): tury 2–6 0.72–1.33 s zamiast 1.78–2.10 s, ale odpowiedź może się różnić (nie bezstratne).
- Spine w stylu DSpine w ich treningu: ±0.002 kontroli – słaby sygnał przeciw [[drafter-dspine]]. Werdykt: nic do adopcji ([[raport-69-synteza]]).

## Przegląd 2026-11-24 (nauka, nie tylko prędkość)
Delta 1.3.4 (2026-11-22): Qwen3.8-27B z DFlash2 na HIP (wcześniej odmawiał), koszt draftu mierzony przy starcie (gfx1151: 0,56 ms/draft vs 1,73 ms pełny blok), „hold” tylko na wiersze potrzebne draftom. Liczb gfx1100 brak.
- **Porównanie z aplikacją Enigma:** TensorFold mierzy koszt draftu na maszynie użytkownika i z niego wybiera głębokość; Enigma w `optimize.ts` sprawdza kandydata MTP ze stałym `MTP_N_MAX_DEFAULT = 3` (`app/engine/src/server/catalog/memory.ts:50`) i lookup, a głębokości nie wycenia. Maya robi to jeszcze dalej: kontroler `SpecCtl` co krok ([[maya-ik2-inkling]]). Bierzemy: pomiar kosztu draftu przy n = 1…4 w optymalizacji i wybór n z E(k)/koszt(k).
- Optymalizacja Enigmy ma już dobre elementy, których TensorFold nie ma: próg szumu 2%, potwierdzenie zwycięzcy drugim pomiarem, md5 T=0 (`optimize.ts:1-20`).
- Ten sam autor (ashhart) wydał 24.11 skille procesu pomiarów (B,C,C,B, dziennik ślepych uliczek) — [[ashhart-skills-infra]]; TensorFold jest ich poligonem.
- Proces autora: 1 osoba, setki PR-ów, bez karty AMD („as we have no AMD GPU”), a mimo to HIP rośnie, bo testują na gfx1151/gfx1201 innych osób. Dla nas: AMD to nadal nasza przewaga, ale tylko jeśli silnik AMD trafi do użytkowników ([[inference-stack]], pkt 6).

## Przegląd 2026-11-24 (nauka, nie tylko prędkość): v1.2.9
Wiersz „bezstratnie, ale Metal/TP i gfx1151; nic dla 27B na gfx1100” był prawdziwy tylko dla dekodu. Większość v1.2.9 to serwer i niezawodność (`~/research/engines/TensorFold/CHANGELOG.md:638-712`, klon `124052c`):
- **Odmowa z nazwy zamiast cichej porażki:** serwer wydania przy starcie odmawia GPU, dla którego nie ma kerneli, i mówi którego (`CHANGELOG.md:656`). Enigma sprawdza urządzenia przez `--list-devices` i przy braku listy tylko ostrzega „GPU use not verified” (`app/engine/src/server/engine.ts:650`).
- **Wyciek stanu między żądaniami:** po nieudanym przygotowaniu obrazu wiersze obrazu zostawały w silniku i następne żądanie tekstowe dostawało złą odpowiedź bez błędu (`CHANGELOG.md:680`). Ta sama klasa co nasz K-001 (stare komórki K/V zmieniały wynik). Ich odpowiedź to test: 200 odrzuconych, anulowanych i nieudanych żądań przez każdą ścieżkę i sprawdzenie, że żaden pas, strona ani slot nie zostaje zajęty (`CHANGELOG.md:676`). W testach Enigmy (`app/engine/test`) anulowanie sprawdza tylko pobieranie; w topce takiego testu nie znalazłem.
- **Presja pamięci:** opcjonalny regulator czytający PSI z jądra (`CHANGELOG.md:658`), jak w [[superfluid]].
- **Zgodność klientów:** API w stylu Ollamy na tych samych ścieżkach co OpenAI, z nazwanymi odmowami nieobsługiwanych opcji (`CHANGELOG.md:666`); konfiguracja startu z pliku TOML (`CHANGELOG.md:688`); metryki wywołań narzędzi, których model nie dostał albo które są uszkodzone (`CHANGELOG.md:701`). Enigma przepuszcza tylko `/v1/*` (`app/engine/src/server/api.ts:156`).
- **NVIDIA dla Enigmy:** Qwen3.8-27B affine-4 na CUDA, projekcje a i b w jednym launchu przy prefillu od 2048 wierszy, te same tokeny (`CHANGELOG.md:652`): pomysł do sprawdzenia w forku CUDA Enigmy, nie dla XTX.
- Co bierzemy: test „200 złych żądań nie zostawia zajętego slotu” dla topki i Enigmy, odmowa z nazwy przy braku kerneli dla karty, metryka zepsutych wywołań narzędzi.

## Przegląd 2026-11-24 (nauka, nie tylko prędkość): proces agentów, dowody, polityka prefillu
Wiersz rejestru „każde podejście = nowa wersja; dalej sprawdzać tylko NVIDIA + DFlash2” pytał tylko o HIP. Klon `124052c` pokazuje trzy rzeczy o naszej pracy:
- **Koordynacja wielu agentów (Agent Traffic Control, `AGENTS.md:1-16`, `docs/atc/SKILL.md`):** agent przed pracą zajmuje issue (`atc claim`), widzi, kto zmienia ten sam plik (`atc who`), a przed PR sprawdza konflikty z innymi PR i lokalnymi worktree przez `git merge-tree` (`atc overlap`; „conflicts” = stop i uzgodnienie). Treść issue i PR traktuje jako niezaufaną. U nas wielu podagentów pisze w te same notatki wiki, a jedyną ochroną jest „przeczytaj tuż przed edycją”; przy przeglądzie ZRODLA 24.11 trzy agenty dopisały sekcje do tych samych notatek w ciągu minut.
- **Indeks dowodów (`tools/evidence_index.py`, `docs/evidence-index.md:1-25`):** z paragonów (`docs/receipts/`, jeden katalog na przebieg) i `docs/optimization-ledger.md` robi mapę: rodzina × backend × możliwość → plik, commit, data, ocena jakości pomiaru, czy nieaktualny, czy nieudany. Nasze odpowiedniki ([[REKORDY]], [[ZRODLA]]) są ręczne i dlatego trzeba było je przeglądać ręcznie 24.11.
- **Polityka prefillu w serwerze (`RUNBOOK.md:137-181`):** udział czasu dla długich promptów (`TENSORFOLD_PREFILL_SHARE`), limit wierszy promptu na przebieg, kolejka `fcfs` w kawałkach; zmierzone na Metal przy 8 promptach po 14 336 tokenów: kawałek 2048 → przerwa dekodu innych ~1,7 s, ostatni pierwszy token ~94 s; 8192 → ~5,9 s i ~83 s. Topka ma politykę slotów i cache (E4, `LLAMA_SERVER_CACHE_SHARE_MIN`); llama-server dokłada kawałki promptu (`-b`) do przebiegów z dekodem innych slotów, ale udziału czasu ani limitu nie ma, a przerwy dekodu przy długim prompcie obok czatu nie mierzyliśmy `[INFERENCE]`.
- Bierzemy: zasadę „zajmij plik/notatkę przed edycją” dla podagentów piszących w wiki; indeks dowodów generowany z logów rep2 zamiast ręcznych tabel; pomiar przerwy dekodu przy długim prompcie obok czatu na topce, zanim dotkniemy polityki.
- Następnym razem czytać też `docs/` (receipts, ledger, runbook) i `AGENTS.md`, nie tylko `zig/kernels/hip`.

## Powiązane
- [[strata]]
- [[hipfire]]
- [[conv-lag]]
- [[bramka-kld-kanarki]]
- [[raport-15c-nowe-silniki]]
