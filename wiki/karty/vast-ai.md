---
typ: karta
tags: [karty, vast, nvidia]
aktualizacja: 2026-11-22
zrodlo: ~/KERNEL/product/research/05-chmura-gpu-do-testow.md:12-22,66,99-128,185-189,202-204; ~/qwen-opt/cloud/PLAN-TESTOW.md:5,11,20-23,36-49,95-104; ~/KERNEL/product/research/09-chmura-3090.md:3-4,183; ~/KERNEL/product/research/09-chmura-5060ti.md:16,191; ~/KERNEL/product/research/09-chmura-3060.md:229; ~/KERNEL/product/PLAN-NV-V2.md:12-14; ~/KERNEL/product/research/05-chmura-gpu-do-testow.md:7,13-22
status: aktualne
karta: vast-ai
gdzie: Vast
stan: główne źródło NVIDIA
---
# Vast.ai (główne źródło kart NVIDIA)

**Marketplace hostów z kartami NVIDIA od GTX 10xx do RTX 50xx; tu wynajmujemy karty do kampanii (3060, 5060 Ti, 3090), bo zakup jest dużo droższy; AMD na Vast nie ma.**

- Oferta (raport 05, 2026-10): ~80 modeli GPU, 0 ofert AMD (filtr `gpu_arch=amd` istnieje); Docker domyślnie albo KVM VM (`vms_enabled=true`); on-demand, interruptible (licytacja), reserved (do −50%); publiczny feed cen JSON.
- Mediany $/h: RTX 3060 ~0.08, 3090 0.228 (162 oferty), 4090 0.507 (318), 5060 Ti 0.165 (163), 5070 0.294, 5090 0.734 (445).
- Profilowanie: w kontenerze brak liczników profilera i blokady zegarów (`ncu` prawie zawsze `ERR_NVGPUCTRPERM` [INFERENCE raportu]); VM Vast deklaruje pełne liczniki → benchmarki w kontenerach, profilowanie w VM.
- Narzędzia u nas: `vastai` CLI 1.8.3 w `cloud/.venv`; `vastai search offers` działa bez klucza; brak max-duration dla on-demand, stąd nasze dwa timery zniszczenia.
- Pierwsza runda (plan 2026-10-15): budżet ≤ $8, plan ~$2.5 na 3060 ($0.097/h z dyskiem), 5060 Ti ($0.188), 3090 ($0.232).
- Pierwsza runda wykonana 2026-10-16 (trzy karty równolegle): 3090 ≈ $0.90, 5060 Ti ≈ $1.05, 3060 ≈ $0.82, razem ≈ $2.77 z budżetu $5; instancje zniszczone. Uwagi: kontenery mają limit cgroup ~7.7 CPU przy `nproc` 64; jedna instancja odrzucała klucz SSH.
- Zasada pomiaru: porównania A/B tylko na tym samym hoście w tej samej sesji; „typowe t/s” dopiero jako mediana z ≥ 3 hostów.

## Aktualizacja 2026-10-21
- Kampania 31-*: transfer $3.80 z $6.90 ([[lekcja-vast-transfer-kosztuje]]); plan v2 ([[raport-plan-nv-v2]]) czeka – [[karty/vast-ai]].
- 2026-11-05: buildfarm 59279813 (14:46–15:05) kosztował $0.027, zniszczony; `down` tylko z `~/qwen-opt/cloud`, `--download-gb` wymagane ([[lekcja-buildfarm-down-z-cloud]]).

## Ze scalonej notatki: Vast.ai

Rynek wynajmu GPU na godziny; nasze główne źródło NVIDIA do testów (kontenery do benchmarków, VM do profilowania).

Mediany on-demand z feedu 2026-10-15 21:30 UTC: RTX 3060 0.08 $, 3090 0.23 $, 4090 0.51 $, 5060 Ti 0.16 $, 5070 0.29 $, 5090 0.73 $ (445 ofert). Zero ofert AMD (feed: 80 modeli, wszystkie NVIDIA). W kontenerach brak liczników profilera i blokady zegarów; VM ma „CUDA profiling with hardware counters”. Szczegóły operacyjne, CLI i lekcje w notatce chmury.

## Przegląd 2026-11-24 (nauka, nie tylko prędkość)

- Werdykt „NVIDIA tanio, Radeonów z rootem prawie brak” mówił o kernelach. Dla produktu chmura to **laboratorium sprzętu klientów**: konfiguracje katalogu Enigmy dla 2080 Ti, 3060, 3090, 4060 Ti, 4070, 4090, 5060 Ti, 5080, 5090 są zmierzone na wynajętych kartach w kampanii 67 (`app/engine/src/server/catalog/index.ts:205-250`, „run end-to-end in campaign 67 on the real card”). Bez Vast katalog byłby szacunkiem.
- Infrastruktura, którą przy tym zbudowaliśmy, to nasz odpowiednik zabezpieczeń kosztowych Inference Stack (harmonogram wyłączenia GPU przed wydaniem pieniędzy): `qwen-opt/cloud/{hostguard.sh,vast-reaper.sh,idle-watch.py,hosty-zle.txt,onstart-guard.sh}` i dwa timery zniszczenia.
- Luka: klienci to też Windows, APU i Radeony ([[lekcja-enigma-apu-jako-karta]]). Vast nie ma AMD, RunPod tylko MI300X, a Salad ma Radeony 7800 XT…9070 XT w WSL2 na Windowsie graczy, ale dla naszej organizacji AMD jest niedostępne ([[salad]]). Mac: Enverge (R30).
- Co bierzemy: macierz testów aplikacji = lista kart z katalogu + Windows + APU; dla Radeonów na Windows ponowić dostęp w Salad albo znaleźć hosta z Windows, zanim wyślemy silnik AMD użytkownikom.

## Powiązane
- [[narzedzia/skrypty-chmury]]
- [[runpod]]
- [[rtx-3090]]
- raport-05-chmura
- [[2026-10-16-kampania-nvidia]]
- [[lekcja-limit-cpu-kontenera]]
