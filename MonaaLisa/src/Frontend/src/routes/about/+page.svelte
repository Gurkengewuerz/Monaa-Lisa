<script>
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