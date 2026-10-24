// Worker: sha256 of a file with progress messages, so hashing a 20 GB model never blocks the API thread.
// in:  { path: string }
// out: { type: 'progress', done, total } … then { type: 'done', sha256 } or { type: 'error', message }
import { statSync } from 'node:fs';

declare const self: Worker;

interface HashRequest { path: string }

self.onmessage = async (ev: MessageEvent<HashRequest>) => {
  const { path } = ev.data;
  try {
    const total = statSync(path).size;
    const hasher = new Bun.CryptoHasher('sha256');
    let done = 0;
    let last = 0;
    for await (const chunk of Bun.file(path).stream()) {
      hasher.update(chunk);
      done += chunk.byteLength;
      const now = performance.now();
      if (now - last > 200) {
        last = now;
        postMessage({ type: 'progress', done, total });
      }
    }
    postMessage({ type: 'progress', done, total });
    postMessage({ type: 'done', sha256: hasher.digest('hex') });
  } catch (e) {
    postMessage({ type: 'error', message: e instanceof Error ? e.message : String(e) });
  }
};
