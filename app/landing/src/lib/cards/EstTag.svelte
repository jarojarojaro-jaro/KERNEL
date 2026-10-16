<script lang="ts">
	/**
	 * Label for anything that comes from our formula, not a measurement. Deliberately neutral (bone
	 * on a dashed steel outline with a "≈"): heat colours mean measured speed and nothing else.
	 */
	let { text }: { text: string } = $props();
</script>

<span class="est"><span class="ap" aria-hidden="true">≈</span>{text}</span>

<style>
	.est {
		display: inline-flex;
		align-items: center;
		gap: 0.4rem;
		width: fit-content;
		padding: 0.2rem 0.6rem 0.2rem 0.45rem;
		border: 1px dashed var(--line-strong);
		border-radius: var(--r-sm);
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		letter-spacing: 0.06em;
		text-transform: uppercase;
		color: var(--text);
		background: repeating-linear-gradient(135deg, rgb(255 255 255 / 0.03) 0 4px, transparent 4px 8px);
	}
	.ap {
		font-size: 1.25em;
		line-height: 1;
		color: var(--text-hi);
	}
</style>
