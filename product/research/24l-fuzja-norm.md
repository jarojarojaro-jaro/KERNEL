# 24l — Fuzja RMS norm do MMVQ (GGML_HIP_NORM_FUSE): zatrzymane po faulcie GPU

Data: 2026-10-19. Gałąź `norm-fuse` (~/wt/normfuse, od topki caf2b8e14). Przełącznik `GGML_HIP_NORM_FUSE=1`, domyślnie wyłączony.

## Werdykt

**STOP. Fuzja jest odrzucona w tej postaci.** Pierwszy job GPU (`nf-tests`) zawiesił taśmę PM4. Proces skończył się z wiszącym dispatchem, potem był page fault i mode1 reset GPU (21:10:09, `test-norm-tail` pid 456530). Zgodnie z zasadą sprzętową build jest zatrzymany, bez ponawiania. Pozostałych jobów (md5, tg128, spec_sweep) nie uruchomiono. **Zysku nie zmierzono.**

## Co zbudowano

- Zamiast prologu w GEMV jest **ogon producenta**. Norma po `MUL_MAT+ADD` (residual) liczy się w ogonie tego samego launchu MMVQ (n=1, n=2..8 oraz WMMA 9..16 kolumn; typy Q4_0/Q8_0/Q4_K/Q5_K/Q6_K/IQ4_XS/IQ4_NL).
  - Każdy blok po swoich zapisach bierze atomowy ticket. Bloki z ostatnimi ticketami (1 fala na blok) czekają, aż wszystkie bloki się wpiszą.
  - Część fali liczy sumy kwadratów swoich warpów normy, dokładnie tak jak `rms_norm_mul_f32_unrolled<NV>`, i publikuje je w buforze ticketów.
  - Potem czeka na pozostałe części wiersza, robi końcową sumę DPP, `rsqrtf` i `scale*x*w`, a na koniec `quantize_q8_1_group<true>`.
  - Planer: `ggml_cuda_norm_tail_plan` w ścieżkach mm+add i mm+reshape+add, pomija węzły RMS_NORM i MUL.
- Pierwsza wersja (pełny odczyt wiersza przez każdą falę) podbijała VGPR we **wszystkich** kernelach has_fusion: 35 → 199, część dostała scratch, czyli wypadała z PM4. Dlatego jest druga wersja:
  - publikowanie sum warpów;
  - osobny parametr szablonu `norm_tail`.
  
  Statycznie (kmeta.py, gfx1100): wszystkie 798 dotychczasowych kerneli `mul_mat_vec_q*` mają **identyczne** VGPR/SGPR/scratch/LDS jak topka. 106 nowych wariantów z ogonem nie ma scratchu.

## Wyniki (jedyny pomiar, `~/qwen-opt/normfuse/logs/`)

| Test | Wynik |
|---|---|
| `test-norm-tail`, 216 przypadków (6 typów × 2048/4096/5120 × 1–16 tokenów), off vs on (wpp domyślne) | wyjście normy F32: **216/216 identyczne bitowo**; wynik następnego matvec: **13/216 różne** |
| przypadki różne | tylko Q4_K (7), Q5_K (4), Q4_0 (2); Q6_K/Q8_0/IQ4_XS 0/108. Te same złe hashe przy wpp=1 (deterministyczne) |
| wpp=1 (32 części na wiersz) | po 177 przypadkach **zawieszenie**: IQ4_XS, 5120, 12 tokenów (WMMA, 320 bloków, 384 części > 160 fal ogona) → `ggml_hip_pm4: tape of 3 dispatches did not complete within 10 s` → abort |
| GPU | 21:10:09 `[gfxhub] page fault` SQC(data) @0x0, STATUS 0x00801431, potem mode1 reset, VRAM lost |
| test-backend-ops, md5, tg128, spec_sweep | nie uruchomione |

## Przyczyna (analiza CPU)

1. **Mechanizm faultu nie jest dostępem poza zakres w nowym kodzie.**
   - SQC(data) @0 ze STATUS 0x00801431 to dokładnie sygnatura z raportu 17. Tam taśma PM4 z `PRIV=0` (`GGML_HIP_PM4_WA=0`) była wywłaszczana w trakcie dispatchu (CWSR) i po przywróceniu miała wskaźnik kernargów 0.
   - Ten sam scenariusz był w 17 R1: wiszący IB PM4, wyjście procesu, REMOVE_QUEUE, reset.
   - Mój `tests.sh` **nie ustawił środowiska PM4**. Domyślnie `GGML_HIP_PM4` jest włączone, a `WA=0` to wersja bez poprawki PRIV. Testy szły więc przez taśmę bez obejścia.
   - Odczyty i zapisy ogona to ładowania wektorowe (klient TCP), nie SQC. Statycznie każdy indeks mieści się w zakresie:
     - x/dst: `row*ncols+col`;
     - q8: `/32`;
     - tickety: do słowa 529 z 4096+530 zaalokowanych.
2. **Prawdziwy defekt: protokół oczekiwania między blokami potrafi się zawiesić.** Zawieszenie wystąpiło w klasie kształtów, gdzie fala ogona ma kilka części (nparts > nblocks/2), przy kernelu WMMA ze 157 VGPR. Wcześniejsze przypadki tej klasy (Q4_K/Q5_K/Q6_K/Q8_0) przeszły.
   - Analiza kolejności (fala bierze części rosnąco po wierszach, wiersze 0–4 to same pierwsze części) nie pokazuje cyklu. [INFERENCE] Pozostają dwie przyczyny:
     - brak gwarancji postępu dla spin-wait między workgroupami w dispatchu taśmy;
     - stan liczników rozjechany po wywłaszczeniu.
   
   Tego nie da się rozstrzygnąć bez GPU.
3. **Rozjazd wyniku następnego matvec** przy bitowo równej normie F32 dotyczy tylko typów, które używają sumy bloku q8_1 (`ds.y`). [INFERENCE] Konsument czyta inne bloki q8_1 niż te, które zapisałby kernel normy: różna suma albo inny slot/kolejność. Przyczyna nieznana. Samo to dyskwalifikuje zmianę, bo wymóg to bitowa zgodność.

## Działania

- Bez dalszego czasu GPU dla tej gałęzi. Kod jest zacommitowany jako negatywny wynik (`norm-fuse`, przełącznik domyślnie wyłączony). Topka bez zmian.
- Gdyby wracać do tematu:
  - joby testowe zawsze z `GGML_HIP_PM4=0` albo `WA=2`;
  - test q8_1 blok po bloku (dump slotu cache) zamiast hasha wyniku;
  - protokół bez spin-waitu: ostatni blok liczy całą normę, bez czekania między blokami.
  
  Zysk ogona i tak jest niepewny, bo krytyczna ścieżka ogona to ~3 rundy L2.

## Do bazy wiedzy

- Kod z oczekiwaniem między workgroupami (spin na liczniku) **nie może iść na GPU przez taśmę PM4 bez `WA=2`**. Wiszący dispatch plus wyjście procesu daje mode1 reset (17 R1, 24l).
- Domyślne `GGML_HIP_PM4` w buildach topki jest włączone z `WA=0`. Każdy test spoza `run-topka.sh` musi jawnie ustawić PM4.
- Dodanie kodu ogona do wspólnego kernela MMVQ (bez parametru szablonu) podbija VGPR wszystkich wariantów has_fusion, także przy wyłączonym przełączniku. Nowe ścieżki trzeba dawać jako osobne instancje. Porównanie metadanych: `~/qwen-opt/normfuse/kmeta.py LIB.so REGEX`.
- Norma z publikowaniem sum warpów jest bitowo zgodna w F32 (216/216). Wyniki kolejnego matvec trzeba jednak porównywać na q8_1 blok po bloku: różnice wyszły tylko na typach z `ds.y`.
