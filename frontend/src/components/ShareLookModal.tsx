import { useRef, useState } from "react";
import { View, Text, Pressable, Modal, Platform, Share, ActivityIndicator } from "react-native";
import ViewShot, { captureRef } from "react-native-view-shot";
import * as Sharing from "expo-sharing";
import Feather from "@react-native-vector-icons/feather";

import { makeStyles, useTheme, fonts } from "@/src/theme";

type Props = {
  visible: boolean;
  text: string;
  onClose: () => void;
};

export function ShareLookModal({ visible, text, onClose }: Props) {
  const styles = useStyles();
  const { colors } = useTheme();
  const shotRef = useRef<ViewShot>(null);
  const [busy, setBusy] = useState(false);

  const shareText = async () => {
    try {
      await Share.share({ message: `${text}\n\n— via StyleScan` });
    } catch {
      /* user dismissed */
    }
    onClose();
  };

  const shareImage = async () => {
    if (Platform.OS === "web") {
      await shareText();
      return;
    }
    setBusy(true);
    try {
      const uri = await captureRef(shotRef, { format: "png", quality: 0.95, result: "tmpfile" });
      const available = await Sharing.isAvailableAsync();
      if (available) {
        await Sharing.shareAsync(uri, { mimeType: "image/png", dialogTitle: "Share your look" });
      } else {
        await shareText();
      }
    } catch {
      await shareText();
    } finally {
      setBusy(false);
      onClose();
    }
  };

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <Pressable style={styles.backdrop} onPress={onClose}>
        <Pressable style={styles.sheet} onPress={() => {}}>
          <View style={styles.grabber} />
          <Text style={styles.title}>Share your look</Text>

          <ViewShot ref={shotRef} style={styles.cardWrap}>
            <View style={styles.card}>
              <Text style={styles.cardKicker}>STYLESCAN</Text>
              <Text style={styles.cardText} numberOfLines={16}>
                {text}
              </Text>
              <Text style={styles.cardFooter}>Styled with StyleScan</Text>
            </View>
          </ViewShot>

          <View style={styles.btnRow}>
            <Pressable testID="share-image-button" style={styles.primaryBtn} onPress={shareImage} disabled={busy}>
              {busy ? (
                <ActivityIndicator color={colors.onBrandPrimary} size="small" />
              ) : (
                <>
                  <Feather name="image" size={18} color={colors.onBrandPrimary} />
                  <Text style={styles.primaryBtnText}>
                    {Platform.OS === "web" ? "Share text" : "Share as image"}
                  </Text>
                </>
              )}
            </Pressable>
            <Pressable testID="share-text-button" style={styles.secondaryBtn} onPress={shareText}>
              <Text style={styles.secondaryBtnText}>Share as text</Text>
            </Pressable>
          </View>
        </Pressable>
      </Pressable>
    </Modal>
  );
}

const useStyles = makeStyles((c) => ({
  backdrop: { flex: 1, backgroundColor: "rgba(0,0,0,0.5)", justifyContent: "flex-end" },
  sheet: {
    backgroundColor: c.surface,
    borderTopLeftRadius: 8,
    borderTopRightRadius: 8,
    padding: 20,
    paddingBottom: 40,
  },
  grabber: {
    width: 40,
    height: 4,
    borderRadius: 2,
    backgroundColor: c.border,
    alignSelf: "center",
    marginBottom: 16,
  },
  title: {
    fontFamily: fonts.display,
    fontSize: 22,
    fontWeight: "700",
    color: c.onSurface,
    marginBottom: 16,
  },
  cardWrap: { borderRadius: 4, overflow: "hidden" },
  card: { backgroundColor: c.surfaceInverse, padding: 24 },
  cardKicker: {
    fontFamily: fonts.text,
    fontSize: 12,
    letterSpacing: 4,
    color: c.onSurfaceInverse,
    opacity: 0.7,
    marginBottom: 16,
  },
  cardText: {
    fontFamily: fonts.display,
    fontSize: 18,
    lineHeight: 28,
    color: c.onSurfaceInverse,
  },
  cardFooter: {
    fontFamily: fonts.text,
    fontSize: 12,
    letterSpacing: 1,
    color: c.onSurfaceInverse,
    opacity: 0.6,
    marginTop: 20,
  },
  btnRow: { marginTop: 20, gap: 12 },
  primaryBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 10,
    backgroundColor: c.brandPrimary,
    borderRadius: 4,
    height: 52,
  },
  primaryBtnText: { fontFamily: fonts.text, fontSize: 16, color: c.onBrandPrimary },
  secondaryBtn: { alignItems: "center", justifyContent: "center", height: 44 },
  secondaryBtnText: { fontFamily: fonts.text, fontSize: 15, color: c.muted },
}));
