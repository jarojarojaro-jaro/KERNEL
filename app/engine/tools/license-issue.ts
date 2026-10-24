// Issues Enigma subscription keys.
//   bun tools/license-issue.ts --sub X --plan pro|team|trial --days 30 [--out FILE]
// First run creates the Ed25519 issuing key in ~/.secrets/enigma-license-ed25519.pem (mode 600) and prints the public
// key to embed as LICENSE_PUBLIC_KEY in src/server/license.ts. The private key never enters the repository.
import { generateKeyPairSync, createPublicKey } from 'node:crypto';
import { chmodSync, existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';
import { parseArgs } from 'node:util';
import {
  LICENSE_PUBLIC_KEY, privateKeyFromPem, rawFromPublicKey, signLicense, verifyLicense, type LicensePayload, type Plan,
} from '../src/server/license.ts';

const { values } = parseArgs({
  options: {
    sub: { type: 'string' },
    plan: { type: 'string', default: 'pro' },
    days: { type: 'string', default: '30' },
    out: { type: 'string' },
    key: { type: 'string', default: join(homedir(), '.secrets', 'enigma-license-ed25519.pem') },
  },
});

const keyFile = values.key;
if (!existsSync(keyFile)) {
  const { privateKey } = generateKeyPairSync('ed25519');
  mkdirSync(join(keyFile, '..'), { recursive: true, mode: 0o700 });
  writeFileSync(keyFile, privateKey.export({ format: 'pem', type: 'pkcs8' }), { mode: 0o600 });
  chmodSync(keyFile, 0o600);
  console.error(`created issuing key ${keyFile} (mode 600)`);
}
const priv = privateKeyFromPem(readFileSync(keyFile, 'utf8'));
const pub = rawFromPublicKey(createPublicKey(priv));
console.error(`public key (LICENSE_PUBLIC_KEY): ${pub}`);
if (pub !== LICENSE_PUBLIC_KEY) {
  console.error('warning: src/server/license.ts embeds a different public key; keys from this issuer will not verify');
}

if (!values.sub) {
  console.error('no --sub given: key pair checked, nothing issued');
  process.exit(0);
}
const plan = values.plan as Plan;
if (plan !== 'pro' && plan !== 'team' && plan !== 'trial') throw new Error(`--plan must be pro|team|trial, got ${values.plan}`);
const days = Number(values.days);
if (!Number.isFinite(days) || days <= 0) throw new Error('--days must be a positive number');
const iat = Math.floor(Date.now() / 1000);
const payload: LicensePayload = { v: 1, sub: values.sub, plan, iat, exp: iat + Math.round(days * 86400), features: ['optimize', 'models'] };
const key = signLicense(payload, priv);
const check = verifyLicense(key, iat, pub);
if (!check.valid) throw new Error(`self-check failed: ${check.reason}`);
if (values.out) {
  writeFileSync(values.out, key + '\n', { mode: 0o600 });
  chmodSync(values.out, 0o600);
  console.error(`key written to ${values.out} (mode 600), expires ${new Date(payload.exp * 1000).toISOString()}`);
} else {
  console.log(key);
}
