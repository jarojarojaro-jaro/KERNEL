<script lang="ts">
	/**
	 * Account step: one screen (1280×720 up, 390×844) over the hero's ember field. A glass card with a
	 * slowly travelling ember border holds three provider tiles (Google · GitHub · Hugging Face) and a
	 * compact username + password form (sign in | create, no e-mail). Everything goes through
	 * `$lib/auth`; with `PUBLIC_AUTH_PROVIDER=none` (preview, no backend) every method answers
	 * `unavailable` and the step continues to /start/paths: nothing is sent or stored.
	 *
	 * Brand marks: the Google "G" is Google's own asset (static/brand/google-g.svg, cut from the Sign in
	 * with Google bundle, unaltered); GitHub uses the Primer mark-github in pure white / black; Hugging
	 * Face uses the official hf-logo (static/brand/huggingface.svg). Every tile keeps Google's neutral
	 * fill (#131314 / #FFFFFF) under its mark and says "Kontynuuj z …"; the brand tint lives only in the
	 * hover ring and glow, and all three tiles are the same size (equal prominence).
	 *
	 * Motion: headline, tiles 60 ms apart, then the form; once, transform/opacity, < 600 ms. Reduced
	 * motion renders the final state, no border loop.
	 */
	import { goto } from '$app/navigation';
	import { tick } from 'svelte';
	import HeatField from '$lib/fx/HeatField.svelte';
	import Hl from '$lib/home/Hl.svelte';
	import { signInWith, signInWithPassword, signUpWithPassword, type AuthErrorCode, type AuthResult, type OAuthProvider } from '$lib/auth';
	import { currentLang, href } from '$lib/i18n';
	import { ob } from '$lib/onboarding/copy';

	const lang = $derived(currentLang());
	const t = $derived(ob[lang].account);

	const PROVIDERS: { id: OAuthProvider; name: string }[] = [
		{ id: 'google', name: 'Google' },
		{ id: 'github', name: 'GitHub' },
		{ id: 'huggingface', name: 'Hugging Face' }
	];

	let mode = $state<'login' | 'register'>('register');
	let username = $state('');
	let password = $state('');
	let password2 = $state('');
	let reveal = $state(false);
	let terms = $state(false);
	/** True once the password form was submitted; drives which errors show. */
	let tried = $state(false);
	let busy = $state<OAuthProvider | 'password' | null>(null);
	let failure = $state<AuthErrorCode | null>(null);
	let form: HTMLFormElement | undefined = $state();

	const register = $derived(mode === 'register');
	const userBad = $derived(tried && !/^[A-Za-z0-9._-]{3,32}$/.test(username.trim()));
	const passBad = $derived(tried && password.length < 10);
	const matchBad = $derived(tried && register && password2 !== password);
	// The checkbox guards "Załóż konto"; the provider tiles carry the implied-consent line under them.
	const termsBad = $derived(tried && register && !terms);
	const failMsg = $derived(failure && { invalid: t.errInvalid, taken: t.errTaken, locked: t.errLocked, failed: t.errAuth }[failure]);

	async function run(kind: OAuthProvider | 'password') {
		failure = null;
		if (kind === 'password') {
			tried = true;
			await tick();
			const invalid = form?.querySelector<HTMLElement>('[aria-invalid="true"]');
			if (invalid) {
				invalid.focus();
				return;
			}
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

<svelte:head>
	<title>{t.title}</title>
	<meta name="description" content={t.lead} />
</svelte:head>

<section class="acct heat-scope" aria-labelledby="acct-title">
	<div class="bg" aria-hidden="true">
		<HeatField heat={0.55} />
		<div class="veil"></div>
	</div>

	<div class="wrap">
		<header class="head in" style="--d:0ms">
			<h1 id="acct-title" class="title"><Hl text={t.heading} /></h1>
			<p class="sub">{t.lead}</p>
		</header>

		<form class="glass" bind:this={form} novalidate aria-busy={busy !== null} onsubmit={(e) => (e.preventDefault(), run('password'))}>
			<div class="tiles">
				{#each PROVIDERS as p, i (p.id)}
					<button class="tile in {p.id}" style="--d:{60 + i * 60}ms" type="button" disabled={busy !== null} onclick={() => run(p.id)}>
						<span class="sweep" aria-hidden="true"></span>
						<span class="mark" aria-hidden="true">
							{#if p.id === 'google'}
								<img src="/brand/google-g.svg" width="20" height="20" alt="" />
							{:else if p.id === 'huggingface'}
								<img src="/brand/huggingface.svg" width="20" height="20" alt="" />
							{:else}
								<svg viewBox="0 0 24 24" width="20" height="20"><path fill="currentColor" d="M10.226 17.284c-2.965-.36-5.054-2.493-5.054-5.256 0-1.123.404-2.336 1.078-3.144-.292-.741-.247-2.314.09-2.965.898-.112 2.111.36 2.83 1.01.853-.269 1.752-.404 2.853-.404 1.1 0 1.999.135 2.807.382.696-.629 1.932-1.1 2.83-.988.315.606.36 2.179.067 2.942.72.854 1.101 2 1.101 3.167 0 2.763-2.089 4.852-5.098 5.234.763.494 1.28 1.572 1.28 2.807v2.336c0 .674.561 1.056 1.235.786 4.066-1.55 7.255-5.615 7.255-10.646C23.5 6.188 18.334 1 11.978 1 5.62 1 .5 6.188.5 12.545c0 4.986 3.167 9.12 7.435 10.669.606.225 1.19-.18 1.19-.786V20.63a2.9 2.9 0 0 1-1.078.224c-1.483 0-2.359-.808-2.987-2.313-.247-.607-.517-.966-1.034-1.033-.27-.023-.359-.135-.359-.27 0-.27.45-.471.898-.471.652 0 1.213.404 1.797 1.235.45.651.921.943 1.483.943.561 0 .92-.202 1.437-.719.382-.381.674-.718.944-.943" /></svg>
							{/if}
						</span>
						<span class="tile-text">
							<span class="via">{busy === p.id ? t.busy : t.via}</span>
							<span class="name">{p.name}</span>
						</span>
					</button>
				{/each}
			</div>
			<p class="implied in" style="--d:240ms">{t.implied} <a href={href(lang, '/legal/terms')}>{t.termsLink}</a> {t.and} <a href={href(lang, '/legal/privacy')}>{t.privacyLink}</a>.</p>

			<p class="or in" style="--d:240ms"><span>{t.or}</span></p>

			<fieldset class="pw in" style="--d:270ms">
				<legend class="sr-only">{t.pwTitle}</legend>
				<div class="pw-top">
					<div class="seg" class:right={register}>
						<span class="thumb" aria-hidden="true"></span>
						<label><input type="radio" name="mode" value="login" bind:group={mode} /><span>{t.login}</span></label>
						<label><input type="radio" name="mode" value="register" bind:group={mode} /><span>{t.register}</span></label>
					</div>
					<span class="pw-title" aria-hidden="true">{t.pwTitle}</span>
				</div>

				<div class="fields">
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
							aria-describedby={userBad ? 'acc-user-err' : 'acc-user-hint'}
						/>
						<span class="sr-only" id="acc-user-hint">{t.usernameHint}</span>
						{#if userBad}<span class="error-text" id="acc-user-err">{t.errUsername}</span>{/if}
					</div>
					<div class="field">
						<label for="acc-pass">{t.password} <span class="req">{t.passwordHint}</span></label>
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
								aria-describedby={passBad ? 'acc-pass-err' : undefined}
							/>
							<button class="eye" type="button" aria-label={t.show} aria-pressed={reveal} aria-controls={register ? 'acc-pass acc-pass2' : 'acc-pass'} onclick={() => (reveal = !reveal)}>
								<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
									<path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12Z" /><circle cx="12" cy="12" r="3" />
									{#if reveal}<path d="M4 4l16 16" />{/if}
								</svg>
							</button>
						</div>
						{#if passBad}<span class="error-text" id="acc-pass-err">{t.errPassword}</span>{/if}
					</div>
				</div>

				<!-- register-only rows: kept in the DOM (inert when closed) so the height can ease open -->
				<div class="more" class:open={register} inert={!register}>
					<div class="more-in">
						<div class="row2">
							<p class="recovery">
								<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="4" y="10.5" width="16" height="10" rx="2.5" /><path d="M8 10.5V8a4 4 0 0 1 8 0v2.5" /></svg>
								<span>{t.noRecovery}</span>
							</p>
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
						</div>
						<div class="consent">
							<label class="check">
								<input type="checkbox" bind:checked={terms} aria-invalid={termsBad} aria-describedby={termsBad ? 'terms-err' : undefined} />
								<span>{t.terms} <a href={href(lang, '/legal/terms')}>{t.termsLink}</a> {t.and} <a href={href(lang, '/legal/privacy')}>{t.privacyLink}</a>.</span>
							</label>
							{#if termsBad}<span class="error-text" id="terms-err">{t.errTerms}</span>{/if}
						</div>
					</div>
				</div>

				<button class="go" type="submit" disabled={busy !== null}>
					<span>{busy === 'password' ? t.busy : register ? t.register : t.login}</span>
					<span class="arrow" aria-hidden="true">→</span>
				</button>
			</fieldset>

			<p class="status" role="status">{#if failMsg}<span class="error-text">{failMsg}</span>{/if}</p>
		</form>
	</div>
</section>

<style>
	@property --spin {
		syntax: '<angle>';
		inherits: false;
		initial-value: 0deg;
	}

	/* ---------- one screen: the section fills the viewport under the sticky header ---------- */
	.acct {
		position: relative;
		isolation: isolate;
		overflow: clip;
		/* slide under the translucent header so the field fills the whole screen */
		margin-top: -4.2rem;
		padding: calc(4.2rem + clamp(0.5rem, 2.4vh, 2.5rem)) var(--gutter, 1rem) clamp(0.75rem, 3vh, 3rem);
		min-height: 100svh;
		display: grid;
		place-items: center;
	}
	.bg {
		position: absolute;
		inset: 0;
		z-index: -1;
	}
	/* calm the field behind the card: near-black in the middle, embers at the edges and below */
	.veil {
		position: absolute;
		inset: 0;
		background:
			radial-gradient(42% 52% at 50% 46%, color-mix(in srgb, var(--bg-0) 88%, transparent), transparent 75%),
			linear-gradient(180deg, color-mix(in srgb, var(--bg-0) 70%, transparent), transparent 30%);
	}
	:global(:root[data-theme='light']) .bg :global(.heatfield) {
		display: none;
	}
	:global(:root[data-theme='light']) .veil {
		background:
			radial-gradient(40% 40% at 50% 20%, color-mix(in srgb, var(--heat-4) 30%, transparent), transparent 70%),
			radial-gradient(30% 30% at 18% 70%, color-mix(in srgb, var(--heat-3) 12%, transparent), transparent 70%),
			radial-gradient(30% 30% at 82% 64%, color-mix(in srgb, var(--heat-5) 80%, transparent), transparent 70%);
	}
	.wrap {
		display: grid;
		justify-items: center;
		gap: clamp(0.75rem, 2.6vh, 1.75rem);
		width: min(100%, 62rem);
	}

	/* ---------- entrance: once, < 600 ms ---------- */
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
		font-size: clamp(1.75rem, 1.1rem + 2.6vw, 3.25rem);
		font-weight: 750;
		font-stretch: 108%;
		line-height: 1.05;
		letter-spacing: -0.03em;
		color: var(--text-hi);
		text-wrap: balance;
	}
	.sub {
		color: var(--text);
		font-size: clamp(1rem, 0.95rem + 0.3vw, 1.15rem);
	}

	/* ---------- glass card with a slowly travelling ember border ---------- */
	.glass {
		position: relative;
		display: grid;
		--g: clamp(0.6rem, 1.5vh, 0.95rem);
		gap: clamp(0.65rem, 1.7vh, 1.1rem);
		width: min(100%, 40rem);
		padding: clamp(0.9rem, 3vh, 1.75rem) clamp(1rem, 0.6rem + 1.6vw, 1.75rem);
		border-radius: 1.5rem;
		background: color-mix(in srgb, var(--bg-1) 72%, transparent);
		backdrop-filter: blur(18px) saturate(1.3);
		-webkit-backdrop-filter: blur(18px) saturate(1.3);
		box-shadow:
			var(--shadow-2),
			0 40px 120px -60px color-mix(in srgb, var(--heat-3) 70%, transparent);
	}
	.glass::before {
		content: '';
		position: absolute;
		inset: 0;
		padding: 1px;
		border-radius: inherit;
		pointer-events: none;
		background:
			conic-gradient(from var(--spin), transparent 0 52%, color-mix(in srgb, var(--heat-2) 90%, transparent) 66%, var(--heat-4) 76%, transparent 90%),
			linear-gradient(var(--line-strong), var(--line-strong));
		-webkit-mask:
			linear-gradient(#000 0 0) content-box,
			linear-gradient(#000 0 0);
		mask:
			linear-gradient(#000 0 0) content-box,
			linear-gradient(#000 0 0);
		-webkit-mask-composite: xor;
		mask-composite: exclude;
	}
	@media (prefers-reduced-motion: no-preference) {
		.glass::before {
			animation: spin 16s linear infinite;
		}
	}
	@keyframes spin {
		to {
			--spin: 360deg;
		}
	}
	:global(:root[data-theme='light']) .glass {
		background: color-mix(in srgb, #ffffff 78%, transparent);
	}

	/* ---------- provider tiles ---------- */
	.tiles {
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		gap: var(--sp-3);
	}
	.tile {
		--fill: #131314;
		--stroke: #8e918f;
		--ink: #e3e3e3;
		--mark: #ffffff;
		position: relative;
		display: grid;
		justify-items: center;
		align-content: center;
		gap: var(--sp-2);
		min-height: clamp(5.25rem, 12vh, 7.75rem);
		padding: var(--sp-4) var(--sp-2) var(--sp-3);
		border: 1px solid color-mix(in srgb, var(--stroke) 70%, transparent);
		border-radius: var(--r-lg);
		background: color-mix(in srgb, var(--fill) 88%, transparent);
		color: var(--ink);
		font: inherit;
		text-align: center;
		cursor: pointer;
		overflow: hidden;
		transition:
			transform 0.45s var(--ease-spring),
			box-shadow var(--dur-3) var(--ease-out),
			border-color var(--dur-3) var(--ease-out);
	}
	:global(:root[data-theme='light']) .tile {
		--fill: #ffffff;
		--stroke: #747775;
		--ink: #1f1f1f;
		--mark: #000000;
	}
	/* brand tint: a ring and a glow underneath, never on the mark's own background */
	.tile::before {
		content: '';
		position: absolute;
		inset: 0;
		padding: 1.5px;
		border-radius: inherit;
		background: var(--ring);
		opacity: 0;
		transition: opacity var(--dur-3) var(--ease-out);
		-webkit-mask:
			linear-gradient(#000 0 0) content-box,
			linear-gradient(#000 0 0);
		mask:
			linear-gradient(#000 0 0) content-box,
			linear-gradient(#000 0 0);
		-webkit-mask-composite: xor;
		mask-composite: exclude;
		pointer-events: none;
	}
	.google {
		--ring: conic-gradient(from 200deg, #4285f4, #34a853, #fbbc05, #ea4335, #4285f4);
		--glow:
			-14px 18px 34px -20px #4285f4, 0 22px 34px -20px #fbbc05, 14px 18px 34px -20px #ea4335;
	}
	.github {
		--ring: linear-gradient(160deg, #ffffff, #6e7681 60%, #30363d);
		--glow: 0 22px 40px -20px rgb(255 255 255 / 0.55);
	}
	:global(:root[data-theme='light']) .github {
		--ring: linear-gradient(160deg, #24292f, #6e7681);
		--glow: 0 22px 40px -20px rgb(36 41 47 / 0.6);
	}
	.huggingface {
		--ring: linear-gradient(160deg, #ffd21e, #ff9d00);
		--glow: 0 22px 40px -18px rgb(255 210 30 / 0.75);
	}
	.sweep {
		position: absolute;
		inset: -20% -60%;
		background: linear-gradient(105deg, transparent 40%, rgb(255 255 255 / 0.16) 50%, transparent 60%);
		transform: translate3d(-60%, 0, 0);
		pointer-events: none;
	}
	.mark {
		display: grid;
		place-items: center;
		width: clamp(2rem, 1.6rem + 1.4vw, 2.6rem);
		aspect-ratio: 1;
		color: var(--mark);
		transition: transform 0.45s var(--ease-spring);
	}
	.mark img,
	.mark svg {
		width: 100%;
		height: 100%;
	}
	.tile-text {
		display: grid;
		line-height: 1.2;
	}
	.via {
		color: color-mix(in srgb, var(--ink) 62%, transparent);
		font-size: var(--fs-2xs);
		letter-spacing: 0.02em;
	}
	.name {
		font-family: 'Google Sans', Roboto, var(--font-sans);
		font-size: var(--fs-sm);
		font-weight: 600;
	}
	.tile:not(:disabled):hover {
		transform: translate3d(0, -3px, 0);
		border-color: transparent;
		box-shadow: var(--glow);
	}
	.tile:not(:disabled):hover::before {
		opacity: 1;
	}
	.tile:not(:disabled):hover .mark {
		transform: scale(1.12);
	}
	.tile:not(:disabled):hover .sweep {
		transform: translate3d(60%, 0, 0);
		transition: transform 0.7s var(--ease-out);
	}
	.tile:active:not(:disabled) {
		transform: scale(0.96);
		transition-duration: 0.12s;
	}
	.tile:focus-visible {
		outline: 2px solid var(--heat-3);
		outline-offset: 3px;
	}
	.tile:focus-visible::before {
		opacity: 1;
	}
	.tile:disabled {
		cursor: progress;
	}

	.implied {
		margin-top: calc(-1 * var(--sp-1));
		color: var(--text-mute);
		font-size: var(--fs-xs);
		text-align: center;
		text-wrap: balance;
	}
	.implied a {
		color: var(--text);
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

	/* ---------- username + password ---------- */
	.pw {
		display: grid;
		gap: var(--g);
		margin: 0;
		padding: 0;
		border: 0;
		min-width: 0;
	}
	.pw-top {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: space-between;
		gap: var(--sp-2) var(--sp-4);
	}
	.pw-title {
		color: var(--text-mute);
		font-size: var(--fs-xs);
	}
	/* segmented toggle with a sliding thumb */
	.seg {
		position: relative;
		display: grid;
		grid-template-columns: 1fr 1fr;
		padding: 3px;
		border: 1px solid var(--line);
		border-radius: var(--r-pill);
		background: var(--bg-1);
	}
	.thumb {
		position: absolute;
		inset: 3px auto 3px 3px;
		width: calc(50% - 3px);
		border-radius: var(--r-pill);
		background: var(--text-hi);
		transition: transform 0.4s var(--ease-spring);
	}
	.seg.right .thumb {
		transform: translate3d(100%, 0, 0);
	}
	.seg label {
		position: relative;
		cursor: pointer;
	}
	.seg input {
		position: absolute;
		inset: 0;
		opacity: 0;
		cursor: pointer;
	}
	.seg span {
		display: block;
		padding: 0.4rem 1.1rem;
		border-radius: var(--r-pill);
		color: var(--text-mute);
		font-size: var(--fs-sm);
		font-weight: 550;
		text-align: center;
		white-space: nowrap;
		transition: color var(--dur-3) var(--ease-out);
	}
	.seg label:hover span {
		color: var(--text-hi);
	}
	.seg input:checked + span {
		color: var(--text-inv);
	}
	.seg input:focus-visible + span {
		outline: 2px solid var(--heat-3);
		outline-offset: 1px;
	}
	.fields,
	.row2 {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: var(--sp-3);
		align-items: start;
	}
	.field {
		display: grid;
		gap: 0.3rem;
	}
	.field > label {
		display: flex;
		flex-wrap: wrap;
		justify-content: space-between;
		gap: 0 var(--sp-2);
		color: var(--text-hi);
		font-size: var(--fs-xs);
		font-weight: 550;
	}
	.req {
		color: var(--text-mute);
		font-weight: 400;
	}
	.pw .input {
		min-height: 2.75rem;
		border-radius: var(--r-md);
		background: color-mix(in srgb, var(--bg-0) 60%, transparent);
	}
	.pw .input:focus-visible {
		border-color: var(--heat-3);
	}
	.pass {
		position: relative;
	}
	.pass .input {
		padding-right: 3rem;
	}
	.eye {
		position: absolute;
		top: 50%;
		right: 0.25rem;
		display: grid;
		place-items: center;
		width: 2.35rem;
		height: 2.35rem;
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
	/* register-only rows ease open (grid rows 0fr → 1fr); the inner box gets room for focus rings */
	.more {
		display: grid;
		grid-template-rows: 0fr;
		margin-top: calc(-1 * var(--g));
		transition:
			grid-template-rows 0.32s var(--ease-out),
			margin-top 0.32s var(--ease-out);
	}
	.more.open {
		grid-template-rows: 1fr;
		margin-top: 0;
	}
	.more-in {
		display: grid;
		gap: var(--g);
		min-height: 0;
		overflow: hidden;
		padding: 4px;
		margin: -4px;
	}
	.row2 {
		align-items: end;
	}
	.recovery {
		display: flex;
		gap: 0.45rem;
		align-items: baseline;
		padding-bottom: 0.75rem;
		color: var(--text-mute);
		font-size: var(--fs-xs);
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

	/* primary: ember gradient, dark ink (≥ 4.5:1 on the whole ramp), a shine crosses on hover */
	.go {
		position: relative;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: var(--sp-2);
		width: 100%;
		min-height: 3rem;
		border: 0;
		border-radius: var(--r-pill);
		background: linear-gradient(90deg, var(--heat-2), var(--heat-3) 70%, var(--heat-4));
		color: #1a0a03;
		font: inherit;
		font-weight: 700;
		font-size: var(--fs-base);
		cursor: pointer;
		overflow: hidden;
		box-shadow: 0 14px 40px -18px color-mix(in srgb, var(--heat-3) 95%, transparent);
		transition:
			transform 0.4s var(--ease-spring),
			box-shadow var(--dur-3) var(--ease-out);
	}
	.go::after {
		content: '';
		position: absolute;
		inset: 0 -40%;
		background: linear-gradient(105deg, transparent 40%, rgb(255 255 255 / 0.45) 50%, transparent 60%);
		transform: translate3d(-70%, 0, 0);
		pointer-events: none;
	}
	.go:not(:disabled):hover {
		box-shadow: 0 18px 50px -16px var(--heat-3);
	}
	.go:not(:disabled):hover::after {
		transform: translate3d(70%, 0, 0);
		transition: transform 0.8s var(--ease-out);
	}
	.go:not(:disabled):hover .arrow {
		transform: translateX(3px);
	}
	.go:active:not(:disabled) {
		transform: scale(0.98);
		transition-duration: 0.12s;
	}
	.go:focus-visible {
		outline: 2px solid var(--heat-3);
		outline-offset: 3px;
	}
	.go:disabled {
		cursor: progress;
	}
	.go .arrow {
		display: inline-block;
		transition: transform var(--dur-3) var(--ease-out);
	}
	.status:empty {
		display: none;
	}
	.status {
		margin-top: calc(-1 * var(--sp-2));
		font-size: var(--fs-sm);
		text-align: center;
	}

	@media (max-width: 600px) {
		.glass {
			padding: 1rem 0.9rem;
			border-radius: 1.25rem;
		}
		.tiles {
			gap: var(--sp-2);
		}
		.tile {
			min-height: 4.5rem;
			padding: var(--sp-3) var(--sp-1) var(--sp-2);
			gap: 0.35rem;
		}
		.name {
			font-size: var(--fs-xs);
		}
		/* Nazwa | Hasło stay side by side down to 360 px; the register row stacks */
		.row2 {
			grid-template-columns: minmax(0, 1fr);
		}
		/* phones: the repeat field first, the one-line warning under it */
		.row2 .recovery {
			order: 1;
			padding-bottom: 0;
		}
		.pw-title {
			display: none;
		}
		.seg {
			width: 100%;
		}
	}
	@media (max-width: 359px) {
		.fields {
			grid-template-columns: minmax(0, 1fr);
		}
	}
</style>
