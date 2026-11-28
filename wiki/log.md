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
Nowe: [[raport-09-chmura-3090]], [[raport-09-chmura-5060ti]], [[raport-09-chmura-3060]], [[testy/2026-10-16-mtp-pl-pilot]], [[2026-10-16-mtp-pl-pilot]], lekcje [[lekcja-fit-mtp-16gb]], [[lekcja-limit-cpu-kontenera]], [[lekcja-md5-wzgledem-upstreamu]], [[lekcja-mtp-glowica-optimum]], [[lekcja-nadpisanie-dzialajacego-skryptu]]. Przepisane z `do-sprawdzenia` na finalne: [[testy/2026-10-16-kampania-nvidia]], karty 3090/5060 Ti/3060, [[2026-10-16-kampania-nvidia]], [[saluki]], [[bonsai]]; uzupełnione m.in. [[nvfp4]], [[lfm2-5-24b-a2b]], [[glowica-mtp]], [[mmvq-n1-wiersze]], [[fuzje-lfm-moe]], [[latki-na-nvidia]], [[testy/2026-10-16-bit-exact]], [[lekcja-bit-exact-attention]]. Wydatki końcowe w [[karty/vast-ai]]. „Stan na dziś”: nic nie działa. Audyt: +998 liczb, 0 błędnych.

## [2026-10-16] ingest | Raporty 14 i 15a–15f
Nowe: [[testy/2026-10-16-nemotron-3090]], [[raport-15a-monokernel]], [[raport-15b-spekulacja-frontier]], [[raport-15c-nowe-silniki]], [[raport-15d-prefill-dlugi-kontekst]], [[raport-15e-kwantyzacja-nowa]], [[raport-15f-agentowa-nauka]] oraz notatki repo/modeli/lekcji/metod z ich sekcji „Do bazy wiedzy” (m.in. [[magnitude]], [[tqllm]], [[swift-1-5]], [[fabryka-v1]], [[zestaw-odlozony]]). Zaktualizowane m.in. [[testy/2026-10-16-kampania-nvidia]], [[fattn-kvq]], [[tensorfold]], [[ik-llama-cpp]], [[werdykt]], [[otwarte-decyzje-produktu]]. Audyt: 676 liczb, 0 błędnych.

## [2026-10-16] ingest | Raport 12 §13 (walidacja bit-exact) i 16c (kvq na CUDA)
Zaktualizowane: [[2026-10-16-bit-exact]] (run 4: PASS, prędkość na flagach produkcyjnych, regresja nowego drzewa ~5–6%), [[testy/2026-10-16-bit-exact]], [[fattn-kvq]], [[fa-kv-kwantyzowane-cuda]], [[raport-15d-prefill-dlugi-kontekst]] (korekta MTP@64k), [[narzedzia/skrypty-chmury]]. Nowe: [[2026-10-16-kvq-cuda]], [[testy/2026-10-16-kvq-cuda]], [[2026-10-16-kvq-cuda-zostaje]], [[lekcja-kld-szum-kolejnosci]], [[lekcja-vast-authorized-keys]], [[lekcja-pkill-wlasna-powloka]].

## [2026-10-16] ingest | Raport 16h (fabryka v1 zbudowana)
Nowe: [[fabryka-cli]], [[2026-10-16-backtest-regul-fabryki]], [[metody/fabryka-v1]]. Zaktualizowane: [[fabryka-v1]] (status aktualne), [[zestaw-odlozony]], [[pomiar-abba]], [[lekcja-label-to-nie-binarka]], [[lekcja-pdl-sm120]], [[seria-amd-opt]]. `log.md` zwolniony z limitu słów (dziennik), zmiana w `tools/wiki.py` i [[KONWENCJE]].

## [2026-10-16] ingest | Raporty 16d i 16i (Magnitude) + decyzja „badamy Magnitude”
Nowe: [[2026-10-16-magnitude-vs-fork]] (z danymi 9B na 5060 Ti), [[2026-10-16-magnitude-rozklad-wygranej]], [[testy/2026-10-16-magnitude-vs-fork]], [[raport-16i-magnitude]], [[ekosystem/magnitude]], [[kontroler-szerokosci-draftu]], [[sprzezone-probkowanie-draftu]], [[lekcja-sufit-bloku]], [[lekcja-drafter-gleboki-vs-mtp]], [[2026-10-16-badamy-magnitude]]. Zaktualizowane: [[magnitude]] (status aktualne), [[drafter-dflash]], [[mmvq-multikolumnowe]], [[produkt-ryzyka]], [[lekcja-limit-cpu-kontenera]], [[lekcja-pkill-wlasna-powloka]], [[zgodnosc-bitowa-md5]], [[2026-10-16-nemotron-3090]] (KLD PASS).

## [2026-10-16] update | Regresja nowego drzewa bit-exact naprawiona
[[2026-10-16-bit-exact]] i [[testy/2026-10-16-bit-exact]]: przyczyna `ce2105d32` (14 spilli VGPR), poprawka `02813c1c5`, tg128 43.15/43.16 = prod. Nowa lekcja [[lekcja-vgpr-limit-hak-spill]].

## [2026-10-16] update | Raport 12 §13 końcowy (`365af3e5e`) + lekcja o awarii omp
[[2026-10-16-bit-exact]] (run 4 końcowy: domyślnie = produkcja; bitexact MTP 0% krótki / −9% ~27k, plain −2.8%, pp5@32k −11%), [[testy/2026-10-16-bit-exact]], [[batch-invariant]], [[lekcja-bit-exact-attention]] (lista źródeł rozbieżności), [[otwarte-decyzje-produktu]] (opt-in „identyczne odpowiedzi” czeka na użytkownika). Nowa: [[lekcja-uslugi-poza-omp]].

## [2026-10-18] ingest | Raport 16e (kwanty 27B, KLD) + incydent danych + Salad
Nowe: [[2026-10-18-e1-kwanty-27b-kld]], [[testy/2026-10-18-e1-kwanty-27b-kld]], [[kld-po-polsku]], lekcje [[lekcja-unikalny-katalog-wynikow]], [[lekcja-build-przed-wynajmem]], [[lekcja-bootstrap-numpy]], [[lekcja-zabicie-skryptu-nie-serwera]], [[lekcja-limit-mocy-hosta]]. Zaktualizowane: [[swift-1-5]], [[rtx-3060]], [[rtx-5060-ti]], [[kwanty-gguf]], [[saluki]], [[bonsai]], [[raport-15e-kwantyzacja-nowa]], [[runpod]], [[raport-09-chmura-3060]] (dane nadpisane), [[lekcja-limit-cpu-kontenera]], [[lekcja-pkill-wlasna-powloka]], [[otwarte-decyzje-produktu]] (16 GB A3, 12 GB IQ3_XXS-mtp – rekomendacje, bez decyzji), [[salad]], [[karty/salad]], [[radeony-do-wynajecia]] (AMD w Salad niedostępne, brak XTX do wynajęcia).

## [2026-10-18] ingest | 16c §9, 16j, landing r6–r8, wentylator XTX i restart
16c §9: wyjątek kvq n=1 D256 q4_0 (`678473a27`) w [[fattn-kvq]], [[2026-10-16-kvq-cuda]], [[2026-10-16-kvq-cuda-zostaje]], [[bramka-kld-kanarki]], [[lekcja-kld-szum-kolejnosci]], [[testy/2026-10-16-kvq-cuda]]. 16j: nowe [[2026-10-18-magnitude-vulkan-xtx]], [[testy/2026-10-18-magnitude-vulkan-xtx]], [[lekcja-koszt-szerokosci-backendu]]; zaktualizowane [[magnitude]], [[ekosystem/magnitude]], [[produkt-ryzyka]], [[raport-16i-magnitude]], [[2026-10-16-badamy-magnitude]]. Landing: [[lekcja-hydration-blok-w-p]], [[landing-qa]], [[app-landing]]. Ops: [[rx-7900-xtx]] (overdrive, krzywa wentylatora, Vulkan bez sudo), [[lekcja-wentylator-rdna3]], [[lekcja-tmp-po-restarcie]] (`/tmp/bx*` utracone, oznaczone w `zrodlo` notatek bit-exact).

## [2026-10-18] update | Źródło bit-exact: raport 12 §13 kanoniczny
`/tmp/bx*` zniknęły przy restarcie ~18:53 UTC (przed archiwum); poprawione [[lekcja-tmp-po-restarcie]], `zrodlo` notatek bit-exact, [[AUDYT]].

## [2026-10-18] ingest | Raport 16g (pasmo MoE LFM)
Nowe: [[2026-10-18-lfm-moe-pasmo]], [[2026-10-18-lfm-moe-negatywne]], [[mmvq-moe-gate-up-blok]], [[att-gfx1100]], [[lekcja-sufit-wzorca]], [[lekcja-limit-mocy-285w]], [[testy/2026-10-18-lfm-moe-pasmo]]. Zaktualizowane: [[lfm2-5-24b-a2b]], [[lfm2-5-uncensored]], [[seria-amd-opt]] (kandydat 0071), [[otwarte-decyzje-produktu]] (scalenie 0071 – decyzja użytkownika), [[amdgpu-moc-i-termika]].

## [2026-10-18] ingest | Landing rundy 9–12
[[app-landing]] (rundy 9–12, źródło bit-exact = raport 12 §13 run 4, juror r9–r12, kontrole r12); nowe lekcje [[lekcja-juror-llm-plateau]], [[lekcja-timeline-scen-3s]].

## [2026-10-18] ingest | Raport 16a (PM4-PDL, prefetch MALL)
Nowe: [[2026-10-18-pm4-pdl-x1]], [[2026-10-18-pm4-ub-lfm]], [[lekcja-handoff-rdna3]], [[lekcja-prefetch-mall-xtx]], [[testy/2026-10-18-pm4-pdl-x1]]. Zaktualizowane: [[raport-15a-monokernel]] (korekta S1: +9…+15% → realnie ≈ +3%), [[pm4-replay]], [[wyniki-negatywne]].

## [2026-10-18] ingest | Raport 16f (szybkie zyski XTX) + wentylator za obciążeniem + Chrome
Nowe: [[2026-10-18-lfm-ubatch-2048]], [[lfm-czulosc-na-podzial-batcha]], [[2026-10-18-cache-promptu-agenta]], [[2026-10-18-hak-mtp-i-checkpointy]], [[cache-sesji-na-dysku]], [[raport-16f-xtx-szybkie]], lekcje [[lekcja-5-seedow]], [[lekcja-nie-odtwarzac-lockow]], [[lekcja-chrome-zostawiony]]. Zaktualizowane: [[latki-spekulacji]], [[wylaczniki-env]], [[2026-10-12-cache-promptu-i-a7]], [[raport-15d-prefill-dlugi-kontekst]], [[lekcja-unikalny-katalog-wynikow]], [[otwarte-decyzje-produktu]] (flagi `run-llm.sh` – decyzja użytkownika), [[rx-7900-xtx]] i [[lekcja-wentylator-rdna3]] (timer, reset GPU, tryb akustyczny).

## [2026-10-19] update | Wentylator XTX 100% przy pracy (decyzja użytkownika)
Nowa [[2026-10-19-wentylator-100-przy-pracy]]; zaktualizowane [[rx-7900-xtx]], [[lekcja-wentylator-rdna3]].

## [2026-10-19] ingest | 16k sprzężone próbkowanie + zasada bezpieczeństwa sprzętu
Nowe: [[2026-10-18-sprzezone-probkowanie-mtp]] (nierozstrzygnięte, nie domyślnie), [[gumbel-max]], [[lekcja-ustalony-seed-to-nie-powtorzenie]], [[testy/2026-10-18-sprzezone-probkowanie-mtp]], [[2026-10-19-bezpieczenstwo-sprzetu]], [[gpu-guard]], [[lekcja-agent-nie-patrzyl-na-temperatury]]. Zaktualizowane: [[sprzezone-probkowanie-draftu]], [[pm4-replay]] (page faulty SQC @0, raport 17 w toku), [[2026-10-16-badamy-magnitude]], [[raport-16i-magnitude]], [[rx-7900-xtx]].

## [2026-10-19] ingest | Raport 16b (ogon lookupu za MTP)
Nowe: [[2026-10-18-lookup-ogon]], [[2026-10-18-kontroler-szerokosci-zerowy]], [[koszt-szerokosci-weryfikacji]], [[zestaw-copy-mvs]], [[lekcja-ogon-zmienia-tekst-t1]], [[testy/2026-10-18-lookup-ogon]]. Zaktualizowane: [[lekcja-mtp-juz-kopiuje]], [[2026-10-16-lookup-kopiowalnosc]], [[kontroler-szerokosci-draftu]], [[raport-15b-spekulacja-frontier]], [[2026-10-16-badamy-magnitude]], [[raport-16i-magnitude]], [[otwarte-decyzje-produktu]] (włączenie w produkcji – decyzja użytkownika).

## [2026-10-19] ingest | Raport 17 (page faulty GPU, resety)
Nowe: [[2026-10-19-page-faulty-gpu-analiza]], [[testy/2026-10-19-page-faulty-gpu-analiza]], [[dekodowanie-page-fault-amdgpu]], [[kfd-smi-eventy]], lekcje [[lekcja-pm4-zamienia-fault-w-reset]], [[lekcja-timeout-tasmy-to-skutek]], [[lekcja-pgrep-f-lapie-powloki]]. Zaktualizowane: [[pm4-replay]], [[2026-10-18-sprzezone-probkowanie-mtp]], [[2026-10-19-bezpieczenstwo-sprzetu]]; korekty [[lekcja-nie-odtwarzac-lockow]] i [[lekcja-wentylator-rdna3]] (reset 23:25 nie z kolizji blokad); [[otwarte-decyzje-produktu]] (`GGML_HIP_PM4=0` – decyzja użytkownika).

## [2026-10-19] ingest | Strona rekordów + benchmarki przed → po
Nowe: [[REKORDY]] (najlepsze wyniki per karta/model/obciążenie/metryka z datą, warunkami, źródłem i statusem produkcji; zwolniona z limitu słów), [[benchmarki-przed-po-2026-10-19]]. Zasada „nowy rekord od razu na stronę rekordów” w [[KONWENCJE]] i `AGENTS.md`; link z [[index]].

## [2026-10-19] ingest | Raport 20 (build topka) + zero-RPM
Nowa [[2026-10-19-build-topka]]; [[REKORDY]]: Uncensored code-edit 414.8 t/s (nowa para), Qwen topka 396.9 t/s obok rekordu 400.9; [[galezie-rund]], [[lekcja-wentylator-rdna3]] i [[gpu-guard]] (fałszywy alarm zero-RPM, próg 80/82 °C).

## [2026-10-19] ingest | Raport 17 §9 (przyczyna PM4: PRIV=1 na GFX11 + ewikcje SVM)
Nowe: [[2026-10-19-pm4-priv-analiza]], [[gfx11-pm4-dispatch-priv]], [[hip-kopie-stronicowane-zostawiaja-svm]], [[kfd-ewikcja-kolejek-gfx11]], [[lekcja-wlasny-pm4-musi-robic-to-co-firmware]], [[lekcja-test-wywlaszczenia]]. Zaktualizowane: [[kfd-smi-eventy]], [[pm4-replay]], [[testy/2026-10-19-page-faulty-gpu-analiza]], [[2026-10-19-page-faulty-gpu-analiza]], [[otwarte-decyzje-produktu]] (testy S1–S6 – decyzja użytkownika).

## [2026-10-19] ingest | Raport 21c (Copy-Paste LM)
Nowe: [[raport-21c-cplm]], [[lekcja-lm-head-bottleneck]], [[2026-10-19-sufit-pointera-lookup]], [[2026-10-19-tokeny-spoza-slownika-draftu]], [[agr-lookup-zgodny-z-mtp]]; zaktualizowany [[testy/2026-10-18-lookup-ogon]].

## [2026-10-19] ingest | Raport 21h (Terminal-RSI) + podział otwartych decyzji
Nowe: [[raport-21h-rsi]], [[rsr-27b]], [[tencent-terminal-rsi]], [[lekcja-verified-to-nie-poprawny]], [[petla-rsi-f]], [[KOLEJKA-TESTOW]], [[KOLEJKA-TESTOW]], [[otwarte-decyzje-techniczne]] (wydzielone z [[otwarte-decyzje-produktu]]: flagi, łatki, testy GPU, wydatki; nowe wiersze P0/P1 i E1). Zaktualizowany [[zestaw-odlozony]].

## [2026-10-19] ingest | Raport 18 (następna fala)
Nowe: [[raport-18-nastepna-fala]], [[2026-10-19-workload-omp]], [[model-kosztu-weryfikacji-moe]], [[2026-10-19-certyfikowana-glowica-pilot]], [[lekcja-rzadkosc-vs-weryfikacja]], [[knlp-lm-head]], [[mtplx]], [[suffixdecoding]]. Zaktualizowane: [[qwen3-8-27b]], [[lfm2-5-24b-a2b]], [[lekcja-prefetch-mall-xtx]].

## [2026-10-19] ingest | Raport 21a (DSpine)
Nowe: [[drafter-dspine]], [[raport-21a-dspine]], [[lekcja-akceptacja-h100-nie-przenosi-sie]], [[lekcja-naglowki-drafterow]]; zaktualizowany [[drafter-dflash]].

## [2026-10-19] ingest | Raport 21b (zasoby GPU perf, Blackwell TG)
Nowe: [[raport-21b-gpu-perf-zasoby]], [[wafer-gpu-perf-lista]], [[projekcja-rtx-5090]], [[karty-nvidia-parametry]], [[pdl-mmvq-trigger]], [[mmvq-prefetch-l2]], [[l2-persist]], [[trwala-siatka-bez-pm4]], [[lekcja-littles-law-gemv]], [[physics-floor-check]]; zaktualizowany [[sm-86-89-120]].

## [2026-10-19] ingest | Raport 21f (InferenceX / AgentX, Kimi K3)
Nowe: [[raport-21f-inferencex]], [[ksztalt-ruchu-agentowego]], [[lekcja-agent-prefill-nie-decode]], [[agentx-harness]], [[research/raport-21f-inferencex]], [[vllm-kimi-k3-specialized-decode]], [[single-neuron-safety-2605-08513]] (link użytkownika dotyczy innej pracy).

## [2026-10-19] ingest | Raport 21d (KV na dysku)
Nowe: [[raport-21d-kv-na-dysku]], [[decyzje/2026-10-19-kv-tylko-w-ram]], [[dysk-serwera-pm9b1]], [[lekcja-restore-stanu-exactness]]; zaktualizowane [[cache-sesji-na-dysku]], [[strata]].

## [2026-10-19] ingest | Raport 21e (KV między modelami, Uncensored = ablacja)
Nowe: [[raport-21e-kv-miedzy-modelami]], [[uncensored-ablacja-kierunku]], [[przelaczanie-main-uncensored]], [[pamiec-stanu-gdn]]; zaktualizowane [[qwen3-8-27b-uncensored]], [[lfm2-5-uncensored]], [[otwarte-decyzje-techniczne]] (źródło wektorów – decyzja użytkownika).

## [2026-10-19] update | Decyzja: KV tylko w RAM
Nowa [[2026-10-19-kv-tylko-w-ram]]; [[decyzje/2026-10-19-kv-tylko-w-ram]] → nieaktualne (analiza bez wdrożenia); linki w [[raport-21d-kv-na-dysku]], [[cache-sesji-na-dysku]], [[dysk-serwera-pm9b1]], [[otwarte-decyzje-techniczne]].

## [2026-10-19] ingest | Raport 21k (smokinggun)
Nowa [[smokinggun]]: skaner CPU + porównanie benchmarków, nie stosuje się; fabryka v1 robi gate lepiej.

## [2026-10-19] ingest | Narzędzie kb (raport 19)
Nowa [[kb]]: `kb search` / `kb facts` (BM25F + e5-small + indeks faktów, cały `~/KERNEL`, `plik:linia`), recall@5 0.963 na 80 pytaniach (`wiki.py` 0.750); [[wiki-py]] `search` deleguje do `kb`; `AGENTS.md`: najpierw `kb`. Raport `product/research/19-kb-wyszukiwanie.md`.

## [2026-10-19] ingest | Raport 21g (nowe silniki)
Nowe: [[raport-21g-nowe-silniki]], [[inferrous]], [[project-maya]], [[bariera-lds-rdna3]], [[lekcja-bit-exact-wobec-siebie]], [[llama-moe-cache-mib]]; zaktualizowane [[tensorfold]] (1.1.0, Beta 7/8), [[strata]] (v0.1.44.1–v0.1.45), [[produkt-ryzyka]].

## [2026-10-19] ingest | Raport 23a (rea) + uzupełnienie raportu 19 (kb)
Nowe: [[raport-23a-rea]], [[hip-fatbin-extract]], [[narzedzia/kb]], [[najpierw-baza-kb]], [[lekcja-markdown-puste-linie]]; zaktualizowane [[kb]].

## [2026-10-19] ingest | Raport 21i (RSI-Inference Bench)
Nowe: [[raport-21i-rsi-inference-bench]], [[zmiany-fabryki-z-21i]], [[aob-v1]], [[lekcja-regula-tylko-w-prompcie]]; zaktualizowana [[petla-rsi-f]].

## [2026-10-19] ingest | Raport 21j (flameox)
Nowe: [[ekosystem/flameox]], [[flameox]], [[lekcja-bootstrap-male-n]], [[dowod-z-profilu]]; zaktualizowane [[fabryka-cli]], [[rocprof]], [[petla-rsi-f]], [[produkt-architektura]].

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
[[2026-11-07-kampania-nvidia-vast]] (sekcja 67c), nowa [[final-recipes-nvidia]]: walidacja picków Enigmy wszystkie PASS (5090 102,19, 4090 76,44, 3090 61,49 t/s); fork+kvq+lean na 4090 262 144 **101,27 t/s**; lean MTP n2 na 16 GB 217–229k (5080 81,62); prism Bonsai 4070 94,81; LFM 4070 w VRAM 179,3; pin b11856 zostaje (5090 ABBA). Aktualizacje: [[REKORDY]], [[KOLEJKA-TESTOW]] (A1/A5/A6/A7/A11/A13, B1–B4, B14, D1/D3/D4, E2), [[rtx-3060]], [[rtx-3090]], [[rtx-4060-ti]], [[rtx-5060-ti]], [[inne-karty-nvidia]], [[final-modele-per-vram]].

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

## [2026-11-19] telegram | QuixiInfer: DeepSeek 284B IQ2 na 5090 (26–32 t/s), drafty z korpusu między żądaniami (znane: SuffixDecoding) + lekcja o prywatności

## [2026-11-20] telegram | TensorFold v1.3.0: cp.async +24% GLM NVFP4 na sm_120; HIP bez gfx1100; K-131 (MMVQ 3090 58% pasma)

## [2026-11-20] telegram | Linux 7.2 a LLM: [[telegram-2026-11-20-linux-7-2-pamiec]], K-132

## [2026-11-20] test | Enigma Turbo (silnik Gemini 4 Neon z agy): bełkot i 0,7 t/s na Qwen3.5-0.8B vs llama.cpp „Paris…” 60,9 t/s; kod GPU niewywoływany
[[enigma-turbo-gemini-2026-11-20]]

## [2026-11-20] silnik | Enigma Turbo w parze z Gemini 4 Argon: gate vs llama.cpp, forward_ref (top-1 5/6, greedy 51/88, było 0); Gemini robi tokenizer
[[enigma-turbo-gemini-2026-11-20]]

## [2026-11-20] silnik | Enigma Turbo: HIP forward na XTX, gate PASS na produkcyjnym Qwen3.8-27B, dekod 3,96 → 28,20 t/s (llama.cpp 42,16); run-jobs odmawia pustej listy (incydent :8080 12 min)
[[enigma-turbo-gemini-2026-11-20]]

## [2026-11-20] silnik | Enigma Turbo 27B na XTX: graf HIP (+2%), GEMV int8 + sudot4 → 35,35 t/s (84% llama.cpp 42,16), gate PASS

## [2026-11-20] silnik | Enigma Turbo pętla: 27B 35,35 → 43,55 t/s (llama.cpp plain 42,16, +3,3%), gate PASS w każdym kroku; Q6_K 224 B odrzucone

## [2026-11-20] zwiad | [[zwiad-2026-11-20]]: ik_llama restore w hybrydzie (u nas brak, K-001 odpada), oMLX weryfikacja kilku wierszy, TRT-LLM 1.3

## [2026-11-20] silnik | Enigma Turbo: MTP na XTX, bezstratnie, 27B 43,9 → 67,0 t/s (+52,6%, K=2); prefill 219 t/s; serwer --gpu działa

## [2026-11-20] silnik | Enigma Turbo serwer lookup+MTP: kod do 188 t/s (×4,57), odpowiedzi 74–86 t/s, bit w bit; Argon bez limitu → Neon

## [2026-11-20] silnik | Enigma Turbo pętla: k_gdn_norm (dekod 43,78 → 44,26, spec 72,27 → 73,59 t/s), rozkład kroku spec (weryfikacja 90%), lekcja: akceptacja ≠ identyczność

## [2026-11-20] silnik | Enigma Turbo pętla: ping-pong stanu GDN (spec 74,4 → 77,7 t/s, +4,3%), fuzja swiglu +0,8%, słownik draftu 64k optimum; serwer kod 192 t/s

## [2026-11-20] silnik | Enigma Turbo pętla: atencja fala-na-klucz (+11,4% przy 1024 tok.), argmax na karcie (+1,3% spec), 2 próby odrzucone (norma w epilogu −7%, K-split szum)

## [2026-11-20] silnik | Enigma Turbo: prefill int8 WMMA 254 → 590 t/s (+132%), serwer Gemini r5 ×3,38 vs no-spec (Q2 76 → 168 t/s), błąd wiersza ukrytego złapany przez Gemini

## [2026-11-20] silnik | Enigma Turbo prefill: 590 → 623 t/s (LDS GEMM, MTP store w kawałku 64, trik 0x4B400000); spec 1024 tok. 97,5 t/s

## [2026-11-20] silnik | Enigma Turbo: flash-decoding (dekod przy 3800 tok. 39,1 → 44,1 t/s, +12,8%), weryfikacja R=1 dla N=2..5 (+1,3% spec), K sweep 2..5

## [2026-11-20] silnik | Enigma Turbo: sprzężony Gumbel-max T>0 (Gemini r6 + karta) 72,6 → 82,0 t/s bit w bit; atencja prefillu GQA +4,7% przy 3800 tok.; norma w prologu GEMV odrzucona (−43%)

## [2026-11-20] silnik | Enigma Turbo: flash-attention prefillu WMMA f16 (8k prompt 504 → 585 t/s); porównanie z produkcją topka-q70: kopie kodu +7/+19%, długie prompty dekod −41..−46%, prefill −30..−37%

## [2026-11-20] silnik | Enigma Turbo: GEMM f16 WMMA odrzucony (−31%), weryfikacja 16 na GEMV odłożona (59 ms vs 32 ms przy 8), lekcja: dokładność bit w bit a szerokość weryfikacji

## [2026-11-20] silnik | Enigma Turbo: cache prefiksu w rozmowie (Gemini r7) TTFT ×34 przy 2k; KV F16 (−50% pamięci, +1,5% dekodu przy 8k); słownik draftu 64k potwierdzony

## [2026-11-20] silnik | Enigma Turbo: prefill Q8_K odrzucony (−19%), prefetch w GDN +1%, accept jako graf bez zysku; Gemini r8 przerwany limitem (kontynuacja 13:26)

## [2026-11-20] silnik | Enigma Turbo: GEMM prefillu w optimum lokalnym (~632 t/s, 8 wariantów kafli), norma uproszczona; draft Q4_K napisany, pomiar wstrzymany (jaroserverai offline od ~19:22)

## [2026-11-20] silnik | Enigma Turbo: prefill przez MMQ z produkcji + kawałki 1024 (2k 624 → 844 t/s, +35%); weryfikacja 16 tokenów bit w bit (k_gemv_wide); ogon lookupu Gemini r8 ×1,55 na kopiach; draft Q4_K +1,4%

## [2026-11-20] research | 20 silników (6 agentów, 13 min): język zostaje C++/HIP; ranking 13 dźwigni dla Enigma Turbo — attention weryfikacji GQA (długie prompty), ogon W=16, chunk GDN prefillu, taśma PM4; notatka [[silniki-inferencji-2026-11-20]]

## [2026-11-20] silnik | Enigma Turbo: ogon lookupu W=16 +24% na kopiach; uczciwe porównanie bez myślenia — produkcja prowadzi w spekulacji (kopie 270–306 vs 200–242 t/s), Turbo tylko w zwykłym dekodzie; odrzucone k_attn_wg (−4%) i kolumnowy GDN prefillu (−4%)

## [2026-11-20] silnik | Enigma Turbo: szeroka weryfikacja 2 kafle wierszy na falę — 16 tokenów 51,2 → 48,2 ms, kopie 275,9 → 289,8 t/s (+5%); 3 warianty odrzucone (LDS −17%, zamiana ról −7%, 4 kafle −33%)

## [2026-11-20] silnik | Enigma Turbo: taśma PM4 z produkcji — dekod 45,4 → 47,5 t/s, spec +6,2%, bit w bit; accept() 0,84 → 0,34 ms; p_min 0 (długie +6%); luka do produkcji: długie 2k 103,8 vs 107,3, kopie 265 vs 306

## [2026-11-20] silnik | Enigma Turbo odłożony (właściciel); duet Kernel + Gemini Argon High optymalizuje produkcyjną llama.cpp — dźwignia 1: GEMV Turbo w MMVQ (20,4 → 18,9 ms/token)

## [2026-11-20] research | Inkling 2 Mini (Thinking Machines): MoE z pętlą warstw, jakość ≈ Qwen3.8-27B (AA 20,1) przy ~3,3 GB odczytu na token; mainline llama.cpp ma inkling2, topka nie; K-133 [[inkling-2-mini]]

## [2026-11-21] stan nocy | duet: r9 V5 odrzucony (−7% e2e), r10 FA_NATIVE_Q4 0% prędkości (KLD PASS); 7 testów kolejki (K-048 odrzucone, K-031 0,4–0,8%, K-053 mediana 141 t/s, K-054 low zostaje, K-044 25 łatek); Inkling: pliki unsloth XL nie ładują się w PR #32695 (734 vs 714 tensorów) → build mastera; AtomicChat AD dociągany; 3090 Vast przepadła bez wyników

## [2026-11-21] zwiad | vLLM Inkling day-0 (fuzje pętli, GB200 3,85 ms/krok) → notatka inkling-2-mini; LocalMaxxing XTX Inkling 33,9 t/s; FlashInfer ROCm tylko CDNA; Strata/Maya/TensorFold/oMLX delta

## [2026-11-21] Inkling XTX pierwszy pomiar | AD-Q4_K tg64 26,9 t/s (stock), INK_FUSE +14,5%, PM4 odrzucone (rocBLAS), DSpark słownik 200058≠201024; K-133 wynik

## [2026-11-21] Inkling r3 | FUSE+FUSE2 tg64 26,85→37,31 (+39%), KLD 0,0024; XL ładuje się, 28,6→39,7

## [2026-11-21] Inkling r4 | PM4 tape 3925 dispatchy (NOBLAS), tg64 37,35→43,0 (+15%), od stocku +60%; DSpark markov_w2 regres

## [2026-11-21] Inkling r5 | FUSE3 58,0 t/s (+37%) ale KLD 4,68 / PPL ×114 → zepsute, wyłączone; lekcja: każde sklejenie przez bramkę KLD

## [2026-11-21] Inkling r6 | czat 49,5 t/s stabilnie (+85% od stocku); DSpark działa, akceptacja 0,83/0,55, ale wolniejszy (taśmy odrzucone, 170 ms na graf); Gemini bez kwoty do ~11:20, Kernel sam bisekcja FUSE3

## [2026-11-21] Inkling diag | DSpark n7 bez PM4: kopie 85, long 67,7, T=0,7 26,4 t/s; PM4 odrzuca weryfikację (FA tile scratch); FUSE3 błąd w pakowaniu QKV (bisekcja b3/b4)

## [2026-11-21] Telegram | @HealthRanger „ROCm 10.2 daje 2,2×” — bzdura (brak bazy, karty, silnika; dotyczy wielu równoległych zapytań, AMD sam nazywa 10.2 wydaniem stabilizacyjnym); znane, K-130 zostaje

## [2026-11-22] panel | Strata 0.2.18: silnik Hy4-Flash (220B MoE, offload RAM/SSD), bez nowości dla Qwen3.8-27B/Inkling na XTX; wiersz ZRODLA

## [2026-11-22] panel | Cerebras+AMD dezagregacja prefill (Instinct) / dekod (CS-3), 5× tokenów/MW; lekcja zapisana, nie do testu u nas

## [2026-11-22] STOP + zwiad | stop na polecenie: bramka Inkling r8/r9 nieuruchomiona (build gotowy), duet r13 przerwany; zwiad: Maya 1.1.73 Inkling na XTX 93,6 t/s bez spec (1,9× nasze) → K-134; 3090 vLLM DSpark 290,8

## [2026-11-22] porządki | polecenie JARO: narzędzia porządków (czesci/porzadki/plan/tabele), porządek (373 przeniesionych, 37 scalonych, 10 w archiwum, w tym limit-mocy-odlozony i budzety-chmury), pola tabel (421 wyników, 89 technik → najlepsze-wyniki, bilans-optymalizacji), notatki jaroserverai/google-colab/rtx-4080-super/qwen3-5-9b, „Najważniejsze” w 13 hubach, 5 nieaktualnych poprawionych, KONWENCJE z czesci.py; ocena hit@5/MRR przed 0,912/0,785 i 0,864/0,731 → po 0,941/0,753 i 0,909/0,765

## [2026-11-23] Telegram | Strata 0.2.20: strata-inkling z paczką hip-rx7900, UD-Q4_K_XL wprost, DSpark W=4 (5090 250,3 t/s, deklaracja); dopisane do K-134

## [2026-11-23] Telegram | colibri 2.2: Inkling-Mini z GGUF (Vulkan/CUDA), 7× dotyczy Flash-Next z offloadem; AMD tylko Vulkan, bez liczb XTX; nie do testu teraz

## [2026-11-23] Telegram | Vocab Surgery (Pliny): zdjęcie odmów edycją 17 wierszy embeddingu/lm_head → notatka llm/vocab-surgery (do sprawdzenia: detektor słów kluczowych)

## [2026-11-23] Telegram | RightNow AI kernele Inkling 2 Small na B300 (5,1× GEMM eksperta, bitowo niezmienne 1 vs 64 wiersze) → research/rightnow-inkling-b300-kernele; lekcja: podział K przy n=1 dla MMVQ-ID na XTX

## [2026-11-23] Telegram | lista 425 dostawców inferencji (Jaber) zapisana: ekosystem/lista-dostawcow-inferencji + CSV/XLSX

## [2026-11-23] Telegram | SAGE-REXL3 (EXL3) kwanty Inkling: tylko CUDA, inna referencja porównania, zmiana kwantu — nie dla XTX

## [2026-11-23] Telegram | tokenizacja vLLM 120× (Elixir/Rust/toks): zysk dla serwerów Pythona; u nas tokenizacja już równoległa (raport 42); pomysł: cache segmentów rozmowy

## [2026-11-23] Telegram | TensorFold 1.3.4: Qwen 27B + DFlash2 na HIP, koszt draftu mierzony przy starcie; bez liczb XTX

## [2026-11-23] Telegram | Maya 1.1.74: Inkling Windows/2 GPU/1M ctx/wiele czatów; K-134 mierzy Mayę na XTX

## [2026-11-23] Telegram | 4 lektury o dekodzie → metody/lektury-dekod-podstawy (wszystko już w użyciu)

## [2026-11-23] Telegram | YuvrajInfer: ogólna hierarchia optymalizacji bez liczb — znane; Inkling to kontrprzykład (narzut kerneli > bajty)

## [2026-11-23] Inkling r8/r9 na XTX | rekord DSpark kopie 91,2 t/s (+7,8% FUSE3), long 2k 73,4; FUSE3 KLD 0,0022; MEGA −33% odrzucony; PM4 z DSpark −25%; OOM przy 32k

## [2026-11-23] K-134 | Strata 0.1.66 na XTX z DSpark: kopie 100,6–109,6, T=0,7 60,6 t/s (nasz 91,2 / 26,8); page fault przy L2048 → stop, Maya nie mierzona

## [2026-11-23] Telegram | aci-cpp (Actual): fork llama.cpp bez AMD, +do 28% vs v1.0.0; nasz topka ×3,21 vs upstream

## [2026-11-23] Telegram | XeFlash Arc B60: 400 t/s to kopiowanie kodu; README 22,4 plain / 61,8 MTP / 86,6 bdraft2

## [2026-11-23] K-134 | Maya 1.1.73 na XTX: kopie 112,7, T=0,7 80,7, long 2k 80,0, prefill 1911 t/s (bez naszego DSpark) vs nasz 91,2 / 26,8 / 73,4 — Maya wzorem

## [2026-11-23] Telegram | Multi-Branch Transformer (2611.19800): architektura do treningu, bez wdrożenia w silniku

## [2026-11-23] K-134 | Maya: AtomicChat Q4_K nieobsługiwany; unsloth drafting on kopie 111,6 / T=0,7 80,6 / long 77,8 (auto: 80 / 82 / 78); Maya jako czat na :18796

## [2026-11-23] Maya + ablacja AtomicChat | Inkling bez cenzury na Mayi: kopie 102,9, T=0,7 77,9, long 2k 76,1 t/s (nasz llama.cpp: 91,2 / 26,8 / 73,4); odmowy 7/8 → 0/8; czat :18796

## [2026-11-23] Telegram | Inkling-2-Mini 10,04× na KernelBench-Mega (agent kernelowy, #1 Gemini Neon); r10 kontroler spekulacji w bramce; r11 port Mayi zlecony

## [2026-11-23] Inkling r10 | kontroler spekulacji: T=0,7 +34% (35,9), kopie +6% z ngram, długi −27%; ub2048 OOM

## [2026-11-23] Maya KV q4 | IK2_KV=q4: PPL +0,92%, KLD 0,024, kopie 101,2 / T=0,7 77,3 / long 74,8 t/s (f16: 102,3 / 78,4 / 76,3), 262k ctx mieści się; wdrożone na :18796

## [2026-11-23] Inkling r11 | KV q4_0 rekord kopie 95,2; FUSE4 −14%, PLANAR KLD 0,008 (błąd), all psuje DSpark → r12

## [2026-11-23] Maya + oficjalny drafter na XTX | czat Q1–Q3 do 93 t/s, kopie 131,8, ale T=0,7 −15%; :18796 bez draftera; 3090 128 t/s vs XTX 82 → eksperci HIP

## [2026-11-23] Maya HIP | IK2_HIP_MVF16+EXPV: czat T=0,7 77,1 → 91,3, długi 2k 74,9 → 86,4 t/s (+15–18%, bit w bit); wdrożone :18796

## [2026-11-23] Inkling r12 | llama.cpp: KLD 0, tg +7,6%, DSpark z all nadal 0/413 → r13; produkcja = Maya

## [2026-11-23] Maya HIP runda 2 | czat T=0,7 94,5, długi 2k 93,5 t/s (bit w bit); do 100 brak ~0,6 ms/token

## [2026-11-23] koniec sesji | Maya :18796 bez draftera (T=0,7 94,5 / długi 93,5 t/s); z drafterem kopie 141, krótkie ~100, T=0,7 79; jaroserverai wyłączony na polecenie JARO

## [2026-11-23] zwiad | vllm-redshift (R9700 Inkling 88–104 t/s, GPU_MAX_HW_QUEUES=2 → K-135); QEngine 275 t/s to 3×3090 TP INT4 (1 karta 102,9); oMLX 0.8.3; r13 czeka na włączenie serwera

## [2026-11-23] K-135 | GPU_MAX_HW_QUEUES=2 na XTX z Mayą: 0% (94,5 → 94,5), odrzucone

## [2026-11-23] Inkling r13 | llama.cpp: tg +15%, DSpark naprawiony, L8k +21%; T=0,7 nadal 28 → r14

## [2026-11-23] Maya HIP runda 3 | nietemporalne odczyty wag: czat T=0,7 104,3, długi 2k 100,8 t/s (>100, bit w bit)

## [2026-11-23] duet | bisekcja prefillu K-001: 5ff6a15 −1,8%, 0bb43ee −1,5% (razem −3,9%); bank GDN bez wpływu

## [2026-11-23] K-005 | siatka checkpointów: wznowienie po edycji 40k 74,1 → 19,4 s (−74%), md5 równe

## [2026-11-23] koniec testów | Maya >100 t/s (T=0,7 104,3), K-135 0%, r13/r14 llama.cpp (tg +17%, narzut serwera 7,8 ms/token → r15), bisekcja K-001, K-005 −74%; jaroserverai wyłączony

## [2026-11-23] Maya v1.1.75 (link JARO) + AtomicChat natywnie | hipx14 przeniesione na 1.1.75 (88b6a6c, STRATA_USE_HIP→MAYA_USE_HIP), kernele Q4_K/Q5_0 (30ff426, test hosta = ggml bit w bit); XTX czeka: K-136, K-137

## [2026-11-23] Unsloth Inkling 1,9× (link JARO) | fuzje ggml-cuda, PRO 6000 81 → 125 t/s bez spekulacji; ~2× mniej wydajne na bajt niż Maya; K-138 (prebuild gfx110X na XTX)

## [2026-11-24] K-138 Unsloth na XTX + ingine (link JARO) | tg128 Unsloth 40,9 vs nasz 58,2; serwer DSpark T=0,7 31,1 vs 23,6 (nasz narzut serwera); ingine 5090 487–561 t/s → wzór: synchronizacja raz na rundę; wyścig Kernel vs Gemini na Mai (gałęzie kern-s1..s4, gem-maya)

## [2026-11-24] K-137 AtomicChat natywnie w Mai: T=0,7 104,3 → 113,2 (+8,6%), wdrożone do mayaserve; K-136 Maya 1.1.75 = produkcja (drafter nadal przegrywa: 94,8); r15 +1–3% i błąd ctl; wyścig Kernel vs Gemini

## [2026-11-24] Wyścig Maya runda 1 Kernela | 16 przełączników IK2_K_*, T=0,7 112,9 → 113,6 (szum); −22% uruchomień bez zysku (lekcja); Gemini zablokowany limitem do 07:41, wznowienie timerem agy-retry-0724

## [2026-11-24] weaponized-curiosity (link JARO) | skill procesu badań (debata 4 agentów, autoresearch z zamrożonym ewaluatorem); bez liczb dla kerneli; wniosek: przewidywanie liczbowe + walidacja w każdej próbie wyścigu

## [2026-11-24] KVCompress (link JARO) | prototyp bez pomiarów jakości i prędkości; lekcja: rotacja Hadamarda przed KV q4

## [2026-11-24] Inference Stack (link JARO) | vLLM+llm-d+LiteLLM+Grafana w jednym instalatorze, tylko NVIDIA, bez liczb; dla nas wzór produktu, nie prędkość

## [2026-11-24] Przegląd ZRODLA pod nowy cel (cała inferencja + nauka) | 151 wpisów (55 ocen „nie dla nas/zero/bzdura”, 106 o serwowaniu/infra/produkcie/agentach): 108 zmienionych, 43 sprawdzone bez zmian; ~70 notatek z sekcją „Przegląd 2026-11-24”, nowe: inference-stack, ashhart-skills-infra, vllm, superfluid, ingine, lemonade, speed-bench, kekzl-imp, vllm-radiance-mxfp4, anatomia-serwowania-kumar, b70-cookbook, speedy, vllm-v060-narzut-cpu, nanbeige4-3-33b, weaponized-curiosity; decyzja 2026-11-24-cel-cala-inferencja-i-nauka

## [2026-11-24] Zwiad 2026-11-24 | 34 wiersze ZRODLA; konkurenci Inkling na XTX (GodGMN 115,7 przy T=0,7 vs nasze 113,2, inna maszyna; Victor 106), R9700 144,6 z DSpark na code-v1 T=0 (na bajt dekodu równo z nami, wygrywa okno), Maya 1.1.77 DPP, upstream llama.cpp przyjął replay GDN (nasze S4 z 10-13), kv4-hopper; notatki ekonomia-okna-weryfikacji, kv4-hopper, mori-umbp; K-141..K-144; wyścig: Gemini runda 1 nvcc OK, bez testów, prognoza 135–155 bez podstaw, K-140

## [2026-11-24] Gemini maya-g2 i ink-r16b padły na limicie (429, reset ~14:13); wznowienie timerem agy-retry-1420 (maya 14:30, ink godzinę później)

## [2026-11-24] llama.cpp #31669 replay GDN (link JARO) | nasze S4 z 10-13 upstream; topka bez zmian; Enigma: podbić upstream b11856 → ≥ b12671 i model pamięci (−0,55 GiB stanu przy n4, wiele slotów tanie)

## [2026-11-24] tools/kol: kolejka GPU jednym poleceniem (stan, pusc --czekaj, czekaj, wynik) — zlecenie JARO o oszczędności tokenów

## [2026-11-24] kolejka | 103 pozycje na polecenie JARO: przegląd, 20 testów na XTX i Colabie, 2 wdrożenia
Przegląd [[przeglad-kolejki-2026-11-24]], Colab [[colab-kolejka-2026-11-24]]. Wdrożone w Mai: DPP (K-142, T=0,7 +0,75%, bit w bit) i okno sufiksowe 128 (K-147, przepisywanie ×3,7, edycja ×2,7, czat bez zmian). Odrzucone: ROCm 10.1 (K-049, prefill −1,7%), ROCm 10.2 (K-130, bez zysku), HRX (K-052, ≥6× wolniej), lazy ctx (K-145, +2% tylko z drafterem), drafter tylko greedy (K-146, T=0,7 −1,7%). Wiedza: nasz stos +4…8% nad GodGMN na tej samej karcie (K-141); DFlash2 bije MTP dla Orci na XTX (K-074, +35%); fork CUDA bez sm_75 (K-069); regresja prefillu CUDA to stara baza (K-023). Przeniesione: 40 do Zrobione, 8 do Odrzucone. Czeka na JARO: K-060 (potwierdzenie faultu z 23.11 w fabryce) i decyzje z przeglądu.

## [2026-11-25] Bonsai 2.5 27B Uncensored (link JARO): pobrany, przepakowany bez strat do Q2_0 + MTP, na XTX T=0,7 77,7 t/s
[[bonsai-2-5-uncensored]]: fork PrismML na gfx1100, 13 wariantów xbench; najlepiej prism Q2_0 + MTP n2 (T=0,7 77,7, greedy 117,9, z ngram-mod 188,4); PTQ1_0 na HIP liczy zamiast czytać (MTP 33,8). Nowe K-149 (kernel PTQ1_0 RDNA3), K-150 (przerwa hosta 19%), K-151 (port Hadamarda do topki); K-152 zrobione.

## [2026-11-25] Bonsai 2.5 Uncensored: 262k, 4 nowe łatki topki; Nib, straggler-finder, Doğukan (linki JARO)
[[bonsai-2-5-uncensored]]: prism 77,7 → topka-k157 116,9 t/s przy T=0,7 (+50%), edycja kodu 174 → 446 t/s, bez spekulacji 54,9 → 76,9; łatki K-150T i K-157 (Gemini), K-154 i K-156 (agent), K-155 (Kernel); KLD 0,000000 do bazowego portu. Cel 200 t/s osiągnięty dla edycji kodu i greedy (Q4 279), nie dla czatu T=0,7. [[nib-chromadera]]: Nib szybszy od Mai (T=0,7 130–151 vs 112,5) dzięki tańszemu DSparkowi → K-158. [[gpu-straggler-finder]]: statystyka p90 okien do A/B i bramki Vast. Doğukan 3060 74 t/s: jego konfiguracja na XTX 39,8 (prism) → 121,9 (topka).

## [2026-11-25] Jak zrobiono Nib i nasz „level wyżej” (polecenie JARO)
[[metoda-nib-level-up]]: Nib = dyscyplina procesu (Step N z pomiarem przy każdej fladze, księga µs/token, warianty w runtime, selftest/oracle/ppl w binarce, spill audit, build 30 s), nie jedna technika; nasza luka to czas pomysł → liczba. Lekcja [[lekcja-przegrywamy-procesem-nie-wiedza]]; K-161 (`tools/perf`), K-162 (profil Nib vs Maya). jaroserverai offline od 04:27 (profil Nib na karcie czeka).

## [2026-11-25] Szybka pętla eval (JARO: eval w minuty, nie godziny)
[[metoda-nib-level-up]] sekcja liczb: dziś 30–45 min/wariant; mamy już xtxbench z przełącznikami runtime (0,3 min/wariant, K-028), nieużyty tej nocy. Hak przeniesiony na topka-bonsai z przełącznikami K-150T/K-155/K-157 (`topka-rtswitch.patch`), K-163.

## [2026-11-25] Zwiad: DFlash2 dla Inklinga (K-164), Strata 0.2.21 bez zmian dla gfx1100
Raport product/research/watch/2026-11-25.md (sekcja „Analiza Kernela”): drafter DFlash2 Inklinga akceptacja 4,96 vs DSpark 3,52 (H200, T=1) → K-164; Pando i kalibracja temperatury draftu dopisane do K-158; Strata 92 vs 29 t/s to CUDA/routing slotu; LocalMaxxing R9700 194,7 niepotwierdzone.

## [2026-11-25] wyniki | Inkling: przenoszenie metody Nib do Mai (K-158…K-168)
- K-165: Nib + LoRA AtomicChat (uncensored) 156,6 / 147,3 t/s (T=0 / T=0,7), odmowy 0/5; HumanEval+ 92,1/87,2 vs Maya 90,2/85,4; ale polski prompt 82,5 / 78,4 vs Maya 113,8 / 112,9.
- K-167: Nib 150 t/s tylko z domyślnym top-k 40; pełny rozkład 39,3 t/s.
- K-158b…e: księga rundy Mai, okno weryfikacji jak Nib (verify(2) = zwykły + 4,1 ms), drafter tańszy 3,6 → 2,0 ms; rep2 T=0 202,7 t/s (+56%), L2k do 131,1 (+22%); wall.py: json +72%, polski chroniony bramką, kod jeszcze bez zysku. K-166 (fuzje dekodu) odrzucone, K-164 (DFlash2) czeka na przeniesienie na k158.
- Lekcje: osierocony server.py odpowiedział za Nib; spekulacja przez prompt `pl` przed wdrożeniem.

## [2026-11-25] research | 8 linków z panelu: llamAmpere Inkling, RustingStrata, Lucebox Inkling Fast, Magnitude 0.3, CSPD, PR #32875, PR #32859, Sirius
- llamAmpere v0.7.5: 189 t/s 3K na 3090 Ti, ale profile mają top-k 20 i własne kwanty → K-171 (równe warunki).
- RustingStrata: nowa notatka; przewaga tylko dla MoE ponad VRAM → K-172 razem z Magnitude 0.3.3 (strumień SSD).
- Lucebox #1056: Inkling na ROCm, R9700 AR 81,7 / DSpark 143,5 → K-170; Inkling Fast to inny model (decyzja JARO).
- CSPD: notatka `llm/cspd-soft-prompt`, pomysł uncensored bez adaptera.
- PR #32875: nie dotyczy Niba; ten sam wzorzec w dekwantyzacji Q4_K/Q6_K topki → K-173.
- K-174 zmierzone na CPU: tokenizacja 178k tokenów 121 → 102 ms (−16%), ID identyczne; bez osobnego wdrożenia.

## [2026-11-25] wyniki | kolejka wieczorna: K-148, K-164d, K-018, K-019, K-020, Bonsai (dsp, conf, bw)
- Wygrane: K-020 wall 208 → 102 s (−51%), K-148 edycja +14,2%, K-018 kopia +5,4%; wdrożenia K-175 i K-176 w kolejce z bramką wall.py `pl`.
- Bez wdrożenia: K-164d (pl 105,9), K-019 (+1,4%), Bonsai K-169 i drafter DFlash2/DSpark (MTP n2 145,8 zostaje).
- Nieważne: K-113 i K-158g (model Qwen skasowany o 17:09; `k158g.sh` bez prawa wykonania) → ponownie w kolejce.

## [2026-11-25] kolejka | K-038, K-009, K-025 zebrane; 6 pozycji przeniesionych; 5 agentów przygotowuje paczki
- K-009 odrzucone (wszystkie maski MMQ wolniejsze, VAR 8 −17%); K-038 bez zwycięzcy, kandydat KV draftu q8_0 +1,8% T=1 do K-175; K-025 bieg nieważny (wariant 83 nie użyty).
- Przeniesione: K-148, K-164, K-018, K-019, K-020, K-165, K-009, K-038. Czeka 60.
- Link Gumbii (DSpark między silnikami): zgodne z naszymi pomiarami.

## [2026-11-25] kolejka | 4 agentów przygotowało paczki: w kolejce K-175, K-176, K-171, K-173, K-025, K-017, K-008, K-058, K-046
- Odrzucone bez karty: K-010 (zmierzone 11-20, −1,3%), K-042 (zysk ≤ 10% tur, łączymy z K-128).
- Zablokowane pobraniem (decyzja JARO): K-170 (Lucebox czyta tylko swój plik, 17,6 GB), K-172 i A3B w K-025 (Qwen3.6-35B skasowany, 35 GB).
- Ocenione: K-057 1,5–3 dni, K-056 2–4 dni (142 konflikty).

## [2026-11-25] wyniki | K-022 (−977 MiB VRAM bezstratnie), K-062 bez efektu (Colab L4), K-004 bramki OK, K-006 poprawka skryptu
- K-022: FA prefill z natywnym q4_0 bit w bit, prędkość ±0,4%, szczyt VRAM przy 255k 23 323 → 22 346 MiB.
- Colab L4 (1,36 jedn., sesja zatrzymana): K-062 identyczny SASS; K-004 GUMBEL_MAX 152/152; L4 230,8 GB/s, fp16 75,4 TFLOPS.
- K-006 A1 padł na błędzie parsera (`k006.py:26`, grupy opcjonalne None); poprawione, ponownie w kolejce.

## [2026-11-25] kolejka | 10 kolejnych paczek: K-075, K-036, K-035, K-121, K-026a/b, K-021, K-001, K-012, K-047
- Ocenione bez karty: K-012 sufit bezstratny +2,5% (poniżej progu), K-047 sufit ok. 1,1%; K-159 Q4_K w Nibie 1–2 tygodnie (decyzja), K-124 wymaga budżetu.

## [2026-11-25] wyniki | K-158g wygrany (T=0 +26,3%, L2k +11,3%, pl −1,7%), K-175 FAIL, K-006 −36% pamięci cache
- K-158g `eq8-hsl-pol2-gated`: parytet 11/11, bramka −2% przechodzi → K-177 (podmiana `maya-atomic.json` po K-176/K-171).
- K-175: AGR2 i KV draftu q8_0 zmieniają md5 i tech T=0,7 −3,6% → odrzucone; sam K-020 → K-178.
- K-006: chude checkpointy −36% pamięci wpisu, wpis wspólnego początku 8,5 s → 0,86 s po wyrzuceniu; md5 harnessu niedeterministyczne → decyzja K-007.
- Ryzyko: `topka-keeper.sh` podnosi czat z modelem `qwen` (z cenzurą), `chat8080.sh restore` z `uncensored`.

## [2026-11-25] wyniki | K-025 (wariant 83 bezstratny na Bonsai, zysk już w produkcji), K-173 bez efektu, K-171 llamAmpere 1,7×

## [2026-11-25] wyniki | K-017 +3,4% proza (K-007), K-008 −1,3…−2,3%, K-046 W16 zostaje (W8 −24%), K-058 psuje tool calls (25 → 0)

## [2026-11-25] wyniki NVIDIA | Colab L4 (6,6 jedn. łącznie, sesje zatrzymane): K-016 n2/n3 +6–7% T=1, K-117 start −76%, K-068 KLD bez wyjątku niższe, K-004 +2,7%, K-064 hak MTP +37% pp512 (140 ms synchronizacji), K-063 0%, K-115 igły PASS

## [2026-11-26] produkcja | topki per model i karta; czat :8080 zawsze z modelu ACTIVE; decyzje: bez pobierania modeli, bramka KLD (K-007)
- `topki/xtx/{qwen-uncensored,qwen,bonsai,inkling}.sh`, `topka-start.sh`, `topka-stop.sh`; keeper, chat8080, topka-restart, run-jobs (podmiana atomowa) i @reboot przez jedno wejście; keeper ponownie uruchomiony.
- K-170, K-172 zamknięte decyzją JARO.

## [2026-11-26] kolejka | Vast nvq: 3090 i 5060 Ti wynajęte (5060 Ti pierwszy host odrzucony: limit mocy 150/180 W); K-113 XTX; zamknięte K-119, K-126, K-107, K-024, K-057, K-176 (do K-179); czeka 36

## [2026-11-26] kolejka | K-075, K-035 odrzucone (sufit < progu), K-121 narzędzie GA działa; Vast nvq2 (K-071, K-066) wystartował; K-050 w kolejce; K-056 rebase 32/49 plików

## [2026-11-26] wyniki | K-026: przy MoE z ekspertami na CPU spekulacja szkodzi (15,7 → 6,0–9,2 t/s); Enigma: domyślnie bez draftu przy --n-cpu-moe

## [2026-11-26] research | adapter pod omp: najpierw zestaw zadań omp i test gotowych adapterów pi (Qwen, Inkling), potem SFT samodestylacja, RL dopiero z budżetem; dane z sesji Claude licencyjnie wątpliwe

## [2026-11-26] wyniki NVIDIA | Vast nvq2 3090 (0,20 $): K-066 nthreads 128 prefill +11,5% (PPL do sprawdzenia), K_vram 512 psuje PPL mimo testów 49/49; K-071 qwen-warp czat +31%, kopia 64k +78% vs fork (inne wagi), DFlash2 nie wystartował

## [2026-11-26] research | qwen-warp: ¾ przewagi czatu to lżejszy kwant (13,25 vs 16,48 GB/token), reszta i kopia 64k to kernel 92–96% pasma i tania weryfikacja 16 wierszy → K-182; edycja wag A–Z: fala self-edit z listopada 2026 daje 1–7 pkt, tweet 4B 35→67% niezweryfikowany

## [2026-11-26] wyniki NVIDIA | Vast nvq 5060 Ti (0,16 $): n2 zostaje (T=1 53,6; n4 −15%), n3 kopia +14,6%; kvq na sm_120 −12% na kopii end-to-end mimo szybszego kernela; PDL +1,1%; igły PASS; K-113 OOM
- 3090 z tej samej paczki: build llamAmpere zablokował pomiary (pętla wypełniacza do terminu); Kernel przerwał build o 02:06, by puścić resztę pozycji przed terminem. Lekcja do paczki: pozycje niezależne od llamAmpere nie mogą czekać na jego build.

## [2026-11-26] wyniki NVIDIA | Vast nvq 3090 (0,34 $): igły 208k PASS, soak 262k bez dławienia (69 t/s, 75 °C), plain dekod 85% pasma (K-131), coupled +4,5% (1 para); K-016/K-064/K-068 przepadły przez build llamAmpere. Kampania 26.11 razem ok. 0,70 $.

## [2026-11-26] metody | szybsze testowanie: narzut XTX ok. 10% (restarty czatu 22 min, przerwy 52 min), Vast 3090 −40 min przez build llamAmpere; naprawione: pomijanie restore między paczkami, orch.py bez czekania na obcy build; WE2 (scalenie LoRA w NVFP4 Niba, proj requant resid 0,005) w kolejce

## [2026-11-26] wdrożenia i wyniki | K-020 w produkcji czatu (−51% w agencie, odpowiedzi identyczne), K-158g w Mai; K-179 −2,7% pl (FAIL), K-007 bramka działa (K-017, K-006 PASS), K-001: produkcja ma 3 wycieki stanu/12, poprawka 0 → bramka K-183; K-050 0%, K-047 sufit 0,5 ms/krok; K-012/K-021/K-060 nieważne

## [2026-11-26] wyniki | WE1 Astra-Stop na Qwen uncensored: przy effort low nie skraca myślenia (skala 1: +17% czasu), jakość bez zmian, LoRA w locie −6,7% dekodu → nie wdrażamy

## [2026-11-26] wyniki | nocna kolejka: WE2 scalona ablacja Nib +5,2/+5,7% przy odmowach 0/5; K-183 FAIL (poprawka K-001 −5…−12%); K-184 PR #33049 działa (akceptacja 0 → 18–37%) ale llama.cpp Inkling 26–44 t/s vs Maya 113; K-182 pasmo GEMV n=16 67%; K-021 KILL; K-012 GO (−19%)

## [2026-11-26] zwiad | Tintero PR #2 (XTX Inkling: plain +9%, draft kod 103 → 151–160) → K-185; Nib 0.1.2 bez spilli, prefill 128K +32% → K-186; tqLLM/Strata/hipfire/TensorFold/NInfer/oMLX bez znaczenia dla XTX; K-182b NO-GO (×1,05)

## [2026-11-26] wyniki | K-186 Nib 0.1.2: 0% na naszym clang 23 (logity identyczne); WE2 HumanEval+ scalone proj 87,2 = LoRA 87,2 (baza 86,0)

## [2026-11-26] wdrożenie | K-185 port Tintero PR #2 do Mai: wall T=0 141,8 → 152,0 (+7,2%), T=0,7 +0,3%, md5 identyczne → produkcja maya-atomic.json

## [2026-11-26] wyniki | K-012b układ par fal kvq: kernel nb5 −14,5…−16,9%, dekod 94k +2,0%, bitowo identyczny → PASS; K-001c tania poprawka wycieku 0/12, md5 identyczne, wall +1…+2% poza T=0,7 tech −3,0% (szum?) → łączna bramka K-183c; K-185b LGB bez znaczenia

## [2026-11-26] wdrożenie | K-183c na :8080: silnik ~/llama-topka-k183c (K-012 pary fal kvq + K-001c), dekod 94k +2,1%, wycieki 0/12, md5 identyczne; topki zaktualizowane (Qwen k183c, Maya k185)

## [2026-11-26] wdrożenie + wyniki | K-006 na :8080 (restart po wyrzuceniu 8,5 → 0,8 s, wall ±0,2%); K-017 FAIL (−3,5…−17,5%); K-036 zamknięty (bezczynność 1,8%, brak kawałka ≥ 0,5 ms); lekcja: build na 6-15 dzieli rdzenie SMT z serwerem 2-5

## [2026-11-26] wyniki | K-159 Maya zostaje (Nib+WE2 na 0.1.2 psuje drafter: 101 vs 149 t/s); K-047 +0,3–0,4% bitowo identyczne (PASS); K-124 KILL (−0,3%) + znalezisko: wynik T=0 zależy od kolejności żądań; K-158r T=0,7 kod +55–64%, json +71–77%, pl −2,3–3,0% → K-158s; K-132 ramię 6.8 (zimny start 45 s vs 6 s)

## [2026-11-26] wdrożenie | K-158s Maya: T=0,7 mediana 112,7 → 147,7 (+31%), kod +64%, json +71%, pl −1,5%, T=0 md5 identyczne → maya-atomic.json; K-120 KILL (LoRA pi −28,5% dekodu); K-182 zamknięty; K-060 P0 fabryka działa (EPI +2,3…2,8% potwierdzone)

## [2026-11-26] wyniki + wdrożenie | K-047 na :8080 (+0,3–0,4%); K-037 KILL (przekazanie 1,1–3,5 µs); K-056 rebase działa (ops 0 FAIL, KLD PASS), wdrożenie wstrzymane (pl T=0 −6,6%); 10 testów XTX z polecenia JARO zamknięte (K-132 ramię 7.0 czeka na restart)

## [2026-11-26] wyniki | nvq3 Vast (0,50 $, przerwane poleceniem JARO 16:25): fork > llamAmpere dokładny (T=0 87,6 vs 70,1), DFlash2 W4A16 w warp +7,5% czat / +22,8% kopia 64k, n2 zostaje na Ampere, 5060 Ti bez dławienia; wszystkie testy zatrzymane, 0 instancji

## [2026-11-26] research | 8 linków JARO: DFly2 (tylko DSA), AITER gfx1100 experimental, expert streaming (lekcja Enigma), YASA i NVFP4 KV stratne, Megatron bzdura, gfx1170 do obserwacji

## [2026-11-26] decyzja | JARO: wiedza też na później (większe modele, inne karty); notatki dostają sekcję „Na później”

## [2026-11-26] lekcja | powtórzony błąd „nie dla nas”: lint wymusza sekcję „Na później” w research/; uzupełnione 4 notatki

## [2026-11-26] research | YASA (Aleph Alpha): notatka llm/yasa-rzadka-uwaga-kolibri; u nas pełna uwaga to ~14% kroku przy 94k, ~25% przy 192k

## [2026-11-26] lekcja + kolejka | +15–30% to test, nie „na później”: K-188 rzadka uwaga bez treningu w kolejce (wysoki priorytet), agent przygotowuje na CPU

## [2026-11-26] lekcja + kolejka | lint wymaga „## Test u nas” (K-… albo „nie da się” z powodem) w research/ i llm/; przegląd dał K-189…K-192

## [2026-11-27] wyniki | K-188 rzadka uwaga bez treningu: kernel −30…−74% przy 96–192k, krok −7…−10%, KLD FAIL każdy budżet → KILL

## [2026-11-27] wyniki | K-056b pl T=0 −6,8% powtórzone (inny tekst greedy); K-189 propose Inklinga 1,59 → 4,83 ms przy 98k (×3,05) → K-194

## [2026-11-27] wyniki | K-194 IK2_DRAFT_CTX: propose przy 98k 4,83 → 1,58 ms, ale dekod przy 90k bez zysku (akceptacja 0,24 → 0,16–0,20) → KILL

## [2026-11-27] wyniki | K-193 Inkling GSQ-RCO IQ3_S: 11,6 GB, w llama.cpp +14–24% vs AD-Q4_K, KLD 0,040 (AD 0,011), Maya 146/148 zostaje; K-195 dla Enigmy 12–16 GB

## [2026-11-27] wyniki | nvq4 (0,53 $): K-131 cp.async odrzucone (−3…−7%), K-112 3090 845 GB/s, K-014 narzut hosta 3–7% czatu, K-015 to inny tekst nie regresja, K-071 DFlash2 +5,2/+12,9%; budżet 1,05 z 1,50 $

## [2026-11-27] vast | reaper: 2 instancje 5060 Ti nvq4 usunięte (FINISHED); wyniki już w testy/2026-11-27-nvq4

## [2026-11-27] serwis | jaroserverai wyłączony na polecenie JARO (sudo -n /usr/bin/systemctl poweroff, NOPASSWD)

## [2026-11-27] zwiad | Tintero paged KV +8,9% przy 131k (K-196), DSpine 5090 663,9 (K-197), drzewo OPT (K-198), dashboard AMD (K-199)

## [2026-11-27] wyniki | nvq5 (0,13 $): Inkling IQ3_S na 5060 Ti 82,7 t/s (+26% nad przepisem Qwena), 3060 IQ2_S +55%; K-190 i K-197 odrzucone; K-201

## [2026-11-27] wyniki | K-196 paged KV w Mai: 0…+0,4% przy 32–128k, md5 identyczne → odrzucone; prawdziwa dźwignia natywny WMMA → K-200; K-199 fork vs upstream TG +14%; K-198 NO-GO

## [2026-11-27] wdrożenie | K-200 Maya natywny WMMA uwagi: dekod 90k +30,7%, 32k +14,2%, 2k +6,7%, okna bitowo = dekod po tokenie, KL w podłodze, igły 5/5; jaroserverai: usunięte mainline + unc-nearest (38 GB, wolne 146 GB)

## [2026-11-27] eksperymenty | K-191 pomijanie bloków Qwena: +1…+3,5% prędkości, KLD 0,04–0,07 (za dużo) → negatywne; K-192 kierunek PL nie steruje językiem → negatywne

## [2026-11-27] wyniki | K-201 Inkling IQ3_S bez cenzury (LoRA w locie) na 5060 Ti: odmowy 0/5, PPL +0,35%, 131k w 14,4 GB → kandydat Enigmy 16 GB; Vast łącznie 1,23 z 1,50 $

## [2026-11-27] wdrożenie | Maya kontekst 16k → 393 216 (384k: igły 5/5, 23,3 GiB, prompt 327 s, dekod 63–80 t/s); 448k OOM draftera; ISTA 1M w llama.cpp tylko bez draftera; K-203 Maya+IQ3_S w kolejce

## [2026-11-27] wdrożenie | Maya kontekst → 425 984 (420k: igły 5/5, 23,77 GiB, prompt 380 s)

## [2026-11-27] topka | Inkling 1M na XTX: Maya + IQ3_S (K-203), KL 0,0019 vs llama.cpp, okna bitowe, wall 67,8, 128k 52–56, 360k 44,5; Maya AD 425 984 w produkcji

## [2026-11-27] K-203 | kernele IQ i mv_parts bitowo dokładne, wall 1M 67 bez zmian; rozkład kroku: macierze mieszane 3,4× wolniejsze od planarnego Q8 → K-206

## [2026-11-28] test | K-204 Enigma 16 GB Inkling IQ3_S: 5060 Ti +104% przy 262k, 4060 Ti +103% przy 283k, 0,41 $; K-207 (ablacja zamiast LoRA)

## [2026-11-28] wdrożenie | K-206 Inkling 1M (Maya IQ3_S) wall 67,8 → 104,2 t/s (+54%) bez straty, 128k +38%, 360k +31%; lekcja o kontrakcji FMA

## [2026-11-28] vast | reaper K-204: 5060 Ti zniszczona po 40 min mimo pracy (fałszywe offline), 4060 Ti FINISHED; wyniki w notatce K-204, 0 instancji

## [2026-11-28] decyzja | Enigma 16 GB: Inkling K-204 na stronie i w aplikacji (5060 Ti, 4060 Ti); 5080 zostaje na Qwenie

## [2026-11-28] wdrożenie | Maya AD kontekst 425 984 → 557 056 (bin-k207p, drafter na 131k, igły 5/5 przy 546k, wall bez zmian, md5 =)

## [2026-11-28] test | K-207 ablacja zamiast LoRA w llama.cpp: +41% (EPYC 7402, stosunek), odmowy 0/5, KL na podłodze; 0,045 $

## [2026-11-28] zwiad | G2GFAST 687,5 (+3,6%, K-198 już ujemne), nib gfx1201 dekod 50% przepustowości, Maya 3090 210 = reasoning-v1 → K-208; compwatch: naprawiony KeyError slug, nasze += Inkling

## [2026-11-28] kolejka | K-202, K-203 → Zrobione; nowa K-209 (loady nietemporalne w MMVQ Qwena)

## [2026-11-28] test | K-208 reasoning-v1 XTX 111/157 vs 3090 133/210; okna sufiksowe nie bitowe → K-210, luka dekodu → K-211; K-207 na Ryzenie 9700X: ablacja 88,45 t/s (+15–28% vs LoRA)
