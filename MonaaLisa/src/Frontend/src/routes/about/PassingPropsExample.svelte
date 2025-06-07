<script lang="ts">
    // Basti: Use the export Tag to act as an "constructor" - when the Component gets mounted you can parse a value for this var.
    //  Check out how to parse a value in the +page.svelte
    export let user: string;
</script>

<p>Greetings to {user}!</p>
