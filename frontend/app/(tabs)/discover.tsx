import { View, Text, ScrollView, Pressable, Linking, Image, ActivityIndicator } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useQuery } from "@tanstack/react-query";
import Feather from "@react-native-vector-icons/feather";

import { getProfile, getCatalogueRecommendations, ProductRecommendation } from "@/src/api";
import { RETAILERS, DEFAULT_RETAILERS, retailerUrl } from "@/src/retailers";
import { makeStyles, fonts } from "@/src/theme";

export default function DiscoverScreen() {
  const styles = useStyles();
  const insets = useSafeAreaInsets();
  const { data: profile } = useQuery({ queryKey: ["profile"], queryFn: getProfile });
  const {
    data: catalogue,
    isLoading: catalogueLoading,
    isError: catalogueError,
  } = useQuery({
    queryKey: ["catalogue-recommendations", profile?.updated_at],
    queryFn: getCatalogueRecommendations,
    enabled: Boolean(profile),
  });

  const prefs = profile?.preferences;
  const preferredIds = prefs?.preferred_retailers ?? DEFAULT_RETAILERS;
  const preferred = RETAILERS.filter((r) => preferredIds.includes(r.id));
  const others = RETAILERS.filter((r) => !preferredIds.includes(r.id));
  const bestColour = profile?.skin?.best_accents?.[0]?.name ?? prefs?.preferred_colours?.[0] ?? "";
  const climateTerm = prefs?.climate === "hot" ? "lightweight linen cotton" : prefs?.climate === "cold" ? "warm layering" : "";
  const query = [bestColour, prefs?.style, climateTerm, prefs?.occasion].filter(Boolean).join(" ");

  const renderRetailer = (r: (typeof RETAILERS)[number]) => (
    <Pressable key={r.id} style={styles.retailer} onPress={() => Linking.openURL(retailerUrl(r, query))}>
      <View style={styles.flex}>
        <Text style={styles.retailerName}>{r.name}</Text>
        <Text style={styles.retailerMeta}>{r.kind === "wholesale" ? "Wholesale catalogue" : query || "Retail catalogue"}</Text>
      </View>
      <Feather name="external-link" size={18} />
    </Pressable>
  );

  const renderProduct = (product: ProductRecommendation) => (
    <View key={product.product_id} style={styles.productCard}>
      {product.image_url ? <Image source={{ uri: product.image_url }} style={styles.productImage} resizeMode="cover" /> : null}
      <View style={styles.productBody}>
        <Text style={styles.productBrand}>{product.brand || "LUMIÈRE EDIT"}</Text>
        <Text style={styles.productName}>{product.name}</Text>
        {product.colour_names.length ? <Text style={styles.productMeta}>Colour · {product.colour_names.join(", ")}</Text> : null}
        {product.sizes.length ? <Text style={styles.productMeta}>Available in snapshot · {product.sizes.join(", ")}</Text> : null}
        {product.materials.length ? <Text style={styles.productMeta}>{product.materials.join(" · ")}</Text> : null}
        <Text style={styles.price}>{product.price != null ? `${product.currency || "AUD"} ${product.price.toFixed(2)}` : "LUMIÈRE price not set yet"}</Text>
        <View style={styles.why}>
          <Text style={styles.whyTitle}>WHY THIS SUITS YOU</Text>
          {product.recommendation_reasons.map((reason) => (
            <Text key={reason} style={styles.reason}>• {reason}</Text>
          ))}
        </View>
      </View>
    </View>
  );

  return (
    <View style={styles.root}>
      <View style={[styles.header, { paddingTop: insets.top + 8 }]}>
        <Text style={styles.title}>Discover</Text>
        <Text style={styles.subtitle}>Your personalised shopping edit</Text>
      </View>
      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.card}>
          <Text style={styles.cardTitle}>What LUMIÈRE is looking for</Text>
          <Text style={styles.body}>
            {prefs?.climate ?? "mild"} climate · {prefs?.style ?? "classic"} style · {prefs?.occasion ?? "casual"}
          </Text>
          {bestColour ? <Text style={styles.body}>Starting with {bestColour} and your analysed palette.</Text> : null}
          {prefs?.climate === "hot" ? <Text style={styles.reason}>Why: lightweight pieces are prioritised and heavy layers are excluded for hot weather.</Text> : null}
        </View>

        <Text style={styles.section}>YOUR LUMIÈRE EDIT</Text>
        <Text style={styles.note}>For this integration trial, these are genuine catalogue records from the supplied XML snapshot. Current stock and selling prices are not claimed live.</Text>
        {catalogueLoading ? <ActivityIndicator style={styles.loading} /> : null}
        {catalogueError ? <Text style={styles.note}>The trial catalogue could not be loaded. Retailer discovery remains available below.</Text> : null}
        {!catalogueLoading && !catalogueError && catalogue?.recommendations.length === 0 ? (
          <View style={styles.info}>
            <Text style={styles.infoTitle}>No catalogue match yet</Text>
            <Text style={styles.body}>Your current filters did not match the trial snapshot. The full XML catalogue will provide a much wider selection.</Text>
          </View>
        ) : null}
        {catalogue?.recommendations.map(renderProduct)}

        <Text style={styles.section}>SHOP YOUR RETAILERS</Text>
        <Text style={styles.note}>These buttons open retailer searches or catalogues. LUMIÈRE does not claim live price, stock or availability from these stores.</Text>
        {preferred.map(renderRetailer)}

        {others.length > 0 ? <Text style={styles.section}>MORE RETAILERS</Text> : null}
        {others.map(renderRetailer)}
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
  reason: { fontFamily: fonts.text, fontSize: 13, lineHeight: 19, color: c.onSurface, marginTop: 5 },
  section: { fontFamily: fonts.text, fontSize: 12, letterSpacing: 1.5, color: c.muted, marginTop: 28, marginBottom: 8 },
  note: { fontFamily: fonts.text, fontSize: 12, lineHeight: 18, color: c.muted, marginBottom: 12 },
  loading: { marginVertical: 28 },
  productCard: { borderWidth: 1, borderColor: c.border, backgroundColor: c.surfaceSecondary, borderRadius: 6, overflow: "hidden", marginBottom: 18 },
  productImage: { width: "100%", aspectRatio: 0.82, backgroundColor: c.surfaceTertiary },
  productBody: { padding: 16 },
  productBrand: { fontFamily: fonts.text, fontSize: 11, letterSpacing: 1.3, color: c.muted, textTransform: "uppercase" },
  productName: { fontFamily: fonts.display, fontSize: 20, fontWeight: "700", color: c.onSurface, marginTop: 5 },
  productMeta: { fontFamily: fonts.text, fontSize: 12, lineHeight: 18, color: c.onSurfaceTertiary, marginTop: 5, textTransform: "capitalize" },
  price: { fontFamily: fonts.text, fontSize: 14, fontWeight: "600", color: c.onSurface, marginTop: 10 },
  why: { marginTop: 14, paddingTop: 12, borderTopWidth: 1, borderTopColor: c.border },
  whyTitle: { fontFamily: fonts.text, fontSize: 10, letterSpacing: 1.2, color: c.muted },
  retailer: { flexDirection: "row", alignItems: "center", gap: 12, borderBottomWidth: 1, borderBottomColor: c.border, paddingVertical: 16 },
  retailerName: { fontFamily: fonts.text, fontSize: 16, fontWeight: "600", color: c.onSurface },
  retailerMeta: { fontFamily: fonts.text, fontSize: 12, color: c.muted, marginTop: 3, textTransform: "capitalize" },
  info: { marginTop: 8, padding: 16, backgroundColor: c.surfaceTertiary, borderRadius: 4 },
  infoTitle: { fontFamily: fonts.text, fontSize: 14, fontWeight: "600", color: c.onSurface },
}));
