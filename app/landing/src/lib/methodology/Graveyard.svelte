<script lang="ts">
	import { reveal } from '$lib/fx/actions';
	import type { Lang } from '$lib/i18n';
	import { COPY } from './copy';

	let { lang }: { lang: Lang } = $props();
	const c = $derived(COPY[lang]);
</script>

<ul class="yard">
	{#each c.n.items as it, i (it.id)}
		<li class="stone {it.tag}" style="--i:{i}" use:reveal>
			<details>
				<summary>
					<span class="tag mono">{it.tag === 'killed' ? c.n.killed : c.n.stopped}</span>
					<span class="fig mono">{it.fig}</span>
					<span class="nm">{it.name}</span>
					<span class="more mono" aria-hidden="true">+</span>
					<span class="sr-only">{c.n.open}</span>
				</summary>
				<dl>
					<div><dt>{c.n.promise}</dt><dd>{it.promise}</dd></div>
					<div><dt>{c.n.result}</dt><dd>{it.result}</dd></div>
					<div class="why"><dt>{c.n.why}</dt><dd>{it.why}</dd></div>
				</dl>
			</details>
		</li>
	{/each}
</ul>

<style>
	.yard {
		margin: 0;
		padding: 0;
		list-style: none;
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(min(100%, 19rem), 1fr));
		gap: var(--sp-4);
		align-items: start;
	}
	.stone {
		border: 1px solid var(--line);
		border-radius: var(--r-xl) var(--r-xl) var(--r-md) var(--r-md);
		background: linear-gradient(180deg, var(--bg-2), var(--bg-1));
		transition:
			border-color var(--dur-3),
			transform var(--dur-3) var(--ease-out);
	}
	.stone:hover {
		border-color: var(--line-strong);
		transform: translateY(-3px);
	}
	.stone.stopped {
		border-color: color-mix(in srgb, var(--danger) 35%, var(--line));
	}
	summary {
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto;
		gap: var(--sp-2) var(--sp-3);
		padding: var(--sp-5);
		cursor: pointer;
		list-style: none;
		border-radius: inherit;
	}
	summary::-webkit-details-marker {
		display: none;
	}
	summary:focus-visible {
		outline: 2px solid var(--focus);
		outline-offset: 2px;
	}
	.tag {
		font-size: var(--fs-2xs);
		letter-spacing: 0.14em;
		text-transform: uppercase;
		color: var(--text-mute);
	}
	.stopped .tag {
		color: var(--danger-ink);
	}
	.fig {
		grid-column: 1;
		font-size: clamp(2rem, 1.5rem + 1.6vw, 2.8rem);
		font-weight: 600;
		letter-spacing: -0.04em;
		line-height: 1;
		color: var(--text-hi);
	}
	.stopped .fig {
		color: var(--danger-ink);
		font-size: clamp(1.6rem, 1.3rem + 1.2vw, 2.2rem);
	}
	.nm {
		grid-column: 1;
		font-weight: 560;
		color: var(--text);
	}
	.more {
		grid-column: 2;
		grid-row: 1 / span 3;
		align-self: end;
		display: grid;
		place-items: center;
		width: 1.75rem;
		height: 1.75rem;
		border: 1px solid var(--line-strong);
		border-radius: var(--r-sm);
		color: var(--text-mute);
		transition: transform var(--dur-3) var(--ease-spring);
	}
	details[open] .more {
		transform: rotate(45deg);
	}
	dl {
		margin: 0;
		padding: 0 var(--sp-5) var(--sp-5);
		display: grid;
		gap: var(--sp-3);
		animation: open 0.35s var(--ease-out);
	}
	@keyframes open {
		from {
			opacity: 0;
			transform: translateY(-6px);
		}
	}
	dl div {
		display: grid;
		gap: 0.15rem;
	}
	dt {
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		letter-spacing: 0.1em;
		text-transform: uppercase;
		color: var(--text-mute);
	}
	dd {
		margin: 0;
		font-size: var(--fs-sm);
		line-height: 1.55;
		color: var(--text);
	}
	.why dd {
		color: var(--text-hi);
	}
	@media (prefers-reduced-motion: reduce) {
		dl {
			animation: none;
		}
		.stone:hover {
			transform: none;
		}
	}
</style>
