<script lang="ts">
    let showAboutModal = false;
</script>

<div class="header">
    <div class="header-accent-line"></div>
    <div class="header-inner">
        <span class="header-logo">M-L</span>
        <h1 class="header-title">
            Monaa-Lisa <span class="header-divider">-</span>
            <span class="header-subtitle">Academic Paper Visualization</span>
        </h1>
        <button class="about-btn" on:click={() => (showAboutModal = true)}
            >About Us</button
        >
    </div>
</div>

{#if showAboutModal}
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <!-- svelte-ignore a11y-no-static-element-interactions -->
    <div class="modal-backdrop" on:click={() => (showAboutModal = false)}>
        <div class="modal-content" on:click|stopPropagation>
            <button
                class="modal-close"
                on:click={() => (showAboutModal = false)}>×</button
            >
            <h2>About Us</h2>
            <p>Dieses Projekt wurde von xy erstellt.</p>
        </div>
    </div>
{/if}

<style>
    .header {
        position: relative;
        padding: 0;
        background: var(--bg-secondary, #141530);
        border-bottom: 1px solid var(--glass-border, rgba(255, 255, 255, 0.08));
        z-index: 100;
        flex-shrink: 0;
        overflow: hidden;
    }

    .header-accent-line {
        position: absolute;
        bottom: 0;
        left: 0;
        right: 0;
        height: 2px;
        background: var(
            --gradient-header,
            linear-gradient(90deg, #9333ea, #e839a0, #22d3ee)
        );
        opacity: 0.7;
    }

    .header-inner {
        display: flex;
        align-items: center;
        gap: 14px;
        padding: 10px 20px;
    }

    .header-logo {
        font-size: 14px;
        font-weight: 800;
        letter-spacing: 2px;
        color: var(--text-primary, #f0f0f8);
        padding: 4px 8px;
        border: 1.5px solid rgba(147, 51, 234, 0.5);
        border-radius: 4px;
        background: linear-gradient(
            135deg,
            rgba(147, 51, 234, 0.15),
            rgba(232, 57, 160, 0.1)
        );
        text-shadow: 0 0 8px rgba(147, 51, 234, 0.4);
        flex-shrink: 0;
    }

    .header-title {
        color: var(--text-primary, #f0f0f8);
        font-size: 15px;
        margin: 0;
        font-weight: 600;
        letter-spacing: 0.5px;
        white-space: nowrap;
    }

    .header-divider {
        color: var(--text-muted, #6b6b8d);
        margin: 0 2px;
        font-weight: 300;
    }

    .header-subtitle {
        color: var(--text-secondary, #a8a8c8);
        font-weight: 400;
    }

    .about-btn {
        margin-left: auto;
        background: var(--glass-bg, rgba(20, 22, 50, 0.55));
        border: 1px solid var(--border-subtle, rgba(147, 51, 234, 0.25));
        color: var(--text-secondary, #a8a8c8);
        border-radius: var(--radius-sm, 8px);
        padding: 5px 14px;
        cursor: pointer;
        font-size: 12px;
        font-weight: 500;
        transition: all 0.2s ease;
        white-space: nowrap;
    }
    .about-btn:hover {
        background: rgba(147, 51, 234, 0.2);
        border-color: rgba(147, 51, 234, 0.5);
        color: var(--text-primary, #f0f0f8);
    }

    .modal-backdrop {
        position: fixed;
        inset: 0;
        background: rgba(0, 0, 0, 0.6);
        z-index: 1000;
        display: flex;
        align-items: center;
        justify-content: center;
        backdrop-filter: blur(4px);
    }

    .modal-content {
        background: var(--bg-secondary, #141530);
        border: 1px solid var(--glass-border, rgba(255, 255, 255, 0.1));
        border-radius: var(--radius-md, 12px);
        padding: 28px 32px;
        max-width: 480px;
        width: 90%;
        position: relative;
        color: var(--text-primary, #f0f0f8);
        box-shadow: 0 16px 48px rgba(0, 0, 0, 0.5);
    }
    .modal-content h2 {
        margin: 0 0 14px;
        font-size: 18px;
        font-weight: 600;
    }
    .modal-content p {
        margin: 0;
        font-size: 14px;
        line-height: 1.6;
        color: var(--text-secondary, #a8a8c8);
    }

    .modal-close {
        position: absolute;
        top: 12px;
        right: 14px;
        background: none;
        border: none;
        color: var(--text-muted, #6b6b8d);
        font-size: 22px;
        cursor: pointer;
        line-height: 1;
        padding: 2px 6px;
        border-radius: 4px;
        transition: color 0.15s ease;
    }
    .modal-close:hover {
        color: var(--text-primary, #f0f0f8);
    }
</style>
