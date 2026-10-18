<script lang="ts">
	import { goto } from '$app/navigation';
	import { tick } from 'svelte';
	import { BRAND } from '$lib/brand';
	import { currentLang, href } from '$lib/i18n';
	import { ob } from '$lib/onboarding/copy';
	import { saveSession, session } from '$lib/onboarding/session.svelte';
	import Shell from '$lib/onboarding/Shell.svelte';

	const lang = $derived(currentLang());
	const t = $derived(ob[lang].account);

	let email = $state('');
	let terms = $state(false);
	let marketing = $state(false);
	let tried = $state(false);
	let form: HTMLFormElement | undefined = $state();
	const emailOk = $derived(/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email.trim()));

	async function proceed(method: 'google' | 'github' | 'email') {
		tried = true;
		if (!terms || (method === 'email' && !emailOk)) {
			await tick();
			form?.querySelector<HTMLElement>('[aria-invalid="true"]')?.focus();
			return;
		}
		// Prototype: no OAuth redirect, no magic link. The choice is kept in this tab only.
		session.account = { method, email: method === 'email' ? email.trim() : null, marketing };
		saveSession();
		goto(href(lang, '/start/paths'));
	}
</script>

<svelte:head><title>{t.title}</title></svelte:head>

<Shell title={t.title} lead={t.lead}>
	<form class="card heat-card stage-card" bind:this={form} novalidate onsubmit={(e) => (e.preventDefault(), proceed('email'))}>
		<div class="oauth">
			<button class="oa" type="button" onclick={() => proceed('google')}>
				<svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true"><path fill="#4285F4" d="M21.6 12.2c0-.7-.1-1.4-.2-2H12v3.8h5.4a4.6 4.6 0 0 1-2 3v2.5h3.2c1.9-1.7 3-4.3 3-7.3Z" /><path fill="#34A853" d="M12 22c2.7 0 5-.9 6.6-2.4l-3.2-2.5c-.9.6-2 1-3.4 1-2.6 0-4.8-1.8-5.6-4.1H3.1v2.6A10 10 0 0 0 12 22Z" /><path fill="#FBBC05" d="M6.4 14c-.2-.6-.3-1.3-.3-2s.1-1.4.3-2V7.4H3.1a10 10 0 0 0 0 9.2L6.4 14Z" /><path fill="#EA4335" d="M12 6c1.5 0 2.8.5 3.8 1.5l2.9-2.9A10 10 0 0 0 3.1 7.4L6.4 10C7.2 7.7 9.4 6 12 6Z" /></svg>
				<span>{t.google}</span>
				<span class="arrow" aria-hidden="true">→</span>
			</button>
			<button class="oa" type="button" onclick={() => proceed('github')}>
				<svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M12 2a10 10 0 0 0-3.2 19.5c.5.1.7-.2.7-.5v-1.7c-2.8.6-3.4-1.3-3.4-1.3-.5-1.2-1.1-1.5-1.1-1.5-.9-.6.1-.6.1-.6 1 .1 1.5 1 1.5 1 .9 1.6 2.4 1.1 3 .9.1-.7.4-1.1.6-1.4-2.2-.2-4.6-1.1-4.6-5 0-1.1.4-2 1-2.7-.1-.3-.4-1.3.1-2.7 0 0 .8-.3 2.8 1a9.6 9.6 0 0 1 5 0c1.9-1.3 2.8-1 2.8-1 .5 1.4.2 2.4.1 2.7.6.7 1 1.6 1 2.7 0 3.9-2.3 4.8-4.6 5 .4.3.7.9.7 1.9V21c0 .3.2.6.7.5A10 10 0 0 0 12 2Z" /></svg>
				<span>{t.github}</span>
				<span class="arrow" aria-hidden="true">→</span>
			</button>
		</div>

		<p class="or"><span>{t.or}</span></p>

		<div class="field">
			<label for="acc-email" class="sr-only">{t.email}</label>
			<div class="magic" class:bad={tried && !emailOk && email !== ''}>
				<svg class="mail" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="2.5" /><path d="m4 7 8 6 8-6" /></svg>
				<input
					id="acc-email"
					type="email"
					autocomplete="email"
					placeholder={t.email}
					bind:value={email}
					aria-invalid={tried && !emailOk && email !== ''}
					aria-describedby="acc-email-hint"
				/>
				<button class="send" type="submit">{t.submit} <span class="arrow" aria-hidden="true">→</span></button>
			</div>
			<span class="hint" id="acc-email-hint">{t.emailHint}</span>
			{#if tried && email !== '' && !emailOk}<span class="error-text">{t.errEmail}</span>{/if}
		</div>

		<div class="consent">
			<label class="check">
				<input type="checkbox" bind:checked={terms} aria-invalid={tried && !terms} aria-describedby={tried && !terms ? 'terms-err' : undefined} />
				<span>{t.terms} <a href={href(lang, '/legal/terms')}>{t.termsLink}</a> {t.and} <a href={href(lang, '/legal/privacy')}>{t.privacyLink}</a>.</span>
			</label>
			{#if tried && !terms}<span class="error-text" id="terms-err">{t.errTerms}</span>{/if}
			<label class="check opt"><input type="checkbox" bind:checked={marketing} /> <span>{t.marketing}</span></label>
		</div>
	</form>

	<aside class="privacy" aria-labelledby="why-title">
		<h2 id="why-title" class="eyebrow">{t.why}</h2>
		<div class="cols">
			<ul class="store" role="list">
				{#each t.storeList as w (w)}<li><span class="ic yes" aria-hidden="true">✓</span>{w}</li>{/each}
			</ul>
			<div class="never">
				<p class="never-t"><span class="ic no" aria-hidden="true">✕</span>{t.neverTitle}</p>
				<ul role="list">{#each t.neverList as w (w)}<li>{w}</li>{/each}</ul>
			</div>
		</div>
		<p class="foot">{t.deletion} <span class="source">{BRAND.name} · OAuth: openid email / user:email</span></p>
	</aside>
</Shell>

<style>
	.stage-card {
		display: grid;
		gap: var(--sp-5);
		padding: clamp(1.25rem, 0.8rem + 2vw, 2.25rem);
	}
	.oauth {
		display: grid;
		gap: var(--sp-3);
	}
	.oa {
		display: grid;
		grid-template-columns: auto 1fr auto;
		align-items: center;
		gap: var(--sp-4);
		min-height: 3.75rem;
		padding: 0 var(--sp-6);
		border: 1px solid var(--line-strong);
		border-radius: var(--r-pill);
		background: var(--bg-1);
		color: var(--text-hi);
		font: inherit;
		font-size: var(--fs-md);
		font-weight: 620;
		font-stretch: 104%;
		text-align: left;
		cursor: pointer;
		transition:
			border-color var(--dur-2) var(--ease-out),
			box-shadow var(--dur-3) var(--ease-out),
			transform var(--dur-2) var(--ease-out);
	}
	.oa:hover {
		border-color: var(--heat-3);
		box-shadow:
			0 0 0 1px color-mix(in srgb, var(--heat-3) 50%, transparent),
			0 10px 36px -14px color-mix(in srgb, var(--heat-3) 80%, transparent);
	}
	.oa:active {
		transform: scale(0.985);
	}
	.oa .arrow {
		color: var(--text-mute);
		transition:
			transform var(--dur-3) var(--ease-out),
			color var(--dur-2);
	}
	.oa:hover .arrow {
		color: var(--accent-ink);
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
	/* magic-link field: one pill, heat ring on focus */
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
		transition:
			background var(--dur-2),
			box-shadow var(--dur-3);
	}
	.send:hover {
		box-shadow: 0 8px 30px -10px color-mix(in srgb, var(--heat-3) 90%, transparent);
	}
	.send:focus-visible {
		outline-offset: 3px;
	}
	.field {
		display: grid;
		gap: var(--sp-2);
	}
	.field .hint {
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

	/* privacy card */
	.privacy {
		display: grid;
		gap: var(--sp-4);
		margin-top: var(--sp-6);
		padding: var(--sp-5) var(--sp-6);
		border: 1px solid var(--line);
		border-radius: var(--r-xl);
		background: var(--bg-1);
	}
	.cols {
		display: grid;
		grid-template-columns: minmax(0, 1.3fr) minmax(0, 1fr);
		gap: var(--sp-5);
	}
	.privacy ul {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: var(--sp-2);
		font-size: var(--fs-sm);
		color: var(--text);
	}
	.store li {
		display: flex;
		gap: var(--sp-3);
		align-items: baseline;
	}
	.ic {
		flex: none;
		display: inline-grid;
		place-items: center;
		width: 1.35rem;
		height: 1.35rem;
		border-radius: 50%;
		font-size: 0.72rem;
		font-weight: 700;
		transform: translateY(0.15em);
	}
	.ic.yes {
		background: color-mix(in srgb, var(--heat-3) 18%, transparent);
		color: var(--accent-ink);
	}
	.ic.no {
		background: var(--bg-3);
		color: var(--text-hi);
	}
	.never {
		display: grid;
		gap: var(--sp-2);
		align-content: start;
		padding-left: var(--sp-5);
		border-left: 1px solid var(--line);
	}
	.never-t {
		display: flex;
		gap: var(--sp-3);
		align-items: baseline;
		font-weight: 650;
		color: var(--text-hi);
		font-size: var(--fs-sm);
	}
	.never ul {
		display: flex;
		flex-wrap: wrap;
		gap: var(--sp-2);
	}
	.never li {
		padding: 0.15rem 0.65rem;
		border: 1px solid var(--line-strong);
		border-radius: var(--r-pill);
		font-size: var(--fs-xs);
		text-decoration: line-through;
		text-decoration-color: color-mix(in srgb, var(--heat-2) 70%, transparent);
	}
	.foot {
		font-size: var(--fs-xs);
		color: var(--text-mute);
	}
	.foot .source {
		display: block;
		margin-top: var(--sp-1);
	}
	@media (max-width: 560px) {
		.cols {
			grid-template-columns: 1fr;
		}
		.never {
			padding-left: 0;
			border-left: 0;
			padding-top: var(--sp-4);
			border-top: 1px solid var(--line);
		}
		.magic {
			flex-wrap: wrap;
			border-radius: var(--r-xl);
			padding: var(--sp-2) var(--sp-2) var(--sp-2) var(--sp-4);
		}
		.send {
			width: 100%;
			justify-content: center;
		}
	}
</style>
