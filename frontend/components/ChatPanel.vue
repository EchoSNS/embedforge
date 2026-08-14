<template>
  <div class="border-t bg-card/50 backdrop-blur-sm">
    <!-- Message history -->
    <Transition name="fade-slide">
      <div v-if="expanded && displayMessages.length" ref="messagesContainer" class="max-h-52 overflow-y-auto border-b px-4 py-3 space-y-2">
        <div
          v-for="(msg, i) in displayMessages"
          :key="i"
          class="flex gap-2.5 animate-fade-in"
          :class="{ 'flex-row-reverse': msg.role === 'user' }"
        >
          <div
            class="flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs"
            :class="msg.role === 'assistant' ? 'bg-primary/10 text-primary' : 'bg-secondary text-muted-foreground'"
          >
            <Bot v-if="msg.role === 'assistant'" class="h-3 w-3" />
            <User v-else class="h-3 w-3" />
          </div>
          <div
            class="rounded-xl px-3 py-1.5 text-xs max-w-[80%]"
            :class="msg.role === 'assistant' ? 'bg-secondary text-foreground' : 'bg-primary/10 text-foreground'"
          >
            {{ msg.content }}
          </div>
        </div>
        <!-- Typing indicator -->
        <div v-if="typing" class="flex gap-2.5 animate-fade-in">
          <div class="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary text-xs">
            <Bot class="h-3 w-3" />
          </div>
          <div class="rounded-xl bg-secondary px-3 py-1.5 text-xs flex items-center gap-1">
            <span class="h-1.5 w-1.5 rounded-full bg-muted-foreground animate-bounce [animation-delay:0ms]" />
            <span class="h-1.5 w-1.5 rounded-full bg-muted-foreground animate-bounce [animation-delay:150ms]" />
            <span class="h-1.5 w-1.5 rounded-full bg-muted-foreground animate-bounce [animation-delay:300ms]" />
          </div>
        </div>
      </div>
    </Transition>

    <!-- Input row -->
    <div class="flex items-center gap-2 px-4 py-2.5">
      <button
        v-if="displayMessages.length"
        class="flex items-center gap-1 rounded-full px-2 py-1 text-xs text-muted-foreground hover:bg-accent transition-all duration-200"
        @click="expanded = !expanded"
      >
        <MessageSquare class="h-3 w-3" />
        {{ displayMessages.length }}
        <ChevronUp class="h-3 w-3 transition-transform" :class="{ 'rotate-180': expanded }" />
      </button>
      <div class="relative flex-1">
        <input
          v-model="message"
          class="w-full rounded-xl border bg-background px-4 py-2 pr-8 text-sm focus:outline-none focus:ring-2 focus:ring-ring/50 transition-all duration-200 placeholder:text-muted-foreground/60"
          placeholder="Ask about this stage, requirements, or get suggestions…"
          @keyup.enter="sendMessage"
        />
        <span
          v-if="connected"
          class="absolute right-3 top-1/2 -translate-y-1/2 h-2 w-2 rounded-full bg-[hsl(var(--success))]"
          title="WebSocket connected"
        />
      </div>
      <button
        class="flex items-center gap-1 rounded-xl bg-primary px-3 py-2 text-xs font-medium text-primary-foreground hover:opacity-90 transition-all duration-200 active:scale-95 disabled:opacity-50"
        :disabled="!message.trim() || typing"
        @click="sendMessage"
      >
        <Send class="h-3 w-3" />
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, watch } from "vue";
import { Send, MessageSquare, ChevronUp, Bot, User } from "@lucide/vue";
import { useWebSocket } from "~/composables/useWebSocket";

const props = defineProps<{
  sessionId: string;
}>();

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

const message = ref("");
const expanded = ref(false);
const typing = ref(false);
const messagesContainer = ref<HTMLElement | null>(null);
const chatHistory = ref<ChatMessage[]>([]);
const { messages, connected, send } = useWebSocket(props.sessionId);

// Convert raw WS messages to display format
const displayMessages = computed(() => chatHistory.value);

watch(() => messages.value.length, () => {
  const latest = messages.value[messages.value.length - 1];
  if (!latest) return;

  if (latest.type === "typing") {
    typing.value = true;
  } else if (latest.type === "chat_response") {
    typing.value = false;
    chatHistory.value.push({ role: "assistant", content: latest.content });
  }

  nextTick(() => {
    messagesContainer.value?.scrollTo({ top: messagesContainer.value.scrollHeight, behavior: "smooth" });
  });
});

function sendMessage() {
  if (!message.value.trim() || typing.value) return;
  chatHistory.value.push({ role: "user", content: message.value });
  send(message.value);
  message.value = "";
  expanded.value = true;
}
</script>
