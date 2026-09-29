import { View, Text, Pressable, ScrollView } from "react-native";
import { Image } from "expo-image";
import { LinearGradient } from "expo-linear-gradient";

import { makeStyles, fonts } from "@/src/theme";

const HERO =
  "https://images.unsplash.com/photo-1483985988355-763728e1935b?crop=entropy&cs=srgb&fm=jpg&w=1200&q=85";

const SUGGESTIONS = [
  "Build me a smart-casual capsule wardrobe",
  "What should I wear to a summer wedding?",
  "Which colors suit a warm skin tone?",
  "Help me pack for a 5-day city trip",
];

export function ChatEmpty({ onPick }: { onPick: (prompt: string) => void }) {
  const styles = useStyles();
  return (
    <ScrollView
      contentContainerStyle={styles.container}
      showsVerticalScrollIndicator={false}
      keyboardShouldPersistTaps="handled"
    >
      <View style={styles.heroWrap}>
        <Image source={{ uri: HERO }} style={styles.hero} contentFit="cover" transition={300} />
        <LinearGradient
          colors={["transparent", "rgba(0,0,0,0.15)", "rgba(0,0,0,0.75)"]}
          style={styles.scrim}
        />
        <View style={styles.heroTextWrap}>
          <Text style={styles.kicker}>STYLESCAN</Text>
          <Text style={styles.heroTitle}>How can I{"\n"}style you today?</Text>
        </View>
      </View>

      <Text style={styles.subtitle}>Try one of these to begin</Text>
      <View style={styles.chips}>
        {SUGGESTIONS.map((s) => (
          <Pressable
            key={s}
            testID={`suggestion-${s.slice(0, 10)}`}
            style={styles.chip}
            onPress={() => onPick(s)}
          >
            <Text style={styles.chipText}>{s}</Text>
          </Pressable>
        ))}
      </View>
    </ScrollView>
  );
}

const useStyles = makeStyles((c) => ({
  container: { paddingBottom: 24 },
  heroWrap: {
    height: 360,
    justifyContent: "flex-end",
  },
  hero: { ...({ position: "absolute" } as const), width: "100%", height: "100%" },
  scrim: { position: "absolute", left: 0, right: 0, bottom: 0, height: "100%" },
  heroTextWrap: { padding: 24 },
  kicker: {
    fontFamily: fonts.text,
    fontSize: 12,
    letterSpacing: 4,
    color: "#FFFFFF",
    marginBottom: 10,
    opacity: 0.85,
  },
  heroTitle: {
    fontFamily: fonts.display,
    fontSize: 38,
    lineHeight: 42,
    color: "#FFFFFF",
    fontWeight: "700",
  },
  subtitle: {
    fontFamily: fonts.text,
    fontSize: 13,
    letterSpacing: 1,
    color: c.muted,
    paddingHorizontal: 24,
    marginTop: 28,
    marginBottom: 14,
    textTransform: "uppercase",
  },
  chips: { paddingHorizontal: 24, gap: 12 },
  chip: {
    borderWidth: 1,
    borderColor: c.border,
    backgroundColor: c.surfaceSecondary,
    borderRadius: 4,
    paddingVertical: 16,
    paddingHorizontal: 18,
  },
  chipText: {
    fontFamily: fonts.text,
    fontSize: 15,
    color: c.onSurfaceSecondary,
  },
}));
