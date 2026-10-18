import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock, patch


# ── Override settings before the app imports them ────────────────────────────
import os
os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017")
os.environ.setdefault("SECRET_KEY", "test-secret-key-that-is-long-enough-for-validation")
os.environ.setdefault("DATABASE_NAME", "Verath_test")


from app.main import app
from app.services.auth import create_access_token, create_refresh_token


# ── Event loop ────────────────────────────────────────────────────────────────
# In modern pytest-asyncio with asyncio_mode=auto, defining a session-scoped
# event_loop fixture breaks loop isolation across test modules and causes
# 'coroutine was never awaited' warnings. pytest-asyncio manages loops automatically.


# ── HTTP client ───────────────────────────────────────────────────────────────
@pytest_asyncio.fixture
async def client():
    """Async test client wired directly to the FastAPI app — no real server needed."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac


# ── Auth helpers ──────────────────────────────────────────────────────────────
@pytest.fixture
def test_username():
    return "test_user"


@pytest.fixture
def access_token(test_username):
    return create_access_token(test_username)


@pytest.fixture
def refresh_token(test_username):
    return create_refresh_token(test_username)


@pytest.fixture
def auth_headers(access_token):
    return {"Authorization": f"Bearer {access_token}"}


class _async_cursor:
    """Minimal async cursor that yields from a list."""
    def __init__(self, items):
        self._items = iter(items)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self._items)
        except StopIteration:
            raise StopAsyncIteration

    def sort(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self


class _MockCollection:
    def __init__(self):
        self._docs = {}
        self.insert_one = AsyncMock(side_effect=self._insert_one)
        self.find_one = AsyncMock(side_effect=self._find_one)
        self.update_one = AsyncMock(side_effect=self._update_one)
        self.delete_one = AsyncMock(side_effect=self._delete_one)
        self.count_documents = AsyncMock(side_effect=self._count_documents)
        self.find = MagicMock(side_effect=self._find)
        self.aggregate = MagicMock(return_value=_async_cursor([]))
        self.create_index = AsyncMock(return_value="idx")
        self.distinct = AsyncMock(side_effect=self._distinct)

    def _get_key(self, query):
        if not isinstance(query, dict):
            return str(query)
        if "username" in query:
            return f"user:{query['username']}"
        if "user_id" in query:
            return f"user:{query['user_id']}"
        if "_id" in query:
            return f"id:{query['_id']}"
        if "jti" in query:
            return f"jti:{query['jti']}"
        return str(sorted(query.items()))

    async def _insert_one(self, doc):
        doc = dict(doc)
        if "_id" not in doc:
            doc["_id"] = "mock_id_" + str(len(self._docs))
        key = self._get_key(doc)
        self._docs[key] = doc
        return MagicMock(inserted_id=doc["_id"])

    async def _find_one(self, query=None, projection=None):
        if not query:
            return next(iter(self._docs.values()), None)
        key = self._get_key(query)
        doc = self._docs.get(key)
        if doc is None:
            for d in self._docs.values():
                if all(d.get(k) == v for k, v in query.items() if not k.startswith("$")):
                    doc = d
                    break
        if doc and projection:
            return {k: doc[k] for k in projection if k in doc}
        return doc

    async def _update_one(self, query, update, upsert=False):
        key = self._get_key(query)
        doc = self._docs.get(key)
        if doc is None:
            if upsert:
                doc = {k: v for k, v in query.items() if not k.startswith("$")}
                self._docs[key] = doc
            else:
                return MagicMock(modified_count=0)
        
        if "$set" in update:
            doc.update(update["$set"])
        return MagicMock(modified_count=1)

    async def _delete_one(self, query):
        key = self._get_key(query)
        existed = self._docs.pop(key, None) is not None
        return MagicMock(deleted_count=1 if existed else 0)

    async def _count_documents(self, query=None):
        if not query:
            return len(self._docs)
        count = sum(
            1 for d in self._docs.values()
            if all(d.get(k) == v for k, v in query.items() if not k.startswith("$"))
        )
        return count

    def _find(self, query=None, *args, **kwargs):
        if not query:
            return _async_cursor(list(self._docs.values()))
        matches = [
            d for d in self._docs.values()
            if all(d.get(k) == v for k, v in query.items() if not k.startswith("$"))
        ]
        return _async_cursor(matches)

    async def _distinct(self, field, query=None):
        docs = self._docs.values()
        if query:
            docs = [d for d in docs if all(d.get(k) == v for k, v in query.items() if not k.startswith("$"))]
        vals = {d[field] for d in docs if field in d}
        return list(vals)


class _MockDB:
    _shared_cols = {}

    def __init__(self):
        self._cols = _MockDB._shared_cols

    def __getitem__(self, name):
        if name not in self._cols:
            self._cols[name] = _MockCollection()
        return self._cols[name]

    def __getattr__(self, name):
        return self[name]

    async def command(self, *args, **kwargs):
        return {"ok": 1}


@pytest.fixture(autouse=True)
def default_db_mock(monkeypatch):
    mock_db_instance = _MockDB()
    from app.services import database
    monkeypatch.setattr(database, "get_db", lambda: mock_db_instance)
    monkeypatch.setattr(database.db_instance, "db", mock_db_instance)
    return mock_db_instance


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    from app.routes.auth import limiter
    try:
        limiter._storage.reset()
    except Exception:
        pass
    yield
    try:
        limiter._storage.reset()
    except Exception:
        pass


@pytest.fixture
def mock_db(default_db_mock):
    """
    Patches all MongoDB collections used in services so tests never
    touch a real database.
    """
    return default_db_mock["memories"]


# ── ChromaDB mock ─────────────────────────────────────────────────────────────
@pytest.fixture
def mock_chroma(monkeypatch):
    """Prevents ChromaDB from touching disk during tests."""
    mock_col = MagicMock()
    mock_col.upsert = MagicMock()
    mock_col.query = MagicMock(return_value={
        "ids": [["mem_1", "mem_2"]],
        "documents": [["Memory about a meeting", "Memory about a deadline"]],
        "metadatas": [[
            {"intent": "meeting", "speaker": "unknown", "importance": 0.8,
             "lifecycle": "short_term", "timestamp": "2024-01-15T15:00:00", "user_id": "test_user"},
            {"intent": "deadline", "speaker": "unknown", "importance": 0.9,
             "lifecycle": "short_term", "timestamp": "2024-01-16T09:00:00", "user_id": "test_user"},
        ]],
        "distances": [[0.1, 0.2]],
    })
    mock_col.count = MagicMock(return_value=2)
    mock_col.delete = MagicMock()
    mock_col.get = MagicMock(return_value={"ids": [], "metadatas": [], "documents": [], "embeddings": []})

    monkeypatch.setattr(
        "app.services.memory_store._get_collection",
        lambda user_id: mock_col
    )
    return mock_col


# ── Embedding mock ────────────────────────────────────────────────────────────
@pytest.fixture
def mock_embedding(monkeypatch):
    """Returns a deterministic fake embedding so tests don't call Gemini."""
    monkeypatch.setattr(
        "app.services.gemini_embedding.get_embedding",
        lambda text: [0.1] * 768
    )
    monkeypatch.setattr(
        "app.services.memory_store.get_embedding",
        lambda text: [0.1] * 768
    )
