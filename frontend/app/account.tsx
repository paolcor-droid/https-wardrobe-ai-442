import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { View, Text, TextInput, Pressable, ScrollView } from "react-native";
import { Stack } from "expo-router";
import * as SecureStore from "expo-secure-store";
import { saveAccountSession, clearAccountSession } from "@/src/account-api";
import { Platform } from "react-native";

// Account UI is staged separately from the legacy shared-profile flow.
// Do not reuse the session for legacy routes until all of them enforce ownership.
const BASE = Platform.OS === "web" ? "" : (process.env.EXPO_PUBLIC_BACKEND_URL ?? "");
const TOKEN_KEY = "lumiere_customer_session";

export default function AccountScreen() {
  const queryClient = useQueryClient();
  const [mode, setMode] = useState<"register" | "login">("register");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit() {
    setBusy(true);
    setMessage("");
    try {
      const res = await fetch(`${BASE}/api/account/${mode}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      const body = await res.json();
      if (!res.ok) throw new Error(body.detail || "Account request failed");
      if (mode === "register") {
        setMode("login");
        setMessage("Account created. Sign in to continue.");
      } else {
        await saveAccountSession(body.access_token);
        queryClient.clear(); // Never show cached data from a previous customer.
        setToken(body.access_token);
        setPassword("");
        setMessage("Signed in to your private account.");
      }
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to connect.");
    } finally {
      setBusy(false);
    }
  }

  async function logout() {
    setBusy(true);
    try {
      const saved = token || await SecureStore.getItemAsync(TOKEN_KEY);
      if (saved) {
        const res = await fetch(`${BASE}/api/account/logout`, {
          method: "POST", headers: { Authorization: `Bearer ${saved}` },
        });
        if (!res.ok) throw new Error("Unable to revoke the session. Try again.");
      }
      await clearAccountSession();
      queryClient.clear();
      setToken("");
      setMessage("Signed out.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to log out.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <ScrollView contentContainerStyle={{ padding: 24, gap: 16, flexGrow: 1 }}>
      <Stack.Screen options={{ title: "LUMIÈRE account", headerShown: true }} />
      <Text style={{ fontSize: 28, fontWeight: "600" }}>Your LUMIÈRE account</Text>
      <Text>Private account preview. Profile, wardrobe, Discover and text styling now use your account. Photo analysis and the existing Try-On screen still require migration.</Text>
      <TextInput placeholder="Email" value={email} autoCapitalize="none"
        keyboardType="email-address" onChangeText={setEmail}
        style={{ borderWidth: 1, borderColor: "#aaa", padding: 12, borderRadius: 8 }} />
      <TextInput placeholder="Password (12 characters minimum)" value={password}
        secureTextEntry onChangeText={setPassword}
        style={{ borderWidth: 1, borderColor: "#aaa", padding: 12, borderRadius: 8 }} />
      <Pressable disabled={busy} onPress={submit}
        style={{ backgroundColor: "#242424", padding: 16, borderRadius: 8 }}>
        <Text style={{ color: "white" }}>{mode === "register" ? "Create account" : "Sign in"}</Text>
      </Pressable>
      <Pressable onPress={() => setMode(mode === "register" ? "login" : "register")}>
        <Text>{mode === "register" ? "Already registered? Sign in" : "Create a new account"}</Text>
      </Pressable>
      <Pressable disabled={busy} onPress={logout}><Text>Sign out of account</Text></Pressable>
      {!!message && <Text accessibilityRole="alert">{message}</Text>}
    </ScrollView>
  );
}
