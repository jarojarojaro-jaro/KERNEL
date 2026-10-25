// Typical machines for recommender tests (shapes as src/server/hw scans would report them); machines without a discrete
// GPU come from recorded raw scans through the real scan code (`buildHw`).
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import type { Backend, Gpu, Hw, RamInfo } from '../src/shared/types.ts';
import { buildHw } from '../src/server/hw/index.ts';
import { parseWindowsProbe } from '../src/server/hw/windows.ts';
import type { LinuxRaw } from '../src/server/hw/linux.ts';

const cpu = { name: 'AMD Ryzen 7 5700X', cores: 8, threads: 16 };

function gpu(vendor: Gpu['vendor'], name: string, vramGiB: number, backends: Backend[], arch?: string): Gpu {
  return { vendor, name, kind: 'discrete', vramGiB, backends, ...(arch ? { arch } : {}) };
}

function pc(os: Hw['os'], ramGiB: number, gpus: Gpu[]): Hw {
  const memory: RamInfo = { totalGiB: ramGiB, type: 'DDR4', speedMTs: 3200, channels: 2, modules: 2, bandwidthGBs: 51.2, source: 'detected' };
  return { os, arch: 'x64', cpu, ramGiB, memory, gpus, diskFreeGiB: 500, scannedAt: 0 };
}

const nv = (name: string, vram: number, arch: string): Gpu => gpu('nvidia', name, vram, ['cuda', 'vulkan'], arch);
const amd = (name: string, vram: number, arch: string): Gpu => gpu('amd', name, vram, ['rocm', 'vulkan'], arch);

function mac(chip: string, ramGiB: number): Hw {
  return {
    os: 'macos', arch: 'arm64', cpu: { name: chip, cores: 12, threads: 12 }, ramGiB,
    memory: { totalGiB: ramGiB, type: 'LPDDR5', bandwidthGBs: 273, source: 'default' },
    gpus: [{ vendor: 'apple', name: chip, kind: 'apple', vramGiB: ramGiB, backends: ['metal'] }], diskFreeGiB: 500, scannedAt: 0,
  };
}

const FIX = join(import.meta.dir, 'fixtures', 'hw');
const host = { cpuName: 'host', threads: 16, ramBytes: 1, diskFreeGiB: 500, arch: 'x64' as const };

/** A recorded Windows probe (test/fixtures/hw) through the real scan code. */
export function windowsScan(file: string): Hw {
  return buildHw({ os: 'windows', raw: parseWindowsProbe(readFileSync(join(FIX, file), 'utf8'), null) }, host, 0);
}

export function linuxScan(file: string): Hw {
  return buildHw({ os: 'linux', raw: JSON.parse(readFileSync(join(FIX, file), 'utf8')) as LinuxRaw }, host, 0);
}

/** Machines without a discrete GPU (integrated graphics or none): RAM-bound. */
export const RAM_MACHINES: Record<string, Hw> = {
  'APU Ryzen 7 5700G, Radeon(TM) Graphics 1 GB, 31 GB DDR4-3200 (user report)': windowsScan('windows-apu-r7-5700g-ddr4.json'),
  'APU Ryzen 5 8600G, Radeon 760M, 32 GB DDR5-5600': windowsScan('windows-apu-r5-8600g-ddr5.json'),
  'Laptop i7-1165G7, Iris Xe, 16 GB DDR4-3200': windowsScan('windows-laptop-irisxe-16gb.json'),
  'Desktop i9-13900KF without GPU, 64 GB DDR5-5600': windowsScan('windows-cpu-only-64gb-ddr5.json'),
  'Linux APU Ryzen 7 7840HS, Radeon 780M, 32 GB DDR5-5600': linuxScan('linux-apu-780m-32gb.json'),
};

export const MACHINES: Record<string, Hw> = {
  'RTX 4060 8 GB': pc('windows', 32, [nv('NVIDIA GeForce RTX 4060', 8, 'sm_89')]),
  'RTX 3060 12 GB': pc('linux', 32, [nv('NVIDIA GeForce RTX 3060', 12, 'sm_86')]),
  'RTX 4060 Ti 16 GB': pc('windows', 32, [nv('NVIDIA GeForce RTX 4060 Ti', 16, 'sm_89')]),
  'RTX 5060 Ti 16 GB': pc('linux', 32, [nv('NVIDIA GeForce RTX 5060 Ti', 16, 'sm_120')]),
  'RX 7800 XT 16 GB': pc('linux', 32, [amd('AMD Radeon RX 7800 XT', 16, 'gfx1101')]),
  'RX 7900 XTX 24 GB': pc('linux', 62, [amd('AMD Radeon RX 7900 XTX', 24, 'gfx1100')]),
  'RTX 3090 24 GB': pc('linux', 64, [nv('NVIDIA GeForce RTX 3090', 24, 'sm_86')]),
  'RTX 4090 24 GB': pc('windows', 64, [nv('NVIDIA GeForce RTX 4090', 24, 'sm_89')]),
  'RTX 5090 32 GB': pc('linux', 64, [nv('NVIDIA GeForce RTX 5090', 32, 'sm_120')]),
  'Mac M4 Pro 24 GB': mac('Apple M4 Pro', 24),
  'Mac M4 Pro 48 GB': mac('Apple M4 Pro', 48),
  'CPU only 32 GB': pc('linux', 32, []),
  ...RAM_MACHINES,
};
