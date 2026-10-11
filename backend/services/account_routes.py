"""Isolated account API. Legacy endpoints remain blocked from remote traffic.

Account records never adopt the old shared "default" profile automatically.
"""
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, UploadFile, File
from fastapi.responses import Response
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from services.customer_auth import (
    normalize_email, hash_password, verify_password, create_session, token_digest,
)

router = APIRouter(prefix="/api/account", tags=["account"])


class Credentials(BaseModel):
    email: str
    password: str = Field(min_length=12, max_length=1024)


def configure_account_router(db, validate_image, sanitize_image, save_image, read_image):
    async def current_user(authorization: Annotated[str | None, Header()] = None):
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(401, "Authentication required")
        token = authorization[7:]
        if len(token) > 256 or not token:
            raise HTTPException(401, "Invalid session")
        record = await db.customer_sessions.find_one({
            "digest": token_digest(token), "revoked_at": None,
            "expires_at": {"$gt": datetime.now(timezone.utc)},
        })
        if not record:
            raise HTTPException(401, "Session expired or invalid")
        user = await db.customer_accounts.find_one({"id": record["user_id"]})
        if not user:
            raise HTTPException(401, "Account not found")
        return user["id"]

    @router.post("/register", status_code=201)
    async def register(payload: Credentials):
        try:
            email = normalize_email(payload.email)
            password_hash = hash_password(payload.password)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        if await db.customer_accounts.find_one({"email": email}):
            raise HTTPException(409, "Account already exists")
        user_id = str(uuid.uuid4())
        try:
            await db.customer_accounts.insert_one({
                "id": user_id, "email": email, "password_hash": password_hash,
                "created_at": datetime.now(timezone.utc),
            })
        except Exception as exc:
            # Database unique index must also be installed before enabling registration.
            raise HTTPException(409, "Account could not be registered") from exc
        return {"id": user_id, "email": email}

    @router.post("/login")
    async def login(payload: Credentials):
        try:
            email = normalize_email(payload.email)
        except ValueError:
            raise HTTPException(401, "Invalid credentials")
        user = await db.customer_accounts.find_one({"email": email})
        if not user or not verify_password(payload.password, user["password_hash"]):
            raise HTTPException(401, "Invalid credentials")
        token, digest, expiry = create_session()
        await db.customer_sessions.insert_one({
            "digest": digest, "user_id": user["id"], "expires_at": expiry,
            "revoked_at": None,
        })
        return {"access_token": token, "token_type": "bearer", "expires_at": expiry.isoformat()}

    @router.post("/logout")
    async def logout(authorization: Annotated[str | None, Header()] = None, user_id: str = Depends(current_user)):
        await db.customer_sessions.update_one(
            {"digest": token_digest(authorization[7:]), "user_id": user_id},
            {"$set": {"revoked_at": datetime.now(timezone.utc)}},
        )
        return {"success": True}

    @router.get("/me")
    async def me(user_id: str = Depends(current_user)):
        user = await db.customer_accounts.find_one({"id": user_id})
        return {"id": user_id, "email": user["email"]}

    @router.get("/profile")
    async def get_profile(user_id: str = Depends(current_user)):
        record = await db.customer_profiles.find_one({"user_id": user_id}, {"_id": 0})
        return record or {"user_id": user_id, "preferences": {}}

    @router.put("/profile")
    async def put_profile(payload: dict, user_id: str = Depends(current_user)):
        allowed = {key: payload[key] for key in ("preferences", "notes", "favorite_colors", "styles", "sizes") if key in payload}
        await db.customer_profiles.update_one({"user_id": user_id}, {"$set": allowed}, upsert=True)
        return await get_profile(user_id)

    @router.get("/wardrobe")
    async def wardrobe(user_id: str = Depends(current_user)):
        return await db.customer_wardrobe.find({"user_id": user_id, "deleted_at": None}, {"_id": 0}).to_list(200)

    @router.post("/wardrobe", status_code=201)
    async def wardrobe_add(payload: dict, user_id: str = Depends(current_user)):
        name = payload.get("name")
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 120:
            raise HTTPException(422, "Invalid garment name")
        item = {"id": str(uuid.uuid4()), "user_id": user_id, "name": name.strip(),
                "category": str(payload.get("category", "other"))[:40],
                "colour": str(payload.get("colour", ""))[:80], "deleted_at": None}
        await db.customer_wardrobe.insert_one(item)
        item.pop("_id", None)
        return item

    @router.delete("/wardrobe/{item_id}")
    async def wardrobe_delete(item_id: str, user_id: str = Depends(current_user)):
        result = await db.customer_wardrobe.update_one(
            {"id": item_id, "user_id": user_id, "deleted_at": None},
            {"$set": {"deleted_at": datetime.now(timezone.utc)}},
        )
        if not result.matched_count:
            raise HTTPException(404, "Wardrobe item not found")
        return {"success": True}


    @router.post("/photos", status_code=201)
    async def upload_photo(file: UploadFile = File(...), user_id: str = Depends(current_user)):
        raw = await file.read(8 * 1024 * 1024 + 1)
        ext, mime = validate_image(raw, file.content_type or "", file.filename or "")
        try:
            data = await run_in_threadpool(sanitize_image, raw, ext)
            path = await run_in_threadpool(save_image, data, ext, mime)
        except Exception as exc:
            raise HTTPException(502, "Photo storage failed") from exc
        photo_id = str(uuid.uuid4())
        await db.customer_photos.insert_one({
            "id": photo_id, "user_id": user_id, "path": path,
            "content_type": mime, "created_at": datetime.now(timezone.utc),
        })
        return {"id": photo_id}

    @router.get("/photos/{photo_id}")
    async def get_photo(photo_id: str, user_id: str = Depends(current_user)):
        photo = await db.customer_photos.find_one({"id": photo_id, "user_id": user_id})
        if not photo:
            raise HTTPException(404, "Photo not found")
        try:
            data, mime = await run_in_threadpool(read_image, photo["path"])
        except Exception as exc:
            raise HTTPException(404, "Photo unavailable") from exc
        return Response(content=data, media_type=mime, headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'; sandbox",
        })


    @router.put("/feedback/{product_id}")
    async def set_feedback(product_id: str, payload: dict, user_id: str = Depends(current_user)):
        if not 1 <= len(product_id) <= 150 or payload.get("sentiment") not in {
            "liked", "disliked", "saved", "purchased"
        }:
            raise HTTPException(422, "Invalid product feedback")
        await db.customer_feedback.update_one(
            {"user_id": user_id, "product_id": product_id},
            {"$set": {"sentiment": payload["sentiment"], "updated_at": datetime.now(timezone.utc)}},
            upsert=True,
        )
        return {"product_id": product_id, "sentiment": payload["sentiment"]}

    @router.get("/feedback")
    async def feedback(user_id: str = Depends(current_user)):
        records = await db.customer_feedback.find({"user_id": user_id}, {"_id": 0}).to_list(500)
        return [{"product_id": entry["product_id"], "sentiment": entry["sentiment"]} for entry in records]

    return router
