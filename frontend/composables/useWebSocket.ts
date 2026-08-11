/**
 * WebSocket composable — real-time connection to backend for stage updates.
 */

import { ref, onUnmounted } from "vue";
import { useRuntimeConfig } from "#app";

export function useWebSocket(sessionId: string) {
  const config = useRuntimeConfig();
  const wsBase = (config.public.apiBase as string).replace(/^http/, "ws");

  const messages = ref<any[]>([]);
  const connected = ref(false);
  let ws: WebSocket | null = null;

  function connect() {
    ws = new WebSocket(`${wsBase}/ws/${sessionId}`);

    ws.onopen = () => {
      connected.value = true;
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        messages.value.push(data);
      } catch {
        messages.value.push({ type: "raw", content: event.data });
      }
    };

    ws.onclose = () => {
      connected.value = false;
    };
  }

  function send(message: string) {
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(message);
    }
  }

  function disconnect() {
    ws?.close();
  }

  connect();

  onUnmounted(() => {
    disconnect();
  });

  return { messages, connected, send, disconnect };
}
