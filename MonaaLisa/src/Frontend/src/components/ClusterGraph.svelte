<!--
  ClusterGraph.svelte
  Canvas-based Manhattan-Voronoi cluster visualization.
  Used for both top-level category and subcategory views.
  Clusters are rendered as pixelated territories with particle fill.
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

  // ─── layout: phyllotaxis spiral weighted by paper count ───────────
  function computeLayout(): LayoutCluster[] {
    if (!clusters.length) return [];
    const sorted = [...clusters].sort((a, b) => b.count - a.count);
    const maxCount = sorted[0].count;
    const GOLDEN_ANGLE = Math.PI * (3 - Math.sqrt(5));
    const BASE = clusters.length <= 10 ? 220 : 160;
    return sorted.map((c, i) => {
      const r = BASE * Math.sqrt(i + 1);
      const theta = i * GOLDEN_ANGLE;
      return {
        ...c,
        x: r * Math.cos(theta),
        y: r * Math.sin(theta),
        radius: 50 + 160 * Math.sqrt(c.count / maxCount),
        color: assignColor(c, i),
      };
    });
  }

  // ─── coordinate transforms ────────────────────────────────────────
  function getTransform(laid: LayoutCluster[], W: number, H: number): Transform {
    if (!laid.length) return { scale: 1, offsetX: 0, offsetY: 0 };
    const pad = 120;
    const xs = laid.map(c => [c.x - c.radius - pad, c.x + c.radius + pad]).flat();
    const ys = laid.map(c => [c.y - c.radius - pad, c.y + c.radius + pad]).flat();
    const minX = Math.min(...xs), maxX = Math.max(...xs);
    const minY = Math.min(...ys), maxY = Math.max(...ys);
    const scale = Math.min(W / (maxX - minX), H / (maxY - minY)) * 0.88;
    return {
      scale,
      offsetX: W / 2 - ((minX + maxX) / 2) * scale,
      offsetY: H / 2 - ((minY + maxY) / 2) * scale,
    };
  }

  function w2s(wx: number, wy: number, t: Transform) {
    return { x: wx * t.scale + t.offsetX, y: wy * t.scale + t.offsetY };
  }

  function s2w(sx: number, sy: number, t: Transform) {
    return { x: (sx - t.offsetX) / t.scale, y: (sy - t.offsetY) / t.scale };
  }

  // ─── Manhattan-Voronoi grid ───────────────────────────────────────
  const CELL = 7; // pixel-art cell size in screen pixels

  let gridCells: Int16Array = new Int16Array(0);
  let gridW = 0;
  let gridH = 0;

  function buildGrid(laid: LayoutCluster[], t: Transform, W: number, H: number) {
    gridW = Math.ceil(W / CELL);
    gridH = Math.ceil(H / CELL);
    gridCells = new Int16Array(gridW * gridH).fill(-1);
    for (let gy = 0; gy < gridH; gy++) {
      for (let gx = 0; gx < gridW; gx++) {
        const w = s2w((gx + 0.5) * CELL, (gy + 0.5) * CELL, t);
        let minD = Infinity, best = -1;
        for (let c = 0; c < laid.length; c++) {
          const d = (Math.abs(w.x - laid[c].x) + Math.abs(w.y - laid[c].y)) / laid[c].radius;
          if (d < minD) { minD = d; best = c; }
        }
        if (best >= 0 && minD < 2.0) gridCells[gy * gridW + gx] = best;
      }
    }
  }

  // ─── deterministic particle generator ─────────────────────────────
  interface Particle { wx: number; wy: number; size: number; ci: number }

  function generateParticles(laid: LayoutCluster[]): Particle[] {
    let seed = 12345;
    const rng = () => { seed = (seed * 16807) % 2147483647; return (seed - 1) / 2147483646; };
    const ps: Particle[] = [];
    laid.forEach((c, ci) => {
      const n = Math.max(80, Math.min(600, Math.sqrt(c.count) * 0.45));
      for (let i = 0; i < n; i++) {
        const a = rng() * Math.PI * 2;
        const r = rng() * c.radius * 0.82;
        ps.push({ wx: c.x + Math.cos(a) * r, wy: c.y + Math.sin(a) * r, size: 1 + rng() * 2.2, ci });
      }
    });
    return ps;
  }

  // ─── rendering ────────────────────────────────────────────────────
  let laid: LayoutCluster[] = [];
  let particles: Particle[] = [];
  let transform: Transform = { scale: 1, offsetX: 0, offsetY: 0 };
  let edgeAnimator: EdgeAnimator | null = null;

  function rebuild(W: number, H: number) {
    laid = computeLayout();
    particles = generateParticles(laid);
    transform = getTransform(laid, W, H);
    buildGrid(laid, transform, W, H);
    if (edgeAnimator) {
      edgeAnimator.updateClusters(laid);
    } else {
      edgeAnimator = new EdgeAnimator(laid);
    }
  }

  function draw() {
    if (!canvasEl) return;
    const ctx = canvasEl.getContext('2d');
    if (!ctx) return;
    const W = canvasEl.width, H = canvasEl.height;

    // background
    ctx.fillStyle = '#1e1e27';
    ctx.fillRect(0, 0, W, H);
    if (!laid.length) return;

    // draw edges
    edgeAnimator?.update(Date.now());
    edgeAnimator?.draw(ctx, transform);

    // ── Manhattan-Voronoi territory cells ──
    for (let gy = 0; gy < gridH; gy++) {
      for (let gx = 0; gx < gridW; gx++) {
        const idx = gridCells[gy * gridW + gx];
        if (idx < 0) continue;
        const c = laid[idx];
        const hov = hoveredCluster === c.id;

        // border detection: any neighbour belongs to a different cluster
        let border = false;
        const gi = gy * gridW + gx;
        if (gx > 0 && gridCells[gi - 1] !== idx) border = true;
        else if (gx < gridW - 1 && gridCells[gi + 1] !== idx) border = true;
        else if (gy > 0 && gridCells[gi - gridW] !== idx) border = true;
        else if (gy < gridH - 1 && gridCells[gi + gridW] !== idx) border = true;

        ctx.fillStyle = c.color + (border ? (hov ? 'bb' : '55') : (hov ? '28' : '12'));
        ctx.fillRect(gx * CELL, gy * CELL, CELL, CELL);
      }
    }

    // ── particles ──
    const rgbCache = new Map<number, [number, number, number]>();
    particles.forEach(p => {
      if (!rgbCache.has(p.ci)) rgbCache.set(p.ci, hexToRgb(laid[p.ci].color));
      const [r, g, b] = rgbCache.get(p.ci)!;
      const hov = hoveredCluster === laid[p.ci].id;
      ctx.fillStyle = `rgba(${r},${g},${b},${hov ? 0.85 : 0.5})`;
      const s = w2s(p.wx, p.wy, transform);
      ctx.beginPath();
      ctx.arc(s.x, s.y, p.size, 0, Math.PI * 2);
      ctx.fill();
    });

    // ── labels ──
    laid.forEach(c => {
      const s = w2s(c.x, c.y, transform);
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

  // ─── hit-testing ──────────────────────────────────────────────────
  function hitTest(sx: number, sy: number): LayoutCluster | null {
    if (!laid.length) return null;
    const w = s2w(sx, sy, transform);
    let minD = Infinity, best: LayoutCluster | null = null;
    for (const c of laid) {
      const d = (Math.abs(w.x - c.x) + Math.abs(w.y - c.y)) / c.radius;
      if (d < minD && d < 2.0) { minD = d; best = c; }
    }
    return best;
  }

  // ─── events ───────────────────────────────────────────────────────
  function handleClick(e: MouseEvent) {
    const rect = canvasEl.getBoundingClientRect();
    const c = hitTest(e.clientX - rect.left, e.clientY - rect.top);
    if (c) dispatch('clusterClick', { id: c.id, name: c.name, color: c.color });
  }

  function handleMouseMove(e: MouseEvent) {
    const rect = canvasEl.getBoundingClientRect();
    const c = hitTest(e.clientX - rect.left, e.clientY - rect.top);
    const newId = c?.id ?? null;
    if (newId !== hoveredCluster) {
      hoveredCluster = newId;
      canvasEl.style.cursor = hoveredCluster ? 'pointer' : 'default';
      draw(); // only re-draw colours, grid stays cached
    }
  }

  function handleMouseLeave() {
    if (hoveredCluster) {
      hoveredCluster = null;
      canvasEl.style.cursor = 'default';
      draw();
    }
  }

  // ─── lifecycle ────────────────────────────────────────────────────
  onMount(() => {
    const resize = () => {
      canvasEl.width = canvasEl.offsetWidth * (window.devicePixelRatio || 1);
      canvasEl.height = canvasEl.offsetHeight * (window.devicePixelRatio || 1);
      canvasEl.getContext('2d')?.scale(window.devicePixelRatio || 1, window.devicePixelRatio || 1);
      rebuild(canvasEl.offsetWidth, canvasEl.offsetHeight);
      draw();
    };
    const ro = new ResizeObserver(resize);
    ro.observe(canvasEl);
    resize();

    // Animation loop for edges
    const animate = () => {
      draw();
      requestAnimationFrame(animate);
    };
    requestAnimationFrame(animate);

    return () => ro.disconnect();
  });

  // re-layout when clusters change
  $: if (clusters && canvasEl) {
    rebuild(canvasEl.offsetWidth, canvasEl.offsetHeight);
    draw();
  }
</script>

<canvas
  bind:this={canvasEl}
  on:click={handleClick}
  on:mousemove={handleMouseMove}
  on:mouseleave={handleMouseLeave}
  class="cluster-canvas"
></canvas>

<style>
  .cluster-canvas {
    width: 100%;
    height: 100%;
    display: block;
    background: #1e1e27;
  }
</style>
