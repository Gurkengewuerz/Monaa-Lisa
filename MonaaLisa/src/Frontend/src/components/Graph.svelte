<script lang="ts">
  import { onMount } from 'svelte';
  import Graph from 'graphology';
  import Sigma from 'sigma';
  import { dummyPapers, type Paper } from '../testdata/dummyData'; 

  let container: HTMLDivElement | null = null; 
  let selectedPaper: Paper | null = null; 
  let selectedNode: string | null = null;
  let renderer: Sigma | null = null;

  //def cluster colors
  //do we need a way to dynamically set cluster colors based on the clusters in the db or
  // do we have a set amount of clusters? - Nick
  const clusterCol: Record<string, string> = {
    A: '#FF6347',
    B: '#4682B4',
    C: '#32CD32',
  };

  onMount(() => {
    //initialize graphology graph
    const graph = new Graph();

    //add nodes
    dummyPapers.forEach(paper => {
      graph.addNode(paper.id, {
        x: paper.tsne1,
        y: paper.tsne2,
        size: 5 + (paper.citations.length * 2),
        label: paper.title,
        color: clusterCol[paper.cluster] || '#999999',
        originalColor: clusterCol[paper.cluster] || '#999999',
        paper: paper
      });
    });

    //add edges (aka citations)
    dummyPapers.forEach(paper => {
      paper.citations.forEach(citedId => {
        if (graph.hasNode(citedId)) {
          graph.addEdge(paper.id, citedId, {
            color: '#cccccc',
            originalColor: '#cccccc',
            size: 1
          });
        }
      });
    });

    //initialize sigma.js
    if (container) { 
      renderer = new Sigma(graph, container, {
        renderEdgeLabels: false,
        defaultNodeType: 'circle',
        defaultEdgeType: 'line',
        minCameraRatio: 0.1,
        maxCameraRatio: 10,
        //node label control
        /*labelFont: 'Arial',
        labelSize: 12,
        labelWeight: 'normal',
        labelColor: { color: '#ffffff' },*/
        renderLabels: false, //disables labels
        
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
        selectedNode = node.toString();

        //reset all components to black with low opacity
        graph.forEachNode((n: string) => {
            graph.setNodeAttribute(n, 'color', 'rgba(0, 0, 0, 0.1)');
        });
        graph.forEachEdge((e: string) => {
            graph.setEdgeAttribute(e, 'color', 'rgba(0, 0, 0, 0.05)');
        });

        //set color of selected node to green
        graph.setNodeAttribute(node, 'color', '#00FF00');

        //look for related nodes (citations and related_papers)
        const paper = graph.getNodeAttributes(node).paper as Paper;
        const relatednodes = new Set<number>([
            ...paper.citations,
            ...paper.related_papers,
            ...dummyPapers
            .filter(p => p.citations.includes(paper.id))
            .map(p => p.id)
        ]);

        //set color of related nodes to yellow
        relatednodes.forEach(relatedId => {
          if (graph.hasNode(relatedId)) {
            graph.setNodeAttribute(relatedId, 'color', '#FFFF00');
          }
        });

        //edge handling
        graph.forEachEdge((edge: string, attributes: any, source: string, target: string) => {
          const sourceId = parseInt(source);
          const targetId = parseInt(target);
          const selectedId = parseInt(node);

          //check if ths edge connects selected node to related node or is between related nodes
          if (
            (sourceId === selectedId && relatednodes.has(targetId)) ||
            (targetId === selectedId && relatednodes.has(sourceId)) ||
            (relatednodes.has(sourceId) && relatednodes.has(targetId))
          ) {
            //set related edge to white
            graph.setEdgeAttribute(edge, 'color', '#FFFFFF');
            graph.setEdgeAttribute(edge, 'size', 2); // Keep thicker edges for visibility
          }
          //unrelated edges stay at low opacity
        });

        //zoom on the selected node
        const nodePosition = graph.getNodeAttributes(node);
        const camera = renderer.getCamera();
        
        const { width, height } = renderer.getDimensions();
        
        camera.animate({
          x: nodePosition.x,
          y: nodePosition.y,
          ratio: 0.15
        }, { 
          duration: 800,
          easing: 'quadInOut'
        });

        renderer.refresh();
      });

      //reset cam pos on canvas click
      renderer.on('clickStage', () => {
        selectedNode = null;
        //restore og colors and sizes
        graph.forEachNode((n: string) => {
          const originalColor = graph.getNodeAttributes(n).originalColor;
          graph.setNodeAttribute(n, 'color', originalColor);
        });
        graph.forEachEdge((e: string) => {
          const originalColor = graph.getEdgeAttributes(e).originalColor;
          graph.setEdgeAttribute(e, 'color', originalColor);
          graph.setEdgeAttribute(e, 'size', 1);
        });
        renderer.getCamera().animatedReset({ duration: 800 });
        renderer.refresh();
      });

      //cleanup function
      return () => {
        if (renderer) {
          renderer.kill();
        }
      };
    }
  });
</script>

<style>
  .graph-container {
    width: 100%;
    height: 600px;
    border: 1px solid #ccc;
    background-color: #1e1e27; 
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

<div class="graph-container" bind:this={container}></div>

{#if selectedPaper}
  <div class="paper-details visible">
    <h3>{selectedPaper.title}</h3>
    <p><strong>aauthors:</strong> {selectedPaper.authors}</p>
    <p><strong>summary:</strong> {selectedPaper.summary}</p>
    <p><strong>published:</strong> {new Date(selectedPaper.published).toLocaleDateString()}</p>
    <p><strong>citations:</strong> {selectedPaper.citations.length}</p>
  </div>
{/if}