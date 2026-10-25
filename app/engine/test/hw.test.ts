import { describe, expect, test } from 'bun:test';
import { join } from 'node:path';
import { buildHw, type RawScan } from '../src/server/hw/index.ts';
import { amdIsIntegrated, backendsFor, gfxFromTargetVersion, parseNvidiaSmi } from '../src/server/hw/common.ts';
import { lspciName, parseCpuinfo, parseKfdNode, parseUdevDmiMemory, slotToLocation, type LinuxRaw } from '../src/server/hw/linux.ts';
import { buildWindowsRam, parseWindowsProbe, type WinMemModule } from '../src/server/hw/windows.ts';
import { appleGpuBudgetBytes, parseSysctl } from '../src/server/hw/macos.ts';
import { defaultRam, ramFromModules } from '../src/server/hw/ram.ts';

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
      vendor: 'amd', name: 'AMD Radeon RX 7900 XTX', kind: 'discrete', vramGiB: 24, backends: ['rocm', 'vulkan'],
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
      vendor: 'nvidia', name: 'NVIDIA GeForce RTX 3090', kind: 'discrete', vramGiB: 24, backends: ['cuda', 'vulkan'],
      arch: 'sm_86', driver: '580.95.05',
    });
    expect(hw.gpus[1]).toMatchObject({ vendor: 'intel', name: 'Intel UHD Graphics 630', kind: 'integrated', vramGiB: 0, backends: ['vulkan'] });
  });

  test('cpuinfo without core ids falls back to threads', () => {
    expect(parseCpuinfo('processor : 0\nmodel name : X\nprocessor : 1\n')).toEqual({ name: 'X', cores: 2, threads: 2 });
  });

  test('container: sysfs shows 4 host boards, nvidia-smi only ours (recorded on a Vast RTX 3060 box)', () => {
    const board = (slot: string, device: string) => ({
      slot, vendor: '0x10de', device, revision: '0xa1', driver: null, vramTotal: null, gttTotal: null, intelVram: null, productName: null,
    });
    const raw: LinuxRaw = {
      cpuinfo: 'processor : 0\nmodel name : Xeon\n', memTotalBytes: 64822968320, kfdNodes: [], lspci: '',
      pci: [board('0000:02:00.0', '0x2504'), board('0000:03:00.0', '0x2487'), board('0000:81:00.0', '0x2504'), board('0000:82:00.0', '0x2487')],
      nvidiaSmi: 'NVIDIA GeForce RTX 3060, 12288, 570.133.07, 8.6, 00000000:81:00.0\n',
    };
    const hw = buildHw({ os: 'linux', raw }, host, 1);
    expect(hw.gpus).toEqual([{
      vendor: 'nvidia', name: 'NVIDIA GeForce RTX 3060', kind: 'discrete', vramGiB: 12, backends: ['cuda', 'vulkan'],
      arch: 'sm_86', driver: '570.133.07',
    }]);
    expect(hw.ramGiB).toBe(60.4);
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
      vendor: 'amd', name: 'AMD Radeon RX 7900 XTX', kind: 'discrete', vramGiB: 24, backends: ['vulkan', 'rocm'],
      arch: 'gfx1100', driver: '25.10.2',
    }]);
  });

  test('NVIDIA dGPU + Intel iGPU, nvidia-smi preferred', async () => {
    const raw = parseWindowsProbe(await Bun.file(join(FIX, 'windows-rtx4090-igpu-sample.json')).text(), 'NVIDIA GeForce RTX 4090, 24564, 581.57, 8.9\n');
    const hw = buildHw({ os: 'windows', raw }, host, 1);
    expect(hw.gpus[0]).toEqual({
      vendor: 'nvidia', name: 'NVIDIA GeForce RTX 4090', kind: 'discrete', vramGiB: 24, backends: ['cuda', 'vulkan'],
      arch: 'sm_89', driver: '581.57',
    });
    expect(hw.gpus[1]).toMatchObject({ vendor: 'intel', kind: 'integrated', vramGiB: 0, sharedGiB: 15.9 });
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
    expect(hw.gpus).toEqual([{ vendor: 'apple', name: 'Apple M3 Max', kind: 'apple', vramGiB: 48, backends: ['metal'], arch: 'apple-m3' }]);
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

describe('integrated graphics and RAM', () => {
  test('AMD iGPU by PCI id, by name, by a small carve-out; discrete names stay discrete', () => {
    expect(amdIsIntegrated('AMD Radeon(TM) Graphics', '0000', 1)).toBe(true); // the user's report: name only
    expect(amdIsIntegrated('AMD Radeon(TM) Graphics', '0000', 4)).toBe(true); // BIOS UMA set to 4 GB
    expect(amdIsIntegrated('AMD Radeon 780M Graphics', '0000', 0.5)).toBe(true);
    expect(amdIsIntegrated('AMD Radeon Vega 8 Graphics', '0000', 2)).toBe(true);
    expect(amdIsIntegrated('Phoenix1', '15bf', 2)).toBe(true);
    expect(amdIsIntegrated('PCI 1002:abcd', 'abcd', 0.5)).toBe(true);
    expect(amdIsIntegrated('AMD Radeon RX 7900 XTX', '744c', 24)).toBe(false);
    expect(amdIsIntegrated('AMD Radeon RX 6400', '743f', 4)).toBe(false);
    expect(amdIsIntegrated('PCI 1002:abcd', 'abcd', 16)).toBe(false);
  });

  test('Windows: SMBIOS type, clock reported as half the transfer rate, channels from locators or module count', () => {
    const mod = (speed: number, type: number, bank: string, loc: string): WinMemModule =>
      ({ Capacity: 16 * 2 ** 30, ConfiguredClockSpeed: speed, Speed: speed, SMBIOSMemoryType: type, DataWidth: 64, BankLabel: bank, DeviceLocator: loc });
    const raw = (mem: WinMemModule[]) => parseWindowsProbe(JSON.stringify({ cpu: [], vc: [], reg: [], mem }), null);
    expect(buildWindowsRam(raw([mod(1600, 26, 'BANK 0', 'DIMM_A1'), mod(1600, 26, 'BANK 1', 'DIMM_B1')]), 32))
      .toMatchObject({ type: 'DDR4', speedMTs: 3200, channels: 2, bandwidthGBs: 51.2, source: 'detected' });
    expect(buildWindowsRam(raw([mod(5600, 34, 'BANK 0', 'DIMM 1')]), 16)).toMatchObject({ type: 'DDR5', channels: 1, bandwidthGBs: 44.8 });
    // two DIMMs in the same channel (wrong slots): single channel
    expect(buildWindowsRam(raw([mod(3200, 26, 'P0 CHANNEL A', 'DIMM 0'), mod(3200, 26, 'P0 CHANNEL A', 'DIMM 1')]), 32)?.channels).toBe(1);
    // four DIMMs, no channel names: dual channel
    expect(buildWindowsRam(raw([0, 1, 2, 3].map((i) => mod(3200, 26, `BANK ${i}`, `DIMM ${i}`))), 64)?.channels).toBe(2);
    expect(buildWindowsRam(raw([]), 32)).toBeNull();
  });

  test('LPDDR: channels from the total bus width', () => {
    const lp = Array.from({ length: 8 }, (_, i) => ({ sizeBytes: 2 * 2 ** 30, type: 'LPDDR5', speedMTs: 6400, dataWidth: 16, locator: `Channel${i}` }));
    expect(ramFromModules(16, lp)).toMatchObject({ channels: 2, bandwidthGBs: 102.4 });
  });

  test('Linux: udev DMI record of our lab (4 × 16 GB DDR4-3200, channels A and B)', () => {
    const dev = (n: number, ch: string) =>
      `E:MEMORY_DEVICE_${n}_DATA_WIDTH=64\nE:MEMORY_DEVICE_${n}_SIZE=17179869184\nE:MEMORY_DEVICE_${n}_LOCATOR=DIMM ${n % 2}\n` +
      `E:MEMORY_DEVICE_${n}_BANK_LOCATOR=P0 CHANNEL ${ch}\nE:MEMORY_DEVICE_${n}_TYPE=DDR4\nE:MEMORY_DEVICE_${n}_SPEED_MTS=3200\n` +
      `E:MEMORY_DEVICE_${n}_CONFIGURED_SPEED_MTS=3200\n`;
    const mods = parseUdevDmiMemory(`E:MEMORY_ARRAY_LOCATION=System Board Or Motherboard\n${dev(0, 'A')}${dev(1, 'A')}${dev(2, 'B')}${dev(3, 'B')}E:MEMORY_DEVICE_4_PRESENT=0\n`);
    expect(mods).toHaveLength(4);
    expect(ramFromModules(62.7, mods)).toMatchObject({ type: 'DDR4', speedMTs: 3200, channels: 2, modules: 4, bandwidthGBs: 51.2, source: 'detected' });
  });

  test('no firmware tables: a conservative default by CPU generation', () => {
    expect(defaultRam(32, 'AMD Ryzen 7 5700G with Radeon Graphics')).toMatchObject({ type: 'DDR4', speedMTs: 3200, bandwidthGBs: 51.2, source: 'default' });
    expect(defaultRam(32, 'AMD Ryzen 7 7840HS w/ Radeon 780M Graphics')).toMatchObject({ type: 'DDR5', speedMTs: 4800 });
    expect(defaultRam(16, 'AMD Ryzen 5 7530U with Radeon Graphics')).toMatchObject({ type: 'DDR4' });
    expect(defaultRam(16, '11th Gen Intel(R) Core(TM) i7-1165G7 @ 2.80GHz')).toMatchObject({ type: 'DDR4', speedMTs: 2933 });
    expect(defaultRam(64, 'Apple M4 Pro').bandwidthGBs).toBe(273);
  });
});
