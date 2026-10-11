import { useEffect, useState } from "react";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { View, Text, Pressable, ScrollView } from "react-native";
import { Image } from "expo-image";
import { LinearGradient } from "expo-linear-gradient";

import { makeStyles, fonts } from "@/src/theme";

// Curated Unsplash editorial images; each source is individually documented.
// Unsplash photo copyright license allows commercial use; model/trademark release
// clearance remains a separate pre-launch review item.
const HERO_PHOTOS = [
  { id: "SS1Oldoervo", category: "women", theme: "evening", source: "https://unsplash.com/photos/woman-in-beige-suit-sitting-on-a-white-chair-SS1Oldoervo" },
  { id: "rArKfPZE-sg", category: "men", theme: "smart casual", source: "https://unsplash.com/photos/young-man-in-a-light-suit-sits-on-a-couch-rArKfPZE-sg" },
  { id: "eaUfKxpGCwM", category: "couples", theme: "summer", source: "https://unsplash.com/photos/a-couple-sitting-on-wooden-steps-outdoors-eaUfKxpGCwM" },
  { id: "CS2qxYl7GOo", category: "women", theme: "smart casual", source: "https://unsplash.com/photos/woman-in-a-beige-dress-and-scarf-holding-a-purse-CS2qxYl7GOo" },
  { id: "gokSMn1wzkc", category: "men", theme: "evening", source: "https://unsplash.com/photos/stylish-man-in-a-suit-adjusting-his-collar-gokSMn1wzkc" },
  { id: "vAULw-BRQcM", category: "couples", theme: "evening", source: "https://unsplash.com/photos/a-stylish-couple-posing-in-black-outfits-outdoors-vAULw-BRQcM" },
  { id: "bEN4kFj4Fm8", category: "women", theme: "summer", source: "https://unsplash.com/photos/a-woman-in-a-beige-strapless-top-and-skirt-bEN4kFj4Fm8" },
  { id: "5ENo-nQayzU", category: "men", theme: "smart casual", source: "https://unsplash.com/photos/a-man-in-a-suit-standing-on-a-dirt-road-5ENo-nQayzU" },
  { id: "yCwNqx6napk", category: "couples", theme: "smart casual", source: "https://unsplash.com/photos/stylish-couple-wearing-sunglasses-and-retro-fashion-yCwNqx6napk" },
  { id: "tO-fzwJ-mbc", category: "women", theme: "evening", source: "https://unsplash.com/photos/a-woman-in-a-beige-outfit-with-a-pink-scarf-tO-fzwJ-mbc" },
  { id: "MO1159nvYkE", category: "men", theme: "evening", source: "https://unsplash.com/photos/man-in-black-suit-and-sunglasses-with-hand-on-face-MO1159nvYkE" },
  { id: "-x1eLzEH2zo", category: "couples", theme: "evening", source: "https://unsplash.com/photos/couple-holding-hands-in-stylish-outfits--x1eLzEH2zo" },
  { id: "j3Gg3CMiyzs", category: "women", theme: "smart casual", source: "https://unsplash.com/photos/a-woman-in-a-hijab-and-loose-clothing-sits-gracefully-j3Gg3CMiyzs" },
  { id: "tjxuD1gSInM", category: "men", theme: "smart casual", source: "https://unsplash.com/photos/man-in-suit-bending-over-with-hands-on-hips-tjxuD1gSInM" },
  { id: "CgCLSjTULbo", category: "couples", theme: "summer", source: "https://unsplash.com/photos/a-couple-poses-in-a-park-with-a-cat-CgCLSjTULbo" },
] as const;
const HERO_INDEX_KEY = "lumiere-home-hero-index-v3";
const heroUrl = (id: string) =>
  "https://unsplash.com/photos/" + encodeURIComponent(id) + "/download?force=true&w=1600";

const SUGGESTIONS = [
  "Build me a smart-casual capsule wardrobe",
  "What should I wear to a summer wedding?",
  "Which colors suit a warm skin tone?",
  "Help me pack for a 5-day city trip",
];

export function ChatEmpty({ onPick }: { onPick: (prompt: string) => void }) {
  const styles = useStyles();
  const [heroIndex, setHeroIndex] = useState<number | null>(null);
  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const value = await AsyncStorage.getItem(HERO_INDEX_KEY);
        const previous = value === null ? -1 : Number(value);
        const next = Number.isInteger(previous) && previous >= 0 && previous < HERO_PHOTOS.length
          ? (previous + 1) % HERO_PHOTOS.length
          : Math.floor(Math.random() * HERO_PHOTOS.length);
        if (!active) return;
        setHeroIndex(next);
        await AsyncStorage.setItem(HERO_INDEX_KEY, String(next));
      } catch {
        if (active) setHeroIndex(Math.floor(Math.random() * HERO_PHOTOS.length));
      }
    })();
    return () => { active = false; };
  }, []);
  return (
    <ScrollView
      contentContainerStyle={styles.container}
      showsVerticalScrollIndicator={false}
      keyboardShouldPersistTaps="handled"
    >
      <View style={styles.heroWrap}>
        {heroIndex !== null && <Image source={{ uri: heroUrl(HERO_PHOTOS[heroIndex].id) }} style={styles.hero} contentFit="cover" transition={900} />}
        <LinearGradient
          colors={["transparent", "rgba(0,0,0,0.15)", "rgba(0,0,0,0.75)"]}
          style={styles.scrim}
        />
        <View style={styles.heroTextWrap}>
          <Text style={styles.kicker}>LUMIÈRE</Text>
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
