// Thin API layer for StyleScan. All network calls go through EXPO_PUBLIC_BACKEND_URL.
const BASE = process.env.EXPO_PUBLIC_BACKEND_URL;

export type Conversation = {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
};

export type ChatMessage = {
  id: string;
  conversation_id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
};

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(text || `Request failed (${res.status})`);
  }
  return res.json() as Promise<T>;
}

export async function createConversation(): Promise<Conversation> {
  const res = await fetch(`${BASE}/api/conversations`, { method: "POST" });
  return json<Conversation>(res);
}

export async function listConversations(): Promise<Conversation[]> {
  const res = await fetch(`${BASE}/api/conversations`);
  return json<Conversation[]>(res);
}

export async function getMessages(conversationId: string): Promise<ChatMessage[]> {
  const res = await fetch(`${BASE}/api/conversations/${conversationId}/messages`);
  return json<ChatMessage[]>(res);
}

export async function deleteConversation(conversationId: string): Promise<void> {
  const res = await fetch(`${BASE}/api/conversations/${conversationId}`, {
    method: "DELETE",
  });
  await json(res);
}

export type StreamHandlers = {
  onDelta: (text: string) => void;
  onDone: (payload: { message_id: string; title?: string | null }) => void;
  onError: (message: string) => void;
};

// Streams the assistant reply token-by-token using XHR progress events, which
// is the reliable way to read a partial SSE body in React Native.
export function streamChat(
  conversationId: string,
  message: string,
  handlers: StreamHandlers,
): () => void {
  const xhr = new XMLHttpRequest();
  xhr.open("POST", `${BASE}/api/conversations/${conversationId}/chat`);
  xhr.setRequestHeader("Content-Type", "application/json");

  let consumed = 0; // chars of xhr.responseText already copied into `buffer`
  let buffer = ""; // unprocessed tail (may contain a partial event)

  const processBuffer = () => {
    const full = xhr.responseText;
    if (full.length > consumed) {
      buffer += full.slice(consumed);
      consumed = full.length;
    }
    let idx: number;
    while ((idx = buffer.indexOf("\n\n")) !== -1) {
      const raw = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 2);
      const line = raw.trim();
      if (!line.startsWith("data:")) continue;
      const dataStr = line.slice(5).trim();
      if (!dataStr) continue;
      try {
        const data = JSON.parse(dataStr);
        if (data.error) {
          handlers.onError(data.error);
        } else if (data.done) {
          handlers.onDone({ message_id: data.message_id, title: data.title });
        } else if (typeof data.delta === "string") {
          handlers.onDelta(data.delta);
        }
      } catch {
        // ignore malformed partial JSON
      }
    }
  };

  xhr.onprogress = processBuffer;
  xhr.onload = () => {
    processBuffer();
    if (xhr.status >= 400) {
      handlers.onError(`Request failed (${xhr.status})`);
    }
  };
  xhr.onerror = () => handlers.onError("We lost connection to the styling desk.");
  xhr.send(JSON.stringify({ message }));

  return () => xhr.abort();
}
