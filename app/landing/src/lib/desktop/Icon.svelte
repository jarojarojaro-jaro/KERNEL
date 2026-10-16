<script lang="ts" module>
	/** 24×24 stroke icons, 1.75 px, drawn for this prototype (no icon font, no external set). */
	const PATHS = {
		overview: 'M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z',
		wizard: 'M5 21V4M5 4h11l-2.5 4L16 12H5',
		chat: 'M4 5.5h16v10.5H10l-4.5 3.5V16H4z',
		computer: 'M7 7h10v10H7zM10 10h4v4h-4zM10 3v4M14 3v4M10 17v4M14 17v4M3 10h4M3 14h4M17 10h4M17 14h4',
		result: 'M5.6 18.4a9 9 0 1 1 12.8 0M12 14l4.2-4.2M12 14h.01',
		night: 'M19.5 14.6A7.5 7.5 0 0 1 9.4 4.5a7.5 7.5 0 1 0 10.1 10.1z',
		models: 'M12 3l8 4.5v9L12 21l-8-4.5v-9zM4 7.5l8 4.5 8-4.5M12 12v9',
		developers: 'M8.5 7L3.5 12l5 5M15.5 7l5 5-5 5M13.5 5l-3 14',
		sun: 'M12 8.5a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7zM12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5.3 5.3l1.4 1.4M17.3 17.3l1.4 1.4M5.3 18.7l1.4-1.4M17.3 6.7l1.4-1.4',
		moon: 'M19.5 14.6A7.5 7.5 0 0 1 9.4 4.5a7.5 7.5 0 1 0 10.1 10.1z',
		menu: 'M4 7h16M4 12h16M4 17h16',
		close: 'M6 6l12 12M18 6L6 18',
		copy: 'M9 9h11v11H9zM5 15H4V4h11v1',
		eye: 'M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12zM12 9.5a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5z',
		eyeOff: 'M3 3l18 18M10.6 5.6A9.6 9.6 0 0 1 12 5.5c6 0 9.5 6.5 9.5 6.5a17 17 0 0 1-2.9 3.7M6.6 6.7A16.6 16.6 0 0 0 2.5 12S6 18.5 12 18.5a9 9 0 0 0 4.5-1.2M9.9 9.9a2.5 2.5 0 0 0 3.5 3.5',
		refresh: 'M20 12a8 8 0 1 1-2.4-5.7M20 4v5h-5',
		download: 'M12 4v11M7 10.5l5 5 5-5M5 20h14',
		undo: 'M9 14L4 9l5-5M4 9h10.5a5.5 5.5 0 0 1 0 11H11',
		pause: 'M8 5v14M16 5v14',
		play: 'M7 4.5v15L19 12z',
		check: 'M4.5 12.5l5 5L19.5 7',
		alert: 'M12 3.5L2.5 20h19zM12 10v4.5M12 17.5h.01',
		send: 'M4 12l16-8-6 16-2.5-6.5z',
		plus: 'M12 5v14M5 12h14',
		arrowRight: 'M5 12h14M13 6l6 6-6 6',
		arrowLeft: 'M19 12H5M11 6l-6 6 6 6',
		thermo: 'M10 13.5V5a2 2 0 1 1 4 0v8.5a4 4 0 1 1-4 0z',
		bolt: 'M13 2.5L4.5 13.5H12L11 21.5l8.5-11H12z',
		fan: 'M12 12m-1.5 0a1.5 1.5 0 1 0 3 0 1.5 1.5 0 1 0-3 0M12 10.5C10 6 12 3 14.5 3.5c2.5.5 1.5 4.5-1 7M13.5 12c4.5 2 4.5 5.5 2 6.5-2.5.9-4-2.5-4.5-5M10.5 12.5C6 14 4 11.5 5 9.5c1-2 4.5-.5 5.5 2',
		window: 'M3.5 5.5h17v13h-17zM3.5 9h17',
		minimize: 'M6 12h12',
		maximize: 'M6.5 6.5h11v11h-11z',
		ext: 'M14 4h6v6M20 4l-9 9M18 14v6H4V6h6'
	} as const;
	export type IconName = keyof typeof PATHS;
</script>

<script lang="ts">
	let { name, size = 18 }: { name: IconName; size?: number } = $props();
</script>

<svg
	class="icon"
	width={size}
	height={size}
	viewBox="0 0 24 24"
	fill="none"
	stroke="currentColor"
	stroke-width="1.75"
	stroke-linecap="round"
	stroke-linejoin="round"
	aria-hidden="true"
	focusable="false"><path d={PATHS[name]} /></svg
>

<style>
	.icon {
		flex: none;
	}
</style>
