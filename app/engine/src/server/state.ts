// The app: a persistent, resumable phase machine (license → scan → recommend → download → baseline → optimize → ready).
// state.json holds the AppState plus what resuming needs (model path, min ctx).
import { existsSync, readFileSync, renameSync, writeFileSync, mkdirSync, unlinkSync } from 'node:fs';
import { basename, dirname, join } from 'node:path';
import type { AppState, BenchResult, Candidate, Hw, LicenseInfo, Option, Phase, Progress, Recommendation } from '../shared/types.ts';
import { recommend as catalogRecommend } from './catalog/index.ts';
import { benchEngine } from './bench.ts';
import { CancelledError, cachedHash, downloadFile, findLocalFile, hfUrl, type TransferProgress } from './download.ts';
import { baselineConfig, baselineEngineFor, engineById, ensureEngine, startServer, stopAllServers, type ResolvedEngine, type RunningServer } from './engine.ts';
import { scanHw } from './hw/index.ts';
import { storeLicenseKey, storedLicenseKey, verifyLicense } from './license.ts';
import { errMsg, log } from './log.ts';
import { optimize, planCandidates } from './optimize.ts';
import { ensureDirs, extraModelsDir, paths, uiPort } from './paths.ts';

export const VERSION = '0.1.0';
export const DEFAULT_MIN_CTX = 131072;

interface Persisted { app: AppState; modelPath: string | null; minCtx: number }

export type StateListener = (s: AppState) => void;
export type ProgressListener = (p: Progress) => void;

export class HttpError extends Error {
  constructor(readonly status: number, message: string) {
    super(message);
  }
}

function initialState(): AppState {
  return {
    phase: 'license', license: null, hw: null, recommendation: null, chosen: null, progress: null, baseline: null,
    candidates: [], best: null, ready: null, error: null, version: VERSION,
  };
}

const RUN_PHASES: Phase[] = ['download', 'baseline', 'optimize'];

export class App {
  state: AppState = initialState();
  private modelPath: string | null = null;
  private minCtx = DEFAULT_MIN_CTX;
  private stateListeners = new Set<StateListener>();
  private progressListeners = new Set<ProgressListener>();
  private abort: AbortController | null = null;
  private running: Promise<void> | null = null;
  server: RunningServer | null = null;
  /** The port the API actually listens on (serveApi sets it; the preferred one may be taken). */
  apiPort = uiPort();

  constructor() {
    ensureDirs();
    this.load();
  }

  // ---- persistence & events ----------------------------------------------------------------------------------------

  private load(): void {
    const file = paths().state;
    if (existsSync(file)) {
      try {
        const p = JSON.parse(readFileSync(file, 'utf8')) as Persisted;
        this.state = { ...initialState(), ...p.app, version: VERSION, progress: null, ready: null };
        this.modelPath = p.modelPath;
        this.minCtx = p.minCtx || DEFAULT_MIN_CTX;
      } catch (e) {
        log.warn(`state.json unreadable, starting fresh: ${errMsg(e)}`);
      }
    }
    // the license is re-verified on every start (expiry)
    const key = storedLicenseKey();
    this.state.license = key ? verifyLicense(key) : null;
    if (!this.state.license?.valid && this.state.phase !== 'license') {
      this.state.phase = 'license';
    }
  }

  private save(): void {
    const file = paths().state;
    mkdirSync(dirname(file), { recursive: true });
    const p: Persisted = { app: { ...this.state, progress: null }, modelPath: this.modelPath, minCtx: this.minCtx };
    const tmp = `${file}.tmp`;
    writeFileSync(tmp, JSON.stringify(p, null, 1));
    renameSync(tmp, file);
  }

  onState(fn: StateListener): () => void {
    this.stateListeners.add(fn);
    return () => this.stateListeners.delete(fn);
  }

  onProgress(fn: ProgressListener): () => void {
    this.progressListeners.add(fn);
    return () => this.progressListeners.delete(fn);
  }

  private changed(patch: Partial<AppState>): void {
    Object.assign(this.state, patch);
    this.save();
    for (const fn of this.stateListeners) fn(this.state);
  }

  private progress(phase: Phase, label: string, done: number, total: number, rate?: number, etaS?: number): void {
    const p: Progress = { phase, label, done, total };
    if (rate !== undefined) p.rate = rate;
    if (etaS !== undefined) p.etaS = etaS;
    this.state.progress = p;
    for (const fn of this.progressListeners) fn(p);
  }

  private transfer(phase: Phase, label: string): (p: TransferProgress) => void {
    return (p) => this.progress(phase, label, p.done, p.total, p.rate, p.etaS);
  }

  get licensed(): boolean {
    return this.state.license?.valid === true;
  }

  // ---- license, scan, recommend -------------------------------------------------------------------------------------

  async setLicense(key: string): Promise<LicenseInfo> {
    const info = verifyLicense(key);
    if (!info.valid) {
      log.warn(`license rejected: ${info.reason}`);
      return info;
    }
    storeLicenseKey(key);
    log.info(`license OK: plan ${info.plan}, valid until ${new Date((info.expiresAt ?? 0) * 1000).toISOString().slice(0, 10)}`);
    this.changed({ license: info });
    if (this.state.phase === 'license') {
      this.changed({ phase: 'scan' });
      await this.scan();
      await this.recommend(this.minCtx);
    }
    return info;
  }

  async scan(): Promise<Hw> {
    this.progress('scan', 'scan', 0, 1);
    const hw = await scanHw();
    const g = hw.gpus.map((x) => `${x.name} ${x.vramGiB} GiB [${x.backends.join('+')}]`).join(', ') || 'none (CPU)';
    log.info(`scan: ${hw.cpu.name} (${hw.cpu.cores}c/${hw.cpu.threads}t), RAM ${hw.ramGiB} GiB, GPU: ${g}, disk free ${hw.diskFreeGiB} GiB`);
    this.progress('scan', 'scan', 1, 1);
    const patch: Partial<AppState> = { hw };
    if (this.licensed && this.state.phase === 'scan') patch.phase = 'recommend';
    this.changed(patch);
    return hw;
  }

  async recommend(minCtx: number = this.minCtx): Promise<Recommendation> {
    const hw = this.state.hw ?? (await this.scan());
    this.minCtx = minCtx;
    const rec = await catalogRecommend(hw, minCtx);
    log.info(rec.pick
      ? `recommend: ${rec.pick.name} ${rec.pick.quant}, ctx ${rec.pick.ctx}, KV ${rec.pick.kvType}, ${rec.pick.backend}` +
        ` (${rec.alternatives.length} alternatives, ${rec.rejected.length} rejected)`
      : `recommend: nothing fits with ctx >= ${minCtx} (${rec.rejected.length} rejected)`);
    const patch: Partial<AppState> = { recommendation: rec };
    if (this.licensed && (this.state.phase === 'scan' || this.state.phase === 'recommend')) patch.phase = 'recommend';
    this.changed(patch);
    return rec;
  }

  // ---- the run: download → baseline → optimize → ready --------------------------------------------------------------

  findOption(optionId: string): Option | null {
    const r = this.state.recommendation;
    if (!r) return null;
    return [r.pick, ...r.alternatives].find((o): o is Option => o !== null && o.id === optionId) ?? null;
  }

  /** Starts (or restarts after an error) the pipeline for an option. Returns at once; progress via events. */
  async start(optionId: string): Promise<void> {
    if (!this.licensed) throw new HttpError(403, 'A valid subscription key is required to download, benchmark and optimise.');
    if (this.running) throw new HttpError(409, 'Already running.');
    const option = this.findOption(optionId) ?? (this.state.chosen?.id === optionId ? this.state.chosen : null);
    if (!option) throw new HttpError(404, `Unknown option ${optionId}; run the recommendation first.`);
    if (this.server) await this.stopEngine();
    const same = this.state.chosen?.id === option.id;
    this.changed({
      chosen: option, phase: 'download', error: null, ready: null, progress: null, // not the scan's 100% under "download"
      ...(same ? {} : { baseline: null, candidates: [], best: null }),
    });
    if (!same) this.modelPath = null;
    this.launch();
  }

  /** Resumes an interrupted download/baseline/optimize after a restart. */
  resume(): void {
    if (this.licensed && this.state.chosen && RUN_PHASES.includes(this.state.phase)) {
      log.info(`resuming phase ${this.state.phase} for ${this.state.chosen.name}`);
      this.launch();
    } else if (this.licensed && this.state.phase === 'ready' && this.state.best) {
      this.startEngine().catch((e: unknown) => log.error(`engine start failed: ${errMsg(e)}`));
    }
  }

  private launch(): void {
    this.abort = new AbortController();
    const signal = this.abort.signal;
    this.running = this.pipeline(signal)
      .catch((e: unknown) => {
        const phase = this.state.phase === 'error' ? (this.state.error?.phase ?? 'download') : this.state.phase;
        const msg = e instanceof CancelledError || signal.aborted ? 'Cancelled.' : errMsg(e);
        if (!signal.aborted) log.error(`${phase}: ${msg}`);
        this.state.progress = null;
        this.changed({ phase: 'error', error: { phase, message: msg } });
      })
      .finally(() => {
        this.running = null;
        this.abort = null;
      });
  }

  /** Resolves when the current run finishes (headless mode). */
  async settled(): Promise<void> {
    await this.running;
  }

  async cancel(): Promise<void> {
    if (!this.abort) return;
    log.warn('cancel requested');
    this.abort.abort();
    await this.running;
  }

  private async pipeline(signal: AbortSignal): Promise<void> {
    const option = this.state.chosen;
    const hw = this.state.hw;
    if (!option || !hw) throw new Error('no option chosen');
    const baseEntry = baselineEngineFor(hw.os, hw.arch, option.backend);
    if (!baseEntry) throw new Error(`No official llama.cpp build for ${hw.os} ${hw.arch} ${option.backend}.`);

    // download: engine + model
    if (this.state.phase === 'download') {
      await ensureEngine(baseEntry, { signal, onProgress: (label, p) => this.progress('download', label, p.done, p.total, p.rate, p.etaS) });
      this.modelPath = await this.fetchModel(option, signal);
      this.changed({ phase: 'baseline' });
    }
    const base = await ensureEngine(baseEntry, { signal });
    const modelPath = this.modelPath ?? (await this.fetchModel(option, signal));
    this.modelPath = modelPath;
    const baseCfg = baselineConfig(base, option, modelPath, hw);

    if (this.state.phase === 'baseline' || !this.state.baseline) {
      if (this.state.phase !== 'baseline') this.changed({ phase: 'baseline' });
      const baseline = await benchEngine(base, baseCfg, {
        label: `baseline ${base.entry.id}`, signal, progress: (label, done, total) => this.progress('baseline', label, done, total),
      });
      if (!baseline.ctxOk) throw new Error(`The context ${option.ctx} does not fit with the official engine.`);
      this.changed({ baseline, phase: 'optimize', candidates: planCandidates(hw, option, base).map((p) => p.candidate) });
    }
    const baseline = this.state.baseline as BenchResult;

    if (this.state.phase === 'optimize') {
      if (this.state.candidates.length === 0) this.changed({ candidates: planCandidates(hw, option, base).map((p) => p.candidate) });
      const res = await optimize({
        hw, option, modelPath, base, baseConfig: baseCfg, baseline, candidates: this.state.candidates, signal,
        update: (c: Candidate[]) => this.changed({ candidates: c }),
        progress: (label, done, total) => this.progress('optimize', label, done, total),
      });
      this.changed({ candidates: res.candidates, best: res.best });
      this.writeResults();
    }
    this.state.progress = null;
    await this.startEngine();
  }

  private async fetchModel(option: Option, signal: AbortSignal): Promise<string> {
    const name = basename(option.file.path);
    const dirs = [extraModelsDir(), paths().models].filter((d): d is string => d !== null);
    const local = findLocalFile(name, option.file.sizeBytes, dirs);
    if (local) {
      if (option.file.sha256) {
        const sha = await cachedHash(local, this.transfer('download', 'verify'), signal);
        if (sha === option.file.sha256.toLowerCase()) {
          log.info(`model: reusing ${local} (sha256 verified)`);
          this.progress('download', 'reuse:model', option.file.sizeBytes, option.file.sizeBytes);
          return local;
        }
        log.warn(`model: ${local} has a different sha256, downloading a fresh copy`);
        if (dirname(local) === paths().models) unlinkSync(local);
      } else {
        log.info(`model: reusing ${local} (same name and size; no published sha256)`);
        this.progress('download', 'reuse:model', option.file.sizeBytes, option.file.sizeBytes);
        return local;
      }
    }
    const dest = join(paths().models, name);
    const hw = this.state.hw;
    const needGiB = option.file.sizeBytes / 1024 ** 3;
    if (hw && hw.diskFreeGiB < needGiB + 1) {
      throw new Error(`Not enough disk space: the model needs ${needGiB.toFixed(1)} GiB, ${hw.diskFreeGiB} GiB free in ${paths().models}.`);
    }
    const url = hfUrl(option.file.repo, option.file.path);
    log.info(`will download ${name} (${needGiB.toFixed(1)} GiB) from ${url} → ${dest}`);
    await downloadFile({
      url, dest, sizeBytes: option.file.sizeBytes, signal, onProgress: this.transfer('download', 'model'),
      ...(option.file.sha256 ? { sha256: option.file.sha256 } : {}),
    });
    return dest;
  }

  private writeResults(): void {
    const s = this.state;
    const file = join(paths().results, `${new Date().toISOString().replace(/[:.]/g, '-')}.json`);
    writeFileSync(file, JSON.stringify({ hw: s.hw, chosen: s.chosen, baseline: s.baseline, candidates: s.candidates, best: s.best }, null, 1));
    log.info(`results saved to ${file}`);
  }

  // ---- the model server ---------------------------------------------------------------------------------------------

  async startEngine(): Promise<void> {
    if (this.server) return;
    const best = this.state.best;
    const option = this.state.chosen;
    if (!best || !option) throw new HttpError(409, 'Nothing to start yet: finish the optimisation first.');
    const entry = engineById(best.config.engineId);
    if (!entry) throw new Error(`unknown engine ${best.config.engineId}`);
    const engine: ResolvedEngine = await ensureEngine(entry);
    this.server = await startServer(engine, best.config, { label: 'ready' });
    this.changed({
      phase: 'ready', error: null, progress: null,
      ready: { endpoint: `http://127.0.0.1:${this.apiPort}/v1`, model: option.name, ctx: best.config.ctx },
    });
  }

  async stopEngine(): Promise<void> {
    const s = this.server;
    this.server = null;
    if (this.state.ready) this.changed({ ready: null });
    if (s) await s.stop();
  }

  async shutdown(): Promise<void> {
    this.abort?.abort();
    await this.running;
    await this.stopEngine();
    await stopAllServers();
  }
}
