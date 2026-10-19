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

## Powiązane
- [[index|Strona główna]]
- [[KONWENCJE]]
