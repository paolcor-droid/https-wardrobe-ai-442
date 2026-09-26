import { FlatList, Pressable, StyleSheet, Text, View } from "react-native";
import { Image } from "expo-image";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import Feather from "@react-native-vector-icons/feather";
import { useQuery } from "@tanstack/react-query";

import { api } from "@/src/api";
import { colors, spacing } from "@/src/theme";

export default function Wishlist() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { data: items = [] } = useQuery({
    queryKey: ["wishlist"],
    queryFn: api.getWishlist,
  });

  return (
    <View style={[styles.container, { paddingTop: insets.top }]}>
      <View style={styles.header}>
        <Text style={styles.title}>Saved</Text>
        <Text style={styles.subtitle}>{items.length} pieces</Text>
      </View>
      <FlatList
        data={items}
        keyExtractor={(i) => i.id}
        numColumns={2}
        columnWrapperStyle={{ gap: spacing.md, paddingHorizontal: spacing.lg }}
        contentContainerStyle={{
          paddingTop: spacing.md,
          paddingBottom: insets.bottom + 100,
          gap: spacing.xl,
        }}
        ListEmptyComponent={
          <View style={styles.empty}>
            <Feather name="bookmark" size={32} color={colors.muted} />
            <Text style={styles.emptyText}>No saved pieces yet.</Text>
            <Text style={styles.emptyHint}>Tap the bookmark on any product to save it.</Text>
          </View>
        }
        renderItem={({ item }) => (
          <Pressable
            testID={`saved-${item.id}`}
            style={styles.card}
            onPress={() => router.push(`/product/${item.id}`)}
          >
            <Image source={{ uri: item.image_url }} style={styles.cardImage} contentFit="cover" />
            <Text style={styles.cardBrand}>{item.brand}</Text>
            <Text style={styles.cardName} numberOfLines={1}>
              {item.name}
            </Text>
            <Text style={styles.cardPrice}>${item.price.toFixed(0)}</Text>
          </Pressable>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.surface },
  header: { paddingHorizontal: spacing.xl, paddingVertical: spacing.lg, gap: 4 },
  title: { fontSize: 32, color: colors.onSurface, fontStyle: "italic" },
  subtitle: { fontSize: 12, color: colors.muted, letterSpacing: 1 },
  card: { flex: 1, gap: 4 },
  cardImage: {
    width: "100%",
    aspectRatio: 3 / 4,
    backgroundColor: colors.surfaceSecondary,
    marginBottom: spacing.sm,
  },
  cardBrand: { fontSize: 10, letterSpacing: 2, color: colors.muted },
  cardName: { fontSize: 14, color: colors.onSurface },
  cardPrice: { fontSize: 13, color: colors.onSurface, fontStyle: "italic" },
  empty: {
    padding: spacing["3xl"],
    alignItems: "center",
    gap: spacing.md,
    marginTop: spacing["2xl"],
  },
  emptyText: { color: colors.onSurface, fontSize: 15 },
  emptyHint: { color: colors.muted, fontSize: 13, textAlign: "center" },
});
