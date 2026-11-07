# Enigma app — kontrakt (backend ⇄ UI ⇄ katalog)

Cel (użytkownik, 2026-10-24): ktoś pobiera Enigmę → podpina subskrypcję → aplikacja analizuje sprzęt → wybiera najlepszy
model z największym kontekstem (**min. 131 072**) → pobiera model i silnik → pokazuje benchmark startowy (prefill, decode,
kontekst) → uruchamia optymalizację → gotowe (lokalny endpoint OpenAI-compatible). Design prosty, spójny z enigmalabz.com.

Stos: **Bun** (TypeScript, backend `Bun.serve`) + **Svelte 5 + Vite** (UI, statyczny build osadzony w binarce) →
`bun build --compile` na linux-x64, windows-x64, darwin-arm64. Bez Rust/Tauri na tym etapie (brak toolchainu; to boring
choice, UI w przeglądarce na 127.0.0.1). Bun: `~/KERNEL/app/.tools/bun` (1.4.3).

## Układ
```
app/engine/
  package.json  tsconfig.json  vite.config.ts  CONTRACT.md  README.md
  data/catalog.json          # modele × kwanty (katalog; agent Catalog)
  data/engines.json          # silniki: upstream llama.cpp (baseline) + enigma (zoptymalizowany) per platforma
  src/shared/types.ts        # typy z tego dokumentu (jedno źródło dla backendu i UI)
  src/server/main.ts         # CLI: `enigma` (UI + otwarcie przeglądarki), `enigma run --headless …`, `enigma license …`
  src/server/{api,state,hw/*,catalog/*,license,download,engine,bench,optimize,paths,log}.ts
  src/ui/…                   # Svelte 5 SPA → dist/ui (osadzone w binarce)
  tools/license-issue.ts     # wystawianie kluczy (klucz prywatny poza repo: ~/.secrets/enigma-license-ed25519.pem)
  test/…                     # bun test
```

## Katalog domowy i nadpisania
- Dane: Linux/macOS `~/.enigma`, Windows `%LOCALAPPDATA%\Enigma`: `config.json`, `state.json`, `models/`, `engines/`,
  `logs/`, `results/`, `bench-workload.json` (żądania benchmarku wyrenderowane na baseline). `ENIGMA_HOME` nadpisuje.
- `ENIGMA_MODELS_DIR` — dodatkowy katalog z gotowymi GGUF (plik o tej samej nazwie i rozmiarze = bez pobierania;
  sha256 sprawdzane, jeśli katalog je zna). Na naszym serwerze: `~/models` (rekurencyjnie, płytko 2 poziomy).
- `ENIGMA_ENGINE_DIR_<ID>` — lokalny katalog silnika (np. `ENIGMA_ENGINE_DIR_ENIGMA_ROCM=~/llama-topka`,
  `ENIGMA_ENGINE_DIR_UPSTREAM_ROCM=~/llama-base`) zamiast pobierania.
- `ENIGMA_PORT` (UI/API, domyślnie **11525**; 11500 zajmuje omp). Zajęty → backend próbuje 20 kolejnych portów i wypisuje
  faktyczny URL; UI bierze port z `location` (jest serwowane przez ten sam serwer), a snippety z `ready.endpoint`.
  `ENIGMA_NO_BROWSER=1`.
- Pobieranie przez sieć tylko w aplikacji użytkownika; w naszym labie testy NIE pobierają modeli (nadpisania wyżej).

## Licencja / subskrypcja
Klucz `ENIGMA-…` = base64url(JSON payload) + "." + base64url(podpis Ed25519). Payload:
`{v:1, sub:"<id konta/email-hash>", plan:"pro"|"team"|"trial", exp:<unix s>, iat, features:["optimize","models"]}`.
Weryfikacja offline kluczem publicznym wbudowanym w aplikację (`src/server/license.ts`). Wystawianie:
`bun tools/license-issue.ts --sub X --plan pro --days 30` (klucz prywatny w `~/.secrets`, mode 600, nigdy w repo).
Bez ważnego klucza: etapy skanu i rekomendacji działają; pobieranie/benchmark/optymalizacja zablokowane z komunikatem.

## Fazy (maszyna stanów, trwała w `state.json`, wznawialna)
`license → scan → recommend → download → baseline → optimize → ready` (+ `error` z `phase`, `message`, `retry`).
- Przejścia: ważny klucz (`/api/license`) → backend sam: `scan` (skan) → `recommend` (rekomendacja, minCtx 131072) →
  czeka na `/api/start`. `/api/scan` i `/api/recommend` są idempotentne i działają też bez klucza (wypełniają `hw`/
  `recommendation`, `phase` zostaje `license`); `/api/start` bez ważnej licencji → 403.
- Retry po `error`: ponowne `POST /api/start {optionId: chosen.id}` (pobrane pliki są reużywane). Po restarcie aplikacji
  przerwana faza `download`/`baseline`/`optimize` wznawia się sama. `/api/cancel` kończy bieżącą fazę jako
  `phase='error'`, `error.message === 'Cancelled.'` (stały string; UI pokazuje „Przerwano” + „Wznów”).
- `ready != null` ⇔ serwer modelu działa (`phase='ready'`); po `/api/engine/stop` `ready=null`, `/v1/*` → 503.
- `Progress.label` (klucze, UI tłumaczy): `engine` | `model` | `verify` | `extract` | `reuse:model` | `reuse:engine` |
  `bench:start` | `bench:prefill` | `bench:decode` | `bench:deep`. Błędy HTTP: `{error: string}` + kod 4xx/5xx.

## API (127.0.0.1:ENIGMA_PORT; sprawdzanie `Host`/`Origin` = tylko 127.0.0.1/localhost)
| Metoda | Ścieżka | Ciało → wynik |
|---|---|---|
| GET | `/api/state` | → `AppState` |
| GET | `/api/events` | SSE: `state` (pełny `AppState` przy każdej zmianie), `log` `{t, level, msg}`, `progress` (pełny `Progress`, z `label`) |
| POST | `/api/license` | `{key}` → `LicenseInfo` |
| POST | `/api/scan` | → `Hw` |
| POST | `/api/recommend` | `{minCtx?: number}` → `Recommendation` |
| POST | `/api/start` | `{optionId}` → rozpoczyna download → baseline → optimize (automatycznie) |
| POST | `/api/cancel` | przerywa bieżącą fazę (łagodnie) |
| POST | `/api/engine/{start,stop}` | serwer modelu w konfiguracji `ready.best` |
| ANY | `/v1/*` | proxy do działającego llama-server (OpenAI-compatible) gdy `phase=ready` |
| GET | `/` | UI |

## Typy (src/shared/types.ts — dokładnie te nazwy)
```ts
type Phase = 'license'|'scan'|'recommend'|'download'|'baseline'|'optimize'|'ready'|'error';
interface LicenseInfo { valid: boolean; plan?: string; sub?: string; expiresAt?: number; reason?: string }
type GpuKind = 'discrete'|'integrated'|'apple';
interface Gpu { vendor:'nvidia'|'amd'|'intel'|'apple'; name:string; kind:GpuKind;
  vramGiB:number /* discrete: VRAM; integrated: część RAM wydzielona przez BIOS; apple: budżet Metal */;
  sharedGiB?:number /* integrated: RAM, który GPU może zmapować (Windows ½ RAM, Linux GTT) */;
  arch?:string /* gfx1100, sm_86, … */; driver?:string; backends:Backend[] }
type Backend = 'cuda'|'rocm'|'vulkan'|'metal'|'cpu';
interface RamInfo { totalGiB:number; type?:string /* DDR4, DDR5, LPDDR5 */; speedMTs?:number; channels?:number;
  modules?:number; bandwidthGBs:number /* MT/s × 8 B × kanały 64-bit */; source:'detected'|'default' }
interface Hw { os:'linux'|'windows'|'macos'; arch:'x64'|'arm64'; cpu:{name:string; cores:number; threads:number};
  ramGiB:number; memory:RamInfo; gpus:Gpu[]; diskFreeGiB:number; scannedAt:number }
interface MemPlan { weightsGiB:number; kvGiB:number; computeGiB:number; overheadGiB:number; totalGiB:number;
  budgetGiB:number; freeGiB:number }
interface Option { id:string; modelId:string; name:string; family:string; params:string; quant:string;
  file:{repo:string; path:string; sizeBytes:number; sha256?:string}; ctx:number; ctxMax:number; kvType:'q4_0'|'q8_0'|'f16';
  ub:number; backend:Backend; gpuIndex:number|null; mem:MemPlan; features:string[] /* mtp, tools, reasoning, vision */;
  score:number; why:string[];
  needsEngine?:string /* id z engines.json: oficjalny llama.cpp nie uruchamia pliku (PTQ1_0); baseline i kandydaci na nim */;
  mtpEngine?:string /* id z engines.json, którego profil MTP zwymiarował plan (features ma 'mtp'); kandydat `enigma` */ }
interface Recommendation { minCtx:number; pick:Option|null; alternatives:Option[];
  rejected:{modelId:string; quant:string; reason:string}[] }
interface Progress { phase:Phase; label:string; done:number; total:number; rate?:number; etaS?:number }
interface BenchResult { engine:{id:string; version:string; backend:Backend}; config:EngineConfig;
  prefill:{tokens:number; tps:number; ttftS:number}; decode:{tokens:number; tps:number /* T=1 */; greedyTps:number /* T=0 */};
  deep?:{ctxTokens:number; prefillTps:number; decodeTps:number}; ctxOk:boolean; outputMd5:string; at:number }
interface EngineConfig { engineId:string; modelPath:string; ctx:number; kvType:string; ub:number; b:number;
  flashAttn:boolean; threads?:number; spec?:'none'|'mtp'|'lookup'; extraArgs:string[]; env:Record<string,string> }
interface Candidate { id:string; label:{pl:string;en:string}; desc:{pl:string;en:string};
  status:'pending'|'running'|'kept'|'rejected'|'failed'; result?:BenchResult; decodePct?:number; prefillPct?:number;
  sameOutput?:boolean; reason?:string }
interface AppState { phase:Phase; license:LicenseInfo|null; hw:Hw|null; recommendation:Recommendation|null;
  chosen:Option|null; progress:Progress|null; baseline:BenchResult|null; candidates:Candidate[];
  best:BenchResult|null; ready:{endpoint:string; model:string; ctx:number}|null;
  error:{phase:Phase; message:string}|null; version:string }
```

## Katalog i rekomendacja (`src/server/catalog/index.ts`)
- `recommend(hw, minCtx = 131072): Recommendation` (synchronicznie); `replan(option, hw, {ub?, ctx?, kvType?, spec?})` i
  `planFor(hw, modelId, quant, {ctx, kvType, ub, spec, backend, gpuIndex})` → `{mem: MemPlan, fits}` (te same zapasy).
- Pamięć = wagi + KV + compute + narzut, dla pełnego kontekstu (prompt = ctx), z rezerwą na kontekst MTP, gdy
  `features` zawiera `mtp`. `fits` = zostaje zapas: Linux 100 MiB (zmierzona produkcja XTX 204800), Windows 512 MiB,
  macOS 0 ponad budżet pamięci zunifikowanej; CUDA +200 MiB (pula K/V naszego silnika rośnie z promptem, zmierzona do
  55.6k; pokrywa też zawyżoną sumę CUDA z nvidia-smi i niedoszacowany narzut kart 4090/5080).
  Upstream na CUDA (kampania 67): plan bez MTP nie liczy bloku nextn w wagach (335 MiB na Qwen3.8-27B), z MTP liczy
  KV draftu w f16, stan rekurencyjny × (n_max + 1) i bufor compute draftu przy `--spec-draft-n-ubatch 64`; brak
  wzrostu z promptem ponad plain. Plan MTP = kandydat `mtp` (`MTP_N_MAX_DEFAULT`, `MTP_DRAFT_UB` w `memory.ts`).
  Kalibracja: `test/catalog.measured.json`.
- Nasze silniki CUDA (`enigma-cuda-lean`, `enigma-cuda-prism`, `enigma-cuda-fork`, `data/engines.json`) wchodzą do planu tylko, gdy są
  dostępne (`distribution: download` albo ustawione `ENIGMA_ENGINE_DIR_<envKey>`; `engineAvailable` w `engine.ts`).
  Plan MTP pliku, dla którego dostępny silnik ma profil z `mtp` (`{nMax, ubd, draftKv?}`), jest liczony pod ten profil
  (`Option.mtpEngine`, why `mtp_engine:<id>/<n>`): stan × (n + 1), bufor draftu przy ubd, KV draftu w typie efektywnym —
  `-ctkd` profilu przy cesze `mtp-lean-reserve` (wtedy też maska draftu ctx × 2 B), typ `-ctk` przy cesze
  `mtp-draft-kv-ctk` (prism, dopasowane do pomiarów 4070), inaczej f16; bez `ubd` w profilu draft liczy się przy `-ub`;
  cecha `mtp-fork-draft` (nasz fork): stan × 1,686 (snapshoty) zamiast × (n + 1) + bufory słownika draftu
  (`mtpExtraMiB`); nigdy powyżej `maxCtx` profilu (zmierzony pełny fill). Silnik z `planOnlyMeasured` (fork) wchodzi do
  planu tylko na karcie z wpisem `VERIFIED` dla niego (4090 i 3090 UD-Q4_K_XL 262144 ub 256, 5090 UD-Q6_K 262144
  ub 512, 5060 Ti GSQ 196608), a kandydat `enigma`
  uruchamia go tylko dla planu, który go wybrał. Kilka dostępnych silników z profilem MTP dla pliku: wygrywa pierwszy w
  `engines.json` (lean przed fork). Kandydat `mtp` (upstream n 3, KV draftu f16) liczy wtedy własne dopasowanie (`replan(…, {mtpEngine:
  null})`), inaczej `mtp_no_memory`. Model z `engine` w katalogu (`bonsai2-27b-mtp` → `enigma-cuda-prism`) jest
  oferowany tylko tam, gdzie ten silnik jest zbudowany dla karty i dostępny (inaczej rejected `needs_engine:<id>`), i
  tylko jako plan profilu MTP tego silnika (zmierzona konfiguracja; plan plain bez pomiaru nie jest oferowany — 3080
  10 GB: MTP się nie mieści → `ctx_below_min`, zostaje Qwen3.5-9B Q6_K). `Option.needsEngine` = baseline na nim (why
  `engine_required:<id>`, `speed_measured:<t/s>/<id>`), `minUpstreamBuild` go nie dotyczy. Przy remisie wyniku
  (plain ≥ 60 t/s) wygrywa plan MTP.
- Konfiguracje zmierzone end-to-end na danej karcie (`VERIFIED` w `catalog/index.ts`; upstream CUDA albo `engine` =
  nasz silnik, który ten plan uruchamia) zastępują szacunek dla tej karty × modelu × kwantu × silnika (mogą sięgać wyżej
  o ≤ 700 MiB ponad zapas i ograniczają kontekst z góry), z ich ub, KV q4_0 i trybem spekulacji; drugi tryb nie jest tam
  oferowany (np. upstream MTP na 16 GB: OOM przy pierwszym długim prompcie; MTP z `enigma-cuda-lean` to inny silnik).
  Lean (kampania 67c, MTP n 2, ubd 64, KV draftu q4_0, ub 256): 4060 Ti i 5060 Ti 229376, 5080 217088 (229376 padło).
- Model z `defaultPick: false` (Gemma 4 12B, odrzucona przez użytkownika) nigdy nie jest `pick`, zostaje w alternatywach.
- Bez karty z własną pamięcią (wszystkie `gpus[].kind === 'integrated'` albo brak GPU) maszyna jest „RAM-bound”:
  urządzenia = grafika zintegrowana × backend (Vulkan; ROCm tylko gfx1150/gfx1151) z budżetem min(`vramGiB + sharedGiB`,
  `vramGiB` + RAM − zapas) oraz zawsze CPU z budżetem RAM − zapas (zapas: Windows ≥ 8 GB lub 25% RAM, Linux/macOS ≥ 6 GB
  lub 20%); ten sam model × kwant woli grafikę zintegrowaną. Z kartą dyskretną (lub Apple) iGPU i CPU nie są planowane.
  Prędkość: `ramSpeed` w `score.ts` — η × `memory.bandwidthGBs` / (bajty/token + KV przy 4096 tokenach), η z pomiarów
  modelu na naszym CPU (`ramMeasured` w katalogu, ±15/10%) albo dense 0,6–0,75 / MoE 0,4–0,7; prefill = pomiar/rdzeń ×
  rdzenie (inaczej 75 GFLOP/s/rdzeń), dolna granica × 0,6 (długi prompt). Decode < 8 t/s (środek zakresu, także na
  kartach) → `too_slow_on_this_hw:<t/s>`.
- Ranking (`Option.score`): jakość × współczynnik kwantu × użyteczność prędkości, potem prędkość zmierzona na tej klasie
  sprzętu (punkt `measured` dla tej karty; na RAM-bound `ramMeasured` modelu) wygrywa z szacowaną, chyba że szacowana ma
  wynik wyższy o > 20% (szacunek / 1,2); na RAM-bound plan z < 3% wolnego budżetu × 0,8 (`tight_memory`).
- `why[]` / `rejected[].reason` = kody `kod` albo `kod:wartość`: why — `quality_best`, `speed_measured:<t/s>[/<engineId>]`,
  `speed_estimated:<t/s>`, `mtp_head`, `mtp_no_memory` (plik ma głowicę MTP, ale kontekst draftu się nie mieści; opcja
  bez 'mtp' w features), `engine_required:<engineId>`, `mtp_engine:<engineId>/<n>`, `moe_fast`, `ctx_model_max`, `ctx_memory_limit`, `kv_q8_0|kv_q4_0|kv_f16`,
  `ub512_for_ctx` (ub 512: osiąga min. kontekst albo daje ≥ 8% więcej; wolniejszy prefill, decode bez zmian),
  `unified_memory` (Apple), `windows_reserve`, `license_conditional:<id licencji z catalog.licenses>`, `tight_memory`; RAM-bound — `no_dgpu_ram`, `igpu_backend:<backend>`,
  `cpu_igpu_pool:<GiB>` (liczy CPU, bo model nie mieści się w pamięci grafiki zintegrowanej), `cpu_only`,
  `speed_ram_moe:<aktywne B>/<lo>-<hi>` | `speed_ram_dense:<parametry B>/<lo>-<hi>` (t/s), `prefill_ram:<lo>-<hi>/<minCtx>`,
  `ram_reserve:<zapas GiB>/<budżet GiB>`, `gpu_faster:<lo>-<hi>` (tylko gdy katalog ma pomiar tego modelu na karcie
  16–24 GB); rejected — `ctx_max_below_min:<ctxMax>`, `weights_too_big:<GiB>/<budżet GiB>`, `ctx_below_min:<max ctx>`,
  `engine_too_old:b<N>` (przypięty upstream w `data/engines.json` starszy niż build obsługujący model),
  `needs_engine:<engineId>` (plik uruchamia tylko nasz silnik, niedostępny dla tej karty albo nieopublikowany),
  `too_slow_on_this_hw:<t/s>`. Przy kilku urządzeniach powód pochodzi z tego, które ma najwięcej pamięci.
- `data/catalog.json` odświeża `ENIGMA_MODELS_DIR=~/models bun src/server/catalog/refresh.ts` (HF tree API + nagłówki
  lokalnych GGUF / `config.json`; nic nie pobiera poza JSON i nagłówkami).

## Zasady wyników (reguła użytkownika)
Każdy wynik pokazywany jako **baseline → teraz → przyrost %**. Baseline = upstream llama.cpp (oficjalne wydanie) z
konfiguracją dobraną przez nas tylko pod mieszczenie (ctx/KV/ub). Liczby tylko zmierzone na maszynie użytkownika.
Wyjątek: plik, którego oficjalny llama.cpp nie uruchamia (`Option.needsEngine`, PTQ1_0 → fork PrismML): baseline =
ten silnik w tej samej konfiguracji „tylko pod mieszczenie” (bez spekulacji), bo upstream daje na nim śmieci.

## Fork na RTX 3090 — rozstrzygnięte (kampania 67c)
Zmierzone na dostarczanym silniku (`enigma-cuda-fork`, build przenośny): Qwen3.8-27B **UD-Q4_K_XL** 262144 / ub 256,
KVQ=1 — load 23590, pełny fill 261504 tokenów, szczyt 23706 MiB, 79.97 t/s T=1 (pick bez forka: XL 245760, pin z MTP
n 3: 61.49 → +30%). Ten sam kwant, więc bez kompromisu jakości: wpis `VERIFIED` jak 4090/5090, z dostępnym forkiem
plan 3090 = XL 262144 / ub 256 na forku. Bez silników picki bez zmian. Model oceny się nie zmienia (bez liczenia
zmierzonych prędkości MTP w wyniku); UD-Q4_K_M (78.97 t/s na forku) nie wchodzi do katalogu.

## Silniki Enigma CUDA — opublikowane (2026-11-07)
`enigma-cuda-lean`, `enigma-cuda-prism` i `enigma-cuda-fork` mają w `data/engines.json` `distribution: "download"`:
archiwa leżą na wydaniu GitHub **`enigma-engines-cuda-2026-11-07`** repozytorium `jarojarojaro-jaro/KERNEL`
(https://github.com/jarojarojaro-jaro/KERNEL/releases/tag/enigma-engines-cuda-2026-11-07, plik `SHA256SUMS`), a runtime
CUDA to oficjalny `cudart-llama-b12110-bin-ubuntu-cuda-12.8-x64.tar.gz` z ggml-org/llama.cpp. `ensureEngine` pobiera,
sprawdza sha256, rozpakowuje, kładzie `draft_vocab_qwen38.txt` do `<silnik>/share` i składa cudart obok
`libggml-cuda.so`; planner używa ich domyślnie (fork tylko na kartach ze zmierzoną konfiguracją: 3090, 4090, 5090).
`ENIGMA_ENGINE_DIR_ENIGMA_CUDA_*` dalej nadpisuje pobieranie lokalnym katalogiem.

| Archiwum | Bajty | sha256 |
|---|---:|---|
| `llama-b12110lean-bin-ubuntu-cuda-12.8-x64.tar.gz` (upstream b12110 + `qwen-opt/patches/nv67-lean-reserve`) | 132282409 | `1ea7532e9edd17216eab559494dfb653258fce9281d2d67a961666349cbe9798` |
| `llama-prism-bin-ubuntu-cuda-12.8-x64.tar.gz` (PrismML prism-b12128-d7b2896) | 227217132 | `4f6927ec8e2e6df311cee311584f5d0e8a6527caa942665a7a88474f100c23d9` |
| `llama-kvqleana-bin-ubuntu-cuda-12.8-x64.tar.gz` (fork, bez AVX2; używany przez Enigmę) | 130083180 | `b63ec233f60a35a8407a5ad583fbfa14ab705470219c08849656c6e256b71df3` |
| `llama-kvqlean-bin-ubuntu-cuda-12.8-x64.tar.gz` (fork, AVX2) | 130105374 | `4fc0126af3150d022fbda3e9b051ed315f0f7ca69cc4a6966a1111e673f4f00e` |
| `draft_vocab_qwen38.txt` | 1627130 | `ef23007d66b0aebb8baf65ef5440faa3daaeb42faf2d07b64be4ac5017ea3a9a` |

Fork przed publikacją dostał `RUNPATH=$ORIGIN` (`patchelf --set-rpath`, 8 plików): zmierzony build wskazywał na katalog
budowania (`/home/…/build-cuda/bin`) i u użytkownika nie znalazłby własnych bibliotek. Kod i flagi bez zmian, stąd nowe
sha256 (stare: kvqleana `3eb4adb1…`, kvqlean `50467018…`). Smoke 2026-11-07: instalacja forka przez `ensureEngine` z
lokalnymi archiwami — wszystkie biblioteki rozwiązane obok `llama-server` (cudart, cublas, ggml), brak tylko
`libcuda.so.1` sterownika (maszyna bez NVIDIA). **Tylko Linux x64:** na Windows i macOS Enigma dalej używa upstreamu.

## Benchmark (jeden protokół dla baseline i kandydatów)
0. Obciążenie renderowane **raz, na serwerze baseline** (jego szablon czatu przez `/apply-template` i jego tokenizer
   przez `/tokenize`, `add_special` + `parse_special` jak `/completion` dla tekstu), z `reasoning_effort` serwowanym
   przez produkt (`--reasoning-effort` z profilu silnika Enigma dla tej opcji, jako `chat_template_kwargs`; bez profilu
   — domyślny szablonu). Każde ramię dostaje do `/completion` **te same id tokenów**; serwer kandydata niczego nie
   renderuje ani nie tokenizuje (flagi szablonu kandydata, np. `LLAMA_CHAT_NATIVE`, nie zmieniają obciążenia).
   Zapis w `bench-workload.json` (klucz: model, silnik baseline, ctx, effort, rozmiary); inny klucz przy wznowieniu →
   baseline mierzony od nowa.
1. Start llama-server (`127.0.0.1`, losowy port, `--api-key` losowy), `-c ctx` — start = kontekst się mieści (`ctxOk`).
   Rozgrzewka 32/4 tokeny; przed **każdym** mierzonym żądaniem krótkie żądanie budzące (8 tokenów, 1 token): karta z
   `power/control=auto` (BACO) usypia się po kilku sekundach bezczynności.
2. Prefill: prompt ~4096 tokenów (stały korpus w repo, surowy tekst), `cache_prompt:false`, mierzone `timings.prompt_per_second`.
3. Decode: 256 tokenów, bez `ignore_eos`, `timings.predicted_per_second`, na zadaniach czatu (oryginalne opowiadanie PL
   i EN), dwa ramiona z osobnymi zadaniami: greedy (`temperature 0`, `seed 1`; md5 tekstów = `outputMd5`,
   `decode.greedyTps`) i próbkowane jak czat (`temperature 1`, `top_k 40`, `top_p 0.95`, `min_p 0.05`, `seed` = 1 +
   powtórzenie; `decode.tps`, decyduje). Nie ciągnięcie korpusu: model go kopiuje, a lookup/MTP akceptują wtedy prawie
   wszystko (zawyżony decode).
4. Deep: korpus ~32k tokenów jako dokument w wiadomości + pytanie wymagające własnej odpowiedzi, 128 tokenów decode
   (greedy); pomijany, gdy prompt nie mieści się w kontekście ramienia.
5. Powtórzenia 2×, mediana; każde powtórzenie i ramię z innymi zadaniami (cache n-gramów serwera przeżywa żądania —
   identyczne żądanie odtworzyłoby poprzednią odpowiedź). Zatrzymanie serwera: czekaj na wolne `/slots`, **jeden**
   SIGTERM, 45 s, potem SIGKILL.

## Optymalizacja (kandydaci, każdy mierzony tym samym benchmarkiem; zostaje najlepszy decode; prefill może spaść ≤ 5%, albo ≤ 15% gdy decode rośnie ≥ 20%; kandydat zmieniający tekst musi dać ≥ 3% decode)
- Reguły `decide()`: zysk decode > próg szumu (2%); deep prefill jak prefill, deep decode ≤ 5% straty (gdy oba mają
  deep). Potwierdzenie: zwycięzca mierzony drugi raz obok ponownego pomiaru baseline; szum = |baseline₂/baseline − 1|,
  próg = max(2 × szum, 2%), pozostałe reguły bez zmian. Potwierdzony: `kept`, `result`/`decodePct`/`prefillPct`/
  `sameOutput` z pary potwierdzającej (wobec baseline₂). Niepotwierdzony: `not_confirmed:<pct>` i potwierdzany jest
  następny najlepszy (ten sam baseline₂).
- silnik `enigma-*` dla platformy, jeśli jest (przy kilku dla karty: ten z profilem dla pliku, dostępny najpierw; na AMD
  gfx1100: topka z flagami jak `~/qwen-opt/run-topka.sh` — PM4, lookup, MTP dla Qwen3.8, coupled, host-gap; wierne
  odwzorowanie `run-llm.sh`; na CUDA: lean/prism z flagami MTP z `profile.mtp`, `--jinja`);
- `-ub/-b` (512/1024/2048) w granicach pamięci; MTP (jeśli model ma głowicę i silnik obsługuje: `--spec-type draft-mtp
  --spec-draft-n-max 3 --spec-draft-n-ubatch 64`); lookup n-gram.
- `sameOutput` = md5 decode greedy == baseline (spekulacja może zmienić bity → pokazujemy jasno, nie ukrywamy).
- `Candidate.id`: `enigma` | `ub-512` | `ub-1024` | `ub-2048` (bez bieżącego ub) | `mtp` | `lookup`.
- `Candidate.reason` = kod (`kod` albo `kod:wartość`; UI tłumaczy, nieznany pokazuje surowo):
  `no_enigma_engine:<arch|vendor>-<backend>-<os>-<arch>` (np. `cpu-linux-x64`, `sm_86-cuda-windows-x64`) |
  `enigma_no_profile:<modelId>` | `enigma_not_published:<engineId>` | `ub_no_fit:<ub>` | `no_mtp_head` | `mtp_no_memory` | `engine_no_mtp` |
  `engine_no_lookup` | `ctx_not_fit` | `prefill_loss:<pct>` | `deep_prefill_loss:<pct>` | `deep_decode_loss:<pct>` |
  `decode_not_faster:<pct>` | `within_noise:<pct>` | `gain_too_small:<pct>` | `not_confirmed:<pct>` | `slower_than:<candidateId>` |
  `oom` | `start_failed:<pierwsza linia>` | `failed:<pierwsza linia>`. Kandydat `kept` nie ma `reason`.
