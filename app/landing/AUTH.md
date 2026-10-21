# Accounts: Google, GitHub, Hugging Face and username + password

The account step is two pages: sign in (`/pl/start/`, `/en/start/`, the default) and sign up (`/pl/start/register/`, `/en/start/register/`). Both talk only to `src/lib/auth` (through `src/lib/account/flow.ts`):

- `signInWith('google' | 'github' | 'huggingface')`
- `signInWithPassword(username, password)` and `signUpWithPassword(username, password)`
- `getSession()` and `signOut()`

The build-time env `PUBLIC_AUTH_PROVIDER` picks the backend:

| Value | File | What happens |
|---|---|---|
| `none` (default, committed in `.env`) | `src/lib/auth/none.ts` | **Preview.** The pages look and behave as final, with no prototype chip. All three provider tiles and both password forms are active and validated in the browser: sign-in checks the username format and a non-empty password; sign-up checks the username format, password ≥ 10 characters, matching repeat, and the Terms checkbox for "Załóż konto". The provider tiles carry an implied-consent line. Every call answers `unavailable`, and the step continues to `/<lang>/start/paths/`. Nothing is sent or stored, and the `onboarding` sessionStorage entry is cleared by the next steps. The pages never show "Zalogowano jako". |
| `authjs` | `src/lib/auth/authjs.ts` | Auth.js (`@auth/sveltekit`) on this app's own Node server (adapter-node). |

Any other value fails the build. A live backend needs **a real domain over https**. Google rejects redirect URIs on raw IP addresses (including private ones such as `192.168.10.230`) and plain `http`, except on `localhost`. For local testing, see [Local testing over an SSH tunnel](#local-testing-over-an-ssh-tunnel).

Placeholders below: `<domain>` is the production host (for example `enigmalabz.com`).

## Why Auth.js (and not Supabase)

The card offers four ways in, and Auth.js covers all of them in one small server we control:

| Requirement | Auth.js | Supabase Auth |
|---|---|---|
| Google, GitHub | built-in providers | built-in |
| Hugging Face | any OIDC issuer works: `issuer: 'https://huggingface.co'` | no Hugging Face provider; custom OIDC sign-in is not a standard feature |
| Username + password **without e-mail** | Credentials provider: we choose the username rules and the hash (argon2id) | password sign-in is keyed on e-mail or phone; a username-only account would need fake e-mail addresses |
| Minimal scopes (privacy §5) | per-provider `scope` | Google always asks for `email profile` |
| Data location | our EEA host plus one SQLite file | Supabase project region |

That is why `src/lib/auth` has no Supabase backend.

## Where secrets go

- `.env` is committed and holds public values only. Today that is just `PUBLIC_AUTH_PROVIDER=none`.
- Secrets go to `.env.local`, which is git-ignored, or to the service environment (systemd `EnvironmentFile=`). Do not commit them.

| Variable | Secret | Value |
|---|---|---|
| `PUBLIC_AUTH_PROVIDER` | no | `none` / `authjs` (build time) |
| `AUTH_SECRET` | **yes** | random 32+ bytes: `openssl rand -base64 33` |
| `AUTH_GOOGLE_ID` / `AUTH_GOOGLE_SECRET` | ID no / secret **yes** | Google OAuth client |
| `AUTH_GITHUB_ID` / `AUTH_GITHUB_SECRET` | ID no / secret **yes** | GitHub OAuth App |
| `AUTH_HUGGINGFACE_ID` / `AUTH_HUGGINGFACE_SECRET` | ID no / secret **yes** | Hugging Face OAuth app |
| `AUTH_DB` | no | path of the SQLite file, e.g. `/var/lib/enigma-labz/auth.sqlite`; back it up and keep it out of `build/` |
| `AUTH_TRUST_HOST` | no | `true` (behind the reverse proxy) |
| `ORIGIN` | no | `https://<domain>` (adapter-node) |

## Redirect URLs at a glance

| Provider | Production | Dev (SSH tunnel to `localhost:18433`) |
|---|---|---|
| Google: Authorized redirect URI | `https://<domain>/auth/callback/google` | `http://localhost:18433/auth/callback/google` |
| Google: Authorized JavaScript origin | `https://<domain>` | `http://localhost:18433` |
| GitHub: Authorization callback URL | `https://<domain>/auth/callback/github` | second app with `http://localhost:18433/auth/callback/github` |
| Hugging Face: Redirect URI | `https://<domain>/auth/callback/huggingface` | `http://localhost/auth/callback/huggingface` (any port is accepted on loopback) |

Username + password needs no redirect URL (`POST /auth/callback/password` and `/auth/callback/register` on our own server). After any sign-in, the app returns the user to `/<lang>/start/paths/` (`redirectTo` in `src/lib/account/flow.ts`).

## 1. Google Cloud Console

1. Open <https://console.cloud.google.com/>. In the project picker, choose **New project** and name it `Enigma LABZ`. Select it.
2. Go to **APIs & Services → OAuth consent screen**, which opens the Google Auth Platform. Click **Get started**:
   - **App information**: app name `Enigma LABZ`, plus a user support e-mail.
   - **Audience**: **External**.
   - **Contact information**: your e-mail. Accept the policy, then **Create**.
3. In **Branding**, set:
   - **App home page**: `https://<domain>/pl/`.
   - **Privacy policy**: `https://<domain>/pl/legal/privacy/`.
   - **Terms of service**: `https://<domain>/pl/legal/terms/`.
   - **Authorized domains**: `<domain>`.
   - A logo is optional; uploading one triggers brand verification.
4. In **Data Access → Add or remove scopes**, pick only `openid` and `.../auth/userinfo.email`. These are non-sensitive scopes, so no security assessment is needed. They match privacy policy §5.
5. **Audience → Test users**: while the app is in **Testing**, add the accounts allowed to sign in. When ready, click **Publish app** to move to **In production**.
6. In **Clients → Create client**:
   - **Application type**: **Web application**, name `Enigma LABZ web`.
   - **Authorized JavaScript origins**: `https://<domain>`. For dev, also add `http://localhost:18433`.
   - **Authorized redirect URIs**: `https://<domain>/auth/callback/google`. For dev, also add `http://localhost:18433/auth/callback/google`.
   - Click **Create**. Copy the **Client ID** and **Client secret** right away; the new console shows the secret only once.

Google rejects redirect URIs that use an IP address (private or public), `http` on anything but `localhost`, wildcards or `#fragments`. Changes can take a few minutes to apply.

## 2. GitHub OAuth App

1. Go to GitHub **Settings → Developer settings → OAuth Apps → New OAuth App**. For an app owned by the organization, start from **Organization settings → Developer settings → OAuth Apps** instead.
2. Fill in:
   - **Application name**: `Enigma LABZ`.
   - **Homepage URL**: `https://<domain>`.
   - **Authorization callback URL**: `https://<domain>/auth/callback/github`.
   - Leave **Enable Device Flow** off.
3. Click **Register application**. Copy the **Client ID**, then **Generate a new client secret** and copy it at once; GitHub shows it only once.
4. An OAuth App has exactly one callback URL. For local testing, register a second app (`Enigma LABZ (dev)`) with callback `http://localhost:18433/auth/callback/github`.
5. Scope: `user:email` only (set in `src/auth.ts` below; privacy policy §5).

## 3. Hugging Face OAuth app

1. Open <https://huggingface.co/settings/applications/new>. Owning it from an organization works the same way, under the organization's settings.
2. Fill in:
   - **Application name**: `Enigma LABZ`.
   - **Homepage URL**: `https://<domain>`.
   - Optionally, a **Logo URL**.
   - **Scopes**: tick only `openid` and `profile` (username and avatar; no e-mail, no repositories). These match privacy policy §5.
   - **Redirect URLs**: `https://<domain>/auth/callback/huggingface`. For dev, add `http://localhost/auth/callback/huggingface`; Hugging Face accepts any port on `http` loopback URIs.
3. Create the app with a client secret. Copy the **Client ID** and **Client secret** into `AUTH_HUGGINGFACE_ID` and `AUTH_HUGGINGFACE_SECRET`.
4. Discovery document: <https://huggingface.co/.well-known/openid-configuration>. Issuer `https://huggingface.co`, code flow with PKCE (S256), ID token RS256. Auth.js reads all of this from the issuer.
5. Branding: Hugging Face allows a custom button. The card uses the official `hf-logo.svg` from `huggingface/brand-assets` (`static/brand/huggingface.svg`), unaltered.

## 4. Auth.js on the server

Auth.js runs inside SvelteKit, so the site needs a Node server instead of the static export. Prerendered pages stay prerendered; only `/auth/*` runs per request.

1. Install the packages:
   ```sh
   bun add @auth/sveltekit @node-rs/argon2 better-sqlite3
   bun add -d @sveltejs/adapter-node @types/better-sqlite3
   ```
2. In `svelte.config.js`, replace `@sveltejs/adapter-static` with `adapter-node`: `import adapter from '@sveltejs/adapter-node'` and `adapter: adapter()`. Keep `prerender.entries`.
3. Create `src/auth.ts`:
   ```ts
   import { SvelteKitAuth, CredentialsSignin } from '@auth/sveltekit';
   import Google from '@auth/sveltekit/providers/google';
   import GitHub from '@auth/sveltekit/providers/github';
   import Credentials from '@auth/sveltekit/providers/credentials';
   import { Algorithm, hash, verify } from '@node-rs/argon2';
   import Database from 'better-sqlite3';
   import { randomUUID } from 'node:crypto';
   import { env } from '$env/dynamic/private';

   const db = new Database(env.AUTH_DB ?? 'auth.sqlite');
   db.pragma('journal_mode = WAL');
   db.exec(`
   	create table if not exists users (
   		id text primary key,
   		provider text not null,   -- google | github | huggingface | password
   		subject text not null,    -- provider account id; lower-cased username for password accounts
   		username text,
   		email text,               -- only what Google / GitHub share; never asked for password accounts
   		pw_hash text,             -- argon2id, password accounts only
   		created_at integer not null,
   		unique (provider, subject)
   	);
   	create table if not exists attempts (
   		key text primary key,     -- 'u:<username>' or 'ip:<address>'
   		fails integer not null,
   		locked_until integer not null,
   		updated_at integer not null
   	);`);

   // OWASP minimum for argon2id: 19 MiB, 2 passes, 1 lane.
   const ARGON = { algorithm: Algorithm.Argon2id, memoryCost: 19456, timeCost: 2, parallelism: 1 };
   // Verified against when the username does not exist, so a wrong username costs the same time.
   const DUMMY = await hash(randomUUID(), ARGON);
   const USERNAME = /^[A-Za-z0-9._-]{3,32}$/; // same rule as the card
   const LIMIT = { u: 5, ip: 20 }; // failed attempts before a lockout
   const LOCK_MS = 15 * 60_000; // "Spróbuj ponownie za 15 minut"
   const KEEP_MS = 24 * 3600_000; // privacy policy §5 / §10: deleted within 24 h

   class Invalid extends CredentialsSignin { code = 'invalid'; }
   class Taken extends CredentialsSignin { code = 'taken'; }
   class Locked extends CredentialsSignin { code = 'locked'; }

   /** Caddy appends the real peer as the LAST X-Forwarded-For entry; earlier entries are client-supplied. */
   const clientIp = (request: Request) => request.headers.get('x-forwarded-for')?.split(',').at(-1)?.trim() || 'unknown';

   function guard(keys: string[]) {
   	const now = Date.now();
   	db.prepare('delete from attempts where updated_at < ?').run(now - KEEP_MS);
   	for (const key of keys) {
   		const row = db.prepare('select locked_until from attempts where key = ?').get(key) as { locked_until: number } | undefined;
   		if (row && row.locked_until > now) throw new Locked();
   	}
   }

   function fail(keys: string[]) {
   	const now = Date.now();
   	for (const key of keys) {
   		const { fails } = db
   			.prepare('insert into attempts values (?, 1, 0, ?) on conflict (key) do update set fails = fails + 1, updated_at = excluded.updated_at returning fails')
   			.get(key, now) as { fails: number };
   		if (fails >= (key.startsWith('u:') ? LIMIT.u : LIMIT.ip)) db.prepare('update attempts set fails = 0, locked_until = ? where key = ?').run(now + LOCK_MS, key);
   	}
   }

   function parse(c: Partial<Record<'username' | 'password', unknown>>) {
   	const username = String(c.username ?? '').trim();
   	const password = String(c.password ?? '');
   	if (!USERNAME.test(username) || password.length < 10 || password.length > 256) throw new Invalid();
   	return { username, password, subject: username.toLowerCase() };
   }

   const fields = { username: {}, password: {} };

   export const { handle } = SvelteKitAuth({
   	trustHost: true,
   	session: { strategy: 'jwt' }, // required by Credentials; no adapter, users live in `users`
   	providers: [
   		Google({ clientId: env.AUTH_GOOGLE_ID, clientSecret: env.AUTH_GOOGLE_SECRET, authorization: { params: { scope: 'openid email' } } }),
   		GitHub({ clientId: env.AUTH_GITHUB_ID, clientSecret: env.AUTH_GITHUB_SECRET, authorization: { params: { scope: 'user:email' } } }),
   		{
   			id: 'huggingface',
   			name: 'Hugging Face',
   			type: 'oidc',
   			issuer: 'https://huggingface.co',
   			clientId: env.AUTH_HUGGINGFACE_ID,
   			clientSecret: env.AUTH_HUGGINGFACE_SECRET,
   			checks: ['pkce', 'state'],
   			authorization: { params: { scope: 'openid profile' } },
   			profile: (p) => ({ id: p.sub, name: p.preferred_username ?? p.name ?? null, email: null, image: null })
   		},
   		Credentials({
   			id: 'password',
   			name: 'Password',
   			credentials: fields,
   			async authorize(c, request) {
   				const { password, subject } = parse(c);
   				const keys = [`u:${subject}`, `ip:${clientIp(request)}`];
   				guard(keys);
   				const row = db.prepare("select id, username, pw_hash from users where provider = 'password' and subject = ?").get(subject) as
   					| { id: string; username: string; pw_hash: string }
   					| undefined;
   				const ok = await verify(row?.pw_hash ?? DUMMY, password);
   				if (!row || !ok) {
   					fail(keys);
   					throw new Invalid();
   				}
   				db.prepare('delete from attempts where key = ?').run(keys[0]);
   				return { id: row.id, name: row.username };
   			}
   		}),
   		Credentials({
   			id: 'register',
   			name: 'Register',
   			credentials: fields,
   			async authorize(c, request) {
   				const { username, password, subject } = parse(c);
   				const ip = `ip:${clientIp(request)}`;
   				guard([ip]);
   				const id = randomUUID();
   				try {
   					db.prepare("insert into users (id, provider, subject, username, pw_hash, created_at) values (?, 'password', ?, ?, ?, ?)").run(id, subject, username, await hash(password, ARGON), Date.now());
   				} catch {
   					fail([ip]); // also slows down username enumeration
   					throw new Taken();
   				}
   				return { id, name: username };
   			}
   		})
   	],
   	callbacks: {
   		async jwt({ token, user, account, profile }) {
   			if (!account) return token; // later requests: the token already carries sub / name / provider
   			if (account.type === 'credentials') return { sub: user.id, name: user.name, provider: 'password' };
   			const name = account.provider === 'github' ? String(profile?.login ?? '') || null : (user.name ?? null);
   			const email = account.provider === 'huggingface' ? null : (user.email ?? null);
   			const { id } = db
   				.prepare('insert into users (id, provider, subject, username, email, created_at) values (?, ?, ?, ?, ?, ?) on conflict (provider, subject) do update set username = excluded.username, email = excluded.email returning id')
   				.get(randomUUID(), account.provider, account.providerAccountId, name, email, Date.now()) as { id: string };
   			return { sub: id, name, email, provider: account.provider };
   		},
   		// src/lib/auth/authjs.ts reads user.id, user.name, user.email and user.provider from /auth/session
   		session({ session, token }) {
   			return { ...session, user: { id: token.sub, name: token.name ?? null, email: token.email ?? null, provider: token.provider } };
   		}
   	}
   });
   ```
   Notes:
   - The provider ids `google`, `github`, `huggingface`, `password` and `register` are the ones `src/lib/auth/authjs.ts` calls.
   - The error codes `invalid`, `taken` and `locked` map to the card's messages.
   - Passwords are hashed only on the server. The browser sends them once, over https, and no avatar or name is stored beyond the username.
4. In `src/hooks.server.ts`, chain the Auth.js handle in front of the existing language handle:
   ```ts
   import { sequence } from '@sveltejs/kit/hooks';
   import { handle as auth } from './auth';
   export const handle = sequence(auth, lang); // `lang` = the current handle, renamed
   ```
5. Set `PUBLIC_AUTH_PROVIDER=authjs` and the secrets from [Where secrets go](#where-secrets-go).
6. Build and run:
   - Run `bun run build`, then `ORIGIN=https://<domain> node build` (port 3000) under systemd.
   - Put it behind Caddy:
     ```
     <domain> {
     	reverse_proxy 127.0.0.1:3000
     }
     ```
     Caddy terminates https and appends the client address to `X-Forwarded-For` (read by `clientIp`).
   - `scripts/serve.ts` serves static files only and has no `/auth`.
7. Check:
   - `https://<domain>/auth/providers` lists `google`, `github`, `huggingface`, `password` and `register`.
   - Each button and the password form return you to `/pl/start/paths/` with "Zalogowano jako …" under the step.
   - Six wrong passwords for one username give "Za dużo nieudanych prób".

## Local testing over an SSH tunnel

The dev box is reached by a LAN IP, which Google does not accept. Tunnel the dev server so your browser sees `http://localhost`:

```sh
# on the laptop
ssh -N -L 18433:127.0.0.1:18433 jaro@192.168.10.230
# on the dev box (keep the port: it is the one registered with Google / GitHub)
cd ~/KERNEL/app/landing && bun run dev
```

Then open `http://localhost:18433/pl/start/` on the laptop. The Auth.js `handle` hook also runs under `vite dev`, so OAuth and passwords work before the adapter switch. Use the dev redirect URIs from the table above (the GitHub dev app, Google's localhost origin, Hugging Face's port-less loopback URI).

## Switch-on checklist

- [ ] Domain with https in place. `PUBLIC_SITE_ORIGIN` is set for the build (`src/lib/site/public.ts`).
- [ ] Google client, GitHub app and Hugging Face app created with the redirect URLs above. The Google app is **In production**.
- [ ] `PUBLIC_AUTH_PROVIDER=authjs` and the secrets are set on the build or server, not in git. `AUTH_DB` is on a backed-up disk.
- [ ] Legal pages. Privacy policy §5, §8, §9 and §10, the Terms (§ 5, § 14) and the Cookie Policy already describe Hugging Face, username + argon2id accounts without e-mail, the 24 h sign-in protection records and the Auth.js cookies. Remove the "po uruchomieniu kont" / "once accounts launch" badges in the cookie tables, and name the host in §8.
- [ ] In `src/lib/onboarding/copy.ts`, change the `prototype` / `protoChip` wording so it no longer says sign-in is not real.
