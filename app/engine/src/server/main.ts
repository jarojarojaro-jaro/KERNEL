// CLI entry:
//   enigma                         UI + API on 127.0.0.1:ENIGMA_PORT, opens the browser (unless ENIGMA_NO_BROWSER=1)
//   enigma run --headless --license-file F [--model auto|<optionId>] [--min-ctx 131072] [--exit-when-ready]
//   enigma license (--key K | --file F)
//   enigma scan [--raw]
import { readFileSync } from 'node:fs';
import { parseArgs } from 'node:util';
import type { BenchResult } from '../shared/types.ts';
import { serveApi } from './api.ts';
import { collectRaw, scanHw } from './hw/index.ts';
import { verifyLicense, storeLicenseKey } from './license.ts';
import { errMsg, onLog } from './log.ts';
import { enigmaHome, uiPort } from './paths.ts';
import { App, DEFAULT_MIN_CTX, VERSION } from './state.ts';

const HELP = `Enigma ${VERSION} — local LLM inference, tuned for your hardware.

Usage:
  enigma                          start the app (UI in the browser, API on 127.0.0.1:${uiPort()})
  enigma run --headless --license-file FILE [--model auto|OPTION_ID] [--min-ctx N] [--exit-when-ready]
                                  run license → scan → recommend → download → baseline → optimize → ready
                                  without the UI, printing progress; exits 0 when ready (with --exit-when-ready)
  enigma license --key KEY | --file FILE
                                  verify and store a subscription key
  enigma scan [--raw]             print the hardware scan (--raw: what the scan read)
  enigma --help | --version

Environment:
  ENIGMA_HOME                data directory (default ~/.enigma, Windows %LOCALAPPDATA%\\Enigma): ${enigmaHome()}
  ENIGMA_PORT                UI/API port (default 11525; when taken, the next 20 ports are tried)
  ENIGMA_NO_BROWSER=1        do not open the browser
  ENIGMA_MODELS_DIR          extra directory with ready GGUF files (same name and size = no download)
  ENIGMA_ENGINE_DIR_<KEY>    local engine directory instead of downloading (e.g. ENIGMA_ENGINE_DIR_UPSTREAM_CPU,
                             ENIGMA_ENGINE_DIR_UPSTREAM_ROCM, ENIGMA_ENGINE_DIR_ENIGMA_ROCM)
  ENIGMA_DEV_CPU=1           plan for CPU only (ignore GPUs)
  ENIGMA_BENCH_PREFILL / _DECODE / _DEEP / _REPS   benchmark sizes (default 4096 / 256 / 32768 / 2)
  HF_ENDPOINT                Hugging Face mirror (default https://huggingface.co)
`;

function openBrowser(url: string): void {
  const cmd = process.platform === 'win32' ? ['cmd', '/c', 'start', '', url] : process.platform === 'darwin' ? ['open', url] : ['xdg-open', url];
  try {
    Bun.spawn(cmd, { stdout: 'ignore', stderr: 'ignore', stdin: 'ignore' }).unref();
  } catch {
    console.log(`Open ${url} in your browser.`);
  }
}

function installSignals(app: App): void {
  let stopping = false;
  const stop = (): void => {
    if (stopping) return;
    stopping = true;
    console.error('\nstopping (waiting for the model server to finish)…');
    app.shutdown().finally(() => process.exit(0));
  };
  process.on('SIGINT', stop);
  process.on('SIGTERM', stop);
}

const ts = (): string => new Date().toTimeString().slice(0, 8);

function fmtRate(bytesPerS: number): string {
  return bytesPerS > 1024 ** 2 ? `${(bytesPerS / 1024 ** 2).toFixed(1)} MiB/s` : `${(bytesPerS / 1024).toFixed(0)} KiB/s`;
}

function gain(now: number, base: number): string {
  if (base <= 0) return '';
  const g = (now / base - 1) * 100;
  return `${g >= 0 ? '+' : ''}${g.toFixed(1)}%`;
}

function summary(base: BenchResult, best: BenchResult): string {
  const row = (name: string, b: number, n: number): string =>
    `  ${name.padEnd(16)} ${b.toFixed(1).padStart(9)} → ${n.toFixed(1).padStart(9)} t/s  ${gain(n, b)}`;
  const lines = [
    `results (baseline ${base.engine.id} ${base.engine.version} → now ${best.engine.id} ${best.engine.version}):`,
    row('prefill', base.prefill.tps, best.prefill.tps),
    row('decode', base.decode.tps, best.decode.tps),
  ];
  if (base.deep && best.deep) {
    lines.push(row(`deep prefill ${Math.round(base.deep.ctxTokens / 1024)}k`, base.deep.prefillTps, best.deep.prefillTps));
    lines.push(row(`deep decode`, base.deep.decodeTps, best.deep.decodeTps));
  }
  lines.push(`  context          ${best.config.ctx} tokens (fits: ${best.ctxOk}), same output as baseline: ${best.outputMd5 === base.outputMd5}`);
  return lines.join('\n');
}

async function runHeadless(argv: string[]): Promise<number> {
  const { values } = parseArgs({
    args: argv,
    options: {
      headless: { type: 'boolean', default: false },
      'license-file': { type: 'string' },
      model: { type: 'string', default: 'auto' },
      'min-ctx': { type: 'string', default: String(DEFAULT_MIN_CTX) },
      'exit-when-ready': { type: 'boolean', default: false },
    },
  });
  if (!values.headless) {
    console.error('enigma run needs --headless (the UI runs with plain `enigma`)');
    return 2;
  }
  const minCtx = Number(values['min-ctx']);
  if (!Number.isInteger(minCtx) || minCtx <= 0) {
    console.error('--min-ctx must be a positive integer');
    return 2;
  }
  onLog((l) => console.log(`[${ts()}] ${l.level === 'info' ? '' : l.level.toUpperCase() + ' '}${l.msg}`));
  const app = new App();
  installSignals(app);
  let lastKey = '';
  let lastT = 0;
  app.onProgress((p) => {
    const now = Date.now();
    const key = `${p.phase}/${p.label}`;
    const finished = p.total > 0 && p.done >= p.total;
    if (key === lastKey && !finished && now - lastT < 2000) return;
    lastKey = key;
    lastT = now;
    const pct = p.total > 0 ? ` ${((p.done / p.total) * 100).toFixed(1)}%` : '';
    const rate = p.rate ? ` ${fmtRate(p.rate)}` : '';
    const eta = p.etaS ? ` ETA ${Math.round(p.etaS)} s` : '';
    console.log(`[${ts()}] progress ${p.phase} ${p.label}${pct} (${p.done}/${p.total})${rate}${eta}`);
  });
  const server = serveApi(app, uiPort());
  console.log(`[${ts()}] Enigma ${VERSION} API on http://127.0.0.1:${server.port} (data ${enigmaHome()})`);

  if (!values['license-file']) {
    console.error('--license-file is required');
    return 2;
  }
  const lic = await app.setLicense(readFileSync(values['license-file'], 'utf8'));
  if (!lic.valid) {
    console.error(`license invalid: ${lic.reason}`);
    return 3;
  }
  if (!app.state.hw) await app.scan();
  const rec = app.state.recommendation?.minCtx === minCtx ? app.state.recommendation : await app.recommend(minCtx);
  const options = [rec.pick, ...rec.alternatives].filter((o) => o !== null);
  for (const o of options) {
    console.log(`[${ts()}]   option ${o.id}: ${o.name} ${o.quant} ctx ${o.ctx} KV ${o.kvType} ${o.backend} ${o.mem.totalGiB}/${o.mem.budgetGiB} GiB score ${o.score}`);
  }
  for (const r of rec.rejected.slice(0, 12)) console.log(`[${ts()}]   rejected ${r.modelId} ${r.quant}: ${r.reason}`);
  const option = values.model === 'auto' ? rec.pick : options.find((o) => o.id === values.model) ?? null;
  if (!option) {
    console.error(values.model === 'auto' ? `nothing fits with ctx >= ${minCtx}` : `option ${values.model} not among the recommendations`);
    return 4;
  }
  console.log(`[${ts()}] chosen: ${option.id} (${option.name} ${option.quant}, ctx ${option.ctx})`);
  await app.start(option.id);
  await app.settled();
  if (app.state.phase !== 'ready' || !app.state.ready) {
    console.error(`failed in phase ${app.state.error?.phase ?? app.state.phase}: ${app.state.error?.message ?? 'unknown'}`);
    await app.shutdown();
    return 1;
  }
  if (app.state.baseline && app.state.best) console.log(summary(app.state.baseline, app.state.best));
  for (const c of app.state.candidates) {
    const r = c.result;
    console.log(`  candidate ${c.id.padEnd(8)} ${c.status.padEnd(8)}` +
      (r ? ` decode ${r.decode.tps.toFixed(1)} t/s (${c.decodePct}%), prefill ${r.prefill.tps.toFixed(1)} t/s (${c.prefillPct}%), same output ${c.sameOutput}` : '') +
      (c.reason ? ` — ${c.reason}` : ''));
  }
  // readiness check through our own proxy, as a client would call it
  const endpoint = app.state.ready.endpoint;
  const t0 = performance.now();
  const res = await fetch(`${endpoint}/chat/completions`, {
    method: 'POST', headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ messages: [{ role: 'user', content: 'Reply with one word: ready' }], max_tokens: 64, temperature: 0 }),
  });
  type Reply = { choices?: { message?: { content?: string; reasoning_content?: string } }[] };
  const reply = (await res.json()) as Reply;
  const msg = reply.choices?.[0]?.message;
  // reasoning models may spend the whole budget thinking: show that text, labelled
  const text = msg?.content?.trim() || (msg?.reasoning_content ? `(reasoning) ${msg.reasoning_content.trim()}` : JSON.stringify(reply));
  console.log(`[${ts()}] ready: ${endpoint} (model ${app.state.ready.model}, ctx ${app.state.ready.ctx}); ` +
    `POST /v1/chat/completions → HTTP ${res.status} in ${((performance.now() - t0) / 1000).toFixed(1)} s: ${JSON.stringify(text.slice(0, 120))}`);
  if (!res.ok) {
    await app.shutdown();
    return 1;
  }
  if (values['exit-when-ready']) {
    await app.shutdown();
    server.stop(true);
    return 0;
  }
  console.log(`[${ts()}] serving; Ctrl-C stops`);
  await new Promise<never>(() => {});
  return 0;
}

async function runApp(): Promise<number> {
  const app = new App();
  installSignals(app);
  const server = serveApi(app, uiPort());
  const url = `http://127.0.0.1:${server.port}/`;
  console.log(`Enigma ${VERSION}: ${url} (data ${enigmaHome()})`);
  app.resume();
  if (process.env.ENIGMA_NO_BROWSER !== '1') openBrowser(url);
  await new Promise<never>(() => {});
  return 0;
}

function runLicense(argv: string[]): number {
  const { values } = parseArgs({ args: argv, options: { key: { type: 'string' }, file: { type: 'string' } } });
  const key = values.key ?? (values.file ? readFileSync(values.file, 'utf8') : '');
  if (!key) {
    console.error('enigma license --key KEY | --file FILE');
    return 2;
  }
  const info = verifyLicense(key);
  console.log(JSON.stringify(info, null, 2));
  if (!info.valid) return 3;
  storeLicenseKey(key);
  return 0;
}

async function runScan(argv: string[]): Promise<number> {
  const { values } = parseArgs({ args: argv, options: { raw: { type: 'boolean', default: false } } });
  if (values.raw) console.log(JSON.stringify(await collectRaw(), null, 1));
  else console.log(JSON.stringify(await scanHw(), null, 1));
  return 0;
}

export async function main(argv: string[]): Promise<number> {
  const [cmd, ...rest] = argv;
  try {
    switch (cmd) {
      case undefined:
        return await runApp();
      case 'run':
        return await runHeadless(rest);
      case 'license':
        return runLicense(rest);
      case 'scan':
        return await runScan(rest);
      case '--version':
      case '-v':
        console.log(VERSION);
        return 0;
      case '--help':
      case '-h':
      case 'help':
        console.log(HELP);
        return 0;
      default:
        console.error(`unknown command: ${cmd}\n\n${HELP}`);
        return 2;
    }
  } catch (e) {
    console.error(`error: ${errMsg(e)}`);
    return 1;
  }
}

if (import.meta.main) process.exit(await main(process.argv.slice(2)));
