<script lang="ts">
  import * as d3 from 'd3';
import { dummyPapers } from '../testdata/dummyData';
  import type { Paper } from '../testdata/dummyData';
  import { onMount } from 'svelte';

  import "../app.css";


  // Initial visualization dimensions
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

  // D3 elements and scales
  let svg: d3.Selection<SVGSVGElement, unknown, null, undefined>;
  let group: d3.Selection<SVGGElement, unknown, null, undefined>;
  let nodes: d3.Selection<SVGCircleElement, Paper, SVGGElement, unknown>;
  let links: d3.Selection<SVGLineElement, { source: Paper; target: Paper }, SVGGElement, unknown>;
  let hulls: d3.Selection<SVGPathElement, {cluster: string, points: [number, number][]}, SVGGElement, unknown>;
  let xScale: d3.ScaleLinear<number, number, never>;
  let yScale: d3.ScaleLinear<number, number, never>;
  let zoom: d3.ZoomBehavior<Element, unknown>;

  // Update node and link styles based on selected paper
  function updateVisualization(selected: Paper | null) {
    selectedPaper = selected;

    if (selected && selected.id) {
      const connectedIds = new Set<number>([
        selected.id,
        ...(selected.related_papers || []),
        ...(selected.citations || [])
      ]);

      nodes.each(function (nodeData: Paper) {
        const isSelected = nodeData.id === selected.id;
        const isConnected = connectedIds.has(nodeData.id);

        d3.select(this as SVGCircleElement)
          .attr('fill', isSelected ? 'green' : isConnected ? 'yellow' : '#d3d3d3')
          .attr('opacity', isConnected ? 1 : 0.2)
          .attr('r', isSelected ? 12 : isConnected ? 10 : 8);
      });

      links.each(function (linkData: { source: Paper; target: Paper }) {
        const srcId = linkData.source?.id;
        const tgtId = linkData.target?.id;
        const connected =
          srcId && tgtId && connectedIds.has(srcId) && connectedIds.has(tgtId);

        d3.select(this as SVGLineElement)
          .attr('stroke', connected ? 'gray' : '#d3d3d3')
          .attr('opacity', connected ? 1 : 0.05);
      });
    } else {
      // Reset all elements to default style
      nodes
        .attr('fill', 'steelblue')
        .attr('opacity', 1)
        .attr('r', 8);

      links
        .attr('stroke', 'gray')
        .attr('opacity', 1);
    }
  }

  // Initialize visualization on component mount
  onMount(() => {
    const margin = { top: 20, right: 20, bottom: 20, left: 20 };
    // Responsive: get container size
    const resize = () => {
      if (vizContainer) {
        WIDTH = vizContainer.clientWidth;
        HEIGHT = vizContainer.clientHeight;
      }
    };
    resize();
    window.addEventListener('resize', resize);

    //@ts-expect-error d3 types mismatch, works at runtime
    svg = d3.select('#paper-viz')
      .append('svg')
      .attr('width', WIDTH)
      .attr('height', HEIGHT)
      .style('background-color', '#1C2526');

    group = svg.append('g');

    // Create scales with padding
    const xExtent = d3.extent(dummyPapers, (d: Paper) => d.tsne1 || 0) as [number, number];
    const yExtent = d3.extent(dummyPapers, (d: Paper) => d.tsne2 || 0) as [number, number];

    xScale = d3.scaleLinear()
      .domain([xExtent[0] - 5, xExtent[1] + 5])
      .range([margin.left, WIDTH - margin.right]);

    yScale = d3.scaleLinear()
      .domain([yExtent[0] - 5, yExtent[1] + 5])
      .range([HEIGHT - margin.bottom, margin.top]);

    // --- CLUSTER HULLS ---
    // Group papers by cluster
    const clusters: Record<string, Paper[]> = {};
    dummyPapers.forEach(p => {
      if (!clusters[p.cluster]) clusters[p.cluster] = [];
      clusters[p.cluster].push(p);
    });

    // Compute convex hulls for each cluster
    const hullData = Object.entries(clusters).map(([cluster, papers]) => {
      // Points in [x, y] for d3.polygonHull
      const points: [number, number][] = papers.map(p => [xScale(p.tsne1), yScale(p.tsne2)]);
      // d3.polygonHull returns null if <3 points
      const hull = points.length >= 3 ? d3.polygonHull(points) : points;
      return { cluster, points: hull || points };
    });

    // Draw hulls (paths)
    hulls = group.selectAll<SVGPathElement, {cluster: string, points: [number, number][]}>("path.cluster-hull")
      .data(hullData)
      .enter()
      .append("path")
      .attr("class", "cluster-hull")
      .attr("d", d => d.points.length >= 3 ?
        "M" + d.points.map(p => p.join(",")).join("L") + "Z" :
        null)
      .attr("fill", (d, i) => ["#2a3a44", "#3b4a5a", "#1e2d3a", "#4a3b5a"][i % 4])
      .attr("fill-opacity", 0.18)
      .attr("stroke", (d, i) => ["#4fd1c5", "#f6ad55", "#63b3ed", "#f56565"][i % 4])
      .attr("stroke-width", 3);

    // --- LINKS ---
    const linkData: { source: Paper; target: Paper }[] = [];
    dummyPapers.forEach((paper: Paper) => {
      (paper.related_papers || []).forEach((relId: number) => {
        const target = dummyPapers.find((p: Paper) => p.id === relId);
        if (target) linkData.push({ source: paper, target });
      });
    });

    // Draw links (lines)
    links = group.selectAll<SVGLineElement, { source: Paper; target: Paper }>('line')
      .data(linkData)
      .enter()
      .append('line')
      .attr('x1', d => xScale(d.source.tsne1 || 0))
      .attr('y1', d => yScale(d.source.tsne2 || 0))
      .attr('x2', d => xScale(d.target.tsne1 || 0))
      .attr('y2', d => yScale(d.target.tsne2 || 0))
      .attr('stroke', 'gray')
      .attr('stroke-width', 1)
      .attr('opacity', 0.5);

    // --- NODES ---
    nodes = group.selectAll<SVGCircleElement, Paper>('circle')
      .data(dummyPapers.filter((p: Paper) => p.id))
      .enter()
      .append('circle')
      .attr('cx', d => xScale(d.tsne1 || 0))
      .attr('cy', d => yScale(d.tsne2 || 0))
      .attr('r', 8)
      .attr('fill', d => {
        // Color by cluster
        if (d.cluster === 'A') return '#4fd1c5';
        if (d.cluster === 'B') return '#f6ad55';
        if (d.cluster === 'C') return '#63b3ed';
        return '#b794f4';
      })
      .attr('stroke', 'black')
      .attr('stroke-width', 1)
      .on('click', (event: MouseEvent, d: Paper) => {
        event.stopPropagation();
        updateVisualization(d);
      })
      .call(
        d3.drag<SVGCircleElement, Paper>()
          .on('start', function () {
            d3.select(this).raise().attr('stroke-width', 2);
          })
          .on('drag', function (event: any, d: Paper) {
            const rect = svg.node()!.getBoundingClientRect();
            const transform = d3.zoomTransform(svg.node()!);

            // Calculate new coordinates accounting for zoom/pan
            const mouseX = event.sourceEvent.clientX - rect.left;
            const mouseY = event.sourceEvent.clientY - rect.top;

            d.tsne1 = xScale.invert((mouseX - transform.x) / transform.k);
            d.tsne2 = yScale.invert((mouseY - transform.y) / transform.k);

            // Update node position
            d3.select(this as SVGCircleElement)
              .attr('cx', xScale(d.tsne1))
              .attr('cy', yScale(d.tsne2));

            // Update links connected to this node
            links
              .attr('x1', l => xScale(l.source.tsne1 || 0))
              .attr('y1', l => yScale(l.source.tsne2 || 0))
              .attr('x2', l => xScale(l.target.tsne1 || 0))
              .attr('y2', l => yScale(l.target.tsne2 || 0));

            // Update hulls
            hulls.attr('d', d => d.points.length >= 3 ?
              "M" + d.points.map(p => p.join(",")).join("L") + "Z" : null);
          })
          .on('end', function () {
            d3.select(this).attr('stroke-width', 1);
          })
      );

    // Add tooltips showing paper titles
    nodes.append('title').text(d => d.title || 'Untitled');

    // Zoom behavior setup
    zoom = d3.zoom<Element, unknown>()
      .scaleExtent([0.5, 5])
      .on('zoom', (e) => group.attr('transform', e.transform));

    svg.call(zoom);

    // Clicking SVG background clears selection
    svg.on('click', () => updateVisualization(null));

    // Cleanup SVG on component unmount
    return () => {
      window.removeEventListener('resize', resize);
      d3.select('#paper-viz svg').remove();
    };
  });

  // Select a paper by ID, highlight and center view
  function selectPaper(paperId: number) {
    const paper = paperMap.get(paperId);
    if (!paper) return;

    updateVisualization(paper);

    // Get current zoom scale
    const { k } = d3.zoomTransform(svg.node()!);

    // Calculate translation to center node
    const translateX = WIDTH / 2 - xScale(paper.tsne1 || 0) * k;
    const translateY = HEIGHT / 2 - yScale(paper.tsne2 || 0) * k;

    // Animate zoom transform to center on selected node
    svg.transition()
      .duration(600)
      .call(
        zoom.transform,
        d3.zoomIdentity.translate(translateX, translateY).scale(k)
      );
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