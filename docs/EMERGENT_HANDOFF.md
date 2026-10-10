# StyleScan v3 integration handoff

This branch is the consolidated StyleScan development line.

## Preserve
- Emergent UX shell: stylist chat, history, saved looks, sharing, photo picker, object storage, try-on gallery.
- StyleScan intelligence: multidimensional colour analysis, deterministic named palettes, preferences, recommendation scoring/reasons, climate rules and retailer directory.

## Runtime verification
1. Install existing backend/frontend dependencies; do not redesign the application.
2. Run focused Python intelligence tests and existing backend tests.
3. Run TypeScript/Expo checks and fix integration/build errors only.
4. Verify a new selfie fully replaces the previous analysis and produces undertone, depth, chroma, contrast, season, confidence/lighting and named palette groups.
5. Verify liked/avoided colours are mutually exclusive.
6. Verify hot climate excludes heavy layers/jackets by default.
7. Verify Discover clearly distinguishes retailer links from live inventory.
8. Verify Try-On uses the uploaded person and preserves face, visible skin appearance, hair, body proportions, pose, hands, camera angle, lighting and original background while changing only clothing.
9. Do not replace object storage with MongoDB base64 image persistence.

## Commerce integrity
Retailer links are navigation only unless a provider is explicitly connected. Do not fabricate products, prices, stock, sizes, availability, images or URLs. backend/services/catalogue_providers.py is the provider-neutral contract for future verified live catalogue integrations, including Romanelli B2B.

## Branch discipline
Do not overwrite main, stylescan-v2-merge, or emergent-new-build. Make integration fixes on stylescan-v3-integration.
