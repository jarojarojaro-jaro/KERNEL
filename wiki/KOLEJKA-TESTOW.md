---
typ: meta
tags: [meta, kolejka, testy, gpu, xtx, nvidia]
aktualizacja: 2026-11-14
zrodlo: ~/KERNEL/product/research/{15,63,66,68,69}-SYNTEZA.md, 68a-d, 69a-d, 70-fa-d256-jak-to-zrobilismy.md, 67c-nvidia-backlog-testow.md; ~/KERNEL/qwen-opt/STATUS-NEXT.md; ~/KERNEL/STAN-PRAC.md; ~/KERNEL/wiki/{eksperymenty,decyzje,metody,kernele,produkt,nvidia,rocm}/; ~/KERNEL/wiki/DO-ZAPISANIA.txt; ~/kernel/archiwum (sesje 2026-09-15 … 2026-11-13, rg)
status: aktualne
---
# Kolejka testów na karcie

**Jedno miejsce na wszystko, co warto sprawdzić na karcie, gdy jaroserverai jest włączony: pozycje `K-…` w „Czeka” ułożone priorytetem (najważniejsza pierwsza), wyniki w „Zrobione”, powody w „Odrzucone”.**

Zasady (KERNEL-SESJA, 2026-11-13):
- **Karty.** jaroserverai = RX 7900 XTX (gfx1100, produkcja topka-q70) + RTX 5060 Ti 16 GB (sm_120). Pozycje oznaczone „wynajem” wymagają 3090/4090/innej karty z Vast i osobnej zgody na wydatek.
- **Start.** Właściciel mówi „testy” / „robimy kolejkę” → lecimy od góry. Każdy test przez `~/qwen-opt/queue/run-jobs.sh`, `GGML_HIP_PM4` ustawione jawnie, eco 2200 bez zmian, `gpu-guard.sh`, ≤ 10 min na pomysł (krótka bramka + krótkie A/B, 2–3 seedy; nie wygrywa wyraźnie → odrzucamy).
- **Po teście.** Notatka eksperymentu (baseline → teraz → przyrost), status tutaj, `log.md`, commit + push.
- **Decyzje.** „Czeka na decyzję” = nie uruchamiać, dopóki właściciel nie zdecyduje w rozmowie.
- **Bezstratność.** Tylko zmiany bezstratne (md5 bit w bit albo KLD = 0, [[2026-11-05-tylko-bezstratne]]). Próg adopcji: ≥ 3–5% decode/prefill albo ≥ 1 s na turę agenta.
- **Telegram.** Z wiadomości z Telegrama nic nie uruchamiamy na karcie; trafiają tu tylko jako pozycje.

Skróty: `R/` = `~/KERNEL/product/research/`, `Q/` = `~/KERNEL/qwen-opt/`. Rekordy: [[REKORDY]]. Rejestr źródeł: [[ZRODLA]].

## Czeka

### K-001 · Naprawić wyciek stanu przy drugim restore slotu (drugi restore na tym samym serwerze ≠ świeży prefill)
- data: 2026-11-09 (ten sam objaw w `det_probe` 2026-10-14)
- źródło: [[2026-11-08-kvq-once-profil]] (`:81-82`), [[lekcja-ten-sam-serwer-pending-h]], `R/68-SYNTEZA.md:31`, `Q/xtxbench/README.md:79-85`; podejrzany niezresetowany kontekst draftu MTP / stan GDN / `pending_h` (por. upstream #30574, `Q/patches/topka-q63/0003-*`)
- hipoteza (2026-11-14): upstream #30541 (w llama.cpp v1.0.0) naprawia kopię stanu „on device” dla skwantowanego KV: liczba elementów liczona jako bloki, więc dla q4_0 kopiowane było 1/32 zakresu → zły stan po restore. Topka (baza b11528) tej poprawki nie ma, a my mamy KV q4_0 [INFERENCE: czy ścieżka `LLAMA_STATE_SEQ_FLAGS_ON_DEVICE` jest używana przez cache/checkpointy topki — sprawdzić w kodzie na CPU przed testem] ([[telegram-2026-11-14-pearlquant-llamacpp-v1]])
- test: najpierw repro na CPU (LFM2.5-2.6B pokazał wzór przy 0,6k). Potem XTX, port testowy, `run-topka.sh uncensored`: restore migawki 1,7k → md5 T=0 → inne żądanie → drugi restore → md5, porównanie z `md5_fresh` (xtxbench t1 A/A). Bez 199k ≤ 10 min.
- zysk: poprawność, nie szybkość. Cachesave i `--cache-ram` odtwarzają wpisy w sesjach agenta, więc produkcja może dziś po cichu zmieniać odpowiedzi. Bez naprawy werdykty md5 xtxbench są pewne tylko przy pierwszym restore.
- ryzyko karty: brak
- priorytet: wysoki (bezstratność produkcji)

### K-002 · Sprawdzić, czy ogon lookupu W16 spowalnia pisanie przy krótkim kontekście
- data: 2026-10-19
- źródło: [[REKORDY]] (`:108`: 1,7k sam MTP 136,5 vs topka W16 123,7 t/s, „nie w produkcji”), `product/WYNIKI-XTX-2026-10-19.md:82`. Jeden przebieg, przed coupled/host-gap/eco, nigdy nie powtórzony.
- test: XTX, xtxbench t1 `--var-env LLAMA_SPEC_LOOKUP=0` vs produkcja, decode 1,7k/94k T=0 + spec_sweep 1 seed (~4 min/wariant).
- zysk: jeśli się potwierdzi, krótkie prompty +5…10%. Bezstratna poprawka: wyższy próg dopasowania ogona przy krótkim kontekście (zmienia tylko drafty).
- ryzyko karty: brak
- priorytet: wysoki (tani, potencjalnie ≥ 3%)

### K-003 · Rozłożyć stały koszt ~210–230 ms na każde żądanie (TTFT krótkich promptów) i dokończyć tańszy zapis stanu GDN (stash `opt-s4`)
- data: 2026-11-09 (stash `opt-s4`: 2026-10-13)
- źródło: [[2026-11-09-evalplus-qwen-uncensored]] (`:37`: `prompt_ms ≈ 155 ms + 0,98 ms/tok`, ~75 ms poza prompt/predict; BFCL TTFT 625 ms przy 416 tok.), [[2026-11-09-jakosc-mini-qwen-unc]], [[2026-10-13-s2-s4]] (`:22`, +10–15 ms/żądanie)
- test: XTX, port testowy, `LLAMA_SERVER_AP_TIMING=1` + rozbicie na 50 krótkich promptach HE+ (checkpoint GDN, hak/dogonienie MTP, zapis cache, render/tokenizacja). Potem A/B poprawki + md5. ≤ 10 min.
- zysk: 4,3–4,7% średniego czasu odpowiedzi (4,8–4,9 s); w agencie ~0,2 s na każde wywołanie narzędzia
- ryzyko karty: brak
- priorytet: wysoki (każda tura, mieści się w progu 3–5%)

### K-004 · Fork CUDA: dokładne próbkowanie spekulacyjne na GPU przy T=1 (jak qwen-warp)
- data: 2026-11-09
- źródło: [[2026-11-09-qwen-warp-vs-fork-3090]] (pkt 2: fork traci przy T=1 7–13%, warp nie traci), `R/69b-tensorfold-qwen-warp.md` §3
- test: najpierw 5060 Ti lokalnie: fork (`kvqleana`) spec_sweep T=0 vs T=1, `LLAMA_SPEC_COUPLED` 0/1 (≤ 10 min). Po porcie: ABBA 6 × 3 seedy, md5 T=0 bez zmian; potwierdzenie na 3090 (wynajem, metoda `nv69q`).
- zysk: odzysk 7–13% przy T=1 na NVIDIA (3090: 76,9 vs 82,9 t/s przy krótkim kontekście); wszyscy użytkownicy Enigmy z NVIDIA
- ryzyko karty: brak
- priorytet: wysoki (Enigma NVIDIA, tani pierwszy pomiar)

### K-103 · Enigma NVIDIA: silnik na llama.cpp v1.0.0 (few-row MMQ #31533) zamiast pinu b11856, z MTP
- data: 2026-11-14
- źródło: [[telegram-2026-11-14-pearlquant-llamacpp-v1]]; PR #31533 (Qwen3.8-27B + DFlash2, 7 draftów: 3090 Ti 57,6 → 77,7 tok/s, +34,9%; RTX PRO 6000 +16,7%; 5090 +20,6%; 80/80 rozmów szybciej, KLD jak master); pin b11856 został, bo b12110 był ~9% wolniejszy z MTP na sm_120 ([[final-recipes-nvidia]])
- test: 5060 Ti lokalnie: spec_sweep T=1 + `mvs`, MTP n 2/4, pin b11856 vs v1.0.0 (b12359), ABBA ≤ 10 min; `llama-bench -p 576 -n 0 -ub 4,8,16` przed/po; KLD vs upstream jak w kampanii 67
- zysk: weryfikacja MTP/DFlash na NVIDIA +10…35% tok/s (dane autora); jeśli regresja b12110 z MTP nie wróci, nowe przepisy Enigmy dla wszystkich kart NVIDIA
- ryzyko karty: brak
- priorytet: wysoki (duży zmierzony zysk, tani test lokalnie)

### K-013 · Tańsza weryfikacja 2–24 kolumn (MTP n=5 i lookup W16): port kernela „few-row” upstream #31533 na RDNA3 (iu8 WMMA)
- data: 2026-11-07
- źródło: `R/68d-swieze-od-spolecznosci.md:140`, `R/69-SYNTEZA.md:30` (W3), [[2026-11-09-qwen-warp-vs-fork-3090]] (pkt 3), `R/67c-nvidia-backlog-testow.md:131` (C14)
- test: XTX `llama-bench -fa 1 -ctk q4_0 -ctv q4_0 -p 1,5,8,9,16 -n 0 -d 2048,32768` przed/po (krzywa V(w)), potem `mvs` + czat ABBA i md5; ≤ 10 min. NVIDIA: `test-backend-ops MUL_MAT` n=8/16 na 5060 Ti.
- nowe (2026-11-14): #31533 scalone w llama.cpp v1.0.0. Na NVIDIA spec-dec Qwen3.8-27B +16,7…34,9% tok/s (3090 Ti 57,6 → 77,7), KLD jak master; port HIP (`6ad15f48`, am17an) na RDNA3.5 z DFlash2: 21 → 37 tok/s. Weryfikacja MTP n=5 (5 kolumn) też w zakresie 2–24. Inny kernel = inna kolejność sum, więc md5 T=0 się zmieni: wdrożenie na XTX wymaga bramki K-007 albo decyzji właściciela.
- zysk: V16 − V5 = 6,4 ms przy 2k; połowa tego → kroki W16 −9%, tury agenta z kopiowaniem +5…10% [SZACUNEK]; czat 0. Warunek dla drzew (K-075).
- ryzyko karty: nowy kernel w PM4
- priorytet: wysoki (zmierzone +17…35% u autora, ten sam model)

### K-005 · Siatka checkpointów GDN co ~8192 tokenów + checkpoint w punkcie rozwidlenia + łańcuch fallbacku (edycja, regeneracja, kompaktowanie omp)
- data: 2026-10-15 (STATUS-NEXT §4), ponownie 2026-11-07 (66 poz. 6)
- źródło: [[siatka-checkpointow-gdn]], `Q/STATUS-NEXT.md:44`, `R/66-SYNTEZA.md:57`, `R/67c-nvidia-backlog-testow.md:116` (B22)
- test: najpierw implementacja w topce. XTX: replay prompt 60k → zmieniony koniec → rodzeństwo; `prompt_n`, TTFT, md5 vs zimny start (~1,5 min prefillu na ramię, ≤ 10 min).
- zysk: edycja ostatnich 10% promptu 60k: TTFT ~65 s → ~8–10 s [SZACUNEK]; ≥ 1 s/turę, gdy dojdzie do rozjazdu
- ryzyko karty: brak (~150 MiB RAM hosta na checkpoint)
- priorytet: wysoki (≥ 1 s/turę)

### K-006 · Wpis „wspólny początek” (Maya #607) i chude checkpointy (stan GDN tylko na granicach wiadomości) zamiast kopii całej sesji w cache
- data: 2026-11-05
- źródło: [[wspolny-poczatek-promptu]], `R/63-SYNTEZA.md:85-86` (plan #6, #7), `R/63b-colibri-maya-delta.md` §6, `R/68c-dlugi-kontekst-gdn.md:143`
- test: najpierw implementacja. XTX: `switch.py` z cachesave (2 przeplatane wątki 75–120k, 14 tur ≈ 3 min), mediana tury, `prompt_n`, md5 = zimny start; ≤ 10 min/ramię.
- zysk: start sesji po wyrzuceniu z cache 4,4 s → 0,3–0,5 s, przy 100k+ ~5–7 s → 0,3–0,5 s [SZACUNEK]; wpis 118k 14,2 GB → ~3–4 GB, czyli 3–4 długie wątki w cache zamiast 1
- ryzyko karty: brak (RAM hosta; `HSA_USE_SVM=0` już jest)
- priorytet: wysoki (≥ 1 s/turę agenta)

### K-007 · Bramka „wymuszanie tokenów + KLD” (SpecPilot) zamiast md5 dla zmian polityki draftu i szerokości weryfikacji, z kalibracją kanarkami
- data: 2026-11-07 (kanarki: 2026-10-15)
- status: **czeka na decyzję** właściciela (decyzja 6 z rundy 69: czy dopuścić „te same tokeny + KLD” zamiast md5)
- źródło: `R/68b-spekulacja-nowe.md:161`, `R/69-SYNTEZA.md:33,41`, [[raport-69-synteza]], [[bramka-kld-kanarki]] (`:27`, nigdy nieuruchomione na GPU), `Q/tools/kld_canary.sh`
- wzór oceny (2026-11-14): PearlQuant ma 3 warstwy: KLD, benchmarki, cechy tekstu (liczba „Wait” na 1000 słów, ślepy sędzia = sam model), a do tego celowo zepsute konfiguracje jako kontrola pozytywna ([[telegram-2026-11-14-pearlquant-llamacpp-v1]])
- test: skrypt teacher-forced na CPU. XTX: topka vs topka (szum), DRAFT_N=5 (powinno przejść), wstrzyknięty bias logitu (musi odpaść), 6 promptów × 2k tok. T=0. Kanarki po jednym na job ≤ 10 min.
- zysk: 0% sama; odblokowuje K-008, K-017 i K-046 (+3…7%)
- ryzyko karty: brak
- priorytet: wysoki (odblokowuje największy bezstratny decode)

### K-008 · Dynamiczna głębokość draftu MTP z luki Gumbela z wczesnym wyjściem z łańcucha (dmin 2, dmax 5)
- data: 2026-10-10 (zmienna długość draftu), 2026-11-07 (68b #1)
- status: **czeka na decyzję** (bramka K-007; zmienna szerokość weryfikacji zmienia md5 T=0, choć rozkład jest zachowany)
- źródło: `R/68b-spekulacja-nowe.md:160,164`, `R/68-SYNTEZA.md:17`, `R/40-akceptacja-prozy.md:116` (proza `DRAFT_N=3` +4,3%, 82,4 vs 79,0 t/s, 8/8 promptów), [[lekcja-glebokosc-zmienia-tekst]]
- test: XTX, `spec_sweep.sh "LLAMA_SPEC_DEPTH_GAP=0" "LLAMA_SPEC_DEPTH_GAP=2"` T=1, ABBA po 2 ramiona na job; xtxbench 1,7k/94k/199k
- zysk: symulacja +3,9% ogółem, czat PL +4,8%, EN +2,9%; bez wczesnego wyjścia ~0
- ryzyko karty: PM4 (warunkowe wyjście w taśmie draftu)
- priorytet: wysoki (największy bezstratny zysk decode, PL najwolniejszy: 120 t/s)

### K-009 · Przegląd configu MMQ na RDNA3 metodą wariantów jak FA 83 (maska `GGML_HIP_MMQ_VAR`: Q4_K/Q6_K/IQ4_XS, `sched_barrier`, offsety u32, prefetch K, skale x f32 w LDS)
- data: 2026-11-09 (skale x f32: 2026-10-15)
- źródło: `R/70-fa-d256-jak-to-zrobilismy.md:185` (#2), `R/68d-swieze-od-spolecznosci.md:138-139`, `Q/STATUS-NEXT.md:49`, [[sweep-wariantow-kernela]]
- test: ISA na CPU (`isa.sh`). XTX: `test-backend-ops perf -o MUL_MAT` Q4_K/Q6_K, md5 12k jak `Q/fa-d256/md5.sh`, ABBA `llama-bench -p 512,4096`; każdy krok ≤ 10 min (szablon `~/qwen-opt/fa-d256/`)
- zysk: pp ≤ 32k +2…4%, fill 255k +1…2% [INFERENCE]; MMQ to 63–81% prefillu, jedyna dźwignia prefillu przy krótkich promptach
- ryzyko karty: brak
- priorytet: średni (prefill; w pakiecie z K-010)

### K-010 · Fuzja gate/up + GLU w MMQ dla WMMA RDNA3 (port upstream #29948)
- data: 2026-11-05
- źródło: `R/68a-rdna3-kernele.md:120`, `R/68-SYNTEZA.md:21`, `R/68d-swieze-od-spolecznosci.md` §2.2
- test: XTX `test-backend-ops -o MUL_MAT` z fuzją, `llama-bench -p 512,4096 -ub 512 -r 5` ABBA, md5; ≤ 10 min/krok
- zysk: pp ≤ 32k +2…4% [INFERENCE] (CUDA u autora +4,6…7,4%)
- ryzyko karty: brak (wariant MoE był na RDNA3 wolniejszy o 3…16%, więc mierzyć)
- priorytet: średni (prefill, pakiet z K-009)

### K-011 · Kontrola ewikcji VRAM do GTT przy 262k (`amd-evicted-vram`, `drm-memory-*` w fdinfo)
- data: 2026-11-07
- źródło: `R/68a-rdna3-kernele.md:123` (4.5), `R/68-SYNTEZA.md:24`
- test: doczepić do najbliższego fillu 255k: odczyt `/proc/<pid>/fdinfo/*` przed promptem, po prefillu i po 256 tokenach (0 dodatkowego czasu GPU)
- zysk: 0%, jeśli ewikcji nie ma; jeśli jest, decode przy 255k jest dziś zaniżony
- ryzyko karty: brak (odczyt)
- priorytet: średni (darmowe, może zaskoczyć)

### K-012 · `kvq` przy W=5 bliżej rooflinu: nowy układ (K dekwantowane raz, głębszy prefetch K/V), cel ~172–300 µs/warstwę przy 98–196k
- data: 2026-11-07
- źródło: [[2026-11-08-kvq-once-profil]] (`:86`: ONCE=1/2 KILL, „potrzebny inny układ”; FA = 30% kroku przy 199k, 11,32 ms), `R/68c-dlugi-kontekst-gdn.md:142`, `R/70-fa-d256-jak-to-zrobilismy.md:188` (#5)
- test: XTX `kvq-once/job.sh` kperf (d98k/196k, nb1/nb5) + `fa_hash` ≤ 10 min; potem xtxbench 199k osobnym jobem
- zysk: sufit +12…16% decode przy 196–255k; realnie +1,5…3% przy ≥ 94k [SZACUNEK]
- ryzyko karty: nowy kernel w taśmie PM4 (bramka `test-backend-ops` przed serwerem)
- priorytet: średni (duży sufit, dwa nieudane podejścia)

### K-014 · Graf CUDA na cały cykl draft + weryfikacja (ścieżka hosta 3,7 ms/krok = 14% na 3090)
- data: 2026-10-21 (Orca), 2026-11-09 (qwen-warp pkt 4)
- źródło: `R/69b-tensorfold-qwen-warp.md:75`, [[2026-11-09-qwen-warp-vs-fork-3090]], sesja Orca 2026-10-21 (archiwum, `O:1986-2003`); potwierdzenie kierunku: Baseten deepseek-ultrafast, krok spec-dec z weryfikacją 7 tokenów w jednym grafie ([[telegram-2026-11-14-silniki-agenci]])
- test: 5060 Ti lokalnie: spec_sweep T=1 + ms/krok z rozbiciem host/GPU, fork vs fork+graf; ≤ 10 min/ramię. Kod: tygodnie.
- zysk: +10–20% decode na 3090 [SZACUNEK]; część przewagi qwen-warp ×1,34–1,81
- ryzyko karty: brak
- priorytet: średni (duży, drogi w kodzie)

### K-015 · Regresja `kvq` na sm_120 przy krótkim kontekście (−4,4% na 5080, −4,7% na 3090) i przegląd `GGML_CUDA_KVQ_BPSM` 1/2/3/4/6
- data: 2026-11-07
- źródło: `R/67-nvidia-vast-kampania.md` §5, `R/67c-nvidia-backlog-testow.md:107` (B13)
- test: 5060 Ti lokalnie: `test-backend-ops perf -o FLASH_ATTN_EXT` hs256 q4_0 przy 32k/98k/196k dla każdego BPSM, potem spec_sweep KVQ 0/1; ≤ 10 min
- zysk: odzysk +4…5% przy krótkim kontekście przy zachowaniu +9,5% decode przy 64k
- ryzyko karty: brak (16 GB: uważać na OOM przy dużym kontekście)
- priorytet: średni (lokalnie, tanio)

### K-016 · Fork CUDA: ogon lookupu W8/W16/off oraz MTP n 2/3/5 per klasa na promptach kopiujących
- data: 2026-11-07
- źródło: `R/67c-nvidia-backlog-testow.md:99-101` (B5–B7; 5060 Ti: n=3 ≥ n=4, fork ma sztywne 4), [[final-recipes-nvidia]]
- test: 5060 Ti: `LLAMA_SPEC_LOOKUP_W=8/16`, `LLAMA_SPEC_LOOKUP=0`, `--spec-draft-n-max 2/3/5`, `mvs` + spec_sweep; po jednym ramieniu na job ≤ 10 min
- zysk: dobór przepisu Enigmy per klasa; W16 na wąskiej szynie może przegrywać [INFERENCE]
- ryzyko karty: brak
- priorytet: średni (przepis Enigmy, lokalnie)

### K-017 · Głębokość i szerokość draftu per klasa żądania (`LLAMA_SPEC_ROUTE`: rozumowanie/kod T=0 → n=5, proza → n=3)
- data: 2026-10-21 (raport 44)
- status: **czeka na decyzję** (bramka K-007; n=5 zmienia md5 → d71a2c04). Najpierw naprawić crash ABBA `ggml-cpu.c:2504` w `ggml_graph_plan`.
- źródło: `R/44-routing-profili-spekulacji.md:5-7`, [[raport-44-spec-route]], `R/36-xtx-qwen-roadmap.md:183`
- test: XTX `~/qwen-opt/xtxlab/sr_gate.sh` + `sr_arm.sh` (`x44.jobs`), reason_bench T=0, spec_sweep, `mvs`; po jednym na job ≤ 10 min
- zysk: rozumowanie T=0 +6,8%, proza +4,3%, kod/JSON T=0 +5…10%, czat 0 (kill < −1%)
- ryzyko karty: brak
- priorytet: średni (zależy od decyzji)

### K-018 · AGR2: kandydat lookupu zgodny z 4 draftami MTP (`LLAMA_SPEC_LOOKUP_AGREE=1`) + dynamiczny słownik draftu
- data: 2026-10-19 (21c), 2026-11-05 (63 #18)
- źródło: [[agr-lookup-zgodny-z-mtp]], [[2026-10-19-sufit-pointera-lookup]], `R/21c-copy-paste-lm.md:185-194`, `R/63-SYNTEZA.md:97`
- test: najpierw symulacja CPU; XTX ABBA w jednej binarce na `mvs`, `copy` (hashline-pl) i spec_sweep T=0/T=1; kill < +2% hashline albo > +0,5% ms/krok na czacie; ≤ 10 min
- zysk: agent +3,7%, hashline +5,4%, czat +0,6% (symulacja); zmienia tylko drafty
- ryzyko karty: brak
- priorytet: średni (na granicy progu)

### K-019 · Cache sufiksów między sesjami (draft z poprzednich wyjść agenta, styl SuffixDecoding)
- data: 2026-10-19 (raport 18), 2026-11-07 (67c C18)
- źródło: `R/67c-nvidia-backlog-testow.md:135`, archiwum (`A:21140`)
- test: symulacja CPU na logach omp, potem XTX spec_sweep PL + replay agenta ABBA (kill < +1%); ≤ 10 min
- zysk: +5–15% na agentach [SZACUNEK]; zmienia tylko drafty
- ryzyko karty: brak
- priorytet: średni (agenci, tani offline)

### K-020 · Polityka wyrzucania `--cache-ram` ważona kosztem przeliczenia (Marconi) zamiast LRU
- data: 2026-11-07
- źródło: `R/68c-dlugi-kontekst-gdn.md:143` (#9)
- test: XTX replay 3 wątków (2 długie + krótkie) z `LLAMA_SERVER_PREFIX_LOG`, liczba pełnych prefilli ≥ 20k; ~10 min
- zysk: chroni wpisy ≥ 100k (przeliczenie 100–550 s) przy presji 40 GB [INFERENCE]
- ryzyko karty: brak
- priorytet: średni (rzadkie, ale ogromne tury)

### K-021 · Dataflow w taśmie PM4: usunąć granice dispatchy w łańcuchu MMVQ → norma → MMVQ weryfikacji (najpierw PoC-A: hand-off w trwałej siatce)
- data: 2026-10-20 (raport 36 L7)
- źródło: `R/37-proza-100.md:17-19` (górna granica `GGML_HIP_PM4_UB=mmvq,norm` −2,17 ms/partię 5 wierszy, −8,8%), `R/36-xtx-qwen-roadmap.md:190`, `R/66-SYNTEZA.md:66` (#15), [[budzet-megakernela-qwen-xtx]]
- test: XTX `klab` mikrobench hand-off, `GGML_HIP_PM4=0` (kill: > 0,3 µs albo < 30% zysku „bez granicy”); potem PoC-B md5 + spec_sweep ABBA; każdy krok ≤ 10 min
- zysk: etap 1 +2,6…4,2%, pełny +3…6% krótki kontekst / +2…4% przy 199k, po 40–70 osobodniach [SZACUNEK]
- ryzyko karty: **wysokie**: zawieszenia taśmy PM4 i resety (16a, 24l); tylko z `gpu-guard.sh`
- priorytet: średni (jedyna duża dźwignia w kernelach, drogie i ryzykowne)

### K-022 · Natywne q4_0 K/V w prefillu FA D256 (bit 128 / #31802): wyjaśnić md5 wariantów 131/147, alternatywnie szybszy staging q4_0→f16
- data: 2026-11-07
- źródło: [[2026-11-08-fa-d256-prefill]] (`:35`), `R/70-fa-d256-jak-to-zrobilismy.md` §3.6 (173/173 w `test-backend-ops`, ale md5 e9dcdd80 ≠ 816334e4), `R/68d-swieze-od-spolecznosci.md:137`, `R/68c-dlugi-kontekst-gdn.md:137`
- test: najpierw różnica na CPU (ścieżka dekwantu vs `dequantize_q4_0`, ogon KV). XTX `fa-d256/md5.sh` + micro (≤ 10 min); szczyt VRAM przy fill 255k osobnym jobem (~9 min).
- zysk: VRAM −~1 GiB przy 262k, fill 255k +2…3%; staging sam −2% fillu (~11 s)
- ryzyko karty: VRAM (szczyt może się przesunąć)
- priorytet: średni (VRAM daje zapas dla K-048)

### K-023 · Bisekcja regresji prefillu forka CUDA względem upstream (sm_89 −3,5…−3,9%, 3060 TTFT 512 +30%) i LOO przełączników forka
- data: 2026-10-20 (raport 29)
- źródło: `R/67c-nvidia-backlog-testow.md:103,105` (B9, B11), `product/BENCHMARKI-PRZED-PO-2026-10-19.md` §4, [[raport-15d-prefill-dlugi-kontekst]]
- test: 5060 Ti lokalnie (sm_120): `llama-bench -p 512,4096` upstream vs fork + po jednym przełączniku `=0` na job; sm_89 wynajem
- zysk: odzysk 3…12% prefillu i TTFT na NVIDIA
- ryzyko karty: brak
- priorytet: średni (TTFT Enigmy)

### K-024 · Enigma ROCm na innych kartach AMD + autotune wariantu FA przy instalacji (gfx1101/1102/1151/1201)
- data: 2026-11-09
- źródło: `R/70-fa-d256-jak-to-zrobilismy.md:186` (#3)
- test: wynajem kart AMD; `fa-d256` micro + md5 + bench przy głębokości na każdej architekturze; ~1 h wynajmu
- zysk: RDNA3 gfx1101/1102: prefill przy głębokości +3…6%; gfx1151 nieznane; gfx1201 wymaga portu [INFERENCE]
- ryzyko karty: brak (wynajem)
- priorytet: średni (warunek sprzedaży Enigmy na inne Radeony)

### K-025 · FA D256 wariant 83 dla innych modeli i kształtów (Saluki/Bonsai, Qwen3.6-35B-A3B, LFM2.5 D=64, f16 KV, RDNA3.5) przed włączeniem domyślnie w kodzie
- data: 2026-11-09
- źródło: `R/70-fa-d256-jak-to-zrobilismy.md:184,187` (#1, #4), §6.2; dziś 83 tylko dla qwen/uncensored przez launcher (f16 KV przy 131k: −2,4%)
- test: XTX `fa-d256/bench.sh` z `M=<model>` przy 4k/32k/131k (~17 min → 2 joby), md5 jak `md5.sh`; dla 35B-A3B rozszerzyć warunek `:2216` i sweep
- zysk: Saluki/Bonsai ≥ +5,8% fillu [INFERENCE], 35B-A3B przy ≥ 128k +3…5%, LFM +1…2%; dla katalogu Enigmy, nie produkcji
- ryzyko karty: brak
- priorytet: średni (Enigma)

### K-026 · Enigma: próg draftu `--spec-draft-p-min` {0; 0,5; 0,8} × n {1,2,4} dla MoE z `--n-cpu-moe` na kartach ≤ 16 GB
- data: 2026-11-07 (66a A2)
- źródło: [[prog-draftu-od-kosztu-wiersza]], `R/66-SYNTEZA.md` poz. 10
- test: 5060 Ti z Qwen3.6-35B-A3B `--n-cpu-moe 20/30/40` albo emulacja na XTX; spec_sweep T=0/T=1 ABBA ~10 min/klasę
- zysk: 0…+15% na MoE z offloadem (Strata +5,6…9,3%); model rezydentny ~0
- ryzyko karty: brak
- priorytet: średni (produkt Enigma)

### K-027 · Profil kroku przy długim kontekście na NVIDIA (`nsys` + `LLAMA_HOSTGAP_TRACE` przy 1,7k/94k/199k)
- data: 2026-11-07
- źródło: `R/67c-nvidia-backlog-testow.md:118` (C1)
- test: 3090/4090 (wynajem; 16 GB 5060 Ti nie zmieści 199k z 27B), po jednym kontekście na job ≤ 10 min
- zysk: 0% sam; rozstrzyga K-062, K-063 i maskę na CUDA
- ryzyko karty: brak
- priorytet: średni (bramka decyzji NVIDIA)

### K-028 · xtxbench: smoke przełącznika bez restartu `GGML_HIP_RUNTIME_SWITCH_FILE`
- data: 2026-11-09
- źródło: [[xtxbench-szybki-ab]] (`:39,48`), `Q/patches/xtxbench/0001-runtime-switch-hook-GGML_HIP_RUNTIME_SWITCH_FILE.patch`
- test: XTX `xtxbench.py t1 --var-switch …` A/A; obowiązkowe ramię md5 ze świeżym startem (wyciek K-001); ≤ 10 min
- zysk: narzędziowy: bez restartu 1,5–2 min na ramię, więc każdy przyszły A/B krótszy
- ryzyko karty: brak
- priorytet: średni (przyspiesza całą kolejkę)

### K-029 · xtx-eco: odczytywać fabryczny `OD_SCLK` przy każdym boocie przed pierwszym zapisem OD (stock zmienia się między bootami: 2885 vs 2935 MHz)
- data: 2026-11-06
- źródło: [[2026-11-06-xtx-eco-instalacja]] (`:12-13`, „poprawka w toku — status do sprawdzenia”), [[raport-64-termika]]
- test: XTX bez obciążenia: po restarcie porównać `pp_od_clk_voltage` z zapisanym stanem bootu, sprawdzić krzywą wentylatora (`pwm1`/RPM); ≤ 10 min
- zysk: 0 t/s; „powrót do stock” nie obniża już limitu o 50 MHz (zasada: karta fabrycznie)
- ryzyko karty: zapis OD na jądrze 6.8 gubi krzywą wentylatora, więc pilnować temperatur
- priorytet: średni (bezpieczeństwo ustawień fabrycznych)

### K-030 · Enigma 12/16 GB: porównanie jakości kandydatów (AP-Q3_K_XL vs UD-Q3_K_XL na 16 GB, IQ3_XXS-mtp Swift W3 / ISTA na 12 GB) zestawem jakość-mini + KLD
- data: 2026-10-18 (16e), zgoda na porównanie 2026-11-09
- status: **czeka na decyzję** (źródła danych i pobrania modeli do potwierdzenia, [[2026-11-09-decyzje-runda-69]])
- źródło: [[raport-16e-kwanty-kld]], `R/67b-wybor-modeli-nvidia.md`, [[jakosc-mini]]
- test: 5060 Ti: `~/qwen-opt/jakosc-mini/run.py gen` + KLD na każdym kandydacie (> 10 min, podzielić po zbiorze)
- zysk: wybór modeli katalogu (AP vs U3: KLD czat −12%, kod −23% przy tych samych bajtach)
- ryzyko karty: brak
- priorytet: średni (produkt)

### K-031 · Maska KQ poza ścieżką krytyczną albo pochodna maska w kernelu (bez `n_kv × n_tokens` z hosta)
- data: 2026-10-13 (K3), 2026-11-07 (66 #9, 68c #4)
- źródło: [[maska-kq-host-dlugi-ctx]], [[2026-11-08-kvq-once-profil]] (`:50,89`: `graph→inputs` 355 µs przy 199k), `R/68c-dlugi-kontekst-gdn.md:15-17,138`
- test: XTX `LLAMA_HOSTGAP_TRACE=16` + xtxbench decode 199k ABBA, md5 (osobny job na 199k)
- zysk: decode 199–255k +0,5…1,5%, fill 255k +0…3%, −256 MiB VRAM i −256 MiB pinned [SZACUNEK]
- ryzyko karty: brak (host); wariant w kernelu = nowy kernel w PM4
- priorytet: niski (sam poniżej progu, łączyć z K-012)

### K-032 · Amplifikacja odczytu KV w `kvq` (bajty z liczników vs 1152 B/token/warstwę)
- data: 2026-11-07
- źródło: `R/68a-rdna3-kernele.md:124` (4.6), [[2026-11-08-kvq-once-profil]] (`:77`, `FETCH_SIZE` = 0)
- test: XTX `rocprofv3 --pmc TCC_EA_RDREQ_sum TCC_EA_RDREQ_32B_sum` na `llama-bench -fa 1 -ctk q4_0 -ctv q4_0 -p 5 -ub 5 -d 131072`, `GGML_HIP_PM4=0`; ≤ 10 min
- zysk: 0…3% decode przy ≥ 128k [INFERENCE]; zasila K-012
- ryzyko karty: brak
- priorytet: niski (diagnostyka)

### K-033 · Diagnoza FCLK/MCLK pod obciążeniem, stock vs eco (tylko odczyt `pp_dpm_*`)
- data: 2026-10-12
- źródło: `R/68a-rdna3-kernele.md:122` (4.4), §2.9
- test: pętla `grep '\*' pp_dpm_{sclk,mclk,fclk}` co 0,25 s doczepiona do najbliższego spec_sweep (0 dodatkowego czasu)
- zysk: 0% sam; wyjaśnia, czy −1,9% decode na eco to fabric
- ryzyko karty: brak (odczyt)
- priorytet: niski (darmowa diagnostyka)

### K-034 · Nadmiar ~10 KiB/token VRAM (nachylenie 29,1 vs 18,4 KiB/token): znaleźć bufor rosnący z kontekstem
- data: 2026-11-05
- źródło: `R/63-SYNTEZA.md:88` (#9), `R/65-vram-rezerwa-mtp-kontekst.md` §5
- test: najpierw CPU (`llama-context`); XTX `-lv 4` przy 131k/262k i szczyt VRAM (fill osobnym jobem)
- zysk: +~2,7 GiB zapasu przy 262k [SZACUNEK], 0 t/s; zapas na OOM i `-ub 1024`
- ryzyko karty: brak
- priorytet: niski (0 t/s)

### K-035 · Głowica draftu MTP: grube przejście (IQ4_XS/Q2_K) + dokładny rerank top-8 na wierszach Q6_K
- data: 2026-10-20 (36 L6c), 2026-11-07 (66 #5)
- źródło: [[glowica-draftu-rerank]], `R/66-SYNTEZA.md:56`
- test: offline na logitach (czy top-8 grubej głowicy zawiera argmax Q6_K); XTX spec_sweep T=1 + E0 + `mvs` ABBA ≤ 10 min
- zysk: +1…3% (B1), +1…4% (B2) [SZACUNEK]; cel nietknięty, md5 bez zmian
- ryzyko karty: brak
- priorytet: niski (poniżej progu)

### K-036 · Nakładanie kroków: wejścia kroku t+1 przed synchronizacją hosta (ZOS-lite), obcinanie po stop-tokenie na GPU
- data: 2026-10-20 (36 L11)
- źródło: `R/36-xtx-qwen-roadmap.md:196`, `R/63-SYNTEZA.md:90`, `R/66-SYNTEZA.md:63`, `R/67c-nvidia-backlog-testow.md:129` (C12)
- test: md5 + test „stop-token w środku okna”, spec_sweep ABBA ≤ 10 min (XTX i 5060 Ti)
- zysk: XTX +0,7…1,8% (luka GPU 410 µs z 27,3 ms), 5060 Ti ≤ +3,9%, LFM +4…6%
- ryzyko karty: PM4 (zmiana porządku taśm)
- priorytet: niski (XTX poniżej progu)

### K-037 · Megakernel / rezydentna pętla MTP (PoC-A w trwałej siatce 96–192 WG)
- data: 2026-10-16 (15a), 2026-11-07 (66c)
- źródło: [[budzet-megakernela-qwen-xtx]], [[lekcja-megakernel-prefetch-nie-granica]], `R/66c-hyperkernel-megakernele.md` §7
- test: XTX mikrobench PoC-A (kill > 0,3 µs albo < 30% zysku „bez granicy”); ≤ 10 min, kod 1–1,5 dnia
- zysk: krótki ctx +4…9,5%, 199k +2…4%, za 40–70 osobodni [SZACUNEK]
- ryzyko karty: **wysokie**: ewikcja kolejki KFD przy kernelu rezydentnym → możliwy reset
- priorytet: niski (koszt i ryzyko; wspólny PoC z K-021)

### K-038 · Przeszukiwanie flag spekulacji (TPE: DRAFT_N, LOOKUP_W/MMIN, PM4_MIN_DISPATCH, typ KV draftu) na odłożonym zestawie
- data: 2026-11-05
- źródło: `R/63-SYNTEZA.md:93` (#14), `R/63e-metodologia-agenci.md` §11, [[zestaw-odlozony]]
- test: XTX xtxbench `--var-switch` po jednej fladze na job (~4 min), zwycięzcy na holdoucie; zmiany szerokości tylko po K-007
- zysk: spec_sweep +1…5% [SZACUNEK]
- ryzyko karty: brak
- priorytet: niski (szum, klątwa zwycięzcy)

### K-039 · Q5_K MMVQ `big_rows` (`GGML_HIP_MMVQ_Q5K_BIG_ROWS=6144`): dokończyć ABBA i sprawdzić env w produkcji
- data: 2026-10-20 (raport 50b)
- źródło: [[raport-50b-mmvq-q5k]], `R/43-integracja-2026-10-20.md:68`, archiwum (`A:36426`: „brakuje 2 z 4 ramion”, md5 PASS)
- test: XTX `~/qwen-opt/queue/i43-int7.jobs` od `i43g-B1b` (2 ramiona × ~2,5 min)
- zysk: kernel −1,3…−3,5%, ~+0,4% decode
- ryzyko karty: brak
- priorytet: niski (poniżej progu, łączyć)

### K-040 · Flaga kompilatora `-mllvm --amdgpu-unroll-threshold-local=600`
- data: 2026-11-07
- źródło: `R/68a-rdna3-kernele.md:126` (4.8)
- test: build + `klab isadiff` gorących kerneli (CPU); GPU tylko, gdy ISA się zmienia: `llama-bench -p 4096` + spec_sweep ABBA + md5 ≤ 10 min
- zysk: 0…2% [INFERENCE]
- ryzyko karty: brak (spille przy większej liczbie VGPR)
- priorytet: niski (tani, mały)

### K-041 · Licznik realokacji grafu (#30329): czy przejścia MTP5 ↔ W16 ↔ catch-up przebudowują graf albo taśmę PM4
- data: 2026-11-07
- źródło: `R/68d-swieze-od-spolecznosci.md:141` (#7)
- test: XTX serwer testowy, replay sesji agenta, licznik w logu + `GGML_HIP_PM4_DEBUG`; ≤ 10 min
- zysk: 0% wprost; kilka % na krokach zmieniających szerokość, jeśli realokacje istnieją [INFERENCE]
- ryzyko karty: brak
- priorytet: niski (diagnostyka)

### K-042 · Spekulatywny prefill następnej tury w przerwie (serwer prefilluje swoją odpowiedź, przerywa na granicy ubatcha)
- data: 2026-11-07
- źródło: `R/68c-dlugi-kontekst-gdn.md:140` (#6)
- test: XTX replay sesji (`agent_bench`): TTFT na turę, trafienie prefiksu (LCP), md5 „trafienie vs zimny start”; ≤ 10 min/ramię
- zysk: ~10–25% czasu małych tur [SZACUNEK], więcej przy ≥ 128k
- ryzyko karty: brak (GPU zajęte w przerwach)
- priorytet: niski (zależne od klienta)

### K-043 · Profil i optymalizacja atencji draftu MTP przy długim kontekście (~1,3 ms/krok przy 199k), np. pamięć MASW (ujścia + okno + sloty)
- data: 2026-11-07
- źródło: `R/68c-dlugi-kontekst-gdn.md:144` (#10), [[2026-11-08-kvq-once-profil]] (`:92`)
- test: offline symulacja akceptacji MTP z oknem 128 + sloty; potem spec_sweep + xtxbench 199k. Wymaga treningu adaptera.
- zysk: sufit +3…5% przy 255k minus spadek akceptacji [SZACUNEK]
- ryzyko karty: brak
- priorytet: niski (trening, niepewne; samo okno MTP to KILL, K-090)

### K-044 · Leave-one-out łatek (`loo.py run`) i Kernel Tuner (`kt tune`) na GPU
- data: 2026-10-15 (runda 6)
- źródło: [[runda-6]], [[loo]], `Q/STATUS-NEXT.md:31-37`, `R/07-nasze-metody-uogolnienie.md:250-252`
- test: XTX `GGML_HIP_PM4=0`, po jednej łatce/fladze na job (xtxbench ~4 min); LOO ~3,8 h + buildy w sumie
- zysk: 0 t/s wprost; wykrywa łatki bez zysku (koszt utrzymania)
- ryzyko karty: niskie (mikrobenche)
- priorytet: niski (higiena)

### K-045 · Model kosztu weryfikacji MoE LFM2.5 (pomiar G1) i drafter dla LFM (LFM2.5-2.6B-QAD-Q4_0 jest na dysku)
- data: 2026-10-19 (raport 18), drafter 2026-10-14
- źródło: [[model-kosztu-weryfikacji-moe]], [[raport-24d-lfm-lookup]], archiwum (`A:36446`)
- test: XTX `llama-bench -p 1,2,3,4,5,8,16 -n 0 -d 0,32768` (bramki T(8) ≤ 13,6 ms, T(3) ≤ 6,8 ms); potem LFM24B + draft 2.6B spec_sweep T=1 + `mvs`; ≤ 10 min każdy
- zysk: decyduje, czy tani drafter dla LFM ma sens (od α ≈ 0,4); LFM poza produkcją
- ryzyko karty: VRAM (+1,6 GB draftera przy KV q8_0 131k)
- priorytet: niski (LFM poza produkcją)

### K-046 · Szerokość ogona lookup zależna od kontekstu: W16 → W8/W5 przy ≥ 128k (`LLAMA_SPEC_LOOKUP_ADAPT=1`)
- data: 2026-10-18, 2026-11-07 (68c #7)
- status: **czeka na decyzję** (bramka K-007, zmiana szerokości zmienia md5)
- źródło: `R/68c-dlugi-kontekst-gdn.md:141`, [[kontroler-szerokosci-draftu]]
- test: najpierw dane z CPU (`LLAMA_SPEC_LOOKUP_LOG`: udział kroków `tail` przy n_past ≥ 128k); XTX `ADAPT=1` vs W16 na replayu 128–200k ABBA ≤ 10 min
- zysk: krok W16 przy 255k to ~+20–25 ms; zależy od udziału ogonów (kill < 2% kroków)
- ryzyko karty: brak
- priorytet: niski (najpierw dane)

### K-047 · GDN w weryfikacji: forma chunkwise/WY w fp32 albo fuzja conv + rekurencja + gated RMSNorm ze stanem w VGPR
- data: 2026-11-05 (63 #21)
- status: **czeka na decyzję** (inna kolejność redukcji fp32 → bramka KLD, nie md5)
- źródło: `R/68b-spekulacja-nowe.md:162`, `R/68-SYNTEZA.md:20`
- test: XTX `test-backend-ops perf -o GATED_DELTA_NET` (n 5/8/16), spec_sweep ABBA, KLD + md5 plain; ≤ 10 min/krok
- zysk: +1,1…1,7% na każdym kontekście [SZACUNEK]; tańszy wiersz dla drzew (K-075)
- ryzyko karty: brak
- priorytet: niski (poniżej progu)

### K-048 · Mikrobatch prefillu `-ub 1024` dla Qwena (po odzyskaniu VRAM)
- data: 2026-10-12 (A7)
- status: **czeka na decyzję**, jeśli md5 ≠ (zmiana ub zmienia kolejność sum)
- źródło: `Q/NOTES.md:218` (ub 2048 pp +3%, OOM przy 204800), `R/63-SYNTEZA.md:84`
- test: XTX md5 greedy 12k ub 512 vs 1024 (jeśli różne → do Odrzuconych); jeśli równe, `llama-bench -p 4096 -ub 1024` + szczyt VRAM przy fill 255k osobnym jobem
- zysk: pp4096 +3…8% [SZACUNEK]
- ryzyko karty: **VRAM OOM przy 262k**
- priorytet: niski (OOM, numeryka; po K-022/K-034)

### K-049 · ROCm 10.1 na gfx1100: md5 + hash logitów + pomiar `kvq` (spill 8 VGPR)
- data: 2026-10-16 (raport 13), 2026-11-05 (63c)
- źródło: [[rocm-10-1]] (`:28-30`), [[lekcja-rocm10-lds-128kb]]
- test: build topki na `~/opt/rocm-10.1` (CPU), XTX md5 greedy/long 32k + xtxbench t1; ≤ 10 min
- zysk: nieznany (RDNA-FAST: 10.1 +3,1% vs 7.2 na innej bazie); `kvq` może zwolnić przez spill
- ryzyko karty: nowy runtime + PM4 (możliwy fault/reset)
- priorytet: niski (niepewny zysk, ryzyko)

### K-050 · Runtime ROCm 7.2.4 z kompilatorem ROCm 10
- data: 2026-11-07
- status: **czeka na decyzję** (pobranie runtime)
- źródło: `R/68a-rdna3-kernele.md:127` (4.9)
- test: XTX `LD_LIBRARY_PATH` na 7.2.4, `llama-bench -p 512,4096 -d 0,16384 -r 3` ABA ≤ 10 min, potem soak PM4
- zysk: prefill 0…+5% (dane z innej XTX); decode ~0 (PM4 omija runtime)
- ryzyko karty: **wysokie**: PM4 zależy od ROCr/CLR (raport 17), page faulty/resety
- priorytet: niski (ryzyko > zysk)

### K-051 · Wyjaśnić ~16 tys. wierszy `amdgpu: init_user_pages: Failed to get user pages: -1` przy każdym starcie serwera
- data: 2026-11-06
- źródło: [[init-user-pages-failed]]
- test: XTX dwa starty serwera `--mmap` vs `--no-mmap`, licznik wierszy w `journalctl -k`, bez obciążenia; ≤ 10 min
- zysk: diagnostyka (krótszy start, czystszy log jądra); 0 t/s
- ryzyko karty: brak
- priorytet: niski (diagnostyka)

### K-052 · HRX (Lemonade `hrx-b99`) jako referencja kerneli: tg128/pp512/pp4096 obok topki
- data: 2026-11-07
- źródło: `R/68a-rdna3-kernele.md:125` (4.7)
- test: XTX `llama-bench -fa 1 -p 512,4096 -n 128 -r 3` HRX vs topka, eco (~30 min → 3 joby); wymaga buildu i pobrania HRX
- zysk: 0% wprost; wzór do portu, jeśli HRX wygra prefill (producent: +30–50% vs HIP upstream)
- ryzyko karty: nieznany runtime (inne kolejki, bez gpu-guard)
- priorytet: niski (wiedza)

### K-053 · Wspólne punkty odniesienia: zestaw YASAKANI/NInfer (12 zadań + edycja) na XTX
- data: 2026-11-05
- źródło: `R/63-SYNTEZA.md:104` (#25), `R/63a-silniki-lokalne.md` §9
- test: XTX ~15 min (2 joby)
- zysk: wiedza i porównanie 1:1 z innymi silnikami; 0 t/s
- ryzyko karty: brak
- priorytet: niski (wiedza)

### K-054 · EvalPlus z `--effort xhigh` vs `low`: czy effort low kosztuje dokładność
- data: 2026-11-09
- źródło: [[2026-11-09-evalplus-qwen-uncensored]] (`:25`), [[evalplus-jakosc-kodu]]
- test: XTX `~/qwen-opt/evalplus/jakosc-mini.sh --effort xhigh --port 8097 all` (HE+ 164 + MBPP+ 378; > 10 min, podzielić po zbiorze)
- zysk: jakość, nie prędkość; potwierdza albo zmienia domyślny effort low (dziś HE+ 92,7%, MBPP+ 80,2%)
- ryzyko karty: brak
- priorytet: niski (nie prędkość)

### K-055 · Usunąć z topki martwy kod capu LDS FA (`57204db1e`, no-op na ROCm 10.0 pre4) przy najbliższym buildzie
- data: 2026-11-06
- źródło: [[2026-11-05-q63-topka]] (wynik negatywny), dawny wpis `DO-ZAPISANIA.txt`
- test: przy następnym buildzie produkcji bramka md5 (long 32k e460e3b6, fill 255k 31b6525a); bez osobnego okna GPU
- zysk: 0 (porządek w kodzie)
- ryzyko karty: brak
- priorytet: niski (przy okazji)

### K-056 · Rebase łatek topki na nowszy upstream (baza b11528 → llama.cpp v1.0.0 = b12359)
- data: 2026-10-16, ostatnio 2026-11-07
- źródło: [[2026-10-16-rebase-v070]], `R/68d-swieze-od-spolecznosci.md:14,18` (#31247 przesunie md5)
- nowe (2026-11-14): v1.0.0 zawiera już u nas portowane #30137, a do tego #30541 (kopia stanu dla skwantowanego KV, K-001), #31533 (few-row MMQ CUDA, K-013/K-103), #31927 (MTP czyta stan celu z bufora na urządzeniu), #32078 (tylko fuzowany GDN), #32009/#32089 (ponowne użycie schedulera), #31838 (ROCm: stały workspace BLAS); API: `defrag_thold` usunięte, NextN w `llama.h`
- test: build (CPU), XTX greedy md5 vs baza, `test-backend-ops`, spec_sweep A/B ≤ 10 min/ramię; zmiana md5 przez #31247 → bramka KLD
- zysk: poprawki upstream; prędkość ~0 (68d: „prawie wszystko topka ma mocniej”)
- ryzyko karty: nowe kernele w PM4
- priorytet: niski (mało zysku)

### K-057 · Tryb „identyczne odpowiedzi” `LLAMA_SPEC_BITEXACT=1` jako opt-in (port gałęzi `batch-invariant` na topkę)
- data: 2026-10-16 (raport 12)
- status: **czeka na decyzję** (wdrożyć przełącznik, domyślnie wyłączony)
- źródło: [[2026-10-16-bit-exact]], [[otwarte-decyzje-techniczne]] (`:14`), `STAN-PRAC.md` (BitExactSpec, `365af3e5e`)
- test: XTX `validate.sh` (plain == MTP) + spec_sweep krótko i przy 27k; ≤ 10 min
- zysk: ujemny (0% krótko, −9% przy ~27k); wartość: dowód bezstratności
- ryzyko karty: brak
- priorytet: niski (nie przyspiesza)

### K-058 · Strażnik „drugie `</think>` zabronione” w `reasoning-budget.cpp` (T7, niezależny od Astry)
- data: 2026-11-09
- status: **czeka na decyzję** (2d; zmienia wyjście tylko przy przecieku)
- źródło: `R/69-SYNTEZA.md:27,37-40` (A3), [[astra-stop]]
- test: build + md5 bazy (musi być =) + skan 50 zadań agentowych; ≤ 10 min/partię
- zysk: 0 t/s; poprawność formatu
- ryzyko karty: brak
- priorytet: niski (nie szybkość)

### K-059 · Pomiar w warunkach LocalMaxxing (`reasoning-v1`/`code-v1`, T=0, 320 tok.) do publikacji wyników XTX
- data: 2026-10-16
- status: **czeka na decyzję** (publikacja „wkrótce”, na razie tylko odczyt: [[2026-10-20-bez-publikacji-localmaxxing]], [[2026-11-09-decyzje-runda-69]])
- źródło: [[raport-32f-ninfer-tqllm]], [[raport-32d-localmaxxing]]
- test: XTX ~15 min (2 joby)
- zysk: 0 t/s (marketing); szacunek ~147 t/s w ich warunkach
- ryzyko karty: brak
- priorytet: niski (nie wydajność)

### K-060 · Pilot fabryki RSI-F: P0 (`./factory verify claims/2026-10-17-mmq-epi-0070.json`) i P1 (playbook 0070 na nowe cele)
- data: 2026-10-19 (21h)
- status: **czeka na decyzję**
- źródło: [[2026-10-19-plan-retro-rsr-0070]], [[petla-rsi-f]], [[otwarte-decyzje-techniczne]] (`:21`)
- test: XTX `GGML_HIP_PM4=0`, P0 ~20 min → 2 joby, P1 4 × 15–20 min
- zysk: walidacja fabryki, 0 t/s
- ryzyko karty: brak
- priorytet: niski (proces)

### K-061 · Tryb wielu użytkowników na NVIDIA: naprawić start `-np 4` z MTP (`failed to create context`), potem k zależne od liczby klientów (`K_BY_B`)
- data: 2026-10-21 (raport 56)
- źródło: `R/67c-nvidia-backlog-testow.md:110` (B16), `R/67-nvidia-vast-kampania.md` §7.2 (`-np 2` agregat +30…36%), `R/69b-tensorfold-qwen-warp.md:77`
- test: 5060 Ti: `-np 2/4` ctx 32k + MTP n=2, C = 1/2/4/8 klientów, suma t/s; ≤ 10 min
- zysk: agregat +20–30% (dane warp: ×2,7–2,9 przy 4–8 klientach); latencja 0
- ryzyko karty: VRAM OOM
- priorytet: niski (jeden użytkownik)

### K-062 · Dekoder FA CUDA z `__launch_bounds__(…,2)` (dual-CTA)
- data: 2026-11-07
- źródło: `R/67c-nvidia-backlog-testow.md:121` (C4), `R/66b-1cat-tokenspeed.md:97-98`
- test: 5060 Ti: perf FA + long_ctx, md5; ≤ 10 min/krok (po K-027)
- zysk: 1Cat V100 128k +19% bitowo; u nas po `kvq` nieznane
- ryzyko karty: brak
- priorytet: niski (po profilu)

### K-063 · Wyzwalacz PDL + prefetch L2 przed `pdl_sync` w gęstym MMVQ (sm_120) i sterowanie L2 (`evict_first`, persisting window `GGML_CUDA_L2_PERSIST`)
- data: 2026-10-19 (21b)
- źródło: [[pdl-mmvq-trigger]], [[l2-persist]], `R/67c-nvidia-backlog-testow.md:122-125` (C5–C8)
- test: 5060 Ti: `GGML_CUDA_MMVQ_PREWAIT=0/1/2`, `WEIGHT_EVICT_FIRST`, `L2_PERSIST`, md5 + tg128/spec_sweep ABBA; ≤ 10 min każdy; kill < +1,5% LFM tg128
- zysk: LFM +1,1…4,6%, Qwen +0,7…2,6% (PDL); L2 +0,5…2% [SZACUNEK]
- ryzyko karty: brak
- priorytet: niski (małe)

### K-064 · Zwinięcie haka promptu MTP do grafu celu (TTFT) w forku CUDA
- data: 2026-10-16
- źródło: `R/67c-nvidia-backlog-testow.md:113` (B19), `R/15d-prefill-dlugi-kontekst.md:110`
- test: 5060 Ti: build + TTFT 512/2k, md5; ≤ 10 min
- zysk: TTFT −5…7% przy 2k
- ryzyko karty: brak
- priorytet: niski (mały TTFT)

### K-065 · Zimny start `--no-mmap` (pierwszy prompt po restarcie 0,39–1,07 t/s) i nieprzetestowane flagi upstream (`--spec-draft-n-ubatch 64`, `GRAPH_CHUNK_SIZE`, `-fa off`, `--spec-default`)
- data: 2026-11-07
- źródło: `R/67c-nvidia-backlog-testow.md:79-91` (A4, A8, A10, A12, A16)
- test: 5060 Ti, po jednym ramieniu na job ≤ 10 min
- zysk: A12: TTFT pierwszego żądania; reszta ~0 [INFERENCE]
- ryzyko karty: brak
- priorytet: niski (UX)

### K-066 · Pipeline kafli MMQ w stylu DeepGEMM / strojenie configu MMQ IQ4_XS (`mmq-config-ampere.cuh`) pod prefill CUDA
- data: 2026-10-16 (15d), 2026-10-21 (Orca)
- źródło: `R/67c-nvidia-backlog-testow.md:133` (C16), sesja Orca (`O:1788-1796`, `O:2187-2196`: occupancy 2 → −11,5%)
- test: przebudowy compile-time + `llama-bench -p 512,4096` + md5/PPL; 5060 Ti lokalnie, 3090 wynajem
- zysk: pp +3…12% (DeepGEMM), +10–20% (config IQ4_XS) [SZACUNEK]
- ryzyko karty: brak
- priorytet: niski (dużo pracy)

### K-067 · Kernel GDN chunked MMA w CUDA zintegrowany z cache i snapshotami (gałąź `orca-gdn2`)
- data: 2026-10-21 (Orca)
- źródło: sesja Orca (`O:1449-1462`: +10,5% pp2048, ale PPL nan; po poprawce 0%; `O:1791`)
- test: PPL + md5 + pp2048, 3090 (wynajem), 2–3 h → podzielić
- zysk: do +10% prefillu
- ryzyko karty: brak
- priorytet: niski (numeryka do naprawy)

### K-068 · CUDA `kvq`: KLD wariantu z wyjątkiem n=1 D256 q4_0 (`678473a27`) i serwer MTP@64k z wyjątkiem
- data: 2026-10-18
- źródło: `STAN-PRAC.md` (CudaKvq, „Niezmierzone”), [[2026-10-16-kvq-cuda-zostaje]]
- test: `llama-perplexity --kl-divergence --chunks 5` Qwen q4_0 ub1 + serwer MTP 64k; 3090 (wynajem) albo 5060 Ti przy mniejszym kontekście; ≤ 10 min/ramię
- zysk: poprawność (przy ub1 = vec z konstrukcji [INFERENCE])
- ryzyko karty: brak
- priorytet: niski (formalność)

### K-069 · Turing sm_75 (2080 Ti): build forka i smoke test
- data: 2026-11-07
- źródło: `R/67c-nvidia-backlog-testow.md:149` (D6)
- test: build `-DCMAKE_CUDA_ARCHITECTURES=75`, `test-backend-ops`, fork vs upstream; wynajem ≤ 10 min po buildzie
- zysk: nieznany; poprawność dla klasy 11 GB w Enigmie
- ryzyko karty: brak
- priorytet: niski (mała klasa)

### K-070 · NVIDIA: soak termiczny 600 s przy fill 262k (E3) i sweep limitu mocy → perf/W na wynajętych kartach (E1)
- data: 2026-11-07
- status: E1 **czeka na decyzję** (zmienia limit mocy; czy zasada „karta fabrycznie” obejmuje karty z wynajmu); E3 otwarte
- źródło: `R/67c-nvidia-backlog-testow.md:152,154`
- test: E3 `stab soak_s=600` (10 min); E1 4 ramiona × ~3 min (`nvidia-smi -pl` 100/85/70/55% TDP), tylko wynajem
- zysk: dane do „cichego trybu” Enigmy; 0 t/s
- ryzyko karty: E1 zmiana mocy; E3 temperatury
- priorytet: niski (produkt)

### K-071 · qwen-warp: DFlash2 ≤ 64k na replayu agentowym (W2)
- data: 2026-11-09
- status: **czeka na decyzję** (3,85 GB pobrania na wynajmie)
- źródło: `R/69-SYNTEZA.md:29` (W2), `R/69b-tensorfold-qwen-warp.md:65`
- test: 3090 (wynajem), ten sam replay co spec_sweep, oba drafty, ~10 min/ramię
- zysk: czat ×1,07–1,34, agent z kopiowaniem −31% (dane autora); u nas −10…+10% [INFERENCE]
- ryzyko karty: brak
- priorytet: niski (agent traci)

### K-072 · Nemotron 3.5 Bolt na NVIDIA: KLD fuzji `GGML_CUDA_TOPK_MOE_NP2`, `MMVQ_N1_IQ2`, kernel IQ2_XXS MMVQ, replay stanu Mamby
- data: 2026-10-16 (raport 14 §10)
- status: **czeka na decyzję** (model odłożony „na później”)
- źródło: `R/14-nemotron-3090.md`, `R/67c-nvidia-backlog-testow.md:114` (B20), `STAN-PRAC.md` („Odłożone”)
- test: 3090/4090 (wynajem), KLD vs upstream (~$0,3) + A/B per łatka ≤ 10 min
- zysk: 87,2 → 141,1 t/s już zmierzone; KLD warunkuje publikację; łatki razem +6,1%
- ryzyko karty: brak
- priorytet: niski (model poza katalogiem)

### K-073 · Flint (NVFP4) na XTX: rozstrzygnąć nieudany test igły przed katalogiem Enigmy
- data: 2026-10-21
- status: **czeka na decyzję** (inny model; PR #30928 niescalony)
- źródło: `R/59-flint.md`, archiwum (`A:37717-37753`)
- test: XTX needle przy długim kontekście, Flint na topce z poprawkami (`run-topka.sh flint`); ≤ 10 min
- zysk: ~2× vs Qwen27B na XTX, ale to zmiana modelu
- ryzyko karty: temperatury (prefill 160–262k: junction 94 °C, 286 W przed eco)
- priorytet: niski (inny model)

### K-074 · OrcaCyber-Nano na XTX z drafterem DFlash2 (dotąd tylko 3090) i E1 RSR-27B vs Qwen (TB 2.1, omp-bench-20)
- data: 2026-10-19 / 2026-10-21
- status: **czeka na decyzję** (Orca: tylko na prośbę; RSR-27B: wydatek $40–70, ~120 GPU-h)
- źródło: [[raport-56-orca-3090]], [[2026-10-19-plan-e1-rsr27b]], [[otwarte-decyzje-techniczne]] (`:22`)
- test: Orca: XTX MTP vs DFlash2 ≤ 10 min; RSR: wynajem, test do zdefiniowania
- zysk: wiedza o innych modelach; 0 t/s dla produkcji
- ryzyko karty: VRAM (Orca 15,7 + 2,1 GB przy 262k)
- priorytet: niski (inne modele)

### K-075 · Drzewo weryfikacji MTP na hybrydzie GDN (forma WY, maska przodków)
- data: 2026-10-20 (24s), 2026-11-07 (66d C)
- źródło: [[drzewo-weryfikacji-gdn-wy]], `R/66-SYNTEZA.md:65`, `R/68b-spekulacja-nowe.md` („dziś kill”: +1,6% przy 0,85 ms/wiersz)
- test: najpierw symulacja `tree_dynamic` na logach MTP (CPU); na XTX tylko koszt wiersza (`test-backend-ops perf` MMVQ n=5 vs n=6) ≤ 10 min; wraca dopiero, gdy wiersz ≤ 0,57 ms (po K-013)
- zysk: kod/T=0 +3…8%, czat T=1 0…+4% [SZACUNEK]
- ryzyko karty: nowe kernele GDN w PM4
- priorytet: niski (zależne od K-013 i K-007)

## W toku

(pusto)

## Zrobione

(pusto; pierwsze wyniki z tej kolejki trafią tutaj z liczbami baseline → teraz → przyrost i linkiem do eksperymentu. Wcześniejsze wdrożenia: [[REKORDY]], np. topka-q70 z 2026-11-09: [[2026-11-09-wdrozenie-topka-q70]])

## Odrzucone

### K-076 · Astra-Stop (LoRA rank-1 skracająca myślenie)
- powód: zmienia zachowanie, przeciek `</think>` 11/32; decyzja właściciela 2026-11-09 ([[2026-11-09-decyzje-runda-69]], [[astra-stop]]). Wraca tylko jako temat fine-tuningu z benchmarkami.

### K-077 · DSpine-27B jako drafter (także test τ T1)
- powód: na 24 GB obcina kontekst do ~64k, proza i PL gorzej niż MTP, mieszanka agentowa +0…4%; decyzja 2026-11-09 ([[drafter-dspine]]).

### K-078 · Zmiana kwantu dla prędkości (lżejszy GGUF wzorem qwen-warp ×1,24, IQ4_XS/Q4_0, mieszanki per tensor, LFM Q4_K_M/QAD-Q4_0, EXL3, NVFP4, Flash-Next, DCQ)
- powód: zmienia odpowiedzi; zakaz właściciela „nie zmieniamy kwantów, żeby przyspieszyć” ([[dcq-kotwica-stanu-gdn]], [[2026-11-09-qwen-warp-vs-fork-3090]]).

### K-079 · Stratna atencja i KV: QSA, LSA, KVA, FLy, KV 3-bit / FP8 / blok 16, PearlQuant (E8, 3,2 bita), stan GDN fp16/bf16/int8, Nucleus SD, `--cache-reuse-hybrid`, HIP fast-math, chunked GDN bf16, `kvq` CUDA P·V f32
- powód: zmienia odpowiedzi (KLD ≠ 0); decyzja „tylko bezstratne” ([[2026-11-05-tylko-bezstratne]]).

### K-080 · FA D256: 83 + `exp2f` (maska 91), config #31746, `nbatch_fa` 32
- powód: zmienia md5 (stratne, ~+1,5% fillu); tylko w pakiecie stratnym z bramką KLD ([[2026-11-08-fa-d256-prefill]]).

### K-081 · PFlash: stratny tryb „szybki odczyt długich dokumentów”
- powód: stratny; decyzja „tylko bezstratne” ([[tryb-stratny-pflash]]).

### K-082 · Uncensored jako tryb w locie (rzut `h ← h − r(r·h)`) / restore KV z drugiego modelu
- powód: nie jest bit-exact (inne wagi efektywne) ([[przelaczanie-main-uncensored]]).

### K-083 · Wykrywacz pętli myślenia / kierunek pętli jako LoRA (WSP E1–E3)
- powód: zmienia odpowiedzi; decyzja właściciela. Obserwacja: 1/290 odpowiedzi jakość-mini zapętliła się do 32 768 tok. ([[2026-11-09-jakosc-mini-qwen-unc]]).

### K-084 · Podkręcanie VRAM, wymuszony FCLK, limit mocy, undervolt XTX
- powód: karta zostaje fabrycznie ([[2026-10-20-karta-fabrycznie]]); jedyny wyjątek to wdrożony eco 2200 ([[2026-11-06-profil-eco-2200]]).

### K-085 · Cache sesji na SSD / slot save przeżywający restart (`--slot-save-path`)
- powód: decyzja „KV tylko w RAM” ([[2026-10-19-kv-tylko-w-ram]]). Szacunek przy powrocie do tematu: pierwsza tura po restarcie przy 50k ~55 s → ~2–4 s.

### K-086 · Więcej slotów `-np 2` / `-np k` na XTX dla roju agentów
- powód: zmierzone 24c: pojedyncze żądanie −5…−17%, fan-out omp wall +11%, ~2,4 GB stanu na slot ([[wyniki-negatywne]]).

### K-087 · `kvq` raz na weryfikację: ONCE=1 / ONCE=2 i przegląd podziałów
- powód: KILL 2026-11-08: ONCE=1 FA −6,1% (e2e +0,9…1,8%), ONCE=2 −0,38%, podział domyślny najlepszy ([[2026-11-08-kvq-once-profil]]). Cel nowego układu żyje w K-012.

### K-088 · Q6_K MMQ: skale jednym `int`
- powód: KILL 0,0% ([[2026-11-07-q6k-mmq-skale]]).

### K-089 · Cache tokenizacji + parser O(n) / parser raz na krok MTP (l1tok)
- powód: −85 ms na turę (tokenizacja 14,0 → 6,6 ms), md5 =, ale poniżej progu ≥ 1 s/turę ([[2026-11-08-l1-tokenizacja-parser]], [[strumien-on-wyrocznia]]).

### K-090 · Okno uwagi draftu MTP (`--spec-mtp-window`, mtpw)
- powód: KILL 2026-10-14, job mtpw anulowany przez właściciela 2026-11-09; zysk maks. ~1,3 ms/krok.

### K-091 · Łatka 0071 `GGML_HIP_MOE_GU_BLOCK` (LFM gate+up)
- powód: LFM +0,33%, Uncensored +1,39%, poniżej progu 3–5% ([[2026-10-18-lfm-moe-pasmo]]).

### K-092 · Drobne kernele poniżej progu: LaunchCut, shortlist draftu EAGLE, Q6_K/Q4_K MMVQ big_rows/stream, GDN bank v3, merge split-KV, split-K MMVQ 1024, taśma delt GDN, fuzje kleju GDN, cięcia granic poza łańcuchem MMVQ, `opt-gdn6`, dalsze rundy klab
- powód: zmierzone −1,9…+0,7% (szum) albo ≤ 2% u autora; kernele na 77–88% z 926 GB/s, zapas leży w drafterze ([[runda-6]], `R/54-mniej-granic.md`).

### K-093 · PM4-PDL, prefetch wag do Infinity Cache, trwała siatka zamiast PM4, czekanie LFM po stronie GPU w taśmie PM4
- powód: 16a: PDL −0,11 µs, MALL w szumie; PM4 z guardem ma 0 faultów; czekanie GPU-side w taśmie = ryzyko resetu za ≤ 1,2% LFM ([[trwala-siatka-bez-pm4]]).

### K-094 · Prefetch L2 w pętli MMVQ (CUDA, `ncols_dst ≥ 2`) i szeroki loader `mmvq_ld` (b128)
- powód: KILL: −0,4…−0,8% i −1,0% tg128 ([[mmvq-prefetch-l2]], [[mmvq-n1-wiersze]]).

### K-095 · Próg pewności draftu `p_min`, obcinanie po iloczynie (`LLAMA_DRAFT_CUMP`), adaptacyjna długość z historii, bitexact + adaptacyjna głębokość (E5)
- powód: `p_min` 0,3 neutralne, 0,5 −7%, 0,5/0,8 gorzej na NVIDIA; E5 ≈ 0; żywa jest tylko wersja z luką Gumbela (K-008). Wyjątek: MoE z offloadem w Enigmie (K-026).

### K-096 · Lookup nadpisujący MTP („zastąp, gdy pewny”)
- powód: −1…−2%, bo MTP trafia w 96,8% tam, gdzie lookup (`R/15b`).

### K-097 · DFlash / DFlash2 na XTX: blok „draft 16, verify k”, słownik głowicy, `LLAMA_DFLASH_SAMPLE`, tryb kod/T=0 EN
- powód: szeroki blok wolniejszy (89,7 vs 104,8 t/s), PL proza ×0,67, MTP + lookup wygrywa; inny tekst T=0 niż produkcja ([[qwen-runda-5]]).

### K-098 · Douczanie głowicy MTP na polskiej prozie (self-distillation 20M tok.)
- powód: pilot 1,7M tok. dał −0,2…+0,2%, głowica jest na optimum ([[2026-10-16-mtp-pl-pilot]], [[lekcja-mtp-glowica-optimum]]).

### K-099 · Bezstratna kompresja wag (entropia, styl DFloat11) czytana w locie
- powód: skale to 2,19% bajtów UD-Q4_K_XL; sufit ≤ 5%, realnie < 1% (24t).

### K-100 · Ścieżka Vulkan, kernele 2-bitowe dla Saluki, MiniCPM5-2B przy 131k
- powód: decyzje właściciela (ROCm domyślny od 2026-10-12, Saluki porzucony 2026-10-14, CC BY-NC); MiniCPM poza produkcją.

### K-101 · `LLAMA_LFM2_MSG_SPANS=1` (start sesji LFM 230 → 166 ms)
- powód: −64 ms tylko dla LFM, poniżej progu ≥ 1 s/turę ([[REKORDY]] `:66`).

### K-102 · Bisekcja regresji prefillu forka vs upstream na NVIDIA z 15d (−1,5…−1,9%)
- powód: część wyjaśnił hak MTP (2,2–2,6% TTFT, 16f); reszta poniżej progu i zastąpiona szerszą K-023.

## Powiązane
- [[index]]
- [[REKORDY]]
- [[ZRODLA]]
- [[decyzje/_hub|decyzje]]
- [[sweep-wariantow-kernela]]
- [[xtxbench-szybki-ab]]
