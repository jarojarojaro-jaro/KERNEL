// Linux hardware detection: sysfs PCI + amdgpu, KFD topology (gfx arch), lspci names, nvidia-smi, /proc, RAM modules
// from udev's DMI record (readable without root) or EDAC.
import { readdirSync, readFileSync, readlinkSync, existsSync } from 'node:fs';
import { basename, join } from 'node:path';
import type { Gpu, RamInfo } from '../../shared/types.ts';
import {
  amdApuName, amdArchFromDevice, amdBoardName, amdIsIntegrated, backendsFor, gfxFromTargetVersion, intelIsDiscrete,
  NVIDIA_SMI_QUERY, parseNvidiaSmi, toGiB, vendorFromPciId,
} from './common.ts';
import { ramFromModules, type RamModule } from './ram.ts';
import { runText } from './run.ts';

/** One PCI display device (class 0x03xxxx) as read from sysfs. */
export interface LinuxPciGpu {
  slot: string; // 0000:2d:00.0
  vendor: string; // 0x1002
  device: string; // 0x744c
  revision: string; // 0xc8
  driver: string | null; // amdgpu, nvidia, i915, xe
  vramTotal: number | null; // amdgpu mem_info_vram_total (bytes)
  gttTotal: number | null; // amdgpu mem_info_gtt_total (bytes)
  intelVram: number | null; // xe tile0/physical_vram_size_bytes
  productName: string | null; // amdgpu product_name (some boards)
}

/** Everything the Linux scan reads; recorded as JSON fixtures for the tests. */
export interface LinuxRaw {
  cpuinfo: string;
  memTotalBytes: number;
  pci: LinuxPciGpu[];
  kfdNodes: string[]; // /sys/class/kfd/kfd/topology/nodes/*/properties
  lspci: string; // `lspci -nn -D` (may be empty)
  nvidiaSmi: string | null; // nvidia-smi csv, null if not available
  /** /run/udev/data/+dmi:id: systemd's copy of SMBIOS type 17 (`E:MEMORY_DEVICE_<n>_*`); absent in older recordings. */
  dmi?: string;
  /** /sys/devices/system/edac/mc/mc*\/dimm*: `dimm_mem_type` ("Unbuffered-DDR4"), `size` (MiB), `dimm_label`. */
  edac?: { type: string; sizeMiB: number; label: string }[];
}

/** udev DMI record -> memory modules (empty slots have no SIZE). */
export function parseUdevDmiMemory(text: string): RamModule[] {
  const dev = new Map<string, Record<string, string>>();
  for (const line of text.split('\n')) {
    const m = /^E:MEMORY_DEVICE_(\d+)_([A-Z_]+)=(.*)$/.exec(line.trim());
    if (!m) continue;
    const [, n = '', key = '', value = ''] = m;
    const rec = dev.get(n) ?? {};
    rec[key] = value;
    dev.set(n, rec);
  }
  const out: RamModule[] = [];
  for (const d of dev.values()) {
    const size = Number(d.SIZE ?? 0);
    if (!size) continue;
    const mod: RamModule = { sizeBytes: size, locator: `${d.BANK_LOCATOR ?? ''} ${d.LOCATOR ?? ''}`.trim() };
    const type = /^(LP)?DDR\d/.exec(d.TYPE ?? '')?.[0];
    if (type) mod.type = type.replace(/X$/, '');
    const speed = Number(d.CONFIGURED_SPEED_MTS ?? d.SPEED_MTS ?? 0);
    if (speed) mod.speedMTs = speed;
    const width = Number(d.DATA_WIDTH ?? 0);
    if (width) mod.dataWidth = width;
    out.push(mod);
  }
  return out;
}

/** RAM from udev DMI, else EDAC (type and module count, no speed); null when neither is readable. */
export function buildLinuxRam(raw: LinuxRaw, totalGiB: number): RamInfo | null {
  const dmi = ramFromModules(totalGiB, parseUdevDmiMemory(raw.dmi ?? ''));
  if (dmi) return dmi;
  return ramFromModules(totalGiB, (raw.edac ?? []).map((d) => {
    const mod: RamModule = { sizeBytes: d.sizeMiB * 1024 * 1024, locator: d.label };
    const type = /(LP)?DDR\d/.exec(d.type)?.[0];
    if (type) mod.type = type;
    return mod;
  }));
}

export interface CpuInfo { name: string; cores: number; threads: number }

/** /proc/cpuinfo -> model name, physical cores (unique physical id/core id pairs), logical threads. */
export function parseCpuinfo(text: string): CpuInfo {
  let name = '';
  let threads = 0;
  const cores = new Set<string>();
  let phys = '0';
  for (const line of text.split('\n')) {
    const m = /^([^:]+?)\s*:\s*(.*)$/.exec(line);
    if (!m) continue;
    const key = m[1] ?? '';
    const val = m[2] ?? '';
    if (key === 'processor') threads++;
    else if (key === 'model name' && !name) name = val.replace(/\s+/g, ' ').trim();
    else if (key === 'physical id') phys = val;
    else if (key === 'core id') cores.add(`${phys}:${val}`);
  }
  return { name: name || 'unknown CPU', cores: cores.size || threads, threads };
}

/** KFD node properties -> { location_id, gfx } for GPU nodes. */
export function parseKfdNode(text: string): { locationId: number; domain: number; gfx: string } | null {
  const props: Record<string, number> = {};
  for (const line of text.split('\n')) {
    const [k, v] = line.trim().split(/\s+/);
    if (k && v !== undefined) props[k] = Number(v);
  }
  const gfx = gfxFromTargetVersion(props.gfx_target_version ?? 0);
  if (!gfx) return null;
  return { locationId: props.location_id ?? 0, domain: props.domain ?? 0, gfx };
}

/** PCI slot "0000:2d:00.0" -> KFD location_id ((bus << 8) | (dev << 3) | fn) and domain. */
export function slotToLocation(slot: string): { domain: number; locationId: number } | null {
  const m = /^([0-9a-f]{4}):([0-9a-f]{2}):([0-9a-f]{2})\.([0-7])$/i.exec(slot);
  if (!m) return null;
  const [, dom, bus, dev, fn] = m;
  return {
    domain: parseInt(dom ?? '0', 16),
    locationId: (parseInt(bus ?? '0', 16) << 8) | (parseInt(dev ?? '0', 16) << 3) | parseInt(fn ?? '0', 16),
  };
}

/**
 * `lspci -nn -D` line -> marketing name for a slot. "… [AMD/ATI] Navi 31 [Radeon RX 7900 XT/7900 XTX/7900M] [1002:744c]"
 * -> "Radeon RX 7900 XT/7900 XTX/7900M"; "NVIDIA Corporation GA102 [GeForce RTX 3090] [10de:2204]" -> "GeForce RTX 3090".
 */
export function lspciName(lspci: string, slot: string): string | null {
  const short = slot.replace(/^0000:/, '');
  for (const line of lspci.split('\n')) {
    if (!(line.startsWith(slot + ' ') || line.startsWith(short + ' '))) continue;
    const afterClass = line.replace(/^\S+\s+[^:]*\[[0-9a-f]{4}\]:\s*/i, '');
    const desc = afterClass.replace(/\s*\[[0-9a-f]{4}:[0-9a-f]{4}\].*$/i, '').trim();
    const brackets = [...desc.matchAll(/\[([^\]]+)\]/g)].map((x) => x[1] ?? '');
    const last = brackets.at(-1);
    // "[AMD/ATI]" is a vendor tag, not a product name
    if (last && last !== 'AMD/ATI' && brackets.length > 0 && desc.trim().endsWith(']')) return last;
    return desc.replace(/^(Advanced Micro Devices, Inc\.|NVIDIA Corporation|Intel Corporation)\s*(\[AMD\/ATI\])?\s*/, '').trim() || null;
  }
  return null;
}

function vendorPrefix(vendor: Gpu['vendor'], name: string): string {
  const prefix = vendor === 'amd' ? 'AMD' : vendor === 'nvidia' ? 'NVIDIA' : vendor === 'intel' ? 'Intel' : 'Apple';
  return name.toUpperCase().startsWith(prefix.toUpperCase()) ? name : `${prefix} ${name}`;
}

export function buildLinuxGpus(raw: LinuxRaw): Gpu[] {
  const kfd = raw.kfdNodes.map(parseKfdNode).filter((n): n is NonNullable<typeof n> => n !== null);
  const smi = raw.nvidiaSmi ? parseNvidiaSmi(raw.nvidiaSmi) : [];
  let nvIndex = 0;
  // sysfs lists every board of the host, also the ones a container (Docker --gpus, Vast, cloud) cannot use;
  // nvidia-smi lists only the visible ones. Matched by PCI address; boards it does not list are skipped.
  const smiByBus = smi.every((s) => s.busId !== undefined) && smi.length > 0;
  const gpus: Gpu[] = [];
  for (const dev of raw.pci) {
    const vendor = vendorFromPciId(dev.vendor);
    if (!vendor) continue;
    const devId = dev.device.replace(/^0x/, '').toLowerCase();
    const pciName = lspciName(raw.lspci, dev.slot);
    if (vendor === 'amd') {
      const loc = slotToLocation(dev.slot);
      const node = loc ? kfd.find((n) => n.locationId === loc.locationId && n.domain === loc.domain) : undefined;
      const arch = node?.gfx ?? amdArchFromDevice(devId);
      const rawName = dev.productName?.trim() || pciName || `PCI 1002:${devId}`;
      const vramGiB = toGiB(dev.vramTotal ?? 0);
      // APU id / iGPU name / ≤ 2 GiB carve-out without a board name; then it computes in RAM: carve-out + GTT
      const integrated = amdIsIntegrated(rawName, devId, vramGiB);
      const name = integrated
        ? (dev.productName?.trim() || (pciName && /\[|Radeon/.test(pciName) ? pciName : amdApuName(devId)) || rawName)
        : amdBoardName(devId, vramGiB) ?? rawName;
      const g: Gpu = {
        vendor, name: vendorPrefix(vendor, name), kind: integrated ? 'integrated' : 'discrete', vramGiB,
        ...(integrated && dev.gttTotal ? { sharedGiB: toGiB(dev.gttTotal) } : {}),
        backends: backendsFor('amd', 'linux', { driver: dev.driver === 'amdgpu', integrated, ...(arch ? { arch } : {}) }),
      };
      if (arch) g.arch = arch;
      if (dev.driver) g.driver = dev.driver;
      gpus.push(g);
    } else if (vendor === 'nvidia') {
      const s = smiByBus ? smi.find((x) => x.busId === dev.slot.toLowerCase()) : smi[nvIndex++];
      if (smiByBus && !s) continue;
      const name = s?.name ?? pciName ?? `PCI 10de:${devId}`;
      const g: Gpu = {
        vendor, name: vendorPrefix(vendor, name), kind: 'discrete', vramGiB: s ? toGiB(s.vramMiB * 1024 * 1024) : 0,
        backends: backendsFor('nvidia', 'linux', { driver: s !== undefined }),
      };
      if (s?.arch) g.arch = s.arch;
      if (s?.driver) g.driver = s.driver;
      gpus.push(g);
    } else {
      const name = pciName ?? `PCI 8086:${devId}`;
      const discrete = intelIsDiscrete(name);
      const g: Gpu = {
        vendor, name: vendorPrefix(vendor, name), kind: discrete ? 'discrete' : 'integrated',
        vramGiB: discrete && dev.intelVram ? toGiB(dev.intelVram) : 0,
        backends: dev.driver ? backendsFor('intel', 'linux', { driver: true }) : [],
      };
      if (dev.driver) g.driver = dev.driver;
      gpus.push(g);
    }
  }
  return gpus;
}

function readOpt(p: string): string | null {
  try {
    return readFileSync(p, 'utf8').trim();
  } catch {
    return null;
  }
}

function numOpt(p: string): number | null {
  const s = readOpt(p);
  if (s === null) return null;
  const n = Number(s);
  return Number.isFinite(n) ? n : null;
}

/** The cgroup memory limit of this process (v2 `memory.max`, v1 `memory.limit_in_bytes`), null when unlimited. */
function cgroupMemLimit(): number | null {
  for (const p of ['/sys/fs/cgroup/memory.max', '/sys/fs/cgroup/memory/memory.limit_in_bytes']) {
    const n = numOpt(p); // "max" (v2 unlimited) is not a number; v1 unlimited is a huge page-rounded value
    if (n !== null && n > 0 && n < 2 ** 60) return n;
  }
  return null;
}

/** Reads the live system into a LinuxRaw; RAM is capped by the cgroup limit (containers see the host's MemTotal). */
export async function collectLinuxRaw(hostMemBytes: number): Promise<LinuxRaw> {
  const limit = cgroupMemLimit();
  const memTotalBytes = limit === null ? hostMemBytes : Math.min(hostMemBytes, limit);
  const pciRoot = '/sys/bus/pci/devices';
  const pci: LinuxPciGpu[] = [];
  for (const slot of existsSync(pciRoot) ? readdirSync(pciRoot) : []) {
    const dir = join(pciRoot, slot);
    const cls = readOpt(join(dir, 'class'));
    if (!cls || !cls.startsWith('0x03')) continue;
    let driver: string | null = null;
    try {
      driver = basename(readlinkSync(join(dir, 'driver')));
    } catch {
      driver = null;
    }
    pci.push({
      slot,
      vendor: readOpt(join(dir, 'vendor')) ?? '',
      device: readOpt(join(dir, 'device')) ?? '',
      revision: readOpt(join(dir, 'revision')) ?? '',
      driver,
      vramTotal: numOpt(join(dir, 'mem_info_vram_total')),
      gttTotal: numOpt(join(dir, 'mem_info_gtt_total')),
      intelVram: numOpt(join(dir, 'tile0', 'physical_vram_size_bytes')),
      productName: readOpt(join(dir, 'product_name')) || null,
    });
  }
  const kfdRoot = '/sys/class/kfd/kfd/topology/nodes';
  const kfdNodes: string[] = [];
  for (const n of existsSync(kfdRoot) ? readdirSync(kfdRoot) : []) {
    const t = readOpt(join(kfdRoot, n, 'properties'));
    if (t) kfdNodes.push(t);
  }
  const edacRoot = '/sys/devices/system/edac/mc';
  const edac: NonNullable<LinuxRaw['edac']> = [];
  for (const mc of existsSync(edacRoot) ? readdirSync(edacRoot).filter((d) => d.startsWith('mc')) : []) {
    for (const dimm of readdirSync(join(edacRoot, mc)).filter((d) => /^(dimm|rank)\d+$/.test(d))) {
      const dir = join(edacRoot, mc, dimm);
      const sizeMiB = numOpt(join(dir, 'size')) ?? 0;
      if (sizeMiB > 0) edac.push({ type: readOpt(join(dir, 'dimm_mem_type')) ?? '', sizeMiB, label: readOpt(join(dir, 'dimm_label')) ?? '' });
    }
  }
  const hasNvidia = pci.some((p) => vendorFromPciId(p.vendor) === 'nvidia');
  return {
    cpuinfo: readOpt('/proc/cpuinfo') ?? '',
    memTotalBytes,
    pci,
    kfdNodes,
    lspci: (await runText(['lspci', '-nn', '-D'])) ?? '',
    nvidiaSmi: hasNvidia ? await runText(NVIDIA_SMI_QUERY) : null,
    dmi: readOpt('/run/udev/data/+dmi:id') ?? '',
    edac,
  };
}
