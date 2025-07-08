<script lang="ts">
  import * as d3 from 'd3';
  import { dummyPapers } from '../testdata/dummyData';
  import type { Paper } from '../testdata/dummyData';
  import { onMount } from 'svelte';

  // Visualization dimensions
  const WIDTH = 800;
  const HEIGHT = 600;


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

    // Build links from related papers
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
      .attr('stroke-width', 1);

    // Draw nodes (circles)
    nodes = group.selectAll<SVGCircleElement, Paper>('circle')
      .data(dummyPapers.filter((p: Paper) => p.id))
      .enter()
      .append('circle')
      .attr('cx', d => xScale(d.tsne1 || 0))
      .attr('cy', d => yScale(d.tsne2 || 0))
      .attr('r', 8)
      .attr('fill', 'steelblue')
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
    return () => d3.select('#paper-viz svg').remove();
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

<style>
  .container {
    display: flex;
    gap: 20px;
    padding: 20px;
  }

  .viz {
    flex: 2;
  }

  .details {
    flex: 1;
    padding: 20px;
    border: 1px solid #ccc;
    border-radius: 5px;
  }

  h1 {
    color: #333;
  }
  h2 {
    color: #555;
  }

  /* search input */
  .paper-selector input {
    width: 100%;
    margin-bottom: 8px;
    padding: 6px 8px;
    border: 1px solid #aaa;
    border-radius: 4px;
  }

  /* paper list */
  .paper-list {
    max-height: 220px;
    overflow-y: auto;
    margin: 0;
    padding-left: 0;
    list-style: none;
    border: 1px solid #ddd;
    border-radius: 4px;
  }
  .paper-list li {
    padding: 4px 8px;
  }
  .paper-list li.selected {
    background: #e7f1ff;
  }

  /* clickable spans */
  .clickable {
    color: #007bff;
    cursor: pointer;
    text-decoration: underline;
  }
  .clickable:hover {
    color: #0056b3;
  }
</style>

<div class="container">
  <div class="viz">
    <h1>monaa lisa frontend early early prototype/demo</h1>
    <p>Visualizing connections between currently available papers (dummy data)</p>
    <div id="paper-viz"></div>
  </div>

  <div class="details">
    <div class="paper-selector">
      <input
        type="text"
        placeholder="Search papers..."
        bind:value={filterTerm}
        aria-label="Search papers"
      />
      <ul class="paper-list">
        {#each filteredPapers as paper}
          <li class:selected={paper.id === selectedPaper?.id}>
            <span
              class="clickable"
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
  <h2>{selectedPaper.title || 'Untitled'}</h2>
  <p><strong>Authors:</strong> {selectedPaper.authors || 'Unknown'}</p>
  <p><strong>Summary:</strong> {selectedPaper.summary || 'No summary available'}</p>
  <p><strong>Published:</strong> 
    {selectedPaper.published
      ? new Date(selectedPaper.published).toLocaleDateString()
      : 'Unknown'}
  </p>
  <p><strong>URL:</strong> 
    <a href={selectedPaper.url || '#'} target="_blank" rel="noopener noreferrer">
      {selectedPaper.url || 'No URL'}
    </a>
  </p>

  <p><strong>Related Papers:</strong></p>
  <ul>
        {#each (selectedPaper.related_papers || []) as rid}
          <li>
            <span
              class="clickable"
              role="button"
              tabindex="0"
              on:click={() => selectPaper(rid)}
            >
              {paperMap.get(rid)?.title || 'Unknown'}
            </span>
          </li>
    {:else}
      <li>None</li>
    {/each}
  </ul>

  <p><strong>Citations:</strong></p>
  <ul>
        {#each (selectedPaper.citations || []) as cid}
          <li>
            <span
              class="clickable"
              role="button"
              tabindex="0"
              on:click={() => selectPaper(cid)}
            >
              {paperMap.get(cid)?.title || 'Unknown'}
            </span>
          </li>
    {:else}
      <li>None</li>
    {/each}
  </ul>
{:else}
  <p>Click on a paper in the list or any node in the graph</p>
{/if}  </div>
</div>