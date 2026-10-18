<script lang="ts">
	/**
	 * "źródło" / "source" chip: a button that opens a small popover with file:line references and
	 * measurement conditions. Native Popover API (light dismiss, Esc, focus return); positioned
	 * next to the button on open. Every number on the showcase pages has one nearby.
	 */
	let {
		lang,
		src,
		note = '',
		label
	}: { lang: 'pl' | 'en'; src: string | string[]; note?: string; label?: string } = $props();

	const uid = $props.id();
	const id = `src-${uid}`;
	const lines = $derived([...new Set(Array.isArray(src) ? src : [src])]);
	let btn: HTMLButtonElement | undefined = $state();
	let pop: HTMLSpanElement | undefined = $state();

	function place(e: Event) {
		if ((e as ToggleEvent).newState !== 'open' || !btn || !pop) return;
		const r = btn.getBoundingClientRect();
		const w = Math.min(360, innerWidth - 24);
		const left = Math.max(12, Math.min(innerWidth - w - 12, r.left + r.width / 2 - w / 2));
		const below = r.bottom + 8;
		pop.style.width = `${w}px`;
		pop.style.left = `${left}px`;
		const h = pop.offsetHeight;
		pop.style.top = `${below + h > innerHeight - 12 ? Math.max(12, r.top - h - 8) : below}px`;
	}
</script>

<button bind:this={btn} type="button" class="src-btn" popovertarget={id} aria-label={label ?? (lang === 'pl' ? 'Źródło i warunki pomiaru' : 'Source and measurement conditions')}>
	<svg viewBox="0 0 12 12" width="10" height="10" aria-hidden="true"><circle cx="6" cy="6" r="5" fill="none" stroke="currentColor" stroke-width="1.2" /><path d="M6 5.2v3.3M6 3.4v.1" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" /></svg>
	<span>{lang === 'pl' ? 'źródło' : 'source'}</span>
</button>
<!-- Phrasing content only (span), so the tip is valid inside a <p>: block elements there make the
     browser repair the HTML, which breaks hydration (hydration_mismatch → remount). -->
<span bind:this={pop} {id} popover="auto" class="src-pop" ontoggle={place}>
	{#if note}<span class="note">{note}</span>{/if}
	<span class="list" role="list">
		{#each lines as l (l)}<span class="item" role="listitem"><code>{l}</code></span>{/each}
	</span>
</span>

<style>
	.src-btn {
		display: inline-flex;
		align-items: center;
		gap: 0.3rem;
		min-height: 1.75rem;
		padding: 0.1rem 0.55rem;
		border: 1px solid var(--line);
		border-radius: var(--r-pill);
		background: transparent;
		color: var(--text-mute);
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		letter-spacing: 0.05em;
		cursor: pointer;
		transition:
			color var(--dur-2),
			border-color var(--dur-2);
	}
	.src-btn:hover {
		color: var(--text-hi);
		border-color: var(--line-strong);
	}
	.src-pop {
		position: fixed;
		inset: auto;
		margin: 0;
		padding: var(--sp-3) var(--sp-4);
		border: 1px solid var(--line-strong);
		border-radius: var(--r-md);
		background: var(--bg-2);
		color: var(--text);
		box-shadow: var(--shadow-2);
		font-size: var(--fs-xs);
		line-height: 1.5;
	}
	.src-pop:popover-open {
		display: block;
	}
	.note {
		display: block;
		margin-bottom: var(--sp-2);
	}
	.list {
		display: grid;
		gap: 0.2rem;
	}
	.item {
		display: block;
	}
	code {
		font-size: var(--fs-2xs);
		color: var(--text-mute);
		overflow-wrap: anywhere;
	}
</style>
