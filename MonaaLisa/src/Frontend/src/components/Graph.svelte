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
    A: '#CC6666', 
    B: '#66B2B2', 
    C: '#9966CC', 
    D: '#CC66B2', 
    E: '#6699CC', 
    F: '#FF4500',
    G: '#00CED1',
  };

  onMount(() => {
    //initialize graphology graph
    const graph = new Graph();

    //add nodes
    dummyPapers.forEach(paper => {
      graph.addNode(paper.id, {
        x: paper.tsne1,
        y: paper.tsne2,
        size: 5,
        label: paper.title,
        color: clusterCol[paper.cluster] || '#999999',
        originalColor: clusterCol[paper.cluster] || '#999999',
        paper: paper
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

        //ad edges dynamically for selected node and related nodes
        const selectedId = parseInt(node);
        
        //add edges from selected node to its citations
        paper.citations.forEach(citedId => {
          if (graph.hasNode(citedId) && !graph.hasEdge(selectedId, citedId)) {
            graph.addEdge(selectedId, citedId, {
              color: '#FFFFFF',
              size: 2
            });
          }
        });

        //add edges from papers that cite the selected paper
        dummyPapers
          .filter(p => p.citations.includes(selectedId))
          .forEach(citingPaper => {
            if (graph.hasNode(citingPaper.id) && !graph.hasEdge(citingPaper.id, selectedId)) {
              graph.addEdge(citingPaper.id, selectedId, {
                color: '#FFFFFF',
                size: 2
              });
            }
          });

        //add edges between related nodes if they exist in related_papers
        paper.related_papers.forEach(relatedId => {
          if (graph.hasNode(relatedId) && !graph.hasEdge(selectedId, relatedId)) {
            graph.addEdge(selectedId, relatedId, {
              color: '#FFFFFF',
              size: 2
            });
          }
        });

        //zoom on the selected node
        const nodePosition = graph.getNodeAttributes(node);
        const camera = renderer.getCamera();
        
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
        
        //restore original node colors
        graph.forEachNode((n: string) => {
          const originalColor = graph.getNodeAttributes(n).originalColor;
          graph.setNodeAttribute(n, 'color', originalColor);
        });
        
        // REMOVE ALL EDGES
        const edgesToRemove = graph.edges();
        edgesToRemove.forEach(edge => {
          graph.dropEdge(edge);
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
    <p><strong>authors:</strong> {selectedPaper.authors}</p>
    <p><strong>summary:</strong> {selectedPaper.summary}</p>
    <p><strong>published:</strong> {new Date(selectedPaper.published).toLocaleDateString()}</p>
    <p><strong>citations:</strong> {selectedPaper.citations.length}</p>
  </div>
{/if}