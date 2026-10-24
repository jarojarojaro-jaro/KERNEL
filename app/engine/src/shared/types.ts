// Shared types: the single source for the backend and the UI (CONTRACT.md "Typy").

export type Phase = 'license' | 'scan' | 'recommend' | 'download' | 'baseline' | 'optimize' | 'ready' | 'error';

export interface LicenseInfo { valid: boolean; plan?: string; sub?: string; expiresAt?: number; reason?: string }

export interface Gpu {
  vendor: 'nvidia' | 'amd' | 'intel' | 'apple'; name: string; vramGiB: number; unified: boolean;
  arch?: string /* gfx1100, sm_86, … */; driver?: string; backends: Backend[];
}

export type Backend = 'cuda' | 'rocm' | 'vulkan' | 'metal' | 'cpu';

export interface Hw {
  os: 'linux' | 'windows' | 'macos'; arch: 'x64' | 'arm64'; cpu: { name: string; cores: number; threads: number };
  ramGiB: number; gpus: Gpu[]; diskFreeGiB: number; scannedAt: number;
}

export interface MemPlan {
  weightsGiB: number; kvGiB: number; computeGiB: number; overheadGiB: number; totalGiB: number;
  budgetGiB: number; freeGiB: number;
}

export interface Option {
  id: string; modelId: string; name: string; family: string; params: string; quant: string;
  file: { repo: string; path: string; sizeBytes: number; sha256?: string }; ctx: number; ctxMax: number;
  kvType: 'q4_0' | 'q8_0' | 'f16';
  ub: number; backend: Backend; gpuIndex: number | null; mem: MemPlan; features: string[] /* mtp, tools, reasoning, vision */;
  score: number; why: string[];
}

export interface Recommendation {
  minCtx: number; pick: Option | null; alternatives: Option[];
  rejected: { modelId: string; quant: string; reason: string }[];
}

export interface Progress { phase: Phase; label: string; done: number; total: number; rate?: number; etaS?: number }

export interface BenchResult {
  engine: { id: string; version: string; backend: Backend }; config: EngineConfig;
  prefill: { tokens: number; tps: number; ttftS: number }; decode: { tokens: number; tps: number };
  deep?: { ctxTokens: number; prefillTps: number; decodeTps: number }; ctxOk: boolean; outputMd5: string; at: number;
}

export interface EngineConfig {
  engineId: string; modelPath: string; ctx: number; kvType: string; ub: number; b: number;
  flashAttn: boolean; threads?: number; spec?: 'none' | 'mtp' | 'lookup'; extraArgs: string[]; env: Record<string, string>;
}

export interface Candidate {
  id: string; label: { pl: string; en: string }; desc: { pl: string; en: string };
  status: 'pending' | 'running' | 'kept' | 'rejected' | 'failed'; result?: BenchResult; decodePct?: number; prefillPct?: number;
  sameOutput?: boolean; reason?: string;
}

export interface AppState {
  phase: Phase; license: LicenseInfo | null; hw: Hw | null; recommendation: Recommendation | null;
  chosen: Option | null; progress: Progress | null; baseline: BenchResult | null; candidates: Candidate[];
  best: BenchResult | null; ready: { endpoint: string; model: string; ctx: number } | null;
  error: { phase: Phase; message: string } | null; version: string;
}
