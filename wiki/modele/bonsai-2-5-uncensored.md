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
  - bonsai-2-5-uncensored | rx-7900-xtx | 106.0 t/s | czat T=0,7, topka-bonsai PM4 + env produkcji + MTP n2 + słownik draftu 64k, ctx 262144 | 2026-11-25
  - bonsai-2-5-uncensored | rx-7900-xtx | 77.7 t/s | czat T=0,7, prism Q2_0 + MTP n2, KV q4_0 | 2026-11-25
  - bonsai-2-5-uncensored | rx-7900-xtx | 237.8 t/s | edycja/kopia kodu T=0 (copy_bench short), topka PM4 + MTP n2 + lookup W7 + słownik 64k | 2026-11-25
  - bonsai-2-5-uncensored | rx-7900-xtx | 117.9 t/s | dekod T=0 (Q4 160 tok.), prism Q2_0 + MTP n2 | 2026-11-25
  - bonsai-2-5-uncensored | rx-7900-xtx | 188.4 t/s | dekod T=0 (Q4), MTP n2 + ngram-mod | 2026-11-25
  - bonsai-2-5-uncensored | rx-7900-xtx | 54.9 t/s | llama-bench tg128 bez spekulacji, Q2_0 | 2026-11-25
---
# Ternary Bonsai 2.5 27B Uncensored (AtomicChat)

**Bonsai 2.5 bez cenzury od AtomicChat to Qwen3.8-27B w trytach (5,99 GB); na XTX najszybciej idzie w naszej topce z portem Hadamarda i PM4 jako bezstratny Q2_0 z MTP n2: przy pełnym kontekście 262k czat T=0,7 106,0 t/s, greedy do 174 t/s.**

## Co to jest
- Baza: PrismML Ternary Bonsai 2.5 27B (Qwen3.8-27B, hybryda 75% liniowej / 25% pełnej uwagi, tryty g128 w bazie Hadamarda, 1,76 bpw), wydanie „agentowe”: tool calling 77,2 vs 77,7 FP16 (README prism-ml).
- AtomicChat: projekcja kierunku odmowy wpieczona w kody trytów warstw 27–44 (36 macierzy, 12 461 746 kodów), skale FP16 i reszta pliku bez zmian. Odmowy 24/24 → 0/24, MMLU 401 → 406/500 (p = 0,30, czyli bez różnicy) według ich `evaluation-v2.json`. Plik nie ma głowicy MTP. Druga droga: LoRA 8,67 MB na oryginale (skala 1,25).
- SHA-256 pobranego pliku zgodne z ich `evaluation-v2.json` (f6b5f856…).

## Jak to uruchamiamy (2026-11-25)
- **Przepakowanie bez strat** (`qwen-opt/bonsai25/build_b25.py`): PTQ1_0 (128 trytów + fp16 d) → dwa bloki Q2_0 (kod = tryt, ta sama skala); test na 2000 losowych blokach: różnica 0,0. Nieedytowane tensory naszego Q2_0 są bajt w bajt takie jak w oficjalnym Q2_0-mtp PrismML (4 tensory po 8 MiB sprawdzone zakresami HTTP), edytowany `blk.30.ffn_down` się różni, czyli tak jak powinien.
- **Głowica MTP** (`blk.64.*`, Q4_0, 239 MB) z oficjalnego PTQ1_0-mtp PrismML pobrana zakresem bajtów; nagłówek z pliku -mtp (block_count 65, nextn 1), reszta KV identyczna. Rozmiary wyników równe oficjalnym plikom -mtp (6 232 818 944 i 7 912 178 944 B).
- **Silnik**: fork PrismML `910442b` (2026-11-24) zbudowany na ROCm 10.0 gfx1100 z dwiema brakującymi definicjami HIP (`prism-hip-event-defines.patch`). Upstream `6792507b7` też czyta Q2_0 + Hadamard, ale jest wolniejszy. Nasza topka (baza b11528) nie zna `prism.hadamard`, więc wymaga portu (K-151).
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
- Akceptacja MTP: n2 0,76–0,79, n3 0,63–0,70, n4 0,58–0,61.
- PPL (40 × 512, korpus xtxbench, prism): PTQ1_0 5,6002 ± 0,146, Q2_0 5,5703 ± 0,144. Te same wagi, różnica w granicach błędu i pochodzi z kerneli.

## Dlaczego tak (profil rocprofv3, Q2_0, dekod)
- Mnożenia Q2_0 (MMVQ) zajmują 68% czasu GPU, ok. 10 ms na token przy ok. 7,3 GB wag, czyli ok. 730 GB/s (76% pasma). Kernel Q2_0 jest już blisko pasma.
- Między tokenami jest ok. 3,4 ms (19%) przerwy po stronie hosta: GPU 14,8 ms na token wobec 18,2 ms zegara. FWHT 3,7%, quantize_q8_1 3,5%.
- PTQ1_0 na HIP liczy, a nie czyta: n=1 daje 446–583 GB/s z cache, a n=4 trwa 3,8× dłużej niż n=1 (q4_0: 1,2×). Dlatego weryfikacja MTP na PTQ1_0 jest wolniejsza niż bez spekulacji. Plik jest o 21% mniejszy, więc dobry kernel PTQ1_0 dla RDNA3 (n = 1–4) to największa dźwignia (K-149).

<!-- TABELE:START -->
## Wyniki z notatek (4)

Najlepszy wynik na metrykę z pól `wynik` notatek testów (tools/tabele.py, 2026-11-25); pełna tabela: [[najlepsze-wyniki]].

| karta | metryka | najlepszy | warunki | data | źródło |
|---|---|---|---|---|---|
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | czat T=0,7, prism Q2_0 + MTP n2, KV q4_0 | **77.7 t/s** |  | 2026-11-25 | [[bonsai-2-5-uncensored]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod T=0 (Q4 160 tok.), prism Q2_0 + MTP n2 | **117.9 t/s** |  | 2026-11-25 | [[bonsai-2-5-uncensored]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod T=0 (Q4), MTP n2 + ngram-mod | **188.4 t/s** |  | 2026-11-25 | [[bonsai-2-5-uncensored]] |
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
- Grok (X, 14 dni): nikt nie publikował Bonsai 2.5 na 7900 XTX; producent: RTX 4090 bez spekulacji 111, z MTP n3 p-min 0,1 204 t/s; RTX 3060 przy 262k 74 t/s z MTP.

## Powiązane
- [[bonsai]]
- [[prism-llama-cpp]]
- [[uncensored-ablacja-kierunku]]
- [[glowica-mtp]]
- [[qwen3-8-27b-uncensored]]
- [[rx-7900-xtx]]
