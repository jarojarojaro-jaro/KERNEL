# Accounts: Google, GitHub and e-mail sign-in

The account step (`/pl/start/`, `/en/start/`) talks only to `src/lib/auth` (`signInWith('google' | 'github')`, `signInWithEmail(email)`, `getSession()`, `signOut()`). The build-time env `PUBLIC_AUTH_PROVIDER` picks the backend:

| Value | File | What happens |
|---|---|---|
| `none` (default, committed in `.env`) | `src/lib/auth/none.ts` | No backend. Google/GitHub buttons are visible but disabled; the "Logowanie wkrótce: zapisz się na listę" note points to the e-mail field, which becomes the waitlist sign-up (kept in this browser tab only, nothing is sent). |
| `authjs` | `src/lib/auth/authjs.ts` | Auth.js (`@auth/sveltekit`) on this app's own Node server. Needs `adapter-node`. |
| `supabase` | `src/lib/auth/supabase.ts` | Supabase Auth over its REST API. Works with the current static build. |

Any other value fails the build. Both live backends need **a real domain over https**. Google rejects redirect URIs on raw IP addresses (including private ones such as `192.168.10.230`) and plain `http`, with `localhost` as the only exception. For local testing, see [Local testing over an SSH tunnel](#local-testing-over-an-ssh-tunnel).

Placeholders below: `<domain>` is the production host (for example `podkret.pl`), and `<ref>` is the Supabase project reference.

## Where secrets go

- `.env` is committed and holds public values only: `PUBLIC_AUTH_PROVIDER`, `PUBLIC_SUPABASE_URL` and `PUBLIC_SUPABASE_ANON_KEY` (both empty by default).
- Secrets go to `.env.local`, which is git-ignored. Vite and SvelteKit load it on top of `.env`. On the server, put them in the service environment (systemd `EnvironmentFile=`, for example). Do not commit them.

| Variable | Backend | Secret | Value |
|---|---|---|---|
| `PUBLIC_AUTH_PROVIDER` | all | no | `none` / `authjs` / `supabase` |
| `AUTH_SECRET` | authjs | **yes** | random 32+ bytes: `openssl rand -base64 33` (or `npx auth secret`) |
| `AUTH_GOOGLE_ID` / `AUTH_GOOGLE_SECRET` | authjs | ID no / secret **yes** | from the Google OAuth client |
| `AUTH_GITHUB_ID` / `AUTH_GITHUB_SECRET` | authjs | ID no / secret **yes** | from the GitHub OAuth App |
| `AUTH_TRUST_HOST` | authjs | no | `true` behind a reverse proxy |
| `ORIGIN` | authjs (adapter-node) | no | `https://<domain>` |
| `EMAIL_SERVER` / `EMAIL_FROM` | authjs (magic link) | server **yes** | `smtp://user:pass@smtp.example.eu:587`, `Podkręt <konto@<domain>>` |
| `DATABASE_URL` | authjs (magic link) | **yes** | database for the Auth.js adapter (verification tokens, users) |
| `PUBLIC_SUPABASE_URL` | supabase | no | `https://<ref>.supabase.co` |
| `PUBLIC_SUPABASE_ANON_KEY` | supabase | no (public by design) | anon / publishable key. **Never** use the `service_role` / secret key in the browser. |

## Redirect URLs at a glance

| | Auth.js | Supabase |
|---|---|---|
| Google "Authorized redirect URIs" | `https://<domain>/auth/callback/google` | `https://<ref>.supabase.co/auth/v1/callback` |
| GitHub "Authorization callback URL" | `https://<domain>/auth/callback/github` | `https://<ref>.supabase.co/auth/v1/callback` |
| Magic-link landing | `https://<domain>/auth/callback/nodemailer` (Auth.js handles it) | Supabase sends the user to `redirectTo` (`/pl/start/paths/`) |
| Google "Authorized JavaScript origins" | `https://<domain>` | `https://<domain>` |
| Dev (SSH tunnel) | add `http://localhost:18433` and `http://localhost:18433/auth/callback/google` | add `http://localhost:18433/**` to Supabase Redirect URLs |

After sign-in, the app returns the user to `/<lang>/start/paths/` (`redirectTo` in `+page.svelte`).

## 1. Google Cloud Console

1. Open <https://console.cloud.google.com/>. In the project picker, choose **New project** and name it `Podkret`. Select the new project.
2. Go to **APIs & Services → OAuth consent screen**. This opens the "Google Auth Platform". Click **Get started**:
   - **App information**: app name `Podkręt`, plus a user support e-mail.
   - **Audience**: **External**.
   - **Contact information**: your e-mail. Accept the user data policy, then **Create**.
3. In **Branding**, set:
   - **App home page**: `https://<domain>/pl/`.
   - **Privacy policy**: `https://<domain>/pl/legal/privacy/`.
   - **Terms of service**: `https://<domain>/pl/legal/terms/`.
   - **Authorized domains**: `<domain>`.
   - Optionally, a 120×120 logo. Uploading a logo triggers brand verification.
4. In **Data Access → Add or remove scopes**, pick only `openid` and `.../auth/userinfo.email`. These are non-sensitive scopes, so no security assessment is needed. They match the Privacy Policy §5 ("`openid email`"). Adding `profile` (name, avatar) requires updating the policy first.
5. **Audience → Test users**: while the app is in **Testing**, add the Google accounts that may sign in. When ready, click **Publish app** to move to **In production**.
6. In **Clients → Create client**:
   - **Application type**: **Web application**. Name: `Podkret web`.
   - **Authorized JavaScript origins**: `https://<domain>`. For dev, also add `http://localhost:18433`.
   - **Authorized redirect URIs**: use the URL for the chosen backend from the table above.
     - Auth.js: `https://<domain>/auth/callback/google`. For dev, also add `http://localhost:18433/auth/callback/google`.
     - Supabase: `https://<ref>.supabase.co/auth/v1/callback`.
   - Click **Create**. Copy the **Client ID** and **Client secret**, or download the JSON. The secret is shown only once in the new console.

Google rejects redirect URIs that use an IP address (private or public), `http` on anything other than `localhost`, wildcards or `#fragments`. Changes can take a few minutes to apply.

## 2. GitHub OAuth App

1. Go to GitHub **Settings → Developer settings → OAuth Apps → New OAuth App**. To have the organization own the app, start from **Organization settings → Developer settings → OAuth Apps** instead.
2. Fill in:
   - **Application name**: `Podkręt`.
   - **Homepage URL**: `https://<domain>`.
   - **Application description**: optional.
   - **Authorization callback URL**:
     - Auth.js: `https://<domain>/auth/callback/github`.
     - Supabase: `https://<ref>.supabase.co/auth/v1/callback`.
   - Leave **Enable Device Flow** off.
3. Click **Register application**. Copy the **Client ID**, then **Generate a new client secret** and copy it right away. GitHub shows it only once.
4. An OAuth App has exactly one callback URL. For local testing, register a second app (`Podkręt (dev)`) with callback `http://localhost:18433/auth/callback/github`. GitHub allows `http://localhost`.
5. Scope: request only `user:email`, as stated in the Privacy Policy §5. The Auth.js snippet below sets it. Supabase requests `user:email` by default.

## 3a. Backend: Auth.js (`PUBLIC_AUTH_PROVIDER=authjs`)

Auth.js runs inside SvelteKit, so the site needs a Node server instead of the static export. Prerendered pages stay prerendered; only `/auth/*` runs at request time.

1. Install the packages:
   ```sh
   bun add @auth/sveltekit nodemailer
   bun add -d @sveltejs/adapter-node
   # magic link needs a database adapter, e.g.:
   bun add @auth/pg-adapter pg
   ```
2. In `svelte.config.js`, replace `@sveltejs/adapter-static` with `adapter-node`: `import adapter from '@sveltejs/adapter-node'` and `adapter: adapter()`. Keep `prerender.entries`.
3. Create `src/auth.ts`:
   ```ts
   import { SvelteKitAuth } from '@auth/sveltekit';
   import Google from '@auth/sveltekit/providers/google';
   import GitHub from '@auth/sveltekit/providers/github';
   import Nodemailer from '@auth/sveltekit/providers/nodemailer';
   import PostgresAdapter from '@auth/pg-adapter';
   import pg from 'pg';
   import { env } from '$env/dynamic/private';

   export const { handle } = SvelteKitAuth({
   	trustHost: true,
   	adapter: PostgresAdapter(new pg.Pool({ connectionString: env.DATABASE_URL })),
   	session: { strategy: 'jwt' },
   	providers: [
   		// AUTH_GOOGLE_ID / AUTH_GOOGLE_SECRET and AUTH_GITHUB_ID / AUTH_GITHUB_SECRET are read automatically
   		Google({ authorization: { params: { scope: 'openid email' } } }),
   		GitHub({ authorization: { params: { scope: 'user:email' } } }),
   		Nodemailer({ server: env.EMAIL_SERVER, from: env.EMAIL_FROM })
   	],
   	callbacks: {
   		jwt({ token, account }) {
   			if (account) token.provider = account.provider;
   			return token;
   		},
   		// src/lib/auth/authjs.ts reads user.id and user.provider from /auth/session
   		session({ session, token }) {
   			return { ...session, user: { ...session.user, id: token.sub, provider: token.provider } };
   		}
   	}
   });
   ```
   Without the database adapter and Nodemailer, OAuth still works with JWT sessions; only the e-mail magic link needs them. The provider id `nodemailer` must match `EMAIL_PROVIDER` in `src/lib/auth/authjs.ts`.
4. In `src/hooks.server.ts`, chain the Auth.js handle in front of the existing language handle:
   ```ts
   import { sequence } from '@sveltejs/kit/hooks';
   import { handle as auth } from './auth';
   export const handle = sequence(auth, lang); // `lang` = the current handle, renamed
   ```
5. Fill in `.env.local`: `PUBLIC_AUTH_PROVIDER=authjs`, `AUTH_SECRET`, `AUTH_GOOGLE_ID`, `AUTH_GOOGLE_SECRET`, `AUTH_GITHUB_ID`, `AUTH_GITHUB_SECRET`, `EMAIL_SERVER`, `EMAIL_FROM` and `DATABASE_URL`.
6. Build and run:
   - `bun run build`, then `ORIGIN=https://<domain> node build` behind an https reverse proxy. With Caddy, `reverse_proxy 127.0.0.1:3000` is enough.
   - `scripts/serve.ts` only serves static files and has no `/auth`.
7. Check:
   - `https://<domain>/auth/providers` lists `google`, `github` and `nodemailer`.
   - Clicking **Kontynuuj z Google** returns you to `/pl/start/paths/` with "Zalogowano jako …" under the step.

## 3b. Backend: Supabase (`PUBLIC_AUTH_PROVIDER=supabase`)

Supabase hosts the OAuth callback and the user table, so the site stays a static build.

1. Go to <https://supabase.com/dashboard> and choose **New project**. Pick an EU region (Frankfurt `eu-central-1`) to match the Privacy Policy's EEA preference.
2. Under **Project Settings → API Keys** (or **Data API**), copy the **Project URL** into `PUBLIC_SUPABASE_URL`. Copy the **anon / publishable** key into `PUBLIC_SUPABASE_ANON_KEY`.
3. Under **Authentication → Sign In / Providers → Google**, enable the provider and paste the Google **Client ID** and **Client secret**. The **Callback URL** shown there (`https://<ref>.supabase.co/auth/v1/callback`) is the one to put in Google's **Authorized redirect URIs**.
4. Under **Authentication → Sign In / Providers → GitHub**, enable the provider and paste the GitHub **Client ID** and **Client secret**. Use the same callback URL as the GitHub app's **Authorization callback URL**.
5. Under **Authentication → Sign In / Providers → Email**, enable it to get the magic link. Then set up the mail:
   - Under **Authentication → Emails → SMTP Settings**, set a custom SMTP server, preferably one in the EEA. The built-in mailer is rate-limited and meant for testing only.
   - Translate the **Magic Link** template to Polish.
6. Under **Authentication → URL Configuration**:
   - **Site URL**: `https://<domain>/pl/`.
   - **Redirect URLs**: `https://<domain>/**`. For dev, also add `http://localhost:18433/**`. Every `redirectTo` the app sends must match an entry.
7. Fill in `.env.local`:
   ```sh
   PUBLIC_AUTH_PROVIDER=supabase
   PUBLIC_SUPABASE_URL=https://<ref>.supabase.co
   PUBLIC_SUPABASE_ANON_KEY=<anon key>
   ```
   Then run `bun run build` and deploy `build/` as before.
8. Before going live:
   - Supabase's Google sign-in always requests `email profile` (name and avatar). Either add these to Privacy Policy §5 or switch to Auth.js, which can limit the scope to `openid email`.
   - The session is stored in localStorage under `auth.supabase`. Add it to the Cookie Policy table, since it is necessary for a service the user asked for.
   - Enable Row Level Security on every table you create. The anon key is public.

`src/lib/auth/supabase.ts` uses the implicit flow: tokens come back in the URL fragment, and `getSession()` moves them to storage and clears the hash. To use PKCE or httpOnly cookies, replace that file with `@supabase/ssr`. The `AuthClient` contract stays the same.

## Local testing over an SSH tunnel

The dev box is reached by a LAN IP, which Google does not accept. Tunnel the dev server so your browser sees `http://localhost`:

```sh
# on the laptop
ssh -N -L 18433:127.0.0.1:18433 jaro@192.168.10.230
# on the dev box (keep the port: it is the one registered with Google/GitHub/Supabase)
cd ~/KERNEL/app/landing && bun run dev
```

Then open `http://localhost:18433/pl/start/` on the laptop.

- **Auth.js:** the `handle` hook also runs under `vite dev`, so this works before the adapter switch. Use the localhost origin and redirect from step 1.6 and the dev GitHub app from step 2.4.
- **Supabase:** the OAuth callback is still Supabase's https URL. Only the final redirect goes to `http://localhost:18433/…`, which must be listed in the Redirect URLs.

## Switch-on checklist

- [ ] Domain with https in place. `SITE_ORIGIN` is set for the build (`svelte.config.js`).
- [ ] Google client and GitHub app created with the redirect URLs above. The Google app is **In production**.
- [ ] `PUBLIC_AUTH_PROVIDER` and the secrets are set on the build or server, not in git.
- [ ] Legal pages updated:
  - Privacy Policy §5 (scopes) and §8 (recipients: name Supabase or the Auth.js host and the mail provider).
  - Cookie Policy (session cookie `authjs.session-token`, or localStorage `auth.supabase`).
  - Terms of Service (accounts are live).
- [ ] In `src/lib/onboarding/copy.ts`, the `prototype` / `protoChip` wording no longer claims sign-in is not real.
