<script lang="ts">
	import { tick } from 'svelte';
	import { currentLang, href } from '$lib/i18n';
	import { copy } from './copy';

	const lang = $derived(currentLang());
	const t = $derived(copy[lang].pricing.form);

	let email = $state('');
	let choice = $state('yearly');
	let gpu = $state('');
	let agreed = $state(false);
	let tried = $state(false);
	let sent = $state(false);
	let thanks: HTMLElement | undefined = $state();
	let form: HTMLFormElement | undefined = $state();

	const emailOk = $derived(/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email.trim()));

	async function submit(e: SubmitEvent) {
		// Fake door: there is no backend. Nothing leaves the browser; we only show the honest thank-you.
		e.preventDefault();
		tried = true;
		if (!emailOk || !agreed) {
			await tick();
			form?.querySelector<HTMLElement>('[aria-invalid="true"]')?.focus();
			return;
		}
		sent = true;
		await tick();
		thanks?.focus();
	}

	async function reset() {
		sent = false;
		tried = false;
		email = '';
		gpu = '';
		agreed = false;
		await tick();
		form?.querySelector<HTMLElement>('input')?.focus();
	}
</script>

<div class="waitlist card">
	<h3 class="h3" id="wl-title">{t.title}</h3>
	{#if sent}
		<div class="thanks" tabindex="-1" bind:this={thanks} role="status">
			<p class="ok">✓ {t.thanksTitle}</p>
			<div class="notice notice--prototype">
				<span class="notice__icon">i</span>
				<p>{t.thanksBody}</p>
			</div>
			<button class="btn btn--secondary btn--sm" type="button" onclick={reset}>{t.again}</button>
		</div>
	{:else}
		<form bind:this={form} onsubmit={submit} novalidate aria-labelledby="wl-title" class="stack">
			<div class="field">
				<label for="wl-email">{t.email}</label>
				<input
					id="wl-email"
					class="input"
					type="email"
					autocomplete="email"
					inputmode="email"
					required
					bind:value={email}
					aria-invalid={tried && !emailOk}
					aria-describedby="wl-email-hint{tried && !emailOk ? ' wl-email-err' : ''}"
				/>
				<span class="hint" id="wl-email-hint">{t.emailHint}</span>
				{#if tried && !emailOk}<span class="error-text" id="wl-email-err">{t.errEmail}</span>{/if}
			</div>
			<fieldset class="field choices">
				<legend class="label">{t.choice}</legend>
				{#each t.choices as [id, label] (id)}
					<label class="choice">
						<input type="radio" name="wl-choice" value={id} bind:group={choice} />
						<span>{label}</span>
					</label>
				{/each}
			</fieldset>
			<div class="field">
				<label for="wl-gpu">{t.gpu}</label>
				<input id="wl-gpu" class="input" type="text" autocomplete="off" placeholder={t.gpuPh} bind:value={gpu} />
			</div>
			<div class="field">
				<label class="check">
					<input type="checkbox" bind:checked={agreed} aria-invalid={tried && !agreed} aria-describedby={tried && !agreed ? 'wl-consent-err' : undefined} />
					<span>{t.consent} <a href={href(lang, '/legal/privacy')}>{t.privacyLink}</a></span>
				</label>
				{#if tried && !agreed}<span class="error-text" id="wl-consent-err">{t.errConsent}</span>{/if}
			</div>
			<button class="btn btn--primary btn--block" type="submit">{t.submit}</button>
		</form>
	{/if}
</div>

<style>
	.waitlist {
		display: grid;
		gap: var(--sp-5);
		align-content: start;
	}
	.choices {
		border: 0;
		padding: 0;
		margin: 0;
		gap: var(--sp-2);
	}
	.choices legend {
		margin-bottom: var(--sp-2);
	}
	.choice {
		display: flex;
		gap: var(--sp-3);
		align-items: center;
		padding: var(--sp-3);
		border: 1px solid var(--line);
		border-radius: var(--r-sm);
		background: var(--bg-1);
		cursor: pointer;
		font-size: var(--fs-sm);
	}
	.choice:has(input:checked) {
		border-color: var(--accent-ink);
		background: var(--accent-soft);
		color: var(--text-hi);
	}
	.choice input {
		accent-color: var(--accent-ink);
		margin: 0;
	}
	.thanks {
		display: grid;
		gap: var(--sp-4);
		justify-items: start;
	}
	.thanks:focus {
		outline: none;
	}
	.ok {
		color: var(--ok-ink);
		font-weight: var(--fw-semibold);
		font-size: var(--fs-md);
	}
</style>
