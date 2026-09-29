import { useState } from "react";
import { View, Text, Pressable, Modal, Linking } from "react-native";
import Feather from "@react-native-vector-icons/feather";

import { makeStyles, useTheme, fonts } from "@/src/theme";
import { pickWithPermission, type PickResult } from "@/src/utils/media";

type Props = {
  visible: boolean;
  onClose: () => void;
  onPicked: (asset: PickResult) => void;
  title?: string;
};

export function PhotoSourceSheet({ visible, onClose, onPicked, title = "Add a photo" }: Props) {
  const styles = useStyles();
  const { colors } = useTheme();
  const [blocked, setBlocked] = useState(false);

  const choose = async (kind: "camera" | "library") => {
    onClose();
    const r = await pickWithPermission(kind);
    if (r.status === "ok" && r.asset) onPicked(r.asset);
    else if (r.status === "blocked") setBlocked(true);
  };

  return (
    <>
      <Modal visible={visible} transparent animationType="fade" onRequestClose={onClose}>
        <Pressable style={styles.backdrop} onPress={onClose}>
          <View style={styles.sheet}>
            <Text style={styles.title}>{title}</Text>
            <Pressable testID="source-camera" style={styles.btn} onPress={() => choose("camera")}>
              <Feather name="camera" size={20} color={colors.onSurface} />
              <Text style={styles.btnText}>Take a photo</Text>
            </Pressable>
            <Pressable testID="source-library" style={styles.btn} onPress={() => choose("library")}>
              <Feather name="image" size={20} color={colors.onSurface} />
              <Text style={styles.btnText}>Choose from library</Text>
            </Pressable>
            <Pressable style={styles.cancel} onPress={onClose}>
              <Text style={styles.cancelText}>Cancel</Text>
            </Pressable>
          </View>
        </Pressable>
      </Modal>

      <Modal visible={blocked} transparent animationType="fade" onRequestClose={() => setBlocked(false)}>
        <Pressable style={styles.backdrop} onPress={() => setBlocked(false)}>
          <View style={styles.sheet}>
            <Text style={styles.title}>Permission needed</Text>
            <Text style={styles.blockedText}>
              Enable camera and photo access in Settings to add a photo.
            </Text>
            <Pressable
              testID="open-settings-button"
              style={styles.btn}
              onPress={() => {
                setBlocked(false);
                Linking.openSettings();
              }}
            >
              <Feather name="settings" size={20} color={colors.onSurface} />
              <Text style={styles.btnText}>Open Settings</Text>
            </Pressable>
            <Pressable style={styles.cancel} onPress={() => setBlocked(false)}>
              <Text style={styles.cancelText}>Not now</Text>
            </Pressable>
          </View>
        </Pressable>
      </Modal>
    </>
  );
}

const useStyles = makeStyles((c) => ({
  backdrop: { flex: 1, backgroundColor: "rgba(0,0,0,0.4)", justifyContent: "flex-end" },
  sheet: {
    backgroundColor: c.surface,
    borderTopLeftRadius: 8,
    borderTopRightRadius: 8,
    padding: 20,
    paddingBottom: 34,
    gap: 8,
  },
  title: { fontFamily: fonts.display, fontSize: 20, fontWeight: "700", color: c.onSurface, marginBottom: 8 },
  btn: { flexDirection: "row", alignItems: "center", gap: 14, paddingVertical: 16, paddingHorizontal: 4 },
  btnText: { fontFamily: fonts.text, fontSize: 16, color: c.onSurface },
  cancel: { paddingVertical: 16, alignItems: "center", marginTop: 4 },
  cancelText: { fontFamily: fonts.text, fontSize: 15, color: c.muted },
  blockedText: { fontFamily: fonts.text, fontSize: 14, lineHeight: 21, color: c.onSurfaceTertiary, marginBottom: 8 },
}));
