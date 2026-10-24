import { describe, expect, test } from 'bun:test';
import { generateKeyPairSync } from 'node:crypto';
import { rawFromPublicKey, signLicense, verifyLicense, type LicensePayload } from '../src/server/license.ts';

const { privateKey, publicKey } = generateKeyPairSync('ed25519');
const pub = rawFromPublicKey(publicKey);
const now = 1_800_000_000;
const base: LicensePayload = { v: 1, sub: 'acct-1', plan: 'pro', iat: now - 10, exp: now + 86400, features: ['optimize', 'models'] };

describe('license', () => {
  test('valid key', () => {
    expect(verifyLicense(signLicense(base, privateKey), now, pub)).toEqual({ valid: true, plan: 'pro', sub: 'acct-1', expiresAt: now + 86400 });
  });

  test('expired', () => {
    const r = verifyLicense(signLicense({ ...base, exp: now - 1 }, privateKey), now, pub);
    expect(r.valid).toBe(false);
    expect(r.reason).toBe('expired');
  });

  test('tampered payload fails the signature', () => {
    const key = signLicense(base, privateKey);
    const [body, sig] = key.slice('ENIGMA-'.length).split('.');
    const forged = Buffer.from(JSON.stringify({ ...base, plan: 'team' })).toString('base64url');
    expect(body).toBeDefined();
    expect(verifyLicense(`ENIGMA-${forged}.${sig}`, now, pub).reason).toBe('signature');
  });

  test('other issuer fails', () => {
    const other = generateKeyPairSync('ed25519').privateKey;
    expect(verifyLicense(signLicense(base, other), now, pub).reason).toBe('signature');
  });

  test('bad format', () => {
    expect(verifyLicense('hello', now, pub).reason).toBe('format');
    expect(verifyLicense('ENIGMA-abc', now, pub).reason).toBe('format');
  });

  test('missing features', () => {
    expect(verifyLicense(signLicense({ ...base, features: ['models'] }, privateKey), now, pub).reason).toBe('features');
  });

  test('embedded public key verifies the lab test key when present', async () => {
    const f = Bun.file(`${process.env.HOME}/.secrets/enigma-test-license.txt`);
    if (!(await f.exists())) return;
    const r = verifyLicense(await f.text());
    expect(r.reason === undefined || r.reason === 'expired').toBe(true);
  });
});
