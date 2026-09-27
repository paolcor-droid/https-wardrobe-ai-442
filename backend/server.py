from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import json
import base64
import re
import uuid
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Literal

from services.palette_engine import build_palette
from services.recommendation_engine import recommendation_score
from datetime import datetime, timezone
import httpx

from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

EMERGENT_LLM_KEY = os.environ['EMERGENT_LLM_KEY']

app = FastAPI()
api_router = APIRouter(prefix="/api")

USER_ID = "default"  # single-user MVP


# ============= MODELS =============

class ColourSwatch(BaseModel):
    name: str
    hex: str

class AnalysisQuality(BaseModel):
    lighting_quality: Literal["poor", "fair", "good"]
    face_visibility: Literal["poor", "fair", "good"]
    confidence: Literal["low", "medium", "high"]

class SkinTone(BaseModel):
    # Kept under the legacy field name skin_tone for backwards-compatible profile storage.
    undertone: Literal["warm", "neutral_warm", "neutral", "neutral_cool", "cool"]
    depth: Literal["light", "medium", "deep"] = "medium"
    chroma: Literal["muted", "balanced", "clear"] = "balanced"
    contrast: Literal["low", "medium", "high"] = "medium"
    season: str
    palette: List[str] = []
    best_neutrals: List[ColourSwatch] = []
    best_accents: List[ColourSwatch] = []
    statement_colours: List[ColourSwatch] = []
    caution_colours: List[ColourSwatch] = []
    analysis_quality: Optional[AnalysisQuality] = None
    description: str


class Preferences(BaseModel):
    budget_min: int = 0
    budget_max: int = 500
    occasion: str = "casual"
    categories: List[str] = []
    climate: str = "mild"
    style: str = "classic"
    preferred_fit: str = "regular"
    preferred_colours: List[str] = []
    avoided_colours: List[str] = []


class Profile(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = USER_ID
    skin_tone: Optional[SkinTone] = None
    preferences: Optional[Preferences] = None
    body_photo: Optional[str] = None  # base64
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Product(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    brand: str
    category: str  # tops, bottoms, dresses, outerwear, shoes, accessories
    price: float
    image_url: str
    description: str
    colors: List[str]  # hex
    palette_tags: List[str]  # warm, cool, neutral
    occasions: List[str]  # casual, formal, party, work, date


class TryOnResult(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = USER_ID
    product_id: str
    product_name: str
    generated_image: str  # base64
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SkinAnalyzeRequest(BaseModel):
    face_photo: str  # base64


class ProfileUpdateRequest(BaseModel):
    skin_tone: Optional[SkinTone] = None
    preferences: Optional[Preferences] = None
    body_photo: Optional[str] = None


class TryOnRequest(BaseModel):
    product_id: str
    body_photo: str  # base64


# ============= HELPERS =============

def clean_doc(doc: dict) -> dict:
    if doc and "_id" in doc:
        doc.pop("_id")
    return doc


async def fetch_image_base64(url: str) -> str:
    async with httpx.AsyncClient(timeout=20.0) as http_client:
        resp = await http_client.get(url)
        resp.raise_for_status()
        return base64.b64encode(resp.content).decode("utf-8")


# ============= SEED DATA =============

SEED_PRODUCTS = [
    # Tops
    {"name": "Silk Camisole", "brand": "Aurelia", "category": "tops", "price": 89, "image_url": "https://images.unsplash.com/photo-1564557287817-3785e38ec1f5?w=600", "description": "Fluid silk camisole with delicate straps.", "colors": ["#F5E6D3"], "palette_tags": ["warm", "neutral"], "occasions": ["date", "casual"]},
    {"name": "Cotton Poplin Shirt", "brand": "Studio Nord", "category": "tops", "price": 120, "image_url": "https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?w=600", "description": "Crisp white poplin, boxy fit.", "colors": ["#FFFFFF"], "palette_tags": ["cool", "neutral"], "occasions": ["work", "casual"]},
    {"name": "Merino Turtleneck", "brand": "Vela", "category": "tops", "price": 145, "image_url": "https://images.unsplash.com/photo-1520975916090-3105956dac38?w=600", "description": "Fine merino wool in deep camel.", "colors": ["#8B6F47"], "palette_tags": ["warm"], "occasions": ["work", "casual"]},
    {"name": "Cashmere Knit", "brand": "Maison Lys", "category": "tops", "price": 220, "image_url": "https://images.unsplash.com/photo-1620799140408-edc6dcb6d633?w=600", "description": "Featherweight cashmere in oat.", "colors": ["#E8DDC8"], "palette_tags": ["warm", "neutral"], "occasions": ["work", "casual"]},
    {"name": "Linen Blouse", "brand": "Isle", "category": "tops", "price": 98, "image_url": "https://images.unsplash.com/photo-1554568218-0f1715e72254?w=600", "description": "Loose linen blouse, tortoise buttons.", "colors": ["#E4C9A7"], "palette_tags": ["warm"], "occasions": ["casual", "date"]},
    {"name": "Rib Knit Tee", "brand": "Norda", "category": "tops", "price": 65, "image_url": "https://images.unsplash.com/photo-1583744946564-b52ac1c389c8?w=600", "description": "Second-skin ribbed tee.", "colors": ["#1A1A18"], "palette_tags": ["cool", "neutral"], "occasions": ["casual"]},

    # Bottoms
    {"name": "High-Rise Trousers", "brand": "Studio Nord", "category": "bottoms", "price": 165, "image_url": "https://images.unsplash.com/photo-1594633312681-425c7b97ccd1?w=600", "description": "Pleated wool trousers, cropped.", "colors": ["#2C2A26"], "palette_tags": ["cool", "neutral"], "occasions": ["work", "formal"]},
    {"name": "Wide Leg Denim", "brand": "Vela", "category": "bottoms", "price": 135, "image_url": "https://images.unsplash.com/photo-1541099649105-f69ad21f3246?w=600", "description": "Rigid indigo denim, wide leg.", "colors": ["#2E3F5C"], "palette_tags": ["cool"], "occasions": ["casual"]},
    {"name": "Pleated Midi Skirt", "brand": "Aurelia", "category": "bottoms", "price": 178, "image_url": "https://images.unsplash.com/photo-1583496661160-fb5886a13d44?w=600", "description": "Sunray-pleated midi in bronze.", "colors": ["#8C6A3D"], "palette_tags": ["warm"], "occasions": ["date", "work"]},
    {"name": "Tailored Shorts", "brand": "Isle", "category": "bottoms", "price": 92, "image_url": "https://images.unsplash.com/photo-1591195853828-11db59a44f6b?w=600", "description": "High-waist tailored shorts.", "colors": ["#D6C5A8"], "palette_tags": ["warm", "neutral"], "occasions": ["casual"]},
    {"name": "Leather Midi Skirt", "brand": "Maison Lys", "category": "bottoms", "price": 295, "image_url": "https://images.unsplash.com/photo-1594633313593-bab3825d0caf?w=600", "description": "Nappa leather, A-line.", "colors": ["#1A1A18"], "palette_tags": ["cool", "neutral"], "occasions": ["party", "date"]},
    {"name": "Cargo Trouser", "brand": "Norda", "category": "bottoms", "price": 148, "image_url": "https://images.unsplash.com/photo-1624378439575-d8705ad7ae80?w=600", "description": "Utility cargo in sage.", "colors": ["#7A8567"], "palette_tags": ["warm"], "occasions": ["casual"]},

    # Dresses
    {"name": "Bias Slip Dress", "brand": "Aurelia", "category": "dresses", "price": 265, "image_url": "https://images.unsplash.com/photo-1595777457583-95e059d581b8?w=600", "description": "Bias-cut satin slip, champagne.", "colors": ["#E4D2A8"], "palette_tags": ["warm"], "occasions": ["party", "date"]},
    {"name": "Poplin Shirt Dress", "brand": "Studio Nord", "category": "dresses", "price": 195, "image_url": "https://images.unsplash.com/photo-1566174053879-31528523f8ae?w=600", "description": "Cotton poplin, belted.", "colors": ["#FFFFFF"], "palette_tags": ["cool", "neutral"], "occasions": ["work", "casual"]},
    {"name": "Knit Midi Dress", "brand": "Vela", "category": "dresses", "price": 220, "image_url": "https://images.unsplash.com/photo-1585487000160-6ebcfceb0d03?w=600", "description": "Ribbed knit column dress.", "colors": ["#3B2F26"], "palette_tags": ["warm"], "occasions": ["work", "date"]},
    {"name": "Silk Maxi", "brand": "Maison Lys", "category": "dresses", "price": 385, "image_url": "https://images.unsplash.com/photo-1539109136881-3be0616acf4b?w=600", "description": "Floor-sweeping silk maxi.", "colors": ["#8F3D3D"], "palette_tags": ["warm", "cool"], "occasions": ["party", "formal"]},
    {"name": "Linen Sundress", "brand": "Isle", "category": "dresses", "price": 148, "image_url": "https://images.unsplash.com/photo-1502716119720-b23a93e5fe1b?w=600", "description": "Sleeveless linen sundress.", "colors": ["#F1E3DF"], "palette_tags": ["warm", "neutral"], "occasions": ["casual", "date"]},
    {"name": "Tailored Blazer Dress", "brand": "Studio Nord", "category": "dresses", "price": 310, "image_url": "https://images.unsplash.com/photo-1509631179647-0177331693ae?w=600", "description": "Sharp-shoulder blazer dress.", "colors": ["#1A1A18"], "palette_tags": ["cool", "neutral"], "occasions": ["work", "formal"]},

    # Outerwear
    {"name": "Wool Overcoat", "brand": "Maison Lys", "category": "outerwear", "price": 495, "image_url": "https://images.unsplash.com/photo-1544022613-e87ca75a784a?w=600", "description": "Long wool coat in camel.", "colors": ["#B08968"], "palette_tags": ["warm", "neutral"], "occasions": ["work", "formal"]},
    {"name": "Cropped Leather Jacket", "brand": "Norda", "category": "outerwear", "price": 425, "image_url": "https://images.unsplash.com/photo-1551028719-00167b16eac5?w=600", "description": "Biker jacket, black nappa.", "colors": ["#1A1A18"], "palette_tags": ["cool", "neutral"], "occasions": ["party", "casual"]},
    {"name": "Oversized Trench", "brand": "Studio Nord", "category": "outerwear", "price": 385, "image_url": "https://images.unsplash.com/photo-1591047139829-d91aecb6caea?w=600", "description": "Cotton gabardine trench.", "colors": ["#C9AE85"], "palette_tags": ["warm", "neutral"], "occasions": ["work", "casual"]},
    {"name": "Puffer Coat", "brand": "Vela", "category": "outerwear", "price": 340, "image_url": "https://images.unsplash.com/photo-1548126032-079a0fb0099d?w=600", "description": "Quilted down puffer.", "colors": ["#2C3E50"], "palette_tags": ["cool"], "occasions": ["casual"]},
    {"name": "Suede Blouson", "brand": "Aurelia", "category": "outerwear", "price": 465, "image_url": "https://images.unsplash.com/photo-1520975954732-35dd22299614?w=600", "description": "Buttery suede blouson.", "colors": ["#8B6F47"], "palette_tags": ["warm"], "occasions": ["date", "casual"]},
    {"name": "Cape Coat", "brand": "Maison Lys", "category": "outerwear", "price": 520, "image_url": "https://images.unsplash.com/photo-1539533018447-63fcce2678e3?w=600", "description": "Dramatic wool cape.", "colors": ["#3B2F26"], "palette_tags": ["warm", "cool"], "occasions": ["formal", "work"]},

    # Shoes
    {"name": "Leather Loafers", "brand": "Norda", "category": "shoes", "price": 195, "image_url": "https://images.unsplash.com/photo-1533867617858-e7b97e060509?w=600", "description": "Penny loafers in cognac.", "colors": ["#8B4513"], "palette_tags": ["warm"], "occasions": ["work", "casual"]},
    {"name": "Suede Mules", "brand": "Isle", "category": "shoes", "price": 165, "image_url": "https://images.unsplash.com/photo-1543163521-1bf539c55dd2?w=600", "description": "Kitten heel mules.", "colors": ["#1A1A18"], "palette_tags": ["cool", "neutral"], "occasions": ["work", "date"]},
    {"name": "Ankle Boots", "brand": "Studio Nord", "category": "shoes", "price": 245, "image_url": "https://images.unsplash.com/photo-1520639888713-7851133b1ed0?w=600", "description": "Sculpted-heel ankle boots.", "colors": ["#3B2F26"], "palette_tags": ["warm", "cool"], "occasions": ["casual", "work"]},
    {"name": "White Sneakers", "brand": "Vela", "category": "shoes", "price": 148, "image_url": "https://images.unsplash.com/photo-1595950653106-6c9ebd614d3a?w=600", "description": "Minimal leather sneakers.", "colors": ["#FFFFFF"], "palette_tags": ["cool", "neutral"], "occasions": ["casual"]},
    {"name": "Strappy Heels", "brand": "Aurelia", "category": "shoes", "price": 285, "image_url": "https://images.unsplash.com/photo-1543163521-1bf539c55dd2?w=600", "description": "Nude satin evening heels.", "colors": ["#E4C9A7"], "palette_tags": ["warm"], "occasions": ["party", "formal"]},
    {"name": "Chelsea Boots", "brand": "Maison Lys", "category": "shoes", "price": 315, "image_url": "https://images.unsplash.com/photo-1638247025967-b4e38f787b76?w=600", "description": "Black leather Chelsea.", "colors": ["#1A1A18"], "palette_tags": ["cool", "neutral"], "occasions": ["casual", "work"]},

    # Accessories
    {"name": "Structured Tote", "brand": "Maison Lys", "category": "accessories", "price": 385, "image_url": "https://images.unsplash.com/photo-1584917865442-de89df76afd3?w=600", "description": "Grained leather tote.", "colors": ["#8B4513"], "palette_tags": ["warm"], "occasions": ["work"]},
    {"name": "Silk Scarf", "brand": "Aurelia", "category": "accessories", "price": 95, "image_url": "https://images.unsplash.com/photo-1601924582970-9238bcb495d9?w=600", "description": "Printed silk twill scarf.", "colors": ["#8F3D3D"], "palette_tags": ["warm"], "occasions": ["work", "date"]},
    {"name": "Leather Belt", "brand": "Norda", "category": "accessories", "price": 128, "image_url": "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=600", "description": "Vegetable-tanned belt.", "colors": ["#8B6F47"], "palette_tags": ["warm"], "occasions": ["work", "casual"]},
    {"name": "Micro Shoulder Bag", "brand": "Isle", "category": "accessories", "price": 245, "image_url": "https://images.unsplash.com/photo-1590874103328-eac38a683ce7?w=600", "description": "Tiny nappa shoulder bag.", "colors": ["#1A1A18"], "palette_tags": ["cool", "neutral"], "occasions": ["party", "date"]},
    {"name": "Gold Hoops", "brand": "Vela", "category": "accessories", "price": 185, "image_url": "https://images.unsplash.com/photo-1611591437281-460bfbe1220a?w=600", "description": "Vermeil chunky hoops.", "colors": ["#D4AF37"], "palette_tags": ["warm"], "occasions": ["date", "party"]},
    {"name": "Wool Fedora", "brand": "Studio Nord", "category": "accessories", "price": 168, "image_url": "https://images.unsplash.com/photo-1521369909029-2afed882baee?w=600", "description": "Wide-brim fedora in charcoal.", "colors": ["#2C2A26"], "palette_tags": ["cool", "neutral"], "occasions": ["casual", "date"]},
]


# ============= ROUTES =============

@api_router.get("/")
async def root():
    return {"message": "Lumière API"}


@api_router.post("/products/seed")
async def seed_products():
    await db.products.delete_many({})
    products = [Product(**p).model_dump() for p in SEED_PRODUCTS]
    await db.products.insert_many(products)
    return {"seeded": len(products)}


@api_router.get("/products")
async def list_products(
    category: Optional[str] = None,
    occasion: Optional[str] = None,
    budget_max: Optional[float] = None,
    palette: Optional[str] = None,  # warm, cool, neutral
):
    query: dict = {}
    if category and category != "all":
        query["category"] = category
    if occasion:
        query["occasions"] = occasion
    if budget_max:
        query["price"] = {"$lte": budget_max}
    if palette:
        query["palette_tags"] = palette

    docs = await db.products.find(query, {"_id": 0}).to_list(200)
    return docs


@api_router.get("/products/{product_id}")
async def get_product(product_id: str):
    doc = await db.products.find_one({"id": product_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Product not found")
    return doc


@api_router.post("/skin/analyze")
async def analyze_skin(req: SkinAnalyzeRequest):
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"skin-{uuid.uuid4()}",
            system_message=(
                "You are a careful personal-colour analysis assistant. Assess only visible colour relationships in the supplied face photo. "
                "Account for lighting and white-balance uncertainty. Return ONLY JSON; never infer ethnicity, health, age, or identity."
            ),
        ).with_model("gemini", "gemini-2.5-flash")
        msg = UserMessage(
            text=(
                'Assess the visible facial colouring using multiple visible facial areas where possible. Return exactly: '
                '{"undertone":"warm|neutral_warm|neutral|neutral_cool|cool","depth":"light|medium|deep",'
                '"chroma":"muted|balanced|clear","contrast":"low|medium|high","season":"spring|summer|autumn|winter",'
                '"lighting_quality":"poor|fair|good","face_visibility":"poor|fair|good","confidence":"low|medium|high",'
                '"description":"two concise sentences explaining the observed colour relationships and uncertainty"}. '
                "Do not generate a palette; the application constructs it deterministically."
            ),
            file_contents=[ImageContent(req.face_photo)],
        )
        response_text = await chat.send_message(msg)
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", response_text.strip(), flags=re.MULTILINE)
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not match:
            raise ValueError("No JSON object returned by colour analysis")
        data = json.loads(match.group(0))
        palette = build_palette(data["undertone"], data["depth"], data["chroma"], data["contrast"])
        data.update(palette)
        data["palette"] = [x["hex"] for x in palette["best_neutrals"] + palette["best_accents"]]
        data["analysis_quality"] = {
            "lighting_quality": data.pop("lighting_quality"),
            "face_visibility": data.pop("face_visibility"),
            "confidence": data.pop("confidence"),
        }
        return SkinTone(**data)
    except Exception as e:
        logger.error(f"Colour analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Colour analysis failed: {str(e)}")


@api_router.get("/profile")
async def get_profile():
    doc = await db.profiles.find_one({"user_id": USER_ID}, {"_id": 0})
    if not doc:
        return {"user_id": USER_ID, "skin_tone": None, "preferences": None, "body_photo": None}
    # never send body_photo in list responses to save bandwidth — but we do include here
    return doc


@api_router.post("/profile")
async def update_profile(req: ProfileUpdateRequest):
    existing = await db.profiles.find_one({"user_id": USER_ID}, {"_id": 0}) or {"user_id": USER_ID}
    update = {k: v for k, v in req.model_dump().items() if v is not None}
    existing.update(update)
    existing["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.profiles.update_one({"user_id": USER_ID}, {"$set": existing}, upsert=True)
    saved = await db.profiles.find_one({"user_id": USER_ID}, {"_id": 0})
    return clean_doc(saved)


@api_router.post("/tryon")
async def virtual_tryon(req: TryOnRequest):
    product = await db.products.find_one({"id": req.product_id}, {"_id": 0})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    try:
        # Fetch product image and convert to base64
        product_b64 = await fetch_image_base64(product["image_url"])

        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"tryon-{uuid.uuid4()}",
            system_message="You are an expert virtual fashion stylist. Generate realistic try-on images.",
        ).with_model("gemini", "gemini-3.1-flash-image-preview").with_params(modalities=["image", "text"])

        prompt = (
            f"Take the person in the first image and dress them in the {product['category']} "
            f"garment shown in the second image ({product['name']} by {product['brand']}, "
            f"description: {product['description']}). "
            f"Preserve the person's face, visible skin appearance, hair, body proportions, pose, hands, "
            f"camera angle, lighting and original background as faithfully as possible. "
            f"Change only the clothing needed to apply the selected garment. Do not replace the person, "
            f"beautify their face, change their body shape, or move them into a studio setting. "
            f"Produce a photorealistic result consistent with the original photograph."
        )

        msg = UserMessage(
            text=prompt,
            file_contents=[ImageContent(req.body_photo), ImageContent(product_b64)],
        )
        _text, images = await chat.send_message_multimodal_response(msg)

        if not images:
            raise ValueError("No image generated")

        generated_b64 = images[0]["data"]

        result = TryOnResult(
            product_id=req.product_id,
            product_name=product["name"],
            generated_image=generated_b64,
        )
        await db.tryons.insert_one(result.model_dump())
        return {
            "id": result.id,
            "product_id": result.product_id,
            "product_name": result.product_name,
            "generated_image": generated_b64,
            "created_at": result.created_at.isoformat(),
        }
    except Exception as e:
        logger.error(f"Try-on failed: {e}")
        raise HTTPException(status_code=500, detail=f"Try-on failed: {str(e)}")


@api_router.get("/tryon")
async def list_tryons():
    docs = await db.tryons.find({"user_id": USER_ID}, {"_id": 0}).sort("created_at", -1).to_list(50)
    for d in docs:
        if isinstance(d.get("created_at"), datetime):
            d["created_at"] = d["created_at"].isoformat()
    return docs


@api_router.get("/tryon/{tryon_id}")
async def get_tryon(tryon_id: str):
    doc = await db.tryons.find_one({"id": tryon_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Try-on not found")
    if isinstance(doc.get("created_at"), datetime):
        doc["created_at"] = doc["created_at"].isoformat()
    return doc


@api_router.get("/wishlist")
async def get_wishlist():
    doc = await db.wishlists.find_one({"user_id": USER_ID}, {"_id": 0})
    product_ids = doc.get("product_ids", []) if doc else []
    if not product_ids:
        return []
    products = await db.products.find({"id": {"$in": product_ids}}, {"_id": 0}).to_list(200)
    return products


@api_router.post("/wishlist/{product_id}")
async def toggle_wishlist(product_id: str):
    doc = await db.wishlists.find_one({"user_id": USER_ID}, {"_id": 0}) or {"user_id": USER_ID, "product_ids": []}
    ids = doc.get("product_ids", [])
    if product_id in ids:
        ids.remove(product_id)
        action = "removed"
    else:
        ids.append(product_id)
        action = "added"
    await db.wishlists.update_one(
        {"user_id": USER_ID},
        {"$set": {"user_id": USER_ID, "product_ids": ids}},
        upsert=True,
    )
    return {"action": action, "product_ids": ids}


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@app.on_event("startup")
async def startup():
    count = await db.products.count_documents({})
    if count == 0:
        products = [Product(**p).model_dump() for p in SEED_PRODUCTS]
        await db.products.insert_many(products)
        logger.info(f"Auto-seeded {len(products)} products")


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
