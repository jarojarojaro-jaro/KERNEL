<script lang="ts">
	/**
	 * Account step: one centred sign-in card. Google / GitHub / Hugging Face, or a username + password
	 * account with no e-mail at all (sign in | create). Everything goes through `$lib/auth`; with
	 * `PUBLIC_AUTH_PROVIDER=none` (preview, no backend) every method answers `unavailable` and the step
	 * simply continues to /start/paths: nothing is sent or stored.
	 *
	 * Brand marks: the Google "G" is Google's own asset (static/brand/google-g.svg, cut from the
	 * Sign in with Google bundle, unaltered) on the button colours from Google's branding guidelines;
	 * GitHub uses the Primer mark-github in pure white / black; Hugging Face uses the official hf-logo
	 * (static/brand/huggingface.svg, huggingface/brand-assets). All three share one button shell, so
	 * Google is "at least as prominent" as the others.
	 */
	import { goto } from '$app/navigation';
	import { tick } from 'svelte';
	import { signInWith, signInWithPassword, signUpWithPassword, type AuthErrorCode, type AuthResult, type OAuthProvider } from '$lib/auth';
	import { currentLang, href } from '$lib/i18n';
	import { ob } from '$lib/onboarding/copy';
	import Shell from '$lib/onboarding/Shell.svelte';

	const lang = $derived(currentLang());
	const t = $derived(ob[lang].account);

	let mode = $state<'login' | 'register'>('register');
	let username = $state('');
	let password = $state('');
	let password2 = $state('');
	let reveal = $state(false);
	let terms = $state(false);
	/** What the visitor last tried; drives which errors show. */
	let tried = $state<'oauth' | 'password' | null>(null);
	let busy = $state<OAuthProvider | 'password' | null>(null);
	let failure = $state<AuthErrorCode | null>(null);
	let form: HTMLFormElement | undefined = $state();

	const register = $derived(mode === 'register');
	const userOk = $derived(/^[A-Za-z0-9._-]{3,32}$/.test(username.trim()));
	const passOk = $derived(password.length >= 10);
	const pw = $derived(tried === 'password');
	const userBad = $derived(pw && !userOk);
	const passBad = $derived(pw && !passOk);
	const matchBad = $derived(pw && register && password2 !== password);
	// Consent is needed whenever an account may be created: any provider, or "Załóż konto".
	const termsBad = $derived((tried === 'oauth' || (pw && register)) && !terms);
	const failMsg = $derived(failure && { invalid: t.errInvalid, taken: t.errTaken, locked: t.errLocked, failed: t.errAuth }[failure]);

	const providers = $derived([
		{ id: 'google' as const, label: t.google },
		{ id: 'github' as const, label: t.github },
		{ id: 'huggingface' as const, label: t.huggingface }
	]);

	async function run(kind: OAuthProvider | 'password') {
		tried = kind === 'password' ? 'password' : 'oauth';
		failure = null;
		await tick();
		const invalid = form?.querySelector<HTMLElement>('[aria-invalid="true"]');
		if (invalid) {
			invalid.focus();
			return;
		}
		const next = href(lang, '/start/paths');
		busy = kind;
		let res: AuthResult;
		if (kind !== 'password') res = await signInWith(kind, { redirectTo: next });
		else if (register) res = await signUpWithPassword(username.trim(), password, { redirectTo: next });
		else res = await signInWithPassword(username.trim(), password, { redirectTo: next });
		if (res.status === 'redirecting') return;
		busy = null;
		if (res.status === 'unavailable') goto(next);
		else failure = res.code;
	}
</script>

<svelte:head><title>{t.title}</title></svelte:head>

<Shell title={t.heading} lead={t.lead}>
	<div class="halo" aria-hidden="true"></div>
	<form class="card heat-card panel" bind:this={form} novalidate aria-busy={busy !== null} onsubmit={(e) => (e.preventDefault(), run('password'))}>
		<div class="oauth rise" style="--d:0ms">
			{#each providers as p (p.id)}
				<button class="oa" type="button" disabled={busy !== null} onclick={() => run(p.id)}>
					<span class="mark" aria-hidden="true">
						{#if p.id === 'google'}
							<img src="/brand/google-g.svg" width="20" height="20" alt="" />
						{:else if p.id === 'huggingface'}
							<img src="/brand/huggingface.svg" width="20" height="20" alt="" />
						{:else}
							<svg viewBox="0 0 24 24" width="20" height="20"><path fill="currentColor" d="M10.226 17.284c-2.965-.36-5.054-2.493-5.054-5.256 0-1.123.404-2.336 1.078-3.144-.292-.741-.247-2.314.09-2.965.898-.112 2.111.36 2.83 1.01.853-.269 1.752-.404 2.853-.404 1.1 0 1.999.135 2.807.382.696-.629 1.932-1.1 2.83-.988.315.606.36 2.179.067 2.942.72.854 1.101 2 1.101 3.167 0 2.763-2.089 4.852-5.098 5.234.763.494 1.28 1.572 1.28 2.807v2.336c0 .674.561 1.056 1.235.786 4.066-1.55 7.255-5.615 7.255-10.646C23.5 6.188 18.334 1 11.978 1 5.62 1 .5 6.188.5 12.545c0 4.986 3.167 9.12 7.435 10.669.606.225 1.19-.18 1.19-.786V20.63a2.9 2.9 0 0 1-1.078.224c-1.483 0-2.359-.808-2.987-2.313-.247-.607-.517-.966-1.034-1.033-.27-.023-.359-.135-.359-.27 0-.27.45-.471.898-.471.652 0 1.213.404 1.797 1.235.45.651.921.943 1.483.943.561 0 .92-.202 1.437-.719.382-.381.674-.718.944-.943" /></svg>
						{/if}
					</span>
					<span class="oa-label">{busy === p.id ? t.busy : p.label}</span>
					<span class="arrow" aria-hidden="true">→</span>
				</button>
			{/each}
		</div>

		<p class="or rise" style="--d:90ms"><span>{t.or}</span></p>

		<fieldset class="pw rise" style="--d:150ms">
			<legend class="pw-title">{t.pwTitle}</legend>
			<div class="segmented mode">
				<label><input type="radio" name="mode" value="login" bind:group={mode} /><span>{t.login}</span></label>
				<label><input type="radio" name="mode" value="register" bind:group={mode} /><span>{t.register}</span></label>
			</div>

			<div class="field">
				<label for="acc-user">{t.username}</label>
				<input
					id="acc-user"
					class="input"
					name="username"
					autocomplete="username"
					autocapitalize="none"
					spellcheck="false"
					maxlength="32"
					bind:value={username}
					aria-invalid={userBad}
					aria-describedby={userBad ? 'acc-user-err' : register ? 'acc-user-hint' : undefined}
				/>
				{#if userBad}<span class="error-text" id="acc-user-err">{t.errUsername}</span>{:else if register}<span class="hint" id="acc-user-hint">{t.usernameHint}</span>{/if}
			</div>

			<div class="field">
				<label for="acc-pass">{t.password}</label>
				<div class="pass">
					<input
						id="acc-pass"
						class="input"
						name="password"
						type={reveal ? 'text' : 'password'}
						autocomplete={register ? 'new-password' : 'current-password'}
						minlength="10"
						bind:value={password}
						aria-invalid={passBad}
						aria-describedby={passBad ? 'acc-pass-err' : register ? 'acc-pass-hint' : undefined}
					/>
					<button class="eye" type="button" aria-label={t.show} aria-pressed={reveal} aria-controls={register ? 'acc-pass acc-pass2' : 'acc-pass'} onclick={() => (reveal = !reveal)}>
						<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
							<path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12Z" /><circle cx="12" cy="12" r="3" />
							{#if reveal}<path d="M4 4l16 16" />{/if}
						</svg>
					</button>
				</div>
				{#if passBad}<span class="error-text" id="acc-pass-err">{t.errPassword}</span>{:else if register}<span class="hint" id="acc-pass-hint">{t.passwordHint}</span>{/if}
			</div>

			{#if register}
				<div class="field">
					<label for="acc-pass2">{t.password2}</label>
					<input
						id="acc-pass2"
						class="input"
						name="password-repeat"
						type={reveal ? 'text' : 'password'}
						autocomplete="new-password"
						bind:value={password2}
						aria-invalid={matchBad}
						aria-describedby={matchBad ? 'acc-pass2-err' : undefined}
					/>
					{#if matchBad}<span class="error-text" id="acc-pass2-err">{t.errMatch}</span>{/if}
				</div>
			{/if}

			<p class="recovery">
				<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="4" y="10.5" width="16" height="10" rx="2.5" /><path d="M8 10.5V8a4 4 0 0 1 8 0v2.5" /></svg>
				<span>{t.noRecovery}</span>
			</p>

			<button class="send" type="submit" disabled={busy !== null}>{busy === 'password' ? t.busy : register ? t.register : t.login} <span class="arrow" aria-hidden="true">→</span></button>
		</fieldset>

		<div class="consent rise" style="--d:210ms">
			<label class="check">
				<input type="checkbox" bind:checked={terms} aria-invalid={termsBad} aria-describedby={termsBad ? 'terms-err' : undefined} />
				<span>{t.terms} <a href={href(lang, '/legal/terms')}>{t.termsLink}</a> {t.and} <a href={href(lang, '/legal/privacy')}>{t.privacyLink}</a>.</span>
			</label>
			{#if termsBad}<span class="error-text" id="terms-err">{t.errTerms}</span>{/if}
		</div>

		<p class="status" role="status">{#if failMsg}<span class="error-text">{failMsg}</span>{/if}</p>
	</form>
</Shell>

<style>
	/* ember light pooled under the card; the card sits centred in the Shell's 40rem column */
	.halo {
		position: absolute;
		left: 50%;
		width: min(46rem, 120vw);
		height: 34rem;
		margin-top: 4rem;
		transform: translateX(-50%);
		z-index: -1;
		pointer-events: none;
		background: radial-gradient(50% 50% at 50% 50%, color-mix(in srgb, var(--heat-3) 16%, transparent), transparent 70%);
		filter: blur(10px);
	}
	@media (prefers-reduced-motion: no-preference) {
		.rise {
			animation: rise 0.7s var(--ease-out) calc(0.25s + var(--d)) both;
		}
	}
	@keyframes rise {
		from {
			opacity: 0.01;
			transform: translate3d(0, 0.9rem, 0);
		}
	}

	.panel {
		position: relative;
		display: grid;
		gap: var(--sp-5);
		width: min(100%, 32rem);
		margin-inline: auto;
		padding: clamp(1.25rem, 0.6rem + 2.6vw, 2.5rem);
		border-radius: calc(var(--r-xl) + 4px);
	}
	.oauth {
		display: grid;
		gap: var(--sp-3);
	}
	/*
	 * Provider buttons, Google's custom-button spec scaled 1.3× (40 → 52 px, G 20 → 26 px, 12 / 10 px
	 * padding → 16 / 13 px): dark fill #131314, 1 px #8E918F stroke, #E3E3E3 text; light theme
	 * #FFFFFF / #747775 / #1F1F1F. GitHub and Hugging Face get the identical shell (equal prominence).
	 * The heat ring on hover sits outside the stroke, so no brand surface is recoloured.
	 */
	.oa {
		--oa-fill: #131314;
		--oa-stroke: #8e918f;
		--oa-ink: #e3e3e3;
		--oa-mark: #ffffff;
		display: flex;
		align-items: center;
		gap: 0.8125rem;
		width: 100%;
		min-height: 3.25rem;
		padding: 0 1.25rem 0 1rem;
		border: 1px solid var(--oa-stroke);
		border-radius: var(--r-pill);
		background: var(--oa-fill);
		color: var(--oa-ink);
		font-family: 'Google Sans', Roboto, var(--font-sans);
		font-size: var(--fs-md);
		font-weight: 500;
		line-height: 1.4;
		text-align: left;
		cursor: pointer;
		transition:
			box-shadow var(--dur-3) var(--ease-out),
			transform var(--dur-2) var(--ease-out);
	}
	:global(:root[data-theme='light']) .oa {
		--oa-fill: #ffffff;
		--oa-stroke: #747775;
		--oa-ink: #1f1f1f;
		--oa-mark: #000000;
	}
	.oa:hover {
		box-shadow:
			0 0 0 3px color-mix(in srgb, var(--heat-3) 35%, transparent),
			0 14px 40px -16px color-mix(in srgb, var(--heat-3) 90%, transparent);
	}
	.oa:active {
		transform: scale(0.985);
	}
	.oa:focus-visible {
		outline: 2px solid var(--heat-3);
		outline-offset: 3px;
	}
	.oa:disabled,
	.send:disabled {
		cursor: progress;
	}
	.mark {
		flex: none;
		display: grid;
		place-items: center;
		width: 1.625rem;
		height: 1.625rem;
		color: var(--oa-mark);
	}
	.mark img,
	.mark svg {
		width: 100%;
		height: 100%;
	}
	.oa-label {
		flex: 1;
		min-width: 0;
	}
	.oa .arrow {
		flex: none;
		opacity: 0.55;
		transition:
			transform var(--dur-3) var(--ease-out),
			opacity var(--dur-2);
	}
	.oa:hover .arrow,
	.oa:focus-visible .arrow {
		opacity: 1;
		transform: translateX(4px);
	}

	.or {
		display: grid;
		grid-template-columns: 1fr auto 1fr;
		align-items: center;
		gap: var(--sp-3);
		color: var(--text-mute);
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		text-transform: uppercase;
		letter-spacing: 0.12em;
	}
	.or::before,
	.or::after {
		content: '';
		height: 1px;
		background: linear-gradient(90deg, transparent, var(--line-strong));
	}
	.or::after {
		background: linear-gradient(90deg, var(--line-strong), transparent);
	}

	/* ---------- username + password (no e-mail) ---------- */
	.pw {
		display: grid;
		gap: var(--sp-4);
		margin: 0;
		padding: 0;
		border: 0;
		min-width: 0;
	}
	.pw-title {
		float: left; /* lets the legend sit in the grid flow instead of on the fieldset border */
		width: 100%;
		margin-bottom: calc(-1 * var(--sp-1));
		color: var(--text-hi);
		font-weight: 650;
		font-size: var(--fs-base);
	}
	.mode {
		display: grid;
		grid-template-columns: 1fr 1fr;
	}
	.mode span {
		text-align: center;
		padding-block: 0.55rem;
	}
	.mode label:hover span {
		color: var(--text-hi);
	}
	.mode input:checked + span {
		background: var(--text-hi);
		color: var(--text-inv);
	}
	.mode input:focus-visible + span {
		outline-color: var(--heat-3);
	}
	.pw .input {
		min-height: 3rem;
		border-radius: var(--r-md);
		font-size: var(--fs-md);
	}
	.pw .input:focus-visible {
		border-color: var(--heat-3);
	}
	.pass {
		position: relative;
	}
	.pass .input {
		padding-right: 3.25rem;
	}
	.eye {
		position: absolute;
		top: 50%;
		right: 0.35rem;
		display: grid;
		place-items: center;
		width: 2.5rem;
		height: 2.5rem;
		transform: translateY(-50%);
		border: 0;
		border-radius: var(--r-sm);
		background: transparent;
		color: var(--text-mute);
		cursor: pointer;
	}
	.eye:hover,
	.eye[aria-pressed='true'] {
		color: var(--text-hi);
	}
	.eye:focus-visible {
		outline: 2px solid var(--heat-3);
		outline-offset: 0;
	}
	.recovery {
		display: grid;
		grid-template-columns: auto minmax(0, 1fr);
		gap: var(--sp-2);
		align-items: start;
		padding: var(--sp-3) var(--sp-4);
		border: 1px solid color-mix(in srgb, var(--heat-3) 30%, var(--line));
		border-radius: var(--r-md);
		background: color-mix(in srgb, var(--heat-3) 6%, transparent);
		color: var(--text);
		font-size: var(--fs-xs);
		line-height: 1.5;
	}
	.recovery svg {
		margin-top: 0.05rem;
		color: var(--accent-ink);
	}
	.send {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: var(--sp-2);
		width: 100%;
		min-height: 3.25rem;
		padding: 0 var(--sp-5);
		border: 0;
		border-radius: var(--r-pill);
		background: var(--text-hi);
		color: var(--text-inv);
		font: inherit;
		font-weight: 650;
		font-size: var(--fs-base);
		cursor: pointer;
		transition:
			box-shadow var(--dur-3),
			transform var(--dur-2) var(--ease-out);
	}
	.send:hover {
		box-shadow: 0 10px 34px -10px color-mix(in srgb, var(--heat-3) 90%, transparent);
	}
	.send:active {
		transform: scale(0.99);
	}
	.send:focus-visible {
		outline: 2px solid var(--heat-3);
		outline-offset: 3px;
	}
	.send .arrow {
		display: inline-block;
		transition: transform var(--dur-3) var(--ease-out);
	}
	.send:hover .arrow {
		transform: translateX(3px);
	}

	.consent {
		display: grid;
		gap: var(--sp-2);
		padding-top: var(--sp-4);
		border-top: 1px solid var(--line);
	}
	.check input {
		accent-color: var(--heat-3);
	}
	.status:empty {
		display: none;
	}
	.status {
		font-size: var(--fs-sm);
	}

	@media (max-width: 560px) {
		.oa {
			font-size: var(--fs-base);
		}
	}
</style>
