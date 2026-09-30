import { useEffect, useState } from "react";
import { useLocalSearchParams } from "expo-router";
import {
  View,
  Text,
  ScrollView,
  Pressable,
  TextInput,
  Platform,
  ActivityIndicator,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { KeyboardAwareScrollView } from "react-native-keyboard-controller";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Image } from "expo-image";
import Feather from "@react-native-vector-icons/feather";
import * as Haptics from "expo-haptics";

import { makeStyles, useTheme, fonts } from "@/src/theme";
import { usesNativeTabs } from "@/src/navigation";
import { uploadImage, createTryOn, listTryOns, deleteTryOn, fileUrl, type TryOn } from "@/src/api";
import { PhotoSourceSheet } from "@/src/components/PhotoSourceSheet";
import { ShareLookModal } from "@/src/components/ShareLookModal";
import type { PickResult } from "@/src/utils/media";

export default function TryOnScreen() {
  const styles = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const queryClient = useQueryClient();
  const params = useLocalSearchParams<{
    garmentPath?: string;
    garmentPreview?: string;
    garmentName?: string;
  }>();

  const [personPath, setPersonPath] = useState<string | null>(null);
  const [personPreview, setPersonPreview] = useState<string | null>(null);
  const [garmentPath, setGarmentPath] = useState<string | null>(null);
  const [garmentPreview, setGarmentPreview] = useState<string | null>(null);
  const [garmentPrompt, setGarmentPrompt] = useState("");
  const [target, setTarget] = useState<"person" | "garment" | null>(null);
  const [uploadingTarget, setUploadingTarget] = useState<"person" | "garment" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<TryOn | null>(null);
  const [shareUrl, setShareUrl] = useState<string | null>(null);

  useEffect(() => {
    if (params.garmentPath) {
      setGarmentPath(params.garmentPath);
      setGarmentPreview(params.garmentPreview || null);
      setGarmentPrompt("");
      setResult(null);
      setError(null);
    }
  }, [params.garmentPath, params.garmentPreview]);


  const bottomPad = (usesNativeTabs ? insets.bottom : 0) + 32;

  const { data: gallery } = useQuery({ queryKey: ["tryons"], queryFn: listTryOns });

  const del = useMutation({
    mutationFn: deleteTryOn,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["tryons"] }),
  });

  const gen = useMutation({
    mutationFn: createTryOn,
    onSuccess: (t) => {
      setResult(t);
      queryClient.invalidateQueries({ queryKey: ["tryons"] });
    },
    onError: (e: Error) => setError(e.message || "Try-on failed. Please try again."),
  });

  const onPicked = async (asset: PickResult) => {
    const which = target;
    setTarget(null);
    if (!which) return;
    if (which === "person") setPersonPreview(asset.uri);
    else setGarmentPreview(asset.uri);
    setUploadingTarget(which);
    try {
      const path = await uploadImage(asset.uri, asset.name, asset.type);
      if (which === "person") setPersonPath(path);
      else setGarmentPath(path);
    } catch {
      if (which === "person") setPersonPreview(null);
      else setGarmentPreview(null);
    } finally {
      setUploadingTarget(null);
    }
  };

  const canGenerate =
    !!personPath && (!!garmentPath || garmentPrompt.trim().length > 0) && !gen.isPending;

  const handleGenerate = () => {
    if (!canGenerate) return;
    if (Platform.OS !== "web") Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    setError(null);
    setResult(null);
    gen.mutate({
      person_image_path: personPath!,
      garment_image_path: garmentPath,
      garment_prompt: garmentPrompt.trim() || null,
    });
  };

  const Slot = ({
    which,
    preview,
    label,
    icon,
  }: {
    which: "person" | "garment";
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
          <Image source={{ uri: preview }} style={styles.slotImg} contentFit="cover" />
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
        <Text style={styles.subtitle}>See a piece on you before you buy</Text>
      </View>

      <KeyboardAwareScrollView
        style={styles.flex}
        contentContainerStyle={{ padding: 20, paddingBottom: bottomPad }}
        showsVerticalScrollIndicator={false}
        bottomOffset={20}
      >
        <View style={styles.slotRow}>
          <Slot which="person" preview={personPreview} label="Your photo" icon="user" />
          <Slot which="garment" preview={garmentPreview} label="Garment" icon="shopping-bag" />
        </View>

        {params.garmentName && garmentPath ? <Text style={styles.catalogueItem}>Selected from Discover · {params.garmentName}</Text> : null}
        <Text style={styles.orText}>or describe the item</Text>
        <TextInput
          testID="garment-prompt-input"
          style={styles.input}
          placeholder="e.g. a beige oversized trench coat"
          placeholderTextColor={colors.muted}
          value={garmentPrompt}
          onChangeText={setGarmentPrompt}
        />

        <Pressable
          testID="generate-tryon-button"
          style={[styles.genBtn, !canGenerate && styles.genBtnDisabled]}
          onPress={handleGenerate}
          disabled={!canGenerate}
        >
          {gen.isPending ? (
            <>
              <ActivityIndicator color={colors.onBrandPrimary} size="small" />
              <Text style={styles.genBtnText}>Rendering your look…</Text>
            </>
          ) : (
            <>
              <Feather name="zap" size={18} color={colors.onBrandPrimary} />
              <Text style={styles.genBtnText}>Try it on</Text>
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
            <Text style={styles.resultLabel}>Your look</Text>
            <Image source={{ uri: fileUrl(result.result_path) }} style={styles.resultImg} contentFit="cover" />
            <Pressable
              testID="share-result-button"
              style={styles.shareBtn}
              onPress={() => setShareUrl(fileUrl(result.result_path))}
            >
              <Feather name="share" size={16} color={colors.onSurface} />
              <Text style={styles.shareBtnText}>Share this look</Text>
            </Pressable>
          </View>
        )}

        {(gallery?.length ?? 0) > 0 && (
          <View style={styles.gallery}>
            <Text style={styles.galleryTitle}>Past try-ons</Text>
            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.galleryRow}>
              {gallery!.map((t) => (
                <View key={t.id} style={styles.galleryItem} testID={`tryon-history-${t.id}`}>
                  <Image source={{ uri: fileUrl(t.result_path) }} style={styles.galleryImg} contentFit="cover" />
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

      <PhotoSourceSheet
        visible={target !== null}
        onClose={() => setTarget(null)}
        onPicked={onPicked}
        title={target === "person" ? "Add your photo" : "Add the garment"}
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
