# 24t — Bezstratna kompresja entropijna wag kwantowych (DFloat11/ZipNN dla GGUF): pomiar CPU

Data: 2026-10-20. Autor: podagent OptEntropyW. Pomiar wyłącznie na CPU (`cpuheavy`, memmap, próbkowanie), bez GPU i bez buildów.
Skrypty: `24t-skrypty/code_entropy.py` (wyrocznia kodów), `ew_full.py` (pełny tensor, kontrola próbkowania), `ew_dup.py` (duplikaty wierszy głowicy). Wyniki: `24t-skrypty/out/qwen27b-8M.txt`, `lfm24b-8M.txt`, `lfm24b-scales.txt`.

## Werdykt

**KILL (bramka < 8%). Bezstratne kodowanie entropijne kwantów oszczędza na krok najwyżej ~5% bajtów, i to jako sufit teoretyczny. Kodek przyjazny dla GPU daje 0–0.9%. Nie projektujemy dekodera dla gfx1100, nie ma prototypu ani jobów GPU.**

- **Kody kwantów** (nibble, 5- i 6-bitowe, indeksy IQ4) są prawie maksymalnie losowe: 3.86/4 b (Q4_K), 4.86/5 (Q5_K), 5.79/6 (Q6_K), 3.91/4 (IQ4_XS). Najlepszy zmierzony model kontekstowy daje **2.83%** bajtów czytanych na token w Qwen3.8-27B (0.48 GB z 16.83 GB) i **2.92%** w LFM2.5-24B-A2B.
- **Skale i minima** zmierzono już w 15e: H1 ≤ 2.19% bajtów typów (Qwen), a teraz dla LFM ≤ 2.24%.
- **Razem sufit ≈ 5.0% (Qwen) / ≈ 5.1% (LFM)**. Ten sufit pomija koszt tablic, flushy stanu, indeksu bloków i dekodowania.
- **Praktycznie:**
  - Huffman statyczny per tensor: 1.81% / 2.01%, ale bez indeksu bloków. Z indeksem 16 bit na blok 256 wartości (warunek losowego dostępu w MMVQ) zostaje **~0.6% / ~0.9%**.
  - Stałe sloty bez indeksu: **0.00%**. Rozrzut rozmiaru bloku (σ ≈ 1.6 B przy średnim zysku ~3 B ze 128) zjada cały zysk na eskapach.
  - rANS z flushem stanu per blok: 0.35% / 0.53%.
- **zstd -19** na surowych blokach daje: Q5_K 1.000, Q6_K 0.996, IQ4_XS 0.996, Q4_K 0.979, Q8_0 0.965.

Dlaczego tak mało: K-quanty dopasowują skalę i minimum do zakresu każdego pod-bloku 16/32 wartości. Kwantyzator jest więc adaptacyjny i kody wypełniają cały alfabet prawie równomiernie. Dla gaussowskich wag przy min-max z 32 próbek wychodzi krok ≈ 0.27σ, czyli h ≈ 2.05 + log2(1/0.27) ≈ 3.9 bitu na 4 [INFERENCE: przybliżenie analityczne zgodne z pomiarem 3.86]. Siatka IQ4 jest nieliniowa właśnie po to, żeby wyrównać użycie kodów (3.91/4). Reszta struktury jest prawie żadna. Kontekst skali pod-bloku, poprzedniego kodu w wierszu, tej samej kolumny w poprzednim wierszu ani osobne tablice per wiersz nie dokładają więcej niż 0.1–0.5 pp ponad H0. Wyjątek to Q8_0 (H(kod | poprzedni) 7.33/8), ale Q8_0 to 0.13 GB na token.

## Tabela 1: entropia kodów (bit/kod, ważona bajtami czytanymi na token)

Qwen3.8-27B-UD-Q4_K_XL (próbka 8M wartości na tensor w 8 warstwach wierszy; unpack sprawdzony przez re-pack bajt w bajt dla każdej próbki):

| typ | bity | H0 (tablica/tensor) | H(kod \| skala pod-bloku) | H(kod \| poprzedni kod) | H(kod \| ten sam kod, poprz. wiersz) | tablica per wiersz | Huffman/tensor |
|---|---|---|---|---|---|---|---|
| Q5_K | 5 | 4.864 | 4.857 | 4.857 | 4.863 | 4.860 | 4.904 |
| IQ4_XS | 4 | 3.909 | 3.892 | 3.908 | 3.909 | 3.907 | 3.959 |
| Q6_K | 6 | 5.789 | 5.757 | 5.781 | 5.785 | 5.781 | 5.824 |
| Q4_K | 4 | 3.865 | 3.859 | 3.859 | 3.865 | 3.863 | 3.903 |
| IQ4_NL | 4 | 3.909 | 3.909 | 3.908 | 3.909 | 3.907 | 3.959 |
| Q8_0 | 8 | 7.626 | 7.624 | 7.329 | 7.343 | 7.587 | 7.648 |

LFM2.5-24B-A2B-Q5_K_M: Q5_K 4.863 / 4.856 / 4.856 / 4.862 / 4.851 / 4.904; Q6_K 5.778 / 5.741 / 5.765 / 5.763 / 5.748 / 5.810.

Histogram Q4_K (`blk.10.attn_qkv`): środek 0.10, brzegi 0.026–0.042, czyli lekki dzwon plus piki obcięcia na 0 i 15. Długości Huffmana to 3–5 bitów.

## Tabela 2: oszczędność bajtów czytanych na token (wiersze typów: % bajtów danego typu; wiersze „razem”/„sufit”: % wszystkich bajtów na token)

Na token czytane są wszystkie tensory oprócz `token_embd` (get_rows). Wyjątek: w LFM głowica jest powiązana z `token_embd`, więc `token_embd` się liczy. Eksperci MoE mają wagę 4/64.

| model / typ | GB/token | H0 | najlepszy kontekst | Huffman/tensor (bez indeksu) | Huffman + indeks 16 b/blok | sloty bez indeksu | rANS flush/blok | zstd -19 (bajty bloku) |
|---|---|---|---|---|---|---|---|---|
| Qwen Q5_K | 7.926 | 2.48% | 2.60% | 1.75% | ~0.6% | 0.00% | 0.21% | 0.00% |
| Qwen IQ4_XS | 3.125 | 2.14% | 2.54% | 0.97% | ~−0.5% | 0.00% | 0.00% | 0.45% |
| Qwen Q6_K | 2.862 | 3.22% | 3.70% | 2.69% | ~1.7% | 0.02% | 1.31% | 0.41% |
| Qwen Q4_K | 2.345 | 3.00% | 3.14% | 2.15% | ~0.8% | 0.00% | 0.22% | 2.13% |
| Qwen IQ4_NL | 0.280 | 2.02% | 2.05% | 0.91% | <0 | 0.00% | 0.00% | 2.05% |
| Qwen Q8_0 | 0.131 | 4.39% | 7.61% | 4.13% | ~3.4% | 0.00% | 0.00% | 3.52% |
| **Qwen razem (kody)** | **16.833** | **2.60%** | **2.83%** | **1.81%** | **~0.6%** | **0.00%** | **0.35%** | – |
| Qwen skale (15e, H1) | | | 2.19% typów | | | | | |
| **Qwen sufit kody+skale** | | | **≈ 5.0% (≈ 0.84 GB)** | | | | | |
| LFM Q5_K | 1.311 | 2.48% | 2.61% | 1.75% | | 0.00% | 0.21% | 0.00% |
| LFM Q6_K | 0.445 | 3.38% | 3.95% | 2.89% | | 0.00% | 1.48% | 0.48% |
| **LFM razem (kody)** | **1.777** | **2.68%** | **2.92%** | **2.01%** | **~0.9%** | **0.00%** | **0.53%** | – |
| LFM skale (`scale_entropy.py`, H1) | | | 2.24% typów | | | | | |
| **LFM sufit kody+skale** | | | **≈ 5.1%** | | | | | |

Jak liczono kolumny:
- „Huffman + indeks”: 2 B na blok 256 wartości (Qwen ~98 M bloków/token = 0.196 GB = 1.17%; LFM 9.6 M bloków = 1.08%).
- „Najlepszy kontekst” to maksimum z kolumn kontekstowych. Te modele się nie sumują.
- Sufit kody+skale to suma dwóch niezależnych górnych ograniczeń, bez kosztu tablic i dekodowania.

Kontrola próbkowania:
- Pierwsza wersja próbki kotwiczyła ostatnie wiersze tensora. Dla `token_embd` LFM (głowica, 12% bajtów/token) dało to fałszywe H(kod | poprz. wiersz) 4.42/6, bo ostatnie id (≥ ~125k) to prawie identyczne tokeny zarezerwowane.
- Pełny tensor (`ew_full.py`, 262 M kodów): H0 5.767, H|skala 5.740, H|poprz. 5.760, H|wiersz 5.744. Próbka warstwowa po poprawce: 5.768 / 5.733 / 5.758 / 5.756, czyli zgodna.
- Duplikaty wierszy (`ew_dup.py`):
  - LFM `token_embd`: 49/128000 (0.04%, 0.1 MB);
  - Qwen `output.weight`: 0/248320.

  Deduplikacja głowicy jako dźwignia = 0.

## Czego nie zrobiono i dlaczego

- Kroku 3 (projekt dekodera LDS-LUT/prefix-sum na gfx1100, budżet VALU z ISA 24f/24n) i prototypu `GGML_HIP_ENTROPY_W` **nie wykonano**. Bramka < 8% zamyka temat.
- Nawet sufit 5% przy czystym ograniczeniu pamięcią dałby ≤ +5% dla kerneli przy 828 GB/s. Realny kodek z losowym dostępem daje ≤ 1% bajtów.
- Średnie macierze (580–700 GB/s) nie są czysto przepustowościowe. Dodatkowe VALU na dekodowanie zwiększyłoby ich czas. 24n pokazało, że MMVQ n=5 nie skaluje się z obłożeniem, a każda serializacja ładowań kosztuje (−6.4%).
- Brak zmian w kodzie llama.cpp, worktree `~/wt/entropy` nie powstał, joby GPU: brak. Gate'y md5 c4708318 / 6f14e814 nie są dotknięte.

## Akcje

1. Zamknąć dźwignię „bezstratna kompresja wag GGUF” dla K-quantów i IQ4 (kody i skale). Ponowne otwarcie ma sens tylko przy formatach z dużą redundancją: BF16/FP8 z wykładnikami (DFloat11 ~30%) albo NVFP4 (skale −5.4…−8%, 15e). Żadnego z nich nie dekodujemy.
2. Bajtów na token nie zmniejszy żaden bezstratny trik na tych plikach. Zostają: sprawność kerneli (OptMmvqN5), mniej przebiegów po wagach na token (spekulacja, większe n w weryfikacji) albo inna kwantyzacja (stratna, poza tym zadaniem).

## Do bazy wiedzy

| gdzie | wpis | źródło |
|---|---|---|
| `eksperymenty/2026-10-20-entropia-kodow-wag` (nowa, `wynik-negatywny`) | Bezstratne kodowanie kodów kwantów GGUF: Qwen3.8-27B UD-Q4_K_XL sufit 2.83% bajtów/token (H0 2.60%), LFM2.5-24B-A2B Q5_K_M 2.92%; ze skalami (15e) ≈ 5%; Huffman+indeks ≤ 0.9%, stałe sloty 0%, zstd -19 0–2%. Kill (< 8%). | `24t-skrypty/code_entropy.py`, `out/*.txt` |
| `eksperymenty/2026-10-16-kompresja-skal-offline` | Dopisać: kody kwantów zmierzone w 24t, łączny sufit kody+skale ≈ 5%; LFM skale H1 2.24%. | `out/lfm24b-scales.txt` |
| `wyniki-negatywne` | „Kompresja entropijna wag K-quant/IQ4 (DFloat11/ZipNN-style) – sufit 5%, praktycznie < 1%, 24t.” | ten raport |
| `kwanty-gguf` | Bit/kod: Q4_K 3.865/4, Q5_K 4.864/5, Q6_K 5.79/6, IQ4_XS/NL 3.909/4, Q8_0 7.63/8; kontekst (skala pod-bloku, poprzedni kod, wiersz) daje ≤ 0.03 b/kod poza Q8_0. | Tabela 1 |
| lekcja (metodyka) | Próbka „od 0 do końca tensora” biasuje `token_embd`/głowicę: ostatnie id słownika to prawie identyczne tokeny zarezerwowane. Próbkować warstwami ze środka i sprawdzać na pełnym tensorze. | `ew_full.py` |
