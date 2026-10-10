# Qwen3.8-27B na RX 7900 XTX — pełny opis aktualnego setupu i pomiarów (2026-10-09)

Wszystkie liczby zmierzone na tej maszynie. Gdzie czegoś nie zmierzono, jest to napisane wprost.

## 1. Sprzęt i oprogramowanie

| Element | Wartość |
|---|---|
| GPU | AMD Radeon RX 7900 XTX, gfx1100, 24 GB GDDR6 (24 560 MiB widoczne), PCIe 4.0 x16 |
| Limit mocy GPU | 303 W (domyślny; zakres sterownika 272–350 W) — niezmieniany |
| CPU / RAM | Ryzen 7 5700X 8C/16T, 62 GB |
| System | Ubuntu 24.04.4, jądro 6.8.0-138 |
| ROCm | 10.0.0 pre4 (`/opt/rocm/core-10.0`, HIP 7.15) |
| Vulkan | Mesa RADV 25.2.8 + loader LunarG 1.4.363, oba w przestrzeni użytkownika (`~/vk`), bez sudo |
| llama.cpp | upstream `e60eff95f` + 5 łatek z `patches/llama.cpp-amd-opt/` |

## 2. Model i pliki

| Plik | Rozmiar | Rola |
|---|---|---|
| `~/models/Qwen3.8-27B-UD-Q4_K_XL.gguf` | 17.56 GB (16.34 GiB), 27.32 B parametrów | model główny; mieszane kwanty: Q5_K 7.9 GB, IQ4_XS 3.1, Q4_K 3.1, Q6_K 2.9, reszta 0.7 |
| głowica MTP (wbudowana w plik, `blk.64`) | — | draft dla spekulacji MTP |
| `~/models/draft/draft_vocab_qwen38.txt` | 1.6 MB | ranking tokenów; draft MTP używa pierwszych 65 536 |
| `~/models/draft/Qwen3.8-27B-DFlash2-Q4_K_M.gguf` | 1.14 GB | osobny drafter DFlash2 (opcja dla EN/kodu) |

Architektura: 64 warstwy (48 Gated DeltaNet + 16 pełnej uwagi), hidden 5120, słownik 248 320 tokenów,
kontekst natywny 262 144.

## 3. Ustawienie domyślne (`~/qwen-opt/run-llm.sh`)

```
llama-server -m Qwen3.8-27B-UD-Q4_K_XL.gguf
  -ngl 999                 # cały model na GPU
  -fa on                   # flash attention
  -ctk q4_0 -ctv q4_0      # KV cache q4_0
  -c 204800                # kontekst 204 800 tokenów
  -np 1                    # jeden równoległy slot
  --jinja                  # szablon czatu Qwen3.8 (narzędzia, thinking)
  --spec-type draft-mtp --spec-draft-n-max 5
  --spec-draft-vocab ~/models/draft/draft_vocab_qwen38.txt --spec-draft-vocab-n 65536
  --host 127.0.0.1 --port 8080
backend: Vulkan (RADV), VK_ICD_FILENAMES=~/llama-opt-vk/radeon_icd.json
```

VRAM przy tym ustawieniu: **22.3 GB** z 24.56 GB.

Warianty: `run-llm.sh qwen mtp rocm` (ROCm, MTP n=4, 23.2 GB VRAM), `run-llm.sh qwen dflash` (DFlash2 n=6),
`run-llm.sh qwen none` (bez spekulacji). Kontekst: `CTX=<liczba> run-llm.sh`.

## 4. Generowanie (decode) — przez serwer, kontekst zaalokowany 204 800, prompty krótkie

Metoda: `serve_bench.py --lang all`, chat, temp 0, thinking wyłączone, 256 tokenów odpowiedzi, każdy prompt 3×,
mediana, 2 rundy rozgrzewki. Prompty: kod EN (LRU cache), proza EN (kolor nieba), rozumowanie EN (pociągi),
te same trzy po polsku.

| Typ tekstu | stary build (start) | ROCm nasz, MTP n=4 | **Vulkan, MTP n=5 (domyślne)** |
|---|---|---|---|
| kod EN | 65.6 | 92.3 | **105.6** |
| proza EN | 54.2 | 65.3 | **64.6** |
| rozumowanie EN | 58.2 | 90.9 | **102.5** |
| kod PL | 59.6 | 85.1 | **87.7** |
| proza PL | 47.4 | 60.2 | **59.4** |
| rozumowanie PL | 61.7 | 85.9 | **93.8** |
| **mediana wszystkich** | **59.2** | **85.5** | **91.8** |
| akceptacja draftu | 0.73 | 0.585 | 0.527 |
| VRAM | 22.8 GB | 23.2 GB | 22.3 GB |

Stary build = b356fa262 (1 wrz), ROCm, MTP n=3, bez draft vocab — punkt startowy użytkownika.

Inne warianty generowania (ctx 131 072, KV q4_0):

| Wariant | kod EN | proza EN | rozum. EN | uwagi |
|---|---|---|---|---|
| DFlash2 n=6, ROCm (nasz build) | 123.3 | 65.3 | 115.7 | po polsku 39–73 t/s (proza PL ~39) |
| DFlash2 n=6, Vulkan | 127.2 | 64.8 | 118.8 | proza PL 40.1 |
| bez spekulacji, ROCm | 36.6 | | | llama-bench tg128 |
| bez spekulacji, Vulkan | 38.8 | | | llama-bench tg128 |

## 5. Wczytywanie promptu (prefill) i generowanie przy wypełnionym kontekście

`llama-bench`, KV q4_0, flash attention, **bez spekulacji** (generowanie z MTP jest ~2.2–2.4× wyższe),
1 powtórzenie, „@ dN" = tyle tokenów już w kontekście przed pomiarem.

| Kontekst już w środku | Vulkan prefill | Vulkan generowanie | ROCm prefill | ROCm generowanie |
|---|---|---|---|---|
| 0 | 896–913 t/s | 38.6 t/s | 1044 t/s (pp4096), 856 (pp512) | 34.8 t/s |
| 16 384 | 622 t/s (pp4096) | 35.8 t/s | 890 t/s (pp4096) | 33.4 t/s |
| 32 768 | 497 t/s | 34.6 t/s | nie zmierzone | nie zmierzone |
| 98 304 | 265 t/s | 29.2 t/s | nie zmierzone | nie zmierzone |
| 196 608 | nie zmierzone | nie zmierzone | nie zmierzone | nie zmierzone |

Pomiar przy 32k/98k/196k na ROCm i 196k na Vulkanie przerwano na prośbę użytkownika (temperatura junction 106°C).

Przybliżony czas wczytania długiego promptu (Vulkan, z tabeli wyżej): 32k tokenów ~1 min, 98k ~4–5 min.
ROCm jest przy prefillu 1.2–1.4× szybszy (dane do 16k).

## 6. Co zostało zmienione względem upstream (łatki)

1. `0001`, `0002`: HIP `mul_mat_vec_q` dla 2–8 kolumn na RDNA3 — wagi rozpakowane raz, szerokie odczyty,
   człon min z sum q8_1. Dotyczy weryfikacji spekulacji. Przy 8 kolumnach Q5_K 296 → 621 GB/s.
2. `0003`: cache skwantyzowanych aktywacji (q8_1) między kolejnymi mnożeniami z tym samym wejściem (+2–4% na ROCm).
3. `0004`: `--spec-draft-vocab` / `--spec-draft-vocab-n` — głowica draftu MTP liczy tylko 65 536 tokenów
   (+7.5%, działa na ROCm i Vulkanie). Wynik bezstratny (greedy bajt w bajt identyczny).
4. `0005`: sprzątanie.

Testy: `test-backend-ops -o MUL_MAT,MUL_MAT_VEC_FUSION` 3709/3709 OK.

## 7. Temperatura i moc

| Stan | Moc | edge | junction | VRAM | wentylatory |
|---|---|---|---|---|---|
| prefill 196k (pełne obciążenie) | 281 W | 66°C | **106°C** | 76°C | ~2970 RPM |
| generowanie (wcześniejszy odczyt) | ~305 W | — | — | — | — |
| po zatrzymaniu (20 s) | 57 W | 50°C | 54°C | 66°C | — |

Różnica edge–junction ~40°C jest duża. Limit mocy (cel ≤250 W): `sudo ~/qwen-opt/gpu-power.sh eco`
(272 W + zegar GPU 2371 MHz). Wpływ na t/s jeszcze nie zmierzony.
