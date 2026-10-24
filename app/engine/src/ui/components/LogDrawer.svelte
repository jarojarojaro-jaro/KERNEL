<script lang="ts">
	/** Live SSE log, collapsed to one bar by default; follows the tail unless the user scrolled up. */
	import { tick } from 'svelte';
	import { time } from '../lib/i18n';
	import { store } from '../lib/store.svelte';

	const t = $derived(store.t);
	const last = $derived(store.logs.at(-1));
	let box: HTMLDivElement | undefined = $state();
	let follow = true;

	$effect(() => {
		void store.logs.length;
		if (!store.logOpen || !box || !follow) return;
		const el = box;
		void tick().then(() => (el.scrollTop = el.scrollHeight));
	});

	function onscroll() {
		if (box) follow = box.scrollHeight - box.scrollTop - box.clientHeight < 24;
	}
</script>

<section class="drawer" class:open={store.logOpen} aria-label={t.log.title}>
	<div class="wrap dbar">
		<button type="button" class="toggle" aria-expanded={store.logOpen} aria-controls="log-body" onclick={() => (store.logOpen = !store.logOpen)}>
			<svg width="14" height="14" viewBox="0 0 16 16" aria-hidden="true" class="chev"><path d="M4 10l4-4 4 4" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" /></svg>
			<span>{store.logOpen ? t.log.close : t.log.open}</span>
			<span class="count num">{store.logs.length}</span>
		</button>
		{#if last && !store.logOpen}
			<span class="peek num" aria-hidden="true"><span class="lv {last.level}">{t.log.levels[last.level] ?? last.level}</span> {last.msg}</span>
		{/if}
	</div>
	<div id="log-body" class="body" hidden={!store.logOpen}>
		<!-- Focusable so keyboard users can scroll the log (WCAG 2.1.1). -->
		<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
		<div class="wrap scroller" bind:this={box} {onscroll} tabindex="0" role="log" aria-live="off" aria-label={t.log.title}>
			{#if store.logs.length === 0}
				<p class="empty">{t.log.empty}</p>
			{:else}
				<ol>
					{#each store.logs as l, i (i)}
						<li><span class="ts">{time(l.t, store.lang)}</span> <span class="lv {l.level}">{t.log.levels[l.level] ?? l.level}</span> <span class="msg">{l.msg}</span></li>
					{/each}
				</ol>
			{/if}
		</div>
	</div>
</section>

<style>
	.drawer {
		position: fixed;
		inset: auto 0 0;
		z-index: 40;
		border-top: 1px solid var(--line);
		background: color-mix(in srgb, var(--bg-1) 92%, transparent);
		backdrop-filter: blur(14px);
		-webkit-backdrop-filter: blur(14px);
	}
	.dbar {
		display: flex;
		align-items: center;
		gap: var(--sp-4);
		height: 2.75rem;
	}
	.toggle {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		flex: none;
		height: 2.25rem;
		padding: 0 0.8rem 0 0.6rem;
		border: 1px solid var(--line);
		border-radius: var(--r-pill);
		background: var(--bg-2);
		color: var(--text-hi);
		font: inherit;
		font-size: var(--fs-xs);
		font-weight: 600;
		cursor: pointer;
	}
	.toggle:hover {
		border-color: var(--line-strong);
	}
	.chev {
		transition: transform var(--dur-2) var(--ease-out);
	}
	.open .chev {
		transform: rotate(180deg);
	}
	.count {
		font-size: var(--fs-2xs);
		color: var(--text-mute);
	}
	.peek {
		flex: 1;
		min-width: 0;
		overflow: hidden;
		white-space: nowrap;
		text-overflow: ellipsis;
		font-size: var(--fs-2xs);
		color: var(--text-mute);
	}
	.body {
		border-top: 1px solid var(--line);
	}
	.scroller {
		height: min(42vh, 22rem);
		overflow: auto;
		padding-block: var(--sp-3);
		font-family: var(--font-mono);
		font-size: 0.72rem;
		line-height: 1.6;
	}
	ol {
		margin: 0;
		padding: 0;
		list-style: none;
	}
	li {
		white-space: pre-wrap;
		overflow-wrap: anywhere;
		color: var(--text);
	}
	.ts {
		color: var(--text-mute);
	}
	.lv {
		font-weight: 600;
		color: var(--text-mute);
	}
	.lv.warn {
		color: var(--warn-ink);
	}
	.lv.error {
		color: var(--danger-ink);
	}
	.lv.info {
		color: var(--info-ink);
	}
	.empty {
		color: var(--text-mute);
	}
</style>
