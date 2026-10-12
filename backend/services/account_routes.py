"""Isolated account API. Legacy endpoints remain blocked from remote traffic.

Account records never adopt the old shared "default" profile automatically.
"""
import uuid
import os
import secrets
import json
from datetime import datetime, timezone, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, UploadFile, File, Request
from fastapi.responses import Response, StreamingResponse
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from services.wardrobe_planner import plan_outfits, capsule_plan
from services.login_throttle import LoginThrottle
from services.account_recovery import recovery_configured, send_recovery_email
from services.customer_auth import (
    normalize_email, hash_password, verify_password, create_session, token_digest,
)

class PrivateTryOnInput(BaseModel):
    person_photo_id: str
    garment_photo_id: str | None = None
    second_garment_photo_id: str | None = None
    garment_prompt: str | None = Field(default=None, max_length=1000)


class AccountChatInput(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    provider: str | None = None
    image_path: str | None = None


class RecoveryRequest(BaseModel):
    email: str


class RecoveryConfirm(BaseModel):
    token: str = Field(min_length=32, max_length=256)
    password: str = Field(min_length=12, max_length=1024)


class Credentials(BaseModel):
    email: str
    password: str = Field(min_length=12, max_length=1024)


def configure_account_router(db, validate_image, sanitize_image, save_image, read_image, delete_image=None, generate_chat=None, recommend_catalogue=None, generate_tryon=None, analyze_skin=None, prepare_catalogue=None):
    # A fresh router binds each app to its own database and storage callbacks.
    router = APIRouter(prefix="/api/account", tags=["account"])
    COOKIE_NAME = "lumiere_session"
    CSRF_NAME = "lumiere_csrf"
    login_throttle = LoginThrottle()
    recovery_throttle = LoginThrottle(attempts=3, window=3600)

    def browser_session(response, token):
        # Host-only cookies, never shared with unrelated domains.
        # For Codespaces forwarded HTTPS, use Secure even when FastAPI receives HTTP.
        secure = os.environ.get("LUMIERE_WEB_COOKIE_SECURE", "1") != "0"
        response.set_cookie(COOKIE_NAME, token, max_age=86400, httponly=True,
                            secure=secure, samesite="lax", path="/api/account")
        csrf = secrets.token_urlsafe(32)
        # The JS-readable CSRF cookie must be available at the site root.
        response.set_cookie(CSRF_NAME, csrf, max_age=86400, httponly=False,
                            secure=secure, samesite="lax", path="/")
        return csrf

    def clear_browser_session(response):
        response.delete_cookie(COOKIE_NAME, path="/api/account")
        response.delete_cookie(CSRF_NAME, path="/")

    async def current_user(request: Request, authorization: Annotated[str | None, Header()] = None):
        token = None
        if authorization and authorization.startswith("Bearer "):
            token = authorization[7:]
        elif request.cookies.get(COOKIE_NAME):
            token = request.cookies[COOKIE_NAME]
            # Unsafe cookie-authenticated requests require double-submit CSRF.
            if request.method not in ("GET", "HEAD", "OPTIONS"):
                csrf = request.headers.get("X-Lumiere-CSRF", "")
                expected = request.cookies.get(CSRF_NAME, "")
                if not csrf or not expected or not secrets.compare_digest(csrf, expected):
                    raise HTTPException(403, "CSRF verification failed")
                # Deny cross-site form/cors requests even with valid cookies.
                origin = request.headers.get("origin")
                if origin:
                    from urllib.parse import urlsplit
                    host = request.headers.get("host", "")
                    if urlsplit(origin).netloc != host:
                        raise HTTPException(403, "Cross-site request blocked")
        if not token or len(token) > 256:
            raise HTTPException(401, "Authentication required")
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
    async def login(payload: Credentials, request: Request, response: Response):
        try:
            email = normalize_email(payload.email)
        except ValueError:
            raise HTTPException(401, "Invalid credentials")
        # Process-local throttle limits repeated failures in private development.
        # Production requires a shared-store limiter across workers and instances.
        client_ip = request.client.host if request.client else "unknown"
        throttle_key = client_ip + ":" + email
        if login_throttle.is_blocked(throttle_key):
            raise HTTPException(429, "Too many login attempts. Try again later")
        user = await db.customer_accounts.find_one({"email": email})
        if not user or not verify_password(payload.password, user["password_hash"]):
            login_throttle.fail(throttle_key)
            raise HTTPException(401, "Invalid credentials")
        login_throttle.clear(throttle_key)
        token, digest, expiry = create_session()
        await db.customer_sessions.insert_one({
            "digest": digest, "user_id": user["id"], "expires_at": expiry,
            "revoked_at": None,
        })
        if request.headers.get("X-Lumiere-Web-Login") == "1":
            origin = request.headers.get("origin")
            if origin:
                from urllib.parse import urlsplit
                if urlsplit(origin).netloc != request.headers.get("host", ""):
                    raise HTTPException(403, "Cross-site login blocked")
            browser_session(response, token)
            return {"success": True, "token_type": "cookie", "expires_at": expiry.isoformat()}
        return {"access_token": token, "token_type": "bearer", "expires_at": expiry.isoformat()}

    @router.post("/recovery/request")
    async def request_recovery(payload: RecoveryRequest, request: Request):
        # Never claim a reset was delivered if the mail provider is unavailable.
        if not recovery_configured():
            raise HTTPException(503, "Account recovery is not configured")
        try:
            address = normalize_email(payload.email)
        except ValueError:
            raise HTTPException(422, "Invalid email")
        request_ip = request.client.host if request.client else "unknown"
        recovery_key = request_ip + ":" + address
        if recovery_throttle.is_blocked(recovery_key):
            raise HTTPException(429, "Too many recovery requests. Try again later")
        recovery_throttle.fail(recovery_key)
        user = await db.customer_accounts.find_one({"email": address})
        if user:
            token = secrets.token_urlsafe(40)
            record = {
                "digest": token_digest(token), "user_id": user["id"],
                "expires_at": datetime.now(timezone.utc) + timedelta(minutes=30),
                "used_at": None,
            }
            await db.customer_recovery.insert_one(record)
            try:
                await run_in_threadpool(send_recovery_email, address, token)
            except Exception as exc:
                await db.customer_recovery.delete_one({"digest": record["digest"]})
                raise HTTPException(503, "Recovery email could not be delivered") from exc
        return {"message": "If that email is registered, recovery instructions will be sent."}

    @router.post("/recovery/confirm")
    async def confirm_recovery(payload: RecoveryConfirm):
        if not recovery_configured():
            raise HTTPException(503, "Account recovery is not configured")
        digest = token_digest(payload.token)
        record = await db.customer_recovery.find_one({
            "digest": digest, "used_at": None,
            "expires_at": {"$gt": datetime.now(timezone.utc)},
        })
        if not record:
            raise HTTPException(400, "Invalid or expired recovery link")
        new_hash = await run_in_threadpool(hash_password, payload.password)
        consumed = await db.customer_recovery.update_one(
            {"digest": digest, "used_at": None, "expires_at": {"$gt": datetime.now(timezone.utc)}},
            {"$set": {"used_at": datetime.now(timezone.utc)}},
        )
        if not consumed.matched_count:
            raise HTTPException(400, "Recovery link already used")
        await db.customer_accounts.update_one(
            {"id": record["user_id"]}, {"$set": {"password_hash": new_hash}},
        )
        await db.customer_sessions.update_many(
            {"user_id": record["user_id"], "revoked_at": None},
            {"$set": {"revoked_at": datetime.now(timezone.utc)}},
        )
        return {"success": True}

    @router.post("/logout")
    async def logout(request: Request, response: Response, authorization: Annotated[str | None, Header()] = None, user_id: str = Depends(current_user)):
        await db.customer_sessions.update_one(
            {"digest": token_digest(authorization[7:] if authorization and authorization.startswith("Bearer ") else request.cookies.get(COOKIE_NAME, "")), "user_id": user_id},
            {"$set": {"revoked_at": datetime.now(timezone.utc)}},
        )
        clear_browser_session(response)
        return {"success": True}

    @router.get("/me")
    async def me(user_id: str = Depends(current_user)):
        user = await db.customer_accounts.find_one({"id": user_id})
        return {"id": user_id, "email": user["email"]}


    @router.post("/conversations", status_code=201)
    async def create_conversation(user_id: str = Depends(current_user)):
        record = {
            "id": str(uuid.uuid4()), "user_id": user_id,
            "title": "New styling session", "pinned": False, "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "deleted_at": None,
        }
        await db.customer_conversations.insert_one(record)
        record.pop("_id", None)
        return record

    @router.get("/conversations")
    async def list_conversations(user_id: str = Depends(current_user)):
        return await db.customer_conversations.find(
            {"user_id": user_id, "deleted_at": None}, {"_id": 0}
        ).to_list(200)

    @router.get("/conversations/{conversation_id}/messages")
    async def list_messages(conversation_id: str, user_id: str = Depends(current_user)):
        conversation = await db.customer_conversations.find_one({
            "id": conversation_id, "user_id": user_id, "deleted_at": None,
        })
        if not conversation:
            raise HTTPException(404, "Conversation not found")
        return await db.customer_messages.find(
            {"user_id": user_id, "conversation_id": conversation_id}, {"_id": 0}
        ).to_list(200)

    @router.delete("/conversations/{conversation_id}")
    async def delete_conversation(conversation_id: str, user_id: str = Depends(current_user)):
        result = await db.customer_conversations.update_one(
            {"id": conversation_id, "user_id": user_id, "deleted_at": None},
            {"$set": {"deleted_at": datetime.now(timezone.utc)}},
        )
        if not result.matched_count:
            raise HTTPException(404, "Conversation not found")
        return {"success": True}


    @router.patch("/conversations/{conversation_id}")
    async def update_conversation(conversation_id: str, payload: dict, user_id: str = Depends(current_user)):
        updates = {}
        if "title" in payload:
            title = payload["title"]
            if not isinstance(title, str) or not 1 <= len(title.strip()) <= 120:
                raise HTTPException(422, "Invalid conversation title")
            updates["title"] = title.strip()
        if "pinned" in payload:
            if not isinstance(payload["pinned"], bool):
                raise HTTPException(422, "Invalid pinned value")
            updates["pinned"] = payload["pinned"]
        if not updates:
            raise HTTPException(422, "No valid changes")
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        result = await db.customer_conversations.update_one(
            {"id": conversation_id, "user_id": user_id, "deleted_at": None},
            {"$set": updates},
        )
        if not result.matched_count:
            raise HTTPException(404, "Conversation not found")
        record = await db.customer_conversations.find_one({"id": conversation_id, "user_id": user_id})
        record.pop("_id", None)
        return record

    @router.post("/conversations/{conversation_id}/chat")
    async def owned_chat(conversation_id: str, payload: AccountChatInput, user_id: str = Depends(current_user)):
        conversation = await db.customer_conversations.find_one({
            "id": conversation_id, "user_id": user_id, "deleted_at": None,
        })
        if not conversation:
            raise HTTPException(404, "Conversation not found")
        if payload.image_path is not None:
            raise HTTPException(422, "Private photo attachment is not yet supported by account chat")
        if generate_chat is None:
            raise HTTPException(503, "Authenticated chat provider unavailable")
        prior = await db.customer_messages.find({
            "user_id": user_id, "conversation_id": conversation_id,
        }, {"_id": 0}).to_list(200)
        prior.sort(key=lambda item: item.get("created_at", ""))
        profile = await db.customer_profiles.find_one({"user_id": user_id}) or {"user_id": user_id}
        # Generate before saving so provider failures do not leave ghost conversations.
        try:
            reply = await generate_chat(conversation_id, profile, prior, payload.message, payload.provider)
        except Exception as exc:
            raise HTTPException(502, "Stylist response unavailable") from exc
        if not isinstance(reply, str) or not reply.strip():
            raise HTTPException(502, "Stylist response unavailable")
        timestamp = datetime.now(timezone.utc).isoformat()
        await db.customer_messages.insert_one({
            "id": str(uuid.uuid4()), "user_id": user_id, "conversation_id": conversation_id,
            "role": "user", "content": payload.message, "image_path": None, "created_at": timestamp,
        })
        message_id = str(uuid.uuid4())
        await db.customer_messages.insert_one({
            "id": message_id, "user_id": user_id, "conversation_id": conversation_id,
            "role": "assistant", "content": reply, "image_path": None, "created_at": timestamp,
        })
        first_message = not prior
        title = payload.message.strip()[:48] if first_message else conversation["title"]
        await db.customer_conversations.update_one(
            {"id": conversation_id, "user_id": user_id},
            {"$set": {"title": title, "updated_at": timestamp}},
        )
        async def stream():
            yield "data: " + json.dumps({"delta": reply}) + "\n\n"
            yield "data: " + json.dumps({"done": True, "message_id": message_id,
                                         "title": title, "provider": payload.provider}) + "\n\n"
        return StreamingResponse(stream(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})




    @router.post("/skin-analysis")
    async def customer_skin_analysis(payload: dict, user_id: str = Depends(current_user)):
        path = payload.get("image_path")
        if not isinstance(path, str) or not path.startswith("private:"):
            raise HTTPException(422, "Colour analysis requires an owned private photo")
        photo_id = path.removeprefix("private:")
        photo = await db.customer_photos.find_one({"id": photo_id, "user_id": user_id})
        if not photo:
            raise HTTPException(404, "Photograph not found")
        if analyze_skin is None:
            raise HTTPException(503, "Private colour analysis unavailable")
        try:
            data, mime = await run_in_threadpool(read_image, photo["path"])
            analysis = await analyze_skin(data, mime, payload.get("provider"))
        except Exception as exc:
            raise HTTPException(502, "Colour analysis unavailable") from exc
        analysis = {**analysis, "image_path": path, "analyzed_at": datetime.now(timezone.utc).isoformat()}
        await db.customer_profiles.update_one(
            {"user_id": user_id}, {"$set": {
                "skin": analysis, "updated_at": datetime.now(timezone.utc).isoformat(),
            }}, upsert=True,
        )
        return analysis

    @router.post("/tryons", status_code=201)
    async def owned_tryon(payload: PrivateTryOnInput, user_id: str = Depends(current_user)):
        person = await db.customer_photos.find_one({
            "id": payload.person_photo_id, "user_id": user_id,
        })
        if not person:
            raise HTTPException(404, "Person photograph not found")
        garment = None
        if payload.garment_photo_id is not None:
            garment = await db.customer_photos.find_one({
                "id": payload.garment_photo_id, "user_id": user_id,
            })
            if not garment:
                raise HTTPException(404, "Garment photograph not found")
        second_garment = None
        if payload.second_garment_photo_id is not None:
            if garment is None:
                raise HTTPException(422, "First garment photo required")
            second_garment = await db.customer_photos.find_one({
                "id": payload.second_garment_photo_id, "user_id": user_id,
            })
            if not second_garment:
                raise HTTPException(404, "Second garment photograph not found")
        if garment is None and not (payload.garment_prompt or "").strip():
            raise HTTPException(422, "A garment photo or description is required")
        if generate_tryon is None:
            raise HTTPException(503, "Private Try-On generation is unavailable")
        try:
            person_bytes, _ = await run_in_threadpool(read_image, person["path"])
            garment_bytes = None
            if garment:
                garment_bytes, _ = await run_in_threadpool(read_image, garment["path"])
            second_bytes = None
            if second_garment:
                second_bytes, _ = await run_in_threadpool(read_image, second_garment["path"])
            result_bytes, mime = await generate_tryon(
                person_bytes, garment_bytes, second_bytes, payload.garment_prompt or ""
            )
            ext, verified_mime = validate_image(result_bytes, mime, "generated.png")
            clean = await run_in_threadpool(sanitize_image, result_bytes, ext)
            path = await run_in_threadpool(save_image, clean, ext, verified_mime)
        except Exception as exc:
            raise HTTPException(502, "Private Try-On failed") from exc
        photo_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        await db.customer_photos.insert_one({
            "id": photo_id, "user_id": user_id, "path": path,
            "content_type": verified_mime, "created_at": now, "generated": True,
        })
        record = {
            "id": str(uuid.uuid4()), "user_id": user_id,
            "person_photo_id": payload.person_photo_id,
            "garment_photo_id": payload.garment_photo_id,
            "second_garment_photo_id": payload.second_garment_photo_id,
            "garment_prompt": payload.garment_prompt,
            "result_photo_id": photo_id, "created_at": now, "deleted_at": None,
        }
        await db.customer_tryons.insert_one(record)
        record.pop("_id", None)
        return record

    @router.get("/tryons")
    async def list_owned_tryons(user_id: str = Depends(current_user)):
        return await db.customer_tryons.find(
            {"user_id": user_id, "deleted_at": None}, {"_id": 0}
        ).to_list(200)

    @router.delete("/tryons/{tryon_id}")
    async def delete_owned_tryon(tryon_id: str, user_id: str = Depends(current_user)):
        record = await db.customer_tryons.find_one({
            "id": tryon_id, "user_id": user_id, "deleted_at": None,
        })
        if not record:
            raise HTTPException(404, "Try-On not found")
        result_photo_id = record.get("result_photo_id")
        photo = await db.customer_photos.find_one({
            "id": result_photo_id, "user_id": user_id,
        })
        if photo:
            if delete_image is None:
                raise HTTPException(503, "Verified generated-image deletion unavailable")
            try:
                await run_in_threadpool(delete_image, photo["path"])
            except Exception as exc:
                raise HTTPException(503, "Verified generated-image deletion unavailable") from exc
            await db.customer_photos.delete_one({
                "id": result_photo_id, "user_id": user_id,
            })
        await db.customer_tryons.update_one(
            {"id": tryon_id, "user_id": user_id, "deleted_at": None},
            {"$set": {"deleted_at": datetime.now(timezone.utc)}},
        )
        return {"success": True, "result_photo_deleted": True}

    @router.post("/catalogue/products/{product_id}/prepare-tryon")
    async def owned_catalogue_garment(product_id: str, user_id: str = Depends(current_user)):
        if prepare_catalogue is None:
            raise HTTPException(503, "Private catalogue garment preparation unavailable")
        try:
            data, mime, name = await prepare_catalogue(product_id)
            ext, verified_mime = validate_image(data, mime, "garment.jpg")
            clean = await run_in_threadpool(sanitize_image, data, ext)
            path = await run_in_threadpool(save_image, clean, ext, verified_mime)
        except Exception as exc:
            raise HTTPException(502, "Catalogue garment preparation failed") from exc
        photo_id = str(uuid.uuid4())
        await db.customer_photos.insert_one({
            "id": photo_id, "user_id": user_id, "path": path,
            "content_type": verified_mime, "created_at": datetime.now(timezone.utc).isoformat(),
        })
        return {"path": "private:" + photo_id, "name": name}

    @router.get("/catalogue/recommendations")
    async def customer_discover(user_id: str = Depends(current_user)):
        if recommend_catalogue is None:
            raise HTTPException(503, "Private catalogue recommendations unavailable")
        return await recommend_catalogue(user_id)

    @router.get("/profile")
    async def get_profile(user_id: str = Depends(current_user)):
        record = await db.customer_profiles.find_one({"user_id": user_id}, {"_id": 0}) or {}
        defaults = {
            "budget_min": 0, "budget_max": 500, "occasion": "casual",
            "categories": [], "climate": "mild", "style": "classic",
            "preferred_fit": "regular", "preferred_colours": [],
            "avoided_colours": [], "preferred_retailers": ["zara", "hm", "uniqlo"],
            "shop_for": "all",
        }
        return {
            "id": user_id, "user_id": user_id, "favorite_colors": [],
            "styles": [], "sizes": {}, "budget": None, "notes": "",
            "skin": None, "updated_at": datetime.now(timezone.utc).isoformat(),
            **record, "preferences": {**defaults, **(record.get("preferences") or {})},
        }

    @router.put("/profile")
    async def put_profile(payload: dict, user_id: str = Depends(current_user)):
        allowed = {key: payload[key] for key in ("preferences", "notes", "favorite_colors", "styles", "sizes", "budget") if key in payload}
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
        private_path = payload.get("image_path", "")
        if not isinstance(private_path, str) or (private_path and not private_path.startswith("private:")):
            raise HTTPException(422, "Wardrobe photographs must use private photo IDs")
        if private_path:
            photo_id = private_path.removeprefix("private:")
            if not await db.customer_photos.find_one({"id": photo_id, "user_id": user_id}):
                raise HTTPException(404, "Wardrobe photograph not found")
        item = {"id": str(uuid.uuid4()), "user_id": user_id, "name": name.strip(),
                "category": str(payload.get("category", "other"))[:40],
                "colour": str(payload.get("colour", ""))[:80], "image_path": private_path,
                "notes": str(payload.get("notes", ""))[:500],
                "created_at": datetime.now(timezone.utc).isoformat(), "deleted_at": None}
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



    @router.post("/wardrobe/outfits")
    async def owned_outfits(payload: dict, user_id: str = Depends(current_user)):
        climate = payload.get("climate", "mild")
        occasion = payload.get("occasion", "casual")
        if climate not in {"hot", "mild", "cold"} or not isinstance(occasion, str) or len(occasion) > 80:
            raise HTTPException(422, "Invalid wardrobe planning preferences")
        items = await db.customer_wardrobe.find(
            {"user_id": user_id, "deleted_at": None}, {"_id": 0}
        ).to_list(200)
        return {"outfits": plan_outfits(items, occasion=occasion, climate=climate)}

    @router.post("/wardrobe/capsule")
    async def owned_capsule(payload: dict, user_id: str = Depends(current_user)):
        climate = payload.get("climate", "mild")
        occasion = payload.get("occasion", "casual")
        if climate not in {"hot", "mild", "cold"} or not isinstance(occasion, str) or len(occasion) > 80:
            raise HTTPException(422, "Invalid wardrobe planning preferences")
        items = await db.customer_wardrobe.find(
            {"user_id": user_id, "deleted_at": None}, {"_id": 0}
        ).to_list(200)
        return capsule_plan(items, occasion=occasion, climate=climate)

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



    @router.delete("/photos/{photo_id}")
    async def delete_photo(photo_id: str, user_id: str = Depends(current_user)):
        photo = await db.customer_photos.find_one({"id": photo_id, "user_id": user_id})
        if not photo:
            raise HTTPException(404, "Photo not found")
        if delete_image is None:
            raise HTTPException(503, "Verified storage deletion unavailable")
        # Deleting a face, person or garment photo also invalidates try-ons
        # containing it. Their generated results can retain a person's likeness.
        active_tryons = await db.customer_tryons.find(
            {"user_id": user_id, "deleted_at": None}, {"_id": 0},
        ).to_list(2000)
        referenced = ("person_photo_id", "garment_photo_id", "second_garment_photo_id", "result_photo_id")
        linked = [t for t in active_tryons if photo_id in (t.get(k) for k in referenced)]
        generated_ids = {
            t["result_photo_id"] for t in linked
            if t.get("result_photo_id") and t["result_photo_id"] != photo_id
        }
        # Verify all derived object deletions before removing their metadata.
        # A retry is safe for previously removed objects.
        try:
            for derived_id in generated_ids:
                derived = await db.customer_photos.find_one(
                    {"id": derived_id, "user_id": user_id},
                )
                if derived:
                    await run_in_threadpool(delete_image, derived["path"])
            await run_in_threadpool(delete_image, photo["path"])
        except Exception as exc:
            raise HTTPException(503, "Verified storage deletion unavailable") from exc

        for derived_id in generated_ids:
            await db.customer_photos.delete_one({"id": derived_id, "user_id": user_id})
        await db.customer_photos.delete_one({"id": photo_id, "user_id": user_id})
        now = datetime.now(timezone.utc).isoformat()
        for record in linked:
            await db.customer_tryons.update_one(
                {"id": record["id"], "user_id": user_id},
                {"$set": {"deleted_at": now}},
            )
        profile = await db.customer_profiles.find_one({"user_id": user_id})
        skin = (profile or {}).get("skin") or {}
        if skin.get("image_path") == "private:" + photo_id:
            await db.customer_profiles.update_one(
                {"user_id": user_id}, {"$set": {"skin": None, "updated_at": now}},
            )
        wardrobe = await db.customer_wardrobe.find(
            {"user_id": user_id}, {"_id": 0},
        ).to_list(1000)
        for item in wardrobe:
            if item.get("image_path") == "private:" + photo_id:
                await db.customer_wardrobe.update_one(
                    {"id": item["id"], "user_id": user_id},
                    {"$set": {"image_path": ""}},
                )
        return {"success": True}

    @router.post("/saved", status_code=201)
    async def save_look(payload: dict, user_id: str = Depends(current_user)):
        message_id = payload.get("message_id")
        if not isinstance(message_id, str) or not message_id or len(message_id) > 150:
            raise HTTPException(422, "Invalid message")
        message = await db.customer_messages.find_one({
            "id": message_id, "user_id": user_id, "role": "assistant",
        })
        if not message:
            raise HTTPException(404, "Message not found")
        conversation = await db.customer_conversations.find_one({
            "id": message["conversation_id"], "user_id": user_id, "deleted_at": None,
        })
        if not conversation:
            raise HTTPException(404, "Conversation not found")
        found = await db.customer_saved.find_one({
            "user_id": user_id, "message_id": message_id,
        })
        if found:
            found.pop("_id", None)
            return found
        record = {
            "id": str(uuid.uuid4()), "user_id": user_id,
            "message_id": message_id, "conversation_id": message["conversation_id"],
            "content": message["content"], "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.customer_saved.insert_one(record)
        record.pop("user_id")
        return record

    @router.get("/saved")
    async def saved_looks(user_id: str = Depends(current_user)):
        records = await db.customer_saved.find({"user_id": user_id}, {"_id": 0}).to_list(200)
        return [{k: v for k, v in record.items() if k != "user_id"} for record in records]

    @router.delete("/saved/{saved_id}")
    async def remove_saved_look(saved_id: str, user_id: str = Depends(current_user)):
        record = await db.customer_saved.find_one({"id": saved_id, "user_id": user_id})
        if not record:
            raise HTTPException(404, "Saved look not found")
        await db.customer_saved.delete_one({"id": saved_id, "user_id": user_id})
        return {"success": True}

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
