import { backendBaseUrl } from "./backend-origin";
import { accountRequest, accountAccessToken, webCsrfHeaders } from "./account-api";
import { Platform } from "react-native";

// On web, same-origin /api calls are forwarded by Metro to local FastAPI.
// Native apps still require an explicit reachable backend URL.


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

// Dev/testing model selector ------------------------------------------------
export type ChatProvider = "openai";

export type ProviderInfo = {
  id: string;
  label: string;
  model: string;
};

export type ModelsResponse = {
  default: string;
  providers: ProviderInfo[];
};

export async function getModels(): Promise<ModelsResponse> {
  const res = await fetch(`${backendBaseUrl()}/api/models`);
  return json<ModelsResponse>(res);
}

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(text || `Request failed (${res.status})`);
  }
  return res.json() as Promise<T>;
}

export function fileUrl(path: string): string {
  if (path.startsWith("private:")) {
    return `${backendBaseUrl()}/api/account/photos/${encodeURIComponent(path.slice(8))}`;
  }
  return `${backendBaseUrl()}/api/files/${path}`;
}

export async function createConversation(): Promise<Conversation> {
  const res = await accountRequest<Conversation>("/conversations", { method: "POST" });
  return res;
}

export async function listConversations(): Promise<Conversation[]> {
  const res = await accountRequest<Conversation[]>("/conversations");
  return res;
}

export async function updateConversation(
  id: string,
  body: { title?: string; pinned?: boolean },
): Promise<Conversation> {
  const res = await accountRequest<Conversation>(`/conversations/${encodeURIComponent(id)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return res;
}

export async function getMessages(conversationId: string): Promise<ChatMessage[]> {
  const res = await accountRequest<ChatMessage[]>(`/conversations/${encodeURIComponent(conversationId)}/messages`);
  return res;
}

export async function deleteConversation(conversationId: string): Promise<void> {
  const res = await accountRequest<{success: boolean}>(`/conversations/${encodeURIComponent(conversationId)}`, {
    method: "DELETE",
  });
  void res;
}

export async function deletePrivatePhoto(imagePath: string): Promise<void> {
  if (!/^private:[a-f0-9-]{36}$/.test(imagePath)) throw new Error("Invalid private photo identifier");
  await accountRequest(`/photos/${encodeURIComponent(imagePath.slice(8))}`, { method: "DELETE" });
}

export async function uploadImage(uri: string, name: string, type: string): Promise<string> {
  const form = new FormData();
  if (Platform.OS === "web") {
    const blob = await (await fetch(uri)).blob();
    form.append("file", blob, name);
  } else {
    // React Native native file part.
    // @ts-expect-error React Native FormData file shape
    form.append("file", { uri, name, type });
  }
  const token = await accountAccessToken();
  // Upload via XMLHttpRequest (React Native's built-in networking, and standard on web)
  // rather than the global fetch. In Expo SDK 54+ the global `fetch` is `expo/fetch`
  // (WinterCG), whose convertFormData rejects the RN `{ uri, name, type }` part with
  // "Unsupported FormDataPart implementation". XHR handles that part natively on Android/iOS.
  return new Promise<string>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${backendBaseUrl()}/api/account/photos`);
    if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);
    else Object.entries(webCsrfHeaders()).forEach(([name, value]) => xhr.setRequestHeader(name, value));
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const data = JSON.parse(xhr.responseText) as { id: string };
          if (!data.id) throw new Error("Missing private photo ID");
          resolve(`private:${data.id}`);
        } catch {
          reject(new Error("Upload succeeded but the response was invalid"));
        }
      } else {
        reject(new Error(xhr.responseText || `Upload failed (${xhr.status})`));
      }
    };
    xhr.onerror = () => reject(new Error("Upload failed: network error"));
    xhr.send(form);
  });
}

export async function saveLook(messageId: string): Promise<SavedLook> {
  return accountRequest<SavedLook>("/saved", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message_id: messageId }),
  });
}

export async function listSaved(): Promise<SavedLook[]> {
  return accountRequest<SavedLook[]>("/saved");
}

export async function deleteSaved(id: string): Promise<void> {
  await accountRequest<{ success: boolean }>(`/saved/${encodeURIComponent(id)}`, { method: "DELETE" });
}

export type StreamHandlers = {
  onDelta: (text: string) => void;
  onDone: (payload: { message_id: string; title?: string | null; provider?: string | null }) => void;
  onError: (message: string) => void;
};

export function streamChat(
  conversationId: string,
  message: string,
  handlers: StreamHandlers,
  imagePath?: string | null,
  provider?: string | null,
): () => void {
  const xhr = new XMLHttpRequest();
  let cancelled = false;

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
          handlers.onDone({ message_id: data.message_id, title: data.title, provider: data.provider });
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
  void (async () => {
    try {
      const token = await accountAccessToken();
      if (cancelled) return;
      if (imagePath) {
        handlers.onError("Private image attachments are not yet supported by account chat.");
        return;
      }
      xhr.open("POST", `${backendBaseUrl()}/api/account/conversations/${encodeURIComponent(conversationId)}/chat`);
      if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);
      else Object.entries(webCsrfHeaders()).forEach(([name, value]) => xhr.setRequestHeader(name, value));
      xhr.setRequestHeader("Content-Type", "application/json");
      xhr.send(JSON.stringify({ message, image_path: null, provider: provider ?? null }));
    } catch (error) {
      if (!cancelled) handlers.onError(error instanceof Error ? error.message : "Sign in required");
    }
  })();

  return () => { cancelled = true; xhr.abort(); };
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
  analyzed_with?: string | null;
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
  shop_for: "mens" | "womens" | "all";
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
  second_garment_image_path?: string | null;
  result_path: string;
  created_at: string;
};

export async function getProfile(): Promise<Profile> {
  const res = await accountRequest<Profile>("/profile");
  return res;
}

export async function updateProfile(body: Partial<Omit<Profile, "id" | "skin" | "updated_at">>): Promise<Profile> {
  const res = await accountRequest<Profile>("/profile", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return res;
}

export async function analyzeSkin(imagePath: string, provider?: string | null): Promise<SkinAnalysis> {
  return accountRequest<SkinAnalysis>("/skin-analysis", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ image_path: imagePath, provider: provider ?? null }),
  });
}

type PrivateTryOnRecord = {
  id: string; person_photo_id: string; garment_photo_id?: string | null;
  second_garment_photo_id?: string | null; garment_prompt?: string | null;
  result_photo_id: string; created_at: string;
};

function ownedPhotoId(path: string): string {
  if (!path.startsWith("private:") || !path.slice(8)) {
    throw new Error("Private Try-On requires a photograph uploaded to your account.");
  }
  return path.slice(8);
}

function presentPrivateTryOn(row: PrivateTryOnRecord): TryOn {
  return {
    id: row.id, person_image_path: `private:${row.person_photo_id}`,
    garment_image_path: row.garment_photo_id ? `private:${row.garment_photo_id}` : null,
    second_garment_image_path: row.second_garment_photo_id ? `private:${row.second_garment_photo_id}` : null,
    garment_prompt: row.garment_prompt, result_path: `private:${row.result_photo_id}`,
    created_at: row.created_at,
  };
}

export type TryOnPreflight = {
  ready: boolean;
  warnings: string[];
  guidance: string;
  limitations: string;
  requires_confirmation: boolean;
};

export async function checkTryOnPhoto(body: {
  person_image_path: string;
  garment_image_path?: string | null;
  second_garment_image_path?: string | null;
  garment_prompt?: string | null;
}): Promise<TryOnPreflight> {
  return accountRequest<TryOnPreflight>("/tryons/preflight", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      person_photo_id: ownedPhotoId(body.person_image_path),
      garment_photo_id: body.garment_image_path ? ownedPhotoId(body.garment_image_path) : null,
      second_garment_photo_id: body.second_garment_image_path ? ownedPhotoId(body.second_garment_image_path) : null,
      garment_prompt: body.garment_prompt ?? null,
    }),
  });
}

export async function createTryOn(body: {
  person_image_path: string;
  garment_image_path?: string | null;
  second_garment_image_path?: string | null;
  garment_prompt?: string | null;
}): Promise<TryOn> {
  const record = await accountRequest<PrivateTryOnRecord>("/tryons", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      person_photo_id: ownedPhotoId(body.person_image_path),
      garment_photo_id: body.garment_image_path ? ownedPhotoId(body.garment_image_path) : null,
      second_garment_photo_id: body.second_garment_image_path ? ownedPhotoId(body.second_garment_image_path) : null,
      garment_prompt: body.garment_prompt ?? null,
    }),
  });
  return presentPrivateTryOn(record);
}

export async function listTryOns(): Promise<TryOn[]> {
  const records = await accountRequest<PrivateTryOnRecord[]>("/tryons");
  return records.map(presentPrivateTryOn);
}

export async function deleteTryOn(id: string): Promise<void> {
  await accountRequest<{ success: boolean }>(`/tryons/${encodeURIComponent(id)}`, { method: "DELETE" });
}


// ----------------------------- Verified catalogue recommendations -----------------------------
export type CatalogueProduct = {
  provider_id: string;
  external_id: string;
  name: string;
  source_url?: string | null;
  brand?: string | null;
  category?: string | null;
  description?: string;
  price?: number | null;
  currency?: string | null;
  image_url?: string | null;
  colour_names?: string[];
  sizes?: string[];
  materials?: string[];
  occasions?: string[];
  palette_tags?: string[];
  availability?: string | null;
};

export type ProductRecommendation = {
  product_id: string;
  name: string;
  brand?: string | null;
  category?: string | null;
  description: string;
  price?: number | null;
  currency?: string | null;
  image_url?: string | null;
  colour_names: string[];
  sizes: string[];
  materials: string[];
  recommendation_score: number;
  recommendation_reasons: string[];
  tryon_supported?: boolean;
  tryon_product_id?: string | null;
  price_status?: string;
  stock_status?: string;
};

export type CatalogueRecommendationsResponse = {
  recommendations: ProductRecommendation[];
  count: number;
  live_inventory_enabled: false;
  source: string;
  notice?: string;
};

export type CatalogueSearchFilters = {
  q?: string; brand?: string; category?: string; colour?: string; size?: string;
  min_price?: number; max_price?: number; page?: number; per_page?: number;
};
export type CatalogueSearchResponse = CatalogueRecommendationsResponse & {
  total: number; page: number; per_page: number; has_more: boolean;
  demo_diagnostics?: { loaded: number; search_matches: number; eligible_after_profile: number };
  demo_outfit_diagnostics?: { candidate_products_checked?: number; eligible_colours?: Record<string, number>; eligible_roles?: Record<string, number>; xml_outfits: number; eligible_garments: number; complete: number; colour_eligible: number; season_eligible: number; budget_eligible: number; generated_combinations?: number };
  demo_outfits?: { id: string; origin?: "xml" | "generated"; title?: string; score: number; total_price: number; currency: string; reason: string; style?: string; occasion?: string; season?: string; source_occasion?: string; source_style?: string; source_season?: string; occasion_confidence?: "High" | "Moderate" | "Low"; occasion_evidence?: string; garments: { name: string; category?: string; colour_names: string[]; price?: number; currency: string }[] }[];
};
export async function searchCatalogue(filters: CatalogueSearchFilters): Promise<CatalogueSearchResponse> {
  const args = Object.entries(filters).filter(([, value]) => value !== "" && value != null);
  const query = new URLSearchParams(args.map(([key, value]) => [key, String(value)]));
  return accountRequest<CatalogueSearchResponse>(`/catalogue/search?${query.toString()}`);
}

export async function searchDemoCatalogue(filters: CatalogueSearchFilters): Promise<CatalogueSearchResponse> {
  const args = Object.entries(filters).filter(([, value]) => value !== "" && value != null);
  const query = new URLSearchParams(args.map(([key, value]) => [key, String(value)]));
  return accountRequest<CatalogueSearchResponse>(`/catalogue/demo/search?${query.toString()}`);
}

export async function getCatalogueRecommendations(): Promise<CatalogueRecommendationsResponse> {
  return accountRequest<CatalogueRecommendationsResponse>("/catalogue/recommendations");
}


export async function prepareCatalogueGarment(productId: string): Promise<{ path: string; name: string }> {
  return accountRequest<{ path: string; name: string }>(
    `/catalogue/products/${encodeURIComponent(productId)}/prepare-tryon`,
    { method: "POST" },
  );
}

export type RecommendationPreviewResponse = {
  recommendations: ProductRecommendation[];
  count: number;
  live_inventory_enabled: false;
  source: "caller_supplied_verified_catalogue";
};

export async function previewCatalogueRecommendations(
  _products: CatalogueProduct[],
  _limit = 20,
): Promise<RecommendationPreviewResponse> {
  // The legacy preview processed caller-supplied products against a shared profile.
  // Fail closed rather than expose another customer's styling preferences.
  throw new Error("Catalogue preview is unavailable until the private preview API is ready.");
}

export type WardrobeItem = {
  id: string;
  name: string;
  category: "top" | "bottom" | "dress" | "outerwear" | "shoes" | "accessory" | "other";
  colour: string;
  image_path: string;
  notes: string;
  created_at: string;
};

export async function listWardrobe(): Promise<WardrobeItem[]> {
  return accountRequest<WardrobeItem[]>("/wardrobe");
}

export async function addWardrobeItem(body: Pick<WardrobeItem, "name" | "category" | "colour" | "image_path" | "notes">): Promise<WardrobeItem> {
  return accountRequest<WardrobeItem>("/wardrobe", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
}

export async function deleteWardrobeItem(id: string): Promise<void> {
  await accountRequest<{success: boolean}>(`/wardrobe/${encodeURIComponent(id)}`, { method: "DELETE" });
}

export type OutfitPlan = { item_ids: string[]; names: string[]; reason: string; image_colour_verified: boolean };
export type CapsulePlan = {
  items: Array<{ id: string; name: string; category: string; colour: string }>;
  possible_outfits: OutfitPlan[];
  missing_categories: string[];
  notice: string;
};
export type ProductSentiment = "liked" | "disliked" | "saved" | "purchased";

export async function saveProductFeedback(product_id: string, sentiment: ProductSentiment) {
  return accountRequest<{ product_id: string; sentiment: ProductSentiment }>(
    `/feedback/${encodeURIComponent(product_id)}`, {
      method: "PUT", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sentiment }),
    });
}
export async function getProductFeedback() {
  return accountRequest<Array<{ product_id: string; sentiment: ProductSentiment }>>("/feedback");
}
export async function getWardrobeOutfits(occasion: string, climate: "hot" | "mild" | "cold") {
  return accountRequest<{ outfits: OutfitPlan[]; weather_live: false; notice: string }>("/wardrobe/outfits", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ occasion, climate }),
  });
}
export async function getCapsulePlan(occasion: string, climate: "hot" | "mild" | "cold") {
  return accountRequest<CapsulePlan>("/wardrobe/capsule", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ occasion, climate }),
  });
}
export async function savePriceTarget(_product_id: string, _target_price_aud: number) {
  // Prevent writing customer interests into the old unauthenticated price-watch store.
  throw new Error("Private price alerts are not available yet.");
}

export type SavedCatalogueOutfit = { id: string; product_ids: string[]; garments?: { product_id: string; name: string }[]; created_at: string };
export const saveCatalogueOutfit = (product_ids: string[]) =>
  accountRequest<SavedCatalogueOutfit>("/outfits", { method: "POST", body: JSON.stringify({ product_ids }) });
export type PreparedOutfitGarment = { product_id: string; path: string; name: string; sizes: string[]; colour_names: string[] };
export const prepareSavedOutfit = (id: string) =>
  accountRequest<{ garments: PreparedOutfitGarment[] }>(`/outfits/${encodeURIComponent(id)}/prepare`, { method: "POST" });
export const listCatalogueOutfits = () => accountRequest<SavedCatalogueOutfit[]>("/outfits");
export const removeCatalogueOutfit = (id: string) =>
  accountRequest<{ success: boolean }>(`/outfits/${encodeURIComponent(id)}`, { method: "DELETE" });

export type ShoppingBagItem = {
  id: string; product_id: string; name: string; brand?: string | null;
  image_url?: string | null; size: string; colour: string; quantity: number;
  price_snapshot?: number | null; currency?: string | null;
  price_verified: false; stock_verified: false;
};
export async function getShoppingBag(): Promise<{items: ShoppingBagItem[]; checkout_enabled: false; notice: string}> {
  return accountRequest("/bag");
}
export async function addShoppingBagItem(item: {
  product_id: string; size: string; colour: string; quantity: number;
}): Promise<ShoppingBagItem> {
  return accountRequest("/bag", { method: "POST", body: JSON.stringify(item) });
}
export async function updateShoppingBagQuantity(id: string, quantity: number): Promise<ShoppingBagItem> {
  return accountRequest(`/bag/${encodeURIComponent(id)}`, {
    method: "PATCH", body: JSON.stringify({ quantity }),
  });
}
export async function removeShoppingBagItem(id: string): Promise<void> {
  await accountRequest(`/bag/${encodeURIComponent(id)}`, { method: "DELETE" });
}

export type CheckoutReadiness = {
  country: "AU" | "MD"; item_count: number; checkout_enabled: false;
  payment_enabled: false; orders_enabled: false; shopify_test_mode: boolean;
  shipping_quote_available: false; tax_quote_available: false;
  currency_codes: string[]; price_verified: false; stock_verified: false;
  requirements: string[]; message: string;
};
export async function getCheckoutReadiness(country: "AU" | "MD"): Promise<CheckoutReadiness> {
  return accountRequest<CheckoutReadiness>(`/checkout/readiness?country=${country}`);
}
