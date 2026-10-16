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

<Shell step={1} title={t.title} lead={t.lead}>
	<div class="grid">
		<form class="card stack" bind:this={form} novalidate onsubmit={(e) => (e.preventDefault(), proceed('email'))}>
			<div class="field">
				<label class="check">
					<input type="checkbox" bind:checked={terms} aria-invalid={tried && !terms} aria-describedby={tried && !terms ? 'terms-err' : undefined} />
					<span>{t.terms} <a href={href(lang, '/legal/terms')}>{t.termsLink}</a> {t.and} <a href={href(lang, '/legal/privacy')}>{t.privacyLink}</a>.</span>
				</label>
				{#if tried && !terms}<span class="error-text" id="terms-err">{t.errTerms}</span>{/if}
			</div>
			<div class="oauth">
				<button class="btn btn--secondary btn--lg btn--block" type="button" onclick={() => proceed('google')}>
					<svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M21.6 12.2c0-.7-.1-1.4-.2-2H12v3.8h5.4a4.6 4.6 0 0 1-2 3v2.5h3.2c1.9-1.7 3-4.3 3-7.3Z" /><path fill="currentColor" opacity=".75" d="M12 22c2.7 0 5-.9 6.6-2.4l-3.2-2.5c-.9.6-2 1-3.4 1-2.6 0-4.8-1.8-5.6-4.1H3.1v2.6A10 10 0 0 0 12 22Z" /><path fill="currentColor" opacity=".55" d="M6.4 14c-.2-.6-.3-1.3-.3-2s.1-1.4.3-2V7.4H3.1a10 10 0 0 0 0 9.2L6.4 14Z" /><path fill="currentColor" opacity=".9" d="M12 6c1.5 0 2.8.5 3.8 1.5l2.9-2.9A10 10 0 0 0 3.1 7.4L6.4 10C7.2 7.7 9.4 6 12 6Z" /></svg>
					{t.google}
				</button>
				<button class="btn btn--secondary btn--lg btn--block" type="button" onclick={() => proceed('github')}>
					<svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M12 2a10 10 0 0 0-3.2 19.5c.5.1.7-.2.7-.5v-1.7c-2.8.6-3.4-1.3-3.4-1.3-.5-1.2-1.1-1.5-1.1-1.5-.9-.6.1-.6.1-.6 1 .1 1.5 1 1.5 1 .9 1.6 2.4 1.1 3 .9.1-.7.4-1.1.6-1.4-2.2-.2-4.6-1.1-4.6-5 0-1.1.4-2 1-2.7-.1-.3-.4-1.3.1-2.7 0 0 .8-.3 2.8 1a9.6 9.6 0 0 1 5 0c1.9-1.3 2.8-1 2.8-1 .5 1.4.2 2.4.1 2.7.6.7 1 1.6 1 2.7 0 3.9-2.3 4.8-4.6 5 .4.3.7.9.7 1.9V21c0 .3.2.6.7.5A10 10 0 0 0 12 2Z" /></svg>
					{t.github}
				</button>
			</div>
			<p class="or"><span>{t.or}</span></p>
			<div class="field">
				<label for="acc-email">{t.email}</label>
				<input
					id="acc-email"
					class="input"
					type="email"
					autocomplete="email"
					bind:value={email}
					aria-invalid={tried && !emailOk && email !== ''}
					aria-describedby="acc-email-hint"
				/>
				<span class="hint" id="acc-email-hint">{t.emailHint}</span>
				{#if tried && email !== '' && !emailOk}<span class="error-text">{t.errEmail}</span>{/if}
			</div>
			<label class="check"><input type="checkbox" bind:checked={marketing} /> <span>{t.marketing}</span></label>
			<button class="btn btn--primary btn--lg btn--block" type="submit">{t.submit} <span class="arrow" aria-hidden="true">→</span></button>
		</form>
		<aside class="card card--inset stack why" aria-labelledby="why-title">
			<h2 id="why-title" class="h3">{t.why}</h2>
			<ul>{#each t.whyList as w (w)}<li>{w}</li>{/each}</ul>
			<p class="small">{t.never}</p>
			<p class="small mute">{t.deletion}</p>
			<p class="source">{BRAND.name} · OAuth: openid email / user:email</p>
		</aside>
	</div>
</Shell>

<style>
	.grid {
		display: grid;
		grid-template-columns: minmax(0, 1.2fr) minmax(0, 1fr);
		gap: var(--sp-6);
		align-items: start;
		max-width: 60rem;
	}
	@media (max-width: 820px) {
		.grid {
			grid-template-columns: 1fr;
		}
	}
	form {
		--stack: var(--sp-5);
	}
	.oauth {
		display: grid;
		gap: var(--sp-3);
	}
	.or {
		display: grid;
		grid-template-columns: 1fr auto 1fr;
		align-items: center;
		gap: var(--sp-3);
		color: var(--text-mute);
		font-size: var(--fs-xs);
		text-transform: uppercase;
		letter-spacing: 0.1em;
	}
	.or::before,
	.or::after {
		content: '';
		height: 1px;
		background: var(--line);
	}
	.why ul {
		margin: 0;
		padding-left: 1.2em;
		display: grid;
		gap: var(--sp-2);
		font-size: var(--fs-sm);
	}
</style>
