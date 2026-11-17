---
typ: eksperyment
tags: [eksperymenty, nvidia, vast, mtp, sufit, enigma, k114]
aktualizacja: 2026-11-17
zrodlo: qwen-opt/cloud/k114/{run.sh,run2.sh,pf.py,pdl.sh,launch.sh,summ.py}; wyniki qwen-opt/cloud/k114/res/{3090,5060ti,3060}/ (bench.jsonl, prefill.jsonl, smi.csv, gpu.csv); `python3 summ.py res/3090 res/5060ti res/3060`
status: aktualne
---
# 2026-11-17 K-114: nasz silnik CUDA na 3090, 5060 Ti i 3060 względem sufitu — czas kroku zjadają drafty, a na Vaście limity hosta

**Zmierzone (Vast, $0,33):**
- 5060 Ti: 51–54 t/s, czyli 51–61% sufitu.
- 3060: 28–31 t/s, czyli 34–43% sufitu.
- 3090: 44–47 t/s, czyli 22–23% sufitu. Host trzymał pamięć na 5001 MHz zamiast 9751 i limit 250 W.

**Odpowiedź na hipotezę K-114:**
- (b) potwierdzona: każdy draft MTP kosztuje 4,8–9 ms, podczas gdy jego bajty to ~1 ms. Przy n4 drafty to 37–40% kroku.
- (a) obalona: próbkowanie przy T=1 nie wydłuża kroku; strata wynika z akceptacji.
- (c) potwierdzona na hostach 3090 i 3060.

**Warunki:**
- Model na wszystkich kartach ten sam: Qwen3.8-27B GSQ-RCO IQ3_XXS-mtp (10,44 GB). Silnik: fork Enigmy `kvqlean` (wydanie `enigma-engines-cuda-2026-11-07`), flagi przepisu: KV q4_0, słownik draftu 64k, głowica i MTP IQ4_XS, `GGML_CUDA_KVQ=1`, lookup W16, `GPU_VERIFY=1`, ctx 8192, ub 256.
- Dekod: `bench.py` z R69b, 6 promptów × T 0/1, 400 tok., mediana, liczby z zegara serwera.
- Tok./krok = n ÷ (n − zaakceptowane). Krok = tok./krok ÷ t/s.
- Przebieg celu: serwer bez spekulacji, T=0.
- Prefill: zimny unikalny dokument przez serwer (`pf.py`), 2 powtórzenia.
- Sufity metodą `ceiling.py` ([[skill-io-sufity]]):
  - dekod: pasmo ze specyfikacji ÷ ((10,34 GB + n × 0,40 GB draftu) ÷ tok./krok);
  - prefill: 50% gęstego szczytu INT8 ÷ FLOP/token.
- Archiwum nie ma `llama-bench`, więc tg128 i pp5 zastąpione pomiarem przez serwer.

| karta (host) | limit mocy / pamięć pod obciążeniem | plain t/s (% sufitu) | MTP n2 T=0 / T=1 t/s (% sufitu) | MTP n4 T=0 / T=1 t/s (% sufitu) | prefill ~3,2k / ~11k t/s (% sufitu) |
|---|---|---|---|---|---|
| RTX 5060 Ti (VN) | 180 W (141 W zużyte), 13 801 MHz = pełna | 31,9 (74%) | **54,2 / 51,0** (60% / 61%) | 53,9 / 49,4 (52% / 51%) | 788 / 828 (43% / 47%) |
| RTX 3060 (VN) | **135 W z 170, przyklejone**, 85 °C, SM 1537 MHz | 18,4 (53%) | **30,8 / 28,6** (43% / 42%) | 30,9 / 28,0 (38% / 35%) | 461 / 442 (47% / 46%) |
| RTX 3090 (TW) | **250 W z 420; pamięć 5001 z 9751 MHz** | 30,6 (34%) | – (pominięte, opis niżej) | 47,1 / 44,4 (22% / 23%) | 319 / 696 (12% / 26%) |

**Czas kroku** (n4, T=0):
- 5060 Ti: 51,1 ms = cel 31,3 + 4 drafty × 4,8–5,2 ms;
- 3060: 87,8 ms = 54,4 + 4 × 7,6–9,1;
- 3090: 58,5 ms = 32,7 + 4 × 6,5.

Bajty jednego draftu (warstwa MTP + głowica 64k ≈ 0,4 GB) to 0,9 / 1,1 / 0,4 ms. **Draft kosztuje 4–15 × swoje bajty**, czyli krok jest zdominowany przez narzut małych kerneli i synchronizacji pętli draftu. Na XTX ten sam problem rozkłada K-111.

**Wnioski:**
1. **Hipoteza K-114 (b) potwierdzona.**
   - Gdyby draft kosztował tyle co jego bajty, krok n4 na 5060 Ti spadłby z 51 do ~36 ms, czyli **+40% dekodu** [INFERENCE: przy tej samej akceptacji].
   - Dźwignia: graf CUDA na całą pętlę draftu i fuzja kroku draftu (K-116).
2. **(a) obalona.** Przy T=1 krok jest ten sam (5060 Ti 51,1 → 52,2 ms; 3090 58,5 → 54,4) albo +8% (3060). Spadek t/s przy T=1 bierze się z akceptacji (0,42 → 0,35–0,40). Na tym silniku próbkowanie GPU nie jest wąskim gardłem; K-004 (port dokładnego próbkowania) dotyczy akceptacji, nie kosztu.
3. **(c) na Vaście wygrywa host, nie silnik.**
   - Host 3090 miał limit 250 W i pamięć GDDR6X na 5001 MHz. Przebieg celu osiągnął 316 GB/s (34% z 936), a prefill 12–26% sufitu.
   - Host 3060 był przyklejony do 135 W przy 85 °C.
   - Liczby z tych hostów to dolna granica, nie wynik karty. Wcześniejsza 3090 z R69b (350 W) robiła 82,9 t/s na Q4_K_XL.
4. **n2 lepsze niż n4** na 5060 Ti (T=1 49,4 → 51,0, +3,2%) i 3060 (28,0 → 28,6, +2,1%). Poniżej progu 3–5%, przepisy Enigmy bez zmian. Zgodne z `levers.md:29-34` skill-io: słabsze pasmo → krótszy draft.
5. **Start serwera na słabym CPU hosta (3090 TW): 12 min** ponownej kwantyzacji głowicy i MTP do IQ4_XS na CPU, a na 5060 Ti z 64 rdzeniami 32 s. Fork CUDA nie ma `LLAMA_MTP_REQUANT_CACHE` (XTX ma). Użytkownik Enigmy ze słabym CPU czeka minuty przy każdym starcie (K-117). Dlatego na 3090 pominięto n2 i n4-b.
6. **Sufit pasma 5060 Ti:** przebieg celu 74%, czyli MMVQ IQ3_XXS na Blackwell jest blisko XTX (77–88%). Luka do sufitu leży w drafcie, nie w głównym GEMV.

**Koszt i przebieg:**
- Kredyt $0,4925 → $0,1609, czyli **$0,33**: 3090 ~1,7 h, 5060 Ti ~0,6 h, 3060 w 4 podejściach.
- Trzy hosty 3060 odpadły: HF ~1–3 MB/s, SSH odrzucał klucz, instancja utknęła w „loading”.
- `pdl.sh` (16 zakresów HTTP) podniósł pobieranie na 3090 z ~2 do 16 MB/s.
- Wszystkie instancje usunięte (`vastai show instances` puste); [[lekcja-vastai-destroy-pyta]].

## Powiązane
- [[skill-io-sufity]]
- [[KOLEJKA-TESTOW]]
- [[final-recipes-nvidia]]
- [[2026-11-09-qwen-warp-vs-fork-3090]]
- [[lekcja-limit-mocy-hosta]]
