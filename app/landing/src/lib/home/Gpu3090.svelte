<script lang="ts">
	/**
	 * X-ray of a GA102-class board, drawn on the same 640×300 grid as `$lib/cards/GpuArt.svelte`
	 * (shroud 24..612 × 26..232, PCB edge to y 262, PCIe fingers 96..346), so the scan scene can lay
	 * it exactly under the product render and reveal it behind the light bar. Bone and steel only:
	 * heat colour is reserved for speed.
	 */
	const mem = [
		...[0, 1, 2].map((i) => ({ x: 266 + i * 36, y: 50, w: 30, h: 20 })),
		...[0, 1, 2].map((i) => ({ x: 266 + i * 36, y: 186, w: 30, h: 20 })),
		...[0, 1, 2].map((i) => ({ x: 222, y: 90 + i * 28, w: 22, h: 22 })),
		...[0, 1, 2].map((i) => ({ x: 392, y: 90 + i * 28, w: 22, h: 22 }))
	];
	const vrm = Array.from({ length: 9 }, (_, i) => ({ x: 70 + (i % 3) * 32, y: 72 + Math.floor(i / 3) * 40 }));
	const vrm2 = Array.from({ length: 6 }, (_, i) => ({ x: 468 + (i % 2) * 32, y: 82 + Math.floor(i / 2) * 40 }));
	const fingers = Array.from({ length: 30 }, (_, i) => 99 + i * 8.2);
</script>

<svg viewBox="0 0 640 300" class="xray" aria-hidden="true">
	<defs>
		<radialGradient id="xr-die">
			<stop offset="0" stop-color="#fff3d6" stop-opacity=".35" />
			<stop offset="1" stop-color="#fff3d6" stop-opacity="0" />
		</radialGradient>
	</defs>
	<!-- bracket -->
	<rect x="2" y="14" width="18" height="250" rx="3" class="ln faint" />
	<!-- board -->
	<rect x="20" y="26" width="600" height="236" rx="16" class="pcb" />
	<!-- memory bus: die to every package -->
	{#each mem as m, i (i)}<path d="M318 128 L{m.x + m.w / 2} {m.y + m.h / 2}" class="trace" />{/each}
	<!-- PCIe lanes to the fingers -->
	{#each [0, 1, 2, 3, 4, 5, 6, 7] as i (i)}<path d="M{110 + i * 28} 262 V{236 - i * 3} H{272 + i * 6} V170" class="trace bus" />{/each}
	<!-- power stages -->
	{#each [...vrm, ...vrm2] as v, i (i)}<rect x={v.x} y={v.y} width="22" height="22" rx="2" class="ln" />{/each}
	<!-- 12 memory packages -->
	{#each mem as m, i (i)}<rect x={m.x} y={m.y} width={m.w} height={m.h} rx="2" class="mem" />{/each}
	<!-- GPU -->
	<circle cx="318" cy="128" r="80" fill="url(#xr-die)" />
	<rect x="268" y="78" width="100" height="100" rx="6" class="ln strong" />
	<rect x="284" y="94" width="68" height="68" rx="3" class="die" />
	<text x="318" y="132" class="die-label" text-anchor="middle">GA102</text>
	<!-- 12-pin power socket and PCIe fingers -->
	<rect x="548" y="10" width="48" height="16" rx="2" class="ln strong" />
	{#each fingers as x (x)}<rect {x} y="264" width="5" height="12" class="ln faint" />{/each}
</svg>

<style>
	.xray {
		display: block;
		width: 100%;
		height: 100%;
		overflow: visible;
	}
	.pcb {
		fill: rgb(12 13 15 / 0.96);
		stroke: rgb(237 234 227 / 0.45);
		stroke-width: 1.2;
	}
	.ln {
		fill: none;
		stroke: rgb(237 234 227 / 0.38);
	}
	.ln.faint {
		stroke: rgb(237 234 227 / 0.22);
	}
	.ln.strong {
		stroke: rgb(237 234 227 / 0.7);
	}
	.trace {
		stroke: rgb(169 199 216 / 0.35);
		stroke-width: 1;
		fill: none;
	}
	.trace.bus {
		stroke: rgb(237 234 227 / 0.16);
	}
	.mem {
		fill: rgb(237 234 227 / 0.08);
		stroke: var(--text-hi);
		stroke-width: 1.2;
	}
	.die {
		fill: rgb(237 234 227 / 0.1);
		stroke: var(--text-hi);
		stroke-width: 1.4;
	}
	.die-label {
		font-family: var(--font-mono);
		font-size: 11px;
		letter-spacing: 0.1em;
		fill: var(--text-hi);
	}
</style>
