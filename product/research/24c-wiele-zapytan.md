# 24c — Wiele zapytań naraz na topce (-np 2/4, MTP+lookup, wspólny prefiks)

**Werdykt: KILL dla -np>1 na XTX 24 GB w obecnej konfiguracji topki (nie adoptować).** -np 2 jest wolniejsze od -np 1 zarówno na pojedynczym zapytaniu (−5…−17% t/s), jak i na powtórce prawdziwego fan-outu omp (wall +11%). Przy -kvu greedy md5 nie jest deterministyczne. Wspólny prefiks między slotami zaimplementowałem za przełącznikiem env, ale **nie mierzyłem go na GPU**: GPU zostało wstrzymane przez Main, zanim ruszył blok np4. Z danych wynika, że w tym fan-oucie da się na nim zyskać najwyżej ~3% wall. Dużo większy problem, który wyszedł przy okazji: przy -np 1 lane'y wypychają się nawzajem z cache'u.

## Konfiguracja
- Każde ramię to świeży serwer `run-topka.sh qwen` (MTP4 + lookup mode 3, CACHE_SHARE_MIN=1024, PM4=0, port 18461, `taskset -c 2-5`) uruchomiony przez `~/qwen-opt/multistream/{block,arm}.sh`.
- Replay: `fan4.json` (`swarm_build.py --pick 1`), czyli prawdziwy fan-out 4 subagentów omp (`AmdTritonPath`, `KernelEcosystem`, `PapersAndCommunity`, `UpstreamHarness`). Wszystkie 4 lane'y startują w t=0, po 8 tur na lane, T=0, ignore_eos, wyjście ≤384, think ≤5 s.
- Poprawność: `slot_md5.py` (6 promptów spec_sweep, 400 tok, T=0, przypięte do slotu).

## Wyniki

**Pojedyncze zapytanie, slot 0 (t/s, średnio z 6 promptów, md5 względem np1):**

| ramię | VRAM | t/s śr. | Δ vs np1 | md5 = np1 |
|---|---|---|---|---|
| np1 (CTX 204800, W16) | 23.6 GB | 108.8 | — | — |
| np2 -kvu, CTX 65536, W16 | — | 90.8 | **−16.5%** | 1/6; **drugi przebieg na tym samym slocie daje inne md5** (np. pl-proza 3c961069 → 487aad44) |
| np2 -kvu, CTX 131072, W8 | 23.6 GB | 103.6 | −4.8% | 1/6 (en-chat) |
| np4 -kvu, CTX 131072, W4 | 24.2 GB | 106.3 (2 prompty) | −3% | 2/2 |

**Replay fan4, 32 zapytania, 11264 wygenerowanych tokenów:**

| ramię | wall | suma latencji | TTFT p50 | prefill tok (s) | cache_n=0 |
|---|---|---|---|---|---|
| np1 | **258.0 s** | 897 s | 23.8 s | 142 838 (151 s) | 15/32 |
| np2 W8 CTX131k | 287.4 s (+11%) | 1002 s | 17.8 s | 151 677 (205 s) | 16/32 |
| np2 W16 CTX65k | **padł**: `ROCm OOM` w `hipGraphInstantiate` po 2:10 | | | | |
| np4 W4 | nie zmierzone: serwer zabity z zewnątrz (pkill wzorca `llama-topka/bin/llama-server`), potem GPU wstrzymane | | | | |

## Diagnoza
1. **Pamięć.** Stan rekurencyjny (GDN) zajmuje `n_seq × (1 + n_rs_seq)` kopii, a `n_rs_seq = max(draft, LOOKUP_W)`. Przy W16 to ok. 2.4 GB na każdy dodatkowy slot (bufor rs 4788 MiB przy np2). Na 24 GB np2 wymaga CTX ≤64k albo W≤8, a np4 W≤4. Każda z tych opcji zabiera to, co topka zyskała na lookup W16 (×2.4 na edycjach kodu, 16b), albo długi kontekst.
2. **Dwa strumienie się nie zwracają.** Przy np2 dekod pojedynczego zapytania spada ze 138 do 40 t/s (mediana). Prefill jednego lane'a blokuje dekod drugiego, a łączna przepustowość nie rośnie.
3. **-kvu nie jest bit-exact.** Pozycja w zunifikowanym KV zmienia kolejność redukcji FA, więc greedy md5 zależy od historii serwera. Odpada kryterium md5 per slot.
4. **Wspólny prefiks dałby mało.** omp wstawia `Your id is X` i listę peerów w ok. 76% system promptu: wspólne jest 10 783 z 14 140 znaków. Wspólny prefiks to więc ok. 2.5k z 5.5k tokenów pierwszej tury [INFERENCE: przeliczenie znaki→tokeny]. Przy 4 lane'ach oszczędność wynosi ≤7.5k tokenów ≈ 8 s prefillu przy 944 t/s, czyli ≤3% z 258 s wall. „⅓ prefillu agentów” z 21f tu nie występuje.
5. **Prawdziwy koszt to thrash w np1.** 15/32 tur miało cache_n=0 (tury 0–3 każdego lane'a: pełny prefill 5.5–11.7k tok), mimo CACHE_SHARE_MIN. Prefill zajął 151 s z 258 s wall. Prawdopodobna przyczyna: replay używa nagranej odpowiedzi Claude'a, nie wygenerowanej, więc stan hybrydowy rozjeżdża się na końcu promptu i nie ma checkpointu. W ruchu z prawdziwym Qwenem może tego być mniej [INFERENCE]. Przekazane OptAgentPath (praca nad prompt cache).

## Co zbudowane
- `~/wt/multistream`, branch `multistream`, commit **51b0b733e**: `LLAMA_SERVER_SLOT_SHARE_MIN=N` (domyślnie 0 = off, wymaga -kvu). Nowy prompt, który dzieli ≥N tokenów więcej z promptem właśnie prefillowanym w innym slocie niż z własnym cache'em, czeka. Lider zatrzymuje się na końcu wspólnego prefiksu i kopiuje do followera całą sekwencję (seq_cp tgt+dft oraz stan spec). Kopia całej sekwencji w punkcie końca prefiksu jest poprawna także dla pamięci hybrydowej i MTP.
- Skompilowane (konfiguracja CPU, `libllama-server-impl.so` w `~/llama-ms`, biblioteki z topki). **Na GPU nie uruchamiane.**
- Skrypty `~/qwen-opt/multistream/{arm,block,slot_md5,swarm_replay,swarm_build}.py|sh`. block.sh nie restartuje już topki (robi to keeper). arm.sh używa `ROCM_DIR=~/llama-ms`, żeby `pkill` topki nie zabijał serwera testowego.

## Nie zrobione (GPU wstrzymane)
- np4 (W4, CTX 65536): base vs `SLOT_SHARE_MIN=256` na fan4. To jedyny pomiar, który mógłby jeszcze dać przewagę wiele slotów nad np1: 4 lane'y w 4 slotach to brak thrashu, kosztem W16→W4.
- md5 `llama-ms` z wyłączonym env vs topka; test poprawności kopii prefiksu (md5 followera vs zimny start).
- fan4b, spec_sweep ≥5 seedów, ABBA.

## Adopt / kill
- **-np 2 w topce: KILL** (wall +11%, single −5…−17%, OOM przy W16, md5 niedeterministyczne).
- **-np 4 W4: otwarte.** Tylko z pomiarem wall na fan4 i bez regresji single. Single −3% już zmierzone, ale W4 traci lookup W16 na kodzie.
- **SLOT_SHARE_MIN: nie adoptować bez pomiaru.** Sufit ~3% wall na fan-oucie omp. Większy zysk dałoby przeniesienie `Your id is`/listy peerów na koniec system promptu w omp: wspólny prefiks objąłby wtedy prawie cały system prompt.

## Do bazy wiedzy
- Qwen3.8 (qwen35, hybryda GDN): koszt slotu to `(1+max(draft,LOOKUP_W))` kopii stanu SSM, przy W16 ok. 2.4 GB na slot. np2 z W16 nie mieści się na XTX przy CTX 204800 (alloc rs 4788 MiB), a przy CTX 65536 pada w trakcie (OOM w hipGraphInstantiate).
- -kvu: greedy md5 zależy od historii serwera (ten sam prompt na tym samym slocie daje 2 różne md5).
- np2 W8 vs np1 W16 na fan4: wall 287 vs 258 s, single −4.8%.
- Fan-out omp: wspólny prefiks to tylko ok. 76% system promptu, bo `Your id is X` i lista peerów są w środku.
- np1, 4 lane'y z nagranymi odpowiedziami: 47% tur bez trafienia w cache, prefill to 59% wall.
