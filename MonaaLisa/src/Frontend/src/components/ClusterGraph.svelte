<!--
  ClusterGraph.svelte
  Smooth cluster visualization with pan/zoom.
  Used for both top-level category and subcategory views.
  Clusters are rendered as glowing territories with particle fill.
-->
<script lang="ts">
  import { onMount, createEventDispatcher } from 'svelte';
  import type { ClusterNode } from '$lib/types/paper';
  import { EdgeAnimator } from './edgeAnimation';

  /** Array of clusters to visualise. */
  export let clusters: ClusterNode[] = [];
  /** If set, subcategory colours are derived from this parent colour. */
  export let parentColor: string | null = null;

  let canvasEl: HTMLCanvasElement;
  let canvasW = 0;
  let canvasH = 0;
  let dpr = 1;
  let hoveredCluster: string | null = null;

  const dispatch = createEventDispatcher();

  // ─── colour palette for top-level categories ──────────────────────
  const CATEGORY_COLORS: Record<string, string> = {
    physics:                '#4361ee',
    computer_science:       '#f72585',
    mathematics:            '#4cc9f0',
    statistics:             '#7209b7',
    electrical_engineering: '#ff7a18',
    quantitative_biology:   '#2ec4b6',
    quantitative_finance:   '#ffd166',
    economics:              '#e71d36',
  };

  // ─── types ────────────────────────────────────────────────────────
  interface LayoutCluster extends ClusterNode {
    x: number;
    y: number;
    radius: number;
    color: string;
  }
  interface Transform { scale: number; offsetX: number; offsetY: number }

  // ─── view state (pan / zoom) ──────────────────────────────────────
  let view: Transform = { scale: 1, offsetX: 0, offsetY: 0 };
  let initialView: Transform = { scale: 1, offsetX: 0, offsetY: 0 };

  // drag state
  let isDragging = false;
  let dragStartX = 0;
  let dragStartY = 0;
  let dragStartOffsetX = 0;
  let dragStartOffsetY = 0;

  // zoom animation
  let zoomAnim = {
    active: false,
    start: { scale: 1, offsetX: 0, offsetY: 0 } as Transform,
    end:   { scale: 1, offsetX: 0, offsetY: 0 } as Transform,
    startTime: 0,
    duration: 700,
    callback: null as (() => void) | null,
  };

  // layout data
  let laid: LayoutCluster[] = [];
  let particles: Particle[] = [];
  let edgeAnimator: EdgeAnimator | null = null;
  let animFrameId = 0;

  // ─── colour helpers ───────────────────────────────────────────────
  function assignColor(c: ClusterNode, idx: number): string {
    if (parentColor) return shiftHue(parentColor, idx * 28);
    return CATEGORY_COLORS[c.id] ?? hslColor(idx, clusters.length);
  }

  function hslColor(i: number, total: number): string {
    const h = (i / Math.max(total, 1)) * 360;
    return `hsl(${h}, 65%, 55%)`;
  }

  function shiftHue(hex: string, deg: number): string {
    let r = parseInt(hex.slice(1, 3), 16) / 255;
    let g = parseInt(hex.slice(3, 5), 16) / 255;
    let b = parseInt(hex.slice(5, 7), 16) / 255;
    const max = Math.max(r, g, b), min = Math.min(r, g, b);
    let h = 0, s = 0;
    const l = (max + min) / 2;
    if (max !== min) {
      const d = max - min;
      s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
      if (max === r) h = ((g - b) / d + (g < b ? 6 : 0)) / 6;
      else if (max === g) h = ((b - r) / d + 2) / 6;
      else h = ((r - g) / d + 4) / 6;
    }
    h = ((h + deg / 360) % 1 + 1) % 1;
    const sat = Math.min(s * 1.05, 1);
    const q = l < 0.5 ? l * (1 + sat) : l + sat - l * sat;
    const p = 2 * l - q;
    const h2r = (pp: number, qq: number, t: number) => {
      t = ((t % 1) + 1) % 1;
      if (t < 1 / 6) return pp + (qq - pp) * 6 * t;
      if (t < 0.5) return qq;
      if (t < 2 / 3) return pp + (qq - pp) * (2 / 3 - t) * 6;
      return pp;
    };
    const nr = Math.round(h2r(p, q, h + 1 / 3) * 255);
    const ng = Math.round(h2r(p, q, h) * 255);
    const nb = Math.round(h2r(p, q, h - 1 / 3) * 255);
    return '#' + [nr, ng, nb].map(v => v.toString(16).padStart(2, '0')).join('');
  }

  function hexToRgb(hex: string): [number, number, number] {
    return [
      parseInt(hex.slice(1, 3), 16),
      parseInt(hex.slice(3, 5), 16),
      parseInt(hex.slice(5, 7), 16),
    ];
  }

  // ─── top-level category angles (degrees clockwise from top) ───────
  // physics at top, quant_finance next to economics,
  // statistics between economics and mathematics
  const CAT_ANGLES: Record<string, number> = {
    physics:                0,
    computer_science:       50,
    mathematics:            100,
    statistics:             148,
    economics:              196,
    quantitative_finance:   222,
    quantitative_biology:   275,
    electrical_engineering: 325,
  };

  // ─── layout ───────────────────────────────────────────────────────
  function computeLayout(): LayoutCluster[] {
    if (!clusters.length) return [];
    const sorted = [...clusters].sort((a, b) => b.count - a.count);
    const maxCount = sorted[0].count;
    const aspect = canvasW && canvasH ? canvasW / canvasH : 16 / 9;
    const sqA = Math.sqrt(Math.max(0.5, Math.min(aspect, 2.5)));

    if (!parentColor) {
      // Top-level: elliptical arrangement matching screen aspect ratio
      const Rx = 240 * sqA;
      const Ry = 240 / sqA;
      return sorted.map((c, i) => {
        const deg = CAT_ANGLES[c.id];
        let x: number, y: number;
        if (deg !== undefined) {
          const rad = deg * Math.PI / 180;
          x = Rx * Math.sin(rad);
          y = -Ry * Math.cos(rad);
        } else {
          const GA = Math.PI * (3 - Math.sqrt(5));
          const r = 180 * Math.sqrt(i + 1);
          x = r * Math.cos(i * GA) * sqA;
          y = r * Math.sin(i * GA) / sqA;
        }
        return {
          ...c, x, y,
          radius: 55 + 110 * Math.sqrt(c.count / maxCount),
          color: assignColor(c, i),
        };
      });
    } else {
      // Subcategory: tighter phyllotaxis with aspect correction
      const GA = Math.PI * (3 - Math.sqrt(5));
      const BASE = clusters.length <= 6 ? 130 : clusters.length <= 12 ? 110 : 90;
      return sorted.map((c, i) => {
        const r = BASE * Math.sqrt(i + 1);
        const theta = i * GA;
        return {
          ...c,
          x: r * Math.cos(theta) * sqA,
          y: r * Math.sin(theta) / sqA,
          radius: 40 + 95 * Math.sqrt(c.count / maxCount),
          color: assignColor(c, i),
        };
      });
    }
  }

  function computeInitialView(laid: LayoutCluster[], W: number, H: number): Transform {
    if (!laid.length) return { scale: 1, offsetX: W / 2, offsetY: H / 2 };
    const pad = 60;
    const xs = laid.map(c => [c.x - c.radius - pad, c.x + c.radius + pad]).flat();
    const ys = laid.map(c => [c.y - c.radius - pad, c.y + c.radius + pad]).flat();
    const minX = Math.min(...xs), maxX = Math.max(...xs);
    const minY = Math.min(...ys), maxY = Math.max(...ys);
    const scale = Math.min(W / (maxX - minX), H / (maxY - minY)) * 1.1;
    return {
      scale,
      offsetX: W / 2 - ((minX + maxX) / 2) * scale,
      offsetY: H / 2 - ((minY + maxY) / 2) * scale,
    };
  }

  // ─── coordinate transforms ────────────────────────────────────────
  function w2s(wx: number, wy: number): { x: number; y: number } {
    return { x: wx * view.scale + view.offsetX, y: wy * view.scale + view.offsetY };
  }

  function s2w(sx: number, sy: number): { x: number; y: number } {
    return { x: (sx - view.offsetX) / view.scale, y: (sy - view.offsetY) / view.scale };
  }

  // ─── deterministic particle generator ─────────────────────────────
  interface Particle { wx: number; wy: number; size: number; ci: number }

  function generateParticles(laid: LayoutCluster[]): Particle[] {
    let seed = 12345;
    const rng = () => { seed = (seed * 16807) % 2147483647; return (seed - 1) / 2147483646; };
    const ps: Particle[] = [];
    laid.forEach((c, ci) => {
      const n = Math.max(100, Math.min(700, Math.sqrt(c.count) * 0.5));
      for (let i = 0; i < n; i++) {
        const a = rng() * Math.PI * 2;
        const r = Math.sqrt(rng()) * c.radius * 0.88;
        ps.push({
          wx: c.x + Math.cos(a) * r,
          wy: c.y + Math.sin(a) * r,
          size: 0.8 + rng() * 2.0,
          ci,
        });
      }
    });
    return ps;
  }

  // ─── rebuild layout (resets view) ─────────────────────────────────
  function rebuild(W: number, H: number) {
    laid = computeLayout();
    particles = generateParticles(laid);
    initialView = computeInitialView(laid, W, H);
    view = { ...initialView };
    if (edgeAnimator) {
      edgeAnimator.updateClusters(laid);
    } else {
      edgeAnimator = new EdgeAnimator(laid);
    }
  }

  // ─── animation helpers ────────────────────────────────────────────
  function lerp(a: number, b: number, t: number): number { return a + (b - a) * t; }
  function easeInOutCubic(t: number): number {
    return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
  }

  // ─── rendering ────────────────────────────────────────────────────
  function draw() {
    if (!canvasEl) return;
    const ctx = canvasEl.getContext('2d');
    if (!ctx) return;

    // handle zoom animation
    if (zoomAnim.active) {
      const elapsed = Date.now() - zoomAnim.startTime;
      const t = Math.min(elapsed / zoomAnim.duration, 1);
      const e = easeInOutCubic(t);
      view = {
        scale:   lerp(zoomAnim.start.scale,   zoomAnim.end.scale,   e),
        offsetX: lerp(zoomAnim.start.offsetX, zoomAnim.end.offsetX, e),
        offsetY: lerp(zoomAnim.start.offsetY, zoomAnim.end.offsetY, e),
      };
      if (t >= 1) {
        zoomAnim.active = false;
        if (zoomAnim.callback) {
          const cb = zoomAnim.callback;
          zoomAnim.callback = null;
          cb();
        }
      }
    }

    // clear with DPR-aware transform
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.fillStyle = '#1e1e27';
    ctx.fillRect(0, 0, canvasW, canvasH);
    if (!laid.length) return;

    // draw edges
    edgeAnimator?.update(Date.now());
    edgeAnimator?.draw(ctx, view);

    // ── territory glows (smooth radial gradients) ──
    laid.forEach(c => {
      const s = w2s(c.x, c.y);
      const sr = c.radius * view.scale;
      const [r, g, b] = hexToRgb(c.color);
      const hov = hoveredCluster === c.id;

      // outer ambient glow
      const outerR = sr * 1.6;
      const outerGrad = ctx.createRadialGradient(s.x, s.y, 0, s.x, s.y, outerR);
      outerGrad.addColorStop(0,   `rgba(${r},${g},${b},${hov ? 0.22 : 0.11})`);
      outerGrad.addColorStop(0.5, `rgba(${r},${g},${b},${hov ? 0.10 : 0.05})`);
      outerGrad.addColorStop(1,   `rgba(${r},${g},${b},0)`);
      ctx.fillStyle = outerGrad;
      ctx.beginPath();
      ctx.arc(s.x, s.y, outerR, 0, Math.PI * 2);
      ctx.fill();

      // inner core glow
      const coreR = sr * 0.6;
      const coreGrad = ctx.createRadialGradient(s.x, s.y, 0, s.x, s.y, coreR);
      coreGrad.addColorStop(0, `rgba(${r},${g},${b},${hov ? 0.14 : 0.07})`);
      coreGrad.addColorStop(1, `rgba(${r},${g},${b},0)`);
      ctx.fillStyle = coreGrad;
      ctx.beginPath();
      ctx.arc(s.x, s.y, coreR, 0, Math.PI * 2);
      ctx.fill();
    });

    // ── subtle territory ring borders ──
    laid.forEach(c => {
      const s = w2s(c.x, c.y);
      const sr = c.radius * view.scale;
      const hov = hoveredCluster === c.id;
      ctx.strokeStyle = c.color + (hov ? '40' : '18');
      ctx.lineWidth = hov ? 1.5 : 0.8;
      ctx.beginPath();
      ctx.arc(s.x, s.y, sr * 0.92, 0, Math.PI * 2);
      ctx.stroke();
    });

    // ── particles ──
    const rgbCache = new Map<number, [number, number, number]>();
    particles.forEach(p => {
      if (!rgbCache.has(p.ci)) rgbCache.set(p.ci, hexToRgb(laid[p.ci].color));
      const [r, g, b] = rgbCache.get(p.ci)!;
      const hov = hoveredCluster === laid[p.ci].id;
      ctx.fillStyle = `rgba(${r},${g},${b},${hov ? 0.85 : 0.5})`;
      const s = w2s(p.wx, p.wy);
      const sz = Math.max(p.size * Math.sqrt(view.scale), 0.5);
      ctx.beginPath();
      ctx.arc(s.x, s.y, sz, 0, Math.PI * 2);
      ctx.fill();
    });

    // ── labels ──
    laid.forEach(c => {
      const s = w2s(c.x, c.y);
      const hov = hoveredCluster === c.id;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.shadowColor = 'rgba(0,0,0,0.9)';
      ctx.shadowBlur = 8;

      ctx.font = `bold ${hov ? 21 : 18}px 'Segoe UI', system-ui, sans-serif`;
      ctx.fillStyle = hov ? '#ffffff' : '#e0e0e0';
      ctx.fillText(c.name, s.x, s.y - 14);

      ctx.font = `${hov ? 15 : 13}px 'Segoe UI', system-ui, sans-serif`;
      ctx.fillStyle = hov ? '#cccccc' : '#888888';
      ctx.fillText(fmtCount(c.count) + ' papers', s.x, s.y + 14);
      ctx.shadowBlur = 0;
    });
  }

  function fmtCount(n: number): string {
    if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M';
    if (n >= 1_000) return Math.round(n / 1_000) + 'K';
    return String(n);
  }

  // ─── hit-testing (Euclidean) ──────────────────────────────────────
  function hitTest(sx: number, sy: number): LayoutCluster | null {
    if (!laid.length) return null;
    const w = s2w(sx, sy);
    let minD = Infinity, best: LayoutCluster | null = null;
    for (const c of laid) {
      const dx = w.x - c.x, dy = w.y - c.y;
      const d = Math.sqrt(dx * dx + dy * dy) / c.radius;
      if (d < minD && d < 1.3) { minD = d; best = c; }
    }
    return best;
  }

  // ─── zoom animation ──────────────────────────────────────────────
  function animateZoomTo(target: LayoutCluster) {
    const targetScale = Math.min(canvasW, canvasH) / (target.radius * 3.5);
    zoomAnim = {
      active: true,
      start: { ...view },
      end: {
        scale:   targetScale,
        offsetX: canvasW / 2 - target.x * targetScale,
        offsetY: canvasH / 2 - target.y * targetScale,
      },
      startTime: Date.now(),
      duration: 700,
      callback: () => {
        dispatch('clusterClick', { id: target.id, name: target.name, color: target.color });
      },
    };
  }

  function resetView() {
    zoomAnim = {
      active: true,
      start: { ...view },
      end:   { ...initialView },
      startTime: Date.now(),
      duration: 500,
      callback: null,
    };
  }

  // ─── events: pan / zoom / hover ───────────────────────────────────
  function handleMouseDown(e: MouseEvent) {
    if (zoomAnim.active) return;
    e.preventDefault();
    isDragging = true;
    dragStartX = e.clientX;
    dragStartY = e.clientY;
    dragStartOffsetX = view.offsetX;
    dragStartOffsetY = view.offsetY;
    canvasEl.style.cursor = 'grabbing';
    window.addEventListener('mousemove', handleDragMove);
    window.addEventListener('mouseup', handleDragEnd);
  }

  function handleDragMove(e: MouseEvent) {
    view = {
      ...view,
      offsetX: dragStartOffsetX + (e.clientX - dragStartX),
      offsetY: dragStartOffsetY + (e.clientY - dragStartY),
    };
  }

  function handleDragEnd(e: MouseEvent) {
    window.removeEventListener('mousemove', handleDragMove);
    window.removeEventListener('mouseup', handleDragEnd);
    isDragging = false;
    const dx = Math.abs(e.clientX - dragStartX);
    const dy = Math.abs(e.clientY - dragStartY);
    // treat as click if movement was minimal
    if (dx < 4 && dy < 4) {
      const rect = canvasEl.getBoundingClientRect();
      const hit = hitTest(e.clientX - rect.left, e.clientY - rect.top);
      if (hit) animateZoomTo(hit);
    }
    updateCursor(e);
  }

  function handleCanvasMouseMove(e: MouseEvent) {
    if (isDragging) return;
    const rect = canvasEl.getBoundingClientRect();
    const hit = hitTest(e.clientX - rect.left, e.clientY - rect.top);
    const newId = hit?.id ?? null;
    if (newId !== hoveredCluster) {
      hoveredCluster = newId;
      canvasEl.style.cursor = hoveredCluster ? 'pointer' : 'grab';
    }
  }

  function handleWheel(e: WheelEvent) {
    e.preventDefault();
    if (zoomAnim.active) return;
    const rect = canvasEl.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    const factor = e.deltaY > 0 ? 0.9 : 1.1;
    const newScale = Math.max(0.1, Math.min(view.scale * factor, 20));
    const ratio = newScale / view.scale;
    view = {
      scale:   newScale,
      offsetX: mx - (mx - view.offsetX) * ratio,
      offsetY: my - (my - view.offsetY) * ratio,
    };
  }

  function handleMouseLeave() {
    if (!isDragging) {
      hoveredCluster = null;
      canvasEl.style.cursor = 'grab';
    }
  }

  function updateCursor(e: MouseEvent) {
    const rect = canvasEl.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    if (mx >= 0 && mx < canvasW && my >= 0 && my < canvasH) {
      const hit = hitTest(mx, my);
      hoveredCluster = hit?.id ?? null;
      canvasEl.style.cursor = hit ? 'pointer' : 'grab';
    }
  }

  // ─── lifecycle ────────────────────────────────────────────────────
  onMount(() => {
    dpr = window.devicePixelRatio || 1;

    const resize = () => {
      const newW = canvasEl.offsetWidth;
      const newH = canvasEl.offsetHeight;
      canvasEl.width = newW * dpr;
      canvasEl.height = newH * dpr;

      if (laid.length && canvasW > 0) {
        // keep center stable on resize — don't reset user's pan/zoom
        view = {
          ...view,
          offsetX: view.offsetX + (newW - canvasW) / 2,
          offsetY: view.offsetY + (newH - canvasH) / 2,
        };
        initialView = computeInitialView(laid, newW, newH);
      } else {
        rebuild(newW, newH);
      }
      canvasW = newW;
      canvasH = newH;
    };

    const ro = new ResizeObserver(resize);
    ro.observe(canvasEl);
    resize();
    canvasEl.style.cursor = 'grab';

    // animation loop
    const animate = () => {
      draw();
      animFrameId = requestAnimationFrame(animate);
    };
    animFrameId = requestAnimationFrame(animate);

    return () => {
      ro.disconnect();
      cancelAnimationFrame(animFrameId);
      window.removeEventListener('mousemove', handleDragMove);
      window.removeEventListener('mouseup', handleDragEnd);
    };
  });

  // rebuild layout when clusters change (new view level)
  $: clustersChanged(clusters);
  function clustersChanged(_: ClusterNode[]) {
    if (!canvasEl || canvasW <= 0) return;
    rebuild(canvasW, canvasH);
  }
</script>

<div class="cluster-container">
  <canvas
    bind:this={canvasEl}
    on:mousedown={handleMouseDown}
    on:mousemove={handleCanvasMouseMove}
    on:mouseleave={handleMouseLeave}
    on:wheel|preventDefault={handleWheel}
  ></canvas>
  <button class="reset-btn" on:click={resetView} title="Reset view">&#x27F2;</button>
</div>

<style>
  .cluster-container {
    width: 100%;
    height: 100%;
    position: relative;
    overflow: hidden;
  }
  canvas {
    width: 100%;
    height: 100%;
    display: block;
    background: #1e1e27;
  }
  .reset-btn {
    position: absolute;
    bottom: 16px;
    right: 16px;
    width: 38px;
    height: 38px;
    border-radius: 50%;
    border: 1px solid rgba(255,255,255,0.15);
    background: rgba(30,30,39,0.8);
    color: #ccc;
    font-size: 20px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    backdrop-filter: blur(6px);
    z-index: 10;
    transition: background 0.2s, color 0.2s;
  }
  .reset-btn:hover {
    background: rgba(74,158,255,0.3);
    color: #fff;
  }
</style>
