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

<div class="wl">
	<h3 class="wl-title" id="wl-title">{t.title}</h3>
	{#if sent}
		<div class="thanks" tabindex="-1" bind:this={thanks} role="status">
			<p class="ok"><span aria-hidden="true">✓</span> {t.thanksTitle}</p>
			<p class="honest">{t.thanksBody}</p>
			<button class="cta cta--line" type="button" onclick={reset}>{t.again}</button>
		</div>
	{:else}
		<form bind:this={form} onsubmit={submit} novalidate aria-labelledby="wl-title">
			<div class="f f--email">
				<label for="wl-email">{t.email}</label>
				<input
					id="wl-email"
					type="email"
					autocomplete="email"
					inputmode="email"
					required
					bind:value={email}
					aria-invalid={tried && !emailOk}
					aria-describedby="wl-email-hint{tried && !emailOk ? ' wl-email-err' : ''}"
				/>
				<span class="hint" id="wl-email-hint">{t.emailHint}</span>
				{#if tried && !emailOk}<span class="err" id="wl-email-err">{t.errEmail}</span>{/if}
			</div>
			<fieldset class="f f--choice">
				<legend>{t.choice}</legend>
				<div class="choices">
					{#each t.choices as [id, label] (id)}
						<label class="choice">
							<input type="radio" name="wl-choice" value={id} bind:group={choice} />
							<span>{label}</span>
						</label>
					{/each}
				</div>
			</fieldset>
			<div class="f f--gpu">
				<label for="wl-gpu">{t.gpu}</label>
				<input id="wl-gpu" type="text" autocomplete="off" placeholder={t.gpuPh} bind:value={gpu} />
			</div>
			<div class="f f--consent">
				<label class="check">
					<input type="checkbox" bind:checked={agreed} aria-invalid={tried && !agreed} aria-describedby={tried && !agreed ? 'wl-consent-err' : undefined} />
					<span>{t.consent} <a href={href(lang, '/legal/privacy')}>{t.privacyLink}</a></span>
				</label>
				{#if tried && !agreed}<span class="err" id="wl-consent-err">{t.errConsent}</span>{/if}
			</div>
			<button class="cta cta--bone submit" type="submit">{t.submit} <span class="arrow" aria-hidden="true">→</span></button>
		</form>
	{/if}
</div>

<style>
	/* a single sign-up strip: title on the left, the form laid out across */
	.wl {
		display: grid;
		grid-template-columns: minmax(10rem, 0.5fr) minmax(0, 2fr);
		gap: var(--sp-5) clamp(1.5rem, 4vw, 4rem);
		align-items: start;
	}
	.wl-title {
		font-weight: 760;
		font-stretch: 112%;
		font-size: var(--fs-xl);
		letter-spacing: -0.02em;
		color: var(--text-hi);
		line-height: 1.1;
	}
	form {
		display: grid;
		grid-template-columns: minmax(0, 1.6fr) minmax(0, 1fr) auto;
		grid-template-areas:
			'email  gpu    submit'
			'choice choice choice'
			'consent consent consent';
		gap: var(--sp-5) var(--sp-4);
		align-items: start;
	}
	.f--email {
		grid-area: email;
	}
	.f--gpu {
		grid-area: gpu;
	}
	.f--choice {
		grid-area: choice;
	}
	.f--consent {
		grid-area: consent;
	}
	.submit {
		grid-area: submit;
		margin-top: 1.45rem;
		min-height: 3rem;
	}
	.f {
		display: grid;
		gap: var(--sp-2);
		margin: 0;
		padding: 0;
		border: 0;
		min-width: 0;
	}
	label,
	legend {
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--text);
	}
	legend {
		margin-bottom: var(--sp-2);
		padding: 0;
	}
	input[type='email'],
	input[type='text'] {
		height: 3rem;
		padding: 0 1rem;
		border: 1px solid var(--line-strong);
		border-radius: var(--r-md);
		background: var(--bg-0);
		color: var(--text-hi);
		font: inherit;
		font-size: var(--fs-base);
		transition:
			border-color var(--dur-2),
			box-shadow var(--dur-2);
	}
	input[type='email']:focus-visible,
	input[type='text']:focus-visible {
		outline: none;
		border-color: var(--text-hi);
		box-shadow: 0 0 0 3px rgb(237 234 227 / 0.18);
	}
	input[aria-invalid='true'] {
		border-color: var(--danger);
	}
	input::placeholder {
		color: var(--text-mute);
	}
	.hint {
		font-size: var(--fs-xs);
		color: var(--text-mute);
	}
	.err {
		font-size: var(--fs-xs);
		color: var(--danger-ink);
	}
	.choices {
		display: flex;
		flex-wrap: wrap;
		gap: var(--sp-2);
	}
	.choice {
		position: relative;
		display: flex;
		align-items: center;
		gap: var(--sp-3);
		min-height: 2.75rem;
		padding: var(--sp-2) var(--sp-4) var(--sp-2) var(--sp-3);
		border: 1px solid var(--line);
		border-radius: var(--r-pill);
		background: var(--bg-0);
		cursor: pointer;
		font-family: var(--font-sans);
		font-size: var(--fs-sm);
		text-transform: none;
		letter-spacing: 0;
		color: var(--text);
		transition:
			border-color var(--dur-2),
			color var(--dur-2),
			transform var(--dur-1);
	}
	.choice:hover {
		border-color: var(--line-strong);
	}
	.choice:active {
		transform: scale(0.98);
	}
	.choice:has(input:checked) {
		border-color: var(--text-hi);
		color: var(--text-hi);
		box-shadow: inset 0 0 0 1px var(--text-hi);
	}
	.choice:has(input:focus-visible) {
		outline: 2px solid var(--focus);
		outline-offset: 2px;
	}
	.choice input {
		accent-color: var(--text-hi);
		margin: 0;
	}
	.check {
		display: flex;
		gap: var(--sp-3);
		align-items: flex-start;
		font-family: var(--font-sans);
		font-size: var(--fs-sm);
		text-transform: none;
		letter-spacing: 0;
		line-height: 1.5;
		color: var(--text);
		cursor: pointer;
	}
	.check input {
		margin-top: 0.25rem;
		accent-color: var(--text-hi);
		width: 1rem;
		height: 1rem;
		flex: none;
	}
	.check a {
		color: var(--text-hi);
	}
	.submit {
		justify-content: center;
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
		color: var(--text-hi);
		font-weight: 700;
		font-size: var(--fs-lg);
	}
	.honest {
		padding: var(--sp-4);
		border-left: 2px solid var(--text-hi);
		background: var(--bg-2);
		border-radius: 0 var(--r-md) var(--r-md) 0;
		color: var(--text-hi);
		font-size: var(--fs-sm);
		line-height: 1.55;
		max-width: 60ch;
	}
	@media (max-width: 900px) {
		.wl {
			grid-template-columns: minmax(0, 1fr);
		}
		form {
			grid-template-columns: minmax(0, 1fr);
			grid-template-areas: 'email' 'gpu' 'choice' 'consent' 'submit';
		}
		.submit {
			margin-top: 0;
			width: 100%;
		}
	}
</style>
