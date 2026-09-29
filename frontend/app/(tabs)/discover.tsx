import { View, Text, ScrollView, Pressable, Linking } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useQuery } from "@tanstack/react-query";
import Feather from "@react-native-vector-icons/feather";

import { getProfile } from "@/src/api";
import { RETAILERS, retailerUrl } from "@/src/retailers";
import { makeStyles, fonts } from "@/src/theme";

export default function DiscoverScreen() {
  const styles = useStyles();
  const insets = useSafeAreaInsets();
  const { data: profile } = useQuery({ queryKey: ["profile"], queryFn: getProfile });
  const prefs = profile?.preferences;
  const selected = RETAILERS.filter((r) => (prefs?.preferred_retailers ?? ["zara", "hm", "uniqlo"]).includes(r.id));
  const bestColour = profile?.skin?.best_accents?.[0]?.name ?? prefs?.preferred_colours?.[0] ?? "";
  const climateTerm = prefs?.climate === "hot" ? "lightweight linen cotton" : prefs?.climate === "cold" ? "warm layering" : "";
  const query = [bestColour, prefs?.style, climateTerm, prefs?.occasion].filter(Boolean).join(" ");

  return (
    <View style={styles.root}>
      <View style={[styles.header, { paddingTop: insets.top + 8 }]}>
        <Text style={styles.title}>Discover</Text>
        <Text style={styles.subtitle}>Your personalised shopping edit</Text>
      </View>
      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.card}>
          <Text style={styles.cardTitle}>What StyleScan is looking for</Text>
          <Text style={styles.body}>
            {prefs?.climate ?? "mild"} climate · {prefs?.style ?? "classic"} style · {prefs?.occasion ?? "casual"}
          </Text>
          {bestColour ? <Text style={styles.body}>Starting with {bestColour} and your analysed palette.</Text> : null}
          {prefs?.climate === "hot" ? <Text style={styles.reason}>Why: lightweight pieces are prioritised and heavy layers are excluded for hot weather.</Text> : null}
        </View>

        <Text style={styles.section}>SHOP YOUR RETAILERS</Text>
        <Text style={styles.note}>These buttons open retailer searches or catalogues. StyleScan does not yet claim live price, stock or availability from these stores.</Text>
        {selected.map((r) => (
          <Pressable key={r.id} style={styles.retailer} onPress={() => Linking.openURL(retailerUrl(r, query))}>
            <View style={styles.flex}>
              <Text style={styles.retailerName}>{r.name}</Text>
              <Text style={styles.retailerMeta}>{r.kind === "wholesale" ? "Wholesale catalogue" : query || "Retail catalogue"}</Text>
            </View>
            <Feather name="external-link" size={18} />
          </Pressable>
        ))}

        <View style={styles.info}>
          <Text style={styles.infoTitle}>Live products are the next data layer</Text>
          <Text style={styles.body}>The catalogue architecture is ready for verified provider data. Products will only be shown as live when a retailer or authorised catalogue source supplies the product, price and source URL.</Text>
        </View>
      </ScrollView>
    </View>
  );
}

const useStyles = makeStyles((c) => ({
  root: { flex: 1, backgroundColor: c.surface },
  flex: { flex: 1 },
  header: { paddingHorizontal: 20, paddingBottom: 12, borderBottomWidth: 1, borderBottomColor: c.border },
  title: { fontFamily: fonts.display, fontSize: 30, fontWeight: "700", color: c.onSurface },
  subtitle: { fontFamily: fonts.text, fontSize: 13, color: c.muted, marginTop: 4 },
  content: { padding: 20, paddingBottom: 60 },
  card: { borderWidth: 1, borderColor: c.border, backgroundColor: c.surfaceSecondary, padding: 18, borderRadius: 4 },
  cardTitle: { fontFamily: fonts.display, fontSize: 20, fontWeight: "700", color: c.onSurface, marginBottom: 8 },
  body: { fontFamily: fonts.text, fontSize: 14, lineHeight: 20, color: c.onSurfaceTertiary, marginTop: 4 },
  reason: { fontFamily: fonts.text, fontSize: 13, lineHeight: 19, color: c.onSurface, marginTop: 12 },
  section: { fontFamily: fonts.text, fontSize: 12, letterSpacing: 1.5, color: c.muted, marginTop: 28, marginBottom: 8 },
  note: { fontFamily: fonts.text, fontSize: 12, lineHeight: 18, color: c.muted, marginBottom: 12 },
  retailer: { flexDirection: "row", alignItems: "center", gap: 12, borderBottomWidth: 1, borderBottomColor: c.border, paddingVertical: 16 },
  retailerName: { fontFamily: fonts.text, fontSize: 16, fontWeight: "600", color: c.onSurface },
  retailerMeta: { fontFamily: fonts.text, fontSize: 12, color: c.muted, marginTop: 3, textTransform: "capitalize" },
  info: { marginTop: 28, padding: 16, backgroundColor: c.surfaceTertiary, borderRadius: 4 },
  infoTitle: { fontFamily: fonts.text, fontSize: 14, fontWeight: "600", color: c.onSurface },
}));
