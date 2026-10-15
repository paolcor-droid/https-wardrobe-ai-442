import { useState } from "react";
import { View, Text, ScrollView, Pressable, Image, ActivityIndicator } from "react-native";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Stack, useRouter } from "expo-router";
import { getShoppingBag, removeShoppingBagItem, getCheckoutReadiness } from "@/src/api";
import { useTheme } from "@/src/theme";

export default function ShoppingBagScreen() {
  const { colors } = useTheme();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [country, setCountry] = useState<"AU" | "MD">("AU");
  const [error, setError] = useState("");
  const [removing, setRemoving] = useState<string | null>(null);
  const { data: bag, isLoading, isError } = useQuery({ queryKey: ["shopping-bag"], queryFn: getShoppingBag });
  const { data: readiness } = useQuery({
    queryKey: ["checkout-readiness", country, bag?.items.length],
    queryFn: () => getCheckoutReadiness(country),
    enabled: !!bag,
  });
  const currencies = new Set(bag?.items.map(item => item.currency || "Unknown") || []);
  const sameCurrency = currencies.size === 1;
  const currency = sameCurrency ? [...currencies][0] : null;
  const provisionalTotal = (bag?.items || []).reduce(
    (sum, item) => sum + (item.price_snapshot ?? 0) * item.quantity, 0);
  async function remove(id: string) {
    setRemoving(id); setError("");
    try {
      await removeShoppingBagItem(id);
      await queryClient.invalidateQueries({ queryKey: ["shopping-bag"] });
      await queryClient.invalidateQueries({ queryKey: ["checkout-readiness"] });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not remove garment.");
    } finally {
      setRemoving(null);
    }
  }
  return (
    <ScrollView style={{ flex: 1, backgroundColor: colors.surface }}
      contentContainerStyle={{ padding: 20, paddingBottom: 80, gap: 18 }}>
      <Stack.Screen options={{ title: "Shopping bag", headerShown: true }} />
      <Text style={{ fontSize: 30, color: colors.onSurface, fontWeight: "600" }}>Your shopping bag</Text>
      <Text style={{ color: colors.muted }}>Save the garments you love. Orders and payments are not available yet.</Text>
      {isLoading && <ActivityIndicator />}
      {isError && <Text style={{ color: colors.error }}>Your private bag could not be loaded.</Text>}
      {bag?.items.length === 0 && <Text style={{ color: colors.onSurface }}>Your bag is empty.</Text>}
      {bag?.items.map(item => (
        <View key={item.id} style={{ borderWidth: 1, borderColor: colors.border, padding: 12, borderRadius: 6, gap: 8 }}>
          <View style={{ flexDirection: "row", gap: 12 }}>
            {item.image_url ? <Image source={{ uri: item.image_url }} style={{ width: 86, height: 108 }} /> : null}
            <View style={{ flex: 1, gap: 5 }}>
              <Text style={{ color: colors.onSurface, fontSize: 17, fontWeight: "600" }}>{item.name}</Text>
              <Text style={{ color: colors.muted }}>{item.brand || "LUMIÈRE selection"}</Text>
              <Text style={{ color: colors.onSurface }}>Size: {item.size || "Unspecified"} · Colour: {item.colour || "Unspecified"}</Text>
              <Text style={{ color: colors.onSurface }}>Quantity: {item.quantity}</Text>
              <Text style={{ color: colors.onSurface }}>
                {item.price_snapshot != null ? `${item.currency || ""} ${item.price_snapshot.toFixed(2)} (indicative)` : "Price to be confirmed"}
              </Text>
            </View>
          </View>
          <Pressable accessibilityRole="button" disabled={removing === item.id}
            onPress={() => remove(item.id)} style={{ paddingVertical: 7 }}>
            <Text style={{ color: colors.onSurface }}>{removing === item.id ? "Removing…" : "Remove from bag"}</Text>
          </Pressable>
        </View>
      ))}
      {error ? <Text style={{ color: colors.error }}>{error}</Text> : null}
      <Pressable onPress={() => router.push("/(tabs)/discover" as any)}>
        <Text style={{ color: colors.onSurface, textDecorationLine: "underline" }}>Continue discovering clothes</Text>
      </Pressable>
      <View style={{ borderTopWidth: 1, borderColor: colors.border, paddingTop: 16, gap: 8 }}>
        <Text style={{ color: colors.onSurface, fontSize: 20, fontWeight: "600" }}>Checkout preparation</Text>
        <Text style={{ color: colors.muted }}>Delivery country</Text>
        <View style={{ flexDirection: "row", gap: 12 }}>
          {([["AU", "Australia"], ["MD", "Moldova"]] as const).map(([code, title]) => (
            <Pressable key={code} onPress={() => setCountry(code)}
              style={{ borderWidth: country === code ? 2 : 1, borderColor: colors.borderStrong, padding: 12 }}>
              <Text style={{ color: colors.onSurface }}>{title}</Text>
            </Pressable>
          ))}
        </View>
        <Text style={{ color: colors.onSurface }}>
          {bag?.items.length && sameCurrency && bag.items.every(x => x.price_snapshot != null)
            ? `Indicative garments subtotal: ${currency} ${provisionalTotal.toFixed(2)}`
            : "A combined subtotal is unavailable until item prices and currency are confirmed."}
        </Text>
        <Text style={{ color: colors.muted }}>Shipping, taxes, duties, final prices and inventory must be verified before checkout.</Text>
        {(readiness?.requirements || []).map(line => <Text key={line} style={{ color: colors.muted }}>• {line}</Text>)}
        <Pressable disabled style={{ backgroundColor: colors.surfaceTertiary, padding: 16, alignItems: "center" }}>
          <Text style={{ color: colors.muted, fontWeight: "600" }}>Secure checkout — coming soon</Text>
        </Pressable>
        <Text style={{ color: colors.muted }}>No payment details are requested or stored by LUMIÈRE at this stage.</Text>
      </View>
    </ScrollView>
  );
}
