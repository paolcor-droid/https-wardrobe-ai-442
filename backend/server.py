import os
import uuid
import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field

from emergentintegrations.llm.chat import LlmChat, UserMessage, TextDelta, StreamDone

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

# MongoDB connection
mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")

app = FastAPI()
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

STYLIST_SYSTEM_PROMPT = (
    "You are StyleScan, a warm, sharp personal wardrobe and fashion stylist. "
    "You help people build outfits, understand their body shape and color palette, "
    "plan capsule wardrobes, pack for trips, and dress for occasions. "
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
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)
    deleted_at: Optional[str] = None


class Message(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    conversation_id: str
    role: str  # "user" | "assistant"
    content: str
    created_at: str = Field(default_factory=now_iso)


class ChatRequest(BaseModel):
    message: str


def clean(doc: dict) -> dict:
    doc.pop("_id", None)
    return doc


# ----------------------------- Routes -----------------------------
@api_router.get("/")
async def root():
    return {"message": "StyleScan API"}


@api_router.post("/conversations", response_model=Conversation)
async def create_conversation():
    convo = Conversation()
    await db.conversations.insert_one(convo.dict())
    return convo


@api_router.get("/conversations", response_model=List[Conversation])
async def list_conversations():
    docs = (
        await db.conversations.find({"deleted_at": None})
        .sort("updated_at", -1)
        .to_list(500)
    )
    return [Conversation(**clean(d)) for d in docs]


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
    if not user_text:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    # Save user message
    user_msg = Message(conversation_id=conversation_id, role="user", content=user_text)
    await db.messages.insert_one(user_msg.dict())

    # Load prior history (excluding the just-added user message) to seed the model
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

    chat_client = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=conversation_id,
        system_message=STYLIST_SYSTEM_PROMPT,
        initial_messages=initial_messages,
    ).with_model("anthropic", "claude-sonnet-5")

    async def event_generator():
        assistant_text_parts: List[str] = []
        try:
            async for event in chat_client.stream_message(UserMessage(text=user_text)):
                if isinstance(event, TextDelta):
                    assistant_text_parts.append(event.content)
                    yield f"data: {json.dumps({'delta': event.content})}\n\n"
                elif isinstance(event, StreamDone):
                    break
        except Exception as e:  # noqa: BLE001
            logger.exception("Streaming failed")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            return

        full_text = "".join(assistant_text_parts).strip()
        assistant_msg = Message(
            conversation_id=conversation_id, role="assistant", content=full_text
        )
        await db.messages.insert_one(assistant_msg.dict())

        update = {"updated_at": now_iso()}
        if is_first_message:
            title = user_text if len(user_text) <= 48 else user_text[:45] + "..."
            update["title"] = title
        await db.conversations.update_one(
            {"id": conversation_id}, {"$set": update}
        )

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


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
