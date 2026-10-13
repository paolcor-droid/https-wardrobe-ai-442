import { backendBaseUrl } from "./backend-origin";
import * as SecureStore from "expo-secure-store";
import { Platform } from "react-native";

// Staged client for ownership-enforcing account endpoints only.
// Never send this token to /api/profile, /api/wardrobe, /api/tryon
// or any other unauthenticated legacy endpoint.

const KEY = "lumiere_customer_session";

export function webCsrfHeaders(): Record<string, string> {
  if (Platform.OS !== "web" || typeof document === "undefined") return {};
  const part = document.cookie.split("; ").find(value => value.startsWith("lumiere_csrf="));
  return part ? { "X-Lumiere-CSRF": decodeURIComponent(part.slice("lumiere_csrf=".length)) } : {};
}

export async function saveAccountSession(token: string): Promise<void> {
  if (Platform.OS === "web") return;
  await SecureStore.setItemAsync(KEY, token);
}

export async function clearAccountSession(): Promise<void> {
  if (Platform.OS === "web") return;
  await SecureStore.deleteItemAsync(KEY);
}

export async function accountAccessToken(): Promise<string> {
  if (Platform.OS === "web") return "";
  const token = await SecureStore.getItemAsync(KEY);
  if (!token) throw new Error("Please sign in to your LUMIÈRE account");
  return token;
}

export async function accountRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = Platform.OS === "web" ? "" : await accountAccessToken();
  if (!path.startsWith("/") || path.startsWith("//")) throw new Error("Invalid account path");
  const response = await fetch(`${backendBaseUrl()}/api/account${path}`, {
    ...init, credentials: "same-origin", headers: { ...(init.headers as Record<string, string> | undefined), ...(token ? { Authorization: `Bearer ${token}` } : webCsrfHeaders()) },
  });
  if (!response.ok) {
    if (response.status === 401) throw new Error("Session expired. Sign in again.");
    // Only this exact, fixed endpoint may expose its server's actionable detail.
    // Other API failures retain generic messages to avoid showing provider data.
    if (response.status === 502 && /^\\/catalogue\\/products\\/[^/]+\\/prepare-tryon$/.test(path)) {
      throw new Error("Supplier garment image unavailable. Try another garment or upload your own garment photograph.");
    }
    throw new Error(`Account request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export type PrivateWardrobeItem = {
  id: string; name: string; category: string; colour: string; user_id: string;
};

export const privateProfile = () => accountRequest<Record<string, unknown>>("/profile");
export const privateWardrobe = () => accountRequest<PrivateWardrobeItem[]>("/wardrobe");
export const privateConversations = () => accountRequest<Array<{id: string; title: string}>>("/conversations");
export const privateFeedback = () => accountRequest<Array<{product_id: string; sentiment: string}>>("/feedback");

export type AccountIdentity = { id: string; email: string };

// An anonymous visitor is not an error; backend/network failures remain visible.
export async function currentAccount(): Promise<AccountIdentity | null> {
  let headers: Record<string, string> = {};
  if (Platform.OS !== "web") {
    const token = await SecureStore.getItemAsync(KEY);
    if (!token) return null;
    headers = { Authorization: `Bearer ${token}` };
  }
  const response = await fetch(`${backendBaseUrl()}/api/account/me`, { credentials: "same-origin", headers });
  if (response.status === 401) return null;
  if (!response.ok) throw new Error(`Unable to verify account (${response.status})`);
  return response.json() as Promise<AccountIdentity>;
}
