// Windows hardware detection: the logic of app/scan/scan.ps1 (CIM + display-class registry for 64-bit VRAM) + nvidia-smi.
import type { Gpu } from '../../shared/types.ts';
import { NVIDIA_SMI_QUERY, amdArchFromDevice, amdIsDiscrete, backendsFor, intelIsDiscrete, parseNvidiaSmi, toGiB } from './common.ts';
import { runText } from './run.ts';

export interface WinVideoController { Name: string; DriverVersion: string; AdapterCompatibility: string; PNPDeviceID: string }
export interface WinRegEntry { Key: string; Desc: string; Match: string; Mem: string; Radeon: string }
export interface WinCpu { Name: string; NumberOfCores: number; NumberOfLogicalProcessors: number; Architecture: number }

/** Everything the Windows scan reads; recorded as JSON fixtures for the tests. */
export interface WindowsRaw {
  os: { Caption: string; Version: string; TotalVisibleMemorySize: number } | null;
  cpu: WinCpu[];
  vc: WinVideoController[];
  reg: WinRegEntry[];
  nvidiaSmi: string | null;
}

/**
 * Read-only PowerShell probe; prints one JSON object. Same sources as scan.ps1: Win32_OperatingSystem,
 * Win32_Processor, Win32_VideoController and HKLM display-adapter class values (qwMemorySize is the 64-bit VRAM size;
 * AdapterRAM is truncated at 4 GB and never used).
 */
export const WINDOWS_PROBE = String.raw`
$ErrorActionPreference = 'SilentlyContinue'
$os = Get-CimInstance -ClassName Win32_OperatingSystem -Property Caption, Version, TotalVisibleMemorySize
$cpu = @(Get-CimInstance -ClassName Win32_Processor -Property Name, NumberOfCores, NumberOfLogicalProcessors, Architecture | Select-Object Name, NumberOfCores, NumberOfLogicalProcessors, Architecture)
$vc = @(Get-CimInstance -ClassName Win32_VideoController -Property Name, DriverVersion, AdapterCompatibility, PNPDeviceID | Select-Object Name, DriverVersion, AdapterCompatibility, PNPDeviceID)
$reg = @()
$cls = [Microsoft.Win32.Registry]::LocalMachine.OpenSubKey('SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}')
if ($cls) {
  foreach ($sk in $cls.GetSubKeyNames()) {
    if ($sk -notmatch '^0\d{3}$') { continue }
    $k = $cls.OpenSubKey($sk)
    if (-not $k) { continue }
    $mem = [uint64]0
    $q = $k.GetValue('HardwareInformation.qwMemorySize')
    if ($null -ne $q) { $mem = [uint64]$q }
    else {
      $m = $k.GetValue('HardwareInformation.MemorySize')
      if ($m -is [byte[]] -and $m.Length -ge 4) { $mem = [uint64][BitConverter]::ToUInt32($m, 0) }
      elseif ($m -is [int]) { $mem = [uint64][BitConverter]::ToUInt32([BitConverter]::GetBytes($m), 0) }
      elseif ($null -ne $m) { $mem = [uint64]$m }
    }
    $reg += [pscustomobject]@{ Key = $sk; Desc = [string]$k.GetValue('DriverDesc'); Match = ([string]$k.GetValue('MatchingDeviceId')).ToLowerInvariant(); Mem = [string]$mem; Radeon = [string]$k.GetValue('RadeonSoftwareVersion') }
    $k.Close()
  }
  $cls.Close()
}
$o = $null
if ($os) { $o = [pscustomobject]@{ Caption = [string]$os.Caption; Version = [string]$os.Version; TotalVisibleMemorySize = [uint64]$os.TotalVisibleMemorySize } }
[pscustomobject]@{ os = $o; cpu = $cpu; vc = $vc; reg = $reg } | ConvertTo-Json -Depth 4 -Compress
`;

function asArray<T>(v: T | T[] | null | undefined): T[] {
  if (v === null || v === undefined) return [];
  return Array.isArray(v) ? v : [v];
}

/** Parses the probe output (PowerShell 5.1 emits single-element arrays as objects). */
export function parseWindowsProbe(json: string, nvidiaSmi: string | null): WindowsRaw {
  const o = JSON.parse(json) as {
    os?: WindowsRaw['os']; cpu?: WinCpu | WinCpu[]; vc?: WinVideoController | WinVideoController[];
    reg?: WinRegEntry | WinRegEntry[];
  };
  return { os: o.os ?? null, cpu: asArray(o.cpu), vc: asArray(o.vc), reg: asArray(o.reg), nvidiaSmi };
}

export function buildWindowsGpus(raw: WindowsRaw): Gpu[] {
  const smi = raw.nvidiaSmi ? parseNvidiaSmi(raw.nvidiaSmi) : [];
  let nvIndex = 0;
  const used = new Set<string>();
  const gpus: Gpu[] = [];
  for (const vc of raw.vc) {
    const pnp = vc.PNPDeviceID ?? '';
    // physical adapters only: PCI (and ACPI for Arm laptops); ROOT\, SWD\, USB\ are virtual/remote/DisplayLink
    if (!/^(PCI|ACPI)\\/i.test(pnp)) continue;
    const name = (vc.Name ?? '').replace(/\s+/g, ' ').trim();
    if (/^Microsoft Basic (Display|Render)/.test(name)) continue; // no vendor driver: unusable for inference
    const ven = /VEN_([0-9A-Fa-f]{4})/.exec(pnp)?.[1]?.toLowerCase() ?? '';
    const dev = /DEV_([0-9A-Fa-f]{4})/.exec(pnp)?.[1]?.toLowerCase() ?? '';
    const compat = vc.AdapterCompatibility ?? '';
    let vendor: Gpu['vendor'] | null = ven === '1002' ? 'amd' : ven === '10de' ? 'nvidia' : ven === '8086' ? 'intel' : null;
    if (!vendor) {
      if (/Advanced Micro Devices|\bAMD\b|\bATI\b/.test(compat)) vendor = 'amd';
      else if (/NVIDIA/.test(compat)) vendor = 'nvidia';
      else if (/Intel/.test(compat)) vendor = 'intel';
    }
    if (!vendor) continue;

    const cands = raw.reg.filter((e) => e.Desc === vc.Name && !used.has(e.Key));
    const entry = cands.find((e) => e.Match && pnp.toLowerCase().startsWith(e.Match)) ?? cands[0];
    if (entry) used.add(entry.Key);
    const mem = entry ? Number(entry.Mem) : 0;

    if (vendor === 'nvidia') {
      const s = smi[nvIndex++];
      const g: Gpu = {
        vendor, name, vramGiB: s ? toGiB(s.vramMiB * 1024 * 1024) : toGiB(mem), unified: false,
        backends: backendsFor('nvidia', 'windows', { driver: true }),
      };
      if (s?.arch) g.arch = s.arch;
      g.driver = s?.driver ?? vc.DriverVersion;
      gpus.push(g);
    } else if (vendor === 'amd') {
      const unified = !amdIsDiscrete(name);
      const arch = amdArchFromDevice(dev);
      const g: Gpu = {
        vendor, name: name.startsWith('AMD') ? name : `AMD ${name}`, vramGiB: toGiB(mem), unified,
        backends: backendsFor('amd', 'windows', { driver: true, ...(arch ? { arch } : {}) }),
      };
      if (arch) g.arch = arch;
      g.driver = entry?.Radeon || vc.DriverVersion;
      gpus.push(g);
    } else {
      const discrete = intelIsDiscrete(name);
      const g: Gpu = {
        vendor, name, vramGiB: discrete ? toGiB(mem) : 0, unified: !discrete,
        backends: backendsFor('intel', 'windows', { driver: true }), driver: vc.DriverVersion,
      };
      gpus.push(g);
    }
  }
  return gpus;
}

export async function collectWindowsRaw(): Promise<WindowsRaw> {
  const out = await runText(['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-Command', WINDOWS_PROBE], 60_000);
  const smi = await runText(NVIDIA_SMI_QUERY);
  if (!out) return { os: null, cpu: [], vc: [], reg: [], nvidiaSmi: smi };
  return parseWindowsProbe(out, smi);
}
