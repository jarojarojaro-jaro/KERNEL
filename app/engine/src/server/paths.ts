// Data directory layout (CONTRACT.md "Katalog domowy i nadpisania").
import { homedir } from 'node:os';
import { join } from 'node:path';
import { mkdirSync } from 'node:fs';

export function expandHome(p: string): string {
  if (p === '~') return homedir();
  if (p.startsWith('~/') || p.startsWith('~\\')) return join(homedir(), p.slice(2));
  return p;
}

export function enigmaHome(): string {
  const override = process.env.ENIGMA_HOME;
  if (override) return expandHome(override);
  if (process.platform === 'win32') {
    const local = process.env.LOCALAPPDATA ?? join(homedir(), 'AppData', 'Local');
    return join(local, 'Enigma');
  }
  return join(homedir(), '.enigma');
}

export interface Paths {
  home: string; config: string; state: string; models: string; engines: string; logs: string; results: string;
  downloads: string;
}

export function paths(): Paths {
  const home = enigmaHome();
  return {
    home,
    config: join(home, 'config.json'),
    state: join(home, 'state.json'),
    models: join(home, 'models'),
    engines: join(home, 'engines'),
    logs: join(home, 'logs'),
    results: join(home, 'results'),
    downloads: join(home, 'downloads'),
  };
}

export function ensureDirs(p: Paths = paths()): Paths {
  for (const d of [p.home, p.models, p.engines, p.logs, p.results, p.downloads]) mkdirSync(d, { recursive: true });
  return p;
}

/** Extra directory with ready GGUF files (ENIGMA_MODELS_DIR), or null. */
export function extraModelsDir(): string | null {
  const v = process.env.ENIGMA_MODELS_DIR;
  return v ? expandHome(v) : null;
}

/** ENIGMA_DEV_CPU=1: plan for CPU only (gpus=[]), use the CPU engine. */
export function devCpu(): boolean {
  return process.env.ENIGMA_DEV_CPU === '1';
}

export const DEFAULT_PORT = 11525;
/** How many ports after the preferred one are tried when it is taken. */
export const PORT_FALLBACKS = 20;

/** Preferred UI/API port (ENIGMA_PORT, default 11525; 11500 is used by omp). */
export function uiPort(): number {
  const v = Number(process.env.ENIGMA_PORT ?? DEFAULT_PORT);
  return Number.isInteger(v) && v > 0 && v < 65536 ? v : DEFAULT_PORT;
}
