<#
Hardware scan (paste-code HW1) for Windows.

Purpose: show which CPU, RAM and graphics cards this PC has, and print one line
("HW1;...") that you can paste into the form on our website so it can suggest a
model that fits your hardware. Read-only: needs no administrator rights, makes
no network connections, writes no files, changes no settings (no
Set-ExecutionPolicy). Works in Windows PowerShell 5.1 and PowerShell 7, both as
    irm <url>/scan.ps1 | iex
and as a downloaded file:
    powershell -NoProfile -ExecutionPolicy Bypass -File .\scan.ps1
(-ExecutionPolicy on the command line applies to that one process only).
Checksum self-test: .\scan.ps1 -SelfTest

Exact list of sources read (nothing else):
  CIM Win32_OperatingSystem  properties Caption, Version, TotalVisibleMemorySize
  CIM Win32_Processor        properties Name, NumberOfLogicalProcessors, Architecture
  CIM Win32_VideoController  properties Name, DriverVersion, AdapterCompatibility,
                             PNPDeviceID (only the VEN_/DEV_/SUBSYS_ hex IDs are
                             used; it is never printed). AdapterRAM is never used:
                             it is truncated to 4 GB.
  Registry HKLM:\SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}\0*
                             values DriverDesc, MatchingDeviceId,
                             HardwareInformation.qwMemorySize (fallback
                             HardwareInformation.MemorySize), RadeonSoftwareVersion
                             (CurrentControlSet is the active ControlSet00N)
  Get-PnpDeviceProperty      DEVPKEY_PciDevice_CurrentLinkSpeed / CurrentLinkWidth
                             (PCIe link; optional)
  .NET  System.Runtime.Intrinsics.X86.Avx512F / Avx2 / Avx .IsSupported
                             (PowerShell 7 only; otherwise the ISA is shown as unknown)
  Culture (Get-Culture / Get-UICulture) to choose Polish or English labels.
RAM comes from Win32_OperatingSystem.TotalVisibleMemorySize (same value as
Win32_ComputerSystem.TotalPhysicalMemory, in KiB) because Win32_ComputerSystem
always returns the computer name as its key property.

Never read: computer name, user name, home paths, serial numbers, GPU UUIDs,
MAC addresses, disk serials, event logs. Every CIM query names its properties
explicitly, so CSName, SerialNumber, RegisteredUser, ProcessorId, SystemName and
similar fields are never requested.

SPDX-License-Identifier: MIT
#>
param([switch]$SelfTest)

& {
param([bool]$SelfTest)
Set-StrictMode -Off
$ErrorActionPreference = 'SilentlyContinue'
$inv = [System.Globalization.CultureInfo]::InvariantCulture

# ---- language --------------------------------------------------------------
$PL = $false
try { if ((Get-Culture).TwoLetterISOLanguageName -eq 'pl' -or (Get-UICulture).TwoLetterISOLanguageName -eq 'pl') { $PL = $true } } catch { }

# Source stays pure ASCII (irm | iex in PowerShell 5.1 may decode as Latin-1),
# Polish letters are written as \uXXXX and decoded here.
function U([string]$s) { [regex]::Unescape($s) }

if ($PL) {
  $T = @{
    Title      = U 'Skan sprz\u0119tu (kod HW1) \u2014 tylko odczyt'
    Reads      = U 'Czyta: Win32_OperatingSystem, Win32_Processor, Win32_VideoController (nazwa, wersja sterownika),'
    Reads2     = U '       rejestr klasy kart graficznych (VRAM) i w\u0142a\u015bciwo\u015bci PCIe karty.'
    Safe       = U 'Nic nie wysy\u0142a, niczego nie zapisuje na dysku i nie potrzebuje uprawnie\u0144 administratora.'
    Never      = U 'Nie czyta nazwy komputera ani u\u017cytkownika, numer\u00f3w seryjnych, UUID, adres\u00f3w MAC ani log\u00f3w.'
    Computer   = 'Komputer'
    Gpus       = 'Karty graficzne'
    LOs        = 'System'
    LCpu       = 'Procesor'
    LThr       = U 'W\u0105tki'
    LIsa       = 'Instrukcje'
    LRam       = U 'Pami\u0119\u0107 RAM'
    LChip      = U 'Uk\u0142ad'
    LBoard     = 'Karta'
    LVendor    = 'Producent'
    LType      = 'Rodzaj'
    LVram      = 'VRAM'
    LDrv       = 'Sterownik'
    LPcie      = 'PCIe'
    Primary    = 'trafia do kodu'
    Discrete   = 'dedykowana'
    Integrated = U 'zintegrowana (pami\u0119\u0107 wsp\u00f3lna z RAM)'
    NoDrv      = U 'brak sterownika producenta (Microsoft Basic Display Adapter) \u2014 nie liczona do ngpu'
    None       = 'brak'
    Unknown    = 'nieznane'
    VramShared = U 'brak w\u0142asnej \u2014 u\u017cywa RAM systemu'
    VramUnk    = U 'nieznana; wybierz swoj\u0105 kart\u0119 w formularzu'
    Carve      = 'wydzielone w BIOS/UEFI (carve-out)'
    Link       = U 'bie\u017c\u0105ce \u0142\u0105cze; bez obci\u0105\u017cenia karta cz\u0119sto je zwalnia'
    NoGpu      = 'Nie znaleziono karty graficznej.'
    Found      = 'Wykryto:'
    Working    = U 'z dzia\u0142aj\u0105cym sterownikiem'
    Card1      = 'karta graficzna'
    Card2      = 'karty graficzne'
    Card5      = 'kart graficznych'
    Thr1       = U 'w\u0105tek logiczny'
    Thr2       = U 'w\u0105tki logiczne'
    Thr5       = U 'w\u0105tk\u00f3w logicznych'
    IsaPs5     = U 'nieznane \u2014 Windows PowerShell 5.1 tego nie sprawdza; uruchom skan w PowerShell 7, aby wykry\u0107 AVX2/AVX-512'
    Isa512     = U '(obs\u0142ugi AVX-512 ta wersja PowerShell nie sprawdza)'
    Code       = U 'Kod do wklejenia na stronie \u2014 skopiuj ca\u0142\u0105 lini\u0119 zaczynaj\u0105c\u0105 si\u0119 od HW1;'
    Code2      = U 'Kod zawiera wy\u0142\u0105cznie pola pokazane powy\u017cej; mo\u017cesz go przeczyta\u0107 przed wklejeniem.'
    Self       = 'Test sumy kontrolnej'
  }
} else {
  $T = @{
    Title      = 'Hardware scan (HW1 code) - read-only'
    Reads      = 'Reads: Win32_OperatingSystem, Win32_Processor, Win32_VideoController (name, driver version),'
    Reads2     = '       the display-adapter class in the registry (VRAM) and the PCIe properties of the card.'
    Safe       = 'Sends nothing, writes nothing to disk, needs no administrator rights.'
    Never      = 'Never reads computer or user name, serial numbers, UUIDs, MAC addresses or logs.'
    Computer   = 'Computer'
    Gpus       = 'Graphics'
    LOs        = 'OS'
    LCpu       = 'CPU'
    LThr       = 'Threads'
    LIsa       = 'SIMD'
    LRam       = 'RAM'
    LChip      = 'Chip'
    LBoard     = 'Board'
    LVendor    = 'Vendor'
    LType      = 'Type'
    LVram      = 'VRAM'
    LDrv       = 'Driver'
    LPcie      = 'PCIe'
    Primary    = 'goes into the code'
    Discrete   = 'discrete'
    Integrated = 'integrated (shares system RAM)'
    NoDrv      = 'no vendor driver (Microsoft Basic Display Adapter) - not counted in ngpu'
    None       = 'none'
    Unknown    = 'unknown'
    VramShared = 'none of its own - uses system RAM'
    VramUnk    = 'unknown; pick your card in the form'
    Carve      = 'reserved in BIOS/UEFI (carve-out)'
    Link       = 'current link; cards often slow it down when idle'
    NoGpu      = 'No graphics card found.'
    Found      = 'Found:'
    Working    = 'with a working driver'
    Card1      = 'graphics card'
    Card2      = 'graphics cards'
    Card5      = 'graphics cards'
    Thr1       = 'logical'
    Thr2       = 'logical'
    Thr5       = 'logical'
    IsaPs5     = 'unknown - Windows PowerShell 5.1 cannot check it; run the scan in PowerShell 7 to detect AVX2/AVX-512'
    Isa512     = '(this PowerShell version cannot check AVX-512)'
    Code       = 'Paste code for the website - copy the whole line starting with HW1;'
    Code2      = 'The code contains only the fields shown above; you can read it before pasting.'
    Self       = 'Checksum self-test'
  }
}

# ---- helpers -----------------------------------------------------------------
# Checksum per contract: h = (h*31 + byte) % 65521 over the UTF-8 bytes; 4 hex digits.
function Get-HwSum([string]$s) {
  $h = 0
  foreach ($b in [System.Text.Encoding]::UTF8.GetBytes($s)) { $h = ($h * 31 + $b) % 65521 }
  '{0:X4}' -f $h
}

# Field value per contract: ASCII printable only, ';' and '=' -> space,
# whitespace collapsed, trimmed, max 48 chars, empty -> '?'.
function Clean([string]$v) {
  if ($null -eq $v) { $v = '' }
  $v = $v -replace '[^\x20-\x7E]', ' ' -replace '[;=]', ' ' -replace ' {2,}', ' '
  $v = $v.Trim(' ')
  if ($v.Length -gt 48) { $v = $v.Substring(0, 48).TrimEnd(' ') }
  if ($v -eq '') { '?' } else { $v }
}

function Plural([int]$n, [string]$one, [string]$few, [string]$many) {
  if ($n -eq 1) { return $one }
  $m10 = $n % 10; $m100 = $n % 100
  if ($m10 -ge 2 -and $m10 -le 4 -and ($m100 -lt 12 -or $m100 -gt 14)) { return $few }
  $many
}

function Fmt1([double]$x) { $x.ToString('0.0', $inv) }
function DNum([string]$s) { if ($PL) { $s.Replace('.', ',') } else { $s } }
function Row([string]$label, [string]$value) { Write-Host ('  {0,-11} {1}' -f $label, $value) }

if ($SelfTest) {
  Write-Host ('{0}: HW1;os=linux -> {1}' -f $T.Self, (Get-HwSum 'HW1;os=linux'))
  return
}

# ---- OS, CPU, RAM --------------------------------------------------------------
$osName = 'Windows'; $ram = '?'
$os = Get-CimInstance -ClassName Win32_OperatingSystem -Property Caption, Version, TotalVisibleMemorySize
if ($os) {
  $osName = ('{0} {1}' -f $os.Caption, $os.Version).Trim()
  if ($os.TotalVisibleMemorySize) { $ram = Fmt1 ([double]$os.TotalVisibleMemorySize / 1048576) }
}

$cpuModel = '?'; $thr = '?'; $arm = $false
$cpus = @(Get-CimInstance -ClassName Win32_Processor -Property Name, NumberOfLogicalProcessors, Architecture)
if ($cpus.Count -gt 0) {
  $cpuModel = ($cpus[0].Name -replace '\s+', ' ').Trim()
  $n = 0; foreach ($c in $cpus) { $n += [int]$c.NumberOfLogicalProcessors }
  if ($n -gt 0) { $thr = [string]$n }
  if ($cpus[0].Architecture -eq 12 -or $cpus[0].Architecture -eq 5) { $arm = $true }
}
if ($env:PROCESSOR_ARCHITECTURE -eq 'ARM64' -or $env:PROCESSOR_ARCHITEW6432 -eq 'ARM64') { $arm = $true }

$isa = '?'; $isaLabel = $T.IsaPs5
if ($arm) { $isa = 'neon'; $isaLabel = 'NEON' }
else {
  $tAvx = 'System.Runtime.Intrinsics.X86.Avx' -as [type]
  $tAvx2 = 'System.Runtime.Intrinsics.X86.Avx2' -as [type]
  $tAvx512 = 'System.Runtime.Intrinsics.X86.Avx512F' -as [type]
  if ($tAvx2) {
    if ($tAvx512 -and $tAvx512::IsSupported) { $isa = 'avx512'; $isaLabel = 'AVX-512' }
    elseif ($tAvx2::IsSupported) { $isa = 'avx2'; $isaLabel = 'AVX2'; if (-not $tAvx512) { $isaLabel = 'AVX2 ' + $T.Isa512 } }
    elseif ($tAvx::IsSupported) { $isa = 'avx'; $isaLabel = 'AVX' }
    else { $isa = 'none'; $isaLabel = $T.None }
  }
}

# ---- GPUs ----------------------------------------------------------------------
# Registry entries of the display-adapter class (one per installed adapter instance).
$regEntries = @()
$classPath = 'SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}'
try {
  $cls = [Microsoft.Win32.Registry]::LocalMachine.OpenSubKey($classPath)
  if ($cls) {
    foreach ($sk in $cls.GetSubKeyNames()) {
      if ($sk -notmatch '^0\d{3}$') { continue }
      try {
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
        $regEntries += [pscustomobject]@{
          Key = $sk
          Desc = [string]$k.GetValue('DriverDesc')
          Match = ([string]$k.GetValue('MatchingDeviceId')).ToLowerInvariant()
          Mem = $mem
          Radeon = [string]$k.GetValue('RadeonSoftwareVersion')
        }
        $k.Close()
      } catch { }
    }
    $cls.Close()
  }
} catch { }

$haveLink = [bool](Get-Command -Name Get-PnpDeviceProperty -ErrorAction SilentlyContinue)
$used = @{}
$gpus = @()
foreach ($vc in @(Get-CimInstance -ClassName Win32_VideoController -Property Name, DriverVersion, AdapterCompatibility, PNPDeviceID)) {
  $pnp = [string]$vc.PNPDeviceID
  # Physical adapters only: PCI (and ACPI for Arm laptops). ROOT\, SWD\, USB\ are virtual/remote/DisplayLink.
  if ($pnp -notmatch '^(PCI|ACPI)\\') { continue }
  $name = ([string]$vc.Name -replace '\s+', ' ').Trim()
  $ven = ''; $dev = ''; $ssid = ''
  if ($pnp -match 'VEN_([0-9A-Fa-f]{4})') { $ven = $Matches[1].ToLowerInvariant() }
  if ($pnp -match 'DEV_([0-9A-Fa-f]{4})') { $dev = $Matches[1].ToLowerInvariant() }
  if ($pnp -match 'SUBSYS_([0-9A-Fa-f]{8})') { $ssid = $Matches[1].ToLowerInvariant() }

  $vendor = 'none'; $vendorLabel = [string]$vc.AdapterCompatibility
  switch ($ven) {
    '1002' { $vendor = 'amd' }
    '10de' { $vendor = 'nvidia' }
    '8086' { $vendor = 'intel' }
  }
  if ($vendor -eq 'none') {
    if ($vendorLabel -match 'Advanced Micro Devices|\bAMD\b|\bATI\b') { $vendor = 'amd' }
    elseif ($vendorLabel -match 'NVIDIA') { $vendor = 'nvidia' }
    elseif ($vendorLabel -match 'Intel') { $vendor = 'intel' }
  }
  if (-not $vendorLabel) { $vendorLabel = $T.Unknown }

  $basic = $name -match '^Microsoft Basic (Display|Render)'
  $hasDrv = -not $basic

  # Board: subsystem vendor + IDs (Windows exposes no board name).
  $sub = ''
  if ($ssid -and $ssid -ne '00000000') {
    $sv = $ssid.Substring(4, 4); $sd = $ssid.Substring(0, 4)
    $svName = switch ($sv) {
      '1002' { 'AMD' } '10de' { 'NVIDIA' } '8086' { 'Intel' } '1043' { 'ASUS' } '1462' { 'MSI' }
      '1458' { 'Gigabyte' } '1da2' { 'Sapphire' } '148c' { 'PowerColor' } '1682' { 'XFX' }
      '19da' { 'Zotac' } '3842' { 'EVGA' } '1849' { 'ASRock' } '196e' { 'PNY' } '1569' { 'Palit' }
      '10b0' { 'Gainward' } '1b4c' { 'KFA2/Galax' } '7377' { 'Colorful' } '17aa' { 'Lenovo' }
      '1028' { 'Dell' } '103c' { 'HP' } '1025' { 'Acer' } '144d' { 'Samsung' } '1414' { 'Microsoft' }
      '1558' { 'Clevo' } '1d05' { 'Tongfang' } default { '' }
    }
    $sub = ('{0} {1}:{2}' -f $svName, $sv, $sd).Trim()
  }

  # Integrated?
  $um = 0
  if ($vendor -eq 'intel' -and $name -notmatch 'Arc.*\b[AB]\d{3}|Xe MAX|Data Center GPU') { $um = 1 }
  # AMD discrete by name (RX, Pro, VII, FirePro, Instinct, R5-R9 nnn, HD nnnn, plain 3-digit rebrands);
  # everything else (Radeon Graphics, Vega 8, 780M, 8060S, HD 8650G, R7 Graphics ...) is an APU.
  $amdDiscrete = '\bRX\s*\d|Vega\s*(56|64|Frontier)|Radeon(\s*\(TM\))?\s*(VII|Pro\b)|FirePro|Instinct|\bR[5-9]\s*\d{3}\b|\bHD\s*\d{4}(?![GD0-9])|Radeon(\s*\(TM\))?\s*\d{3}(?![0-9MS])'
  if ($vendor -eq 'amd' -and $name -notmatch $amdDiscrete) { $um = 1 }
  if ($vendor -eq 'none' -and $pnp -match '^ACPI\\') { $um = 1 }

  # VRAM from the registry entry with the same DriverDesc (prefer the one whose MatchingDeviceId fits this device).
  $entry = $null
  $cands = @($regEntries | Where-Object { $_.Desc -eq $name -and -not $used.ContainsKey($_.Key) })
  foreach ($e in $cands) { if ($e.Match -and $pnp.ToLowerInvariant().StartsWith($e.Match)) { $entry = $e; break } }
  if (-not $entry -and $cands.Count -gt 0) { $entry = $cands[0] }
  if ($entry) { $used[$entry.Key] = $true }

  $vram = '?'; $vramMiB = 0; $vramNote = ''
  if ($entry -and $entry.Mem -gt 0 -and -not $basic) {
    if ($vendor -eq 'intel' -and $um -eq 1) { $vramNote = $T.VramShared }
    else {
      $vram = Fmt1 ([double]$entry.Mem / 1073741824)
      $vramMiB = [int64]($entry.Mem / 1048576)
      if ($um -eq 1) { $vramNote = $T.Carve }
    }
  } elseif ($um -eq 1) { $vramNote = $T.VramShared }
  else { $vramNote = $T.VramUnk }

  # Driver
  $dv = [string]$vc.DriverVersion
  $drv = '?'; $drvLabel = $T.None
  if ($hasDrv) {
    switch ($vendor) {
      'nvidia' {
        $p = $dv.Split('.')
        if ($p.Count -eq 4) {
          $digits = $p[2] + $p[3]
          if ($digits.Length -ge 5) { $d5 = $digits.Substring($digits.Length - 5); $drv = 'nvidia {0}.{1}' -f $d5.Substring(0, 3), $d5.Substring(3) }
        }
        if ($drv -eq '?') { $drv = "nvidia $dv" }
      }
      'amd' { if ($entry -and $entry.Radeon) { $drv = 'amd ' + $entry.Radeon } else { $drv = "amd $dv" } }
      'intel' { $drv = "intel $dv" }
      default { $drv = ('{0} {1}' -f $vendorLabel, $dv).Trim() }
    }
    $drvLabel = $drv
    if ($dv -and $drv -notlike "*$dv") { $drvLabel = "$drv (Windows $dv)" }
  } else {
    $drvLabel = "$($T.None) ($($T.NoDrv))"
  }

  # PCIe link (optional; Get-PnpDeviceProperty needs no admin rights)
  $pcie = '?'; $pcieLabel = $T.Unknown
  if ($haveLink -and $pnp -match '^PCI\\') {
    try {
      $props = @(Get-PnpDeviceProperty -InstanceId $pnp -KeyName 'DEVPKEY_PciDevice_CurrentLinkSpeed', 'DEVPKEY_PciDevice_CurrentLinkWidth' -ErrorAction Stop)
      $gen = 0; $width = 0
      foreach ($pr in $props) {
        if ($pr.KeyName -eq 'DEVPKEY_PciDevice_CurrentLinkSpeed' -and $null -ne $pr.Data) { $gen = [int]$pr.Data }
        if ($pr.KeyName -eq 'DEVPKEY_PciDevice_CurrentLinkWidth' -and $null -ne $pr.Data) { $width = [int]$pr.Data }
      }
      if ($gen -ge 1 -and $gen -le 6 -and $width -gt 0) {
        $pcie = '{0}x{1}' -f $gen, $width
        $gts = @('2.5', '5.0', '8.0', '16.0', '32.0', '64.0')[$gen - 1]
        $pcieLabel = '{0}.0 x{1} ({2} GT/s; {3})' -f $gen, $width, $gts, $T.Link
      }
    } catch { }
  }
  if ($ven -and $vendor -eq 'none') { $vendorLabel = "$vendorLabel (PCI $ven)" }

  $gpus += [pscustomobject]@{
    Name = $(if ($name) { $name } else { "PCI ${ven}:${dev}" })
    Sub = $sub; Vendor = $vendor; VendorLabel = $vendorLabel; Um = $um
    Vram = $vram; VramMiB = $vramMiB; VramNote = $vramNote
    HasDrv = $hasDrv; Drv = $drv; DrvLabel = $drvLabel; Pcie = $pcie; PcieLabel = $pcieLabel
    Score = ([int64]$hasDrv * 20000000) + ((1 - $um) * 10000000) + $vramMiB
  }
}

# ---- output --------------------------------------------------------------------
Write-Host ''
Write-Host $T.Title
Write-Host $T.Reads
Write-Host $T.Reads2
Write-Host $T.Safe
Write-Host $T.Never
Write-Host ''
Write-Host $T.Computer
Row $T.LOs $osName
Row $T.LCpu $cpuModel
if ($thr -ne '?') { Row $T.LThr ('{0} {1}' -f $thr, (Plural ([int]$thr) $T.Thr1 $T.Thr2 $T.Thr5)) } else { Row $T.LThr $T.Unknown }
Row $T.LIsa $isaLabel
if ($ram -ne '?') { Row $T.LRam ('{0} GiB' -f (DNum $ram)) } else { Row $T.LRam $T.Unknown }
Write-Host ''
Write-Host $T.Gpus

$best = $null; $bestN = 0; $ngpu = 0; $i = 0
foreach ($g in $gpus) {
  $i++
  if ($g.HasDrv) { $ngpu++ }
  Write-Host ('  GPU {0}' -f $i)
  Row $T.LChip $g.Name
  if ($g.Sub) { Row $T.LBoard $g.Sub }
  Row $T.LVendor $g.VendorLabel
  if ($g.Um -eq 1) { Row $T.LType $T.Integrated } else { Row $T.LType $T.Discrete }
  if ($g.Vram -eq '?') { Row $T.LVram $g.VramNote }
  else { Row $T.LVram (('{0} GiB {1}' -f (DNum $g.Vram), $g.VramNote).Trim()) }
  Row $T.LDrv $g.DrvLabel
  Row $T.LPcie $g.PcieLabel
  if ($null -eq $best -or $g.Score -gt $best.Score) { $best = $g; $bestN = $i }
}
if ($gpus.Count -eq 0) { Write-Host ('  ' + $T.NoGpu) }
else {
  Write-Host ('  {0} {1} {2} {3}; GPU {4} {5}.' -f $T.Found, $ngpu, (Plural $ngpu $T.Card1 $T.Card2 $T.Card5), $T.Working, $bestN, $T.Primary)
}
Write-Host ''

# ---- paste code ----------------------------------------------------------------
$c = [ordered]@{ os = 'windows'; gpu = '?'; sub = '?'; vendor = 'none'; vram = '?'; ngpu = [string]$ngpu; drv = '?'; ram = (Clean $ram); thr = (Clean $thr); isa = (Clean $isa); pcie = '?'; um = '0' }
if ($best) {
  $c.gpu = Clean $best.Name
  $c.sub = Clean $best.Sub
  $c.vendor = $best.Vendor
  $c.vram = $best.Vram
  if ($best.HasDrv) { $c.drv = Clean $best.Drv }
  $c.pcie = $best.Pcie
  $c.um = [string]$best.Um
}
$code = 'HW1'
foreach ($k in $c.Keys) { $code += ';{0}={1}' -f $k, $c[$k] }
$code += ';sum=' + (Get-HwSum $code)

$rule = '-' * 80
Write-Host $T.Code
Write-Host $rule
Write-Host ''
Write-Host $code -ForegroundColor Green
Write-Host ''
Write-Host $rule
Write-Host $T.Code2
Write-Host ''
} $SelfTest.IsPresent
