<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { onMount } from 'svelte';
  import Graph from 'graphology';
  import Sigma from 'sigma';
  import { dummyPapers, type Paper } from '../testdata/dummyData'; //temporary import for the dummy thick data; replace with api later

  /**
   * array of papers to display in the graph.
   * passed from the parent component.
   * @type {Paper[]}
   */
  export let papers: Paper[] = [];

  /**
   * id of the currently selected paper
   * used for external selection control
   * @type {string | null}
   */
  export let selectedPaperId: string | null = null;

  /**
   * flag to use dummy data for showcasing.
   * when true, uses dummypapers instead of the papers prop.
   * set to true for demo, false for real data.
   * @type {boolean}
   */
  export let useDummyData: boolean = true;

  //internal state variables for component management
  let container: HTMLDivElement | null = null;
  let selectedPaper: Paper | null = null;
  let selectedNode: string | null = null;
  let renderer: Sigma | null = null;
  let graph: Graph | null = null;

  //add cache for quick paper lookup
  let paperCache: Map<string, Paper> = new Map();

  //add debounce for hover
  let hoverTimeout: number | null = null;

  const dispatch = createEventDispatcher();

  //cluster color mapping for visual grouping
  //todo: figure out if we even need this later on or if cluster colors are static instead of dynamic
  const clusterCol: Record<string, string> = {
    A: '#CC6666',
    B: '#66B2B2',
    C: '#9966CC',
    D: '#CC66B2',
    E: '#6699CC',
    F: '#FF4500',
    G: '#00CED1',
  };

  /**
   * selects and highlights a node in the graph, updating visuals and connections.
   * clears edges, resets colors, highlights related nodes, adds edges, and zooms.
   * @param {string} nodeId - the id of the node to select.
   */
  function selectNodeById(nodeId: string) {
    if (!graph || !renderer || !graph.hasNode(nodeId)) return;

    //clear all edges to reset the view
    const edgesToRemove = graph.edges();
    edgesToRemove.forEach(edge => {
      graph.dropEdge(edge);
    });

    //set all nodes to a semi-transparent black to help focus on selections
    graph.forEachNode((n: string) => {
      graph.setNodeAttribute(n, 'color', 'rgba(0, 0, 0, 0.1)');
    });

    //highlight selected node in green
    graph.setNodeAttribute(nodeId, 'color', '#00FF00');

    //retrieve paper data and collect only direct citations (no related or citing papers)
    const paper = graph.getNodeAttributes(nodeId).paper as Paper;
    const relatedNodes = new Set<number>(paper.citations); //only citations

    //highlight related nodes in yellow
    relatedNodes.forEach(relatedId => {
      if (graph.hasNode(relatedId.toString())) {
        graph.setNodeAttribute(relatedId.toString(), 'color', '#FFFF00');
      }
    });

    //add edges only for citations
    //edges to cited papers
    paper.citations.forEach(citedId => {
      if (graph.hasNode(citedId.toString())) {
        graph.addEdge(nodeId, citedId.toString(), {
          color: '#FFFFFF',
          size: 0.5
        });
      }
    });

    //zoom to the selected node
    const nodePosition = graph.getNodeAttributes(nodeId);
    console.log('Zooming to node:', nodeId, 'Position:', nodePosition.x, nodePosition.y);
    const camera = renderer.getCamera();
    camera.animatedSetState({
      x: nodePosition.x,
      y: nodePosition.y,
      ratio: 1  // Zoom in closer to the selected node for better focus
    }, { duration: 800 });  // Smooth animation like stage reset

    selectedNode = nodeId;
    renderer.refresh();
  }

  //react to prop changes: update selection when selectedpaperid changes
  $: if (selectedPaperId && selectedPaperId !== selectedNode && graph && renderer) {
    selectNodeById(selectedPaperId);
  }

  onMount(() => {
    //initialize graphology graph for data storage
    graph = new Graph();

    //determine data source: use dummypapers if flag is set, otherwise use papers prop
    //to use dummy data: set usedummydata={true} in parent component
    //to use real data: pass papers prop from api/db and set usedummydata={false}
    //later, replace dummypapers import with api call in parent
    const dataSource = useDummyData ? dummyPapers : papers;

    //populate graph with nodes from the selected data source
    dataSource.forEach(paper => {
      
      const scaleFactor = 0.5; //adjust as needed for better spacing
      const scaledX = paper.tsne1 * scaleFactor;
      const scaledY = paper.tsne2 * scaleFactor;

      graph.addNode(paper.id.toString(), {
        x: scaledX,
        y: scaledY,
        size: 1.5,
        label: paper.title,
        color: clusterCol[paper.cluster] || '#999999',
        originalColor: clusterCol[paper.cluster] || '#999999',
        paper: paper
      });

      //cache paper for fast lookup
      paperCache.set(paper.id.toString(), paper);
    });

    //initialize sigma renderer for visualization
    if (container) {
      renderer = new Sigma(graph, container, {
        renderEdgeLabels: false,
        defaultNodeType: 'circle',
        defaultEdgeType: 'line',
        minCameraRatio: 0.1,
        maxCameraRatio: 10,
        //labels disabled for clarity; use sidebar/search instead
        renderLabels: false,
      });

      //handle node hover: show paper details with debounce
      renderer.on('enterNode', ({ node }) => {
        //clear previous timeout
        if (hoverTimeout) clearTimeout(hoverTimeout);
        
        //debounce: delay setting selectedPaper by 100ms
        hoverTimeout = setTimeout(() => {
          selectedPaper = paperCache.get(node) || null;
        }, 100);
      });

      renderer.on('leaveNode', () => {
        //clear timeout and hide details
        if (hoverTimeout) clearTimeout(hoverTimeout);
        selectedPaper = null;
      });

      //handle node click: select node and emit event
      renderer.on('clickNode', ({ node }) => {
        selectNodeById(node);
        dispatch('nodeSelected', node);
      });

      //handle stage click: deselect and reset view
      renderer.on('clickStage', () => {
        selectedNode = null;

        //restore original node colors
        graph.forEachNode((n: string) => {
          const originalColor = graph.getNodeAttributes(n).originalColor;
          graph.setNodeAttribute(n, 'color', originalColor);
        });

        //remove all edges
        const edgesToRemove = graph.edges();
        edgesToRemove.forEach(edge => {
          graph.dropEdge(edge);
        });

        renderer.getCamera().animatedReset({ duration: 800 });
        renderer.refresh();

        dispatch('nodeDeselected');
      });

      //cleanup: destroy renderer and clear cache on unmount
      return () => {
        if (renderer) renderer.kill();
        paperCache.clear();
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