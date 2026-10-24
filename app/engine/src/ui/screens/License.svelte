<script lang="ts">
	/**
	 * Welcome (phase `license`): a hero in the site's voice, the measured speed duel, what happens next,
	 * and the licence key as one compact field that validates on paste. A valid key moves the backend on
	 * to the scan by itself; "Let's go" without a key starts the scan (it needs no subscription).
	 */
	import type { LicenseInfo } from '../../shared/types';
	import SpeedDuel from '../components/SpeedDuel.svelte';
	import { api } from '../lib/api';
	import { date } from '../lib/i18n';
	import { store } from '../lib/store.svelte';

	let { onscanfirst, onnext }: { onscanfirst: () => void; onnext: () => void } = $props();

	const w = $derived(store.t.welcome);
	const t = $derived(store.t.license);
	const lang = $derived(store.lang);
	const current = $derived(store.state?.license ?? null);

	let key = $state('');
	let busy = $state(false);
	let fieldError = $state('');
	let checked = $state<LicenseInfo | null>(null);
	let editing = $state(false);
	let input: HTMLInputElement | undefined = $state();

	const active = $derived(current?.valid === true && !editing);
	const failed = $derived(checked && !checked.valid ? checked : null);

	async function validate(): Promise<boolean> {
		const k = key.trim();
		fieldError = !k ? t.empty : !k.startsWith('ENIGMA-') ? t.badPrefix : '';
		if (fieldError) {
			input?.focus();
			return false;
		}
		busy = true;
		try {
			checked = await api.license(k);
		} catch (err) {
			checked = { valid: false, reason: err instanceof Error ? err.message : String(err) };
		} finally {
			busy = false;
		}
		if (checked.valid) editing = false;
		else input?.focus();
		return checked.valid;
	}

	function onpaste() {
		// The pasted text lands in the field after this event; validate right after.
		setTimeout(() => void validate(), 0);
	}

	async function go() {
		if (active) return onnext();
		if (key.trim() && !(await validate())) return;
		if (!key.trim()) onscanfirst();
	}

	const ICONS = [
		'M7 7h10v10H7zM10 3v4M14 3v4M10 17v4M14 17v4M3 10h4M3 14h4M17 10h4M17 14h4',
		'M12 3 3 8l9 5 9-5-9-5ZM3 13l9 5 9-5M3 17.5l9 5 9-5',
		'M4.5 17a8 8 0 1 1 15 0M12 13l4-4M12 13a1.6 1.6 0 1 0 0 .01',
		'M13 2 4 14h7l-1 8 9-12h-7l1-8Z'
	];
</script>

<section class="screen welcome" aria-labelledby="lic-title">
	<div class="hero">
		<div class="copy">
			<p class="eyebrow">{w.eyebrow}</p>
			<h1 id="lic-title" class="giga" tabindex="-1" data-screen-title>
				<span class="l1">{w.title}</span>
				<span class="l2 hx-accent">{w.accent}</span>
			</h1>
			<p class="lede">{w.lead}</p>

			<div class="start">
				<button class="go go--xl" type="button" onclick={go} disabled={busy}>
					{#if busy}<span class="ring" aria-hidden="true"></span>{t.checking}{:else}{w.go} <span class="arrow" aria-hidden="true">→</span>{/if}
				</button>

				{#if active && current}
					<p class="licensed" role="status">
						<span class="ok-badge">✓ {t.plans[current.plan ?? ''] ?? current.plan ?? t.valid}{#if current.expiresAt}<span class="exp"> · {w.validUntil} {date(current.expiresAt, lang)}</span>{/if}</span>
						<button type="button" class="linkish" onclick={() => ((editing = true), (checked = null))}>{w.changeKey}</button>
					</p>
				{:else}
					<form
						class="key"
						novalidate
						onsubmit={(e) => {
							e.preventDefault();
							void validate();
						}}
					>
						<label for="lic-key" class="key-label">{w.keyLabel}</label>
						<div class="key-row" class:bad={!!fieldError || !!failed}>
							<input
								id="lic-key"
								bind:this={input}
								bind:value={key}
								{onpaste}
								class="key-in num"
								type="text"
								spellcheck="false"
								autocomplete="off"
								autocapitalize="off"
								placeholder={w.keyPlaceholder}
								aria-invalid={fieldError || failed ? 'true' : undefined}
								aria-describedby="lic-hint{fieldError || failed ? ' lic-err' : ''}"
							/>
							<button class="key-btn" type="submit" disabled={busy}>{w.keyCheck}</button>
						</div>
						<p id="lic-hint" class="hint">{w.keyHint}</p>
						{#if fieldError}
							<p id="lic-err" class="error-text" role="alert">{fieldError}</p>
						{:else if failed}
							<p id="lic-err" class="error-text" role="alert">{t.reasons[failed.reason ?? ''] ?? failed.reason ?? t.invalid}</p>
						{/if}
					</form>
				{/if}

				<p class="aside">
					<a href={t.buyHref} target="_blank" rel="noopener">{w.buy} <span aria-hidden="true">↗</span></a>
					<span class="mute">· {w.noKeyNote}</span>
				</p>
			</div>
		</div>

		<SpeedDuel />
	</div>

	<section class="steps4" aria-labelledby="steps4-title">
		<h2 id="steps4-title" class="eyebrow">{w.stepsTitle}</h2>
		<ol>
			{#each w.steps as s, i (i)}
				<li>
					<span class="ic" aria-hidden="true">
						<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d={ICONS[i]} /></svg>
					</span>
					<span class="n num" aria-hidden="true">0{i + 1}</span>
					<span class="st">{s.t}</span>
					<span class="sd">{s.d}</span>
				</li>
			{/each}
		</ol>
	</section>
</section>

<style>
	.welcome {
		gap: var(--sp-12);
	}
	.hero {
		display: grid;
		grid-template-columns: minmax(0, 1.15fr) minmax(0, 1fr);
		gap: clamp(var(--sp-8), 4vw, var(--sp-16));
		align-items: center;
		padding-top: var(--sp-4);
	}
	.copy {
		display: grid;
		gap: var(--sp-5);
	}
	.giga {
		display: grid;
		gap: 0.1em;
		font-size: clamp(2.4rem, 1.2rem + 4.4vw, 4.6rem);
		font-weight: 800;
		font-stretch: 110%;
		line-height: 0.98;
		letter-spacing: -0.035em;
	}
	.giga:focus {
		outline: none;
	}
	.l1 {
		font-size: 0.62em;
		letter-spacing: -0.03em;
		background: linear-gradient(180deg, #ffffff, #b9b5ad);
		-webkit-background-clip: text;
		background-clip: text;
		color: transparent;
		padding-bottom: 0.08em;
	}
	:global(:root[data-theme='light']) .l1 {
		background: none;
		color: var(--text-hi);
	}
	.l2 {
		background: var(--heat-ramp-hot);
		-webkit-background-clip: text;
		background-clip: text;
		filter: drop-shadow(0 6px 30px rgb(255 122 26 / 0.25));
	}
	:global(:root[data-theme='light']) .l2 {
		background: linear-gradient(90deg, #c2330f, #d94a14 85%);
		-webkit-background-clip: text;
		background-clip: text;
		filter: none;
	}
	.lede {
		max-width: 36rem;
	}
	.start {
		display: grid;
		gap: var(--sp-5);
		justify-items: start;
		margin-top: var(--sp-2);
	}
	.go--xl {
		min-height: 3.6rem;
		padding: 0 var(--sp-8);
		font-size: var(--fs-md);
	}
	.key {
		display: grid;
		gap: 0.4rem;
		width: min(100%, 30rem);
	}
	.key-label {
		font-size: var(--fs-sm);
		font-weight: 600;
		color: var(--text-hi);
	}
	.key-row {
		display: flex;
		align-items: center;
		padding: 0.25rem;
		border: 1px solid var(--line-strong);
		border-radius: var(--r-pill);
		background: var(--bg-1);
		transition: border-color var(--dur-1) var(--ease-out);
	}
	.key-row:focus-within {
		border-color: var(--heat-3);
		box-shadow: 0 0 0 3px color-mix(in srgb, var(--heat-3) 22%, transparent);
	}
	.key-row.bad {
		border-color: var(--danger-ink);
	}
	.key-in {
		flex: 1;
		min-width: 0;
		height: 2.4rem;
		padding: 0 0.9rem;
		border: 0;
		background: none;
		color: var(--text-hi);
		font-size: var(--fs-sm);
	}
	.key-in:focus-visible {
		outline: none;
	}
	.key-in::placeholder {
		color: var(--text-mute);
		opacity: 1;
	}
	.key-btn {
		flex: none;
		height: 2.4rem;
		padding: 0 1rem;
		border: 1px solid var(--line-strong);
		border-radius: var(--r-pill);
		background: var(--bg-3);
		color: var(--text-hi);
		font: inherit;
		font-size: var(--fs-xs);
		font-weight: 650;
		cursor: pointer;
	}
	.key-btn:hover {
		border-color: var(--text-hi);
	}
	.licensed {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--sp-3);
		margin: 0;
	}
	.ok-badge {
		display: inline-flex;
		align-items: center;
		min-height: 2.4rem;
		padding: 0 1rem;
		border-radius: var(--r-pill);
		border: 1px solid color-mix(in srgb, var(--ok-ink) 55%, transparent);
		background: var(--ok-soft);
		color: var(--ok-ink);
		font-weight: 650;
		font-size: var(--fs-sm);
	}
	.exp {
		font-weight: 500;
	}
	.linkish {
		border: 0;
		background: none;
		padding: 0.4rem 0.2rem;
		color: var(--text-hi);
		font: inherit;
		font-size: var(--fs-sm);
		text-decoration: underline;
		text-decoration-color: color-mix(in srgb, var(--text-hi) 38%, transparent);
		text-underline-offset: 0.2em;
		cursor: pointer;
	}
	.aside {
		margin: 0;
		font-size: var(--fs-sm);
		display: flex;
		flex-wrap: wrap;
		gap: 0.3rem 0.5rem;
	}
	.mute {
		color: var(--text-mute);
	}
	.steps4 {
		display: grid;
		gap: var(--sp-4);
	}
	.steps4 h2 {
		margin: 0;
	}
	.steps4 ol {
		display: grid;
		grid-template-columns: repeat(4, minmax(0, 1fr));
		gap: var(--sp-4);
		margin: 0;
		padding: 0;
		list-style: none;
	}
	.steps4 li {
		position: relative;
		display: grid;
		gap: 0.4rem;
		align-content: start;
		padding: var(--sp-5);
		border: 1px solid var(--line);
		border-radius: var(--r-xl);
		background:
			linear-gradient(180deg, color-mix(in srgb, var(--text-hi) 3%, transparent), transparent 50%),
			var(--bg-2);
	}
	.ic {
		display: grid;
		place-items: center;
		width: 2.6rem;
		height: 2.6rem;
		border-radius: var(--r-md);
		color: var(--accent-ink);
		background: color-mix(in srgb, var(--heat-3) 10%, transparent);
		border: 1px solid color-mix(in srgb, var(--heat-3) 35%, transparent);
	}
	.n {
		position: absolute;
		top: var(--sp-5);
		right: var(--sp-5);
		font-size: var(--fs-xs);
		color: var(--text-mute);
	}
	.st {
		margin-top: var(--sp-2);
		color: var(--text-hi);
		font-weight: 700;
	}
	.sd {
		font-size: var(--fs-sm);
		color: var(--text-mute);
		line-height: 1.45;
	}
	@media (max-width: 1000px) {
		.hero {
			grid-template-columns: 1fr;
		}
		.steps4 ol {
			grid-template-columns: repeat(2, minmax(0, 1fr));
		}
	}
	@media (max-width: 560px) {
		.steps4 ol {
			grid-template-columns: 1fr;
		}
		.go--xl {
			width: 100%;
		}
		.start {
			justify-items: stretch;
		}
	}
</style>
