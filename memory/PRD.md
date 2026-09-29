# StyleScan (Wardrobe AI) — PRD

## Original Problem Statement
User wanted to import an existing GitHub repo (paolcor-droid/https-wardrobe-ai-442, branch stylescan-v2-merge) to continue work. The repo never imported into the workspace (only the blank starter template was present), so the user could not update existing code. User then requested: "Add the Claude AI Models integration to my app."

User choices (gathered):
- Claude acts as a general chat assistant AND a wardrobe/outfit styling advisor
- Model: Claude Sonnet 5
- Chat history saved between sessions
- Use built-in Emergent Universal LLM key

## Architecture
- Frontend: Expo Router (React Native), @tanstack/react-query, react-native-keyboard-controller, expo-blur, expo-linear-gradient, expo-image, expo-haptics, @react-native-vector-icons/feather. Custom fonts Playfair Display + DM Sans (variable TTFs).
- Backend: FastAPI + Motor (MongoDB). Claude Sonnet 5 via emergentintegrations LlmChat, streamed over SSE.
- DB collections: `conversations`, `messages` (uuid string ids, soft-delete via `deleted_at`, `_id` excluded).

## User Personas
- Everyday user seeking outfit/styling advice and general chat, wanting to revisit past styling sessions.

## Core Requirements (static)
- Streaming AI chat with a wardrobe stylist persona (Claude Sonnet 5).
- Multi-turn conversation memory within a session.
- Persistent conversation history, viewable and reopenable.
- Editorial, high-fashion visual design (light + dark theme tokens).

## Implemented (2026-09-29)
- Backend endpoints: POST /api/conversations, GET /api/conversations, GET /api/conversations/{id}/messages, POST /api/conversations/{id}/chat (SSE stream), DELETE /api/conversations/{id} (soft delete).
- Streaming Claude Sonnet 5 with seeded history for multi-turn; auto-titles conversation from first message.
- Frontend Chat screen: glass sticky header, editorial empty state (hero + suggestion chips), streaming bubbles, **bold** markdown rendering, keyboard handling, new-chat.
- Frontend History screen: list with relative timestamps, reopen conversation, delete, loading skeletons, empty state.
- System prompt steered away from unsupported markdown (headings/rules/tables).
- Verified: 9/9 backend pytest passing; all frontend flows validated by testing agent.

## Backlog (prioritized)
- P1: Render richer markdown (headings, numbered lists) or keep steering via prompt.
- P2: Swipe-to-delete on history rows; rename conversation title.
- P2: Save favorite outfits / outfit cards; share a styling reply.
- P2: Image input (photograph a garment for advice) via Object Storage.
- P3: Migrate deprecated FastAPI @app.on_event("shutdown") to lifespan handler.

## Next Tasks
- Await user direction on which enhancement to build next.
