---
typ: meta
tags: [meta]
aktualizacja: 2026-10-16
zrodlo: wiki
status: aktualne
---
# Dziennik wiki

**Chronologiczny zapis zmian w wiki (tylko dopisywanie); każdy wpis zaczyna się od `## [data] rodzaj | opis`.**

Ostatnie wpisy: `grep "^## \[" wiki/log.md | tail -5`.

## [2026-10-16] ingest | Zasiew wiki
Szkielet 16 kategorii, `tools/wiki.py` (lint/index/search), 140 notatek z `qwen-opt/NOTES.md`, `STATUS-NEXT.md`, `qwen-opt/research/**`, `qwen-opt/tools/**`, `product/**`, `reports/`, `hardware/`, `~/qwen-opt/cloud/**`, `~/wt/rebase070/REBASE.md`. Wypełnione: metody, kernele, latki, rocm, nvidia, karty, modele, eksperymenty, chmura; częściowo narzedzia, decyzje, lekcje. Puste huby: repo, research, produkt, ludzie-firmy (do uzupełnienia). Lint: 0 błędów.

## [2026-10-16] ingest | Dokończenie wiki (jeden agent)
Nowe notatki: repo/ (30 repo z przeglądu, Strata, TensorFold, ik_llama.cpp, laya-mlx, fork PrismML, speculators/SpecForge, nasze gałęzie i worktree), research/ (raporty 01–08, 10, 12, 13, przegląd 30 repo, runda 6; raportów 09 i 11 nie ma), produkt/ (sekcje PLAN.md + aplikacja „w budowie”), ludzie-firmy/ (23 firmy i projekty), narzedzia/ (+13), lekcje/ (+20: tryby awarii z raportu 07 i lekcje z 2026-10-16), decyzje/ (+9). Naprawione sieroty. Audyt liczb: [[AUDYT]] (1 liczba poprawiona, 23 `zrodlo` uzupełnione). Odświeżony „stan na dziś” w [[index]].

## [2026-10-16] ingest | Prototyp aplikacji (app/REPORT.md)
Przepisana [[aplikacja-w-budowie]] (status aktualne, commit `9f96ff4`); nowe: [[app-system-projektowy]], [[app-landing]], [[app-onboarding-prototyp]], [[app-skrypty-skanu]], [[app-prototyp-desktop]], [[otwarte-decyzje-produktu]]. Audyt: +66 liczb, 0 błędnych.

## [2026-10-16] ingest | Wyniki finalne: chmura NVIDIA, pilot MTP, bit-exact
Nowe: [[raport-09-chmura-3090]], [[raport-09-chmura-5060ti]], [[raport-09-chmura-3060]], [[raport-11-mtp-pl-pilot]], [[2026-10-16-mtp-pl-pilot]], lekcje [[lekcja-fit-mtp-16gb]], [[lekcja-limit-cpu-kontenera]], [[lekcja-md5-wzgledem-upstreamu]], [[lekcja-mtp-glowica-optimum]], [[lekcja-nadpisanie-dzialajacego-skryptu]]. Przepisane z `do-sprawdzenia` na finalne: [[nvidia-wyniki-2026-10-16]], karty 3090/5060 Ti/3060, [[2026-10-16-kampania-nvidia]], [[saluki]], [[bonsai]]; uzupełnione m.in. [[nvfp4]], [[lfm2-5-24b-a2b]], [[glowica-mtp]], [[mmvq-n1-wiersze]], [[fuzje-lfm-moe]], [[latki-na-nvidia]], [[raport-12-bit-exact]], [[lekcja-bit-exact-attention]]. Wydatki końcowe w [[2026-10-16-budzety-chmury]]. „Stan na dziś”: nic nie działa. Audyt: +998 liczb, 0 błędnych.

## [2026-10-16] ingest | Raporty 14 i 15a–15f
Nowe: [[raport-14-nemotron-3090]], [[raport-15a-monokernel]], [[raport-15b-spekulacja-frontier]], [[raport-15c-nowe-silniki]], [[raport-15d-prefill-dlugi-kontekst]], [[raport-15e-kwantyzacja-nowa]], [[raport-15f-agentowa-nauka]] oraz notatki repo/modeli/lekcji/metod z ich sekcji „Do bazy wiedzy” (m.in. [[magnitude]], [[tqllm]], [[swift-1-5]], [[fabryka-v1]], [[zestaw-odlozony]]). Zaktualizowane m.in. [[nvidia-wyniki-2026-10-16]], [[fattn-kvq]], [[tensorfold]], [[ik-llama-cpp]], [[werdykt]], [[otwarte-decyzje-produktu]]. Audyt: 676 liczb, 0 błędnych.

## [2026-10-16] ingest | Raport 12 §13 (walidacja bit-exact) i 16c (kvq na CUDA)
Zaktualizowane: [[2026-10-16-bit-exact]] (run 4: PASS, prędkość na flagach produkcyjnych, regresja nowego drzewa ~5–6%), [[raport-12-bit-exact]], [[fattn-kvq]], [[fa-kv-kwantyzowane-cuda]], [[raport-15d-prefill-dlugi-kontekst]] (korekta MTP@64k), [[harness-chmurowy]]. Nowe: [[2026-10-16-kvq-cuda]], [[raport-16c-kvq-cuda]], [[2026-10-16-kvq-cuda-zostaje]], [[lekcja-kld-szum-kolejnosci]], [[lekcja-vast-authorized-keys]], [[lekcja-pkill-wlasna-powloka]].

## [2026-10-16] ingest | Raport 16h (fabryka v1 zbudowana)
Nowe: [[fabryka-cli]], [[2026-10-16-backtest-regul-fabryki]], [[raport-16h-fabryka-v1]]. Zaktualizowane: [[fabryka-v1]] (status aktualne), [[zestaw-odlozony]], [[pomiar-abba]], [[lekcja-label-to-nie-binarka]], [[lekcja-pdl-sm120]], [[seria-amd-opt]]. `log.md` zwolniony z limitu słów (dziennik), zmiana w `tools/wiki.py` i [[KONWENCJE]].

## [2026-10-16] ingest | Raporty 16d i 16i (Magnitude) + decyzja „badamy Magnitude”
Nowe: [[2026-10-16-magnitude-vs-fork]] (z danymi 9B na 5060 Ti), [[2026-10-16-magnitude-rozklad-wygranej]], [[raport-16d-magnitude-vs-nasz]], [[raport-16i-magnitude]], [[firma-magnitude]], [[kontroler-szerokosci-draftu]], [[sprzezone-probkowanie-draftu]], [[lekcja-sufit-bloku]], [[lekcja-drafter-gleboki-vs-mtp]], [[2026-10-16-badamy-magnitude]]. Zaktualizowane: [[magnitude]] (status aktualne), [[drafter-dflash]], [[mmvq-multikolumnowe]], [[produkt-ryzyka]], [[lekcja-limit-cpu-kontenera]], [[lekcja-pkill-wlasna-powloka]], [[zgodnosc-bitowa-md5]], [[2026-10-16-nemotron-3090]] (KLD PASS).

## [2026-10-16] update | Regresja nowego drzewa bit-exact naprawiona
[[2026-10-16-bit-exact]] i [[raport-12-bit-exact]]: przyczyna `ce2105d32` (14 spilli VGPR), poprawka `02813c1c5`, tg128 43.15/43.16 = prod. Nowa lekcja [[lekcja-vgpr-limit-hak-spill]].

## [2026-10-16] update | Raport 12 §13 końcowy (`365af3e5e`) + lekcja o awarii omp
[[2026-10-16-bit-exact]] (run 4 końcowy: domyślnie = produkcja; bitexact MTP 0% krótki / −9% ~27k, plain −2.8%, pp5@32k −11%), [[raport-12-bit-exact]], [[batch-invariant]], [[lekcja-bit-exact-attention]] (lista źródeł rozbieżności), [[otwarte-decyzje-produktu]] (opt-in „identyczne odpowiedzi” czeka na użytkownika). Nowa: [[lekcja-uslugi-poza-omp]].

## [2026-10-18] ingest | Raport 16e (kwanty 27B, KLD) + incydent danych + Salad
Nowe: [[2026-10-18-e1-kwanty-27b-kld]], [[raport-16e-kwanty-kld]], [[kld-po-polsku]], lekcje [[lekcja-unikalny-katalog-wynikow]], [[lekcja-build-przed-wynajmem]], [[lekcja-bootstrap-numpy]], [[lekcja-zabicie-skryptu-nie-serwera]], [[lekcja-limit-mocy-hosta]]. Zaktualizowane: [[swift-1-5]], [[rtx-3060]], [[rtx-5060-ti]], [[kwanty-gguf]], [[saluki]], [[bonsai]], [[raport-15e-kwantyzacja-nowa]], [[runpod]], [[raport-09-chmura-3060]] (dane nadpisane), [[lekcja-limit-cpu-kontenera]], [[lekcja-pkill-wlasna-powloka]], [[otwarte-decyzje-produktu]] (16 GB A3, 12 GB IQ3_XXS-mtp – rekomendacje, bez decyzji), [[salad]], [[firma-salad]], [[radeony-do-wynajecia]] (AMD w Salad niedostępne, brak XTX do wynajęcia).

## [2026-10-18] ingest | 16c §9, 16j, landing r6–r8, wentylator XTX i restart
16c §9: wyjątek kvq n=1 D256 q4_0 (`678473a27`) w [[fattn-kvq]], [[2026-10-16-kvq-cuda]], [[2026-10-16-kvq-cuda-zostaje]], [[bramka-kld-kanarki]], [[lekcja-kld-szum-kolejnosci]], [[raport-16c-kvq-cuda]]. 16j: nowe [[2026-10-18-magnitude-vulkan-xtx]], [[raport-16j-magnitude-vulkan-xtx]], [[lekcja-koszt-szerokosci-backendu]]; zaktualizowane [[magnitude]], [[firma-magnitude]], [[produkt-ryzyka]], [[raport-16i-magnitude]], [[2026-10-16-badamy-magnitude]]. Landing: [[lekcja-hydration-blok-w-p]], [[landing-qa]], [[app-landing]]. Ops: [[rx-7900-xtx]] (overdrive, krzywa wentylatora, Vulkan bez sudo), [[lekcja-wentylator-rdna3]], [[lekcja-tmp-po-restarcie]] (`/tmp/bx*` utracone, oznaczone w `zrodlo` notatek bit-exact).

## [2026-10-18] update | Źródło bit-exact: raport 12 §13 kanoniczny
`/tmp/bx*` zniknęły przy restarcie ~18:53 UTC (przed archiwum); poprawione [[lekcja-tmp-po-restarcie]], `zrodlo` notatek bit-exact, [[AUDYT]].

## [2026-10-18] ingest | Raport 16g (pasmo MoE LFM)
Nowe: [[2026-10-18-lfm-moe-pasmo]], [[2026-10-18-lfm-moe-negatywne]], [[mmvq-moe-gate-up-blok]], [[att-gfx1100]], [[lekcja-sufit-wzorca]], [[lekcja-limit-mocy-285w]], [[raport-16g-lfm-moe-pasmo]]. Zaktualizowane: [[lfm2-5-24b-a2b]], [[lfm2-5-uncensored]], [[seria-amd-opt]] (kandydat 0071), [[otwarte-decyzje-produktu]] (scalenie 0071 – decyzja użytkownika), [[amdgpu-moc-i-termika]].

## [2026-10-18] ingest | Landing rundy 9–12
[[app-landing]] (rundy 9–12, źródło bit-exact = raport 12 §13 run 4, juror r9–r12, kontrole r12); nowe lekcje [[lekcja-juror-llm-plateau]], [[lekcja-timeline-scen-3s]].

## [2026-10-18] ingest | Raport 16a (PM4-PDL, prefetch MALL)
Nowe: [[2026-10-18-pm4-pdl-x1]], [[2026-10-18-pm4-ub-lfm]], [[lekcja-handoff-rdna3]], [[lekcja-prefetch-mall-xtx]], [[raport-16a-pm4-pdl]]. Zaktualizowane: [[raport-15a-monokernel]] (korekta S1: +9…+15% → realnie ≈ +3%), [[pm4-replay]], [[wyniki-negatywne]].

## [2026-10-18] ingest | Raport 16f (szybkie zyski XTX) + wentylator za obciążeniem + Chrome
Nowe: [[2026-10-18-lfm-ubatch-2048]], [[lfm-czulosc-na-podzial-batcha]], [[2026-10-18-cache-promptu-agenta]], [[2026-10-18-hak-mtp-i-checkpointy]], [[cache-sesji-na-dysku]], [[raport-16f-xtx-szybkie]], lekcje [[lekcja-5-seedow]], [[lekcja-nie-odtwarzac-lockow]], [[lekcja-chrome-zostawiony]]. Zaktualizowane: [[latki-spekulacji]], [[wylaczniki-env]], [[2026-10-12-cache-promptu-i-a7]], [[raport-15d-prefill-dlugi-kontekst]], [[lekcja-unikalny-katalog-wynikow]], [[otwarte-decyzje-produktu]] (flagi `run-llm.sh` – decyzja użytkownika), [[rx-7900-xtx]] i [[lekcja-wentylator-rdna3]] (timer, reset GPU, tryb akustyczny).

## [2026-10-19] update | Wentylator XTX 100% przy pracy (decyzja użytkownika)
Nowa [[2026-10-19-wentylator-100-przy-pracy]]; zaktualizowane [[rx-7900-xtx]], [[lekcja-wentylator-rdna3]].

## [2026-10-19] ingest | 16k sprzężone próbkowanie + zasada bezpieczeństwa sprzętu
Nowe: [[2026-10-18-sprzezone-probkowanie-mtp]] (nierozstrzygnięte, nie domyślnie), [[gumbel-max]], [[lekcja-ustalony-seed-to-nie-powtorzenie]], [[raport-16k-sprzezone-probkowanie]], [[2026-10-19-bezpieczenstwo-sprzetu]], [[gpu-guard]], [[lekcja-agent-nie-patrzyl-na-temperatury]]. Zaktualizowane: [[sprzezone-probkowanie-draftu]], [[pm4-replay]] (page faulty SQC @0, raport 17 w toku), [[2026-10-16-badamy-magnitude]], [[raport-16i-magnitude]], [[rx-7900-xtx]].

## [2026-10-19] ingest | Raport 16b (ogon lookupu za MTP)
Nowe: [[2026-10-18-lookup-ogon]], [[2026-10-18-kontroler-szerokosci-zerowy]], [[koszt-szerokosci-weryfikacji]], [[zestaw-copy-mvs]], [[lekcja-ogon-zmienia-tekst-t1]], [[raport-16b-lookup-tail]]. Zaktualizowane: [[lekcja-mtp-juz-kopiuje]], [[2026-10-16-lookup-kopiowalnosc]], [[kontroler-szerokosci-draftu]], [[raport-15b-spekulacja-frontier]], [[2026-10-16-badamy-magnitude]], [[raport-16i-magnitude]], [[otwarte-decyzje-produktu]] (włączenie w produkcji – decyzja użytkownika).

## [2026-10-19] ingest | Raport 17 (page faulty GPU, resety)
Nowe: [[2026-10-19-page-faulty-gpu-analiza]], [[raport-17-gpu-page-fault]], [[dekodowanie-page-fault-amdgpu]], [[kfd-smi-eventy]], lekcje [[lekcja-pm4-zamienia-fault-w-reset]], [[lekcja-timeout-tasmy-to-skutek]], [[lekcja-pgrep-f-lapie-powloki]]. Zaktualizowane: [[pm4-replay]], [[2026-10-18-sprzezone-probkowanie-mtp]], [[2026-10-19-bezpieczenstwo-sprzetu]]; korekty [[lekcja-nie-odtwarzac-lockow]] i [[lekcja-wentylator-rdna3]] (reset 23:25 nie z kolizji blokad); [[otwarte-decyzje-produktu]] (`GGML_HIP_PM4=0` – decyzja użytkownika).

## [2026-10-19] ingest | Strona rekordów + benchmarki przed → po
Nowe: [[REKORDY]] (najlepsze wyniki per karta/model/obciążenie/metryka z datą, warunkami, źródłem i statusem produkcji; zwolniona z limitu słów), [[benchmarki-przed-po-2026-10-19]]. Zasada „nowy rekord od razu na stronę rekordów” w [[KONWENCJE]] i `AGENTS.md`; link z [[index]].

## [2026-10-19] ingest | Raport 20 (build topka) + zero-RPM
Nowa [[2026-10-19-build-topka]]; [[REKORDY]]: Uncensored code-edit 414.8 t/s (nowa para), Qwen topka 396.9 t/s obok rekordu 400.9; [[galezie-rund]], [[lekcja-wentylator-rdna3]] i [[gpu-guard]] (fałszywy alarm zero-RPM, próg 80/82 °C).

## [2026-10-19] ingest | Raport 17 §9 (przyczyna PM4: PRIV=1 na GFX11 + ewikcje SVM)
Nowe: [[2026-10-19-pm4-priv-analiza]], [[gfx11-pm4-dispatch-priv]], [[hip-kopie-stronicowane-zostawiaja-svm]], [[kfd-ewikcja-kolejek-gfx11]], [[lekcja-wlasny-pm4-musi-robic-to-co-firmware]], [[lekcja-test-wywlaszczenia]]. Zaktualizowane: [[kfd-smi-eventy]], [[pm4-replay]], [[raport-17-gpu-page-fault]], [[2026-10-19-page-faulty-gpu-analiza]], [[otwarte-decyzje-produktu]] (testy S1–S6 – decyzja użytkownika).

## [2026-10-19] ingest | Raport 21c (Copy-Paste LM)
Nowe: [[raport-21c-cplm]], [[lekcja-lm-head-bottleneck]], [[2026-10-19-sufit-pointera-lookup]], [[2026-10-19-tokeny-spoza-slownika-draftu]], [[agr-lookup-zgodny-z-mtp]]; zaktualizowany [[raport-16b-lookup-tail]].

## [2026-10-19] ingest | Raport 21h (Terminal-RSI) + podział otwartych decyzji
Nowe: [[raport-21h-rsi]], [[rsr-27b]], [[tencent-terminal-rsi]], [[lekcja-verified-to-nie-poprawny]], [[petla-rsi-f]], [[2026-10-19-plan-retro-rsr-0070]], [[2026-10-19-plan-e1-rsr27b]], [[otwarte-decyzje-techniczne]] (wydzielone z [[otwarte-decyzje-produktu]]: flagi, łatki, testy GPU, wydatki; nowe wiersze P0/P1 i E1). Zaktualizowany [[zestaw-odlozony]].

## [2026-10-19] ingest | Raport 18 (następna fala)
Nowe: [[raport-18-nastepna-fala]], [[2026-10-19-workload-omp]], [[model-kosztu-weryfikacji-moe]], [[2026-10-19-certyfikowana-glowica-pilot]], [[lekcja-rzadkosc-vs-weryfikacja]], [[knlp-lm-head]], [[mtplx]], [[suffixdecoding]]. Zaktualizowane: [[qwen3-8-27b]], [[lfm2-5-24b-a2b]], [[lekcja-prefetch-mall-xtx]].

## [2026-10-19] ingest | Raport 21a (DSpine)
Nowe: [[drafter-dspine]], [[raport-21a-dspine]], [[lekcja-akceptacja-h100-nie-przenosi-sie]], [[lekcja-naglowki-drafterow]]; zaktualizowany [[drafter-dflash]].

## [2026-10-19] ingest | Raport 21b (zasoby GPU perf, Blackwell TG)
Nowe: [[raport-21b-gpu-perf-zasoby]], [[wafer-gpu-perf-lista]], [[projekcja-rtx-5090]], [[karty-nvidia-parametry]], [[pdl-mmvq-trigger]], [[mmvq-prefetch-l2]], [[l2-persist]], [[trwala-siatka-bez-pm4]], [[lekcja-littles-law-gemv]], [[physics-floor-check]]; zaktualizowany [[sm-86-89-120]].

## [2026-10-19] ingest | Raport 21f (InferenceX / AgentX, Kimi K3)
Nowe: [[raport-21f-inferencex]], [[ksztalt-ruchu-agentowego]], [[lekcja-agent-prefill-nie-decode]], [[agentx-harness]], [[qwen38-27b-inferencex]], [[vllm-kimi-k3-specialized-decode]], [[single-neuron-safety-2605-08513]] (link użytkownika dotyczy innej pracy).

## [2026-10-19] ingest | Raport 21d (KV na dysku)
Nowe: [[raport-21d-kv-na-dysku]], [[kv-na-dysku-polityka]], [[dysk-serwera-pm9b1]], [[lekcja-restore-stanu-exactness]]; zaktualizowane [[cache-sesji-na-dysku]], [[strata]].

## [2026-10-19] ingest | Raport 21e (KV między modelami, Uncensored = ablacja)
Nowe: [[raport-21e-kv-miedzy-modelami]], [[uncensored-ablacja-kierunku]], [[przelaczanie-main-uncensored]], [[pamiec-stanu-gdn]]; zaktualizowane [[qwen3-8-27b-uncensored]], [[lfm2-5-uncensored]], [[otwarte-decyzje-techniczne]] (źródło wektorów – decyzja użytkownika).

## [2026-10-19] update | Decyzja: KV tylko w RAM
Nowa [[2026-10-19-kv-tylko-w-ram]]; [[kv-na-dysku-polityka]] → nieaktualne (analiza bez wdrożenia); linki w [[raport-21d-kv-na-dysku]], [[cache-sesji-na-dysku]], [[dysk-serwera-pm9b1]], [[otwarte-decyzje-techniczne]].

## [2026-10-19] ingest | Raport 21k (smokinggun)
Nowa [[smokinggun]]: skaner CPU + porównanie benchmarków, nie stosuje się; fabryka v1 robi gate lepiej.

## [2026-10-19] ingest | Narzędzie kb (raport 19)
Nowa [[kb]]: `kb search` / `kb facts` (BM25F + e5-small + indeks faktów, cały `~/KERNEL`, `plik:linia`), recall@5 0.963 na 80 pytaniach (`wiki.py` 0.750); [[wiki-py]] `search` deleguje do `kb`; `AGENTS.md`: najpierw `kb`. Raport `product/research/19-kb-wyszukiwanie.md`.

## [2026-10-19] ingest | Raport 21g (nowe silniki)
Nowe: [[raport-21g-nowe-silniki]], [[inferrous]], [[project-maya]], [[bariera-lds-rdna3]], [[lekcja-bit-exact-wobec-siebie]], [[llama-moe-cache-mib]]; zaktualizowane [[tensorfold]] (1.1.0, Beta 7/8), [[strata]] (v0.1.44.1–v0.1.45), [[produkt-ryzyka]].

## [2026-10-19] ingest | Raport 23a (rea) + uzupełnienie raportu 19 (kb)
Nowe: [[raport-23a-rea]], [[hip-fatbin-extract]], [[raport-19-kb-wyszukiwanie]], [[najpierw-baza-kb]], [[lekcja-markdown-puste-linie]]; zaktualizowane [[kb]].

## [2026-10-19] ingest | Raport 21i (RSI-Inference Bench)
Nowe: [[raport-21i-rsi-inference-bench]], [[zmiany-fabryki-z-21i]], [[aob-v1]], [[lekcja-regula-tylko-w-prompcie]]; zaktualizowana [[petla-rsi-f]].

## [2026-10-19] ingest | Raport 21j (flameox)
Nowe: [[raport-21j-flameox]], [[flameox]], [[lekcja-bootstrap-male-n]], [[dowod-z-profilu]]; zaktualizowane [[fabryka-cli]], [[rocprof]], [[petla-rsi-f]], [[produkt-architektura]].

## [2026-10-19] update | Decyzja: najlepiej, bez pytania
Nowe [[2026-10-19-najlepiej-bez-pytania]] (linia w `AGENTS.md`) i [[2026-10-19-szanujemy-sprzet-serwera]] (zasada z `AGENTS.md:7` bez notatki w decyzjach); [[otwarte-decyzje-techniczne]] zaktualizowane.

## [2026-10-19] update | Zasada `cpuheavy.lock`
[[2026-10-19-szanujemy-sprzet-serwera]]: ciężkie komendy CPU tylko pod `flock /tmp/cpuheavy.lock nice -n 19 taskset -c 0-3`, buildy `-j4`.

## [2026-10-19] ingest | Raport 21l (RE dla GPU)
Nowe: [[raport-21l-re-gpu]], [[co-stats]], [[umr-offline-pm4]], [[lekcja-radare2-sass]], [[re-vendorow-zasady]]; [[mmvq-multikolumnowe]] (klif VGPR ncols 4 → 5).

## [2026-10-19] update | `cpuheavy.lock` na rdzeniach 0–1
[[2026-10-19-szanujemy-sprzet-serwera]]: `taskset -c 0-1`, buildy `-j2`, CUDA jedna architektura na build.

## [2026-10-19] ingest | Raport 23b (RE kerneli AMD)
Nowa [[raport-23b-re-kernele-amd]]; zaktualizowana [[mmvq-n1-wiersze]].

## [2026-10-19] ingest | Raport 23d (RE runtime AMD, firmware MEC)
Nowe: [[mec-fw-dispatch-aql-gfx11]], [[rs64-firmware-re]]; zaktualizowane [[gfx11-pm4-dispatch-priv]], [[hip-graph-narzut]]. Zrzuty firmware tylko lokalnie, w wiki same numery linii.

## [2026-10-19] ingest | Raporty 23b2 (bariery) i 23e (RE silników)
Nowa [[raport-23e-re-silniki]] (hipfire 54.3 vs 43.2 t/s – bajty, nie ISA; pomysł nr 1 już w forku); zaktualizowane [[raport-23b-re-kernele-amd]], [[bariera-lds-rdna3]], [[hipfire]], [[gdn-replay]].

## [2026-10-19] ingest | Raport 23c (RE kerneli NVIDIA)
Nowa [[raport-23c-re-kernele-nvidia]]; zaktualizowana [[pdl-mmvq-trigger]].

## [2026-10-19] ingest | Raport 23f (podręcznik optymalizacji GPU)
Nowe: [[podrecznik-gpu]] (hub, link z [[index]]), [[isa-kstat]]; poprawka reguły occupancy w [[rdna3-gfx1100]] (granulat 24 VGPR, 255 VGPR = 5 fal, nie 6).

## [2026-10-19] ingest | Raport 21m (Declarative Attention)
Nowe: [[raport-21m-declarative-attention]] (nie dla nas), [[lekcja-odczyty-kv-batch1]].

## [2026-10-19] update | Rejestr źródeł ZRODLA
Nowe: [[ZRODLA]] (przebadane źródła z raportów 01–24b, 21n, `qwen-opt/research/`, repo/ i ludzie-firmy/; tabela dublowania). Zasada „nie badamy drugi raz tego samego” w [[KONWENCJE]]; link w [[index]]; `kb` daje ZRODLA mnożnik 1.25 jak REKORDY.

## [2026-10-20] ingest | Raporty 20–30 i WYNIKI-XTX (wszystkie bez notatki)
Nowe `raport-*` (36): 20, 21k, 21n, 21o, 22, 23b2, 23d, 23f, 24a–24v, 25, 26, 27, 28, 30, WYNIKI-XTX; przegląd [[raporty-2026-10-19-20]]. Lekcje: [[lekcja-pm4-zawsze-jawnie]], [[lekcja-wyrazna-wygrana-albo-nic]], [[lekcja-glebokosc-zmienia-tekst]], [[lekcja-landing-jeden-uklad]], [[lekcja-dostep-intel-apple]]; zaktualizowana [[lekcja-obciazenie-cpu]] (benchmark nigdy razem z buildem, 24o). Decyzje: [[2026-10-20-karta-fabrycznie]], [[2026-10-20-szybkie-iteracje]], [[2026-10-19-buildy-przez-rbuild]], [[2026-10-19-chmura-bez-destroy-all]], [[2026-10-19-topka-tylko-keeper]], [[2026-10-20-auth-bez-backendu]], [[2026-10-20-uncensored-poza-strona]]. Aktualizacje: [[sprzezone-probkowanie-draftu]], [[kontroler-szerokosci-draftu]], [[koszt-szerokosci-weryfikacji]], [[wyniki-negatywne]], [[bariera-lds-rdna3]] (odrzucona), [[strata]], [[rtx-3090]]. [[REKORDY]]: XTX czat 114.8, host-gap 117.9 (gałąź), sprzężone 111.4, mvs 419.9 / 430.8, long_ctx 1.7k 136.5 (MTP-only), Uncensored mvs 434.9, 3090 93.3, 3060 38.2. [[ZRODLA]]: gemma.ai, Gyro/agentionai, DFloat11/ZipNN, TensorFold 1.1.0 na 3090, hipfire R24g, Apple SLA/Metal. [[AUDYT]]: sekcja ingestu 2026-10-20.

## [2026-10-20] ingest | Raporty 29, 24w, podsumowanie nocy
Nowe: [[rtx-4060-ti]], [[raport-29-4060ti]], [[raport-24w-pair2]], [[2026-10-20-podsumowanie-nocy]]; [[raport-24q-adaptacyjna-spekulacja]] – werdykt końcowy (odrzucone). [[REKORDY]]: 4060 Ti (Qwen 35.4 / mvs 170.9, LFM 149.4 t/s, nie w produkcji), topka-next 114.6 t/s (+1.4%, niezainstalowana). [[AUDYT]] uzupełniony.

## [2026-10-20] update | Wyniki rano: topka-next zainstalowana, PAIR2 odrzucone
[[2026-10-20-podsumowanie-nocy]]: topka-next jako `~/llama-topka` (host-gap dla Qwen), `mvs` 420.2 → 433.0 t/s (+3.0%), md5 OK. [[raport-24w-pair2]]: +0.4% → odrzucone; [[wyniki-negatywne]], [[lekcja-wyrazna-wygrana-albo-nic]]. [[REKORDY]]: XTX `mvs` 433.0 i czat 114.6 (`hg_ab.sh`), oba w produkcji. [[AUDYT]] uzupełniony.

## [2026-10-20] narzędzia | Aplikacja WWW bazy zamiast graph.py
`tools/site/build.py` (dashboard, kategorie, notatki z backlinkami i lokalnym grafem, wyszukiwarka, oś czasu, graf skupisk, tabele REKORDY/ZRODLA, jasny/ciemny, telefon) → `~/.cache/wiki-graph`; `tools/graph.py` usunięty, cron codziennie 6:40. Zrzuty: `app/screens/kb/`. [[KONWENCJE]] → Utrzymanie.

## [2026-10-21] ingest | Raporty 31–54, watch, PLAN-NV-V2 (wszystkie bez notatki)
Nowe `raport-*` (43): 31 (3060/3080, 3090, 4060 Ti, 4070 Ti, 5060 Ti), 32a–32f, 33–38, 39a–39f, 40–48, 49, 50a–50d, 51–54, compwatch, PLAN-NV-V2; przegląd [[raporty-2026-10-20-21]]. Nowe notatki tematyczne: [[opoznienia-ttft]], [[bezpieczenstwo-tokenow-specjalnych]], [[qwen3-6-35b-a3b]], [[gemma-4]], [[ninfer]], [[eagle-4]], [[nvidia-flare]], [[deepinfer]], [[metryka-prozy-e0]]. Lekcje: [[lekcja-kolejka-fifo-bilety]], [[lekcja-higiena-pomiaru]], [[lekcja-qa-clip-blokuje-gpu]], [[lekcja-rbuild-pod-flock]], [[lekcja-proza-e0-vs-myslenie]], [[lekcja-zmiana-draftu-zmienia-md5]]; podlinkowana [[lekcja-nie-zabijaj-pm4-w-trakcie]]. Decyzja: [[2026-10-21-enigma-labz]]. Aktualizacje: [[mmvq-multikolumnowe]], [[pamiec-stanu-gdn]], [[rmsnorm-dpp]], [[fattn-kvq]], [[pm4-replay]], [[glowica-mtp]], [[app-landing]], [[vast-ai]], [[tqllm]], [[project-maya]], [[qwen3-8-27b]]. [[REKORDY]]: E0 78.93 t/s (definicja metryki), topka f9b84bcfa (mvs 433.8, start 38.5 → 6.55 s, tura agenta 687/579 → 197 ms, 2k TTFT −22%), NVIDIA 31-*. [[ZRODLA]] i [[AUDYT]] uzupełnione.

## [2026-10-24] ingest | Raport 60c: Gyro-Coder, tqLLM 1.2, DCQ, @superalesha, Bolt-E4B
Nowe: [[raport-60c-quant-3090]], [[gyro-coder]], [[dcq-kotwica-stanu-gdn]], [[nemotron-3-5-bolt-e4b]]. Aktualizacje: [[tqllm]] (1.2.x), [[hyperqwen]] („4.6×”). Testy dopisane do `product/DO-PRZETESTOWANIA.md`; CompWatch: `syv-ai/HyperQwen`, `fraserprice/dspark-vllm`, autorzy HF `agentionai`, `YTan2000`.

## [2026-10-24] ingest | Raport 60d: Humming, SGLang HiCache, AKV, sonar #1788, Maya v1.1.21–1.1.26
Nowe: [[raport-60d-serving-kernels-cache]], [[humming]], [[sglang-hicache]], [[akv-cache-agentow]]. Aktualizacja: [[project-maya]] (v1.1.21–1.1.26). Rejestr [[ZRODLA]] (5 wierszy). Testy T1–T7 dopisane do `product/DO-PRZETESTOWANIA.md`; CompWatch: `vllm-project/humming`, `thu-nics/AKV`, `dphnAI/sonar`.

## Powiązane
- [[index|Strona główna]]
- [[KONWENCJE]]

## [2026-10-24] ingest | Raport 60b: oMLX 0.7.2, Locals, konkurs Bonsai 2 9B, Flapping Airplanes
Nowe notatki [[omlx]], [[locals]], [[bonsai-fast-contest]], [[flapping-airplanes]], [[raport-60b-apple-bonsai]]; uzupełnione [[gdn-replay]], [[bonsai]], [[ZRODLA]]; 6 pomysłów w `product/DO-PRZETESTOWANIA.md`; 4 repo w compwatch.

## [2026-11-05] ingest | Raport 63: synteza 44 wątków, reguła „tylko bezstratne”, test termiczny eco
Nowe: [[raport-63-synteza]], [[qwen-qsa-llama-cpp]], [[latent-sparse-attention]], [[rdna-fast]], [[yasakani]], [[qwen-warp]], [[colibri]], [[vllm-rocm-octave]], [[strata-kva]], [[fly-stratna-weryfikacja]], [[wspolny-poczatek-promptu]], [[reward-hacking-inferencji]], [[lekcja-rocm10-lds-128kb]], [[lekcja-gorzka-lekcja-tkcc]], [[lekcja-cache-ram-za-maly]]. Decyzje: [[2026-11-05-tylko-bezstratne]], [[2026-11-05-termika-eco-test]] (zmienia [[2026-10-20-karta-fabrycznie]]). Aktualizacje: [[strata]], [[project-maya]], [[hyperqwen]], [[tensorfold]], [[ninfer]], [[lekcja-higiena-pomiaru]], [[rocm-10-1]]. [[ZRODLA]]: sekcja „Raport 63” (51 wierszy). [[AUDYT]] uzupełniony. [[REKORDY]] bez zmian (brak nowych pomiarów). Synteza i plan: `product/research/63-SYNTEZA.md`, rejestr `63-WATKI.md`.

## [2026-11-05] update | Wdrożenie topka-q63 + cache-ram 40 GB
Produkcja `~/llama-topka` = topka-q63 c0576e3e8 (ABBA vs f9b84bcfa: t/s 0%, md5 identyczny, −1.0 GiB VRAM, akceptacja po odtworzeniu slotu 0.41 → 0.60); `run-llm.sh` `--cache-ram 16384 → 40960` (raport 63b). Uzupełnione [[qwen3-8-27b]]. Do zbadania: `amdgpu: init_user_pages: Failed to get user pages: -1` (~16k wierszy w logu jądra przy każdym starcie serwera, od co najmniej 2026-10-25; bez faultów i resetów).

## [2026-11-06] ingest | q63, Enigma uczciwy benchmark, raport 64, xtx-eco, Vast
Nowe: [[2026-11-05-q63-topka]], [[lekcja-rezerwa-mtp-kopia-f16]], [[enigma-uczciwy-benchmark]], [[lekcja-benchmark-te-same-tokeny]], [[raport-64-termika]], [[lekcja-od-commit-gubi-krzywa]], [[2026-11-06-xtx-eco-instalacja]] (fabryczny OD_SCLK 2885 → 2935 MHz między bootami), [[init-user-pages-failed]], [[lekcja-buildfarm-down-z-cloud]]. Aktualizacje: [[rx-7900-xtx]], [[amdgpu-moc-i-termika]], [[vast-ai]], [[reward-hacking-inferencji]], [[lekcja-enigma-apu-jako-karta]], [[lekcja-cache-ram-za-maly]] (wdrożone, efekt niezmierzony). [[REKORDY]]: spec_sweep 120.58 t/s; VRAM bez kategorii. [[ZRODLA]]: sekcja „Raport 64”. [[AUDYT]] uzupełniony.

## [2026-11-06] meta | Wymuszenie zapisu wyników
Użytkownik: wszystko, co działa, zapisujemy; wszystko, co nie działa, wyrzucamy. `DO-ZAPISANIA.txt`: `run-jobs.sh` dopisuje każdą zakończoną kolejkę GPU, a `wiki.py lint` zgłasza każdą niezapisaną linię jako błąd, dopóki wyniki nie trafią do notatek. Reguła w `~/AGENTS.md`.

## [2026-11-06] ingest | Sweep eco (limit sclk)
[[2026-11-06-eco-sweep-sclk]]: 2200 MHz −1,9% pisania / −10,5% W; 2000 MHz −4,1% / −16,2% W / hotspot −12 °C; 1800 −7,1% / −20,9% W; md5 identyczne. Seria 1600 przerwana przez użytkownika.

## [2026-11-06] decyzja | Profil eco 2200 MHz w produkcji
[[2026-11-06-profil-eco-2200]]: limit sclk 2200 MHz na stałe (crontab @reboot); pod obciążeniem 2215 MHz, 233 W, hotspot 64 °C, wentylator 3578 RPM.

## [2026-11-06] ingest | Szybki bench eco vs stock
[[2026-11-06-eco-szybki-bench]]: greedy −2,0%, prefill −11%, −35 W, hotspot −6 °C, md5 identyczne.

## [2026-11-06] ingest | Kontekst 262 144 na XTX
[[2026-11-06-ctx-262k-fit]]: 254 977 tok. bez OOM, szczyt 23 367 MiB, decode 78,7 t/s na końcu; czat (uncensored) domyślnie 262 144.

## [2026-11-06] ingest | FINAL MODE (eco 2200 + 262k)
[[2026-11-06-final-mode]] i sekcja FINAL MODE w [[REKORDY]]: czat 262 144, −13,9% W, greedy −1,8%, md5 identyczne; UD-Q4_K_XL 262k mieści się z zapasem 336 MiB (niewdrożone).

## [2026-11-06] ingest | Raport 65: VRAM z rezerwy MTP
[[raport-65-vram-rezerwa-mtp]]: −1,0 GiB → kontekst 262 144; akcja na CUDA/Enigmę w DO-ZAPISANIA.

## [2026-11-06] update | REACTOR: płynny przez SSH, prefill na żywo
[[reactor-monitor]]: faza LLM na żywo (PREFILL t/s · tokeny · % z linii `prompt processing`, DECODE z `GET /slots`), dane co 0,25 s, renderer różnicowy na komórkach + kontrola przepływu sondą DSR, tryb `ssh-lite`. 200x55 przez SSH: 1,79–1,81 MB → 267–280 KB / 10 s; wolny terminal 40 KB/s: zaległość do 30 s → 0,07–0,10 s.

## [2026-11-06] ingest | Tailscale na serwerze
[[tailscale]]: zdalny SSH przez tailnet (MagicDNS), bez otwierania portów.

## [2026-11-06] research | 66f Flash-Next: dobór kwantu na XTX
[[qwen38-flash-next]]: Strata + IQ3_S zalecane; UD-IQ4_XS najwyższy mieszczący się; UD-Q4_K_XL nie.

## [2026-11-07] ingest | Raport 66: Strata 0.2.12, Maya 1.1.55–56, 1Cat, TokenSpeed, Hyperkernel, Saber, tqLLM 1.4.4
Nowe: [[raport-66-synteza]], [[kv-raz-na-weryfikacje]], [[mmq-q6k-skale-lds]], [[maska-kq-host-dlugi-ctx]], [[prog-draftu-od-kosztu-wiersza]], [[glowica-draftu-rerank]], [[drzewo-weryfikacji-gdn-wy]], [[siatka-checkpointow-gdn]], [[strumien-on-wyrocznia]], [[budzet-megakernela-qwen-xtx]], [[lekcja-tps-z-zalozonej-akceptacji]], [[lekcja-flaga-bez-dowodu-dzialania]], [[hyperkernel]], [[1cat-vllm]], [[tokenspeed]], [[saber-engine]]. Aktualizacje: [[strata]], [[project-maya]], [[tqllm]], [[megakernele-prior-art]], [[fattn-kvq]], [[radeon-ai-pro-r9700]], [[lekcja-mikrobench-klamie]], [[raport-24h-kv-jeden-przebieg]], [[raport-54-mniej-granic]] (pomiar x54 z 2026-10-21: proza +0.24%, `mvs` 0.0%). Synteza z rankingiem 20 bezstratnych pomysłów: `product/research/66-SYNTEZA.md`. [[ZRODLA]]: sekcja „Raport 66”. [[AUDYT]] uzupełniony. [[REKORDY]] bez zmian (brak nowych pomiarów GPU).

## [2026-11-07] update | 66f Flash-Next: korekta z 66a, GSQ-RCO, Unsloth v3.1 vs GSQ
[[qwen38-flash-next]]: MTP `qwen4exp` w llama.cpp master od b11330 (#29761), gałąź danielhanchen #28243 zamknięta bez scalenia. Strata ma dwie reguły RAM: ISTA „eksperci + ~10 GB”, Unsloth „eksperci + 16 GiB”, inaczej budżet RAM − 24 GB. UD-IQ4_XS w Stracie działa w trybie budżetu (~17 GiB z SSD). Kwant: UD-IQ3_XXS v3.1 (83.6 GB) najlepszy przy tym rozmiarze (KLD ~0.052 vs ~0.065 GSQ IQ3_S, wykres Unsloth, stronniczy); GSQ IQ3_S zostaje alternatywą w Stracie.

## [2026-11-07] eksperyment | prawdziwa sesja w final mode
[[2026-11-06-sesja-uzytkownika-final-mode]]: 120,8 t/s ważone (143 zadania, do 139k), 95,8 t/s przy 128–160k; README i REKORDY zaktualizowane; serwer nie wstał sam po restarcie (brak usługi).

## [2026-11-07] ingest | raport 67b: ostateczne modele per VRAM (NVIDIA)
[[final-modele-per-vram]]:
- 24 / 32 GB: Qwen3.8-27B przy 262 144 z MTP (UD-Q4_K_M / UD-Q6_K).
- 16 GB: GSQ IQ3_XXS-mtp, 200–217k z MTP albo 262k bez MTP.
- 12 GB: Saluki-MTP 135k (licencja od 11-05 CC BY-NC) albo Bonsai Q2_0 221k.
- 11 GB: Bonsai. 8–10 GB: LFM2.5 Q4_K_M z `--n-cpu-moe`.

Model pamięci upstream: błąd ≤ 23 MiB, RS × (n+1), limit = suma CUDA. [[saluki]]: licencja poprawiona.

## [2026-11-07] eksperyment | kampania NVIDIA na Vast (17 kart)
[[2026-11-07-kampania-nvidia-vast]]: 262 144 z MTP na 4090 79,1 t/s (+67,6 proc.) i 5090 86,9 (+44,7 proc.); 16 GB wymaga zapasu 0,7 GiB; poprawki memory.ts/optimize.ts/index.ts; koszt $3,47.

## [2026-11-07] eksperyment | kampania NVIDIA 67c (wznowienie)
[[2026-11-07-kampania-nvidia-vast]] (sekcja 67c), nowa [[final-recipes-nvidia]]: walidacja picków Enigmy wszystkie PASS (5090 102,19, 4090 76,44, 3090 61,49 t/s); fork+kvq+lean na 4090 262 144 **101,27 t/s**; lean MTP n2 na 16 GB 217–229k (5080 81,62); prism Bonsai 4070 94,81; LFM 4070 w VRAM 179,3; pin b11856 zostaje (5090 ABBA). Aktualizacje: [[REKORDY]], [[backlog-testow-nvidia]] (A1/A5/A6/A7/A11/A13, B1–B4, B14, D1/D3/D4, E2), [[rtx-3060]], [[rtx-3090]], [[rtx-4060-ti]], [[rtx-5060-ti]], [[inne-karty-nvidia]], [[final-modele-per-vram]].

## [2026-11-07] synteza | Enigma na NVIDIA: strona + nauki
`product/SITE-NVIDIA.md` (materiał na enigmalabz.com) i [[jak-przyspieszylismy-nvidia]] (co dało ile, 9 nauk); nowe lekcje [[lekcja-zapas-doladowania-kerneli-cuda]], [[lekcja-paczka-march-native]], [[lekcja-pick-z-kalkulatora]], [[lekcja-licencja-modelu-sie-zmienia]]; [[lekcja-limit-mocy-hosta]] uzupełniona o 5090 450/575 W.

## [2026-11-07] wdrożenie | silniki CUDA Enigmy opublikowane
Wydanie GitHub `enigma-engines-cuda-2026-11-07` (KERNEL): fork kvqlean/kvqleana, b12110lean, prism, słownik draftu; `engines.json` → download; planner domyślnie na silnikach Enigmy (Linux x64). Fork z poprawionym RUNPATH ([[lekcja-paczka-march-native]]).

## [2026-11-07] lekcja | czat wstał na starym silniku
[[lekcja-restart-zlym-launcherem]]: po restarcie maszyny `run-llm.sh` zamiast `run-topka.sh` → ~6 h produkcji na llama-opt z 15.10; naprawione restartem przez run-topka.sh (topka-q63, PM4, lookup, GPU verify, n_ctx 262144).

## [2026-11-07] eksperyment | Q6_K MMQ skale — KILL
[[2026-11-07-q6k-mmq-skale]]: pp4096 1000,7 → 1000,6 t/s, prefill 12k 933,1 → 933,0, md5 =; łatka 0004 usunięta. Research 68a–d + synteza 68.

## [2026-11-08] lekcja | cpuheavy w jobie kolejki
[[lekcja-cpuheavy-w-jobie-kolejki]]: zakleszczenie kvq-once2 (quiet.lock); kolejność biletów GPU ustawiona wg wartości.

## [2026-11-08] eksperyment | kvq KV raz na weryfikację + profil 199k — KILL
[[2026-11-08-kvq-once-profil]]: FA = 100% nachylenia kroku 1.7k→199k (11.3 ms, 30% GPU); `GGML_HIP_KVQ_ONCE=1` bitowo = (md5 1.7k/94k/199k), FA −6.1% przy 199k (próg −10%) → KILL, e2e 199k +1.79%, 94k +0.89%; podziały kvq: 2 bloki/SM najlepsze → KILL. ONCE=2 (job przerwany zakleszczeniem cpuheavy) ponowiony.

## [2026-11-08] eksperyment | zapis prompt cache bez zerowania (#30137) + THP — niezmierzone
[[2026-11-08-cachesave-30137]]: port #30137 + `LLAMA_SERVER_CACHE_HUGE=1` (THP, ponowne użycie bufora po eksmisji) na `l1-cachesave` 3152b0bfa, łatka topka-q63/0004; nie zbudowane ani zmierzone (koniec testów), job `qwen-opt/cachesave/` gotowy do wznowienia.

## [2026-11-08] update | kvq-once: koniec testów
[[2026-11-08-kvq-once-profil]]: ONCE=2 i okno uwagi draftu MTP przy 94k/199k nie zmierzone (joby anulowane przed startem); sekcja „Stan / do wznowienia”.

## [2026-11-09] zamknięcie | testy XTX z 07–08.11 spisane
[[2026-11-08-l1-tokenizacja-parser]] (tokenizacja 14,0 → 6,6 ms, md5 =, pomiar A→B bez A2), [[2026-11-08-fa-d256-prefill]] i [[xtxbench-szybki-ab]] (kod gotowy, niezmierzone), synteza 68 ze stanem wznowienia; czat po restarcie maszyny 09.11 00:30 uruchomiony przez run-topka.sh + autostart w crontabie (@reboot).

## [2026-11-09] eksperyment | xtxbench t1: walidacja A/A na GPU
[[xtxbench-szybki-ab]]: pomiar czasu działa (szum decode 0,02–0,15%, prefill 0,03–0,33%, A/A NULL, 3,9 min/wariant vs ~38 min), ale md5 decode z migawek niewiarygodne — tylko pierwszy restore na świeżym serwerze = świeży prefill, kolejne inne (fałszywy KILL w A/A); do poprawki przed bramką md5.

## [2026-11-09] update | xtxbench: md5 tylko z pierwszego restore + wyciek stanu
[[xtxbench-szybki-ab]]: werdykt md5 tylko z pierwszej rundy po świeżym starcie serwera, `--var-switch` → md5 n/a (same-server); selftest 7/7 z modelem wycieku. Znalezisko w [[2026-11-08-kvq-once-profil]] i syntezie 68: drugi restore slotu ≠ świeży prefill (podejrzenie: reset MTP/rekurencji, por. #30574).

## [2026-11-09] eksperyment | kvq ONCE=2 (K raz na parę fal) — KILL
[[2026-11-08-kvq-once-profil]]: bitowo = (fa_hash 18/18, tbo 381/381, md5 199k efdb8053), FA 196k nb5 623,4 → 625,7 µs (+0,4%; ONCE=1 574,0), 98k 321,2 → 325,6; e2e 199k 95,09 → 94,73 t/s (−0,38%), spec_sweep 121,05 → 120,9; PMC FETCH_SIZE = 0 (licznik nie działa).

## [2026-11-09] decyzja | próg adopcji ≥ 3–5% / ≥ 1 s na turę; l1tok i mtpw zamknięte
Użytkownik: ułamki procenta to nie cel. [[2026-11-08-l1-tokenizacja-parser]]: bezstratne, −85 ms/turę, nie wdrażamy (A2/C anulowane). [[2026-11-08-kvq-once-profil]]: ONCE=1/2 KILL, okno MTP nie mierzone (anulowane, oczekiwany KILL). Próg w syntezie 68 i [[xtxbench-szybki-ab]].

## [2026-11-09] ingest | raport 69: DSpine-27B, qwen-warp/TensorFold, Astra-Stop, AMD Adrenalin
[[raport-69-synteza]] (synteza `product/research/69-SYNTEZA.md`). Zaktualizowane: [[drafter-dspine]] (27B: SWA 8192, port Ajay9o9 `d493f84`, twierdzenia vs fakty, model XTX per klasa), [[qwen-warp]] (v0.8.0: DFlash2 w grafie, multiuser), [[tensorfold]] (v1.2.5+: gfx1100 dalej brak). Nowe: [[astra-stop]] (zmiana zachowania, nie bezstratna; przeciek `</think>` 11/32; LoRA 90 KB), [[amd-adrenalin-zapisy-ssd]] (serwer nie dotyczy; nigdy nie radzić wyłączania ReBAR). [[ZRODLA]]: sekcja „Raport 69” + wiersze dublowania DSpine/qwen-warp/TensorFold. Wszystkie testy czekają na decyzję użytkownika (6 punktów w syntezie).

## [2026-11-09] decyzja | po rundzie 69
[[2026-11-09-decyzje-runda-69]]: DSpine odpuszczony (64k), Astra-Stop odłożony (temat na fine-tuning), publikacja rankingów wkrótce, jakość-mini dla 12–16 GB.

## [2026-11-08] lekcja | build landingu bez $HOME
[[lekcja-build-landing-nie-czyta-home]]: `scripts/cards.ts` i `scripts/sync-results.ts` liczą ścieżki danych od roota repo (fallback do `~` zostaje dla serwera GPU); build w klonie z pustym `HOME` = kod 0, sha256 `cards.json`/`cloud-results.json` bez zmian.

## [2026-11-09] produkt | landing przebazowany na KERNEL main 8307d36, równy żywej d3054d2
[[strona-zrodlo-rowna-zywej]]: gałąź `nvidia-2026-11` przebazowana bez `--force` na `main` `8307d36`; konflikt tylko w meta — meta z maina (`metaTitle`/`metaDescription`) + `<Seo>` z misji, twarde spacje z żywej wróciły do źródła; ekrany `/app/` dostały OG/Twitter. Pomiar: head 86/86 i tekst 86/86 bez różnic, markup 0 realnych różnic, `leaks` CZYSTO, `bun run check` 0/0, `404.html` 0 `../` i 53/53 zasobów < 400. Odstępstwo: nazwy chunków `_app/i4` inne (źródło ma dodatkowe moduły), `version.json` z definicji.

## [2026-11-09] eksperyment | FA D256 prefill RDNA3 (VAR 83) — PASS, rekord
[[2026-11-08-fa-d256-prefill]]: fill 255k 466,3 → 493,4 t/s (+5,8%, −30 s), llama-bench d128k 459,5 → 486,3 (+5,8%), d32k +1,9%, d4k +0,5%; md5 12k/32k/255k =, spec_sweep 119,2 = 119,2. Kandydat do wdrożenia (czeka na OK). Pierwszy przebieg padł na rc=127 (LD_LIBRARY_PATH), ponowiony. [[REKORDY]].

## [2026-11-09] research | raport 70: post-mortem FA D256 VAR 83
`product/research/70-fa-d256-jak-to-zrobilismy.md`: oś czasu pomysłu (0042 → 24v → #31746 → 68a/c/d → XtxFaPrefill), rozkład maski 83 (bariery KQ/V + V^T w LDS + `nbatch_V2` 32; spille 220 → 0, LDS bez zmian), efekty izolowane wariantów, model udziału FA od głębokości, metoda i porażki (rc=127 RUNPATH z cichą kaskadą rc=0, `cpuheavy` w jobie), macierz reprodukowalności (MMQ, autotune Enigmy per arch, inne kształty FA, `kvq`, CUDA, GDN, upstream) i przepis wdrożenia. Nowe: [[sweep-wariantow-kernela]], [[lekcja-zysk-rosnie-z-glebokoscia]]; link w [[2026-11-08-fa-d256-prefill]].

## [2026-11-09] eksperyment | cachesave PASS
[[2026-11-08-cachesave-30137]]: #30137 + huge pages — tura przełączenia wątku −972 ms (−7,2
## [2026-11-09] eksperyment | cachesave PASS
[[2026-11-08-cachesave-30137]]: #30137 + huge pages — tura przełączenia wątku −972 ms (−7,2 proc.), zapis cache 1 056 → 267 ms, md5 =; EvalPlus i jakość-mini wstrzymane na polecenie użytkownika.

## [2026-11-09] eksperyment | qwen-warp vs fork CUDA na wynajętym 3090 (R69b Q1)
[[2026-11-09-qwen-warp-vs-fork-3090]]: ta sama karta 350 W, 6 promptów, streaming, oba przy 262 144. qwen-warp ×1.46/×1.61 (krótki), ×1.48/×1.81 (16k), ×1.58/×1.59 (64k), ×1.60/×1.65 (128k), ×1.34/×1.52 (262k) T=0/T=1 → kill < ×1.15 nie zachodzi; ~×1.24 to lżejsze wagi [SZACUNEK]. Oba mieszczą 262 144. Zaktualizowane [[qwen-warp]]. Koszt $0.53, 0 instancji.

## [2026-11-09] wdrozenie | topka-q70 w produkcji XTX
[[2026-11-09-wdrozenie-topka-q70]]: `~/llama-topka` = topka-q70 (q63 c0576e3e8 + cachesave #30137/huge pages + FA D256 VAR 83, env domyślne w `run-topka.sh`), zamiana 15:00:16 UTC, backup `~/llama-topka.c0576e3e8`. md5 long 32k / fill 255k / przełączanie =; fill 255k 466,3 → 492,5 t/s (+5,6%), tura agenta 76–112k 13 413 → 12 029 ms (−10,3%), spec_sweep 119,3 bez zmian. [[REKORDY]] nowy wiersz tury agenta, fill 255k „prod. tak”; [[qwen3-8-27b]] linia produkcji; raport 70 §6 wykonany. Łatki `qwen-opt/patches/topka-q70/`, skrypty `qwen-opt/deploy-q70/`, narzędzie `qwen-opt/speed_real.py`.

## [2026-11-09] eksperyment | EvalPlus: Qwen3.8-27B-Uncensored, produkcja XTX, effort low
[[2026-11-09-evalplus-qwen-uncensored]]: greedy pass@1 HumanEval 97,6 / HumanEval+ 92,7 / MBPP 92,9 / MBPP+ 80,2 % (topka-q70 `3191b25f4`, port 8097, 786/704 tok/odp., 0 uciętych, gen 2627 s); dekod 174,2 / 156,7 t/s (T=0), narzut stały ~230 ms/żądanie. Effort low vs wyższy niezmierzony. Nowa metoda [[evalplus-jakosc-kodu]] (`qwen-opt/evalplus/jakosc-mini.sh`, piaskownica Landlock).

## [2026-11-09] eksperyment | jakość-mini: Qwen3.8-27B-Uncensored, produkcja XTX, effort low
[[2026-11-09-jakosc-mini-qwen-unc]]: 255/290 = 87,9% (CI 83,7–91,2), makro 91,3%; GSM8K 50/50, MMLU-Pro 115/140, PL 43/50, HumanEval+ 28/30 (z biegu EvalPlus), BFCL 19/20; topka-q70 `3191b25f4`, T=0, gen 2253 s, 1 ucięta (32 768 tok). Prędkość na zadaniach: dekod ważony 142,4 t/s (PL 120,1 … HumanEval+ 174,8). Nowa metoda [[jakosc-mini]] (`qwen-opt/jakosc-mini/`, podzbiory seed 20261109, 5 źródeł w [[ZRODLA]]).

## [2026-11-13] meta | Kolejka testów na karcie
[[KOLEJKA-TESTOW]]: nowa jedna kolejka pomysłów do sprawdzenia na karcie (jaroserverai: XTX + RTX 5060 Ti), zebrana z raportów (15–70, SYNTEZY 63/66/68/69/70, 67c), wiki (eksperymenty, decyzje, metody, STAN-PRAC, REKORDY) i archiwum rozmów 2026-09-15 … 2026-11-13: 75 pozycji „Czeka” (17 czeka na decyzję właściciela), 27 „Odrzucone” (zmieniają odpowiedzi, zakazy właściciela, zmierzone KILL). Wpis z `DO-ZAPISANIA.txt` (martwy kod capu LDS FA `57204db1e`) przeniesiony do kolejki jako K-055. Indeks i rejestr źródeł linkują kolejkę; `tools/wiki.py` zwalnia ją z limitu słów jak REKORDY/ZRODLA.

## [2026-11-13] research | Telegram „gpu”: SGLang Unified Memory
[[sglang-unified-memory]]: jedna arena VRAM dla KV, okna SWA i stanu GDN w SGLang (blog LMSYS 2026-11-11); zysk tylko przy wielu żądaniach naraz (H200: do +26%, 1000 vs 618 żądań), domyślnie szum (5830 vs 5880 tok/s). Werdykt: nie warto, topka ma 1 slot bez podziału pul; brak pozycji w [[KOLEJKA-TESTOW]].

## [2026-11-13] meta | Nowa sekcja llm/ (trening i jakość LLM)
Na prośbę właściciela (Telegram „gpu”): folder [[llm/_hub|llm]] na trening, dostrajanie, edycje wag i jakość modeli, oddzielony od optymalizacji silnika; mapa [[trening-llm-mapa]] zbiera dotychczasowe wyniki (pilot głowicy MTP ±0,2%, fine-tune DFlash2 bez zysku, Uncensored i Astra-Stop jako edycje wag, EvalPlus/jakość-mini). Starsze notatki zostały na miejscu, mapa do nich linkuje. `tools/wiki.py` i [[KONWENCJE]]: nowy typ `llm`.

## [2026-11-14] research | Telegram „gpu”: silnik pod DeepSeek, InferenceForge, vstack
[[telegram-2026-11-14-silniki-agenci]]: 4 linki. Silnik Rust+CUDA pod DeepSeek-V4.1-Flash (Baseten, 4× B300 ~1740 TPS, +15% vs SGLang) potwierdza K-014 (dopisane źródło), InferenceForge (+43% na AgentX, brak źródła pierwotnego) i vstack (TLA+/Z3, 17 błędów w vLLM/SGLang) dotyczą serwowania wielu żądań. Werdykt: nic nowego do testu na karcie; 3 wiersze w [[ZRODLA]].

## [2026-11-14] research | Telegram „gpu”: PearlQuant, llama.cpp v1.0.0
[[telegram-2026-11-14-pearlquant-llamacpp-v1]]: PearlQuant (KV E8, 3,2 bita) stratne → K-079, metoda oceny → K-007. llama.cpp v1.0.0 (b12359): #31533 few-row MMQ scalone (Qwen3.8-27B spec-dec na NVIDIA +16,7…34,9% tok/s) → nowa K-103 (Enigma NVIDIA na v1.0.0, priorytet wysoki) i K-013 podniesione; #30541 (kopia stanu skwantowanego KV) jako hipoteza K-001; K-056 cel rebase v1.0.0.

## [2026-11-14] research | Telegram „gpu”: TokenSpeed Kimi K3 na AgentX
[[tokenspeed]] (delta): blog Kimi K3 331 tok/s/GPU na 32× GB300 (1,92× DCP8) przez DWDP prefill, DEP16 dekod i wspólną pamięć hosta 5,45 TB; skala klastra, dla jednej karty 0%, nic nowego do kolejki (źródło dopisane do K-047).

## [2026-11-14] research | Telegram „gpu”: llama.cpp v1.0.0 (ponownie)
Ten sam link co rano ([[telegram-2026-11-14-pearlquant-llamacpp-v1]], commit `b88ec25`); najnowsze wydanie nadal v1.0.0 (b12359), delta brak. Działania w kolejce bez zmian: K-103, K-013, K-001, K-056.

## [2026-11-14] meta | ZRODLA: adresy x.com dla dwóch wpisów z Telegrama
Na prośbę właściciela: dopisane URL https://x.com/zainhas/status/2120806646356295682 (TokenSpeed Kimi K3 AgentX, także w [[tokenspeed]]) i https://x.com/ggerganov/status/2121246103312212124 (llama.cpp v1.0.0, także w [[telegram-2026-11-14-pearlquant-llamacpp-v1]]).

## [2026-11-14] research | Telegram „gpu”: Project Maya v1.1.62
[[project-maya]] (delta v1.1.57–v1.1.63): APU AMD + NVIDIA liczą jeden model MoE (GLM-5.3-Flash prefill 32K 293 → 901 t/s, DeepSeek dekod +18%); dla gęstego Qwen 27B na XTX nic, 5060 Ti przy podziale warstw tylko spowolni dekod. Bez pozycji w kolejce.

## [2026-11-14] research | Telegram „gpu”: Infrathon
Infrathon (arXiv 2611.11995, [[ZRODLA]]): benchmark długich przebiegów agentów nad infrastrukturą AI na H100; wynik 19,86× to stratny kodek KV dla modelu wideo. Dla nas brak testu na karcie; wniosek o metodzie (bramki przeciw „przedwczesnemu gotowe” i zawodnym testom) już stosujemy.

## [2026-11-14] llm | Telegram „gpu”: techniki PEFT
[[peft-lora-warianty]]: ściąga LoRA / LoRA-FA / VeRA / Delta-LoRA / LoRA+ (prace źródłowe zweryfikowane na arXiv) w sekcji [[llm/_hub|llm]]; lekcja: metoda PEFT zmienia koszt treningu, a koszt inferencji zależy od scalenia adaptera. Bez testu na karcie.

## [2026-11-14] produkt | Karty NVIDIA z kampanii 67 na stronie
[[karty-nvidia-na-stronie]]: właściciel odrzucił osobną stronę z tabelą 11 kart; każda karta dostaje stronę jak RTX 3090 (5090, 4090, 5080, 4070, 2080 Ti, 3080, 3070 nowe, 3060 z nowymi danymi). Underdog Saluki (CC BY-NC) usunięty ze strony. Kciuk wyboru karty na Wynikach naprawiony dla wielu rzędów.

## [2026-11-14] decyzja | Saluki usunięty z aplikacji Enigma; na stronie zawsze najnowsze pomiary
[[2026-11-14-saluki-usuniety]]: aplikacja Enigma bez Saluki (katalog, planer, UI, testy 208/208 + tsc + svelte-check 0 błędów); 12 GB = Bonsai 2 (prism PTQ1_0+MTP 94,73/58,31 t/s, upstream Q2_0 196 608 zmierzone); [[saluki]] → nieaktualne; SITE-NVIDIA, [[final-recipes-nvidia]], [[final-modele-per-vram]] poprawione. Stała reguła: po kampanii zgłaszać karty do odświeżenia na stronie.

## [2026-11-14] produkt | Karty 3090, 5060 Ti, 4060 Ti z listopada; lżejsze strony kart
[[karty-nvidia-na-stronie]]: decyzja właściciela „najnowsze dane wygrywają”: 3090 (40,93 → 61,49 → 79,97 t/s), 5060 Ti (27,48 → 31,42 → 43,40) i 4060 Ti (19,78 → 24,02 → 36,30) z raportu 67; LFM2.5/Nemotron bez nowszych pomiarów zostają z października z opisem hosta. Strony kart lżejsze na telefonach (TBT ~100 ms, mobile z kompresją 82/85, bez kompresji 64/66). Gałęzie `karty-r5` (KERNEL) i `nvidia-r5` (strona, build `_app/i6`).

## [2026-11-14] eksperyment | kolejka na XTX: K-001, K-002, K-003, K-013
[[2026-11-14-k001-wyciek-stanu-restore]]: md5 po restore zależy od historii serwera (R1 = świeży, R2/R3/F2 inne) niezależnie od lookupu, sprzężenia i PM4; podejrzany `v_heads`, #30541 odpada. [[2026-11-14-k002-k003-k013-xtx]]: K-002 odrzucone (lookup 130,4 vs 131,2 t/s, w szumie); K-003 koszt stały = 139 ms serwera (checkpointy GDN + prefill w 2–3 przebiegach) → nowa K-104; K-013 baseline V16 − V5 = 7,1 / 10,1 ms (2k / 32k). PM4 przy 1,7k: 122,6 → 130,4 t/s (+6,4%). Produkcja :8080 po testach: topka-q70, n_ctx 262144, health ok.

## [2026-11-14] eksperyment | K-103 na Vast (RTX 5060 Ti)
[[2026-11-14-k103-llamacpp-v1-nvidia]]: llama.cpp v1.0.0 vs pin b11856, Qwen3.8-27B ISTA IQ3_XXS-mtp MTP n2: spec_sweep T=1 43,95 → 45,62 t/s (+3,8%, ABBA; poprawione 2026-11-14, wcześniej +3,5% = sama para A1→B1), przebieg weryfikacji ub 8 +12,1%, ub 16 +9,8%; brak regresji b12110. Koszt ~0,10 USD, 0 instancji. Nowa K-105 (szersza weryfikacja, 24/32 GB, decyzja o pinie).

## [2026-11-14] rekord | decode 1,7k na produkcji (PM4)
[[REKORDY]]: decode MTP 1,7k T=0 topka-q70 133,9 t/s (świeży prefill 130,4; bez PM4 125,2/122,6 → PM4 +6,4%), zastępuje 130,2 z 2026-10-14. PM4 jest w produkcji od 2026-10-21 (`run-topka.sh`: `GGML_HIP_PM4=1 WA=2 GUARD=1`), nic do wdrożenia.

## [2026-11-14] decyzja | pin Enigmy zostaje b11856 (bramka K-103)
[[2026-11-14-k103-llamacpp-v1-nvidia]]: oficjalne binarki b12359 (v1.0.0) vs b11856 na 5060 Ti: KLD 0,000700 vs szum upstreamu 0,000569–0,000615 (~2σ ponad), MTP n3 +0,6%, VRAM +48 MiB (zapas 4090 upstream 46 MiB) → zgoda właściciela na wdrożenie „jak lepsze”, ale v1.0.0 nie jest bezstratny ani ponad progiem; pin bez zmian. PM4 już w produkcji. K-105 przeformułowane na port #31533 do forka. Vast łącznie ~0,15 USD, 0 instancji.

## [2026-11-14] poprawka | K-103 i K-003 (uwagi Jarva)
K-103: zysk przy MTP n2 to +3,8% (mediany 43,95 → 45,62 t/s; parami +3,5 / +4,2%), nie +3,5%; poprawione w [[2026-11-14-k103-llamacpp-v1-nvidia]], [[KOLEJKA-TESTOW]] i wpisie wyżej. K-003: reszta poza serwerem to 2,0 ms w każdym żądaniu (1,7–2,3); „brakujące” 12 ms to efekt sumowania median — w [[2026-11-14-k002-k003-k013-xtx]] dodana kolumna średnich, które się domykają (147,2 + 106,7 + 2,0 = 255,9).

## [2026-11-14] eksperyment | K-104 KILL, K-013 build w toku
[[2026-11-14-k104-krotki-ogon-promptu]]: `LLAMA_SERVER_SHORT_TAIL=32` — prompt krótkiej tury 148,7 → 148,5 ms (0%), zmienia md5, decode 1,7k 135,4 → 128,0 t/s → odrzucone; nic nie wdrożone. K-013: build upstream few-row MMQ HIP (6ad15f48) dla gfx1100 i automatyczny pomiar V(w) w kolejce po buildzie (odłączone).

## [2026-11-14] update | Zwiad: compwatch na serwerze 24/7 + arXiv i blogi RSS
[[raport-watch-compwatch]]: compwatch przeniesiony na serwer bez GPU (timer systemd 06:30, `Persistent=true`, `nice 15`, `CPUQuota=50%`); błąd jednego źródła nie kończy przebiegu. Nowe źródła: TensorRT-LLM, MLC LLM, mistral.rs (tier B), arXiv (`cs.LG/DC/PF/AR/CL`, 1 zapytanie na 3 s, duplikaty po id), 9 blogów RSS/Atom. Raport z nowościami → wiadomość `[Zwiad · data]` dla sesji Kernel; próba 14.11: 87 pozycji (przebieg bazowy) w 47 s, drugi przebieg 0 nowych.

## [2026-11-14] zwiad | compwatch przebieg bazowy
[[zwiad-2026-11-14]] (raport `product/research/watch/2026-11-14.md`): hipfire 0.4.4 na XTX dogonił topkę przy krótkim kontekście (127–131 t/s) numerycznymi kernelami weryfikacji (#987/#989), my bitowo jesteśmy na tym samym poziomie; LocalMaxxing XTX top verified nadal 97,2; tqLLM dokładne próbkowanie MTP T>0 → K-004; TensorFold wznowienie po usunięciu rozumowania (do sprawdzenia w omp); 6 wierszy ZRODLA, źródła dopisane do K-004/K-012/K-059. K-013 (zlecenie właściciela z 14.11): upstream few-row 26–81% wolniejszy od topki na V5–V16, few-row bez darmowego zysku.

## [2026-11-15] zwiad | compwatch (delta, 15 pozycji)
[[zwiad-2026-11-14]] (delta 11-15, raport `product/research/watch/2026-11-15.md`): TensorFold 1.2.9 (Metal/TP/gfx1151), 1Cat-vLLM T>0 bez sync hosta (warunkowy graf CUDA → źródło K-014), sglang reset GDN bez sync; nic do testu na karcie; 3 wiersze ZRODLA.

## [2026-11-15] research | Telegram „gpu”: architektura GPU (wpis edukacyjny)
Wpis @akshay_pachaar o pasmie pamięci vs obliczeniach: znane podstawy, już w [[sufit-pasma-i-mapa-czasu]]; bez testu, wiersz w [[ZRODLA]].

## [2026-11-15] llm | Mapa inżynierii inferencji (roadmapa z Telegrama)
[[mapa-inferencji-roadmap]]: 114 tematów roadmapy „LLM Inference Engineering” zestawione z wiki: 79 zmierzonych u nas, 15 opisanych, 20 luk; ranking luk; nowe K-106 (interferencja prefill–decode, XTX) i K-107 (XTX + 5060 Ti) w [[KOLEJKA-TESTOW]]. Notatka zwolniona z limitu słów (tabela) w `tools/wiki.py`.

## [2026-11-16] zwiad | compwatch (delta, 29 pozycji)
[[zwiad-2026-11-14]] (delta 11-16): hipfire 0.4.7 patch, Strata 0.2.14 własne kernele prefillu (stratnie), Maya 1.1.64–65 stabilność; arXiv: energia na rozwiązane zadanie (wzór dla Enigmy), Superfluid (priorytet interaktywnych żądań → K-106). Nic na kartę; 6 wierszy ZRODLA.

## [2026-11-17] research | skill „inference-optimisation” (Sybil Solutions) — przestudiowany w całości
[[skill-io-przeglad]] + [[skill-io-sufity]], [[skill-io-metodyka]], [[skill-io-dzwignie]], [[skill-io-pulapki]], [[skill-io-publikacja]], [[skill-io-skrypty]]: 17 plików @ fda968e; nasz sufit z ceiling.py (dekod czatu 167 t/s przy 2k → produkcja 71–77%, krok 19,2 vs 26,9 ms; prefill 92–95%); 19 z 29 dźwigni stosujemy; nowe K-108 (FLOPS XTX), K-109 (bramka igieł), K-110 (ich bench.py 1:1), K-111 (rozkład luki kroku).

## [2026-11-17] research | skill-io pod kątem AMD i NVIDIA (zakres: wszystkie karty obu firm)
[[skill-io-sufity]]: sufity `ceiling.py` dla 18 kart (RX 6800/6900 XT, 7900 GRE/XT/XTX, 9070 XT, MI250/300X/325X/355X, RTX 3090/4090/5060 Ti/5090, A100/H100/H200/B200) ze specyfikacji producentów (`qwen-opt/skill-io/karty.py`); zmierzone vs sufit: XTX 69–71%, 4090/5090 59%, 3090 50%, 5060 Ti 41%. Sekcje per firma w [[skill-io-dzwignie]], [[skill-io-pulapki]], [[skill-io-metodyka]], [[skill-io-publikacja]], [[skill-io-skrypty]], [[skill-io-przeglad]]. Kolejka: K-112 (pasmo/GEMM/prefill NVIDIA), K-113 (bench.py 1:1 trzy karty), K-114 (rozkład kroku NVIDIA), K-115 (igły NVIDIA).

## [2026-11-17] telegram | zgoda na Vast (3090, 5060 Ti, 3060 ≤ $1) — wstrzymane: brak klucza Vast tutaj, jaroserverai wyłączony
[[skill-io-sufity]]: dopisana RTX 3060 12 GB (360 GB/s, 25,5/101,9 TFLOPS; sufit MTP Qwen 65 t/s; Bonsai 58,3 t/s = 45–54% sufitu [INFERENCE]). K-114: wstępna odpowiedź z R69b (3090 przy 350 W: limit mocy odpada, T=1 −7%, qwen-warp ×1,46–1,61 na tej samej karcie → luka w silniku), runner `qwen-opt/cloud/k114/run.sh` gotowy (K-112 + K-114 jednym runem).

## [2026-11-17] research | skill-io: wszystkie firmy (Apple, Intel, Tenstorrent)
[[skill-io-sufity]]: +15 kart (M3 Max, M4 Pro/Max, M5/Pro/Max, Arc A770/B580/Pro B70, Lunar/Panther Lake iGPU, Gaudi 3, Wormhole n150/n300, Blackhole p150), razem 34 w `karty.py`; wniosek: weryfikacja MTP na Apple M1–M4 ograniczona obliczeniami (M4 Pro 63 ms vs 59 ms bajtów) → krótki draft; B70 llama.cpp Q4_K_M 25,0 t/s = 23% sufitu MTP. [[skill-io-dzwignie]]: dźwignie per architektura + „czego brakuje naszemu silnikowi” (upstream `9581154`: GDN/FA są w Metal, SYCL, Vulkan, OpenVINO; Tenstorrent i Gaudi bez backendu ggml). Pułapki, metodyka, skrypty uzupełnione. Vast (K-114) dalej wstrzymany: jaroserverai wyłączony.

## [2026-11-17] zwiad | compwatch 2026-11-17
[[zwiad-2026-11-17]]: rekord kyuz0 R9700 Qwen3.8-27B 594,7 t/s niefizyczny (≤ 190 t/s z sufitu 640 GB/s przy 8 tok./krok); arXiv 2611.20565 (KV draftu K4V4 −1,36% akceptacji; my q4_0 od dawna), 2611.19455 (lookup: najnowsze dopasowanie = nasz lookup); llama.cpp #31327 GDN mma na CDNA, #32308 MMVQ RDNA3.5; Strata 0.2.15, vLLM v0.34.0 bez wpływu. Lekcja [[lekcja-vastai-destroy-pyta]].

## [2026-11-17] eksperyment | K-114 NVIDIA na Vast (3090, 5060 Ti, 3060), $0,33
[[2026-11-17-k114-nvidia-sufit]]: 5060 Ti n2 T=1 51,0 t/s (61% sufitu), 3060 28,6 (42%), 3090 44,4 (23%, host 250 W i pamięć 5001 MHz); draft MTP kosztuje 4–15 × swoje bajty (37–40% kroku) → K-116; T=1 nie wydłuża kroku; start 12 min na słabym CPU → K-117. Instancje usunięte, kredyt $0,16.

## [2026-11-17] lekcja | Vast: tylko karty z pełną mocą (właściciel)
[[lekcja-vast-tylko-pelna-moc]]: bramka `qwen-opt/cloud/hostguard.sh` (moc ≥ 95%, zegar pamięci ≥ 95% specyfikacji z karty.json, < 80 °C bez obciążenia) w `k114/launch.sh`, czarna lista `hosty-zle.txt` (5 hostów), flaga LIMITED HOST w `summ.py`; K-114 3090/3060 oznaczone jako dolne granice; K-118 powtórka po doładowaniu.

## [2026-11-17] poprawka | próg pełnej mocy na Vaście 85% (było 95%)
[[lekcja-vast-tylko-pelna-moc]]: `hostguard.sh` i `summ.py` na 0.85; dzisiejsze 3090 (60% mocy, pamięć 51%) i 3060 (79% mocy) dalej poniżej progu = dolne granice.

## [2026-11-17] telegram | SenseNova-Loop-9B (SenseTime)
[[sensenova-loop-9b]]: pętla warstw 32→56 wykonań, ~7,7 GB/token przy Q4_K_M (plik 5,3 GB) → sufit ~2,1 × Qwen3.8-27B; jakość tylko wg producenta (NL2Repo 41,36 vs 44,60); llama.cpp #31571 otwarte; lekcja: ceiling.py dla pętli liczy wykonania; LoopSkim = darmowy drafter; K-119.

## [2026-11-17] telegram | SenseNova-Loop-9B: cel = pobrać i przetestować (nie optymalizować)
K-119 przepisane na zwykły test modelu (panel ręczny, jakość-mini, EvalPlus, igła 128k; AWQ w SGLang/vLLM na Vast albo GGUF po obsłudze w llama.cpp), priorytet średni, czeka na kredyt.

## [2026-11-17] telegram | Project Maya v1.1.66 (delta)
[[project-maya]]: GLM APU+NVIDIA +19% (weryfikacja czyta wagi raz, jedno wywołanie na warstwę zamiast na token; auto-wybór kolejności tylko przy identycznych odpowiedziach); dla gęstego 27B na XTX nic; lekcja zgodna z K-116.

## [2026-11-18] telegram | Qwen3.8-27B-pi-adapted (HF harness-hub)
[[qwen38-27b-pi-adapter]]: LoRA r32 RL (AsyncGRPO, nagroda + bonus za mniej wywołań, safeagents) na Qwen3.8-27B pod pi: SWE-bench Pro hard 51 29,4 → 62,7%, TB 2.1 39,5 → 55,8%; omp = fork pi; koszt LoRA bez scalania i MTP po scaleniu do sprawdzenia; K-120; pomysł: adapter pod omp z naszych sesji.

## [2026-11-18] telegram | „dlaczego KV bez Q” (Akshay) — podstawy, nic nowego
ZRODLA: wiersz; lekcja dla nas tylko przypomnienie: w hybrydzie GDN poza KV cache trzymamy stan rekurencyjny (checkpointy, K-001), a przy weryfikacji spekulacji N wierszy Q naraz.

## [2026-11-18] telegram | właściciel: „super fajne pomysły” (K-120, adapter pod omp)
Odnotowane w K-120; start po zgodzie na pobranie ~17 GB i doładowaniu Vast.

## [2026-11-18] telegram | Rohan Arun: GA z wyścigami do kerneli (delta R63e)
[[ga-racing-rohanarun]]: silnik 847 linii, eliminacja na log-ratio do mediany żywych, bramka rel < 0,997 i CI < 1 na świeżych danych, pending → czarna lista; demo działa tu (1,4 s, syntetyczne); K-121 adapter do naszych sweepów.

## [2026-11-18] zwiad | compwatch 2026-11-18
[[zwiad-2026-11-18]]: Splash 1.7 (drzewo + lookup, Qwen3.8-27B Mac 1,22–1,46 ×, stratny stan INT8 i niedeterministyczny domyślnie; nasz werdykt drzewa ≤ +5% bez zmian); drafter NVIDIA 0,8B do 27B (droższy niż MTP; lekcja: destylacja draftera PL); llama.cpp stream-k GCN; kyuz0 R9700 514,9 dalej niefizyczne.

## [2026-11-18] telegram | ml-systems-notes (Jino Rohit) — notatki edukacyjne
Nic nowego w teorii; zapisane 2 pomiary autora w [[skill-io-pulapki]]: kolejka uruchomień CUDA ~1024 kernele (4060 Ti) → uwaga w K-116; SGLang 0.5.9 radix na hybrydzie wyłącza overlap schedule (dotyczy K-119).

## [2026-11-18] telegram | llamAmpere v0.7 (fork Ampere)
[[llamampere]]: nagłówki stratne (mb-MTP domyślnie, LSA na 12/8 GB +40–51%, własne kwanty); bezstratne: drafter DFlash2 ×3,4 po usunięciu podwójnego kroku (wzorzec K-116), weryfikacja 4 użytkowników równolegle ×2,1; K-122 porównanie w trybie dokładnym z forkiem na 3090 (razem z K-118).

## [2026-11-18] lekcja | czas optymalizacji to metryka (właściciel)
[[lekcja-czas-optymalizacji-to-metryka]]: bodziec RightNow (Hy4 flash < 2 h, bez danych do sprawdzenia); nasze czasy: FA83 ~27 h ściany / 62 min GPU, K-114 ~2 h / ~25 min GPU; reguła: znaczniki etapów w każdej kampanii, wiersz czasu w notatce; dopisane do K-119, K-120, skill-io-metodyka.

## [2026-11-18] telegram | adapter Qwen3.8-27B pod OpenCode (harness-hub, v2)
[[qwen38-27b-pi-adapter]]: bez myślenia dorównuje bazie z myśleniem xhigh przy 6–8 × mniej tokenów (SWE-bench Pro 31,8k → 3,9k; ~265 s → ~33 s dekodu przy 120 t/s); słabsza istotność niż pi (p = 0,057 / 0,38); skrypt TRL publiczny; K-120: miara tokeny i czas na zadanie.

## [2026-11-19] telegram | DaisyRose-27B (RadixArk, pełny RL na Qwen3.8-27B)
[[daisyrose-27b]]: 144 H200 × 18 dni ≈ 62k GPU-h; TB 4.1 5,6 → 12,0%, reszta +0,4…4 pp; drop-in GGUF; lekcja: celowany LoRA w jednym harnessie ma dużo lepszy stosunek zysku do kosztu; dopisany do K-120 (tokeny, czas, akceptacja MTP).

## [2026-11-19] telegram | Strata v0.2.16 (delta)
[[strata]]: własny silnik bez ggml na wszystkich platformach (te same tokeny); lekcja do [[skill-io-pulapki]]: błąd M1–M4 liczył 1/4 kolumn przy płynnym tekście (KL 0,303 → 0,0068), JIT Blackwell 173 → 0,34 s; nic dla 27B na XTX.

## [2026-11-19] telegram | blog „Quantization, finally explained” — wstęp dla laików, nic nowego

## [2026-11-19] telegram | TensorTonic llm-optimization-handbook — spis tematów z linkami, nic nowego

## [2026-11-19] zwiad | compwatch 2026-11-19
[[zwiad-2026-11-19]]: oMLX prefill z pomocnikiem (Qwen3.8-27B 64K 352 → 1879 t/s) → K-107c; TensorFold wiersze draftu parami (+24–29% Mac); Maya 1.1.67 (zegar iGPU = nasz keepawake); strix-llama.cpp: rejekcja przyjmowała drafty po EOG → K-123 (wysoki, przegląd kodu); ROCm 10.2 AITER na Radeonach.

## [2026-11-19] telegram | megakernel-zoo (agent pisze megakernel per model)
[[megakernel-zoo]]: Qwen3.8-27B B200 SGLang 9,52 → 8,44 ms (tor A, ~63 h agenta) → 7,17 (12-bit BF16, bitowo); ewaluator (FP64, ukryty zbiór, odwrócenie batcha, audyt) dopisany do [[skill-io-metodyka]]; audyt: pętla powtórzeń dawała fałszywe 0,415 ms/token; K-124 megakernel pętli draftu (najpierw NVIDIA).

## [2026-11-19] telegram | DNeo (drafter dyfuzyjny, Cerebras)
[[drafter-dflash]]: 1,3 × vs DFlash2 na Qwen3-4B/H100 (pamięć odrzuconych propozycji, MoFA); brak wag 27B i llama.cpp; u nas DFlash2 przegrywa z MTP (PL, T=1), więc bez testu; lekcja do douczania MTP.

## [2026-11-19] telegram | Helion (DSL kerneli PyTorch) — narzędzie do nauki/prototypów, nie do naszego silnika

## [2026-11-19] audyt | Gemini: całe repo KERNEL
[[audyt-gemini-2026-11-19]]: bezpieczeństwo prawdziwe i naprawione (gpu-guard exit 4, pgrep -f, 3 s SIGKILL; run-jobs bez strażnika; bramka transferu Vast, down.sh --all); naprawione też spec_sweep (pętle, md5), summ.py, run-llm/run-topka, profil Enigmy ROCm = topka-q70; 8 pomysłów było już odrzuconych, zyski zwykle 2–10× zawyżone; kolejka: K-004/K-116/K-118 poprawione, nowe K-125–K-128.

## [2026-11-19] kolejka | XTX: K-109, K-110, K-106 (GPU), K-111, K-123 (bez karty)
[[2026-11-19-k109-k110-k106-xtx]]: igły 3/3 przy 130k i 222k (PASS), bench.py skill-io c1 110,3 t/s, prefill 839/933, -np 1 bez blokady dekodu (B czeka +2,6 s); [[2026-11-19-k111-k123-krok-xtx]]: krok 27 ms = MMVQ weryf. 20,2 (86%) + draft 1,9 (≈ bajty) + małe kernele 3,5; EOG w rejekcji nie dotyczy produkcji. Strażnik GPU w kolejce działał (0 WARN), produkcja przywrócona, 0 faultów.

## [2026-11-19] telegram | topka kolejki + 5 linków
KOLEJKA: sekcja TOPKA (K-001, K-125, K-013, K-007→K-008, K-004, K-116) na górze Czeka. Linki: adapter Hermes (dopisany do [[qwen38-27b-pi-adapter]]), Kinetic (4,5× = powtórzona edycja), 2× B70 (1,3–1,5×), Speedy (Flash-Next, Q2_0), DNeo (już zrobione).

## [2026-11-19] telegram | TensorTonic handbook (powtórka) i lista materiałów do nauki (kipp.ly, FlashAttention, vLLM, SGLang) — nic nowego

## [2026-11-19] eksperyment | kolejka XTX: K-125 PASS (kvq KLD 0,004522 → 0,003862 vs standardowy kernel), K-001 bisekcja (pamięć, host, kvq odpadają)
[[2026-11-19-k125-k001-xtx]], [[lekcja-env-switch-domyslnie-wlaczony]]; K-123 poprawka gotowa w gałęzi k123-eog. Produkcja :8080 przywrócona, 0 błędów karty.

## [2026-11-19] vast | K-118/K-116a/K-127 na 4 kartach naraz (3090, 3060, 4080 SUPER, 5060 Ti), budżet $2
run3.sh (upstream llama-bench V(n), kvqleana vs kvqlean, ramię ~122k), fetch.sh zbiera i usuwa instancje. hostguard odrzucił 3090 (250/420 W) i 5070 (175/250 W).

## [2026-11-19] vast | K-118 wyniki: 3090 n4 86,6 t/s (+84% vs dolna granica), 4080 SUPER 107,3; K-116 odrzucone (draft ≈ bajty, weryfikacja V(5)/V(1) 1,26–1,64); K-127 bez różnicy; K-129 DRAFT_N=2 nowe
[[2026-11-19-k118-nvidia-pelna-moc]], [[lekcja-tlo-z-sesji-agenta-ginie]]. Wydane $1,11 z $2 (~$0,8 bezczynne instancje: fetch.sh zginął z sesją; launch.sh przechodzi na systemd-run).

## [2026-11-19] telegram | ROCm 10.2 (AMD): powtórka ze zwiadu; delta dopisana w ZRODLA, K-130 (A/B kompilatora, niski)

## [2026-11-19] vast | karty nigdy nie stoją: vast-reaper (timer systemd co 2 min: FINISHED/padnięty runner/GPU idle 10 min → wyniki, destroy, raport przez skrzynkę), onstart-guard na instancji, launch.sh bez timera nie wynajmuje; test na 2 × 3060 OK
[[lekcja-tlo-z-sesji-agenta-ginie]], AGENTS.md zasada z 2026-10-16 zaostrzona.

## [2026-11-19] telegram | Basalt v0.5.0: delta od v0.2.1 = model Hy4-flash (MoE, NVFP4, stratny KLD 0,201), nie Qwen; lekcje do K-008/K-111 w ZRODLA

## [2026-11-19] telegram | WavePP (arXiv 2609.35263): prefill PP4 na klastrze, ×2–2,9 przy ponownym użyciu prefiksu; lekcja do K-107

## [2026-11-19] telegram | KernelBench-CUDA Neon #2: lekcje (bramka top-k, PDL), bez nowego testu

## [2026-11-19] telegram | Maya v1.1.68: Hy4-Flash 220B (kwanty top-1 88,5–96,6%), bez liczb t/s; nie nasz model
