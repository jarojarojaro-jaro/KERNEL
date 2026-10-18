---
typ: hub
tags: [research, hub]
aktualizacja: 2026-10-16
zrodlo: wiki/tools/wiki.py index
status: aktualne
---
# Research

**Streszczenia raportów badawczych: produktowych (01–10), technicznych i głównego raportu o AMD.**

Pełne raporty leżą w `product/research/`, `qwen-opt/research/` i `reports/`; tu są wnioski z liczbami i linkami.

Wróć: [[index|Strona główna]]. Lista niżej jest generowana przez `python3 tools/wiki.py index`; nie edytuj jej ręcznie.

<!-- AUTO:START -->
## Notatki (34)

- [[repos-30-przeglad|Przegląd 30 repozytoriów (REPOS-PODSUMOWANIE)]] — Przegląd 30 repo o kernelach GPU + aktualizacja TensorFold (2026-10-14): werdykty, ranking eksperymentów dla LFM i Qwena oraz lista odrzuconych pomysłów.
- [[raport-01-konkurencja|Raport 01: konkurencja]] — Detekcja sprzętu i rekomendacja modelu to już standard; żaden produkt konsumencki nie łączy pomiaru, długiej optymalizacji poza flagami, weryfikacji bitowej i raportu przed → po (stan 2026-10-15).
- [[raport-02-autotuning|Raport 02: autotuning i agenci kerneli]] — Duże „przed → po” robi praca wykonana raz w labie, nie strojenie u użytkownika; agenci kerneli działają tylko z mocną bramką i zostają w labie.
- [[raport-03-silniki|Raport 03: silniki inferencji i stack]] — Bazą zostaje llama.cpp jako cienki overlay łatek, nie twardy fork; rdzeń w Rust, GUI w Tauri 2, daemon z API OpenAI na 127.0.0.1.
- [[raport-04-sprzet|Raport 04: wykrywanie sprzętu i dobór modeli]] — Wykrywanie sprzętu dwuwarstwowe (inwentarz API + capability probe w podprocesie), estymacja pamięci z llama.cpp `--fit`, a prędkości z modelu dwuczłonowego pasmo + liczba kerneli.
- [[raport-05-chmura|Raport 05: chmura GPU do testów]] — NVIDIA wynajmujemy tanio (Vast od 0.08 $/h), a konsumenckich Radeonów z rootem w chmurze praktycznie nie ma, więc AMD, Intel kupujemy, Apple wynajmujemy w Scaleway.
- [[raport-06-produkt|Raport 06: produkt, UX, prawo, biznes]] — Nisza „lokalne przyspieszenie twojej karty” jest pusta, ale łatwa do skopiowania; obrona to katalog profili i bitowa identyczność, a AI Act dotyczy nas jako providera aplikacji czatu.
- [[raport-07-metody|Raport 07: nasze metody i uogólnienie]] — 70 łatek: 45 bitowo identycznych, 6 te same tokeny, 3 tylko drafty, 3 poprawki, 7 zmienia numerykę (4 przeszły KLD); proces jest powtarzalny, ~60 h zegarowych w 6.4 dnia.
- [[raport-08-platforma|Raport 08: analiza platformy 70 łatek]] — HIP na Windows działa na PAL, nie na ROCr, więc PM4 replay (0060, 0061) tam nie działa; z zysku XTX na NVIDIA pewne jest 25% (host), realnie do testu ok. +14–16%.
- [[raport-09-chmura-3060|Raport 09 (3060): Saluki i Bonsai na RTX 3060]] — RTX 3060 12 GB (sm_86, Vast, 2026-10-16), tylko Saluki 27B i Bonsai 2 27B: nasz silnik daje jednocyfrowy zysk (Saluki 22.3 → 23.4 t/s, +4.8%; Bonsai Q2_0 33.15 → 35.51, +7.1%), PQ2_0 → Q2_0 to bezstratny repack, a KLD forka vs upstream jest na poziomie szumu.
- [[raport-09-chmura-3090|Raport 09 (3090): RTX 3090 w chmurze]] — RTX 3090 (sm_86, Vast, 2026-10-16): nasz silnik daje Qwen3.8-27B 39 → 78 t/s (×2.0 vs domyślny llama.cpp i Ollama, ×1.23 vs najlepsze flagi upstream) i LFM2.5 180 → 264 t/s (×1.46); greedy md5 różni się od upstreamu przez łatki 0001/0002 i 0013.
- [[raport-09-chmura-5060ti|Raport 09 (5060 Ti): RTX 5060 Ti 16 GB w chmurze]] — RTX 5060 Ti (Blackwell sm_120, Vast, 2026-10-16): Qwen3.8-27B UD-Q3_K_XL 28 → 51.7 t/s (×1.84; ×1.38 vs flagi upstream), LFM2.5 Q4_K_M 148 → 208 t/s (×1.41); NVFP4 przyspiesza tylko prefill, a jakość dostępnych GGUF NVFP4 jest słaba.
- [[raport-10-post-training|Raport 10: trening i post-training]] — Do obietnicy produktu najlepiej pasuje trening draftera, nie modelu: fine-tune głowicy MTP Qwen3.8-27B przez self-distillation na trunku Q4, szacunek +10–17% tok/krok na czacie PL za $0–4.
- [[raport-11-mtp-pl-pilot|Raport 11: pilot douczania głowicy MTP]] — Wynik negatywny (2026-10-16, RunPod A40, $2.14): douczona głowica MTP Qwen3.8-27B na 1.7 M tokenów zmienia tok/krok o ±2% (offline +0.2% w najlepszym przebiegu); fabryczna głowica jest już blisko optimum dla tej skali danych.
- [[raport-12-bit-exact|Raport 12: bitowo identyczna spekulacja]] — Plain greedy (`c4708318`) i MTP (`6f14e814`) dają różne md5, bo ta sama pozycja liczona jest innym kernelem przy N=1 i N=2..6; tryb `LLAMA_SPEC_BITEXACT=1` na GPU wyrównał warstwy 0–6, zostało wyjście atencji `kqv_out-3`, a §13 domyka sprawę: zerowanie zamaskowanych wierszy KV daje plain == MTP i pełna walidacja przechodzi (PASS).
- [[raport-13-rocm-10-1|Raport 13: ROCm 10.1]] — ROCm 10.1 nic istotnego nie daje na gfx1100: zostajemy na 10.0, a 10.1 trzymamy obok jako tarball user-local; ważniejsze odkrycia to ATT na gfx1100 i przyczyna PMC = 0.
- [[raport-14-nemotron-3090|Raport 14: Nemotron 3.5 Bolt 74B-A9B na RTX 3090]] — Nemotron 3.5 Bolt 74B-A9B (IQ2_XXS, 22 GB) mieści się na RTX 3090 z drafterem DFlash; nasz silnik po dwóch nowych łatkach daje 87.2 → 141.1 t/s (×1.62 vs domyślny llama.cpp, ×1.07 vs najlepsze flagi upstream), ale KLD jest niezmierzone.
- [[raport-15-synteza|Raport 15: synteza fali researchu (14, 15a–15f)]] — Ranking działań po audycie głośnych twierdzeń: najpierw fabryka v1 i logowanie lookupu, potem ogon lookupu szerokości 8, PM4-PDL dla LFM i port `kvq` na CUDA.
- [[raport-15a-monokernel|Raport 15a: megakernele dla decode (vLLM MonoKernel)]] — Trwały kernel *dataflow* z prefetchem wag mógłby dać LFM2.5 na XTX +12…+28% `[SZACUNEK]`, ale trwały kernel z barierami między fazami nie pobije PM4; tańszy pierwszy krok to „PM4-PDL” (+5…+15%, bitowo) – 16a zmierzył realnie ≈ +3% (kill).
- [[raport-15b-spekulacja-frontier|Raport 15b: frontier spekulacji (lookup, szeroki blok, DFlash2, bit-exact)]] — Lookup z kontekstu i szeroki blok weryfikacji (HyperQwen) dają nam mało, bo nasza głowica MTP już kopiuje (P(MTP d1 | lookup d1) = 0.968 vs 0.765 bazowo); sens ma tylko doklejanie ogona („EXT”) na edycjach agenta.
- [[raport-15c-nowe-silniki|Raport 15c: nowe silniki konkurencji (Magnitude, tqLLM, Actual, TensorFold 1.0.12)]] — Strojenie kerneli na komputerze użytkownika przestało być unikalne (Magnitude), a „spekulacja nie zmienia odpowiedzi” robią już tqLLM, Actual i TensorFold; unikalne zostaje AMD natywnie, dowolny GGUF, przed → po wobec tuned upstream i opublikowana bramka md5/KLD.
- [[raport-15d-prefill-dlugi-kontekst|Raport 15d: prefill i długi kontekst (PFlash v2, KVFlash, cache sesji)]] — Największa bezstratna strata przy długim kontekście na NVIDIA to kernel atencji, nie prefill: port naszego `kvq` na CUDA to top pomysł; PFlash v2 to tryb stratny opt-in, KVFlash odrzucony, dyskowy cache sesji to realny bezstratny brak.
- [[raport-15e-kwantyzacja-nowa|Raport 15e: nowe formaty niskobitowe dla 27B na 12–16 GB]] — GSQ-RCO jest „SOTA” tylko w wąskiej klasie, Swift 1.5 to fine-tune z niedouczoną głowicą MTP, CSF/QAD (NVFP4) są poza naszymi kartami, a największy zysk na 12 GB to MTP na istniejących 2-bitowych plikach.
- [[raport-15f-agentowa-nauka|Raport 15f: agentowa nauka (Sakana v3, KernelGuard) a nasza fabryka]] — Z systemów automatycznej nauki warto przenieść dyscyplinę artefaktów (ewaluator poza zasięgiem agenta, ledger, reguły z fixture’ami), ale nie promocję „wynik ściśle większy” bez statystyki; propozycja fabryki v1 za ~8–9 osobodni.
- [[raport-16a-pm4-pdl|Raport 16a: PM4-PDL i prefetch wag na XTX (X1–X3 z 15a)]] — Wszystkie trzy eksperymenty z raportu 15a odpadły na lokalnym XTX ($0, gałąź `pm4-pdl` @ `3a008359b`, przełączniki domyślnie wyłączone): X1 mikrobench PDL −0.11 µs (próg 0.5), X2 górna granica +12% w LFM, ale realnie ~+3%, X3 prefetch do MALL w szumie.
- [[raport-16c-kvq-cuda|Raport 16c: kvq na CUDA (E1)]] — Agent CudaKvq przeniósł kernel `kvq` na NVIDIA Ampere+ (mma.sync m16n8k16, jedno przejście KV dla całej grupy GQA): +24.6…+36.8% tg przy 64k na 3090 i 5060 Ti, MTP@64k +27.6%, jeden graniczny FAIL KLD.
- [[raport-16d-magnitude-vs-nasz|Raport 16d: Magnitude vs nasz fork vs upstream (X1 z 15c) + KLD Nemotrona]] — Head-to-head na 3090 i 5060 Ti: przewaga naszych kerneli na NVIDIA bez draftera +30–40% i w prefillu +18–35%, a słabością są głębokie drafty – Magnitude wygrywa kopią/edycją kodu dzięki DFlash2 (7.3–7.8 tok/krok vs sufit 5 MTP n=4).
- [[raport-16e-kwanty-kld|Raport 16e: nowe kwanty 27B na 12–16 GB (E1 + E3 z 15e)]] — Agent QuantKLD zmierzył 12 ramion kwantów Qwen3.8-27B/Swift/Saluki/Bonsai (KLD do BF16 na 5 korpusach, 20 zadań, prędkość na 3060 i 5060 Ti) w dwóch rundach (2026-10-16, dokończenie po awarii omp 2026-10-18).
- [[raport-16g-lfm-moe-pasmo|Raport 16g: pasmo kerneli MoE LFM2.5 na XTX]] — Agent XtxLfmMoe rozłożył narzut matvec LFM2.5 (718 µs/token) na kernele, pokazał mikrobenchem i ATT, że gate+up ogranicza wzorzec dostępu, i zbudował bitowy kernel `GGML_HIP_MOE_GU_BLOCK` (`7c5b2a116`): LFM +0.33% (w szumie), Uncensored +1.39%, stabilniejsze tempo.
- [[raport-16h-fabryka-v1|Raport 16h: fabryka v1 zbudowana]] — Rdzeń fabryki z raportu 15f (działanie nr 1 z syntezy 15) zbudowany na CPU za $0: karta, ledger, weryfikator G0–G5, zestaw zapieczętowany, 36 reguł z fixture'ami z prawdziwych incydentów; brak walidacji na GPU.
- [[raport-16i-magnitude|Raport 16i: Magnitude – co robią dobrze i co przejąć]] — Analiza kodu Magnitude 0.2.9 (`954d677d`) i logów z 16d (tylko CPU): ich przewaga to sufit bloku DFlash2 i kontroler szerokości, nie kernele; najtańsza droga do ich wyniku to ogon z lookupu do 8 wierszy przy MTP4 (projekcja XTX code-edit ×1.4).
- [[raport-16j-magnitude-vulkan-xtx|Raport 16j: Magnitude przez Vulkan na 7900 XTX (E-X5)]] — Agent MagnitudeVulkanXtx uruchomił Magnitude na naszej XTX przez Vulkan i zmierzył go tym samym harnessem co 16d: na AMD Magnitude jest konkurentem w łatwości instalacji (jedna binarka, bez ROCm), nie w wydajności (×1.42–×2.24 dla nas).
- [[runda-6-raporty|Runda 6: raporty GDN, MMQ i narzędzi]] — Trzy raporty rundy 6 (2026-10-15), wszystkie bez GPU: szybki kernel GDN bitowy z konstrukcji, epilog MMQ w VOPD oraz narzędzia LOO / kanarki KLD / Kernel Tuner.
- [[star-elastic-2605-07182|Star Elastic (arXiv 2605.07182)]] — Praca NVIDIA o zagnieżdżonych podmodelach Nemotron Nano v3 (30B → 23B/12B z jednego post-trainingu) i osobnym podmodelu dla fazy myślenia; nie dotyczy kerneli, dla nas niska istotność.
<!-- AUTO:END -->
