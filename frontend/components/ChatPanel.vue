<template>
  <div class="border-t bg-card/50 backdrop-blur-sm">
    <!-- Message history (collapsed by default, expandable) -->
    <Transition name="fade-slide">
      <div v-if="expanded && messages.length" class="max-h-48 overflow-y-auto border-b px-4 py-2 space-y-2">
        <div
          v-for="(msg, i) in messages"
          :key="i"
          class="flex gap-2 text-xs animate-fade-in"
        >
          <span class="text-muted-foreground shrink-0">
            {{ msg.type === 'ack' ? '🤖' : '💬' }}
          </span>
          <span class="text-foreground/80">
            {{ msg.type === 'ack' ? `Received: ${msg.received}` : msg.content || JSON.stringify(msg) }}
          </span>
        </div>
      </div>
    </Transition>

    <div class="flex items-center gap-2 px-4 py-2.5">
      <button
        v-if="messages.length"
        class="rounded-full p-1.5 text-xs text-muted-foreground hover:bg-accent transition-all duration-200"
        @click="expanded = !expanded"
      >
        {{ expanded ? '▼' : '▲' }} {{ messages.length }}
      </button>
      <div class="relative flex-1">
        <input
          v-model="message"
          class="w-full rounded-xl border bg-background px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring/50 transition-all duration-200 placeholder:text-muted-foreground/60"
          placeholder="Ask a clarifying question about this stage..."
          @keyup.enter="sendMessage"
        />
        <span
          v-if="connected"
          class="absolute right-3 top-1/2 -translate-y-1/2 h-2 w-2 rounded-full bg-green-500"
          title="Connected"
        />
      </div>
      <button
        class="rounded-xl bg-primary px-4 py-2 text-xs font-medium text-primary-foreground hover:opacity-90 transition-all duration-200 active:scale-95 disabled:opacity-50"
        :disabled="!message.trim()"
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
const expanded = ref(false);
const { messages, connected, send } = useWebSocket(props.sessionId);

function sendMessage() {
  if (!message.value.trim()) return;
  send(message.value);
  message.value = "";
  expanded.value = true;
}
</script>
