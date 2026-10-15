# LUMIÈRE multi-supplier catalogue — private development

The four-phase groundwork is implemented on the development branch, **not publicly activated**.

1. **Provider mapping:** `scripts/import_supplier_catalogue.py` loads *authorised* supplier CSV/JSON samples using explicit column mappings. Feed contents, credentials and exported snapshots must remain outside Git.
2. **Isolated database:** `supplier_catalogue_v2` is separate from all customer collections. Unique keys are `provider_id + external_id`. Staged products are inactive and unapproved by default.
3. **Discover:** The account-authenticated Discover recommendation service reads active, approved supplier records only when `LUMIERE_SUPPLIER_CATALOGUE_ENABLED=1`. The existing Matterhorn snapshot remains the default. Source-backed is **not** equivalent to live stock.
4. **Sync preparation:** `scripts/sync_supplier_catalogue.py` can stage a local authorised snapshot into Mongo when `LUMIERE_SUPPLIER_IMPORT_ENABLED=1` is explicitly set. It does not poll supplier APIs, schedule any work or activate listings.

## Deployment and licensing gates

- Both environment gates default to **off**.
- Supplier terms must authorise display of product images, commercial prices, and any AI try-on transformations independently.
- No public supplier API keys, scraping, public feed endpoints or live supplier ordering are configured.
- **Do not run import/sync against production** before feed approval, isolating a staging DB and checking catalogues for PII and supplier secrets.
- A scheduled provider sync requires an approved official API/feed URL, documented update cadence, secure credentials, stock-change semantics, retries, alerts, currency/tax/shipping rules, and licence review.
- Import currently supports CSV/JSON, not general-purpose XML. Matterhorn has its own XML importer.
- Current read scan is capped at 5,000 active supplier items; pagination/indexed candidate selection and durable batch reconciliation are required before scaling production.
- Customer Try-On preparation remains restricted to the trusted existing snapshot; imported supplier imagery is **not** passed into AI try-on until rights and image validation are approved.
- GitHub Actions includes synthetic importer and store tests, but passing CI and real integration still require verification.

## Future operational sequence

Obtain official sample feed and written licence → map fields → run offline sample tests → stage in isolated Mongo → approve product rights and business terms → enable privately for internal Discover testing → add licensed, monitored scheduled sync → conduct mobile and security regression tests.
