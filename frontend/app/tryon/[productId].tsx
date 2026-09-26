import { useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { Image } from "expo-image";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import Feather from "@react-native-vector-icons/feather";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/src/api";
import { captureImageBase64, pickImageBase64 } from "@/src/utils/image-picker";
import { colors, spacing } from "@/src/theme";

export default function TryOnFlow() {
  const { productId } = useLocalSearchParams<{ productId: string }>();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const qc = useQueryClient();

  const { data: product } = useQuery({
    queryKey: ["product", productId],
    queryFn: () => api.getProduct(productId!),
    enabled: !!productId,
  });
  const { data: profile } = useQuery({ queryKey: ["profile"], queryFn: api.getProfile });

  const [bodyPhoto, setBodyPhoto] = useState<string | null>(profile?.body_photo ?? null);
  const [result, setResult] = useState<string | null>(null);

  const tryOn = useMutation({
    mutationFn: (b64: string) => api.tryOn(productId!, b64),
    onSuccess: async (data) => {
      setResult(data.generated_image);
      qc.invalidateQueries({ queryKey: ["tryons"] });
    },
  });

  const pickPhoto = async (fromCamera: boolean) => {
    setResult(null);
    const b64 = fromCamera ? await captureImageBase64() : await pickImageBase64();
    if (!b64) return;
    setBodyPhoto(b64);
    // Save body photo to profile for reuse
    api.updateProfile({ body_photo: b64 }).catch(() => {});
    tryOn.mutate(b64);
  };

  const runAgain = () => {
    if (bodyPhoto) {
      setResult(null);
      tryOn.mutate(bodyPhoto);
    }
  };

  return (
    <View style={[styles.container, { paddingTop: insets.top }]}>
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} testID="tryon-back-btn" hitSlop={12}>
          <Feather name="arrow-left" size={22} color={colors.onSurface} />
        </Pressable>
        <Text style={styles.title}>Virtual Try-On</Text>
        <View style={{ width: 22 }} />
      </View>

      <ScrollView contentContainerStyle={{ paddingBottom: insets.bottom + 120 }}>
        {product ? (
          <View style={styles.productStrip}>
            <Image source={{ uri: product.image_url }} style={styles.stripImage} />
            <View style={{ flex: 1 }}>
              <Text style={styles.stripBrand}>{product.brand.toUpperCase()}</Text>
              <Text style={styles.stripName} numberOfLines={1}>
                {product.name}
              </Text>
              <Text style={styles.stripPrice}>${product.price.toFixed(0)}</Text>
            </View>
          </View>
        ) : null}

        <View style={styles.splitRow}>
          <View style={styles.pane}>
            <Text style={styles.paneLabel}>YOU</Text>
            {bodyPhoto ? (
              <Image
                source={{ uri: `data:image/jpeg;base64,${bodyPhoto}` }}
                style={styles.paneImage}
                contentFit="cover"
              />
            ) : (
              <View style={styles.paneEmpty}>
                <Feather name="user" size={28} color={colors.muted} />
                <Text style={styles.paneEmptyText}>Upload a{"\n"}full-body photo</Text>
              </View>
            )}
          </View>
          <View style={styles.pane}>
            <Text style={styles.paneLabel}>WITH GARMENT</Text>
            {tryOn.isPending ? (
              <View style={styles.paneEmpty}>
                <ActivityIndicator color={colors.brand} />
                <Text style={styles.paneEmptyText}>Simulating{"\n"}garment…</Text>
              </View>
            ) : result ? (
              <Image
                source={{ uri: `data:image/png;base64,${result}` }}
                style={styles.paneImage}
                contentFit="cover"
              />
            ) : (
              <View style={styles.paneEmpty}>
                <Feather name="image" size={28} color={colors.muted} />
                <Text style={styles.paneEmptyText}>Result{"\n"}appears here</Text>
              </View>
            )}
          </View>
        </View>

        {tryOn.isError ? (
          <Text style={styles.errorText}>
            Try-on failed. Please try a clearer full-body photo.
          </Text>
        ) : null}

        <View style={styles.actions}>
          <Pressable
            testID="tryon-camera-btn"
            style={styles.secondary}
            onPress={() => pickPhoto(true)}
            disabled={tryOn.isPending}
          >
            <Feather name="camera" size={16} color={colors.onSurface} />
            <Text style={styles.secondaryLabel}>Camera</Text>
          </Pressable>
          <Pressable
            testID="tryon-upload-btn"
            style={styles.secondary}
            onPress={() => pickPhoto(false)}
            disabled={tryOn.isPending}
          >
            <Feather name="upload" size={16} color={colors.onSurface} />
            <Text style={styles.secondaryLabel}>Upload</Text>
          </Pressable>
        </View>

        <Text style={styles.hint}>
          Tip: Use a well-lit, front-facing full-body photo against a plain background for the
          best result.
        </Text>
      </ScrollView>

      {result ? (
        <View style={[styles.stickyFooter, { paddingBottom: insets.bottom + spacing.lg }]}>
          <Pressable
            testID="tryon-run-again-btn"
            style={styles.ctaGhost}
            onPress={runAgain}
          >
            <Text style={styles.ctaGhostLabel}>Regenerate</Text>
          </Pressable>
          <Pressable
            testID="tryon-done-btn"
            style={styles.cta}
            onPress={() => router.push("/(tabs)/tryon")}
          >
            <Text style={styles.ctaLabel}>See all looks</Text>
          </Pressable>
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.surface },
  header: {
    paddingHorizontal: spacing.xl,
    paddingVertical: spacing.md,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  title: { fontSize: 14, letterSpacing: 3, color: colors.onSurface, fontWeight: "500" },
  productStrip: {
    flexDirection: "row",
    gap: spacing.md,
    alignItems: "center",
    paddingHorizontal: spacing.xl,
    paddingVertical: spacing.md,
    borderTopWidth: 1,
    borderBottomWidth: 1,
    borderColor: colors.divider,
  },
  stripImage: {
    width: 56,
    height: 72,
    backgroundColor: colors.surfaceSecondary,
  },
  stripBrand: { fontSize: 10, letterSpacing: 2, color: colors.muted },
  stripName: { fontSize: 14, color: colors.onSurface },
  stripPrice: { fontSize: 13, color: colors.onSurface, fontStyle: "italic" },
  splitRow: {
    flexDirection: "row",
    gap: spacing.sm,
    paddingHorizontal: spacing.lg,
    marginTop: spacing.lg,
  },
  pane: { flex: 1, gap: spacing.sm },
  paneLabel: { fontSize: 10, letterSpacing: 2, color: colors.muted },
  paneImage: {
    width: "100%",
    aspectRatio: 3 / 4,
    backgroundColor: colors.surfaceSecondary,
  },
  paneEmpty: {
    width: "100%",
    aspectRatio: 3 / 4,
    backgroundColor: colors.surfaceSecondary,
    alignItems: "center",
    justifyContent: "center",
    gap: spacing.sm,
  },
  paneEmptyText: {
    fontSize: 12,
    color: colors.muted,
    textAlign: "center",
    lineHeight: 18,
  },
  actions: {
    paddingHorizontal: spacing.xl,
    marginTop: spacing.xl,
    flexDirection: "row",
    gap: spacing.md,
  },
  secondary: {
    flex: 1,
    flexDirection: "row",
    gap: spacing.sm,
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: 14,
    borderWidth: 1,
    borderColor: colors.borderStrong,
  },
  secondaryLabel: { fontSize: 13, letterSpacing: 2, color: colors.onSurface },
  errorText: {
    marginHorizontal: spacing.xl,
    marginTop: spacing.md,
    color: colors.error,
    fontSize: 13,
  },
  hint: {
    marginTop: spacing.lg,
    paddingHorizontal: spacing.xl,
    fontSize: 12,
    color: colors.muted,
    lineHeight: 18,
    fontStyle: "italic",
  },
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
    flexDirection: "row",
    gap: spacing.md,
  },
  cta: {
    flex: 1,
    backgroundColor: colors.surfaceInverse,
    paddingVertical: 18,
    alignItems: "center",
  },
  ctaLabel: { color: colors.onSurfaceInverse, fontSize: 13, letterSpacing: 2 },
  ctaGhost: {
    flex: 1,
    paddingVertical: 18,
    alignItems: "center",
    borderWidth: 1,
    borderColor: colors.borderStrong,
  },
  ctaGhostLabel: { color: colors.onSurface, fontSize: 13, letterSpacing: 2 },
});
