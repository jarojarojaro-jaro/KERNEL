# 25. Zdalny serwer buildów (Vast) + `rbuild`

Data: 2026-10-19. Autor: podagent BuildFarm. Cel: kompilacje agentów poza lokalnym CPU (2 sloty × 2 rdzenie).

## Werdykt

Działa. Jedno polecenie `~/qwen-opt/tools/rbuild <worktree> [cele…]`; pełny build topki na zdalnym 24 vCPU w
**232–271 s**, zero kompilacji lokalnie. Toolchain identyczny co do wersji (diff pusty), a wynik **bitowo identyczny**
z lokalnym buildem tego samego drzewa: 109/109 plików `bin/` mają te same `.text/.rodata/.data/.hip_fatbin`
(różni się tylko RUNPATH w trybie `--prefix`). Testy GPU (test-backend-ops, greedy md5) **nie zrobione — pauza GPU**.

| pomiar | wartość |
|---|---|
| maszyna | Vast 53521855: Xeon E5-2678 v3, przydział 24 vCPU (48 widocznych), 97 GB RAM, NVMe, Meksyk |
| cena | $0.094/h, transfer $0/TB; do 17:15 UTC ~1.2 h najmu ≈ $0.11 (stawka × czas) |
| instalacja toolchainów (ubuntu:24.04) | 226 s / 141 s (+ ~1 min start Vast) |
| pełny build, zimny ccache, -j24 | 269 s, 271 s; po wyłączeniu ccache dla HIP: 232 s |
| pełny build bez ccache: czas CPU | 272 s ściany, 3719 s user + 121 s sys |
| pełny rebuild z ciepłym ccache (przed wyłączeniem HIP z ccache) | 9.3 s |
| rbuild bez zmian (push + make no-op + diff sha1) | 9 s całość, 4 KB pobrane |
| pobranie po pełnym buildzie | 23 MB zstd (115 MB surowo); typowo 2.4–14 MB |
| 1 TU, 1 wątek: `mmq-instance-q4_k.cu` / `llama-model.cpp` | lokalnie 10.5 / 6.7 s, zdalnie 24.4 / 14.6 s |
| lokalny pełny build -j2 (szacunek) | 3840 CPU·s ÷ 2.27 (rdzeń 5700X szybszy) ÷ 2 ≈ **~14 min** [SZACUNEK; Main obserwował ~50 min trzymania quiet.lock przez buildy -j2] |

## Jak to działa

- `buildfarm.sh up <offer>` (`~/qwen-opt/cloud/`): ubuntu:24.04 + **te same deby** ROCm 10.0.0~pre4-32424980240
  (`repo.radeon.com/rocmradeon/apt/26.14`, `amdrocm-core-dev10.0-gfx1100`; obraz `rocm/dev-ubuntu-24.04:10.0.0-full` to
  wydanie „stable”, nie nasze rc4), CUDA 12.8 jako ten sam env conda (lista URL+md5 z `~/opt/cuda-12.8/conda-meta`, ta
  sama ścieżka `/home/jaro/opt/cuda-12.8`), gcc 13.3 / cmake 3.28 z noble-updates. Na końcu diff wersji z lokalnymi
  (hipcc 7.15.26333, clang 23.0.0git 8f497e09, nvcc V12.8.93, cublas 12.8.5.5, gcc 13.3.0-6ubuntu2~24.04.1): pusty.
- Kod CPU: `GGML_NATIVE=ON` jak lokalnie, ale `/usr/local/bin/ccache` (wrapper) zamienia `-march=native` na
  rozwinięcie gcc z naszego Ryzena (`-march=znver3 … -mno-avx512f … --param=l1-cache-size=32 …`), więc `.text`
  libggml-cpu jest identyczny z lokalnym; `remote-build.sh` odmawia wysyłki, gdy libggml-cpu/base/libllama mają `zmm`
  (zmierzone: 0).
- **Pułapka znaleziona:** ccache zmienia `__hip_cuid_*` (clang liczy go m.in. ze ścieżki wyjścia, a ccache kompiluje do
  pliku tymczasowego) → 140/140 bundli fatbin różnych, 4/140 obiektów kodu z innym układem funkcji. Dlatego TU HIP
  idą z pominięciem ccache (make i tak buduje tylko zmienione). Po poprawce fatbin identyczny.
- Migawka brudnego drzewa (HEAD + zmiany + małe tekstowe pliki nieśledzone) jako commit o stałej dacie (ten sam sha
  dla tego samego drzewa), `git push` (tylko nowe obiekty), checkout pod tą samą ścieżką; HEAD na serwerze cofany do
  lokalnego HEAD, więc stringi wersji/commitu są jak w lokalnym buildzie.
- Zabezpieczenia kosztu: watchdog lokalny (N h), samozniszczenie na instancji (N h + 15 min), `idle-kill.sh` (30 min
  bez buildu). `idle-watch.py` pomija etykiety `buildfarm*`; `down.sh --all` i masowe `vastai destroy instances`
  w `lib.sh` nie ruszają `buildfarm*` (16:48 pierwszą instancję skasował teardown innego agenta).

## Użycie

```
~/qwen-opt/tools/rbuild ~/wt/<drzewo> llama-server test-backend-ops    # do <drzewo>/build-hip/bin
~/qwen-opt/tools/rbuild --prefix /tmp/x ~/wt/<drzewo>                  # do /tmp/x/bin, RUNPATH $ORIGIN
~/qwen-opt/tools/rbuild -B build-cuda ~/wt/<drzewo> llama-server       # CUDA 12.8
~/qwen-opt/cloud/buildfarm.sh status | run '<cmd>' | down | find 0.25 | up <offer> --hours N
```
Serwer nie odpowiada → `rbuild` sam robi lokalny `cpuheavy --quiet … -j2`. Symulacje CPU innych agentów: tylko
z wejściami pobieranymi na serwerze z HF, przez `buildfarm.sh run` (opis: `~/qwen-opt/tools/README.md` §4).

## Nie zrobione

- test-backend-ops (MUL_MAT, FLASH_ATTN_EXT) i greedy md5 (c4708318 / 6f14e814) na binarkach zdalnych — **pauza GPU**
  (zadanie czekało na blokadę i zostało zabite przy pauzie). Zastępczo: bitowa zgodność kodu z lokalnym `build-hip`.
- Zmierzony lokalny pełny build (tylko szacunek z czasu CPU i 1 TU, żeby nie grzać CPU).
- Build CUDA zdalnie nieuruchomiony (toolchain zainstalowany i zgodny wersjami).

## Do bazy wiedzy

- Builduj przez `rbuild`; wynik zdalny = lokalny bit w bit (sekcje kodu/danych), ~4–4.5 min pełny build, sekundy przyrostowo.
- ccache psuje bitową zgodność HIP (`__hip_cuid` zależy od ścieżki wyjścia) — TU HIP bez ccache.
- Obraz `rocm/dev-ubuntu-24.04:10.0.0-full` ≠ nasz ROCm 10.0.0~pre4; dokładna kopia = te same deby z rocmradeon/apt/26.14.
- Bezpośredni port SSH na Vast bywa filtrowany — `buildfarm.sh up` przechodzi na proxy `sshN.vast.ai`.
