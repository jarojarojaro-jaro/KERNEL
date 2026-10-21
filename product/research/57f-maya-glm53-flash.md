# 57f. Project Maya / GLM-5.3-Flash (@PeasantSmith): przegląd A–Z + delta v1.1.20

Data: 2026-10-21. Praca tylko na CPU. Szczegóły wcześniejszych wersji są w R21g (notatki `21g-notatki/maya.md`), R32a (v1.1.17), R39a (v1.1.19) i [[project-maya]]. Tutaj jest synteza i delta `v1.1.19` `3bf6867` → `v1.1.20` `35bb2b2` (2026-10-21).

## TL;DR

1. **Maya to wyspecjalizowany silnik (C++/CUDA/HIP), a nie model.** Służy do uruchamiania gigantycznych MoE na jednym PC: GLM-5.3-Flash (321B, ~18B aktywnych, kontekst do 1M) i DeepSeek-V4.1-Flash-1017 (748B). Eksperci są w trzech poziomach: najczęściej używani w VRAM, kolejni w RAM, reszta czytana z NVMe. Autor: Peasant Smith (GitHub `mw00`), współopiekun `needmorevram`. MIT. **Silnik wyrósł ze Strata** (Niko1221, czyli @coldniko z listy).
2. **„GLM5.3-Flash” w bio to model Z.ai, a Maya dorzuca własne kwanty GGUF** (Maya-S/S24/M/L, 94.7–156.3 GB). Robione są z FP8 Z.ai z imatrix **per ekspert** i zaokrąglaniem GPTQ z error feedback (przepis ISTA-DASLab, czyli ta sama grupa co GSQ-RCO). Maya-L zachowuje 99.2% zero-shot FP8, Maya-S 97.9%.
3. **Liczby (zgłoszenia użytkowników z `./maya.sh --bench`):**
   - 2×H100: 122–124 t/s; 4×4090: 118; RTX PRO 6000: 81; 1×3090 + EPYC: 27 t/s (Maya-M); 3090 + 64 GB RAM IQ2_XXS: 22–24 t/s (@ItsmeAjayKV).
   - **Jedno RX 7900 XT: ~15 t/s** decode, 414 t/s prefill (Maya-S, v1.0.11). R9700 32 GB: 21.4 t/s.
4. **Najważniejsze dla nas w v1.1.20: #304 włącza fuzowane int8-WMMA eksperckie GEMM-y prefillu (gate/up + clipped SwiGLU + down) na gfx1100.** Wcześniej działały tylko na gfx1151. Zysk +5–13% prefillu na 4×7900 XT, a z `MAYA_GLM_PREFILL_ATTN=wmma2` +14–18%. To dowód, że **int8 WMMA na RDNA3 bije MMQ (q8_1 dp4a) w prefillu**. U nas to dotyczy prefillu gęstego 27B (MMQ), a nie dekodu.
5. Dla dekodu Qwen3.8-27B na jednej XTX Maya nie daje nic nowego. Offload ekspertów i tiering SSD nie dotyczą gęstego 27B mieszczącego się w VRAM. Rozgrzewka przed READY (#285) została opisana w R39a.

## 1. Co to jest

- **Project Maya** ([github.com/mw00/project-maya](https://github.com/mw00/project-maya)): instalator (`setup.sh` / `START-MAYA.bat`), silnik per model (`maya` dla GLM, `maya-ds4` dla DeepSeek), serwer API OpenAI + Anthropic (narzędzia, streaming, do 8 równoległych żądań), dashboard z czatem i monitorem VRAM (wagi / KV / pula ekspertów).
- **GLM-5.3-Flash** ([zai-org/GLM-5.3-Flash](https://huggingface.co/zai-org/GLM-5.3-Flash)): MoE 321B z ~18B aktywnymi, MIT. Atencja hybrydowa: projekcje KDA (Kimi Delta Attention, liniowa) oraz MLA z DSA (sparse attention z indekserem). Ma 3 gęste warstwy, 42 warstwy MoE i warstwę NextN (MTP). Wizja przez mmproj. (Skład tensorów wg tabeli karty HF Maya.)
- **Maya-S/S24/M/L**: kwanty GGUF Mai ([peasantsmith/GLM-5.3-Flash-Maya-GGUF](https://huggingface.co/peasantsmith/GLM-5.3-Flash-Maya-GGUF)).

## 2. Kto / skąd

- Peasant Smith (@PeasantSmith na X, `mw00` na GitHubie). Współopiekun: @needmorevram. Duża społeczność PR-ów (~20 kontrybutorów na wydanie; R32a).
- Rodowód: silnik startował od **Strata** (Niko1221, MIT), a potem przepisano go pod GLM: tiering ekspertów, split warstw, dekodowanie MTP. Z ggml/llama.cpp pochodzą formaty kwantów, iloczyny skalarne na CPU i kernele MMQ prefillu (przypięta wersja). Z exllamav3 dekodowanie kafli tensor-core (EXL3). Forward draftera DFlash2 według beellama.cpp (Anbeeld).
- Kwanty: „częściowo na przepisie ISTA-DASLab” (GPTQ-style error feedback per ekspert, ewaluacja jako dokładność zadań względem FP8).

## 3. Jak działa technicznie

1. **Trzy poziomy ekspertów: VRAM → RAM → NVMe**, przenoszonych w trakcie rozmowy według profilu użycia. `--expert-cache` i `--vram-reserve-mib` ustawiają pulę (v1.1.11). Silnik mierzy GPU, CPU, RAM i SSD i sam się stroi (`--calibrate`).
2. **Split warstw między GPU** (heurystyka „midpoint + 2”). Druga połowa liczy też blok MTP, więc obie karty są zajęte. Na AMD nie jest potrzebny P2P, bo przesyłany jest jeden wektor na token. Pary identycznych GPU dzielą też wiersze warstwy.
3. **Eksperci na CPU z helperem GPU:** helper kwantyzuje aktywacje i redukuje ważone wyjścia ekspertów na swoim GPU, zanim odda jeden wektor na token (docs/AMD_MAYA.md).
4. **Dekodowanie spekulatywne:**
   - GLM: własna warstwa NextN (MTP), z ekspertami draftu w Q2_K–Q5_K. Akceptacja ~76% na R9700 + 7900 XT.
   - DeepSeek: drafter DSpark (8 GB). v1.1.20 dodaje odcięcie po skumulowanym prawdopodobieństwie akceptacji (`MAYA_DS4_DSPARK_CUM=0.5`): draft, którego wcześniejsze tokeny prawdopodobnie zostaną odrzucone, nie idzie do weryfikacji. +6.5% na Strix Halo.
   - Setup mierzy, czy drafter w ogóle przyspiesza na danym PC (10–30 min, `--drafting measure|on|off`).
5. **Prefill na AMD:** fuzowane int8 WMMA gate/up → clipped SwiGLU → down dla routowanych ekspertów (geometria 4096/2048, typy IQ), `src/prefill/moe_fused_rdna4.cu`. Test parzystości `tests/hip/prefill_fused_parity.cpp`: 24 pary typów, różnica ≤1e-4 vs MMQ. v1.1.20 (#304) dopisuje gfx1100 do bramki runtime (zmiana 7 linii, bo kernel był już kompilowany dla gfx1100). Atencja prefillu `wmma2` jest opcjonalna.
6. **Rozbicie czasu chunków prefillu** (#284), **sprawiedliwy split wierszy między równoległymi żądaniami** (#324, opt-in), **Stop w trakcie długiego promptu** z zachowaniem już wczytanego kontekstu.
7. **Przepis kwantów** (karta HF):
   - kalibracja na 128×2048 tokenach w szablonie GLM (czat, wielojęzyczny, reasoning, web-kod, tool calls);
   - imatrix **per ekspert** liczony z modelu FP8;
   - GPTQ-style error-feedback rounding gate/up w blokach 256, co obniża błąd wyjścia ekspertów o ~¼ vs zwykłe imatrix przy tym samym rozmiarze;
   - kwantyzery ggml, więc pliki to zwykłe GGUF;
   - mieszanka: eksperci IQ2_XXS…IQ4_XS, `down` w pierwszych i ostatnich 4 warstwach MoE o stopień wyżej, atencja i shared w Q6_K (S24: Q4_K, co daje +1.5 GB na ekspertów i +14% dekodu na 24 GB);
   - indekser DSA i małe projekcje KDA w Q8_0, router i normy w F32.

## 4. Liczby

| Sprzęt | Model | Decode | Prefill | Źródło |
|---|---|---:|---:|---|
| 2×H100 80 GB | Maya-L / M-Derisked, 1M ctx | 122.4 / 123.7 | 2099 / 1986 | README, #258/#259 |
| 4×RTX 4090 | Maya-S24 | 118 | 4129 | README, #89 |
| RTX PRO 6000 96 GB | Maya-M, 256K | 81.0 | 3102 | README, #172 |
| 2×RTX 3090 (225 W) | Maya-S24 | 53.0 | 885 | README, #135 |
| 1×RTX 3090 + EPYC 7702P, 141 GB RAM | Maya-M, 128K | 27.0 | 1069 | README, #157 |
| RTX 3090 + 64 GB RAM | własny IQ2_XXS | 22–24 | 910 (8K) / 1150 (32K) | [X @ItsmeAjayKV](https://x.com/ItsmeAjayKV/status/2109360177598321095) |
| **1×RX 7900 XT 20 GB** | Maya-S, 8K | ~15 | ~414 (4K) | docs/AMD_MAYA.md, v1.0.11 |
| R9700 + RX 7900 XT | Maya-S | ~33 (MTP ~76%) | ~490 | jw. |
| R9700 32 GB | Maya-S | 21.4 | — | README, #213 |
| 4×RX 7900 XT, ROCm 10 | Maya-S24, prefill fused off→on | — | 1.3K: 306→347; 7.9K: 866→919; 16K: 1093→1149 | PR #304 |
| Radeon 8065S (Strix Halo) | Maya-S, 32K | 29.6 (23.2 po 8K) | 278 | README |

Jakość (karta HF, 400 pytań na zadanie, zero-shot): FP8 82.5 → Maya-L 81.8 (99.2%), Maya-M 80.7, Maya-S 80.8, Maya-S24 80.6. Ten sam top token co FP8: 83.1–90.0%; KL 0.188–0.444. Na XTX 24 GB nie ma bezpośredniego pomiaru, jest tylko 7900 XT (20 GB) `[niezweryfikowane dla XTX]`.

## 5. Licencja / dostępność

- Kod Maya: MIT; zawiera notki Strata, ggml, exllamav3 i beellama.cpp. Model GLM-5.3-Flash: MIT; kwanty Maya: MIT.
- AMD jest eksperymentalne (Linux ROCm 7+, Windows HIP): 7900 XT/XTX, R9700/9070, Strix/Gorgon Halo. Na AMD GLM obsługuje tylko tekst.
- Śledzone w CompWatch (`mw00/project-maya`, tier A) i w ZRODLA.

## 6. Co z tego dla nas

1. **Prefill gęstego Qwen3.8-27B na int8 WMMA zamiast MMQ dp4a (gfx1100).** #304 pokazuje +5–13% na ekspertach MoE (int8 vs q8_1, ta sama kwantyzacja aktywacji).
   - U nas prefill 27B idzie przez MMQ (q8_1). Rocm `rocwmma`/WMMA int8 w ggml-cuda MMQ na RDNA3 trzeba sprawdzić w naszej gałęzi.
   - **Zysk:** +5–15% prefillu (TTFT), dekod bez zmian `[INFERENCE]`. **Koszt:** średni. Do przeczytania: `src/prefill/moe_fused_rdna4.cu` (layout kafli, fuzja SwiGLU) i porównanie z naszym `mmq.cuh` dla gfx1100. Najpierw CPU-owy przegląd kodu, potem jeden pomiar `llama-bench -p 4096`.
2. **Odcięcie draftu po skumulowanej akceptacji (`DSPARK_CUM`)** to ten sam pomysł co nasze `p_min` dla DFlash2/DSpark, tylko na iloczynie. Mamy p_min per pozycja (`speculative.cpp:1308-1316`). Wariant z iloczynem kosztuje kilka linii. **Zysk:** 0–5% przy T>0 na prozie (krótsze, tańsze weryfikacje) `[INFERENCE]`. **Koszt:** niski. Warto zrobić razem z próbkowaną ścieżką z R57e.
3. **Duże MoE na XTX + RAM (GLM-5.3-Flash Maya-S24):** realnie ~12–15 t/s na jednej karcie 24 GB (7900 XT 20 GB: ~15). To nowy produkt/scenariusz, a nie przyspieszenie Qwen. **Nie dotyczy** celu 27B. Ewentualnie jako pozycja katalogu „duży model na XTX” po teście 30 min (wymaga ~95 GB na NVMe).
4. **3090:** Maya na 1×3090 daje 22–27 t/s GLM-5.3-Flash. Przydatne tylko jako punkt odniesienia w raporcie porównawczym 3090. Dla Qwen3.8-27B nie dotyczy.
5. **Przepis kwantów (imatrix per ekspert + GPTQ error feedback):** dla gęstego 27B odpowiednikiem jest GPTQ-style rounding w GGUF. To temat GSQ-RCO/ISTA (osobny raport R57 o GSQ-RCO). Bez nowej pracy tutaj.
- **Nie dotyczy:** tiering SSD/RAM, split warstw multi-GPU, helper redukcji ekspertów, cięcie wierszy prefillu DeepSeek (R39a).

## 7. Do bazy wiedzy

- Project Maya v1.1.20 `35bb2b2` (2026-10-21), MIT. Silnik z rodowodem Strata, per model (GLM-5.3-Flash 321B / DeepSeek-V4.1-Flash 748B), eksperci VRAM → RAM → NVMe.
- #304 (v1.1.20): fuzowane int8 WMMA eksperckie GEMM prefillu włączone na gfx1100, +5–13% prefill na 4×7900 XT, z `wmma2` +14–18%. Parzystość ≤1e-4 vs MMQ. Kandydat do przeniesienia na prefill gęsty.
- `MAYA_DS4_DSPARK_CUM=0.5`: odcięcie draftu po skumulowanej akceptacji, +6.5% DeepSeek na Strix Halo.
- Kwanty Maya: imatrix per ekspert z FP8 + GPTQ error feedback (przepis ISTA-DASLab). Maya-L 99.2%, Maya-S 97.9% zero-shot FP8.
- 1×7900 XT: ~15 t/s GLM-5.3-Flash Maya-S; 1×3090: 22–27 t/s.

## 8. Źródła

- https://github.com/mw00/project-maya (README, CHANGELOG v1.1.20, docs/AMD_MAYA.md, docs/SETTINGS.md); lokalny klon `~/qwen-opt/research-src/project-maya` `35bb2b2`
- https://github.com/mw00/project-maya/pull/304
- https://huggingface.co/peasantsmith/GLM-5.3-Flash-Maya-GGUF
- https://huggingface.co/zai-org/GLM-5.3-Flash
- https://x.com/PeasantSmith/status/2112232671023644743, https://x.com/PeasantSmith/status/2110640569378562459
- https://x.com/ItsmeAjayKV/status/2109360177598321095
- https://github.com/Niko1221/Strata
- poprzednie: R21g, R32a, R39a
