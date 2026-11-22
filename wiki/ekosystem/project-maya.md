---
typ: ekosystem
tags: [ekosystem, konkurencja, moe]
aktualizacja: 2026-11-14
zrodlo: ~/KERNEL/product/research/21g-nowe-silniki.md:158-216; ~/KERNEL/product/research/21g-notatki/maya.md; https://github.com/mw00/project-maya (`a4e1ff0`, v1.1.15; `f26d8ba`, v1.1.26; `c167004`, v1.1.54; `c4effee6`, v1.1.55; `22fc101f`, v1.1.56; `30145b8`, v1.1.62 + CHANGELOG do v1.1.63, 2026-11-14; https://x.com/PeasantSmith/status/2121371735157264831); ~/KERNEL/product/research/32a-maya-1117-strata-020-gyro.md:14-20; ~/KERNEL/product/research/39a-maya-1119.md:14-30; ~/KERNEL/product/research/60d-serving-kernels-cache.md:196-213,232-239; ~/KERNEL/product/research/63b-colibri-maya-delta.md:166-220; ~/KERNEL/product/research/66a-strata-maya.md:206-226,300-353
status: aktualne
---
# Project Maya (mw00): silnik jednego modelu GLM-5.3-Flash

**Pochodna Straty (nie fork llama.cpp) uruchamiająca tylko GLM-5.3-Flash (321B, 18B aktywnych) z ekspertami w trzech warstwach VRAM → przypięty RAM → NVMe (O_DIRECT); 81 t/s na RTX PRO 6000 = 41% pasma; liczby z README to najlepsze wiersze z różnych wersji, bez llama.cpp (raport 21g, 2026-10-19).**

- Jakość: „97.7–99.2% dokładności FP8” to marketing (5 testów MC po 400 pytań); uczciwie KL Maya-S 0.428 / top-1 83.3%, Maya-L 0.188 / 90.0% – poziom ~q2_K.
- Determinizm: domyślnie tylko 17/70 par restartów daje identyczne tokeny, v1.1.13 i v1.1.15 zmieniły domyślne tokeny.
- v1.1.14 Pascal: `-Xptxas -dlcm=ca`, P40 dekod ×1.7–3.0; P100 (sm_60) najpewniej się nie kompiluje (`__dp4a` wymaga CC 6.1) `[INFERENCE]`; nowy typ ekspertów Q6_K_XL/Q8_0.
- Przypina cały RAM poza 6 GB; buduje się 20–40 min ze źródeł; XTX eksperymentalnie, niezmierzony; polskiego brak.
- Do skopiowania: pętla społeczności `--bench` → `--report` → issue → README, rozgrzewka cache ekspertów z profilu (+15% na świeżym starcie), kalibracja MTP/DFlash2 per maszyna.

## Aktualizacja 2026-10-21
- v1.1.17: bez nowych kerneli ([[raport-32a-maya-strata-gyro]]); v1.1.19: #318 pomija martwe obliczenia DeepSeek, nie przenosi się na Qwen3.8; rozgrzewka przed READY (#285) ([[raport-39a-maya-1119]]).

## Aktualizacja 2026-10-24 (v1.1.21–1.1.26, tylko DeepSeek `maya-ds4`)
- Prefill AMD 2.35–2.53× (Strix Halo, v1.1.21): sparse attention na `wmma_f32_16x16x16_bf16_w32` z Q/P rozbitym na BF16 hi+lo (~16 bitów mantysy), dense GEMM przez hipBLASLt z wyborem per kształt. RDNA4 (#370): 1.16–1.40×. RTX 3090 MMA (#369): prefill ~30K 957–992 → 1104–1234 tok/s.
- v1.1.26: `DS4_FAT_ROWS` (gorący ekspert raz do FP16 + cuBLAS) 1.3–1.56× prefillu na 3× V100; dokładny softmax FP32 na `wmma` dla Volta/Turing.
- v1.1.22: TP bez P2P (copy engine → pinned host, `allreduce_dma`), 9 GPU PCIe 3.0: dekod 42.9 → 66.8 t/s; drafting 8.5 → 15.9 t/s (strumienie HIP).
- **2× RX 7900 XTX (#382):** jeden launch kwantyzacji q8 zamiast wielu: 12.5 vs 13.1 t/s, bez zysku (gap 3.3 µs, praca ~2 µs). v1.1.25: sesje przeżywają restart (`MAYA_DS4_SLOT_KEEP=1`).
- Dla Qwen3.8/gfx1100 nic do wzięcia ([[raport-60d-serving-kernels-cache]]).

## Aktualizacja 2026-11-05 (v1.1.27–1.1.54, R63b)
- Gęstego 27B dalej brak (GLM, DeepSeek, MiniMax, Flash-Next). Dla decode/prefill na gfx1100 nic.
- Do wzięcia dla ścieżki agenta: **#607 „wspólny początek”** (system + narzędzia jako osobny mały wpis, nowa rozmowa 19× szybciej) → [[wspolny-poczatek-promptu]]; #639 punkty przywracania; `tools/agent_bench.py` (#406) jako benchmark.
- Zasady: żadna warstwa pośrednia nie przepisuje prefiksu (#704: strażnik pętli psuł cache, 150K ~15× szybciej po poprawce); przerwanie nie gubi stanu (#573, #746). #625 stała kolejność narzędzi zmienia prompt, więc u nas tylko za zgodą ([[2026-11-05-tylko-bezstratne]]).
- v1.1.54 „follow-up czytał całą rozmowę” na Qwenie: ten sam błąd klasy co colibri #2517 ([[colibri]]).

## Aktualizacja 2026-11-07 (v1.1.55–1.1.56, R66a)
- **#864 (XTX, ROCm 7.2.4):** kernele ekspertów EXL3 na WMMA −39% przy ≥ 128 wierszach na eksperta, 108/108 wyjść bitowo. Koszt był w podawaniu operandów: 2× `ds_load_b128` zamiast 8 słów, słowa kafla przez `v_permlane16`, LDS 57 → 24 KB. Nasz audyt ISA tej lekcji znalazł Q6_K w MMQ topki ([[mmq-q6k-skale-lds]]).
- `MAYA_PROMPT_MEMO` domyślnie (przyrostowe przygotowanie promptu): follow-up po 115K −6%. Nasz odpowiednik `TOK_CACHE` jest w produkcji martwy ([[lekcja-flaga-bez-dowodu-dzialania]]).
- #840: przy nieudanym wczytaniu slotu następny slot, potem checkpoint ([[siatka-checkpointow-gdn]]). Dla Enigmy: Codex CLI na `/v1/responses` (#726), odpowiedź biegnie do końca bez czytelnika.
- Stratne (parked): GLM KV INT8 domyślnie, `DS4_CHUNK_GFX11=0`, #869/#870 RDNA2.

- **Delta v1.1.57–v1.1.63 (2026-11-09…14, Telegram „gpu”):**
  - **Główna nowość v1.1.62:** APU AMD Halo (ROCm) i karta NVIDIA (CUDA) liczą jeden model w jednym procesie, ze wspólną kopią wag w pamięci APU. Między kartami idą tylko aktywacje. Na NVIDIA trafia atencja, KV, draft i najczęstsze eksperty. Wyniki: GLM-5.3-Flash prefill 32K 293 → 901 t/s, dekod +21%; DeepSeek dekod +18%. Maya trzyma ten tryb tylko wtedy, gdy daje > 3%.
  - **Pozostałe:** GLM-5.3 744B, kwant Maya-XS ~1,6 bita, ablacja odmowy przełączana per żądanie, lookup promptu dla MiniMax (+6% na kodzie, mamy od 10.10), szybsze eksperty CPU.
  - **Werdykt:** dla gęstego Qwen 27B na XTX nic nowego. Zysk mieszanego trybu bierze się z MoE: atencja i gorące eksperty idą na szybszą kartę, a reszta wag zostaje w pamięci, której szybka karta nie ma. U nas cały model mieści się w XTX (960 GB/s). Dołożenie 5060 Ti (448 GB/s) przy podziale warstw dekod tylko spowolni ([[rtx-5060-ti]]). Ablacja per żądanie to ten sam pomysł co odrzucona K-082 w [[KOLEJKA-TESTOW]]. Nic do kolejki.

## Aktualizacja 2026-11-17 (v1.1.66, Telegram „gpu”)

Delta od v1.1.65:
- **GLM na parze APU AMD + NVIDIA: dekod +19%** (A/B na tym samym PC, V100 obok APU, te same odpowiedzi). Dwie przyczyny:
  - karta NVIDIA czytała każdą wagę dwa razy podczas weryfikacji draftów, teraz raz;
  - para wymienia całą warstwę weryfikacji jednym wywołaniem zamiast wywołania na token.
- **Strojenie w trakcie działania:** Maya mierzy obie kolejności na pierwszych odpowiedziach i zostawia szybszą, ale tylko tam, gdzie obie dają te same odpowiedzi.
- Reszta to poprawki (DeepSeek: dwa rozmiary obok siebie, eksperci draftu w profilu; uśpienie bezczynnego CPU jako ustawienie; diagnostyka faultów prefillu).

Dla gęstego 27B na XTX nic nowego do portu. Lekcja zgodna z naszym K-114/K-116: narzut wywołań na token w weryfikacji i drafcie kosztuje więcej niż bajty. U nas weryfikacja czyta wagi raz (MMVQ N=5), więc pierwszego błędu nie mamy.

## Powiązane
- [[strata]]
- [[raport-21g-nowe-silniki]]
- [[lekcja-bit-exact-wobec-siebie]]
