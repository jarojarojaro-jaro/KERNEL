<script lang="ts">
	/**
	 * Sign in (the default account step): one centred glass card over the hero's ember field. Three
	 * provider tiles, "albo", username + password (show/hide), "Zaloguj się"; under it a separate
	 * secondary action to the sign-up page (/start/register). Everything goes through `$lib/auth`; with
	 * `PUBLIC_AUTH_PROVIDER=none` every method answers `unavailable` and the step continues to
	 * /start/paths: nothing is sent or stored. Fits one screen at 1366×768, 1440×900 and 390×844.
	 *
	 * Motion: headline, card, tiles 60 ms apart, then the form; once, transform/opacity, < 600 ms.
	 * Reduced motion renders the final state, no border loop.
	 */
	import { tick } from 'svelte';
	import Hl from '$lib/home/Hl.svelte';
	import Field from '$lib/account/Field.svelte';
	import Glass from '$lib/account/Glass.svelte';
	import Providers from '$lib/account/Providers.svelte';
	import Scene from '$lib/account/Scene.svelte';
	import Submit from '$lib/account/Submit.svelte';
	import { authenticate, USERNAME_RE, type Method } from '$lib/account/flow';
	import type { AuthErrorCode, OAuthProvider } from '$lib/auth';
	import { currentLang, href } from '$lib/i18n';
	import { ob } from '$lib/onboarding/copy';

	const lang = $derived(currentLang());
	const t = $derived(ob[lang].account);
	const s = $derived(t.signin);

	let username = $state('');
	let password = $state('');
	let reveal = $state(false);
	/** True once the form was submitted; drives which errors show. */
	let tried = $state(false);
	let busy = $state<OAuthProvider | 'password' | null>(null);
	let failure = $state<AuthErrorCode | null>(null);
	let form: HTMLFormElement | undefined = $state();

	const userErr = $derived(tried && !USERNAME_RE.test(username.trim()) ? t.errUsername : null);
	const passErr = $derived(tried && password.length === 0 ? t.errPassEmpty : null);
	const failMsg = $derived(failure && { invalid: t.errInvalid, taken: t.errTaken, locked: t.errLocked, failed: t.errAuth }[failure]);

	async function run(method: Method) {
		failure = null;
		busy = typeof method === 'string' ? method : 'password';
		failure = await authenticate(lang, method);
		if (failure) busy = null;
	}

	async function submit(e: SubmitEvent) {
		e.preventDefault();
		tried = true;
		await tick();
		const invalid = form?.querySelector<HTMLElement>('[aria-invalid="true"]');
		if (invalid) return invalid.focus();
		run({ mode: 'signin', username: username.trim(), password });
	}
</script>

<svelte:head>
	<title>{s.title}</title>
	<meta name="description" content={s.lead} />
</svelte:head>

<Scene labelledby="signin-title">
	<div class="wrap">
		<header class="head in" style="--d:0ms">
			<h1 id="signin-title" class="title"><Hl text={s.heading} /></h1>
			<p class="sub">{s.lead}</p>
		</header>

		<Glass width="30rem">
			<form class="card" bind:this={form} novalidate aria-busy={busy !== null} onsubmit={submit}>
				<Providers {lang} via={s.via} {busy} delay={100} onpick={run} />

				<div class="fields in" style="--d:300ms">
					<Field id="si-user" name="username" label={t.username} autocomplete="username" maxlength={32} srHint={t.usernameHint} error={userErr} bind:value={username} />
					<Field id="si-pass" name="password" label={t.password} autocomplete="current-password" secret eye={{ label: t.show, controls: 'si-pass' }} error={passErr} bind:value={password} bind:reveal />
				</div>

				<div class="in" style="--d:340ms">
					<Submit label={busy === 'password' ? t.busy : s.submit} disabled={busy !== null} />
				</div>

				<p class="status" role="status">{#if failMsg}<span class="error-text">{failMsg}</span>{/if}</p>
			</form>

			<p class="alt in" style="--d:380ms">
				<span>{s.noAccount}</span>
				<a href={href(lang, '/start/register')}>{s.create} <span class="arrow" aria-hidden="true">→</span></a>
			</p>
		</Glass>
	</div>
</Scene>

<style>
	.wrap {
		display: grid;
		justify-items: center;
		gap: clamp(0.75rem, 2.4vh, 1.5rem);
		width: min(100%, 40rem);
	}
	@media (prefers-reduced-motion: no-preference) {
		.in {
			animation: rise 0.32s var(--ease-out) var(--d) both;
		}
	}
	@keyframes rise {
		from {
			opacity: 0.01;
			transform: translate3d(0, 0.75rem, 0);
		}
	}

	.head {
		display: grid;
		gap: var(--sp-2);
		text-align: center;
	}
	.title {
		font-family: var(--font-display);
		font-size: clamp(1.75rem, 1.1rem + 2.4vw, 3rem);
		font-weight: 750;
		font-stretch: 108%;
		line-height: 1.05;
		letter-spacing: -0.03em;
		color: var(--text-hi);
		text-wrap: balance;
	}
	.sub {
		color: var(--text);
		font-size: clamp(1rem, 0.95rem + 0.3vw, 1.125rem);
	}

	.card {
		display: grid;
		gap: clamp(0.65rem, 1.7vh, 1rem);
		padding: clamp(1rem, 3vh, 1.75rem) clamp(1rem, 0.6rem + 1.6vw, 1.75rem) clamp(0.85rem, 2.2vh, 1.25rem);
	}
	.fields {
		display: grid;
		gap: clamp(0.6rem, 1.5vh, 0.9rem);
	}
	.status:empty {
		display: none;
	}
	.status {
		margin-top: calc(-1 * var(--sp-1));
		font-size: var(--fs-sm);
		text-align: center;
	}

	/* secondary action: a separate band at the card's foot, clearly not the primary */
	.alt {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: center;
		gap: var(--sp-1) var(--sp-3);
		padding: clamp(0.75rem, 2vh, 1.1rem) var(--sp-4);
		border-top: 1px solid var(--line);
		border-radius: 0 0 1.5rem 1.5rem;
		background: color-mix(in srgb, var(--bg-0) 35%, transparent);
		color: var(--text-mute);
		font-size: var(--fs-sm);
	}
	.alt a {
		display: inline-flex;
		align-items: center;
		gap: 0.35rem;
		padding: 0.35rem 0.9rem;
		border: 1px solid color-mix(in srgb, var(--heat-3) 55%, var(--line));
		border-radius: var(--r-pill);
		color: var(--text-hi);
		font-weight: 600;
		text-decoration: none;
		transition:
			border-color var(--dur-3) var(--ease-out),
			background-color var(--dur-3) var(--ease-out);
	}
	.alt a:hover {
		border-color: var(--heat-3);
		background: color-mix(in srgb, var(--heat-3) 14%, transparent);
	}
	.alt a:focus-visible {
		outline: 2px solid var(--heat-3);
		outline-offset: 2px;
	}
	.alt .arrow {
		color: var(--accent-ink);
		transition: transform var(--dur-3) var(--ease-out);
	}
	.alt a:hover .arrow {
		transform: translateX(3px);
	}
	@media (max-width: 600px) {
		.alt {
			border-radius: 0 0 1.25rem 1.25rem;
		}
	}
</style>
