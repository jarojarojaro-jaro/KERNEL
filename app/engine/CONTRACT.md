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
  `logs/`, `results/`. `ENIGMA_HOME` nadpisuje.
- `ENIGMA_MODELS_DIR` — dodatkowy katalog z gotowymi GGUF (plik o tej samej nazwie i rozmiarze = bez pobierania;
  sha256 sprawdzane, jeśli katalog je zna). Na naszym serwerze: `~/models` (rekurencyjnie, płytko 2 poziomy).
- `ENIGMA_ENGINE_DIR_<ID>` — lokalny katalog silnika (np. `ENIGMA_ENGINE_DIR_ENIGMA_ROCM=~/llama-topka`,
  `ENIGMA_ENGINE_DIR_UPSTREAM_ROCM=~/llama-base`) zamiast pobierania.
- `ENIGMA_PORT` (UI/API, domyślnie 11500), `ENIGMA_NO_BROWSER=1`.
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
  przerwana faza `download`/`baseline`/`optimize` wznawia się sama.
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
interface Gpu { vendor:'nvidia'|'amd'|'intel'|'apple'; name:string; vramGiB:number; unified:boolean;
  arch?:string /* gfx1100, sm_86, … */; driver?:string; backends:Backend[] }
type Backend = 'cuda'|'rocm'|'vulkan'|'metal'|'cpu';
interface Hw { os:'linux'|'windows'|'macos'; arch:'x64'|'arm64'; cpu:{name:string; cores:number; threads:number};
  ramGiB:number; gpus:Gpu[]; diskFreeGiB:number; scannedAt:number }
interface MemPlan { weightsGiB:number; kvGiB:number; computeGiB:number; overheadGiB:number; totalGiB:number;
  budgetGiB:number; freeGiB:number }
interface Option { id:string; modelId:string; name:string; family:string; params:string; quant:string;
  file:{repo:string; path:string; sizeBytes:number; sha256?:string}; ctx:number; ctxMax:number; kvType:'q4_0'|'q8_0'|'f16';
  ub:number; backend:Backend; gpuIndex:number|null; mem:MemPlan; features:string[] /* mtp, tools, reasoning, vision */;
  score:number; why:string[] }
interface Recommendation { minCtx:number; pick:Option|null; alternatives:Option[];
  rejected:{modelId:string; quant:string; reason:string}[] }
interface Progress { phase:Phase; label:string; done:number; total:number; rate?:number; etaS?:number }
interface BenchResult { engine:{id:string; version:string; backend:Backend}; config:EngineConfig;
  prefill:{tokens:number; tps:number; ttftS:number}; decode:{tokens:number; tps:number};
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
  `features` zawiera `mtp`. `fits` = zostaje ≥ 300 MiB (Windows ≥ 1 GiB). Kalibracja: `test/catalog.measured.json`.
- `why[]` / `rejected[].reason` = kody `kod` albo `kod:wartość`: why — `quality_best`, `speed_measured:<t/s>`,
  `speed_estimated:<t/s>`, `mtp_head`, `moe_fast`, `ctx_model_max`, `ctx_memory_limit`, `kv_q8_0|kv_q4_0|kv_f16`,
  `ub_512`, `unified_memory`, `windows_reserve`, `cpu_only`, `license_conditional`; rejected — `ctx_max_below_min:<ctxMax>`,
  `weights_too_big:<GiB>/<budżet GiB>`, `ctx_below_min:<max ctx>`, `engine_unsupported`, `not_cpu_tier`.
- `data/catalog.json` odświeża `ENIGMA_MODELS_DIR=~/models bun src/server/catalog/refresh.ts` (HF tree API + nagłówki
  lokalnych GGUF / `config.json`; nic nie pobiera poza JSON i nagłówkami).

## Zasady wyników (reguła użytkownika)
Każdy wynik pokazywany jako **baseline → teraz → przyrost %**. Baseline = upstream llama.cpp (oficjalne wydanie) z
konfiguracją dobraną przez nas tylko pod mieszczenie (ctx/KV/ub). Liczby tylko zmierzone na maszynie użytkownika.

## Benchmark (jeden protokół dla baseline i kandydatów)
1. Start llama-server (`127.0.0.1`, losowy port, `--api-key` losowy), `-c ctx` — start = kontekst się mieści (`ctxOk`).
2. Prefill: prompt ~4096 tokenów (stały korpus w repo), `cache_prompt:false`, mierzone `timings.prompt_per_second`.
3. Decode: 256 tokenów, `temperature 0`, `seed 1`, `timings.predicted_per_second`; md5 tekstu = `outputMd5`.
4. Deep: prompt ~32k tokenów + 128 tokenów decode (pokazuje zachowanie przy długim kontekście).
5. Powtórzenia 2×, mediana. Zatrzymanie serwera: czekaj na wolne `/slots`, **jeden** SIGTERM, 45 s, potem SIGKILL.

## Optymalizacja (kandydaci, każdy mierzony tym samym benchmarkiem; zostaje najlepszy decode bez straty prefill > 5%)
- silnik `enigma-*` dla platformy, jeśli jest (na AMD gfx1100: topka z flagami jak `~/qwen-opt/run-topka.sh` — PM4,
  lookup, MTP dla Qwen3.8, coupled, host-gap; wierne odwzorowanie `run-llm.sh`);
- `-ub/-b` (512/1024/2048) w granicach pamięci; MTP (jeśli model ma głowicę i silnik obsługuje); lookup n-gram.
- `sameOutput` = md5 decode == baseline (spekulacja może zmienić bity → pokazujemy jasno, nie ukrywamy).
