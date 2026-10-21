<script lang="ts">
	/**
	 * Sign up: a wide two-column glass card (value panel left, form right; phones: the panel shrinks
	 * to a headline). Provider tiles in a low row ("Załóż konto przez …"), "albo", then username on
	 * top, password + repeat side by side, the one-line no-recovery note, the consent checkbox right
	 * under the fields, "Załóż konto", and the way back to sign-in. `PUBLIC_AUTH_PROVIDER=none`:
	 * every method continues to /start/paths, nothing is sent or stored.
	 */
	import { tick } from 'svelte';
	import Hl from '$lib/home/Hl.svelte';
	import Field from '$lib/account/Field.svelte';
	import Glass from '$lib/account/Glass.svelte';
	import Providers from '$lib/account/Providers.svelte';
	import Scene from '$lib/account/Scene.svelte';
	import Submit from '$lib/account/Submit.svelte';
	import { authenticate, MIN_PASSWORD, USERNAME_RE, type Method } from '$lib/account/flow';
	import type { AuthErrorCode, OAuthProvider } from '$lib/auth';
	import { currentLang, href } from '$lib/i18n';
	import { ob } from '$lib/onboarding/copy';

	const lang = $derived(currentLang());
	const t = $derived(ob[lang].account);
	const s = $derived(t.signup);

	let username = $state('');
	let password = $state('');
	let password2 = $state('');
	let reveal = $state(false);
	let terms = $state(false);
	let tried = $state(false);
	let busy = $state<OAuthProvider | 'password' | null>(null);
	let failure = $state<AuthErrorCode | null>(null);
	let form: HTMLFormElement | undefined = $state();

	const userErr = $derived(tried && !USERNAME_RE.test(username.trim()) ? t.errUsername : null);
	const passErr = $derived(tried && password.length < MIN_PASSWORD ? t.errPassword : null);
	const matchErr = $derived(tried && password2 !== password ? t.errMatch : null);
	const termsBad = $derived(tried && !terms);
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
		run({ mode: 'signup', username: username.trim(), password });
	}
</script>

<svelte:head>
	<title>{s.title}</title>
	<meta name="description" content={s.lead} />
</svelte:head>

<Scene labelledby="signup-title" focus="62% 50%">
	<Glass width="62rem">
		<div class="split">
			<aside class="panel">
				<span class="mark" aria-hidden="true"></span>
				<p class="kicker in" style="--d:60ms">{s.kicker}</p>
				<h1 id="signup-title" class="title in" style="--d:90ms"><Hl text={s.heading} /></h1>
				<p class="lead in" style="--d:120ms">{s.lead}</p>
				<ul class="points">
					{#each s.points as p, i (p)}
						<li class="in" style="--d:{160 + i * 50}ms">
							<svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"><path d="M3.5 8.5 6.5 11.5 12.5 4.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" /></svg>
							<span>{p}</span>
						</li>
					{/each}
				</ul>
				<p class="back in" style="--d:320ms">{s.haveAccount} <a href={href(lang, '/start')}>{s.signIn}</a></p>
			</aside>

			<form class="form" bind:this={form} novalidate aria-busy={busy !== null} onsubmit={submit}>
				<Providers {lang} via={s.via} {busy} layout="row" delay={120} onpick={run} />

				<div class="fields in" style="--d:330ms">
					<Field id="su-user" name="username" label={t.username} autocomplete="username" maxlength={32} hint={t.usernameHint} error={userErr} bind:value={username} />
					<div class="pair">
						<Field id="su-pass" name="new-password" label={t.password} note={t.passwordHint} autocomplete="new-password" minlength={MIN_PASSWORD} secret eye={{ label: t.show, controls: 'su-pass su-pass2' }} error={passErr} bind:value={password} bind:reveal />
						<Field id="su-pass2" name="new-password-repeat" label={t.password2} autocomplete="new-password" secret error={matchErr} bind:value={password2} bind:reveal />
					</div>
					<p class="recovery">
						<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="4" y="10.5" width="16" height="10" rx="2.5" /><path d="M8 10.5V8a4 4 0 0 1 8 0v2.5" /></svg>
						<span>{t.noRecovery}</span>
					</p>
					<div class="consent">
						<label class="check">
							<input type="checkbox" bind:checked={terms} aria-invalid={termsBad} aria-describedby={termsBad ? 'su-terms-err' : undefined} />
							<span>{t.terms} <a href={href(lang, '/legal/terms')}>{t.termsLink}</a> {t.and} <a href={href(lang, '/legal/privacy')}>{t.privacyLink}</a>.</span>
						</label>
						{#if termsBad}<span class="error-text" id="su-terms-err">{t.errTerms}</span>{/if}
					</div>
				</div>

				<div class="in" style="--d:370ms">
					<Submit label={busy === 'password' ? t.busy : s.submit} disabled={busy !== null} />
				</div>

				<p class="status" role="status">{#if failMsg}<span class="error-text">{failMsg}</span>{/if}</p>
				<p class="back back--m">{s.haveAccount} <a href={href(lang, '/start')}>{s.signIn}</a></p>
			</form>
		</div>
	</Glass>
</Scene>

<style>
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

	.split {
		display: grid;
		grid-template-columns: minmax(0, 0.82fr) minmax(0, 1.18fr);
	}

	/* ---------- value panel: warm ember wash, brand line, three facts ---------- */
	.panel {
		position: relative;
		display: flex;
		flex-direction: column;
		gap: clamp(0.6rem, 1.6vh, 1rem);
		padding: clamp(1.25rem, 4vh, 2.5rem) clamp(1.25rem, 0.6rem + 1.8vw, 2.25rem);
		border-radius: 1.5rem 0 0 1.5rem;
		border: 0;
		border-right: 1px solid var(--line);
		background:
			radial-gradient(120% 70% at 0% 100%, color-mix(in srgb, var(--heat-3) 26%, transparent), transparent 65%),
			radial-gradient(80% 50% at 100% 0%, color-mix(in srgb, var(--heat-4) 10%, transparent), transparent 70%),
			color-mix(in srgb, var(--bg-0) 40%, transparent);
		overflow: hidden;
	}
	.mark {
		width: 2.25rem;
		height: 3px;
		border-radius: 2px;
		background: linear-gradient(90deg, var(--heat-2), var(--heat-4));
	}
	.kicker {
		color: var(--accent-ink);
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		letter-spacing: 0.14em;
		text-transform: uppercase;
	}
	.title {
		font-family: var(--font-display);
		font-size: clamp(1.6rem, 1rem + 1.7vw, 2.5rem);
		font-weight: 750;
		font-stretch: 108%;
		line-height: 1.08;
		letter-spacing: -0.03em;
		color: var(--text-hi);
		text-wrap: balance;
	}
	.lead {
		color: var(--text);
		font-size: var(--fs-sm);
		line-height: 1.5;
	}
	.points {
		display: grid;
		gap: 0.55rem;
		margin: var(--sp-2) 0 0;
		padding: 0;
		list-style: none;
		color: var(--text);
		font-size: var(--fs-sm);
	}
	.points li {
		display: flex;
		gap: 0.55rem;
		align-items: baseline;
	}
	.points svg {
		flex: none;
		transform: translateY(2px);
		color: var(--heat-3);
	}
	.back {
		margin-top: auto;
		padding-top: var(--sp-4);
		color: var(--text-mute);
		font-size: var(--fs-sm);
	}
	.back a {
		color: var(--text-hi);
		font-weight: 600;
		text-decoration-color: var(--heat-3);
		text-underline-offset: 3px;
	}
	.back--m {
		display: none;
	}

	/* ---------- form column ---------- */
	.form {
		display: grid;
		align-content: center;
		gap: clamp(0.6rem, 1.6vh, 1rem);
		padding: clamp(1.1rem, 3.4vh, 2rem) clamp(1rem, 0.6rem + 1.6vw, 2rem);
		min-width: 0;
	}
	.fields {
		display: grid;
		gap: clamp(0.55rem, 1.4vh, 0.85rem);
	}
	.pair {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: var(--sp-3);
		align-items: start;
	}
	.recovery {
		display: flex;
		gap: 0.4rem;
		align-items: baseline;
		color: var(--text-mute);
		font-size: var(--fs-2xs);
		line-height: 1.4;
	}
	.recovery svg {
		flex: none;
		transform: translateY(2px);
		color: var(--accent-ink);
	}
	.consent {
		display: grid;
		gap: var(--sp-1);
		font-size: var(--fs-sm);
	}
	.check input {
		accent-color: var(--heat-3);
	}
	.status:empty {
		display: none;
	}
	.status {
		font-size: var(--fs-sm);
		text-align: center;
	}

	@media (max-width: 860px) {
		.split {
			grid-template-columns: minmax(0, 1fr);
		}
		.panel {
			gap: var(--sp-1);
			padding: 0.9rem 1rem 0.25rem;
			border-right: 0;
			overflow: visible;
			border-radius: 1.25rem 1.25rem 0 0;
			background: transparent;
			text-align: center;
			align-items: center;
		}
		.mark,
		.kicker,
		.lead,
		.points,
		.panel > .back {
			display: none;
		}
		.title {
			font-size: clamp(1.5rem, 1rem + 2.4vw, 2rem);
		}
		.form {
			padding: 0.85rem 0.9rem 1rem;
		}
		.back--m {
			display: block;
			margin: 0;
			padding: 0;
			text-align: center;
		}
	}
	@media (max-width: 480px) {
		.pair {
			grid-template-columns: minmax(0, 1fr);
		}
	}
</style>
