# 30 — Dostęp do Intel Arc i Apple Silicon + plan testów na MacBooku M1 Pro 16 GB

Data: 2026-10-20. Research tylko z sieci i z CLI Vast (bez wynajmu, bez GPU). To jest **delta względem R05** (`05-chmura-gpu-do-testow.md`, 2026-10-15) i karty [[arc-b580-i-mac]]. Rzeczy już opisane w R05 tylko potwierdzam albo poprawiam ceny.

## Werdykt w skrócie

- **Intel: nadal nie ma wynajmu godzinowego.** Vast.ai 2026-10-20 02:34 UTC: 5039 ofert (`rentable=any verified=any`), wszystkie `gpu_arch=nvidia`, 99 nazw kart, **0 Intel i 0 AMD** (zapytania `gpu_arch=intel`, `gpu_name=Arc_A770`, `Arc_B580`, `A770` zwracają 0). Uwaga: operator `~` z zadania (`gpu_name~Arc`) zwraca w vastai 1.8.3 błąd „Unknown operator”. Najtańsza realna opcja to **GigaGPU Arc Pro B60 za £129/mies.**: bare metal, root, Ubuntu, UK. To ten sam krzem BMG-G21 co B580 i to samo pasmo 456 GB/s.
- **Apple, karta „Apple M4” z landingu: Scaleway M4-M** (M4, **32 GB**, €0.29/h). Minimum 24 h daje **€6.96 za sesję**. To najtańszy M4 z ≥ 24 GB. Nowość względem R05: R05 znał tylko M4-S 16 GB.
- **Apple, krótkie testy na górnym końcu: Enverge Mac Studio M5 Ultra 256 GB, $2.50/h, rozliczane co minutę, bez minimum.** Godzina testu kosztuje $2.50. AWS wymaga minimum 24 h: M4 Max to $150 za sesję, a M3 Ultra $300.
- **Darkbloom to nie wynajem maszyn.** To API inferencji routowane na cudze Maki, bez SSH. Do testów się nie nadaje.
- **M1 Pro 16 GB użytkownika: domyślny limit GPU to 2/3 RAM ≈ 10.67 GiB.** Bez zmian mieści się **Saluki 27B IQ2-mix + MTP (8.35 GB)**. Qwen3.8-27B **UD-IQ3_XXS (10.93 GB, ma głowicę MTP)** wejdzie tylko po `iogpu.wired_limit_mb=12288`. UD-Q3_K_XL (13.15 GB) i LFM2.5 Q4 (14.5 GB) odpadają.

## 1. Tabela opcji

Ceny bez VAT, stan na 2026-10-20 (z wyjątkiem pozycji oznaczonych inną datą).

| dostawca | sprzęt | pamięć | cena | min. rozliczenie | dostęp | werdykt |
|---|---|---|---|---|---|---|
| **Vast.ai** (CLI, live) | 0 ofert Intel/AMD na 5039 | – | – | – | Docker/VM | **brak Intela**; tylko NVIDIA |
| **GigaGPU** (UK) | **Arc Pro B60** (BMG-G21, 20 Xe2, 160 XMX), Ryzen 7/9, do 128 GB DDR5 | 24 GB GDDR6 ECC, 456 GB/s | **£129/mies.** | miesiąc (rezygnacja w każdej chwili, działa do końca okresu); bez opłaty startowej | **bare metal, root, SSH**; Ubuntu 22.04/24.04, sterowniki Intel, oneAPI Base Toolkit „na życzenie”, Vulkan 1.3, SYCL, L0; dostawa < 24 h ([gg-b60]) | **Intel: TAK**, najlepszy zamiennik B580 |
| GigaGPU | Arc Pro B70 (Battlemage Pro) | 32 GB, 456 GB/s | £179/mies. | miesiąc; brak w magazynie = 3–5 dni roboczych | jw. ([gg-b70]) | tylko jeśli potrzebne 32 GB |
| Zed Up (DE) | fizyczna karta Arc Pro B60 (Sparkle) | 24 GB | €500 / 6 mies. (R05: od €199 / 2 tyg.) | 2 tyg.–6 mies. | **karta wysyłana pocztą**, trzeba mieć własny host ([zedup]) | nie (drożej niż zakup B580) |
| Intel Tiber AI Cloud | Gaudi 2/3, Data Center GPU Max 1100/1550 | – | – | – | VM/BM | **bez zmian vs R05**: Arc nie ma. Strony `ai.cloud.intel.com` (DNS) i intel.com (blokada bota) nie dały się pobrać, nowych ofert Arc nie znalazłem w wyszukiwarce |
| TensorDock, Hetzner GPU, OVH GPU, Scaleway GPU | tylko NVIDIA (Hetzner: H100…; OVH: L4/L40S/A100/H100/H200/RTX 5000; Scaleway: L4/L40S/H100/B300) | – | – | – | – | brak Intela |
| zakup B580 | Arc B580 | 12 GB, 456 GB/s | ~€270 używana (R05), $249 nowa ([lam-b580]) | – | własna ława | alternatywa, jeśli Intel ma być na stałe |
| **Scaleway** Apple silicon (PAR-1) | **M4-M**: M4 10C CPU / 10C GPU | **32 GB** | **€0.29/h** (€199/mies.) | **24 h** (licencja Apple) → €6.96 | bare metal macOS, SSH, API ([scw-mac]) | **Apple M4: TAK** |
| Scaleway | M4-S / M4-SP: M4 | 16 GB | €0.22 / €0.24/h | 24 h | jw. | za mało pamięci na 27B Q3+ |
| Scaleway | **M4-XL**: M4 Pro 14C / 20C GPU | 64 GB | €0.49/h (€335/mies.) | 24 h → €11.76 | jw. | M4 Pro: TAK (tanio) |
| Scaleway | M1-M 8 GB €0.11/h; M2-M 16 GB €0.17/h; M2-L (M2 Pro 16 GB, też wariant Asahi Linux) €0.21/h | – | – | 24 h | jw. | nie potrzebne (M1 Pro mamy u użytkownika) |
| **AWS EC2 Mac** | mac-m4 (24 GiB), mac-m4pro (48 GiB), **mac-m4max (Mac Studio, 128 GiB)**, mac-m3ultra (Mac Studio, 256 GiB); stare mac2 M1 / M2 / M2 Pro / M1 Ultra | jw. | $1.23 / $1.97 / **$6.25** / $12.50/h; mac2 $0.65, m2 $0.878, m2pro $1.56, m1ultra $5/h (us-east, Vantage) | **24 h** dedicated host, potem co sekundę → m4 $29.5, m4pro $47.3, m4max **$150**, m3ultra $300 | SSH, root (ec2-user + sudo) ([aws-mac], [vantage]) | tylko M4 Max / Ultra, gdy potrzebne; drogo |
| **Enverge** (`mac-studio.enverge.ai`) | **Mac Studio M5 Ultra**, 36C CPU, 64C GPU, 4 TB SSD | **256 GB, 1.2 TB/s** | **$2.50/h** | **co minutę, bez minimum** („no 1-hour minimums”; rozliczenie od create do delete, restart nie zatrzymuje licznika, płatność przez Stripe; plik llms.txt pisze „billed daily”, czyli rozliczenie zbiorcze raz na dobę) | **SSH na konto admin z `sudo`**, macOS z preinstalowanymi Xcode CLT, Homebrew, Python 3, MLX, llama.cpp, Ollama i PyTorch MPS; VNC opcjonalnie ([env-docs], [env-blog]) | **Apple, krótkie testy: TAK**. Dostępności nie sprawdziłem (portal `app.enverge.ai` to SPA za logowaniem). Przy braku mocy działa darmowa kolejka FIFO |
| Enverge (reszta katalogu) | DGX Spark GB10 128 GB $0.75/h (2× $1.65/h), RTX Pro 6000 96 GB $1.95/h, H100 $4, H200 $5.50, B300 $7.50 | – | – | co minutę | SSH przez `relay.enverge.ai` / `*.ssh.enverge.dev` ([env]) | Spark/RTX Pro 6000 to osobny temat (NVIDIA) |
| MyRemoteMac | Mac mini M4 (16/24 GB), M4 Pro 24/48/64 GB, M6, Mac Pro M2 Ultra | – | M4 od $14/dzień lub $85/mies.; M4 Pro 24 GB $229/mies. | 24 h (plan dzienny), miesiąc | root, SSH, VNC ([mrm]) | rezerwa |
| MacStadium / MacinCloud / RentAMac / MacRent / RoundFleet / HostMyApple | Mac mini M2/M4/M6 | 16 GB (najczęściej) | $85–164/mies.; $15–19/dzień | dzień lub miesiąc | MacinCloud managed = konto bez admina | nie (16 GB, brak godzinowego) ([mrm-cmp]) |
| GitHub macOS runners | – | – | – | – | – | brak Metal/MPS (R05) |
| **Darkbloom** (darkbloom.dev, Eigen Labs / Layr-Labs `d-inference`, public alpha od 2026-04-15) | Maki dostawców w sieci | – | rozliczenie za tokeny | – | **tylko API** zgodne z OpenAI (`api.darkbloom.dev/v1`); coordinator w poufnej VM, plaintext u dostawcy; **bez SSH i roota** ([dbl]) | **nie do testów**: nie uruchomimy tam naszego silnika ani benchmarków. To tylko punkt danych rynkowych (prywatna inferencja na Apple Silicon) |

**Licencja Apple:** macOS SLA §3A pozwala na leasing tylko dla „Permitted Developer Services” i wymaga minimum 24 kolejnych godzin ([apple-sla]). AWS, Scaleway i MyRemoteMac to egzekwują. Enverge rozlicza co minutę. `[INFERENCE]` Ryzyko jest po stronie Enverge (może zmienić zasady), dla nas to tylko kwestia ceny.

## 2. Rekomendacje

### Intel

1. **GigaGPU Arc Pro B60, 1 miesiąc, £129** (~$170).
   - Ten sam BMG-G21 i te same 456 GB/s co B580. Dekod jest ograniczony pasmem, więc tok/s powinny być bliskie B580 `[INFERENCE]`. Prefill może wyjść kilka procent niżej, bo B60 boostuje do 2.4 GHz, a B580 do 2.67 GHz `[INFERENCE]`.
   - Dostajemy root, Ubuntu i SSH w < 24 h, a wyłączenie działa na koniec okresu rozliczeniowego.
   - Na karcie landingu podpisać: „Arc Pro B60 (krzem B580)”.
2. **Zakup B580 (~€270)** dopiero wtedy, gdy Intel ma wejść do stałej macierzy, bo zwraca się po ~2 miesiącach dedyka (R05).
3. Na Intelu mierzyć **Vulkan i SYCL (Level Zero)**. Opy `TOP_K/GET_ROWS/SUM_ROWS/ARGSORT` z GPU verify są w `ggml-vulkan` i `ggml-sycl` na `cuda-topka2` (sprawdzone grepem). `GGML_OP_GUMBEL_MAX` (sprzężone próbkowanie) ma tylko CPU i CUDA, więc na Intelu i Metal liczy się na CPU (fallback schedulera) `[INFERENCE: koszt nieznany]`.

### Apple

1. **Karta „Apple M4”: Scaleway M4-M 32 GB, jedna sesja 24 h = €6.96.**
   - Włączyć auto-delete po 24 h.
   - 32 GB mieści Qwen3.8-27B UD-Q4_K_XL (17.56 GB) przy limicie GPU ~21.3 GiB (2/3 z 32 GB) `[INFERENCE]`.
   - Daje też Saluki i Qwen3.8 Q3.
2. **Krótkie sprawdzenie, czy silnik w ogóle działa na Metal: najpierw M1 Pro użytkownika (0 zł)**, potem ewentualnie **Enverge M5 Ultra** na 1–2 h (~$2.50–5). Ten koszt bije każde 24-godzinne minimum: AWS M4 Max to $150.
3. **AWS** tylko wtedy, gdy potrzebny konkretnie M4 Max (128 GB) albo M3 Ultra, i to na kredytach Activate.

## 3. MacBook M1 Pro 16 GB: co się mieści

**Limit GPU.** Metal raportuje `recommendedMaxWorkingSetSize`, a llama.cpp traktuje go jako całą pamięć urządzenia (`ggml-metal-device.m`, [ll-26129]: 21845 MiB na 32 GiB = 2/3).
- Na 16 GiB daje to **10922.67 MiB ≈ 10.67 GiB**. Dopiero od ~64 GB Apple podnosi go do ~75% ([vram-cap]).
- Podniesienie: `sudo sysctl iogpu.wired_limit_mb=<MiB>` (macOS 14+). Ustawienie znika po restarcie.
- M1 Pro ma pasmo 200 GB/s i 14 albo 16 rdzeni GPU.

| model | plik | z MTP | pamięć GPU (szac.) | domyślny limit 10.67 GiB | z `wired_limit_mb=12288` | werdykt |
|---|---|---|---|---|---|---|
| **Underdog Saluki 27B IQ2-mix + MTP Kujiry** (`Kujira/Underdog-Saluki-27B-1.0-MTP-GGUF@5d92db9b`) | **8.35 GB** (7.78 GiB) | tak | ~9.6 GiB przy ctx 20480 / KV q8_0 (3060: 9811 MiB) | **mieści się** | zapas ~1 GiB | **model nr 1** |
| Qwen3.8-27B **UD-IQ3_XXS** (`unsloth@4ca72078`) | 10.93 GB (10.18 GiB) | **tak** (`blk.64.nextn.*`, sprawdzone nagłówkiem GGUF) | ~10.7 GiB przy 16k (W3 IQ3_XXS-mtp: 11.5 GB VRAM) | nie | **tak, ctx ≤ 8–16k**; macOS zostaje ~4 GiB | model nr 2, przy zamkniętych aplikacjach |
| Qwen3.8-27B UD-Q3_K_XL | 13.15 GB (12.24 GiB) | tak | ~13 GiB | nie | nie (potrzeba ~14 GiB limitu, macOS < 3 GiB → swap) | **nie** |
| LFM2.5-24B-A2B Q4_K_M | 14.53 GB | – | ~14 GiB | nie | nie | **nie** |
| gpt-oss-20b MXFP4 | 12.11 GB (11.28 GiB) | EAGLE3 | ~12 GiB | nie | na granicy | pominąć |
| Qwen3.5-9B Q4_K_M (`unsloth@3885219b`) | 5.68 GB | **nie** (0 tensorów nextn) | ~6.5 GiB | tak | tak | kontrola: tylko ogon lookupu (mvs) |
| Gemma 4 12B Q4_K_M + mtp | 7.12 + 0.47 GB | drafter upstream | ~8.5 GiB | tak | tak | opcjonalnie (nasz graf MTP jest dla qwen35) |

Szacunek roofline dla Saluki: 200 GB/s ÷ ~7.9 GB na token ≈ 25 t/s górnej granicy dekodu bez spekulacji. Realnie spodziewam się ~15–19 t/s `[INFERENCE]`.

## 4. Plan testów na M1 Pro (ok. 2–2.5 h zegarowo)

**Ramiona** (jak w R27: final 3090/3060):
- **U0**: upstream `-m` only (fit sam dobiera ctx, KV f16, bez spekulacji).
- **U1**: upstream + flagi produkcyjne + własne MTP upstreamu.
- **T**: topka, flagi jak U1 + 64k draft vocab, głowice iq4_xs, `LLAMA_SPEC_LOOKUP=3 W=16`, `LLAMA_SERVER_CACHE_SHARE_MIN=1024`, `LLAMA_GPU_VERIFY=1`.

**Źródła:**
- upstream `4c3c5810f` (ten sam co w R27);
- topka `cuda-topka2` @ `2a261101b`: przenośna gałąź, która kompiluje się poza HIP i ma bramkę GPU verify 22/22 na 3090;
- wariant **T+C** = `cuda-topka2` + merge `coupled-topka` (`7cdc0121b`). Dry-run `git merge-tree` przechodzi bez konfliktów (drzewo `0215b3eb`). Na serwerze robimy z niego gałąź `metal-topka` i bundle.

**Narzędzia** z `~/qwen-opt/cloud/runs/nvfinal/inst/`: `spec_sweep.py`, `copy_bench.py` + `copy_prompts.json`, `long_bench.py`, `gate_chat.py`, `draft_vocab_qwen38.txt`. Są w czystym Pythonie i komunikują się przez HTTP z serwerem, więc działają na macOS. VRAM czytamy z logu serwera (`ggml_metal ... allocated`), RAM z `vm_stat`/`memory_pressure`.

| krok | co | czas |
|---|---|---|
| 0 | `sw_vers; sysctl hw.memsize machdep.cpu.brand_string; system_profiler SPDisplaysDataType \| grep -i cores; df -h ~`. Wymagane ≥ 35 GB wolnego miejsca. `pmset -g batt`: musi być zasilacz | 2 min |
| 1 | `scp` bundle git i skryptów z serwera; równolegle `curl -L` Saluki (8.35 GB, sha256 `98f6ebb5…e52`) | ~10 min (zależy od łącza) |
| 2 | buildy, każdy w osobnym katalogu: `cmake -B build -G Ninja -DGGML_METAL=ON -DCMAKE_BUILD_TYPE=Release -DLLAMA_CURL=OFF && cmake --build build -j 8 --target llama-server llama-bench test-backend-ops`. Kolejno: upstream, `cuda-topka2`, `metal-topka` | ~3 × 6–8 min `[INFERENCE]` |
| 3 | **Bramka** (≤ 10 min): `test-backend-ops -b Metal -o TOP_K`, `-o GET_ROWS`, `-o SUM_ROWS`, `-o ARGSORT`; potem `gate_chat.py` z md5 przy `LLAMA_GPU_VERIFY=0` vs `=1` (6 promptów T=0/T=1 + mvs 4). Różnica = T idzie z `GPU_VERIFY=0` | 10 min |
| 4 | **llama-bench Saluki** w kolejności U T T U: `-ngl 999 -fa 1 -ctk q8_0 -ctv q8_0 -p 512 -n 128 -r 3 -o jsonl` (pp512, tg128) | ~8 min |
| 5 | **Serwery Saluki** w kolejności U0 U1 T T U1 U0, każdy świeży. U1: `-ngl 999 -fa on -ctk q8_0 -ctv q8_0 -c 20480 -np 1 --jinja --cache-ram 4096 --reasoning-effort low --spec-type draft-mtp --spec-draft-n-max 2 -ctkd q8_0 -ctvd q8_0`. T: to samo + `--spec-draft-vocab draft_vocab_qwen38.txt --spec-draft-vocab-n 65536 --spec-draft-head-type iq4_xs --spec-mtp-type iq4_xs` + env jak `fin3060.sh`. Na każde ramię: `spec_sweep.py --temps 1.0 --seeds 1,2,3 --tokens 400` (czat) i `copy_bench.py --set mvs` (T=0, 1024 tok) | 6 × ~8 min ≈ 50 min |
| 6a | pomysł: `LLAMA_GPU_VERIFY` 0 vs 1 (mvs, ABBA). `[INFERENCE]` Na pamięci zunifikowanej kopia logitów jest tania, więc zysk może być ~0 | ≤ 10 min |
| 6b | pomysł: **T+C** (`LLAMA_SPEC_COUPLED=1`, binarka `metal-topka`) vs T, czat T=1, seeds 1–3. `GUMBEL_MAX` liczy się na CPU, więc patrzymy na ms/krok | ≤ 10 min |
| 6c | pomysł: MTP `--spec-draft-n-max` 2 vs 3 w T (czat) | ≤ 10 min |
| 6d | pomysł: lookup `LLAMA_SPEC_LOOKUP=0` vs 3 (mvs). Izoluje zysk ogona lookupu | ≤ 10 min |
| 7 | (opcja) `sudo sysctl iogpu.wired_limit_mb=12288` → **Qwen3.8-27B UD-IQ3_XXS**: llama-bench U/T + serwery U1 T (ctx 8192, KV q4_0) spec_sweep seeds 1,2 + mvs. Przy swapie (`memory_pressure` „critical”) przerwać | ≤ 20 min |
| 8 | (opcja) Qwen3.5-9B: U0 vs T (sam lookup) na mvs | ≤ 10 min |
| 9 | `rsync` wyników do `~/qwen-opt/cloud/results/m1pro-<data>/` | 2 min |

**Zasady:**
- Podczas testu laptop jest na zasilaczu, z otwartą klapą. Benchmarki puszczamy pod `caffeinate -dims`.
- W tle nic nie działa (zamknąć przeglądarkę i Docker).
- Termikę sprawdzamy przez `pmset -g therm` przed każdym ramieniem.
- Raportujemy t/s, ms/krok, tok/krok, pp512, tg128 i n_ctx w tabeli takiej jak w R27.

## 5. Co musi zrobić użytkownik (dostęp do M1 Pro)

1. **Remote Login:** System Settings → General → Sharing → **Remote Login: ON**. W „Allow access for” wybrać „Only these users” i swoje konto.
2. **Nasz klucz publiczny** (dedykowany, już wygenerowany na serwerze: `~/.ssh/mac_ed25519.pub`, fingerprint `SHA256:5mtnkaZM/FchtGb4sg28pU9w8d/z5M4XyfoYTnIOGSA`). W Terminalu na Macu:
   ```bash
   mkdir -p ~/.ssh && chmod 700 ~/.ssh
   echo 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIEjY1MOcSWDX6EUtfzr+t5peVrIhLnO46lqKspc1F/8A serwer-kernel->m1pro' >> ~/.ssh/authorized_keys
   chmod 600 ~/.ssh/authorized_keys
   ```
3. **Adres:**
   - Jeśli Mac jest w tej samej sieci co serwer (192.168.10.0/24), wystarczy podać wynik `ipconfig getifaddr en0` i nazwę użytkownika (`whoami`).
   - Poza domem potrzebny jest Tailscale na Macu (`brew install --cask tailscale` albo App Store) i podanie `tailscale ip -4`. Na serwerze Tailscale **nie jest zainstalowany**, a sudo wymaga hasła, więc instalację (`curl -fsSL https://tailscale.com/install.sh | sh` + `sudo tailscale up`) musi zrobić użytkownik.
4. **Narzędzia:**
   ```bash
   xcode-select --install
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   brew install cmake ninja
   ```
5. **(Opcja, dla kroku 7)** Pozwolić nam zmieniać limit GPU bez hasła:
   ```bash
   echo "$(whoami) ALL=(root) NOPASSWD: /usr/sbin/sysctl iogpu.wired_limit_mb=*" | sudo tee /etc/sudoers.d/iogpu
   ```
   Alternatywnie użytkownik sam wykona `sudo sysctl iogpu.wired_limit_mb=12288` przed testem.
6. Na czas testu: zasilacz, otwarta klapa, wyłączone usypianie (System Settings → Battery/Energy → „Prevent automatic sleeping when the display is off”) i zamknięte aplikacje.

## Do bazy wiedzy

- Vast.ai 2026-10-20: 5039 ofert, 100% NVIDIA, 0 Intel i 0 AMD. W vastai 1.8.3 nie działa operator `~`; poprawna jest składnia `gpu_name=Arc_A770` / `gpu_arch=intel`.
- Intel z rootem tylko jako dedyk miesięczny: GigaGPU Arc Pro B60 £129 (BMG-G21 = B580, 456 GB/s, 24 GB) i B70 £179. Godzinowego Arc nie ma nigdzie (Vast, TensorDock, Hetzner, OVH, Scaleway, Tiber).
- Scaleway ma **M4-M 32 GB za €0.29/h** (R05 znał tylko 16 GB). Minimum 24 h → €6.96. To najtańszy M4 ≥ 24 GB.
- AWS EC2 Mac (24 h min.): m4 24 GiB $1.23/h, m4pro 48 GiB $1.97, **m4max 128 GiB $6.25**, m3ultra 256 GiB $12.50. Stare: mac2 $0.65, m2 $0.878, m2pro $1.56, m1ultra $5.
- **Enverge:** Mac Studio M5 Ultra 256 GB, 1.2 TB/s, $2.50/h, co minutę, bez minimum, admin+sudo, darmowa kolejka FIFO. Ignoruje 24-godzinne minimum z licencji Apple. Najtańszy krótki test Apple Silicon.
- Darkbloom (Eigen Labs) to API prywatnej inferencji na cudzych Makach, bez SSH. Nie służy do benchmarków; to sygnał rynkowy.
- macOS: limit GPU `recommendedMaxWorkingSetSize` = 2/3 RAM do ~36 GB (16 GB → 10922.67 MiB). Podnosi go `sudo sysctl iogpu.wired_limit_mb=N`, reset po restarcie. llama.cpp traktuje ten limit jako całą pamięć urządzenia.
- Opy GPU verify (TOP_K, GET_ROWS, SUM_ROWS, ARGSORT) istnieją w Metal, Vulkan i SYCL. `GGML_OP_GUMBEL_MAX` (sprzężone próbkowanie) ma tylko CPU i CUDA.
- `cuda-topka2` + `coupled-topka` łączą się bez konfliktów (`git merge-tree` → `0215b3eb`).
- Qwen3.8-27B UD-IQ3_XXS ma głowicę MTP (`blk.64.nextn.*`, Q6_K). Qwen3.5-9B Q4_K_M od unsloth jej nie ma.

## Źródła

- [vast]: `vastai search offers 'rentable=any verified=any' --limit 20000 --raw` (2026-10-20 02:34 UTC; 5039 ofert, `gpu_arch` = nvidia ×5039)
- [gg-b60]: https://gigagpu.com/intel-arc-pro-b60-hosting/
- [gg-b70]: https://gigagpu.com/intel-arc-pro-b70-hosting/
- [zedup]: https://videocardz.com/newz/german-company-launches-intel-arc-pro-b60-rental-program
- [lam-b580]: https://localaimaster.com/blog/intel-arc-b580-local-ai (2026-08)
- [scw-mac]: https://www.scaleway.com/en/pricing/apple-silicon/
- [aws-mac]: https://aws.amazon.com/ec2/instance-types/mac/ (24 h min., per second; M4 Max 128 GB, M3 Ultra 256 GB)
- [vantage]: https://instances.vantage.sh/aws/ec2/mac-m4max.metal (i analogicznie mac2, mac2-m2, mac2-m2pro, mac2-m1ultra, mac-m4, mac-m4pro, mac-m3ultra)
- [env]: https://enverge.ai/
- [env-docs]: https://mac-studio.enverge.ai/docs/
- [env-blog]: https://mac-studio.enverge.ai/blog/how-to-rent-a-mac-studio-m5-ultra (2026-08-26)
- [mrm]: https://myremotemac.com/pricing
- [mrm-cmp]: https://myremotemac.com/best-mac-cloud-hosting (porównanie 9 dostawców, ceny z 2026-10-10; autor jest jednym z dostawców)
- [dbl]: https://darkbloom.dev/ (→ darkbloom.ai), https://github.com/Layr-Labs/d-inference
- [apple-sla]: https://www.apple.com/legal/sla/docs/macOSTahoe.pdf §3A; https://wiki.licenseware.io/catalog/rules/apple-macos-lease-minimum-24-consecutive-hours-with-exclusive-use
- [ll-26129]: https://github.com/ggml-org/llama.cpp/issues/26129
- [vram-cap]: https://github.com/ivanopcode/devnote-override-macos-metal-vram-cap
- Lokalnie: `~/qwen-opt/cloud/runs/nvfinal/inst/fin3060.sh` (ramiona Saluki), `boot.sh:27` (URL i sha256 Saluki), R27 (wyniki 3060/3090), `cloud/models.tsv` (rozmiary), `cloud/runs/3060/gguf_head.py` (nagłówki MTP).
