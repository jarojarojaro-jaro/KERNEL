// Resumable HTTP downloads (Range), progress (rate, ETA), sha256 verification, temp file + atomic rename, cancel;
// reuse of files already on disk (ENIGMA_MODELS_DIR) with hashing on a worker.
import { existsSync, readdirSync, readFileSync, renameSync, statSync, unlinkSync, writeFileSync, mkdirSync, type Dirent } from 'node:fs';
import { open } from 'node:fs/promises';
import { basename, dirname, join } from 'node:path';
import { paths } from './paths.ts';

export interface TransferProgress { done: number; total: number; rate: number; etaS: number }
export type ProgressFn = (p: TransferProgress) => void;

export class CancelledError extends Error {
  constructor() {
    super('cancelled');
    this.name = 'CancelledError';
  }
}

export interface DownloadOptions {
  url: string;
  dest: string;
  sizeBytes?: number;
  sha256?: string;
  signal?: AbortSignal;
  onProgress?: ProgressFn;
  /** attempts after network failures (each one resumes from the bytes already on disk) */
  retries?: number;
  headers?: Record<string, string>;
}

export interface DownloadResult { path: string; bytes: number; sha256: string }

/** HF resolve URL for a repo file; HF_ENDPOINT overrides the host (mirrors). */
export function hfUrl(repo: string, path: string): string {
  const base = (process.env.HF_ENDPOINT ?? 'https://huggingface.co').replace(/\/+$/, '');
  return `${base}/${repo}/resolve/main/${path.split('/').map(encodeURIComponent).join('/')}`;
}

/** Progress meter: smoothed rate (bytes/s) and ETA, throttled to ~4 updates/s. */
export class Meter {
  private lastT = 0;
  private lastDone = 0;
  private rate = 0;
  private primed = false;
  constructor(private readonly fn: ProgressFn | undefined, private total: number, startDone = 0) {
    this.lastT = performance.now();
    this.lastDone = startDone;
  }
  setTotal(total: number): void {
    this.total = total;
  }
  update(done: number, force = false): void {
    if (!this.fn) return;
    const now = performance.now();
    const dt = (now - this.lastT) / 1000;
    if (!force && dt < 0.25) return;
    // the first sample after construction includes connect/redirect/prefix-hash time, not transfer: only re-base
    if (dt > 0 && this.primed) {
      const inst = (done - this.lastDone) / dt;
      this.rate = this.rate === 0 ? inst : this.rate * 0.7 + inst * 0.3;
    }
    this.primed = true;
    this.lastT = now;
    this.lastDone = done;
    const left = Math.max(0, this.total - done);
    this.fn({ done, total: this.total, rate: Math.max(0, this.rate), etaS: this.rate > 0 ? left / this.rate : 0 });
  }
}

async function hashPrefix(path: string): Promise<Bun.CryptoHasher> {
  const hasher = new Bun.CryptoHasher('sha256');
  if (existsSync(path)) for await (const chunk of Bun.file(path).stream()) hasher.update(chunk);
  return hasher;
}

function sleep(ms: number, signal?: AbortSignal): Promise<void> {
  const { promise, resolve, reject } = Promise.withResolvers<void>();
  const t = setTimeout(resolve, ms);
  signal?.addEventListener('abort', () => {
    clearTimeout(t);
    reject(new CancelledError());
  }, { once: true });
  return promise;
}

/** The server ignored our Range request: the caller drops the .part and starts over. */
class RestartError extends Error {}

/** One transfer attempt from the current .part size; returns the final size. */
async function attempt(o: DownloadOptions, part: string, hasher: Bun.CryptoHasher, meter: Meter): Promise<number> {
  const have = existsSync(part) ? statSync(part).size : 0;
  if (o.sizeBytes !== undefined && have === o.sizeBytes) return have;
  const headers: Record<string, string> = { ...o.headers, 'accept-encoding': 'identity' };
  if (have > 0) headers.range = `bytes=${have}-`;
  const res = await fetch(o.url, { headers, signal: o.signal, redirect: 'follow' });
  if (res.status === 416 && have > 0) {
    // the server has nothing past what we hold: the .part is complete (size checked by the caller)
    await res.body?.cancel();
    return have;
  }
  if (!res.ok) {
    await res.body?.cancel();
    throw new Error(`HTTP ${res.status} for ${o.url}`);
  }
  if (have > 0 && res.status !== 206) {
    await res.body?.cancel();
    throw new RestartError('range ignored');
  }
  const len = Number(res.headers.get('content-length') ?? NaN);
  if (o.sizeBytes === undefined && Number.isFinite(len)) meter.setTotal(have + len);
  const fh = await open(part, 'a');
  try {
    if (!res.body) throw new Error('empty response body');
    let done = have;
    for await (const chunk of res.body) {
      await fh.write(chunk);
      hasher.update(chunk);
      done += chunk.byteLength;
      meter.update(done);
    }
    meter.update(done, true);
    return done;
  } finally {
    await fh.close();
  }
}


/**
 * Downloads `url` to `dest` through `dest.part` (resumed with a Range request when present), verifies size and
 * sha256 when known, then renames atomically. Cancelling leaves the .part for a later resume.
 */
export async function downloadFile(o: DownloadOptions): Promise<DownloadResult> {
  mkdirSync(dirname(o.dest), { recursive: true });
  const part = `${o.dest}.part`;
  const retries = o.retries ?? 5;
  let hasher = await hashPrefix(part);
  const meter = new Meter(o.onProgress, o.sizeBytes ?? 0, existsSync(part) ? statSync(part).size : 0);
  let size = 0;
  for (let i = 0; ; i++) {
    if (o.signal?.aborted) throw new CancelledError();
    try {
      size = await attempt(o, part, hasher, meter);
      if (o.sizeBytes !== undefined && size < o.sizeBytes) throw new Error(`transfer ended at ${size} of ${o.sizeBytes} bytes`);
      break;
    } catch (e) {
      if (o.signal?.aborted) throw new CancelledError();
      if (e instanceof RestartError) {
        unlinkSync(part);
        hasher = new Bun.CryptoHasher('sha256');
        continue;
      }
      if (i >= retries) throw e;
      // resume from what reached the disk; rehash the prefix so the digest matches the file exactly
      hasher = await hashPrefix(part);
      await sleep(Math.min(30_000, 500 * 2 ** i), o.signal);
    }
  }
  if (o.sizeBytes !== undefined && size !== o.sizeBytes) {
    unlinkSync(part);
    throw new Error(`size mismatch: got ${size}, expected ${o.sizeBytes}`);
  }
  const sha256 = hasher.digest('hex');
  if (o.sha256 && sha256 !== o.sha256.toLowerCase()) {
    unlinkSync(part);
    throw new Error(`sha256 mismatch for ${basename(o.dest)}: got ${sha256}, expected ${o.sha256}`);
  }
  renameSync(part, o.dest);
  rememberHash(o.dest, sha256); // a later reuse (retry, restart) must not hash the whole file again
  return { path: o.dest, bytes: size, sha256 };
}

interface WorkerMsg { type: 'progress' | 'done' | 'error'; done?: number; total?: number; sha256?: string; message?: string }

/** sha256 of a file on a worker thread, with progress; cancel terminates the worker. */
export function hashFile(path: string, onProgress?: ProgressFn, signal?: AbortSignal): Promise<string> {
  const { promise, resolve, reject } = Promise.withResolvers<string>();
  const worker = new Worker(new URL('./hash-worker.js', import.meta.url).href);
  const total = statSync(path).size;
  const meter = new Meter(onProgress, total);
  const finish = (): void => {
    signal?.removeEventListener('abort', abort);
    worker.terminate();
  };
  const abort = (): void => {
    finish();
    reject(new CancelledError());
  };
  signal?.addEventListener('abort', abort, { once: true });
  worker.onmessage = (ev: MessageEvent<WorkerMsg>) => {
    const m = ev.data;
    if (m.type === 'progress') {
      meter.update(m.done ?? 0, m.done === total);
      return;
    }
    finish();
    if (m.type === 'done' && m.sha256) resolve(m.sha256);
    else reject(new Error(m.message ?? 'hash failed'));
  };
  worker.onerror = (e) => {
    finish();
    reject(new Error(e.message));
  };
  worker.postMessage({ path });
  return promise;
}

// ---- reuse of files already on disk -------------------------------------------------------------------------------

/** Finds `name` with exactly `sizeBytes` in the given dirs, searching each dir and two levels below it. */
export function findLocalFile(name: string, sizeBytes: number, dirs: string[]): string | null {
  for (const root of dirs) {
    const stack: { dir: string; depth: number }[] = [{ dir: root, depth: 0 }];
    while (stack.length > 0) {
      const { dir, depth } = stack.shift() as { dir: string; depth: number };
      let entries: Dirent[];
      try {
        entries = readdirSync(dir, { withFileTypes: true });
      } catch {
        continue;
      }
      for (const e of entries) {
        const p = join(dir, e.name);
        if (e.isFile() && e.name === name) {
          try {
            if (statSync(p).size === sizeBytes) return p;
          } catch {
            // vanished between readdir and stat
          }
        } else if (e.isDirectory() && depth < 2 && !e.name.startsWith('.')) {
          stack.push({ dir: p, depth: depth + 1 });
        }
      }
    }
  }
  return null;
}

interface HashCacheEntry { size: number; mtimeMs: number; sha256: string }

function hashCacheFile(): string {
  return join(paths().home, 'hashes.json');
}

function readHashCache(): Record<string, HashCacheEntry> {
  try {
    return JSON.parse(readFileSync(hashCacheFile(), 'utf8')) as Record<string, HashCacheEntry>;
  } catch {
    return {};
  }
}

function rememberHash(path: string, sha256: string): void {
  const st = statSync(path);
  const cache = readHashCache();
  cache[path] = { size: st.size, mtimeMs: st.mtimeMs, sha256 };
  mkdirSync(dirname(hashCacheFile()), { recursive: true });
  writeFileSync(hashCacheFile(), JSON.stringify(cache, null, 1));
}

/** sha256 of a file, cached by path+size+mtime (verifying a 20 GB file once is enough). */
export async function cachedHash(path: string, onProgress?: ProgressFn, signal?: AbortSignal): Promise<string> {
  const st = statSync(path);
  const hit = readHashCache()[path];
  if (hit && hit.size === st.size && hit.mtimeMs === st.mtimeMs) return hit.sha256;
  const sha256 = await hashFile(path, onProgress, signal);
  rememberHash(path, sha256);
  return sha256;
}
