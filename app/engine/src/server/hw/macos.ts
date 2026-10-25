// macOS hardware detection: sysctl. Apple Silicon GPUs share unified memory with the CPU.
import type { Gpu } from '../../shared/types.ts';
import { backendsFor, GIB, toGiB } from './common.ts';
import { runText } from './run.ts';

export const MACOS_SYSCTL_KEYS = [
  'machdep.cpu.brand_string', 'hw.memsize', 'hw.physicalcpu', 'hw.logicalcpu', 'hw.optional.arm64', 'iogpu.wired_limit_mb',
] as const;

/** `sysctl key …` output ("key: value" lines) -> map. Missing keys are simply absent. */
export function parseSysctl(text: string): Record<string, string> {
  const out: Record<string, string> = {};
  for (const line of text.split('\n')) {
    const i = line.indexOf(':');
    if (i <= 0) continue;
    out[line.slice(0, i).trim()] = line.slice(i + 1).trim();
  }
  return out;
}

/**
 * GPU working set Metal allows by default: 2/3 of RAM up to 36 GiB, 3/4 above; `iogpu.wired_limit_mb` > 0 overrides.
 */
export function appleGpuBudgetBytes(memBytes: number, wiredLimitMb: number): number {
  if (wiredLimitMb > 0) return wiredLimitMb * 1024 * 1024;
  return memBytes <= 36 * GIB ? (memBytes * 2) / 3 : (memBytes * 3) / 4;
}

export function buildMacGpus(sysctl: Record<string, string>): Gpu[] {
  if (sysctl['hw.optional.arm64'] !== '1') return []; // Intel Macs: no Metal path in our engines, CPU only
  const mem = Number(sysctl['hw.memsize'] ?? 0);
  const brand = sysctl['machdep.cpu.brand_string'] ?? 'Apple Silicon';
  const chip = /Apple (M\d+)/.exec(brand)?.[1];
  const g: Gpu = {
    vendor: 'apple', name: brand, kind: 'apple',
    vramGiB: toGiB(appleGpuBudgetBytes(mem, Number(sysctl['iogpu.wired_limit_mb'] ?? 0))),
    backends: backendsFor('apple', 'macos', { driver: true }),
  };
  if (chip) g.arch = `apple-${chip.toLowerCase()}`;
  return [g];
}

export async function collectSysctl(): Promise<Record<string, string>> {
  const out: Record<string, string> = {};
  // one key per call: sysctl stops at the first unknown key on some macOS versions
  for (const key of MACOS_SYSCTL_KEYS) {
    const v = await runText(['sysctl', '-n', key]);
    if (v !== null) out[key] = v.trim();
  }
  return out;
}
