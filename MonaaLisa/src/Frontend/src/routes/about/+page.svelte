<script lang="ts">
    // Basti: Check out the SampleComponent to see how creating a component looks like
    //  This Example shows how to bind a component into a SvelteKit routing page
    import SampleComponent from "./SampleComponent.svelte";

    let current = 0;

    function addCounter() {
        current++;
    }
</script>
<!-- Bind the component here - 7th June 2025 - Basti -->
<SampleComponent/>
<h1>About Monaa Lisa</h1>
<p>Current Count: {current}</p>
<button on:click={addCounter}>Click me!</button>