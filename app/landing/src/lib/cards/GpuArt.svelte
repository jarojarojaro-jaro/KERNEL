<script lang="ts" module>
	/**
	 * Per-card shroud, inferred from the card's short name (the same `label` every caller already
	 * passes): length, fan count and the maker's shroud. Stylised, not photoreal; sizes follow the
	 * real boards (≈ 1 unit per 0.56 mm of length), so a 3060 is visibly shorter than a 3090.
	 *   fe30  NVIDIA Founders (30 series): silver frame, graphite plate, one fan + flow-through fins
	 *   fe40  NVIDIA Founders (40 series, Ada): gunmetal frame with chamfered tail corners, a bigger
	 *         fan in a thick bezel, a raked fin window
	 *   fe50  NVIDIA Founders (50 series): graphite, double flow-through, a fan at each end
	 *   dark  partner two-fan boards: charcoal shroud with machined corners
	 *   amd   Radeon reference (RDNA3): black shroud, red accent stripes between the fans
	 *   radeon partner Radeon: black, brushed-silver lower edge, a thin red line
	 *   arc   Intel Arc Limited Edition: matte black, a pale diagonal light band
	 */
	type Shroud = 'fe30' | 'fe40' | 'fe50' | 'dark' | 'amd' | 'radeon' | 'arc';
	export interface ArtSpec {
		len: number;
		fans: number;
		shroud: Shroud;
	}
	const SPECS: [RegExp, ArtSpec][] = [
		[/3090/, { len: 560, fans: 1, shroud: 'fe30' }],
		[/4090/, { len: 545, fans: 1, shroud: 'fe40' }],
		[/4080/, { len: 545, fans: 1, shroud: 'fe40' }],
		[/4070/, { len: 440, fans: 1, shroud: 'fe40' }],
		[/5090|5080/, { len: 545, fans: 2, shroud: 'fe50' }],
		[/5070/, { len: 430, fans: 2, shroud: 'fe50' }],
		[/7900/, { len: 515, fans: 3, shroud: 'amd' }],
		[/9070/, { len: 570, fans: 3, shroud: 'radeon' }],
		[/B5\d0|A7\d0/, { len: 490, fans: 2, shroud: 'arc' }],
		[/5060/, { len: 415, fans: 2, shroud: 'dark' }],
		[/4060/, { len: 450, fans: 2, shroud: 'dark' }],
		[/3060/, { len: 380, fans: 2, shroud: 'dark' }]
	];
	/**
	 * Rim light per family: colour and the angle it comes from (0 = from the left, 90 = from the
	 * top). Product identity only; never the heat hues, which mean speed.
	 */
	export const LIGHT: Record<Shroud, { c: string; a: number }> = {
		fe30: { c: '#eef2f8', a: 35 },
		fe40: { c: '#a6e34a', a: 205 },
		fe50: { c: '#8fc2ff', a: 90 },
		dark: { c: '#b4c4d6', a: 120 },
		amd: { c: '#ff3b4f', a: 150 },
		radeon: { c: '#ff5d6c', a: 165 },
		arc: { c: '#3ea8ff', a: 0 }
	};
	export function artSpec(label: string, vendor: string, vram: number | null): ArtSpec {
		const hit = SPECS.find(([re]) => re.test(label));
		if (hit) return hit[1];
		const big = (vram ?? 0) >= 20;
		if (vendor === 'amd') return { len: big ? 540 : 470, fans: big ? 3 : 2, shroud: 'radeon' };
		if (vendor === 'intel') return { len: 470, fans: 2, shroud: 'arc' };
		return { len: big ? 540 : 450, fans: big ? 3 : 2, shroud: 'dark' };
	}
</script>

<script lang="ts">
	/**
	 * Stylised product render of the specific graphics card (or an Apple SoC package): bracket,
	 * the maker's shroud at the board's length with its fan layout (see `artSpec`), PCB edge with one
	 * memory package per 2 GB, PCIe fingers. `heat` (0..1) is the
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
	const spec = $derived(artSpec(label, vendor, vram));
	const fe = $derived(spec.shroud.startsWith('fe'));
	/** Shroud box on the 640×300 grid, centred: x0..x1, y 26..232. */
	const x0 = $derived(24 + (588 - spec.len) / 2);
	const x1 = $derived(x0 + spec.len);
	const fans = $derived.by(() => {
		const { fans: n, len, shroud } = spec;
		// flow-through Founders: one fan by the bracket (the second blows through the fins from behind)
		if (n === 1) return shroud === 'fe40' ? [{ cx: x0 + 108, r: len > 500 ? 92 : 84 }] : [{ cx: x0 + 100, r: len > 500 ? 88 : 80 }];
		// double flow-through: a fan at each end, the board in between
		if (shroud === 'fe50') return [{ cx: x0 + 96, r: 82 }, { cx: x1 - 96, r: 82 }];
		const slot = len / n;
		return Array.from({ length: n }, (_, i) => ({ cx: x0 + slot * (i + 0.5), r: Math.min(n === 3 ? 74 : 76, slot / 2 - (n === 3 ? 10 : 14)) }));
	});
	/** Flow-through fin window (single-fan Founders): from past the fan to the far end. */
	const fin = $derived(spec.fans === 1 ? { x: fans[0].cx + fans[0].r + 22, w: x1 - 16 - (fans[0].cx + fans[0].r + 22) } : null);
	const ada = $derived(spec.shroud === 'fe40');
	const light = $derived(LIGHT[spec.shroud]);
	/** Shroud outline: a rounded box; Ada's tail end is chamfered (a different silhouette). */
	const outline = $derived(
		ada
			? `M${x0 + 26} 26 H${x1 - 32} L${x1} 58 V200 L${x1 - 32} 232 H${x0 + 26} A26 26 0 0 1 ${x0} 206 V52 A26 26 0 0 1 ${x0 + 26} 26 Z`
			: `M${x0 + 18} 26 H${x1 - 18} A18 18 0 0 1 ${x1} 44 V214 A18 18 0 0 1 ${x1 - 18} 232 H${x0 + 18} A18 18 0 0 1 ${x0} 214 V44 A18 18 0 0 1 ${x0 + 18} 26 Z`
	);
	/** Ada's raked fin window: the leading edge leans back, the tail follows the chamfer. */
	const adaFin = $derived(fin ? `M${fin.x + 20} 46 H${x1 - 42} L${x1 - 16} 72 V186 L${x1 - 42} 212 H${fin.x - 8} Z` : '');
	/** Gaps between fans (accent stripes on the Radeon reference). */
	const gaps = $derived(fans.slice(1).map((f, i) => (fans[i].cx + fans[i].r + f.cx - f.r) / 2));
	const chips = $derived(Math.max(4, Math.min(16, Math.round((vram ?? 8) / 2))));
	/** Sheen and underglow follow the shroud box (percent of the 640-wide grid). */
	const box = $derived(`--sl:${(x0 / 6.4).toFixed(2)}%; --sr:${((640 - x1) / 6.4).toFixed(2)}%; --ul:${((x0 + 16) / 6.4).toFixed(2)}%; --uw:${((spec.len - 32) / 6.4).toFixed(2)}%`);
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

<div class="art" class:live class:flat class:ignite={ignite && charge == null} class:driven={charge != null} class:cold={h === 0} style="--h:{h}; --c:{c}; --rpm:{rpm}; --fl:{light.c}; {box}" aria-hidden="true">
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
				<text x="320" y="164" text-anchor="middle" class="engrave apple">{label.replace(/^Apple\s+/i, "")}</text>
				<rect class="strip" x="236" y="242" width="168" height="3" rx="1.5" />
			</svg>
		{:else}
			<svg viewBox="0 0 640 300" class="sh-{spec.shroud}">
				<defs>
					<linearGradient id="sh-{uid}" x1="0" y1="0" x2="0" y2="1">
						{#if spec.shroud === 'fe30'}
							<stop offset="0" stop-color="#8a8d94" />
							<stop offset="0.3" stop-color="#53565d" />
							<stop offset="0.75" stop-color="#2c2e33" />
							<stop offset="1" stop-color="#1c1d21" />
						{:else if spec.shroud === 'fe40'}
							<stop offset="0" stop-color="#4a4d54" />
							<stop offset="0.3" stop-color="#2b2d32" />
							<stop offset="1" stop-color="#141518" />
						{:else if spec.shroud === 'fe50'}
							<stop offset="0" stop-color="#3f4147" />
							<stop offset="0.4" stop-color="#232429" />
							<stop offset="1" stop-color="#121315" />
						{:else if spec.shroud === 'arc'}
							<stop offset="0" stop-color="#1d1d21" />
							<stop offset="1" stop-color="#0b0b0d" />
						{:else if spec.shroud === 'amd' || spec.shroud === 'radeon'}
							<stop offset="0" stop-color="#1c1c20" />
							<stop offset="0.55" stop-color="#0f0f12" />
							<stop offset="1" stop-color="#08080a" />
						{:else}
							<stop offset="0" stop-color="#202026" />
							<stop offset="0.55" stop-color="#121215" />
							<stop offset="1" stop-color="#0a0a0c" />
						{/if}
					</linearGradient>
					<radialGradient id="fan-{uid}" cx="0.5" cy="0.4" r="0.6">
						<stop offset="0" stop-color="#18181c" />
						<stop offset="1" stop-color="#060607" />
					</radialGradient>
					<linearGradient id="bl-{uid}" x1="0" y1="0" x2="1" y2="1">
						<stop offset="0" stop-color={fe ? '#4a4c53' : '#34343b'} />
						<stop offset="0.6" stop-color="#18181c" />
						<stop offset="1" stop-color="#0e0e10" />
					</linearGradient>
					<linearGradient id="rim-{uid}" x1="0" y1="0" x2="0" y2="1">
						<stop offset="0" stop-color={spec.shroud === 'fe30' ? '#9a9da4' : '#3c3c44'} />
						<stop offset="0.5" stop-color="#17171b" />
						<stop offset="1" stop-color={spec.shroud === 'fe30' ? '#55585e' : '#2a2a31'} />
					</linearGradient>
					<linearGradient id="br-{uid}" x1="0" y1="0" x2="1" y2="0">
						<stop offset="0" stop-color="#4a4a52" />
						<stop offset="1" stop-color="#1e1e23" />
					</linearGradient>
					<linearGradient id="ramp-{uid}" x1="0" y1="0" x2="1" y2="0">
						<stop offset="0" style="stop-color: var(--heat-1, #7a2e1f)" />
						<stop offset="0.35" style="stop-color: var(--heat-2, #e2401c)" />
						<stop offset="0.6" style="stop-color: var(--heat-3, #ff7a1a)" />
						<stop offset="0.85" style="stop-color: var(--heat-4, #ffc15a)" />
						<stop offset="1" style="stop-color: var(--heat-5, #fff3d6)" />
					</linearGradient>
					<linearGradient id="sw-{uid}" x1="0" y1="0" x2="1" y2="0">
						<stop offset="0" stop-color="#fff" stop-opacity="0" />
						<stop offset="0.5" style="stop-color: var(--heat-5, #fff3d6)" stop-opacity="0.16" />
						<stop offset="1" stop-color="#fff" stop-opacity="0" />
					</linearGradient>
					<radialGradient id="smear-{uid}" cx="0.5" cy="0.5" r="0.5">
						<stop offset="0.25" stop-color="#1b1b20" stop-opacity="0" />
						<stop offset="0.45" stop-color="#2e2e35" stop-opacity="0.9" />
						<stop offset="0.8" stop-color="#26262c" stop-opacity="0.95" />
						<stop offset="0.97" stop-color="#3a3a42" stop-opacity="0.7" />
						<stop offset="1" stop-color="#0a0a0c" stop-opacity="0" />
					</radialGradient>
					<clipPath id="clip-{uid}"><path d={outline} /></clipPath>
					{#if ada}<clipPath id="fin-{uid}"><path d={adaFin} /></clipPath>{/if}
					<linearGradient id="rl-{uid}" x1="0" y1="0.5" x2="1" y2="0.5" gradientTransform="rotate({light.a} 0.5 0.5)">
						<stop offset="0" stop-color={light.c} stop-opacity="0.95" />
						<stop offset="0.32" stop-color={light.c} stop-opacity="0.3" />
						<stop offset="0.6" stop-color={light.c} stop-opacity="0" />
						<stop offset="1" stop-color={light.c} stop-opacity="0.12" />
					</linearGradient>
				</defs>
				<!-- bracket -->
				<rect x={x0 - 22} y="14" width="18" height="250" rx="3" fill="url(#br-{uid})" />
				{#each [0, 1, 2, 3, 4, 5, 6] as i (i)}<rect x={x0 - 17} y={40 + i * 28} width="8" height="18" rx="3" fill="#0b0b0d" />{/each}
				<!-- PCB edge with memory packages -->
				<rect x={x0 - 4} y="222" width={spec.len + 8} height="40" rx="4" fill="#0d0e10" stroke="#1f2024" />
				{#each Array.from({ length: chips }, (_, i) => i) as i (i)}
					<rect x={x0 + 36 + i * ((spec.len - 72) / chips)} y="240" width={(spec.len - 72) / chips - 8} height="12" rx="1.5" fill="#1b1c20" stroke="#2a2b30" stroke-width="0.8" />
				{/each}
				<!-- PCIe fingers -->
				<rect x={x0 + 72} y="262" width="250" height="16" rx="2" fill="#4d4636" />
				{#each Array.from({ length: 30 }, (_, i) => i) as i (i)}<rect x={x0 + 75 + i * 8.2} y="264" width="5" height="12" fill="#6b604c" />{/each}
				<!-- shroud -->
				<path d={outline} fill="url(#sh-{uid})" stroke={fe ? '#5a5d64' : '#2c2c33'} />
				<path d="M{x0 + 26} 27.5H{x1 - (ada ? 34 : 18)}" stroke="rgb(255 255 255 / {spec.shroud === 'fe30' ? 0.45 : 0.2})" stroke-width="1" />
				<g clip-path="url(#clip-{uid})">
					{#if fe}
						<!-- Founders: a graphite plate inside the metal frame -->
						{#if ada}
							<!-- Ada: a gunmetal band with two machined grooves, no inner plate -->
							<path d="M{x0 + 30} 36 H{x1 - 40} M{x0 + 30} 222 H{x1 - 40}" stroke="rgb(0 0 0 / 0.55)" stroke-width="1.5" />
							<path d="M{x0 + 30} 37.5 H{x1 - 40} M{x0 + 30} 223.5 H{x1 - 40}" stroke="rgb(255 255 255 / 0.08)" />
						{:else}
							<rect x={x0 + 12} y="38" width={spec.len - 24} height="182" rx="11" fill="#121316" stroke="rgb(0 0 0 / 0.6)" />
						{/if}
						{#if fin && ada}
							<!-- raked fin window: the fin stack behind it, fins lean with the leading edge -->
							<path d={adaFin} fill="#050506" />
							<g clip-path="url(#fin-{uid})">
								{#each Array.from({ length: Math.floor((fin.w + 30) / 6.5) }, (_, i) => i) as i (i)}
									<path d="M{fin.x + 2 + i * 6.5} 46 L{fin.x - 20 + i * 6.5} 212" stroke="#26272c" stroke-width="2" />
								{/each}
							</g>
							<path d={adaFin} fill="none" stroke="rgb(255 255 255 / 0.12)" />
						{:else if fin}
							<!-- flow-through: the fin stack shows through, the second fan is behind it -->
							<rect x={fin.x} y="46" width={fin.w} height="166" rx="6" fill="#060607" />
							{#each Array.from({ length: Math.floor(fin.w / 7) }, (_, i) => i) as i (i)}
								<rect x={fin.x + 4 + i * 7} y="50" width="2" height="158" fill="#24252a" />
							{/each}
							<rect x={fin.x} y="46" width={fin.w} height="166" rx="6" fill="none" stroke="rgb(255 255 255 / 0.08)" />
							{#if spec.shroud === 'fe30'}
								<!-- the 30-series V of the frame cutting across the fins -->
								<path d="M{fin.x - 6} 30 L{fin.x + fin.w * 0.58} 132 L{fin.x - 6} 228" fill="none" stroke="#7d8087" stroke-width="12" stroke-linejoin="round" />
								<path d="M{fin.x - 6} 30 L{fin.x + fin.w * 0.58} 132 L{fin.x - 6} 228" fill="none" stroke="rgb(255 255 255 / 0.35)" stroke-width="1.2" stroke-linejoin="round" transform="translate(0 -4)" />
							{/if}
						{:else}
							<!-- double flow-through: the board sits between the two fans -->
							<rect x={fans[0].cx + fans[0].r + 18} y="70" width={fans[1].cx - fans[1].r - fans[0].cx - fans[0].r - 36} height="124" rx="8" fill="#0b0c0e" stroke="rgb(255 255 255 / 0.07)" />
						{/if}
					{:else if spec.shroud === 'dark'}
						<!-- machined accents in the corners -->
						<path d="M{x0} 196 L{x0 + 86} 232 H{x0} Z M{x1} 60 L{x1 - 72} 26 H{x1} Z" fill="#17171b" stroke="rgb(255 255 255 / 0.06)" />
					{:else if spec.shroud === 'arc'}
						<!-- a pale light band across the matte shroud -->
						<path d="M{x0 + spec.len * 0.44} 26 L{x0 + spec.len * 0.52} 26 L{x0 + spec.len * 0.48} 232 L{x0 + spec.len * 0.4} 232 Z" fill="#cfd0d6" opacity="0.5" />
					{/if}
					{#if spec.shroud === 'dark' || spec.shroud === 'amd' || spec.shroud === 'radeon'}
						{#each Array.from({ length: 9 }, (_, i) => i) as i (i)}<rect x={x1 - 112 + i * 11} y="208" width="5" height="12" rx="1.5" fill="#09090b" />{/each}
					{/if}
					{#each fans as f, i (i)}
						{#if ada}<circle cx={f.cx} cy="132" r={f.r + 14} fill="#1b1c20" stroke="rgb(255 255 255 / 0.1)" />{/if}
						<circle cx={f.cx} cy="132" r={f.r + 8} fill="url(#rim-{uid})" />
						<circle cx={f.cx} cy="132" r={f.r + 3} fill="#050506" />
						<circle cx={f.cx} cy="132" r={f.r} fill="url(#fan-{uid})" />
						<g class="fan" style="--d:{0.9 + i * 0.13}s" transform={charge != null ? `rotate(${(angle + i * 40) % 360} ${f.cx} 132)` : undefined}>
							{#each blades as a (a)}
								<path transform="translate({f.cx} 132) rotate({a})" d="M0 -{f.r * 0.24} C {f.r * 0.32} -{f.r * 0.42}, {f.r * 0.5} -{f.r * 0.78}, {f.r * 0.2} -{f.r * 0.96} L -{f.r * 0.06} -{f.r * 0.9} C {f.r * 0.14} -{f.r * 0.7}, {f.r * 0.04} -{f.r * 0.46}, -{f.r * 0.12} -{f.r * 0.27} Z" fill="url(#bl-{uid})" stroke="rgb(255 255 255 / 0.07)" stroke-width="0.8" />
							{/each}
						</g>
						{#if charge != null}<circle class="blur" cx={f.cx} cy="132" r={f.r * 0.97} fill="url(#smear-{uid})" />{/if}
						<circle cx={f.cx} cy="132" r={f.r * 0.26} fill="#111114" stroke={spec.shroud === 'arc' ? '#8d8e95' : '#34343c'} stroke-width="1.5" />
						<circle cx={f.cx} cy="132" r={f.r * 0.14} fill="none" stroke="#24242a" />
						<circle cx={f.cx} cy="132" r="2.5" fill="#4a4a52" />
					{/each}
					{#if spec.shroud === 'amd'}
						<!-- reference RDNA3: three red stripes in each gap between the fans, top and bottom -->
						{#each gaps as gx (gx)}
							{#each [-7, 0, 7] as o (o)}
								<path d="M{gx + o - 5} 30 L{gx + o + 5} 52" stroke="#d1202f" stroke-width="2.2" stroke-linecap="round" />
								<path d="M{gx + o - 5} 206 L{gx + o + 5} 228" stroke="#d1202f" stroke-width="2.2" stroke-linecap="round" />
							{/each}
						{/each}
					{:else if spec.shroud === 'radeon'}
						<rect x={x0} y="214" width={spec.len} height="18" fill="#3b3d42" />
						<path d="M{x0} 214.5 H{x1}" stroke="rgb(255 255 255 / 0.25)" />
						<path d="M{x0 + 26} 208 H{x0 + spec.len * 0.36}" stroke="#d1202f" stroke-width="2" stroke-linecap="round" />
					{/if}
					<rect class="sweep" x={x0 - 244} y="0" width="200" height="300" fill="url(#sw-{uid})" />
				</g>
				<!-- rim light: the family's colour, from the family's side -->
				<path d={outline} fill="none" stroke="url(#rl-{uid})" stroke-width="5" opacity="0.28" />
				<path d={outline} fill="none" stroke="url(#rl-{uid})" stroke-width="1.6" />
				{#if spec.shroud === 'fe50'}
					<text x={(x0 + x1) / 2} y="182" text-anchor="middle" class="engrave fe">{label}</text>
				{:else if fe}
					<!-- a dark name plate over the fin stack: always whole, always readable -->
					{@const pw = label.length * 8.8 + 18}
					<rect x={x1 - (ada ? 52 : 30) - pw} y="54" width={pw} height="20" rx="4" fill="#141518" stroke="rgb(255 255 255 / 0.24)" />
					<text x={x1 - (ada ? 52 : 30) - pw / 2} y="68" text-anchor="middle" class="engrave fe band">{label}</text>
				{:else}
					<text x={x0 + 22} y="46" class="engrave">{label}</text>
				{/if}
				<!-- light strip: as long and as hot as the measured speed-up -->
				<rect x={x0 + 16} y="226" width={spec.len - 32} height="3" rx="1.5" fill="#1a1a1e" />
				<rect class="strip" x={x0 + 16} y="226" width={spec.len - 32} height="3" rx="1.5" fill="url(#ramp-{uid})" />
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
		left: var(--sl, 3.75%);
		right: var(--sr, 4.4%);
		top: 8.7%;
		bottom: 22.7%;
		border-radius: 2.8% / 8.7%;
		pointer-events: none;
		background:
			radial-gradient(40% 75% at var(--gx, 28%) var(--gy, 18%), rgb(var(--white-rgb, 255 243 214) / 0.16), transparent 70%),
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
		left: var(--ul, 6%);
		width: var(--uw, 87%);
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
		background: radial-gradient(closest-side, rgb(var(--hot-rgb, 255 122 26) / calc((0.08 + var(--h) * 0.38) * var(--c))), rgb(var(--ember-rgb, 226 64 28) / calc(var(--h) * 0.12 * var(--c))) 55%, transparent);
		filter: blur(18px);
		transform: scale(0.92);
		transition:
			transform 0.9s var(--ease-out),
			opacity 0.9s var(--ease-out);
	}
	/* not measured yet: no heat, the family's own light behind the card */
	.cold .glow {
		background: radial-gradient(closest-side, color-mix(in srgb, var(--fl, #7d8794) 13%, transparent), transparent);
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
	.engrave.fe {
		fill: #b3b6bd;
	}
	.engrave.band {
		font-size: 11px;
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
			radial-gradient(40% 75% at var(--gx, 28%) var(--gy, 18%), rgb(var(--white-rgb, 255 243 214) / 0.12), transparent 70%),
			linear-gradient(0deg, rgb(var(--hot-rgb, 255 122 26) / calc(var(--h) * var(--c) * 0.3)), transparent 60%),
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
