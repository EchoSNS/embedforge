/**
 * SSE-based activity log stream from the backend.
 */

import { ref, onUnmounted } from "vue";
import { useRuntimeConfig } from "#app";

export interface LogEntry {
  level: "info" | "step" | "warn" | "error" | "ai" | "success";
  message: string;
  detail: string;
  timestamp: number;
}

export function useActivityLog() {
  const config = useRuntimeConfig();
  const apiBase = config.public.apiBase as string;

  const entries = ref<LogEntry[]>([]);
  const connected = ref(false);
  let eventSource: EventSource | null = null;

  function connect() {
    if (eventSource) return;
    eventSource = new EventSource(`${apiBase}/api/logs/stream`);

    eventSource.onopen = () => { connected.value = true; };

    eventSource.onmessage = (event) => {
      try {
        const entry: LogEntry = JSON.parse(event.data);
        entries.value.push(entry);
        if (entries.value.length > 200) entries.value.shift();
      } catch { /* ignore parse errors */ }
    };

    eventSource.onerror = () => {
      connected.value = false;
      eventSource?.close();
      eventSource = null;
      // Reconnect after 3s
      setTimeout(connect, 3000);
    };
  }

  function disconnect() {
    eventSource?.close();
    eventSource = null;
    connected.value = false;
  }

  function clear() {
    entries.value = [];
  }

  onUnmounted(disconnect);

  return { entries, connected, connect, disconnect, clear };
}
