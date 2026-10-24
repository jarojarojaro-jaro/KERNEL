// Typical machines for recommender tests (shapes as src/server/hw scans would report them).
import type { Backend, Gpu, Hw } from '../src/shared/types.ts';

const cpu = { name: 'AMD Ryzen 7 5700X', cores: 8, threads: 16 };

function gpu(vendor: Gpu['vendor'], name: string, vramGiB: number, backends: Backend[], arch?: string): Gpu {
  return { vendor, name, vramGiB, unified: false, backends, ...(arch ? { arch } : {}) };
}

function pc(os: Hw['os'], ramGiB: number, gpus: Gpu[]): Hw {
  return { os, arch: 'x64', cpu, ramGiB, gpus, diskFreeGiB: 500, scannedAt: 0 };
}

const nv = (name: string, vram: number, arch: string): Gpu => gpu('nvidia', name, vram, ['cuda', 'vulkan'], arch);
const amd = (name: string, vram: number, arch: string): Gpu => gpu('amd', name, vram, ['rocm', 'vulkan'], arch);

function mac(chip: string, ramGiB: number): Hw {
  return {
    os: 'macos', arch: 'arm64', cpu: { name: chip, cores: 12, threads: 12 }, ramGiB,
    gpus: [{ vendor: 'apple', name: chip, vramGiB: ramGiB, unified: true, backends: ['metal'] }], diskFreeGiB: 500, scannedAt: 0,
  };
}

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
};
