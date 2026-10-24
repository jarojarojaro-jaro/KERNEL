<script lang="ts">
	/** One transfer/check line: name, state, bar, GB done of total, speed and time left. */
	import type { Progress } from '../../shared/types';
	import { duration, num } from '../lib/i18n';
	import { store } from '../lib/store.svelte';

	interface Props {
		title: string;
		detail?: string;
		p: Progress | null;
		/** Found on disk: the step is skipped. */
		reused?: boolean;
		/** Total to show before the first progress event (bytes). */
		totalHint?: number;
		/** Units of done/total: bytes (shown as GB) or plain steps. */
		unit?: 'bytes' | 'steps';
		/** The phase is over (shown from the stepper later): finished whatever events this page saw. */
		done?: boolean;
	}
	let { title, detail, p, reused = false, totalHint, unit = 'bytes', done: over = false }: Props = $props();

	const t = $derived(store.t.dl);
	const lang = $derived(store.lang);
	const total = $derived(p?.total || totalHint || 0);
	const finished = $derived(over || reused || (p !== null && p.total > 0 && p.done >= p.total));
	const done = $derived(reused || (over && !p) ? total : (p?.done ?? 0));
	const frac = $derived(finished ? 1 : total > 0 ? Math.min(1, done / total) : 0);
	const status = $derived(reused ? t.reused : finished ? t.done : p ? `${num(frac * 100, lang, frac < 0.1 ? 1 : 0)}%` : t.waiting);
	const GiB = 1024 ** 3;
</script>

<div class="row" class:active={p && !finished} class:finished class:waiting={!p && !finished}>
	<div class="top">
		<span class="mark" aria-hidden="true">
			{#if finished}✓{:else if p}<span class="ring"></span>{:else}·{/if}
		</span>
		<span class="name">
			<span class="ttl">{title}</span>
			{#if detail}<span class="detail num">{detail}</span>{/if}
		</span>
		<span class="state" class:ok={finished}>{status}</span>
	</div>
	<div
		class="track"
		role="progressbar"
		aria-label={title}
		aria-valuemin="0"
		aria-valuemax="100"
		aria-valuenow={Math.round(frac * 100)}
		aria-valuetext={status}
	>
		<i style="width:{frac * 100}%"></i>
	</div>
	{#if !reused && (p || (total && !finished))}
		<p class="nums num">
			{#if unit === 'bytes'}
				<span>{num(done / GiB, lang, 2)} / {num(total / GiB, lang, 2)} GB</span>
			{:else}
				<span>{done} / {total}</span>
			{/if}
			{#if p?.rate && !finished}<span>{t.speed} {num(p.rate / 1e6, lang, 1)} MB/s</span>{/if}
			{#if p?.etaS !== undefined && !finished && p.etaS > 0}<span>{t.eta} {duration(p.etaS)}</span>{/if}
		</p>
	{/if}
</div>

<style>
	.row {
		display: grid;
		gap: var(--sp-3);
		padding: var(--sp-5) 0;
		border-top: 1px solid var(--line);
	}
	.row:first-child {
		border-top: 0;
		padding-top: 0;
	}
	.top {
		display: flex;
		align-items: center;
		gap: var(--sp-3);
	}
	.mark {
		display: grid;
		place-items: center;
		flex: none;
		width: 1.9rem;
		height: 1.9rem;
		border-radius: 50%;
		border: 1px solid var(--line-strong);
		color: var(--text-mute);
		font-family: var(--font-mono);
		font-size: var(--fs-xs);
	}
	.finished .mark {
		background: var(--text-hi);
		border-color: var(--text-hi);
		color: var(--text-inv);
		font-weight: 700;
	}
	.active .mark {
		color: var(--text-hi);
		border-color: var(--text-hi);
	}
	.mark .ring {
		width: 0.85rem;
		height: 0.85rem;
	}
	.name {
		display: grid;
		min-width: 0;
		flex: 1;
	}
	.ttl {
		color: var(--text-hi);
		font-weight: 650;
	}
	.detail {
		font-size: var(--fs-xs);
		color: var(--text-mute);
		overflow-wrap: anywhere;
	}
	.state {
		font-family: var(--font-mono);
		font-size: var(--fs-xs);
		color: var(--text);
		text-align: right;
	}
	.state.ok {
		color: var(--ok-ink);
	}
	.track {
		height: 0.5rem;
		border-radius: var(--r-pill);
		background: var(--bg-3);
		overflow: hidden;
	}
	.track i {
		display: block;
		height: 100%;
		border-radius: inherit;
		background: var(--text-hi);
		transition: width var(--dur-3) var(--ease-out);
	}
	.finished .track i {
		background: color-mix(in srgb, var(--text-hi) 70%, transparent);
	}
	.waiting {
		opacity: 0.8;
	}
	.nums {
		display: flex;
		flex-wrap: wrap;
		gap: var(--sp-2) var(--sp-6);
		margin: 0;
		font-size: var(--fs-xs);
		color: var(--text-mute);
	}
	.nums span:first-child {
		color: var(--text-hi);
	}
</style>
