# LUMIÈRE Pre-Loved — private pilot

## Product position
The **AI personal fashion stylist stays the primary experience**. Pre-Loved is an optional secondary Discover / My Wardrobe feature. Owned garments are prioritised in outfit suggestions. The marketplace does not make paid orders, transfer money, exchange contact details, or send unsolicited messages.

## What is implemented
- In **My Wardrobe**, choose an existing garment and create a **private listing draft**. Condition, size, asking price (AUD), optional description and willingness to swap are collected. A listing is NOT created on photograph upload.
- An approved pilot can deliberately publish a listing by calling the confirmed publication action. Listing status can be paused or irreversibly withdrawn.
- Published listings expose only an allowlist of garment attributes. **Private photo IDs, image paths, seller account ID, contact details, buyer preferences, and skin-colour assessments are never exposed.** The original private photograph is not copied or published.
- In Discover, users can view anonymous descriptions and **opt in** to private, server-side matching using saved wardrobe, colour scan, style and size. Other users never see this matching information.
- No push notifications: eligible matches appear only in the recipient's own Discover screen. No direct seller/buyer chat is implemented.
- Removing a wardrobe item or its source photograph withdraws attached listings. Account export and deletion include listing data.
- All records stay in account-scoped MongoDB collections. Use synthetic accounts in testing; do not access real customer photos.

## Pilot gate
Set `LUMIERE_PRELOVED_PUBLISH_ENABLED=1` **only** in an explicitly approved test environment after listing moderation and trust processes have been evaluated. The flag is absent/disabled by default; users can still create private drafts.

## Before any public launch
- Moderation queue, report/review/takedown workflows and prohibited items policy.
- Public photo-processing pipeline with **separate consent**, metadata stripping, moderation and revocable copies. Do **not** expose account photo URLs.
- Seller verification where applicable; shipping and collection safety; abuse, fraud and dispute handling.
- Implement authenticated, abuse-resistant messaging and recipient controls **before** contact.
- Verify purchase/payment/refund/tax/shipping legal and provider requirements before enabling checkout.
- Assess cross-border operations separately (Australia and Moldova). This pilot currently supports AUD only, with no shipping promises.
- Privacy review, retention/delete policies, production access controls, rate limits, indexes and load tests.

## Smoke test
1. Create two disposable accounts A and B.
2. A uploads a garment to their private wardrobe, creates a Pre-Loved draft, and verifies B cannot see it.
3. In an approved pilot with the feature flag, A explicitly publishes. B can see only anonymised text.
4. B enables private Pre-Loved matches and receives matching suggestions only in B's account; A cannot access B's scan or wardrobe.
5. B disables matching and no matches are returned.
6. A withdraws the listing or removes the garment; it disappears from B's results.
7. Confirm no payment, order, message, push notification, or publicly accessible private photo was created.

Run `pytest -q backend/tests/test_account_routes.py` from a Python environment with the repository's backend dependencies installed (and `backend` on `PYTHONPATH`).
