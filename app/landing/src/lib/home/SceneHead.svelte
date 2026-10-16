<script lang="ts">
	/** Heading block of a scroll scene: index + step name, two-width statement, one line of body. */
	import Duo from './Duo.svelte';

	let { k, step, head, body, id, mode = 'plain' }: { k: string; step: string; head: string; body: string; id: string; mode?: 'duo' | 'plain' } = $props();
</script>

<header class="sh">
	<p class="idx"><span class="k">{k}</span><span class="rule" aria-hidden="true"></span><span>{step}</span></p>
	<Duo text={head} tag="h3" {id} size="scene" {mode} />
	<p class="body">{body}</p>
</header>

<style>
	.sh {
		display: grid;
		gap: clamp(0.9rem, 2.2vh, 1.5rem);
		align-content: start;
	}
	.idx {
		display: flex;
		align-items: center;
		gap: 0.8rem;
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		letter-spacing: 0.14em;
		text-transform: uppercase;
		color: var(--text);
	}
	.k {
		color: var(--text-hi);
	}
	.rule {
		width: 2.5rem;
		height: 1px;
		background: var(--line-strong);
	}
	.body {
		font-size: clamp(1rem, 0.9rem + 0.35vw, 1.2rem);
		line-height: 1.5;
		color: var(--text);
		max-width: 34ch;
		text-wrap: pretty;
	}
</style>
