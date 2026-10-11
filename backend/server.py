import os
import re
import uuid
import json
import base64
import hashlib
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Literal

import requests
from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse, Response
from starlette.concurrency import run_in_threadpool
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field

from services.palette_engine import build_palette, suggested_season
from services.photo_privacy import sanitize_photo
from services.wardrobe_planner import plan_outfits, capsule_plan
from services.catalogue_providers import list_providers, normalize_product
from services.product_recommendations import rank_verified_products, customer_recommendations
from services.matterhorn_trial_snapshot import MATTERHORN_TRIAL_SNAPSHOT

try:
    from emergentintegrations.llm.chat import (
        LlmChat,
        UserMessage,
        ImageContent,
        TextDelta,
        StreamDone,
    )
except ImportError:
    # Local catalogue/profile development does not require the optional AI SDK.
    # AI endpoints remain unavailable until the real integration is installed.
    class _UnavailableAIIntegration:
        def __init__(self, *args, **kwargs):
            raise HTTPException(
                status_code=503,
                detail="AI integration is not configured in this environment",
            )

    LlmChat = UserMessage = ImageContent = _UnavailableAIIntegration

    class TextDelta:
        pass

    class StreamDone:
        pass

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_SKIN_MODEL = os.environ.get("OPENAI_SKIN_MODEL", "gpt-4.1-mini")

# Selectable chat / analysis providers. Claude remains the default so existing
# behaviour is preserved; OpenAI (ChatGPT) is added ALONGSIDE it. The provider is
# chosen per-request via an optional `provider` field (dev/testing selector).
CHAT_MODELS: Dict[str, Dict[str, str]] = {
    "claude": {"provider": "anthropic", "model": "claude-sonnet-5", "label": "Claude (Anthropic)"},
    "openai": {"provider": "openai", "model": "gpt-5.6-sol", "label": "ChatGPT (OpenAI)"},
}
DEFAULT_CHAT_PROVIDER = "claude"
# Backward-compatible default tuple used where no explicit provider is supplied.
CHAT_MODEL = (CHAT_MODELS[DEFAULT_CHAT_PROVIDER]["provider"], CHAT_MODELS[DEFAULT_CHAT_PROVIDER]["model"])
IMAGE_MODEL = ("gemini", "gemini-3.1-flash-image-preview")


def resolve_provider_id(provider: Optional[str]) -> str:
    """Normalise a requested provider id, falling back to the default."""
    key = (provider or DEFAULT_CHAT_PROVIDER).strip().lower()
    return key if key in CHAT_MODELS else DEFAULT_CHAT_PROVIDER


def resolve_chat_model(provider: Optional[str]) -> tuple:
    """Return the (provider, model) tuple for LlmChat.with_model()."""
    entry = CHAT_MODELS[resolve_provider_id(provider)]
    return (entry["provider"], entry["model"])

# ----------------------------- Object storage -----------------------------
STORAGE_BASE = (os.environ.get("INTEGRATION_PROXY_URL") or "").strip() or "https://integrations.emergentagent.com"
STORAGE_URL = STORAGE_BASE.rstrip("/") + "/objstore/api/v1/storage"
APP_NAME = "stylescan"
# Codespaces development uses a local private directory when Emergent is unavailable.
# Production deployments must provide authenticated persistent object storage.
LOCAL_IMAGE_STORAGE = os.environ.get("LUMIERE_LOCAL_IMAGE_STORAGE", "1" if not EMERGENT_LLM_KEY else "0") == "1"
LOCAL_IMAGE_DIR = ROOT_DIR / ".lumiere-private-images"
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
    if path.startswith("local/"):
        if not LOCAL_IMAGE_STORAGE:
            raise ValueError("Local image storage is disabled")
        name = path.removeprefix("local/")
        if not re.fullmatch(r"[0-9a-f]{32}\.(jpg|jpeg|png|webp)", name):
            raise ValueError("Invalid local image path")
        file_path = LOCAL_IMAGE_DIR / name
        mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}[file_path.suffix.lstrip(".")]
        return file_path.read_bytes(), mime
    if not re.fullmatch(r"stylescan/uploads/anon/(?:[0-9a-f]{32}|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\\.(jpg|jpeg|png|webp)", path):
        raise ValueError("Invalid remote image path")
    key = init_storage()
    resp = requests.get(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")


def store_bytes(data: bytes, ext: str, content_type: str) -> str:
    if LOCAL_IMAGE_STORAGE:
        if ext not in ("jpg", "jpeg", "png", "webp"):
            raise ValueError("Local storage supports JPEG, PNG and WebP only")
        if len(data) > 8 * 1024 * 1024:
            raise ValueError("Photograph exceeds 8 MB limit")
        LOCAL_IMAGE_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(LOCAL_IMAGE_DIR, 0o700)
        name = f"{uuid.uuid4().hex}.{ext}"
        target = LOCAL_IMAGE_DIR / name
        with target.open("xb") as output:
            os.chmod(target, 0o600)
            output.write(data)
        return f"local/{name}"
    path = f"{APP_NAME}/uploads/anon/{uuid.uuid4()}.{ext}"
    result = put_object(path, data, content_type)
    return result["path"]


def validate_uploaded_image(data: bytes, content_type: str, filename: str) -> tuple[str, str]:
    """Validate image bytes rather than trusting user-supplied MIME/extension.

    The application stores the original bytes only after Pillow can decode them.
    Reject decompression bombs, malformed files and excessive payload sizes.
    """
    import io
    import warnings
    from PIL import Image, UnidentifiedImageError

    if not data or len(data) > 8 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Photograph must be between 1 byte and 8 MB")
    if content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(status_code=415, detail="Use a JPEG, PNG or WebP photograph")
    accepted = {"JPEG": ("jpg", "image/jpeg"), "PNG": ("png", "image/png"),
                "WEBP": ("webp", "image/webp")}
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as image:
                image.verify()
            with Image.open(io.BytesIO(data)) as image:
                if image.format not in accepted:
                    raise HTTPException(status_code=415, detail="Unsupported image encoding")
                if image.width * image.height > 30_000_000:
                    raise HTTPException(status_code=413, detail="Image dimensions exceed safety limit")
                ext, mime = accepted[image.format]
    except HTTPException:
        raise
    except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombWarning, Image.DecompressionBombError) as exc:
        raise HTTPException(status_code=415, detail="Invalid or unsafe image file") from exc
    if mime != content_type:
        raise HTTPException(status_code=415, detail="Image content does not match declared file type")
    return ext, mime


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


class AnalysisQuality(BaseModel):
    lighting_quality: Literal["poor", "fair", "good"] = "fair"
    face_visibility: Literal["poor", "fair", "good"] = "fair"
    confidence: Literal["low", "medium", "high"] = "medium"


class SkinAnalysis(BaseModel):
    undertone: Literal["warm", "neutral_warm", "neutral", "neutral_cool", "cool"] = "neutral"
    depth: Literal["light", "medium", "deep"] = "medium"
    chroma: Literal["muted", "balanced", "clear"] = "balanced"
    contrast: Literal["low", "medium", "high"] = "medium"
    season: Optional[str] = None
    summary: str = ""
    palette: List[ColorSwatch] = []
    best_neutrals: List[ColorSwatch] = []
    best_accents: List[ColorSwatch] = []
    statement_colours: List[ColorSwatch] = []
    caution_colours: List[ColorSwatch] = []
    analysis_quality: Optional[AnalysisQuality] = None
    analyzed_with: Optional[str] = None  # provider id used for this analysis (e.g. "claude" / "openai")
    image_path: Optional[str] = None
    analyzed_at: Optional[str] = None


class Preferences(BaseModel):
    budget_min: int = 0
    budget_max: int = 500
    occasion: str = "casual"
    categories: List[str] = []
    climate: Literal["hot", "mild", "cold"] = "mild"
    style: str = "classic"
    preferred_fit: str = "regular"
    preferred_colours: List[str] = []
    avoided_colours: List[str] = []
    preferred_retailers: List[str] = ["zara", "hm", "uniqlo"]
    # Catalogue department the customer wants to shop. "all" (default) keeps
    # existing profiles compatible. Never inferred from the selfie.
    shop_for: Literal["mens", "womens", "all"] = "all"


class Profile(BaseModel):
    id: str = "default"
    favorite_colors: List[str] = []
    styles: List[str] = []
    sizes: Dict[str, str] = {}
    budget: Optional[str] = None
    notes: str = ""
    preferences: Preferences = Field(default_factory=Preferences)
    skin: Optional[SkinAnalysis] = None
    updated_at: str = Field(default_factory=now_iso)


class ProductFeedbackInput(BaseModel):
    product_id: str = Field(min_length=1, max_length=150)
    sentiment: Literal["liked", "disliked", "saved", "purchased"]
    # Explicit feedback only; never infer that an outbound retailer click is a purchase.


class OutfitPlanInput(BaseModel):
    occasion: str = Field(default="casual", max_length=80)
    climate: Literal["hot", "mild", "cold"] = "mild"


class PriceWatchInput(BaseModel):
    product_id: str = Field(min_length=1, max_length=150)
    target_price_aud: float = Field(gt=0, le=100000)


class WardrobeItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    category: Literal["top", "bottom", "dress", "outerwear", "shoes", "accessory", "other"] = "other"
    colour: str = ""
    image_path: str
    notes: str = ""
    created_at: str = Field(default_factory=now_iso)
    deleted_at: Optional[str] = None


class WardrobeItemInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    category: Literal["top", "bottom", "dress", "outerwear", "shoes", "accessory", "other"] = "other"
    colour: str = Field(default="", max_length=80)
    image_path: str
    notes: str = Field(default="", max_length=500)


class TryOn(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    person_image_path: str
    garment_image_path: Optional[str] = None
    garment_prompt: Optional[str] = None
    second_garment_image_path: Optional[str] = None
    result_path: str
    created_at: str = Field(default_factory=now_iso)
    deleted_at: Optional[str] = None


class ChatRequest(BaseModel):
    message: str = ""
    image_path: Optional[str] = None
    provider: Optional[str] = None  # "claude" (default) or "openai" — dev/testing selector


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
    preferences: Optional[Preferences] = None


class SkinAnalysisRequest(BaseModel):
    image_path: str
    provider: Optional[str] = None  # "claude" (default) or "openai" — dev/testing selector
    force_refresh: bool = False  # explicitly request a fresh paid AI analysis


class TryOnRequest(BaseModel):
    person_image_path: str
    garment_image_path: Optional[str] = None
    garment_prompt: Optional[str] = None
    second_garment_image_path: Optional[str] = None


class CatalogueProductInput(BaseModel):
    provider_id: str
    external_id: str
    name: str
    source_url: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    description: str = ""
    price: Optional[float] = None
    currency: Optional[str] = None
    image_url: Optional[str] = None
    colour_names: List[str] = []
    sizes: List[str] = []
    materials: List[str] = []
    occasions: List[str] = []
    palette_tags: List[str] = []
    availability: Optional[str] = None


class RecommendationPreviewRequest(BaseModel):
    products: List[CatalogueProductInput]
    limit: int = 20


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
        "You are LUMIÈRE, a warm, sharp personal wardrobe and fashion stylist. "
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
    prefs = profile.get("preferences") or {}
    if prefs:
        facts.append(
            f"Current styling context: {prefs.get('climate', 'mild')} climate; "
            f"{prefs.get('style', 'classic')} style; {prefs.get('occasion', 'casual')} occasion"
        )
        if prefs.get("preferred_colours"):
            facts.append("Preferred clothing colours: " + ", ".join(prefs["preferred_colours"]))
        if prefs.get("avoided_colours"):
            facts.append("Avoided clothing colours: " + ", ".join(prefs["avoided_colours"]))
    skin = profile.get("skin")
    if skin and skin.get("undertone"):
        pal = ", ".join(c["name"] for c in skin.get("palette", [])[:8])
        avoid = ", ".join(c["name"] for c in skin.get("caution_colours", [])[:6])
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


@api_router.get("/catalogue/providers")
async def catalogue_providers():
    """Expose configured shopping sources without implying live inventory access."""
    return {"providers": list_providers(), "live_inventory_enabled": False}


@api_router.post("/catalogue/products/{product_id}/prepare-tryon")
async def prepare_catalogue_tryon(product_id: str):
    """Copy a trusted snapshot garment image into app storage for Try-On.

    The client cannot supply an arbitrary URL: the image URL is resolved only
    from the server-side genuine Matterhorn snapshot.
    """
    raw = next((item for item in MATTERHORN_TRIAL_SNAPSHOT if item["external_id"] == product_id), None)
    if not raw or not raw.get("image_url"):
        raise HTTPException(status_code=404, detail="Catalogue garment image not found")
    try:
        resp = await run_in_threadpool(
            lambda: requests.get(raw["image_url"], timeout=30)
        )
        resp.raise_for_status()
        content_type = resp.headers.get("Content-Type", "image/jpeg").split(";")[0]
        if not content_type.startswith("image/"):
            raise ValueError("Catalogue asset is not an image")
        ext = "png" if "png" in content_type else "webp" if "webp" in content_type else "jpg"
        path = await run_in_threadpool(store_bytes, resp.content, ext, content_type)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Could not prepare catalogue garment for try-on")
        raise HTTPException(status_code=502, detail="Could not prepare this garment for try-on") from exc
    # Return only the LUMIÈRE-hosted copy. The original supplier URL is never
    # exposed to the client; the preview is served via GET /api/files/{path}.
    return {"path": path, "name": raw["name"]}


@api_router.get("/catalogue/recommendations")
async def catalogue_recommendations():
    """Return customer-safe recommendations from the genuine trial snapshot.

    This endpoint exists so the Emergent build can exercise the complete
    personalization UI before a production catalogue sync/API is configured.
    Snapshot stock is historical catalogue data and is never labelled live.
    """
    profile = await get_or_create_profile()
    # Prefer a locally imported genuine XML snapshot; it is not live stock.
    catalogue_path = ROOT_DIR / ".lumiere-private-catalogue" / "matterhorn_products.json"
    raw_products = MATTERHORN_TRIAL_SNAPSHOT
    catalogue_source = "matterhorn_xml_trial_snapshot"
    if catalogue_path.is_file():
        try:
            with catalogue_path.open("r", encoding="utf-8") as handle:
                imported = json.load(handle)
            if isinstance(imported, list):
                raw_products = imported
                catalogue_source = "matterhorn_imported_xml_snapshot"
        except (OSError, ValueError) as exc:
            logger.warning("Could not read imported Matterhorn catalogue: %s", exc)
    normalized = [normalize_product("matterhorn", raw) for raw in raw_products]
    ranked = rank_verified_products(normalized, profile, limit=60)
    recommendations = customer_recommendations(ranked)
    # Explicit feedback refines presentation only after all existing
    # colour, department and other eligibility filters have run.
    feedback_docs = await db.product_feedback.find({"profile_id": "default"}).to_list(500)
    feedback = {x["product_id"]: x["sentiment"] for x in feedback_docs}
    recommendations = [x for x in recommendations if feedback.get(x.get("product_id")) != "disliked"]
    weight = {"purchased": 3, "saved": 2, "liked": 1}
    recommendations.sort(key=lambda x: -weight.get(feedback.get(x.get("product_id")), 0))
    return {
        "recommendations": recommendations,
        "count": len(recommendations),
        "live_inventory_enabled": False,
        "source": catalogue_source,
        "notice": "Trial catalogue snapshot; price and current stock are not claimed live.",
    }


@api_router.post("/catalogue/recommendations/preview")
async def catalogue_recommendations_preview(req: RecommendationPreviewRequest):
    """Rank caller-supplied verified catalogue records against the saved profile.

    This is an integration seam for authorised providers. It does not fetch,
    scrape, fabricate, cache, or claim retailer inventory.
    """
    if req.limit < 1 or req.limit > 100:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 100")

    normalized = []
    for item in req.products:
        raw = item.dict(exclude={"provider_id"})
        try:
            normalized.append(normalize_product(item.provider_id, raw))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    profile = await get_or_create_profile()
    ranked = rank_verified_products(normalized, profile, req.limit)
    return {
        "recommendations": customer_recommendations(ranked),
        "count": len(ranked),
        "live_inventory_enabled": False,
        "source": "caller_supplied_verified_catalogue",
    }


@api_router.get("/models")
async def available_chat_models():
    """List the selectable chat/analysis providers for the dev/testing model selector."""
    return {
        "default": DEFAULT_CHAT_PROVIDER,
        "providers": [
            {"id": pid, "label": entry["label"], "model": entry["model"]}
            for pid, entry in CHAT_MODELS.items()
        ],
    }


@api_router.post("/upload")
async def upload(file: UploadFile = File(...)):
    data = await file.read(8 * 1024 * 1024 + 1)
    ext, content_type = validate_uploaded_image(data, file.content_type or "", file.filename or "")
    try:
        clean_data = await run_in_threadpool(sanitize_photo, data, ext)
        path = await run_in_threadpool(store_bytes, clean_data, ext, content_type)
    except Exception:  # noqa: BLE001
        logger.exception("Upload failed")
        raise HTTPException(status_code=502, detail="Upload failed")
    return {"path": path}


@api_router.get("/files/{path:path}")
async def files(path: str):
    try:
        content, content_type = await run_in_threadpool(get_object, path)
    except Exception:  # noqa: BLE001
        raise HTTPException(status_code=404, detail="File not found")
    return Response(content=content, media_type=content_type, headers={
        "Cache-Control": "private, no-store",
        "X-Content-Type-Options": "nosniff",
        "Content-Security-Policy": "default-src 'none'; sandbox",
    })


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
    ).with_model(*resolve_chat_model(req.provider))

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
            "provider": resolve_provider_id(req.provider),
        }
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
    # Serialize the request (recursively converts nested Pydantic models such as
    # `preferences` into plain dicts so MongoDB/BSON can encode them).
    data = req.dict(exclude_none=True)
    # A colour can never be both preferred and avoided. The UI already prevents
    # this; enforce the same invariant for any direct API caller.
    prefs = data.get("preferences")
    if prefs is not None:
        preferred = prefs.get("preferred_colours") or []
        avoided = set(prefs.get("avoided_colours") or [])
        conflicts = [c for c in preferred if c in avoided]
        if conflicts:
            raise HTTPException(
                status_code=400,
                detail=f"Colours cannot be both preferred and avoided: {', '.join(conflicts)}",
            )
    for field in ("favorite_colors", "styles", "sizes", "budget", "notes", "preferences"):
        if field in data:
            update[field] = data[field]
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


def _openai_skin_vision(image_bytes: bytes, mime_type: str) -> dict:
    """Direct OpenAI vision request. Secret is read only by the backend."""
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY is not configured; restart Codespaces after adding its secret")
    if len(image_bytes) > 8 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Photograph exceeds the 8 MB analysis limit")
    if mime_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(status_code=415, detail="Please upload a JPEG, PNG, or WebP photograph")
    prompt = (
        "Assess visible facial colour relationships for clothing recommendations only. "
        "Ignore clothing and background; consider multiple visible skin regions, hair and eyes "
        "only for contrast. Do not infer identity, ethnicity, age, health, or other sensitive traits. "
        "Evaluate chroma as the clarity versus softness of visible colouring, not clothing saturation. "
        "Evaluate contrast from relative light-dark differences between visible skin, hair and eyes, "
        "not from background or clothing. Use balanced chroma or medium contrast when borderline; "
        "do not overstate certainty. Treat warm indoor lighting and white-balance shifts as uncertainty. "
        "If the face is unclear or lighting makes colour unreliable, mark quality poor and confidence low. "
        "Return a JSON object with exactly these keys: "
        "undertone (warm, neutral_warm, neutral, neutral_cool, cool), "
        "depth (light, medium, deep), chroma (muted, balanced, clear), "
        "contrast (low, medium, high), season (spring, summer, autumn, winter), "
        "lighting_quality (poor, fair, good), face_visibility (poor, fair, good), "
        "confidence (low, medium, high), summary (two concise sentences about observed "
        "colour relationships and uncertainty). No palette."
    )
    payload = {
        "model": OPENAI_SKIN_MODEL,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {
                "url": f"data:{mime_type};base64,{base64.b64encode(image_bytes).decode('ascii')}",
                "detail": "high",
            }},
        ]}],
        "max_completion_tokens": 500,
    }
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
            json=payload,
            timeout=90,
        )
        if response.status_code in (401, 403):
            raise HTTPException(status_code=502, detail="OpenAI API authentication or model access failed")
        if response.status_code == 429:
            raise HTTPException(status_code=503, detail="OpenAI rate limit or API credits reached")
        response.raise_for_status()
        return _parse_json_block(response.json()["choices"][0]["message"]["content"])
    except HTTPException:
        raise
    except (requests.RequestException, KeyError, IndexError, ValueError) as exc:
        logger.warning("OpenAI skin analysis request failed: %s", type(exc).__name__)
        raise HTTPException(status_code=502, detail="OpenAI skin analysis request failed") from exc


@api_router.post("/skin-analysis", response_model=SkinAnalysis)
async def skin_analysis(req: SkinAnalysisRequest):
    direct_openai = req.provider == "openai" or (req.provider is None and bool(OPENAI_API_KEY))
    if not direct_openai and not EMERGENT_LLM_KEY:
        raise HTTPException(status_code=503, detail="No AI provider configured")
    try:
        image_bytes, mime_type = await run_in_threadpool(get_object, req.image_path)
    except Exception:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="Could not read image")
    # Cache by actual image bytes, provider, model and prompt revision (not by file path).
    provider_id = "openai" if direct_openai else resolve_provider_id(req.provider)
    model_id = OPENAI_SKIN_MODEL if direct_openai else resolve_chat_model(req.provider)[1]
    image_hash = hashlib.sha256(image_bytes).hexdigest()
    cache_key = f"skin-v2:{provider_id}:{model_id}:{image_hash}"
    if not req.force_refresh:
        cached = await db.skin_analysis_cache.find_one({"key": cache_key})
        if cached:
            stored = dict(cached["analysis"])
            # Recompute palette in case the deterministic engine was upgraded.
            palette = build_palette(stored["undertone"], stored["depth"], stored["chroma"], stored["contrast"])
            stored.update(
                palette=[*palette["best_neutrals"], *palette["best_accents"]],
                best_neutrals=palette["best_neutrals"],
                best_accents=palette["best_accents"],
                statement_colours=palette["statement_colours"],
                caution_colours=palette["caution_colours"],
                season=suggested_season(stored["undertone"], stored["depth"], stored["chroma"], stored["contrast"]),
                image_path=req.image_path,
            )
            analysis = SkinAnalysis(**stored)
            await get_or_create_profile()
            await db.profiles.update_one(
                {"id": "default"}, {"$set": {"skin": analysis.dict(), "updated_at": now_iso()}}
            )
            return analysis
    b64 = base64.b64encode(image_bytes).decode("ascii")

    if direct_openai:
        data = await run_in_threadpool(_openai_skin_vision, image_bytes, mime_type)
    else:
        data = None

    system = (
        "You are a careful personal-colour analysis assistant. Assess only visible colour "
        "relationships in the supplied face photo. Sample multiple visible facial areas where "
        "possible and account for lighting and white-balance uncertainty. Never infer ethnicity, "
        "health, age, identity, or other sensitive traits. Return ONLY valid JSON."
    )
    if not direct_openai:
        llm = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"skin-{uuid.uuid4()}",
            system_message=system,
        ).with_model(*resolve_chat_model(req.provider))
        msg = UserMessage(
            text=(
                'Return exactly this schema: {"undertone":"warm|neutral_warm|neutral|neutral_cool|cool",'
            '"depth":"light|medium|deep","chroma":"muted|balanced|clear",'
            '"contrast":"low|medium|high","season":"spring|summer|autumn|winter",'
            '"lighting_quality":"poor|fair|good","face_visibility":"poor|fair|good",'
            '"confidence":"low|medium|high","summary":"two concise sentences explaining visible '
            'colour relationships and uncertainty"}. Do not invent a palette; the application '
            'constructs it deterministically.'
        ),
        file_contents=[ImageContent(image_base64=b64)],
    )
    try:
        if not direct_openai:
            resp = await llm.send_message(msg)
            data = _parse_json_block(resp)
        allowed = {
            "undertone": {"warm", "neutral_warm", "neutral", "neutral_cool", "cool"},
            "depth": {"light", "medium", "deep"},
            "chroma": {"muted", "balanced", "clear"},
            "contrast": {"low", "medium", "high"},
        }
        if any(data.get(key) not in choices for key, choices in allowed.items()):
            raise ValueError("AI returned invalid palette dimensions")
        palette = build_palette(
            data["undertone"], data["depth"], data["chroma"], data["contrast"]
        )
    except Exception:  # noqa: BLE001
        logger.exception("Skin analysis failed")
        raise HTTPException(status_code=502, detail="Analysis failed, please try again")

    quality = AnalysisQuality(
        lighting_quality=data.get("lighting_quality", "fair"),
        face_visibility=data.get("face_visibility", "fair"),
        confidence=data.get("confidence", "medium"),
    )
    analysis = SkinAnalysis(
        undertone=data.get("undertone", "neutral"),
        depth=data.get("depth", "medium"),
        chroma=data.get("chroma", "balanced"),
        contrast=data.get("contrast", "medium"),
        season=suggested_season(data["undertone"], data["depth"], data["chroma"], data["contrast"]),
        summary=str(data.get("summary", "")),
        palette=[ColorSwatch(**c) for c in palette["best_neutrals"] + palette["best_accents"]],
        best_neutrals=[ColorSwatch(**c) for c in palette["best_neutrals"]],
        best_accents=[ColorSwatch(**c) for c in palette["best_accents"]],
        statement_colours=[ColorSwatch(**c) for c in palette["statement_colours"]],
        caution_colours=[ColorSwatch(**c) for c in palette["caution_colours"]],
        analysis_quality=quality,
        analyzed_with="openai" if direct_openai else resolve_provider_id(req.provider),
        image_path=req.image_path,
        analyzed_at=now_iso(),
    )
    await get_or_create_profile()
    await db.profiles.update_one(
        {"id": "default"}, {"$set": {"skin": analysis.dict(), "updated_at": now_iso()}}
    )
    await db.skin_analysis_cache.update_one(
        {"key": cache_key},
        {"$set": {"key": cache_key, "analysis": analysis.dict(), "updated_at": now_iso()}},
        upsert=True,
    )
    return analysis

# ---- Explicit recommendation feedback and wardrobe planning ----
@api_router.put("/feedback")
async def record_product_feedback(req: ProductFeedbackInput):
    # Development-only single-profile store. Production requires authenticated
    # per-user ownership and access controls.
    await db.product_feedback.update_one(
        {"profile_id": "default", "product_id": req.product_id},
        {"$set": {"sentiment": req.sentiment, "updated_at": now_iso()}},
        upsert=True,
    )
    return {"product_id": req.product_id, "sentiment": req.sentiment}


@api_router.get("/feedback")
async def list_product_feedback():
    docs = await db.product_feedback.find({"profile_id": "default"}).to_list(500)
    return [{"product_id": x["product_id"], "sentiment": x["sentiment"]} for x in docs]


@api_router.post("/wardrobe/outfits")
async def wardrobe_outfits(req: OutfitPlanInput):
    docs = await db.wardrobe_items.find({"deleted_at": None}).to_list(500)
    return {"outfits": plan_outfits(docs, req.occasion, req.climate),
            "weather_live": False, "notice": "Uses selected climate, not live weather."}


@api_router.post("/wardrobe/capsule")
async def wardrobe_capsule(req: OutfitPlanInput):
    docs = await db.wardrobe_items.find({"deleted_at": None}).to_list(500)
    return capsule_plan(docs, req.occasion, req.climate)


@api_router.get("/subscriptions/config")
async def subscription_config():
    # Never pretend that payment credentials, entitlements or billing webhooks
    # exist when they have not been configured and validated.
    return {
        "billing_enabled": False,
        "provider": None,
        "plans": [],
        "notice": "Subscriptions are unavailable until payment provider, secure accounts, webhook verification and entitlement enforcement are configured.",
    }


@api_router.post("/price-watch")
async def save_price_watch(req: PriceWatchInput):
    # A target-price wishlist only. There is no live feed, scheduler, or
    # notification delivery, so never claim active price-drop alerts.
    await db.price_watches.update_one(
        {"profile_id": "default", "product_id": req.product_id},
        {"$set": {"target_price_aud": req.target_price_aud, "updated_at": now_iso()}},
        upsert=True,
    )
    return {"product_id": req.product_id, "target_price_aud": req.target_price_aud,
            "monitoring_active": False, "notice": "Saved target only; live price alerts are not enabled."}


@api_router.get("/price-watch")
async def list_price_watches():
    docs = await db.price_watches.find({"profile_id": "default"}).to_list(500)
    return [{"product_id": x["product_id"], "target_price_aud": x["target_price_aud"],
             "monitoring_active": False} for x in docs]


# ---- Digital wardrobe (development-only user-uploaded items; authentication pending) ----
@api_router.get("/wardrobe", response_model=List[WardrobeItem])
async def list_wardrobe():
    docs = await db.wardrobe_items.find({"deleted_at": None}).sort("created_at", -1).to_list(500)
    return [WardrobeItem(**clean(doc)) for doc in docs]


@api_router.post("/wardrobe", response_model=WardrobeItem)
async def add_wardrobe_item(req: WardrobeItemInput):
    # The path must refer to an already uploaded application image; never
    # accept arbitrary external URLs or filesystem paths.
    if not (req.image_path.startswith("local/") or req.image_path.startswith(f"{APP_NAME}/uploads/anon/")):
        raise HTTPException(status_code=400, detail="Upload a wardrobe photograph first")
    try:
        await run_in_threadpool(get_object, req.image_path)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="Wardrobe photograph could not be read") from exc
    item = WardrobeItem(**req.dict())
    await db.wardrobe_items.insert_one(item.dict())
    return item


@api_router.delete("/wardrobe/{item_id}")
async def delete_wardrobe_item(item_id: str):
    result = await db.wardrobe_items.update_one(
        {"id": item_id, "deleted_at": None}, {"$set": {"deleted_at": now_iso()}}
    )
    if not result.matched_count:
        raise HTTPException(status_code=404, detail="Wardrobe item not found")
    # Deleting the wardrobe record is not a claim of permanent media erasure:
    # legacy uploads are unowned and can be referenced by try-on/history.
    return {"success": True, "photo_deleted": False,
            "notice": "Wardrobe record removed; media erasure requires authenticated ownership."}


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

    if req.second_garment_image_path:
        if not req.garment_image_path:
            raise HTTPException(status_code=400, detail="Select the first garment before adding a second")
        try:
            second_b64 = await run_in_threadpool(image_to_b64, req.second_garment_image_path)
            file_contents.append(ImageContent(image_base64=second_b64))
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail="Could not read the second garment photo") from exc

    if req.second_garment_image_path:
        prompt = (
            "Create ONE photorealistic outfit try-on. The FIRST image is the person, "
            "the SECOND image is the first garment, and the THIRD image is the second garment. "
            "Dress the person in BOTH garments simultaneously, keeping the exact garment colours, "
            "textures and designs. Do not replace one selected garment with the other. "
            "Preserve the person's face, skin appearance, hair, body proportions, pose, hands, "
            "camera angle, lighting and background. Change only the clothes. "
            "If the garments overlap, layer them naturally. Do not invent additional clothing."
        )
    elif req.garment_image_path:
        prompt = (
            "Take the person in the FIRST image and edit the photo so they are wearing the "
            "clothing item shown in the SECOND image. Preserve the exact person: face, visible skin "
            "appearance, hair, body proportions, pose, hands, camera angle, lighting and original "
            "background. Change only the clothing. Do not beautify the face, reshape the body, "
            "change identity, or move the person to a studio. Make the garment fit photorealistically."
        )
    else:
        prompt = (
            f"Edit the photo of this person so they are wearing: {req.garment_prompt}. "
            "Preserve the exact person's face, visible skin appearance, hair, body proportions, pose, "
            "hands, camera angle, lighting and original background. Change only the clothing; "
            "do not beautify, reshape, change identity, or move them to a studio. Photorealistic fit."
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
        second_garment_image_path=req.second_garment_image_path,
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


# Fail closed for public deployments until real per-user authentication and
# object ownership are implemented. Development mode remains available locally.
@app.middleware("http")
async def block_unauthenticated_public_deployment(request, call_next):
    if (os.environ.get("LUMIERE_PUBLIC_DEPLOYMENT", "0") == "1"
            or os.environ.get("ENVIRONMENT", "").lower() in {"production", "prod"}):
        return Response(
            content=json.dumps({"detail": "Public access disabled until authenticated user isolation is configured"}),
            status_code=503,
            media_type="application/json",
        )
    return await call_next(request)


app.include_router(api_router)

# Explicit trusted origins only. Development clients may be configured via
# LUMIERE_CORS_ORIGINS (comma-separated); never allow wildcard + credentials.
_allowed_origins = [
    origin.strip()
    for origin in os.environ.get(
        "LUMIERE_CORS_ORIGINS",
        "http://localhost:8081,http://127.0.0.1:8081,http://localhost:19006",
    ).split(",")
    if origin.strip() and origin.strip() != "*"
]
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=_allowed_origins,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
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
