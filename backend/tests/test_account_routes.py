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
        self.customer_profiles = Collection()
        self.customer_wardrobe = Collection()
        self.customer_photos = Collection()
        self.customer_feedback = Collection()
        self.customer_conversations = Collection()
        self.customer_messages = Collection()
        self.customer_tryons = Collection()


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
    async def generate(person, garment, prompt):
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
