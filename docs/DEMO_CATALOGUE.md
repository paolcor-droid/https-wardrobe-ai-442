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
