import { Platform } from "react-native";

/** A native mobile build must never silently send account requests to its Metro origin. */
export function backendBaseUrl(): string {
  if (Platform.OS === "web") return "";
  const value = (process.env.EXPO_PUBLIC_BACKEND_URL ?? "").trim().replace(/\/$/, "");
  if (!value) throw new Error("Android staging API is not configured yet. Do not upload photos or sign in.");
  let parsed: URL;
  try { parsed = new URL(value); } catch { throw new Error("Invalid Android staging API URL"); }
  if (parsed.protocol !== "https:" || !parsed.hostname || parsed.username || parsed.password
      || parsed.search || parsed.hash || parsed.pathname !== "/") {
    throw new Error("Android staging API must be a valid HTTPS origin");
  }
  return value;
}
