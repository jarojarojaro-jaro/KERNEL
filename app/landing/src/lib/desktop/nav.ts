import type { IconName } from './Icon.svelte';

export type ScreenKey = 'wizard' | 'chat' | 'computer' | 'result' | 'night' | 'models' | 'developers';

/** Every prototype screen, in sidebar order. The wizard is a first-run flow, so it is not in the sidebar. */
export const SCREENS: { key: ScreenKey; path: string; icon: IconName; sidebar: boolean }[] = [
	{ key: 'wizard', path: '/app/wizard', icon: 'wizard', sidebar: false },
	{ key: 'chat', path: '/app/chat', icon: 'chat', sidebar: true },
	{ key: 'computer', path: '/app/computer', icon: 'computer', sidebar: true },
	{ key: 'result', path: '/app/result', icon: 'result', sidebar: true },
	{ key: 'night', path: '/app/night', icon: 'night', sidebar: true },
	{ key: 'models', path: '/app/models', icon: 'models', sidebar: true },
	{ key: 'developers', path: '/app/developers', icon: 'developers', sidebar: true }
];
