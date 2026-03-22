<template>
  <router-view />
</template>

<script setup>
</script>

<style>
/* Global reset — dark Palantir theme */
:root {
  --bg-primary: #0a0a0f;
  --bg-secondary: #12121a;
  --bg-surface: #1a1a26;
  --bg-elevated: #222233;
  --border: #2a2a3a;
  --border-light: #3a3a4a;
  --text-primary: #e8e8f0;
  --text-secondary: #8888aa;
  --text-muted: #555570;
  --accent: #00e87b;
  --accent-dim: #00c868;
  --danger: #ff4455;
  --warning: #ffaa22;
  --info: #4488ff;
  --orange: #ff6b35;
  --font-mono: 'JetBrains Mono', monospace;
  --font-sans: 'Space Grotesk', system-ui, sans-serif;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

#app {
  font-family: var(--font-sans);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: var(--text-primary);
  background: var(--bg-primary);
  min-height: 100vh;
}

::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
::-webkit-scrollbar-track {
  background: var(--bg-secondary);
}
::-webkit-scrollbar-thumb {
  background: var(--border-light);
  border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
  background: var(--text-muted);
}

button {
  font-family: inherit;
  cursor: pointer;
}
</style>
