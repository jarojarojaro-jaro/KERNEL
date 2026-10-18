<script lang="ts">
	import { onMount } from 'svelte';
	import { tilt } from '$lib/fx/actions';
	import { currentLang, href } from '$lib/i18n';
	import { ob } from '$lib/onboarding/copy';
	import Shell from '$lib/onboarding/Shell.svelte';

	const lang = $derived(currentLang());
	const t = $derived(ob[lang].paths);
	let suggested = $state<string | null>(null);

	onMount(() => {
		// Hint only: a terminal user on Linux, everyone else the app. Never blocks a choice.
		suggested = /Linux/.test(navigator.userAgent) && !/Android/.test(navigator.userAgent) ? 'terminal' : 'download';
	});
</script>

<svelte:head><title>{t.title}</title></svelte:head>

<Shell title={t.title} lead={t.lead} wide back="/start">
	<ul class="paths" role="list">
		{#each t.items as p, i (p.id)}
			<li style="--d:{i * 90}ms">
				<a class="tile" href={href(lang, `/start/${p.id}`)} class:suggested={suggested === p.id} use:tilt={{ max: 4 }}>
					<span class="glow" aria-hidden="true"></span>
					<span class="top">
						<span class="ic" aria-hidden="true">
							{#if p.id === 'hardware'}
								<svg viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="6" y="14" width="36" height="20" rx="3" /><circle cx="17" cy="24" r="5" /><circle cx="31" cy="24" r="5" /><path d="M10 34v5M38 34v5M6 20H3M6 28H3" /></svg>
							{:else if p.id === 'download'}
								<svg viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M24 6v24M14 21l10 10 10-10" /><path d="M8 34v5a3 3 0 0 0 3 3h26a3 3 0 0 0 3-3v-5" /></svg>
							{:else}
								<svg viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="5" y="8" width="38" height="32" rx="4" /><path d="m13 19 6 5-6 5M23 30h11" /></svg>
							{/if}
						</span>
						<span class="k mono">{p.k}</span>
					</span>
					<span class="title">{p.title}</span>
					<span class="body">{p.body}</span>
					{#if suggested === p.id}<span class="rec">{t.recommended}</span>{/if}
					<span class="go">{p.cta} <span class="arrow" aria-hidden="true">→</span></span>
				</a>
			</li>
		{/each}
	</ul>
</Shell>

<style>
	.paths {
		list-style: none;
		padding: 0;
		margin: 0;
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		gap: var(--sp-5);
	}
	@media (prefers-reduced-motion: no-preference) {
		.paths li {
			animation: tile-in 0.8s var(--ease-out) calc(0.2s + var(--d)) both;
		}
	}
	@keyframes tile-in {
		from {
			opacity: 0.01;
			transform: translate3d(0, 1.5rem, 0);
		}
	}
	.tile {
		position: relative;
		display: grid;
		gap: var(--sp-3);
		align-content: start;
		height: 100%;
		min-height: 22rem;
		padding: var(--sp-8) var(--sp-6) var(--sp-6);
		border: 1px solid var(--line);
		border-radius: var(--r-xl);
		background: var(--bg-1);
		color: var(--text);
		text-decoration: none;
		overflow: hidden;
		transition:
			border-color var(--dur-3) var(--ease-out),
			box-shadow var(--dur-3) var(--ease-out);
	}
	/* heat that follows the cursor (tilt sets --gx/--gy); centred at rest */
	.glow {
		position: absolute;
		inset: 0;
		pointer-events: none;
		opacity: 0;
		background:
			radial-gradient(60% 45% at var(--gx, 50%) var(--gy, 0%), color-mix(in srgb, var(--heat-3) 26%, transparent), transparent 70%),
			linear-gradient(180deg, transparent 55%, color-mix(in srgb, var(--heat-2) 10%, transparent));
		transition: opacity var(--dur-3) var(--ease-out);
	}
	.tile:hover,
	.tile:focus-visible {
		border-color: var(--heat-3);
		box-shadow:
			0 0 0 1px color-mix(in srgb, var(--heat-3) 40%, transparent),
			0 30px 80px -36px color-mix(in srgb, var(--heat-3) 90%, transparent);
	}
	.tile:hover .glow,
	.tile:focus-visible .glow,
	.suggested .glow {
		opacity: 1;
	}
	.suggested {
		border-color: color-mix(in srgb, var(--heat-3) 55%, var(--line));
	}
	.top {
		position: relative;
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		margin-bottom: var(--sp-4);
	}
	.ic {
		display: grid;
		place-items: center;
		width: 4.25rem;
		height: 4.25rem;
		border-radius: var(--r-lg);
		border: 1px solid var(--line-strong);
		background: var(--bg-2);
		color: var(--text-hi);
		transition:
			color var(--dur-3),
			border-color var(--dur-3),
			box-shadow var(--dur-3);
	}
	.ic svg {
		width: 2.25rem;
		height: 2.25rem;
	}
	.tile:hover .ic,
	.tile:focus-visible .ic,
	.suggested .ic {
		color: var(--accent-ink);
		border-color: color-mix(in srgb, var(--heat-3) 60%, transparent);
		box-shadow: 0 0 30px -6px color-mix(in srgb, var(--heat-3) 70%, transparent);
	}
	.k {
		font-size: clamp(2.5rem, 1.6rem + 2vw, 3.5rem);
		font-weight: 200;
		font-stretch: 87.5%;
		letter-spacing: -0.05em;
		line-height: 0.8;
		color: var(--line-strong);
		transition: color var(--dur-3);
	}
	.tile:hover .k,
	.suggested .k {
		color: var(--accent-ink);
	}
	:global(:root[data-theme='light']) .tile:hover .k,
	:global(:root[data-theme='light']) .suggested .k {
		background: var(--heat-large);
		-webkit-background-clip: text;
		background-clip: text;
		color: transparent;
	}
	.title {
		position: relative;
		font-size: var(--fs-xl);
		font-weight: 720;
		font-stretch: 108%;
		letter-spacing: -0.03em;
		line-height: 1.05;
		color: var(--text-hi);
	}
	.body {
		position: relative;
		font-size: var(--fs-sm);
		line-height: 1.55;
	}
	.rec {
		position: relative;
		justify-self: start;
		display: inline-flex;
		align-items: center;
		gap: 0.45em;
		padding: 0.2rem 0.7rem;
		border-radius: var(--r-pill);
		background: color-mix(in srgb, var(--heat-3) 14%, transparent);
		border: 1px solid color-mix(in srgb, var(--heat-3) 50%, transparent);
		color: var(--text-hi);
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		font-stretch: 87.5%;
		letter-spacing: 0.08em;
		text-transform: uppercase;
	}
	.rec::before {
		content: '';
		width: 0.45em;
		height: 0.45em;
		border-radius: 50%;
		background: var(--heat-3);
		box-shadow: 0 0 6px var(--heat-3);
	}
	.go {
		position: relative;
		margin-top: auto;
		padding-top: var(--sp-4);
		color: var(--text-hi);
		font-weight: 650;
		font-size: var(--fs-sm);
	}
	.go .arrow {
		display: inline-block;
		transition: transform var(--dur-3) var(--ease-out);
	}
	.tile:hover .go .arrow {
		transform: translateX(5px);
		color: var(--accent-ink);
	}
	@media (max-width: 860px) {
		.paths {
			grid-template-columns: 1fr;
		}
		.tile {
			min-height: 0;
			padding: var(--sp-6) var(--sp-5);
		}
	}
</style>
