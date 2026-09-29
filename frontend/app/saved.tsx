import { useState } from "react";
import { View, Text, Pressable, FlatList, Platform } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Image } from "expo-image";
import Feather from "@react-native-vector-icons/feather";
import * as Haptics from "expo-haptics";

import { makeStyles, useTheme, fonts } from "@/src/theme";
import { listSaved, deleteSaved, type SavedLook } from "@/src/api";
import { ShareLookModal } from "@/src/components/ShareLookModal";

const EMPTY_IMG =
  "https://images.unsplash.com/photo-1445205170230-053b83016050?crop=entropy&cs=srgb&fm=jpg&w=800&q=85";

export default function SavedScreen() {
  const styles = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [shareText, setShareText] = useState<string | null>(null);

  const { data: looks, isLoading } = useQuery({
    queryKey: ["saved"],
    queryFn: listSaved,
  });

  const del = useMutation({
    mutationFn: deleteSaved,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["saved"] }),
  });

  const haptic = () => Platform.OS !== "web" && Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);

  const renderItem = ({ item }: { item: SavedLook }) => (
    <View style={styles.card} testID={`saved-card-${item.id}`}>
      <Text style={styles.cardText}>{item.content.replace(/\*\*/g, "")}</Text>
      <View style={styles.cardActions}>
        <Pressable
          testID={`saved-share-${item.id}`}
          style={styles.act}
          onPress={() => {
            haptic();
            setShareText(item.content);
          }}
        >
          <Feather name="share" size={16} color={colors.muted} />
          <Text style={styles.actText}>Share</Text>
        </Pressable>
        <Pressable
          testID={`saved-open-${item.id}`}
          style={styles.act}
          onPress={() => {
            haptic();
            router.replace({ pathname: "/", params: { id: item.conversation_id } });
          }}
        >
          <Feather name="message-circle" size={16} color={colors.muted} />
          <Text style={styles.actText}>Open chat</Text>
        </Pressable>
        <Pressable
          testID={`saved-delete-${item.id}`}
          style={styles.act}
          hitSlop={8}
          onPress={() => del.mutate(item.id)}
        >
          <Feather name="trash-2" size={16} color={colors.muted} />
        </Pressable>
      </View>
    </View>
  );

  return (
    <View style={[styles.root, { paddingTop: insets.top }]}>
      <View style={styles.header}>
        <Pressable testID="saved-back-button" onPress={() => router.back()} style={styles.iconBtn}>
          <Feather name="chevron-left" size={26} color={colors.onSurface} />
        </Pressable>
      </View>
      <Text style={styles.title}>Saved Looks</Text>

      {isLoading ? (
        <View style={styles.skeletonWrap} testID="saved-loading">
          {[0, 1, 2].map((i) => (
            <View key={i} style={styles.skeleton} />
          ))}
        </View>
      ) : (looks?.length ?? 0) === 0 ? (
        <View style={styles.empty} testID="saved-empty">
          <Image source={{ uri: EMPTY_IMG }} style={styles.emptyImg} contentFit="cover" />
          <Text style={styles.emptyText}>No saved looks yet.</Text>
          <Text style={styles.emptySub}>Tap “Save” on any stylist reply to keep it here.</Text>
        </View>
      ) : (
        <FlatList
          data={looks}
          keyExtractor={(l) => l.id}
          renderItem={renderItem}
          contentContainerStyle={{ paddingHorizontal: 20, paddingBottom: insets.bottom + 24, gap: 16 }}
        />
      )}

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
  card: {
    borderWidth: 1,
    borderColor: c.border,
    backgroundColor: c.surfaceSecondary,
    borderRadius: 4,
    padding: 18,
  },
  cardText: { fontFamily: fonts.text, fontSize: 15, lineHeight: 23, color: c.onSurfaceSecondary },
  cardActions: {
    flexDirection: "row",
    alignItems: "center",
    gap: 22,
    marginTop: 14,
    paddingTop: 14,
    borderTopWidth: 1,
    borderTopColor: c.divider,
  },
  act: { flexDirection: "row", alignItems: "center", gap: 6 },
  actText: { fontFamily: fonts.text, fontSize: 13, color: c.muted },
  skeletonWrap: { paddingHorizontal: 24, gap: 20 },
  skeleton: { height: 90, borderRadius: 4, backgroundColor: c.surfaceTertiary },
  empty: { flex: 1, alignItems: "center", justifyContent: "center", padding: 32, gap: 16 },
  emptyImg: { width: 180, height: 180, borderRadius: 4 },
  emptyText: { fontFamily: fonts.display, fontSize: 22, color: c.onSurface, textAlign: "center" },
  emptySub: { fontFamily: fonts.text, fontSize: 14, color: c.muted, textAlign: "center" },
}));
