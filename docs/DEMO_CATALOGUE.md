# LUMIÈRE Demo Catalogue (private test only)

The uploaded `catalogue_real_brands.xml` is a **synthetic development dataset** (2,000 records, 24 brand labels). It is not genuine inventory. Named labels **do not** imply brand association, product availability, authenticity or permission to sell.

## One-time Codespaces installation

The XML is deliberately NOT checked into GitHub. In the Codespaces VS Code file explorer, upload your `catalogue_real_brands.xml` into `backend/.lumiere-private-catalogue/` and rename it `demo_catalogue.xml`.

Create the destination if necessary:

```bash
mkdir -p /workspaces/https-wardrobe-ai-442/backend/.lumiere-private-catalogue
```

The final absolute path must be:
`/workspaces/https-wardrobe-ai-442/backend/.lumiere-private-catalogue/demo_catalogue.xml`

**Do not upload the demo XML to the supplier collection or commit it to Git.** Its directory is ignored. Any change to the XML is picked up on the next query (based on file modification timestamp).

Restart the backend after pulling the integration and refresh Expo. Open **Discover → Catalogue Source → Demo catalogue**. Use regular filters and personalised ranking. Switch back to **Supplier catalogue** at any time.

Demo browsing is read-only: placeholder Picsum URLs are intentionally suppressed, and demo entries have no Add to Bag, purchasing, supplier checkout, customer feedback, or Virtual Try-On actions. Saved real outfits remain unaffected. Existing recommendation budget fields are applied numerically to EUR demo test values; no currency conversion is implied.

## Validation

From repository root:

```bash
bash scripts/verify-lumiere.sh
```

The adapter reads the local XML safely, excludes inactive and out-of-stock variants, retains gender and category, and reports synthetic product price. This source is separated from real supplier discovery and cannot resolve through the account-owned shopping bag.

The file currently contains 2,000 records, some inactive; the actual visible count also depends on stock, profile filters and budget. Currency amounts and fabric labels are artificial test data. A later performance pass should index or cache ranked products for a larger 10k+ sample, rather than recomputing full candidate ranking for every request.
