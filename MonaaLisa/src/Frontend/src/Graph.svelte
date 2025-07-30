<script lang="ts">
  import { onMount } from 'svelte';
  import Graph from 'graphology';
  import Sigma from 'sigma';
  import { dummyPapers, type Paper } from './testdata/dummyData'; 

  let container: HTMLDivElement | null = null; 
  let selectedPaper: Paper | null = null; 

  //def cluster colors
  //Note: Do we need to define the colors dynamically based on the amount of clusters?
  //Or will we have a set amount of clusterS? - Nick
  const clusterCol: Record<string, string> = {
    A: '#FF6347',
    B: '#4682B4',
    C: '#32CD32',
  };

  onMount(() => {
    //init graphology graph
    const graph = new Graph();

    //add nodes
    dummyPapers.forEach(paper => {
      graph.addNode(paper.id, {
        x: paper.tsne1,
        y: paper.tsne2,
        size: 5 + (paper.citations.length * 2),
        label: paper.title,
        color: clusterCol[paper.cluster] || '#999999',
        paper: paper
      });
    });

    //add edges (aka citations)
    dummyPapers.forEach(paper => {
      paper.citations.forEach(citedId => {
        if (graph.hasNode(citedId)) {
          graph.addEdge(paper.id, citedId, {
            color: '#cccccc',
            size: 1
          });
        }
      });
    });

    //init sigma.js
    if (container) { 
      const renderer = new Sigma(graph, container, {
        renderEdgeLabels: false,
        defaultNodeType: 'circle',
        defaultEdgeType: 'line',
        minCameraRatio: 0.1,
        maxCameraRatio: 10,
      });

      //node hover handling
      renderer.on('enterNode', ({ node }) => {
        const paper = graph.getNodeAttributes(node).paper as Paper;
        selectedPaper = paper;
      });

      renderer.on('leaveNode', () => {
        selectedPaper = null;
      });

      //node click handling
      renderer.on('clickNode', ({ node }) => {
        const paper = graph.getNodeAttributes(node).paper as Paper;
        window.open(paper.url, '_blank');
      });

      //cleanup function: on component destroying
      return () => {
        renderer.kill();
      };
    }
  });
</script>

<style>
  .graph-container {
    width: 100%;
    height: 600px;
    border: 1px solid #ccc;
  }
  .paper-details {
    position: absolute;
    top: 10px;
    right: 10px;
    background: white;
    padding: 10px;
    border: 1px solid #ccc;
    max-width: 300px;
    display: none;
  }
  .paper-details.visible {
    display: block;
  }
</style>

<div class="graph-container" bind:this={container}></div>

{#if selectedPaper}
  <div class="paper-details visible">
    <h3>{selectedPaper.title}</h3>
    <p><strong>authors:</strong> {selectedPaper.authors}</p>
    <p><strong>summary:</strong> {selectedPaper.summary}</p>
    <p><strong>published date:</strong> {new Date(selectedPaper.published).toLocaleDateString()}</p>
    <p><strong>ccitations:</strong> {selectedPaper.citations.length}</p>
  </div>
{/if}