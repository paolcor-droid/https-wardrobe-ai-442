import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
  Linking,
} from "react-native";
import { Image } from "expo-image";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import Feather from "@react-native-vector-icons/feather";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/src/api";
import { DEFAULT_RETAILERS, RETAILERS, retailerUrl } from "@/src/retailers";
import { colors, spacing } from "@/src/theme";

export default function ProductDetail() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const qc = useQueryClient();

  const { data: product, isLoading } = useQuery({
    queryKey: ["product", id],
    queryFn: () => api.getProduct(id!),
    enabled: !!id,
  });
  const { data: profile } = useQuery({ queryKey: ["profile"], queryFn: api.getProfile });
  const { data: wishlist = [] } = useQuery({
    queryKey: ["wishlist"],
    queryFn: api.getWishlist,
  });

  const isSaved = wishlist.some((w) => w.id === id);
  const toggle = useMutation({
    mutationFn: () => api.toggleWishlist(id!),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["wishlist"] }),
  });

  if (isLoading || !product) {
    return (
      <View style={[styles.container, { alignItems: "center", justifyContent: "center" }]}>
        <ActivityIndicator color={colors.brand} />
      </View>
    );
  }

  const selectedRetailerIds = profile?.preferences?.preferred_retailers?.length
    ? profile.preferences.preferred_retailers
    : DEFAULT_RETAILERS;
  const selectedRetailers = RETAILERS.filter((r) => selectedRetailerIds.includes(r.id));
  const shopQuery = [product.name, product.category].filter(Boolean).join(" ");

  const reasons = product.recommendation_reasons?.length
    ? product.recommendation_reasons
    : ["This piece fits your current wardrobe preferences."];


  return (
    <View style={styles.container}>
      <ScrollView contentContainerStyle={{ paddingBottom: insets.bottom + 120 }}>
        <View style={{ position: "relative" }}>
          <Image source={{ uri: product.image_url }} style={styles.hero} contentFit="cover" />
          <View style={[styles.floatingHeader, { paddingTop: insets.top + spacing.md }]}>
            <Pressable
              testID="pd-back-btn"
              style={styles.iconBtn}
              onPress={() => router.back()}
              hitSlop={12}
            >
              <Feather name="arrow-left" size={20} color={colors.onSurface} />
            </Pressable>
            <Pressable
              testID="pd-save-btn"
              style={styles.iconBtn}
              onPress={() => toggle.mutate()}
              hitSlop={12}
            >
              <Feather
                name="bookmark"
                size={20}
                color={isSaved ? colors.brand : colors.onSurface}
              />
            </Pressable>
          </View>
        </View>

        <View style={styles.body}>
          <Text style={styles.brand}>{product.brand.toUpperCase()}</Text>
          <Text style={styles.name}>{product.name}</Text>
          <Text style={styles.price}>${product.price.toFixed(0)}</Text>

          <View style={styles.divider} />

          <Text style={styles.sectionTitle}>Description</Text>
          <Text style={styles.desc}>{product.description}</Text>

          <View style={styles.divider} />
          <Text style={styles.sectionTitle}>Why this suits you</Text>
          <View style={styles.swatchesInline}>
            {product.colors.map((c, i) => (
              <View key={i} style={[styles.smallSwatch, { backgroundColor: c }]} />
            ))}
          </View>
          {reasons.map((reason, i) => (
            <Text key={i} style={styles.reasonLine}>• {reason}</Text>
          ))}

          <View style={styles.divider} />
          <Text style={styles.sectionTitle}>Shop similar from your retailers</Text>
          <Text style={styles.shopHelper}>StyleScan uses your recommendation as the brief and opens matching retailer searches where supported.</Text>
          <View style={styles.retailerWrap}>
            {selectedRetailers.map((retailer) => (
              <Pressable
                key={retailer.id}
                style={styles.retailerButton}
                onPress={() => Linking.openURL(retailerUrl(retailer, shopQuery))}
              >
                <Text style={styles.retailerButtonText}>{retailer.name}</Text>
                <Feather name="external-link" size={14} color={colors.onSurface} />
              </Pressable>
            ))}
          </View>

          <View style={styles.divider} />
          <Text style={styles.sectionTitle}>Details</Text>
          <View style={styles.pRow}>
            <Text style={styles.pKey}>Category</Text>
            <Text style={styles.pVal}>
              {product.category[0].toUpperCase() + product.category.slice(1)}
            </Text>
          </View>
          <View style={styles.pRow}>
            <Text style={styles.pKey}>Occasions</Text>
            <Text style={styles.pVal}>
              {product.occasions.map((o) => o[0].toUpperCase() + o.slice(1)).join(", ")}
            </Text>
          </View>
        </View>
      </ScrollView>

      <View style={[styles.stickyFooter, { paddingBottom: insets.bottom + spacing.lg }]}>
        <Pressable
          testID="try-on-btn"
          style={styles.cta}
          onPress={() => router.push(`/tryon/${product.id}`)}
        >
          <Feather name="camera" size={16} color={colors.onSurfaceInverse} />
          <Text style={styles.ctaLabel}>Virtual Try-On</Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.surface },
  hero: { width: "100%", aspectRatio: 3 / 4, backgroundColor: colors.surfaceSecondary },
  floatingHeader: {
    position: "absolute",
    left: 0,
    right: 0,
    top: 0,
    paddingHorizontal: spacing.lg,
    flexDirection: "row",
    justifyContent: "space-between",
  },
  iconBtn: {
    width: 40,
    height: 40,
    backgroundColor: colors.surface,
    alignItems: "center",
    justifyContent: "center",
  },
  body: { paddingHorizontal: spacing.xl, paddingTop: spacing.xl, gap: 4 },
  brand: { fontSize: 11, letterSpacing: 3, color: colors.muted },
  name: { fontSize: 26, color: colors.onSurface, fontStyle: "italic", marginTop: 2 },
  price: { fontSize: 18, color: colors.onSurface, marginTop: spacing.sm },
  divider: {
    height: 1,
    backgroundColor: colors.divider,
    marginVertical: spacing.xl,
  },
  sectionTitle: {
    fontSize: 11,
    letterSpacing: 3,
    color: colors.brand,
    marginBottom: spacing.md,
  },
  desc: { fontSize: 14, lineHeight: 22, color: colors.onSurface },
  reasonLine: { fontSize: 14, lineHeight: 21, color: colors.onSurface, marginTop: spacing.sm },
  shopHelper: { fontSize: 12, lineHeight: 18, color: colors.muted, marginBottom: spacing.md },
  retailerWrap: { gap: spacing.sm },
  retailerButton: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", borderWidth: 1, borderColor: colors.borderStrong, paddingHorizontal: spacing.lg, paddingVertical: spacing.md },
  retailerButtonText: { fontSize: 13, color: colors.onSurface, letterSpacing: 1 },
  matchRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: spacing.md,
  },
  matchBadge: {
    paddingHorizontal: spacing.md,
    paddingVertical: 8,
    backgroundColor: colors.brandTertiary,
  },
  matchBadgeText: { fontSize: 12, letterSpacing: 1, color: colors.onBrandTertiary },
  swatchesInline: { flexDirection: "row", gap: spacing.sm },
  smallSwatch: { width: 24, height: 24, borderWidth: 1, borderColor: colors.borderStrong },
  pRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingVertical: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.divider,
  },
  pKey: { fontSize: 13, color: colors.muted, letterSpacing: 1 },
  pVal: { fontSize: 14, color: colors.onSurface },
  stickyFooter: {
    position: "absolute",
    left: 0,
    right: 0,
    bottom: 0,
    paddingHorizontal: spacing.xl,
    paddingTop: spacing.md,
    backgroundColor: colors.surface,
    borderTopWidth: 1,
    borderTopColor: colors.divider,
  },
  cta: {
    backgroundColor: colors.surfaceInverse,
    paddingVertical: 18,
    alignItems: "center",
    flexDirection: "row",
    justifyContent: "center",
    gap: spacing.sm,
  },
  ctaLabel: { color: colors.onSurfaceInverse, fontSize: 13, letterSpacing: 2 },
});
