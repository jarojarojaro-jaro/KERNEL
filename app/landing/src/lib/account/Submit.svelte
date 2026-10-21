<script lang="ts">
	/** Primary submit: ember gradient, dark ink (≥ 4.5:1 on the whole ramp), a shine crosses on hover. */
	interface Props {
		label: string;
		disabled?: boolean;
	}
	let { label, disabled = false }: Props = $props();
</script>

<button class="go" type="submit" {disabled}>
	<span>{label}</span>
	<span class="arrow" aria-hidden="true">→</span>
</button>

<style>
	.go {
		position: relative;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: var(--sp-2);
		width: 100%;
		min-height: 3rem;
		border: 0;
		border-radius: var(--r-pill);
		background: linear-gradient(90deg, var(--heat-2), var(--heat-3) 70%, var(--heat-4));
		color: #1a0a03;
		font: inherit;
		font-weight: 700;
		font-size: var(--fs-base);
		cursor: pointer;
		overflow: hidden;
		box-shadow: 0 14px 40px -18px color-mix(in srgb, var(--heat-3) 95%, transparent);
		transition:
			transform 0.4s var(--ease-spring),
			box-shadow var(--dur-3) var(--ease-out);
	}
	.go::after {
		content: '';
		position: absolute;
		inset: 0 -40%;
		background: linear-gradient(105deg, transparent 40%, rgb(255 255 255 / 0.45) 50%, transparent 60%);
		transform: translate3d(-70%, 0, 0);
		pointer-events: none;
	}
	.go:not(:disabled):hover {
		box-shadow: 0 18px 50px -16px var(--heat-3);
	}
	.go:not(:disabled):hover::after {
		transform: translate3d(70%, 0, 0);
		transition: transform 0.8s var(--ease-out);
	}
	.go:not(:disabled):hover .arrow {
		transform: translateX(3px);
	}
	.go:active:not(:disabled) {
		transform: scale(0.98);
		transition-duration: 0.12s;
	}
	.go:focus-visible {
		outline: 2px solid var(--heat-3);
		outline-offset: 3px;
	}
	.go:disabled {
		cursor: progress;
	}
	.arrow {
		display: inline-block;
		transition: transform var(--dur-3) var(--ease-out);
	}
	@media (prefers-reduced-motion: reduce) {
		.go,
		.go::after,
		.arrow {
			transition: none;
		}
	}
</style>
