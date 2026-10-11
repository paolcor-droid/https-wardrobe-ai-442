import * as SecureStore from "expo-secure-store";
import { Platform } from "react-native";

// Staged client for ownership-enforcing account endpoints only.
// Never send this token to /api/profile, /api/wardrobe, /api/tryon
// or any other unauthenticated legacy endpoint.
const BASE = Platform.OS === "web" ? "" : (process.env.EXPO_PUBLIC_BACKEND_URL ?? "");
const KEY = "lumiere_customer_session";

export async function saveAccountSession(token: string): Promise<void> {
  if (Platform.OS === "web") throw new Error("Secure web session storage is not configured");
  await SecureStore.setItemAsync(KEY, token);
}

export async function clearAccountSession(): Promise<void> {
  if (Platform.OS === "web") return;
  await SecureStore.deleteItemAsync(KEY);
}

export async function accountAccessToken(): Promise<string> {
  if (Platform.OS === "web") throw new Error("Secure web account sessions are not configured");
  const token = await SecureStore.getItemAsync(KEY);
  if (!token) throw new Error("Please sign in to your LUMIÈRE account");
  return token;
}

export async function accountRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = await accountAccessToken();
  if (!path.startsWith("/") || path.startsWith("//")) throw new Error("Invalid account path");
  const response = await fetch(`${BASE}/api/account${path}`, {
    ...init, headers: { ...(init.headers as Record<string, string> | undefined), Authorization: `Bearer ${token}` },
  });
  if (!response.ok) throw new Error(response.status === 401 ? "Session expired. Sign in again." : `Account request failed (${response.status})`);
  return response.json() as Promise<T>;
}

export type PrivateWardrobeItem = {
  id: string; name: string; category: string; colour: string; user_id: string;
};

export const privateProfile = () => accountRequest<Record<string, unknown>>("/profile");
export const privateWardrobe = () => accountRequest<PrivateWardrobeItem[]>("/wardrobe");
export const privateConversations = () => accountRequest<Array<{id: string; title: string}>>("/conversations");
export const privateFeedback = () => accountRequest<Array<{product_id: string; sentiment: string}>>("/feedback");
