import { useEffect, useRef, useState } from "react";
import { useLocalSearchParams, useRouter } from "expo-router";
import {
  View,
  Text,
  ScrollView,
  Pressable,
  TextInput,
  Platform,
  ActivityIndicator,
  Modal,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { KeyboardAwareScrollView } from "react-native-keyboard-controller";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Image } from "expo-image";
import { AccountPhoto } from "@/src/components/AccountPhoto";
import Feather from "@react-native-vector-icons/feather";
import * as Haptics from "expo-haptics";

import { makeStyles, useTheme, fonts } from "@/src/theme";
import { usesNativeTabs } from "@/src/navigation";
import { uploadImage, createTryOn, checkTryOnPhoto, listTryOns, listPrivatePhotos, deleteTryOn, addShoppingBagItem, saveCatalogueOutfit, fileUrl, type TryOn } from "@/src/api";
import { PhotoSourceSheet } from "@/src/components/PhotoSourceSheet";
import { ShareLookModal } from "@/src/components/ShareLookModal";
import type { PickResult } from "@/src/utils/media";

export default function TryOnScreen() {
  const styles = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const queryClient = useQueryClient();
  const router = useRouter();
  const params = useLocalSearchParams<{
    garmentPath?: string;
    garmentName?: string;
    garmentProductId?: string;
    garmentSizes?: string;
    garmentColours?: string;
    secondGarmentPath?: string;
    secondGarmentName?: string;
    secondGarmentProductId?: string;
    secondGarmentSizes?: string;
    secondGarmentColours?: string;
    demoOutfitId?: string;
    demoOutfitPrompt?: string;
  }>();

  const [showPrivatePhotoPicker, setShowPrivatePhotoPicker] = useState(false);
  const {data: privatePhotos, isLoading: privatePhotosLoading, isError: privatePhotosError, refetch: refreshPrivatePhotos} = useQuery({queryKey:["private-photos"],queryFn:listPrivatePhotos,enabled:!!params.demoOutfitId,staleTime:30000});
  const [personPath, setPersonPath] = useState<string | null>(null);
  const [personPreview, setPersonPreview] = useState<string | null>(null);
  const [garmentPath, setGarmentPath] = useState<string | null>(null);
  const [garmentPreview, setGarmentPreview] = useState<string | null>(null);
  const [garmentPrompt, setGarmentPrompt] = useState("");
  const [secondGarmentPath, setSecondGarmentPath] = useState<string | null>(null);
  const [secondGarmentPreview, setSecondGarmentPreview] = useState<string | null>(null);
  const [target, setTarget] = useState<"person" | "garment" | "secondGarment" | null>(null);
  const [uploadingTarget, setUploadingTarget] = useState<"person" | "garment" | "secondGarment" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [checking, setChecking] = useState(false);
  const [warning, setWarning] = useState<string | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [result, setResult] = useState<TryOn | null>(null);
  const [shareUrl, setShareUrl] = useState<string | null>(null);
  const [viewedTryOn, setViewedTryOn] = useState<TryOn | null>(null);
  const [zoom, setZoom] = useState(1);
  const pinchDistance = useRef<number | null>(null);
  const pinchStartZoom = useRef(1);
  const [saving, setSaving] = useState(false);
  const [selectedSize, setSelectedSize] = useState("");
  const [selectedColour, setSelectedColour] = useState("");
  const [secondSelectedSize, setSecondSelectedSize] = useState("");
  const [secondSelectedColour, setSecondSelectedColour] = useState("");
  const [bagSaving, setBagSaving] = useState(false);
  const [bagStatus, setBagStatus] = useState("");
  const [outfitSaveBusy, setOutfitSaveBusy] = useState(false);
  const [outfitSaveMessage, setOutfitSaveMessage] = useState("");
  const parseOptions = (encoded?: string) => {
    try {
      const parsed: unknown = JSON.parse(encoded || "[]");
      return Array.isArray(parsed) ? parsed.filter((x): x is string => typeof x === "string").slice(0, 40) : [];
    } catch { return []; }
  };
  const garmentSizes = parseOptions(params.garmentSizes);
  const garmentColours = parseOptions(params.garmentColours);
  const secondSizes = parseOptions(params.secondGarmentSizes);
  const secondColours = parseOptions(params.secondGarmentColours);
  async function saveCurrentOutfit() {
    const ids = [params.garmentProductId, secondGarmentPath ? params.secondGarmentProductId : null]
      .filter((x): x is string => Boolean(x));
    if (!result || !ids.length) return;
    setOutfitSaveBusy(true);
    setOutfitSaveMessage("");
    try {
      await saveCatalogueOutfit(ids);
      setOutfitSaveMessage("Outfit saved to your private collection.");
      await queryClient.invalidateQueries({ queryKey: ["saved-catalogue-outfits"] });
    } catch (e) {
      setOutfitSaveMessage(e instanceof Error ? e.message : "Unable to save outfit.");
    } finally { setOutfitSaveBusy(false); }
  }

  async function saveTryOnToBag(which: "first" | "second" = "first") {
    if (!result) return;
    const productId = which === "first" ? params.garmentProductId : params.secondGarmentProductId;
    const sizes = which === "first" ? garmentSizes : secondSizes;
    const colours = which === "first" ? garmentColours : secondColours;
    const size = which === "first" ? selectedSize : secondSelectedSize;
    const colour = which === "first" ? selectedColour : secondSelectedColour;
    if (!productId) return;
    if (sizes.length && !size) { setBagStatus("Choose a size above to add this garment."); return; }
    if (colours.length && !colour) { setBagStatus("Choose a colour above to add this garment."); return; }
    setBagSaving(true); setBagStatus("Adding garment to your bag…");
    try {
      await addShoppingBagItem({
        product_id: productId,
        size, colour, quantity: 1,
      });
      await queryClient.invalidateQueries({ queryKey: ["shopping-bag"] });
      setBagStatus("Garment added to your shopping bag. Checkout is not enabled yet.");
    } catch (e) {
      setBagStatus(e instanceof Error ? e.message : "Unable to add this garment.");
    } finally { setBagSaving(false); }
  }


  useEffect(() => {
    if (!params.demoOutfitId || !params.demoOutfitPrompt) return;
    // Do not automatically call any paid image endpoint.
    const description = params.demoOutfitPrompt.slice(0, 700);
    setGarmentPath(null);
    setSecondGarmentPath(null);
    setGarmentPrompt(`[LUMIERE-DEMO:${params.demoOutfitId}] An illustrative, fully clothed outfit containing exactly: ${description}. Keep the person's face, body and background as consistent as possible. This is a demo styling simulation, not real supplier inventory.`);
    setResult(null);
  }, [params.demoOutfitId,params.demoOutfitPrompt]);

  useEffect(() => {
    if (params.garmentPath) {
      setGarmentPath(params.garmentPath);
      // Preview the LUMIÈRE-hosted copy via /api/files, never the supplier URL.
      setGarmentPreview(params.garmentPath);
      setGarmentPrompt("");
      setSelectedSize("");
      setSelectedColour("");
      setSecondSelectedSize("");
      setSecondSelectedColour("");
      setBagStatus("");
      setResult(null);
      setError(null);
    }
  }, [params.garmentPath]);

  useEffect(() => {
    setSecondGarmentPath(params.secondGarmentPath || null);
    setSecondGarmentPreview(params.secondGarmentPath || null);
  }, [params.secondGarmentPath]);


  function replaceOutfitGarment(which: "first" | "second") {
    const keepSecond = which === "first";
    const remainingPath = keepSecond ? secondGarmentPath : garmentPath;
    const remainingId = keepSecond ? params.secondGarmentProductId : params.garmentProductId;
    if (!remainingPath || !remainingId) return;
    // Discover's verified two-garment selection keeps the remaining piece.
    // When replacing first, its former second item is promoted to the primary slot.
    router.push({ pathname: "/(tabs)/discover", params: {
      outfitFirstPath: remainingPath,
      outfitFirstName: (keepSecond ? params.secondGarmentName : params.garmentName) || "",
      outfitFirstId: remainingId,
      outfitFirstSizes: (keepSecond ? params.secondGarmentSizes : params.garmentSizes) || "[]",
      outfitFirstColours: (keepSecond ? params.secondGarmentColours : params.garmentColours) || "[]",
    } });
  }

  function removeFirstGarment() {
    if (secondGarmentPath) {
      // Promote the remaining item to the primary Try-On slot.
      // Keep its original catalogue identity and variants for Add to Bag.
      router.setParams({
        garmentPath: secondGarmentPath,
        garmentName: params.secondGarmentName || "",
        garmentProductId: params.secondGarmentProductId || "",
        garmentSizes: params.secondGarmentSizes || "[]",
        garmentColours: params.secondGarmentColours || "[]",
        secondGarmentPath: "",
        secondGarmentName: "",
        secondGarmentProductId: "",
        secondGarmentSizes: "[]",
        secondGarmentColours: "[]",
      });
      setSecondGarmentPath(null);
      setSecondGarmentPreview(null);
    } else {
      setGarmentPath(null);
      setGarmentPreview(null);
      router.setParams({ garmentPath: "", garmentName: "", garmentProductId: "", garmentSizes: "[]", garmentColours: "[]" });
    }
    setResult(null);
    setConfirmed(false);
    setWarning(null);
    setBagStatus("");
  }

  const bottomPad = (usesNativeTabs ? insets.bottom : 0) + 32;

  const { data: gallery } = useQuery({ queryKey: ["tryons"], queryFn: listTryOns });

  const del = useMutation({
    mutationFn: deleteTryOn,
    onSuccess: () => { setViewedTryOn(null); queryClient.invalidateQueries({ queryKey: ["tryons"] }); },
    onError: (e: Error) => setError(e.message || "Verified image deletion failed. Try again."),
  });

  const gen = useMutation({
    mutationFn: createTryOn,
    onSuccess: (t) => {
      setResult(t);
      queryClient.invalidateQueries({ queryKey: ["tryons"] });
    },
    onError: (e: Error) => setError(e.message || "Try-on failed. Please try again."),
  });

  const saveViewedTryOn = async () => {
    if (!viewedTryOn || saving) return;
    if (Platform.OS !== "web") {
      setError("Saving private photos is currently supported in the browser. Open LUMIÈRE in Chrome to save.");
      return;
    }
    setSaving(true);
    try {
      // The authenticated, same-origin fetch never exposes the private image as a public URL.
      const response = await fetch(fileUrl(viewedTryOn.result_path), { credentials: "same-origin" });
      if (!response.ok) throw new Error("Could not retrieve the image. Please sign in again.");
      const blob = await response.blob();
      if (!blob.type.startsWith("image/")) throw new Error("The saved file is not an image.");
      const objectUrl = URL.createObjectURL(blob);
      try {
        const link = document.createElement("a");
        link.href = objectUrl;
        link.download = `lumiere-tryon-${viewedTryOn.id}.png`;
        document.body.appendChild(link);
        link.click();
        link.remove();
      } finally {
        window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1500);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to save this Try-On image.");
    } finally {
      setSaving(false);
    }
  };

  const onPicked = async (asset: PickResult) => {
    const which = target;
    setTarget(null);
    if (!which) return;
    if (which === "person") setPersonPreview(asset.uri);
    else if (which === "secondGarment") setSecondGarmentPreview(asset.uri);
    else setGarmentPreview(asset.uri);
    // Never reuse a previous uploaded path when the replacement upload fails.
    if (which === "person") setPersonPath(null);
    else if (which === "secondGarment") setSecondGarmentPath(null);
    else setGarmentPath(null);
    setWarning(null);
    setConfirmed(false);
    setUploadingTarget(which);
    setError(null);
    try {
      const path = await uploadImage(asset.uri, asset.name, asset.type, which === "person" ? "person" : "garment");
      if (which === "person") { setPersonPath(path); refreshPrivatePhotos(); }
      else if (which === "secondGarment") setSecondGarmentPath(path);
      else setGarmentPath(path);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Image upload failed. Please try again.");
      if (which === "person") setPersonPreview(null);
      else if (which === "secondGarment") setSecondGarmentPreview(null);
      else setGarmentPreview(null);
    } finally {
      setUploadingTarget(null);
    }
  };

  const canGenerate =
    !!personPath && (!!garmentPath || garmentPrompt.trim().length > 0) && !uploadingTarget && !gen.isPending && !checking;

  const handleGenerate = async () => {
    if (!canGenerate) return;
    if (Platform.OS !== "web") Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    setError(null);
    setResult(null);
    const request = {
      person_image_path: personPath!,
      garment_image_path: garmentPath,
      second_garment_image_path: garmentPath ? secondGarmentPath : null,
      garment_prompt: garmentPrompt.trim() || null,
    };
    if (!confirmed) {
      setChecking(true);
      try {
        const quality = await checkTryOnPhoto({ ...request, garment_prompt: request.garment_prompt || params.garmentName || params.secondGarmentName || null });
        if (quality.warnings.length) {
          setWarning(quality.warnings.join(" ") + " Check the photo guidance below before continuing.");
          setConfirmed(true);
          return; // No paid Gemini call until customer confirms.
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : "Photo pre-check unavailable. Please try again.");
        return; // Fail closed: no paid request without a successful check.
      } finally {
        setChecking(false);
      }
    }
    setWarning(null);
    setConfirmed(false);
    gen.mutate(request);
  };

  const Slot = ({
    which,
    preview,
    label,
    icon,
  }: {
    which: "person" | "garment" | "secondGarment";
    preview: string | null;
    label: string;
    icon: "user" | "shopping-bag";
  }) => (
    <Pressable
      testID={`tryon-slot-${which}`}
      style={styles.slot}
      onPress={() => setTarget(which)}
    >
      {preview ? (
        <>
          <AccountPhoto path={preview} style={styles.slotImg} contentFit="cover" />
          {uploadingTarget === which && (
            <View style={styles.slotOverlay}>
              <ActivityIndicator color={colors.onBrandPrimary} />
            </View>
          )}
        </>
      ) : (
        <View style={styles.slotEmpty}>
          <Feather name={icon} size={26} color={colors.muted} />
          <Text style={styles.slotLabel}>{label}</Text>
        </View>
      )}
    </Pressable>
  );

  return (
    <View style={styles.root}>
      <View style={[styles.header, { paddingTop: insets.top + 8 }]}>
        <Text style={styles.title}>Virtual Try-On</Text>
        <Text style={styles.subtitle}>Try one garment or a complete outfit · AI preview, not a fit guarantee</Text>
      </View>

      <KeyboardAwareScrollView
        style={styles.flex}
        contentContainerStyle={{ padding: 20, paddingBottom: bottomPad }}
        showsVerticalScrollIndicator={false}
        bottomOffset={20}
      >
        <View style={styles.guidanceWrap} testID="tryon-photo-guidance">
          <Text style={styles.secondTitle}>Choose a photo that works well</Text>
          <Text style={styles.secondHint}>For tops, include your upper body. For trousers, skirts and dresses, use a full-body standing photograph.</Text>
          <Text style={styles.secondHint}>Use good lighting, a simple background and ordinary fully covering clothing. Keep arms, legs and the garment unobstructed.</Text>
          <Text style={styles.secondHint}>A free check looks for low resolution, poor lighting and unusual framing. It cannot assess pose or guarantee Gemini will generate an image.</Text>
        </View>
        <View style={styles.slotRow}>
          <Slot which="person" preview={personPreview} label="Your photo" icon="user" />
          {!params.demoOutfitId ? <Slot which="garment" preview={garmentPreview} label="Garment" icon="shopping-bag" /> : null}
        </View>
        {params.demoOutfitId ? <View style={{gap:8,marginVertical:10}}>
          <Text style={styles.secondHint}>Demo outfit from Discover · AI simulation only, not actual purchasable products.</Text>
          <Pressable testID="choose-existing-photo" accessibilityRole="button" onPress={() => { if (!showPrivatePhotoPicker) void refreshPrivatePhotos(); setShowPrivatePhotoPicker(v=>!v); }} style={styles.shareBtn}>
            <Text style={styles.shareBtnText}>{showPrivatePhotoPicker?"Close saved photos":"Choose existing private photo"}</Text>
          </Pressable>
          {showPrivatePhotoPicker ? <View style={{flexDirection:"row",flexWrap:"wrap",gap:10}}>
            {(privatePhotos||[]).map((photo,index)=><Pressable key={photo.id} testID={`photo-choice-${photo.id}`} accessibilityRole="button"
              accessibilityLabel={`Select saved photo ${index+1}`}
              accessibilityState={{selected:personPath===`private:${photo.id}`}}
              onPress={() => {setPersonPath(`private:${photo.id}`);setPersonPreview(`private:${photo.id}`);setConfirmed(false);setWarning(null);setShowPrivatePhotoPicker(false);setResult(null);}}>
              <View style={{borderWidth:personPath===`private:${photo.id}`?3:1,borderColor:personPath===`private:${photo.id}`?colors.brandPrimary:"#999",borderRadius:9,padding:2}}>
                <AccountPhoto path={`private:${photo.id}`} style={{width:95,height:130,borderRadius:7}} contentFit="cover" />
              </View>
            </Pressable>)}
            {privatePhotosLoading ? <ActivityIndicator accessibilityLabel="Loading private photos" /> : null}
            {privatePhotosError ? <Text style={styles.secondHint}>Unable to load private photos. Close and reopen to retry, or upload a new photo.</Text> : null}
            {!privatePhotosLoading && !privatePhotosError && !privatePhotos?.length ? <Text style={styles.secondHint}>No saved photos. Tap Your photo above to upload one.</Text> : null}
          </View> : null}
          {personPath ? (
            <View accessibilityRole="text" testID="demo-photo-selected" style={{paddingVertical:6}}>
              <Text style={styles.secondHint}>✓ Private photo selected. You can change it above before the free photo check.</Text>
            </View>
          ) : (
            <Text style={styles.secondHint}>No person photo selected yet. Choose a saved photo or tap Your photo above to upload one.</Text>
          )}
          <Text style={styles.secondHint}>Use a well-lit, full-body standing photo. Generation starts only after you request the free photo check.</Text>
        </View> : null}
        {garmentPath ? (
          <Pressable testID="remove-first-garment" accessibilityRole="button" onPress={removeFirstGarment}>
            <Text style={styles.secondHint}>Remove first garment{secondGarmentPath ? " (keep second garment)" : ""}</Text>
          </Pressable>
        ) : null}

        {garmentPath && secondGarmentPath && params.garmentProductId && params.secondGarmentProductId ? (
          <View style={{ gap: 8, marginVertical: 12 }}>
            <Text style={styles.secondHint}>Change one garment without losing the other</Text>
            <Pressable testID="replace-first-garment" accessibilityRole="button" onPress={() => replaceOutfitGarment("first")}>
              <Text style={styles.secondHint}>Replace first garment in Discover</Text>
            </Pressable>
            <Pressable testID="replace-second-garment" accessibilityRole="button" onPress={() => replaceOutfitGarment("second")}>
              <Text style={styles.secondHint}>Replace second garment in Discover</Text>
            </Pressable>
          </View>
        ) : null}

        {garmentPath && params.garmentProductId && !secondGarmentPath ? (
          <Pressable testID="tryon-select-second-from-discover" accessibilityRole="button"
            onPress={() => router.push({ pathname: "/(tabs)/discover", params: {
              outfitFirstPath: garmentPath,
              outfitFirstName: params.garmentName || "First garment",
              outfitFirstId: params.garmentProductId,
              outfitFirstSizes: params.garmentSizes || "[]",
              outfitFirstColours: params.garmentColours || "[]",
            } })} style={styles.shareBtn}>
            <Text style={styles.shareBtnText}>Choose a second garment from Discover</Text>
          </Pressable>
        ) : null}
        {garmentPath && (
          <View style={styles.secondRow}>
            <Text style={styles.secondTitle}>Build an outfit (optional)</Text>
            <View style={styles.secondControls}>
              <Pressable testID="tryon-slot-secondGarment" style={styles.secondSlot} onPress={() => setTarget("secondGarment")}>
                {secondGarmentPreview ? <AccountPhoto path={secondGarmentPreview} style={styles.slotImg} contentFit="cover" /> : <Text style={styles.slotLabel}>+ Upload second garment photo</Text>}
              </Pressable>
              {secondGarmentPath && <Pressable testID="remove-second-garment" onPress={() => { setSecondGarmentPath(null); setSecondGarmentPreview(null); }}><Text style={styles.slotLabel}>Remove</Text></Pressable>}
            </View>
            <Text style={styles.secondHint}>{params.secondGarmentName && secondGarmentPath ? `Selected from Discover · ${params.secondGarmentName}` : "Use the Discover button above to select a purchasable second garment, or upload your own garment photo here."}</Text>
          </View>
        )}

        {params.garmentName && garmentPath ? <Text style={styles.catalogueItem}>Selected from Discover · {params.garmentName}</Text> : null}
        {params.demoOutfitId ? (
          <View style={{marginVertical:10, gap:4}}>
            <Text style={styles.secondTitle}>Outfit to visualise</Text>
            <Text style={styles.secondHint}>{params.demoOutfitPrompt}</Text>
            <Text style={styles.secondHint}>To change garments, return to Discover and choose a different outfit.</Text>
          </View>
        ) : (
          <>
            <Text style={styles.orText}>or describe the item</Text>
            <TextInput
              testID="garment-prompt-input"
              style={styles.input}
              placeholder="e.g. a beige oversized trench coat"
              placeholderTextColor={colors.muted}
              value={garmentPrompt}
              onChangeText={(value) => { setGarmentPrompt(value); setConfirmed(false); setWarning(null); }}
            />
          </>
        )}

        {warning && (
          <Text style={styles.preflightWarning} testID="tryon-preflight-warning">{warning}</Text>
        )}
        <Pressable
          testID="generate-tryon-button"
          style={[styles.genBtn, !canGenerate && styles.genBtnDisabled]}
          onPress={handleGenerate}
          disabled={!canGenerate}
        >
          {gen.isPending || checking ? (
            <>
              <ActivityIndicator color={colors.onBrandPrimary} size="small" />
              <Text style={styles.genBtnText}>{checking ? "Checking photo…" : "Rendering your look…"}</Text>
            </>
          ) : (
            <>
              <Feather name="zap" size={18} color={colors.onBrandPrimary} />
              <Text style={styles.genBtnText}>{confirmed ? "Continue with this photo" : "Check photo & try on"}</Text>
            </>
          )}
        </Pressable>

        {error && (
          <Text style={styles.error} testID="tryon-error">
            {error}
          </Text>
        )}

        {result && (
          <View style={styles.resultWrap} testID="tryon-result">
            <Text style={styles.resultLabel}>AI-generated preview · Fit, drape and colour may differ in reality</Text>
            <AccountPhoto path={result.result_path} style={styles.resultImg} contentFit="cover" />
            {params.garmentProductId ? (
              <Pressable testID="tryon-save-outfit" accessibilityRole="button" disabled={outfitSaveBusy}
                style={[styles.shareBtn, { marginTop: 14 }]} onPress={saveCurrentOutfit}>
                <Text style={styles.shareBtnText}>{outfitSaveBusy ? "Saving outfit…" : "Save this outfit"}</Text>
              </Pressable>
            ) : null}
            {outfitSaveMessage ? <Text accessibilityRole="alert" style={{ color: colors.onSurface }}>{outfitSaveMessage}</Text> : null}
            {params.garmentProductId ? (
              <View style={{ marginTop: 16, gap: 10 }}>
                <Text style={{ color: colors.onSurface, fontWeight: "600" }}>
                  Like this look? Save the garment to your bag.
                </Text>
                {garmentSizes.length > 0 && (
                  <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
                    {garmentSizes.map(size => (
                      <Pressable key={size} onPress={() => setSelectedSize(size)}
                        style={{ borderWidth: selectedSize === size ? 2 : 1, borderColor: colors.borderStrong, padding: 10 }}>
                        <Text style={{ color: colors.onSurface }}>{size}</Text>
                      </Pressable>
                    ))}
                  </View>
                )}
                {garmentColours.length > 0 && (
                  <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
                    {garmentColours.map(colour => (
                      <Pressable key={colour} onPress={() => setSelectedColour(colour)}
                        style={{ borderWidth: selectedColour === colour ? 2 : 1, borderColor: colors.borderStrong, padding: 10 }}>
                        <Text style={{ color: colors.onSurface }}>{colour}</Text>
                      </Pressable>
                    ))}
                  </View>
                )}
                <Pressable testID="tryon-add-to-bag" accessibilityRole="button"
                  disabled={bagSaving}
                  style={styles.shareBtn} onPress={() => saveTryOnToBag("first")}>
                  <Feather name="shopping-bag" size={16} color={colors.onSurface} />
                  <Text style={styles.shareBtnText}>{bagSaving ? "Adding…" : "Add garment to bag"}</Text>
                </Pressable>
                {bagStatus ? <Text style={{ color: colors.onSurface }}>{bagStatus}</Text> : null}
                <Pressable onPress={() => router.push("/bag" as any)}>
                  <Text style={{ color: colors.onSurface, textDecorationLine: "underline" }}>View shopping bag</Text>
                </Pressable>
                {params.secondGarmentProductId && secondGarmentPath ? (
                  <View style={{ gap: 10, marginTop: 12 }}>
                    <Text style={{ color: colors.onSurface, fontWeight: "600" }}>Second garment · {params.secondGarmentName}</Text>
                    {secondSizes.length > 0 ? <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
                      {secondSizes.map(size => <Pressable key={size} onPress={() => setSecondSelectedSize(size)}
                        style={{ borderWidth: secondSelectedSize === size ? 2 : 1, borderColor: colors.borderStrong, padding: 10 }}>
                        <Text style={{ color: colors.onSurface }}>{size}</Text>
                      </Pressable>)}
                    </View> : null}
                    {secondColours.length > 0 ? <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
                      {secondColours.map(colour => <Pressable key={colour} onPress={() => setSecondSelectedColour(colour)}
                        style={{ borderWidth: secondSelectedColour === colour ? 2 : 1, borderColor: colors.borderStrong, padding: 10 }}>
                        <Text style={{ color: colors.onSurface }}>{colour}</Text>
                      </Pressable>)}
                    </View> : null}
                    <Pressable testID="tryon-add-second-to-bag" accessibilityRole="button"
                      disabled={bagSaving} style={styles.shareBtn} onPress={() => saveTryOnToBag("second")}>
                      <Feather name="shopping-bag" size={16} color={colors.onSurface}/>
                      <Text style={styles.shareBtnText}>Add second garment to bag</Text>
                    </Pressable>
                  </View>
                ) : null}
              </View>
            ) : (
              <Text style={{ color: colors.muted, marginTop: 12 }}>To purchase this look, select a catalogue garment from Discover. Uploaded garments are not linked to saleable products.</Text>
            )}

            {!result.result_path.startsWith("private:") && <Pressable
              testID="share-result-button"
              style={styles.shareBtn}
              onPress={() => setShareUrl(fileUrl(result.result_path))}
            >
              <Feather name="share" size={16} color={colors.onSurface} />
              <Text style={styles.shareBtnText}>Share this look</Text>
            </Pressable>}
          </View>
        )}

        {(gallery?.length ?? 0) > 0 && (
          <View style={styles.gallery}>
            <Text style={styles.galleryTitle}>Past try-ons</Text>
            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.galleryRow}>
              {gallery!.map((t) => (
                <View key={t.id} style={styles.galleryItem} testID={`tryon-history-${t.id}`}>
                  <Pressable testID={`tryon-open-${t.id}`} accessibilityRole="button" accessibilityLabel="Open past try-on" style={styles.galleryImg} onPress={() => { setZoom(1); setViewedTryOn(t); }}>
                    <AccountPhoto path={t.result_path} style={styles.galleryImg} contentFit="cover" />
                  </Pressable>
                  <Pressable
                    testID={`tryon-delete-${t.id}`}
                    style={styles.galleryDelete}
                    onPress={() => del.mutate(t.id)}
                    hitSlop={8}
                  >
                    <Feather name="x" size={12} color={colors.onBrandPrimary} />
                  </Pressable>
                </View>
              ))}
            </ScrollView>
          </View>
        )}
      </KeyboardAwareScrollView>

      <Modal visible={viewedTryOn !== null} transparent animationType="fade" onRequestClose={() => setViewedTryOn(null)}>
        <View style={styles.viewerBackdrop}>
          <View style={styles.viewerHeader}>
            <Text style={styles.viewerHeading}>Past Try-On</Text>
            <Pressable testID="tryon-viewer-close" accessibilityRole="button" accessibilityLabel="Close image" onPress={() => setViewedTryOn(null)} style={styles.viewerClose}>
              <Feather name="x" size={25} color="#FFFFFF" />
            </Pressable>
          </View>
          {viewedTryOn && (
            <View style={styles.viewerImage}
              onTouchStart={(event) => {
                const touches = event.nativeEvent.touches;
                if (touches.length === 2) {
                  pinchDistance.current = Math.hypot(
                    touches[0].pageX - touches[1].pageX,
                    touches[0].pageY - touches[1].pageY,
                  );
                  pinchStartZoom.current = zoom;
                }
              }}
              onTouchMove={(event) => {
                const touches = event.nativeEvent.touches;
                if (touches.length === 2 && pinchDistance.current && pinchDistance.current > 0) {
                  const distance = Math.hypot(
                    touches[0].pageX - touches[1].pageX,
                    touches[0].pageY - touches[1].pageY,
                  );
                  setZoom(Math.max(1, Math.min(4, pinchStartZoom.current * distance / pinchDistance.current)));
                }
              }}
              onTouchEnd={() => { pinchDistance.current = null; }}>
              <AccountPhoto path={viewedTryOn.result_path} style={[styles.viewerImage, { transform: [{ scale: zoom }] }]} contentFit="contain" />
            </View>
          )}
          <View style={styles.viewerActions}>
            <Pressable testID="tryon-zoom-out" accessibilityLabel="Zoom out" style={styles.viewerAction} onPress={() => setZoom(value => Math.max(1, value - 0.5))}>
              <Text style={styles.viewerActionText}>−</Text>
            </Pressable>
            <Text style={styles.viewerZoomText}>{Math.round(zoom * 100)}%</Text>
            <Pressable testID="tryon-zoom-in" accessibilityLabel="Zoom in" style={styles.viewerAction} onPress={() => setZoom(value => Math.min(4, value + 0.5))}>
              <Text style={styles.viewerActionText}>+</Text>
            </Pressable>
            <Pressable testID="tryon-save-photo" accessibilityLabel="Save image to phone" style={styles.viewerSave} disabled={saving} onPress={saveViewedTryOn}>
              <Text style={styles.viewerSaveText}>{saving ? "Saving…" : "Save image"}</Text>
            </Pressable>
          </View>
          <Text style={styles.viewerCaption}>AI-generated preview · Clothing and fit may differ in reality.</Text>
        </View>
      </Modal>
      <PhotoSourceSheet
        visible={target !== null}
        onClose={() => setTarget(null)}
        onPicked={onPicked}
        title={target === "person" ? "Add your photo" : target === "secondGarment" ? "Add another garment" : "Add the garment"}
      />
      <ShareLookModal visible={!!shareUrl} text="" imageUrl={shareUrl} onClose={() => setShareUrl(null)} />
    </View>
  );
}

const useStyles = makeStyles((c) => ({
  root: { flex: 1, backgroundColor: c.surface },
  flex: { flex: 1 },
  header: { paddingHorizontal: 20, paddingBottom: 12, borderBottomWidth: 1, borderBottomColor: c.border },
  title: { fontFamily: fonts.display, fontSize: 30, fontWeight: "700", color: c.onSurface },
  subtitle: { fontFamily: fonts.text, fontSize: 13, color: c.muted, marginTop: 4 },
  slotRow: { flexDirection: "row", gap: 14 },
  slot: {
    flex: 1,
    aspectRatio: 0.8,
    borderRadius: 4,
    borderWidth: 1,
    borderColor: c.border,
    backgroundColor: c.surfaceTertiary,
    overflow: "hidden",
  },
  slotImg: { width: "100%", height: "100%" },
  slotOverlay: {
    ...({ position: "absolute" } as const),
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "rgba(0,0,0,0.4)",
  },
  slotEmpty: { flex: 1, alignItems: "center", justifyContent: "center", gap: 8 },
  slotLabel: { fontFamily: fonts.text, fontSize: 13, color: c.muted },
  catalogueItem: { fontFamily: fonts.text, fontSize: 12, lineHeight: 18, color: c.muted, textAlign: "center", marginTop: 12 },
  secondRow: { marginTop: 18, gap: 10 },
  guidanceWrap: { gap: 8, marginBottom: 18, padding: 14, borderWidth: 1, borderColor: c.border, borderRadius: 4 },
  preflightWarning: { fontFamily: fonts.text, fontSize: 13, color: c.onSurface, marginTop: 16, lineHeight: 20 },
  secondTitle: { fontFamily: fonts.text, fontSize: 15, color: c.onSurface },
  secondControls: { flexDirection: "row", alignItems: "center", gap: 16 },
  secondSlot: { width: 140, height: 125, borderWidth: 1, borderColor: c.border, backgroundColor: c.surfaceTertiary, alignItems: "center", justifyContent: "center", overflow: "hidden" },
  secondHint: { fontFamily: fonts.text, fontSize: 12, color: c.muted },
  orText: {
    fontFamily: fonts.text,
    fontSize: 12,
    letterSpacing: 1,
    color: c.muted,
    textTransform: "uppercase",
    textAlign: "center",
    marginTop: 20,
    marginBottom: 12,
  },
  input: {
    borderWidth: 1,
    borderColor: c.border,
    backgroundColor: c.surfaceTertiary,
    borderRadius: 4,
    paddingHorizontal: 14,
    paddingVertical: 14,
    fontFamily: fonts.text,
    fontSize: 15,
    color: c.onSurface,
  },
  genBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 10,
    height: 54,
    backgroundColor: c.brandPrimary,
    borderRadius: 4,
    marginTop: 20,
  },
  genBtnDisabled: { opacity: 0.35 },
  genBtnText: { fontFamily: fonts.text, fontSize: 16, color: c.onBrandPrimary },
  error: { fontFamily: fonts.text, fontSize: 14, color: c.error, marginTop: 14, textAlign: "center" },
  resultWrap: { marginTop: 28 },
  resultLabel: {
    fontFamily: fonts.text,
    fontSize: 12,
    letterSpacing: 1,
    color: c.muted,
    textTransform: "uppercase",
    marginBottom: 12,
  },
  resultImg: { width: "100%", aspectRatio: 0.8, borderRadius: 4, backgroundColor: c.surfaceTertiary },
  shareBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    height: 48,
    borderWidth: 1,
    borderColor: c.borderStrong,
    borderRadius: 4,
    marginTop: 12,
  },
  shareBtnText: { fontFamily: fonts.text, fontSize: 15, color: c.onSurface },
  gallery: { marginTop: 32 },
  galleryTitle: { fontFamily: fonts.display, fontSize: 20, fontWeight: "700", color: c.onSurface, marginBottom: 14 },
  galleryRow: { gap: 12, paddingRight: 8 },
  galleryItem: { width: 110, height: 140 },
  galleryImg: { width: 110, height: 140, borderRadius: 4, backgroundColor: c.surfaceTertiary },
  viewerBackdrop: { flex: 1, backgroundColor: "rgba(0,0,0,0.95)", paddingTop: 56, paddingBottom: 35, paddingHorizontal: 16 },
  viewerHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 16 },
  viewerHeading: { fontFamily: fonts.display, color: "#FFFFFF", fontSize: 20 },
  viewerClose: { padding: 9 },
  viewerImage: { flex: 1, width: "100%" },
  viewerActions: { flexDirection: "row", justifyContent: "center", alignItems: "center", gap: 12, marginTop: 12 },
  viewerAction: { borderWidth: 1, borderColor: "#FFFFFF", minWidth: 45, paddingVertical: 7, alignItems: "center", borderRadius: 4 },
  viewerActionText: { color: "#FFFFFF", fontSize: 20 },
  viewerZoomText: { color: "#FFFFFF", fontSize: 13 },
  viewerSave: { borderWidth: 1, borderColor: "#FFFFFF", paddingHorizontal: 16, paddingVertical: 11, borderRadius: 4 },
  viewerSaveText: { color: "#FFFFFF", fontSize: 13 },
  viewerCaption: { fontFamily: fonts.text, color: "#FFFFFF", opacity: 0.8, textAlign: "center", marginTop: 16 },
  galleryDelete: {
    position: "absolute",
    top: 6,
    right: 6,
    width: 22,
    height: 22,
    borderRadius: 11,
    backgroundColor: "rgba(0,0,0,0.6)",
    alignItems: "center",
    justifyContent: "center",
  },
}));
