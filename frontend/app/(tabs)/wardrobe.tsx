import { useState, useRef } from "react";
import { View, Text, ScrollView, Pressable, TextInput, ActivityIndicator } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { Image } from "expo-image";
import { AccountPhoto } from "@/src/components/AccountPhoto";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Feather from "@react-native-vector-icons/feather";
import { makeStyles, fonts } from "@/src/theme";
import { uploadImage, fileUrl, listWardrobe, addWardrobeItem, recognizeWardrobePhoto, correctWardrobeItem, deleteWardrobeItem, createPreLovedDraft, getMyPreLovedListings, getPreLovedReadiness, setPreLovedStatus, getWardrobeOutfits, getCapsulePlan, type OutfitPlan, type CapsulePlan, type WardrobeItem } from "@/src/api";
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
  const [style, setStyle] = useState("");
  const [pattern, setPattern] = useState("");
  const [season, setSeason] = useState("");
  const [material, setMaterial] = useState("");
  const [recognitionLoading, setRecognitionLoading] = useState(false);
  const [autoRecognize, setAutoRecognize] = useState(false);
  const [recognitionMessage, setRecognitionMessage] = useState("");
  const uploadedPhotoRef = useRef<string | null>(null);
  const [category, setCategory] = useState<WardrobeItem["category"]>("top");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [outfitSelection, setOutfitSelection] = useState<WardrobeItem[]>([]);
  const [occasion, setOccasion] = useState("casual");
  const [climate, setClimate] = useState<"hot" | "mild" | "cold">("mild");
  const [plannedOutfits, setPlannedOutfits] = useState<OutfitPlan[]>([]);
  const [capsule, setCapsule] = useState<CapsulePlan | null>(null);
  const [editing, setEditing] = useState<WardrobeItem | null>(null);
  const [selling, setSelling] = useState<WardrobeItem | null>(null);
  const [saleSize, setSaleSize] = useState("");
  const [salePrice, setSalePrice] = useState("");
  const [saleCondition, setSaleCondition] = useState("good");
  const [swapAccepted, setSwapAccepted] = useState(false);
  const [saleDescription, setSaleDescription] = useState("");
  const {data: preLovedReadiness} = useQuery({
    queryKey:["preloved-readiness"], queryFn:getPreLovedReadiness,
  });
  const {data: myListings = [], isLoading: listingsLoading} = useQuery({
    queryKey:["preloved-mine"], queryFn:getMyPreLovedListings,
  });
  const draftSale = useMutation({
    mutationFn: createPreLovedDraft,
    onSuccess:() => {
      client.invalidateQueries({queryKey:["preloved-mine"]});
      setSelling(null); setSaleSize(""); setSalePrice(""); setSaleDescription(""); setSwapAccepted(false); setError(null);
    },
    onError:(e:Error)=>setError(e.message),
  });
  const changeSaleStatus = useMutation({
    mutationFn: ({id,status}:{id:string;status:"published"|"paused"|"withdrawn"})=>
      setPreLovedStatus(id,status),
    onSuccess:()=> {
      client.invalidateQueries({queryKey:["preloved-mine"]});
      client.invalidateQueries({queryKey:["preloved-browse"]});
      setError(null);
    },
    onError:(e:Error)=>setError(e.message),
  });
  const save = useMutation({
    mutationFn: addWardrobeItem,
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["wardrobe"] });
      setPhotoPath(null); uploadedPhotoRef.current = null; setPhotoPreview(null); setName(""); setColour(""); setStyle(""); setPattern(""); setSeason(""); setMaterial(""); setRecognitionMessage(""); setError(null);
    },
    onError: (e: Error) => setError(e.message),
  });
  const correction = useMutation({
    mutationFn: (item: WardrobeItem) => correctWardrobeItem(item.id, {
      name:item.name, category:item.category, colour:item.colour, style:item.style || "",
      pattern:item.pattern || "", season:item.season || "", material:item.material || "",
    }),
    onSuccess: () => {
      client.invalidateQueries({queryKey:["wardrobe"]});
      client.invalidateQueries({queryKey:["wardrobe-outfits"]});
      client.invalidateQueries({queryKey:["mixed-wardrobe-outfits"]});
      setEditing(null); setPlannedOutfits([]); setCapsule(null); setError(null);
    },
    onError:(e:Error) => setError(e.message),
  });
  const del = useMutation({
    mutationFn: deleteWardrobeItem,
    onSuccess: () => client.invalidateQueries({ queryKey: ["wardrobe"] }),
    onError: (e: Error) => setError(e.message),
  });
  const onPicked = async (asset: PickResult) => {
    setSheetOpen(false); setBusy(true); setError(null);
    try {
      const path = await uploadImage(asset.uri, asset.name, asset.type, "garment");
      uploadedPhotoRef.current = path;
      setPhotoPath(path); setPhotoPreview(asset.uri);
      setRecognitionMessage("Photo uploaded. Analyse it to suggest garment details, or complete the fields yourself.");
      if (autoRecognize) await recognizePhoto(path);
    } catch (e) { setError(e instanceof Error ? e.message : "Upload failed"); }
    finally { setBusy(false); }
  };
  const recognizePhoto = async (pathOverride?: string) => {
    const requestedPath = pathOverride || photoPath;
    if (!requestedPath || recognitionLoading) return;
    setRecognitionLoading(true); setRecognitionMessage("");
    try {
      const suggestion = await recognizeWardrobePhoto(requestedPath);
      // Ignore an answer for a photograph that has since been replaced.
      if (uploadedPhotoRef.current !== requestedPath) return;
      if (suggestion.name) setName(suggestion.name);
      if (suggestion.colour) setColour(suggestion.colour);
      setCategory(suggestion.category);
      if (suggestion.style && suggestion.style !== "other") setStyle(suggestion.style);
      if (suggestion.pattern && suggestion.pattern !== "other") setPattern(suggestion.pattern);
      if (suggestion.season && suggestion.season !== "unknown") setSeason(suggestion.season);
      setRecognitionMessage("AI suggestions applied. Please verify the category, colour and style, then save only if correct.");
    } catch (e) {
      if (uploadedPhotoRef.current === requestedPath) setRecognitionMessage(
        "Recognition unavailable. You can enter garment details manually. No details were saved.");
    } finally { setRecognitionLoading(false); }
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
          <Pressable accessibilityRole="checkbox" accessibilityState={{ checked: autoRecognize }}
            onPress={() => setAutoRecognize(value => !value)}
            style={{ paddingVertical: 12, minHeight: 44 }}>
            <Text style={styles.note}>{autoRecognize ? "☑" : "☐"} Automatically analyse each new photo (opt-in; may incur AI usage charges)</Text>
          </Pressable>
          <Pressable testID="wardrobe-add-photo" style={styles.photoButton} onPress={() => setSheetOpen(true)}>
            {photoPreview ? <Image source={{ uri: photoPreview }} style={styles.preview} contentFit="cover" /> : <Text style={styles.action}>+ Choose a garment photo</Text>}
          </Pressable>
          <Pressable testID="wardrobe-analyse-photo" accessibilityRole="button"
            disabled={!photoPath || busy || recognitionLoading || save.isPending}
            style={[styles.button, (!photoPath || busy || recognitionLoading) && styles.disabled]}
            onPress={() => recognizePhoto()}>
            <Text style={styles.buttonText}>{recognitionLoading ? "Recognising garment…" : "Analyse photo · suggest details"}</Text>
          </Pressable>
          <Text style={styles.note}>Optional AI image recognition sends this photograph to the configured provider and may incur a usage charge. Nothing is saved until you confirm and tap Save.</Text>
          {recognitionMessage ? <Text accessibilityLiveRegion="polite" style={styles.note}>{recognitionMessage}</Text> : null}
          <TextInput testID="wardrobe-name" style={styles.input} value={name} onChangeText={setName} placeholder="Name, e.g. linen shirt" placeholderTextColor="#888" maxLength={120} />
          <TextInput testID="wardrobe-colour" style={styles.input} value={colour} onChangeText={setColour} placeholder="Colour (optional)" placeholderTextColor="#888" maxLength={80} />
          <TextInput testID="wardrobe-style" style={styles.input} value={style} onChangeText={setStyle} placeholder="Style (e.g. casual, business, formal)" placeholderTextColor="#888" maxLength={80} />
          <TextInput testID="wardrobe-pattern" style={styles.input} value={pattern} onChangeText={setPattern} placeholder="Pattern (e.g. solid, striped, floral)" placeholderTextColor="#888" maxLength={80} />
          <TextInput testID="wardrobe-season" style={styles.input} value={season} onChangeText={setSeason} placeholder="Season (e.g. warm weather, all season)" placeholderTextColor="#888" maxLength={80} />
          <TextInput testID="wardrobe-material" style={styles.input} value={material} onChangeText={setMaterial} placeholder="Fabric/material (optional; enter from the label)" placeholderTextColor="#888" maxLength={80} />
          <Text style={styles.note}>Review each AI suggestion. Material is never inferred from the image; enter it from the clothing label if known.</Text>
          <View style={styles.chips}>{CATEGORIES.map((c) => (
            <Pressable key={c} style={[styles.chip, category === c && styles.active]} onPress={() => setCategory(c)}>
              <Text style={styles.chipText}>{c}</Text>
            </Pressable>
          ))}</View>
          <Pressable testID="wardrobe-save" style={[styles.button, (!photoPath || !name.trim() || busy || recognitionLoading || save.isPending) && styles.disabled]}
            disabled={!photoPath || !name.trim() || busy || recognitionLoading || save.isPending}
            onPress={() => save.mutate({ name: name.trim(), category, colour: colour.trim(), style: style.trim(), pattern: pattern.trim(), season: season.trim(), material: material.trim(), image_path: photoPath!, notes: "" })}>
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
            {typeof outfit.compatibility_score === "number" ?
              <Text style={styles.note}>Compatibility ranking: {outfit.compatibility_score}/100 · Relative style estimate, not a fit guarantee</Text> : null}
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
        <Text style={styles.heading}>Pre-Loved · Optional</Text>
        <Text style={styles.note}>Your personal stylist remains the focus. You can prepare a sale listing from an item you own, but it stays private until you explicitly publish. No photographs, personal details, chat or payments are shared.</Text>
        <Text style={styles.note}>{preLovedReadiness?.notice || "Public listings are gated until the Pre-Loved pilot is approved."}</Text>
        {selling ? <View style={styles.form}>
          <Text style={styles.heading}>Prepare a listing · {selling.name}</Text>
          <Text style={styles.note}>Your garment details are reused. Buyers see text details only, not your private photograph or account information.</Text>
          <TextInput testID="preloved-size" accessibilityLabel="Garment size" style={styles.input}
            placeholder="Size (required)" placeholderTextColor="#888" maxLength={30}
            value={saleSize} onChangeText={setSaleSize} />
          <TextInput testID="preloved-price" accessibilityLabel="Asking price in Australian dollars" style={styles.input}
            placeholder="Asking price AUD" placeholderTextColor="#888" keyboardType="decimal-pad"
            value={salePrice} onChangeText={setSalePrice} />
          <Text style={styles.note}>Garment condition</Text>
          <View style={styles.chips}>{(["new with tags","like new","good","fair"] as const).map(value=>(
            <Pressable key={value} accessibilityRole="button" accessibilityState={{selected:saleCondition===value}}
              onPress={()=>setSaleCondition(value)} style={[styles.chip,saleCondition===value&&styles.active]}>
              <Text style={styles.chipText}>{value}</Text>
            </Pressable>
          ))}</View>
          <Pressable accessibilityRole="checkbox" accessibilityState={{checked:swapAccepted}}
            onPress={()=>setSwapAccepted(value=>!value)} style={{minHeight:44,paddingVertical:12}}>
            <Text style={styles.note}>{swapAccepted?"☑":"☐"} Also open to swapping this garment (no swaps can be arranged in the pilot yet)</Text>
          </Pressable>
          <TextInput testID="preloved-description" accessibilityLabel="Garment description"
            style={styles.input} multiline maxLength={500}
            placeholder="Optional garment description. No contact details or links."
            placeholderTextColor="#888" value={saleDescription} onChangeText={setSaleDescription}/>
          <Pressable accessibilityRole="button" testID="preloved-save-draft"
            style={[styles.button,(!saleSize.trim()||!salePrice||draftSale.isPending)&&styles.disabled]}
            disabled={!saleSize.trim()||!salePrice||draftSale.isPending}
            onPress={()=>draftSale.mutate({wardrobe_item_id:selling.id,size:saleSize.trim(),
              price:Number(salePrice),condition:saleCondition,currency:"AUD",
              description:saleDescription,delivery:"arrange later",swap_accepted:swapAccepted})}>
            <Text style={styles.buttonText}>{draftSale.isPending?"Saving…":"Save private draft"}</Text>
          </Pressable>
          <Pressable accessibilityRole="button" onPress={()=>setSelling(null)} style={{paddingVertical:12}}>
            <Text style={styles.action}>Cancel listing</Text>
          </Pressable>
        </View>:null}
        {listingsLoading?<ActivityIndicator accessibilityLabel="Loading your listing drafts"/>:null}
        {myListings.map(listing=>(
          <View key={listing.id} style={styles.form}>
            <Text style={styles.itemName}>{items.find(x=>x.id===listing.wardrobe_item_id)?.name || "Wardrobe garment"} · {listing.status}</Text>
            <Text style={styles.note}>AUD {listing.price.toFixed(2)} · {listing.condition} · Size {listing.size}{listing.swap_accepted?" · Open to swapping":""}</Text>
            {listing.status!=="withdrawn" ? <View style={styles.chips}>
              {listing.status!=="published" ? <Pressable accessibilityRole="button"
                disabled={changeSaleStatus.isPending || preLovedReadiness?.publishing_enabled !== true}
                onPress={()=>changeSaleStatus.mutate({id:listing.id,status:"published"})}
                style={styles.chip}><Text style={styles.chipText}>Publish listing</Text></Pressable> : null}
              {listing.status==="published" ? <Pressable accessibilityRole="button"
                disabled={changeSaleStatus.isPending}
                onPress={()=>changeSaleStatus.mutate({id:listing.id,status:"paused"})}
                style={styles.chip}><Text style={styles.chipText}>Pause</Text></Pressable> : null}
              <Pressable accessibilityRole="button" disabled={changeSaleStatus.isPending}
                onPress={()=>changeSaleStatus.mutate({id:listing.id,status:"withdrawn"})}
                style={styles.chip}><Text style={styles.chipText}>Withdraw listing</Text></Pressable>
            </View>:null}
            {listing.status==="draft" ? <Text style={styles.note}>Publishing shares the garment description and asking price with other signed-in users. Your photo and identity stay private.</Text>:null}
          </View>
        ))}
        <Text style={styles.heading}>Your pieces ({items.length})</Text>
        {editing ? <View style={styles.form}>
          <Text style={styles.heading}>Correct garment details</Text>
          <Text style={styles.note}>Update the labels you confirmed earlier. Your original private photograph is retained.</Text>
          {(["name","colour","style","pattern","season","material"] as const).map(key => (
            <TextInput key={key} testID={`wardrobe-edit-${key}`}
              accessibilityLabel={`Edit garment ${key}`} style={styles.input}
              placeholder={key} placeholderTextColor="#888"
              value={editing[key] || ""}
              onChangeText={value => setEditing(current => current ? {...current,[key]:value} : current)}
              maxLength={key === "name" ? 120 : 80} />
          ))}
          <View style={styles.chips}>{CATEGORIES.map(key => (
            <Pressable key={key} accessibilityRole="button"
              accessibilityState={{selected:editing.category===key}}
              style={[styles.chip,editing.category===key && styles.active]}
              onPress={() => setEditing(current=>current?{...current,category:key}:current)}>
              <Text style={styles.chipText}>{key}</Text>
            </Pressable>
          ))}</View>
          <Pressable accessibilityRole="button" testID="wardrobe-save-corrections"
            disabled={!editing.name.trim() || correction.isPending}
            onPress={() => correction.mutate(editing)}
            style={[styles.button,(!editing.name.trim()||correction.isPending)&&styles.disabled]}>
            <Text style={styles.buttonText}>{correction.isPending ? "Saving changes…" : "Save corrected details"}</Text>
          </Pressable>
          <Pressable accessibilityRole="button" onPress={() => setEditing(null)} style={{paddingVertical:12}}>
            <Text style={styles.action}>Cancel edits</Text>
          </Pressable>
        </View> : null}
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
            <Text style={styles.note}>{item.category}{item.colour ? ` · ${item.colour}` : ""}{item.style ? ` · ${item.style}` : ""}{item.pattern ? ` · ${item.pattern}` : ""}{item.season ? ` · ${item.season}` : ""}</Text>
            <Pressable testID={`wardrobe-try-${item.id}`} onPress={() => tryItem(item)}><Text style={styles.action}>Try on</Text></Pressable>
            <Pressable testID={`wardrobe-select-${item.id}`} onPress={() => toggleOutfit(item)}>
              <Text style={styles.action}>{outfitSelection.some((i) => i.id === item.id) ? "✓ Selected" : "+ Add to outfit"}</Text>
            </Pressable>
            <Pressable accessibilityRole="button" testID={`wardrobe-sell-${item.id}`}
              onPress={()=>{setSelling(item);setSalePrice("");setSaleSize("");setSaleDescription("");setError(null);}}>
              <Text style={styles.action}>Sell as Pre-Loved (optional)</Text>
            </Pressable>
            <Pressable accessibilityRole="button" testID={`wardrobe-edit-${item.id}`}
              onPress={() => { setEditing({...item}); setError(null); }}>
              <Text style={styles.action}>Correct details</Text>
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
