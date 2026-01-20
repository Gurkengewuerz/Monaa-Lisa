<script lang="ts">
  import { createEventDispatcher, onMount } from 'svelte';
  import Graph from 'graphology';
  import Sigma from 'sigma';
  import concaveman from 'concaveman';
  import type { Paper } from '$lib/types/paper';
  import { getClusterColor } from '../utils/clusterColors';
  import { getCategoryCountryName } from '../utils/categoryCountries';

  /**
   * array of papers to display in the graph.
   * passed from the parent component.
   * @type {Paper[]}
   */export let papers: Paper[] = [];
  export let selectedPaperId: string | null = null;

   /**
   * flag to use dummy data for showcasing.
   * when true, uses dummypapers instead of the papers prop.
   * set to true for demo, false for real data.
   * @type {boolean}
   
  export let useDummyData: boolean = true;

  // DEMO-ONLY: easy-to-remove organic layout pass to make dummy clusters look organic (no FA2).
  // Remove by deleting this export and the block labeled "DEMO-ONLY ORGANIC LAYOUT" below.
  export let organicDemoLayout: boolean = true;

  // DEMO-ONLY: global compression factor (0..1). Lower brings clusters closer together.
  // Remove by deleting this export and the block labeled "DEMO-ONLY GLOBAL COMPRESSION" below.
  export let demoClusterCompression: number = 0.45;
*/
  //internal state variables for component management
  let container: HTMLDivElement | null = null;
  let hullCanvas: HTMLCanvasElement | null = null;
  let selectedPaper: Paper | null = null;
  let selectedNode: string | null = null;
  let renderer: Sigma | null = null;
  let graph: Graph | null = null;

    //add cache for quick paper lookup
  let paperCache: Map<string, Paper> = new Map();
    //add debounce for hover
  let hoverTimeout: number | null = null;

  const dispatch = createEventDispatcher();
  const FALLBACK_NODE_COLOR = '#999999';

    /**
   * selects and highlights a node in the graph, updating visuals and connections.
   * clears edges, resets colors, highlights related nodes, adds edges, and zooms.
   * @param {string} nodeId - the id of the node to select.
   */
  function selectNodeById(nodeId: string) {
    if (!graph || !renderer || !graph.hasNode(nodeId)) return;

    const edgesToRemove = graph.edges();
    edgesToRemove.forEach((edge) => graph!.dropEdge(edge));

    graph.forEachNode((n) => {
      graph!.setNodeAttribute(n, 'color', 'rgba(0, 0, 0, 0.25)');
    });

    graph.setNodeAttribute(nodeId, 'color', '#00FF00');

    const paper = graph.getNodeAttribute(nodeId, 'paper') as Paper;
    selectedPaper = paper;
    const relatedNodes = new Set<string>(paper.citations);

    relatedNodes.forEach(relatedId => {
      if (graph!.hasNode(relatedId)) {
        graph!.setNodeAttribute(relatedId, 'color', '#FFFF00');
      }
    });

        //add edges only for citations
    //edges to cited papers
    paper.citations.forEach(citedId => {
      if (graph!.hasNode(citedId)) {
        graph!.addEdge(nodeId, citedId, {
          color: '#FFFFFF',
          size: 1.5
        });
      }
    });

    const nodePosition = graph.getNodeAttributes(nodeId);
    const camera = renderer.getCamera();
        // TypeScript's AnimateOptions may not include x/y directly depending on the sigma types;
    // cast to any to allow passing x/y while keeping runtime behavior unchanged.
    camera.animatedReset({
      x: nodePosition.x,
      y: nodePosition.y,
      ratio: 0.5,
      duration: 800
    } as any);

    selectedNode = nodeId;
    renderer.refresh();
    dispatch('nodeSelected', nodeId);
    console.log(`Node ${nodeId} is currently selected lelele`);
  }

  /**
   * 
   * @param points
   * @param cx
   * @param cy
   * @param factor
   * @param minOffset
   */
function inflateAroundCenter(
  points: [number, number][],
  cx: number,
  cy: number,
  factor: number
) {
  return points.map(([x, y]) => {
    const dx = x - cx;
    const dy = y - cy;
    return [cx + dx * factor, cy + dy * factor] as [number, number];
  });
}

function inflateToContainPadding(
  hull: [number, number][],
  points: { x: number; y: number }[],
  cx: number,
  cy: number,
  padding: number,
  maxFactor = 1.6 // Schutz gegen Monster-Hulls
) {
  const maxPointR = Math.max(...points.map(p => Math.hypot(p.x - cx, p.y - cy)));
  const maxHullR  = Math.max(...hull.map(([x,y]) => Math.hypot(x - cx, y - cy))) || 1;

  const targetR = maxPointR + padding;
  const rawFactor = targetR / maxHullR;
  const factor = Math.min(Math.max(1, rawFactor), maxFactor);

  return inflateAroundCenter(hull, cx, cy, factor);
}

// optional: Cluster-"Spread" für dynamisches Padding
function clusterSpread(points: {x:number;y:number}[], cx:number, cy:number) {
  const meanSq = points.reduce((s, p) => s + (p.x - cx)**2 + (p.y - cy)**2, 0) / points.length;
  return Math.sqrt(meanSq);
}

  /**
   * 
   * @param points
   * @param iterations
   */
  function chaikinSmooth(points: [number, number][], iterations = 2) {
  let pts = points;
  for (let k = 0; k < iterations; k++) {
    const res: [number, number][] = [];
    for (let i = 0; i < pts.length; i++) {
      const p0 = pts[i];
      const p1 = pts[(i + 1) % pts.length]; // closed ring

      // Q = 0.75*p0 + 0.25*p1
      res.push([
        0.75 * p0[0] + 0.25 * p1[0],
        0.75 * p0[1] + 0.25 * p1[1],
      ]);

      // R = 0.25*p0 + 0.75*p1
      res.push([
        0.25 * p0[0] + 0.75 * p1[0],
        0.25 * p0[1] + 0.75 * p1[1],
      ]);
    }
    pts = res;
  }
  return pts;
}

  $: if (selectedPaperId && selectedPaperId !== selectedNode && graph && renderer) {
    selectNodeById(selectedPaperId);
  }

  function drawHulls(hulls: any[]) {
    if (!hullCanvas || !renderer) return;
    const ctx = hullCanvas.getContext('2d');
    if (!ctx) return;

    // Resize canvas to match container
    if (hullCanvas.width !== hullCanvas.offsetWidth || hullCanvas.height !== hullCanvas.offsetHeight) {
        hullCanvas.width = hullCanvas.offsetWidth;
        hullCanvas.height = hullCanvas.offsetHeight;
    }

    ctx.clearRect(0, 0, hullCanvas.width, hullCanvas.height);

    hulls.forEach(hull => {
        if (!hull.path || hull.path.length < 3) return;

        ctx.beginPath();
        hull.path.forEach((pt: [number, number], i: number) => {
            const pos = renderer!.graphToViewport({x: pt[0], y: pt[1]});
            if (i === 0) ctx.moveTo(pos.x, pos.y);
            else ctx.lineTo(pos.x, pos.y);
        });
        ctx.closePath();
        ctx.fillStyle = hull.color; 
        ctx.fill();
        ctx.strokeStyle = hull.strokeColor;
        ctx.lineWidth = 2;
        ctx.stroke();

        // Draw Label
        const center = renderer!.graphToViewport({x: hull.cx, y: hull.cy});
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 14px Arial';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.shadowColor = 'black';
        ctx.shadowBlur = 4;
        ctx.fillText(hull.label, center.x, center.y);
        ctx.shadowBlur = 0;
    });
  }

  onMount(() => {
    console.log("Graph Component Mounting...");
    graph = new Graph();
    const dataSource = papers;
    console.log(`Processing ${dataSource.length} papers...`);

    const inDegree = new Map<string, number>();
    dataSource.forEach(p => inDegree.set(p.entry_id, 0));
    dataSource.forEach(p => {
      p.citations.forEach(cid => {
        if (inDegree.has(cid)) inDegree.set(cid, (inDegree.get(cid) || 0) + 1);
      });
    });
    let maxIn = 0;
    inDegree.forEach(v => { if (v > maxIn) maxIn = v; });
    const minSize = 1;
    const maxSize = 6;
    const sizeFor = (count: number) => {
      if (maxIn === 0) return minSize;
      const t = count / maxIn;
      return minSize + t * (maxSize - minSize);
    };

    // Collect points for hulls
    const categoryPoints = new Map<string, {x: number, y: number}[]>();

    // --- FORCE SEPARATION LOGIC ---
    // 1. Calculate Centroids per Category
    const papersByCategory = new Map<string, Paper[]>();
    const categoryCentroids = new Map<string, {x: number, y: number}>();
    
    dataSource.forEach(p => {
        const cat = p.category || 'Unknown';
        if (!papersByCategory.has(cat)) papersByCategory.set(cat, []);
        papersByCategory.get(cat)!.push(p);
    });

    papersByCategory.forEach((papers, cat) => {
        let sumX = 0, sumY = 0;
        papers.forEach(p => { sumX += p.tsne1; sumY += p.tsne2; });
        categoryCentroids.set(cat, { x: sumX / papers.length, y: sumY / papers.length });
    });

    // 2. Assign Territory Centers (Phyllotaxis Spiral Layout)
    const categories = Array.from(papersByCategory.keys()).sort();
    const territoryCenters = new Map<string, {x: number, y: number}>();
    
    // Spiral parameters
    const SPACING_FACTOR = 400; // Distance between spiral arms
    const ANGLE_INCREMENT = 137.5 * (Math.PI / 180); // Golden angle in radians
    
    categories.forEach((cat, i) => {
        // Formula: r = c * sqrt(n), theta = n * 137.5 deg
        const r = SPACING_FACTOR * Math.sqrt(i + 1); 
        const theta = i * ANGLE_INCREMENT;
        
        territoryCenters.set(cat, {
            x: r * Math.cos(theta),
            y: r * Math.sin(theta)
        });
    });

    dataSource.forEach(paper => {
      const cat = paper.category || 'Unknown';
      const centroid = categoryCentroids.get(cat) || {x: 0, y: 0};
      const territory = territoryCenters.get(cat) || {x: 0, y: 0};
      
      // Local coordinates relative to cluster center
      // Scale local cluster to keep it compact within its territory
      const LOCAL_SCALE = 20.0; 
      const localX = (paper.tsne1 - centroid.x) * LOCAL_SCALE;
      const localY = (paper.tsne2 - centroid.y) * LOCAL_SCALE;

      const finalX = territory.x + localX;
      const finalY = territory.y + localY;

      const inCitations = inDegree.get(paper.entry_id) || 0;
      const nodeSize = sizeFor(inCitations);
      const nodeColor = getClusterColor(paper.category, paper.cluster) ?? FALLBACK_NODE_COLOR;

      graph!.addNode(paper.entry_id, {
        x: finalX,
        y: finalY,
        size: nodeSize,
        label: paper.title,
        color: nodeColor,
        originalColor: nodeColor,
        paper: paper,
        inCitations
      });

      //cache paper for fast lookup
      paperCache.set(paper.entry_id, paper);

      // Collect points
      // Kleiner bugfix hier wäre es besser cat zu verwenden statt paper.category
      if (!categoryPoints.has(cat)) categoryPoints.set(cat, []);
      categoryPoints.get(cat)!.push({ x: finalX, y: finalY });
    });

    // Initialize Sigma Renderer FIRST to ensure papers are visible! :)
    if (container) {
      console.log("Initializing Sigma Renderer...");
      renderer = new Sigma(graph, container, {
        renderEdgeLabels: false,
        defaultNodeType: 'circle',
        defaultEdgeType: 'line',
        minCameraRatio: 0.001,
        maxCameraRatio: 100,
        renderLabels: false,
      });

      
      //handle node hover: show paper details with debounce
      renderer.on('enterNode', ({ node }) => {
        if (hoverTimeout) clearTimeout(hoverTimeout);
        hoverTimeout = setTimeout(() => {
          selectedPaper = paperCache.get(node) || null;
        }, 200) as unknown as number;
      });

      renderer.on('leaveNode', () => {
          //clear timeout and hide details
        if (hoverTimeout) clearTimeout(hoverTimeout);
        selectedPaper = null;
      });

      // *** FIXED CLICK HANDLER - NO DUPLICATE DISPATCH ***
      renderer.on('clickNode', ({ node }) => {
        selectNodeById(node);
      });

      renderer.on('clickStage', () => {
        selectedNode = null;
        selectedPaper = null;
        graph!.forEachNode((n) => {
          const originalColor = graph!.getNodeAttribute(n, 'originalColor');
          graph!.setNodeAttribute(n, 'color', originalColor);
        });
        const edgesToRemove = graph!.edges();
        edgesToRemove.forEach((edge) => graph!.dropEdge(edge));
        renderer!.getCamera().animatedReset({ duration: 800 });
        renderer!.refresh();
        dispatch('nodeDeselected');
      });

      // Cleanup
      const killRenderer = () => {
        // Hier stellen wir sicher dass wir IMMER evt. noch offene Listener entfernen sonst memory leak - nico
        if (hoverTimeout) clearTimeout(hoverTimeout);
        if (renderer) {
          // Listener entfernen
          renderer.getCamera().off('updated');
          renderer.kill();
        }        
        paperCache.clear();
      };

      // Compute Hulls SAFELY and on client side (for now!!)
      try {
        console.log("Computing Hulls...");
        const hulls: any[] = [];
        categoryPoints.forEach((points, cat) => {
            if (points.length < 3) return;

            // 1. Centroid of all points
            const cx = points.reduce((sum, p) => sum + p.x, 0) / points.length;
            const cy = points.reduce((sum, p) => sum + p.y, 0) / points.length;

            // 2. Filter outliers (98% densest)
            // this is to prevent concaveman from creating huge hulls due to outliers
            // we need to name the outliers something cool though
            const withDist = points.map(p => ({
                p,
                // calculate squared distance to centroid
                dist: (p.x - cx)**2 + (p.y - cy)**2
            }));
            // sort by distance
            withDist.sort((a, b) => a.dist - b.dist);
            // keep only closest 98%
            const keepCount = Math.ceil(points.length * 0.98);
            
            // ensure at least 3 points to form a hull
            if (keepCount < 3) return;
            
            // extract kept points
            const keptPoints = withDist.slice(0, keepCount).map(item => [item.p.x, item.p.y] as [number, number]);

            // 3. usage of concaveman package to compute hull 
            // Use lower concavity (1.0) for tighter hulls to avoid visual overlap
            let hullPoints;
            if (typeof concaveman === 'function') {
                hullPoints = concaveman(keptPoints, 1.0);
            } else if ((concaveman as any).default) {
                 // Handle potential ESM/CJS interop issues because I had 
                 // the issue in some setups where concaveman was an object with a default property
                hullPoints = (concaveman as any).default(keptPoints, 1.0);
            } else {
                console.warn("Concaveman not found or invalid type", concaveman);
                return;
            }

            // 1) glätten
            let smoothHull = chaikinSmooth(hullPoints as [number, number][], 2);

            // 2) Padding dynamisch aus Spread (statt minOffset=35)
            const spread = clusterSpread(points, cx, cy);
            const padding = Math.max(20, spread * 0.35);

            // 3) aufblasen bis alle Punkte + padding "radial" reinpassen (mit cap)
            smoothHull = inflateToContainPadding(
              smoothHull,
              points,
              cx, cy,
              padding,
              1.6
            );

            const color = getClusterColor(cat, cat) || '#cccccc';
            
            // finally store hull
            hulls.push({
                path: smoothHull,
                color: color + '33', 
                strokeColor: color + '66',
                label: getCategoryCountryName(cat),
                cx, cy
            });
        });

        console.log(`Generated ${hulls.length} hulls.`);

        // Bind hull drawing
        const camera = renderer.getCamera();
        camera.on('updated', () => drawHulls(hulls));
        
        // Initial draw
        setTimeout(() => drawHulls(hulls), 100);

      } catch (e) {
        console.error("Error generating hulls:", e);
      }

      return killRenderer;
    }
  });
</script>

<style>
  .graph-container {
    width: 100%;
    height: 600px;
    border: none;
    background-color: #1e1e27;
    position: relative; 
  }

  canvas {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    pointer-events: none; 
    z-index: 1; 
  }

  .paper-details {
    position: absolute;
    top: 10px;
    right: 10px;
    background: rgba(255, 255, 255, 0.95);
    padding: 15px;
    border: 1px solid #34495e;
    border-radius: 8px;
    max-width: 300px;
    display: none;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    font-size: 14px;
    z-index: 10; 
  }

  .paper-details.visible {
    display: block;
  }

  .paper-details h3 {
    margin: 0 0 10px 0;
    color: #2c3e50;
    font-size: 16px;
  }

  .paper-details p {
    margin: 5px 0;
    color: #34495e;
  }
</style>

<div class="graph-container" bind:this={container}>
    <canvas bind:this={hullCanvas}></canvas>
</div>

{#if selectedPaper}
  <div class="paper-details visible">
    <h3>{selectedPaper.title}</h3>
    <p><strong>authors:</strong> {selectedPaper.authors}</p>
    <p><strong>summary:</strong> {selectedPaper.summary}</p>
    <p><strong>published:</strong> {selectedPaper.published ? new Date(selectedPaper.published).toLocaleDateString() : 'Unbekannt'}</p>
    <p><strong>citations:</strong> {selectedPaper.citations.length}</p>
  </div>
{/if}
