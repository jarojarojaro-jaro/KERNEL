// Hardware scan entry point: dispatches per OS and assembles the shared `Hw`.
import { cpus, totalmem, availableParallelism } from 'node:os';
import { statfsSync, existsSync } from 'node:fs';
import { dirname } from 'node:path';
import type { Hw, Gpu, RamInfo } from '../../shared/types.ts';
import { sortGpus, toGiB } from './common.ts';
import { buildLinuxGpus, buildLinuxRam, collectLinuxRaw, parseCpuinfo, type LinuxRaw } from './linux.ts';
import { buildWindowsGpus, buildWindowsRam, collectWindowsRaw, type WindowsRaw } from './windows.ts';
import { buildMacGpus, collectSysctl } from './macos.ts';
import { defaultRam } from './ram.ts';
import { devCpu, paths } from '../paths.ts';

export function hostOs(): Hw['os'] {
  return process.platform === 'win32' ? 'windows' : process.platform === 'darwin' ? 'macos' : 'linux';
}

export function hostArch(): Hw['arch'] {
  return process.arch === 'arm64' ? 'arm64' : 'x64';
}

/** Free space (GiB) on the filesystem holding `dir` (nearest existing ancestor). */
export function diskFreeGiB(dir: string): number {
  let d = dir;
  while (!existsSync(d) && dirname(d) !== d) d = dirname(d);
  const s = statfsSync(d);
  return toGiB(Number(s.bavail) * Number(s.bsize));
}

export type RawScan = { os: 'linux'; raw: LinuxRaw } | { os: 'windows'; raw: WindowsRaw } | { os: 'macos'; raw: Record<string, string> };

export async function collectRaw(): Promise<RawScan> {
  const os = hostOs();
  if (os === 'linux') return { os, raw: await collectLinuxRaw(totalmem()) };
  if (os === 'windows') return { os, raw: await collectWindowsRaw() };
  return { os, raw: await collectSysctl() };
}

interface HostFacts { cpuName: string; threads: number; ramBytes: number; diskFreeGiB: number; arch: Hw['arch'] }

export function buildHw(scan: RawScan, host: HostFacts, now: number): Hw {
  let gpus: Gpu[] = [];
  let cpu = { name: host.cpuName, cores: host.threads, threads: host.threads };
  let ramBytes = host.ramBytes;
  let memory: RamInfo | null = null;
  if (scan.os === 'linux') {
    gpus = buildLinuxGpus(scan.raw);
    const c = parseCpuinfo(scan.raw.cpuinfo);
    cpu = { name: c.name, cores: c.cores, threads: c.threads || host.threads };
    ramBytes = scan.raw.memTotalBytes;
    memory = buildLinuxRam(scan.raw, toGiB(ramBytes));
  } else if (scan.os === 'windows') {
    gpus = buildWindowsGpus(scan.raw);
    const c0 = scan.raw.cpu[0];
    if (c0) {
      cpu = {
        name: c0.Name.replace(/\s+/g, ' ').trim(),
        cores: scan.raw.cpu.reduce((s, c) => s + (c.NumberOfCores || 0), 0) || host.threads,
        threads: scan.raw.cpu.reduce((s, c) => s + (c.NumberOfLogicalProcessors || 0), 0) || host.threads,
      };
    }
    if (scan.raw.os?.TotalVisibleMemorySize) ramBytes = scan.raw.os.TotalVisibleMemorySize * 1024;
    memory = buildWindowsRam(scan.raw, toGiB(ramBytes));
  } else {
    gpus = buildMacGpus(scan.raw);
    cpu = {
      name: scan.raw['machdep.cpu.brand_string'] ?? host.cpuName,
      cores: Number(scan.raw['hw.physicalcpu'] ?? host.threads),
      threads: Number(scan.raw['hw.logicalcpu'] ?? host.threads),
    };
    if (scan.raw['hw.memsize']) ramBytes = Number(scan.raw['hw.memsize']);
  }
  const ramGiB = toGiB(ramBytes);
  return {
    os: scan.os, arch: host.arch, cpu, ramGiB, memory: memory ?? defaultRam(ramGiB, cpu.name), gpus: sortGpus(gpus),
    diskFreeGiB: host.diskFreeGiB, scannedAt: now,
  };
}

/**
 * Scans this machine. ENIGMA_DEV_CPU=1 keeps the real CPU/RAM/disk but plans without GPUs (gpus=[]),
 * the CPU-only dev path.
 */
export async function scanHw(): Promise<Hw> {
  const scan = await collectRaw();
  const c = cpus();
  const hw = buildHw(scan, {
    cpuName: c[0]?.model.trim() ?? 'unknown CPU', threads: c.length || availableParallelism(), ramBytes: totalmem(),
    diskFreeGiB: diskFreeGiB(paths().models), arch: hostArch(),
  }, Date.now());
  if (devCpu()) hw.gpus = [];
  return hw;
}
