<script lang="ts">
  import { onMount } from 'svelte';
  import Sigma from 'sigma';
  import { UndirectedGraph } from 'graphology';
  import { dummyPapers } from '../testdata/dummyData';
  import type { Paper } from '../testdata/dummyData';
  import * as d3 from 'd3'; // Used only for convex hull calculation
  import "../app.css";


  // Visualization container and dimensions
  let vizContainer: HTMLDivElement;
  let WIDTH = 800;
  let HEIGHT = 600;

  // State: selected paper and search filter
  let selectedPaper: Paper | null = null;
  let filterTerm: string = '';

  // Efficient lookup map for papers by ID
  const paperMap: Map<number, Paper> = new Map(dummyPapers.map(p => [p.id, p]));

  // Filter papers by search term (case-insensitive)
  let filteredPapers: Paper[] = dummyPapers;
  $: filteredPapers = dummyPapers.filter((p: Paper) =>
    (p.title || '').toLowerCase().includes(filterTerm.toLowerCase())
  );

  // Sigma.js and graph variables
  let sigmaInstance: Sigma | null = null;
  let graph: UndirectedGraph;

  // Scales for positioning (same as D3 for consistency)
  let xScale: d3.ScaleLinear<number, number, never>;
  let yScale: d3.ScaleLinear<number, number, never>;

  // Update node and edge styles based on selected paper
  function updateVisualization(selected: Paper | null) {
    selectedPaper = selected;

    if (!graph || !sigmaInstance) return;

    const connectedIds = selected
      ? new Set<number>([selected.id, ...(selected.related_papers || []), ...(selected.citations || [])])
      : new Set<number>();

    graph.forEachNode((node, attributes) => {
      const isSelected = selected && attributes.id === selected.id;
      const isConnected = connectedIds.has(attributes.id);

      graph.setNodeAttribute(node, 'color', isSelected ? 'green' : isConnected ? 'yellow' : '#d3d3d3');
      graph.setNodeAttribute(node, 'size', isSelected ? 12 : isConnected ? 10 : 8);
      graph.setNodeAttribute(node, 'opacity', isConnected ? 1 : 0.2);
    });

    graph.forEachEdge((edge, attributes) => {
      const srcId = attributes.sourceId;
      const tgtId = attributes.targetId;
      const connected = srcId && tgtId && connectedIds.has(srcId) && connectedIds.has(tgtId);

      graph.setEdgeAttribute(edge, 'color', connected ? 'gray' : '#d3d3d3');
      graph.setEdgeAttribute(edge, 'opacity', connected ? 1 : 0.05);
    });

    sigmaInstance.refresh();
  }

  // Initialize visualization on component mount
  onMount(() => {
    // Responsive container sizing
    const resize = () => {
      if (vizContainer) {
        WIDTH = vizContainer.clientWidth;
        HEIGHT = vizContainer.clientHeight;
      }
    };
    resize();
    window.addEventListener('resize', () => {
      resize();
      if (sigmaInstance) {
        sigmaInstance.getCamera().setState({ x: 0.5, y: 0.5, ratio: 1 });
        sigmaInstance.refresh();
      }
    });

    // Initialize graph
    graph = new UndirectedGraph();

    // Create scales with padding
    const margin = { top: 20, right: 20, bottom: 20, left: 20 };
    const xExtent = d3.extent(dummyPapers, (d: Paper) => d.tsne1 || 0) as [number, number];
    const yExtent = d3.extent(dummyPapers, (d: Paper) => d.tsne2 || 0) as [number, number];

    xScale = d3.scaleLinear()
      .domain([xExtent[0] - 5, xExtent[1] + 5])
      .range([margin.left / WIDTH, 1 - margin.right / WIDTH]);

    yScale = d3.scaleLinear()
      .domain([yExtent[0] - 5, yExtent[1] + 5])
      .range([1 - margin.bottom / HEIGHT, margin.top / HEIGHT]);

    // Add nodes
    dummyPapers.forEach((paper: Paper) => {
      if (paper.id) {
        graph.addNode(paper.id.toString(), {
          id: paper.id,
          x: xScale(paper.tsne1 || 0),
          y: yScale(paper.tsne2 || 0),
          size: 8,
          label: paper.title || 'Untitled',
          color: paper.cluster === 'A' ? '#4fd1c5' : paper.cluster === 'B' ? '#f6ad55' : paper.cluster === 'C' ? '#63b3ed' : '#b794f4',
          opacity: 1
        });
      }
    });

    // Add edges
    dummyPapers.forEach((paper: Paper) => {
      (paper.related_papers || []).forEach((relId: number) => {
        if (paper.id && paperMap.has(relId)) {
          graph.addEdgeWithKey(`${paper.id}-${relId}`, paper.id.toString(), relId.toString(), {
            sourceId: paper.id,
            targetId: relId,
            color: 'gray',
            size: 1,
            opacity: 0.5
          });
        }
      });
    });

    // Initialize Sigma.js
    sigmaInstance = new Sigma(graph, vizContainer, {
      allowInvalidContainer: false,
      defaultNodeType: 'circle',
      defaultEdgeType: 'line',
      enableEdgeEvents: true,
      minCameraRatio: 0.5,
      maxCameraRatio: 5,
      labelFont: 'Arial',
      labelSize: 12,
      labelColor: { color: '#e0e6ed' },
      backgroundColor: '#1C2526'
    });

    // Draw cluster hulls using canvas
    const canvas = vizContainer.querySelector('canvas')!;
    const ctx = canvas.getContext('2d')!;
    const drawHulls = () => {
      ctx.clearRect(0, 0, WIDTH, HEIGHT);
      const clusters: Record<string, Paper[]> = {};
      dummyPapers.forEach(p => {
        if (!clusters[p.cluster]) clusters[p.cluster] = [];
        clusters[p.cluster].push(p);
      });

      Object.entries(clusters).forEach(([cluster, papers], i) => {
        const points: [number, number][] = papers.map(p => [
          xScale(p.tsne1 || 0) * WIDTH,
          yScale(p.tsne2 || 0) * HEIGHT
        ]);
        if (points.length < 3) return;

        const hull = d3.polygonHull(points);
        if (!hull) return;

        ctx.beginPath();
        ctx.moveTo(hull[0][0], hull[0][1]);
        hull.forEach(([x, y], i) => {
          if (i > 0) ctx.lineTo(x, y);
        });
        ctx.closePath();
        ctx.fillStyle = ["#2a3a44", "#3b4a5a", "#1e2d3a", "#4a3b5a"][i % 4];
        ctx.globalAlpha = 0.18;
        ctx.fill();
        ctx.strokeStyle = ["#4fd1c5", "#f6ad55", "#63b3ed", "#f56565"][i % 4];
        ctx.lineWidth = 3;
        ctx.globalAlpha = 1;
        ctx.stroke();
      });
    };

    // Redraw hulls on camera change
    sigmaInstance.on('afterRender', drawHulls);

    // Node click handler
    sigmaInstance.on('clickNode', ({ node }) => {
      const paperId = parseInt(node);
      const paper = paperMap.get(paperId);
      if (paper) updateVisualization(paper);
    });

    // Background click clears selection
    sigmaInstance.on('clickStage', () => updateVisualization(null));

    // Node dragging
    let draggedNode: string | null = null;
    sigmaInstance.on('downNode', ({ node }) => {
      draggedNode = node;
      graph.setNodeAttribute(node, 'highlighted', true);
    });

    sigmaInstance.on('clickStage', ({ event }) => {
      if (draggedNode) {
        const rect = vizContainer.getBoundingClientRect();
        const camera = sigmaInstance.getCamera();
        const { x, y } = sigmaInstance.viewportToGraph({ x: event.clientX - rect.left, y: event.clientY - rect.top });

        graph.setNodeAttribute(draggedNode, 'x', x);
        graph.setNodeAttribute(draggedNode, 'y', y);
        graph.setNodeAttribute(draggedNode, 'highlighted', false);
        draggedNode = null;
        sigmaInstance.refresh();
        drawHulls();
      }
    });

    // Cleanup on unmount
    return () => {
      window.removeEventListener('resize', resize);
      if (sigmaInstance) {
        sigmaInstance.kill();
        sigmaInstance = null;
      }
    };
  });

  // Select a paper by ID, highlight and center view
  function selectPaper(paperId: number) {
    const paper = paperMap.get(paperId);
    if (!paper || !sigmaInstance) return;

    updateVisualization(paper);

    // Center camera on selected node
    const node = paper.id.toString();
    const { x, y } = graph.getNodeAttributes(node);
    sigmaInstance.getCamera().animate({ x, y, ratio: 1 }, { duration: 600 });
  }
</script>

<div class="flex flex-col md:flex-row gap-8 p-8 min-h-screen bg-[#181f23]">
  <div class="viz flex-[3_3_0%] bg-[#1c2526] rounded-xl shadow-lg p-6 flex flex-col items-center border border-[#27313a]">
    <h1 class="text-3xl font-bold text-[#e0e6ed] mb-2 tracking-tight">Monaa Lisa: Paper Graph Demo</h1>
    <p class="text-[#8fa2b7] mb-4">Visualizing connections between currently available papers (dummy data)</p>
    <div id="paper-viz" bind:this={vizContainer} class="w-full grow min-h-[400px] rounded-lg border border-[#27313a] shadow-inner bg-[#1c2526]"></div>
  </div>

  <div class="details flex-[1_1_0%] max-w-md bg-[#232b32] rounded-xl shadow-lg p-4 md:p-6 border border-[#27313a]">
    <div class="paper-selector mb-4">
      <input
        type="text"
        placeholder="Search papers..."
        bind:value={filterTerm}
        aria-label="Search papers"
        class="w-full mb-2 px-4 py-2 border border-[#27313a] rounded-md focus:outline-none focus:ring-2 focus:ring-[#3b4a5a] bg-[#1c2526] text-[#e0e6ed] placeholder-[#8fa2b7]"
      />
      <ul class="paper-list max-h-48 overflow-y-auto rounded-md border border-[#27313a] bg-[#232b32] divide-y divide-[#1c2526]">
        {#each filteredPapers as paper}
          <li class:selected={paper.id === selectedPaper?.id}>
            <span
              class="block px-3 py-2 cursor-pointer rounded hover:bg-[#27313a] transition-colors focus:outline-none focus:ring-2 focus:ring-[#3b4a5a] {paper.id === selectedPaper?.id ? 'bg-[#1c2526] font-semibold text-[#e0e6ed]' : 'text-[#b6c2cf]'}"
              role="button"
              tabindex="0"
              on:click={() => selectPaper(paper.id)}
              on:keydown={e => e.key === 'Enter' && selectPaper(paper.id)}
            >
              {paper.title}
            </span>
          </li>
        {/each}
      </ul>
    </div>

    {#if selectedPaper}
      <div class="space-y-2">
        <h2 class="text-2xl font-bold text-[#e0e6ed] mb-2">{selectedPaper.title || 'Untitled'}</h2>
        <p class="text-[#b6c2cf]"><span class="font-semibold text-[#8fa2b7]">Authors:</span> {selectedPaper.authors || 'Unknown'}</p>
        <p class="text-[#b6c2cf]"><span class="font-semibold text-[#8fa2b7]">Summary:</span> {selectedPaper.summary || 'No summary available'}</p>
        <p class="text-[#b6c2cf]"><span class="font-semibold text-[#8fa2b7]">Published:</span> {selectedPaper.published ? new Date(selectedPaper.published).toLocaleDateString() : 'Unknown'}</p>
        <p class="text-[#b6c2cf]"><span class="font-semibold text-[#8fa2b7]">URL:</span> <a href={selectedPaper.url || '#'} target="_blank" rel="noopener noreferrer" class="text-[#8fa2b7] underline hover:text-[#e0e6ed]">{selectedPaper.url || 'No URL'}</a></p>

        <div>
          <p class="font-semibold text-[#8fa2b7] mt-4">Related Papers:</p>
          <ul class="list-disc list-inside ml-2">
            {#each (selectedPaper.related_papers || []) as rid}
              <li>
                <span
                  class="text-[#8fa2b7] underline cursor-pointer hover:text-[#e0e6ed]"
                  role="button"
                  tabindex="0"
                  on:click={() => selectPaper(rid)}
                >
                  {paperMap.get(rid)?.title || 'Unknown'}
                </span>
              </li>
            {:else}
              <li class="text-[#27313a]">None</li>
            {/each}
          </ul>
        </div>

        <div>
          <p class="font-semibold text-[#8fa2b7] mt-4">Citations:</p>
          <ul class="list-disc list-inside ml-2">
            {#each (selectedPaper.citations || []) as cid}
              <li>
                <span
                  class="text-[#8fa2b7] underline cursor-pointer hover:text-[#e0e6ed]"
                  role="button"
                  tabindex="0"
                  on:click={() => selectPaper(cid)}
                >
                  {paperMap.get(cid)?.title || 'Unknown'}
                </span>
              </li>
            {:else}
              <li class="text-[#27313a]">None</li>
            {/each}
          </ul>
        </div>
      </div>
    {:else}
      <div class="text-[#8fa2b7] mt-8 text-center">
        <p>Click on a paper in the list or any node in the graph</p>
      </div>
    {/if}
  </div>
</div>