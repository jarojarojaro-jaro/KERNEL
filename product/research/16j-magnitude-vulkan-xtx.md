# 16j. Magnitude przez Vulkan na RX 7900 XTX (E-X5)

Data: 2026-10-18. Autor: podagent MagnitudeVulkanXtx. Eksperyment E-X5 z planu [16i §8](16i-magnitude-co-robia-dobrze.md).
Katalog roboczy: `X/` = `~/qwen-opt/magnitude-xtx/` (skrypty `session.sh`, `prep.sh`, `analyze.py`, `xbench.py`; wyniki `x/xbench.jsonl`, `servers.jsonl`, `results.txt`, logi i tuning trace w `logs/`).
Porównanie chmurowe: `R3/` = `~/qwen-opt/cloud/results/magnitude-vs-3090-20261016/`.

## 0. Wynik w 5 punktach

1. **Magnitude działa na gfx1100 przez Vulkan (RADV, Mesa 25.2.8) bez żadnych poprawek.** Wymagało to tylko user-local sterownika Vulkan (bez sudo). Pierwszy start z pustym cache: ~95 s, z czego ~71–75 s to jednorazowe przygotowanie kerneli. Kolejne starty: 23–26 s (Qwen), 10–15 s (LFM).
2. **Na Qwen3.8-27B nasz silnik (ROCm/HIP, MTP) jest ~2× szybszy w każdym workloadzie.** Sweep T=1: 100.0 vs 50.1 t/s (×2.00), copy 64k: 141.2 vs 63.7 t/s (×2.22), code-edit: 170.0 vs 87.7 t/s (×1.94), prefill 64k: 78.4 vs 117.6 s.
3. **Na LFM2.5-24B-A2B (plain, bez drafta) przewaga jest ×1.47–×2.2.** Sweep 322.9 vs 219.6 t/s, copy 64k 246.4 vs 116.7 t/s, prefill 64k 14.6 vs 32.7 s.
4. **Ich przewaga tok/krok jest, ale na Vulkanie każdy szerszy krok jest drogi.** Code-edit: 7.05 vs 4.92 tok/krok, ale 83 vs 29 ms/krok. Krok jednowierszowy Magnitude (pl-proza, adaptacja wyłącza draft) to 27.7 ms, tyle co nasz krok 5-wierszowy (28.1 ms). Ich krok 8 wierszy kosztuje ×3.0 kroku 1-wierszowego, a u nas szerokość prawie nic nie kosztuje (28.0–28.4 ms dla 1.9–3.6 tok/krok).
5. **Pozycjonowanie: na AMD Magnitude nie jest dziś realnym konkurentem wydajnościowym.** Jest konkurentem „działa od ręki” (jedna binarka, Vulkan, bez ROCm). Na XTX przegrywa 1.4–2.2× na każdym workloadzie i każdym modelu, który zmierzyliśmy.

## 1. Uruchomienie

- **Release:** `magnitude-icn-base-linux-x64-gnu.tar.gz` (0.2.9) zawiera `magnitude-inference` (serwis ICN) z wkompilowanym backendem Vulkan (`seismic/backends/vulkan/*` w stringach binarki) i runtime NVRTC. Do pomiaru użyłem `magnitude-engine` z lokalnego buildu źródeł `954d677d` (ten sam commit co release i co MagnitudeVs w chmurze; `~/qwen-opt/magnitude/build.log`, 20 min CPU). Backend Vulkan jest w tej binarce (11 ścieżek `backends/vulkan` w stringach), kopia z sha256 w `X/magnitude-engine.sha256`.
- **Vulkan:** system nie miał loadera ani ICD (`libvulkan1`, `mesa-vulkan-drivers` niezainstalowane). Bez sudo: `apt-get download` + `dpkg -x` do `~/.local/vk/root/` (libvulkan1 1.3.275, mesa-vulkan-drivers 25.2.8, libllvm20 i 9 bibliotek xcb/wayland), ICD przepisany na ścieżkę absolutną, `. ~/.local/vk/env.sh` (`VK_ICD_FILENAMES`, `LD_LIBRARY_PATH`). `vulkaninfo`: `AMD Radeon RX 7900 XTX (RADV NAVI31)`, API 1.4.318.
- **Modele:** `~/models/Qwen3.8-27B-UD-Q4_K_XL.gguf` (produkcyjny), drafter z ich katalogu `magnitudedev/Qwen3.8-27B-DFlash2-GGUF` `Qwen3.8-27B-DFlash2-Q8_0.gguf` rev `ead2a051` (sha256 `e92a3bac…`, zgodne z `R3`/`models.tsv`), `LiquidAI/LFM2.5-24B-A2B-GGUF` `LFM2.5-24B-A2B-Q4_K_M.gguf` rev `0912d331` (sha256 `d3334405…`, zgodne). Oba w `~/models/magnitude/`.
- **Komenda Magnitude** (jak w MagnitudeVs, `R3/servers.jsonl`): `magnitude-engine --device vulkan --model … [--draft … --method dflash2 | --method plain] --no-projector --context-tokens 67584 --output-capacity 1024 --cache-dir X/cache/<model>`.
- **Nasz silnik:** Qwen: `CTX=67584 EFFORT=off run-llm.sh qwen mtp rocm` (produkcyjny `~/llama-opt`, KV q4_0, MTP n=4 + słownik draftu 64k, IQ4_XS). LFM: flagi `run-llm.sh lfm` (KV q8_0, ctx 67584), ale **ten sam plik Q4_K_M co Magnitude** (produkcja ma Q5_K_M), żeby porównanie było na identycznych wagach.
- **Pierwsza próba (smoke, `--method plain`, ctx 8192) 2026-10-16** utknęła po „device opened” na >300 s (125 artefaktów w cache); przerwana limitem 300 s. Po zniesieniu limitu pełna konfiguracja startowała w 95 s. [INFERENCE] przy smoke konkurował inny job o CPU/GPU; nie odtwarzałem.

## 2. Przygotowanie kerneli i autotune

| model | pierwszy start | przygotowanie kerneli | autotune | artefakty | start z cache | źródło |
|---|---|---|---|---|---|---|
| Qwen 27B + DFlash2 | 95.6 s | 70.7 s (771 s CPU w unitach) | 67 unitów, 0 zmierzonych konfiguracji, 67/67 canonical defaults | 323 | 23.2 / 26.2 s | `X/logs/qwen.mag.first.{log,tuning.jsonl}`, `X/servers.jsonl` |
| LFM 24B-A2B plain | 94.6 s | 75.0 s (145 s CPU) | 21 unitów, 21/21 canonical defaults | 113 | 10.1 / 15.1 s | `X/logs/lfm.mag.first.*` |
| (3090, CUDA, dla porównania) | 51.5 s | 40.2 s (274 s CPU) | 67/67 defaults | — | 9.1–10.1 s | `R3/logs/qwen.mag.first.tuning.jsonl`, `R3/servers.jsonl` |

Autotune na Vulkanie zachowuje się jak na CUDA: każdy unit kończy się „0 of the 1 configurations asked for measured … serving 1.000 of the defaults”. Budżet 60 s idzie na formowanie programów (glslang → SPIR-V → RADV/ACO), nie na pomiar. Czyli **na XTX Magnitude chodzi na nietunowanych, kanonicznych konfiguracjach kerneli**.

## 3. Wyniki (ABBA, świeży proces na sesję)

Workload identyczny z MagnitudeVs: `xbench.py` z `R3` (sweep: 6 promptów PL/EN × 3 seedy × 400 tok, T=1, thinking off; ttft ~2k ×3 i ~16k ×1; copy: prose-repeat moby-dick lanes 0,1 rozmiarowane na 64k szablonem Qwena/LFM (`prose64k-*.json` z chmury); code-edit: 4 pliki, T=0, 1024 tok). Jedyna zmiana w kliencie: VRAM czytany z `/sys/class/drm/card0/device/mem_info_vram_used` zamiast `nvidia-smi` (cały device, łącznie z ~0.3 GB tła).
Kolejność wykonania: Qwen mag1, ours2, mag4, ours3 (przed rebootem 18.10, fabryczna krzywa wentylatora); LFM mag1, ours2, ours3, mag4 (po reboocie, wentylator 100% od 50 °C). Rozrzut między powtórzeniami ≤4% (sweep Magnitude 49.1/51.0), u nas ≤0.5%.

### 3.1 Qwen3.8-27B UD-Q4_K_XL (Magnitude: DFlash2 Q8_0, adaptacyjna szerokość; my: MTP n=4)

| workload | Magnitude-Vulkan t/s | nasz t/s | × | Mag tok/krok | nasz tok/krok | Mag ms/krok | nasz ms/krok |
|---|---|---|---|---|---|---|---|
| sweep T=1 (mediana 6 promptów) | 49.1 / 51.0 | 99.9 / 100.1 | ×2.00 | 2.49 / 2.51 | 2.82 | 50.5 / 49.1 | 28.3 / 28.3 |
| pl-proza / pl-tech / pl-kod | 36 / 43 / 67 | 68 / 102 / 128 | ×1.9 / ×2.4 / ×1.9 | 1.00 / 1.69 / 3.87 | 1.92 / 2.88 / 3.63 | 27.7 / 38.9 / 58.0 | 28.1 / 28.2 / 28.3 |
| copy 64k (2 lanes) | 63.8 / 63.5 | 141.1 / 141.3 | ×2.22 | 6.57 | 4.53 | 92.8 (lane 0), 113.2 (lane 1) | 31.9 |
| code-edit (4 pliki) | 87.8 / 87.5 | 169.6 / 170.4 | ×1.94 | 7.05 | 4.92 | 83.3 (3 pliki), 68.6 (lazy.py) | 28.9 |
| prefill ~2k (t/s) | 692 / 688 | 871 / 879 | ×1.27 | | | | |
| prefill ~16k (t/s) | 680 / 678 | 988 / 988 | ×1.45 | | | | |
| prefill 64k (s, copy) | 117.5 / 117.7 | 78.5 / 78.4 | ×1.50 | | | | |
| VRAM po starcie / szczyt (MiB, device) | 20709 / 22886 | 19609 / 20182 | | | | | |
| start (cache ciepły) | 23.2 / 26.2 s | 25.9 / 23.7 s | | | | | |

Źródła: `X/x/xbench.jsonl` (label `qwen|xtx|mag|1`, `…|4`, `qwen|xtx|ours|2`, `…|3`), zestawienie `X/results.txt`, `X/servers.jsonl`. Jakość: copy prefix_frac 1.00 u obu, code-edit ratio 0.967 u obu (identyczne na każdym pliku).

### 3.2 LFM2.5-24B-A2B Q4_K_M (plain, bez spekulacji po obu stronach)

| workload | Magnitude-Vulkan t/s | nasz t/s | × | Mag ms/krok | nasz ms/krok |
|---|---|---|---|---|---|
| sweep T=1 | 219.9 / 219.2 | 322.7 / 323.0 | ×1.47 | 4.55 | 3.10 |
| copy 64k | 116.8 / 116.5 | 245.5 / 247.3 | ×2.11 | 8.6 | 4.1 |
| code-edit | 220.1 / 219.8 | 312.0 / 311.7 | ×1.42 | 4.5 | 3.2 |
| prefill ~2k (t/s) | 2691 / 2682 | 5745 / 5789 | ×2.15 | | |
| prefill ~16k (t/s) | 2681 / 2688 | 6002 / 6026 | ×2.24 | | |
| prefill 64k (s) | 32.7 / 32.7 | 14.6 / 14.6 | ×2.24 | | |
| VRAM po starcie / szczyt (MiB) | 15602 / 15956 | 15237–15245 / 15378 | | | |
| start (cache ciepły) | 10.1 / 15.1 s | 3.7 / 7.2 s | | | |

Źródła: `X/x/xbench.jsonl` (`lfm|xtx|*`), `X/servers.jsonl`. LFM nie kopiuje tekstu w tym zadaniu (prefix_frac 0.00 u obu silników, także na 3090 w `R3`), a code-edit ratio różni się (0.42 vs 0.51) przez różną numerykę przy T=0. To cecha modelu, nie miara jakości silnika.

## 4. Dlaczego przegrywają na XTX

- **Koszt szerokości weryfikacji na Vulkanie jest stromy.** Z sweepu Qwena (ten sam silnik, różne prompty → różna szerokość wybrana adaptacyjnie): 1.00 tok/krok → 27.7 ms, 1.69 → 38.9 ms, 2.23 → 47.9 ms, 2.77 → 51.7 ms, 3.12 → 53.0 ms, 3.87 → 58.0 ms, code-edit 7.05–7.88 → 83 ms. Krok przy bloku 8 kosztuje ×3.0 kroku jednowierszowego. Na 3090 (CUDA) ten sam blok to 50 ms przy ~44 ms dla ~3 wierszy (16i §0 pkt 3), czyli Vulkan jest tu ×1.66 wolniejszy od ich własnego CUDA.
- **Nasz krok prawie nie zależy od szerokości** (28.0–28.4 ms dla 1.9–3.6 tok/krok, 5 wierszy weryfikacji). Ich krok jednowierszowy (27.7 ms) = nasz krok pięciowierszowy (28.1 ms). Zatem nawet przy idealnym drafcie (7.88 tok/krok) przegrywają: 7.88/83 ms = 95 t/s vs nasze 4.92/29 ms = 170 t/s.
- **Kontroler adaptacyjny działa poprawnie i sam to widzi.** Na pl-proza wyłącza draft całkowicie (1.00 tok/krok, akceptacja 0.04–0.09), bo przy takim koszcie szerokości draft się nie opłaca. To dobra właściwość (nie tracą na prozie względem plain), ale sufit to ich plain decode, który jest 2× za wolny.
- **Długi kontekst:** krok copy 64k 93–113 ms vs 83 ms przy ~2–3k (code-edit), a nasz 31.9 vs 28.9 ms. Prefill 64k 117.6 s vs 78.4 s.
- **Brak tuningu:** wszystkie 67 (Qwen) i 21 (LFM) unitów na kanonicznych defaultach (§2). [INFERENCE] defaulty są strojone pod NVIDIA/Apple (WARPS=4, kooperatywne macierze 16×16×16); RDNA3 przez RADV dostaje generyczny SPIR-V bez strojenia pod WMMA/dual-issue.
- **LFM (bez spekulacji):** czysty koszt kerneli. Decode ×1.47, prefill ×2.2. Na 3090 Magnitude wygrywał LFM copy 64k (164 vs 132 t/s, `R3/x/xbench.jsonl`); na XTX przegrywa ×2.1 (116.7 vs 246.4), więc ich kernele attention dla długiego kontekstu na Vulkanie nie przenoszą przewagi z CUDA.

## 5. Co możemy przejąć (wnioski dla forka)

- **Nic z kerneli Vulkan** — są wolniejsze w każdej kategorii.
- **Potwierdzenie z 16i: przewaga Magnitude to wyłącznie tok/krok** (blok 8 DFlash2 + adaptacyjna szerokość). Na XTX nasz koszt szerokości jest mały (V(16) − V(5) = +7.1 ms, 16i §0 pkt 3), więc szerszy blok (lookup W8/W16, E-X0..E-X2 u XtxLookupTail) ma tu lepsze warunki niż u nich: przy 7.88 tok/krok i ~35 ms/krok [INFERENCE, ekstrapolacja z +7.1 ms] code-edit dałby ~225 t/s.
- **Kontroler szerokości** warto mieć głównie jako „wyłącznik” na prozie PL (u nich 1.00 tok/krok bez straty). U nas na XTX koszt szerokości jest płaski, więc zysk z wyłączania byłby mały (27.7 vs 28.1 ms).

## 6. Pozycjonowanie produktu

- **Na AMD (RDNA3, Linux) Magnitude jest konkurentem w łatwości instalacji, nie w wydajności.** Jedna binarka + Vulkan, bez ROCm, działa na gfx1100 od ręki (po dostarczeniu ICD; na typowym desktopie Mesa RADV jest preinstalowana). Pierwszy start 95 s, potem 10–26 s.
- **Wydajność:** nasz silnik ×1.94–×2.22 na Qwen 27B (sweep, copy 64k, code-edit) i ×1.42–×2.24 na LFM (decode, prefill), przy podobnym VRAM (Qwen: 20.2 vs 22.9 GB szczyt; LFM 15.4 vs 16.0 GB).
- **PL:** na pl-proza Magnitude ma 36 t/s, my 68 t/s (×1.9); na pl-tech ×2.4.
- **Ryzyko:** jeśli Magnitude dostroi kernele pod RDNA (autotune dziś nic nie mierzy) i obniży koszt szerokości, ich tok/krok (7.05–7.88 na kodzie) stanie się groźny. Dziś na XTX jest to odległe: musieliby skrócić krok 8-wierszowy z 83 do <48 ms, żeby zrównać się z nami na code-edit.
- **Komunikat:** „Na kartach AMD jesteśmy ~2× szybsi od Magnitude na tym samym modelu i tym samym GPU” jest poparte pomiarem (XTX, ABBA, ten sam harness co MagnitudeVs).

## 7. Odstępstwa i ograniczenia

- Kolejność Qwen: mag1, ours2, mag4, ours3 (ABAB zamiast ABBA, przez przerwanie sesji ours3 kolizją z innym serwerem; powtórzona). Różnica między powtórzeniami ≤4%, różnica między silnikami ×1.9–×2.2, więc kolejność nie zmienia wniosku.
- Qwen mierzony przed rebootem (fabryczna krzywa wentylatora, pamięć do ~90 °C), LFM po reboocie (wentylator 100% od 50 °C). Pary w ramach modelu w tych samych warunkach.
- `xbench.py` wysyła `cache_prompt:false`; nasz serwer ma `--cache-ram 16384` (produkcja), prompty sweep są unikalne, więc bez wpływu.
- Smoke 16.10 (`logs/smoke.log`) nie doszedł do readiness w 300 s; w pomiarach nieużyty.
- Kod forka bez zmian (nie było nic do wyłączenia przełącznikiem; brak commitu). Greedy md5 nie dotyczy.

## 8. Do bazy wiedzy

| folder | tytuł | treść (liczby ze źródłami) |
|---|---|---|
| `eksperymenty/` | `2026-10-18-magnitude-vulkan-xtx.md` | E-X5: Magnitude 0.2.9 (`954d677d`) na RX 7900 XTX przez RADV 25.2.8. Qwen3.8-27B Q4_K_XL + DFlash2 Q8_0 vs nasz `run-llm.sh qwen mtp rocm`: sweep 50.1 vs 100.0 t/s, copy 64k 63.7 vs 141.2, code-edit 87.7 vs 170.0, prefill 64k 117.6 vs 78.4 s, pp 16k 679 vs 988 t/s; LFM2.5-24B-A2B Q4_K_M plain: 219.6 vs 322.9, copy 64k 116.7 vs 246.4, pp 16k 2685 vs 6014 t/s (`~/qwen-opt/magnitude-xtx/x/xbench.jsonl`, `results.txt`). |
| `lekcje/` | `lekcja-koszt-szerokosci-backendu.md` „tok/krok nie wygra z drogim krokiem” | Magnitude-Vulkan: 7.05 tok/krok przy 83 ms → 88 t/s; my 4.92 tok/krok przy 29 ms → 170 t/s. Ich krok 1-wierszowy 27.7 ms = nasz 5-wierszowy 28.1 ms; ich krok 8 wierszy ×3.0 kroku 1-wierszowego (sweep per prompt, `xbench.jsonl` `qwen|xtx|mag|*`). |
| `repo/` | aktualizacja `magnitude.md` | Vulkan na gfx1100 działa (RADV, user-local ICD); pierwszy start 95.6 s (prep 70.7 s), z cache 23–26 s; autotune 67/67 i 21/21 canonical defaults, 0 pomiarów (`logs/*.mag.first.tuning.jsonl`); wymagania Vulkan `inference/docs/compatibility.md:100-150`. |
| `produkt/` | aktualizacja `produkt-ryzyka.md` | Pozycja „Magnitude na XTX przez Vulkan: niezmierzone (E-X5)” → zmierzone: my ×1.94–×2.22 (Qwen 27B), ×1.42–×2.24 (LFM); VRAM szczyt 20.2 vs 22.9 GB (Qwen). Przewaga Magnitude na AMD: tylko instalacja bez ROCm. |
| `hardware/` | aktualizacja notatki XTX | User-local Vulkan bez sudo: `apt-get download libvulkan1 mesa-vulkan-drivers libllvm20 …` + `dpkg -x` do `~/.local/vk/root`, ICD ze ścieżką absolutną, `. ~/.local/vk/env.sh`; `vulkaninfo`: RADV NAVI31, API 1.4.318. |
| `research/` | `raport-16j-magnitude-vulkan-xtx.md` (strona hub) | Link do tego raportu; zamyka E-X5 z 16i §8 („przegrywają z naszym HIP” — potwierdzone, mvs < 1.2× → bez priorytetu). |
