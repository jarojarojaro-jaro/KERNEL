# 57c. @MiaAI_lab (Mia's AI Lab): przepisy inferencji na DGX Spark

Źródło: bio badacza (współtwórca GSQ-RCO) z listą silników: „@MiaAI_lab (DGX Spark)”. Czytałem README i patche repo `MiaAI-Lab/Qwen3.8-Flash-Next-Single-DGX-Spark-TensorFold` (płytki klon `656879f`, 2026-10-18, w `~/qwen-opt/research/mia-tf`), stronę mia-ai.net i wpisy X (tylko przez wyniki wyszukiwarki, bo X blokuje czytnik). Bez GPU. W KB jest już TensorFold (`wiki/repo/tensorfold.md`) i Flare (39f), więc tu opisuję tylko to, co Mia dokłada.

## 1. Co to jest

Mia nie pisze własnego silnika. Robi **„przepisy”**, czyli repo z `start.sh`, patchami do cudzego silnika, przypiętym checkpointem i benchmarkami, które serwują duże MoE na 1–3 DGX Spark (GB10, 128 GB pamięci zunifikowanej, ~273 GB/s). Silniki:

- **TensorFold** (`ashhart/TensorFold`, Zig, gałąź `zig-flashnext`): główny dla Qwen3.8-Flash-Next i GLM-5.3-Flash;
- **SGLang**: DeepSeek-V4.1-Flash na 3× Spark (DSpark spec-decode);
- wcześniej Python TensorFold i checkpoint MLX 4-bit.

Do pomiarów używa własnego narzędzia **sparkDash** (`MiaAI-Lab/sparkDash`).

## 2. Kto / skąd

„Mia's AI Lab” (<https://mia-ai.net>, GitHub `MiaAI-Lab`, X `@MiaAI_lab`) to niezależny twórca przepisów, finansowany przez GitHub Sponsors. Najpopularniejsze repo, `DeepSeek-v4-Flash-DSpark-2x-DGX-Spark`, ma ~1.1k gwiazdek. Licencja skryptów: MIT (Qwen TF) lub AGPL-3.0 (`start.sh` starszego przepisu). Tożsamość osoby `[niezweryfikowane]`.

## 3. Jak działa technicznie (przepis Qwen3.8-Flash-Next, 1× Spark)

- **Checkpoint:** `nvidia/Qwen3.8-Flash-Next-FP4-Local` (QAD od NVIDIA). Routed experts są w NVFP4 (grupa 16, skale **CSF-compressed**), attention i shared-expert w MXFP8, MTP i wieża wizji też skwantowane. Do tego **26.8 GiB tablica n-gram/PLE w NVFP4, czytana z dysku przez `pread`** z read-ahead następnego chunka promptu, a nie trzymana na GPU. 512 ekspertów, 10 na token. Alternatywa INT4-AutoRound tnie do top-5 (4.8B aktywnych) i ma ~10% niższą jakość według autorów tego checkpointu.
- **Patche 0011–0015** to wkład Mii:
  - 0012: obsługa NVFP4/CSF/MXFP8 w silniku Zig;
  - 0013: tuning (głębokość draftu MTP 6, repeat-cache, burst admission);
  - 0014: kafel ekspertów w pamięci współdzielonej dla prefillu;
  - 0015: sprawiedliwy prefill.
- **Spekulacja:** tylko głowa MTP, głębokość 6, „hybrid stop rule”: running product przy ≤ 5 strumieniach, próg pewności 0.5 powyżej. Kontrakt „drafted == `"draft": false`” sprawdza `tools/exact.py`. Na CUDA nie ma copy-draftera, więc na kodzie jest o 15–21% wolniej niż w buildzie Python, który go ma.
- **Repeat-prompt cache (`TF_FLASHNEXT_REPEAT_CACHE`):** serwer trzyma stan **o jeden token krótszy** od już obsłużonego promptu. Powtórka liczy wtedy 1 wiersz, a TTFT dla promptu 63 tokenów spada ze 170 do 70 ms. Na hybrydzie liniowej to jedyny tani sposób, żeby po trafieniu w prefiks i tak mieć logity ostatniej pozycji.
- **Burst admission (`ADMIT_WAIT_MS=3`):** bezczynny serwer czeka 3 ms na kolejne żądania, żeby prefill zrobić jednym przebiegiem.
- **Prompt expert tile (0014):** dla chunków promptu ≥ 1024 wierszy routed experts idą przez kernel z kaflem w shared memory. Wynik bitowo identyczny, cold prefill +13–15% (4k: 2,325 → 2,665 t/s).
- **Fair prefill (0015, opt-in):** prompt wypełniany plasterkami po 2 warstwy, najkrótszy pierwszy, z „aging” 1024 wiersze. Krótkie żądanie za pięcioma promptami 100k czeka 1.8 s zamiast 187 s, a najdłuższa przerwa dekodera spada z 12–15 s do 0.27 s. Koszt: +~20% całkowitego czasu mieszanego obciążenia.
- **FP8 KV:** klucze z dwiema skalami, wartości jako kody. Indexer key i pooled blocks zostają w bf16. 17,888 B/token vs 30,784 bf16 (×1.72 pojemności), ~98.8% zgodności top-1 z bf16. Format przeniesiony z patcha `0038-glm-kv-fp8` z przepisu GLM.
- **System-memory cache (0010, opt-in):** KV i snapshoty w zwykłej zablokowanej pamięci (`cuMemHostRegister`) zamiast `cuMemCreate`. Obchodzi `NV_ERR_NO_MEMORY` w GB10 pod obciążeniem (103 → 0–10 komunikatów, t/s bez zmian).

## 4. Liczby (wszystkie: 1× DGX Spark GB10, pomiary autorki, README)

| Konfiguracja | Decode 1 strumień | Agregat 5 strumieni | Prefill | Źródło |
|---|---|---|---|---|
| Qwen3.8-Flash-Next NVFP4 QAD, TensorFold Zig, FP8 KV, MTP, sparkDash, proza | **46–55 t/s** (rozrzut ~15%: 46.2/46.9/48.5/55.0) | 132.7 t/s | 2,665 t/s @4k → 2,197 @128k | README §Performance |
| to samo, `bench_streams.py`, thinking on, 256 tok | 49.8 t/s | 198.2 t/s | 2,400 @4k → 2,264 @126k | README |
| INT4-AutoRound (top-5), Zig, przed FP4 | 64.4 t/s | 200.9 (8 strumieni) | 2,526–2,643 | README |
| DeepSeek V4.1 Flash 1017, 2× Spark, EXL3-EAQv1 2.9 bpw | 75 t/s proza | 130 t/s (4) | 2,000–2,175 | wpis X 2112105974546694249 `[niezweryfikowane – tylko snippet]` |

Pozostałe pomiary:

- Needle w 194,723 tokenach: znaleziony, prefill 99.4 s.
- Pula KV dla FP4: 24.36 GiB, ~1.46 M tokenów FP8, 5 okien po 262k.
- Teacher forcing Zig vs Python: 98.9% zgodnych tokenów (2,270/2,295).
- Dla porównania w KB: Spark + Qwen3.8-27B (dense) w atlas NVFP4 + DFlash2 = 34.4 t/s (`watch/2026-10-20.md:82`).

## 5. Licencja / dostępność

Skrypty i patche są otwarte (MIT, część AGPL-3.0). Silnik TensorFold jest otwarty. Wagi mają własne licencje: NVIDIA Open Model Agreement i Qwen Community License 1.0. Obraz Docker oparty na `nvcr.io/nvidia/pytorch` podlega licencji NVIDIA. Działa tylko na GB10/CUDA.

## 6. Co z tego dla nas

| # | Pomysł | Dla kogo | Zysk (szacunek) | Wysiłek | Uwagi |
|---|---|---|---|---|---|
| 1 | **Repeat-cache „stan N−1”**: przy trafieniu w cały prompt trzymać checkpoint GDN o 1 token krótszy i liczyć tylko ostatni wiersz (zamiast cofać się do odległego checkpointu) | XTX, 3090, Orca | TTFT powtórki/regeneracji: −100 ms lub więcej (u nas checkpoint GDN to 94–180 ms, R35/32b) `[INFERENCE]` | 0.5–1 dnia w `server` (slot save przy końcu promptu −1) | Bezstratny. Sprawdzić najpierw, czy nasz cache promptu już nie robi tego samego |
| 2 | **Fair prefill (plasterki warstw, najkrótszy pierwszy)** | tylko przy `-np > 1` | 1 użytkownik: 0 | 2–4 dni | Dla produktu wieloagentowego; dla E0/chat nie dotyczy |
| 3 | **Kafel ekspertów w shared memory dla prefillu** | nie dotyczy (27B dense) | — | — | Dotyczy MoE (Flash-Next). Odpowiednikiem u nas jest MMQ, gdzie mamy własne kafle |
| 4 | **FP8 KV ze skalami** | 3090 (brak FP8 HW), XTX (brak FP8) | ujemny w bajtach vs q4_0 (zob. 39f #6) | — | Nie dotyczy. Jedyna lekcja: 98.8% top-1 przy FP8 to realny koszt jakości, a nasz q4_0 KV warto zmierzyć tą samą metryką |
| 5 | **Metodologia: rozrzut 1 strumienia ±15% raportowany jawnie**, mediana z 3 startów serwera | wszystkie | 0 t/s, lepsze decyzje | 0.5 dnia | Przyjąć przy porównaniach w CompWatch: liczba Mii „46–55” to zakres, nie punkt |

Główny wniosek: na Sparku (273 GB/s) Qwen3.8-27B dense robi 34 t/s (atlas). Nasz XTX z 79–104 t/s jest szybszy dla jednego użytkownika. Przewaga Sparka to 128 GB, czyli MoE 125B i 5 × 262k kontekstu, a nie szybkość.

## 7. Do bazy wiedzy

- Mia's AI Lab = przepisy (start.sh + patche + benchmark sparkDash), nie silnik. Silnikiem jest TensorFold Zig (Ash Hart) albo SGLang.
- Qwen3.8-Flash-Next NVFP4 QAD na 1× Spark: 46–55 t/s (1 strumień, rozrzut 15%), 132.7 t/s przy 5 strumieniach, prefill ~2.2–2.7k t/s.
- Trik: repeat-prompt cache trzyma stan hybrydy o 1 token krótszy (TTFT 170 → 70 ms).
- Trik: kafel ekspertów w shared memory dla chunków ≥ 1024 wierszy daje prefill +13–15% bitowo identycznie.
- Fair prefill: 2 warstwy na plasterek, shortest-first z aging; czekanie krótkiego żądania 187 s → 1.8 s.
- NVIDIA FP4 QAD: CSF-compressed skale NVFP4; tablica n-gram/PLE 26.8 GiB czytana `pread` z dysku.
- FP8 KV: 98.8% zgodności top-1 z bf16 (pomiar autorki).
- GB10: `NV_ERR_NO_MEMORY` przy `cuMemCreate` pod obciążeniem; obejście przez `cuMemHostRegister`.
- CompWatch: dodane `MiaAI-Lab/Qwen3.8-Flash-Next-Single-DGX-Spark-TensorFold` (tier B).

## 8. Źródła

- <https://github.com/MiaAI-Lab/Qwen3.8-Flash-Next-Single-DGX-Spark-TensorFold> (README, patches 0010–0015)
- <https://mia-ai.net/>, <https://mia-ai.net/models>
- <https://github.com/MiaAI-Lab>
- <https://github.com/MiaAI-Lab/DeepSeek-v4.1-Flash-DGX-Sparks>
- <https://github.com/ashhart/TensorFold/tree/zig-flashnext>
- <https://huggingface.co/nvidia/Qwen3.8-Flash-Next-FP4-Local>
- X: <https://x.com/MiaAI_lab/status/2111540267840901174>, <https://x.com/MiaAI_lab/status/2112105974546694249>, <https://x.com/MiaAI_lab/status/2112812782508794105> (treść tylko ze snippetów wyszukiwarki)

## 9. Dodatek 2026-10-21: czy nasz serwer już robi „stan N−1”? (sprawdzenie kodu, `~/wt/topka-int`)

**Werdykt: tak. Robi to w wariancie N−4, a przejście na N−1 nic by nie dało.**

- `tools/server/server-context.cpp:4174-4193`: przy `do_checkpoint` prefill łamie batch tak, żeby checkpoint powstał **4 + n_ubatch** oraz **4** tokeny przed końcem promptu (`checkpoint_offsets[] = {4 + n_ubatch, 4}`, wzorzec upstream PR #20288). Checkpoint tworzy się przed `llama_decode` (`:4246-4250`, `create_checkpoint` `:2655`), a `LLAMA_CKPT_VRAM` robi szybki snapshot (`:2716-2719`).
- `:3850`: `pos_min_thold = pos_next − n_swa − (has_new_tokens ? 0 : 1)`. Przy dokładnej powtórce (brak nowych tokenów) próg wymusza checkpoint sprzed końca.
- `:3902-3942`: przywracany jest najgłębszy checkpoint z `pos_min < pos_min_thold` (dla GDN to ten sprzed 4 tokenów).
- `:3977-3981` [TAG_PROMPT_LOGITS]: `n_past--`, czyli zawsze liczy się ≥ 1 token, żeby były logity.
- Wynik: dokładna powtórka lub regeneracja przelicza **~4 tokeny w jednym ubatchu** zamiast całego promptu. N−1 zamiast N−4 to wciąż jeden forward, więc różnica wynosi 3 wiersze w MMVQ/MMQ przy N ≤ 8, czyli praktycznie zero `[INFERENCE]`.
- Jedyna różnica wobec Mii: jej stan „N−1” jest trwały per prompt (repeat-cache), a nasz checkpoint może zostać wyrzucony z kolejki `n_ctx_checkpoints` (`:2677-2685`) albo przez min-step (`:2662-2670`). To nie jest powód do zmian. `cache_share` nie występuje w `topka-int` (grep pusty).
- **Nie wdrażamy.** Pomysł #1 z §6 jest zamknięty jako „już mamy”.
