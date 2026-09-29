import os
import re
import uuid
import json
import base64
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

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
CHAT_MODEL = ("anthropic", "claude-sonnet-5")
IMAGE_MODEL = ("gemini", "gemini-3.1-flash-image-preview")

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
        timeout=180,
    )
    if resp.status_code == 503:
        _storage_key = None
        key = init_storage()
        resp = requests.put(
            f"{STORAGE_URL}/objects/{path}",
            headers={"X-Storage-Key": key, "Content-Type": content_type},
            data=data,
            timeout=180,
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


def store_bytes(data: bytes, ext: str, content_type: str) -> str:
    path = f"{APP_NAME}/uploads/anon/{uuid.uuid4()}.{ext}"
    result = put_object(path, data, content_type)
    return result["path"]


def image_to_b64(path: str) -> str:
    img_bytes, _ = get_object(path)
    return base64.b64encode(img_bytes).decode("utf-8")


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


class ColorSwatch(BaseModel):
    name: str
    hex: str


class SkinAnalysis(BaseModel):
    undertone: str = ""
    season: Optional[str] = None
    summary: str = ""
    palette: List[ColorSwatch] = []
    avoid: List[ColorSwatch] = []
    image_path: Optional[str] = None
    analyzed_at: Optional[str] = None


class Profile(BaseModel):
    id: str = "default"
    favorite_colors: List[str] = []
    styles: List[str] = []
    sizes: Dict[str, str] = {}
    budget: Optional[str] = None
    notes: str = ""
    skin: Optional[SkinAnalysis] = None
    updated_at: str = Field(default_factory=now_iso)


class TryOn(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    person_image_path: str
    garment_image_path: Optional[str] = None
    garment_prompt: Optional[str] = None
    result_path: str
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


class ProfileUpdate(BaseModel):
    favorite_colors: Optional[List[str]] = None
    styles: Optional[List[str]] = None
    sizes: Optional[Dict[str, str]] = None
    budget: Optional[str] = None
    notes: Optional[str] = None


class SkinAnalysisRequest(BaseModel):
    image_path: str


class TryOnRequest(BaseModel):
    person_image_path: str
    garment_image_path: Optional[str] = None
    garment_prompt: Optional[str] = None


def clean(doc: dict) -> dict:
    doc.pop("_id", None)
    return doc


# ----------------------------- Profile helpers -----------------------------
async def get_or_create_profile() -> dict:
    doc = await db.profiles.find_one({"id": "default"})
    if not doc:
        p = Profile()
        await db.profiles.insert_one(p.dict())
        return p.dict()
    return clean(doc)


def build_system_prompt(profile: Optional[dict]) -> str:
    base = (
        "You are StyleScan, a warm, sharp personal wardrobe and fashion stylist. "
        "You help people build outfits, understand body shape and color palette, "
        "plan capsule wardrobes, pack for trips, and dress for occasions. "
        "When the user shares a photo of a clothing item, describe what you see and give "
        "specific ways to style it. Give confident, specific advice — name garments, colors, "
        "fabrics, and silhouettes. Friendly, editorial tone. "
        "Use short paragraphs and tasteful bullet points (with '- '). "
        "Do not use markdown headings (#), horizontal rules (---), or tables. You may use "
        "**bold** sparingly. Keep replies concise and skimmable on a phone."
    )
    if not profile:
        return base
    facts = []
    if profile.get("favorite_colors"):
        facts.append("Favorite colors: " + ", ".join(profile["favorite_colors"]))
    if profile.get("styles"):
        facts.append("Preferred styles: " + ", ".join(profile["styles"]))
    if profile.get("sizes"):
        sizes = ", ".join(f"{k}: {v}" for k, v in profile["sizes"].items() if v)
        if sizes:
            facts.append("Sizes: " + sizes)
    if profile.get("budget"):
        facts.append("Budget preference: " + profile["budget"])
    if profile.get("notes"):
        facts.append("Notes: " + profile["notes"])
    skin = profile.get("skin")
    if skin and skin.get("undertone"):
        pal = ", ".join(c["name"] for c in skin.get("palette", [])[:8])
        avoid = ", ".join(c["name"] for c in skin.get("avoid", [])[:6])
        line = f"Skin undertone: {skin['undertone']}"
        if skin.get("season"):
            line += f" ({skin['season']})"
        if pal:
            line += f". Best colors: {pal}"
        if avoid:
            line += f". Colors to avoid: {avoid}"
        facts.append(line)
    if not facts:
        return base
    return base + "\n\nPersonalize every answer to this user's profile:\n- " + "\n- ".join(facts)


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
    content_type = file.content_type or "image/jpeg"
    try:
        path = await run_in_threadpool(store_bytes, data, ext, content_type)
    except Exception as e:  # noqa: BLE001
        logger.exception("Upload failed")
        raise HTTPException(status_code=502, detail=f"Upload failed: {e}")
    return {"path": path}


@api_router.get("/files/{path:path}")
async def files(path: str):
    try:
        content, content_type = await run_in_threadpool(get_object, path)
    except Exception:  # noqa: BLE001
        raise HTTPException(status_code=404, detail="File not found")
    return Response(content=content, media_type=content_type)


# ---- Conversations ----
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
    update: Dict[str, Any] = {}
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

    profile = await get_or_create_profile()
    system_prompt = build_system_prompt(profile)

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
    initial_messages = [{"role": "system", "content": system_prompt}]
    for m in prior:
        initial_messages.append({"role": m["role"], "content": m["content"]})

    is_first_message = len(prior) == 0

    image_contents = []
    if req.image_path:
        try:
            b64 = await run_in_threadpool(image_to_b64, req.image_path)
            image_contents = [ImageContent(image_base64=b64)]
        except Exception:  # noqa: BLE001
            logger.exception("Could not load image for vision")

    chat_client = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=conversation_id,
        system_message=system_prompt,
        initial_messages=initial_messages,
    ).with_model(*CHAT_MODEL)

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

        payload = {"done": True, "message_id": assistant_msg.id, "title": update.get("title")}
        yield f"data: {json.dumps(payload)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---- Saved looks ----
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
    docs = await db.saved_looks.find({"deleted_at": None}).sort("created_at", -1).to_list(500)
    return [SavedLook(**clean(d)) for d in docs]


@api_router.delete("/saved/{look_id}")
async def delete_saved(look_id: str):
    result = await db.saved_looks.update_one(
        {"id": look_id, "deleted_at": None}, {"$set": {"deleted_at": now_iso()}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Saved look not found")
    return {"success": True}


# ---- Profile ----
@api_router.get("/profile", response_model=Profile)
async def get_profile():
    doc = await get_or_create_profile()
    return Profile(**doc)


@api_router.put("/profile", response_model=Profile)
async def update_profile(req: ProfileUpdate):
    await get_or_create_profile()
    update: Dict[str, Any] = {"updated_at": now_iso()}
    for field in ("favorite_colors", "styles", "sizes", "budget", "notes"):
        val = getattr(req, field)
        if val is not None:
            update[field] = val
    await db.profiles.update_one({"id": "default"}, {"$set": update})
    doc = await db.profiles.find_one({"id": "default"})
    return Profile(**clean(doc))


def _parse_json_block(text: str) -> dict:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(json)?", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        cleaned = match.group(0)
    return json.loads(cleaned)


@api_router.post("/skin-analysis", response_model=SkinAnalysis)
async def skin_analysis(req: SkinAnalysisRequest):
    if not EMERGENT_LLM_KEY:
        raise HTTPException(status_code=500, detail="LLM key not configured")
    try:
        b64 = await run_in_threadpool(image_to_b64, req.image_path)
    except Exception:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="Could not read image")

    system = (
        "You are a professional color analyst. Analyze the person's skin tone from the selfie "
        "and return ONLY valid JSON (no prose, no code fences) with this exact schema:\n"
        '{"undertone": "warm|cool|neutral|olive", "season": "e.g. Warm Autumn", '
        '"summary": "1-2 warm friendly sentences about their coloring", '
        '"palette": [{"name": "Camel", "hex": "#C19A6B"}], '
        '"avoid": [{"name": "Icy Blue", "hex": "#AFEEEE"}]}\n'
        "Give 8 flattering palette colors and 4 colors to avoid, each with a realistic hex. "
        "If you cannot see a face clearly, still give best-effort neutral guidance."
    )
    llm = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"skin-{uuid.uuid4()}",
        system_message=system,
    ).with_model(*CHAT_MODEL)
    msg = UserMessage(
        text="Analyze my skin tone and give my color palette as JSON.",
        file_contents=[ImageContent(image_base64=b64)],
    )
    try:
        resp = await llm.send_message(msg)
        data = _parse_json_block(resp)
    except Exception:  # noqa: BLE001
        logger.exception("Skin analysis failed")
        raise HTTPException(status_code=502, detail="Analysis failed, please try again")

    analysis = SkinAnalysis(
        undertone=str(data.get("undertone", "")),
        season=data.get("season"),
        summary=str(data.get("summary", "")),
        palette=[ColorSwatch(name=c.get("name", ""), hex=c.get("hex", "#000000")) for c in data.get("palette", [])],
        avoid=[ColorSwatch(name=c.get("name", ""), hex=c.get("hex", "#000000")) for c in data.get("avoid", [])],
        image_path=req.image_path,
        analyzed_at=now_iso(),
    )
    await get_or_create_profile()
    await db.profiles.update_one(
        {"id": "default"}, {"$set": {"skin": analysis.dict(), "updated_at": now_iso()}}
    )
    return analysis


# ---- Virtual try-on ----
@api_router.post("/tryon", response_model=TryOn)
async def create_tryon(req: TryOnRequest):
    if not EMERGENT_LLM_KEY:
        raise HTTPException(status_code=500, detail="LLM key not configured")
    if not req.garment_image_path and not (req.garment_prompt and req.garment_prompt.strip()):
        raise HTTPException(status_code=400, detail="Provide a garment photo or a description")

    try:
        person_b64 = await run_in_threadpool(image_to_b64, req.person_image_path)
    except Exception:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="Could not read your photo")

    file_contents = [ImageContent(image_base64=person_b64)]
    if req.garment_image_path:
        try:
            garment_b64 = await run_in_threadpool(image_to_b64, req.garment_image_path)
            file_contents.append(ImageContent(image_base64=garment_b64))
        except Exception:  # noqa: BLE001
            logger.exception("Could not read garment image")

    if req.garment_image_path:
        prompt = (
            "Take the person in the FIRST image and edit the photo so they are wearing the "
            "clothing item shown in the SECOND image. Keep the person's face, hair, body shape, "
            "skin tone and pose exactly the same. Replace only their outfit with the garment. "
            "Make it photorealistic with natural lighting, full clothing fit, clean background."
        )
    else:
        prompt = (
            f"Edit the photo of this person so they are wearing: {req.garment_prompt}. "
            "Keep their face, hair, body shape, skin tone and pose the same. Photorealistic, "
            "natural lighting, realistic fit."
        )

    llm = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"tryon-{uuid.uuid4()}",
        system_message="You are an expert fashion photo editor.",
    ).with_model(*IMAGE_MODEL).with_params(modalities=["image", "text"])

    msg = UserMessage(text=prompt, file_contents=file_contents)
    try:
        _text, images = await llm.send_message_multimodal_response(msg)
    except Exception as e:  # noqa: BLE001
        logger.exception("Try-on generation failed")
        raise HTTPException(status_code=502, detail=f"Try-on failed: {e}")

    if not images:
        raise HTTPException(status_code=502, detail="No image was generated, please try again")

    img = images[0]
    try:
        result_bytes = base64.b64decode(img["data"])
        mime = img.get("mime_type", "image/png")
        ext = "png" if "png" in mime else "jpg"
        result_path = await run_in_threadpool(store_bytes, result_bytes, ext, mime)
    except Exception as e:  # noqa: BLE001
        logger.exception("Storing try-on result failed")
        raise HTTPException(status_code=502, detail="Could not save the result")

    tryon = TryOn(
        person_image_path=req.person_image_path,
        garment_image_path=req.garment_image_path,
        garment_prompt=req.garment_prompt,
        result_path=result_path,
    )
    await db.tryons.insert_one(tryon.dict())
    return tryon


@api_router.get("/tryons", response_model=List[TryOn])
async def list_tryons():
    docs = await db.tryons.find({"deleted_at": None}).sort("created_at", -1).to_list(300)
    return [TryOn(**clean(d)) for d in docs]


@api_router.delete("/tryons/{tryon_id}")
async def delete_tryon(tryon_id: str):
    result = await db.tryons.update_one(
        {"id": tryon_id, "deleted_at": None}, {"$set": {"deleted_at": now_iso()}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Try-on not found")
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
