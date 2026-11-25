---
typ: model
tags: [modele, kwanty, qwen, uncensored, ternary]
aktualizacja: 2026-11-25
zrodlo: https://huggingface.co/AtomicChat/Ternary-Bonsai-2.5-27B-Uncensored-GGUF (README, evaluation-v2.json); https://huggingface.co/prism-ml/Ternary-Bonsai-2.5-27B-GGUF (README); ~/qwen-opt/queue/logs/b25-*.log (jaroserverai); ~/KERNEL/qwen-opt/bonsai25/
status: aktualne
model: bonsai-2-5-uncensored
rozmiar: 27B
kwant: PTQ1_0, Q2_0
karty: rx-7900-xtx
wyniki:
  - bonsai-2-5-uncensored | rx-7900-xtx | 116.9 t/s | czat T=0,7, topka-k157 PM4 + env produkcji + MTP n2 + słownik 64k, ctx 262144 | 2026-11-25
  - bonsai-2-5-uncensored | rx-7900-xtx | 446.4 t/s | edycja/kopia kodu T=0 (copy_bench short), topka-k157 | 2026-11-25
  - bonsai-2-5-uncensored | rx-7900-xtx | 76.9 t/s | dekod bez spekulacji, topka-k157 PM4 | 2026-11-25
  - bonsai-2-5-uncensored | rx-7900-xtx | 106.0 t/s | czat T=0,7, topka-bonsai PM4 + env produkcji + MTP n2 + słownik draftu 64k, ctx 262144 | 2026-11-25
  - bonsai-2-5-uncensored | rx-7900-xtx | 77.7 t/s | czat T=0,7, prism Q2_0 + MTP n2, KV q4_0 | 2026-11-25
  - bonsai-2-5-uncensored | rx-7900-xtx | 426.1 t/s | edycja/kopia kodu T=0 (copy_bench short, mediana), topka-best PM4 + MTP n2 + lookup W16 + słownik 64k | 2026-11-25
  - bonsai-2-5-uncensored | rx-7900-xtx | 70.6 t/s | dekod bez spekulacji, topka-best PM4, ctx 262144 | 2026-11-25
  - bonsai-2-5-uncensored | rx-7900-xtx | 121.9 t/s | konfiguracja Dogukana (temp 1,0) na topka-best, MTP n2 | 2026-11-25
  - bonsai-2-5-uncensored | rx-7900-xtx | 117.9 t/s | dekod T=0 (Q4 160 tok.), prism Q2_0 + MTP n2 | 2026-11-25
  - bonsai-2-5-uncensored | rx-7900-xtx | 188.4 t/s | dekod T=0 (Q4), MTP n2 + ngram-mod | 2026-11-25
  - bonsai-2-5-uncensored | rx-7900-xtx | 54.9 t/s | llama-bench tg128 bez spekulacji, Q2_0 | 2026-11-25
---
# Ternary Bonsai 2.5 27B Uncensored (AtomicChat)

**Bonsai 2.5 bez cenzury od AtomicChat to Qwen3.8-27B w trytach (5,99 GB); na XTX najszybciej idzie w naszej topce (`topka-k157`: port Hadamarda, PM4, 4 nowe łatki) jako bezstratny Q2_0 z MTP n2: przy pełnym kontekście 262k czat T=0,7 115–117 t/s, edycja kodu 434–446 t/s, bez spekulacji 76,7 t/s.**

## Co to jest
- Baza: PrismML Ternary Bonsai 2.5 27B (Qwen3.8-27B, hybryda 75% liniowej / 25% pełnej uwagi, tryty g128 w bazie Hadamarda, 1,76 bpw), wydanie „agentowe”: tool calling 77,2 vs 77,7 FP16 (README prism-ml).
- AtomicChat: projekcja kierunku odmowy wpieczona w kody trytów warstw 27–44 (36 macierzy, 12 461 746 kodów), skale FP16 i reszta pliku bez zmian. Odmowy 24/24 → 0/24, MMLU 401 → 406/500 (p = 0,30, czyli bez różnicy) według ich `evaluation-v2.json`. Plik nie ma głowicy MTP. Druga droga: LoRA 8,67 MB na oryginale (skala 1,25).
- SHA-256 pobranego pliku zgodne z ich `evaluation-v2.json` (f6b5f856…).

## Jak to uruchamiamy (2026-11-25)
- **Przepakowanie bez strat** (`qwen-opt/bonsai25/build_b25.py`): PTQ1_0 (128 trytów + fp16 d) → dwa bloki Q2_0 (kod = tryt, ta sama skala); test na 2000 losowych blokach: różnica 0,0. Nieedytowane tensory naszego Q2_0 są bajt w bajt takie jak w oficjalnym Q2_0-mtp PrismML (4 tensory po 8 MiB sprawdzone zakresami HTTP), edytowany `blk.30.ffn_down` się różni, czyli tak jak powinien.
- **Głowica MTP** (`blk.64.*`, Q4_0, 239 MB) z oficjalnego PTQ1_0-mtp PrismML pobrana zakresem bajtów; nagłówek z pliku -mtp (block_count 65, nextn 1), reszta KV identyczna. Rozmiary wyników równe oficjalnym plikom -mtp (6 232 818 944 i 7 912 178 944 B).
- **Silnik**: fork PrismML `910442b` (2026-11-24) zbudowany na ROCm 10.0 gfx1100 z dwiema brakującymi definicjami HIP (`prism-hip-event-defines.patch`). Upstream `6792507b7` też czyta Q2_0 + Hadamard, ale jest wolniejszy. Nasza topka (baza b11528) nie zna `prism.hadamard`, więc wymaga portu (K-151).
- Na jaroserverai zostaje tylko `Ternary-Bonsai-2.5-27B-Uncensored-Q2_0-mtp.gguf` (PTQ1_0-mtp usunięty 2026-11-25 przy 0,9 GB wolnego dysku; odtwarza go `build_b25.py`).
- Start: `qwen-opt/bonsai25/serve.sh` (port 18796, KV q4_0, MTP n2).

## Wyniki na XTX (xbench, KV q4_0, PM4=0, 2026-11-25)
| silnik / plik / spekulacja | Q1 T=0 | Q4 T=0 | **T=0,7** | L2k | L8k | prefill 2k / 8k |
|---|---|---|---|---|---|---|
| prism PTQ1_0, bez | 53,2 | 53,4 | 54,0 | 52,5 | 51,3 | 665 / 671 |
| prism PTQ1_0, MTP n3 | 53,7 | 63,8 | 33,8 | 44,8 | 44,9 | 609 / 649 |
| upstream Q2_0, bez | 47,3 | 48,8 | 49,0 | 48,3 | 47,4 | 822 / 857 |
| upstream Q2_0, MTP n3 | 94,3 | 119,2 | 65,8 | 83,9 | 80,5 | 805 / 832 |
| prism Q2_0, bez | 53,8 | 53,8 | 54,4 | 53,3 | 52,0 | 808 / 833 |
| **prism Q2_0, MTP n2** (2 przebiegi) | 87,8 | 117,6–117,9 | **77,5–77,7** | 97,5 | 92,3–92,6 | 731–733 / 788–791 |
| prism Q2_0, MTP n3 (2 przebiegi) | 103,7–103,8 | 132,3 | 70,2–70,4 | 92,9 | 93,4–94,0 | 725–730 / 787–789 |
| prism Q2_0, MTP n4 | 93,6 | 139,3 | 61,1 | 89,8 | 87,2 | 731 / 793 |
| prism Q2_0, MTP n2 + ngram-mod | 88,2 | **188,4** | 78,2 | 97,8 | 76,0 | 727 / 790 |
| prism Q2_0, MTP n3 + ngram-mod | 103,6 | 188,1 | 69,3 | 92,9 | 74,4 | 728 / 791 |
| prism Q2_0, MTP n3, p-min 0,5 | 104,4 | 132,3 | 67,8 | 88,7 | 82,0 | 727 / 794 |
| prism Q2_0, MTP n4, p-min 0,7 | 94,4 | 138,6 | 66,5 | 85,5 | 80,4 | 728 / 787 |

- llama-bench tg128 bez spekulacji: Q2_0 54,88, PTQ1_0 54,38; pp512 886 / 717.
- Akceptacja MTP: n2 0,76–0,79, n3 0,63–0,70, n4 0,58–0,61. **Uwaga 2026-11-25:** te liczby (i DFlash2 0,27–0,40) pochodzą z zapytań L2k/L8k przy T=0 (`tail -2` w `b25.sh`), nie z T=0,7; akceptację przy T=0,7 mierzy dopiero `drafter-gate.sh`. GGUF 2.5 ma domyślne próbkowanie top_k 20, top_p 0,95, min_p 0,05, więc nasze biegi T=0,7 nigdy nie były na pełnym rozkładzie. W topce `src/models/dflash.cpp:693` drafter pożycza `token_embd` bez odwrotnego Hadamarda (prism go stosuje): wyniki DFlash/DSpark na Bonsai w topce są nieważne do poprawki. Plan draftera: `qwen-opt/bonsai25/drafter-plan.md`.
- PPL (40 × 512, korpus xtxbench, prism): PTQ1_0 5,6002 ± 0,146, Q2_0 5,5703 ± 0,144. Te same wagi, różnica w granicach błędu i pochodzi z kerneli.

## Dlaczego tak (profil rocprofv3, Q2_0, dekod)
- Mnożenia Q2_0 (MMVQ) zajmują 68% czasu GPU, ok. 10 ms na token przy ok. 7,3 GB wag, czyli ok. 730 GB/s (76% pasma). Kernel Q2_0 jest już blisko pasma.
- Między tokenami jest ok. 3,4 ms (19%) przerwy po stronie hosta: GPU 14,8 ms na token wobec 18,2 ms zegara. FWHT 3,7%, quantize_q8_1 3,5%.
- PTQ1_0 na HIP liczy, a nie czyta: n=1 daje 446–583 GB/s z cache, a n=4 trwa 3,8× dłużej niż n=1 (q4_0: 1,2×). Dlatego weryfikacja MTP na PTQ1_0 jest wolniejsza niż bez spekulacji. Plik jest o 21% mniejszy, więc dobry kernel PTQ1_0 dla RDNA3 (n = 1–4) to największa dźwignia (K-149).

<!-- TABELE:START -->
## Wyniki z notatek (11)

Najlepszy wynik na metrykę z pól `wynik` notatek testów (tools/tabele.py, 2026-11-25); pełna tabela: [[najlepsze-wyniki]].

| karta | metryka | najlepszy | warunki | data | źródło |
|---|---|---|---|---|---|
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | czat T=0,7, prism Q2_0 + MTP n2, KV q4_0 | **77.7 t/s** |  | 2026-11-25 | [[bonsai-2-5-uncensored]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | czat T=0,7, topka-bonsai PM4 + env produkcji + MTP n2 + słownik draftu 64k, ctx 262144 | **106.0 t/s** |  | 2026-11-25 | [[bonsai-2-5-uncensored]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | czat T=0,7, topka-k157 PM4 + env produkcji + MTP n2 + słownik 64k, ctx 262144 | **116.9 t/s** |  | 2026-11-25 | [[bonsai-2-5-uncensored]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod bez spekulacji, topka-best PM4, ctx 262144 | **70.6 t/s** |  | 2026-11-25 | [[bonsai-2-5-uncensored]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod bez spekulacji, topka-k157 PM4 | **76.9 t/s** |  | 2026-11-25 | [[bonsai-2-5-uncensored]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod T=0 (Q4 160 tok.), prism Q2_0 + MTP n2 | **117.9 t/s** |  | 2026-11-25 | [[bonsai-2-5-uncensored]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod T=0 (Q4), MTP n2 + ngram-mod | **188.4 t/s** |  | 2026-11-25 | [[bonsai-2-5-uncensored]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | edycja/kopia kodu T=0 (copy_bench short), topka-k157 | **446.4 t/s** |  | 2026-11-25 | [[bonsai-2-5-uncensored]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | edycja/kopia kodu T=0 (copy_bench short, mediana), topka-best PM4 + MTP n2 + lookup W16 + słownik 64k | **426.1 t/s** |  | 2026-11-25 | [[bonsai-2-5-uncensored]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | konfiguracja Dogukana (temp 1,0) na topka-best, MTP n2 | **121.9 t/s** |  | 2026-11-25 | [[bonsai-2-5-uncensored]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | llama-bench tg128 bez spekulacji, Q2_0 | **54.9 t/s** |  | 2026-11-25 | [[bonsai-2-5-uncensored]] |
<!-- TABELE:END -->

## Runda 2 (2026-11-25, polecenie JARO: pełny kontekst, cel 200 t/s)
- **Pełny kontekst 262 144** (KV q4_0) nic nie kosztuje: prism MTP n2 przy 32k 77,7, przy 262k 77,6 t/s.
- **K-151 port do topki** (`topka-bonsai` c76335b: upstream #29600, runtime prism.hadamard + przenoszenie transformacji na głowicę draftu, słownik i requant): bez PM4 T=0,7 78,2; **z PM4** 91,4; **z env produkcji** (lookup W16, coupled, GPU verify, yield fast, PM4 min dispatch/lazy) 101,7 / 102,8; **+ słownik draftu 64k: 106,0 t/s** (Q1 116,6, Q4 141,9, L2k 118,3, L8k 127,3). MTP n3 + słownik 64k: Q4 174,1, T=0,7 92,6; IQ4_XS głowicy draftu nic nie daje przy T=0,7 (101,3).
- **K-149 kernel PTQ1_0 PT na HIP** (agent, `prism-ptq1-hip.patch`): test-backend-ops MUL_MAT 255/255, fuzje 120/120, MUL_MAT_ID 85/85; 17408×5120 n=1 43,7 → 27,1 µs, n=4 167 → 43,1 µs (×3,9). End-to-end prism PTQ1_0 MTP n2: T=0,7 33,8 → 75,9 (tyle co Q2_0), bo resztę zjada przerwa hosta.
- **DFlash2 dla Qwen3.8-27B na Bonsai** (Q4_K_M, n 6/8/12): T=0 do 159 t/s, ale T=0,7 38,6–41,7 (akceptacja 0,27–0,40): odrzucone.
- **Profil kroku MTP (prism, serwer)**: 216 tys. kerneli na 200 tokenów (ok. 1080 na token), GPU zajęte 67%, mediana przerwy między kernelami 3,44 µs: przerwy to 33% czasu, dlatego PM4 (taśma bez AQL) daje tu +17%.
- **K-150 (Gemini, przegląd forka prism)**: fuzje FWHT+q8_1, norm+FWHT, łańcuch GDN conv i para ssm_beta/alpha są w forku tylko dla NVIDIA (`GGML_CUDA_CC_IS_NVIDIA`), na HIP nieużywane: ok. 800 zbędnych kerneli na token; łatka `prism-k150-gemini.patch` w budowie, przeniesienie do topki w toku.
- **K-150 Gemini na forku prism** (`prism-k150-gemini.patch`): test-backend-ops MUL_MAT 3150/3150, fuzje 1745/1745, RMS_NORM 53/53, SSM_CONV 60/60; llama-bench tg128 54,9 → **61,4 t/s (+11,9%)**, serwer MTP n2 T=0,7 77,6 → **86,5 (+11,5%)**, akceptacja bez zmian. Przeniesienie tych fuzji do topki w toku (Gemini, K-150T).
- **Przepisywanie i edycja kodu** (`copy_bench.py`, zestaw short, 512 tok., topka PM4 + env produkcji + MTP n2 + słownik 64k): okno lookupu 16 → mediana 174 t/s; **okno 7 → 237,8 t/s przy T=0 i 229,1 przy T=0,7** (edit 2k/8k 236–243); okno 11 → 129,8. Przyczyna: krok weryfikacji ≤ 8 tokenów kosztuje 27 ms, 9–16 tokenów 74–80 ms (Q2_0 poza ścieżką MMVQ). Naprawa w toku (K-154).
- **K-153 PTQ1_0 w topce** (`topka-ptq1.patch`, dee979b): test-backend-ops MUL_MAT 81/81, fuzje 105/105, GET_ROWS 12/12; ale z PM4 T=0,7 102,4 (Q2_0 105,0), edycja 188,7 (Q2_0 232,7): mniejszy plik nie pomaga, bo MMVQ Q2_0 w topce jest już szybszy niż kernel PT. Zostaje Q2_0.
- **Konfiguracja Doğukana z RTX 3060** (X 2026-11-24: 262k, PTQ1_0-mtp, MTP n3 p-min 0, temp 1,0; u niego ~74 t/s, bez MTP 47) odtworzona na XTX (5 odpowiedzi po 400 tok., temp 1,0, top-p 0,95, top-k 20): prism PTQ1_0 jak u niego **39,8 t/s** (na HIP wolniej niż jego 3060), prism + nasz kernel PT 83,3, **topka PM4 Q2_0 + słownik 64k 106,3**, topka PM4 PTQ1_0 97,1. 3060 ma 360 GB/s, XTX 960 GB/s: przy tej samej sprawności XTX powinien dać ok. 2,7× (ok. 200 t/s), ma 1,44×. Różnica to oprogramowanie HIP (przerwy między kernelami, fuzje tylko dla NVIDIA, wolna weryfikacja > 8 tokenów), nie karta.
- **K-150T (Gemini) w topce**: test-backend-ops MUL_MAT 2496/2496, RMS_NORM 53/53, fuzje 1265/1265; z PM4 T=0,7 107,5 → 110,6 (+2,9%), edycja 238,6 → 247,3 (+3,6%), L8k +4%.
- **K-154 (agent) Q2_0 w kernelu WMMA dla 9–16 kolumn**: MUL_MAT 117/117, MUL_MAT_ADD 42/42; krok 14 tokenów 79 → 61 ms, edycja W16 174 → 218 t/s. Profil n=16: 47% czasu GPU to hipBLAS SGEMM 280 µs × 96 na krok dla cienkich wag F32 GDN (`ssm_alpha`/`ssm_beta`, 48 wierszy), bo MMVF bierze tylko ≤ 8 kolumn.
- **K-155 (Kernel) MMVF w porcjach po 8 kolumn zamiast hipBLAS** (`topka-k155-mmvf-split.patch`, env `GGML_HIP_K155_MMVF_SPLIT`): MUL_MAT f32 275/275, f16 361/361; krok 14 tokenów 58 → 31 ms; **edycja/kopia kodu W16: 236,6 → 426,1 t/s przy T=0 i 422,2 przy T=0,7** (edit 8k 452,6), Q4 greedy 265,5.
- **topka-best** (`~/wt/topka-best`: port Hadamarda + K-150T + K-154 + K-155): bez spekulacji 70,6 t/s (prism 54,9; +29%), czat T=0,7 MTP n2 106,5–108,0 (±3% szumu), konfiguracja Doğukana temp 1,0: 116,0 (n3) / 121,9 (n2) t/s wobec jego 74 na 3060.
- **Profil topka-best (PM4 wył.)**: GPU 14,2 ms na token, PM4 zjada przerwy całkowicie (70,6 t/s = 14,2 ms); MMVQ Q2_0 74% (ok. 10,5 ms, ok. 695 GB/s, 72% pasma). Następna dźwignia: kernel Q2_0 n=1–3 (K-156, agent).
- **K-156 (agent) kernel Q2_0 n=1–3** (`topka-k156.patch`, env `GGML_HIP_K156`, `_ROWS`): testy 2/4 wierszy: MUL_MAT 138/138, MUL_MAT_ADD 60/60, PAIR 4/4, fuzje 105/105, FFN 2/2; mikrobench 17408×5120 n=1 31 → 16,3 µs (dane z Infinity Cache), ale **end-to-end bez zmian**: bez spekulacji 70,1 vs 70,3, czat T=0,7 105,7 vs 106,1. Wniosek: w dekodzie MMVQ Q2_0 jest ograniczony pasmem DRAM (ok. 695 GB/s przy całym kroku), nie kodem pętli; mikrobench na jednej macierzy mieszczącej się w 96 MB cache kłamie. Nie wdrażamy.
- **K-157 (Gemini) drobne kernele** (`topka-k157-gemini.patch`: wieloblokowy `add_rms_norm_fwht`, FWHT na DPP z 2 barierami, fuzja GDN alpha/beta F32 z ogonem, fuzja `ADD→SOFTPLUS→MUL`, cienki MMVF): testy MUL_MAT 2531/2531, RMS_NORM 53/53, fuzje 1265/1265, SSM_CONV 45/45; bez spekulacji 70,8 → **76,9 t/s (+8,6%)**, czat T=0,7 106,7 → **116,9 (+9,6%)**, edycja 446,4, L8k 143,7. Ablacja md5 greedy: NORM_FWHT, FWHT_DPP, GDN_TAIL bit w bit; tylko MMVF_THIN zmienia zaokrąglenie; z `GGML_HIP_K157_MMVF_THIN=0` odpowiedzi identyczne z topka-best i szybkość ta sama (76,7 / 115,2 / 434–439). K-150T bit w bit z bazowym portem (68c39468).
- **KLD (40 × 512, korpus xtxbench) topka-k157 vs bazowy port c76335b**: średnie KLD 0,000000, maks. 0,000059, ten sam top-1 100%, PPL 5,5709 vs 5,5692. Różnice od K-154/K-155 (prefill krótkich promptów inną ścieżką) to zaokrąglenia, nie strata.
- **Runda 3 (2026-11-25, polecenie JARO: metoda Nib dla ternary).** Księga kosztu weryfikacji (`qwen-opt/bonsai25/b25-ledger.sh`: llama-bench pp m @ d1024, topka-rt, env produkcji, ±10%): m=2 15,5 ms, m=3 16,5, m=4 17,9, m=5 21,2, m=8 26,9, m=16 30,1 ms; zwykły token ok. 13 ms (76,9 t/s). Przy d8192 tak samo. Weryfikacja 3 tokenów kosztuje ok. 1,27 tokenu, 8 tokenów ok. 2,1 (gęsty model, wagi czytane raz), więc odwrotnie niż w Inklingu (MoE: okno 8 = 5,1 tokenu): dźwignią jest liczba przyjętych tokenów na rundę (drafter i szerokość okna), nie koszt weryfikacji.
- **Szerokość okna MTP z p-min (topka-k157, PM4, env produkcji, słownik 64k, xbench Q1 / Q4 T=0 / Q6 T=0,7 / L2k / L8k):** n2 128,4 / 275,0 / **114,5** / **137,7** / **145,3**; n3 p0,5 150,8 / 297,1 / 111,4 / 108,5 / 124,0; n4 p0,6 133,8 / 284,8 / 105,3 / 116,4 / 119,2; n6 p0,7 **180,3** / 285,4 / 107,0 / 93,6 / 118,2; n6 p0,8 171,2 / 280,3 / 101,2 / 103,6 / 117,6; n8 p0,9 148,1 / 285,2 / 99,0 / 104,0 / 108,5. Szersze okno daje +40% na krótkim T=0, ale traci przy T=0,7 i na długim kontekście: kroki MTP idą po kolei (każdy ok. 1 ms), a z p-min > 0 drafting nie jest jednym grafem. Produkcyjnie zostaje n2; dźwignia to tańszy łańcuch draftu w jednym grafie z oknem wg pewności (agent BonsaiConfWindow) i lepszy drafter.
- **drafter-gate (wall.py 4 kategorie × 300 tok., top-k 20 / top-p 0,95 jawnie, topka-k157 PM4 + env produkcji, 2026-11-25):** MTP n2 T=0 139,4 (code 139,8, tech 139,1, **pl 106,6**, json 172,2), **T=0,7 145,4** (code 151,0, tech 139,7, pl 99,5, json 168,8); pełny rozkład (top_k 0) T=0,7 133,3; MTP n3 138,3 / 135,8. Syntetyczna akceptacja (`--spec-synth-rates`, koszt bez zależności od draftera): krzywa „DFlash” 0,75/0,55/0,40/… przy n3/n4/n5/n7: T=0,7 118,7 / 112,7 / 115,8 / 91,1, krzywa MTP n2/n3/n4: 127,5 / 125,4 / 114,1. Wniosek: w obecnej ścieżce draft-dflash topki drafter blokowy z typową akceptacją nie pobije MTP n2 (reguła planu: < 125 t/s = najpierw tańsza runda); polski jest najwolniejszy (99,5–106,6).
- **E1 naprawione (topka-dsp 431b9b0e7, `qwen-opt/bonsai25/topka-e1-draft-hdmd.patch`):** draftery DFlash/DSpark/EAGLE-3 pożyczają `token_embd` i `output` od celu, a kontekst draftu nie widział transformacji Hadamarda celu, więc każdy pomiar DFlash/DSpark na Bonsai w topce był zepsuty. Teraz kontekst bez własnych transformacji bierze je od celu (jak prism). Pobrany DSpark z głowicą pewności: magnitudedev Q8_0 1,46 GB (`~/models/draft/Qwen3.8-27B-DSpark-Q8_0.gguf`). Pomiar akceptacji: `dsp.jobs`.
- **Mikrobench pasma Q2_0 (`test-mmvq-bw`, gałąź topka-bw 726ee7c83):** dzisiejszy kernel dekodu trzyma na falę tylko 288 B wag w locie i nie robi prefetchu; nowe warianty `GGML_HIP_Q2BW*` (prefetch partiami U, wiersze na falę R, fale na blok, nontemporal, ładowania 128-bit) bit w bit; wyniki z `bw.jobs`.
- **K-169 okno pewności MTP jak w Nib (topka-conf 4fa1df911, wszystko domyślnie wyłączone):** `LLAMA_SPEC_CONF=próg` drafuje do N tokenów w jednym grafie i weryfikuje wiodące drafty z p > próg; wczesne wyjście na GPU (flaga w grafie strzeże MMVQ kolejnych kroków, pominięty krok pisze zera), `LLAMA_SPEC_GATE=1` bramka per zapytanie, linia statystyk `request rounds`. Nadal 2 synchronizacje hosta na rundę. Pomiar: `qwen-opt/bonsai25/conf.jobs` (parytet md5, xbench c0,6/0,7/0,8 ± bramka, wall z `pl`).
- Grok (X, 14 dni): nikt nie publikował Bonsai 2.5 na 7900 XTX; producent: RTX 4090 bez spekulacji 111, z MTP n3 p-min 0,1 204 t/s; RTX 3060 przy 262k 74 t/s z MTP.

## Powiązane
- [[bonsai]]
- [[prism-llama-cpp]]
- [[uncensored-ablacja-kierunku]]
- [[glowica-mtp]]
- [[qwen3-8-27b-uncensored]]
- [[rx-7900-xtx]]
