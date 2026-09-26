import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import Feather from "@react-native-vector-icons/feather";
import { useQuery } from "@tanstack/react-query";

import { api } from "@/src/api";
import { colors, spacing } from "@/src/theme";

export default function Profile() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { data: profile } = useQuery({ queryKey: ["profile"], queryFn: api.getProfile });

  const st = profile?.skin_tone;
  const pref = profile?.preferences;

  return (
    <View style={[styles.container, { paddingTop: insets.top }]}>
      <ScrollView contentContainerStyle={{ paddingBottom: insets.bottom + 100 }}>
        <View style={styles.header}>
          <Text style={styles.title}>Profile</Text>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionLabel}>YOUR PALETTE</Text>
          {st ? (
            <>
              <Text style={styles.season}>{st.season.toUpperCase()}</Text>
              <Text style={styles.subrow}>
                {st.undertone.charAt(0).toUpperCase() + st.undertone.slice(1)} undertone
              </Text>
              <View style={styles.paletteRow}>
                {st.palette.map((c, i) => (
                  <View key={i} style={[styles.swatch, { backgroundColor: c }]} />
                ))}
              </View>
              <Text style={styles.desc}>{st.description}</Text>
            </>
          ) : (
            <Text style={styles.placeholderText}>No analysis yet.</Text>
          )}
          <Pressable
            testID="redo-scan-btn"
            style={styles.linkRow}
            onPress={() => router.push("/(onboarding)/skin-scan")}
          >
            <Text style={styles.linkText}>Redo skin analysis</Text>
            <Feather name="chevron-right" size={16} color={colors.onSurface} />
          </Pressable>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionLabel}>PREFERENCES</Text>
          {pref ? (
            <>
              <View style={styles.pRow}>
                <Text style={styles.pKey}>Budget</Text>
                <Text style={styles.pVal}>Up to ${pref.budget_max}</Text>
              </View>
              <View style={styles.pRow}>
                <Text style={styles.pKey}>Occasion</Text>
                <Text style={styles.pVal}>
                  {pref.occasion.charAt(0).toUpperCase() + pref.occasion.slice(1)}
                </Text>
              </View>
              <View style={styles.pRow}>
                <Text style={styles.pKey}>Categories</Text>
                <Text style={styles.pVal} numberOfLines={2}>
                  {pref.categories.map((c) => c[0].toUpperCase() + c.slice(1)).join(", ")}
                </Text>
              </View>
            </>
          ) : (
            <Text style={styles.placeholderText}>Not set.</Text>
          )}
          <Pressable
            testID="edit-preferences-btn"
            style={styles.linkRow}
            onPress={() => router.push("/(onboarding)/preferences")}
          >
            <Text style={styles.linkText}>Edit preferences</Text>
            <Feather name="chevron-right" size={16} color={colors.onSurface} />
          </Pressable>
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.surface },
  header: { paddingHorizontal: spacing.xl, paddingVertical: spacing.lg },
  title: { fontSize: 32, color: colors.onSurface, fontStyle: "italic" },
  section: {
    paddingHorizontal: spacing.xl,
    paddingVertical: spacing.xl,
    borderTopWidth: 1,
    borderTopColor: colors.divider,
  },
  sectionLabel: { fontSize: 11, letterSpacing: 3, color: colors.brand, marginBottom: spacing.md },
  season: { fontSize: 28, letterSpacing: 3, color: colors.onSurface },
  subrow: { fontSize: 13, color: colors.muted, marginTop: 4 },
  paletteRow: { flexDirection: "row", gap: spacing.sm, marginVertical: spacing.lg },
  swatch: { width: 36, height: 36, borderWidth: 1, borderColor: colors.borderStrong },
  desc: { fontSize: 14, lineHeight: 21, color: colors.onSurface },
  placeholderText: { fontSize: 14, color: colors.muted },
  linkRow: {
    marginTop: spacing.lg,
    paddingTop: spacing.md,
    borderTopWidth: 1,
    borderTopColor: colors.divider,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  linkText: { fontSize: 14, color: colors.onSurface, letterSpacing: 1 },
  pRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingVertical: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.divider,
    gap: spacing.lg,
  },
  pKey: { fontSize: 13, color: colors.muted, letterSpacing: 1 },
  pVal: { fontSize: 14, color: colors.onSurface, flex: 1, textAlign: "right" },
});
