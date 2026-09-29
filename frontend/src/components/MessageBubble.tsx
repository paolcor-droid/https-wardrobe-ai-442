import { View, Text } from "react-native";
import { makeStyles, fonts } from "@/src/theme";
import type { ChatMessage } from "@/src/api";

type Props = {
  message: Pick<ChatMessage, "role" | "content">;
  streaming?: boolean;
};

// Renders inline **bold** markdown as actual bold spans, leaving the rest plain.
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

export function MessageBubble({ message, streaming }: Props) {
  const styles = useStyles();
  const isUser = message.role === "user";

  return (
    <View
      style={[styles.row, isUser ? styles.rowUser : styles.rowAssistant]}
      testID={`message-${message.role}`}
    >
      <View style={[styles.bubble, isUser ? styles.userBubble : styles.assistantBubble]}>
        {!isUser && <Text style={styles.stylistLabel}>STYLIST</Text>}
        <Text style={[styles.text, isUser ? styles.userText : styles.assistantText]}>
          {isUser ? message.content : renderInline(message.content)}
          {streaming && !message.content ? "…" : ""}
        </Text>
      </View>
    </View>
  );
}

const useStyles = makeStyles((c) => ({
  row: {
    width: "100%",
    marginBottom: 16,
    flexDirection: "row",
  },
  rowUser: { justifyContent: "flex-end" },
  rowAssistant: { justifyContent: "flex-start" },
  bubble: {
    maxWidth: "86%",
    paddingVertical: 12,
    paddingHorizontal: 14,
    borderRadius: 4,
  },
  userBubble: {
    backgroundColor: c.surfaceTertiary,
    borderTopRightRadius: 0,
  },
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
  text: {
    fontFamily: fonts.text,
    fontSize: 15,
    lineHeight: 23,
  },
  userText: { color: c.onSurfaceTertiary },
  assistantText: { color: c.onSurfaceSecondary },
}));
