# StyleScan (Wardrobe AI) — PRD

## Original Problem Statement
User wanted to continue an existing GitHub repo (never imported; only blank template was present), then requested a Claude AI chat integration, followed by four enhancements: Photo Advice, Outfit Saving, Rename/Pin chats, and Share Look.

User choices:
- Claude = general assistant + wardrobe/outfit stylist; model Claude Sonnet 5; saved history; Emergent Universal LLM key.
- Photo Advice: camera + library.
- Saved Looks: bookmark icon in top bar → Saved screen.
- Share Look: image card on native, text fallback on web.
- Pinned chats float to top with a marker.

## Architecture
- Frontend: Expo Router, @tanstack/react-query, react-native-keyboard-controller, expo-blur, expo-linear-gradient, expo-image, expo-image-picker, react-native-view-shot, expo-sharing, @react-native-vector-icons/feather. Fonts: Playfair Display + DM Sans.
- Backend: FastAPI + Motor (MongoDB). Claude Sonnet 5 via emergentintegrations LlmChat (SSE streaming, vision via ImageContent). Emergent Object Storage for photos.
- DB collections: conversations {id,title,pinned,created_at,updated_at,deleted_at}, messages {id,conversation_id,role,content,image_path,created_at}, saved_looks {id,message_id,conversation_id,content,created_at,deleted_at}. UUID ids, soft-delete, _id excluded.

## User Personas
- Everyday user seeking outfit/styling advice, wants to photograph garments, save favorite tips, revisit and organize sessions, and share looks.

## Core Requirements (static)
- Streaming AI stylist chat (Claude Sonnet 5) with multi-turn memory.
- Photo-based styling advice (camera/library → Object Storage → Claude vision).
- Persistent, organizable conversation history (rename, pin).
- Save favorite replies as outfit cards; share replies as image/text.
- Editorial high-fashion design (light + dark tokens).

## Implemented
- 2026-09-29: Claude Sonnet 5 streaming chat, multi-turn, saved history, editorial UI, History screen (reopen/delete). 9/9 backend tests.
- 2026-09-29: Photo Advice (upload /api/upload, /api/files, vision in chat), Outfit Saving (/api/saved + Saved screen), Rename+Pin (PATCH /api/conversations, pinned-first sort, rename modal), Share Look (ShareLookModal image card + text fallback). Camera/library permission flow with Open Settings fallback. 11/11 backend tests; all frontend flows verified.
- Hero image on empty state swapped to a model photo per user request.

## Backlog (prioritized)
- P2: Stronger pinned affordance (filled vs outline bookmark).
- P2: Attach multiple photos; edit/crop before send.
- P2: Group saved looks into collections/boards.
- P3: Migrate FastAPI @app.on_event to lifespan; pytest fixture cleanup.

## Next Tasks
- Await user direction on next enhancement.
