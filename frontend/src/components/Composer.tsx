import { useState } from "react";
import { View, TextInput, Pressable, Platform } from "react-native";
import { BlurView } from "expo-blur";
import Feather from "@react-native-vector-icons/feather";
import * as Haptics from "expo-haptics";

import { makeStyles, useTheme, fonts } from "@/src/theme";

type Props = {
  onSend: (text: string) => void;
  disabled?: boolean;
  bottomInset: number;
};

export function Composer({ onSend, disabled, bottomInset }: Props) {
  const styles = useStyles();
  const { colors, scheme } = useTheme();
  const [text, setText] = useState("");

  const canSend = text.trim().length > 0 && !disabled;

  const handleSend = () => {
    if (!canSend) return;
    if (Platform.OS !== "web") Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    onSend(text.trim());
    setText("");
  };

  return (
    <BlurView
      intensity={Platform.OS === "ios" ? 40 : 0}
      tint={scheme === "dark" ? "dark" : "light"}
      style={[styles.wrap, { paddingBottom: bottomInset + 10 }]}
    >
      <View style={styles.inner}>
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
  inner: {
    flexDirection: "row",
    alignItems: "flex-end",
    gap: 10,
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
}));
