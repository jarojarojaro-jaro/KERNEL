<script lang="ts">
	/**
	 * Our lab card, Sapphire PULSE RX 7900 XTX, drawn after Sapphire's dimension drawing and product
	 * photos as the faces of a box the scan scene assembles in CSS 3D (one SVG per face, so each stays
	 * crisp at any size):
	 * - `front` (800×330): gunmetal shroud, a darker recessed fan panel bordered by the PULSE red
	 *   pinstripes that step between fans 1 and 2, nine-blade fans with the red-ringed PULSE hub, corner
	 *   vents, top bevel and specular sheen, short steel bracket, PCIe x16 fingers with their key;
	 * - `top` (800×135, back edge at the top): backplate edge, the SAPPHIRE plate, fin stack and heat
	 *   pipes through the shroud window, three 8-pin sockets at the tail (spec sheet: 3 × 8-pin);
	 * - `end` (135×330): the open fin edge of the tail;
	 * - `xray` (800×330, same grid as `front`): the board (Navi 31: GCD + six MCDs, 12 GDDR6 packages,
	 *   two per MCD, VRM, outputs, fin stack past the PCB end); `lit` turns the parts the scan has read red,
	 *   fills the memory with the model's share (`fill`) and runs the data (`flow`) and current animations.
	 * No <text>: lettering is stroked paths from a small built-in glyph set, so nothing in the drawing
	 * reaches the page text, selection or reader mode. Rotors turn by `--spin` (turns) and blur by
	 * `--rpm` (0..1), both set by the caller.
	 */
	type Part = 'front' | 'top' | 'end' | 'xray';
	/** Parts the scan has read (stay lit), the model's share of VRAM (0..1) and the live effects. */
	type Lit = { mem?: boolean; gpu?: boolean; bus?: boolean; pwr?: boolean; fill?: number; flow?: boolean; current?: boolean };
	let { part, lit = {} }: { part: Part; lit?: Lit } = $props();
	const uid = $props.id();

	/** Stroke glyphs on a 4 × 6 cell (y down); width 0 = a single stem. */
	const GLYPH: Record<string, [string, number]> = {
		A: ['M0 6L2 0L4 6M0.8 3.9H3.2', 4],
		D: ['M0 0V6H1.8C3.4 6 4 4.8 4 3S3.4 0 1.8 0Z', 4],
		E: ['M4 0H0V6H4M0 3H3.2', 4],
		H: ['M0 0V6M4 0V6M0 3H4', 4],
		I: ['M0 0V6', 0],
		L: ['M0 0V6H3.6', 3.6],
		N: ['M0 6V0L4 6V0', 4],
		O: ['M2 0C3.4 0 4 1.2 4 3S3.4 6 2 6S0 4.8 0 3S0.6 0 2 0Z', 4],
		P: ['M0 6V0H2.6C3.6 0 4 0.7 4 1.6S3.6 3.2 2.6 3.2H0', 4],
		R: ['M0 6V0H2.6C3.6 0 4 0.7 4 1.6S3.6 3.2 2.6 3.2H0M2.2 3.2L4 6', 4],
		S: ['M4 0.8C3.6 0.2 3 0 2 0C0.8 0 0 0.6 0 1.5C0 3.2 4 2.6 4 4.5C4 5.4 3.2 6 2 6C1 6 0.3 5.7 0 5.2', 4],
		U: ['M0 0V4.2C0 5.4 0.8 6 2 6S4 5.4 4 4.2V0', 4],
		V: ['M0 0L2 6L4 0', 4],
		'1': ['M0.4 1.2L1.8 0V6', 1.8],
		'3': ['M0.2 0.6C0.6 0.2 1.2 0 2 0C3.3 0 4 0.6 4 1.5S3.3 3 2 3C3.3 3 4 3.6 4 4.5S3.3 6 2 6C1.2 6 0.5 5.8 0.1 5.4', 4]
	};
	/** Lay out a word: glyph paths with their x offsets and the total width (glyph units). */
	function word(s: string, track = 1.5) {
		let x = 0;
		const g: { d: string; x: number; i: number }[] = [];
		[...s].forEach((ch, i) => {
			if (ch === ' ') {
				x += 2.4;
				return;
			}
			const [d, w] = GLYPH[ch];
			g.push({ d, x, i });
			x += w + track;
		});
		return { g, w: x - track };
	}
	const PULSE = word('PULSE', 1.3);
	const SAPPHIRE = word('SAPPHIRE', 1.7);
	const NAVI = word('NAVI 31', 1.4);

	const FANS = [170, 403, 636];
	const FY = 157;
	const pt = (cx: number, r: number, deg: number) => {
		const a = (deg * Math.PI) / 180;
		return `${(cx + r * Math.cos(a)).toFixed(1)} ${(FY + r * Math.sin(a)).toFixed(1)}`;
	};
	/** A swept PULSE blade: leading edge hub → tip, along the tip circle, trailing edge back to the hub. */
	const blade = (cx: number, a: number) =>
		`M${pt(cx, 33, a)} C${pt(cx, 56, a + 2)} ${pt(cx, 86, a + 16)} ${pt(cx, 104, a + 40)} A104 104 0 0 0 ${pt(cx, 104, a + 13)} C${pt(cx, 84, a - 3)} ${pt(cx, 54, a - 15)} ${pt(cx, 33, a - 23)}Z`;
	/** Leading edge alone, for the specular highlight. */
	const edge = (cx: number, a: number) => `M${pt(cx, 35, a)} C${pt(cx, 56, a + 2)} ${pt(cx, 86, a + 16)} ${pt(cx, 103, a + 39)}`;
	const BLADES = Array.from({ length: 9 }, (_, i) => i * 40);
	/** Three 8-pin sockets at the tail (x of each, 36 wide), on the top edge and in the x-ray. */
	const PINS = [586, 628, 670];
	const holes = Array.from({ length: 8 }, (_, i) => ({ dx: 5 + (i % 4) * 7.5, dy: i < 4 ? 6 : 12 }));
	/** PCIe x16: the short segment before the key, then the long run. */
	const fingers = [...Array.from({ length: 3 }, (_, i) => 101 + i * 6.6), ...Array.from({ length: 28 }, (_, i) => 131 + i * 7.3)];
	/** Shroud outline (x 22..784, y 16..298) with the slight chamfer at the tail bottom. */
	const SHROUD = 'M22 24Q22 16 30 16H776Q784 16 784 24V286L772 298H30Q22 298 22 290Z';
	/** The recessed fan panel between the two pinstripes (they step between fans 1 and 2). */
	const PANEL = 'M22 72H272L288 56H784V258H288L272 242H22Z';
	const SLOTS = [
		[40, 60],
		[40, 254],
		[290, 64],
		[290, 250],
		[766, 64],
		[766, 250]
	];

	// top face: fin stack through the shroud window
	const topFins = Array.from({ length: 64 }, (_, i) => 304 + i * 4);
	// end face: the open fin edge
	const endFins = Array.from({ length: 52 }, (_, i) => 26 + i * 5.2);

	// x-ray, on the front grid: the Navi 31 package sits behind the middle fan (die centre 403, 160),
	// 12 GDDR6 packages around it, each pair on one of the six MCDs, the VRM toward the tail under the
	// 8-pin sockets, PCIe lanes from the fingers into the package
	const DIE = { x: 403, y: 160 };
	const MCD = [
		{ x: 345, y: 112 },
		{ x: 345, y: 147 },
		{ x: 345, y: 182 },
		{ x: 443, y: 112 },
		{ x: 443, y: 147 },
		{ x: 443, y: 182 }
	];
	const mc = (i: number) => ({ x: MCD[i].x + 9, y: MCD[i].y + 13 });
	/** Clockwise from the top-left, so the chips light up around the die in order. */
	const MEM = [
		...[328, 368].map((x) => ({ x, y: 48, w: 30, h: 22, to: 0 })),
		...[408, 448].map((x) => ({ x, y: 48, w: 30, h: 22, to: 3 })),
		...[120, 172].map((y) => ({ x: 499, y, w: 22, h: 30, to: 4 })),
		...[448, 408].map((x) => ({ x, y: 250, w: 30, h: 22, to: 5 })),
		...[368, 328].map((x) => ({ x, y: 250, w: 30, h: 22, to: 2 })),
		...[172, 120].map((y) => ({ x: 285, y, w: 22, h: 30, to: 1 }))
	];
	const bus = MEM.map((m) => {
		const c = { x: m.x + m.w / 2, y: m.y + m.h / 2 };
		const t = mc(m.to);
		return m.w > m.h ? `M${c.x} ${c.y} V${(c.y + t.y) / 2} H${t.x} V${t.y}` : `M${c.x} ${c.y} H${(c.x + t.x) / 2} V${t.y} H${t.x}`;
	});
	const CH = Array.from({ length: 6 }, (_, i) => 548 + i * 25);
	const chokes = CH.flatMap((x) => [98, 202].map((y) => ({ x, y })));
	const caps = Array.from({ length: 8 }, (_, i) => 552 + i * 18);
	/** Current: sockets → a bus along the top → every choke column → down to the lower row → into the package. */
	const power = [
		...PINS.map((x) => `M${x + 18} 21V72`),
		'M560 72H700',
		...CH.map((x) => `M${x + 10.5} 72V98`),
		...CH.map((x) => `M${x + 10.5} 119V202`),
		'M548 140H471',
		'M548 180H471'
	];
	const xfins = Array.from({ length: 13 }, (_, i) => 708 + i * 6);
	const lanes = Array.from({ length: 6 }, (_, i) => `M${120 + i * 34} 300V${290 - i * 3}H${312 + i * 3}V${212 + i * 2}H335`);
</script>

{#snippet lettering(w: ReturnType<typeof word>, x: number, y: number, s: number, cls: string, skew = 0)}
	<g transform="translate({x - (w.w * s) / 2} {y}) scale({s}) skewX({skew})" class={cls}>
		{#each w.g as l (l.i)}<path d={l.d} transform="translate({l.x} 0)" />{/each}
	</g>
{/snippet}

{#if part === 'front'}
	<svg viewBox="0 0 800 330" class="art" aria-hidden="true" focusable="false">
		<defs>
			<linearGradient id="{uid}-body" x1="0" y1="0" x2="0.15" y2="1">
				<stop offset="0" stop-color="#5a5b62" />
				<stop offset="0.18" stop-color="#46474d" />
				<stop offset="0.8" stop-color="#34353a" />
				<stop offset="1" stop-color="#26272b" />
			</linearGradient>
			<linearGradient id="{uid}-panel" x1="0" y1="0" x2="0" y2="1">
				<stop offset="0" stop-color="#1c1d21" />
				<stop offset="0.5" stop-color="#242529" />
				<stop offset="1" stop-color="#1a1b1e" />
			</linearGradient>
			<linearGradient id="{uid}-sheen" x1="0" y1="0" x2="1" y2="0.35">
				<stop offset="0.3" stop-color="#fff" stop-opacity="0" />
				<stop offset="0.46" stop-color="#fff" stop-opacity="0.09" />
				<stop offset="0.5" stop-color="#fff" stop-opacity="0.025" />
				<stop offset="0.62" stop-color="#fff" stop-opacity="0" />
			</linearGradient>
			<linearGradient id="{uid}-brkt" x1="0" y1="0" x2="1" y2="0">
				<stop offset="0" stop-color="#6a6a72" />
				<stop offset="0.45" stop-color="#d4d4da" />
				<stop offset="1" stop-color="#55555c" />
			</linearGradient>
			<linearGradient id="{uid}-bevel" x1="0" y1="0" x2="0" y2="1">
				<stop offset="0" stop-color="#0d0d0f" />
				<stop offset="0.55" stop-color="#2b2c31" />
				<stop offset="1" stop-color="#7a7b83" />
			</linearGradient>
			<radialGradient id="{uid}-well">
				<stop offset="0.28" stop-color="#040405" />
				<stop offset="0.9" stop-color="#0f0f12" />
				<stop offset="1" stop-color="#1b1b1f" />
			</radialGradient>
			<linearGradient id="{uid}-blade" x1="0" y1="0" x2="1" y2="1">
				<stop offset="0" stop-color="#4a4b53" />
				<stop offset="0.45" stop-color="#2a2b31" />
				<stop offset="1" stop-color="#15161a" />
			</linearGradient>
			<radialGradient id="{uid}-smear">
				<stop offset="0.3" stop-color="#3a3b42" stop-opacity="0.25" />
				<stop offset="0.78" stop-color="#55565e" stop-opacity="0.6" />
				<stop offset="1" stop-color="#2a2b31" stop-opacity="0.35" />
			</radialGradient>
			<radialGradient id="{uid}-hub" cx="0.38" cy="0.32" r="0.75">
				<stop offset="0" stop-color="#4a4b52" />
				<stop offset="0.55" stop-color="#1d1e22" />
				<stop offset="1" stop-color="#09090b" />
			</radialGradient>
			<linearGradient id="{uid}-gold" x1="0" y1="0" x2="0" y2="1">
				<stop offset="0" stop-color="#e6c27a" />
				<stop offset="1" stop-color="#7d6534" />
			</linearGradient>
		</defs>
		<!-- PCB edge and PCIe fingers under the shroud -->
		<rect x="92" y="294" width="252" height="10" fill="#0c1410" />
		{#each fingers as x (x)}<rect {x} y="302" width="4.6" height="20" rx="0.8" fill="url(#{uid}-gold)" />{/each}
		<!-- bracket, edge-on: shorter than the shroud, top tab, tongue -->
		<path d="M2 84H22V330H16V320H9V92H2Z" fill="url(#{uid}-brkt)" />
		<path d="M6 120V160M6 200V240" class="brkt-slot" />
		<!-- backplate edge peeking along the bottom -->
		<path d="M30 300H770" class="bp" />
		<!-- shroud: body, recessed fan panel, bevels -->
		<path d={SHROUD} fill="url(#{uid}-body)" class="body" />
		<path d={PANEL} fill="url(#{uid}-panel)" class="panel" />
		<path d="M30 17.5H776" class="hi" />
		<path d="M24 73H271.5L287.5 57H782" class="hi soft" />
		<path d="M30 296.5H770" class="lo" />
		<!-- the PULSE red pinstripes on the bands, stepping between fans 1 and 2 -->
		<path d="M24 66H269L285 50H782 M24 248H269L285 264H782" class="red" />
		{#each SLOTS as [x, y] (x * 1000 + y)}<path d="M{x - 5} {y + 5}L{x + 5} {y - 5}" class="slot" />{/each}
		<!-- three fans -->
		{#each FANS as cx (cx)}
			<circle {cx} cy={FY} r="121" class="ring-shadow" />
			<circle {cx} cy={FY} r="117" class="ring" stroke="url(#{uid}-bevel)" />
			<circle {cx} cy={FY} r="112" fill="url(#{uid}-well)" />
			<g class="rotor" style="transform-origin: {cx}px {FY}px">
				<g class="blades">
					{#each BLADES as a (a)}
						<path d={blade(cx, a)} fill="url(#{uid}-blade)" class="blade" />
						<path d={edge(cx, a)} class="blade-hi" />
					{/each}
				</g>
				<circle {cx} cy={FY} r="33" fill="url(#{uid}-hub)" class="hub" />
				<circle {cx} cy={FY} r="27.5" class="hub-ring" />
				{@render lettering(PULSE, cx + 1.2, FY - 4.2, 1.42, 'mark', -14)}
				<path d="M{cx - 18} {FY - 17}A26 26 0 0 1 {cx + 12} {FY - 22}" class="gloss" />
			</g>
			<!-- motion blur: the spinning blades read as a disc -->
			<circle {cx} cy={FY} r="106" fill="url(#{uid}-smear)" class="smear" />
		{/each}
		<!-- specular sheen across the shroud -->
		<path d={SHROUD} fill="url(#{uid}-sheen)" class="sheen" />
	</svg>
{:else if part === 'top'}
	<svg viewBox="0 0 800 135" class="art" preserveAspectRatio="none" aria-hidden="true" focusable="false">
		<defs>
			<linearGradient id="{uid}-lip" x1="0" y1="0" x2="0" y2="1">
				<stop offset="0" stop-color="#2a2b30" />
				<stop offset="1" stop-color="#5d5e65" />
			</linearGradient>
			<linearGradient id="{uid}-plate" x1="0" y1="0" x2="1" y2="1">
				<stop offset="0" stop-color="#8d8e95" />
				<stop offset="0.5" stop-color="#c9cad0" />
				<stop offset="1" stop-color="#77787f" />
			</linearGradient>
			<linearGradient id="{uid}-pipe" x1="0" y1="0" x2="0" y2="1">
				<stop offset="0" stop-color="#5a5b61" />
				<stop offset="0.5" stop-color="#b9babf" />
				<stop offset="1" stop-color="#4a4b51" />
			</linearGradient>
		</defs>
		<!-- backplate edge, then the shroud's top lip, lit from above toward the front -->
		<rect x="0" y="0" width="800" height="12" fill="#151518" />
		<path d="M0 11.5H800" class="hi" />
		<rect x="0" y="12" width="800" height="123" fill="url(#{uid}-lip)" />
		<!-- window onto the fin stack and the heat pipes -->
		<rect x="300" y="26" width="262" height="86" rx="3" fill="#0c0c0e" />
		{#each topFins as x (x)}<path d="M{x} 28V110" class="tfin" />{/each}
		{#each [42, 60, 78, 96] as y (y)}<rect x="300" y={y - 4} width="262" height="8" rx="4" fill="url(#{uid}-pipe)" />{/each}
		<!-- SAPPHIRE plate -->
		<rect x="86" y="40" width="190" height="56" rx="4" fill="url(#{uid}-plate)" class="plate" />
		{@render lettering(SAPPHIRE, 181, 59, 2.9, 'plate-mark')}
		<!-- 3 × 8-pin sockets at the tail, facing up -->
		{#each PINS as x (x)}
			<g class="sock" class:on={lit.pwr}>
				<rect {x} y="40" width="36" height="34" rx="2.5" />
				{#each holes as h (h.dx + h.dy * 10)}<rect x={x + h.dx} y={40 + h.dy * 1.6} width="4.4" height="5.6" rx="0.8" class="hole" />{/each}
				<rect x={x + 12} y="74" width="12" height="6" rx="1" class="latch" />
			</g>
		{/each}
		<path d="M0 134H800" class="lo" />
	</svg>
{:else if part === 'end'}
	<svg viewBox="0 0 135 330" class="art" preserveAspectRatio="none" aria-hidden="true" focusable="false">
		<rect x="0" y="0" width="135" height="330" fill="#1d1e22" />
		<rect x="10" y="20" width="115" height="290" rx="3" fill="#08080a" />
		{#each endFins as y (y)}<path d="M12 {y}H123" class="efin" />{/each}
		{#each [34, 58, 82, 106] as x (x)}<circle cx={x} cy="40" r="6" class="epipe" />{/each}
		<path d="M0.5 0V330" class="hi" />
	</svg>
{:else}
	<svg viewBox="0 0 800 330" class="art xray" aria-hidden="true" focusable="false">
		<defs>
			<pattern id="{uid}-grid" width="16" height="16" patternUnits="userSpaceOnUse">
				<path d="M16 0H0V16" fill="none" stroke="rgb(237 234 227 / 0.05)" />
			</pattern>
			<radialGradient id="{uid}-die">
				<stop offset="0" stop-color="#ff3b4f" stop-opacity=".4" />
				<stop offset="1" stop-color="#ff3b4f" stop-opacity="0" />
			</radialGradient>
		</defs>
		<!-- the cooler past the PCB end: fin stack and heat pipes -->
		<path d={SHROUD} class="shell" />
		{#each xfins as x (x)}<path d="M{x} 26V288" class="fin" />{/each}
		<!-- PCB -->
		<rect x="24" y="22" width="678" height="278" rx="6" class="pcb" />
		<rect x="24" y="22" width="678" height="278" rx="6" fill="url(#{uid}-grid)" />
		<path d="M403 92V60Q403 34 433 34H780 M403 228V262Q403 286 433 286H780 M471 132H780 M471 188H780" class="pipe" />
		<!-- bracket and display outputs -->
		<path d="M2 84H22V330H16V320H9V92H2Z" class="ln faint" />
		{#each [96, 148, 200, 252] as y (y)}<rect x="28" {y} width="26" height="42" rx="3" class="ln" />{/each}
		<!-- PCIe x16 fingers and lanes into the package -->
		{#each fingers as x (x)}<rect {x} y="302" width="4.6" height="20" rx="0.8" class="ln faint" />{/each}
		{#each lanes as d (d)}<path {d} class="trace lane" />{/each}
		<!-- memory bus: two GDDR6 packages per MCD; dashes race along it while the bandwidth is read -->
		{#each bus as d, i (d)}<path {d} pathLength="20" class="trace bus" class:on={lit.bus} class:flow={lit.flow} class:rev={i % 2 === 1} />{/each}
		{#each MEM as m, i (i)}
			<rect x={m.x} y={m.y} width={m.w} height={m.h} rx="2" class="mem" class:on={lit.mem} style="--i:{i}" />
			<rect x={m.x + 2} y={m.y + 2} width={m.w - 4} height={m.h - 4} rx="1" class="mfill" style="--i:{i}; --f:{Math.max(0, Math.min(1, (lit.fill ?? 0) * MEM.length - i))}" />
		{/each}
		<!-- Navi 31 package: GCD and six MCDs -->
		<circle cx={DIE.x} cy={DIE.y} r="96" fill="url(#{uid}-die)" class="halo" class:on={lit.gpu} />
		<rect x="335" y="92" width="136" height="136" rx="6" class="ln strong" />
		{#each MCD as d, i (i)}<rect x={d.x} y={d.y} width="18" height="26" rx="2" class="die mcd" class:on={lit.gpu} />{/each}
		<rect x="371" y="128" width="64" height="64" rx="3" class="die" class:on={lit.gpu} />
		{@render lettering(NAVI, DIE.x, 155, 1.35, 'die-mark')}
		<!-- VRM: chokes, power stages, capacitors; current flows from the sockets while the power is read -->
		{#each power as d (d)}<path {d} pathLength="20" class="trace pwr" class:on={lit.pwr} class:flow={lit.current} />{/each}
		{#each chokes as k, i (i)}
			<rect x={k.x} y={k.y} width="21" height="21" rx="3" class="choke" class:on={lit.pwr} />
			<rect x={k.x + 3} y={k.y + (k.y < 150 ? 27 : -15)} width="15" height="9" rx="1" class="ln faint" />
		{/each}
		{#each caps as x (x)}<circle cx={x} cy="166" r="6" class="ln faint" />{/each}
		<!-- 3 × 8-pin -->
		{#each PINS as x (x)}
			<rect {x} y="1" width="36" height="20" rx="2" class="sock-x" class:on={lit.pwr} />
			{#each holes as h (h.dx + h.dy * 10)}<rect x={x + h.dx} y={h.dy} width="4" height="4" rx="0.6" class="ln faint" />{/each}
		{/each}
	</svg>
{/if}

<style>
	.art {
		display: block;
		width: 100%;
		height: 100%;
		overflow: visible;
		user-select: none;
		pointer-events: none;
	}
	/* ---- lettering ---- */
	.mark :global(path),
	.plate-mark :global(path),
	.die-mark :global(path) {
		fill: none;
		stroke-linecap: round;
		stroke-linejoin: round;
	}
	.mark :global(path) {
		stroke: #e4e5e9;
		stroke-width: 1.15;
	}
	/* the red L of the PULSE wordmark */
	.mark :global(path:nth-child(3)) {
		stroke: #ff3b4f;
	}
	.plate-mark :global(path) {
		stroke: #d8243a;
		stroke-width: 0.85;
	}
	.die-mark :global(path) {
		stroke: var(--text-hi);
		stroke-width: 0.8;
	}
	/* ---- front ---- */
	.brkt-slot {
		stroke: #3c3c43;
		stroke-width: 2.5;
		stroke-linecap: round;
	}
	.bp {
		stroke: #121215;
		stroke-width: 5;
		stroke-linecap: round;
	}
	.body {
		stroke: #6a6b72;
		stroke-width: 1;
	}
	.panel {
		stroke: #121214;
		stroke-width: 1.5;
	}
	.hi {
		fill: none;
		stroke: rgb(255 255 255 / 0.28);
		stroke-width: 1;
	}
	.hi.soft {
		stroke: rgb(255 255 255 / 0.1);
	}
	.lo {
		fill: none;
		stroke: rgb(0 0 0 / 0.55);
		stroke-width: 2;
	}
	.red {
		fill: none;
		stroke: #e3283e;
		stroke-width: 2.2;
		stroke-linejoin: round;
		filter: drop-shadow(0 0 2px rgb(255 59 79 / 0.6));
	}
	.slot {
		stroke: #121214;
		stroke-width: 4;
		stroke-linecap: round;
	}
	.ring-shadow {
		fill: none;
		stroke: rgb(0 0 0 / 0.45);
		stroke-width: 5;
	}
	.ring {
		fill: #0c0c0e;
		stroke-width: 3.2;
	}
	.rotor {
		transform-box: view-box;
		transform: rotate(calc(var(--spin, 0) * 1turn));
	}
	.blades {
		opacity: calc(1 - var(--rpm, 0) * 0.65);
	}
	.blade {
		stroke: rgb(0 0 0 / 0.5);
		stroke-width: 0.8;
	}
	.blade-hi {
		fill: none;
		stroke: rgb(255 255 255 / 0.2);
		stroke-width: 1.1;
		stroke-linecap: round;
	}
	.smear {
		opacity: var(--rpm, 0);
	}
	.hub {
		stroke: #55565d;
		stroke-width: 1.2;
	}
	.hub-ring {
		fill: none;
		stroke: #e3283e;
		stroke-width: 1.8;
	}
	.gloss {
		fill: none;
		stroke: rgb(255 255 255 / 0.22);
		stroke-width: 2;
		stroke-linecap: round;
	}
	/* ---- top and end faces ---- */
	.tfin {
		stroke: rgb(237 234 227 / 0.16);
		stroke-width: 1.4;
	}
	.plate {
		stroke: rgb(0 0 0 / 0.4);
	}
	.sock rect:first-child {
		fill: #0a0a0c;
		stroke: #48484f;
	}
	.sock.on rect:first-child {
		stroke: #ff6b7a;
		filter: drop-shadow(0 0 4px rgb(255 59 79 / 0.9));
		transition:
			stroke 0.3s,
			filter 0.3s;
	}
	.hole {
		fill: #2e2e35;
	}
	.latch {
		fill: #2a2a30;
	}
	.efin {
		stroke: rgb(237 234 227 / 0.14);
		stroke-width: 1.6;
	}
	.epipe {
		fill: #2a2b30;
		stroke: #8d8e95;
		stroke-width: 1.5;
	}
	/* ---- x-ray: bone and steel, red where the scan has read ---- */
	.shell {
		fill: #060607;
		stroke: rgb(237 234 227 / 0.3);
		stroke-width: 1;
	}
	.fin {
		stroke: rgb(237 234 227 / 0.16);
		stroke-width: 1;
	}
	.pcb {
		fill: #0a0c0c;
		stroke: rgb(237 234 227 / 0.5);
		stroke-width: 1.2;
	}
	.pipe {
		fill: none;
		stroke: rgb(237 234 227 / 0.12);
		stroke-width: 7;
		stroke-linecap: round;
	}
	.ln {
		fill: none;
		stroke: rgb(237 234 227 / 0.4);
	}
	.ln.faint {
		stroke: rgb(237 234 227 / 0.22);
	}
	.ln.strong {
		stroke: rgb(237 234 227 / 0.7);
	}
	.trace {
		fill: none;
		stroke: rgb(169 199 216 / 0.3);
		stroke-width: 1.2;
		transition:
			stroke 0.4s,
			stroke-width 0.4s;
	}
	.trace.lane {
		stroke: rgb(237 234 227 / 0.14);
	}
	.mem,
	.die,
	.choke,
	.sock-x {
		fill: rgb(237 234 227 / 0.07);
		stroke: var(--text-hi);
		stroke-width: 1.2;
		transition:
			fill 0.4s,
			stroke 0.4s;
	}
	.die {
		stroke-width: 1.4;
	}
	.choke {
		stroke: rgb(237 234 227 / 0.6);
	}
	.halo {
		opacity: 0;
		transition: opacity 0.5s;
	}
	.mem.on,
	.die.on,
	.choke.on,
	.sock-x.on {
		fill: rgb(255 59 79 / 0.3);
		stroke: #ff6b7a;
	}
	/* chips light up one by one around the die */
	.mem.on {
		transition-delay: calc(var(--i) * 45ms);
	}
	/* the model's share of the 24 GB, filling chip after chip */
	.mfill {
		fill: rgb(94 200 194 / 0.75);
		transform-box: fill-box;
		transform-origin: 0 50%;
		transform: scaleX(var(--f));
		transition: transform 0.25s linear calc(var(--i) * 40ms);
	}
	/* data and current: dashes racing along the traces (pathLength 20) */
	.trace.trace.flow {
		stroke: #ff8a96;
		stroke-width: 2;
		stroke-dasharray: 1.4 2.6;
		animation: race 0.32s linear infinite;
	}
	.trace.trace.flow.rev {
		animation-direction: reverse;
	}
	@keyframes race {
		to {
			stroke-dashoffset: -4;
		}
	}
	.trace.on {
		stroke: rgb(255 59 79 / 0.9);
		stroke-width: 1.8;
	}
	.halo.on {
		opacity: 1;
	}
	@media (prefers-reduced-motion: reduce) {
		.trace.flow {
			animation: none;
		}
		.mfill {
			transition: none;
		}
		.trace,
		.mem,
		.die,
		.choke,
		.sock-x,
		.halo {
			transition: none;
		}
	}
</style>
