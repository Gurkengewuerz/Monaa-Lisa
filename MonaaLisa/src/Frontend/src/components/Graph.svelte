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

    //retrieve paper data and collect related node ids
    const paper = graph.getNodeAttributes(nodeId).paper as Paper;
    const dataSource = useDummyData ? dummyPapers : papers;
    const relatedNodes = new Set<number>([
      ...paper.citations,
      ...paper.related_papers,
      ...dataSource
        .filter(p => p.citations.includes(paper.id))
        .map(p => p.id)
    ]);

    //highlight related nodes in yellow
    relatedNodes.forEach(relatedId => {
      if (graph.hasNode(relatedId)) {
        graph.setNodeAttribute(relatedId, 'color', '#FFFF00');
      }
    });

    //add edges for citations, citing papers, and related papers
    const selectedId = parseInt(nodeId);

    //edges to cited papers
    paper.citations.forEach(citedId => {
      if (graph.hasNode(citedId)) {
        graph.addEdge(selectedId, citedId, {
          color: '#FFFFFF',
          size: 2
        });
      }
    });

    //edges from citing papers
    dataSource
      .filter(p => p.citations.includes(selectedId))
      .forEach(citingPaper => {
        if (graph.hasNode(citingPaper.id)) {
          graph.addEdge(citingPaper.id, selectedId, {
            color: '#FFFFFF',
            size: 2
          });
        }
      });

    //edges to related papers
    paper.related_papers.forEach(relatedId => {
      if (graph.hasNode(relatedId)) {
        graph.addEdge(selectedId, relatedId, {
          color: '#FFFFFF',
          size: 2
        });
      }
    });

    //zoom to the selected node
    const nodePosition = graph.getNodeAttributes(nodeId);
    const camera = renderer.getCamera();
    camera.animate({
      x: nodePosition.x,
      y: nodePosition.y,
      ratio: 0.15
    }, {
      duration: 800,
      easing: 'quadInOut'
    });

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

      //handle node hover: show paper details
      renderer.on('enterNode', ({ node }) => {
        const paper = graph.getNodeAttributes(node).paper as Paper;
        selectedPaper = paper;
      });

      renderer.on('leaveNode', () => {
        selectedPaper = null;
      });

      //handle node click: select node and emit event
      renderer.on('clickNode', ({ node }) => {
        selectNodeById(node.toString());
        dispatch('nodeSelected', node.toString());
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

      //cleanup: destroy renderer on unmount
      return () => {
        if (renderer) renderer.kill();
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