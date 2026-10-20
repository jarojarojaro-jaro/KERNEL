<script lang="ts">
	import { onMount } from 'svelte';

	let { items, label }: { items: { id: string; nav: string }[]; label: string } = $props();
	let active = $state(0);
	let bar: HTMLElement | undefined = $state();

	onMount(() => {
		const els = items.map((it) => document.getElementById(it.id)).filter((e): e is HTMLElement => !!e);
		const io = new IntersectionObserver(
			(entries) => {
				for (const e of entries) if (e.isIntersecting) active = els.indexOf(e.target as HTMLElement);
			},
			{ rootMargin: '-45% 0px -50% 0px' }
		);
		els.forEach((e) => io.observe(e));
		/* scroll progress through the journey (first chapter top → last chapter bottom), transform only */
		let raf = 0;
		const measure = () => {
			raf = 0;
			const first = els[0];
			const last = els[els.length - 1];
			if (!first || !last || !bar) return;
			const top = first.getBoundingClientRect().top + scrollY;
			const end = last.getBoundingClientRect().bottom + scrollY - innerHeight;
			const p = Math.min(1, Math.max(0, (scrollY - top) / Math.max(1, end - top)));
			bar.style.transform = `scaleY(${p})`;
		};
		const onScroll = () => {
			if (!raf) raf = requestAnimationFrame(measure);
		};
		addEventListener('scroll', onScroll, { passive: true });
		addEventListener('resize', onScroll, { passive: true });
		measure();
		return () => {
			io.disconnect();
			removeEventListener('scroll', onScroll);
			removeEventListener('resize', onScroll);
			cancelAnimationFrame(raf);
		};
	});
</script>

<nav class="rail" aria-label={label}>
	<span class="line" aria-hidden="true"><i bind:this={bar}></i></span>
	<ol>
		{#each items as it, i (it.id)}
			<li>
				<a href="#{it.id}" class:on={active === i} class:past={i < active} aria-current={active === i ? 'location' : undefined}>
					<span class="dot" aria-hidden="true"></span>
					<span class="no mono">{String(i + 1).padStart(2, '0')}</span>
					<span class="nm">{it.nav}</span>
				</a>
			</li>
		{/each}
	</ol>
</nav>

<style>
	.rail {
		position: fixed;
		left: clamp(0.75rem, 1.5vw, 1.75rem);
		top: 50%;
		transform: translateY(-50%);
		z-index: 5;
		display: none;
	}
	@media (min-width: 1360px) {
		.rail {
			display: block;
		}
	}
	.line {
		position: absolute;
		left: 0.4rem;
		top: 0.9rem;
		bottom: 0.9rem;
		width: 1px;
		background: var(--line);
	}
	.line i {
		position: absolute;
		inset: 0;
		background: linear-gradient(180deg, var(--heat-2), var(--heat-3), var(--heat-4));
		transform-origin: top;
		transform: scaleY(0);
		box-shadow: 0 0 8px var(--heat-3);
	}
	ol {
		position: relative;
		margin: 0;
		padding: 0;
		list-style: none;
		display: grid;
		gap: 0.15rem;
	}
	a {
		display: flex;
		align-items: center;
		gap: 0.6rem;
		min-height: 2rem;
		color: var(--text-mute);
		text-decoration: none;
		font-size: var(--fs-2xs);
	}
	.dot {
		width: 0.8rem;
		height: 0.8rem;
		flex: none;
		border-radius: 50%;
		border: 1px solid var(--line-strong);
		background: var(--bg-0);
		transition:
			transform var(--dur-3) var(--ease-spring),
			background-color var(--dur-3),
			border-color var(--dur-3);
	}
	a.past .dot {
		background: var(--heat-2);
		border-color: var(--heat-2);
	}
	a.on .dot {
		background: var(--heat-4);
		border-color: var(--heat-4);
		transform: scale(1.3);
		box-shadow: 0 0 12px var(--heat-3);
	}
	.no {
		color: inherit;
	}
	.nm {
		opacity: 0;
		transform: translateX(-4px);
		transition:
			opacity var(--dur-2),
			transform var(--dur-3) var(--ease-out);
		white-space: nowrap;
	}
	.rail:hover .nm,
	.rail:focus-within .nm {
		opacity: 1;
		transform: none;
	}
	a.on {
		color: var(--text-hi);
	}
	a:hover {
		color: var(--text-hi);
	}
	a:focus-visible {
		outline: 2px solid var(--focus);
		outline-offset: 2px;
		border-radius: var(--r-xs);
	}
</style>
