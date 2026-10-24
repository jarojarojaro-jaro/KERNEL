<script lang="ts">
	import type { LicenseInfo } from '../../shared/types';
	import ScreenHead from '../components/ScreenHead.svelte';
	import { api } from '../lib/api';
	import { date } from '../lib/i18n';
	import { store } from '../lib/store.svelte';

	let { onscanfirst }: { onscanfirst: () => void } = $props();

	const t = $derived(store.t.license);
	const lang = $derived(store.lang);
	const current = $derived(store.state?.license ?? null);

	let key = $state('');
	let busy = $state(false);
	let fieldError = $state('');
	let checked = $state<LicenseInfo | null>(null);
	let editing = $state(false);
	let input: HTMLTextAreaElement | undefined = $state();

	const shown = $derived(checked ?? current);
	const showForm = $derived(editing || !current?.valid);

	async function submit(e: SubmitEvent) {
		e.preventDefault();
		const k = key.trim();
		fieldError = !k ? t.empty : !k.startsWith('ENIGMA-') ? t.badPrefix : '';
		if (fieldError) {
			input?.focus();
			return;
		}
		busy = true;
		try {
			checked = await api.license(k);
			if (checked.valid) editing = false;
		} catch (err) {
			checked = { valid: false, reason: err instanceof Error ? err.message : String(err) };
		} finally {
			busy = false;
		}
	}

	function daysLeft(exp: number): number {
		return Math.max(0, Math.ceil((exp * 1000 - Date.now()) / 86_400_000));
	}
</script>

<section class="screen" aria-labelledby="lic-title">
	{#if showForm}
		<ScreenHead id="lic-title" overline={t.overline} title={t.title} accent={t.titleAccent} lead={t.lead} />
	{:else}
		<ScreenHead id="lic-title" overline={t.overline} title={t.activeTitle} accent={t.activeAccent} lead={t.activeLead} />
	{/if}

	<div class="layout" class:solo={!showForm}>
		<div class="panel panel--heat main">
			{#if shown && (shown.valid || checked)}
				<div class="result" class:ok={shown.valid} role="status">
					<p class="badge {shown.valid ? 'badge--ok' : 'badge--danger'}">{shown.valid ? t.valid : t.invalid}</p>
					{#if shown.valid}
						<dl class="facts">
							{#if shown.plan}<div><dt>{t.plan}</dt><dd>{t.plans[shown.plan] ?? shown.plan}</dd></div>{/if}
							{#if shown.expiresAt}
								<div><dt>{t.expires}</dt><dd>{date(shown.expiresAt, lang)}<span class="sub">{t.daysLeft(daysLeft(shown.expiresAt))}</span></dd></div>
							{/if}
							{#if shown.sub}<div><dt>{t.account}</dt><dd class="num mono">{shown.sub}</dd></div>{/if}
						</dl>
					{:else}
						{#if shown.reason}<p class="reason">{t.reasons[shown.reason] ?? shown.reason}</p>{/if}
						{#if shown.expiresAt}<p class="hint">{t.expires}: {date(shown.expiresAt, lang)}</p>{/if}
					{/if}
				</div>
			{/if}

			{#if showForm}
				<form class="form" onsubmit={submit} novalidate>
					<div class="field">
						<label for="lic-key">{t.label}</label>
						<textarea
							id="lic-key"
							class="textarea input--mono key"
							rows="3"
							spellcheck="false"
							autocomplete="off"
							autocapitalize="off"
							placeholder={t.placeholder}
							bind:value={key}
							bind:this={input}
							aria-invalid={fieldError ? 'true' : undefined}
							aria-describedby={fieldError ? 'lic-hint lic-err' : 'lic-hint'}
						></textarea>
						<p id="lic-hint" class="hint">{t.hint}</p>
						{#if fieldError}<p id="lic-err" class="error-text">{fieldError}</p>{/if}
					</div>
					<div class="actions">
						<button class="go" type="submit" disabled={busy}>
							{#if busy}<span class="ring" aria-hidden="true"></span>{t.checking}{:else}{t.submit} <span class="arrow" aria-hidden="true">→</span>{/if}
						</button>
					</div>
				</form>
			{:else}
				<div class="actions">
					<button class="btn btn--secondary" type="button" onclick={() => ((editing = true), (checked = null))}>{t.change}</button>
				</div>
			{/if}
		</div>

		{#if showForm}
			<aside class="side">
				<div class="panel">
					<p class="panel-title">{t.noKey}</p>
					<a class="btn btn--primary buy" href={t.buyHref} target="_blank" rel="noopener">{t.buy} <span class="arrow" aria-hidden="true">↗</span></a>
				</div>
				<div class="panel">
					<p class="hint-body">{t.scanFirstHint}</p>
					<button class="btn btn--secondary" type="button" onclick={onscanfirst}>{t.scanFirst} <span class="arrow" aria-hidden="true">→</span></button>
				</div>
			</aside>
		{/if}
	</div>
</section>

<style>
	.layout.solo {
		grid-template-columns: minmax(0, 40rem);
	}
	.layout {
		display: grid;
		gap: var(--sp-6);
		grid-template-columns: minmax(0, 1.6fr) minmax(16rem, 1fr);
		align-items: start;
	}
	.main {
		display: grid;
		gap: var(--sp-6);
	}
	.form {
		display: grid;
		gap: var(--sp-5);
	}
	.key {
		resize: vertical;
		min-height: 6rem;
		font-size: var(--fs-sm);
		line-height: 1.5;
		word-break: break-all;
	}
	.result {
		display: grid;
		gap: var(--sp-4);
	}
	.result .badge {
		justify-self: start;
		margin: 0;
	}
	.reason {
		color: var(--danger-ink);
		font-weight: 560;
	}
	.mono {
		font-family: var(--font-mono);
		font-weight: 400;
		font-size: var(--fs-sm);
	}
	.side {
		display: grid;
		gap: var(--sp-4);
	}
	.side .panel {
		display: grid;
		gap: var(--sp-4);
		justify-items: start;
	}
	.hint-body {
		font-size: var(--fs-sm);
		color: var(--text);
	}
	@media (max-width: 860px) {
		.layout {
			grid-template-columns: 1fr;
		}
	}
</style>
