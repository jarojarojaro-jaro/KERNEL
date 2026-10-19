<script lang="ts">
	/**
	 * Our lab card, Sapphire PULSE RX 7900 XTX, seen from the fan side on an 800×330 grid, drawn after
	 * Sapphire's dimension drawing and product photos (313 × 121 mm shroud, fans at 19.5 / 50 / 80.5%
	 * of the length, 78% of its height): gunmetal shroud with the PULSE red pinstripes stepping down
	 * between the first two fans, nine-blade fans with the red-ringed PULSE hub, corner vent slots,
	 * backplate edge along the top, three 8-pin sockets at the tail, steel bracket (shorter than the
	 * shroud) and the PCIe x16 fingers with their key. `part="xray"` draws the board on the same grid
	 * (Navi 31: one GCD + six MCDs, 12 GDDR6 packages, two per MCD, VRM, outputs, fin stack past the
	 * PCB end), so the scan scene can lay it exactly under the shroud. `lit` turns the parts the scan
	 * has read red. Rotors turn by `--spin` (turns) and blur by `--rpm` (0..1), both set by the caller.
	 */
	let { part, lit = {} }: { part: 'shroud' | 'xray'; lit?: { mem?: boolean; gpu?: boolean; bus?: boolean; pwr?: boolean } } = $props();
	const uid = $props.id();

	const FANS = [170, 403, 636];
	const FY = 157;
	const pt = (cx: number, r: number, deg: number) => {
		const a = (deg * Math.PI) / 180;
		return `${(cx + r * Math.cos(a)).toFixed(1)} ${(FY + r * Math.sin(a)).toFixed(1)}`;
	};
	/** A wide swept PULSE blade: leading edge hub → tip, along the tip ring, trailing edge back. */
	const blade = (cx: number, a: number) =>
		`M${pt(cx, 33, a)} Q${pt(cx, 74, a + 4)} ${pt(cx, 104, a + 36)} A104 104 0 0 0 ${pt(cx, 104, a + 8)} Q${pt(cx, 68, a - 16)} ${pt(cx, 33, a - 28)}Z`;
	const BLADES = Array.from({ length: 9 }, (_, i) => i * 40);
	/** Three 8-pin sockets at the tail of the top edge: x of each, 36 wide. */
	const PINS = [586, 628, 670];
	const holes = Array.from({ length: 8 }, (_, i) => ({ dx: 5 + (i % 4) * 7.5, dy: i < 4 ? 6 : 12 }));
	/** PCIe x16: the short segment before the key, then the long run. */
	const fingers = [...Array.from({ length: 3 }, (_, i) => 101 + i * 6.6), ...Array.from({ length: 28 }, (_, i) => 131 + i * 7.3)];
	/** Shroud outline (x 22..784, y 16..298) with the slight chamfer at the tail bottom. */
	const SHROUD = 'M22 24Q22 16 30 16H776Q784 16 784 24V286L772 298H30Q22 298 22 290Z';
	/** Vent slots in the shroud corners beside the fans. */
	const SLOTS = [
		[40, 58],
		[40, 256],
		[286, 58],
		[286, 256],
		[766, 58],
		[766, 256]
	];

	// x-ray: 12 GDDR6 packages, each pair wired to one of the six MCDs around the GCD
	const MCD = [
		{ x: 232, y: 112 },
		{ x: 232, y: 147 },
		{ x: 232, y: 182 },
		{ x: 330, y: 112 },
		{ x: 330, y: 147 },
		{ x: 330, y: 182 }
	];
	const mc = (i: number) => ({ x: MCD[i].x + 9, y: MCD[i].y + 13 });
	const MEM = [
		...[215, 255].map((x) => ({ x, y: 48, w: 30, h: 22, to: 0 })),
		...[295, 335].map((x) => ({ x, y: 48, w: 30, h: 22, to: 3 })),
		...[215, 255].map((x) => ({ x, y: 250, w: 30, h: 22, to: 2 })),
		...[295, 335].map((x) => ({ x, y: 250, w: 30, h: 22, to: 5 })),
		...[120, 172].map((y) => ({ x: 172, y, w: 22, h: 30, to: 1 })),
		...[120, 172].map((y) => ({ x: 386, y, w: 22, h: 30, to: 4 }))
	];
	const bus = MEM.map((m) => {
		const c = { x: m.x + m.w / 2, y: m.y + m.h / 2 };
		const t = mc(m.to);
		return m.w > m.h ? `M${c.x} ${c.y} V${(c.y + t.y) / 2} H${t.x} V${t.y}` : `M${c.x} ${c.y} H${(c.x + t.x) / 2} V${t.y} H${t.x}`;
	});
	const chokes = Array.from({ length: 12 }, (_, i) => ({ x: 452 + (i % 6) * 28, y: i < 6 ? 98 : 202 }));
	const caps = Array.from({ length: 8 }, (_, i) => 456 + i * 24);
	const fins = Array.from({ length: 13 }, (_, i) => 708 + i * 6);
	const lanes = Array.from({ length: 6 }, (_, i) => `M${146 + i * 30} 300 V${284 - i * 4} H${226 + i * 4} V228`);
</script>

{#if part === 'shroud'}
	<svg viewBox="0 0 800 330" class="art" aria-hidden="true">
		<defs>
			<linearGradient id="{uid}-body" x1="0" y1="0" x2="0.25" y2="1">
				<stop offset="0" stop-color="#4a4b51" />
				<stop offset="0.35" stop-color="#36373c" />
				<stop offset="1" stop-color="#222327" />
			</linearGradient>
			<linearGradient id="{uid}-sheen" x1="0" y1="0" x2="1" y2="0">
				<stop offset="0" stop-color="#fff" stop-opacity="0" />
				<stop offset="0.45" stop-color="#fff" stop-opacity="0.07" />
				<stop offset="0.55" stop-color="#fff" stop-opacity="0" />
			</linearGradient>
			<linearGradient id="{uid}-brkt" x1="0" y1="0" x2="1" y2="0">
				<stop offset="0" stop-color="#6a6a72" />
				<stop offset="0.5" stop-color="#c2c2c9" />
				<stop offset="1" stop-color="#55555c" />
			</linearGradient>
			<linearGradient id="{uid}-bevel" x1="0" y1="0" x2="0" y2="1">
				<stop offset="0" stop-color="#121214" />
				<stop offset="1" stop-color="#6d6e75" />
			</linearGradient>
			<radialGradient id="{uid}-well">
				<stop offset="0.3" stop-color="#050506" />
				<stop offset="1" stop-color="#151518" />
			</radialGradient>
			<linearGradient id="{uid}-blade" x1="0" y1="0" x2="1" y2="1">
				<stop offset="0" stop-color="#3d3e45" />
				<stop offset="0.6" stop-color="#202126" />
				<stop offset="1" stop-color="#141418" />
			</linearGradient>
			<radialGradient id="{uid}-smear">
				<stop offset="0.3" stop-color="#3a3b42" stop-opacity="0.2" />
				<stop offset="0.75" stop-color="#4a4b53" stop-opacity="0.55" />
				<stop offset="1" stop-color="#2a2b31" stop-opacity="0.35" />
			</radialGradient>
			<radialGradient id="{uid}-hub" cx="0.4" cy="0.35">
				<stop offset="0" stop-color="#3a3b41" />
				<stop offset="1" stop-color="#0c0c0e" />
			</radialGradient>
			<linearGradient id="{uid}-gold" x1="0" y1="0" x2="0" y2="1">
				<stop offset="0" stop-color="#d8b56a" />
				<stop offset="1" stop-color="#7d6534" />
			</linearGradient>
		</defs>
		<!-- PCB edge and PCIe fingers under the shroud -->
		<rect x="92" y="296" width="250" height="8" fill="#0c1410" />
		{#each fingers as x (x)}<rect {x} y="302" width="4.6" height="20" rx="0.8" fill="url(#{uid}-gold)" />{/each}
		<!-- bracket, edge-on: shorter than the shroud, top tab, tongue -->
		<path d="M2 84H22V330H16V320H9V92H2Z" fill="url(#{uid}-brkt)" />
		<!-- 8-pin sockets at the tail, peeking over the top edge -->
		{#each PINS as x (x)}
			<g class="sock">
				<rect {x} y="1" width="36" height="20" rx="2" />
				<rect x={x + 13} y="0" width="10" height="3" rx="1" class="latch" />
				{#each holes as h (h.dx + h.dy * 10)}<rect x={x + h.dx} y={h.dy} width="4" height="4" rx="0.6" class="hole" />{/each}
			</g>
		{/each}
		<!-- backplate edge along the top and down the tail -->
		<path d="M26 13H780Q787 13 787 20V284" class="bp" />
		<!-- shroud -->
		<path d={SHROUD} fill="url(#{uid}-body)" class="body" />
		<path d={SHROUD} fill="url(#{uid}-sheen)" class="sheen" />
		<!-- panel grooves and the PULSE red pinstripes, stepping between fans 1 and 2 -->
		<path d="M24 70H276L290 56H782 M24 244H276L290 258H782" class="groove" />
		<path d="M24 66H274L288 52H782 M24 248H274L288 262H782" class="red" />
		<path d="M24 28H782 M24 286H770" class="seam" />
		{#each SLOTS as [x, y] (x * 1000 + y)}<path d="M{x - 4} {y + 4}L{x + 4} {y - 4}" class="slot" />{/each}
		<!-- three fans -->
		{#each FANS as cx (cx)}
			<circle {cx} cy={FY} r="117" class="ring" stroke="url(#{uid}-bevel)" />
			<circle {cx} cy={FY} r="112" fill="url(#{uid}-well)" />
			<g class="rotor" style="transform-origin: {cx}px {FY}px">
				<g class="blades">
					{#each BLADES as a (a)}<path d={blade(cx, a)} fill="url(#{uid}-blade)" class="blade" />{/each}
				</g>
				<circle {cx} cy={FY} r="33" fill="url(#{uid}-hub)" class="hub" />
				<circle {cx} cy={FY} r="27" class="hub-ring" />
				<text x={cx} y={FY - 9} class="hub-s" text-anchor="middle">SAPPHIRE</text>
				<text x={cx} y={FY + 5} class="hub-t" text-anchor="middle">PU<tspan class="hub-l">L</tspan>SE</text>
			</g>
			<!-- motion blur: the spinning blades read as a disc -->
			<circle {cx} cy={FY} r="106" fill="url(#{uid}-smear)" class="smear" />
		{/each}
	</svg>
{:else}
	<svg viewBox="0 0 800 330" class="art xray" aria-hidden="true">
		<defs>
			<pattern id="{uid}-grid" width="16" height="16" patternUnits="userSpaceOnUse">
				<path d="M16 0H0V16" fill="none" stroke="rgb(237 234 227 / 0.05)" />
			</pattern>
			<radialGradient id="{uid}-die">
				<stop offset="0" stop-color="#ff3b4f" stop-opacity=".35" />
				<stop offset="1" stop-color="#ff3b4f" stop-opacity="0" />
			</radialGradient>
		</defs>
		<!-- the cooler past the PCB end: fin stack and heat pipes -->
		<path d={SHROUD} class="shell" />
		{#each fins as x (x)}<path d="M{x} 26V288" class="fin" />{/each}
		<!-- PCB -->
		<rect x="24" y="22" width="678" height="278" rx="6" class="pcb" />
		<rect x="24" y="22" width="678" height="278" rx="6" fill="url(#{uid}-grid)" />
		<path d="M290 96V60Q290 40 320 40H780 M290 224V262Q290 280 320 280H780 M358 132H780 M358 188H780" class="pipe" />
		<!-- bracket and display outputs -->
		<path d="M2 84H22V330H16V320H9V92H2Z" class="ln faint" />
		{#each [96, 148, 200, 252] as y (y)}<rect x="28" {y} width="26" height="42" rx="3" class="ln" />{/each}
		<!-- PCIe x16 fingers and lanes -->
		{#each fingers as x (x)}<rect {x} y="302" width="4.6" height="20" rx="0.8" class="ln faint" />{/each}
		{#each lanes as d (d)}<path {d} class="trace lane" />{/each}
		<!-- memory bus: two GDDR6 packages per MCD -->
		{#each bus as d (d)}<path {d} class="trace bus" class:on={lit.bus} />{/each}
		{#each MEM as m, i (i)}<rect x={m.x} y={m.y} width={m.w} height={m.h} rx="2" class="mem" class:on={lit.mem} />{/each}
		<text x="290" y="40" class="lbl" text-anchor="middle">GDDR6 × 12</text>
		<!-- Navi 31 package: GCD and six MCDs -->
		<circle cx="290" cy="160" r="96" fill="url(#{uid}-die)" class="halo" class:on={lit.gpu} />
		<rect x="222" y="92" width="136" height="136" rx="6" class="ln strong" />
		{#each MCD as d, i (i)}<rect x={d.x} y={d.y} width="18" height="26" rx="2" class="die mcd" class:on={lit.gpu} />{/each}
		<rect x="258" y="128" width="64" height="64" rx="3" class="die" class:on={lit.gpu} />
		<text x="290" y="157" class="die-l" text-anchor="middle">NAVI</text>
		<text x="290" y="172" class="die-l" text-anchor="middle">31</text>
		<!-- VRM: chokes, power stages, capacitors -->
		{#each chokes as k, i (i)}
			<rect x={k.x} y={k.y} width="21" height="21" rx="3" class="choke" class:on={lit.pwr} />
			<rect x={k.x + 3} y={k.y + (k.y < 150 ? 27 : -15)} width="15" height="9" rx="1" class="ln faint" />
		{/each}
		{#each caps as x (x)}<circle cx={x} cy="166" r="6" class="ln faint" />{/each}
		<text x="533" y="88" class="lbl" text-anchor="middle">VRM</text>
		<!-- 3 × 8-pin, wired to the VRM -->
		{#each PINS as x (x)}
			<path d="M{x + 18} 21V60H{x - 90}V98" class="trace pwr" class:on={lit.pwr} />
			<rect {x} y="1" width="36" height="20" rx="2" class="sock-x" class:on={lit.pwr} />
			{#each holes as h (h.dx + h.dy * 10)}<rect x={x + h.dx} y={h.dy} width="4" height="4" rx="0.6" class="ln faint" />{/each}
		{/each}
		<text x="646" y="36" class="lbl" text-anchor="middle">3 × 8-PIN</text>
		<text x="226" y="294" class="lbl" text-anchor="middle">PCIe ×16</text>
	</svg>
{/if}

<style>
	.art {
		display: block;
		width: 100%;
		height: 100%;
		overflow: visible;
	}
	/* ---- shroud ---- */
	.bp {
		fill: none;
		stroke: #1a1a1e;
		stroke-width: 5;
		stroke-linecap: round;
	}
	.sock rect:first-child {
		fill: #0b0b0d;
		stroke: #45454d;
	}
	.latch {
		fill: #2c2c33;
	}
	.hole {
		fill: #3a3a42;
	}
	.body {
		stroke: #5a5b62;
		stroke-width: 1.2;
	}
	/* the sheen follows the pointer tilt (set by the scene; 0 at rest) */
	.sheen {
		transform: translate3d(calc(var(--tx, 0) * 6%), 0, 0);
		transition: transform 0.6s cubic-bezier(0.22, 1, 0.36, 1);
	}
	.groove {
		fill: none;
		stroke: #17171a;
		stroke-width: 2;
	}
	.red {
		fill: none;
		stroke: #e3283e;
		stroke-width: 2;
		filter: drop-shadow(0 0 2px rgb(255 59 79 / 0.55));
	}
	.seam {
		fill: none;
		stroke: rgb(255 255 255 / 0.07);
		stroke-width: 1;
	}
	.slot {
		stroke: #121214;
		stroke-width: 3.5;
		stroke-linecap: round;
	}
	.ring {
		fill: #0c0c0e;
		stroke-width: 3;
	}
	.rotor {
		transform-box: view-box;
		transform: rotate(calc(var(--spin, 0) * 1turn));
	}
	.blades {
		opacity: calc(1 - var(--rpm, 0) * 0.65);
	}
	.blade {
		stroke: rgb(255 255 255 / 0.13);
		stroke-width: 0.8;
	}
	.smear {
		opacity: var(--rpm, 0);
		pointer-events: none;
	}
	.hub {
		stroke: #4a4b52;
		stroke-width: 1.2;
	}
	.hub-ring {
		fill: none;
		stroke: #e3283e;
		stroke-width: 1.8;
	}
	.hub-s {
		font-family: var(--font-mono);
		font-size: 3.6px;
		letter-spacing: 0.2em;
		fill: #9a9ba3;
	}
	.hub-t {
		font-family: var(--font-display);
		font-weight: 800;
		font-style: italic;
		font-size: 12px;
		letter-spacing: 0.04em;
		fill: #d9dade;
	}
	.hub-l {
		fill: #ff3b4f;
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
		fill: rgb(255 59 79 / 0.28);
		stroke: #ff6b7a;
	}
	.trace.on {
		stroke: rgb(255 59 79 / 0.85);
		stroke-width: 1.6;
	}
	.halo.on {
		opacity: 1;
	}
	.lbl {
		font-family: var(--font-mono);
		font-size: 9px;
		letter-spacing: 0.14em;
		fill: rgb(237 234 227 / 0.6);
	}
	.die-l {
		font-family: var(--font-mono);
		font-size: 11px;
		font-weight: 600;
		letter-spacing: 0.12em;
		fill: var(--text-hi);
	}
	@media (prefers-reduced-motion: reduce) {
		.sheen,
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
