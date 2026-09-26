import { FlatList, Pressable, StyleSheet, Text, View } from "react-native";
import { Image } from "expo-image";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import Feather from "@react-native-vector-icons/feather";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "expo-router";

import { api } from "@/src/api";
import { colors, spacing } from "@/src/theme";

export default function TryOnHistory() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { data: items = [], isLoading } = useQuery({
    queryKey: ["tryons"],
    queryFn: api.listTryOns,
  });

  return (
    <View style={[styles.container, { paddingTop: insets.top }]}>
      <View style={styles.header}>
        <Text style={styles.title}>Try-On</Text>
        <Text style={styles.subtitle}>{items.length} looks</Text>
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
          isLoading ? null : (
            <View style={styles.empty}>
              <Feather name="camera" size={32} color={colors.muted} />
              <Text style={styles.emptyText}>No looks yet.</Text>
              <Text style={styles.emptyHint}>
                Open any piece and tap "Virtual Try-On" to see it on you.
              </Text>
              <Pressable
                style={styles.emptyCta}
                testID="empty-browse-btn"
                onPress={() => router.push("/(tabs)")}
              >
                <Text style={styles.emptyCtaLabel}>Browse the edit</Text>
              </Pressable>
            </View>
          )
        }
        renderItem={({ item }) => (
          <View style={styles.card} testID={`tryon-${item.id}`}>
            <Image
              source={{ uri: `data:image/png;base64,${item.generated_image}` }}
              style={styles.cardImage}
              contentFit="cover"
            />
            <Text style={styles.cardName} numberOfLines={1}>
              {item.product_name}
            </Text>
          </View>
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
  card: { flex: 1, gap: spacing.sm },
  cardImage: {
    width: "100%",
    aspectRatio: 3 / 4,
    backgroundColor: colors.surfaceSecondary,
  },
  cardName: { fontSize: 13, color: colors.onSurface },
  empty: {
    padding: spacing["3xl"],
    alignItems: "center",
    gap: spacing.md,
    marginTop: spacing["2xl"],
  },
  emptyText: { color: colors.onSurface, fontSize: 15 },
  emptyHint: { color: colors.muted, fontSize: 13, textAlign: "center" },
  emptyCta: {
    marginTop: spacing.lg,
    paddingHorizontal: spacing.xl,
    paddingVertical: 14,
    backgroundColor: colors.surfaceInverse,
  },
  emptyCtaLabel: { color: colors.onSurfaceInverse, letterSpacing: 2, fontSize: 12 },
});
