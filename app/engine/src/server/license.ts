// Subscription keys: "ENIGMA-" + base64url(JSON payload) + "." + base64url(Ed25519 signature of the payload segment).
// Verified offline against the public key below; the private key lives only in ~/.secrets (tools/license-issue.ts).
import { createPrivateKey, createPublicKey, sign, verify, type KeyObject } from 'node:crypto';
import { existsSync, readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname } from 'node:path';
import type { LicenseInfo } from '../shared/types.ts';
import { paths } from './paths.ts';

/** Raw 32-byte Ed25519 public key (base64url) of the issuing key in ~/.secrets/enigma-license-ed25519.pem. */
export const LICENSE_PUBLIC_KEY = 'EPuQXUXCh7I29pFQYIEgkMDN-FWBiKj6e6xuiPmStNY';

export const KEY_PREFIX = 'ENIGMA-';
export type Plan = 'pro' | 'team' | 'trial';
export interface LicensePayload { v: 1; sub: string; plan: Plan; exp: number; iat: number; features: string[] }

const SPKI_ED25519_PREFIX = Buffer.from('302a300506032b6570032100', 'hex');

export function publicKeyFromRaw(rawB64url: string): KeyObject {
  const raw = Buffer.from(rawB64url, 'base64url');
  if (raw.length !== 32) throw new Error('Ed25519 public key must be 32 bytes');
  return createPublicKey({ key: Buffer.concat([SPKI_ED25519_PREFIX, raw]), format: 'der', type: 'spki' });
}

export function rawFromPublicKey(key: KeyObject): string {
  const der = key.export({ format: 'der', type: 'spki' });
  return der.subarray(der.length - 32).toString('base64url');
}

export function signLicense(payload: LicensePayload, privateKey: KeyObject): string {
  const body = Buffer.from(JSON.stringify(payload)).toString('base64url');
  const sig = sign(null, Buffer.from(body), privateKey).toString('base64url');
  return `${KEY_PREFIX}${body}.${sig}`;
}

export function privateKeyFromPem(pem: string): KeyObject {
  return createPrivateKey(pem);
}

function isPayload(v: unknown): v is LicensePayload {
  if (typeof v !== 'object' || v === null) return false;
  const p = v as Record<string, unknown>;
  return p.v === 1 && typeof p.sub === 'string' && (p.plan === 'pro' || p.plan === 'team' || p.plan === 'trial') &&
    typeof p.exp === 'number' && typeof p.iat === 'number' && Array.isArray(p.features) &&
    p.features.every((f) => typeof f === 'string');
}

export function verifyLicense(key: string, nowS = Date.now() / 1000, publicKey: string = LICENSE_PUBLIC_KEY): LicenseInfo {
  const k = key.trim();
  if (!k.startsWith(KEY_PREFIX)) return { valid: false, reason: 'format' };
  const [body, sig, ...rest] = k.slice(KEY_PREFIX.length).split('.');
  if (!body || !sig || rest.length > 0) return { valid: false, reason: 'format' };
  let ok = false;
  try {
    ok = verify(null, Buffer.from(body), publicKeyFromRaw(publicKey), Buffer.from(sig, 'base64url'));
  } catch {
    ok = false;
  }
  if (!ok) return { valid: false, reason: 'signature' };
  let payload: unknown;
  try {
    payload = JSON.parse(Buffer.from(body, 'base64url').toString('utf8'));
  } catch {
    return { valid: false, reason: 'format' };
  }
  if (!isPayload(payload)) return { valid: false, reason: 'format' };
  const info: LicenseInfo = { valid: true, plan: payload.plan, sub: payload.sub, expiresAt: payload.exp };
  if (payload.exp <= nowS) return { ...info, valid: false, reason: 'expired' };
  if (!payload.features.includes('optimize') || !payload.features.includes('models')) {
    return { ...info, valid: false, reason: 'features' };
  }
  return info;
}

interface StoredConfig { licenseKey?: string }

function readConfig(): StoredConfig {
  const file = paths().config;
  if (!existsSync(file)) return {};
  try {
    return JSON.parse(readFileSync(file, 'utf8')) as StoredConfig;
  } catch {
    return {};
  }
}

export function storedLicenseKey(): string | null {
  return readConfig().licenseKey ?? null;
}

export function storeLicenseKey(key: string): void {
  const file = paths().config;
  mkdirSync(dirname(file), { recursive: true });
  writeFileSync(file, JSON.stringify({ ...readConfig(), licenseKey: key.trim() }, null, 2), { mode: 0o600 });
}
