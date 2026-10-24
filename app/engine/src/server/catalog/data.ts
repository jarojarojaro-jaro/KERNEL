// Catalog schema (data/catalog.json) and typed access. The JSON is generated/refreshed by `refresh.ts`.
import catalogJson from '../../../data/catalog.json';
import type { Backend } from '../../shared/types.ts';

export type KvType = 'q4_0' | 'q8_0' | 'f16';

/** Attention layers of one kind and their cached K/V widths per token (elements). */
export interface AttnGroup { layers: number; kvHeads: number; keyLen: number; valueLen: number }

export interface ModelArch {
  /** Where the numbers come from: `gguf:<file>` (local header) or `config:<repo>` (HF config.json). */
  source: string;
  arch: string;
  nLayer: number;
  nEmbd: number;
  nVocab: number;
  tiedEmbd: boolean;
  /** Full-attention layers: cache grows with the context. */
  full: AttnGroup;
  /** Sliding-window layers: cache = pad256(window + ubatch) cells. */
  swa: AttnGroup & { window: number };
  /** MTP/NextN blocks present in the GGUF (draft context when speculation is on). */
  nextn: AttnGroup;
  /** Recurrent state per sequence (GDN / shortconv), MiB. */
  stateMiB: number;
  /** Extra MTP draft buffers of our engine (reduced draft vocab head + embedding + requant cache), MiB. */
  mtpExtraMiB: number;
}

export interface QuantFile {
  quant: string;
  repo: string;
  path: string;
  sizeBytes: number;
  sha256: string;
  /** token_embd bytes kept in host memory by llama.cpp (untied heads); 0 for tied embeddings. */
  hostEmbdBytes: number;
  /** Bytes read per decoded token, GB (dense: GPU weights; MoE: shared + active experts). */
  bTokGB: number;
  /** Quality retained vs the full-precision model (from published/measured KLD), 0..1. */
  qualityFactor: number;
}

export interface MeasuredSpeed {
  gpu: string; backend: Backend; quant: string;
  /** Upstream llama.cpp plain decode (tg128 / server), t/s. */
  decodeTps: number;
  source: string;
}

export interface CatalogModel {
  id: string;
  name: string;
  family: string;
  params: string;
  paramsB: number;
  activeB: number;
  kind: 'dense' | 'moe' | 'hybrid';
  /** Quality score for local chat / agentic coding (Artificial Analysis index scale), see qualitySource. */
  quality: number;
  qualitySource: string;
  license: string;
  ctxMax: number;
  features: string[];
  /** First upstream llama.cpp build (`b<N>`) that runs the model; 0 = every release we pin. Compared with the pinned
   *  upstream tag in data/engines.json; older pins reject the model (`engine_too_old:b<N>`). */
  minUpstreamBuild: number;
  engineNote?: string;
  /** Small enough to offer on CPU-only machines. */
  cpuTier: boolean;
  arch: ModelArch;
  quants: QuantFile[];
  measured: MeasuredSpeed[];
  /** HF repo whose config.json describes the architecture when no local GGUF is available. */
  configRepo: string;
  /** The GGUF files carry MTP/NextN blocks (used only when no local GGUF can confirm it). */
  mtpInFile: boolean;
}

export interface GpuSpec {
  id: string; name: string; vendor: 'nvidia' | 'amd' | 'intel' | 'apple'; vramGiB: number | null;
  bwGBs: number; unified: boolean;
}

export interface License { name: string; commercial: 'yes' | 'conditional'; note: { pl: string; en: string } }

export interface Catalog {
  _meta: Record<string, string>;
  gpus: GpuSpec[];
  licenses: Record<string, License>;
  models: CatalogModel[];
}

export const CATALOG = catalogJson as Catalog;
