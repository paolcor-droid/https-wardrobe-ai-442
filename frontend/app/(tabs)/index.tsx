import { useEffect, useRef, useState, useCallback } from "react";
import {
  View,
  Text,
  ScrollView,
  Pressable,
  Platform,
  ActivityIndicator,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { KeyboardAvoidingView } from "react-native-keyboard-controller";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useQueryClient } from "@tanstack/react-query";
import { BlurView } from "expo-blur";
import Feather from "@react-native-vector-icons/feather";
import * as Haptics from "expo-haptics";

import { makeStyles, useTheme, fonts } from "@/src/theme";
import { usesNativeTabs } from "@/src/navigation";
import {
  createConversation,
  getMessages,
  streamChat,
  saveLook,
  type ChatMessage,
} from "@/src/api";
import { MessageBubble } from "@/src/components/MessageBubble";
import { Composer } from "@/src/components/Composer";
import { ChatEmpty } from "@/src/components/ChatEmpty";
import { ShareLookModal } from "@/src/components/ShareLookModal";
import { ModelSelector } from "@/src/components/ModelSelector";
import { useModel } from "@/src/model-provider";

type LocalMsg = Pick<ChatMessage, "role" | "content" | "image_path"> & { id: string };

export default function ChatScreen() {
  const styles = useStyles();
  const { colors, scheme } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const params = useLocalSearchParams<{ id?: string }>();
  const queryClient = useQueryClient();
  const { provider } = useModel();
  const providerRef = useRef(provider);
  providerRef.current = provider;

  const [convoId, setConvoId] = useState<string | null>(null);
  const [messages, setMessages] = useState<LocalMsg[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [savedIds, setSavedIds] = useState<Set<string>>(new Set());
  const [shareText, setShareText] = useState<string | null>(null);

  const streamingRef = useRef(false);
  const streamTextRef = useRef("");
  const scrollRef = useRef<ScrollView>(null);
  const abortRef = useRef<null | (() => void)>(null);

  const headerHeight = 56 + insets.top;
  const bottomChrome = usesNativeTabs ? insets.bottom : 0;

  useEffect(() => {
    const pid = params.id ? String(params.id) : null;
    if (pid !== convoId && !streamingRef.current) setConvoId(pid);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.id]);

  useEffect(() => {
    if (streamingRef.current) return;
    if (!convoId) {
      setMessages([]);
      setError(null);
      return;
    }
    let active = true;
    setLoadingHistory(true);
    getMessages(convoId)
      .then((m) => {
        if (active)
          setMessages(
            m.map((x) => ({ id: x.id, role: x.role, content: x.content, image_path: x.image_path })),
          );
      })
      .catch(() => active && setError("We lost connection to the styling desk."))
      .finally(() => active && setLoadingHistory(false));
    return () => {
      active = false;
    };
  }, [convoId]);

  useEffect(() => {
    const t = setTimeout(() => scrollRef.current?.scrollToEnd({ animated: true }), 60);
    return () => clearTimeout(t);
  }, [messages, streamingText]);

  useEffect(() => () => abortRef.current?.(), []);

  const handleSend = useCallback(
    async (text: string, imagePath?: string | null) => {
      setError(null);
      const userMsg: LocalMsg = {
        id: `u-${Date.now()}`,
        role: "user",
        content: text,
        image_path: imagePath ?? null,
      };
      setMessages((prev) => [...prev, userMsg]);
      streamingRef.current = true;
      streamTextRef.current = "";
      setStreamingText("");
      setStreaming(true);

      let id = convoId;
      if (!id) {
        try {
          const convo = await createConversation();
          id = convo.id;
          setConvoId(id);
        } catch {
          streamingRef.current = false;
          setStreaming(false);
          setError("Couldn't start a new session. Please try again.");
          return;
        }
      }

      abortRef.current = streamChat(
        id,
        text,
        {
          onDelta: (t) => {
            streamTextRef.current += t;
            setStreamingText(streamTextRef.current);
          },
          onDone: ({ message_id }) => {
            const finalText = streamTextRef.current;
            setMessages((prev) => [
              ...prev,
              { id: message_id, role: "assistant", content: finalText, image_path: null },
            ]);
            streamingRef.current = false;
            setStreaming(false);
            setStreamingText("");
            queryClient.invalidateQueries({ queryKey: ["conversations"] });
          },
          onError: (msg) => {
            streamingRef.current = false;
            setStreaming(false);
            setStreamingText("");
            setError(msg || "We lost connection to the styling desk.");
          },
        },
        imagePath,
        providerRef.current,
      );
    },
    [convoId, queryClient],
  );

  const handleSave = useCallback(
    async (messageId: string) => {
      if (Platform.OS !== "web") Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
      setSavedIds((prev) => new Set(prev).add(messageId));
      try {
        await saveLook(messageId);
        queryClient.invalidateQueries({ queryKey: ["saved"] });
      } catch {
        setSavedIds((prev) => {
          const next = new Set(prev);
          next.delete(messageId);
          return next;
        });
      }
    },
    [queryClient],
  );

  const startNewChat = useCallback(() => {
    if (streamingRef.current) return;
    if (Platform.OS !== "web") Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    abortRef.current?.();
    setConvoId(null);
    setMessages([]);
    setStreamingText("");
    setError(null);
    router.setParams({ id: "" });
  }, [router]);

  const openHistory = useCallback(() => {
    if (Platform.OS !== "web") Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    router.push("/history");
  }, [router]);

  const openSaved = useCallback(() => {
    if (Platform.OS !== "web") Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    router.push("/saved");
  }, [router]);

  const showEmpty = !convoId && messages.length === 0 && !streaming;

  return (
    <View style={styles.root}>
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === "ios" ? "translate-with-padding" : "height"}
        keyboardVerticalOffset={headerHeight}
      >
        {showEmpty ? (
          <View style={[styles.flex, { paddingTop: headerHeight }]}>
            <View style={styles.selectorBar}>
              <ModelSelector />
            </View>
            <ChatEmpty onPick={(p) => handleSend(p)} />
          </View>
        ) : (
          <ScrollView
            ref={scrollRef}
            style={styles.flex}
            contentContainerStyle={[styles.feed, { paddingTop: headerHeight + 16 }]}
            showsVerticalScrollIndicator={false}
            keyboardShouldPersistTaps="handled"
            keyboardDismissMode="interactive"
          >
            {loadingHistory && messages.length === 0 ? (
              <View style={styles.center} testID="chat-loading">
                <ActivityIndicator color={colors.onSurface} />
                <Text style={styles.loadingText}>Consulting stylist…</Text>
              </View>
            ) : (
              <>
                {messages.map((m) => (
                  <MessageBubble
                    key={m.id}
                    message={m}
                    saved={savedIds.has(m.id)}
                    onSave={m.role === "assistant" ? () => handleSave(m.id) : undefined}
                    onShare={m.role === "assistant" ? () => setShareText(m.content) : undefined}
                  />
                ))}
                {streaming && (
                  <MessageBubble
                    message={{ role: "assistant", content: streamingText }}
                    streaming
                  />
                )}
                {error && (
                  <View style={styles.errorBox} testID="chat-error">
                    <Text style={styles.errorText}>{error}</Text>
                  </View>
                )}
              </>
            )}
          </ScrollView>
        )}

        <Composer onSend={handleSend} disabled={streaming} bottomInset={bottomChrome} />
      </KeyboardAvoidingView>

      <BlurView
        intensity={Platform.OS === "ios" ? 50 : 0}
        tint={scheme === "dark" ? "dark" : "light"}
        style={[styles.header, { paddingTop: insets.top, height: headerHeight }]}
      >
        <Pressable testID="open-history-button" onPress={openHistory} style={styles.iconBtn}>
          <Feather name="menu" size={22} color={colors.onSurface} />
        </Pressable>
        <Text style={styles.headerTitle}>StyleScan</Text>
        <View style={styles.headerRight}>
          <Pressable testID="open-saved-button" onPress={openSaved} style={styles.iconBtn}>
            <Feather name="bookmark" size={20} color={colors.onSurface} />
          </Pressable>
          <Pressable testID="new-chat-button" onPress={startNewChat} style={styles.iconBtn}>
            <Feather name="edit" size={20} color={colors.onSurface} />
          </Pressable>
        </View>
      </BlurView>

      <ShareLookModal
        visible={!!shareText}
        text={shareText ?? ""}
        onClose={() => setShareText(null)}
      />
    </View>
  );
}

const useStyles = makeStyles((c) => ({
  root: { flex: 1, backgroundColor: c.surface },
  flex: { flex: 1 },
  selectorBar: { paddingHorizontal: 16, paddingTop: 12 },
  feed: { paddingHorizontal: 16, paddingBottom: 20 },
  header: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 12,
    borderBottomWidth: 1,
    borderBottomColor: c.border,
    backgroundColor: Platform.OS === "ios" ? "transparent" : c.surface,
  },
  headerRight: { flexDirection: "row", alignItems: "center" },
  headerTitle: {
    fontFamily: fonts.display,
    fontSize: 22,
    fontWeight: "700",
    color: c.onSurface,
    letterSpacing: 0.5,
  },
  iconBtn: { width: 44, height: 44, alignItems: "center", justifyContent: "center" },
  center: { paddingTop: 80, alignItems: "center", gap: 12 },
  loadingText: { fontFamily: fonts.text, color: c.muted, fontSize: 14 },
  errorBox: { borderWidth: 1, borderColor: c.error, borderRadius: 4, padding: 14, marginTop: 4 },
  errorText: { fontFamily: fonts.text, color: c.error, fontSize: 14 },
}));
