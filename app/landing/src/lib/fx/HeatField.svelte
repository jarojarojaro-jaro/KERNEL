<script lang="ts">
	/**
	 * Animated background: a dim ember field with speed streaks flowing left → right, coloured by the
	 * heat ramp, with a warm light that follows the cursor. One fragment shader on a half-resolution
	 * canvas (devicePixelRatio capped at 1.5, then ×0.5), drawn at ≤ 30 fps. It starts only once the
	 * page is idle after load (≥ 1.2 s), renders only while on screen and the tab is visible, and
	 * under reduced motion draws one still frame. On software GL (SwiftShader, llvmpipe) or without
	 * WebGL it never starts the shader: a static CSS ember field with composited CSS streaks stays.
	 */
	import { onMount } from 'svelte';
	import { visible } from './actions';
	import { onFrame, reducedMotion, whenIdle } from './motion';

	let {
		heat = 0.6,
		/** 0..1: speed streaks get denser and brighter (the hero's redline flare). Eased, never jumps. */
		boost = 0,
		class: cls = ''
	}: { heat?: number; boost?: number; class?: string } = $props();

	let canvas: HTMLCanvasElement | undefined = $state();
	let ok = $state(false);
	let soft = $state(false);
	let onScreen = $state(true);

	const VERT = `attribute vec2 p;void main(){gl_Position=vec4(p,0.,1.);}`;
	const FRAG = `precision mediump float;
uniform vec2 r;uniform float t;uniform vec2 m;uniform float h;uniform float b;
float hash(vec2 p){p=fract(p*vec2(123.34,456.21));p+=dot(p,p+45.32);return fract(p.x*p.y);}
float noise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);
 return mix(mix(hash(i),hash(i+vec2(1,0)),f.x),mix(hash(i+vec2(0,1)),hash(i+vec2(1,1)),f.x),f.y);}
float fbm(vec2 p){float v=0.,a=.5;for(int i=0;i<4;i++){v+=a*noise(p);p=p*2.03+vec2(1.7,9.2);a*=.5;}return v;}
vec3 ramp(float x){x=clamp(x,0.,1.);
 vec3 c0=vec3(.118,.204,.282),c1=vec3(.478,.18,.122),c2=vec3(.886,.251,.11),c3=vec3(1.,.478,.102),c4=vec3(1.,.757,.353),c5=vec3(1.,.953,.839);
 if(x<.2)return mix(c0,c1,x/.2);if(x<.4)return mix(c1,c2,(x-.2)/.2);if(x<.6)return mix(c2,c3,(x-.4)/.2);if(x<.8)return mix(c3,c4,(x-.6)/.2);return mix(c4,c5,(x-.8)/.2);}
void main(){
 vec2 uv=gl_FragCoord.xy/r;vec2 q=uv;q.x*=r.x/r.y;
 float flow=t*.06;
 vec2 w=vec2(fbm(q*1.6+vec2(-flow*2.,0.)),fbm(q*1.6+vec2(5.2,1.3)-flow));
 float e=fbm(q*2.2+w*1.4+vec2(-flow*3.,0.));
 float band=smoothstep(.95,.0,abs(uv.y-.18)*2.2);
 float ember=pow(e,2.6)*band;
 float s=noise(vec2(q.x*1.2-t*.9,uv.y*90.));s=smoothstep(.78-.14*b,1.,s)*smoothstep(.0,.6,uv.y)*smoothstep(1.,.35,uv.y);
 float streak=s*.55*(1.+1.8*b)*smoothstep(.15,.9,fbm(vec2(q.x*.8-t*.3,uv.y*6.)));
 vec2 mm=m;mm.x*=r.x/r.y;float d=length(q-mm);float glow=exp(-d*d*7.)*.55;
 float k=(ember*1.35+streak*.9)*h+glow*.35;
 vec3 col=ramp(k*1.15)*k;
 col+=vec3(.012,.01,.009);
 float vig=smoothstep(1.25,.25,length((uv-.5)*vec2(1.1,1.4)));
 gl_FragColor=vec4(col*vig,1.);}`;

	/** Software GL (SwiftShader, llvmpipe, …) renders the shader on the CPU: a perf trap, use the CSS field. */
	function softwareGL(gl: WebGLRenderingContext): boolean {
		const ext = gl.getExtension('WEBGL_debug_renderer_info');
		const name = String(ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER));
		return /swiftshader|llvmpipe|software|softpipe|basic render/i.test(name);
	}

	onMount(() => {
		let cleanup: (() => void) | undefined;
		// GL setup and the render loop wait until the page is idle (≥ 1.2 s): never during hydration/LCP.
		const cancel = whenIdle(() => {
			cleanup = start();
		}, 1200);
		return () => {
			cancel();
			cleanup?.();
		};
	});

	function start(): (() => void) | undefined {
		if (!canvas) return;
		const gl = canvas.getContext('webgl', { antialias: false, alpha: false, depth: false, stencil: false, powerPreference: 'low-power', preserveDrawingBuffer: false });
		if (!gl) {
			soft = true;
			return;
		}
		if (softwareGL(gl)) {
			gl.getExtension('WEBGL_lose_context')?.loseContext();
			soft = true;
			return;
		}
		const sh = (type: number, src: string) => {
			const s = gl.createShader(type)!;
			gl.shaderSource(s, src);
			gl.compileShader(s);
			return gl.getShaderParameter(s, gl.COMPILE_STATUS) ? s : null;
		};
		const vs = sh(gl.VERTEX_SHADER, VERT);
		const fs = sh(gl.FRAGMENT_SHADER, FRAG);
		if (!vs || !fs) return;
		const prog = gl.createProgram()!;
		gl.attachShader(prog, vs);
		gl.attachShader(prog, fs);
		gl.linkProgram(prog);
		if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) return;
		gl.useProgram(prog);
		const buf = gl.createBuffer();
		gl.bindBuffer(gl.ARRAY_BUFFER, buf);
		gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
		const loc = gl.getAttribLocation(prog, 'p');
		gl.enableVertexAttribArray(loc);
		gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
		const uR = gl.getUniformLocation(prog, 'r');
		const uT = gl.getUniformLocation(prog, 't');
		const uM = gl.getUniformLocation(prog, 'm');
		const uH = gl.getUniformLocation(prog, 'h');
		const uB = gl.getUniformLocation(prog, 'b');

		const scale = 0.5 * Math.min(devicePixelRatio || 1, 1.5);
		const resize = () => {
			if (!canvas) return;
			const w = Math.max(1, Math.round(canvas.clientWidth * scale));
			const hgt = Math.max(1, Math.round(canvas.clientHeight * scale));
			if (canvas.width !== w || canvas.height !== hgt) {
				canvas.width = w;
				canvas.height = hgt;
				gl.viewport(0, 0, w, hgt);
			}
		};
		const ro = new ResizeObserver(resize);
		ro.observe(canvas);
		resize();

		// Cursor light: target in uv space (y up), eased toward it.
		const mouse = { x: 0.72, y: 0.3, tx: 0.72, ty: 0.3 };
		const move = (e: PointerEvent) => {
			if (!canvas) return;
			const r = canvas.getBoundingClientRect();
			mouse.tx = (e.clientX - r.left) / r.width;
			mouse.ty = 1 - (e.clientY - r.top) / r.height;
		};
		addEventListener('pointermove', move, { passive: true });

		let time = 7.3;
		let hs = heat;
		let bs = boost;
		const draw = () => {
			gl.uniform2f(uR, canvas!.width, canvas!.height);
			gl.uniform1f(uT, time);
			gl.uniform2f(uM, mouse.x, mouse.y);
			gl.uniform1f(uH, hs);
			gl.uniform1f(uB, bs);
			gl.drawArrays(gl.TRIANGLES, 0, 3);
		};
		ok = true;
		if (reducedMotion()) {
			draw();
			return () => {
				ro.disconnect();
				removeEventListener('pointermove', move);
			};
		}
		// 30 fps is plenty for slow embers and streaks, and halves the GPU/CPU cost.
		let acc = 0;
		const stop = onFrame((dt) => {
			if (!onScreen) return;
			time += dt;
			mouse.x += (mouse.tx - mouse.x) * Math.min(1, dt * 3);
			mouse.y += (mouse.ty - mouse.y) * Math.min(1, dt * 3);
			hs += (heat - hs) * Math.min(1, dt * 1.5);
			bs += (boost - bs) * Math.min(1, dt * (boost > bs ? 4 : 1.2));
			acc += dt;
			if (acc < 1 / 30) return;
			acc = 0;
			draw();
		});
		return () => {
			stop();
			ro.disconnect();
			removeEventListener('pointermove', move);
			gl.getExtension('WEBGL_lose_context')?.loseContext();
		};
	}
</script>

<div class="heatfield {cls}" class:soft class:off={!onScreen} class:boost={boost > 0.5} style="--heat:{heat}" aria-hidden="true" use:visible={(v) => (onScreen = v)}>
	<canvas bind:this={canvas} class:ok></canvas>
	{#if soft}<div class="streak-frame"><div class="streaks"></div></div>{/if}
</div>

<style>
	.heatfield {
		position: absolute;
		inset: 0;
		overflow: hidden;
		pointer-events: none;
		/* static fallback: the same ember band, painted before WebGL starts (and instead of it) */
		background:
			radial-gradient(60% 45% at 30% 88%, rgb(226 64 28 / 0.22), transparent 70%),
			radial-gradient(45% 35% at 72% 92%, rgb(255 122 26 / 0.16), transparent 70%),
			radial-gradient(80% 60% at 50% 110%, rgb(122 46 31 / 0.35), transparent 70%),
			var(--bg-0);
	}
	canvas {
		width: 100%;
		height: 100%;
		display: block;
		opacity: 0;
		transition: opacity 1.2s var(--ease-out);
	}
	canvas.ok {
		opacity: 1;
	}
	/* CSS field for software GL: a few composited speed streaks; they run hotter while `boost` is on */
	/* static frame for the moving streaks: a parent (e.g. the hero) can mask it without the mask
	 * travelling with the streaks */
	.streak-frame {
		position: absolute;
		inset: 0;
		overflow: hidden;
		pointer-events: none;
	}
	.streaks {
		position: absolute;
		inset: 30% -50% 0 -50%;
		background:
			repeating-linear-gradient(180deg, transparent 0 37px, rgb(255 122 26 / 0.22) 37px 38px, transparent 38px 71px),
			repeating-linear-gradient(180deg, transparent 0 53px, rgb(255 193 90 / 0.14) 53px 54px, transparent 54px 97px);
		mask-image: linear-gradient(90deg, transparent, #000 30%, #000 70%, transparent), linear-gradient(180deg, transparent, #000 40%, #000 80%, transparent);
		mask-composite: intersect;
		opacity: calc(0.35 + 0.5 * var(--heat));
		transition: opacity 0.8s;
	}
	.soft.boost .streaks {
		opacity: 1;
		filter: brightness(1.6);
	}
	@media (prefers-reduced-motion: no-preference) {
		.streaks {
			animation: streak 6s linear infinite;
		}
		.soft.boost .streaks {
			animation-duration: 2.2s;
		}
	}
	.off .streaks {
		animation-play-state: paused;
	}
	@keyframes streak {
		from {
			transform: translate3d(-25%, 0, 0);
		}
		to {
			transform: translate3d(25%, 0, 0);
		}
	}
</style>
