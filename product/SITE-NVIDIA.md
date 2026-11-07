# Enigma na kartach NVIDIA — materiał na enigmalabz.com (2026-11-07)

Jeden dokument z wszystkim, co trafia na stronę: finalne zestawy per karta, wyniki i jak je osiągnęliśmy.
Źródło każdej liczby: `product/research/67-nvidia-vast-kampania.md` (§1 tabela, §2 silnik i limity mocy, §5 Bonsai/fork/kvq/lean, §7 szczegóły),
`product/research/67b-wybor-modeli-nvidia.md` (wybór modeli), surowe dane `~/qwen-opt/cloud/results/nv67-*/`.

**Zasady publikacji (jak przy Flincie):**
- tylko zmierzone liczby, każda z nazwaną kartą;
- format **dziś → Enigma → przyrost**;
- kolumnę „z silnikiem Enigmy” publikujemy dopiero, kiedy archiwa silników są na release (patrz §6), wcześniej jako „wkrótce”.

## 1. Nagłówek

> **Ta sama karta, ten sam model, ta sama jakość odpowiedzi — do 2× szybciej i z pełnym kontekstem 262 144 tokenów.**
> Sprawdziliśmy Enigmę na 11 kartach NVIDIA, od RTX 2080 Ti do RTX 5090. Każde ustawienie przeszło test pełnego wypełnienia kontekstu na prawdziwej karcie.

Liczby do wyróżnienia:

| | |
|---|---|
| **148,6 t/s** | RTX 5090, Qwen3.8-27B (Q6_K), kontekst 262 144 |
| **101,3 t/s** | RTX 4090, Qwen3.8-27B (Q4_K_XL), kontekst 262 144 |
| **+47%** | 5090 wobec zwykłego llama.cpp z MTP na tym samym hoście |
| **×2,6** | RTX 3060: 27B dla 12 GB, 22,2 → 58,3 t/s |
| **262 144** | pełny natywny kontekst Qwen3.8-27B na 24 i 32 GB |

## 2. Tabela per karta (gotowa na stronę)

t/s = tempo pisania, mediana 6 promptów PL/EN przy T=1 (sampling jak w czacie). „Dziś” = wcześniejszy wybór Enigmy na zwykłym llama.cpp; „Enigma” = obecny wybór; „z silnikiem Enigmy” = nasze silniki CUDA (§5).

| Karta (VRAM) | Model | Kontekst | Dziś | Enigma | Z silnikiem Enigmy |
|---|---|---|---|---|---|
| **RTX 5090** (32 GB) | Qwen3.8-27B UD-Q6_K | 262 144 | 62,5 | **102,2** (+63%) | **148,6** (+138% vs dziś) |
| **RTX 4090** (24 GB) | Qwen3.8-27B UD-Q4_K_XL | 262 144 | 46,9 | **76,4** (+63%) | **101,3** (+116%) |
| **RTX 3090** (24 GB) | Qwen3.8-27B UD-Q4_K_XL | 245 760 → **262 144** | 40,9 | **61,5** (+50%) | **80,0** (+95%) |
| **RTX 5080** (16 GB) | Qwen3.8-27B ISTA IQ3_XXS | 208 896 → 217 088 | 52,1 | **58,8** (+13%) | **81,6** (+57%) |
| **RTX 5060 Ti** (16 GB) | Qwen3.8-27B ISTA IQ3_XXS | 200 704 → 229 376 | 27,5 | **31,4** (+14%) | **43,4** (+58%) |
| **RTX 4060 Ti** (16 GB) | Qwen3.8-27B ISTA IQ3_XXS | 217 088 → 229 376 | 19,8 | **24,0** (+21%) | **36,3** (+84%) |
| **RTX 4070** (12 GB) | Qwen3.8-27B (Bonsai 2 / Saluki) | 151 552 → 208 896 | – | Saluki **44,4** | Bonsai 2 + MTP **94,7** |
| **RTX 3060** (12 GB) | Qwen3.8-27B (Bonsai 2 / Saluki) | 135 168 → 204 800 | – | Saluki **22,2** | Bonsai 2 + MTP **58,3** (×2,6) |
| **RTX 2080 Ti** (11 GB) | Qwen3.8-27B Bonsai 2 | 131 072 → 155 648 | – | **39,6** | **78,0** (×2,0) |
| **RTX 3080** (10 GB) | Qwen3.5-9B Q6_K | 192 512 | – | **85,2** | – |
| **RTX 3070** (8 GB) | Qwen3.5-9B Q4_K_M | 151 552 | – | **66,9** | – |

Przy 12 GB i mniej „dziś” było innym modelem (Gemma 4 12B), dlatego bez procentów.

**Szybka alternatywa (MoE, LFM2.5-24B-A2B, kontekst 131 072, cały model w VRAM):** RTX 4070 **179,3 t/s**, RTX 5060 Ti **139,5 t/s**, RTX 3060 **102,5 t/s**.

**Dla porównania AMD (nasza referencja, RX 7900 XTX 24 GB, tryb eco):** Qwen3.8-27B Uncensored przy 262 144, prawdziwa praca agentowa średnio **120,8 t/s**, 241 W.

## 3. Modele i licencje

| Model | Plik | Licencja |
|---|---|---|
| Qwen3.8-27B (Unsloth UD) | https://huggingface.co/unsloth/Qwen3.8-27B-GGUF | Apache-2.0 |
| Qwen3.8-27B ISTA GSQ-RCO IQ3_XXS-mtp | https://huggingface.co/ISTA-DASLab/Qwen3.8-27B-GSQ-RCO-GGUF | Apache-2.0 |
| Ternary Bonsai 2 27B (PrismML), Q2_0 | https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf | Apache-2.0 |
| Bonsai 2 27B PTQ1_0 + głowica MTP | https://huggingface.co/sudoingx/Ternary-Bonsai-2-27B-PTQ1_0-MTP-GGUF | Apache-2.0 |
| Underdog Saluki 27B + MTP | https://huggingface.co/Kujira/Underdog-Saluki-27B-1.0-MTP-GGUF | **CC BY-NC 4.0 — tylko niekomercyjnie** (od 2026-11-05) |
| Qwen3.5-9B | https://huggingface.co/unsloth/Qwen3.5-9B-GGUF | Apache-2.0 |
| LFM2.5-24B-A2B | https://huggingface.co/LiquidAI/LFM2.5-24B-A2B-GGUF, https://huggingface.co/unsloth/LFM2.5-24B-A2B-GGUF | LFM Open 1.0 (firmy < $10M przychodu) |

## 4. Gotowe ustawienia (dla zaawansowanych)

Wspólne: `llama-server -ngl 999 -fa on -ctk q4_0 -ctv q4_0 -c <kontekst> -ub <batch> --jinja`.

| Klasa | Silnik | Dodatkowe flagi | batch |
|---|---|---|---|
| 32 GB, 24 GB (Enigma dziś) | llama.cpp b11856 | `--spec-type draft-mtp --spec-draft-n-max 3 --spec-draft-n-ubatch 64` | 5090: 1024, 4090/3090: 256 |
| 24–32 GB (silnik Enigmy) | fork + kvq + lean | `--spec-draft-n-max 4 -ctkd q4_0 -ctvd q4_0 --spec-draft-vocab draft_vocab_qwen38.txt --spec-draft-vocab-n 65536 --spec-draft-head-type iq4_xs --spec-mtp-type iq4_xs`, env `GGML_CUDA_KVQ=1 LLAMA_SPEC_LOOKUP=3 LLAMA_SPEC_LOOKUP_W=16 LLAMA_GPU_VERIFY=1` | 5090: 512, 4090/3090: 256 |
| 16 GB (Enigma dziś) | llama.cpp b11856 | bez MTP | 256 |
| 16 GB (silnik Enigmy) | b12110 + lean | `--spec-type draft-mtp --spec-draft-n-max 2 --spec-draft-n-ubatch 64 -ctkd q4_0 -ctvd q4_0` | 256 |
| 11–12 GB (silnik Enigmy) | PrismML b12128 | `--spec-type draft-mtp --spec-draft-n-max 2` | 4070/3060: 256, 2080 Ti: 512 |
| LFM2.5 | llama.cpp | `-ctk q8_0 -ctv q8_0`, 8–10 GB: `--n-cpu-moe 20` (10 GB) / `26` (8 GB) | 512 |

Pełna tabela z VRAM-em w szczycie: `wiki/produkt/final-recipes-nvidia.md`.

## 5. Jak to osiągnęliśmy (tekst na stronę, wersja krótka)

1. **Spekulacja MTP dobrana do karty.** Qwen3.8-27B ma wbudowaną głowicę, która zgaduje kolejne tokeny, a model sprawdza je jednym przebiegiem — odpowiedzi są identyczne, tylko szybciej. Najlepiej działa 2–3 tokeny naprzód, nie 4.
2. **Pełny kontekst bez marnowania pamięci.** Zwykły llama.cpp rezerwuje ~1 GB na bufor spekulacji, który nigdy się nie wykonuje. Nasza poprawka zwalnia tę pamięć — to ona pozwala zmieścić 262 144 tokenów na 24 GB i ponad 200 000 na 16 GB.
3. **Nasz kernel atencji `kvq`** czyta skwantyzowany kontekst bez kopiowania go do pełnej precyzji. Oszczędza pamięć (4090: 0,5 GB mniej przy 64k), dzięki czemu długi kontekst w ogóle się mieści; przy długich rozmowach pisze też szybciej (3090 przy 64k: 102,5 → 112,2 t/s).
4. **Najlepszy model dla każdej ilości pamięci.** 27B nawet na kartach 11–12 GB dzięki 2-bitowemu Bonsai 2 z doszczepioną głowicą MTP.
5. **Każde ustawienie sprawdzone na prawdziwej karcie** z pełnym wypełnieniem kontekstu, nie wyliczone z kalkulatora.

## 6. Zastrzeżenia (muszą być na stronie lub w przypisach)

- **Kolumna „z silnikiem Enigmy” wymaga publikacji archiwów silników** (fork kvqlean, b12110lean, prism) i pliku `draft_vocab_qwen38.txt` na release Enigmy (`app/engine/CONTRACT.md`, sekcja „Silniki Enigma CUDA — brakujący krok”). Do tego czasu aplikacja używa zwykłego llama.cpp i daje wartości z kolumny „Enigma”.
- **Limity mocy wynajętych kart:** 4090 była przycięta do 250 W (domyślnie 450 W), 3090 340 W, 5060 Ti 160 W, 3060 140 W — liczby 4090 są zaniżone względem karty na pełnej mocy. Pisać „zmierzone na wynajętej karcie”.
- **Pomiar 67c to 1 seed × 6 promptów;** porównania silników na 5090 robione naprzemiennie (A-B-B-A) na tym samym hoście.
- **Fork CUDA dla 16 GB** nie jest wybierany (zmierzony tylko na 5060 Ti: 49,4 t/s przy 196 608).
- **Saluki:** tylko do użytku niekomercyjnego; w wersji komercyjnej 12 GB = Bonsai 2.
- Bonsai 2 to inna kwantyzacja Qwen3.8-27B (2 bity, trytowe), czyli słabszy w jakości niż 4-bitowy 27B na większych kartach. Na stronie nie porównywać jakości między klasami.
