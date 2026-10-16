<script lang="ts">
	/**
	 * Stylised, dark-on-dark product render of a graphics card (or an Apple SoC package): bracket,
	 * shroud with fans, PCB edge with one memory package per 2 GB, PCIe fingers. `heat` (0..1) is the
	 * measured speed-up mapped to the heat ramp: the light strip and the glow behind the card show how
	 * much faster it writes with our engine (0 = not measured, stays cold). Fans spin and a light sweep
	 * passes only while `live` is true and motion is allowed. A specular sheen follows the tilt
	 * action's --gx/--gy (inherited from the tile). `ignite` plays a one-off power-on: the strip and
	 * the underglow heat up from cold (CSS only; reduced motion shows the end state).
	 *
	 * Driven mode (card page): `charge` (0..1) scales all the heat (strip length, underglow, the glow
	 * behind the card) and `rpm` (0..1) spins the fans from JS, with a motion-blur disc that thickens
	 * as they speed up. The parent drives both from the same timeline as its speed counter.
	 */
	import { onFrame } from '$lib/fx/motion';
	let {
		label,
		vendor,
		vram = null,
		heat = 0,
		live = false,
		flat = false,
		ignite = false,
		charge = null,
		rpm = 0
	}: {
		label: string;
		vendor: string;
		vram?: number | null;
		heat?: number;
		live?: boolean;
		flat?: boolean;
		ignite?: boolean;
		/** 0..1, fraction of the measured heat shown; null = not driven (full heat, CSS transitions). */
		charge?: number | null;
		/** 0..1, fan speed (driven mode only). */
		rpm?: number;
	} = $props();

	const uid = $props.id();
	const apple = $derived(vendor === 'apple');
	const nFans = $derived((vram ?? 0) >= 20 ? 3 : 2);
	const fans = $derived(Array.from({ length: nFans }, (_, i) => ({ cx: 24 + (588 * (i + 0.5)) / nFans, r: nFans === 3 ? 74 : 84 })));
	const chips = $derived(Math.max(4, Math.min(16, Math.round((vram ?? 8) / 2))));
	const blades = Array.from({ length: 11 }, (_, i) => (i * 360) / 11);
	const h = $derived(Math.max(0, Math.min(1, heat)));
	const c = $derived(charge == null ? 1 : Math.max(0, Math.min(1, charge)));

	/** Fan angle, integrated from rpm on the shared frame loop (up to ~7 turns/s, read as a blur). */
	let angle = $state(0);
	$effect(() => {
		if (rpm <= 0) return;
		return onFrame((dt) => {
			angle = (angle + rpm * 2500 * dt) % 360;
		});
	});
</script>

<div class="art" class:live class:flat class:ignite={ignite && charge == null} class:driven={charge != null} class:cold={h === 0} style="--h:{h}; --c:{c}; --rpm:{rpm}" aria-hidden="true">
	<div class="glow"></div>
	<div class="floor"></div>
	<div class="body">
		{#if apple}
			<svg viewBox="0 0 640 300">
				<defs>
					<linearGradient id="pk-{uid}" x1="0" y1="0" x2="1" y2="1">
						<stop offset="0" stop-color="#26262c" />
						<stop offset="1" stop-color="#0d0d10" />
					</linearGradient>
					<linearGradient id="die-{uid}" x1="0" y1="0" x2="0" y2="1">
						<stop offset="0" stop-color="#1b1b20" />
						<stop offset="1" stop-color="#09090b" />
					</linearGradient>
				</defs>
				<rect x="190" y="20" width="260" height="260" rx="26" fill="url(#pk-{uid})" stroke="#34343c" />
				{#each Array.from({ length: 12 }, (_, i) => i) as i (i)}
					<rect x={212 + i * 18.5} y="34" width="7" height="7" rx="1.5" fill="#3a3a42" />
					<rect x={212 + i * 18.5} y="259" width="7" height="7" rx="1.5" fill="#3a3a42" />
				{/each}
				<rect x="236" y="66" width="168" height="168" rx="14" fill="url(#die-{uid})" stroke="#2c2c33" />
				<text x="320" y="164" text-anchor="middle" class="engrave apple">{label}</text>
				<rect class="strip" x="236" y="242" width="168" height="3" rx="1.5" />
			</svg>
		{:else}
			<svg viewBox="0 0 640 300">
				<defs>
					<linearGradient id="sh-{uid}" x1="0" y1="0" x2="0" y2="1">
						<stop offset="0" stop-color="#202026" />
						<stop offset="0.55" stop-color="#121215" />
						<stop offset="1" stop-color="#0a0a0c" />
					</linearGradient>
					<radialGradient id="fan-{uid}" cx="0.5" cy="0.4" r="0.6">
						<stop offset="0" stop-color="#18181c" />
						<stop offset="1" stop-color="#060607" />
					</radialGradient>
					<linearGradient id="bl-{uid}" x1="0" y1="0" x2="1" y2="1">
						<stop offset="0" stop-color="#34343b" />
						<stop offset="0.6" stop-color="#18181c" />
						<stop offset="1" stop-color="#0e0e10" />
					</linearGradient>
					<linearGradient id="rim-{uid}" x1="0" y1="0" x2="0" y2="1">
						<stop offset="0" stop-color="#3c3c44" />
						<stop offset="0.5" stop-color="#17171b" />
						<stop offset="1" stop-color="#2a2a31" />
					</linearGradient>
					<linearGradient id="br-{uid}" x1="0" y1="0" x2="1" y2="0">
						<stop offset="0" stop-color="#4a4a52" />
						<stop offset="1" stop-color="#1e1e23" />
					</linearGradient>
					<linearGradient id="ramp-{uid}" x1="0" y1="0" x2="1" y2="0">
						<stop offset="0" stop-color="#7a2e1f" />
						<stop offset="0.35" stop-color="#e2401c" />
						<stop offset="0.6" stop-color="#ff7a1a" />
						<stop offset="0.85" stop-color="#ffc15a" />
						<stop offset="1" stop-color="#fff3d6" />
					</linearGradient>
					<linearGradient id="sw-{uid}" x1="0" y1="0" x2="1" y2="0">
						<stop offset="0" stop-color="#fff" stop-opacity="0" />
						<stop offset="0.5" stop-color="#fff3d6" stop-opacity="0.16" />
						<stop offset="1" stop-color="#fff" stop-opacity="0" />
					</linearGradient>
					<radialGradient id="smear-{uid}" cx="0.5" cy="0.5" r="0.5">
						<stop offset="0.25" stop-color="#1b1b20" stop-opacity="0" />
						<stop offset="0.45" stop-color="#2e2e35" stop-opacity="0.9" />
						<stop offset="0.8" stop-color="#26262c" stop-opacity="0.95" />
						<stop offset="0.97" stop-color="#3a3a42" stop-opacity="0.7" />
						<stop offset="1" stop-color="#0a0a0c" stop-opacity="0" />
					</radialGradient>
					<clipPath id="clip-{uid}"><rect x="24" y="26" width="588" height="206" rx="18" /></clipPath>
				</defs>
				<!-- bracket -->
				<rect x="2" y="14" width="18" height="250" rx="3" fill="url(#br-{uid})" />
				{#each [0, 1, 2, 3, 4, 5, 6] as i (i)}<rect x="7" y={40 + i * 28} width="8" height="18" rx="3" fill="#0b0b0d" />{/each}
				<!-- PCB edge with memory packages -->
				<rect x="20" y="222" width="600" height="40" rx="4" fill="#0d0e10" stroke="#1f2024" />
				{#each Array.from({ length: chips }, (_, i) => i) as i (i)}
					<rect x={60 + i * (520 / chips)} y="240" width={520 / chips - 8} height="12" rx="1.5" fill="#1b1c20" stroke="#2a2b30" stroke-width="0.8" />
				{/each}
				<!-- PCIe fingers -->
				<rect x="96" y="262" width="250" height="16" rx="2" fill="#4d4636" />
				{#each Array.from({ length: 30 }, (_, i) => i) as i (i)}<rect x={99 + i * 8.2} y="264" width="5" height="12" fill="#6b604c" />{/each}
				<!-- shroud -->
				<rect x="24" y="26" width="588" height="206" rx="18" fill="url(#sh-{uid})" stroke="#2c2c33" />
				<path d="M42 27.5H594" stroke="rgb(255 255 255 / 0.2)" stroke-width="1" />
				<g clip-path="url(#clip-{uid})">
					<!-- machined accents between the fans -->
					<path d="M24 196 L110 232 H24 Z M612 60 L540 26 H612 Z" fill="#17171b" stroke="rgb(255 255 255 / 0.06)" />
					{#each Array.from({ length: 9 }, (_, i) => i) as i (i)}<rect x={500 + i * 11} y="208" width="5" height="12" rx="1.5" fill="#09090b" />{/each}
					{#each fans as f, i (i)}
						<circle cx={f.cx} cy="132" r={f.r + 8} fill="url(#rim-{uid})" />
						<circle cx={f.cx} cy="132" r={f.r + 3} fill="#050506" />
						<circle cx={f.cx} cy="132" r={f.r} fill="url(#fan-{uid})" />
						<g class="fan" style="--d:{0.9 + i * 0.13}s" transform={charge != null ? `rotate(${(angle + i * 40) % 360} ${f.cx} 132)` : undefined}>
							{#each blades as a (a)}
								<path transform="translate({f.cx} 132) rotate({a})" d="M0 -{f.r * 0.24} C {f.r * 0.32} -{f.r * 0.42}, {f.r * 0.5} -{f.r * 0.78}, {f.r * 0.2} -{f.r * 0.96} L -{f.r * 0.06} -{f.r * 0.9} C {f.r * 0.14} -{f.r * 0.7}, {f.r * 0.04} -{f.r * 0.46}, -{f.r * 0.12} -{f.r * 0.27} Z" fill="url(#bl-{uid})" stroke="rgb(255 255 255 / 0.07)" stroke-width="0.8" />
							{/each}
						</g>
						{#if charge != null}<circle class="blur" cx={f.cx} cy="132" r={f.r * 0.97} fill="url(#smear-{uid})" />{/if}
						<circle cx={f.cx} cy="132" r={f.r * 0.26} fill="#111114" stroke="#34343c" stroke-width="1.5" />
						<circle cx={f.cx} cy="132" r={f.r * 0.14} fill="none" stroke="#24242a" />
						<circle cx={f.cx} cy="132" r="2.5" fill="#4a4a52" />
					{/each}
					<rect class="sweep" x="-220" y="0" width="200" height="300" fill="url(#sw-{uid})" />
				</g>
				<text x="46" y="46" class="engrave">{label}</text>
				<!-- light strip: as long and as hot as the measured speed-up -->
				<rect x="40" y="226" width="556" height="3" rx="1.5" fill="#1a1a1e" />
				<rect class="strip" x="40" y="226" width={556} height="3" rx="1.5" fill="url(#ramp-{uid})" />
			</svg>
		{/if}
		<div class="under" class:apple></div>
		<div class="sheen" class:apple></div>
	</div>
</div>

<style>
	.art {
		position: relative;
		user-select: none;
		width: 100%;
		aspect-ratio: 640 / 300;
	}
	.body {
		position: relative;
		width: 100%;
		height: 100%;
		transform: perspective(1500px) rotateY(var(--ay, -15deg)) rotateX(var(--ax, 7deg));
		transition: transform 0.9s var(--ease-out);
	}
	svg {
		position: relative;
		width: 100%;
		height: 100%;
		display: block;
		overflow: visible;
		filter: drop-shadow(0 30px 40px rgb(0 0 0 / 0.7));
	}
	.live .body {
		--ay: -6deg;
		--ax: 3deg;
	}
	.flat .body {
		--ay: 0deg;
		--ax: 0deg;
	}
	/* specular sheen on the shroud: follows the cursor through the tile's --gx/--gy */
	.sheen {
		position: absolute;
		left: 3.75%;
		right: 4.4%;
		top: 8.7%;
		bottom: 22.7%;
		border-radius: 2.8% / 8.7%;
		pointer-events: none;
		background:
			radial-gradient(40% 75% at var(--gx, 28%) var(--gy, 18%), rgb(255 243 214 / 0.16), transparent 70%),
			linear-gradient(112deg, transparent 32%, rgb(255 255 255 / 0.045) 44%, transparent 56%);
		mix-blend-mode: screen;
		opacity: 0.55;
		transition: opacity 0.5s var(--ease-out);
	}
	.sheen.apple {
		left: 29.7%;
		right: 29.7%;
		top: 6.7%;
		bottom: 6.7%;
		border-radius: 10%;
	}
	.live .sheen {
		opacity: 1;
	}
	/* heat underglow: light spilling from the strip onto the PCB, as long as the speed-up */
	.under {
		position: absolute;
		left: 6%;
		width: 87%;
		bottom: 18%;
		height: 9%;
		border-radius: 50%;
		background: var(--heat-ramp-hot);
		filter: blur(16px);
		opacity: calc((0.1 + var(--h) * 0.3) * var(--c));
		transform-origin: left center;
		transform: scaleX(calc(var(--h) * var(--c)));
		transition: opacity 0.5s var(--ease-out);
		pointer-events: none;
	}
	.under.apple,
	.cold .under {
		display: none;
	}
	.live .under {
		opacity: calc(0.2 + var(--h) * 0.6);
	}
	.floor {
		position: absolute;
		left: 12%;
		right: 8%;
		bottom: -9%;
		height: 12%;
		border-radius: 50%;
		background: radial-gradient(closest-side, rgb(0 0 0 / 0.9), transparent);
		filter: blur(6px);
	}
	.glow {
		position: absolute;
		inset: 10% 6% -8%;
		border-radius: 50%;
		background: radial-gradient(closest-side, rgb(255 122 26 / calc((0.08 + var(--h) * 0.38) * var(--c))), rgb(226 64 28 / calc(var(--h) * 0.12 * var(--c))) 55%, transparent);
		filter: blur(18px);
		transform: scale(0.92);
		transition:
			transform 0.9s var(--ease-out),
			opacity 0.9s var(--ease-out);
	}
	.cold .glow {
		background: radial-gradient(closest-side, rgb(125 135 148 / 0.1), transparent);
	}
	.live .glow {
		transform: scale(1.04);
	}
	.engrave {
		font-family: var(--font-mono);
		font-size: 13px;
		font-weight: 600;
		letter-spacing: 0.18em;
		fill: #4a4a52;
		text-transform: uppercase;
	}
	.engrave.apple {
		font-family: var(--font-display);
		font-size: 44px;
		font-weight: 800;
		letter-spacing: -0.02em;
		fill: #5a5a63;
	}
	.strip {
		transform-box: fill-box;
		transform-origin: left center;
		transform: scaleX(calc(var(--h) * var(--c)));
		transition: transform 1.2s var(--ease-out) 0.2s;
	}
	/* driven by the parent's timeline every frame: no transitions in the way */
	.driven .strip,
	.driven .under,
	.driven .glow {
		transition: none;
	}
	.driven .under {
		opacity: calc((0.15 + var(--h) * 0.55) * var(--c));
	}
	/* the backplate itself warms up: a heat wash across the shroud, as strong as the measured gain */
	.driven .sheen {
		opacity: 1;
		background:
			radial-gradient(40% 75% at var(--gx, 28%) var(--gy, 18%), rgb(255 243 214 / 0.12), transparent 70%),
			linear-gradient(0deg, rgb(255 122 26 / calc(var(--h) * var(--c) * 0.3)), transparent 60%),
			linear-gradient(180deg, rgb(125 135 148 / calc((1 - var(--c)) * 0.16)), rgb(30 52 72 / calc((1 - var(--c)) * 0.12)));
	}
	/* motion blur: the blades fade into a smeared disc as the fans speed up */
	.blur {
		opacity: calc(var(--rpm) * 0.85);
		pointer-events: none;
	}
	/* driven fans rotate through their SVG transform attribute (about the fan centre), so the CSS
	   origin must not shift it */
	.driven .fan {
		transform-box: view-box;
		transform-origin: 0 0;
		opacity: calc(1 - var(--rpm) * 0.55);
	}
	.cold .strip,
	.driven.cold .strip {
		fill: #2a3038;
		transform: scaleX(1);
	}
	.fan {
		transform-box: fill-box;
		transform-origin: center;
	}
	.sweep {
		opacity: 0;
	}
	@media (prefers-reduced-motion: no-preference) {
		/* power-on: the strip and the underglow heat up from cold, the glow swells, a light sweep passes */
		.ignite:not(.cold) .strip,
		.ignite:not(.cold) .under {
			animation: ignite 1.7s var(--ease-out) 0.55s both;
		}
		.ignite:not(.cold) .glow {
			animation: power 2.2s var(--ease-out) 0.35s both;
		}
		.ignite .sweep {
			animation: sweep 1.8s var(--ease-out) 0.9s 1 both;
		}
		.live .fan {
			animation: spin var(--d) linear infinite;
		}
		.live .sweep {
			animation: sweep 1.6s var(--ease-out) 1 both;
		}
	}
	@keyframes ignite {
		from {
			transform: scaleX(0);
			opacity: 0;
		}
	}
	@keyframes power {
		from {
			opacity: 0;
			transform: scale(0.75);
		}
		40% {
			opacity: 1;
			transform: scale(1.08);
		}
	}
	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}
	@keyframes sweep {
		0% {
			opacity: 1;
			transform: translateX(0) skewX(-18deg);
		}
		100% {
			opacity: 1;
			transform: translateX(1100px) skewX(-18deg);
		}
	}
</style>
