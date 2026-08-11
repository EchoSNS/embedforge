<template>
  <div class="min-h-screen bg-background transition-colors duration-300" :class="{ dark: isDark }">
    <NuxtPage />
  </div>
</template>

<script setup lang="ts">
import { useColorMode } from "@vueuse/core";

const { store: isDark } = useColorMode({
  attribute: "class",
  modes: { dark: "dark", light: "" },
});

provide("toggleDark", () => {
  isDark.value = isDark.value === "dark" ? "light" : "dark";
});
provide("isDark", isDark);
</script>
