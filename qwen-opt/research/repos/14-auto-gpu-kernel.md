# 14 — Dogacel/auto-gpu-kernel: co nowego od analizy z 2026-10-03 i co pętla agenta może jeszcze znaleźć u nas

Poprzednie analizy: `~/KERNEL/sources/auto-gpu-kernel.md` (2026-10-03, commit `db02153`), `~/autokernel-amd/reports/06-dogacel-lessons.md`, port pętli `~/autokernel-amd/` (Triton/PyTorch na gfx1100, track A, bez wpływu na llama.cpp: `README.md:74-77`). Tu opisuję **tylko** to, co doszło od tamtej pory, i oceniam pomysły pod nasz stan z 54 łatkami.

Źródła przejrzane 2026-10-14 (klon w `/tmp/repos`, już usunięty):
- upstream `Dogacel/auto-gpu-kernel`: `main` = `db02153` (2026-09-12), gałąź `slurm-backend` `33fef5b`, PR #1 (= v1, już w `main`);
- fork **`ludoo/auto-gpu-kernel` @ `54e3c5f`** (22 commity, 2026-09-15..10-05). Jedyne merytorycznie nowe źródło. Dalej oznaczam go jako `L:`;
- fork `Marcelo5444/auto-gpu-kernel` @ `ca23741` (5 commitów, 09-22..09-25, cuTile);
- `archive/fable/gdn_decode_qk4_v8_d128_k_last.py` z `main`, oznaczany `F:`. Był w repo już wcześniej, ale poprzednia analiza go nie omawiała.

## 1. Co to jest

Harness agenta do pisania kerneli: `kbench` (walidacja i pomiar) plus `kopt` (pętla tur agenta z budżetem). Autor wygrał nim MLSys 2026 FlashInfer contest (B200). Licencja Apache-2.0, 316★, 17 forków. **Upstream nie ma żadnych nowych commitów od 2026-09-12.** Jedyny nowy kod upstreamu to gałąź `slurm-backend` (backend `srun --overlap` do klastrów, `kbench/slurm.py`), dla nas nieistotna.

Wartość nowości jest w forku `ludoo`. Autor optymalizuje nim kernele własnego silnika „sparkle” dla **Qwen3.8-Flash-Next i Gemma 4 na DGX Spark (GB10, sm_121, 48 SM, ~237 GB/s, pamięć zunifikowana)**. Najciekawszy jest `gdn-rec`: GDN o **tej samej geometrii co nasz Qwen3.8-27B** (H=16, HV=48, K=V=128, stan fp32 3 MiB/warstwę) i z **weryfikacją T=5 (draft 4)**, czyli dokładnie jak u nas (`L:examples/gdn-rec/shapes.py:1-34`). Każdy task to plik `configs/*.toml`, który określa cel, pomiar, walidację i „hints” ze zmierzonymi ścianami. Wyników końcowych w repo prawie nie ma: transkrypty leżą na prywatnym hoście `agentlogs.home.qix.it`, który u mnie nie odpowiadał (curl timeout). Znane są tylko wyniki opisane w następnych rundach (patrz T3, T4).

## 2. Kluczowe techniki (nowe; wszystkie liczby to pomiary autora forka na GB10, chyba że zaznaczono)

**T1. Kontrakt „fold” zamiast tolerancji, z jawną listą wolnych osi.**
- Task ustala bitowo dokładną kolejność arytmetyki na element: liczbę akumulatorów, drzewo shuffle, `expf`, kolejność kroków (`L:configs/gdn_rec.toml:26-44`).
- Wolne jest „wszystko wokół”: geometria, staging, sposób czytania i zapisu stanu, rejestry, liczba instancji kernela (`:45-52`).
- Autor zmierzył, które parametry wchodzą do foldu:
  - `tl.dot(A,B,acc=C) != tl.dot(A,B)+C`, bo akumulacja MMA nie jest dodawaniem IEEE (~50% elementów);
  - szerokość K pojedynczego dotu **nie** wchodzi do foldu;
  - kafel (BM/BN/warps/stages) nie wchodził w 81 wariantach GEMM;
  - w attention `num_warps` **wchodził** (1 na 25k elementów) (`L:configs/w4a16_gemm.toml:102-117`, `gemma_attn_chunk_2.toml:165`).
- „Ręczne sondy bitowe zgłaszały EQUAL na zepsutych wariantach, które łapał dopiero pełny suite” (`gemma_attn_chunk_2.toml:165`).

**T2. GDN dla tej samej geometrii (`gdn-rec`).** Baseline ich kernela: t1 20.6 µs, t5 (z zapisem stanu po każdym wierszu) 97.1 µs, chunk 8192 4536 µs (`gdn_rec.toml:63-76`). Diagnozy:
- (a) Lane trzyma ćwierć wiersza stanu (128 B przy stride 512 B), więc odczyt i zapis 3 MiB idą z połową efektywności sektora. **Ten sam load/store przez koalescujący tile w shared memory: t1 20.6 → 11.3 µs** (`:90-99`). Implementacja: `L:examples/gdn-rec/reference.py:105-115,148-188` (tile `[16 wierszy × (128+4)]`, float4 = pełne wiersze 512 B, arytmetyka nietknięta).
- (b) Instancja z tile’em kosztuje +45 VGPR i +31% na chunku, dlatego są dwie instancje (`:96-99`).
- (c) „Ogon fali”: 384 bloki przy limicie 7/SM to dwie fale; pinchunk 7108 µs vs 5.05 ms przy siatce mieszczącej się w jednej fali (`:101-109`).
- (d) Chunk to łańcuch 0.56 µs/krok-wiersz przy podłodze FMA ~0.25. 8 warpów jednej głowy V staguje **te same** wiersze k/q osobno, co daje 8× nadmiarowy ruch L2 (`:111-121`).
- **Niezależne potwierdzenie z `F:`** (B200, kontest): układ „lane trzyma 16 B ciągłego K, lane’y przylegają, jedna instrukcja = pełny wiersz 512 B”. Układ wygodny dla redukcji (ciągłe biegi 32 elementów na wątek) był **~2× wolniejszy** przy B≥16, a store’y degenerowały do read-modify-write (`F:88-100`). Do tego dwie reguły: load stanu wydany przed łańcuchem bramek (`F:43-45`) i duży store przed redukcją wyjścia (`F:77-81`).

**T3. GEMV/W4A16 przy dekodzie (`mconst-thin`, `bf16-gemv`, `w4a16-gemm/decode`).**
- Pomiar „cold chain”: 96 różnych wag po kolei, granica wywołania w mierzonym regionie. Hot daje 18.6 µs, cold 47.4 µs dla tej samej wagi (`mconst_thin.toml:51-59`).
- Myślenie w kategoriach „bajtów w locie na SM”: ~240 KB w locie, żeby pokryć ~1 µs latencji (`:75-81`).
- Wynik pętli (DeepSeek flash): kernel W4A16 od naiwnego **4.11 → 1.1175** czasu Marlina na 18 komórkach (`L:examples/w4a16-decode/README.md:3`, `w4a16_gemm.toml:69`). W wyniku:
  - kafel BM=4 (MMA paduje do 16), żeby oddać shared memory strumieniowi wag: 1.13 vs 1.18 (`w4a16-decode/w4a16_gemm.py:51-70`);
  - **tablica nadpisań per (N,K)**: q_proj +15% z BN=32 (`:76-81`);
  - kolejność siatki „N najszybsze”, żeby rezydentne bloki dzieliły slab x (`:143-151`).
- Lista zmierzonych zer (`w4a16_decode.toml:69-78`):
  - N-coarsening 1.72/1.97 vs 1.24;
  - tańsza dequantyzacja: szum;
  - `.cg`/`evict_last`: zero;
  - ncu: ~80% cykli bez gotowego warpa, czyli strumień ograniczony latencją.
- PDL: −5.7% na łańcuchu 96 wywołań (`:96-105`).

**T4. Attention (`gemma-attn`, `gemma-attn-chunk`, `-2`, `qsa-attn`).**
- Kernel bitowo niezmienny między decode/verify/chunk ma verify 4 wiersze przy 4k w **51.7 µs vs FlashInfer 74.8**: verify kosztuje tyle co decode, bo K/V czytane są raz (tabela w `L:examples/gemma-attn-chunk-2/README.md`).
- Runda 1 na chunku (DeepSeek flash, 12 iteracji) dała **−4.85%**, potem „wszystkie osie strojenia zamknięte” (`gemma-attn-chunk-2/README.md:3`).
- Sonda diagnostyczna: wymuszenie wszystkich adresów K/V jako rezydentnych w L1 daje 8.3 vs 24 ms. Ścieżka pamięci to ~2/3 czasu, bo przy jednym CTA na SM load’y są szeregowane z obliczeniami (`gemma_attn_chunk_2.toml:76,97-104`).
- Brief rundy 2 ma trzy sekcje: „CLOSED AXES” (`:117-131`), „THE QUESTION” (pytanie strukturalne, `:132`) oraz zasadę „lądowanie na zmierzonym suficie to powód, by przeliczyć założenia sufitu” (`:179`).
- Wynik liczony z **komórkami trzymanymi**: geomean komórek celu × geomean `max(1, ratio)` pozostałych 9 komórek. Wygrana na chunku kosztem decode nie przechodzi (`:63-66`).

**T5. Proces harnessu.**
- `kopt` czeka na bezczynne GPU przed pomiarem baseline’u (`L:kopt/cli.py:94-121,173`). Commit `30ad6a1`: „3 z 5 przebiegów pristine zakłócone, baseline 1.29 zamiast 1.0”, bo bench agenta-buildera jeszcze działał.
- Rundy: runda 2 startuje od „survivora” rundy 1 z listą zamkniętych osi. Tani model do strojenia (`w4a16_decode.toml:7`: `deepseek/deepseek-flash`, budżet 10), Opus 5 do reszty (`gdn_rec.toml:7`: `-n 8 --budget 40`).
- Backend `pi` obok OMP (`L:kopt/agent.py:50-141`): dla nas bez znaczenia.

**T6. Fork Marcelo5444 (cuTile).** Deklarowane „~8× na GB10, ~2× na 4090” (`BENCHMARK_RESULTS.md`) pochodzi głównie z usunięcia narzutu hosta: `torch.cuda.synchronize()`, lookup streamu, cache stałych. cuTile to tylko NVIDIA. Dla nas nic.

## 3. Przeniesienie na AMD/HIP/RDNA3

| Technika | Na gfx1100? | Jak / dlaczego nie |
|---|---|---|
| T1 kontrakt fold + wolne osie | **Tak** | Nasze bramki to logit hash, greedy md5 i test-backend-ops, więc już działamy bitowo. Brakuje tylko **spisanej tabeli „co jest w foldzie”** dla każdego kernela. Ważna różnica na naszą korzyść [WNIOSEK]: w ścieżkach int8 (dp4a w MMVQ, WMMA iu8 w MMQ/K4) akumulacja int32 jest dokładna i łączna, więc kolejność K **wewnątrz bloku q8_1** jest wolna. W foldzie są tylko sumy fp32 (`d·sumi`) między blokami i drzewo redukcji. Dla f16 WMMA z akumulacją f32 (FA kvq P·V) trzeba zmierzyć ich sondę `wmma(A,B,C)` vs `wmma(A,B,0)+C`. |
| T2a koalescujący staging stanu GDN | **Tak, z niepewnym zyskiem** | U nas `gated_delta_net.cu:56-67,88-92`: 4 kolumny na wave32, 8 lane’ów na kolumnę, `s_shard[r] = curr_state[col*128 + r*8 + lane]`. Jedna instrukcja to 4 kawałki po 32 B ze stride’em 512 B, 16× `global_load_dword` zamiast 4× `dwordx4`. Zapisy końcowe wyglądają tak samo (`:284-309`). Odpowiednik GB10: `global_load_dwordx4` po pełnych wierszach do LDS (tile 16 kolumn × 132 floaty ≈ 8.4 KB/blok przy 64 KB LDS/CU) albo transpozycja w obrębie 8-lane’owego segmentu przez `ds_bpermute`/DPP bez alokacji LDS. Arytmetyka i mapowanie elementów na lane’y bez zmian, więc wynik jest **bitowo identyczny z konstrukcji**. Na RDNA3 zysk może być mniejszy niż na GB10, bo linie 128 B w L0 są ponownie używane przez r, r+1, r+2, r+3 [WNIOSEK]. Najpierw ablacja. |
| T2c ogon fali | Prawdopodobnie nie dotyczy | U nas siatka to (48, 1, 8) × 128 wątków = 384 bloki po 4 wave’y, czyli 4 bloki/CU na 96 CU (`gated_delta_net.cu:383-389`). Mieści się w jednej fali, o ile VGPR < ~96 [WNIOSEK; do sprawdzenia w metadanych ISA `.vgpr_count`, bez GPU]. |
| T2d nadmiarowe k/q między blokami jednej głowy | Tak (prefill) | 8 bloków (z) jednej głowy czyta te same wiersze k/q. Dotyczy tylko prefillu (GDN ≈15 ms z 554 ms ubatcha, `research/v2/roadmap.md:25`). |
| `F:` load stanu najpierw, store przed redukcją | Już mamy (load) | Load stanu jest pierwszy (`:88-92`). Kolejność store vs redukcja ma znaczenie tylko w ścieżce z zapisami. |
| T3 cold chain | Już mamy | `mmvq-bench/mmvq_bench.cpp:1-5,29-30`: kopie > 96 MB IC w jednym grafie. |
| T3 tablica per-kształt, BM=4 | Częściowo | Tablica per (typ, N, K) dla MMVQ tak, bo kształty są statyczne. BM=4 to odpowiednik naszego WMMA iu8 K4 dla 9–16 kolumn; przy 1/5 kolumnach zostaje dp4a. |
| PDL | **Nie** | Brak w ROCm 10 (`repos/07-flashinfer.md:68`). Odpowiednik `hipExtAnyOrderLaunch` jest już w `research/v2/roadmap.md:102-105`. |
| T4 sonda „wszystko rezydentne” | **Tak** | Wariant-sonda (nie kernel) MMQ/FA, w którym wszystkie bloki czytają ten sam kafel K/wag (adres z modulo), mierzony w rocprofv3. Odcina koszt ścieżki pamięci od wydawania instrukcji. |
| T4 komórki trzymane `max(1,ratio)` | **Tak** | Nasze kernele obsługują n=1, n=5, n=9–16 i prefill, a dotąd mierzyliśmy klasy osobno. |
| T5 czekanie na bezczynne GPU | **Tak, z poprawką** | `flock /tmp/gpu.lock` już mamy (`repos/06-kernelagent.md:47`), ale lock nie łapie procesu, który ktoś zostawił: incydent K4, serwer na 8097 trzymał VRAM (`NOTES.md:300`). Na AMD sprawdzamy `/sys/class/kfd/kfd/proc/` (PID-y z kontekstem KFD) plus `/sys/class/drm/card0/device/gpu_busy_percent`. Uwaga: `gpu-keepawake` trzyma kontekst KFD na stałe (`NOTES.md:125`), więc potrzebna jest whitelista. W trakcie tej analizy `kfd/proc` pokazywał `llama-perplexity` innego agenta. |

## 4. Pomysły dla nas

**P1. GDN: ablacja, potem koalescujący staging stanu (bitowo).**
- **Co zmienić.** Najpierw sonda w `ggml/src/ggml-cuda/gated_delta_net.cu`: wariant, który czyta i pisze stan jako `float4` po pełnych wierszach (wynik celowo błędny), mierzony rocprofv3 przy weryfikacji. Jeśli kernel spada o ≥ 20%, robimy właściwą wersję:
  - `dwordx4` do LDS (albo `ds_bpermute` w segmencie 8 lane’ów), potem `s_shard[r]` w obecnym mapowaniu;
  - to samo dla zapisu końcowego i `pend_wr` (`:88-92, 284-309`);
  - osobna instancja szablonu, jeśli VGPR wzrosną (lekcja T2b).
- **Zysk [SZACUNEK].** Ostatni pomiar to 638 µs/weryfikację (`NOTES.md:292`), czyli 13.3 µs/warstwę. Ruch to 6.3 MB stanu na warstwę; 48×3 MiB = 144 MiB nie mieści się w 96 MB MALL, więc podłoga przy ~900 GB/s to ~7 µs. Realnie −3…5 µs/warstwę, czyli **−0.15…0.25 ms/krok, +0.5…0.9% t/s Qwena**. Zero, jeśli L0 już skleja te dostępy.
- **Koszt i ryzyko.** Sonda zajmuje 2–3 h, wersja właściwa ~1 dzień. Ryzyko niskie, bo arytmetyka się nie zmienia.
- **Pomiar.** µs kernela GDN w rocprofv3 (min z ≥ 5), `lh.sh` (logit hash) oraz greedy md5 plain i MTP.

**P2. Zadanie dla pętli agenta: FA dla KV q8_0 ze wspólnym GQA, bitowo zgodne z `flash_attn_ext_vec` (LFM).**
- **Brief w stylu `gdn_rec.toml`.**
  - *Reference*: obecny kernel vec, bez zmian.
  - *Kontrakt*: mapowanie wątków per głowa i podział `parallel_blocks` jak w launchu 1-głowowym (`lfm-decode-round2.md:99-101`).
  - *Wolne*: liczba głów Q na blok, staging K/V, raz czytany kafel.
  - *Komórki trzymane*: depth 0 i 8k (nie mogą zwolnić).
  - *Komórki celu*: 32k i 98k.
  - *Twarde ściany do briefu*: 8.55 µs/wywołanie, 1070 MB K/V/token przy 98k, ~450 GB/s.
- **Zysk [SZACUNEK z round2 §4].** ~połowa z −1.1 ms przy 98k, czyli **−0.5 ms/token (~+8% t/s przy 98k)**, oraz −0.15 ms przy 32k.
- **Koszt i ryzyko.** Koszt średni. Ryzyko średnie: bitowość przy innym podziale bloków jest trudna, a alternatywa nie-bitowa (instancja q8_0 kernela kvq) wymaga decyzji użytkownika.
- **Pomiar.** `ab.sh` llama-bench tg128 przy `-d 32768/98304`, plus logit hash d3000 q8_0.

**P3. Pętla na tanim modelu: tablica MMVQ per (typ, N, K, ncols) z komórkami trzymanymi.**
- **Co zmienić.**
  - Przestrzeń wyłącznie poza foldem [WNIOSEK z kodu: `nwarps` zmienia podział bloków między wątki, więc **jest** w foldzie i jest wykluczony]: rows/blok {1,2,4}, `amdgpu_waves_per_eu`, unroll pętli przy zachowanej kolejności sum, GLC/DLC, prefetch nagłówków.
  - Celem są klasy LFM n=1 o niskim GB/s: out_proj/attn q/o 2048×2048 ~560 GB/s, in_proj ~670 (`lfm-decode-round2.md:110`). Komórki trzymane: Qwen n=1/n=5/n=9.
  - To dokładnie ten typ pracy, który ich runda 1 (DeepSeek flash) zrobiła dobrze (4.11 → 1.12).
- **Zysk [SZACUNEK].** +0.03…0.08 ms/token LFM (≤ 2%). Dla Qwena n=5 mało, bo K1 jest już strojony.
- **Koszt i ryzyko.** Koszt niski, bo `mmvq_bench` istnieje. Ryzyko: „slow mode” gate+up (`lfm-decode-round2.md:78-81`) zaszumi pojedyncze pomiary, więc tylko przeplatane A/B.

**P4. Sonda „rezydentne operandy” dla prefillu MMQ (decyzyjna, nie optymalizacja).**
- **Co zmienić.** Wariant MMQ, w którym wszystkie bloki czytają ten sam kafel wag (pointer modulo jeden kafel), na kształtach FFN Qwena.
- **Jak czytać wynik.** Jeśli TFLOPS skoczą z ~50 do >90, ograniczeniem jest ścieżka pamięci i podwójne buforowanie LDS. Jeśli nie, wąskim gardłem jest wydawanie instrukcji dequant/WMMA i trzeba przebudować pętlę wewnętrzną.
- **Koszt.** Pół dnia.
- **Zysk.** Rozstrzyga, czy dalsza praca nad prefillem (~50 z 123 TFLOPS) w ogóle ma sens.

**P5. Szablon briefu dla naszych agentów kernelowych (proces).** Bierzemy tylko to, czego nie ma w `repos/04`/`06`:
- tabela „w foldzie / poza foldem” per kernel (T1);
- sekcja zamkniętych osi przenoszona do następnej rundy, czyli lista naszych zerowych wyników z NOTES/round2;
- jedno pytanie strukturalne na rundę;
- wynik = geomean celu × `max(1, ratio)` komórek trzymanych;
- test kernelowy „T wierszy w jednym launchu == T launchy jednowierszowych”;
- wejścia przechwycone z modelu (zrzut tensorów przez eval-callback);
- przed baseline’em sprawdzenie bezczynności GPU (`kfd/proc` z whitelistą + `gpu_busy_percent`), nie tylko `flock`.

Koszt niski, zysk w jakości pomiaru.

**P6. Outside the box: `kopt` w trybie generic na wyciętym, samodzielnym harnessie HIP.**
- **Co zrobić.** Wzorem `gdn-rec` (reference = kernel bez zmian, kandydat = kopia, `load_inline`) jeden plik `.cu` kompilowany `hipcc` w kilkanaście sekund zamiast przebudowy ggml-cuda trwającej minuty (wąskie gardło iteracji wskazane w `repos/06-kernelagent.md:41`).
- **Rola modeli.** Tani model do rund strojenia, mocny do rund strukturalnych. Pętla `-n 8` przy budżecie 10–40 $/run (ich konfiguracje).
- **Najlepsze cele.** P1 i P2: zamknięta arytmetyka, wolna geometria, jasny sufit.

**Czego pętla nie znajdzie (wniosek z ich własnych rund).**
- Strojenie zamyka się szybko: w4a16 dało listę zer, gemma chunk −4.85% po 12 iteracjach i koniec.
- Zysk strukturalny wymaga pytania postawionego przez człowieka.
- Nasze największe otwarte gardło, czyli koszt granic kerneli w LFM (416 kerneli/token, ~2.5 µs/granicę), to praca na poziomie grafu (fuzje między op’ami). Pętla per-kernel się do tego nie nadaje.
- Lista z `lfm-decode-round2.md` §5 (np. MoE down + attn_norm następnej warstwy jako ticket tail, gate+up piszące q8_1) jest i tak lepiej określona niż cokolwiek, co pętla wymyśli sama.

## 5. Krytyka

- **Upstream stoi.** Wszystko nowe pochodzi z forka jednej osoby, pod jej silnik i GB10 (237 GB/s, 48 SM, zunifikowana pamięć). Bezwzględne liczby nie przenoszą się na 960 GB/s + 96 MB MALL.
- **Brak wyników końcowych** dla `gdn-rec`, `mconst-thin`, `qsa-*`. Transkrypty są na prywatnym hoście. Znane są tylko liczby baseline’ów oraz wyniki rund 1 cytowane w rundach 2 (w4a16 1.1175, gemma chunk −4.85%).
- **Bitowa M-invariance** (ten sam wiersz bitowo przy M=1 i M=8192) to kontrakt ich silnika. TensorFold zapłacił za podobny 20–29% (`tensorfold/README.md:253`). My jej nie potrzebujemy i przenosimy tylko bitowość „nowy kernel == stary kernel”.
- PDL (−5.7%) i cp.async/Gluon nie mają odpowiednika na RDNA3. Fork cuTile („8×”) to głównie usunięcie synchronizacji hosta.
- Sprostowanie do poprzedniej analizy: w kontekście poprzedniej analizy „zakaz CUDA graphs” dotyczył benchmarku kontestu. W forku `ludoo` jest odwrotnie: każdy task wymaga capture/replay w grafie i wolnego od hosta launchu. To zgodne z naszą rzeczywistością (HIP graphs).

## 6. Werdykt

**Średnia.** Upstream od poprzedniej analizy nie dodał nic. Fork `ludoo` daje dwie rzeczy:
- pomiary GDN dla tej samej geometrii i tej samej weryfikacji T=5, które wskazują jeden konkretny, bitowo bezpieczny eksperyment na naszym kernelu GDN (P1, ≤ 1%);
- dobry szablon briefu dla pętli agenta (fold, zamknięte osie, komórki trzymane, bezczynne GPU), najbardziej przydatny przy zadaniu FA q8_0 dla LFM (P2, ~+8% przy 98k).

Większych zysków kernelowych tu nie ma.
