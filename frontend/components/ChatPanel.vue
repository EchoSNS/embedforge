<template>
  <div class="border-t">
    <div class="flex items-center gap-2 px-4 py-2">
      <span class="text-xs text-muted-foreground">💬</span>
      <input
        v-model="message"
        class="flex-1 rounded-md border bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
        placeholder="Ask a clarifying question about this stage..."
        @keyup.enter="sendMessage"
      />
      <button
        class="rounded-md bg-primary px-3 py-1.5 text-xs text-primary-foreground hover:opacity-90"
        @click="sendMessage"
      >
        Send
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useWebSocket } from "~/composables/useWebSocket";

const props = defineProps<{
  sessionId: string;
}>();

const message = ref("");
const { send } = useWebSocket(props.sessionId);

function sendMessage() {
  if (!message.value.trim()) return;
  send(message.value);
  message.value = "";
}
</script>
