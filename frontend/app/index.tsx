import { Image } from "expo-image";
import { LinearGradient } from "expo-linear-gradient";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { useQuery } from "@tanstack/react-query";

import { api } from "@/src/api";
import { colors, spacing } from "@/src/theme";

const HERO_IMG =
  "https://images.unsplash.com/photo-1662532577856-e8ee8b138a8b?crop=entropy&cs=srgb&fm=jpg&w=1200&q=85";

export default function Index() {
  const insets = useSafeAreaInsets();
  const router = useRouter();

  // If profile has skin tone already, skip onboarding
  const { data: profile, isLoading } = useQuery({
    queryKey: ["profile"],
    queryFn: api.getProfile,
  });

  const hasCompleted = profile?.skin_tone && profile?.preferences;

  return (
    <View style={styles.container}>
      <Image source={{ uri: HERO_IMG }} style={StyleSheet.absoluteFill} contentFit="cover" />
      <LinearGradient
        colors={["rgba(0,0,0,0)", "rgba(0,0,0,0.15)", "rgba(26,26,24,0.92)"]}
        locations={[0, 0.45, 1]}
        style={StyleSheet.absoluteFill}
      />
      <View style={[styles.header, { paddingTop: insets.top + spacing.xl }]}>
        <Text style={styles.eyebrow} testID="brand-eyebrow">LUMIÈRE</Text>
      </View>

      <View style={[styles.footer, { paddingBottom: insets.bottom + spacing.xl }]}>
        <Text style={styles.title} testID="onboarding-title">
          Fashion, tailored{"\n"}to your palette.
        </Text>
        <Text style={styles.subtitle}>
          A private stylist that reads your skin tone, learns your taste, and lets you try on
          pieces before you buy.
        </Text>
        <Pressable
          testID="get-started-btn"
          disabled={isLoading}
          style={({ pressed }) => [styles.cta, pressed && { opacity: 0.85 }]}
          onPress={() =>
            router.push(hasCompleted ? "/(tabs)" : "/(onboarding)/skin-scan")
          }
        >
          <Text style={styles.ctaLabel}>
            {hasCompleted ? "Enter the atelier" : "Begin your palette"}
          </Text>
        </Pressable>
        {hasCompleted ? (
          <Pressable onPress={() => router.push("/(onboarding)/skin-scan")}>
            <Text style={styles.linkAlt}>Redo skin analysis</Text>
          </Pressable>
        ) : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.surfaceInverse },
  header: { paddingHorizontal: spacing.xl },
  eyebrow: {
    fontSize: 12,
    letterSpacing: 4,
    color: colors.onSurfaceInverse,
    fontWeight: "500",
  },
  footer: {
    marginTop: "auto",
    paddingHorizontal: spacing.xl,
    gap: spacing.lg,
  },
  title: {
    fontSize: 40,
    lineHeight: 46,
    color: colors.onSurfaceInverse,
    fontWeight: "400",
    fontStyle: "italic",
  },
  subtitle: {
    fontSize: 15,
    lineHeight: 22,
    color: colors.onSurfaceInverse,
    opacity: 0.82,
  },
  cta: {
    backgroundColor: colors.surface,
    paddingVertical: 18,
    alignItems: "center",
    marginTop: spacing.sm,
  },
  ctaLabel: {
    color: colors.onSurface,
    fontSize: 14,
    letterSpacing: 2,
    fontWeight: "500",
  },
  linkAlt: {
    color: colors.onSurfaceInverse,
    opacity: 0.7,
    fontSize: 13,
    letterSpacing: 1,
    textAlign: "center",
    textDecorationLine: "underline",
  },
});
