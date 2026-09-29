import { useEffect, useState } from "react";
import { View, Text, Pressable, TextInput, Platform, ActivityIndicator } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { KeyboardAwareScrollView } from "react-native-keyboard-controller";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Image } from "expo-image";
import Feather from "@react-native-vector-icons/feather";
import * as Haptics from "expo-haptics";

import { makeStyles, useTheme, fonts } from "@/src/theme";
import { usesNativeTabs } from "@/src/navigation";
import {
  getProfile,
  updateProfile,
  analyzeSkin,
  uploadImage,
  fileUrl,
  type Profile,
  type SkinAnalysis,
} from "@/src/api";
import { PhotoSourceSheet } from "@/src/components/PhotoSourceSheet";
import { RETAILERS } from "@/src/retailers";
import type { PickResult } from "@/src/utils/media";

const COLORS = ["Black", "White", "Navy", "Beige", "Olive", "Burgundy", "Camel", "Grey", "Blush", "Emerald", "Rust", "Denim"];
const STYLES = ["Minimal", "Classic", "Streetwear", "Boho", "Smart casual", "Formal", "Athleisure", "Vintage", "Edgy", "Preppy"];
const BUDGETS = ["Budget", "Mid-range", "Premium", "Luxury"];
const CLIMATES = ["hot", "mild", "cold"];
const FITS = ["slim", "regular", "relaxed"];
const PREF_STYLES = ["classic", "relaxed", "minimal", "romantic", "bold"];

export default function ProfileScreen() {
  const styles = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const queryClient = useQueryClient();

  const bottomPad = (usesNativeTabs ? insets.bottom : 0) + 40;

  const { data: profile } = useQuery({ queryKey: ["profile"], queryFn: getProfile });

  const [colorsSel, setColorsSel] = useState<string[]>([]);
  const [stylesSel, setStylesSel] = useState<string[]>([]);
  const [sizeTop, setSizeTop] = useState("");
  const [sizeBottom, setSizeBottom] = useState("");
  const [sizeShoe, setSizeShoe] = useState("");
  const [budget, setBudget] = useState<string | null>(null);
  const [notes, setNotes] = useState("");
  const [climate, setClimate] = useState("mild");
  const [prefStyle, setPrefStyle] = useState("classic");
  const [preferredFit, setPreferredFit] = useState("regular");
  const [likedColours, setLikedColours] = useState<string[]>([]);
  const [avoidedColours, setAvoidedColours] = useState<string[]>([]);
  const [retailers, setRetailers] = useState<string[]>(["zara", "hm", "uniqlo"]);
  const [seeded, setSeeded] = useState(false);
  const [sheetOpen, setSheetOpen] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [scanError, setScanError] = useState<string | null>(null);

  useEffect(() => {
    if (profile && !seeded) {
      setColorsSel(profile.favorite_colors ?? []);
      setStylesSel(profile.styles ?? []);
      setSizeTop(profile.sizes?.top ?? "");
      setSizeBottom(profile.sizes?.bottom ?? "");
      setSizeShoe(profile.sizes?.shoe ?? "");
      setBudget(profile.budget ?? null);
      setNotes(profile.notes ?? "");
      setClimate(profile.preferences?.climate ?? "mild");
      setPrefStyle(profile.preferences?.style ?? "classic");
      setPreferredFit(profile.preferences?.preferred_fit ?? "regular");
      setLikedColours(profile.preferences?.preferred_colours ?? []);
      setAvoidedColours(profile.preferences?.avoided_colours ?? []);
      setRetailers(profile.preferences?.preferred_retailers ?? ["zara", "hm", "uniqlo"]);
      setSeeded(true);
    }
  }, [profile, seeded]);

  const save = useMutation({
    mutationFn: (body: Partial<Profile>) => updateProfile(body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["profile"] });
      if (Platform.OS !== "web") Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
    },
  });

  const skin: SkinAnalysis | null | undefined = profile?.skin;

  const toggle = (list: string[], set: (v: string[]) => void, item: string) => {
    if (Platform.OS !== "web") Haptics.selectionAsync();
    set(list.includes(item) ? list.filter((x) => x !== item) : [...list, item]);
  };

  const handleSave = () => {
    save.mutate({
      favorite_colors: colorsSel,
      styles: stylesSel,
      sizes: { top: sizeTop, bottom: sizeBottom, shoe: sizeShoe },
      budget: budget ?? undefined,
      notes,
      preferences: {
        ...(profile?.preferences ?? { budget_min: 0, budget_max: 500, occasion: "casual", categories: [] }),
        climate: climate as "hot" | "mild" | "cold", style: prefStyle, preferred_fit: preferredFit,
        preferred_colours: likedColours, avoided_colours: avoidedColours, preferred_retailers: retailers,
      },
    });
  };

  const onScanPicked = async (asset: PickResult) => {
    setSheetOpen(false);
    setScanError(null);
    setScanning(true);
    try {
      const path = await uploadImage(asset.uri, asset.name, asset.type);
      await analyzeSkin(path);
      queryClient.invalidateQueries({ queryKey: ["profile"] });
      if (Platform.OS !== "web") Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
    } catch {
      setScanError("Couldn't analyze that photo. Try a clear, well-lit selfie.");
    } finally {
      setScanning(false);
    }
  };

  const Chip = ({ label, active, onPress }: { label: string; active: boolean; onPress: () => void }) => (
    <Pressable
      testID={`chip-${label}`}
      onPress={onPress}
      style={[styles.chip, active && styles.chipActive]}
    >
      <Text style={[styles.chipText, active && styles.chipTextActive]}>{label}</Text>
    </Pressable>
  );

  return (
    <View style={styles.root}>
      <View style={[styles.header, { paddingTop: insets.top + 8 }]}>
        <Text style={styles.title}>You</Text>
        <Text style={styles.subtitle}>Your stylist learns from this</Text>
      </View>

      <KeyboardAwareScrollView
        style={styles.flex}
        contentContainerStyle={{ padding: 20, paddingBottom: bottomPad }}
        showsVerticalScrollIndicator={false}
        bottomOffset={20}
      >
        {/* Skin tone */}
        <Text style={styles.sectionTitle}>Skin tone & colors</Text>
        {skin && skin.undertone ? (
          <View style={styles.skinCard} testID="skin-result">
            <View style={styles.skinTop}>
              {skin.image_path ? (
                <Image source={{ uri: fileUrl(skin.image_path) }} style={styles.skinAvatar} contentFit="cover" />
              ) : null}
              <View style={styles.flex}>
                <Text style={styles.undertone}>
                  {skin.undertone.replace("_", " ")}
                  {skin.season ? ` · ${skin.season}` : ""}
                </Text>
                <Text style={styles.skinDimensions}>
                  {skin.depth} · {skin.chroma} · {skin.contrast} contrast
                </Text>
                {skin.analysis_quality ? (
                  <Text style={styles.skinQuality}>
                    {skin.analysis_quality.confidence} confidence · {skin.analysis_quality.lighting_quality} lighting
                  </Text>
                ) : null}
                {skin.summary ? <Text style={styles.skinSummary}>{skin.summary}</Text> : null}
              </View>
            </View>
            {[
              ["Best neutrals", skin.best_neutrals],
              ["Best accents", skin.best_accents],
              ["Statement colours", skin.statement_colours],
              ["Use carefully near the face", skin.caution_colours],
            ].map(([label, swatches]) => (
              <View key={label as string}>
                <Text style={styles.swatchLabel}>{label as string}</Text>
                <View style={styles.swatchRow}>
                  {(swatches as typeof skin.palette).map((c, i) => (
                    <View key={`${c.name}-${i}`} style={styles.swatchItem}>
                      <View style={[styles.swatch, { backgroundColor: c.hex }]} />
                      <Text style={styles.swatchName} numberOfLines={2}>{c.name}</Text>
                    </View>
                  ))}
                </View>
              </View>
            ))}
            <Pressable testID="rescan-button" style={styles.scanBtnSm} onPress={() => setSheetOpen(true)}>
              <Feather name="refresh-ccw" size={15} color={colors.onSurface} />
              <Text style={styles.scanBtnSmText}>Re-scan</Text>
            </Pressable>
          </View>
        ) : (
          <Pressable testID="scan-skin-button" style={styles.scanCard} onPress={() => setSheetOpen(true)}>
            {scanning ? (
              <>
                <ActivityIndicator color={colors.onSurface} />
                <Text style={styles.scanText}>Analyzing your coloring…</Text>
              </>
            ) : (
              <>
                <Feather name="aperture" size={26} color={colors.onSurface} />
                <Text style={styles.scanTitle}>Scan your skin tone</Text>
                <Text style={styles.scanText}>Take a selfie to get your personal color palette</Text>
              </>
            )}
          </Pressable>
        )}
        {scanError && <Text style={styles.error}>{scanError}</Text>}

        {/* Favorite colors */}
        <Text style={styles.sectionTitle}>Favorite colors</Text>
        <View style={styles.chipWrap}>
          {COLORS.map((c) => (
            <Chip key={c} label={c} active={colorsSel.includes(c)} onPress={() => toggle(colorsSel, setColorsSel, c)} />
          ))}
        </View>

        {/* Styles */}
        <Text style={styles.sectionTitle}>Your style</Text>
        <View style={styles.chipWrap}>
          {STYLES.map((s) => (
            <Chip key={s} label={s} active={stylesSel.includes(s)} onPress={() => toggle(stylesSel, setStylesSel, s)} />
          ))}
        </View>

        <Text style={styles.sectionTitle}>Climate</Text>
        <View style={styles.chipWrap}>{CLIMATES.map((v) => <Chip key={v} label={v} active={climate === v} onPress={() => setClimate(v)} />)}</View>

        <Text style={styles.sectionTitle}>Preferred style</Text>
        <View style={styles.chipWrap}>{PREF_STYLES.map((v) => <Chip key={v} label={v} active={prefStyle === v} onPress={() => setPrefStyle(v)} />)}</View>

        <Text style={styles.sectionTitle}>Preferred fit</Text>
        <View style={styles.chipWrap}>{FITS.map((v) => <Chip key={v} label={v} active={preferredFit === v} onPress={() => setPreferredFit(v)} />)}</View>

        <Text style={styles.sectionTitle}>Colours you like</Text>
        <View style={styles.chipWrap}>{COLORS.map((v) => <Chip key={v} label={v} active={likedColours.includes(v.toLowerCase())} onPress={() => {
          const x = v.toLowerCase(); setLikedColours(likedColours.includes(x) ? likedColours.filter(c => c !== x) : [...likedColours, x]); setAvoidedColours(avoidedColours.filter(c => c !== x));
        }} />)}</View>

        <Text style={styles.sectionTitle}>Colours to avoid</Text>
        <Text style={styles.helper}>Selecting a colour here automatically removes it from your liked colours.</Text>
        <View style={styles.chipWrap}>{COLORS.map((v) => <Chip key={v} label={v} active={avoidedColours.includes(v.toLowerCase())} onPress={() => {
          const x = v.toLowerCase(); setAvoidedColours(avoidedColours.includes(x) ? avoidedColours.filter(c => c !== x) : [...avoidedColours, x]); setLikedColours(likedColours.filter(c => c !== x));
        }} />)}</View>

        <Text style={styles.sectionTitle}>Favourite retailers</Text>
        <View style={styles.chipWrap}>{RETAILERS.map((r) => <Chip key={r.id} label={r.name} active={retailers.includes(r.id)} onPress={() => toggle(retailers, setRetailers, r.id)} />)}</View>

        {/* Sizes */}
        <Text style={styles.sectionTitle}>Sizes</Text>
        <View style={styles.sizeRow}>
          <View style={styles.flex}>
            <Text style={styles.sizeLabel}>Top</Text>
            <TextInput testID="size-top" style={styles.sizeInput} value={sizeTop} onChangeText={setSizeTop} placeholder="M" placeholderTextColor={colors.muted} />
          </View>
          <View style={styles.flex}>
            <Text style={styles.sizeLabel}>Bottom</Text>
            <TextInput testID="size-bottom" style={styles.sizeInput} value={sizeBottom} onChangeText={setSizeBottom} placeholder="32" placeholderTextColor={colors.muted} />
          </View>
          <View style={styles.flex}>
            <Text style={styles.sizeLabel}>Shoe</Text>
            <TextInput testID="size-shoe" style={styles.sizeInput} value={sizeShoe} onChangeText={setSizeShoe} placeholder="9" placeholderTextColor={colors.muted} />
          </View>
        </View>

        {/* Budget */}
        <Text style={styles.sectionTitle}>Budget</Text>
        <View style={styles.chipWrap}>
          {BUDGETS.map((b) => (
            <Chip key={b} label={b} active={budget === b} onPress={() => setBudget(budget === b ? null : b)} />
          ))}
        </View>

        {/* Notes */}
        <Text style={styles.sectionTitle}>Anything else?</Text>
        <TextInput
          testID="notes-input"
          style={styles.notes}
          value={notes}
          onChangeText={setNotes}
          placeholder="e.g. I avoid heels, love natural fabrics, dress for a warm climate…"
          placeholderTextColor={colors.muted}
          multiline
        />

        <Pressable testID="save-profile-button" style={styles.saveBtn} onPress={handleSave} disabled={save.isPending}>
          {save.isPending ? (
            <ActivityIndicator color={colors.onBrandPrimary} size="small" />
          ) : (
            <Text style={styles.saveBtnText}>Save profile</Text>
          )}
        </Pressable>
        {save.isSuccess && !save.isPending && <Text style={styles.savedNote}>Saved ✓</Text>}
      </KeyboardAwareScrollView>

      <PhotoSourceSheet
        visible={sheetOpen}
        onClose={() => setSheetOpen(false)}
        onPicked={onScanPicked}
        title="Take a selfie"
      />
    </View>
  );
}

const useStyles = makeStyles((c) => ({
  root: { flex: 1, backgroundColor: c.surface },
  flex: { flex: 1 },
  header: { paddingHorizontal: 20, paddingBottom: 12, borderBottomWidth: 1, borderBottomColor: c.border },
  title: { fontFamily: fonts.display, fontSize: 30, fontWeight: "700", color: c.onSurface },
  subtitle: { fontFamily: fonts.text, fontSize: 13, color: c.muted, marginTop: 4 },
  sectionTitle: {
    fontFamily: fonts.text,
    fontSize: 12,
    letterSpacing: 1.5,
    textTransform: "uppercase",
    color: c.muted,
    marginTop: 28,
    marginBottom: 14,
  },
  scanCard: {
    borderWidth: 1,
    borderColor: c.borderStrong,
    borderRadius: 4,
    paddingVertical: 28,
    alignItems: "center",
    gap: 8,
  },
  scanTitle: { fontFamily: fonts.display, fontSize: 20, fontWeight: "700", color: c.onSurface },
  scanText: { fontFamily: fonts.text, fontSize: 13, color: c.muted, textAlign: "center", paddingHorizontal: 20 },
  skinCard: { borderWidth: 1, borderColor: c.border, borderRadius: 4, padding: 16, backgroundColor: c.surfaceSecondary },
  skinTop: { flexDirection: "row", gap: 14, alignItems: "center", marginBottom: 16 },
  skinAvatar: { width: 56, height: 56, borderRadius: 4, backgroundColor: c.surfaceTertiary },
  undertone: { fontFamily: fonts.display, fontSize: 20, fontWeight: "700", color: c.onSurface, textTransform: "capitalize" },
  skinDimensions: { fontFamily: fonts.text, fontSize: 12, color: c.onSurfaceSecondary, marginTop: 3, textTransform: "capitalize" },
  skinQuality: { fontFamily: fonts.text, fontSize: 11, color: c.muted, marginTop: 3, textTransform: "capitalize" },
  skinSummary: { fontFamily: fonts.text, fontSize: 13, lineHeight: 19, color: c.onSurfaceTertiary, marginTop: 6 },
  swatchLabel: {
    fontFamily: fonts.text,
    fontSize: 11,
    letterSpacing: 1,
    textTransform: "uppercase",
    color: c.muted,
    marginTop: 8,
    marginBottom: 10,
  },
  swatchRow: { flexDirection: "row", flexWrap: "wrap", gap: 12 },
  swatchItem: { width: 58, alignItems: "center" },
  swatch: { width: 40, height: 40, borderRadius: 4, borderWidth: 1, borderColor: c.border },
  swatchName: { fontFamily: fonts.text, fontSize: 10, color: c.onSurfaceTertiary, marginTop: 5 },
  scanBtnSm: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    alignSelf: "flex-start",
    marginTop: 16,
    paddingVertical: 8,
    paddingHorizontal: 14,
    borderWidth: 1,
    borderColor: c.borderStrong,
    borderRadius: 4,
  },
  scanBtnSmText: { fontFamily: fonts.text, fontSize: 14, color: c.onSurface },
  chipWrap: { flexDirection: "row", flexWrap: "wrap", gap: 10 },
  chip: {
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: c.border,
    backgroundColor: c.surfaceSecondary,
  },
  chipActive: { backgroundColor: c.brandPrimary, borderColor: c.brandPrimary },
  chipText: { fontFamily: fonts.text, fontSize: 14, color: c.onSurfaceSecondary },
  chipTextActive: { color: c.onBrandPrimary },
  sizeRow: { flexDirection: "row", gap: 12 },
  sizeLabel: { fontFamily: fonts.text, fontSize: 12, color: c.muted, marginBottom: 6 },
  sizeInput: {
    borderWidth: 1,
    borderColor: c.border,
    backgroundColor: c.surfaceTertiary,
    borderRadius: 4,
    paddingHorizontal: 12,
    paddingVertical: 12,
    fontFamily: fonts.text,
    fontSize: 15,
    color: c.onSurface,
    textAlign: "center",
  },
  notes: {
    borderWidth: 1,
    borderColor: c.border,
    backgroundColor: c.surfaceTertiary,
    borderRadius: 4,
    padding: 14,
    minHeight: 90,
    fontFamily: fonts.text,
    fontSize: 15,
    color: c.onSurface,
    textAlignVertical: "top",
  },
  saveBtn: {
    height: 54,
    borderRadius: 4,
    backgroundColor: c.brandPrimary,
    alignItems: "center",
    justifyContent: "center",
    marginTop: 32,
  },
  saveBtnText: { fontFamily: fonts.text, fontSize: 16, color: c.onBrandPrimary },
  savedNote: { fontFamily: fonts.text, fontSize: 13, color: c.success, textAlign: "center", marginTop: 12 },
  helper: { fontFamily: fonts.text, fontSize: 12, lineHeight: 17, color: c.muted, marginTop: -8, marginBottom: 12 },
  error: { fontFamily: fonts.text, fontSize: 13, color: c.error, marginTop: 12 },
}));
