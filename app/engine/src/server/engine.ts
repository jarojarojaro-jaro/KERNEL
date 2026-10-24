// Engines: catalogue (data/engines.json), install (download + extract or a local ENIGMA_ENGINE_DIR_<KEY>),
// configs (upstream baseline, enigma profiles), and the llama-server process (spawn, health, graceful stop).
import { chmodSync, closeSync, existsSync, mkdirSync, openSync, readdirSync, readFileSync, renameSync, rmSync, statSync, writeFileSync, writeSync } from 'node:fs';
import { availableParallelism, homedir } from 'node:os';
import { basename, delimiter, dirname, join } from 'node:path';
import { randomBytes } from 'node:crypto';
import { inflateRawSync } from 'node:zlib';
import type { Subprocess } from 'bun';
import type { Backend, EngineConfig, Hw, Option } from '../shared/types.ts';
import enginesData from '../../data/engines.json' with { type: 'json' };
import { cachedHash, downloadFile, type TransferProgress } from './download.ts';
import { errMsg, log } from './log.ts';
import { expandHome, extraModelsDir, paths } from './paths.ts';

// ---- catalogue ----------------------------------------------------------------------------------------------------

export interface EngineAsset { name: string; url: string; sizeBytes: number; sha256?: string }

/** Model-specific settings of an enigma engine (args/env mirror the production launch scripts). */
export interface EngineProfile {
  id: string;
  /** regex tested (case-insensitive) against `modelId` and the model file name */
  match: string;
  spec: 'none' | 'mtp' | 'lookup';
  b?: number;
  ub?: number;
  /** files the profile needs; resolved into placeholders (e.g. {draftVocab}) */
  needs: string[];
  env: Record<string, string>;
  args: string[];
}

export interface EngineEntry {
  id: string;
  kind: 'upstream' | 'enigma';
  label: string;
  version: string;
  os: Hw['os'];
  arch: Hw['arch'];
  backend: Backend;
  /** ENIGMA_ENGINE_DIR_<envKey> points at a local build instead of downloading */
  envKey: string;
  distribution: 'download' | 'local';
  features: string[];
  assets: EngineAsset[];
  gpuArchs?: string[];
  note?: string;
  profiles?: EngineProfile[];
}

export interface EnginesFile {
  upstream: { repo: string; release: string; tag: string; publishedAt: string; pinnedAt: string };
  engines: EngineEntry[];
}

export const ENGINES = enginesData as EnginesFile;

export function engineById(id: string): EngineEntry | undefined {
  return ENGINES.engines.find((e) => e.id === id);
}

export function baselineEngineFor(os: Hw['os'], arch: Hw['arch'], backend: Backend): EngineEntry | undefined {
  return ENGINES.engines.find((e) => e.kind === 'upstream' && e.os === os && e.arch === arch && e.backend === backend);
}

/** `code` is the machine-readable reason (Candidate.reason, translated by the UI); `reason` is the log text. */
export interface EnigmaChoice { entry: EngineEntry | null; code: string; reason: string }

/** The optimised engine for this machine and option, or a plain reason why there is none. */
export function enigmaEngineFor(hw: Hw, option: Option): EnigmaChoice {
  const gpu = option.gpuIndex === null ? undefined : hw.gpus[option.gpuIndex];
  const forPlatform = ENGINES.engines.filter((e) => e.kind === 'enigma' && e.os === hw.os && e.arch === hw.arch);
  const fits = forPlatform.filter((e) => e.backend === option.backend && (!e.gpuArchs || (gpu?.arch !== undefined && e.gpuArchs.includes(gpu.arch))));
  const entry = fits[0];
  if (!entry) {
    const platform = `${gpu ? `${gpu.arch ?? gpu.vendor}-${option.backend}` : 'cpu'}-${hw.os}-${hw.arch}`;
    const what = gpu ? `${gpu.name}${gpu.arch ? ` (${gpu.arch})` : ''}, ${option.backend}` : `CPU (${hw.os} ${hw.arch})`;
    return { entry: null, code: `no_enigma_engine:${platform}`, reason: `No Enigma-optimised engine for ${what} yet; the official llama.cpp engine is used.` };
  }
  if (!profileFor(entry, option)) {
    return { entry: null, code: `enigma_no_profile:${option.modelId}`, reason: `The Enigma engine ${entry.id} has no profile for ${option.name}.` };
  }
  if (entry.distribution === 'local' && !envDir(entry)) {
    return {
      entry: null, code: `enigma_not_published:${entry.id}`,
      reason: `The Enigma engine ${entry.id} is not published for download yet (set ENIGMA_ENGINE_DIR_${entry.envKey}).`,
    };
  }
  return { entry, code: '', reason: '' };
}

export function profileFor(entry: EngineEntry, option: Option): EngineProfile | undefined {
  const name = option.file.path.split('/').at(-1) ?? '';
  return entry.profiles?.find((p) => {
    const re = new RegExp(p.match, 'i');
    return re.test(option.modelId) || re.test(name);
  });
}

// ---- install ------------------------------------------------------------------------------------------------------

export interface ResolvedEngine { entry: EngineEntry; dir: string; serverBin: string; version: string; local: boolean }

const SERVER_EXE = process.platform === 'win32' ? 'llama-server.exe' : 'llama-server';

function envDir(entry: EngineEntry): string | null {
  const v = process.env[`ENIGMA_ENGINE_DIR_${entry.envKey}`];
  return v ? expandHome(v) : null;
}

/** Finds llama-server in `dir`, `dir/bin`, `dir/build/bin` or one level of subdirectories (release archives). */
export function findServerBin(dir: string): string | null {
  const direct = [join(dir, SERVER_EXE), join(dir, 'bin', SERVER_EXE), join(dir, 'build', 'bin', SERVER_EXE)];
  for (const p of direct) if (existsSync(p)) return p;
  let subs: string[] = [];
  try {
    subs = readdirSync(dir, { withFileTypes: true }).filter((d) => d.isDirectory()).map((d) => join(dir, d.name));
  } catch {
    return null;
  }
  for (const s of subs) {
    for (const p of [join(s, SERVER_EXE), join(s, 'bin', SERVER_EXE)]) if (existsSync(p)) return p;
  }
  return null;
}

/** `llama-server --version` -> "version: 7123 (abcdef0)" line, or null. */
async function binVersion(bin: string): Promise<string | null> {
  try {
    const proc = Bun.spawn([bin, '--version'], { stdout: 'pipe', stderr: 'pipe', env: { ...process.env, LD_LIBRARY_PATH: libPath(bin, true) } });
    const [out, err] = await Promise.all([new Response(proc.stdout).text(), new Response(proc.stderr).text()]);
    await proc.exited;
    const m = /version:\s*(.+)/.exec(out + err);
    return m?.[1]?.trim() ?? null;
  } catch {
    return null;
  }
}

function installDir(entry: EngineEntry): string {
  return join(paths().engines, entry.id, entry.version);
}

interface DigestStore { [assetName: string]: string }

function digestFile(entry: EngineEntry): string {
  return join(paths().engines, entry.id, 'digests.json');
}

/**
 * Makes the engine runnable: a local override directory, an existing install, or download + verify + extract.
 * Assets without a published digest are hashed at first download and the digest is stored next to the install.
 */
export async function ensureEngine(entry: EngineEntry, opts: { signal?: AbortSignal; onProgress?: (label: string, p: TransferProgress) => void } = {}): Promise<ResolvedEngine> {
  const local = envDir(entry);
  if (local) {
    const bin = findServerBin(local);
    if (!bin) throw new Error(`ENIGMA_ENGINE_DIR_${entry.envKey}=${local}: llama-server not found`);
    const commit = existsSync(join(local, 'COMMIT')) ? readFileSync(join(local, 'COMMIT'), 'utf8').split(/\s/)[0] : null;
    const version = commit ? `${entry.version.split(' ')[0]} ${commit}` : (await binVersion(bin)) ?? entry.version;
    opts.onProgress?.('reuse:engine', { done: 1, total: 1, rate: 0, etaS: 0 });
    return { entry, dir: engineRoot(bin), serverBin: bin, version, local: true };
  }
  if (entry.distribution === 'local') {
    throw new Error(`${entry.label} is not available for download yet (local engine only: ENIGMA_ENGINE_DIR_${entry.envKey})`);
  }
  const dir = installDir(entry);
  const marker = join(dir, '.installed');
  if (existsSync(marker)) {
    const bin = findServerBin(dir);
    if (bin) {
      opts.onProgress?.('reuse:engine', { done: 1, total: 1, rate: 0, etaS: 0 });
      return { entry, dir: engineRoot(bin), serverBin: bin, version: entry.version, local: false };
    }
  }
  const dl = join(paths().downloads, entry.id);
  mkdirSync(dl, { recursive: true });
  const digests: DigestStore = existsSync(digestFile(entry)) ? (JSON.parse(readFileSync(digestFile(entry), 'utf8')) as DigestStore) : {};
  const tmp = `${dir}.tmp-${process.pid}`;
  rmSync(tmp, { recursive: true, force: true });
  mkdirSync(tmp, { recursive: true });
  for (const asset of entry.assets) {
    const known = asset.sha256 ?? digests[asset.name];
    const archive = join(dl, asset.name);
    if (!existsSync(archive)) {
      log.info(`will download ${asset.name} (${(asset.sizeBytes / 1024 ** 3).toFixed(2)} GiB) from ${asset.url}`);
      const res = await downloadFile({
        url: asset.url, dest: archive, sizeBytes: asset.sizeBytes, ...(known ? { sha256: known } : {}),
        ...(opts.signal ? { signal: opts.signal } : {}), onProgress: (p) => opts.onProgress?.('engine', p),
      });
      if (!known) digests[asset.name] = res.sha256;
    } else if (known) {
      const sha = await cachedHash(archive, (p) => opts.onProgress?.('verify', p), opts.signal);
      if (sha !== known) {
        rmSync(archive);
        throw new Error(`${asset.name}: sha256 mismatch (file removed; retry downloads it again)`);
      }
    }
    opts.onProgress?.('extract', { done: 0, total: 1, rate: 0, etaS: 0 });
    await extractArchive(archive, tmp);
    opts.onProgress?.('extract', { done: 1, total: 1, rate: 0, etaS: 0 });
  }
  mkdirSync(dirname(digestFile(entry)), { recursive: true });
  writeFileSync(digestFile(entry), JSON.stringify(digests, null, 2));
  const bin = findServerBin(tmp);
  if (!bin) throw new Error(`${entry.id}: llama-server not found in the release archive`);
  if (process.platform !== 'win32') chmodSync(bin, 0o755);
  rmSync(dir, { recursive: true, force: true });
  renameSync(tmp, dir);
  writeFileSync(marker, new Date().toISOString());
  const finalBin = findServerBin(dir);
  if (!finalBin) throw new Error(`${entry.id}: install failed`);
  log.info(`engine ${entry.id} ${entry.version} installed in ${dir}`);
  return { entry, dir: engineRoot(finalBin), serverBin: finalBin, version: entry.version, local: false };
}

/** Engine root: the directory holding bin/ (ROCm-style prefix) or the binary itself. */
function engineRoot(bin: string): string {
  const d = dirname(bin);
  return d.endsWith('/bin') || d.endsWith('\\bin') ? dirname(d) : d;
}

// ---- archives -----------------------------------------------------------------------------------------------------

export async function extractArchive(archive: string, dest: string): Promise<void> {
  mkdirSync(dest, { recursive: true });
  if (archive.endsWith('.zip')) {
    extractZip(archive, dest);
    return;
  }
  const proc = Bun.spawn(['tar', '-xzf', archive, '-C', dest], { stdout: 'ignore', stderr: 'pipe' });
  const err = await new Response(proc.stderr).text();
  if ((await proc.exited) !== 0) throw new Error(`tar failed for ${archive}: ${err.trim()}`);
}

/** Minimal ZIP reader (stored + deflate, no ZIP64): enough for the llama.cpp release archives. */
export function extractZip(archive: string, dest: string): void {
  const buf = readFileSync(archive);
  let eocd = -1;
  for (let i = buf.length - 22; i >= Math.max(0, buf.length - 65557); i--) {
    if (buf.readUInt32LE(i) === 0x06054b50) {
      eocd = i;
      break;
    }
  }
  if (eocd < 0) throw new Error(`${archive}: not a zip file`);
  const count = buf.readUInt16LE(eocd + 10);
  let off = buf.readUInt32LE(eocd + 16);
  if (off === 0xffffffff) throw new Error(`${archive}: ZIP64 is not supported`);
  for (let n = 0; n < count; n++) {
    if (buf.readUInt32LE(off) !== 0x02014b50) throw new Error(`${archive}: bad central directory`);
    const method = buf.readUInt16LE(off + 10);
    const csize = buf.readUInt32LE(off + 20);
    const nameLen = buf.readUInt16LE(off + 28);
    const extraLen = buf.readUInt16LE(off + 30);
    const commentLen = buf.readUInt16LE(off + 32);
    const extAttr = buf.readUInt32LE(off + 38);
    const local = buf.readUInt32LE(off + 42);
    const name = buf.subarray(off + 46, off + 46 + nameLen).toString('utf8');
    off += 46 + nameLen + extraLen + commentLen;
    const target = join(dest, name);
    if (!target.startsWith(join(dest)) || name.split(/[\\/]/).includes('..')) throw new Error(`${archive}: unsafe path ${name}`);
    if (name.endsWith('/')) {
      mkdirSync(target, { recursive: true });
      continue;
    }
    const lNameLen = buf.readUInt16LE(local + 26);
    const lExtraLen = buf.readUInt16LE(local + 28);
    const start = local + 30 + lNameLen + lExtraLen;
    const data = buf.subarray(start, start + csize);
    mkdirSync(dirname(target), { recursive: true });
    if (method === 0) writeFileSync(target, data);
    else if (method === 8) writeFileSync(target, inflateRawSync(data));
    else throw new Error(`${archive}: compression method ${method} not supported (${name})`);
    const mode = extAttr >>> 16;
    if (process.platform !== 'win32' && mode & 0o111) chmodSync(target, mode & 0o777);
  }
}

// ---- configs ------------------------------------------------------------------------------------------------------

/** Threads for CPU inference: the cores this process may run on (affinity-aware), at most the physical cores. */
export function cpuThreads(hw: Hw | null): number {
  const avail = availableParallelism();
  return Math.max(1, Math.min(avail, hw?.cpu.cores ?? avail));
}

/** Baseline: the official engine with only the settings needed to fit (ctx, KV type, ubatch). */
export function baselineConfig(engine: ResolvedEngine, option: Option, modelPath: string, hw: Hw | null): EngineConfig {
  const cfg: EngineConfig = {
    engineId: engine.entry.id, modelPath, ctx: option.ctx, kvType: option.kvType, ub: option.ub, b: Math.max(2048, option.ub),
    flashAttn: true, spec: 'none', extraArgs: ['--jinja'], env: {},
  };
  if (option.backend === 'cpu') cfg.threads = cpuThreads(hw);
  return cfg;
}

function rocmLib(): string {
  const candidates = [process.env.ROCM_PATH ? join(process.env.ROCM_PATH, 'lib') : '', '/opt/rocm/core-10.0/lib', '/opt/rocm/lib'];
  return candidates.find((c) => c && existsSync(c)) ?? '/opt/rocm/lib';
}

/** Files a profile needs, looked up next to the engine and in the model directories. */
function resolveNeed(need: string, engine: ResolvedEngine, modelPath: string): string | null {
  if (need === 'draftVocab') {
    const name = 'draft_vocab_qwen38.txt';
    const roots = [join(engine.dir, 'share'), engine.dir, dirname(modelPath), extraModelsDir(), paths().models].filter((d): d is string => !!d);
    for (const r of roots) {
      for (const p of [join(r, name), join(r, 'draft', name)]) if (existsSync(p)) return p;
    }
  }
  return null;
}

export interface EnigmaConfigResult { config: EngineConfig | null; reason: string }

/** The enigma profile for this option, with placeholders resolved. */
export function enigmaConfig(engine: ResolvedEngine, option: Option, modelPath: string): EnigmaConfigResult {
  const profile = profileFor(engine.entry, option);
  if (!profile) return { config: null, reason: `no profile for ${option.modelId}` };
  const vars: Record<string, string> = {
    engineDir: engine.dir, rocmLib: rocmLib(), pathSep: delimiter, kv: option.kvType,
    mtpCache: join(homedir(), '.cache', 'llama-mtp'), home: homedir(),
  };
  for (const need of profile.needs) {
    const p = resolveNeed(need, engine, modelPath);
    if (!p) return { config: null, reason: `${profile.id} needs ${need}, not found next to the engine or the models` };
    vars[need] = p;
  }
  const sub = (s: string): string => s.replace(/\{(\w+)\}/g, (m, k: string) => vars[k] ?? m);
  const env: Record<string, string> = {};
  for (const [k, v] of Object.entries(profile.env)) env[k] = sub(v);
  if (env.LLAMA_MTP_REQUANT_CACHE) mkdirSync(env.LLAMA_MTP_REQUANT_CACHE, { recursive: true });
  const ub = profile.ub ?? option.ub;
  return {
    config: {
      engineId: engine.entry.id, modelPath, ctx: option.ctx, kvType: option.kvType, ub, b: profile.b ?? Math.max(2048, ub),
      flashAttn: true, spec: profile.spec, extraArgs: profile.args.map(sub), env,
    },
    reason: '',
  };
}

// ---- server process -----------------------------------------------------------------------------------------------

export interface RunningServer {
  url: string;
  port: number;
  apiKey: string;
  logFile: string;
  config: EngineConfig;
  engine: ResolvedEngine;
  stop(): Promise<void>;
}

const running = new Set<RunningServer>();

/** Library path for an engine: next to the binary, ../lib, the ROCm runtime for HIP builds, then the inherited one. */
function libPath(bin: string, rocm: boolean): string {
  const parts = [dirname(bin), join(dirname(dirname(bin)), 'lib')];
  if (rocm) parts.push(rocmLib());
  if (process.env.LD_LIBRARY_PATH) parts.push(process.env.LD_LIBRARY_PATH);
  return [...new Set(parts.filter(Boolean))].join(delimiter);
}

export function serverArgs(engine: ResolvedEngine, cfg: EngineConfig, port: number, apiKey: string): string[] {
  const gpu = engine.entry.backend !== 'cpu';
  const args = [
    '-m', cfg.modelPath, '-c', String(cfg.ctx), '-ngl', gpu ? '999' : '0', '-fa', cfg.flashAttn ? 'on' : 'off',
    '-ctk', cfg.kvType, '-ctv', cfg.kvType, '-b', String(cfg.b), '-ub', String(cfg.ub), '-np', '1',
    '--host', '127.0.0.1', '--port', String(port), '--api-key', apiKey,
    // clients see the model file name, not a local path
    '--alias', basename(cfg.modelPath).replace(/\.gguf$/i, ''),
  ];
  if (cfg.threads) args.push('-t', String(cfg.threads));
  args.push(...cfg.extraArgs);
  return args;
}

async function freePort(): Promise<number> {
  const s = Bun.listen({ hostname: '127.0.0.1', port: 0, socket: { data() {} } });
  const port = s.port;
  s.stop(true);
  return port;
}

function tail(file: string, lines = 30): string {
  try {
    return readFileSync(file, 'utf8').split('\n').slice(-lines).join('\n');
  } catch {
    return '';
  }
}

interface Slot { is_processing?: boolean }

/** Waits until no slot is processing (or the timeout passes). */
async function waitIdle(url: string, apiKey: string, timeoutMs: number): Promise<void> {
  const end = Date.now() + timeoutMs;
  while (Date.now() < end) {
    try {
      const r = await fetch(`${url}/slots`, { headers: { authorization: `Bearer ${apiKey}` }, signal: AbortSignal.timeout(5000) });
      if (!r.ok) return; // slots endpoint disabled: nothing to wait for
      const slots = (await r.json()) as Slot[];
      if (!slots.some((s) => s.is_processing)) return;
    } catch {
      return; // not answering: no generation to protect
    }
    await Bun.sleep(1000);
  }
}

/** Graceful stop: idle /slots, ONE SIGTERM, 45 s, SIGKILL last. */
async function gracefulStop(proc: Subprocess, url: string, apiKey: string): Promise<void> {
  if (proc.exitCode !== null || proc.signalCode !== null) return;
  await waitIdle(url, apiKey, 120_000);
  proc.kill('SIGTERM');
  const done = await Promise.race([proc.exited.then(() => true), Bun.sleep(45_000).then(() => false)]);
  if (!done) {
    log.warn(`llama-server pid ${proc.pid} ignored SIGTERM for 45 s, sending SIGKILL`);
    proc.kill('SIGKILL');
    await proc.exited;
  }
}

export interface StartOptions { signal?: AbortSignal; timeoutMs?: number; label?: string }

/** Spawns llama-server on 127.0.0.1 with a random port and API key; resolves when /health is OK. */
export async function startServer(engine: ResolvedEngine, cfg: EngineConfig, opts: StartOptions = {}): Promise<RunningServer> {
  const port = await freePort();
  const apiKey = randomBytes(18).toString('base64url');
  const logDir = paths().logs;
  mkdirSync(logDir, { recursive: true });
  const stamp = new Date().toISOString().replace(/[:.]/g, '-');
  const logFile = join(logDir, `server-${engine.entry.id}-${stamp}.log`);
  const args = serverArgs(engine, cfg, port, apiKey);
  const env: Record<string, string> = { ...(process.env as Record<string, string>), ...cfg.env };
  // a profile's LD_LIBRARY_PATH is used verbatim (run-llm.sh sets it, nothing inherited)
  env.LD_LIBRARY_PATH = cfg.env.LD_LIBRARY_PATH ?? libPath(engine.serverBin, engine.entry.backend === 'rocm');
  const shown = args.map((a) => (a === apiKey ? '***' : a));
  const envShown = Object.entries(cfg.env).map(([k, v]) => `${k}=${v}`).join(' ');
  log.info(`start ${opts.label ?? engine.entry.id}: ${envShown ? envShown + ' ' : ''}${engine.serverBin} ${shown.join(' ')}`);
  const fd = openSync(logFile, 'a');
  writeSync(fd, `# ${new Date().toISOString()} ${envShown} ${engine.serverBin} ${shown.join(' ')}\n`);
  let proc: Subprocess;
  try {
    proc = Bun.spawn([engine.serverBin, ...args], { env, stdin: 'ignore', stdout: fd, stderr: fd, cwd: dirname(engine.serverBin) });
  } finally {
    closeSync(fd);
  }
  const url = `http://127.0.0.1:${port}`;
  const server: RunningServer = {
    url, port, apiKey, logFile, config: cfg, engine,
    stop: async () => {
      running.delete(server);
      await gracefulStop(proc, url, apiKey);
    },
  };
  running.add(server);
  const deadline = Date.now() + (opts.timeoutMs ?? 20 * 60_000);
  try {
    while (true) {
      if (opts.signal?.aborted) throw new Error('cancelled');
      if (proc.exitCode !== null || proc.signalCode !== null) {
        throw new Error(`llama-server exited (${proc.exitCode ?? proc.signalCode}) while loading:\n${tail(logFile)}`);
      }
      if (Date.now() > deadline) throw new Error(`llama-server not healthy after ${Math.round((opts.timeoutMs ?? 1_200_000) / 1000)} s`);
      try {
        const r = await fetch(`${url}/health`, { signal: AbortSignal.timeout(3000) });
        if (r.ok) break;
      } catch {
        // still starting
      }
      await Bun.sleep(500);
    }
  } catch (e) {
    await server.stop();
    throw e;
  }
  log.info(`llama-server ready on ${url} (pid ${proc.pid}, log ${logFile})`);
  return server;
}

/** n_ctx the server actually allocated (GET /props). */
export async function serverCtx(s: RunningServer): Promise<number | null> {
  try {
    const r = await fetch(`${s.url}/props`, { headers: { authorization: `Bearer ${s.apiKey}` } });
    if (!r.ok) return null;
    const p = (await r.json()) as { default_generation_settings?: { n_ctx?: number }; n_ctx?: number };
    return p.default_generation_settings?.n_ctx ?? p.n_ctx ?? null;
  } catch {
    return null;
  }
}

/** Stops every server this process started (app shutdown). */
export async function stopAllServers(): Promise<void> {
  await Promise.all([...running].map((s) => s.stop().catch((e: unknown) => log.warn(`stop failed: ${errMsg(e)}`))));
}
