<!-- Use the TS lang in the Script part please -->
<script lang="ts">
    // Basti: Declare type of var like this:
    //  let x : <type> = <decleration>;
    let today: string = new Date().toLocaleTimeString();
</script>

<!-- 07. June 2025 - Basti - a simple Demo Component to show how to make Components in Svelte for the boys ( - IF THEY EVEN SEE IT =( - ) -->
<div class="toolbar">
    <p class="maintext">Monaa Lisa Demo Component</p>
    <p class="sample-text">
        Hey Jungs hier könnt ihr sehen wie eine Komponente aussieht.
    </p>
    <p class="time">{today}</p>
</div>

<style>
    .toolbar {
        height: 2rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        background-color: #e2e2e2;
        padding: 0 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
    }

    .time {
        font-family: "Courier New", Courier, monospace;
        font-size: 1.2rem;
        letter-spacing: 0.1em;
        background: #222;
        color: #0f0;
        padding: 0.2em 0.7em;
        border-radius: 0.3em;
    }
</style>
