# 26 — Kolejka GPU 2026-10-19 wieczorem: wyniki testów odłożonych przez pauzę

Testy z raportów 24a, 24f, 24g, 24k, 21o i 17 (S6) przeszły po kolei, jeden na raz, przez `~/qwen-opt/queue/run-queue.sh` i `run-jobs.sh` (blokady GPU+quiet trzymane przez całą kolejkę, kontrola logu jądra po każdym teście). Logi: `~/qwen-opt/queue/logs/`. 0 błędów GPU, max hotspot 71 °C.

## Werdykt

| Zmiana | Wynik (ABBA) | md5 / testy | Decyzja |
|---|---|---|---|
| **PM4 WA=2 + GUARD + `HSA_USE_SVM=0`** (17) | Qwen spec_sweep T=1 111.0/110.8 → **115.3/115.8 t/s (+4.2%)**, 29.13 → 27.80 ms/krok; T=0.7 +4.9%; LFM tg128 266.4/266.2 → **295.7/296.2 (+11.1%)** | S6: 5 × 241 = **1205 zapytań, 0 błędów**; md5 c4708318 / 6f14e814 / 894e56e4 | **wdrożone w topce** (19:57) |
| Bariera tylko-LDS (24a, `94e4c92c8`) | Qwen pp4096 1133.2/1127.9 (off) vs 1129.7/1127.8 (on); LFM 6124.8/6125.9 vs 6149.4/6128.1; czat 102.5 vs 102.4 | MUL_MAT 540/540, FA 740/740, md5 bez zmian | **odrzucone** (w szumie) |
| MMVQ n=1 szerokie ładowania (24f, `9be6076d5`) | Qwen tg128 40.86/40.88 (0) vs 40.41/40.52 (wide=2, −1.0%), 41.02 (wide=1); LFM 265.4/258.0 vs 266.9/266.9 | md5 identyczne (Qwen, MTP, LFM) | **odrzucone** |
| Ogon OOV draft-head, klastry (21o, `cfc463dc1`) | 111.0/110.9 → 109.4/109.2 t/s (**−1.5%**) | — | **odrzucone** |
| Fuzja norm → prolog GEMV (24g), górny limit | tg128 40.82 → 42.69 t/s przy pominięciu 129 norm (**+4.6%**, 1.07 ms/token) | wyjście celowo błędne (pomiar) | **robić**: limit > progu 0.3 ms |
| Koszt kroku W16 (24k), profil | krok MTP 31.0 ms vs W16 37.3 ms: matmul +2.4, GDN+conv +1.3, normy/reszta +1.1, **bezczynność GPU +1.6 ms** (2 przerwy ~0.9 ms vs ~0.3 ms) | — | następny krok: weryfikacja draftu na GPU (bez kopii ~16 MB logitów) |
| Binarki z serwera kompilacji (25) | — | MUL_MAT 822/822, FA 567/567, md5 bez zmian | **rbuild poprawny** |

## Wpadki i poprawki
- Podgląd landingu na porcie 18433 zabrał port `greedy.sh` → md5 testu 24f nie wyszło; podgląd przeniesiony na 18533, test powtórzony.
- `orphan-guard.sh` zabił serwer testowy z kolejki `run-jobs.sh` (nie było go na liście właścicieli) → jedno ramię czatu 24a przepadło. Teraz właścicielem jest każdy przodek z otwartą blokadą GPU/quiet.

## Do bazy wiedzy
- PM4 z poprawką PRIV (WA=2) jest stabilne w produkcji: 1205 zapytań bez błędu; zysk +4% na Qwenie (MTP, kroki ~28 ms) i +11% na LFM (krótkie kroki, więcej narzutu uruchomień).
- Bariera tylko-LDS i szerokie ładowania MMVQ n=1 są poprawne bitowo, ale nic nie dają na XTX: wąskim gardłem nie są bariery ani liczba instrukcji ładowania.
- W kroku W16 ~1.6 ms to GPU czekające na CPU — najtańszy kierunek dla edycji kodu.
