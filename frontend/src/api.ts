// API client for Lumière backend
const BASE = process.env.EXPO_PUBLIC_BACKEND_URL;

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}/api${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status}: ${body}`);
  }
  return res.json();
}

export type ColourSwatch = { name: string; hex: string };

export type SkinTone = {
  undertone: "warm" | "neutral_warm" | "neutral" | "neutral_cool" | "cool";
  depth: "light" | "medium" | "deep";
  chroma: "muted" | "balanced" | "clear";
  contrast: "low" | "medium" | "high";
  season: string;
  palette: string[];
  best_neutrals: ColourSwatch[];
  best_accents: ColourSwatch[];
  statement_colours: ColourSwatch[];
  caution_colours: ColourSwatch[];
  analysis_quality?: {
    lighting_quality: "poor" | "fair" | "good";
    face_visibility: "poor" | "fair" | "good";
    confidence: "low" | "medium" | "high";
  };
  description: string;
};

export type Preferences = {
  budget_min: number;
  budget_max: number;
  occasion: string;
  categories: string[];
  climate?: "hot" | "mild" | "cold";
  style?: string;
  preferred_fit?: string;
  preferred_colours?: string[];
  avoided_colours?: string[];
};

export type Profile = {
  user_id: string;
  skin_tone: SkinTone | null;
  preferences: Preferences | null;
  body_photo: string | null;
};

export type Product = {
  id: string;
  name: string;
  brand: string;
  category: string;
  price: number;
  image_url: string;
  description: string;
  colors: string[];
  palette_tags: string[];
  occasions: string[];
  recommendation_score?: number;
  recommendation_reasons?: string[];
};

export type TryOnResult = {
  id: string;
  product_id: string;
  product_name: string;
  generated_image: string;
  created_at: string;
};

export const api = {
  analyzeSkin: (face_photo: string) =>
    json<SkinTone>("/skin/analyze", { method: "POST", body: JSON.stringify({ face_photo }) }),
  getProfile: () => json<Profile>("/profile"),
  updateProfile: (payload: Partial<Profile>) =>
    json<Profile>("/profile", { method: "POST", body: JSON.stringify(payload) }),
  listProducts: (params: Record<string, string | number | undefined> = {}) => {
    const q = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== "" && v !== "all") q.append(k, String(v));
    });
    const qs = q.toString();
    return json<Product[]>(`/products${qs ? `?${qs}` : ""}`);
  },
  getProduct: (id: string) => json<Product>(`/products/${id}`),
  tryOn: (product_id: string, body_photo: string) =>
    json<TryOnResult>("/tryon", {
      method: "POST",
      body: JSON.stringify({ product_id, body_photo }),
    }),
  listTryOns: () => json<TryOnResult[]>("/tryon"),
  getWishlist: () => json<Product[]>("/wishlist"),
  toggleWishlist: (product_id: string) =>
    json<{ action: string; product_ids: string[] }>(`/wishlist/${product_id}`, { method: "POST" }),
};
