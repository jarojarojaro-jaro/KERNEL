# 24j: router ogon lookupu / DFlash2 / MTP na code-edit: negatyw na triażu (2026-10-19)

**Werdykt: kill bez GPU.** Sufit wyroczni na `mvs` wynosi **+1.1%** (T=0) / +2.0% (T=1), daleko pod progiem +8%. Dane: logi per krok konfiguracji topki (tryb 3, W16) `~/qwen-opt/lookup/logs/e4-mvs-{W5,D3,D4}.lk.jsonl` (XTX, 16b E-X2; 3 ramiona dają identyczne kroki). Skrypt: `24j-router-ceiling.py`.

| `mvs` 4×1024 tok. | kroki | tok/krok | kroki bez trafienia ogona | MTP przyjęte w tych krokach | sufit: chybienia → 8 tok. | sufit: każdy krok < 8 → 8 tok. |
|---|---|---|---|---|---|---|
| T=0 | 283 | 14.46 | 15 (5.3%) | 4/4 we wszystkich 15 | **+1.10%** | +2.71% |
| T=1 (seedy 1–2) | 562 | 14.56 | 46 (8.2%) | 4/4 w 32, 3/4 w 10 | +1.96% | +2.35% |

- Sufit jest hojny: DFlash2 (blok 8) dostaje 8/8 tokenów i krok za darmo (koszt = krok MTP4). Prawdziwe akceptacje DFlash2 mogą sufit tylko obniżyć, więc nie liczyłem ich teacher-forced. Na 3090 nasz krok DFlash2 kosztuje 64 vs 46.5 ms dla MTP (16d), a plik draftera dokłada +1.14 GB VRAM.
- Hipoteza się nie potwierdziła. Kroki bez ogona to nie „nowy kod”: MTP przyjmuje w nich zwykle 4/4, tylko lookup nie miał dopasowania ≥ 6. Nowy kod edycji to łańcuchy lookupu odrzucone wcześnie (a = 0–6), a te mieszczą się w kolumnie „każdy krok < 8” (≤ +2.7%).
- Ogon W16 daje już 14.5 z 16 możliwych tok/krok. Blok 8 nie ma czego dołożyć.

**Akcje:** router `LLAMA_SPEC_ROUTER` nie powstaje. Brak gałęzi i commitu, nic do przekazania Pm4Fix2. Przewagi nad TensorFold na 3090 (+3.7%) szukać w koszcie kroku W16 (44.35 vs 39.0 ms na CUDA), a nie w drafterze.

## Do bazy wiedzy
- `lekcje/` (nowa) „Na code-edit ogon W16 nie zostawia miejsca na drugi drafter”: `mvs` W16 to 5.3% kroków bez ogona (wszystkie z MTP 4/4). Sufit routera z DFlash2 wynosi +1.1% (T=0) / +2.0% (T=1), a dla dowolnego kroku < 8 tokenów +2.7%.
- `modele/drafter-dflash.md` (aktualizacja): DFlash2 jako drafter „nowego kodu” obok ogona nie ma uzasadnienia na `mvs`. Potwierdza to 21a §4.3 (budżet 16 wierszy jest już wypełniony).
