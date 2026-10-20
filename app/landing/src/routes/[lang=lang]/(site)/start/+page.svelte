<script lang="ts">
	/**
	 * Account step (1 of 4). Google / GitHub / e-mail magic link through `$lib/auth`. With
	 * `PUBLIC_AUTH_PROVIDER=none` (no backend yet) the provider buttons stay visible but disabled, an
	 * honest "sign-in soon" note points to the e-mail field, and that field becomes the waitlist
	 * sign-up (kept in this tab only, like every prototype step).
	 *
	 * Brand marks: the Google "G" is Google's own asset (static/brand/google-g.svg, cut from the
	 * Sign in with Google bundle, unaltered) on the button colours from Google's branding guidelines;
	 * GitHub uses the Primer mark-github in pure white / black. Both buttons share size and weight
	 * (Google's equal-prominence rule).
	 */
	import { goto } from '$app/navigation';
	import { tick } from 'svelte';
	import { auth, signInWith, signInWithEmail, type OAuthProvider } from '$lib/auth';
	import { currentLang, href } from '$lib/i18n';
	import { ob } from '$lib/onboarding/copy';
	import { saveSession, session } from '$lib/onboarding/session.svelte';
	import Shell from '$lib/onboarding/Shell.svelte';

	const lang = $derived(currentLang());
	const t = $derived(ob[lang].account);
	const live = auth.live;

	let email = $state('');
	let terms = $state(false);
	let marketing = $state(false);
	/** What the visitor last tried; drives which errors show. */
	let tried = $state<'oauth' | 'email' | null>(null);
	let busy = $state<OAuthProvider | 'email' | null>(null);
	let sentTo = $state<string | null>(null);
	let failed = $state(false);
	let form: HTMLFormElement | undefined = $state();
	let emailInput: HTMLInputElement | undefined = $state();
	const emailOk = $derived(/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email.trim()));
	const termsBad = $derived(tried !== null && !terms);
	const emailBad = $derived(tried === 'email' && !emailOk);

	const providers = $derived([
		{ id: 'google' as const, label: t.google },
		{ id: 'github' as const, label: t.github }
	]);

	async function proceed(method: OAuthProvider | 'email') {
		tried = method === 'email' ? 'email' : 'oauth';
		failed = false;
		sentTo = null;
		if (!terms || (method === 'email' && !emailOk)) {
			await tick();
			form?.querySelector<HTMLElement>('[aria-invalid="true"]')?.focus();
			return;
		}
		const next = href(lang, '/start/paths');
		session.marketing = marketing;
		if (!live) {
			// No backend: the e-mail goes on the waitlist (this tab only, nothing is sent).
			session.account = { method: 'waitlist', email: email.trim() };
			saveSession();
			goto(next);
			return;
		}
		saveSession();
		busy = method;
		const res = method === 'email' ? await signInWithEmail(email.trim(), { redirectTo: next }) : await signInWith(method, { redirectTo: next });
		if (res.status === 'redirecting') return;
		busy = null;
		if (res.status === 'email-sent') sentTo = email.trim();
		else failed = true;
	}

	function toWaitlist(e: MouseEvent) {
		e.preventDefault();
		emailInput?.focus({ preventScroll: true });
		emailInput?.scrollIntoView({ block: 'center', behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' });
	}
</script>

<svelte:head><title>{t.title}</title></svelte:head>

<Shell title={t.heading} lead={t.lead} step={1} wide>
	<div class="acct">
		<form class="card heat-card panel" bind:this={form} novalidate aria-busy={busy !== null} onsubmit={(e) => (e.preventDefault(), proceed('email'))}>
			<div class="oauth rise" style="--d:0ms">
				{#each providers as p (p.id)}
					<button class="oa" type="button" disabled={!live || busy !== null} aria-describedby={live ? undefined : 'auth-soon'} onclick={() => proceed(p.id)}>
						<span class="mark" aria-hidden="true">
							{#if p.id === 'google'}
								<img src="/brand/google-g.svg" width="20" height="20" alt="" />
							{:else}
								<svg viewBox="0 0 24 24" width="20" height="20"><path fill="currentColor" d="M10.226 17.284c-2.965-.36-5.054-2.493-5.054-5.256 0-1.123.404-2.336 1.078-3.144-.292-.741-.247-2.314.09-2.965.898-.112 2.111.36 2.83 1.01.853-.269 1.752-.404 2.853-.404 1.1 0 1.999.135 2.807.382.696-.629 1.932-1.1 2.83-.988.315.606.36 2.179.067 2.942.72.854 1.101 2 1.101 3.167 0 2.763-2.089 4.852-5.098 5.234.763.494 1.28 1.572 1.28 2.807v2.336c0 .674.561 1.056 1.235.786 4.066-1.55 7.255-5.615 7.255-10.646C23.5 6.188 18.334 1 11.978 1 5.62 1 .5 6.188.5 12.545c0 4.986 3.167 9.12 7.435 10.669.606.225 1.19-.18 1.19-.786V20.63a2.9 2.9 0 0 1-1.078.224c-1.483 0-2.359-.808-2.987-2.313-.247-.607-.517-.966-1.034-1.033-.27-.023-.359-.135-.359-.27 0-.27.45-.471.898-.471.652 0 1.213.404 1.797 1.235.45.651.921.943 1.483.943.561 0 .92-.202 1.437-.719.382-.381.674-.718.944-.943" /></svg>
							{/if}
						</span>
						<span class="oa-label">{busy === p.id ? t.busy : p.label}</span>
						{#if !live}<span class="soon-tag mono">{t.soonBadge}</span>{/if}
					</button>
				{/each}
			</div>

			{#if !live}
				<div class="soon rise" style="--d:90ms" id="auth-soon">
					<span class="pulse" aria-hidden="true"></span>
					<div>
						<p class="soon-t">{t.soonTitle}</p>
						<p class="soon-b">{t.soonBody}</p>
						<a class="soon-cta" href="#acc-email" onclick={toWaitlist}>{t.soonCta} <span class="arrow" aria-hidden="true">↓</span></a>
					</div>
				</div>
			{/if}

			<p class="or rise" style="--d:150ms"><span>{live ? t.or : t.orWaitlist}</span></p>

			<div class="field rise" style="--d:210ms">
				<label for="acc-email" class="sr-only">{t.email}</label>
				<div class="magic" class:bad={emailBad}>
					<svg class="mail" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="2.5" /><path d="m4 7 8 6 8-6" /></svg>
					<input
						id="acc-email"
						type="email"
						autocomplete="email"
						placeholder={t.email}
						bind:this={emailInput}
						bind:value={email}
						aria-invalid={emailBad}
						aria-describedby={emailBad ? 'acc-email-hint acc-email-err' : 'acc-email-hint'}
					/>
					<button class="send" type="submit" disabled={busy !== null}>{busy === 'email' ? t.busy : live ? t.submit : t.waitSubmit} <span class="arrow" aria-hidden="true">→</span></button>
				</div>
				<span class="hint" id="acc-email-hint">{live ? t.emailHint : t.waitHint}</span>
				{#if emailBad}<span class="error-text" id="acc-email-err">{t.errEmail}</span>{/if}
			</div>

			<div class="consent rise" style="--d:270ms">
				<label class="check">
					<input type="checkbox" bind:checked={terms} aria-invalid={termsBad} aria-describedby={termsBad ? 'terms-err' : undefined} />
					<span>{t.terms} <a href={href(lang, '/legal/terms')}>{t.termsLink}</a> {t.and} <a href={href(lang, '/legal/privacy')}>{t.privacyLink}</a>.</span>
				</label>
				{#if termsBad}<span class="error-text" id="terms-err">{live ? t.errTerms : t.errTermsWait}</span>{/if}
				<label class="check opt"><input type="checkbox" bind:checked={marketing} /> <span>{t.marketing}</span></label>
			</div>

			<p class="status" role="status">
				{#if sentTo}<span class="ok">{t.sent(sentTo)}</span>{:else if failed}<span class="error-text">{t.errAuth}</span>{/if}
			</p>
		</form>

		<aside class="store rise" style="--d:180ms" aria-labelledby="why-title">
			<h2 id="why-title" class="eyebrow">{t.why}</h2>
			<ul class="yes" role="list">
				{#each t.storeList as w (w)}<li><span class="ic" aria-hidden="true">✓</span><span>{w}</span></li>{/each}
			</ul>
			<div class="never">
				<p class="never-t"><span class="ic no" aria-hidden="true">✕</span>{t.neverTitle}</p>
				<ul class="chips" role="list">{#each t.neverList as w (w)}<li>{w}</li>{/each}</ul>
			</div>
			<p class="foot">{t.deletion}</p>
			<p class="source">{t.scopes}</p>
		</aside>
	</div>
</Shell>

<style>
	.acct {
		display: grid;
		grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr);
		gap: var(--sp-6);
		align-items: start;
		width: min(100%, 62rem);
		margin-inline: auto;
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

	/* ---------- the sign-in card ---------- */
	.panel {
		position: relative;
		display: grid;
		gap: var(--sp-5);
		padding: clamp(1.25rem, 0.8rem + 2vw, 2.25rem);
		border-radius: var(--r-xl);
	}
	.oauth {
		display: grid;
		gap: var(--sp-3);
	}
	/*
	 * Provider buttons, Google's custom-button spec scaled 1.3× (40 → 52 px, G 20 → 26 px, 12 / 10 px
	 * padding → 16 / 13 px): dark fill #131314, 1 px #8E918F stroke, #E3E3E3 text; light theme
	 * #FFFFFF / #747775 / #1F1F1F. GitHub gets the identical shell (equal prominence). The heat ring
	 * on hover sits outside the stroke, so neither brand surface is recoloured.
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
		padding: 0 1rem;
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
	.oa:not(:disabled):hover {
		box-shadow:
			0 0 0 3px color-mix(in srgb, var(--heat-3) 35%, transparent),
			0 14px 40px -16px color-mix(in srgb, var(--heat-3) 90%, transparent);
	}
	.oa:not(:disabled):active {
		transform: scale(0.985);
	}
	.oa:focus-visible {
		outline: 2px solid var(--heat-3);
		outline-offset: 3px;
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
	/* Google's own disabled state: content at 38 %, the stroke stays */
	.oa:disabled {
		cursor: not-allowed;
	}
	.oa:disabled .mark,
	.oa:disabled .oa-label {
		opacity: 0.38;
	}
	.soon-tag {
		flex: none;
		padding: 0.15rem 0.55rem;
		border: 1px solid color-mix(in srgb, var(--heat-3) 55%, transparent);
		border-radius: var(--r-pill);
		color: var(--heat-4);
		font-size: var(--fs-2xs);
		letter-spacing: 0.08em;
		text-transform: uppercase;
	}
	:global(:root[data-theme='light']) .soon-tag {
		color: var(--oa-ink);
	}

	/* ---------- honest "sign-in soon" note ---------- */
	.soon {
		display: grid;
		grid-template-columns: auto minmax(0, 1fr);
		gap: var(--sp-3);
		padding: var(--sp-4) var(--sp-5);
		border: 1px solid color-mix(in srgb, var(--heat-3) 35%, var(--line));
		border-radius: var(--r-lg);
		background:
			radial-gradient(80% 120% at 0% 0%, color-mix(in srgb, var(--heat-3) 12%, transparent), transparent 70%),
			var(--bg-1);
	}
	.pulse {
		position: relative;
		width: 0.55rem;
		height: 0.55rem;
		margin-top: 0.45rem;
		border-radius: 50%;
		background: var(--heat-3);
		box-shadow: 0 0 10px var(--heat-3);
	}
	@media (prefers-reduced-motion: no-preference) {
		.pulse::after {
			content: '';
			position: absolute;
			inset: 0;
			border-radius: 50%;
			background: var(--heat-3);
			animation: pulse 2.4s var(--ease-out) infinite;
		}
	}
	@keyframes pulse {
		to {
			transform: scale(3);
			opacity: 0;
		}
	}
	.soon-t {
		color: var(--text-hi);
		font-weight: 650;
	}
	.soon-b {
		margin-top: var(--sp-1);
		font-size: var(--fs-sm);
		color: var(--text);
	}
	.soon-cta {
		display: inline-flex;
		align-items: center;
		gap: 0.4rem;
		margin-top: var(--sp-3);
		color: var(--text-hi);
		font-size: var(--fs-sm);
		font-weight: 650;
		text-decoration: underline;
		text-decoration-color: color-mix(in srgb, var(--heat-3) 70%, transparent);
		text-underline-offset: 0.25em;
	}
	.soon-cta .arrow {
		display: inline-block;
		transition: transform var(--dur-3) var(--ease-out);
	}
	.soon-cta:hover .arrow {
		transform: translateY(3px);
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

	/* ---------- magic-link / waitlist field: one pill, heat ring on focus ---------- */
	.magic {
		display: flex;
		align-items: center;
		gap: var(--sp-3);
		padding: 0.35rem 0.35rem 0.35rem var(--sp-5);
		border: 1px solid var(--line-strong);
		border-radius: var(--r-pill);
		background: var(--bg-1);
		transition:
			border-color var(--dur-2) var(--ease-out),
			box-shadow var(--dur-3) var(--ease-out);
	}
	.magic:focus-within {
		border-color: var(--heat-3);
		box-shadow:
			0 0 0 3px color-mix(in srgb, var(--heat-3) 28%, transparent),
			0 0 34px -6px color-mix(in srgb, var(--heat-3) 70%, transparent);
	}
	.magic.bad {
		border-color: var(--danger-ink);
	}
	.mail {
		flex: none;
		color: var(--text-mute);
	}
	.magic:focus-within .mail {
		color: var(--accent-ink);
	}
	.magic input {
		flex: 1;
		min-width: 0;
		min-height: 2.9rem;
		border: 0;
		background: transparent;
		color: var(--text-hi);
		font: inherit;
		font-size: var(--fs-md);
		outline: none;
	}
	.magic input::placeholder {
		color: var(--text-mute);
	}
	.send {
		flex: none;
		display: inline-flex;
		align-items: center;
		gap: var(--sp-2);
		min-height: 2.9rem;
		padding: 0 var(--sp-5);
		border: 0;
		border-radius: var(--r-pill);
		background: var(--text-hi);
		color: var(--text-inv);
		font: inherit;
		font-weight: 650;
		font-size: var(--fs-sm);
		cursor: pointer;
		transition: box-shadow var(--dur-3);
	}
	.send:hover {
		box-shadow: 0 8px 30px -10px color-mix(in srgb, var(--heat-3) 90%, transparent);
	}
	.send:focus-visible {
		outline-offset: 3px;
	}
	.send .arrow {
		display: inline-block;
		transition: transform var(--dur-3) var(--ease-out);
	}
	.send:hover .arrow {
		transform: translateX(3px);
	}
	.field {
		display: grid;
		gap: var(--sp-2);
	}
	.field .hint,
	.field .error-text {
		padding-left: var(--sp-5);
	}
	.consent {
		display: grid;
		gap: var(--sp-3);
		padding-top: var(--sp-4);
		border-top: 1px solid var(--line);
	}
	.opt {
		color: var(--text-mute);
		font-size: var(--fs-xs);
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
	.ok {
		color: var(--text-hi);
	}

	/* ---------- compact "what we store" panel ---------- */
	.store {
		display: grid;
		gap: var(--sp-4);
		padding: var(--sp-6);
		border: 1px solid var(--line);
		border-radius: var(--r-xl);
		background:
			radial-gradient(90% 60% at 100% 0%, color-mix(in srgb, var(--heat-2) 10%, transparent), transparent 70%),
			color-mix(in srgb, var(--bg-1) 82%, transparent);
		backdrop-filter: blur(10px);
	}
	.store ul {
		list-style: none;
		margin: 0;
		padding: 0;
	}
	.yes {
		display: grid;
		gap: var(--sp-3);
		font-size: var(--fs-sm);
		color: var(--text);
	}
	.yes li {
		display: grid;
		grid-template-columns: auto minmax(0, 1fr);
		gap: var(--sp-3);
		align-items: baseline;
	}
	.ic {
		display: inline-grid;
		place-items: center;
		width: 1.35rem;
		height: 1.35rem;
		border-radius: 50%;
		background: color-mix(in srgb, var(--heat-3) 18%, transparent);
		color: var(--accent-ink);
		font-size: 0.72rem;
		font-weight: 700;
		transform: translateY(0.15em);
	}
	.ic.no {
		background: var(--bg-3);
		color: var(--text-hi);
	}
	.never {
		display: grid;
		gap: var(--sp-2);
		padding-top: var(--sp-4);
		border-top: 1px solid var(--line);
	}
	.never-t {
		display: flex;
		gap: var(--sp-3);
		align-items: baseline;
		color: var(--text-hi);
		font-size: var(--fs-sm);
		font-weight: 650;
	}
	.chips {
		display: flex;
		flex-wrap: wrap;
		gap: var(--sp-2);
	}
	.chips li {
		padding: 0.15rem 0.65rem;
		border: 1px solid var(--line-strong);
		border-radius: var(--r-pill);
		color: var(--text);
		font-size: var(--fs-xs);
		text-decoration: line-through;
		text-decoration-color: color-mix(in srgb, var(--heat-2) 70%, transparent);
	}
	.foot {
		font-size: var(--fs-xs);
		color: var(--text-mute);
	}
	.store .source {
		margin-top: calc(-1 * var(--sp-3));
	}

	@media (max-width: 900px) {
		.acct {
			grid-template-columns: minmax(0, 1fr);
			width: min(100%, 40rem);
		}
	}
	@media (max-width: 560px) {
		.magic {
			flex-wrap: wrap;
			border-radius: var(--r-xl);
			padding: var(--sp-2) var(--sp-2) var(--sp-2) var(--sp-4);
		}
		.send {
			width: 100%;
			justify-content: center;
		}
		.field .hint,
		.field .error-text {
			padding-left: var(--sp-2);
		}
		.soon {
			padding: var(--sp-4);
		}
		/* one line per provider: the note right under the buttons already says "soon" */
		.soon-tag {
			display: none;
		}
		.oa {
			font-size: var(--fs-base);
		}
		.store {
			padding: var(--sp-5);
		}
	}
</style>
