import { useState } from "react";
import {
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import Slider from "@react-native-community/slider";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import Feather from "@react-native-vector-icons/feather";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "@/src/api";
import { colors, spacing } from "@/src/theme";

const OCCASIONS = ["casual", "work", "date", "party", "formal"];
const CATEGORIES = ["tops", "bottoms", "dresses", "outerwear", "shoes", "accessories"];

export default function Preferences() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const qc = useQueryClient();

  const [budget, setBudget] = useState(300);
  const [occasion, setOccasion] = useState("casual");
  const [categories, setCategories] = useState<string[]>(["tops", "bottoms", "dresses"]);

  const toggleCategory = (c: string) =>
    setCategories((prev) => (prev.includes(c) ? prev.filter((x) => x !== c) : [...prev, c]));

  const save = useMutation({
    mutationFn: () =>
      api.updateProfile({
        preferences: {
          budget_min: 0,
          budget_max: Math.round(budget),
          occasion,
          categories,
        },
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["profile"] });
      router.replace("/(tabs)");
    },
  });

  return (
    <View style={[styles.container, { paddingTop: insets.top }]}>
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} testID="back-btn" hitSlop={12}>
          <Feather name="arrow-left" size={22} color={colors.onSurface} />
        </Pressable>
        <Text style={styles.step}>02 / 02</Text>
      </View>

      <ScrollView contentContainerStyle={{ paddingBottom: insets.bottom + 140 }}>
        <View style={styles.intro}>
          <Text style={styles.eyebrow}>PREFERENCES</Text>
          <Text style={styles.title}>Set the{"\n"}tone.</Text>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionLabel}>MAX BUDGET</Text>
          <Text style={styles.budgetValue} testID="budget-value">
            ${Math.round(budget)}
          </Text>
          <Slider
            testID="budget-slider"
            style={{ height: 40 }}
            minimumValue={50}
            maximumValue={800}
            step={10}
            value={budget}
            onValueChange={setBudget}
            minimumTrackTintColor={colors.brand}
            maximumTrackTintColor={colors.borderStrong}
            thumbTintColor={colors.brand}
          />
          <View style={styles.budgetLimits}>
            <Text style={styles.limitText}>$50</Text>
            <Text style={styles.limitText}>$800</Text>
          </View>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionLabel}>OCCASION</Text>
          <View style={styles.optionList}>
            {OCCASIONS.map((o) => {
              const active = occasion === o;
              return (
                <Pressable
                  key={o}
                  testID={`occasion-${o}`}
                  style={[styles.optionRow, active && styles.optionRowActive]}
                  onPress={() => setOccasion(o)}
                >
                  <Text style={[styles.optionText, active && styles.optionTextActive]}>
                    {o.charAt(0).toUpperCase() + o.slice(1)}
                  </Text>
                  {active ? <Feather name="check" size={16} color={colors.brand} /> : null}
                </Pressable>
              );
            })}
          </View>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionLabel}>CATEGORIES</Text>
          <View style={styles.chipWrap}>
            {CATEGORIES.map((c) => {
              const active = categories.includes(c);
              return (
                <Pressable
                  key={c}
                  testID={`category-${c}`}
                  style={[styles.chip, active && styles.chipActive]}
                  onPress={() => toggleCategory(c)}
                >
                  <Text style={[styles.chipText, active && styles.chipTextActive]}>
                    {c.charAt(0).toUpperCase() + c.slice(1)}
                  </Text>
                </Pressable>
              );
            })}
          </View>
        </View>
      </ScrollView>

      <View style={[styles.stickyFooter, { paddingBottom: insets.bottom + spacing.lg }]}>
        <Pressable
          testID="save-preferences-btn"
          style={[styles.cta, categories.length === 0 && { opacity: 0.4 }]}
          disabled={categories.length === 0 || save.isPending}
          onPress={() => save.mutate()}
        >
          <Text style={styles.ctaLabel}>
            {save.isPending ? "Saving…" : "Show my wardrobe"}
          </Text>
        </Pressable>
      </View>
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
  title: { fontSize: 38, lineHeight: 42, color: colors.onSurface, fontStyle: "italic" },
  section: { paddingHorizontal: spacing.xl, marginTop: spacing["2xl"] },
  sectionLabel: {
    fontSize: 11,
    letterSpacing: 3,
    color: colors.muted,
    marginBottom: spacing.md,
  },
  budgetValue: {
    fontSize: 40,
    color: colors.onSurface,
    fontWeight: "400",
    fontStyle: "italic",
    marginBottom: spacing.sm,
  },
  budgetLimits: { flexDirection: "row", justifyContent: "space-between" },
  limitText: { fontSize: 11, color: colors.muted, letterSpacing: 1 },
  optionList: { borderTopWidth: 1, borderTopColor: colors.divider },
  optionRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingVertical: spacing.lg,
    borderBottomWidth: 1,
    borderBottomColor: colors.divider,
  },
  optionRowActive: {},
  optionText: { fontSize: 17, color: colors.onSurface, fontWeight: "400" },
  optionTextActive: { color: colors.brand },
  chipWrap: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm },
  chip: {
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    borderWidth: 1,
    borderColor: colors.borderStrong,
  },
  chipActive: { backgroundColor: colors.surfaceInverse, borderColor: colors.surfaceInverse },
  chipText: { fontSize: 13, color: colors.onSurface, letterSpacing: 1 },
  chipTextActive: { color: colors.onSurfaceInverse },
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
