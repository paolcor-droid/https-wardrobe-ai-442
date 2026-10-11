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


def test_account_profile_wardrobe_and_photo_access_isolation():
    db = Database()
    app = FastAPI()
    app.include_router(configure_account_router(
        db, lambda *args: ("png", "image/png"),
        lambda data, ext: data, lambda *args: "local/fake.png",
        lambda path: (b"private image", "image/png"),
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
    assert client.put("/api/account/profile", headers=a,
                      json={"notes": "first account"}).status_code == 200
    assert client.get("/api/account/profile", headers=b).json().get("notes") is None
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
    assert client.post("/api/account/logout", headers=a).status_code == 200
    assert client.get("/api/account/me", headers=a).status_code == 401
    assert client.get("/api/account/me", headers=b).status_code == 200
