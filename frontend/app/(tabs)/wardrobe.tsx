import { useState } from "react";
import { View, Text, ScrollView, Pressable, TextInput, ActivityIndicator } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { Image } from "expo-image";
import { AccountPhoto } from "@/src/components/AccountPhoto";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Feather from "@react-native-vector-icons/feather";
import { makeStyles, fonts } from "@/src/theme";
import { uploadImage, fileUrl, listWardrobe, addWardrobeItem, deleteWardrobeItem, getWardrobeOutfits, getCapsulePlan, type OutfitPlan, type CapsulePlan, type WardrobeItem } from "@/src/api";
import { PhotoSourceSheet } from "@/src/components/PhotoSourceSheet";
import type { PickResult } from "@/src/utils/media";

const CATEGORIES: WardrobeItem["category"][] = ["top", "bottom", "dress", "outerwear", "shoes", "accessory", "other"];

export default function WardrobeScreen() {
  const styles = useStyles();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const client = useQueryClient();
  const { data: items = [], isLoading } = useQuery({ queryKey: ["wardrobe"], queryFn: listWardrobe });
  const [sheetOpen, setSheetOpen] = useState(false);
  const [photoPath, setPhotoPath] = useState<string | null>(null);
  const [photoPreview, setPhotoPreview] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [colour, setColour] = useState("");
  const [category, setCategory] = useState<WardrobeItem["category"]>("top");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [outfitSelection, setOutfitSelection] = useState<WardrobeItem[]>([]);
  const [occasion, setOccasion] = useState("casual");
  const [climate, setClimate] = useState<"hot" | "mild" | "cold">("mild");
  const [plannedOutfits, setPlannedOutfits] = useState<OutfitPlan[]>([]);
  const [capsule, setCapsule] = useState<CapsulePlan | null>(null);
  const save = useMutation({
    mutationFn: addWardrobeItem,
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["wardrobe"] });
      setPhotoPath(null); setPhotoPreview(null); setName(""); setColour(""); setError(null);
    },
    onError: (e: Error) => setError(e.message),
  });
  const del = useMutation({
    mutationFn: deleteWardrobeItem,
    onSuccess: () => client.invalidateQueries({ queryKey: ["wardrobe"] }),
    onError: (e: Error) => setError(e.message),
  });
  const onPicked = async (asset: PickResult) => {
    setSheetOpen(false); setBusy(true); setError(null);
    try {
      const path = await uploadImage(asset.uri, asset.name, asset.type);
      setPhotoPath(path); setPhotoPreview(asset.uri);
    } catch (e) { setError(e instanceof Error ? e.message : "Upload failed"); }
    finally { setBusy(false); }
  };
  const toggleOutfit = (item: WardrobeItem) => {
    setOutfitSelection((current) => current.some((i) => i.id === item.id)
      ? current.filter((i) => i.id !== item.id)
      : current.length < 2 ? [...current, item] : current);
  };
  const tryOutfit = () => {
    if (outfitSelection.length !== 2) return;
    const [first, second] = outfitSelection;
    router.push({ pathname: "/(tabs)/tryon", params: {
      garmentPath: first.image_path, garmentName: first.name,
      secondGarmentPath: second.image_path, secondGarmentName: second.name,
    } });
  };
  const tryItem = (item: WardrobeItem) => {
    router.push({ pathname: "/(tabs)/tryon", params: { garmentPath: item.image_path, garmentName: item.name } });
  };
  return (
    <View style={[styles.root, { paddingTop: insets.top + 8 }]}>
      <Text style={styles.title}>My Wardrobe</Text>
      <Text style={styles.subtitle}>Keep track of pieces you own and try them on.</Text>
      <ScrollView contentContainerStyle={{ padding: 18, paddingBottom: insets.bottom + 60 }}>
        <View style={styles.form}>
          <Text style={styles.heading}>Add something you own</Text>
          <Pressable testID="wardrobe-add-photo" style={styles.photoButton} onPress={() => setSheetOpen(true)}>
            {photoPreview ? <Image source={{ uri: photoPreview }} style={styles.preview} contentFit="cover" /> : <Text style={styles.action}>+ Choose a garment photo</Text>}
          </Pressable>
          <TextInput testID="wardrobe-name" style={styles.input} value={name} onChangeText={setName} placeholder="Name, e.g. linen shirt" placeholderTextColor="#888" maxLength={120} />
          <TextInput testID="wardrobe-colour" style={styles.input} value={colour} onChangeText={setColour} placeholder="Colour (optional)" placeholderTextColor="#888" maxLength={80} />
          <View style={styles.chips}>{CATEGORIES.map((c) => (
            <Pressable key={c} style={[styles.chip, category === c && styles.active]} onPress={() => setCategory(c)}>
              <Text style={styles.chipText}>{c}</Text>
            </Pressable>
          ))}</View>
          <Pressable testID="wardrobe-save" style={[styles.button, (!photoPath || !name.trim() || busy || save.isPending) && styles.disabled]}
            disabled={!photoPath || !name.trim() || busy || save.isPending}
            onPress={() => save.mutate({ name: name.trim(), category, colour: colour.trim(), image_path: photoPath!, notes: "" })}>
            <Text style={styles.buttonText}>{busy || save.isPending ? "Saving…" : "Save to wardrobe"}</Text>
          </Pressable>
          {error ? <Text style={styles.error}>{error}</Text> : null}
          <Text style={styles.note}>Removing an item hides its wardrobe record; uploaded photos are not yet permanently erased from storage.</Text>
        </View>
        <View style={styles.form}>
          <Text style={styles.heading}>Plan what to wear</Text>
          <TextInput style={styles.input} value={occasion} onChangeText={setOccasion} placeholder="Occasion (e.g. work, weekend)" placeholderTextColor="#888" maxLength={80} />
          <View style={styles.chips}>{(["hot", "mild", "cold"] as const).map((value) => (
            <Pressable key={value} onPress={() => setClimate(value)} style={[styles.chip, climate === value && styles.active]}><Text style={styles.chipText}>{value}</Text></Pressable>
          ))}</View>
          <Text style={styles.note}>Choose a climate preference. Live weather is not connected.</Text>
          <Pressable testID="wardrobe-plan-outfits" style={styles.button} onPress={async () => {
            try { const result = await getWardrobeOutfits(occasion, climate); setPlannedOutfits(result.outfits); setError(null); }
            catch (e) { setError(e instanceof Error ? e.message : "Planning failed"); }
          }}><Text style={styles.buttonText}>Suggest outfits</Text></Pressable>
          <Pressable testID="wardrobe-plan-capsule" style={[styles.button, { marginTop: 8 }]} onPress={async () => {
            try { setCapsule(await getCapsulePlan(occasion, climate)); setError(null); }
            catch (e) { setError(e instanceof Error ? e.message : "Capsule planning failed"); }
          }}><Text style={styles.buttonText}>Build capsule wardrobe</Text></Pressable>
          {plannedOutfits.map((outfit, index) => <View key={index} style={styles.planned}>
            <Text style={styles.itemName}>{outfit.names.join(" + ")}</Text>
            <Text style={styles.note}>{outfit.reason}</Text>
            {outfit.item_ids.length >= 2 && <Pressable onPress={() => {
              const chosen = outfit.item_ids.map((id) => items.find((item) => item.id === id)).filter((item): item is WardrobeItem => Boolean(item));
              if (chosen.length >= 2) setOutfitSelection(chosen.slice(0, 2));
            }}><Text style={styles.action}>Select first two for try-on</Text></Pressable>}
          </View>)}
          {capsule && <View style={styles.planned}>
            <Text style={styles.heading}>Your capsule ({capsule.items.length} pieces)</Text>
            <Text style={styles.note}>{capsule.items.map((item) => item.name).join(" · ") || "Add wardrobe items to begin."}</Text>
            <Text style={styles.itemName}>Pieces to consider</Text>
            <Text style={styles.note}>{capsule.missing_categories.join(" · ") || "No basic category gaps identified."}</Text>
            <Text style={styles.note}>{capsule.possible_outfits.length} possible combinations from these pieces (not fit-verified).</Text>
          </View>}
        </View>
        <Text style={styles.heading}>Your pieces ({items.length})</Text>
        {outfitSelection.length > 0 && <View style={styles.form}>
          <Text style={styles.itemName}>{outfitSelection.length}/2 garments selected</Text>
          <Text style={styles.note}>{outfitSelection.map((item) => item.name).join(" + ")}</Text>
          <Pressable testID="wardrobe-try-outfit" style={[styles.button, outfitSelection.length !== 2 && styles.disabled]} disabled={outfitSelection.length !== 2} onPress={tryOutfit}>
            <Text style={styles.buttonText}>Try both together</Text>
          </Pressable>
          <Pressable onPress={() => setOutfitSelection([])}><Text style={styles.action}>Clear selection</Text></Pressable>
        </View>}
        {isLoading ? <ActivityIndicator /> : items.length === 0 ? <Text style={styles.note}>Your wardrobe is empty. Add a garment to get started.</Text> : null}
        <View style={styles.grid}>{items.map((item) => (
          <View key={item.id} style={styles.item}>
            <AccountPhoto path={item.image_path} style={styles.itemPhoto} contentFit="cover" />
            <Text style={styles.itemName}>{item.name}</Text>
            <Text style={styles.note}>{item.category}{item.colour ? ` · ${item.colour}` : ""}</Text>
            <Pressable testID={`wardrobe-try-${item.id}`} onPress={() => tryItem(item)}><Text style={styles.action}>Try on</Text></Pressable>
            <Pressable testID={`wardrobe-select-${item.id}`} onPress={() => toggleOutfit(item)}>
              <Text style={styles.action}>{outfitSelection.some((i) => i.id === item.id) ? "✓ Selected" : "+ Add to outfit"}</Text>
            </Pressable>
            <Pressable testID={`wardrobe-delete-${item.id}`} onPress={() => { setOutfitSelection((current) => current.filter((i) => i.id !== item.id)); del.mutate(item.id); }}><Text style={styles.note}>Remove from wardrobe</Text></Pressable>
          </View>
        ))}</View>
      </ScrollView>
      <PhotoSourceSheet visible={sheetOpen} onClose={() => setSheetOpen(false)} onPicked={onPicked} title="Photograph a garment" />
    </View>
  );
}

const useStyles = makeStyles((c) => ({
  root: { flex: 1, backgroundColor: c.surface },
  title: { fontFamily: fonts.display, fontSize: 28, color: c.onSurface, marginHorizontal: 20 },
  subtitle: { fontFamily: fonts.text, fontSize: 13, color: c.muted, marginHorizontal: 20, marginBottom: 12 },
  heading: { fontFamily: fonts.display, fontSize: 20, color: c.onSurface, marginVertical: 12 },
  form: { padding: 16, borderWidth: 1, borderColor: c.border, marginBottom: 18 },
  photoButton: { height: 150, borderWidth: 1, borderColor: c.borderStrong, justifyContent: "center", alignItems: "center", marginBottom: 10 },
  preview: { width: "100%", height: "100%" },
  input: { borderWidth: 1, borderColor: c.border, padding: 12, marginBottom: 10, color: c.onSurface, fontFamily: fonts.text },
  chips: { flexDirection: "row", flexWrap: "wrap", gap: 7, marginBottom: 12 },
  chip: { paddingHorizontal: 10, paddingVertical: 8, borderWidth: 1, borderColor: c.border },
  active: { backgroundColor: c.surfaceTertiary, borderColor: c.borderStrong },
  chipText: { fontFamily: fonts.text, color: c.onSurface, fontSize: 12 },
  button: { backgroundColor: c.brandPrimary, padding: 14, alignItems: "center" },
  disabled: { opacity: 0.4 },
  buttonText: { color: c.onBrandPrimary, fontFamily: fonts.text },
  error: { color: c.error, fontFamily: fonts.text, marginTop: 8 },
  note: { color: c.muted, fontFamily: fonts.text, fontSize: 12, marginTop: 6 },
  grid: { flexDirection: "row", flexWrap: "wrap", gap: 12 },
  planned: { borderTopWidth: 1, borderTopColor: c.border, paddingTop: 12, marginTop: 12, gap: 5 },
  item: { width: "47%", borderWidth: 1, borderColor: c.border, padding: 10, gap: 5 },
  itemPhoto: { width: "100%", aspectRatio: 0.85 },
  itemName: { color: c.onSurface, fontFamily: fonts.text, fontSize: 14 },
  action: { color: c.onSurface, fontFamily: fonts.text, fontSize: 13, textDecorationLine: "underline", marginTop: 7 },
}));
