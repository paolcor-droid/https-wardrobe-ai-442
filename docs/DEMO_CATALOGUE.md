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
