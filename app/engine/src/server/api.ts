// HTTP API on 127.0.0.1 (CONTRACT.md "API"): JSON routes, SSE events, the /v1 proxy to llama-server, and the UI.
import { existsSync, statSync } from 'node:fs';
import { join, normalize } from 'node:path';
import type { Server } from 'bun';
import type { AppState, Progress } from '../shared/types.ts';
import { App, HttpError } from './state.ts';
import { errMsg, log, onLog, type LogLine } from './log.ts';
import { PORT_FALLBACKS } from './paths.ts';

/** UI files embedded by tools/build.ts (path without leading slash -> embedded file path); empty in dev. */
const embeddedUi = new Map<string, string>();

export function registerEmbeddedUi(files: Record<string, string>): void {
  for (const [k, v] of Object.entries(files)) embeddedUi.set(k, v);
}

/** dist/ui on disk next to the sources (dev runs). */
const DEV_UI_DIR = join(import.meta.dir, '..', '..', 'dist', 'ui');

function json(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), { status, headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' } });
}

function fail(status: number, error: string): Response {
  return json({ error }, status);
}

const LOCAL_HOSTS: Record<string, true> = { '127.0.0.1': true, localhost: true, '[::1]': true };

/** DNS-rebinding and cross-site guard: Host and (if sent) Origin must name this machine. */
export function hostAllowed(req: Request): boolean {
  const host = req.headers.get('host');
  if (!host) return false;
  const hostname = host.startsWith('[') ? host.slice(0, host.indexOf(']') + 1) : host.split(':')[0];
  if (!hostname || !LOCAL_HOSTS[hostname.toLowerCase()]) return false;
  const origin = req.headers.get('origin');
  if (origin === null) return true;
  try {
    const u = new URL(origin);
    return (u.protocol === 'http:' || u.protocol === 'https:') && LOCAL_HOSTS[u.hostname.toLowerCase()] === true;
  } catch {
    return false;
  }
}

async function body<T>(req: Request): Promise<T> {
  const text = await req.text();
  if (!text) return {} as T;
  try {
    return JSON.parse(text) as T;
  } catch {
    throw new HttpError(400, 'invalid JSON body');
  }
}

/** Server-sent events: `state`, `log`, `progress`. */
function events(app: App, req: Request): Response {
  const enc = new TextEncoder();
  let cleanup = (): void => {};
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      const send = (event: string, data: unknown): void => {
        try {
          controller.enqueue(enc.encode(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`));
        } catch {
          cleanup();
        }
      };
      send('state', app.state);
      const offState = app.onState((s: AppState) => send('state', s));
      const offProgress = app.onProgress((p: Progress) => send('progress', p));
      const offLog = onLog((l: LogLine) => send('log', l));
      const ping = setInterval(() => {
        try {
          controller.enqueue(enc.encode(': ping\n\n'));
        } catch {
          cleanup();
        }
      }, 15_000);
      cleanup = () => {
        offState();
        offProgress();
        offLog();
        clearInterval(ping);
      };
      req.signal.addEventListener('abort', () => {
        cleanup();
        try {
          controller.close();
        } catch {
          // already closed
        }
      });
    },
    cancel() {
      cleanup();
    },
  });
  return new Response(stream, { headers: { 'content-type': 'text/event-stream', 'cache-control': 'no-store', connection: 'keep-alive' } });
}

const HOP_HEADERS = ['host', 'authorization', 'origin', 'referer', 'connection', 'content-length', 'accept-encoding', 'cookie'];

/** /v1/* → the running llama-server, with its private API key; streaming responses pass through. */
async function proxy(app: App, req: Request, url: URL): Promise<Response> {
  const s = app.server;
  if (!s || app.state.phase !== 'ready') return fail(503, 'The model server is not running.');
  const headers = new Headers(req.headers);
  for (const h of HOP_HEADERS) headers.delete(h);
  headers.set('authorization', `Bearer ${s.apiKey}`);
  const init: RequestInit = { method: req.method, headers, signal: req.signal };
  if (req.method !== 'GET' && req.method !== 'HEAD') init.body = await req.arrayBuffer();
  let res: Response;
  try {
    res = await fetch(`${s.url}${url.pathname}${url.search}`, init);
  } catch (e) {
    return fail(502, `model server unreachable: ${errMsg(e)}`);
  }
  const out = new Headers(res.headers);
  out.delete('content-encoding');
  out.delete('content-length');
  out.delete('access-control-allow-origin');
  return new Response(res.body, { status: res.status, headers: out });
}

const MIME: Record<string, string> = {
  html: 'text/html; charset=utf-8', js: 'text/javascript; charset=utf-8', css: 'text/css; charset=utf-8',
  svg: 'image/svg+xml', png: 'image/png', jpg: 'image/jpeg', ico: 'image/x-icon', json: 'application/json',
  woff2: 'font/woff2', woff: 'font/woff', txt: 'text/plain; charset=utf-8', webp: 'image/webp',
};

function uiFile(path: string): Response | null {
  const rel = normalize(path.replace(/^\/+/, '')).replace(/\\/g, '/');
  if (rel.startsWith('..')) return null;
  const embedded = embeddedUi.get(rel);
  const file = embedded ?? join(DEV_UI_DIR, rel);
  if (!embedded && (!existsSync(file) || !statSync(file).isFile())) return null;
  const ext = rel.split('.').pop() ?? '';
  const cache = rel.startsWith('assets/') ? 'public, max-age=31536000, immutable' : 'no-cache';
  return new Response(Bun.file(file), { headers: { 'content-type': MIME[ext] ?? 'application/octet-stream', 'cache-control': cache } });
}

/** Static UI with SPA fallback to index.html. */
function ui(url: URL): Response {
  const direct = url.pathname !== '/' ? uiFile(url.pathname) : null;
  if (direct) return direct;
  if (url.pathname.startsWith('/assets/')) return fail(404, 'not found');
  return uiFile('index.html') ?? new Response('Enigma UI is not built (run `bun run build:ui`). The API is available under /api.', {
    status: 503, headers: { 'content-type': 'text/plain; charset=utf-8' },
  });
}

async function route(app: App, req: Request, url: URL): Promise<Response> {
  const p = url.pathname;
  const m = req.method;
  if (p.startsWith('/v1/') || p === '/v1') return proxy(app, req, url);
  if (!p.startsWith('/api/')) return m === 'GET' || m === 'HEAD' ? ui(url) : fail(405, 'method not allowed');
  if (m === 'GET' && p === '/api/state') return json(app.state);
  if (m === 'GET' && p === '/api/events') return events(app, req);
  if (m !== 'POST') return fail(405, 'method not allowed');
  switch (p) {
    case '/api/license': {
      const b = await body<{ key?: unknown }>(req);
      if (typeof b.key !== 'string' || !b.key.trim()) return fail(400, 'key required');
      return json(await app.setLicense(b.key));
    }
    case '/api/scan':
      return json(await app.scan());
    case '/api/recommend': {
      const b = await body<{ minCtx?: unknown }>(req);
      const minCtx = b.minCtx === undefined ? undefined : Number(b.minCtx);
      if (minCtx !== undefined && !(Number.isInteger(minCtx) && minCtx > 0)) return fail(400, 'minCtx must be a positive integer');
      return json(await app.recommend(minCtx));
    }
    case '/api/start': {
      const b = await body<{ optionId?: unknown }>(req);
      if (typeof b.optionId !== 'string') return fail(400, 'optionId required');
      await app.start(b.optionId);
      return json(app.state);
    }
    case '/api/cancel':
      await app.cancel();
      return json(app.state);
    case '/api/engine/start':
      await app.startEngine();
      return json(app.state);
    case '/api/engine/stop':
      await app.stopEngine();
      return json(app.state);
    default:
      return fail(404, 'not found');
  }
}

async function handle(app: App, req: Request): Promise<Response> {
  if (!hostAllowed(req)) return fail(403, 'forbidden host/origin');
  const url = new URL(req.url);
  try {
    return await route(app, req, url);
  } catch (e) {
    if (e instanceof HttpError) return fail(e.status, e.message);
    log.error(`${req.method} ${url.pathname}: ${errMsg(e)}`);
    return fail(500, errMsg(e));
  }
}

/**
 * Serves the API on 127.0.0.1:`port`, or on the next free port of the following PORT_FALLBACKS when it is taken
 * (11500 belongs to omp on many machines). The bound port is stored in `app.apiPort` (ready.endpoint uses it).
 */
export function serveApi(app: App, port: number): Server<undefined> {
  for (let p = port; p <= Math.min(65535, port + PORT_FALLBACKS); p++) {
    try {
      const server = Bun.serve({
        hostname: '127.0.0.1',
        port: p,
        idleTimeout: 0, // SSE and long generations through /v1
        fetch: (req) => handle(app, req),
      });
      if (p !== port) log.warn(`port ${port} is taken; using ${p}`);
      app.apiPort = server.port ?? p;
      return server;
    } catch (e) {
      const inUse = e instanceof Error && 'code' in e && e.code === 'EADDRINUSE';
      if (!inUse) throw e;
    }
  }
  throw new Error(`ports ${port}-${port + PORT_FALLBACKS} are all taken; set ENIGMA_PORT`);
}
