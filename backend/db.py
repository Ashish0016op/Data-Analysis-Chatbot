import os

from dotenv import load_dotenv
from pymongo import AsyncMongoClient
from pymongo.errors import PyMongoError
from pymongo.server_api import ServerApi

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI") or os.getenv("MONGO_URL")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "data_analytics")
MONGO_TIMEOUT_MS = int(os.getenv("MONGO_TIMEOUT_MS", "15000"))

if not MONGO_URI:
    raise RuntimeError("MONGO_URI or MONGO_URL must be set in backend/.env")

client = AsyncMongoClient(
    MONGO_URI,
    server_api=ServerApi("1"),
    serverSelectionTimeoutMS=MONGO_TIMEOUT_MS,
)
db = client[MONGO_DB_NAME]

users_collection = db["users"]

_mongo_status = {
    "connected": False,
    "database": MONGO_DB_NAME,
    "error": None,
}


async def ping_mongo(raise_on_error: bool = True) -> bool:
    try:
        await client.admin.command("ping")
        _mongo_status["connected"] = True
        _mongo_status["error"] = None
        print(f"MongoDB connected successfully | database: {MONGO_DB_NAME}")
        return True
    except PyMongoError as exc:
        _mongo_status["connected"] = False
        _mongo_status["error"] = str(exc)
        print(f"MongoDB connection failed: {exc}")
        if raise_on_error:
            raise RuntimeError(f"MongoDB connection failed: {exc}") from exc
        return False


def get_mongo_status() -> dict:
    return _mongo_status.copy()


async def close_mongo_connection() -> None:
    await client.close()
