import { useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { Image } from "expo-image";
import Feather from "@react-native-vector-icons/feather";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api, SkinTone } from "@/src/api";
import { captureImageBase64, pickImageBase64 } from "@/src/utils/image-picker";
import { colors, spacing } from "@/src/theme";

export default function SkinScan() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const qc = useQueryClient();

  const [photo, setPhoto] = useState<string | null>(null);
  const [result, setResult] = useState<SkinTone | null>(null);

  const analyze = useMutation({
    mutationFn: (b64: string) => api.analyzeSkin(b64),
    onSuccess: async (data) => {
      setResult(data);
      await api.updateProfile({ skin_tone: data });
      qc.invalidateQueries({ queryKey: ["profile"] });
    },
  });

  const handlePick = async (fromCamera: boolean) => {
    setResult(null);
    const b64 = fromCamera ? await captureImageBase64() : await pickImageBase64();
    if (!b64) return;
    setPhoto(b64);
    analyze.mutate(b64);
  };

  return (
    <View style={[styles.container, { paddingTop: insets.top }]}>
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} testID="back-btn" hitSlop={12}>
          <Feather name="arrow-left" size={22} color={colors.onSurface} />
        </Pressable>
        <Text style={styles.step}>01 / 02</Text>
      </View>

      <ScrollView
        contentContainerStyle={{ paddingBottom: insets.bottom + 120 }}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.intro}>
          <Text style={styles.eyebrow}>SKIN ANALYSIS</Text>
          <Text style={styles.title}>Reveal your{"\n"}season.</Text>
          <Text style={styles.body}>
            A clear, well-lit photo of your face — no makeup, no filter. Our color analyst
            reads your undertone and finds the palette that lets you glow.
          </Text>
        </View>

        <View style={styles.photoFrame}>
          {photo ? (
            <Image
              source={{ uri: `data:image/jpeg;base64,${photo}` }}
              style={styles.photo}
              contentFit="cover"
            />
          ) : (
            <View style={styles.photoPlaceholder}>
              <Feather name="user" size={40} color={colors.muted} />
              <Text style={styles.placeholderText}>Your face here</Text>
            </View>
          )}
          {analyze.isPending ? (
            <View style={styles.photoOverlay}>
              <ActivityIndicator color={colors.onSurfaceInverse} />
              <Text style={styles.overlayText}>Analyzing skin tone…</Text>
            </View>
          ) : null}
        </View>

        <View style={styles.actions}>
          <Pressable
            testID="capture-face-btn"
            style={styles.secondary}
            onPress={() => handlePick(true)}
          >
            <Feather name="camera" size={16} color={colors.onSurface} />
            <Text style={styles.secondaryLabel}>Camera</Text>
          </Pressable>
          <Pressable
            testID="upload-face-btn"
            style={styles.secondary}
            onPress={() => handlePick(false)}
          >
            <Feather name="image" size={16} color={colors.onSurface} />
            <Text style={styles.secondaryLabel}>Upload</Text>
          </Pressable>
        </View>

        {analyze.isError ? (
          <Text style={styles.errorText}>
            Unable to detect face clearly. Please try another photo.
          </Text>
        ) : null}

        {result ? (
          <View style={styles.resultCard} testID="skin-result-card">
            <Text style={styles.resultEyebrow}>YOUR SEASON</Text>
            <Text style={styles.resultSeason}>{result.season.toUpperCase()}</Text>
            <Text style={styles.resultUndertone}>
              {result.undertone.charAt(0).toUpperCase() + result.undertone.slice(1)} undertone
            </Text>
            <View style={styles.paletteRow}>
              {result.palette.map((c, i) => (
                <View key={`${c}-${i}`} style={[styles.swatch, { backgroundColor: c }]} />
              ))}
            </View>
            <Text style={styles.resultDesc}>{result.description}</Text>
          </View>
        ) : null}
      </ScrollView>

      {result ? (
        <View style={[styles.stickyFooter, { paddingBottom: insets.bottom + spacing.lg }]}>
          <Pressable
            testID="continue-preferences-btn"
            style={styles.cta}
            onPress={() => router.push("/(onboarding)/preferences")}
          >
            <Text style={styles.ctaLabel}>Continue</Text>
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
  step: { fontSize: 11, letterSpacing: 2, color: colors.muted },
  intro: { paddingHorizontal: spacing.xl, paddingTop: spacing.lg, gap: spacing.md },
  eyebrow: { fontSize: 11, letterSpacing: 3, color: colors.brand, fontWeight: "500" },
  title: { fontSize: 38, lineHeight: 42, color: colors.onSurface, fontStyle: "italic", fontWeight: "400" },
  body: { fontSize: 14, lineHeight: 22, color: colors.muted, marginTop: spacing.sm },
  photoFrame: {
    marginHorizontal: spacing.xl,
    marginTop: spacing["2xl"],
    aspectRatio: 3 / 4,
    backgroundColor: colors.surfaceSecondary,
    overflow: "hidden",
  },
  photo: { width: "100%", height: "100%" },
  photoPlaceholder: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    gap: spacing.md,
  },
  placeholderText: { fontSize: 12, color: colors.muted, letterSpacing: 2 },
  photoOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: "rgba(26,26,24,0.55)",
    alignItems: "center",
    justifyContent: "center",
    gap: spacing.md,
  },
  overlayText: { color: colors.onSurfaceInverse, letterSpacing: 2, fontSize: 12 },
  actions: {
    paddingHorizontal: spacing.xl,
    marginTop: spacing.lg,
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
    backgroundColor: colors.surface,
  },
  secondaryLabel: { fontSize: 13, letterSpacing: 2, color: colors.onSurface },
  errorText: {
    marginHorizontal: spacing.xl,
    marginTop: spacing.md,
    color: colors.error,
    fontSize: 13,
  },
  resultCard: {
    marginHorizontal: spacing.xl,
    marginTop: spacing["2xl"],
    padding: spacing.xl,
    backgroundColor: colors.surfaceSecondary,
    gap: spacing.sm,
  },
  resultEyebrow: { fontSize: 10, letterSpacing: 3, color: colors.brand },
  resultSeason: { fontSize: 32, letterSpacing: 4, color: colors.onSurface, fontWeight: "400" },
  resultUndertone: { fontSize: 14, color: colors.muted, marginBottom: spacing.md },
  paletteRow: { flexDirection: "row", gap: spacing.sm, marginVertical: spacing.md },
  swatch: { width: 36, height: 36, borderWidth: 1, borderColor: colors.borderStrong },
  resultDesc: { fontSize: 14, lineHeight: 21, color: colors.onSurface },
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
  },
  ctaLabel: { color: colors.onSurfaceInverse, fontSize: 13, letterSpacing: 2 },
});
