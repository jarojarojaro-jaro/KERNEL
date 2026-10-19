# 21m: Declarative Attention (KAIST + Google DeepMind) – czy to coś dla nas?

**Werdykt: NIE dla nas (triage, bez eksperymentu).** U nas (batch 1, hybryda GDN: tylko 16 z 64 warstw ma pełną atencję, KV q4_0 + `kvq`) koszt zależny od kontekstu to **~4.5% kroku decode przy 29.5k i ~14% przy 94k**. Nawet idealny DA (maska 100%, zero dodatkowych tokenów, MTP bez zmian) skraca sesję agenta najwyżej o **~1.4% / ~4.6%**. Z liczbami z pracy dla Qwena (−20% odczytów, **+32% tokenów wyjścia**) decode **zwalnia o 25–30%**. Prefill nie zyskuje nic, a prompt rośnie o ~4.6% tokenów. Metoda jest stratna (−2.1 pp), działa tylko z wyłączonym myśleniem i psuje bramki bitowe. Kryterium odcięcia („idealny sufit < 5% zegara sesji”) jest spełnione już na arytmetyce, więc symulacja na CPU nic by nie zmieniła.

## Liczby

| wielkość | 29.5k (≈32k) | 94k | źródło |
|---|---|---|---|
| krok MTP n=4 (weryfikacja 5 tok.), ms | 31.4 | 35.0 | `long_ctx.jsonl` e2e-final-dkvq4: 105.16 t/s × 1/(1+4·0.575); 100.58 t/s × 1/(1+4·0.63) |
| krok przy 1.7k, ms | 30.0 | 30.0 | 130.2 t/s, akceptacja 0.727 |
| część kroku zależna od kontekstu, ms (udział) | 1.4 (4.5%) | 5.0 (14.3%) | różnica powyżej `[SZACUNEK]` |
| dolna granica odczytu KV (16 warstw atencji, q4_0) | 0.57 ms | 1.81 ms (+~0.45 głowica MTP) | `qwen-opt/research/v2/rr-prefill-kv.md:65-73` |
| **idealny DA**: decode / sesja (decode = 32% zegara) | −4.5% / **−1.4%** | −14% / **−4.6%** | |
| **DA wg pracy (Qwen)**: 1.32× kroków, 0.8× odczytów | 1.32·30 + 0.8·1.4 = 40.7 ms vs 31.4 → **+30%** | 1.32·30 + 0.8·5 = 43.6 vs 35.0 → **+25%** | arytmetyka |
| maks. narzut tokenów, przy którym idealny DA wychodzi na zero | 4.7% | 16.7% | x·30 < 1.4 / 5.0 |
| prefill: dodatkowe tokeny promptu (instrukcja + rusztowanie segmentów) | +4.6% | +4.6% | Tab. 4 pracy (2.3% + 2.3–2.4%) |
| prefill: część oszczędzana przez DA | 0 | 0 | „The estimate excludes prefill, which DA does not reduce” (§5.2) |

## Co twierdzi praca i co z tego jest prawdą (arXiv 2609.02737 v2, kod `itsnamgyu/declarative-attention` @24110b7)
- Mechanizm: model pisze w CoT tagi `<global>`, `<focus magic_chunks="N">` i `<local>`. Kontekst jest pocięty na ~2K-tokenowe „magic chunks” udające wyniki narzędzi. Silnik (hook na vLLM 0.29) przepisuje block table, więc kernele FA czytają mniej bloków. KV zostaje nietknięty: to „compaction” metadanych, w pełni odwracalna. Maska działa **tylko na warstwach globalnych**, a GDN/SWA zostają bez zmian.
- **Nagłówki się zgadzają, ale dotyczą łącznej liczby obsłużonych tokenów KV na odpowiedź, nie czasu:** Gemma-4-31B −45.8±5.6% przy −1.40 pp, Qwen-3.6-27B −19.6±7.4% przy −2.10 pp. Dla Qwena 3 przebiegi dały 31.1 / 5.8 / 21.9%.
- „Do 99%” dotyczy pojedynczego kroku w trybie `<local>` przy kontekście > 128k. Kroki `<global>` to ~26% tokenów, ale >80% obsłużonych tokenów DA.
- Słabości metodyki:
  - baseline'y to tylko vanilla i DA-bez-maski, bez Quest/DSA na tych samych zadaniach;
  - w kompozycji z DSA DA daje 278% kroków i 128% skanu indeksera względem samego DSA;
  - zestaw 15 źródeł jest **wybrany**, a 6 źródeł, na których DA przegrywa, trafiło do dodatku E.3;
  - sędzią jest Qwen-3.5-4B;
  - **myślenie było wyłączone** (protokół nie działał w śladach myślenia);
  - spadki dla Qwena koncentrują się w zadaniach wielofragmentowych (−4.84 pp);
  - przy długim kontekście na Qwenie spada dokładność i maleje oszczędność.
- Czas: model rooflinowy B200 przy dużym batchu (matmul liczony jako compute-bound, współdzielony) daje Qwen 0.87× (zakres 0.78–1.01) i globalny odczyt KV = **86%** kroku. U nas ten sam odczyt to ~5–14%, bo przy batchu 1 dominuje odczyt wag, a 48 z 64 warstw to GDN. W pomiarze per krok Qwen zyskuje 31% tylko w koszyku maski > 90%, a przy małej masce ma narzut 3.9%.

## Odpowiedzi na pytania
1. **Udział globalnej atencji u nas:** decode ~4.5% kroku przy 32k i ~14% przy 94k (~19% przy 128k po ekstrapolacji liniowej `[SZACUNEK]`). Sufit e2e: 1.4% / 4.6% zegara sesji. Realnie wynik jest ujemny przez +32% tokenów.
2. **Prefill:** DA nic nie daje, a nawet kosztuje (+4.6% tokenów promptu, a prefill to 58% zegara, czyli ok. +2.7% sesji). Atencja prefillu (FA ≈ 26% przy 94k) wymagałaby innej metody (rzadki prefill), a nie deklaracji modelu: tokenów narzędzi nie generuje model.
3. **Stratność, MTP i bitowość:**
   - Tekst zmienia się z założenia, więc greedy md5 i bramka KLD/kanarki nie mają sensu. KV tokenów wygenerowanych pod maską zostaje w historii i wpływa na kolejne tury.
   - Pod MTP zmiana trybu w środku draftu wymaga maski per wiersz w weryfikacji i cofania automatu stanów przy rollbacku. Maska KQ w llama.cpp to umożliwia, ale `kvq` musiałby pomijać kafle niespójnych zakresów.
   - Zawężanie atencji głowicy MTP już testowaliśmy (S3 `--spec-mtp-window 8192`): akceptacja spadła 3.31 → 2.78, a t/s 105 → 90 (`qwen-opt/NOTES.md`, S3). Bez maski na głowicy MTP draft i tak czyta cały KV.
4. **Offloading sterowany przez model / odwracalna kompakcja vs nasza decyzja „KV tylko w RAM”:**
   - Konfliktu nie ma i zmiana nic nie wnosi. DA nie przenosi KV, tylko pomija bloki.
   - Wariant z offloadem do RAM hosta nie pasuje: każdy krok `<global>` potrzebuje całego KV na GPU. Przy 94k to 1.74 GB, czyli ~70 ms przez PCIe 4.0 x16 (~25 GB/s) na każde przejście do `<global>`, przy kroku 35 ms.
   - Na 24 GB przy limicie 128k nie mamy presji VRAM na KV aktywnej sesji. Warstwa RAM (`--cache-ram`) służy nieaktywnym sesjom, nie stronicowaniu aktywnej.
5. **Coś taniego:** nie.
   - Symulacja maski na CPU wymagałaby prefillu 27B na ~90k tokenów na 2 rdzeniach, czyli godzin na prompt. Zmierzyłaby też tylko to, co arytmetyka już ogranicza z góry (sufit 4.6%).
   - Nagrania odpowiedzi z repo dotyczą benchmarków bez myślenia, nie naszych sesji.
   - Powrót do tematu ma sens tylko wtedy, gdy pojawi się model trenowany pod DA, z myśleniem i narzutem tokenów < 10%, a my będziemy pracować przy ≥ 200k.

## Działania
- Brak wdrożeń i eksperymentów. Temat zamknięty kryterium odcięcia (idealny sufit < 5% zegara sesji).
- Do wykorzystania gdzie indziej: przy batchu 1 na hybrydzie liczy się koszt wag i kroków, a nie odczyt KV. Każda metoda, która wydłuża wyjście (CoT, tagi), przegrywa u nas z wyprzedzeniem.

## Źródła
- Praca: https://arxiv.org/abs/2609.02737 (v2, 14.10.2026): Tab. 2, 3, 4, §2.3, §5.2, §8.2.
- Kod: https://github.com/itsnamgyu/declarative-attention (commit 24110b7, vLLM 0.29, SM100).
- Nasze: `~/qwen-opt/long_ctx.jsonl` (e2e-final-dkvq4), `qwen-opt/NOTES.md` (S3, T1), `qwen-opt/research/v2/rr-prefill-kv.md:65-73,202`, `wiki/lekcje/lekcja-agent-prefill-nie-decode.md`, `wiki/decyzje/2026-10-19-kv-tylko-w-ram.md`.

## Do bazy wiedzy
- **fakt:** Qwen3.8-27B na XTX (MTP n=4, KV q4_0, `kvq`): krok 30.0 ms przy 1.7k, 31.4 ms przy 29.5k i 35.0 ms przy 94k. Część zależna od kontekstu to 4.5% / 14% kroku.
- **raport:** 21m Declarative Attention: NIE. Pomaga tylko w decode przy dużym batchu (B200, globalny odczyt KV = 86% kroku). U nas idealny sufit to ≤ 4.6% sesji, a realnie +25–30% czasu decode przez +32% tokenów. Prefill bez zysku, metoda stratna (−2.1 pp na Qwen-3.6-27B), wymaga trybu bez myślenia.
- **lekcja:** liczby „mniej odczytów KV” z prac serwerowych przeliczać na nasz krok batch 1. Na hybrydzie GDN odczyt KV globalnej atencji to < 15% kroku nawet przy 94k.
