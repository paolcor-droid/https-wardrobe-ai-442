import { useState } from "react";
import {
  View,
  TextInput,
  Pressable,
  Platform,
  Modal,
  Text,
  ActivityIndicator,
  Linking,
} from "react-native";
import { Image } from "expo-image";
import { BlurView } from "expo-blur";
import Feather from "@react-native-vector-icons/feather";
import * as Haptics from "expo-haptics";

import { makeStyles, useTheme, fonts } from "@/src/theme";
import { uploadImage } from "@/src/api";
import {
  ensureCameraPermission,
  ensureLibraryPermission,
  takePhoto,
  pickFromLibrary,
  type PickResult,
} from "@/src/utils/media";

type Props = {
  onSend: (text: string, imagePath?: string | null) => void;
  disabled?: boolean;
  bottomInset: number;
};

export function Composer({ onSend, disabled, bottomInset }: Props) {
  const styles = useStyles();
  const { colors, scheme } = useTheme();
  const [text, setText] = useState("");
  const [sheetOpen, setSheetOpen] = useState(false);
  const [blocked, setBlocked] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);
  const [imagePath, setImagePath] = useState<string | null>(null);

  const canSend = (text.trim().length > 0 || !!imagePath) && !disabled && !uploading;

  const handleSend = () => {
    if (!canSend) return;
    if (Platform.OS !== "web") Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    onSend(text.trim(), imagePath);
    setText("");
    setPreview(null);
    setImagePath(null);
  };

  const doUpload = async (asset: PickResult) => {
    setPreview(asset.uri);
    setUploading(true);
    try {
      const path = await uploadImage(asset.uri, asset.name, asset.type);
      setImagePath(path);
    } catch {
      setPreview(null);
      setImagePath(null);
    } finally {
      setUploading(false);
    }
  };

  const chooseCamera = async () => {
    setSheetOpen(false);
    const perm = await ensureCameraPermission();
    if (!perm.granted) {
      if (!perm.canAskAgain) setBlocked(true);
      return;
    }
    const asset = await takePhoto();
    if (asset) doUpload(asset);
  };

  const chooseLibrary = async () => {
    setSheetOpen(false);
    const perm = await ensureLibraryPermission();
    if (!perm.granted) {
      if (!perm.canAskAgain) setBlocked(true);
      return;
    }
    const asset = await pickFromLibrary();
    if (asset) doUpload(asset);
  };

  return (
    <BlurView
      intensity={Platform.OS === "ios" ? 40 : 0}
      tint={scheme === "dark" ? "dark" : "light"}
      style={[styles.wrap, { paddingBottom: bottomInset + 10 }]}
    >
      {preview && (
        <View style={styles.previewRow}>
          <Image source={{ uri: preview }} style={styles.previewImg} contentFit="cover" />
          {uploading ? (
            <View style={styles.previewOverlay}>
              <ActivityIndicator color={colors.onBrandPrimary} size="small" />
            </View>
          ) : (
            <Pressable
              testID="remove-photo-button"
              style={styles.removeBadge}
              onPress={() => {
                setPreview(null);
                setImagePath(null);
              }}
            >
              <Feather name="x" size={12} color={colors.onBrandPrimary} />
            </Pressable>
          )}
        </View>
      )}

      <View style={styles.inner}>
        <Pressable
          testID="attach-photo-button"
          style={styles.attachBtn}
          onPress={() => {
            if (Platform.OS !== "web") Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
            setSheetOpen(true);
          }}
        >
          <Feather name="camera" size={20} color={colors.onSurfaceTertiary} />
        </Pressable>
        <TextInput
          testID="composer-input"
          style={styles.input}
          placeholder="Ask your stylist anything…"
          placeholderTextColor={colors.muted}
          value={text}
          onChangeText={setText}
          multiline
          onSubmitEditing={handleSend}
          submitBehavior="submit"
        />
        <Pressable
          testID="composer-send-button"
          onPress={handleSend}
          disabled={!canSend}
          style={[styles.sendBtn, !canSend && styles.sendBtnDisabled]}
        >
          <Feather name="arrow-up" size={20} color={colors.onBrandPrimary} />
        </Pressable>
      </View>

      {/* Photo source picker */}
      <Modal visible={sheetOpen} transparent animationType="fade" onRequestClose={() => setSheetOpen(false)}>
        <Pressable style={styles.backdrop} onPress={() => setSheetOpen(false)}>
          <View style={styles.sheet}>
            <Text style={styles.sheetTitle}>Add a photo</Text>
            <Pressable testID="source-camera" style={styles.sheetBtn} onPress={chooseCamera}>
              <Feather name="camera" size={20} color={colors.onSurface} />
              <Text style={styles.sheetBtnText}>Take a photo</Text>
            </Pressable>
            <Pressable testID="source-library" style={styles.sheetBtn} onPress={chooseLibrary}>
              <Feather name="image" size={20} color={colors.onSurface} />
              <Text style={styles.sheetBtnText}>Choose from library</Text>
            </Pressable>
            <Pressable style={styles.sheetCancel} onPress={() => setSheetOpen(false)}>
              <Text style={styles.sheetCancelText}>Cancel</Text>
            </Pressable>
          </View>
        </Pressable>
      </Modal>

      {/* Permission blocked */}
      <Modal visible={blocked} transparent animationType="fade" onRequestClose={() => setBlocked(false)}>
        <Pressable style={styles.backdrop} onPress={() => setBlocked(false)}>
          <View style={styles.sheet}>
            <Text style={styles.sheetTitle}>Permission needed</Text>
            <Text style={styles.blockedText}>
              Enable camera and photo access in Settings to share a clothing photo.
            </Text>
            <Pressable
              testID="open-settings-button"
              style={styles.sheetBtn}
              onPress={() => {
                setBlocked(false);
                Linking.openSettings();
              }}
            >
              <Feather name="settings" size={20} color={colors.onSurface} />
              <Text style={styles.sheetBtnText}>Open Settings</Text>
            </Pressable>
            <Pressable style={styles.sheetCancel} onPress={() => setBlocked(false)}>
              <Text style={styles.sheetCancelText}>Not now</Text>
            </Pressable>
          </View>
        </Pressable>
      </Modal>
    </BlurView>
  );
}

const useStyles = makeStyles((c) => ({
  wrap: {
    borderTopWidth: 1,
    borderTopColor: c.border,
    backgroundColor: Platform.OS === "ios" ? "transparent" : c.surface,
    paddingTop: 10,
    paddingHorizontal: 16,
  },
  previewRow: { marginBottom: 10, flexDirection: "row" },
  previewImg: { width: 64, height: 64, borderRadius: 4, backgroundColor: c.surfaceTertiary },
  previewOverlay: {
    ...({ position: "absolute" } as const),
    width: 64,
    height: 64,
    borderRadius: 4,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "rgba(0,0,0,0.45)",
  },
  removeBadge: {
    position: "absolute",
    top: -6,
    left: 52,
    width: 22,
    height: 22,
    borderRadius: 11,
    backgroundColor: c.brandPrimary,
    alignItems: "center",
    justifyContent: "center",
  },
  inner: { flexDirection: "row", alignItems: "flex-end", gap: 8 },
  attachBtn: {
    width: 44,
    height: 44,
    borderRadius: 4,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: c.surfaceTertiary,
  },
  input: {
    flex: 1,
    minHeight: 44,
    maxHeight: 140,
    backgroundColor: c.surfaceTertiary,
    borderRadius: 4,
    paddingHorizontal: 14,
    paddingTop: 12,
    paddingBottom: 12,
    fontFamily: fonts.text,
    fontSize: 15,
    color: c.onSurface,
  },
  sendBtn: {
    width: 44,
    height: 44,
    borderRadius: 4,
    backgroundColor: c.brandPrimary,
    alignItems: "center",
    justifyContent: "center",
  },
  sendBtnDisabled: { opacity: 0.35 },
  backdrop: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.4)",
    justifyContent: "flex-end",
  },
  sheet: {
    backgroundColor: c.surface,
    borderTopLeftRadius: 8,
    borderTopRightRadius: 8,
    padding: 20,
    paddingBottom: 34,
    gap: 8,
  },
  sheetTitle: {
    fontFamily: fonts.display,
    fontSize: 20,
    fontWeight: "700",
    color: c.onSurface,
    marginBottom: 8,
  },
  sheetBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 14,
    paddingVertical: 16,
    paddingHorizontal: 4,
  },
  sheetBtnText: { fontFamily: fonts.text, fontSize: 16, color: c.onSurface },
  sheetCancel: { paddingVertical: 16, alignItems: "center", marginTop: 4 },
  sheetCancelText: { fontFamily: fonts.text, fontSize: 15, color: c.muted },
  blockedText: {
    fontFamily: fonts.text,
    fontSize: 14,
    lineHeight: 21,
    color: c.onSurfaceTertiary,
    marginBottom: 8,
  },
}));
