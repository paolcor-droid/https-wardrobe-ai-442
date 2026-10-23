import { useState } from "react";
import { View, Text, ScrollView, Pressable, Image, ActivityIndicator, useWindowDimensions } from "react-native";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Stack, useRouter } from "expo-router";
import { getShoppingBag, removeShoppingBagItem, updateShoppingBagQuantity, getCheckoutReadiness, listCatalogueOutfits, removeCatalogueOutfit, prepareSavedOutfit } from "@/src/api";
import { useTheme } from "@/src/theme";

export default function ShoppingBagScreen() {
  const { colors } = useTheme();
  const { width: viewportWidth } = useWindowDimensions();
  const compact = viewportWidth < 420;
  const router = useRouter();
  const queryClient = useQueryClient();
  const [country, setCountry] = useState<"AU" | "MD">("AU");
  const [error, setError] = useState("");
  const [removingOutfit, setRemovingOutfit] = useState<string | null>(null);
  const [openingOutfit, setOpeningOutfit] = useState<string | null>(null);
  const { data: savedOutfits, isError: outfitsError } = useQuery({ queryKey: ["saved-catalogue-outfits"], queryFn: listCatalogueOutfits });
  const [removing, setRemoving] = useState<string | null>(null);
  const [updating, setUpdating] = useState<string | null>(null);
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
  async function changeQuantity(id: string, quantity: number) {
    if (quantity < 1 || quantity > 10) return;
    setUpdating(id); setError("");
    try {
      await updateShoppingBagQuantity(id, quantity);
      await queryClient.invalidateQueries({ queryKey: ["shopping-bag"] });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to update quantity.");
    } finally { setUpdating(null); }
  }
  async function reopenOutfit(id: string) {
    setOpeningOutfit(id); setError("");
    try {
      const data = await prepareSavedOutfit(id);
      const [first, second] = data.garments;
      if (!first) throw new Error("This outfit has no available garments.");
      router.push({ pathname: "/(tabs)/tryon", params: {
        garmentPath: first.path, garmentName: first.name,
        garmentProductId: first.product_id, garmentSizes: JSON.stringify(first.sizes),
        garmentColours: JSON.stringify(first.colour_names),
        secondGarmentPath: second?.path || "", secondGarmentName: second?.name || "",
        secondGarmentProductId: second?.product_id || "",
        secondGarmentSizes: JSON.stringify(second?.sizes || []),
        secondGarmentColours: JSON.stringify(second?.colour_names || []),
      } });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not open saved outfit.");
    } finally { setOpeningOutfit(null); }
  }
  async function forgetOutfit(id: string) {
    setRemovingOutfit(id); setError("");
    try {
      await removeCatalogueOutfit(id);
      await queryClient.invalidateQueries({ queryKey: ["saved-catalogue-outfits"] });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not remove outfit.");
    } finally { setRemovingOutfit(null); }
  }
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
              <View style={{ flexDirection: "row", alignItems: "center", gap: 12 }}>
                <Text style={{ color: colors.onSurface }}>Quantity</Text>
                <Pressable testID={`bag-decrease-${item.id}`} accessibilityRole="button" disabled={updating === item.id || item.quantity <= 1}
                  onPress={() => changeQuantity(item.id, item.quantity - 1)} style={{ padding: 9, borderWidth: 1, borderColor: colors.border }}>
                  <Text style={{ color: colors.onSurface }}>−</Text>
                </Pressable>
                <Text style={{ color: colors.onSurface }}>{updating === item.id ? "…" : item.quantity}</Text>
                <Pressable testID={`bag-increase-${item.id}`} accessibilityRole="button" disabled={updating === item.id || item.quantity >= 10}
                  onPress={() => changeQuantity(item.id, item.quantity + 1)} style={{ padding: 9, borderWidth: 1, borderColor: colors.border }}>
                  <Text style={{ color: colors.onSurface }}>+</Text>
                </Pressable>
              </View>
              <Text style={{ color: colors.onSurface }}>
                {item.price_snapshot != null ? `${item.currency || ""} ${item.price_snapshot.toFixed(2)} each (indicative) · Line total: ${item.currency || ""} ${(item.price_snapshot * item.quantity).toFixed(2)}` : "Price to be confirmed"}
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
      <View style={{ borderTopWidth: 1, borderColor: colors.border, paddingTop: 16, gap: 10 }}>
        <Text style={{ color: colors.onSurface, fontSize: 20, fontWeight: "600" }}>Saved outfits</Text>
        <Text style={{ color: colors.muted }}>Private outfit ideas saved from Try-On. Return to Discover to explore or change garments.</Text>
        {outfitsError ? <Text style={{ color: colors.error }}>Saved outfits could not be loaded.</Text> : null}
        {savedOutfits?.length === 0 ? <Text style={{ color: colors.muted }}>No saved outfits yet.</Text> : null}
        {savedOutfits?.map(outfit => (
          <View key={outfit.id} style={{ borderWidth: 1, borderColor: colors.border, padding: 12, gap: 8 }}>
            <Text style={{ color: colors.onSurface }}>{outfit.garments?.map(x => x.name).join(" + ") || outfit.product_ids.length + " saved garment(s)"}</Text>
            <Pressable testID={`saved-outfit-open-${outfit.id}`} disabled={!!openingOutfit}
              onPress={() => reopenOutfit(outfit.id)}>
              <Text style={{ color: colors.onSurface, textDecorationLine: "underline" }}>
                {openingOutfit === outfit.id ? "Preparing garments…" : "Reopen in Virtual Try-On"}
              </Text>
            </Pressable>
            <Pressable onPress={() => router.push("/(tabs)/discover" as any)}>
              <Text style={{ color: colors.onSurface, textDecorationLine: "underline" }}>Discover alternatives</Text>
            </Pressable>
            <Pressable disabled={removingOutfit === outfit.id} onPress={() => forgetOutfit(outfit.id)}>
              <Text style={{ color: colors.muted }}>{removingOutfit === outfit.id ? "Removing…" : "Remove saved outfit"}</Text>
            </Pressable>
          </View>
        ))}
      </View>
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
