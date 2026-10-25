// System RAM: type, speed and channels from the firmware (SMBIOS type 17) and the bandwidth that bounds inference on
// machines without a discrete GPU (integrated graphics and the CPU both read the weights from this RAM).
import type { RamInfo } from '../../shared/types.ts';
import { matchGpu } from '../catalog/score.ts';

/** One memory module as Windows (Win32_PhysicalMemory) or udev (`MEMORY_DEVICE_<n>_*`, DMI type 17) reports it. */
export interface RamModule {
  sizeBytes: number;
  type?: string;
  /** Configured speed, MT/s. */
  speedMTs?: number;
  /** Data bus width, bits (64 for a DIMM; 16/32 per LPDDR package). */
  dataWidth?: number;
  /** Bank and device locator joined ("P0 CHANNEL A DIMM 0", "Controller0-ChannelA-DIMM0"). */
  locator: string;
}

/** SMBIOS memory type codes (SMBIOS 3.x §7.18.2). LPDDR4X/LPDDR5X report as LPDDR4/LPDDR5. */
const SMBIOS_TYPE: Record<number, string> = {
  24: 'DDR3', 26: 'DDR4', 27: 'LPDDR', 28: 'LPDDR2', 29: 'LPDDR3', 30: 'LPDDR4', 34: 'DDR5', 35: 'LPDDR5',
};

export function smbiosMemoryType(code: number): string | undefined {
  return SMBIOS_TYPE[code];
}

/** Typical speed per type when the firmware does not report one, MT/s (low end of what ships). */
const TYPE_SPEED: Record<string, number> = { DDR3: 1600, DDR4: 2666, DDR5: 4800, LPDDR3: 1866, LPDDR4: 4266, LPDDR5: 5500 };

/**
 * Some firmware reports the memory clock instead of the transfer rate (DDR4-3200 as 1600). Below the slowest speed the
 * type actually ships at the value is a clock and gets doubled.
 */
function transferRate(type: string | undefined, mts: number): number {
  const floor: Record<string, number> = { DDR3: 1000, DDR4: 1700, DDR5: 4000, LPDDR4: 2000, LPDDR5: 4000 };
  const f = type ? floor[type] : undefined;
  return f !== undefined && mts < f ? mts * 2 : mts;
}

/** Channel of a DIMM from its locator ("P0 CHANNEL A", "ChannelB-DIMM0", "Controller1-ChannelA", "DIMM_A1"). */
function channelOf(locator: string): string | undefined {
  const ch = /CHANNEL\s*[-_#]?\s*([A-H0-9])\b/i.exec(locator)?.[1] ?? /\bDIMM[_\s-]?([A-H])\d\b/i.exec(locator)?.[1];
  if (!ch) return undefined;
  const ctrl = /Controller\s*(\d)/i.exec(locator)?.[1] ?? '';
  return `${ctrl}${ch.toUpperCase()}`;
}

/** 64-bit channels: LPDDR from the total bus width (128 bits when unknown); DIMMs from their locators when every
 *  module names its channel, else 1 module = 1 channel, 2+ modules = dual channel (desktop/laptop default). */
function channelsOf(modules: RamModule[], type: string | undefined): number {
  if (type?.startsWith('LPDDR')) {
    const bits = modules.reduce((s, m) => s + (m.dataWidth ?? 0), 0);
    return bits >= 64 ? Math.max(1, Math.round(bits / 64)) : 2;
  }
  const named = modules.map((m) => channelOf(m.locator));
  if (named.every((c) => c !== undefined)) return Math.min(8, new Set(named).size);
  return modules.length >= 2 ? 2 : 1;
}

const bandwidth = (mts: number, channels: number): number => Math.round(mts * 8 * channels / 100) / 10;

/** RAM from the module list; null when the firmware lists no modules (VMs, some laptops). */
export function ramFromModules(totalGiB: number, modules: RamModule[]): RamInfo | null {
  const mods = modules.filter((m) => m.sizeBytes > 0);
  if (mods.length === 0) return null;
  const type = mods.find((m) => m.type)?.type;
  const speeds = mods.map((m) => m.speedMTs ?? 0).filter((s) => s > 0);
  const reported = speeds.length ? Math.min(...speeds) : 0; // mixed kits run at the slowest module
  const speed = reported ? transferRate(type, reported) : type ? TYPE_SPEED[type] : undefined;
  if (!speed) return null;
  const channels = channelsOf(mods, type);
  const r: RamInfo = {
    totalGiB, speedMTs: speed, channels, modules: mods.length, bandwidthGBs: bandwidth(speed, channels),
    source: reported ? 'detected' : 'default',
  };
  if (type) r.type = type;
  return r;
}

/**
 * Conservative RAM for a CPU generation when the firmware tables are not readable (Linux without udev DMI data,
 * Windows probe failure): the slowest memory the platform ships with, dual channel. Apple Silicon: the chip's
 * bandwidth from the catalog table.
 */
export function defaultRam(totalGiB: number, cpuName: string): RamInfo {
  const apple = /Apple M\d/.test(cpuName) ? matchGpu(cpuName, totalGiB) : null;
  if (apple) return { totalGiB, type: 'LPDDR5', bandwidthGBs: apple.bwGBs, source: 'default' };
  const [type, speed] = cpuGeneration(cpuName);
  return { totalGiB, type, speedMTs: speed, channels: 2, bandwidthGBs: bandwidth(speed, 2), source: 'default' };
}

function cpuGeneration(name: string): [string, number] {
  if (/Core.*Ultra|Ryzen AI/i.test(name)) return ['DDR5', 5600];
  const ryzen = /Ryzen\s+(?:Threadripper\s+)?(?:PRO\s+)?\d?\s*(\d)(\d)(\d)(\d)([A-Z0-9]*)/i.exec(name);
  if (ryzen) {
    const series = Number(ryzen[1]);
    const suffix = ryzen[5] ?? '';
    // Ryzen 7020 (Mendocino) / 7030 (Barcelo) laptops are DDR4/LPDDR4X-era chips under the 7000 name
    const ddr4Mobile = series === 7 && /^U/i.test(suffix) && (ryzen[3] === '2' || ryzen[3] === '3');
    return series >= 6 && !ddr4Mobile ? ['DDR5', 4800] : ['DDR4', 3200];
  }
  // "i7-8700K" -> 8; "i9-13900K" -> 13; mobile "i7-1165G7" / "i5-1235U" -> 11 / 12 (no 1st-gen part has 4 digits)
  const intel = /\bi[3579]-(\d{4,5})/i.exec(name)?.[1];
  if (intel) {
    const gen = intel.length === 5 || intel[0] === '1' ? Number(intel.slice(0, 2)) : Number(intel[0]);
    if (gen >= 12) return ['DDR4', 3200];
    if (gen >= 10) return ['DDR4', 2933];
    if (gen >= 6) return ['DDR4', 2400];
    return ['DDR3', 1600];
  }
  return ['DDR4', 2666];
}
