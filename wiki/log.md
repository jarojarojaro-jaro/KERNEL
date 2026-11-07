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
