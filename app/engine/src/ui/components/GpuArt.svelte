<script lang="ts">
	/**
	 * Stylised render of the scanned hardware: a graphics card (fan count from VRAM, one memory package
	 * per 2 GB along the board edge, the die tagged with its architecture), an Apple SoC package, or a
	 * bare CPU package when there is no GPU. Decorative: every fact is also in the text list next to it.
	 * Vendor rim light is product identity, never the heat hues (heat means speed).
	 */
	import type { Gpu } from '../../shared/types';

	let { gpu, cpuName = '' }: { gpu: Gpu | null; cpuName?: string } = $props();

	const RIM: Record<Gpu['vendor'], string> = { nvidia: '#a6e34a', amd: '#ff3b4f', intel: '#3ea8ff', apple: '#d8dde6' };
	const kind = $derived(!gpu ? 'cpu' : gpu.vendor === 'apple' || gpu.unified ? 'soc' : 'card');
	const rim = $derived(gpu ? RIM[gpu.vendor] : '#b4c4d6');
	const fans = $derived(gpu && gpu.vramGiB >= 20 ? 3 : 2);
	const chips = $derived(Math.max(2, Math.min(12, Math.round((gpu?.vramGiB ?? 8) / 2))));
	const tag = $derived(gpu?.arch ?? (gpu ? gpu.vendor.toUpperCase() : 'CPU'));
	const fanX = $derived(Array.from({ length: fans }, (_, i) => 30 + ((470 - 30) / fans) * (i + 0.5)));
	const blades = Array.from({ length: 9 }, (_, i) => i * 40);
	const socPins = Array.from({ length: 10 }, (_, i) => i);
</script>

<div class="art" style="--rim:{rim}">
	{#if kind === 'card'}
		<svg viewBox="0 0 520 210" role="presentation" aria-hidden="true" focusable="false">
			<defs>
				<linearGradient id="ga-shroud" x1="0" y1="0" x2="0" y2="1">
					<stop offset="0" stop-color="#2a2a30" />
					<stop offset=".55" stop-color="#16161a" />
					<stop offset="1" stop-color="#0c0c0f" />
				</linearGradient>
				<radialGradient id="ga-fan" cx=".5" cy=".5" r=".5">
					<stop offset="0" stop-color="#1b1b20" />
					<stop offset="1" stop-color="#08080a" />
				</radialGradient>
				<linearGradient id="ga-gold" x1="0" y1="0" x2="0" y2="1">
					<stop offset="0" stop-color="#e9c46a" />
					<stop offset="1" stop-color="#a87b26" />
				</linearGradient>
			</defs>
			<!-- bracket -->
			<rect x="2" y="14" width="18" height="168" rx="3" fill="#8c9096" />
			<rect x="7" y="34" width="8" height="26" rx="2" fill="#4a4d52" />
			<rect x="7" y="70" width="8" height="26" rx="2" fill="#4a4d52" />
			<rect x="7" y="106" width="8" height="26" rx="2" fill="#4a4d52" />
			<!-- pcb edge with memory packages -->
			<rect x="22" y="152" width="486" height="22" rx="4" fill="#101a16" />
			{#each Array.from({ length: chips }, (_, i) => i) as i (i)}
				<rect x={52 + i * (420 / chips)} y="157" width={Math.min(26, 420 / chips - 6)} height="12" rx="2" fill="#2b2f33" stroke="#4b5056" stroke-width=".8" />
			{/each}
			<!-- pcie fingers -->
			<rect x="70" y="174" width="210" height="16" rx="2" fill="url(#ga-gold)" />
			{#each Array.from({ length: 26 }, (_, i) => i) as i (i)}
				<rect x={74 + i * 8} y="176" width="4" height="12" fill="#7a5a1c" opacity=".55" />
			{/each}
			<!-- shroud -->
			<rect x="22" y="14" width="486" height="142" rx="16" fill="url(#ga-shroud)" />
			<rect x="22.5" y="14.5" width="485" height="141" rx="15.5" fill="none" stroke="var(--rim)" stroke-opacity=".55" />
			<path d="M40 150 H490" stroke="var(--rim)" stroke-width="2" stroke-linecap="round" opacity=".8" />
			{#each fanX as cx (cx)}
				<g transform="translate({cx} 84)">
					<circle r="60" fill="#0a0a0c" stroke="#2c2c33" stroke-width="2" />
					<circle r="54" fill="url(#ga-fan)" />
					{#each blades as a (a)}
						<path d="M0 -11 C 15 -20 25 -38 12 -51 C 3 -42 -5 -27 0 -11 Z" fill="#26262c" stroke="#3a3a42" stroke-width=".8" transform="rotate({a})" />
					{/each}
					<circle r="13" fill="#1d1d22" stroke="#3a3a42" />
					<circle r="5" fill="var(--rim)" opacity=".7" />
				</g>
			{/each}
			<!-- die tag -->
			<g transform="translate(442 30)">
				<rect x="-36" y="0" width="72" height="20" rx="10" fill="#0a0a0c" stroke="var(--rim)" stroke-opacity=".6" />
				<text x="0" y="14" text-anchor="middle" fill="#edeae3" font-family="Martian Mono, monospace" font-size="10" letter-spacing=".5">{tag}</text>
			</g>
		</svg>
	{:else}
		<svg viewBox="0 0 260 210" role="presentation" aria-hidden="true" focusable="false">
			<defs>
				<linearGradient id="ga-pkg" x1="0" y1="0" x2="1" y2="1">
					<stop offset="0" stop-color="#2a2a30" />
					<stop offset="1" stop-color="#0e0e11" />
				</linearGradient>
			</defs>
			<rect x="40" y="15" width="180" height="180" rx="22" fill="#121216" stroke="#2c2c33" stroke-width="2" />
			{#each socPins as i (i)}
				<rect x={52 + i * 16} y="3" width="6" height="12" rx="1.5" fill="#8c9096" />
				<rect x={52 + i * 16} y="195" width="6" height="12" rx="1.5" fill="#8c9096" />
				<rect x="28" y={27 + i * 16} width="12" height="6" rx="1.5" fill="#8c9096" />
				<rect x="220" y={27 + i * 16} width="12" height="6" rx="1.5" fill="#8c9096" />
			{/each}
			<rect x="70" y="45" width="120" height="120" rx="12" fill="url(#ga-pkg)" stroke="var(--rim)" stroke-opacity=".6" />
			{#if kind === 'soc'}
				<rect x="52" y="60" width="12" height="90" rx="3" fill="#2b2f33" stroke="#4b5056" />
				<rect x="196" y="60" width="12" height="90" rx="3" fill="#2b2f33" stroke="#4b5056" />
			{/if}
			<text x="130" y="110" text-anchor="middle" fill="#edeae3" font-family="Martian Mono, monospace" font-size="12" letter-spacing=".5">{kind === 'cpu' ? 'CPU' : tag}</text>
			{#if kind === 'cpu' && cpuName}
				<text x="130" y="128" text-anchor="middle" fill="#8e8a83" font-family="Martian Mono, monospace" font-size="7">{cpuName.replace(/^(AMD|Intel\(R\)|Intel)\s+/i, '').replace(/\s+\d+-Core Processor$|\s+Processor$/i, '').slice(0, 24)}</text>
			{/if}
		</svg>
	{/if}
</div>

<style>
	.art {
		position: relative;
		display: grid;
		place-items: center;
		padding: var(--sp-4);
		border-radius: 1.25rem;
		background:
			radial-gradient(60% 55% at 50% 60%, color-mix(in srgb, var(--rim) 14%, transparent), transparent 70%),
			linear-gradient(180deg, #121215, #070708);
		border: 1px solid var(--line);
		overflow: hidden;
	}
	.art::after {
		content: '';
		position: absolute;
		inset: 0;
		background-image:
			linear-gradient(rgb(237 234 227 / 0.04) 1px, transparent 1px),
			linear-gradient(90deg, rgb(237 234 227 / 0.04) 1px, transparent 1px);
		background-size: 24px 24px;
		pointer-events: none;
	}
	svg {
		position: relative;
		z-index: 1;
		width: 100%;
		height: auto;
		max-height: 15rem;
		filter: drop-shadow(0 20px 30px rgb(0 0 0 / 0.55));
	}
</style>
