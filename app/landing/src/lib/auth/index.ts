/**
 * Auth entry point. `PUBLIC_AUTH_PROVIDER` (build time, `.env`; default `none`) picks the backend:
 * - `none`: no accounts yet; sign-in answers `unavailable`, the UI offers the waitlist (none.ts).
 * - `authjs`: Auth.js on this app's server, needs adapter-node (authjs.ts, AUTH.md).
 * - `supabase`: Supabase Auth, works with the static build (supabase.ts, AUTH.md).
 * Any other value fails the build, so a typo never ships a silently disabled login.
 */
import { PUBLIC_AUTH_PROVIDER } from '$env/static/public';
import { authjsClient } from './authjs';
import { noneClient } from './none';
import { supabaseClient } from './supabase';
import type { AuthBackend, AuthClient, AuthSession, OAuthProvider, SignInOptions } from './types';

export type { AuthBackend, AuthClient, AuthResult, AuthSession, AuthUser, OAuthProvider, SignInMethod, SignInOptions } from './types';

const CLIENTS: Record<AuthBackend, AuthClient> = { none: noneClient, authjs: authjsClient, supabase: supabaseClient };

const backend = PUBLIC_AUTH_PROVIDER || 'none';
if (!(backend in CLIENTS)) throw new Error(`PUBLIC_AUTH_PROVIDER must be none, authjs or supabase (got "${backend}")`);

/** The configured client; `auth.live` tells the UI whether sign-in really works. */
export const auth: AuthClient = CLIENTS[backend as AuthBackend];

export const signInWith = (provider: OAuthProvider, options?: SignInOptions) => auth.signInWith(provider, options);
export const signInWithEmail = (email: string, options?: SignInOptions) => auth.signInWithEmail(email, options);
export const getSession = (): Promise<AuthSession | null> => auth.getSession();
export const signOut = () => auth.signOut();
