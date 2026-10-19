<script lang="ts">
	/**
	 * Our lab card, Sapphire PULSE RX 7900 XTX, seen from the fan side on an 800×330 grid: steel
	 * bracket, three fans in a black shroud with red accents, backplate edge along the top, three 8-pin
	 * sockets in the top notch, PCIe x16 fingers under the board. `part="xray"` draws the board on the
	 * same grid (Navi 31: one GCD + six MCDs, 12 GDDR6 packages, two per MCD, VRM, outputs, heatsink
	 * past the PCB end), so the scan scene can lay it exactly under the shroud. `lit` turns the parts
	 * the scan has read red. Rotors turn by `--spin` (turns, set by the caller).
	 */
	let { part, lit = {} }: { part: 'shroud' | 'xray'; lit?: { mem?: boolean; gpu?: boolean; bus?: boolean; pwr?: boolean } } = $props();
	const uid = $props.id();

	const FANS = [160, 403, 646];
	const FY = 160;
	const pt = (cx: number, r: number, deg: number) => {
		const a = (deg * Math.PI) / 180;
		return `${(cx + r * Math.cos(a)).toFixed(1)} ${(FY + r * Math.sin(a)).toFixed(1)}`;
	};
	/** Swept blade from the hub to the tip ring (11 per rotor). */
	const blade = (cx: number, a: number) =>
		`M${pt(cx, 27, a - 6)} Q${pt(cx, 66, a + 4)} ${pt(cx, 97, a + 25)} L${pt(cx, 97, a + 3)} Q${pt(cx, 60, a - 12)} ${pt(cx, 27, a - 28)}Z`;
	const BLADES = Array.from({ length: 11 }, (_, i) => (i * 360) / 11);
	/** 8-pin sockets in the top notch: x of each, 36 wide. */
	const PINS = [468, 510, 552];
	const holes = Array.from({ length: 8 }, (_, i) => ({ dx: 5 + (i % 4) * 7.5, dy: i < 4 ? 9 : 15 }));
	/** PCIe x16: a short key segment, then the long run. */
	const fingers = [...Array.from({ length: 3 }, (_, i) => 113 + i * 7.6), ...Array.from({ length: 25 }, (_, i) => 146 + i * 7.4)];

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
	const chokes = Array.from({ length: 12 }, (_, i) => ({ x: 440 + (i % 6) * 27, y: i < 6 ? 98 : 202 }));
	const caps = Array.from({ length: 7 }, (_, i) => 446 + i * 24);
	const fins = Array.from({ length: 28 }, (_, i) => 616 + i * 6);
	const lanes = Array.from({ length: 6 }, (_, i) => `M${158 + i * 26} 300 V${284 - i * 4} H${226 + i * 4} V228`);
</script>

{#if part === 'shroud'}
	<svg viewBox="0 0 800 330" class="art" aria-hidden="true">
		<defs>
			<linearGradient id="{uid}-body" x1="0" y1="0" x2="0" y2="1">
				<stop offset="0" stop-color="#202026" />
				<stop offset="0.45" stop-color="#131317" />
				<stop offset="1" stop-color="#09090b" />
			</linearGradient>
			<linearGradient id="{uid}-steel" x1="0" y1="0" x2="0" y2="1">
				<stop offset="0" stop-color="#8a8a93" />
				<stop offset="1" stop-color="#34343b" />
			</linearGradient>
			<linearGradient id="{uid}-brkt" x1="0" y1="0" x2="1" y2="0">
				<stop offset="0" stop-color="#5a5a62" />
				<stop offset="0.5" stop-color="#a3a3ab" />
				<stop offset="1" stop-color="#4a4a51" />
			</linearGradient>
			<radialGradient id="{uid}-well">
				<stop offset="0.25" stop-color="#030304" />
				<stop offset="1" stop-color="#0f0f13" />
			</radialGradient>
			<linearGradient id="{uid}-blade" x1="0" y1="0" x2="1" y2="1">
				<stop offset="0" stop-color="#34343c" />
				<stop offset="1" stop-color="#16161a" />
			</linearGradient>
			<linearGradient id="{uid}-gold" x1="0" y1="0" x2="0" y2="1">
				<stop offset="0" stop-color="#b79a5c" />
				<stop offset="1" stop-color="#6d5a32" />
			</linearGradient>
		</defs>
		<!-- PCB edge and PCIe fingers under the shroud -->
		<rect x="96" y="290" width="512" height="12" fill="#0d1311" />
		{#each fingers as x (x)}<rect {x} y="301" width="5" height="19" rx="1" fill="url(#{uid}-gold)" />{/each}
		<!-- bracket, seen edge-on: plate, top tab, tongue -->
		<path d="M1 6H24V316H19V328H12V316H8V20H1Z" fill="url(#{uid}-brkt)" />
		<!-- backplate edge along the top and down the tail -->
		<path d="M28 14H774Q786 14 786 26V286" class="bp" />
		<!-- 8-pin sockets in the top notch -->
		{#each PINS as x (x)}
			<g class="sock">
				<rect {x} y="3" width="36" height="27" rx="2" />
				<rect x={x + 13} y="0" width="10" height="5" rx="1" class="latch" />
				{#each holes as h (h.dx + h.dy * 10)}<rect x={x + h.dx} y={h.dy - 3} width="4" height="4" rx="0.6" class="hole" />{/each}
			</g>
		{/each}
		<!-- shroud: notch over the sockets, chamfered tail corner -->
		<path d="M22 32Q22 20 34 20H458L466 30H594L602 20H772Q784 20 784 32V276L766 298H34Q22 298 22 286Z" fill="url(#{uid}-body)" class="body" />
		<!-- facets and the brushed lower lip -->
		<path d="M22 268H784V276L766 298H34Q22 298 22 286Z" class="lip" />
		<path d="M272 24L294 24L286 52Z M515 24L537 24L529 52Z M272 296L294 296L286 268Z M515 296L537 296L529 268Z" class="facet" />
		<!-- red accents (Radeon) -->
		<path d="M30 272H118 M202 272H318 M488 272H560" class="red" />
		<path d="M281.5 132V188 M524.5 132V188" class="red thin" />
		<!-- three fans -->
		{#each FANS as cx (cx)}
			<circle {cx} cy={FY} r="111" class="ring" />
			<circle {cx} cy={FY} r="106" fill="url(#{uid}-well)" />
			<g class="rotor">
				{#each BLADES as a (a)}<path d={blade(cx, a)} fill="url(#{uid}-blade)" class="blade" />{/each}
				<circle {cx} cy={FY} r="98" class="tip" />
				<circle {cx} cy={FY} r="27" class="hub" />
				<circle {cx} cy={FY} r="19" class="hub-in" />
				<path d="M{cx - 7} {FY + 4}L{cx} {FY - 8}L{cx + 7} {FY + 4}Z" class="gem" />
			</g>
		{/each}
		<!-- branding -->
		<text x="36" y="291" class="brand">PULSE</text>
		<text x="760" y="290" class="model" text-anchor="end">RADEON RX 7900 XTX</text>
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
		<path d="M22 32Q22 20 34 20H772Q784 20 784 32V276L766 298H34Q22 298 22 286Z" class="shell" />
		{#each fins as x (x)}<path d="M{x} 34V286" class="fin" />{/each}
		<!-- PCB -->
		<rect x="26" y="22" width="584" height="278" rx="6" class="pcb" />
		<rect x="26" y="22" width="584" height="278" rx="6" fill="url(#{uid}-grid)" />
		<path d="M290 96V60Q290 40 320 40H780 M290 224V262Q290 280 320 280H780 M358 132H780 M358 188H780" class="pipe" />
		<!-- bracket and display outputs -->
		<path d="M1 6H24V316H19V328H12V316H8V20H1Z" class="ln faint" />
		{#each [36, 92, 148, 204] as y (y)}<rect x="30" {y} width="28" height="46" rx="3" class="ln" />{/each}
		<!-- PCIe x16 fingers and lanes -->
		{#each fingers as x (x)}<rect {x} y="301" width="5" height="19" rx="1" class="ln faint" />{/each}
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
		<text x="518" y="90" class="lbl" text-anchor="middle">VRM</text>
		<!-- 3 × 8-pin, wired to the VRM -->
		{#each PINS as x (x)}
			<path d="M{x + 18} 25V{98}" class="trace pwr" class:on={lit.pwr} />
			<rect {x} y="3" width="36" height="22" rx="2" class="sock-x" class:on={lit.pwr} />
			{#each holes as h (h.dx + h.dy * 10)}<rect x={x + h.dx} y={h.dy - 3} width="4" height="4" rx="0.6" class="ln faint" />{/each}
		{/each}
		<text x="528" y="62" class="lbl" text-anchor="middle">3 × 8-PIN</text>
		<text x="238" y="296" class="lbl" text-anchor="middle">PCIe ×16</text>
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
		stroke: #6d6d76;
		stroke-width: 4;
		stroke-linecap: round;
	}
	.sock rect:first-child {
		fill: #0b0b0d;
		stroke: #3c3c44;
	}
	.latch {
		fill: #26262c;
	}
	.hole {
		fill: #3a3a42;
	}
	.body {
		stroke: #34343c;
		stroke-width: 1.5;
	}
	.lip {
		fill: #1d1d22;
		stroke: #3a3a42;
		stroke-width: 1;
	}
	.facet {
		fill: #26262d;
	}
	.red {
		fill: none;
		stroke: #ff3b4f;
		stroke-width: 3;
		stroke-linecap: round;
		filter: drop-shadow(0 0 3px rgb(255 59 79 / 0.6));
	}
	.red.thin {
		stroke-width: 2;
	}
	.ring {
		fill: #070708;
		stroke: #3a3a43;
		stroke-width: 2.5;
	}
	.rotor {
		transform-box: fill-box;
		transform-origin: 50% 50%;
		transform: rotate(calc(var(--spin, 0) * 1turn));
	}
	.blade {
		stroke: rgb(255 255 255 / 0.1);
		stroke-width: 0.8;
	}
	.tip {
		fill: none;
		stroke: #2f2f37;
		stroke-width: 3;
	}
	.hub {
		fill: #141418;
		stroke: #45454e;
		stroke-width: 1.5;
	}
	.hub-in {
		fill: #0c0c0e;
		stroke: rgb(255 59 79 / 0.55);
		stroke-width: 1;
	}
	.gem {
		fill: #9a9aa3;
	}
	.brand {
		font-family: var(--font-display);
		font-weight: 800;
		font-style: italic;
		font-size: 15px;
		letter-spacing: 0.12em;
		fill: #e9e7e2;
	}
	.model {
		font-family: var(--font-mono);
		font-size: 9px;
		letter-spacing: 0.16em;
		fill: #8d8d96;
	}
	/* ---- x-ray: bone and steel, red where the scan has read ---- */
	.shell {
		fill: #060607;
		stroke: rgb(237 234 227 / 0.3);
		stroke-width: 1;
	}
	.fin {
		stroke: rgb(237 234 227 / 0.13);
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
	}
	.die {
		stroke-width: 1.4;
	}
	.choke {
		stroke: rgb(237 234 227 / 0.6);
	}
	.halo {
		opacity: 0;
	}
	.on {
		stroke: #ff3b4f;
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
</style>
