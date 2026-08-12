<template>
  <div class="min-h-screen bg-background transition-colors duration-300">
    <NuxtPage />
  </div>
</template>

<script setup lang="ts">
import { useDark, useToggle } from "@vueuse/core";
import { provide } from "vue";

const isDark = useDark({ attribute: "class", valueDark: "dark", valueLight: "" });
const toggleDark = useToggle(isDark);

provide("isDark", isDark);
provide("toggleDark", toggleDark);
</script>
