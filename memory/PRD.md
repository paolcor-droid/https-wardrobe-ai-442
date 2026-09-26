# Lumière — AI Fashion Shopping App (PRD)

## Vision
A premium, editorial mobile shopping experience that personalizes clothing recommendations by the user's skin-tone/seasonal palette and lets them virtually try on garments from a full-body photo.

## MVP Scope (v1)
- **No auth** — single-user MVP (default user id)
- **AI Skin Analysis** — user uploads a face photo → Gemini 2.5 Flash returns undertone (warm/cool/neutral), season (spring/summer/autumn/winter), 6-color flattering palette, description
- **Preferences intake** — max budget slider, occasion (casual/work/date/party/formal), category multiselect
- **Discover** — 2-column product grid filtered by category + palette (matches user's undertone) + budget + occasion
- **Product detail** — brand, price, palette-match badge, description, occasions
- **Wishlist** — bookmark toggle, dedicated "Saved" tab
- **Virtual Try-On** — user uploads a full-body photo, Nano Banana (gemini-3.1-flash-image-preview) composites the selected garment on their body. Result shown in a split view; history in "Try-On" tab
- **Profile** — palette summary, preferences summary, edit shortcuts

## Tech
- **Backend**: FastAPI + MongoDB (motor), emergentintegrations LlmChat
- **Frontend**: Expo Router 57 (React Native 0.86), TanStack Query, expo-image, expo-image-picker, @react-native-community/slider, Feather icons
- **AI**: Gemini 2.5 Flash for skin analysis, gemini-3.1-flash-image-preview (Nano Banana) for try-on, both via EMERGENT_LLM_KEY
- **Design system**: Editorial Mobile LIGHT — Playfair-like italic display + Satoshi body, terracotta accent `#A85B4B` on paper-white `#FDFBF7`, radius 0, no shadows, generous whitespace

## Data models (MongoDB)
- `profiles` — single doc keyed by `user_id="default"` with `skin_tone`, `preferences`, `body_photo` (base64)
- `products` — 36 seeded items across 6 categories; palette_tags used for undertone matching
- `wishlists` — array of product_ids per user
- `tryons` — history of generated images (base64) with product ref

## API (all under /api)
- `POST /skin/analyze` → SkinTone
- `GET/POST /profile`
- `GET /products` (filters: category, occasion, budget_max, palette)
- `GET /products/{id}`
- `POST /tryon`, `GET /tryon`, `GET /tryon/{id}`
- `GET /wishlist`, `POST /wishlist/{product_id}` (toggle)

## Future enhancements
- Emergent Google Auth + multi-user
- Stripe checkout
- Emergent Object Storage for images (currently base64 in Mongo)
- Save/name outfits, share look-books, follow stylists
- Iterate try-on with different pose/background prompts
