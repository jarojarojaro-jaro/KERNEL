import { afterAll, beforeAll, describe, expect, test } from 'bun:test';
import { createHash, randomBytes } from 'node:crypto';
import { existsSync, mkdirSync, mkdtempSync, rmSync, statSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import type { Server } from 'bun';
import { CancelledError, downloadFile, findLocalFile, hashFile, type TransferProgress } from '../src/server/download.ts';

const DATA = randomBytes(3 * 1024 * 1024 + 123);
const SHA = createHash('sha256').update(DATA).digest('hex');
let server: Server<undefined>;
let base = '';
let dir = '';
const hits: Record<string, number> = {};

/**
 * Streams `body` in 64 KiB chunks; `cutAt` drops the connection after that many bytes; `delayMs` per chunk.
 * The delay is real on purpose: the meter derives rate/ETA from the wall clock across a real socket.
 */
function stream(body: Uint8Array, cutAt?: number, delayMs = 0): ReadableStream<Uint8Array> {
  let off = 0;
  return new ReadableStream({
    async pull(c) {
      if (delayMs) await Bun.sleep(delayMs);
      if (cutAt !== undefined && off >= cutAt) {
        c.error(new Error('connection dropped'));
        return;
      }
      if (off >= body.length) {
        c.close();
        return;
      }
      const end = Math.min(body.length, off + 65536, cutAt ?? Infinity);
      c.enqueue(body.subarray(off, end));
      off = end;
    },
  });
}

const prevHome = process.env.ENIGMA_HOME;
beforeAll(() => {
  dir = mkdtempSync(join(tmpdir(), 'enigma-dl-'));
  process.env.ENIGMA_HOME = join(dir, 'home'); // the digest cache (hashes.json) must not land in the real ~/.enigma
  server = Bun.serve({
    port: 0,
    hostname: '127.0.0.1',
    fetch(req) {
      const url = new URL(req.url);
      const n = (hits[url.pathname] = (hits[url.pathname] ?? 0) + 1);
      const range = req.headers.get('range');
      const start = range && url.pathname !== '/norange' ? Number(/bytes=(\d+)-/.exec(range)?.[1] ?? 0) : 0;
      if (start >= DATA.length && start > 0) return new Response(null, { status: 416 });
      const slice = DATA.subarray(start);
      const headers = { 'content-length': String(slice.length), 'accept-ranges': 'bytes' };
      const status = start > 0 ? 206 : 200;
      // /flaky: the first two responses drop the connection after 1 MiB
      if (url.pathname === '/flaky' && n <= 2) return new Response(stream(slice, 1024 * 1024), { status, headers });
      if (url.pathname === '/norange' && n === 1) return new Response(stream(slice, 512 * 1024), { status: 200, headers });
      if (url.pathname === '/slow') return new Response(stream(slice, undefined, 20), { status, headers });
      return new Response(stream(slice), { status, headers });
    },
  });
  base = `http://127.0.0.1:${server.port}`;
});

afterAll(() => {
  server.stop(true);
  if (prevHome === undefined) delete process.env.ENIGMA_HOME;
  else process.env.ENIGMA_HOME = prevHome;
  rmSync(dir, { recursive: true, force: true });
});

describe('downloadFile', () => {
  test('resumes interrupted transfers with Range and verifies sha256', async () => {
    const dest = join(dir, 'flaky.bin');
    const seen: TransferProgress[] = [];
    const r = await downloadFile({ url: `${base}/flaky`, dest, sizeBytes: DATA.length, sha256: SHA, onProgress: (p) => seen.push(p) });
    expect(r.sha256).toBe(SHA);
    expect(statSync(dest).size).toBe(DATA.length);
    expect(existsSync(`${dest}.part`)).toBe(false);
    expect(hits['/flaky']).toBe(3);
    expect(seen.at(-1)?.done).toBe(DATA.length);
  });

  test('restarts when the server ignores Range', async () => {
    const dest = join(dir, 'norange.bin');
    const r = await downloadFile({ url: `${base}/norange`, dest, sizeBytes: DATA.length, sha256: SHA });
    expect(r.sha256).toBe(SHA);
  });

  test('cancel keeps the .part, a later call resumes it', async () => {
    const dest = join(dir, 'slow.bin');
    const ac = new AbortController();
    const p = downloadFile({
      url: `${base}/slow`, dest, sizeBytes: DATA.length, signal: ac.signal,
      onProgress: (pr) => { if (pr.done > 256 * 1024) ac.abort(); },
    });
    await expect(p).rejects.toBeInstanceOf(CancelledError);
    const partSize = statSync(`${dest}.part`).size;
    expect(partSize).toBeGreaterThan(0);
    expect(partSize).toBeLessThan(DATA.length);
    const r = await downloadFile({ url: `${base}/ok`, dest, sizeBytes: DATA.length, sha256: SHA });
    expect(r.sha256).toBe(SHA);
  });

  test('sha256 mismatch fails and leaves nothing', async () => {
    const dest = join(dir, 'bad.bin');
    await expect(downloadFile({ url: `${base}/ok`, dest, sizeBytes: DATA.length, sha256: '0'.repeat(64), retries: 0 })).rejects.toThrow('sha256 mismatch');
    expect(existsSync(dest)).toBe(false);
    expect(existsSync(`${dest}.part`)).toBe(false);
  });

  test('progress carries rate and ETA', async () => {
    const seen: TransferProgress[] = [];
    await downloadFile({ url: `${base}/slow`, dest: join(dir, 'rate.bin'), sizeBytes: DATA.length, onProgress: (p) => seen.push(p) });
    const mid = seen.find((p) => p.done < DATA.length && p.rate > 0);
    expect(mid).toBeDefined();
    expect(mid?.etaS).toBeGreaterThan(0);
    expect(mid?.total).toBe(DATA.length);
  });
});

describe('reuse', () => {
  test('hashFile on a worker', async () => {
    const f = join(dir, 'h.bin');
    writeFileSync(f, DATA);
    const seen: number[] = [];
    expect(await hashFile(f, (p) => seen.push(p.done))).toBe(SHA);
    expect(seen.at(-1)).toBe(DATA.length);
  });

  test('findLocalFile: same name and size, two levels deep', () => {
    const root = join(dir, 'models');
    mkdirSync(join(root, 'a', 'b'), { recursive: true });
    mkdirSync(join(root, 'a', 'b', 'c'), { recursive: true });
    writeFileSync(join(root, 'a', 'b', 'm.gguf'), 'x'.repeat(10));
    writeFileSync(join(root, 'a', 'b', 'c', 'deep.gguf'), 'x'.repeat(10));
    expect(findLocalFile('m.gguf', 10, [root])).toBe(join(root, 'a', 'b', 'm.gguf'));
    expect(findLocalFile('m.gguf', 11, [root])).toBeNull();
    expect(findLocalFile('deep.gguf', 10, [root])).toBeNull();
  });
});
