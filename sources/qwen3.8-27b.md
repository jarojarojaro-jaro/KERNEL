# Qwen3.8-27B (+ wersja Uncensored od OrcaRouter)

Przeanalizowane: 2026-10-07. Główny model użytkownika na RX 7900 XTX.

## Architektura (ważne dla kerneli)
- Gęsty model 27B, **64 warstwy: 48 × Gated DeltaNet (linear attention) + 16 × pełny (gated) attention**, układ 3:1, hidden 5120 – [OrcaRouter blog](https://www.orcarouter.ai/blog/qwen-3-8-27b-gguf), [HackerNoon](https://hackernoon.com/qwen38-27b-uncensored-vs-other-qwen-gguf-models)
- Warstwy DeltaNet trzymają **stały stan rekurencyjny zamiast rosnącego KV cache** → KV cache to ok. 1/4 tego, co w klasycznym 27B. Kontekst natywny 262K.
- **Wbudowana głowica MTP** (multi-token prediction, `blk.64` / nextn) – zostaje w plikach GGUF → speculative decoding bez osobnego modelu-draftu – [HF: Qwen3.8-27B-MTP-GGUF](https://huggingface.co/Terathox-Coder/Qwen3.8-27B-MTP-GGUF)
- Model wizyjny: potrzebny osobny plik `mmproj` (~0,9 GB). Bez niego obrazki są po cichu ignorowane.

Co to znaczy dla wydajności:
- Decode: dalej czytamy całe ~17 GB wag na token → ograniczenie pasmem jak w każdym gęstym modelu.
- Długi kontekst: tańszy niż zwykle (mało KV), ale dochodzi kernel DeltaNet (`gated_delta_net.comp` w Vulkanie, `fused_gdn` w Stracie) – osobny kandydat do profilowania.

## Rozmiary plików GGUF (OrcaRouter)
| Kwant | Rozmiar | Uwagi |
|---|---|---|
| IQ2_XXS | 8,9–9,0 GB | |
| Q3_K_M | 13,8 GB | |
| IQ4_XS | 15,7 GB | |
| **Q4_K_M** | **16,8–17,1 GB** | rekomendowany dla 24 GB, mieści 32K–64K kontekstu |
| Q6_K | 20,9–22,9 GB | na styk w 24 GB |
| Q8_0 | 29,0 GB | nie mieści się w 24 GB |
| BF16 | 54,7 GB | |

(Dwie strony OrcaRouter podają nieco inne rozmiary – sprawdzić na konkretnym pliku.)

Przykładowa komenda z bloga OrcaRouter:
```bash
llama-server -m Qwen3.8-27B-Q4_K_M.gguf --ctx-size 32768 -ngl 99 --jinja --cache-type-k q8_0
# + --mmproj Qwen3.8-27B-mmproj-bf16.gguf  (wizja)
```

## Qwen3.8-27B-Uncensored (OrcaRouter)
- Repo: [orcarouter/Qwen3.8-27B-Uncensored-GGUF](https://huggingface.co/orcarouter/Qwen3.8-27B-Uncensored-GGUF) (Apache 2.0), są też kopie/requanty (np. [chimingw](https://huggingface.co/chimingw/Qwen3.8-27B-Uncensored-OrcaRouter-GGUF), bartowski) i wersja MLX/FP8. Prasa: [borncity](https://borncity.com/news/qwen-3-8-27b-orca-router-veroeffentlicht-unzensiertes-ki-modell/), [voix.jp](https://voix.jp/?p=120784) (3. miejsce w trendach HF).
- To **abliteracja**: usunięty „kierunek odmowy” w wagach bazowego Qwen3.8-27B. Architektura, MTP, wizja i kontekst bez zmian.
- **Dla nas: identyczna wydajność jak bazowy model w tym samym kwancie** – te same kształty tensorów, te same kernele. Można je benchmarkować zamiennie.
- Abliteracja zwykle lekko pogarsza jakość (rozumowanie, czasem stabilność) – warto porównać na własnych promptach. OrcaRouter nie podaje miar jakości (KL, benchmarki).
- Autorzy zaznaczają, że model wykona też szkodliwe/nielegalne prośby i cała odpowiedzialność jest po stronie użytkownika. Wspomniane jest docelowe ograniczenie dostępu publicznego – **pobrać, jeśli chcemy go mieć**.
- Strata wspiera osobno „OrcaRouter IQ3_XXS” – ale to wariant dużego MoE (Qwen3.8-Flash-Next), nie 27B.

## Liczby z innych kart (do porównań)
- R9700 (640 GB/s), wątek [#21043](https://github.com/ggml-org/llama.cpp/discussions/21043): MTP z `spec-draft-n-max=7` dało +9,7%, akceptacja 77–95%.
  - **Podejrzane:** ten sam wątek podaje 59,2 tok/s dla Q8_0 bez MTP. Przy 29 GB wag i 640 GB/s sufit to ~22 tok/s – liczba prawie na pewno dotyczy innego kwantu lub konfiguracji. Nie cytować bez sprawdzenia.
- Benchmarki jakości (Alibaba) – niezreprodukowane.

## Do zrobienia
- [ ] Pobrać Q4_K_M (bazowy lub Uncensored – wydajnościowo to samo) + mmproj
- [ ] Etap 0b z `hardware/rx-7900-xtx.md`
- [ ] Sprawdzić flagi MTP w aktualnym `llama-server --help` i zmierzyć zysk na XTX
