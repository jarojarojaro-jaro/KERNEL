# Inference Stack (BerriAI) vs Enigma: a study

Paths: `IS/` = `~/kernel/zrodla/inference-stack` @ 812b448. `EN/` = `~/KERNEL/app/engine`. `ARCH` = `~/KERNEL/archiwum/zywa/2026-10-14T15-41-08-699Z_01a13b13-….md`.

## TL;DR
1. Inference Stack (IS) does not make inference faster. It is a small control plane, about 1.2k lines of Python, that wires mature parts together: vLLM, the llm-d router (Envoy plus an endpoint picker), LiteLLM, Prometheus, Grafana and Lens. Most of the engineering effort went into lifecycle, safety, upgrades and cost limits, not into the model.
2. On speed and fit, Enigma is far ahead: measured per-card recipes, at least 131k context with a KV memory model, AMD support, our own engines, and a fair baseline → optimized benchmark. IS sizes a model as `weights×1.25+2 GB`, uses 4096 context by default and supports NVIDIA only.
3. On operations, IS is far ahead: crash restart, metrics and dashboards, a simulation mode that needs no GPU, a checksummed installer with upgrade backup and rollback, redacted diagnostics, a Helm/K8s path, and cost guards with tests for every failure path.
4. Why our attempt went worse (hypotheses with evidence):
   - We built the "speed" half and treated the "operations" half as design documents that were never implemented.
   - Effort went to the landing page (97 commits, 12 juror rounds) rather than the app (28 commits).
   - We tested on our own lab machine, not on our users' hardware.
   - Our AMD engine, our main differentiator, is never shipped to users.
5. Top adoptions, cheap first:
   - `--metrics` on llama-server plus Prometheus metrics at our proxy;
   - a watchdog that restarts a crashed server;
   - a simulator mode for CI and for no-GPU testing;
   - a checksummed one-line installer with upgrade backup;
   - redacted diagnostics.

   KV/prefix-aware routing and LiteLLM matter only for a later multi-slot or multi-user Enigma, but they are core infrastructure knowledge.

## 1. Architecture of Inference Stack (file:line)

**Request path.** App → LiteLLM :4000 (`IS/compose/docker-compose.yaml:29-50`) → Envoy :8081 (`IS/compose/router/envoy.yaml:9-13`) → ext_proc gRPC to the llm-d EPP at `epp:9002` (`envoy.yaml:40-55`, `FULL_DUPLEX_STREAMED` bodies). The EPP picks a replica and returns the header `x-gateway-destination-endpoint`. Envoy's `ORIGINAL_DST` cluster then routes to that pod IP (`envoy.yaml:73-84`) → vLLM :8000.

**Launcher** (FastAPI, `IS/launcher/app.py`, 607 lines; plain HTML/JS UI).

*Auth*
- The admin password is the generated LiteLLM master key (`settings.py:13-14`). It is checked for length ≥ 20 and against placeholder values (`settings.py:4-8`).
- Sessions use an HMAC-signed cookie with a 12 h lifetime (`app.py:35-48`, `150-158`).
- Basic auth is accepted as a fallback (`app.py:119-127`).
- A same-origin check guards every mutation (`app.py:134-137`).
- Validation errors never echo the submitted input (`app.py:108-111`).

*Hugging Face search* (`catalog.py:87-107`)
- Uses the HF `api/models` endpoint sorted by downloads with `expand[]=safetensors`.
- Pins three Qwen starter models (`catalog.py:104-106`).
- Model details read `config.json` to check gated access without downloading weights (`catalog.py:119-132`).
- The HF token is checked with `whoami`. It is saved with mode 0600, or as a K8s Secret (`catalog.py:44-66`).

*"GPU requirements" check*
- Estimate = `ceil(weights_bytes×1.25/GiB + 2)`, from safetensors dtype counts (`catalog.py:74-84`). The file itself says "estimates are never a runtime guarantee" (`catalog.py:1`).
- Suggested GPU count = `ceil(estimated / max GPU memory)`. Suggested context = `min(4096, max_position_embeddings)` (`app.py:321-325`).
- Validation (`app.py:328-373`): free GPU count; weights must not exceed memory × GPUs per replica; on K8s, each replica must fit on one node.
- **No KV-cache or context memory model.** Context is capped at 131072 (`app.py:55`).

*GPU inventory*
- Compose: runs `nvidia-smi` inside a throwaway container with all GPUs attached (`compose_backend.py:139-170`).
- K8s: node `allocatable nvidia.com/gpu` minus GPUs requested by pods, and the `nvidia.com/gpu.memory` label (`kubernetes_backend.py:66-103`).
- **NVIDIA only.**

*Deployment lifecycle*
- One global operation lock, plus deployment state persisted atomically to `/state/deployment.json` (`app.py:30-33`, `78-83`).
- After a launcher restart mid-deploy, the user sees "restarted, check status" instead of a silent hang (`app.py:86-95`).
- Compose steps (`app.py:395-417`): pull image → deregister the old model → start N `vllm-i` containers (`compose_backend.py:93-105`, `restart_policy unless-stopped`) → wait for `/health`, failing fast if a container exits (`compose_backend.py:127-136`) → write `endpoints.yaml` plus Prometheus file-SD targets (`compose_backend.py:40-49`) → register in LiteLLM (`litellm_client.py:25-33`) → verify the registration.
- K8s: `helm upgrade --install` of the model chart (`kubernetes_backend.py:199-201`). If RBAC does not allow deploying, the launcher prints the `helm` command for the user to run instead (`kubernetes_backend.py:181-186`, `app.py:436-439`). Discovery is from labels and annotations (`kubernetes_backend.py:133-168`).
- Compose runs **one model at a time**; replacing it needs explicit confirmation (`app.py:440-443`).

*Simulation mode*
- `simulate=true` swaps vLLM for `ghcr.io/llm-d/llm-d-inference-sim:v1.2.0` (`settings.py:30`, `compose_backend.py:108-112`, chart `model-server.yaml:62-64`), which returns canned text.
- Every GPU check is skipped (`app.py:330-331`), but the whole path still runs: LiteLLM → Envoy → EPP → "replica" → Prometheus → Grafana.

*Diagnostics*
- Logs are bounded (`tail 150`, 16 kB) and redacted: secrets, any line mentioning password/key/token, `sk-`/`hf_` strings, URLs and IPs (`diagnostics.py:12-20`).
- The panel also shows the exact `kubectl`/`docker` commands to run (`diagnostics.py:29-37`).

**Router (llm-d EPP v1.0.0).**
- Configuration (`compose/router/epp-config.yaml:1-36`):
  - discovery from a file the launcher writes (`file-discovery`, `watchFile`);
  - metrics scraped from vLLM (`metrics-data-source`, `core-metrics-extractor`);
  - profile `default` with weights **queue-scorer 2, kv-cache-utilization-scorer 2, prefix-cache-scorer 3, no-hit-lru-scorer 2**.
- Flow control (queueing when saturated) is turned on with `--feature-gates=flowControl=true` (`docker-compose.yaml:78`, chart `model/values.yaml:33-34`). The docs say the default queue wait limit is 60 s and that stale metrics pause dispatch (`docs/setup.md:156`).
- The UI exposes only the prefix-cache and queue weights, each 0–5 (`app.py:67-70`, `548-599`). Saving rewrites the YAML and **restarts the EPP** (`compose_backend.py:180-185`); on K8s it does a Helm upgrade (`kubernetes_backend.py:213-217`).
- [External llm-d knowledge, not in this repo]:
  - Each enabled scorer returns a score in [0,1] per endpoint; the picker takes the maximum of Σ weight × score.
  - *prefix-cache-scorer* (approximate mode) hashes the prompt into blocks and keeps an LRU index of which endpoint recently served which block hashes. Its score is the matched-prefix fraction.
  - *kv-cache-utilization* = 1 − `vllm:kv_cache_usage_perc`.
  - *queue* is based on `vllm:num_requests_waiting`.
  - *no-hit-lru* sends cold requests (no prefix hit) to the least-recently-used endpoint, so cache contents spread out.
- Fairness:
  - A LiteLLM pre-call hook adds the header `x-llm-d-inference-fairness-id` = team or user id (`charts/inference-stack/files/llmd_headers.py:7-11`).
  - Flow control can use it to share capacity between teams.

**LiteLLM configuration generation.** There is no generated YAML: models live in Postgres (`store_model_in_db: true`, `compose/litellm/config.yaml:1-10`).
- Compose: the launcher calls `/model/new` with `hosted_vllm/<id>` and `api_base = router/v1` (`litellm_client.py:25-33`), always deleting the old entry first (idempotent).
- K8s: a Helm hook Job runs post-install/upgrade/delete with inline Python and the same calls (`charts/model/templates/register-job.yaml:1-56`).
- Callbacks: `prometheus` plus the fairness header (`config.yaml:7-10`).

**Metrics.**
- Prometheus scrapes LiteLLM `/metrics/`, the EPP on :9090, and vLLM through file-SD. The launcher writes the file-SD file (`compose/prometheus/prometheus.yml:1-15`); K8s uses pod annotations (`model-server.yaml:31-33`).
- Dashboards (`charts/inference-stack/files/dashboards/`; Compose and Helm share one set, `configmaps.yaml:1-9`):
  - **overview** (`overview.json:17-213`): ready servers (`llm_d_epp_ready_endpoints`), waiting (`vllm:num_requests_waiting`), TTFT p95 (`vllm:time_to_first_token_seconds_bucket`), tok/s (`vllm:generation_tokens_total`), requests per team (`litellm_proxy_total_requests_metric_total`), requests per fairness id (`llm_d_epp_request_total`), requests per replica (`vllm:request_success_total`), KV usage per replica (`vllm:kv_cache_usage_perc`). These trace one request across the three layers.
  - upstream **LiteLLM** (latency histograms, failed requests, remaining limits);
  - **llm-d Router** (flow-control queue size/bytes/durations, pool saturation, request/response sizes, input/output tokens);
  - **llm-d vLLM** (TTFT, ITL, e2e, queue/prefill/decode time, prompt/generation histograms);
  - **KV performance** (`prefix_cache_hits/queries`, KV usage).

**Lens traces.** Standalone Lens 0.4.0 runs with ClickHouse, 14-day retention and hardened containers (read-only, `cap_drop ALL`, mem/pids limits) (`docker-compose.yaml:120-164`). It is an OTLP sink for **agent** traces and logs (Claude Code/Codex/OpenCode) on `/v1/traces` and `/v1/logs` with a bearer tracing key. LiteLLM does **not** forward request traces to it in this release (`docs/setup.md:84-97`). So "traces" means agent sessions, not spans from the serving path.

**install.sh flow** (207 lines).
- Mode `docker|kubernetes`; prerequisite checks with human-readable messages (`install.sh:7-22`).
- Downloads the bundle and SHA256SUMS and verifies them; refuses an incomplete archive (`install.sh:36-55`). [Note: the checksum comes from the same release origin, so it proves integrity, not authenticity; there is no signature.]
- Refuses to install into a foreign directory (`install.sh:100-111`).
- Version-aware upgrade: moves the old install to `<dir>.v<old>`, carries `.env` over and rewrites only the launcher image line, restores on failure (`install.sh:113-141`).
- Creates `.env` with `umask 077` + `set -C` (no-clobber) and generated secrets, and appends any new secrets on upgrade (`install.sh:151-157`).
- Migrates Grafana data from older installs, safe to retry (`install.sh:57-98`). Then `docker compose up -d --no-build --wait`.
- K8s: refuses a release that needs recovery (`install.sh:162-166`); `helm install` with generated Postgres passwords; port-forwards to a LiteLLM *Deployment* pod, explicitly avoiding the migration Job (`install.sh:183-200`).

**Helm.**
- `charts/inference-stack` (dependencies `litellm-helm` 1.110.2, `prometheus` 27.3.0, `grafana` 8.8.2, `lens` 0.4.0; `Chart.yaml:7-21`) installs launcher + LiteLLM + Prometheus + Grafana + Lens. A template refuses weak DB passwords (`templates/validate.yaml`).
- `charts/model` contains one model:
  - a vLLM Deployment with the `Recreate` strategy (reuses its GPUs; `model-server.yaml:20-22`);
  - readiness on `/health`;
  - node affinity on `nvidia.com/gpu.memory > minGpuMemoryMiB` (`model-server.yaml:39-48`);
  - an embedded `llm-d-router-standalone` (EPP + Envoy) per model (`charts/model/Chart.yaml:7-10`, `values.yaml:19-50`);
  - the register/unregister Jobs.
- The launcher's RBAC is limited to its namespace; `manageModels=false` switches it to printing commands (`values.yaml:4-7`, `docs/setup.md:119-136`).

**AWS path** (`aws/`, about 1.4k lines + CloudFormation).
- The CFN stack (`aws/stack.yaml`) creates a VPC, a t3.xlarge launcher with k3s (checksummed download, `bootstrap.py:101-128`), CloudFront in front with no public ingress (`test_aws.py:229`), Secrets Manager, and four stack-owned GPU ASGs (`stack.yaml:432-516`).
- `capacity.py` is a Unix-socket service only the launcher can reach (`capacity.py:2`, `app.py:195-205`). It checks quota and re-checks the price before launch; a changed price is refused (`capacity.py:55-64`).
- It creates an EventBridge **stop schedule before any billable capacity**: GPUs are deleted after `StopAfterHours`, default 4 (`stack.yaml:27-31`, `642-658`; `capacity.py:140-170`; `test_capacity.py:42-58`).
- Removal cordons the node and refuses to remove one that still runs models (`test_capacity.py:83-107`).

**Tests** (99 test functions). These cover:
- installer: checksum failure, corrupt archive, upgrade backup conflict, preserved credentials, Grafana migration retries (`tests/test_install.py`, 24);
- AWS capacity state machine and cost safety (`test_capacity.py`, 16);
- the AWS template and bootstrap (`test_aws.py`, 17);
- the GPU catalogue and prices (`test_gpu_catalogue.py`, 4);
- launcher auth and locking (`test_launcher.py`);
- journeys (`test_journey.py`), e.g. "diagnostics never echo credentials", "expensive allocation cannot rent a GPU";
- Helm upgrade paths on a real kind cluster (`test_helm_upgrades.py`, CI `checks.yaml:34-48`);
- Playwright UI tests (`test_model_settings.cjs`).

**I ran 61 of them locally** in a /tmp copy (`nice 15`): install 24, capacity 16, gpu_catalogue 4, aws 17. All passed, 22 s. The rest need fastapi, helm or kind, which I did not install (no network installs).

**Solid engineering.**
- Lifecycle state that survives restarts.
- An idempotent register/verify loop.
- Fail-fast on exited containers.
- Redacted diagnostics.
- Generated secrets, no weak passwords anywhere.
- Upgrade with backup and rollback, tested.
- Graceful degradation when RBAC denies deployment: the launcher prints the commands instead.
- One discovery file feeds both the router and Prometheus.
- Cost-safety ordering on AWS (schedule before spend).
- Tests named after failure modes, not features.

**Preview fluff / weak spots.**
- The memory estimate ignores KV and context.
- Context defaults to 4096.
- NVIDIA only.
- Compose runs one model at a time, so llm-d routing on one box only matters with several GPUs.
- No performance numbers anywhere: no startup benchmark, only dashboards.
- `litellm:main-stable` is a floating tag (`docker-compose.yaml:30`), unlike the other pinned images.
- The launcher mounts `docker.sock`, which is root-equivalent (`docker-compose.yaml:62`; acknowledged in `docs/setup.md:21`).
- Grafana allows anonymous viewers (`docker-compose.yaml:111-112`).
- The metrics endpoint has no auth (`config.yaml:7`).
- Changing a router weight restarts the EPP.
- "Traces" are agent OTLP only.
- Single-flight global lock.

## 2. Comparison table

| Layer | Inference Stack | Enigma (ours) | Who is better |
|---|---|---|---|
| Install | `curl … install.sh docker` with checksum, generated secrets, `compose up --wait`, upgrade backup and rollback (`install.sh:36-55,113-159`); Helm; AWS CFN | Single Bun binary (`bun build --compile`, 3 targets; `EN/README.md:320-328`), test build shared on LAN 2026-10-24 (`ARCH:38921`). No installer script, no update channel, `VERSION='0.1.0'` (`EN/src/server/state.ts:19`) | IS for operations; ours is simpler for a desktop user |
| HW detection | `nvidia-smi` probe / K8s allocatable; NVIDIA only (`compose_backend.py:139-170`) | Linux/Windows/macOS, NVIDIA/AMD/Intel/Apple, iGPU vs dGPU, RAM type/MT/s/channels → bandwidth (`EN/CONTRACT.md:74-83`; `hw/*`) | **Ours**, by far |
| Model choice | Open HF search; `weights×1.25+2 GB`; ctx 4096 default (`catalog.py:74-84`, `app.py:321-325`) | Curated catalog (13 models) with a memory model for weights + KV + compute + MTP draft, ≥ 131072 ctx, measured `VERIFIED` plans per card, speed ranking (`CONTRACT.md:109-168`) | **Ours** for fit and speed; IS for openness (any HF model) |
| Engine management | vLLM container; Docker `restart_policy unless-stopped` (`compose_backend.py:103`); K8s Deployment | Pinned upstream llama.cpp + our engines with sha256 (`README.md:353-386`); **`enigma-rocm-gfx1100` is `distribution: "local"`** (`EN/data/engines.json:272`), so AMD users get only upstream | Ours technically; but the AMD engine does not ship |
| Benchmark | None | Fair A/B: same tokens, noise threshold, winner confirmation, deep 32k (`CONTRACT.md:206-247`); XTX 35.0 → 97.8 t/s (`wiki/testy/enigma-uczciwy-benchmark.md`) | **Ours** (IS has no equivalent at all) |
| Observability | Prometheus + 5 Grafana dashboards spanning gateway/router/engine; Lens | Log files (`~/.enigma/logs`), SSE progress; llama-server started **without `--metrics`** (`EN/src/server/engine.ts:567-579`), although llama.cpp exports `llamacpp:*` counters including `prompt_tokens_cached_total` and `spec_decode_num_accepted_tokens_total` (`~/praca/llama-duo/tools/server/server-task.cpp:1525-1609`) | **IS** |
| API | LiteLLM: virtual keys, teams, budgets, one API over many models, Chat UI | `/v1/*` proxy with a private key, Host/Origin check (`EN/src/server/api.ts:105-124`); one model | IS for multi-tenant use; ours is fine for one desktop user |
| Multi-model | K8s: one Helm release per model; Compose: one at a time | One model, `-np 1` (`engine.ts:571`); llama-server router mode (`--models-dir`, `--models-max` LRU) known but unused (`product/research/03-silniki-i-stack.md:114`) | IS on K8s; tie on one box |
| Update | Installer upgrade with backup; Helm `--reset-then-reuse-values` tested on kind | None built. Designed: Tauri updater, A/B engine slots, regression guard (`app/design/APP-ARCHITECTURE.md:89,169,506`) | **IS** |
| Failure handling | Fail-fast on exited container, restart policy, deployment state survives launcher restart, redacted logs plus copyable commands, cancel during GPU start | Resumable phase machine (`CONTRACT.md:44-54`), graceful stop (`engine.ts:614-623`), exit detected **only while loading** (`engine.ts:698-701`). After `ready` nothing watches the process: phase stays `ready` and clients get 502 (`api.ts:106,114-117`). Designed but not built: supervisor and watchdog, backoff restart (`APP-ARCHITECTURE.md:41,85`) | **IS** |
| No-GPU testing | First-class simulator through the real path | `ENIGMA_DEV_CPU=1`: a real CPU run on a real model, ~8 min (`README.md:281-301`) | IS for CI speed; ours is more honest |
| Tests | 99, named after failure modes, kind cluster in CI | `bun test` 208/208 per audit (`wiki/research/audyt-gemini-2026-11-19.md`); hardware fixtures missed APUs until the owner hit it (`wiki/lekcje/lekcja-enigma-apu-jako-karta.md`) | IS on breadth of failure modes; ours on numeric fixtures |

## 3. Why our own attempt went worse (hypotheses; evidence from our files)

H1 to H6 are my inference. The evidence cited for each is observed.

**H1. We built the "make it fast" half and left the "keep it running" half as a design document.**
- APP-ARCHITECTURE specified:
  - a Rust daemon with a supervisor and watchdog;
  - `/metrics`;
  - crash restart with backoff and fallback to Vulkan/CPU;
  - an updater with A/B slots and a regression guard

  (`app/design/APP-ARCHITECTURE.md:23,41,84-89,169,488,506`).
- What shipped has none of them:
  - no post-ready exit handler (only `engine.ts:619`, inside `gracefulStop`, waits on `proc.exited`);
  - no `--metrics` flag (`engine.ts:569-575`);
  - no update mechanism (`state.ts:19`).
- IS put most of its 39 commits into exactly these parts.

**H2. Effort went to the shop window, not the product.** In `git log -- app/landing` vs `app/engine` I counted 97 vs 28 commits. `REPORT.md:192-225` records 12 juror rounds chasing a design score of 8/8/8. Our own verdict said "We don't start with the GUI" (`wiki/produkt/werdykt.md:91`). The owner was steering landing copy and design in many messages (`ARCH:14537` through `ARCH:34718`) before he asked for the app at all (`ARCH:38436`, 2026-10-24).

**H3. The owner asked for "the app first, so we can test the whole process on different cards; optimisation later" (`ARCH:38614`). Optimisation took over anyway.**
- The same day, the agent ran GPU tests without his approval (`ARCH:38596`).
- The planner contradicted our own production setup: 196608 vs 204800 measured on the XTX (`ARCH:38573`).
- Since 2026-11-20 sessions have been dominated by the "Enigma Turbo" and "Duo" engine loops (`ARCH:52665` onward).

**H4. We tested on our lab, not on our users.** The first real user PC (Windows APU) was misclassified as a GPU with unified memory, and the speed estimate was wrong (`wiki/lekcje/lekcja-enigma-apu-jako-karta.md`; owner: "PODSTAWOWY BŁĄD", `ARCH:39081`). The default model picks were rejected by the owner (`wiki/lekcje/lekcja-pick-z-kalkulatora.md`). IS instead gives every user a simulator and tests each failure path. Our test matrix mirrored our own hardware.

**H5. Our differentiator does not ship.**
- The AMD-optimized engine is `local` only (`engines.json:272`; `README.md:361-363`: "Adres dystrybucji jeszcze nie istnieje"). An AMD user gets upstream llama.cpp only.
- The NVIDIA engines were published 2026-11-07 (`CONTRACT.md:183-190`).
- So the product promise ("we accelerate, AMD natively") is not reachable on AMD.

**H6. Building a whole engine from scratch repeated the mistake at a larger scale.**
- Enigma Turbo's README promised CUDA/HIP. It actually ran CPU-only at 0.7 t/s and answered with gibberish; its "ALL PASS" tests ran on a synthetic model (`wiki/research/enigma-turbo-gemini-2026-11-20.md`).
- The IS team did the opposite: they wrote **no** engine, router or gateway. They composed proven parts and spent their effort on the glue, the guarantees and the tests.

**H7 (weaker; not checked against a real end-to-end run).** The app is one 5-phase pipeline that ends at `ready`; after that the app goes quiet. A product lives *after* `ready`:
- Is it still up?
- How fast is it right now?
- Did the update regress anything?
- What do I do when it breaks?

IS is designed around exactly these questions (status page, dashboards, logs panel, retry/remove). Ours is designed around reaching `ready`.

## 4. Lessons and adoptions, ranked (value ÷ effort)

| # | Adopt into Enigma | Value | Effort | Where |
|---|---|---|---|---|
| 1 | Start llama-server with `--metrics`. Proxy `/metrics` through our API and add per-request TTFT/tok/s/prefix-cached counters at our `/v1` proxy (we already see every request). Show live t/s and draft acceptance in the UI, so the benchmark is no longer the only number | high | ½ day | `engine.ts:569-575`, `api.ts:105-124`; metric names in `server-task.cpp:1525-1609` |
| 2 | Post-ready watchdog: on `proc.exited`, set `engine.state=crashed`, restart with backoff (3 in 5 min), then fall back to the baseline config, then to upstream, and emit an SSE alert (the design already exists) | high | 1 day | `engine.ts:662-716`, `APP-ARCHITECTURE.md:85` |
| 3 | Simulator mode: a fake llama-server (stub `/health`, `/completion`, `/v1/chat/completions`, `/slots`, `/metrics`, with a canned speed profile) so the full phase machine, UI and proxy run in CI and on machines without a GPU. Pattern: `llm-d-inference-sim` | high | 1–2 days | new `EN/test/sim/`; `ENIGMA_SIMULATE=1` |
| 4 | Diagnostics panel: last N log lines, redacted (keys, paths, IPs), plus the exact command lines and the config JSON. "Copy for support" | med-high | ½ day | port `diagnostics.py:12-37` to `log.ts` |
| 5 | One-line installer and update: checksummed and **signed** (we already have Ed25519 keys for licenses); keep the previous version as a backup; refuse unknown directories; re-run safely | high | 2 days | pattern `install.sh:36-55,100-141` |
| 6 | Ship the AMD engine (`distribution: download` for `enigma-rocm-gfx1100`), otherwise the AMD differentiator does not exist for users | very high | 1–2 days of packaging (RUNPATH, sha256, like CUDA) | `engines.json:272`; precedent `CONTRACT.md:200-204` |
| 7 | Hardware test matrix = the distribution of real customers (APU, iGPU laptop, 8/12/16 GB, Windows); each class gets a fixture from a real scan before release, plus the simulator for flows | high | ongoing | `lekcja-enigma-apu-jako-karta.md` |
| 8 | Tests named after failure modes ("restart mid-download keeps the .part", "crash after ready recovers", "update rollback keeps models") | med | ongoing | style of `IS/tests/test_journey.py` |
| 9 | Multi-model on one box via llama-server router mode (`--models-dir`, `--models-max`): later, when users ask for coder + chat | med | 2–3 days | `03-silniki-i-stack.md:114` |
| 10 | Grafana dashboard JSON for our own server (topka, production :8080): TTFT p95, t/s, draft acceptance, cached prompt tokens. Useful for the lab now, even before the product | med | ½ day | dashboards dir pattern |
| 11 | LiteLLM in front of Enigma only for a "Team/Business" edition (keys, budgets, many users) | low now | — | `produkt-biznes-edycje.md` |
| 12 | Helm/K8s and AWS paths | none for consumer Enigma | — | skip |

## Do bazy wiedzy

- **Inference Stack = composition, not an engine.** vLLM + llm-d (Envoy ext_proc + EPP) + LiteLLM + Prometheus/Grafana + Lens, glued by about 1.2k lines of FastAPI. Its value is in lifecycle, safety, upgrades and cost guards (`IS/launcher/app.py`, `install.sh`, `aws/capacity.py`).
- **llm-d routing.**
  - Envoy sends each request to an Endpoint Picker over ext_proc. The picker scores each replica with weighted scorers; here queue 2, KV-utilization 2, prefix-cache 3, no-hit-LRU 2 (`compose/router/epp-config.yaml:17-27`).
  - It returns `x-gateway-destination-endpoint`, and Envoy's `ORIGINAL_DST` cluster routes there (`envoy.yaml:73-84`).
  - Flow control queues requests at the router when replicas are saturated.
  - The fairness id comes from the LiteLLM team via a header (`llmd_headers.py`).
- **KV/prefix-cache-aware routing.** Send a request to the replica that already holds its prompt prefix in KV, but not if that replica is saturated: a weighted trade-off between cache hits and load. No-hit LRU spreads cold prefixes out. The single-box version of the same problem is choosing a slot. Our measured E4 case: a foreign request plus `f_keep < 0.25` evicted the agent cache, and `LLAMA_SERVER_CACHE_SHARE_MIN=1024` brought Qwen from 8.0 s to 1.6 s (`STAN-PRAC.md:47`). With `-np > 1`, llama-server's slot-prompt-similarity selection is the per-process equivalent.
- **LiteLLM as a gateway.** One OpenAI API over many backends (`hosted_vllm/…` + `api_base`), with virtual keys, teams, budgets and a Prometheus callback. Models are stored in the DB and registered through the `/model/new` and `/model/delete` API (`litellm_client.py`). Pre-call hooks can inject routing headers.
- **Observability standard for LLM serving.**
  - Per request: TTFT, inter-token latency, e2e latency, queue time, prefill and decode time.
  - Per engine: requests running/waiting, KV usage %, prefix-cache hits/queries, prompt/generation token counters.
  - Per gateway: requests and failures per key or team.
  - Names: `vllm:*`, `llm_d_epp_*`, `litellm_*`; llama.cpp uses `llamacpp:*`, including spec-decode drafts/accepted and cached prompt tokens (`llama-duo/tools/server/server-task.cpp:1525-1609`).
- **Simulator-first testing.** A fake engine with the same API lets the whole product path (UI → gateway → router → metrics) be tested in CI without a GPU. It does not validate speed or quality, and IS says so plainly.
- **Lesson for us.** IS ships the operational half (watchdog, metrics, install and upgrade, diagnostics, failure-mode tests) and borrows the engine. We built a strong engine half (fit, measured recipes, a fair benchmark) and left the operational half in a design document. The fix is to adopt items 1–6 above, not to write another engine.
