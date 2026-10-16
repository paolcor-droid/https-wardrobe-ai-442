import { useEffect, useState } from "react";
import { useRouter, useLocalSearchParams } from "expo-router";
import { View, Text, ScrollView, Pressable, Linking, Image, ActivityIndicator, useWindowDimensions, TextInput } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import Feather from "@react-native-vector-icons/feather";

import { getProfile, getCatalogueRecommendations, searchCatalogue, searchDemoCatalogue, addShoppingBagItem, getShoppingBag, prepareCatalogueGarment, saveProductFeedback, getProductFeedback, type ProductSentiment, type ProductRecommendation } from "@/src/api";
import { RETAILERS, DEFAULT_RETAILERS, retailerUrl } from "@/src/retailers";
import { makeStyles, fonts } from "@/src/theme";

export default function DiscoverScreen() {
  const styles = useStyles();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const completingOutfit = useLocalSearchParams<{ outfitFirstPath?: string; outfitFirstName?: string; outfitFirstId?: string; outfitFirstSizes?: string; outfitFirstColours?: string; stylistQuery?: string; }>();
  const queryClient = useQueryClient();
  const { data: profile } = useQuery({ queryKey: ["profile"], queryFn: getProfile });
  const [searchText, setSearchText] = useState("");
  const [demoMode, setDemoMode] = useState(false);
  const [showOutfitDiagnostics, setShowOutfitDiagnostics] = useState(false);
  const [expandedDemoOutfits, setExpandedDemoOutfits] = useState<string[]>([]);
  const [stylistContext, setStylistContext] = useState("");
  useEffect(() => {
    if (!completingOutfit.stylistQuery) return;
    const advice = completingOutfit.stylistQuery.slice(0, 450);
    setStylistContext(advice);
    // Never send an entire personal conversation as catalogue search terms.
    const garment = advice.match(/\b(blazer|trousers|jeans|dress|shirt|skirt|coat|jacket|sweater|cardigan|linen|blouse|shorts|chinos|suit|top|polo)\b/i);
    setSearchText(garment ? garment[0] : "");
    setPage(1);
  }, [completingOutfit.stylistQuery]);
  const [brandFilter, setBrandFilter] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [colourFilter, setColourFilter] = useState("");
  const [sizeFilter, setSizeFilter] = useState("");
  const [minPrice, setMinPrice] = useState("");
  const [maxPrice, setMaxPrice] = useState("");
  const [page, setPage] = useState(1);
  const searchFilters = { q: searchText, brand: brandFilter, category: categoryFilter,
    colour: colourFilter, size: sizeFilter,
    min_price: minPrice ? Number(minPrice) : undefined,
    max_price: maxPrice ? Number(maxPrice) : undefined, page, per_page: 20 };
  const { data: searchResults, isLoading: searching, isError: searchError } = useQuery({
    queryKey: ["catalogue-search", demoMode, profile?.updated_at, searchFilters],
    queryFn: () => demoMode ? searchDemoCatalogue(searchFilters) : searchCatalogue(searchFilters),
    enabled: Boolean(profile),
  });
  const shownProducts = searchResults?.recommendations ?? [];
  const [bagMessage, setBagMessage] = useState("");
  const [bagMessageProduct, setBagMessageProduct] = useState("");
  const [selectedSizes, setSelectedSizes] = useState<Record<string, string>>({});
  const [selectedColours, setSelectedColours] = useState<Record<string, string>>({});
  const { data: bag } = useQuery({ queryKey: ["shopping-bag"], queryFn: getShoppingBag });
  const [feedbackError, setFeedbackError] = useState<string | null>(null);
  const { width: screenWidth } = useWindowDimensions();
  const gridColumns = screenWidth >= 1150 ? 3 : screenWidth >= 720 ? 2 : 1;
  const [preparingTryOn, setPreparingTryOn] = useState<string | null>(null);
  const [tryOnError, setTryOnError] = useState<string | null>(null);
  const [tryOnErrorProduct, setTryOnErrorProduct] = useState<string | null>(null);
  const [outfitItems, setOutfitItems] = useState<ProductRecommendation[]>([]);
  const {
    data: catalogue,
    isLoading: catalogueLoading,
    isError: catalogueError,
  } = useQuery({
    queryKey: ["catalogue-recommendations", profile?.preferences?.shop_for, profile?.updated_at],
    queryFn: getCatalogueRecommendations,
    enabled: Boolean(profile),
  });

  const { data: productFeedback = [] } = useQuery({ queryKey: ["product-feedback"], queryFn: getProductFeedback });
  const recordFeedback = async (id: string, sentiment: ProductSentiment) => {
    try {
      await saveProductFeedback(id, sentiment);
      setFeedbackError(null);
      await Promise.all([queryClient.invalidateQueries({ queryKey: ["product-feedback"] }), queryClient.invalidateQueries({ queryKey: ["catalogue-recommendations"] }), queryClient.invalidateQueries({ queryKey: ["catalogue-search"] })]);
    } catch (e) { setFeedbackError(e instanceof Error ? e.message : "Could not save feedback"); }
  };

  const prefs = profile?.preferences;
  const preferredIds = prefs?.preferred_retailers ?? DEFAULT_RETAILERS;
  const preferred = RETAILERS.filter((r) => preferredIds.includes(r.id));
  const others = RETAILERS.filter((r) => !preferredIds.includes(r.id));
  const bestColour = profile?.skin?.best_accents?.[0]?.name ?? prefs?.preferred_colours?.[0] ?? "";
  const paletteGroups = profile?.skin ? [
    { label: "Best neutrals", colours: profile.skin.best_neutrals ?? [] },
    { label: "Best accents", colours: profile.skin.best_accents ?? [] },
    { label: "Statement colours", colours: profile.skin.statement_colours ?? [] },
  ] : [];
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

  const openTryOn = async (product: ProductRecommendation) => {
    if (!product.image_url || preparingTryOn) return;
    if (completingOutfit.outfitFirstPath && completingOutfit.outfitFirstId) {
      if (product.product_id === completingOutfit.outfitFirstId) {
        setTryOnError("Choose a different second garment.");
        setTryOnErrorProduct(product.product_id);
        return;
      }
      setPreparingTryOn(product.product_id); setTryOnError(null);
      try {
        const second = await prepareCatalogueGarment(product.tryon_product_id || product.product_id);
        router.push({ pathname: "/(tabs)/tryon", params: {
          garmentPath: completingOutfit.outfitFirstPath,
          garmentName: completingOutfit.outfitFirstName || "First garment",
          garmentProductId: completingOutfit.outfitFirstId,
          garmentSizes: completingOutfit.outfitFirstSizes || "[]",
          garmentColours: completingOutfit.outfitFirstColours || "[]",
          secondGarmentPath: second.path, secondGarmentName: second.name,
          secondGarmentProductId: product.product_id,
          secondGarmentSizes: JSON.stringify(product.sizes),
          secondGarmentColours: JSON.stringify(product.colour_names),
        } });
      } catch (e) {
        setTryOnErrorProduct(product.product_id);
        setTryOnError(e instanceof Error ? e.message : "Could not prepare second garment.");
      } finally { setPreparingTryOn(null); }
      return;
    }
    setTryOnErrorProduct(null);
    setPreparingTryOn(product.product_id);
    setTryOnError(null);
    try {
      const garment = await prepareCatalogueGarment(product.tryon_product_id || product.product_id);
      router.push({
        pathname: "/(tabs)/tryon",
        params: {
          garmentPath: garment.path,
          garmentName: garment.name,
          garmentProductId: product.product_id,
          garmentSizes: JSON.stringify(product.sizes),
          garmentColours: JSON.stringify(product.colour_names),
        },
      });
    } catch (error) {
      setTryOnErrorProduct(product.product_id);
      setTryOnError(error instanceof Error ? error.message : "Could not prepare this garment for try-on.");
    } finally {
      setPreparingTryOn(null);
    }
  };

  const openOutfitTryOn = async () => {
    if (outfitItems.length !== 2 || preparingTryOn) return;
    setTryOnErrorProduct(null);
    setPreparingTryOn("outfit");
    setTryOnError(null);
    try {
      const [first, second] = await Promise.all(outfitItems.map((item) => prepareCatalogueGarment(item.tryon_product_id || item.product_id)));
      router.push({
        pathname: "/(tabs)/tryon",
        params: {
          garmentPath: first.path, garmentName: first.name,
          garmentProductId: outfitItems[0].product_id,
          garmentSizes: JSON.stringify(outfitItems[0].sizes),
          garmentColours: JSON.stringify(outfitItems[0].colour_names),
          secondGarmentPath: second.path, secondGarmentName: second.name,
          secondGarmentProductId: outfitItems[1].product_id,
          secondGarmentSizes: JSON.stringify(outfitItems[1].sizes),
          secondGarmentColours: JSON.stringify(outfitItems[1].colour_names),
        },
      });
    } catch (error) {
      setTryOnError(error instanceof Error ? error.message : "Could not prepare your outfit for try-on.");
    } finally {
      setPreparingTryOn(null);
    }
  };

  const toggleOutfitItem = (product: ProductRecommendation) => {
    setOutfitItems((current) => current.some((item) => item.product_id === product.product_id)
      ? current.filter((item) => item.product_id !== product.product_id)
      : current.length < 2 ? [...current, product] : current);
  };

  const addToBag = async (product: ProductRecommendation) => {
    setBagMessageProduct(product.product_id);
    if (product.sizes.length && !selectedSizes[product.product_id]) { setBagMessage("Select a size for " + product.name + " before adding to bag."); return; }
    if (product.colour_names.length && !selectedColours[product.product_id]) { setBagMessage("Select a colour for " + product.name + " before adding to bag."); return; }
    setBagMessage("Adding " + product.name + " to your bag…");
    try {
      await addShoppingBagItem({
        product_id: product.product_id,
        size: selectedSizes[product.product_id] || "",
        colour: selectedColours[product.product_id] || "",
        quantity: 1,
      });
      setBagMessage("Added to your bag. Checkout is not enabled yet.");
      await queryClient.invalidateQueries({ queryKey: ["shopping-bag"] });
    } catch (error) {
      setBagMessage(error instanceof Error ? error.message : "Could not add item.");
    }
  };

  const renderProduct = (product: ProductRecommendation) => (
    <View key={product.product_id} style={styles.productCard}>
      {product.image_url ? <Image source={{ uri: product.image_url }} style={styles.productImage} resizeMode="cover" /> : null}
      <View style={styles.productBody}>
        {demoMode ? <Text style={styles.productMeta}>DEMO PRODUCT · SIMULATED · NOT FOR SALE</Text> : null}
        <Text style={styles.productBrand}>{product.brand || "LUMIÈRE EDIT"}</Text>
        <Text style={styles.productName}>{product.name}</Text>
        {product.colour_names.length ? <Text style={styles.productMeta}>Colour · {product.colour_names.join(", ")}</Text> : null}
        {product.sizes.length ? <Text style={styles.productMeta}>Available in snapshot · {product.sizes.join(", ")}</Text> : null}
        {product.materials.length ? <Text style={styles.productMeta}>{product.materials.join(" · ")}</Text> : null}
        <Text style={styles.price}>{product.price != null ? `${product.currency || "AUD"} ${product.price.toFixed(2)}` : "Price unavailable"}</Text>
        <Text style={styles.productMeta}>{demoMode ? "Synthetic test price in EUR · no brand affiliation or live inventory" : "Supplier catalogue price · stock not verified live"}</Text>
        {!demoMode ? <Text style={styles.productMeta}>Choose size and colour before saving to bag</Text> : null}
        <View style={styles.feedbackRow}>
          {product.sizes.map((size) => (
            <Pressable key={size} onPress={() => setSelectedSizes(v => ({ ...v, [product.product_id]: size }))}
              style={[styles.feedbackButton, selectedSizes[product.product_id] === size && styles.feedbackSelected]}>
              <Text style={styles.feedbackText}>{size}</Text>
            </Pressable>
          ))}
        </View>
        <View style={styles.feedbackRow}>
          {product.colour_names.map((colour) => (
            <Pressable key={colour} onPress={() => setSelectedColours(v => ({ ...v, [product.product_id]: colour }))}
              style={[styles.feedbackButton, selectedColours[product.product_id] === colour && styles.feedbackSelected]}>
              <Text style={styles.feedbackText}>{colour}</Text>
            </Pressable>
          ))}
        </View>
        {!demoMode ? <Pressable accessibilityRole="button" testID={`add-to-bag-${product.product_id}`}
          onPress={() => addToBag(product)} style={styles.tryOnButton}>
          <Feather name="shopping-bag" size={16}/>
          <Text style={styles.tryOnText}>Add to bag</Text>
        </Pressable> : null}
        {bagMessageProduct === product.product_id && bagMessage ? <Text testID={`bag-message-${product.product_id}`} accessibilityRole="alert" style={styles.productMeta}>{bagMessage}</Text> : null}
        <View style={styles.why}>
          <Text style={styles.whyTitle}>WHY THIS SUITS YOU</Text>
          {product.recommendation_reasons.map((reason) => (
            <Text key={reason} style={styles.reason}>• {reason}</Text>
          ))}
        </View>
        {!demoMode ? <View style={styles.feedbackRow}>
          {(["liked", "disliked", "saved", "purchased"] as ProductSentiment[]).map((sentiment) => (
            <Pressable key={sentiment} testID={`feedback-${sentiment}-${product.product_id}`}
              onPress={() => recordFeedback(product.product_id, sentiment)}
              style={[styles.feedbackButton, productFeedback.some((f) => f.product_id === product.product_id && f.sentiment === sentiment) && styles.feedbackSelected]}>
              <Text style={styles.feedbackText}>{sentiment === "purchased" ? "I bought it" : sentiment === "saved" ? "Save" : sentiment === "liked" ? "Like" : "Not for me"}</Text>
            </Pressable>
          ))}
        </View> : null}
        {!demoMode && product.image_url && product.tryon_supported ? (
          <Pressable
            style={styles.tryOnButton}
            onPress={() => openTryOn(product)}
            disabled={preparingTryOn !== null}
          >
            {preparingTryOn === product.product_id ? <ActivityIndicator size="small" /> : <Feather name="zap" size={16} />}
            <Text style={styles.tryOnText}>{preparingTryOn === product.product_id ? "Preparing…" : completingOutfit.outfitFirstId ? "Choose as second garment" : "Try this on (one item)"}</Text>
          </Pressable>
        ) : null}
        {tryOnErrorProduct === product.product_id && tryOnError ? <Text testID={`tryon-error-${product.product_id}`} style={styles.error}>{tryOnError}</Text> : null}
        {!demoMode && product.image_url && product.tryon_supported ? (
          <Pressable testID={`outfit-select-${product.product_id}`} style={styles.outfitSelect} onPress={() => toggleOutfitItem(product)}>
            <Feather name={outfitItems.some((item) => item.product_id === product.product_id) ? "check-square" : "square"} size={17} />
            <Text style={styles.outfitSelectText}>{outfitItems.some((item) => item.product_id === product.product_id) ? "Selected for outfit" : "Add to outfit"}</Text>
          </Pressable>
        ) : null}
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
          {bestColour ? <Text style={styles.body}>{profile?.skin ? `Starting with ${bestColour} and your analysed palette.` : `Starting with ${bestColour}, one of your preferred clothing colours.`}</Text> : null}
          {prefs?.climate === "hot" ? <Text style={styles.reason}>Why: lightweight pieces are prioritised and heavy layers are excluded for hot weather.</Text> : null}
          {profile?.skin ? (
            <View style={styles.paletteSection}>
              <Text style={styles.paletteHeading}>YOUR SAVED COLOUR ANALYSIS</Text>
              <Text style={styles.body}>{profile.skin.undertone?.replace(/_/g, " ")} undertone · {profile.skin.depth} depth · {profile.skin.chroma} chroma · {profile.skin.contrast} contrast</Text>
              {paletteGroups.map((group) => group.colours.length > 0 ? (
                <View key={group.label} style={styles.paletteGroup}>
                  <Text style={styles.paletteLabel}>{group.label}</Text>
                  <View style={styles.swatchRow}>
                    {group.colours.map((colour) => (
                      <View key={colour.name} style={styles.swatchItem}>
                        <View style={[styles.swatch, { backgroundColor: colour.hex }]} />
                        <Text style={styles.swatchName}>{colour.name}</Text>
                      </View>
                    ))}
                  </View>
                </View>
              ) : null)}
              <Text style={styles.paletteNote}>Recommendations use supplier-provided garment colour labels, not independently verified garment-image colours. Palette matching is an estimate, not a guarantee.</Text>
            </View>
          ) : <Text style={styles.body}>Scan your skin tone in You to personalise recommendations using your colour palette.</Text>}
        </View>

        <Text style={styles.section}>CATALOGUE SOURCE</Text>
        <View style={styles.feedbackRow}>
          <Pressable accessibilityRole="button" onPress={() => { setDemoMode(false); setPage(1); }}
            style={[styles.feedbackButton, !demoMode && styles.feedbackSelected]}>
            <Text style={styles.feedbackText}>Supplier catalogue</Text>
          </Pressable>
          <Pressable accessibilityRole="button" onPress={() => { setDemoMode(true); setPage(1); }}
            style={[styles.feedbackButton, demoMode && styles.feedbackSelected]}>
            <Text style={styles.feedbackText}>Demo catalogue · 10,000 garments</Text>
          </Pressable>
        </View>
        {demoMode ? <Text style={styles.note}>SIMULATED TEST DATA ONLY. Brands, inventory, prices and reviews are fictional examples; no affiliation, purchasing or Virtual Try-On. Test images are intentionally hidden.</Text> : null}
        <Text style={styles.section}>FIND YOUR STYLE</Text>
        <View style={styles.card}>
          {([
            ["Search garments", searchText, setSearchText], ["Brand", brandFilter, setBrandFilter],
            ["Category", categoryFilter, setCategoryFilter], ["Colour", colourFilter, setColourFilter],
            ["Size", sizeFilter, setSizeFilter], ["Minimum price", minPrice, setMinPrice],
            ["Maximum price", maxPrice, setMaxPrice],
          ] as [string, string, (value: string) => void][]).map(([label, value, setter]) => (
            <TextInput key={label} accessibilityLabel={label} placeholder={label}
              value={value} onChangeText={(v) => { setter(v); setPage(1); }}
              keyboardType={label.includes("price") ? "decimal-pad" : "default"}
              style={styles.filterInput} />
          ))}
          <Pressable onPress={() => { setSearchText(""); setBrandFilter(""); setCategoryFilter("");
            setColourFilter(""); setSizeFilter(""); setMinPrice(""); setMaxPrice(""); setPage(1); }}>
            <Text style={styles.body}>Clear filters</Text>
          </Pressable>
        </View>
        {completingOutfit.outfitFirstId ? <Text style={styles.note}>Choosing the second garment for {completingOutfit.outfitFirstName || "your outfit"}. Tap “Choose as second garment” on a different item below.</Text> : null}
        {stylistContext ? (
          <View style={styles.info}>
            <Text style={styles.infoTitle}>Shopping your Stylist recommendation</Text>
            <Text style={styles.note}>Starting with the garment type mentioned in your advice. Refine the filters to find suitable products.</Text>
            <Pressable onPress={() => { setStylistContext(""); setSearchText(""); setPage(1); router.setParams({ stylistQuery: "" }); }}>
              <Text style={styles.body}>Clear Stylist search</Text>
            </Pressable>
          </View>
        ) : null}
        <Text style={styles.section}>YOUR LUMIÈRE EDIT</Text>
        <Text style={styles.note}>Shopping bag: {bag?.items.length ?? 0} items saved · Checkout is not yet enabled</Text>
        <Pressable accessibilityRole="button" onPress={() => router.push("/bag" as any)} style={styles.tryOnButton}>
          <Feather name="shopping-bag" size={16} />
          <Text style={styles.tryOnText}>View shopping bag</Text>
        </Pressable>
        {bagMessage ? <Text style={styles.note}>{bagMessage}</Text> : null}
        {!demoMode ? <Text style={styles.note}>For this integration trial, these are genuine catalogue records from the supplied XML snapshot. LUMIÈRE trial prices use a 25% markup on the supplier price; current stock is not claimed live.</Text> : null}
        {searching ? <ActivityIndicator style={styles.loading} /> : null}
        {searchError ? <Text style={styles.error}>{demoMode ? "Demo catalogue search failed. Please check the backend log (.lumiere-dev-logs/backend.log) and ensure the XML file is installed." : "Supplier catalogue search is unavailable. Retailer discovery remains available below."}</Text> : null}
        {demoMode && !searching && !searchError && searchResults?.demo_diagnostics ? (
          <Text style={styles.note}>Demo search: {searchResults.demo_diagnostics.loaded} garments loaded · {searchResults.demo_diagnostics.search_matches} text/filter matches · {searchResults.demo_diagnostics.eligible_after_profile} match your personalisation.</Text>
        ) : null}
        {demoMode && !searching && !searchError && searchResults?.source === "lumiere_demo_xml" && searchResults.total === 0 ? <Text style={styles.note}>No demo results: {!searchResults.demo_diagnostics ? "the backend has not supplied search diagnostics. Restart the old FastAPI process to load the latest code." : searchResults.demo_diagnostics.loaded === 0 ? "the XML is not loaded by the backend" : searchResults.demo_diagnostics.search_matches === 0 ? "no garments match this search; try Sneakers, Navy or Cotton" : "your saved colour, department, category or budget preferences exclude these results."}</Text> : null}
        {!searching && !searchError && shownProducts.length === 0 ? (
          <View style={styles.info}>
            <Text style={styles.infoTitle}>No suitable products found yet</Text>
            <Text style={styles.body}>LUMIÈRE couldn't find products in the current trial catalogue that meet your colour profile and shopping preferences. We won't recommend unsuitable colours just to fill your results. You can explore your preferred retailers below.</Text>
          </View>
        ) : null}
        {outfitItems.length > 0 ? (
          <View style={styles.outfitBar}>
            <Text style={styles.body}>{outfitItems.length}/2 garments selected for one try-on</Text>
            <Text style={styles.note}>{outfitItems.map((item) => item.name).join(" + ")}</Text>
            <Pressable testID="try-on-outfit-button" style={[styles.tryOnButton, outfitItems.length !== 2 && { opacity: 0.4 }]} disabled={outfitItems.length !== 2 || !!preparingTryOn} onPress={openOutfitTryOn}>
              {preparingTryOn === "outfit" ? <ActivityIndicator size="small" /> : <Feather name="zap" size={16} />}
              <Text style={styles.tryOnText}>Try both on together</Text>
            </Pressable>
            <Pressable onPress={() => setOutfitItems([])}><Text style={styles.outfitSelectText}>Clear selection</Text></Pressable>
          </View>
        ) : null}
        {tryOnError && !tryOnErrorProduct ? <Text testID="tryon-outfit-error" style={styles.error}>{tryOnError}</Text> : null}
        {feedbackError ? <Text style={styles.error}>{feedbackError}</Text> : null}
        {!searching && !searchError ? (
          <View style={styles.productGrid}>
            {shownProducts.map((product) => (
              <View key={product.product_id} style={{ width: gridColumns === 1 ? "100%" : gridColumns === 2 ? "48%" : "31.5%" }}>
                {renderProduct(product)}
              </View>
            ))}
          </View>
        ) : null}

        {searchResults ? (
          <View style={styles.paginationBar}>
            <Text style={styles.body}>Page {page} · {searchResults.total} matching items (scanned catalogue)</Text>
            <Pressable disabled={page <= 1} onPress={() => setPage((p) => Math.max(1, p - 1))}>
              <Text style={styles.body}>{page > 1 ? "Previous" : ""}</Text>
            </Pressable>
            <Pressable disabled={!searchResults.has_more} onPress={() => setPage((p) => p + 1)}>
              <Text style={styles.body}>{searchResults.has_more ? "Next page →" : ""}</Text>
            </Pressable>
          </View>
        ) : null}
        {demoMode && !searching && !searchError && searchResults ? (
          <View>
            <Text style={styles.section}>COORDINATED DEMO OUTFITS</Text>
            <Text style={styles.note}>Complete looks from the source XML and carefully generated combinations of eligible demo garments. Illustrative only; no photographs, purchasing or Try-On.</Text>
            <Text style={styles.note}>{searchResults.demo_outfits?.length || 0} complete personalised outfits · All prices are simulated EUR amounts</Text>
            <Pressable accessibilityRole="button" onPress={() => setShowOutfitDiagnostics(v => !v)}>
              <Text style={styles.body}>{showOutfitDiagnostics ? "Hide outfit diagnostics" : "Show outfit diagnostics"}</Text>
            </Pressable>
            {showOutfitDiagnostics && (searchResults.demo_outfit_diagnostics ? (
              <Text style={styles.note}>Outfit checks: {searchResults.demo_outfit_diagnostics.xml_outfits} in XML · {searchResults.demo_outfit_diagnostics.complete} complete candidate sets · {searchResults.demo_outfit_diagnostics.colour_eligible} pass exact colours · {searchResults.demo_outfit_diagnostics.season_eligible} match season/climate · {searchResults.demo_outfit_diagnostics.budget_eligible} eligible XML outfits · {searchResults.demo_outfit_diagnostics.generated_combinations ?? 0} generated combinations.</Text>
            ) : <Text style={styles.note}>Outfit diagnostics unavailable; restart FastAPI to load the updated backend.</Text>)}
            {!searchResults.demo_outfits?.length ? <Text style={styles.note}>No complete outfit is currently eligible. The counts above show which rule is removing the combinations.</Text> : null}
            {(searchResults.demo_outfits ?? []).map((outfit) => (
              <View key={outfit.id} style={styles.card}>
                <Text style={styles.cardTitle}>{outfit.title || outfit.id} · {outfit.garments.length} coordinated pieces</Text>
                <Text style={styles.note}>{outfit.origin === "generated" ? "New combination · Demo items only" : "Source XML outfit"}{outfit.occasion ? ` · ${outfit.occasion}` : ""}{outfit.style ? ` · ${outfit.style}` : ""}</Text>
                <Text style={styles.price}>Demo outfit total: {typeof outfit.total_price === "number" && Number.isFinite(outfit.total_price) ? `EUR ${outfit.total_price.toFixed(2)}` : "unavailable until the backend is updated"}</Text>
                <Text style={styles.note}>{outfit.garments.map(g => g.name).join(" · ")}</Text>
                <Pressable accessibilityRole="button" accessibilityLabel={expandedDemoOutfits.includes(outfit.id) ? "Hide outfit details" : "View outfit details"} onPress={() => setExpandedDemoOutfits(current => current.includes(outfit.id) ? current.filter(id => id !== outfit.id) : [...current, outfit.id])}>
                  <Text style={styles.body}>{expandedDemoOutfits.includes(outfit.id) ? "Hide styling details ▲" : "View styling details ▼"}</Text>
                </Pressable>
                {expandedDemoOutfits.includes(outfit.id) ? (
                  <View>
                    {outfit.reason ? <Text style={styles.note}>{outfit.reason}</Text> : null}
                    {outfit.garments.map((garment, index) => (
                  <View key={index} style={{ marginVertical: 7, paddingVertical: 5, borderBottomWidth: 1, borderBottomColor: "rgba(128,128,128,0.18)" }}>
                    <Text style={styles.body}>{index + 1}. {garment.name} · {garment.category || "Garment"}</Text>
                    <Text style={styles.note}>EUR {typeof garment.price === "number" ? garment.price.toFixed(2) : "—"}</Text>
                    <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 4 }}>
                      {garment.colour_names.slice(0, 3).map((colour) => (
                        <Text key={colour} style={[styles.productMeta, { borderWidth: 1, borderColor: "rgba(128,128,128,0.3)", borderRadius: 6, paddingHorizontal: 8, paddingVertical: 3 }]}>{colour}</Text>
                      ))}
                    </View>
                  </View>
                    ))}
                  </View>
                ) : null}
              </View>
            ))}
          </View>
        ) : null}
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
  filterInput: { borderWidth: 1, borderColor: c.border, color: c.onSurface, padding: 12, marginBottom: 8, borderRadius: 4 },
  paginationBar: { flexDirection: "row", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between", gap: 12, paddingVertical: 12 },
  card: { borderWidth: 1, borderColor: c.border, backgroundColor: c.surfaceSecondary, padding: 18, borderRadius: 4 },
  paletteSection: { marginTop: 16, paddingTop: 12, borderTopWidth: 1, borderTopColor: c.border },
  paletteHeading: { fontFamily: fonts.text, fontSize: 11, letterSpacing: 1.2, color: c.muted, marginBottom: 6 },
  paletteGroup: { marginTop: 12 },
  paletteLabel: { fontFamily: fonts.text, fontSize: 12, color: c.onSurface, marginBottom: 6 },
  swatchRow: { flexDirection: "row", flexWrap: "wrap", gap: 10 },
  swatchItem: { alignItems: "center", width: 66 },
  swatch: { width: 30, height: 30, borderRadius: 15, borderWidth: 1, borderColor: c.borderStrong },
  swatchName: { fontFamily: fonts.text, fontSize: 10, textAlign: "center", color: c.onSurfaceTertiary, marginTop: 4 },
  paletteNote: { fontFamily: fonts.text, fontSize: 11, lineHeight: 16, color: c.muted, marginTop: 12 },
  cardTitle: { fontFamily: fonts.display, fontSize: 20, fontWeight: "700", color: c.onSurface, marginBottom: 8 },
  body: { fontFamily: fonts.text, fontSize: 14, lineHeight: 20, color: c.onSurfaceTertiary, marginTop: 4 },
  reason: { fontFamily: fonts.text, fontSize: 13, lineHeight: 19, color: c.onSurface, marginTop: 5 },
  section: { fontFamily: fonts.text, fontSize: 12, letterSpacing: 1.5, color: c.muted, marginTop: 28, marginBottom: 8 },
  note: { fontFamily: fonts.text, fontSize: 12, lineHeight: 18, color: c.muted, marginBottom: 12 },
  loading: { marginVertical: 28 },
  error: { fontFamily: fonts.text, fontSize: 13, lineHeight: 19, color: c.error, marginBottom: 12 },
  outfitBar: { borderWidth: 1, borderColor: c.borderStrong, padding: 16, marginBottom: 16, gap: 8 },
  outfitSelect: { flexDirection: "row", alignItems: "center", gap: 8, marginTop: 12 },
  outfitSelectText: { fontFamily: fonts.text, fontSize: 13, color: c.onSurface },
  feedbackRow: { flexDirection: "row", flexWrap: "wrap", gap: 6, marginTop: 12 },
  feedbackButton: { borderWidth: 1, borderColor: c.border, paddingHorizontal: 8, paddingVertical: 7 },
  feedbackSelected: { backgroundColor: c.surfaceTertiary, borderColor: c.borderStrong },
  feedbackText: { fontFamily: fonts.text, fontSize: 11, color: c.onSurface },
  productGrid: { flexDirection: "row", flexWrap: "wrap", justifyContent: "flex-start", alignItems: "flex-start", columnGap: "2%", rowGap: 16 },
  productCard: { borderWidth: 1, borderColor: c.border, backgroundColor: c.surfaceSecondary, borderRadius: 6, overflow: "hidden", marginBottom: 18 },
  productImage: { width: "100%", aspectRatio: 0.82, backgroundColor: c.surfaceTertiary },
  productBody: { padding: 16 },
  productBrand: { fontFamily: fonts.text, fontSize: 11, letterSpacing: 1.3, color: c.muted, textTransform: "uppercase" },
  productName: { fontFamily: fonts.display, fontSize: 20, fontWeight: "700", color: c.onSurface, marginTop: 5 },
  productMeta: { fontFamily: fonts.text, fontSize: 12, lineHeight: 18, color: c.onSurfaceTertiary, marginTop: 5, textTransform: "capitalize" },
  price: { fontFamily: fonts.text, fontSize: 14, fontWeight: "600", color: c.onSurface, marginTop: 10 },
  why: { marginTop: 14, paddingTop: 12, borderTopWidth: 1, borderTopColor: c.border },
  whyTitle: { fontFamily: fonts.text, fontSize: 10, letterSpacing: 1.2, color: c.muted },
  tryOnButton: { marginTop: 14, height: 46, borderWidth: 1, borderColor: c.borderStrong, borderRadius: 4, flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8 },
  tryOnText: { fontFamily: fonts.text, fontSize: 14, fontWeight: "600", color: c.onSurface },
  retailer: { flexDirection: "row", alignItems: "center", gap: 12, borderBottomWidth: 1, borderBottomColor: c.border, paddingVertical: 16 },
  retailerName: { fontFamily: fonts.text, fontSize: 16, fontWeight: "600", color: c.onSurface },
  retailerMeta: { fontFamily: fonts.text, fontSize: 12, color: c.muted, marginTop: 3, textTransform: "capitalize" },
  info: { marginTop: 8, padding: 16, backgroundColor: c.surfaceTertiary, borderRadius: 4 },
  infoTitle: { fontFamily: fonts.text, fontSize: 14, fontWeight: "600", color: c.onSurface },
}));
