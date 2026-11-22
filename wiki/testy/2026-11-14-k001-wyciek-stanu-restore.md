---
typ: test
tags: [testy, xtx, determinizm, cache, mtp, kolejka]
aktualizacja: 2026-11-14
zrodlo: ~/KERNEL/qwen-opt/k001/k001.py; ~/KERNEL/qwen-opt/k001/res/{k001.json,xtxbench.log} (run 1114-205229-k001-aa; pierwszy run 1114-203645); ~/KERNEL/qwen-opt/k001/k1114.jobs; kod topka-q70 tools/server/server-context.cpp (load_slot_draft), src/llama-kv-cache.cpp (v_heads)
status: aktualne
model: qwen3-8-27b-uncensored
karta: rx-7900-xtx
wyniki:
  - qwen3-8-27b-uncensored | rx-7900-xtx | 130,4 t/s | dekod T=0 1,7k; topka-q70, PM4 | 2026-11-14
  - qwen3-8-27b-uncensored | rx-7900-xtx | 122,6 t/s | dekod T=0 1,7k; topka-q70, bez PM4 | 2026-11-14
k: K-001
---
# 2026-11-14: K-001 — „wyciek stanu” przy restore to zależność od historii serwera, nie od lookupu, sprzężenia ani PM4

**Na produkcyjnym silniku topka-q70 (XTX, eco 2200) odpowiedź T=0 po restore slotu 1,7k zależy od tego, co serwer liczył wcześniej. Pierwszy restore i restore zaraz po tym samym tekście dają md5 świeżego prefillu (3f26f79c). Po innym żądaniu (krótki czat, prefill 32k) albo przy świeżym prefillu na używanym serwerze md5 się zmienia (38028947, 3dd78584, 501b8c06). Wzór jest identyczny i deterministyczny w 4 konfiguracjach: produkcja, `LLAMA_SPEC_LOOKUP=0`, `LLAMA_SPEC_COUPLED=0`, `GGML_HIP_PM4=0`.**

| krok (ten sam serwer, kolejno) | md5 T=0, 256 tok. | drafty / przyjęte |
|---|---|---|
| F: świeży prefill (osobny serwer) | 3f26f79c | 276 / 185 |
| R1: pierwszy restore | 3f26f79c | 276 / 185 |
| R1b: restore po R1 | 3f26f79c | 276 / 185 |
| R2: restore po krótkim czacie | 38028947 | 282 / 184 |
| R3: restore po prefillu 32k | 3dd78584 | 286 / 183 |
| F2: świeży prefill na używanym serwerze | 501b8c06 | – |

**Wnioski:**
- **Źródłem nie jest restore pliku.** F2 (bez restore) też się różni. Nie są nim też lookup, sprzężone losowanie ani taśma PM4: w każdej z 4 konfiguracji te same md5 w tych samych krokach.
- **Stan draftu z pliku jest ładowany poprawnie.** `load_slot_draft` czyści KV draftu (`seq_rm`) i wczytuje go z pliku.
- **Hipotezy otwarte [INFERENCE]:**
  - Wskaźnik `v_heads` odpada: `seq_rm` całego slotu ustawia `head` na najniższą zwolnioną komórkę (`src/llama-kv-cache.cpp`, sprawdzone w kodzie).
  - Zostają trzy kandydaci: `n_kv` z `used_max_p1` po wcześniejszych żądaniach, czyli inny zakres FA; komórki pamięci rekurencyjnej GDN; stan `common_speculative` spoza pliku slotu.
  - Mechanizm: drobna różnica numeryczna zmienia akceptację draftu i szerokość weryfikacji, a od tego zmienia się tekst. Odpowiedzi są tak samo poprawne, ale nie są powtarzalne.
- **Poprawka #30541 (llama.cpp v1.0.0) tu nie pomoże:** dotyczy `LLAMA_STATE_SEQ_FLAGS_ON_DEVICE`, a topka zapisuje sloty z `FLAGS_NONE`.
- **Prędkość przy okazji:** decode T=0 przy 1,7k produkcja 130,4 t/s, bez PM4 122,6 t/s (PM4 daje +6,4%).

**Następny krok (1 job ≤ 10 min):** log `n_kv`, `used_max_p1` i indeksów komórek GDN przy R1 i R2 (`-lv 4` albo jednolinijkowy log w topce). Jeśli różnią się tylko `n_kv`, to poprawka jest bezstratna: zerować `used_max` przy pustym slocie, wtedy numeryka jest jak na świeżym serwerze. Do tego czasu xtxbench bierze md5 tylko z pierwszej rundy po starcie (zasada bez zmian).

## Powiązane
- [[KOLEJKA-TESTOW]]
- [[2026-11-08-kvq-once-profil]]
- [[xtxbench-szybki-ab]]
- [[lekcja-ten-sam-serwer-pending-h]]
- [[lekcja-glebokosc-zmienia-tekst]]
