import { View, Text, Pressable, FlatList, Platform } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Image } from "expo-image";
import Feather from "@react-native-vector-icons/feather";
import * as Haptics from "expo-haptics";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";

import { makeStyles, useTheme, fonts } from "@/src/theme";
import { listConversations, deleteConversation, type Conversation } from "@/src/api";

dayjs.extend(relativeTime);

const EMPTY_IMG =
  "https://images.unsplash.com/photo-1517502166878-35c93a0072f0?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA1NzB8MHwxfHNlYXJjaHwxfHxtaW5pbWFsaXN0JTIwZW1wdHklMjB3YXJkcm9iZSUyMGhhbmdlciUyMHdoaXRlfGVufDB8fHx8MTc5MDY3MTgxNnww&ixlib=rb-4.1.0&q=85";

export default function HistoryScreen() {
  const styles = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const queryClient = useQueryClient();

  const { data: conversations, isLoading } = useQuery({
    queryKey: ["conversations"],
    queryFn: listConversations,
  });

  const del = useMutation({
    mutationFn: deleteConversation,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["conversations"] }),
  });

  const openConversation = (id: string) => {
    if (Platform.OS !== "web") Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    router.replace({ pathname: "/", params: { id } });
  };

  const renderItem = ({ item }: { item: Conversation }) => (
    <Pressable
      testID={`history-row-${item.id}`}
      style={styles.row}
      onPress={() => openConversation(item.id)}
    >
      <View style={styles.rowText}>
        <Text style={styles.rowTitle} numberOfLines={1}>
          {item.title}
        </Text>
        <Text style={styles.rowMeta}>{dayjs(item.updated_at).fromNow()}</Text>
      </View>
      <Pressable
        testID={`history-delete-${item.id}`}
        hitSlop={10}
        style={styles.deleteBtn}
        onPress={() => del.mutate(item.id)}
      >
        <Feather name="trash-2" size={18} color={colors.muted} />
      </Pressable>
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
  row: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: 20,
    paddingHorizontal: 24,
  },
  rowText: { flex: 1, paddingRight: 12 },
  rowTitle: { fontFamily: fonts.text, fontSize: 16, color: c.onSurface, marginBottom: 6 },
  rowMeta: { fontFamily: fonts.text, fontSize: 12, color: c.muted },
  deleteBtn: { width: 40, height: 40, alignItems: "center", justifyContent: "center" },
  divider: { height: 1, backgroundColor: c.divider, marginHorizontal: 24 },
  skeletonWrap: { paddingHorizontal: 24, gap: 24, marginTop: 8 },
  skeleton: { height: 18, borderRadius: 4, backgroundColor: c.surfaceTertiary, width: "70%" },
  empty: { flex: 1, alignItems: "center", justifyContent: "center", padding: 32, gap: 24 },
  emptyImg: { width: 200, height: 200, borderRadius: 4 },
  emptyText: { fontFamily: fonts.display, fontSize: 20, color: c.onSurface, textAlign: "center" },
}));
