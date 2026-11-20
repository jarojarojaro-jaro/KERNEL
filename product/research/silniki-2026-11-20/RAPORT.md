# Research silników: co bierzemy do Enigma Turbo (2026-11-20)

Źródła: 6 notatek w `notes/` (klony z 2026-11-20 w `~/research/engines`). Liczby zysku dla Turbo to szacunki `[INFERENCE]`, chyba że oznaczone „zmierzone”. Research Gemini (Neon) przerwał limit modelu przed zapisem; tę pracę wykonało 6 agentów Kernela.

## Werdykt
- **Język zostaje: C++20 + HIP**, jedno źródło dla AMD i NVIDIA. Żaden DSL nie ma szybszych kerneli Q4_K/Q6_K na gfx1100:
  - TileLang: na gfx11 tylko f16/bf16, bez int8;
  - HipKittens: tylko CDNA;
  - Mojo/MAX: GGUF q4 liczy na CPU;
  - MLC: wymaga własnego formatu wag.
  
  Źródło: `notes/kernel-languages.md`.
- **vLLM i SGLang na pojedynczej karcie RDNA3 są wolniejsze od Turbo** (29–47 t/s, Turbo 45,9). Bierzemy od nich metody, nie kernele.
- **Najmocniejszy konkurent na XTX to hipfire** (Rust + HIP): 27B z MTP 136–141 t/s przy 1K. Ma jednak własny, mniejszy format wag i KV Q8, a poprawność sprawdza testem jakości, nie bit w bit.

## Ranking dźwigni (od największego zysku dla naszych trzech luk)

| # | Dźwignia | Źródło | Luka | Szac. zysk | Koszt | Bit w bit |
|---|---|---|---|---|---|---|
| 1 | Attention weryfikacji: blok na (głowa KV, zakres kluczy), wszystkie T tokenów × 6 głów q naraz, K/V czytane raz. Ten sam kernel dla dekodu i weryfikacji. | SGLang `verify_attention_gfx1151`: 8k 3,5 → 0,24 ms/warstwę; hipfire #989: +24% @39K, +57% @101K | długie prompty 95–99 → 120–140 t/s | duży | 3–4 dni | tak, gdy jeden kernel i stały podział kluczy |
| 2 | Ogon lookupu W=16 na `k_gemv_wide` + szybszy wide verify (cel 16 tok. ≈ 28–30 ms zamiast 51) | llama.cpp few-row MMQ #31533 (8 kolumn ×1,17–1,42; spec 3090 Ti +35%); hipfire +40% na kopiach | kopie, długie prompty | duży | 2–5 dni | tak (stała kolejność sum, już mamy) |
| 3 | Taśma PM4 zamiast `hipGraphLaunch` (port `hip-pm4.cu` z topki, łatka 0060) | granica kernela 3,6–3,9 → 0,5–0,9 µs; topka +6,4%; hipfire XTX 27B 53,4 → 62,5 t/s (×1,17) | wszystkie dekody | +5–7% | 3–5 dni | tak; ryzyko resetu karty (raport 17: PRIV, WA=2, guard) |
| 4 | Równoległy/chunkowany GDN w prefillu | llama.cpp PR #29353 (WMMA, wyłączony na gfx1100), vLLM `rdna35_gdn_chunked.cu`, FLA; u nas GDN 271 ms z 2480 (11%, zmierzone) | prefill 848 → ~920–960 t/s | +7–13% | 1–2 dni (więcej bloków), 3–4 dni (chunk) | prefill ≠ dekod numerycznie (dozwolone); multiturn działa wg kryterium replay |
| 5 | DFlash2 / drzewo weryfikacji przy T>0 | Qwen3.8-27B H200: MTP 178,5 → DFlash2 236,1 t/s (+32%); SGLang tree verify dla GDN | T=0,7 72 → ? | duży, ale potrzebny model draftu 1,92B | 5+ dni | sprzężone losowanie do przeniesienia |
| 6 | Polityka spekulacji liczona kosztem cyklu + autotune n_max/p_min, najpierw ngram, potem MTP | ik #1595, hipfire, TensorFold (−2,3…−3,2%, gdy polityka źle wycenia szybsze kernele) | T=0,7, ogólnie | +5–15% | 1–2 dni (Gemini) | tak |
| 11 | Prefill przez dekwant do f16 + własny WMMA f16 GEMM (wyjście f16) | ExLlamaV3 `exl3.py:140-189`; port phoenixhaxor na XTX: 27B prefill ~1180–1200 t/s @32K (zgłoszone, nie nasz pomiar) | prefill | +15–30% (do sprawdzenia: nasz wcześniejszy f16 GEMM przegrał z int8) | 3–4 dni | n/d (prefill) |
| 12 | Kalibrowane cięcie łańcucha MTP online zamiast stałego p_min; głowica draftu z tokenów sesji | ExLlamaV3 `draft_confidence.py`, `sparse_head.py` (MTP-7 157 vs MTP-4 129 t/s, 3090) | T=0,7, spec | +3–8%, +1–2% | 1–2 dni | tak |
| 13 | Block verification przy T>0 | TensorRT-LLM `block_verification.py` | T=0,7 | +3–6% | 2 dni | sprzężone losowanie do sprawdzenia |
| 7 | Fuzja gate/up + GLU w MMQ | llama.cpp #29948: +7,1% prefillu na GB10 | prefill | +2–4% | 1–2 dni | n/d (prefill) |
| 8 | Norma + kwant int8 robione przez ostatni blok GEMV | hipfire | dekod | +2–4% | 2 dni | tak, przy tej samej kolejności redukcji |
| 9 | Trwałe segmenty (bariera siatki) dla łańcucha GDN i `accept` | ignite-llama RDNA3: bariera 0,36–0,41 µs, +25% na MoE (3000 kerneli/token) | dekod | +1–3% | 2–4 dni na segment | tak |
| 10 | Prefix cache stanu GDN: zapis w prefillu, w punkcie rozejścia i co 256 tok. | vLLM `--enable-mamba-shared-prefix-checkpoint`, SGLang `mamba_track_interval` | TTFT wielu tur | TTFT | 2 dni (Gemini) | tak (replay) |

## Odrzucone
- **PowerInfer:** wykorzystuje rzadkość aktywacji ReLU, a Qwen ma SwiGLU, więc byłoby stratnie.
- **Zapis stanu GDN co token draftu, jak w mainline:** ok. 151 MB na token; to droższe niż nasz replay 0,35–0,5 ms.
- **Kwant int8 stanu w SGLang:** stratny.
- **Pełny megakernel 27B:** +3–6% za 40–70 osobodni.
- **HRX (Lemonade):** dziś dekod 2× wolniejszy niż HIP.
- **ik_llama.cpp na RDNA3:** słabszy od mainline.

## Kolejność pracy (Kernel)
1. Attention weryfikacji GQA (dźwignia 1), bo długie prompty to największa luka: 95–99 vs 140–159 t/s.
2. Szybszy `k_gemv_wide` i ogon W=16 (dźwignia 2, razem z Gemini r9b).
3. GDN prefillu: najpierw 96+ bloków, potem chunk (dźwignia 4); cel prefill > 882 t/s.
4. Taśma PM4 (dźwignia 3), według procedury bezpieczeństwa z raportu 17.

Gemini: polityka spekulacji (6), prefix cache GDN (10), potem DFlash2 (5).
