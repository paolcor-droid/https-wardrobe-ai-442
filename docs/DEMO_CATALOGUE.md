# LUMIÈRE English demo catalogue (testing only)

The user's `catalogue_10k_english.xml` contains 10,000 synthetic garment records and 3,000 coordinated test outfits. All inventory, pricing and brand associations are **fictional**; do not activate checkout or use placeholder images for Virtual Try-On.

## Repository installation

The backend now loads the versioned file from:

`backend/demo-data/demo_catalogue.xml`

For a one-time upload in GitHub Codespaces, put the downloaded English XML into that directory (rename it to `demo_catalogue.xml`). Then run:

```bash
cd /workspaces/https-wardrobe-ai-442
git pull --ff-only origin lumiere-recommendations-v2
mkdir -p backend/demo-data
# Place the downloaded XML at backend/demo-data/demo_catalogue.xml
git add backend/demo-data/demo_catalogue.xml
git commit -m "data(demo): add 10k English synthetic garment catalogue"
git push origin lumiere-recommendations-v2
bash scripts/verify-lumiere.sh
```

The XML is about 38 MB and is below GitHub's 100 MB single-file limit; large XMLs do increase repository size. **The XML has not yet been committed by the assistant**. GitHub's connected text-file editing interface does not accept the local uploaded 38 MB artifact.

After restarting the backend and refreshing Expo, select **Discover → Catalogue Source → Demo catalogue**. The source is isolated from genuine suppliers, hides placeholder photos, and disables bag, feedback and Try-On actions.

If the bundled `backend/demo-data/demo_catalogue.xml` is missing, the old ignored `backend/.lumiere-private-catalogue/demo_catalogue.xml` remains a fallback for existing development setups. Changing XML files does not affect customer data.

The loader accepts the nested `<products><product>...` schema, reads nested composition parts, and omits inactive or fully out-of-stock products. The 3,000 `<outfits>` records are preserved in the XML but are **not yet connected** to outfit recommendations.

Ranking large catalogues can be slower than the 2,000-record trial; test responsiveness and performance before using a larger feed.

## Coordinated outfit preview

The demo search endpoint now reads outfit references from the source XML and displays up to eight text-only matching outfit groupings. These groupings are **not** purchasable, saveable, or valid for photographic Try-On. Only individual products passing the customer's strict personalisation and current search appear as outfit pieces, so a grouping may be partial; this is a preview of the XML outfit relationships, not a complete outfit-availability guarantee. Actual live garment photos are required for Try-On. The XML data is left unchanged.

## Outfit preview v2

The Discover demo cards now use English product-name presentation where supported, source-defined outfit colours, per-garment simulated EUR prices and whole-outfit totals. Outfit previews require **every source outfit item** to survive account eligibility and the active search; season conflicts, hot/cold incompatibility and full-outfit totals above the profile budget are filtered. Results are ordered by the average score of the eligible members. This intentionally may yield fewer or no outfit previews when narrow searches or strict preferences are active. Italian names not yet in the translation map may remain untranslated. No images, checkout or Try-On are enabled.

## Outfit recommendations: category diversity

When several complete outfits meet the customer's existing colour, department, climate and per-garment-budget eligibility rules, Discover now applies a small category-combination diversity penalty during selection of the top eight. This reduces repeated near-identical outfits while preserving the original XML garment associations and exact chosen colours. The outfit diagnostic funnel is available through a Show/Hide control instead of occupying the default shopping view. No supplier, shopping bag, Try-On or payment behaviour changes.

## Generated outfits (development preview)

Discover combines the original XML outfits with bounded three-piece looks assembled from source-backed, active and in-stock synthetic products that already satisfy profile hard filters. The generated combinations use distinct garments in complementary roles (top + bottom + shoes, or dress + layer + shoes when climate permits), never mix exclusive men's and women's departments, and require a qualifying colour for each piece. Season and climate exclusions still apply. Colour harmony uses a simple transparent neutral/accent heuristic; occasion labels are inferred from available garment terms, not third-party occasion certification. These are recommendations, **not** supplier-listed outfit bundles. Generated cards show their provenance; no photo generation, Try-On, purchase or bag features are enabled for demo items. The matching routine is bounded to avoid a full 10,000-product Cartesian search. The standard verification script includes generation, colour and department regression tests.

## Outfit quality update

Generated demo outfits are now classified at the **complete-look** level, rather than assigning an occasion based on the first matching word. The classifier distinguishes casual, hot-weather casual, smart casual, business, formal and evening using combinations of garment types. These are heuristic labels rather than verified dress-code guarantees.

The Discover shortlist also deduplicates visual silhouettes (e.g. two different T-shirts combined with comparable trousers and loafers) along with colour palettes. This can legitimately reduce the number of displayed cards below the maximum of sixteen. Styling copy uses verified selected colours and descriptive footwear classes, not unedited reversed names such as “loafers penny”. All changes remain confined to the demo catalogue; source XML, accounts, saved outfits, checkout and Try-On are unchanged.

## Occasion confidence and translated metadata

Each demo outfit is classified from its whole garment set. A transparent **High / Moderate / Low** confidence label identifies clear evidence versus borderline combinations; it is a rule-based evidence grade, not a calibrated probability. The expanded card reports the evidence and flags differences between source XML occasion labels and garment-derived classifications. The original Italian XML file is unchanged; translated season, occasion and style labels are displayed in English where a verified mapping exists, and original source labels are preserved separately for auditability. Unknown labels are left unchanged rather than guessed.

## Occasion filters and readable titles

Discover now supports client-side occasion chips: All, Casual, Hot-weather casual, Smart casual, Business, Formal and Evening. The chips filter **only** the already-eligible and already-diversified outfit results, so they cannot introduce off-profile, out-of-stock or prohibited products. Empty categories display a helpful empty state instead of expanding the recommendation pool. Repeated occasion/style/season labels are collapsed case-insensitively for display. Monochrome outfits use real garment names in titles instead of generic “coordinated look” wording. No persisted profile settings or source XML are changed.

## Visual outfit preview (Priority 1)

Discover shows a compact tile for every selected demo garment with its name, selected XML colour, illustrative colour swatch and simulated EUR price. Swatches use a fixed display-colour lookup only for known colour labels; unfamiliar colour names receive an explicit “No swatch” placeholder. The tiles are not product photography, AI-generated merchandise, fabric colour verification, stock claims or Try-On output. Existing occasion filters, eligibility and expanded styling explanations are preserved. No new backend, storage, accounts, purchase paths or external image services are introduced.

## Outfit-level palette optimisation

The generated combinations and eligible source XML outfits now evaluate the complete outfit palette, not independent best colours for each garment. A bounded candidate search (up to 16 stocked eligible variants per garment, beam cap 128) preserves all existing colour restrictions, stock checks, per-piece budget and climate gates. Solid identical-colour palettes receive a conservative penalty because differences in texture/shade cannot be verified; coordinated two- or three-colour looks receive a preference, never a guarantee of aesthetic quality. Source XML colour choices remain available but are permitted to change only to stocked profile-eligible variants; substitutions are still tracked. Final diversification disallows repeating a palette or the same clothing-colour/footwear-colour pairing; if available colours are limited, fewer outfits are shown instead of imaginary alternatives.

## Broader candidate exploration and colour diagnostics

Generated outfits now draw from a bounded, distributed sample of the demo catalogue in addition to the XML-referenced garments. Every sampled item passes the existing personalisation and availability gate before any outfit is built. The generator considers up to 48 eligible products per garment role and 96 bounded iterations (two role combinations per iteration) rather than exhaustive Cartesian combinations. A final collection-level ranking penalises reused palettes and dominant colours while preserving silhouette-based diversity and still allowing genuinely different looks in constrained catalogues. Discover's expanded diagnostics show how many sampled products were inspected, eligible product counts by role, and how many eligible in-stock products offer each of the top colour labels. These counts describe the sampled and filtered pool, not the entire supplier market or final unique outfit availability.

## Colour-variety diagnosis and demo-only exploration

The previous colour bottleneck was strict scan/preferred-colour eligibility: a profile with no manually preferred colours could yield only Navy, Camel and Coral. The normal product-ranking and supplier paths remain strict. **Only coordinated demo outfits** now opt into a separate, visibly labelled exploratory-neutral mode for stocked White, Cream, Beige, Sand, Taupe, Grey, Pearl Grey, Charcoal, Brown, Tan and Olive. These are styling experiments, NOT verified scan-compatible colours or updates to the saved palette. Explicitly avoided colours are still rejected **per colour variant**, and no variant is invented. Per-garment budget, department, availability, season, occasion and diversity checks remain in force. A product with an avoided colour and a different acceptable in-stock variant can use only the acceptable variant; no purchase or Try-On is enabled. Explore-mode provenance is labelled in outfit copy and preview. Manual review of colour suitability is required before promoting any new colour to the verified palette.

## Tonal colour compatibility and garment illustrations

The outfit harmony heuristic now considers explicit garment-colour names by light/mid/dark tone, rewards legible light–dark contrast and restrained two- or three-colour arrangements, and penalises identical colour names and competing saturated accents from unrelated families. This is an explainable styling aid, not camera-calibrated colour measurement or evidence of fabric hue, texture or visual fit. The existing complete-outfit colour eligibility and individual product restrictions still apply.

The Discover demo outfit tiles now display generic category pictograms (top, trousers, dress, coat or shoe) over indicative selected-colour swatches, using only garment names and categories. They are **not** actual item photography, and a pictogram is **not** evidence of style, gender, fit, silhouette or selected variant. No external images, image URLs, photo storage, product claims, supplier operations, checkout or Try-On were introduced. Verified real-product imagery still requires an authoritative per-variant image source and validation before display.

## Colour-matched silhouettes and compact cards

Discover now uses dependency-free React Native geometric garment silhouettes instead of OS-coloured emoji. These are simplistic category representations coloured with the *selected, stocked colour label's indicative swatch*. Garment silhouettes, fabric hues and variants are not verified product photographs. Cards present short compact garment tiles with responsive wrapping; outfit titles list actual selected colour + garment name for each piece. No new external image links, supplier product photographs, storage, checkout, or Try-On actions were introduced. Real photograph integration is intentionally deferred until variant-specific authoritative imagery is available and verified.

## Editorial demo cards (visual revision)

After visual review, the geometric silhouettes were removed from Discover because they resembled neither the real garment nor the intended polished experience. Cards now use compact, source-labelled colour strips and concise occasion/palette headings, with garment names and prices beneath. The earlier silhouette component remains unused as a historical development asset; it is not rendered. Images remain deferred until genuine variant-matched supplier photographs can be verified. Backend styling, stored profiles and demo eligibility are unchanged.

## Curated representative photography (limited initial integration)

Discover can display **representative style-inspiration photographs**, never alleged photos of a synthetic demo SKU. The curated image manifest `frontend/src/demo-inspiration-images.ts` specifies exact source page, creator, licence and supported garment + colour categories. Initial matches are White Oxford/button-down shirt (Wikimedia Commons, `Button up (Unsplash).jpg`, michael m_minimal, CC0) and beige/sand chino trousers (Wikimedia Commons, `Chino pants.jpg`, Kuha455405, CC BY-SA 3.0). Each image tile is explicitly marked as representative and links its source/credit; the adjacent swatch communicates the **actual selected demo variant colour**. No image is used where its depicted garment/colour lacks a suitably reviewed match (e.g. navy loafers or cream chinos); those still use swatches. Images are remote Wikimedia file references, may fail offline or if hotlink permissions change, and are not bundled assets or validated supplier images. Full photo coverage requires further manual visual/licence review before expanding the manifest. Do not populate this manifest with supplier image URLs or unverified random image search results.

## Unified Discover card refinement

Individual demo product cards now use a consistent preview area made of available source-colour swatches; long styling explanations, size/colour selector chips and variant caveats are available under a user-controlled details toggle. Neither a palette match for one source-colour variant nor the presence of multiple colours is interpreted as a verified match for all variants. Supplier-product actions are unchanged. Coordinated outfit tiles display equal-height representative-photo-or-swatch media regions with licence/source links preserved under expanded outfit details, preventing tall blank image-less cards and overly long on-card attribution. Real-product photo verification remains a later, independent prerequisite.

## Lookbook presentation pass

Discover coordinated outfits now use a centred editorial-width card with compact occasion/palette title, short garment summary, right-aligned simulated total, consistent garment media areas and expandable styling provenance. Individual demo garments show photos **only after an actual matching colour variant is selected** (or when the garment has a single listed colour); otherwise they show a tidy colour sample group instead of implying that one image depicts every variant. Product recommendation explanations remain collapsible. The photo manifest in `frontend/src/demo-inspiration-images.ts` maps garment category + exact named colour family to vetted Wikimedia image sources with creator/licence metadata. It deliberately **does not** fall back to a category-only image in the wrong colour. Added a CC0 white-sneaker example from `Fashion-shoes-white-snickers (23699823403).jpg` by www.Pixel.la Free Stock Photos; the Commons source page is linked in the manifest. Navy loafers and unmatched garments remain colour-only, with no invented variants, product image claims or changes to purchase/Try-On.

## Photography expansion and error handling (2026-10)

The carefully matched Commons manifest now also contains a **White T-shirt** image (`White-tshirt.jpg`, Paulinaela, CC0 1.0) as a distinct T-shirt category, not an Oxford shirt substitute. Its source and licence were reviewed on the Wikimedia file page; the existing white sneakers example is also CC0 as documented. The conservative matcher continues to leave unverified navy loafers, cream chinos, grey shirts and other unmatched colours without photos. All photo tiles use `DemoPhotoTile`: if a remote Commons URL fails to load, the corresponding **actual selected** named-colour swatch replaces it, with an explicit “Photo unavailable” message. This fallback applies to outfit cards and individual product cards when a specifically matched variant is chosen. The design has been reviewed against the user's shared desktop screenshots; direct browser-level interaction in Codespaces and complete visual/licence QA remain necessary. Do not represent illustrative photos as actual demo merchandise.
