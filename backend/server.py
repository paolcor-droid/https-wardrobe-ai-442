import os
import uuid
import json
import base64
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Optional

import requests
from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse, Response
from starlette.concurrency import run_in_threadpool
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field

from emergentintegrations.llm.chat import (
    LlmChat,
    UserMessage,
    ImageContent,
    TextDelta,
    StreamDone,
)

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")

# ----------------------------- Object storage -----------------------------
STORAGE_BASE = (os.environ.get("INTEGRATION_PROXY_URL") or "").strip() or "https://integrations.emergentagent.com"
STORAGE_URL = STORAGE_BASE.rstrip("/") + "/objstore/api/v1/storage"
APP_NAME = "stylescan"
_storage_key: Optional[str] = None

app = FastAPI()
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_storage() -> str:
    global _storage_key
    if _storage_key:
        return _storage_key
    resp = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": EMERGENT_LLM_KEY}, timeout=30)
    resp.raise_for_status()
    _storage_key = resp.json()["storage_key"]
    return _storage_key


def put_object(path: str, data: bytes, content_type: str) -> dict:
    global _storage_key
    key = init_storage()
    resp = requests.put(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key, "Content-Type": content_type},
        data=data,
        timeout=120,
    )
    if resp.status_code == 503:
        _storage_key = None
        key = init_storage()
        resp = requests.put(
            f"{STORAGE_URL}/objects/{path}",
            headers={"X-Storage-Key": key, "Content-Type": content_type},
            data=data,
            timeout=120,
        )
    resp.raise_for_status()
    return resp.json()


def get_object(path: str) -> tuple[bytes, str]:
    key = init_storage()
    resp = requests.get(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")


STYLIST_SYSTEM_PROMPT = (
    "You are StyleScan, a warm, sharp personal wardrobe and fashion stylist. "
    "You help people build outfits, understand their body shape and color palette, "
    "plan capsule wardrobes, pack for trips, and dress for occasions. "
    "When the user shares a photo of a clothing item, describe what you see and give "
    "specific ways to style it (pieces, colors, footwear, occasions). "
    "You give confident, specific, actionable advice — name garments, colors, fabrics, "
    "and silhouettes rather than vague suggestions. Keep a friendly, editorial tone. "
    "You can also answer general questions helpfully when asked. "
    "Use short paragraphs and tasteful bullet points (with '- ') when listing outfit pieces. "
    "Do not use markdown headings (#), horizontal rules (---), or tables. You may use **bold** "
    "sparingly for emphasis. "
    "Keep replies concise and skimmable on a phone."
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ----------------------------- Models -----------------------------
class Conversation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str = "New styling session"
    pinned: bool = False
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)
    deleted_at: Optional[str] = None


class Message(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    conversation_id: str
    role: str
    content: str
    image_path: Optional[str] = None
    created_at: str = Field(default_factory=now_iso)


class SavedLook(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    message_id: str
    conversation_id: str
    content: str
    created_at: str = Field(default_factory=now_iso)
    deleted_at: Optional[str] = None


class ChatRequest(BaseModel):
    message: str = ""
    image_path: Optional[str] = None


class UpdateConversationRequest(BaseModel):
    title: Optional[str] = None
    pinned: Optional[bool] = None


class SaveLookRequest(BaseModel):
    message_id: str


def clean(doc: dict) -> dict:
    doc.pop("_id", None)
    return doc


# ----------------------------- Routes -----------------------------
@api_router.get("/")
async def root():
    return {"message": "StyleScan API"}


@api_router.post("/upload")
async def upload(file: UploadFile = File(...)):
    data = await file.read()
    ext = (file.filename or "img.jpg").rsplit(".", 1)[-1].lower()
    if ext not in ("jpg", "jpeg", "png", "webp", "heic"):
        ext = "jpg"
    path = f"{APP_NAME}/uploads/anon/{uuid.uuid4()}.{ext}"
    content_type = file.content_type or "image/jpeg"
    try:
        result = await run_in_threadpool(put_object, path, data, content_type)
    except Exception as e:  # noqa: BLE001
        logger.exception("Upload failed")
        raise HTTPException(status_code=502, detail=f"Upload failed: {e}")
    return {"path": result["path"]}


@api_router.get("/files/{path:path}")
async def files(path: str):
    try:
        content, content_type = await run_in_threadpool(get_object, path)
    except Exception:  # noqa: BLE001
        raise HTTPException(status_code=404, detail="File not found")
    return Response(content=content, media_type=content_type)


@api_router.post("/conversations", response_model=Conversation)
async def create_conversation():
    convo = Conversation()
    await db.conversations.insert_one(convo.dict())
    return convo


@api_router.get("/conversations", response_model=List[Conversation])
async def list_conversations():
    docs = (
        await db.conversations.find({"deleted_at": None})
        .sort([("pinned", -1), ("updated_at", -1)])
        .to_list(500)
    )
    return [Conversation(**clean(d)) for d in docs]


@api_router.patch("/conversations/{conversation_id}", response_model=Conversation)
async def update_conversation(conversation_id: str, req: UpdateConversationRequest):
    update = {}
    if req.title is not None:
        title = req.title.strip()
        if title:
            update["title"] = title[:60]
    if req.pinned is not None:
        update["pinned"] = req.pinned
    if not update:
        raise HTTPException(status_code=400, detail="Nothing to update")
    result = await db.conversations.update_one(
        {"id": conversation_id, "deleted_at": None}, {"$set": update}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Conversation not found")
    doc = await db.conversations.find_one({"id": conversation_id})
    return Conversation(**clean(doc))


@api_router.get("/conversations/{conversation_id}/messages", response_model=List[Message])
async def get_messages(conversation_id: str):
    convo = await db.conversations.find_one({"id": conversation_id, "deleted_at": None})
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")
    docs = (
        await db.messages.find({"conversation_id": conversation_id})
        .sort("created_at", 1)
        .to_list(2000)
    )
    return [Message(**clean(d)) for d in docs]


@api_router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    result = await db.conversations.update_one(
        {"id": conversation_id, "deleted_at": None},
        {"$set": {"deleted_at": now_iso()}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"success": True}


@api_router.post("/conversations/{conversation_id}/chat")
async def chat(conversation_id: str, req: ChatRequest):
    convo = await db.conversations.find_one({"id": conversation_id, "deleted_at": None})
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if not EMERGENT_LLM_KEY:
        raise HTTPException(status_code=500, detail="LLM key not configured")

    user_text = req.message.strip()
    if not user_text and not req.image_path:
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    if not user_text and req.image_path:
        user_text = "Here's a clothing item — how should I style it?"

    # Save user message (with optional image)
    user_msg = Message(
        conversation_id=conversation_id,
        role="user",
        content=user_text,
        image_path=req.image_path,
    )
    await db.messages.insert_one(user_msg.dict())

    prior = (
        await db.messages.find(
            {"conversation_id": conversation_id, "id": {"$ne": user_msg.id}}
        )
        .sort("created_at", 1)
        .to_list(2000)
    )
    initial_messages = [{"role": "system", "content": STYLIST_SYSTEM_PROMPT}]
    for m in prior:
        initial_messages.append({"role": m["role"], "content": m["content"]})

    is_first_message = len(prior) == 0

    # Build the user message, attaching the image for vision if present
    image_contents = []
    if req.image_path:
        try:
            img_bytes, _ = await run_in_threadpool(get_object, req.image_path)
            b64 = base64.b64encode(img_bytes).decode("utf-8")
            image_contents = [ImageContent(image_base64=b64)]
        except Exception:  # noqa: BLE001
            logger.exception("Could not load image for vision")

    chat_client = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=conversation_id,
        system_message=STYLIST_SYSTEM_PROMPT,
        initial_messages=initial_messages,
    ).with_model("anthropic", "claude-sonnet-5")

    outgoing = UserMessage(text=user_text, file_contents=image_contents)

    async def event_generator():
        parts: List[str] = []
        try:
            async for event in chat_client.stream_message(outgoing):
                if isinstance(event, TextDelta):
                    parts.append(event.content)
                    yield f"data: {json.dumps({'delta': event.content})}\n\n"
                elif isinstance(event, StreamDone):
                    break
        except Exception as e:  # noqa: BLE001
            logger.exception("Streaming failed")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            return

        full_text = "".join(parts).strip()
        assistant_msg = Message(
            conversation_id=conversation_id, role="assistant", content=full_text
        )
        await db.messages.insert_one(assistant_msg.dict())

        update = {"updated_at": now_iso()}
        if is_first_message:
            title = user_text if len(user_text) <= 48 else user_text[:45] + "..."
            update["title"] = title
        await db.conversations.update_one({"id": conversation_id}, {"$set": update})

        payload = {
            "done": True,
            "message_id": assistant_msg.id,
            "title": update.get("title"),
        }
        yield f"data: {json.dumps(payload)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ----------------------------- Saved looks -----------------------------
@api_router.post("/saved", response_model=SavedLook)
async def save_look(req: SaveLookRequest):
    msg = await db.messages.find_one({"id": req.message_id})
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    existing = await db.saved_looks.find_one({"message_id": req.message_id, "deleted_at": None})
    if existing:
        return SavedLook(**clean(existing))
    look = SavedLook(
        message_id=req.message_id,
        conversation_id=msg["conversation_id"],
        content=msg["content"],
    )
    await db.saved_looks.insert_one(look.dict())
    return look


@api_router.get("/saved", response_model=List[SavedLook])
async def list_saved():
    docs = (
        await db.saved_looks.find({"deleted_at": None})
        .sort("created_at", -1)
        .to_list(500)
    )
    return [SavedLook(**clean(d)) for d in docs]


@api_router.delete("/saved/{look_id}")
async def delete_saved(look_id: str):
    result = await db.saved_looks.update_one(
        {"id": look_id, "deleted_at": None}, {"$set": {"deleted_at": now_iso()}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Saved look not found")
    return {"success": True}


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_storage():
    try:
        await run_in_threadpool(init_storage)
        logger.info("Object storage initialized")
    except Exception:  # noqa: BLE001
        logger.exception("Storage init failed (will retry on first upload)")


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
