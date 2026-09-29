import { useState } from "react";
import {
  View,
  Text,
  Pressable,
  FlatList,
  Platform,
  Modal,
  TextInput,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { KeyboardAvoidingView } from "react-native-keyboard-controller";
import { useRouter } from "expo-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Image } from "expo-image";
import Feather from "@react-native-vector-icons/feather";
import * as Haptics from "expo-haptics";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";

import { makeStyles, useTheme, fonts } from "@/src/theme";
import {
  listConversations,
  deleteConversation,
  updateConversation,
  type Conversation,
} from "@/src/api";

dayjs.extend(relativeTime);

const EMPTY_IMG =
  "https://images.unsplash.com/photo-1517502166878-35c93a0072f0?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA1NzB8MHwxfHNlYXJjaHwxfHxtaW5pbWFsaXN0JTIwZW1wdHklMjB3YXJkcm9iZSUyMGhhbmdlciUyMHdoaXRlfGVufDB8fHx8MTc5MDY3MTgxNnww&ixlib=rb-4.1.0&q=85";

export default function HistoryScreen() {
  const styles = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const queryClient = useQueryClient();

  const [renaming, setRenaming] = useState<Conversation | null>(null);
  const [renameText, setRenameText] = useState("");

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["conversations"] });

  const { data: conversations, isLoading } = useQuery({
    queryKey: ["conversations"],
    queryFn: listConversations,
  });

  const del = useMutation({ mutationFn: deleteConversation, onSuccess: invalidate });
  const patch = useMutation({
    mutationFn: (v: { id: string; title?: string; pinned?: boolean }) =>
      updateConversation(v.id, { title: v.title, pinned: v.pinned }),
    onSuccess: invalidate,
  });

  const haptic = () => Platform.OS !== "web" && Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);

  const openConversation = (id: string) => {
    haptic();
    router.replace({ pathname: "/", params: { id } });
  };

  const submitRename = () => {
    if (renaming && renameText.trim()) {
      patch.mutate({ id: renaming.id, title: renameText.trim() });
    }
    setRenaming(null);
  };

  const renderItem = ({ item }: { item: Conversation }) => (
    <Pressable
      testID={`history-row-${item.id}`}
      style={styles.row}
      onPress={() => openConversation(item.id)}
    >
      <View style={styles.rowText}>
        <View style={styles.titleRow}>
          {item.pinned && (
            <Feather name="bookmark" size={13} color={colors.onSurface} style={styles.pinMark} />
          )}
          <Text style={styles.rowTitle} numberOfLines={1}>
            {item.title}
          </Text>
        </View>
        <Text style={styles.rowMeta}>{dayjs(item.updated_at).fromNow()}</Text>
      </View>
      <View style={styles.rowActions}>
        <Pressable
          testID={`history-pin-${item.id}`}
          hitSlop={8}
          style={styles.actBtn}
          onPress={() => {
            haptic();
            patch.mutate({ id: item.id, pinned: !item.pinned });
          }}
        >
          <Feather
            name={item.pinned ? "bookmark" : "bookmark"}
            size={17}
            color={item.pinned ? colors.onSurface : colors.muted}
          />
        </Pressable>
        <Pressable
          testID={`history-rename-${item.id}`}
          hitSlop={8}
          style={styles.actBtn}
          onPress={() => {
            haptic();
            setRenaming(item);
            setRenameText(item.title);
          }}
        >
          <Feather name="edit-2" size={16} color={colors.muted} />
        </Pressable>
        <Pressable
          testID={`history-delete-${item.id}`}
          hitSlop={8}
          style={styles.actBtn}
          onPress={() => del.mutate(item.id)}
        >
          <Feather name="trash-2" size={17} color={colors.muted} />
        </Pressable>
      </View>
    </Pressable>
  );

  return (
    <View style={[styles.root, { paddingTop: insets.top }]}>
      <View style={styles.header}>
        <Pressable testID="history-back-button" onPress={() => router.back()} style={styles.iconBtn}>
          <Feather name="chevron-left" size={26} color={colors.onSurface} />
        </Pressable>
      </View>
      <Text style={styles.title}>Conversations</Text>

      {isLoading ? (
        <View style={styles.skeletonWrap} testID="history-loading">
          {[0, 1, 2, 3, 4].map((i) => (
            <View key={i} style={styles.skeleton} />
          ))}
        </View>
      ) : (conversations?.length ?? 0) === 0 ? (
        <View style={styles.empty} testID="history-empty">
          <Image source={{ uri: EMPTY_IMG }} style={styles.emptyImg} contentFit="cover" />
          <Text style={styles.emptyText}>Your styling history is clear.</Text>
        </View>
      ) : (
        <FlatList
          data={conversations}
          keyExtractor={(c) => c.id}
          renderItem={renderItem}
          ItemSeparatorComponent={() => <View style={styles.divider} />}
          contentContainerStyle={{ paddingBottom: insets.bottom + 24 }}
        />
      )}

      <Modal visible={!!renaming} transparent animationType="fade" onRequestClose={() => setRenaming(null)}>
        <KeyboardAvoidingView
          style={styles.backdrop}
          behavior={Platform.OS === "ios" ? "padding" : "height"}
        >
          <Pressable style={styles.backdropFill} onPress={() => setRenaming(null)} />
          <View style={styles.renameCard}>
            <Text style={styles.renameTitle}>Rename session</Text>
            <TextInput
              testID="rename-input"
              style={styles.renameInput}
              value={renameText}
              onChangeText={setRenameText}
              placeholder="Session name"
              placeholderTextColor={colors.muted}
              autoFocus
              onSubmitEditing={submitRename}
            />
            <View style={styles.renameBtns}>
              <Pressable style={styles.renameCancel} onPress={() => setRenaming(null)}>
                <Text style={styles.renameCancelText}>Cancel</Text>
              </Pressable>
              <Pressable testID="rename-save-button" style={styles.renameSave} onPress={submitRename}>
                <Text style={styles.renameSaveText}>Save</Text>
              </Pressable>
            </View>
          </View>
        </KeyboardAvoidingView>
      </Modal>
    </View>
  );
}

const useStyles = makeStyles((c) => ({
  root: { flex: 1, backgroundColor: c.surface },
  header: { height: 44, justifyContent: "center", paddingHorizontal: 8 },
  iconBtn: { width: 44, height: 44, alignItems: "center", justifyContent: "center" },
  title: {
    fontFamily: fonts.display,
    fontSize: 34,
    fontWeight: "700",
    color: c.onSurface,
    paddingHorizontal: 24,
    marginTop: 4,
    marginBottom: 20,
  },
  row: { flexDirection: "row", alignItems: "center", paddingVertical: 18, paddingHorizontal: 24 },
  rowText: { flex: 1, paddingRight: 12 },
  titleRow: { flexDirection: "row", alignItems: "center", marginBottom: 6 },
  pinMark: { marginRight: 6 },
  rowTitle: { fontFamily: fonts.text, fontSize: 16, color: c.onSurface, flexShrink: 1 },
  rowMeta: { fontFamily: fonts.text, fontSize: 12, color: c.muted },
  rowActions: { flexDirection: "row", alignItems: "center", gap: 4 },
  actBtn: { width: 34, height: 40, alignItems: "center", justifyContent: "center" },
  divider: { height: 1, backgroundColor: c.divider, marginHorizontal: 24 },
  skeletonWrap: { paddingHorizontal: 24, gap: 24, marginTop: 8 },
  skeleton: { height: 18, borderRadius: 4, backgroundColor: c.surfaceTertiary, width: "70%" },
  empty: { flex: 1, alignItems: "center", justifyContent: "center", padding: 32, gap: 24 },
  emptyImg: { width: 200, height: 200, borderRadius: 4 },
  emptyText: { fontFamily: fonts.display, fontSize: 20, color: c.onSurface, textAlign: "center" },
  backdrop: { flex: 1, justifyContent: "center", alignItems: "center" },
  backdropFill: { ...({ position: "absolute" } as const), top: 0, left: 0, right: 0, bottom: 0, backgroundColor: "rgba(0,0,0,0.4)" },
  renameCard: {
    width: "84%",
    backgroundColor: c.surface,
    borderRadius: 8,
    padding: 20,
  },
  renameTitle: { fontFamily: fonts.display, fontSize: 20, fontWeight: "700", color: c.onSurface, marginBottom: 16 },
  renameInput: {
    borderWidth: 1,
    borderColor: c.border,
    borderRadius: 4,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontFamily: fonts.text,
    fontSize: 15,
    color: c.onSurface,
    backgroundColor: c.surfaceTertiary,
  },
  renameBtns: { flexDirection: "row", justifyContent: "flex-end", gap: 8, marginTop: 16 },
  renameCancel: { paddingVertical: 12, paddingHorizontal: 16 },
  renameCancelText: { fontFamily: fonts.text, fontSize: 15, color: c.muted },
  renameSave: { paddingVertical: 12, paddingHorizontal: 20, backgroundColor: c.brandPrimary, borderRadius: 4 },
  renameSaveText: { fontFamily: fonts.text, fontSize: 15, color: c.onBrandPrimary },
}));
