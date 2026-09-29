import { View, Text, Pressable } from "react-native";
import { Image } from "expo-image";
import Feather from "@react-native-vector-icons/feather";

import { makeStyles, useTheme, fonts } from "@/src/theme";
import { fileUrl, type ChatMessage } from "@/src/api";

type Props = {
  message: Pick<ChatMessage, "role" | "content" | "image_path"> & { id?: string };
  streaming?: boolean;
  saved?: boolean;
  onSave?: () => void;
  onShare?: () => void;
};

function renderInline(text: string) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**") && part.length > 4) {
      return (
        <Text key={i} style={{ fontWeight: "700" }}>
          {part.slice(2, -2)}
        </Text>
      );
    }
    return part;
  });
}

export function MessageBubble({ message, streaming, saved, onSave, onShare }: Props) {
  const styles = useStyles();
  const { colors } = useTheme();
  const isUser = message.role === "user";
  const showActions = !isUser && !streaming && !!message.content && (onSave || onShare);

  return (
    <View
      style={[styles.row, isUser ? styles.rowUser : styles.rowAssistant]}
      testID={`message-${message.role}`}
    >
      <View style={styles.column}>
        <View style={[styles.bubble, isUser ? styles.userBubble : styles.assistantBubble]}>
          {!isUser && <Text style={styles.stylistLabel}>STYLIST</Text>}
          {message.image_path ? (
            <Image
              testID="message-image"
              source={{ uri: fileUrl(message.image_path) }}
              style={styles.image}
              contentFit="cover"
              transition={200}
            />
          ) : null}
          {message.content ? (
            <Text style={[styles.text, isUser ? styles.userText : styles.assistantText]}>
              {isUser ? message.content : renderInline(message.content)}
            </Text>
          ) : streaming ? (
            <Text style={[styles.text, styles.assistantText]}>…</Text>
          ) : null}
        </View>

        {showActions && (
          <View style={styles.actions}>
            <Pressable testID="save-look-button" style={styles.actionBtn} onPress={onSave} hitSlop={8}>
              <Feather
                name="bookmark"
                size={15}
                color={saved ? colors.onSurface : colors.muted}
              />
              <Text style={[styles.actionText, saved && styles.actionTextActive]}>
                {saved ? "Saved" : "Save"}
              </Text>
            </Pressable>
            <Pressable testID="share-look-button" style={styles.actionBtn} onPress={onShare} hitSlop={8}>
              <Feather name="share" size={15} color={colors.muted} />
              <Text style={styles.actionText}>Share</Text>
            </Pressable>
          </View>
        )}
      </View>
    </View>
  );
}

const useStyles = makeStyles((c) => ({
  row: { width: "100%", marginBottom: 16, flexDirection: "row" },
  rowUser: { justifyContent: "flex-end" },
  rowAssistant: { justifyContent: "flex-start" },
  column: { maxWidth: "86%" },
  bubble: { paddingVertical: 12, paddingHorizontal: 14, borderRadius: 4 },
  userBubble: { backgroundColor: c.surfaceTertiary, borderTopRightRadius: 0 },
  assistantBubble: {
    backgroundColor: c.surfaceSecondary,
    borderWidth: 1,
    borderColor: c.border,
    borderTopLeftRadius: 0,
  },
  stylistLabel: {
    fontFamily: fonts.text,
    fontSize: 10,
    letterSpacing: 2,
    color: c.muted,
    marginBottom: 6,
  },
  image: {
    width: 200,
    height: 200,
    borderRadius: 4,
    marginBottom: 8,
    backgroundColor: c.surfaceTertiary,
  },
  text: { fontFamily: fonts.text, fontSize: 15, lineHeight: 23 },
  userText: { color: c.onSurfaceTertiary },
  assistantText: { color: c.onSurfaceSecondary },
  actions: { flexDirection: "row", gap: 20, marginTop: 8, paddingLeft: 2 },
  actionBtn: { flexDirection: "row", alignItems: "center", gap: 6 },
  actionText: { fontFamily: fonts.text, fontSize: 13, color: c.muted },
  actionTextActive: { color: c.onSurface },
}));
