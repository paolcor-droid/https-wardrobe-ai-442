"""Account isolation regression tests using in-memory collections; no live DB or photos."""
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.testclient import TestClient

from services.account_routes import configure_account_router
from services.customer_auth import hash_password, token_digest


class Result:
    def __init__(self, matched=1):
        self.matched_count = matched


class Cursor:
    def __init__(self, items):
        self.items = items

    async def to_list(self, limit):
        return self.items[:limit]


class Collection:
    def __init__(self):
        self.docs = []

    async def find_one(self, query, projection=None):
        for doc in self.docs:
            if all(self._match(doc.get(k), v) for k, v in query.items()):
                return dict(doc)
        return None

    def _match(self, value, expected):
        if isinstance(expected, dict) and "$gt" in expected:
            return value is not None and value > expected["$gt"]
        return value == expected

    async def insert_one(self, doc):
        self.docs.append(dict(doc))

    async def update_one(self, query, update, upsert=False):
        item = await self.find_one(query)
        if item:
            for doc in self.docs:
                if all(self._match(doc.get(k), v) for k, v in query.items()):
                    doc.update(update["$set"])
                    return Result()
        if upsert:
            self.docs.append({**query, **update["$set"]})
            return Result()
        return Result(0)

    async def update_many(self, query, update):
        matched = 0
        for doc in self.docs:
            if all(self._match(doc.get(k), v) for k, v in query.items()):
                doc.update(update["$set"])
                matched += 1
        return Result(matched)

    async def count_documents(self, query):
        return len([d for d in self.docs if all(self._match(d.get(k), v) for k, v in query.items())])

    async def delete_many(self, query):
        self.docs = [d for d in self.docs if not all(self._match(d.get(k), v) for k, v in query.items())]
        return Result()

    async def delete_one(self, query):
        self.docs = [doc for doc in self.docs if not all(self._match(doc.get(k), v) for k, v in query.items())]
        return Result()

    def find(self, query, projection=None):
        return Cursor([dict(doc) for doc in self.docs
                       if all(self._match(doc.get(k), v) for k, v in query.items())])


class Database:
    def __init__(self):
        self.customer_accounts = Collection()
        self.customer_sessions = Collection()
        self.customer_recovery = Collection()
        self.customer_profiles = Collection()
        self.customer_wardrobe = Collection()
        self.customer_photos = Collection()
        self.customer_feedback = Collection()
        self.customer_conversations = Collection()
        self.customer_messages = Collection()
        self.customer_tryons = Collection()
        self.customer_saved = Collection()
        self.customer_bag = Collection()
        self.customer_outfits = Collection()
        self.customer_rate_limits = Collection()


def test_account_profile_wardrobe_and_photo_access_isolation():
    db = Database()
    app = FastAPI()
    app.include_router(configure_account_router(
        db, lambda *args: ("png", "image/png"),
        lambda data, ext: data, lambda *args: "local/fake.png",
        lambda path: (b"private image", "image/png"), lambda path: None,
    ))
    client = TestClient(app)
    tokens = []
    for email in ("first@example.com", "second@example.com"):
        response = client.post("/api/account/register",
                               json={"email": email, "password": "long secure password"})
        assert response.status_code == 201, response.text
        login = client.post("/api/account/login",
                            json={"email": email, "password": "long secure password"})
        assert login.status_code == 200, login.text
        tokens.append(login.json()["access_token"])
    a = {"Authorization": "Bearer " + tokens[0]}
    b = {"Authorization": "Bearer " + tokens[1]}
    assert client.get("/api/account/profile").status_code == 401
    conversation = client.post("/api/account/conversations", headers=a).json()
    assert client.get("/api/account/conversations", headers=b).json() == []
    assert client.get("/api/account/conversations/" + conversation["id"] + "/messages", headers=b).status_code == 404
    assert client.delete("/api/account/conversations/" + conversation["id"], headers=b).status_code == 404
    assert client.delete("/api/account/conversations/" + conversation["id"], headers=a).status_code == 200
    assert client.put("/api/account/profile", headers=a,
                      json={"notes": "first account"}).status_code == 200
    assert client.get("/api/account/profile", headers=b).json().get("notes") == ""
    item = client.post("/api/account/wardrobe", headers=a, json={"name": "Private shirt"}).json()
    assert len(client.get("/api/account/wardrobe", headers=b).json()) == 0
    assert client.post("/api/account/wardrobe/capsule", headers=b, json={}).json()["items"] == []
    assert [x["id"] for x in client.post("/api/account/wardrobe/capsule", headers=a, json={}).json()["items"]] == [item["id"]]
    assert client.post("/api/account/wardrobe/outfits", headers=b, json={}).json()["outfits"] == []
    assert client.delete("/api/account/wardrobe/" + item["id"], headers=b).status_code == 404
    photo = client.post("/api/account/photos", headers=a,
                        files={"file": ("sample.png", b"fake bytes", "image/png")})
    assert photo.status_code == 201, photo.text
    photo_id = photo.json()["id"]
    assert client.get("/api/account/photos/" + photo_id, headers=b).status_code == 404
    assert client.get("/api/account/photos/" + photo_id, headers=a).status_code == 200
    assert client.put("/api/account/feedback/item123", headers=a, json={"sentiment": "liked"}).status_code == 200
    assert client.get("/api/account/feedback", headers=b).json() == []
    assert client.get("/api/account/feedback", headers=a).json() == [{"product_id": "item123", "sentiment": "liked"}]
    assert client.delete("/api/account/photos/" + photo_id, headers=b).status_code == 404
    assert client.delete("/api/account/photos/" + photo_id, headers=a).status_code == 200
    assert client.get("/api/account/photos/" + photo_id, headers=a).status_code == 404
    assert client.post("/api/account/logout", headers=a).status_code == 200
    assert client.get("/api/account/me", headers=a).status_code == 401
    assert client.get("/api/account/me", headers=b).status_code == 200


def test_remote_photo_deletion_unavailable_keeps_record():
    db = Database()
    app = FastAPI()
    def unsupported_delete(path):
        raise NotImplementedError("Remote object storage delete not verified")
    app.include_router(configure_account_router(
        db, lambda *args: ("png", "image/png"),
        lambda data, ext: data, lambda *args: "remote/private-id.png",
        lambda path: (b"photo", "image/png"), unsupported_delete,
    ))
    client = TestClient(app)
    assert client.post("/api/account/register", json={
        "email": "third@example.com", "password": "long secure password"
    }).status_code == 201
    login = client.post("/api/account/login", json={
        "email": "third@example.com", "password": "long secure password"
    })
    headers = {"Authorization": "Bearer " + login.json()["access_token"]}
    photo = client.post("/api/account/photos", headers=headers,
                        files={"file": ("sample.png", b"bytes", "image/png")}).json()
    path = "/api/account/photos/" + photo["id"]
    assert client.delete(path, headers=headers).status_code == 503
    assert client.get(path, headers=headers).status_code == 200


def test_authenticated_chat_requires_owner_and_uses_only_that_user_profile():
    db = Database()
    app = FastAPI()
    calls = []

    async def reply(conversation_id, profile, prior, message, provider):
        calls.append((profile.get("notes"), [p["content"] for p in prior], message))
        return "Private style advice"

    app.include_router(configure_account_router(
        db, lambda *args: ("png", "image/png"),
        lambda data, ext: data, lambda *args: "local/fake.png",
        lambda path: (b"photo", "image/png"), lambda path: None, reply,
    ))
    client = TestClient(app)
    headers = []
    for email in ("style-a@example.com", "style-b@example.com"):
        assert client.post("/api/account/register", json={
            "email": email, "password": "long secure password"
        }).status_code == 201
        logged_in = client.post("/api/account/login", json={
            "email": email, "password": "long secure password"
        })
        headers.append({"Authorization": "Bearer " + logged_in.json()["access_token"]})

    a, b = headers
    assert client.put("/api/account/profile", headers=a,
                      json={"notes": "Private preference A"}).status_code == 200
    conversation = client.post("/api/account/conversations", headers=a).json()
    url = "/api/account/conversations/" + conversation["id"] + "/chat"
    assert client.post(url, headers=b, json={"message": "style me"}).status_code == 404
    assert client.post(url, json={"message": "style me"}).status_code == 401
    assert client.post(url, headers=a, json={
        "message": "style me", "image_path": "somebody-elses-photo"
    }).status_code == 422
    response = client.post(url, headers=a, json={"message": "style me"})
    assert response.status_code == 200
    assert '"delta": "Private style advice"' in response.text
    assert '"done": true' in response.text
    assert calls == [("Private preference A", [], "style me")]
    assert client.get("/api/account/conversations/" + conversation["id"] + "/messages",
                      headers=b).status_code == 404
    messages = client.get("/api/account/conversations/" + conversation["id"] + "/messages",
                          headers=a).json()
    assert [message["role"] for message in messages] == ["user", "assistant"]


def test_discover_uses_authenticated_customer_only():
    db = Database()
    app = FastAPI()
    async def private_recommendations(user_id):
        row = await db.customer_profiles.find_one({"user_id": user_id}) or {}
        return {"count": 1, "recommendations": [{"name": row.get("notes", "New user")}],
                "source": "test", "live_inventory_enabled": False}
    app.include_router(configure_account_router(
        db, lambda *args: ("png", "image/png"),
        lambda data, ext: data, lambda *args: "local/fake.png",
        lambda path: (b"photo", "image/png"), None, None, private_recommendations,
    ))
    client = TestClient(app)
    headers = []
    for email in ("rec-a@example.com", "rec-b@example.com"):
        assert client.post("/api/account/register", json={
            "email": email, "password": "long secure password"
        }).status_code == 201
        login = client.post("/api/account/login", json={
            "email": email, "password": "long secure password"
        }).json()
        headers.append({"Authorization": "Bearer " + login["access_token"]})
    a, b = headers
    assert client.get("/api/account/catalogue/recommendations").status_code == 401
    assert client.put("/api/account/profile", headers=a, json={
        "notes": "Customer A styles"
    }).status_code == 200
    assert client.get("/api/account/catalogue/recommendations", headers=a).json()[
        "recommendations"][0]["name"] == "Customer A styles"
    assert client.get("/api/account/catalogue/recommendations", headers=b).json()[
        "recommendations"][0]["name"] == "New user"


def test_private_tryon_requires_owned_person_and_garment_and_hides_results():
    db = Database()
    app = FastAPI()
    async def generate(person, garment, second_garment, prompt):
        return b"generated output", "image/png"
    app.include_router(configure_account_router(
        db, lambda *args: ("png", "image/png"), lambda data, ext: data,
        lambda *args: "local/private.png",
        lambda path: (b"private image", "image/png"),
        lambda path: None, None, None, generate,
    ))
    client = TestClient(app)
    headers = []
    for email in ("try-a@example.com", "try-b@example.com"):
        assert client.post("/api/account/register", json={
            "email": email, "password": "long secure password"
        }).status_code == 201
        login = client.post("/api/account/login", json={
            "email": email, "password": "long secure password"
        })
        headers.append({"Authorization": "Bearer " + login.json()["access_token"]})
    a, b = headers
    person = client.post("/api/account/photos", headers=a,
                         files={"file": ("person.png", b"bytes", "image/png")}).json()["id"]
    garment = client.post("/api/account/photos", headers=a,
                          files={"file": ("garment.png", b"bytes", "image/png")}).json()["id"]
    uri = "/api/account/tryons"
    assert client.post(uri, json={"person_photo_id": person,
                                  "garment_prompt": "linen shirt"}).status_code == 401
    assert client.post(uri, headers=b, json={
        "person_photo_id": person, "garment_prompt": "linen shirt"
    }).status_code == 404
    assert client.post(uri, headers=b, json={
        "person_photo_id": garment, "garment_photo_id": person
    }).status_code == 404
    made = client.post(uri, headers=a, json={
        "person_photo_id": person, "garment_photo_id": garment
    })
    assert made.status_code == 201, made.text
    item = made.json()
    assert client.get(uri, headers=b).json() == []
    assert len(client.get(uri, headers=a).json()) == 1
    result_uri = "/api/account/photos/" + item["result_photo_id"]
    assert client.get(result_uri, headers=b).status_code == 404
    assert client.get(result_uri, headers=a).status_code == 200
    assert client.delete(uri + "/" + item["id"], headers=b).status_code == 404
    assert client.delete(uri + "/" + item["id"], headers=a).status_code == 200
    assert client.get(result_uri, headers=a).status_code == 404


def test_skin_analysis_and_wardrobe_photo_links_require_ownership():
    db = Database()
    app = FastAPI()
    async def analyse(data, mime, provider):
        return {"undertone": "neutral", "depth": "medium", "chroma": "muted",
                "contrast": "low", "summary": "private colour result",
                "palette": [], "best_neutrals": [], "best_accents": [],
                "statement_colours": [], "caution_colours": []}
    app.include_router(configure_account_router(
        db, lambda *args: ("png", "image/png"),
        lambda data, ext: data, lambda *args: "local/fake.png",
        lambda path: (b"private photo bytes", "image/png"), None, None, None, None, analyse,
    ))
    client = TestClient(app)
    users = []
    for email in ("scan-a@example.com", "scan-b@example.com"):
        assert client.post("/api/account/register", json={
            "email": email, "password": "long secure password"
        }).status_code == 201
        logged = client.post("/api/account/login", json={
            "email": email, "password": "long secure password"
        })
        users.append({"Authorization": "Bearer " + logged.json()["access_token"]})
    a, b = users
    photo = client.post("/api/account/photos", headers=a,
                        files={"file": ("face.png", b"bytes", "image/png")}).json()["id"]
    private_path = "private:" + photo
    assert client.post("/api/account/skin-analysis", headers=b,
                       json={"image_path": private_path}).status_code == 404
    assert client.post("/api/account/wardrobe", headers=b, json={
        "name": "Stolen photo", "image_path": private_path
    }).status_code == 404
    assert client.post("/api/account/wardrobe", headers=b, json={
        "name": "Legacy shared photo", "image_path": "local/legacy.png"
    }).status_code == 422
    analysed = client.post("/api/account/skin-analysis", headers=a,
                           json={"image_path": private_path})
    assert analysed.status_code == 200, analysed.text
    assert client.get("/api/account/profile", headers=a).json()["skin"]["summary"] == "private colour result"
    assert client.get("/api/account/profile", headers=b).json()["skin"] is None
    assert client.post("/api/account/wardrobe", headers=a, json={
        "name": "Owned item", "image_path": private_path
    }).status_code == 201


def test_multi_feature_two_customer_e2e():
    db = Database()
    app = FastAPI()

    async def chat_reply(conversation_id, profile, prior, message, provider):
        return "Private advice for " + profile.get("notes", "anonymous")

    async def recommendations(user_id):
        profile = await db.customer_profiles.find_one({"user_id": user_id}) or {}
        return {"count": 1, "recommendations": [{"name": profile.get("notes", "new user")}],
                "source": "test", "live_inventory_enabled": False}

    async def tryon(person, garment, second, prompt):
        return b"generated image", "image/png"

    async def scan(data, mime, provider):
        return {"undertone": "neutral", "depth": "medium", "chroma": "muted",
                "contrast": "low", "summary": "private scan"}

    async def prepare(product_id):
        if product_id != "trusted":
            raise ValueError("Untrusted product")
        return b"trusted bytes", "image/png", "Trusted garment"

    app.include_router(configure_account_router(
        db, lambda *args: ("png", "image/png"),
        lambda data, ext: data, lambda *args: "local/fake.png",
        lambda path: (b"private bytes", "image/png"),
        lambda path: None, chat_reply, recommendations, tryon, scan, prepare,
    ))
    client = TestClient(app)
    headers = []
    for email in ("journey-a@example.com", "journey-b@example.com"):
        assert client.post("/api/account/register", json={
            "email": email, "password": "long secure password"
        }).status_code == 201
        login = client.post("/api/account/login", json={
            "email": email, "password": "long secure password"
        })
        assert login.status_code == 200
        headers.append({"Authorization": "Bearer " + login.json()["access_token"]})
    a, b = headers
    assert client.put("/api/account/profile", headers=a, json={"notes": "linen lover"}).status_code == 200
    photo = client.post("/api/account/photos", headers=a,
                        files={"file": ("person.png", b"private bytes", "image/png")})
    assert photo.status_code == 201
    photo_id = photo.json()["id"]
    assert client.post("/api/account/skin-analysis", headers=a, json={
        "image_path": "private:" + photo_id
    }).status_code == 200
    assert client.get("/api/account/profile", headers=b).json()["skin"] is None
    assert client.post("/api/account/wardrobe", headers=a, json={
        "name": "Linen shirt", "image_path": "private:" + photo_id
    }).status_code == 201
    assert client.get("/api/account/wardrobe", headers=b).json() == []
    assert client.get("/api/account/catalogue/recommendations", headers=a).json()[
        "recommendations"][0]["name"] == "linen lover"
    assert client.get("/api/account/catalogue/recommendations", headers=b).json()[
        "recommendations"][0]["name"] == "new user"
    conversation = client.post("/api/account/conversations", headers=a).json()
    url = "/api/account/conversations/" + conversation["id"] + "/chat"
    assert client.post(url, headers=a, json={"message": "Style me"}).status_code == 200
    assert client.post(url, headers=b, json={"message": "Spy"}).status_code == 404
    garment = client.post("/api/account/catalogue/products/trusted/prepare-tryon", headers=a)
    assert garment.status_code == 200, garment.text
    garment_id = garment.json()["path"].removeprefix("private:")
    generated = client.post("/api/account/tryons", headers=a, json={
        "person_photo_id": photo_id, "garment_photo_id": garment_id,
    })
    assert generated.status_code == 201, generated.text
    result_id = generated.json()["result_photo_id"]
    assert client.get("/api/account/photos/" + result_id, headers=b).status_code == 404
    assert client.get("/api/account/tryons", headers=b).json() == []
    assert client.delete("/api/account/photos/" + result_id, headers=b).status_code == 404
    assert client.delete("/api/account/photos/" + result_id, headers=a).status_code == 200
    assert client.get("/api/account/photos/" + result_id, headers=a).status_code == 404
    assert client.post("/api/account/logout", headers=a).status_code == 200
    assert client.get("/api/account/profile", headers=a).status_code == 401
    assert client.get("/api/account/profile", headers=b).status_code == 200


def test_saved_looks_are_customer_owned_and_revocable():
    db = Database()
    app = FastAPI()

    async def chat_reply(conversation_id, profile, prior, message, provider):
        return "Private outfit suggestion"

    app.include_router(configure_account_router(
        db, lambda *args: ("png", "image/png"), lambda data, ext: data,
        lambda *args: "local/fake.png", lambda path: (b"image", "image/png"),
        lambda path: None, generate_chat=chat_reply,
    ))
    client = TestClient(app)
    users = []
    for email in ("saved-a@example.com", "saved-b@example.com"):
        assert client.post("/api/account/register", json={
            "email": email, "password": "secure password for testing"
        }).status_code == 201
        token = client.post("/api/account/login", json={
            "email": email, "password": "secure password for testing"
        }).json()["access_token"]
        users.append({"Authorization": "Bearer " + token})
    alice, bob = users
    assert client.get("/api/account/saved").status_code == 401
    conversation = client.post("/api/account/conversations", headers=alice).json()
    assert client.post(
        "/api/account/conversations/" + conversation["id"] + "/chat",
        headers=alice, json={"message": "Find an outfit"},
    ).status_code == 200
    messages = client.get(
        "/api/account/conversations/" + conversation["id"] + "/messages",
        headers=alice,
    ).json()
    assistant = next(message for message in messages if message["role"] == "assistant")
    url = "/api/account/saved"
    assert client.post(url, headers=bob, json={"message_id": assistant["id"]}).status_code == 404
    assert client.post(url, headers=alice, json={"message_id": messages[0]["id"]}).status_code == 404
    saved = client.post(url, headers=alice, json={"message_id": assistant["id"]})
    assert saved.status_code == 201, saved.text
    saved_id = saved.json()["id"]
    assert saved.json()["content"] == "Private outfit suggestion"
    assert len(client.get(url, headers=alice).json()) == 1
    assert client.get(url, headers=bob).json() == []
    assert client.delete(url + "/" + saved_id, headers=bob).status_code == 404
    assert client.delete(url + "/" + saved_id, headers=alice).status_code == 200
    assert client.get(url, headers=alice).json() == []
    assert client.post("/api/account/logout", headers=alice).status_code == 200
    assert client.get(url, headers=alice).status_code == 401


def test_customer_feedback_is_isolated():
    db = Database()
    app = FastAPI()
    app.include_router(configure_account_router(
        db, lambda *args: ("png", "image/png"), lambda data, ext: data,
        lambda *args: "local/fake.png", lambda path: (b"image", "image/png"),
    ))
    client = TestClient(app)
    users = []
    for email in ("feedback-a@example.com", "feedback-b@example.com"):
        assert client.post("/api/account/register", json={
            "email": email, "password": "secure password for testing"
        }).status_code == 201
        token = client.post("/api/account/login", json={
            "email": email, "password": "secure password for testing"
        }).json()["access_token"]
        users.append({"Authorization": "Bearer " + token})
    alice, bob = users
    assert client.put("/api/account/feedback/item42", json={"sentiment": "liked"}).status_code == 401
    assert client.put("/api/account/feedback/item42", headers=alice,
                      json={"sentiment": "liked"}).status_code == 200
    assert client.get("/api/account/feedback", headers=alice).json() == [
        {"product_id": "item42", "sentiment": "liked"}
    ]
    assert client.get("/api/account/feedback", headers=bob).json() == []
    assert client.put("/api/account/feedback/item42", headers=bob,
                      json={"sentiment": "disliked"}).status_code == 200
    assert client.get("/api/account/feedback", headers=alice).json()[0]["sentiment"] == "liked"
    assert client.get("/api/account/feedback", headers=bob).json()[0]["sentiment"] == "disliked"


def test_expired_session_is_rejected_without_revoking_other_customers():
    from datetime import timedelta
    db = Database()
    app = FastAPI()
    app.include_router(configure_account_router(
        db, lambda *args: ("png", "image/png"), lambda data, ext: data,
        lambda *args: "local/fake.png", lambda path: (b"image", "image/png"),
    ))
    client = TestClient(app)
    headers = []
    for email in ("expiry-a@example.com", "expiry-b@example.com"):
        assert client.post("/api/account/register", json={
            "email": email, "password": "a secure account passphrase"
        }).status_code == 201
        token = client.post("/api/account/login", json={
            "email": email, "password": "a secure account passphrase"
        }).json()["access_token"]
        headers.append({"Authorization": "Bearer " + token})
    a, b = headers
    assert client.get("/api/account/me", headers=a).status_code == 200
    assert client.get("/api/account/me", headers=b).status_code == 200
    digest = token_digest(a["Authorization"].removeprefix("Bearer "))
    for record in db.customer_sessions.docs:
        if record["digest"] == digest:
            record["expires_at"] = datetime.now(timezone.utc) - timedelta(minutes=1)
    assert client.get("/api/account/me", headers=a).status_code == 401
    assert client.get("/api/account/profile", headers=a).status_code == 401
    assert client.get("/api/account/me", headers=b).status_code == 200


def test_browser_cookie_login_csrf_photo_and_logout():
    db = Database()
    app = FastAPI()
    app.include_router(configure_account_router(
        db, lambda *args: ("png", "image/png"), lambda data, ext: data,
        lambda *args: "local/fake.png", lambda path: (b"image", "image/png"),
        lambda path: None,
    ))
    client = TestClient(app, base_url="https://lumiere.example")
    creds = {"email": "browser@example.com", "password": "secure browser testing password"}
    assert client.post("/api/account/register", json=creds).status_code == 201
    login = client.post("/api/account/login", json=creds,
                        headers={"X-Lumiere-Web-Login": "1"})
    assert login.status_code == 200
    assert "access_token" not in login.json()
    assert "httponly" in login.headers["set-cookie"].lower()
    csrf = client.cookies.get("lumiere_csrf")
    assert csrf
    assert client.get("/api/account/me").status_code == 200
    assert client.post("/api/account/photos",
                       files={"file": ("face.png", b"data", "image/png")}).status_code == 403
    headers = {"X-Lumiere-CSRF": csrf}
    upload = client.post("/api/account/photos", headers=headers,
                         files={"file": ("face.png", b"data", "image/png")})
    assert upload.status_code == 201, upload.text
    assert client.get("/api/account/photos/" + upload.json()["id"]).status_code == 200
    assert client.post("/api/account/logout", headers={
        **headers, "Origin": "https://attacker.example"
    }).status_code == 403
    assert client.post("/api/account/logout", headers=headers).status_code == 200
    assert client.get("/api/account/me").status_code == 401


def test_login_rate_limit_after_repeated_failures():
    db = Database()
    app = FastAPI()
    app.include_router(configure_account_router(
        db, lambda *args: ("png", "image/png"), lambda data, ext: data,
        lambda *args: "local/example.png", lambda path: (b"data", "image/png"),
    ))
    client = TestClient(app)
    creds = {"email": "throttle@example.test", "password": "safe password 12345"}
    assert client.post("/api/account/register", json=creds).status_code == 201
    for _ in range(5):
        assert client.post("/api/account/login", json={**creds, "password": "incorrect password"}).status_code == 401
    assert client.post("/api/account/login", json=creds).status_code == 429


def test_recovery_token_single_use_and_revokes_active_sessions(monkeypatch):
    from services import account_routes
    mailed = []
    monkeypatch.setattr(account_routes, "recovery_configured", lambda: True)
    monkeypatch.setattr(account_routes, "send_recovery_email", lambda email, token: mailed.append((email, token)))
    db = Database()
    app = FastAPI()
    app.include_router(configure_account_router(
        db, lambda *args: ("png", "image/png"), lambda data, ext: data,
        lambda *args: "local/example.png", lambda path: (b"data", "image/png"),
    ))
    client = TestClient(app)
    creds = {"email": "recover@example.test", "password": "old password safe 12345"}
    assert client.post("/api/account/register", json=creds).status_code == 201
    session = client.post("/api/account/login", json=creds).json()["access_token"]
    assert client.post("/api/account/recovery/request", json={"email": creds["email"]}).status_code == 200
    assert len(mailed) == 1 and mailed[0][0] == creds["email"]
    reset = {"token": mailed[0][1], "password": "new password safe 12345"}
    assert client.post("/api/account/recovery/confirm", json=reset).status_code == 200
    assert client.post("/api/account/recovery/confirm", json=reset).status_code == 400
    assert client.get("/api/account/me", headers={"Authorization": "Bearer " + session}).status_code == 401
    assert client.post("/api/account/login", json=creds).status_code == 401
    assert client.post("/api/account/login", json={**creds, "password": reset["password"]}).status_code == 200

def test_photo_deletion_clears_skin_wardrobe_and_derived_tryon():
    db = Database()
    deleted_paths = []
    app = FastAPI()
    app.include_router(configure_account_router(
        db, lambda *args: ("png", "image/png"), lambda data, ext: data,
        lambda *args: "local/synthetic.png", lambda path: (b"synthetic", "image/png"),
        lambda path: deleted_paths.append(path),
    ))
    client = TestClient(app)
    creds = {"email": "cascade@example.test", "password": "safe testing password 123"}
    assert client.post("/api/account/register", json=creds).status_code == 201
    login = client.post("/api/account/login", json=creds).json()
    token = {"Authorization": "Bearer " + login["access_token"]}
    face = client.post("/api/account/photos", headers=token,
                       files={"file": ("face.png", b"bytes", "image/png")}).json()["id"]
    generated = client.post("/api/account/photos", headers=token,
                            files={"file": ("tryon.png", b"bytes", "image/png")}).json()["id"]
    client_profile = client.get("/api/account/profile", headers=token).json()
    db.customer_profiles.docs.append({
        "user_id": client_profile["id"], "skin": {"image_path": "private:" + face},
    })
    item = client.post("/api/account/wardrobe", headers=token, json={
        "name": "Test garment", "image_path": "private:" + face,
    }).json()
    db.customer_tryons.docs.append({
        "id": "synthetic-tryon", "user_id": client_profile["id"],
        "person_photo_id": face, "result_photo_id": generated,
        "garment_photo_id": None, "second_garment_photo_id": None, "deleted_at": None,
    })
    assert client.delete("/api/account/photos/" + face, headers=token).status_code == 200
    assert len(deleted_paths) == 2
    assert client.get("/api/account/photos/" + face, headers=token).status_code == 404
    assert client.get("/api/account/photos/" + generated, headers=token).status_code == 404
    assert client.get("/api/account/profile", headers=token).json()["skin"] is None
    items = client.get("/api/account/wardrobe", headers=token).json()
    assert next(v for v in items if v["id"] == item["id"])["image_path"] == ""
    assert client.get("/api/account/tryons", headers=token).json() == []



def test_cross_origin_browser_login_does_not_create_session():
    db = Database()
    app = FastAPI()
    app.include_router(configure_account_router(
        db, lambda *args: ("png", "image/png"), lambda data, ext: data,
        lambda *args: "local/example.png", lambda path: (b"data", "image/png"),
    ))
    client = TestClient(app)
    creds = {"email": "origin-test@example.invalid", "password": "secure password for test 123"}
    assert client.post("/api/account/register", json=creds).status_code == 201
    denied = client.post(
        "/api/account/login", json=creds,
        headers={"X-Lumiere-Web-Login": "1", "Origin": "https://untrusted.example.invalid"},
    )
    assert denied.status_code == 403
    assert db.customer_sessions.docs == []
    assert client.post("/api/account/login", json=creds).status_code == 200


def test_account_export_is_owner_only_and_redacts_storage_paths():
    db = Database()
    app = FastAPI()
    app.include_router(configure_account_router(
        db, lambda *args: ("png", "image/png"), lambda data, ext: data,
        lambda *args: "local/file.png", lambda path: (b"fake", "image/png"), lambda path: None,
    ))
    client = TestClient(app)
    headers = []
    for address in ("alpha@example.com", "beta@example.com"):
        client.post("/api/account/register", json={"email": address, "password": "long secure password"})
        token = client.post("/api/account/login", json={"email": address, "password": "long secure password"}).json()["access_token"]
        headers.append({"Authorization": "Bearer " + token})
    owner_id = client.get("/api/account/me", headers=headers[0]).json()["id"]
    db.customer_photos.docs.append({"id": "a", "user_id": owner_id, "path": "local/private.png"})
    assert client.get("/api/account/account/export").status_code == 401
    alpha = client.get("/api/account/account/export", headers=headers[0])
    beta = client.get("/api/account/account/export", headers=headers[1])
    assert alpha.status_code == 200 and beta.status_code == 200
    assert alpha.headers["cache-control"] == "no-store"
    assert "local/private.png" not in alpha.text
    assert alpha.json()["data"]["photos"][0]["id"] == "a"
    assert beta.json()["data"]["photos"] == []


def test_account_deletion_disabled_by_default_and_preview_safe(monkeypatch):
    monkeypatch.delenv("LUMIERE_ENABLE_ACCOUNT_DELETION", raising=False)
    db = Database()
    app = FastAPI()
    app.include_router(configure_account_router(
        db, lambda *args: ("png", "image/png"), lambda data, ext: data,
        lambda *args: "local/file.png", lambda path: (b"fake", "image/png"), lambda path: None,
    ))
    client = TestClient(app)
    client.post("/api/account/register", json={"email": "temporary@example.com", "password": "long secure password"})
    token = client.post("/api/account/login", json={"email": "temporary@example.com", "password": "long secure password"}).json()["access_token"]
    headers = {"Authorization": "Bearer " + token}
    preview = client.post("/api/account/account/deletion-preview", headers=headers)
    assert preview.status_code == 200
    assert preview.json()["deletion_enabled"] is False
    attempt = client.post("/api/account/account/delete", headers=headers, json={
        "password": "long secure password", "confirmation": "DELETE MY LUMIERE ACCOUNT"
    })
    assert attempt.status_code == 503
    assert client.get("/api/account/me", headers=headers).status_code == 200


def test_deletion_failure_preserves_disposable_account(monkeypatch):
    monkeypatch.setenv("LUMIERE_ENABLE_ACCOUNT_DELETION", "1")
    db = Database()
    app = FastAPI()
    def storage_fails(path):
        raise OSError("storage temporarily unavailable")
    app.include_router(configure_account_router(
        db, lambda *args: ("png", "image/png"), lambda data, ext: data,
        lambda *args: "local/file.png", lambda path: (b"fake", "image/png"), storage_fails,
    ))
    client = TestClient(app)
    client.post("/api/account/register", json={"email": "disposable@example.com", "password": "long secure password"})
    token = client.post("/api/account/login", json={"email": "disposable@example.com", "password": "long secure password"}).json()["access_token"]
    headers = {"Authorization": "Bearer " + token}
    owner_id = client.get("/api/account/me", headers=headers).json()["id"]
    db.customer_photos.docs.append({"id": "temporary-photo", "user_id": owner_id, "path": "local/disposable.png"})
    wrong = client.post("/api/account/account/delete", headers=headers,
                        json={"password": "incorrect password", "confirmation": "DELETE MY LUMIERE ACCOUNT"})
    assert wrong.status_code == 403
    failed = client.post("/api/account/account/delete", headers=headers,
                         json={"password": "long secure password", "confirmation": "DELETE MY LUMIERE ACCOUNT"})
    assert failed.status_code == 503
    assert client.get("/api/account/me", headers=headers).status_code == 200
    assert len(db.customer_photos.docs) == 1


def test_photo_zip_export_never_leaks_other_customer_photos():
    import io
    import uuid
    import zipfile
    db = Database()
    app = FastAPI()
    photo_a = str(uuid.uuid4())
    photo_b = str(uuid.uuid4())
    def owned_read(path):
        return (b"image bytes A" if path == "local/a.png" else b"image bytes B", "image/png")
    app.include_router(configure_account_router(
        db, lambda *args: ("png", "image/png"), lambda data, ext: data,
        lambda *args: "local/image.png", owned_read, lambda path: None,
    ))
    client = TestClient(app)
    tokens = []
    for email in ("export-a@example.com", "export-b@example.com"):
        assert client.post("/api/account/register", json={"email": email, "password": "long secure password"}).status_code == 201
        tokens.append(client.post("/api/account/login", json={"email": email, "password": "long secure password"}).json()["access_token"])
    h_a = {"Authorization": "Bearer " + tokens[0]}
    h_b = {"Authorization": "Bearer " + tokens[1]}
    id_a = client.get("/api/account/me", headers=h_a).json()["id"]
    id_b = client.get("/api/account/me", headers=h_b).json()["id"]
    db.customer_photos.docs.extend([
        {"id": photo_a, "user_id": id_a, "path": "local/a.png"},
        {"id": photo_b, "user_id": id_b, "path": "local/b.png"},
    ])
    assert client.get("/api/account/account/export/photos").status_code == 401
    response = client.get("/api/account/account/export/photos", headers=h_a)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store, private"
    with zipfile.ZipFile(io.BytesIO(response.content)) as zipped:
        assert zipped.namelist() == [f"photos/{photo_a}.png"]
        assert zipped.read(zipped.namelist()[0]) == b"image bytes A"


def test_disposable_account_deletion_removes_only_owned_records(monkeypatch):
    """In-memory deletion success, including token revocation; never touches real storage."""
    monkeypatch.setenv("LUMIERE_ENABLE_ACCOUNT_DELETION", "1")
    db = Database()
    app = FastAPI()
    removed_objects = []
    app.include_router(configure_account_router(
        db, lambda *args: ("png", "image/png"), lambda data, ext: data,
        lambda *args: "local/test.png", lambda path: (b"synthetic", "image/png"),
        lambda path: removed_objects.append(path),
    ))
    client = TestClient(app)
    sessions = []
    for email in ("delete-disposable@example.test", "keep-disposable@example.test"):
        credentials = {"email": email, "password": "test password long enough"}
        assert client.post("/api/account/register", json=credentials).status_code == 201
        token = client.post("/api/account/login", json=credentials).json()["access_token"]
        sessions.append({"Authorization": "Bearer " + token})
    deleted_id = client.get("/api/account/me", headers=sessions[0]).json()["id"]
    kept_id = client.get("/api/account/me", headers=sessions[1]).json()["id"]
    db.customer_photos.docs.extend([
        {"id": "deleted-photo", "user_id": deleted_id, "path": "local/disposable-only.png"},
        {"id": "kept-photo", "user_id": kept_id, "path": "local/other-account.png"},
    ])
    db.customer_tryons.docs.append({"id": "test-tryon", "user_id": deleted_id})
    db.customer_profiles.docs.append({"user_id": deleted_id, "preferences": {}})
    result = client.post("/api/account/account/delete", headers=sessions[0], json={
        "password": "test password long enough",
        "confirmation": "DELETE MY LUMIERE ACCOUNT",
    })
    assert result.status_code == 200
    assert removed_objects == ["local/disposable-only.png"]
    assert client.get("/api/account/me", headers=sessions[0]).status_code == 401
    assert client.get("/api/account/me", headers=sessions[1]).status_code == 200
    assert all(doc.get("user_id") != deleted_id for collection in (
        db.customer_photos, db.customer_tryons, db.customer_profiles, db.customer_sessions,
    ) for doc in collection.docs)
    assert any(doc["user_id"] == kept_id for doc in db.customer_photos.docs)


def test_complete_export_includes_only_owner_records_and_photos():
    import io
    import json
    import uuid
    import zipfile

    db = Database()
    app = FastAPI()
    ids = [str(uuid.uuid4()), str(uuid.uuid4())]
    content = {"test/a": b"synthetic image A", "test/b": b"synthetic image B"}
    app.include_router(configure_account_router(
        db, lambda *args: ("png", "image/png"), lambda data, ext: data,
        lambda *args: "test/a", lambda path: (content[path], "image/png"),
        lambda path: None,
    ))
    client = TestClient(app)
    headers = []
    for email in ("bundle-a@example.test", "bundle-b@example.test"):
        creds = {"email": email, "password": "long test-only password"}
        assert client.post("/api/account/register", json=creds).status_code == 201
        token = client.post("/api/account/login", json=creds).json()["access_token"]
        headers.append({"Authorization": "Bearer " + token})
    owners = [client.get("/api/account/me", headers=h).json()["id"] for h in headers]
    db.customer_photos.docs.extend([
        {"id": ids[0], "user_id": owners[0], "path": "test/a"},
        {"id": ids[1], "user_id": owners[1], "path": "test/b"},
    ])
    db.customer_profiles.docs.extend([
        {"user_id": owners[0], "notes": "synthetic owner A"},
        {"user_id": owners[1], "notes": "synthetic owner B"},
    ])
    uri = "/api/account/account/export/complete"
    assert client.get(uri).status_code == 401
    result = client.get(uri, headers=headers[0])
    assert result.status_code == 200
    assert result.headers["cache-control"] == "private, no-store"
    with zipfile.ZipFile(io.BytesIO(result.content)) as zipped:
        assert set(zipped.namelist()) == {"account.json", f"photos/{ids[0]}.png"}
        assert zipped.read(f"photos/{ids[0]}.png") == content["test/a"]
        data = json.loads(zipped.read("account.json"))
        assert data["format"] == "lumiere-account-export-v2"
        assert data["data"]["profile"][0]["notes"] == "synthetic owner A"
        assert data["data"]["photos"][0]["id"] == ids[0]
        assert "test/a" not in zipped.read("account.json").decode()
        assert owners[1] not in zipped.read("account.json").decode()
    assert any(photo["user_id"] == owners[1] for photo in db.customer_photos.docs)


def test_complete_export_fails_closed_for_missing_photo():
    import uuid
    db = Database()
    app = FastAPI()
    def missing_photo(path):
        raise OSError("Synthetic missing image")
    app.include_router(configure_account_router(
        db, lambda *args: ("png", "image/png"), lambda data, ext: data,
        lambda *args: "test/missing", missing_photo, lambda path: None,
    ))
    client = TestClient(app)
    credentials = {"email": "missing@example.test", "password": "long test-only password"}
    assert client.post("/api/account/register", json=credentials).status_code == 201
    token = client.post("/api/account/login", json=credentials).json()["access_token"]
    headers = {"Authorization": "Bearer " + token}
    user_id = client.get("/api/account/me", headers=headers).json()["id"]
    db.customer_photos.docs.append({
        "id": str(uuid.uuid4()), "user_id": user_id, "path": "test/missing",
    })
    assert client.get("/api/account/account/export/complete", headers=headers).status_code == 503


def test_password_reset_revokes_all_sessions_of_only_target_account(monkeypatch):
    from services import account_routes
    delivered = []
    monkeypatch.setattr(account_routes, "recovery_configured", lambda: True)
    monkeypatch.setattr(account_routes, "send_recovery_email", lambda address, token: delivered.append((address, token)))
    db = Database()
    app = FastAPI()
    app.include_router(configure_account_router(
        db, lambda *args: ("png", "image/png"), lambda data, ext: data,
        lambda *args: "test/photo", lambda path: (b"synthetic", "image/png"),
    ))
    client = TestClient(app)
    creds_a = {"email": "reset-a@example.test", "password": "original test password"}
    creds_b = {"email": "reset-b@example.test", "password": "other account password"}
    for creds in (creds_a, creds_b):
        assert client.post("/api/account/register", json=creds).status_code == 201
    def login(creds):
        return {"Authorization": "Bearer " + client.post("/api/account/login", json=creds).json()["access_token"]}
    a1, a2, b1 = login(creds_a), login(creds_a), login(creds_b)
    assert client.post("/api/account/recovery/request", json={"email": creds_a["email"]}).status_code == 200
    assert len(delivered) == 1
    token = delivered[0][1]
    reset = client.post("/api/account/recovery/confirm", json={
        "token": token, "password": "replacement test password",
    })
    assert reset.status_code == 200
    assert client.get("/api/account/me", headers=a1).status_code == 401
    assert client.get("/api/account/me", headers=a2).status_code == 401
    assert client.get("/api/account/me", headers=b1).status_code == 200
    assert client.post("/api/account/recovery/confirm", json={
        "token": token, "password": "another replacement password",
    }).status_code == 400
    assert client.post("/api/account/login", json=creds_a).status_code == 401
    assert client.post("/api/account/login", json={
        **creds_a, "password": "replacement test password",
    }).status_code == 200


def test_private_bag_requires_owner_variant_and_no_checkout():
    db = Database()
    app = FastAPI()
    async def resolve(user_id, identity):
        if identity == "matterhorn:valid":
            return {"name": "Linen shirt", "brand": "Test",
                    "sizes": ["M", "L"], "colour_names": ["Navy"],
                    "price": 49.0, "currency": "AUD"}
        return None
    app.include_router(configure_account_router(
        db, lambda *args: ("png", "image/png"), lambda data, ext: data,
        lambda *args: "local/test.png", lambda path: (b"synthetic", "image/png"),
        resolve_bag_product=resolve,
    ))
    client = TestClient(app)
    headers = []
    for email in ("bag-a@example.test", "bag-b@example.test"):
        payload = {"email": email, "password": "test-only-password-long"}
        assert client.post("/api/account/register", json=payload).status_code == 201
        token = client.post("/api/account/login", json=payload).json()["access_token"]
        headers.append({"Authorization": "Bearer " + token})
    data = {"product_id": "matterhorn:valid", "size": "M", "colour": "Navy", "quantity": 1}
    assert client.post("/api/account/bag", json=data).status_code == 401
    assert client.post("/api/account/bag", headers=headers[0],
                       json={**data, "size": "XXL"}).status_code == 422
    created = client.post("/api/account/bag", headers=headers[0], json=data)
    assert created.status_code == 201
    assert created.json()["price_snapshot"] == 49.0
    assert created.json()["stock_verified"] is False
    assert client.post("/api/account/bag", headers=headers[0], json=data).status_code == 409
    own = client.get("/api/account/bag", headers=headers[0]).json()
    other = client.get("/api/account/bag", headers=headers[1]).json()
    assert len(own["items"]) == 1 and other["items"] == []
    assert own["checkout_enabled"] is False
    bag_id = created.json()["id"]
    # Quantity mutations must respect ownership, range and existing bag selection.
    assert client.patch("/api/account/bag/" + bag_id, headers=headers[1], json={"quantity": 3}).status_code == 404
    assert client.patch("/api/account/bag/" + bag_id, headers=headers[0], json={"quantity": 0}).status_code == 422
    assert client.patch("/api/account/bag/" + bag_id, headers=headers[0], json={"quantity": True}).status_code == 422
    assert client.patch("/api/account/bag/" + bag_id, headers=headers[0], json={"quantity": 11}).status_code == 422
    updated = client.patch("/api/account/bag/" + bag_id, headers=headers[0], json={"quantity": 3})
    assert updated.status_code == 200 and updated.json()["quantity"] == 3
    assert client.get("/api/account/bag", headers=headers[0]).json()["items"][0]["quantity"] == 3
    assert client.get("/api/account/bag", headers=headers[1]).json()["items"] == []
    assert client.delete("/api/account/bag/" + bag_id, headers=headers[1]).status_code == 404
    assert client.delete("/api/account/bag/" + bag_id, headers=headers[0]).status_code == 200


def test_saved_catalogue_outfits_are_private_and_validate_product_ids():
    db = Database()
    app = FastAPI()
    async def resolve(_user_id, identity):
        return {"name": identity} if identity in {"supplier:item-a", "supplier:item-b"} else None
    app.include_router(configure_account_router(
        db, lambda *args: ("png", "image/png"), lambda data, ext: data,
        lambda *args: "local/test.png", lambda path: (b"synthetic", "image/png"),
        resolve_bag_product=resolve,
    ))
    client = TestClient(app)
    headers = []
    for email in ("outfit-a@example.test", "outfit-b@example.test"):
        payload = {"email": email, "password": "test-only-password-long"}
        assert client.post("/api/account/register", json=payload).status_code == 201
        token = client.post("/api/account/login", json=payload).json()["access_token"]
        headers.append({"Authorization": "Bearer " + token})
    data = {"product_ids": ["supplier:item-a", "supplier:item-b"]}
    assert client.post("/api/account/outfits", json=data).status_code == 401
    assert client.post("/api/account/outfits", headers=headers[0],
                       json={"product_ids": ["supplier:item-a", "supplier:item-a"]}).status_code == 422
    assert client.post("/api/account/outfits", headers=headers[0],
                       json={"product_ids": ["supplier:missing"]}).status_code == 404
    created = client.post("/api/account/outfits", headers=headers[0], json=data)
    assert created.status_code == 201, created.text
    assert created.json()["product_ids"] == data["product_ids"]
    outfit_id = created.json()["id"]
    assert len(client.get("/api/account/outfits", headers=headers[0]).json()) == 1
    assert client.get("/api/account/outfits", headers=headers[1]).json() == []
    # An outfit prepared by another account must remain completely inaccessible.
    assert client.post("/api/account/outfits/" + outfit_id + "/prepare", headers=headers[1]).status_code == 404
    assert client.delete("/api/account/outfits/" + outfit_id, headers=headers[1]).status_code == 404
    assert client.delete("/api/account/outfits/" + outfit_id, headers=headers[0]).status_code == 200
    assert client.get("/api/account/outfits", headers=headers[0]).json() == []


def test_saved_outfit_reopens_with_private_photos_and_keeps_ownership():
    db = Database()
    app = FastAPI()
    async def product(_user, identity):
        if identity in ("matterhorn:hashed-a", "matterhorn:hashed-b"):
            return {"name": "Sample garment", "sizes": ["M"], "colour_names": ["navy"]}
        return None
    async def saved_source(_user, identity):
        item = await product(_user, identity)
        if not item:
            return None
        return {"source_id": "source-a" if identity.endswith("-a") else "source-b",
                "product": item}
    async def supplier_image(source_id):
        assert source_id in {"source-a", "source-b"}
        return b"synthetic-private-garment", "image/png", "Sample garment"
    app.include_router(configure_account_router(
        db, lambda *args: ("png", "image/png"), lambda data, ext: data,
        lambda *args: "local/private.png", lambda path: (b"private", "image/png"),
        prepare_catalogue=supplier_image, resolve_bag_product=product,
        resolve_saved_outfit=saved_source,
    ))
    client = TestClient(app)
    tokens = []
    for email in ("reopen-a@example.test", "reopen-b@example.test"):
        credentials = {"email": email, "password": "test-only-password-long"}
        assert client.post("/api/account/register", json=credentials).status_code == 201
        response = client.post("/api/account/login", json=credentials)
        assert response.status_code == 200
        tokens.append({"Authorization": "Bearer " + response.json()["access_token"]})
    created = client.post("/api/account/outfits", headers=tokens[0],
        json={"product_ids": ["matterhorn:hashed-a", "matterhorn:hashed-b"]})
    assert created.status_code == 201, created.text
    outfit_id = created.json()["id"]
    endpoint = f"/api/account/outfits/{outfit_id}/prepare"
    assert client.post(endpoint, headers=tokens[1]).status_code == 404
    response = client.post(endpoint, headers=tokens[0])
    assert response.status_code == 200, response.text
    garments = response.json()["garments"]
    assert len(garments) == 2
    assert [x["product_id"] for x in garments] == ["matterhorn:hashed-a", "matterhorn:hashed-b"]
    assert all(x["path"].startswith("private:") for x in garments)
    assert all(x["sizes"] == ["M"] and x["colour_names"] == ["navy"] for x in garments)
    assert len(db.customer_photos.docs) == 2
    for photo in db.customer_photos.docs:
        assert photo["user_id"] == db.customer_accounts.docs[0]["id"]
    for garment in garments:
        photo_id = garment["path"].split(":", 1)[1]
        assert client.get(f"/api/account/photos/{photo_id}", headers=tokens[1]).status_code == 404


def test_saved_outfit_reopen_missing_source_returns_conflict_without_creating_photos():
    db = Database()
    app = FastAPI()
    async def product(_user, identity):
        return {"name": "Old blouse"} if identity == "matterhorn:old" else None
    async def missing(_user, identity):
        return None
    async def supplier_image(source):
        raise AssertionError("Missing source should never be fetched")
    app.include_router(configure_account_router(
        db, lambda *args: ("png", "image/png"), lambda data, ext: data,
        lambda *args: "local/private.png", lambda path: (b"private", "image/png"),
        prepare_catalogue=supplier_image, resolve_bag_product=product,
        resolve_saved_outfit=missing,
    ))
    client = TestClient(app)
    credentials = {"email": "missing-outfit@example.test", "password": "test-only-password-long"}
    assert client.post("/api/account/register", json=credentials).status_code == 201
    login = client.post("/api/account/login", json=credentials)
    headers = {"Authorization": "Bearer " + login.json()["access_token"]}
    saved = client.post("/api/account/outfits", headers=headers,
        json={"product_ids": ["matterhorn:old"]})
    assert saved.status_code == 201
    response = client.post(f"/api/account/outfits/{saved.json()['id']}/prepare", headers=headers)
    assert response.status_code == 409
    assert db.customer_photos.docs == []
    assert len(db.customer_outfits.docs) == 1


def test_demo_tryon_private_photo_picker_cache_isolation_and_deletion():
    """No paid repeat generation; saved demos stay private and deletions invalidate cache."""
    db = Database()
    app = FastAPI()
    generated = []

    async def generate(person, garment, second, prompt):
        generated.append(prompt)
        return b"generated output", "image/png"

    app.include_router(configure_account_router(
        db, lambda *args: ("png", "image/png"), lambda data, ext: data,
        lambda *args: "local/private.png",
        lambda path: (b"private image", "image/png"),
        lambda path: None, None, None, generate,
    ))
    client = TestClient(app)
    headers = []
    for email in ("demo-one@example.com", "demo-two@example.com"):
        assert client.post("/api/account/register", json={
            "email": email, "password": "long secure password"
        }).status_code == 201
        login = client.post("/api/account/login", json={
            "email": email, "password": "long secure password"
        })
        headers.append({"Authorization": "Bearer " + login.json()["access_token"]})
    a, b = headers
    assert client.get("/api/account/photos").status_code == 401
    original = client.post("/api/account/photos", headers=a,
                           files={"file": ("person.png", b"original", "image/png")}).json()["id"]
    assert [p["id"] for p in client.get("/api/account/photos", headers=a).json()] == [original]
    assert client.get("/api/account/photos", headers=b).json() == []

    payload = {"person_photo_id": original,
               "garment_prompt": "[LUMIERE-DEMO:outfit-42] navy trousers; white sneakers"}
    first = client.post("/api/account/tryons", headers=a, json=payload)
    assert first.status_code == 201, first.text
    again = client.post("/api/account/tryons", headers=a, json=payload)
    assert again.status_code == 201, again.text
    assert again.json()["id"] == first.json()["id"]
    assert len(generated) == 1
    assert client.get("/api/account/photos", headers=a).json() == [{"id": original}]
    assert client.get("/api/account/tryons", headers=b).json() == []
    assert client.post("/api/account/tryons", headers=b, json=payload).status_code == 404

    changed = {**payload, "garment_prompt": "[LUMIERE-DEMO:outfit-42] grey trousers; white sneakers"}
    assert client.post("/api/account/tryons", headers=a, json=changed).status_code == 201
    assert len(generated) == 2
    assert client.delete("/api/account/tryons/" + first.json()["id"], headers=a).status_code == 200
    assert client.post("/api/account/tryons", headers=a, json=payload).status_code == 201
    assert len(generated) == 3
