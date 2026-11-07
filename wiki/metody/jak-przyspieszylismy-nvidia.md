---
typ: metoda
tags: [metody, nvidia, cuda, enigma, mtp, kontekst, playbook]
aktualizacja: 2026-11-07
zrodlo: ~/KERNEL/product/research/67-nvidia-vast-kampania.md; 67b-wybor-modeli-nvidia.md; 67c-nvidia-backlog-testow.md; 65-vram-rezerwa-mtp-kontekst.md; ~/KERNEL/product/SITE-NVIDIA.md
status: aktualne
---
# Jak przyspieszyliśmy Enigmę na NVIDIA: 262 144 przy 101–149 t/s (kampania 67)

**Największe zyski nie przyszły z nowych kerneli pisanych pod NVIDIA, tylko z przeniesienia tego, czego nauczyliśmy się na AMD (zwolniona rezerwa MTP, kernel `kvq`, fork z MTP n=4 i słownikiem draftu), z poprawnego modelu pamięci i z wyboru modelu z pomiarów zamiast z kalkulatora; RTX 5090 62,5 → 148,6 t/s, RTX 4090 46,9 → 101,3 t/s, obie przy pełnym 262 144 (2026-11-07).**

## Co dało ile (w kolejności wkładu)

| Krok | Co zrobiliśmy | Efekt (zmierzony) |
|---|---|---|
| 1. MTP na upstreamie, dobrane n | `--spec-draft-n-max 3` zamiast sztywnego 4; n=2 na lean 16 GB | 4090 46,9 → 76,4 (+63%), 5090 62,5 → 102,2 (+63%); n4 na 5090 −10% vs n3 |
| 2. Rezerwa draftu proporcjonalna do ctx×ub | `--spec-draft-n-ubatch 64` (flaga upstreamu, nikt jej nie ustawiał) | 648 → 40 MiB przy 262k, wyjście bez zmian |
| 3. Batch 256 w planerze | `ub 256` jako kandydat | 4090 262 144 z MTP mieści się (ub 512: OOM) |
| 4. Model pamięci z prawdziwych buforów | `-lv 4` na 19 konfiguracjach, dopasowanie z błędem ≤23 MiB; usunięty mnożnik wzrostu forka 3,77 | planer: 4090 152k → **262 144**, 3090 160k → 245 760 |
| 5. Lean reserve z AMD → CUDA | łatka 0002 z topka-q63 (raport 65) nałożona na b12110 i na fork CUDA | 16 GB z MTP: 4060 Ti 24,0 → 36,3 (+51%) przy 229k; fork mieści 262 144 |
| 6. Fork CUDA + `kvq` + lean | `cuda-topka2` (MTP n4, słownik 64k, lookup W16, GPU verify) + kernel `kvq` + lean | 4090 76,4 → **101,3**, 5090 100,9 → **148,6** (ten sam host), 3090 61,5 → 80,0 |
| 7. Model z pomiarów, nie z kalkulatora | Gemma wyrzucona; Bonsai 2 PTQ1_0 + głowica MTP na silniku PrismML | 3060 22,2 → 58,3 (×2,6), 2080 Ti 39,6 → 78,0 |

## Nauki (dlaczego to zadziałało)

1. **Przenosić wiedzę między vendorami, zanim pisze się nowe kernele.** Rezerwa MTP marnowała ~1 GiB na ROCm (raport 65) i dokładnie tak samo na CUDA. Ta sama łatka dała 262k na obu.
2. **Mierzyć pamięć buforami, nie kalkulatorem.** Planer liczył 3,9 GiB „wzrostu” zmierzonego na naszym forku i ucinał 24 GB do 160k, a upstream rośnie o 2–28 MiB. Limit to suma CUDA (`cudaMemGetInfo`), nie `nvidia-smi` (różnica 313–498 MiB per karta). Zob. [[lekcja-zapas-doladowania-kerneli-cuda]].
3. **Załadowanie ≠ działanie.** 16 GB z MTP ładowało się z 0,5–0,66 GiB wolnego i padało przy pierwszym długim prompcie; dopiero fill pełnego kontekstu to łapie. Walidacja = load + fill na dokładnie tych flagach, które uruchamia aplikacja.
4. **Wybór modelu to decyzja, nie domyślna wartość.** Domyślne picki Enigmy (Gemma 4 12B, 27B Q3 przy 135k) były „dopasowane”, a nie najlepsze; po przeglądzie bazy wiedzy (Saluki, Bonsai, ISTA, LFM) 12 GB dostało 2,6× szybszy 27B. Zob. [[lekcja-pick-z-kalkulatora]].
5. **Ten sam host, naprzemiennie (ABBA).** 5090 „86,9 vs 102,2” to był limit mocy hosta (450 vs 575 W), nie silnik; dopiero ABBA na jednym hoście pokazało, że pin b11856 jest szybszy od b12110 o ~9% z MTP. Zob. [[lekcja-limit-mocy-hosta]].
6. **Paczki budować przenośnie.** Fork z `-march=native` dawał `Illegal instruction` na hoście 3090 bez AVX2; build `GGML_NATIVE=OFF` i wariant bez AVX2 działają wszędzie. Zob. [[lekcja-paczka-march-native]].
7. **Licencje sprawdzać w dniu publikacji.** Saluki przeszedł z Apache-2.0 na CC BY-NC 4.0 dwa dni przed kampanią. Zob. [[lekcja-licencja-modelu-sie-zmienia]].
8. **Krótkie ramiona, fill tylko raz.** Kilka minut na wariant (load + `spec_sweep` + md5), pełne wypełnienie tylko dla finalnego zestawu; druga runda: 11 kart + walidacja wszystkich picków w ~2,5 h za $5.
9. **Wyniki negatywne zapisujemy.** `p-min` szkodzi wszędzie; flagi CUDA (typ KV, grafy, `GRAPH_OPT`, `-t`, PDL) w szumie albo gorzej; `kvq` na sm_120/sm_86 to −4…−5% w krótkim kontekście (zysk głównie w pamięci); b12110 nie zastępuje pinu.

## Gdzie co jest
- Strona: `product/SITE-NVIDIA.md`; tabela z flagami i VRAM: [[final-recipes-nvidia]].
- Wyniki: [[2026-11-07-kampania-nvidia-vast]], [[REKORDY]], `product/research/67-nvidia-vast-kampania.md`.
- Kod: `app/engine` (commity `1a1896a`, `e584d42`), łatka lean `qwen-opt/patches/nv67-lean-reserve/`, narzędzia `qwen-opt/cloud/nv67/`.
- Co dalej: [[backlog-testow-nvidia]] (fork na 4060 Ti/5080, warianty bez AVX2 na 4090/5090, publikacja archiwów).

## Powiązane
- [[metody/_hub|metody]]
- [[playbook-optymalizacji]]
- [[raport-67-kampania-nvidia]]
- [[raport-65-vram-rezerwa-mtp]]
- [[lekcja-rezerwa-mtp-kopia-f16]]
- [[glowica-mtp]]
- [[pomiar-abba]]
