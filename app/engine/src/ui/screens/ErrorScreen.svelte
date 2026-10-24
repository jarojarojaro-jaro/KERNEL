<script lang="ts">
	import type { Phase } from '../../shared/types';
	import { api } from '../lib/api';
	import type { Step } from '../lib/i18n';
	import { store } from '../lib/store.svelte';

	let { onview }: { onview: (s: Step) => void } = $props();

	const t = $derived(store.t.err);
	const s = $derived(store.state);
	const err = $derived(s?.error ?? { phase: 'license' as Phase, message: '' });
	const stepName = $derived(err.phase === 'error' ? '' : store.t.steps[err.phase]);
	const recent = $derived(store.logs.filter((l) => l.level === 'error' || l.level === 'warn').slice(-5));
	/** The backend reports a user cancel as an error with this message. */
	const cancelled = $derived(err.message === 'Cancelled.');

	let busy = $state(false);
	let retryError = $state('');

	/** Retry what failed: the pipeline restarts from the chosen option (finished files are reused). */
	async function retry() {
		busy = true;
		retryError = '';
		try {
			if (s?.chosen) await api.start(s.chosen.id);
			else if (err.phase === 'scan') await api.scan();
			else if (err.phase === 'recommend') await api.recommend();
			else onview(err.phase === 'error' ? 'license' : err.phase);
		} catch (e) {
			retryError = e instanceof Error ? e.message : String(e);
		} finally {
			busy = false;
		}
	}
</script>

<section class="screen" aria-labelledby="err-title">
	<header class="screen-head">
		<p class="eyebrow">{t.inPhase}: {stepName}</p>
		<h1 id="err-title" class="title" tabindex="-1" data-screen-title>{cancelled ? t.cancelledTitle : t.title}</h1>
	</header>

	{#if cancelled}
		<p class="lede">{t.cancelledBody}</p>
	{:else}
		<div class="panel errp" role="alert">
			<p class="msg">{err.message}</p>
			{#if recent.length}
				<ul class="recent num">
					{#each recent as l, i (i)}<li>{l.msg}</li>{/each}
				</ul>
			{/if}
		</div>
	{/if}
	{#if retryError}<p class="error-text" role="alert">{retryError}</p>{/if}

	<div class="actions">
		<button class="go" type="button" onclick={retry} disabled={busy}>
			{#if busy}<span class="ring" aria-hidden="true"></span>{t.retrying}{:else}{cancelled ? t.resume : t.retry} <span class="arrow" aria-hidden="true">{cancelled ? '→' : '↻'}</span>{/if}
		</button>
		{#if s?.recommendation}
			<button class="btn btn--secondary" type="button" onclick={() => onview('recommend')}>{t.backToRec}</button>
		{/if}
		<button class="btn btn--ghost" type="button" onclick={() => (store.logOpen = true)}>{t.showLog}</button>
	</div>
</section>

<style>
	h1:focus {
		outline: none;
	}
	.errp {
		display: grid;
		gap: var(--sp-4);
		border-color: color-mix(in srgb, var(--danger-ink) 55%, var(--line));
		background:
			radial-gradient(120% 70% at 0% 0%, var(--danger-soft), transparent 60%),
			var(--bg-2);
	}
	.msg {
		color: var(--text-hi);
		font-size: var(--fs-md);
		font-weight: 560;
		white-space: pre-wrap;
		overflow-wrap: anywhere;
	}
	.recent {
		display: grid;
		gap: 0.3rem;
		margin: 0;
		padding: var(--sp-3) 0 0;
		border-top: 1px solid var(--line);
		list-style: none;
		font-size: var(--fs-xs);
		color: var(--text-mute);
		overflow-wrap: anywhere;
	}
</style>
