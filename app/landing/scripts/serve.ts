/**
 * Local preview of the static build with what a real static host does: gzip, long-lived caching
 * for hashed assets, `<dir>/index.html` resolution. Usage: `bun scripts/serve.ts [port] [host]`
 * (default 18433, 127.0.0.1). Pass the LAN address (e.g. 192.168.10.230) to open it from another machine on the
 * home network; this is not a deployment.
 */
import { existsSync, statSync } from 'node:fs';
import { extname, join, normalize, resolve } from 'node:path';

const root = resolve(import.meta.dir, '../build');
const port = Number(process.argv[2] ?? 18433);
const hostname = process.argv[3] ?? '127.0.0.1';
const TYPES: Record<string, string> = {
	'.html': 'text/html; charset=utf-8',
	'.js': 'text/javascript; charset=utf-8',
	'.css': 'text/css; charset=utf-8',
	'.json': 'application/json; charset=utf-8',
	'.svg': 'image/svg+xml',
	'.woff2': 'font/woff2',
	'.avif': 'image/avif',
	'.webp': 'image/webp',
	'.txt': 'text/plain; charset=utf-8',
	'.sh': 'text/plain; charset=utf-8',
	'.ps1': 'text/plain; charset=utf-8'
};
const COMPRESSIBLE = new Set(['.html', '.js', '.css', '.json', '.svg', '.txt', '.sh', '.ps1']);

Bun.serve({
	hostname,
	port,
	async fetch(req) {
		const url = new URL(req.url);
		let path = normalize(join(root, decodeURIComponent(url.pathname)));
		if (!path.startsWith(root)) return new Response('Forbidden', { status: 403 });
		if (existsSync(path) && statSync(path).isDirectory()) {
			if (!url.pathname.endsWith('/')) return Response.redirect(`${url.pathname}/${url.search}`, 308);
			path = join(path, 'index.html');
		}
		if (!existsSync(path)) return new Response('Not found', { status: 404 });
		const ext = extname(path);
		const headers: Record<string, string> = {
			'content-type': TYPES[ext] ?? 'application/octet-stream',
			'cache-control': url.pathname.startsWith('/_app/immutable/') || url.pathname.startsWith('/fonts/') ? 'public, max-age=31536000, immutable' : 'no-cache',
			'x-content-type-options': 'nosniff',
			'referrer-policy': 'strict-origin-when-cross-origin'
		};
		const body = new Uint8Array(await Bun.file(path).arrayBuffer());
		if (COMPRESSIBLE.has(ext) && /\bgzip\b/.test(req.headers.get('accept-encoding') ?? '')) {
			headers['content-encoding'] = 'gzip';
			headers['vary'] = 'accept-encoding';
			return new Response(Bun.gzipSync(body), { headers });
		}
		return new Response(body, { headers });
	}
});
console.log(`serving ${root} on http://${hostname}:${port}/`);
