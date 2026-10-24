import { describe, expect, test } from 'bun:test';
import { join } from 'node:path';
import { buildHw, type RawScan } from '../src/server/hw/index.ts';
import { backendsFor, gfxFromTargetVersion, parseNvidiaSmi } from '../src/server/hw/common.ts';
import { lspciName, parseCpuinfo, parseKfdNode, slotToLocation, type LinuxRaw } from '../src/server/hw/linux.ts';
import { parseWindowsProbe } from '../src/server/hw/windows.ts';
import { appleGpuBudgetBytes, parseSysctl } from '../src/server/hw/macos.ts';

const FIX = join(import.meta.dir, 'fixtures', 'hw');
const host = { cpuName: 'host', threads: 16, ramBytes: 1, diskFreeGiB: 100, arch: 'x64' as const };

async function json<T>(name: string): Promise<T> {
  return (await Bun.file(join(FIX, name)).json()) as T;
}

describe('linux (recorded on our Ryzen 7 5700X + RX 7900 XTX)', () => {
  test('full scan', async () => {
    const raw = await json<LinuxRaw>('linux-ryzen5700x-rx7900xtx.json');
    const hw = buildHw({ os: 'linux', raw }, host, 1);
    expect(hw.cpu).toEqual({ name: 'AMD Ryzen 7 5700X 8-Core Processor', cores: 8, threads: 16 });
    expect(hw.ramGiB).toBeGreaterThan(60);
    expect(hw.gpus).toEqual([{
      vendor: 'amd', name: 'AMD Radeon RX 7900 XTX', vramGiB: 24, unified: false, backends: ['rocm', 'vulkan'],
      arch: 'gfx1100', driver: 'amdgpu',
    }]);
  });

  test('kfd + pci helpers', () => {
    expect(gfxFromTargetVersion(110000)).toBe('gfx1100');
    expect(gfxFromTargetVersion(90010)).toBe('gfx90a');
    expect(gfxFromTargetVersion(120001)).toBe('gfx1201');
    expect(gfxFromTargetVersion(0)).toBeUndefined();
    expect(slotToLocation('0000:2d:00.0')).toEqual({ domain: 0, locationId: 11520 });
    expect(parseKfdNode('cpu_cores_count 16\ngfx_target_version 0\n')).toBeNull();
    expect(parseKfdNode('gfx_target_version 110000\nlocation_id 11520\ndomain 0\n')).toEqual({ locationId: 11520, domain: 0, gfx: 'gfx1100' });
  });

  test('lspci names', () => {
    const l = '0000:01:00.0 VGA compatible controller [0300]: NVIDIA Corporation GA102 [GeForce RTX 3090] [10de:2204] (rev a1)';
    expect(lspciName(l, '0000:01:00.0')).toBe('GeForce RTX 3090');
    const a = '0000:2d:00.0 VGA compatible controller [0300]: Advanced Micro Devices, Inc. [AMD/ATI] Navi 31 [Radeon RX 7900 XT/7900 XTX/7900M] [1002:744c] (rev c8)';
    expect(lspciName(a, '0000:2d:00.0')).toBe('Radeon RX 7900 XT/7900 XTX/7900M');
    expect(lspciName(a, '0000:2e:00.0')).toBeNull();
  });

  test('nvidia + intel iGPU', async () => {
    const raw = await json<LinuxRaw>('linux-rtx3090-sample.json');
    const hw = buildHw({ os: 'linux', raw }, host, 1);
    expect(hw.cpu).toEqual({ name: 'Intel(R) Core(TM) i9-10900K CPU @ 3.70GHz', cores: 2, threads: 4 });
    expect(hw.gpus[0]).toEqual({
      vendor: 'nvidia', name: 'NVIDIA GeForce RTX 3090', vramGiB: 24, unified: false, backends: ['cuda', 'vulkan'],
      arch: 'sm_86', driver: '580.95.05',
    });
    expect(hw.gpus[1]).toMatchObject({ vendor: 'intel', name: 'Intel UHD Graphics 630', unified: true, vramGiB: 0, backends: ['vulkan'] });
  });

  test('cpuinfo without core ids falls back to threads', () => {
    expect(parseCpuinfo('processor : 0\nmodel name : X\nprocessor : 1\n')).toEqual({ name: 'X', cores: 2, threads: 2 });
  });

  test('nvidia-smi parser', () => {
    expect(parseNvidiaSmi('NVIDIA GeForce RTX 4090, 24564, 580.82.07, 8.9\nNVIDIA RTX A6000, 49140, 580.82.07, 8.6\n')).toEqual([
      { name: 'NVIDIA GeForce RTX 4090', vramMiB: 24564, driver: '580.82.07', arch: 'sm_89' },
      { name: 'NVIDIA RTX A6000', vramMiB: 49140, driver: '580.82.07', arch: 'sm_86' },
    ]);
  });
});

describe('windows (scan.ps1 logic)', () => {
  test('AMD with qwMemorySize, basic display adapter skipped', async () => {
    const raw = parseWindowsProbe(await Bun.file(join(FIX, 'windows-rx7900xtx-sample.json')).text(), null);
    const hw = buildHw({ os: 'windows', raw } satisfies RawScan, host, 1);
    expect(hw.os).toBe('windows');
    expect(hw.cpu).toEqual({ name: 'AMD Ryzen 7 5700X 8-Core Processor', cores: 8, threads: 16 });
    expect(hw.ramGiB).toBe(63.9);
    expect(hw.gpus).toEqual([{
      vendor: 'amd', name: 'AMD Radeon RX 7900 XTX', vramGiB: 24, unified: false, backends: ['vulkan', 'rocm'],
      arch: 'gfx1100', driver: '25.10.2',
    }]);
  });

  test('NVIDIA dGPU + Intel iGPU, nvidia-smi preferred', async () => {
    const raw = parseWindowsProbe(await Bun.file(join(FIX, 'windows-rtx4090-igpu-sample.json')).text(), 'NVIDIA GeForce RTX 4090, 24564, 581.57, 8.9\n');
    const hw = buildHw({ os: 'windows', raw }, host, 1);
    expect(hw.gpus[0]).toEqual({
      vendor: 'nvidia', name: 'NVIDIA GeForce RTX 4090', vramGiB: 24, unified: false, backends: ['cuda', 'vulkan'],
      arch: 'sm_89', driver: '581.57',
    });
    expect(hw.gpus[1]).toMatchObject({ vendor: 'intel', unified: true, vramGiB: 0 });
  });

  test('AMD Windows without a HIP arch gets vulkan only', () => {
    expect(backendsFor('amd', 'windows', { driver: true, arch: 'gfx1031' })).toEqual(['vulkan']);
    expect(backendsFor('amd', 'windows', { driver: true })).toEqual(['vulkan']);
  });
});

describe('macos', () => {
  test('Apple Silicon unified memory', async () => {
    const raw = parseSysctl(await Bun.file(join(FIX, 'macos-m3max-sample.txt')).text());
    const hw = buildHw({ os: 'macos', raw }, { ...host, arch: 'arm64' }, 1);
    expect(hw.cpu).toEqual({ name: 'Apple M3 Max', cores: 16, threads: 16 });
    expect(hw.ramGiB).toBe(64);
    expect(hw.gpus).toEqual([{ vendor: 'apple', name: 'Apple M3 Max', vramGiB: 48, unified: true, backends: ['metal'], arch: 'apple-m3' }]);
  });

  test('working-set budget', () => {
    expect(appleGpuBudgetBytes(16 * 1024 ** 3, 0)).toBeCloseTo((16 * 1024 ** 3 * 2) / 3);
    expect(appleGpuBudgetBytes(64 * 1024 ** 3, 57344)).toBe(57344 * 1024 * 1024);
  });

  test('Intel Mac has no GPU backend', () => {
    const hw = buildHw({ os: 'macos', raw: { 'hw.optional.arm64': '0', 'hw.memsize': String(16 * 1024 ** 3) } }, host, 1);
    expect(hw.gpus).toEqual([]);
  });
});
