// Shared hardware helpers: backend mapping, PCI id tables, number formatting.
import type { Backend, Gpu, Hw } from '../../shared/types.ts';

export const GIB = 1024 ** 3;

/** Bytes -> GiB with one decimal. */
export function toGiB(bytes: number): number {
  return Math.round((bytes / GIB) * 10) / 10;
}

export type Os = Hw['os'];
export type Vendor = Gpu['vendor'];

/** GPU architectures the official ROCm/HIP Windows builds support (llama.cpp win-rocm assets). */
const HIP_WINDOWS_ARCHS: Record<string, true> = {
  gfx1030: true, gfx1100: true, gfx1101: true, gfx1102: true, gfx1150: true, gfx1151: true, gfx1200: true, gfx1201: true,
};

/**
 * Backends per GPU, preferred first:
 * AMD Linux rocm+vulkan; AMD Windows vulkan (+rocm when the HIP build supports the arch); NVIDIA cuda+vulkan
 * (vulkan only without a driver); Intel vulkan; Apple metal. AMD integrated graphics: vulkan, ROCm only for the APUs
 * the HIP builds target (Strix Point/Halo gfx1150/gfx1151); the official ROCm builds carry no kernels for older APUs
 * (gfx90c, gfx1035, gfx1103 …). A machine without a discrete GPU also plans for 'cpu' (catalog).
 */
export function backendsFor(vendor: Vendor, os: Os, opts: { arch?: string; driver: boolean; integrated?: boolean }): Backend[] {
  switch (vendor) {
    case 'amd': {
      const hip = opts.arch !== undefined && HIP_WINDOWS_ARCHS[opts.arch] === true;
      if (os === 'linux') return !opts.driver ? [] : opts.integrated && !hip ? ['vulkan'] : ['rocm', 'vulkan'];
      if (os === 'windows') return hip ? ['vulkan', 'rocm'] : ['vulkan'];
      return [];
    }
    case 'nvidia':
      if (os === 'macos') return [];
      return opts.driver ? ['cuda', 'vulkan'] : [];
    case 'intel':
      return os === 'macos' ? [] : ['vulkan'];
    case 'apple':
      return ['metal'];
  }
}

export function vendorFromPciId(id: string): Vendor | null {
  switch (id.toLowerCase().replace(/^0x/, '')) {
    case '1002': return 'amd';
    case '10de': return 'nvidia';
    case '8086': return 'intel';
    default: return null;
  }
}

/** AMD PCI device id -> gfx target (used where the KFD topology is not available, i.e. Windows). */
const AMD_ARCH_BY_DEVICE: Record<string, string> = {
  '73a2': 'gfx1030', '73a3': 'gfx1030', '73a5': 'gfx1030', '73af': 'gfx1030', '73bf': 'gfx1030',
  '73df': 'gfx1031', '73ef': 'gfx1032', '73ff': 'gfx1032',
  '744c': 'gfx1100', '7448': 'gfx1100', '745e': 'gfx1100',
  '747e': 'gfx1101', '7470': 'gfx1101',
  '7480': 'gfx1102', '7483': 'gfx1102', '7489': 'gfx1102',
  '15bf': 'gfx1103', '15c8': 'gfx1103', '1900': 'gfx1103',
  '150e': 'gfx1150', '1586': 'gfx1151',
  '15dd': 'gfx902', '15d8': 'gfx909', '1636': 'gfx90c', '1638': 'gfx90c', '164c': 'gfx90c', '15e7': 'gfx90c',
  '163f': 'gfx1033', '1681': 'gfx1035', '164e': 'gfx1036', '13c0': 'gfx1036', '1506': 'gfx1037',
  '7590': 'gfx1200', '7550': 'gfx1201', '7551': 'gfx1201',
};

export function amdArchFromDevice(device: string): string | undefined {
  return AMD_ARCH_BY_DEVICE[device.toLowerCase().replace(/^0x/, '')];
}

/** KFD gfx_target_version (e.g. 110000, 90010) -> 'gfx1100', 'gfx90a'. 0 = not a GPU node. */
export function gfxFromTargetVersion(v: number): string | undefined {
  if (!Number.isFinite(v) || v <= 0) return undefined;
  const major = Math.floor(v / 10000);
  const minor = Math.floor(v / 100) % 100;
  const step = v % 100;
  return `gfx${major}${minor.toString(16)}${step.toString(16)}`;
}

/**
 * Some PCI names cover several boards ("Radeon RX 7900 XT/7900 XTX/7900M"); the VRAM size tells them apart.
 * Only boards whose VRAM is unique within the device id are listed.
 */
const AMD_NAME_BY_DEVICE_VRAM: Record<string, Record<number, string>> = {
  '744c': { 24: 'Radeon RX 7900 XTX', 20: 'Radeon RX 7900 XT' },
};

export function amdBoardName(device: string, vramGiB: number): string | undefined {
  const byVram = AMD_NAME_BY_DEVICE_VRAM[device.toLowerCase().replace(/^0x/, '')];
  return byVram?.[Math.round(vramGiB)];
}

/** AMD discrete by name (scan.ps1 rule): RX, Pro, VII, FirePro, Instinct, R5-R9 nnn, HD nnnn. */
const AMD_DISCRETE = /\bRX\s*\d|Vega\s*(56|64|Frontier)|Radeon(\s*\(TM\))?\s*(VII|Pro\b)|FirePro|Instinct|\bR[5-9]\s*\d{3}\b|\bHD\s*\d{4}(?![GD0-9])|Radeon(\s*\(TM\))?\s*\d{3}(?![0-9MS])/;

/** AMD APU graphics by PCI device id (Raven/Picasso, Renoir, Cezanne/Lucienne/Barcelo, Van Gogh, Rembrandt 680M,
 *  Raphael/Granite Ridge, Mendocino, Phoenix/Hawk Point 780M/760M/740M, Strix Point 890M, Strix Halo 8060S). */
const AMD_APU_NAME: Record<string, string> = {
  '15dd': 'Radeon Vega Graphics', '15d8': 'Radeon Vega Graphics', '1636': 'Radeon Graphics', '1638': 'Radeon Graphics',
  '164c': 'Radeon Graphics', '15e7': 'Radeon Graphics', '163f': 'Radeon Graphics (Van Gogh)', '1681': 'Radeon 680M',
  '164e': 'Radeon Graphics', '13c0': 'Radeon Graphics', '1506': 'Radeon 610M', '15bf': 'Radeon 760M/780M Graphics',
  '15c8': 'Radeon 740M Graphics', '1900': 'Radeon 760M/780M Graphics', '150e': 'Radeon 880M/890M Graphics',
  '1586': 'Radeon 8060S Graphics',
};

/** Marketing name of an AMD APU's graphics (lspci only knows codenames such as "Phoenix1"). */
export function amdApuName(device: string): string | undefined {
  return AMD_APU_NAME[device.toLowerCase().replace(/^0x/, '')];
}
/** iGPU names: "Radeon(TM) Graphics", "Radeon Vega 8 Graphics", "Radeon 780M Graphics", "Radeon 8060S", codenames (lspci). */
const AMD_IGPU_NAME = /Radeon(\s*\(TM\))?\s*(Graphics|Vega\b|\d{3,4}[MS]\b)|Vega\s*\d+\s*Graphics|Raven|Picasso|Renoir|Cezanne|Lucienne|Barcelo|Van\s*Gogh|Rembrandt|Raphael|Granite Ridge|Mendocino|Phoenix|Strix/i;
/** AMD carve-out at or below this (GiB) with no discrete name = an APU (BIOS UMA frame buffer is 512 MB–2 GB). */
const APU_CARVEOUT_GIB = 2;

/** AMD graphics that computes in system RAM: an APU device id, an iGPU name, or a small carve-out without a board name. */
export function amdIsIntegrated(name: string, device: string, vramGiB: number): boolean {
  if (amdApuName(device)) return true;
  if (AMD_DISCRETE.test(name)) return false;
  return AMD_IGPU_NAME.test(name) || vramGiB <= APU_CARVEOUT_GIB;
}

/** Intel discrete: Arc A/B series, Xe MAX, Data Center GPU. Everything else is integrated. */
export function intelIsDiscrete(name: string): boolean {
  return /Arc.*\b[AB]\d{3}|Xe MAX|Data Center GPU/.test(name);
}

/** nvidia-smi `compute_cap` "8.6" -> "sm_86". */
export function smFromComputeCap(cc: string): string | undefined {
  const m = /^(\d+)\.(\d+)$/.exec(cc.trim());
  return m ? `sm_${m[1]}${m[2]}` : undefined;
}

export interface NvidiaSmiGpu { name: string; vramMiB: number; driver: string; arch?: string; busId?: string }

/** The one nvidia-smi query every OS runs; `parseNvidiaSmi` reads its columns in this order. */
export const NVIDIA_SMI_QUERY = ['nvidia-smi', '--query-gpu=name,memory.total,driver_version,compute_cap,pci.bus_id', '--format=csv,noheader,nounits'];

/** PCI address in the sysfs form `0000:81:00.0` (nvidia-smi prints `00000000:81:00.0`). */
export function normPciAddr(addr: string): string | undefined {
  const m = /^([0-9a-f]+):([0-9a-f]{2}):([0-9a-f]{2})\.([0-7])$/i.exec(addr.trim());
  return m ? `${parseInt(m[1] as string, 16).toString(16).padStart(4, '0')}:${m[2]}:${m[3]}.${m[4]}`.toLowerCase() : undefined;
}

/** CSV of `NVIDIA_SMI_QUERY` (older 4-column captures without `pci.bus_id` parse too). */
export function parseNvidiaSmi(csv: string): NvidiaSmiGpu[] {
  const out: NvidiaSmiGpu[] = [];
  for (const line of csv.split(/\r?\n/)) {
    if (!line.trim()) continue;
    const parts = line.split(',').map((s) => s.trim());
    if (parts.length < 3) continue;
    const [name, mem, driver, cc, bus] = parts;
    const vramMiB = Number(mem);
    if (!name || !Number.isFinite(vramMiB)) continue;
    const g: NvidiaSmiGpu = { name, vramMiB, driver: driver ?? '' };
    const arch = cc ? smFromComputeCap(cc) : undefined;
    if (arch) g.arch = arch;
    const busId = bus ? normPciAddr(bus) : undefined;
    if (busId) g.busId = busId;
    out.push(g);
  }
  return out;
}

/** Sort GPUs: discrete with most VRAM first (index 0 = the card the planner prefers). */
export function sortGpus(gpus: Gpu[]): Gpu[] {
  return [...gpus].sort((a, b) => Number(a.kind === 'integrated') - Number(b.kind === 'integrated') || b.vramGiB - a.vramGiB);
}
