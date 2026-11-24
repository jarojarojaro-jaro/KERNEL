---
typ: ekosystem
tags: [ekosystem, vllm, rdna4, serwowanie, produkt, enigma]
aktualizacja: 2026-11-24
zrodlo: https://github.com/GGZ14/vllm-mxfp4 (README, `d6162425`, 2026-10-13; wersja repo 0.12.0, obraz `stilldeadcode/vllm-radiance:0.9.3`); ~/KERNEL/product/research/66d-saber-engine-rdna.md:25,189
status: aktualne
---
# vLLM-Radiance (GGZ14/vllm-mxfp4): serwer vLLM dla R9700, czyli „prod”, z którego autor przenosi Sabera

**Na prędkość XTX to nie wpływa (tylko gfx1201, wagi MXFP4 i KV fp8 są stratne), ale to najlepszy znany nam przykład tego, czego brakuje aplikacji Enigma: jedna komenda od klonu do działającego serwera, wykrywanie sprzętu zamiast konfiguracji, KV zmierzone na danej karcie, czytelne diagnozy i uczciwie opisany benchmark.**

## Co robi (README `d6162425`)
- **Instalacja:** `./docker-quickstart.sh` sprawdza hosta (dostęp do dockera, `/dev/kfd`, `/dev/dri`, wolne miejsce na obu dyskach, wolny port), pobiera ~40 GiB, startuje serwer, czeka na `/health`, mówi, co robi log (kompilacja kerneli, wagi, grafy), i oddaje terminal dopiero po prawdziwej odpowiedzi na czat. Ponowne uruchomienie pomija zrobione kroki, a pobieranie wznawia się. Do tego `status`, `logs`, `test`, `stop`, `restart`, `clean` i `DRY_RUN=1`.
- **Wykrywanie sprzętu:** `gpu-detect.sh` czyta `mem_info_vram_total` z sysfs i odrzuca karty poniżej 8192 MiB. Dzięki temu iGPU (2 GiB Granite Ridge) nie wchodzi do liczby kart; bez tego wybrałby TP=3. TP to największe z 8/4/2/1, które dzieli też głowice GDN (16/48).
- **KV zmierzone, a nie policzone:** profilowanie vLLM zostawia 0,93 GiB/kartę (5,7% cache) zapasu, więc autor mierzy pojemność per sprzęt i kształt (`kv-profiles.tsv`, klucz `2x7551-32624` + maxseqs/chunk/maxlen/spec) i przypina ją.
- **Diagnoza:** kernel, który się nie podepnie, „po cichu spada na wolniejszą ścieżkę”, więc serwer drukuje tabelę wyboru kerneli (`RADIANCE_R4D_REPORT=1`). README ma tabelę objaw → przyczyna → komenda i listę nieszkodliwych linii logu.
- **Pomiar:** BetterBench 0.4.0 z korpusem i datą. Raportują ms/krok zamiast t/s, bo „t/s skacze ~14% od samego szczęścia akceptacji”, a do tego `tok/update` i TTFT per kategoria. Kod 253,8 t/s i proza 109,4 t/s mają ten sam krok 22,8–23,2 ms; różnica to tylko akceptacja. Jakość: WikiText-2 PPL 8,3708, GSM8K 97,8%. Jest też ledger zmian w `PERFORMANCE.md`.
- **Pułapka sterownika:** przy 4 kolejkach HIP firmware czasem kładzie kolejkę kopii na tej samej rurze co model i cały proces chodzi 43–44 zamiast 35 ms/krok. `GPU_MAX_HW_QUEUES=1` dało 0 wolnych startów na 22 (wcześniej 1 na 19). Na XTX z Mayą wartość 2 dała 0% (K-135 w [[KOLEJKA-TESTOW]]), ale dla użytkowników Enigmy z RDNA4 to realny przełącznik.

## Porównanie z naszymi odpowiednikami
| warstwa | vLLM-Radiance | u nas |
|---|---|---|
| instalacja | jedna komenda, wznawianie, test na końcu | Enigma: instalator bez sumy i podpisu, bez kopii poprzedniej wersji ([[inference-stack]], punkt 5) |
| wykrywanie GPU | próg VRAM 8 GiB odcina iGPU | Enigma pomyliła APU z kartą ([[lekcja-enigma-apu-jako-karta]]) |
| rozmiar KV | zmierzony per sprzęt i kształt, zapisany w tabeli | Enigma: szacunek pamięci (`catalog/index.ts:188-195`); zmierzone konfiguracje tylko dla kart z naszej kampanii 67 (`VERIFIED`, `:204-215`), nie na karcie użytkownika |
| cichy fallback | tabela wyboru kerneli w logu | Enigma nie czyta `splits = N`; strażnik deep 32k złapie gorszego kandydata, ale nie bazę, która od startu liczy FA na CPU (63c E10, niezrobione) |
| benchmark | ms/krok + tok/update per kategoria, ważona mieszanka | Enigma: t/s z zegara serwera; lab: ms/krok w `spec_sweep` ([[reward-hacking-inferencji]]) |
| droga do własnego silnika | Saber przenosi ten działający stos kernel po kernelu z bramką bajtową ([[saber-engine]]) | Enigma Turbo pisana od zera, testy tylko na syntetycznym modelu, bełkot 0,7 t/s ([[enigma-turbo-gemini-2026-11-20]]) |

## Co bierzemy
1. Do Enigmy: próg VRAM przy wykrywaniu kart, KV mierzone przy Optimize i zapisane per sprzęt, tabela „co się podpięło” w diagnostyce, `status/logs/test` jako komendy.
2. Do procesu: własny silnik tylko jako przeniesienie działającej referencji krok po kroku z bramką bajtową, nigdy od zera.
3. Do raportów: ms/krok obok t/s, `tok/update` per kategoria, data i wersja korpusu przy każdej liczbie.

## Powiązane
- [[saber-engine]]
- [[inference-stack]]
- [[lekcja-uczymy-sie-nie-tylko-predkosc]]
- [[radeon-ai-pro-r9700]]
