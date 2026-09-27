import { useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { Image } from "expo-image";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { useQuery } from "@tanstack/react-query";

import { api, Product } from "@/src/api";
import { colors, spacing } from "@/src/theme";

const CATEGORIES = ["all", "tops", "bottoms", "dresses", "outerwear", "shoes", "accessories"];

export default function Discover() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const [category, setCategory] = useState("all");

  const { data: profile } = useQuery({ queryKey: ["profile"], queryFn: api.getProfile });
  const palette = profile?.skin_tone?.undertone;
  const budget = profile?.preferences?.budget_max;
  const occasion = profile?.preferences?.occasion;
  const climate = profile?.preferences?.climate;
  const style = profile?.preferences?.style;

  const { data: products, isLoading } = useQuery({
    queryKey: ["products", category, palette, budget, occasion, climate, style],
    queryFn: () =>
      api.listProducts({
        category,
        palette,
        budget_max: budget,
        occasion,
        climate,
        style,
      }),
  });

  return (
    <View style={[styles.container, { paddingTop: insets.top }]}>
      <View style={styles.header}>
        <View>
          <Text style={styles.brand}>LUMIÈRE</Text>
          <Text style={styles.hello}>
            {profile?.skin_tone
              ? `Curated for ${profile.skin_tone.season}`
              : "Your daily edit"}
          </Text>
        </View>
      </View>

      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        style={styles.chipRow}
        contentContainerStyle={styles.chipRowContent}
      >
        {CATEGORIES.map((c) => {
          const active = c === category;
          return (
            <Pressable
              key={c}
              testID={`filter-${c}`}
              style={[styles.chip, active && styles.chipActive]}
              onPress={() => setCategory(c)}
            >
              <Text style={[styles.chipText, active && styles.chipTextActive]}>
                {c === "all" ? "All" : c.charAt(0).toUpperCase() + c.slice(1)}
              </Text>
            </Pressable>
          );
        })}
      </ScrollView>

      {isLoading ? (
        <View style={styles.loading}>
          <ActivityIndicator color={colors.brand} />
        </View>
      ) : (
        <FlatList
          data={products ?? []}
          keyExtractor={(item) => item.id}
          numColumns={2}
          columnWrapperStyle={{ gap: spacing.md, paddingHorizontal: spacing.lg }}
          contentContainerStyle={{
            paddingTop: spacing.md,
            paddingBottom: insets.bottom + 100,
            gap: spacing.xl,
          }}
          ListEmptyComponent={
            <View style={styles.empty}>
              <Text style={styles.emptyText}>No matches found for this filter.</Text>
            </View>
          }
          renderItem={({ item }) => (
            <ProductCard product={item} onPress={() => router.push(`/product/${item.id}`)} />
          )}
        />
      )}
    </View>
  );
}

function ProductCard({ product, onPress }: { product: Product; onPress: () => void }) {
  return (
    <Pressable
      testID={`product-card-${product.id}`}
      style={styles.card}
      onPress={onPress}
    >
      <Image source={{ uri: product.image_url }} style={styles.cardImage} contentFit="cover" />
      <Text style={styles.cardBrand}>{product.brand}</Text>
      <Text style={styles.cardName} numberOfLines={1}>
        {product.name}
      </Text>
      <Text style={styles.cardPrice}>${product.price.toFixed(0)}</Text>
      {product.recommendation_reasons?.[0] ? (
        <Text style={styles.reason} numberOfLines={2}>{product.recommendation_reasons[0]}</Text>
      ) : null}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.surface },
  header: {
    paddingHorizontal: spacing.xl,
    paddingVertical: spacing.lg,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-end",
  },
  brand: { fontSize: 22, letterSpacing: 4, color: colors.onSurface, fontWeight: "500" },
  hello: { fontSize: 12, color: colors.muted, marginTop: 2, letterSpacing: 1 },
  chipRow: { maxHeight: 56, marginBottom: spacing.sm },
  chipRowContent: {
    gap: spacing.sm,
    paddingHorizontal: spacing.xl,
    alignItems: "center",
    height: 56,
  },
  chip: {
    flexShrink: 0,
    height: 36,
    paddingHorizontal: spacing.lg,
    justifyContent: "center",
    borderWidth: 1,
    borderColor: colors.borderStrong,
  },
  chipActive: { backgroundColor: colors.surfaceInverse, borderColor: colors.surfaceInverse },
  chipText: { fontSize: 12, color: colors.onSurface, letterSpacing: 1 },
  chipTextActive: { color: colors.onSurfaceInverse },
  card: { flex: 1, gap: 4 },
  cardImage: {
    width: "100%",
    aspectRatio: 3 / 4,
    backgroundColor: colors.surfaceSecondary,
    marginBottom: spacing.sm,
  },
  cardBrand: { fontSize: 10, letterSpacing: 2, color: colors.muted },
  cardName: { fontSize: 14, color: colors.onSurface },
  cardPrice: { fontSize: 13, color: colors.onSurface, fontStyle: "italic", marginTop: 2 },
  reason: { fontSize: 10, lineHeight: 14, color: colors.muted, marginTop: 3 },
  loading: { flex: 1, alignItems: "center", justifyContent: "center" },
  empty: { padding: spacing["2xl"], alignItems: "center" },
  emptyText: { color: colors.muted, fontSize: 13 },
});
