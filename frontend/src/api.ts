import { Platform } from "react-native";

const BASE = process.env.EXPO_PUBLIC_BACKEND_URL;

export type Conversation = {
  id: string;
  title: string;
  pinned: boolean;
  created_at: string;
  updated_at: string;
};

export type ChatMessage = {
  id: string;
  conversation_id: string;
  role: "user" | "assistant";
  content: string;
  image_path?: string | null;
  created_at: string;
};

export type SavedLook = {
  id: string;
  message_id: string;
  conversation_id: string;
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

export function fileUrl(path: string): string {
  return `${BASE}/api/files/${path}`;
}

export async function createConversation(): Promise<Conversation> {
  const res = await fetch(`${BASE}/api/conversations`, { method: "POST" });
  return json<Conversation>(res);
}

export async function listConversations(): Promise<Conversation[]> {
  const res = await fetch(`${BASE}/api/conversations`);
  return json<Conversation[]>(res);
}

export async function updateConversation(
  id: string,
  body: { title?: string; pinned?: boolean },
): Promise<Conversation> {
  const res = await fetch(`${BASE}/api/conversations/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return json<Conversation>(res);
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

export async function uploadImage(uri: string, name: string, type: string): Promise<string> {
  const form = new FormData();
  if (Platform.OS === "web") {
    const blob = await (await fetch(uri)).blob();
    form.append("file", blob, name);
  } else {
    // @ts-expect-error React Native FormData file shape
    form.append("file", { uri, name, type });
  }
  const res = await fetch(`${BASE}/api/upload`, { method: "POST", body: form });
  const data = await json<{ path: string }>(res);
  return data.path;
}

export async function saveLook(messageId: string): Promise<SavedLook> {
  const res = await fetch(`${BASE}/api/saved`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message_id: messageId }),
  });
  return json<SavedLook>(res);
}

export async function listSaved(): Promise<SavedLook[]> {
  const res = await fetch(`${BASE}/api/saved`);
  return json<SavedLook[]>(res);
}

export async function deleteSaved(id: string): Promise<void> {
  const res = await fetch(`${BASE}/api/saved/${id}`, { method: "DELETE" });
  await json(res);
}

export type StreamHandlers = {
  onDelta: (text: string) => void;
  onDone: (payload: { message_id: string; title?: string | null }) => void;
  onError: (message: string) => void;
};

export function streamChat(
  conversationId: string,
  message: string,
  handlers: StreamHandlers,
  imagePath?: string | null,
): () => void {
  const xhr = new XMLHttpRequest();
  xhr.open("POST", `${BASE}/api/conversations/${conversationId}/chat`);
  xhr.setRequestHeader("Content-Type", "application/json");

  let consumed = 0;
  let buffer = "";

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
    if (xhr.status >= 400) handlers.onError(`Request failed (${xhr.status})`);
  };
  xhr.onerror = () => handlers.onError("We lost connection to the styling desk.");
  xhr.send(JSON.stringify({ message, image_path: imagePath ?? null }));

  return () => xhr.abort();
}

// ----------------------------- Profile / Skin / Try-on -----------------------------
export type ColorSwatch = { name: string; hex: string };

export type AnalysisQuality = {
  lighting_quality: "poor" | "fair" | "good";
  face_visibility: "poor" | "fair" | "good";
  confidence: "low" | "medium" | "high";
};

export type SkinAnalysis = {
  undertone: "warm" | "neutral_warm" | "neutral" | "neutral_cool" | "cool";
  depth: "light" | "medium" | "deep";
  chroma: "muted" | "balanced" | "clear";
  contrast: "low" | "medium" | "high";
  season?: string | null;
  summary: string;
  palette: ColorSwatch[];
  best_neutrals: ColorSwatch[];
  best_accents: ColorSwatch[];
  statement_colours: ColorSwatch[];
  caution_colours: ColorSwatch[];
  analysis_quality?: AnalysisQuality | null;
  image_path?: string | null;
  analyzed_at?: string | null;
};

export type Preferences = {
  budget_min: number;
  budget_max: number;
  occasion: string;
  categories: string[];
  climate: "hot" | "mild" | "cold";
  style: string;
  preferred_fit: string;
  preferred_colours: string[];
  avoided_colours: string[];
  preferred_retailers: string[];
};

export type Profile = {
  id: string;
  favorite_colors: string[];
  styles: string[];
  sizes: Record<string, string>;
  budget?: string | null;
  notes: string;
  preferences: Preferences;
  skin?: SkinAnalysis | null;
  updated_at: string;
};

export type TryOn = {
  id: string;
  person_image_path: string;
  garment_image_path?: string | null;
  garment_prompt?: string | null;
  result_path: string;
  created_at: string;
};

export async function getProfile(): Promise<Profile> {
  const res = await fetch(`${BASE}/api/profile`);
  return json<Profile>(res);
}

export async function updateProfile(body: Partial<Omit<Profile, "id" | "skin" | "updated_at">>): Promise<Profile> {
  const res = await fetch(`${BASE}/api/profile`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return json<Profile>(res);
}

export async function analyzeSkin(imagePath: string): Promise<SkinAnalysis> {
  const res = await fetch(`${BASE}/api/skin-analysis`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ image_path: imagePath }),
  });
  return json<SkinAnalysis>(res);
}

export async function createTryOn(body: {
  person_image_path: string;
  garment_image_path?: string | null;
  garment_prompt?: string | null;
}): Promise<TryOn> {
  const res = await fetch(`${BASE}/api/tryon`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return json<TryOn>(res);
}

export async function listTryOns(): Promise<TryOn[]> {
  const res = await fetch(`${BASE}/api/tryons`);
  return json<TryOn[]>(res);
}

export async function deleteTryOn(id: string): Promise<void> {
  const res = await fetch(`${BASE}/api/tryons/${id}`, { method: "DELETE" });
  await json(res);
}
