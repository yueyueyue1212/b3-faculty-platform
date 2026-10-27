"""Application configuration loaded from environment variables."""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# When frozen by PyInstaller, keep writable data next to the executable and
# read bundled assets (the built frontend) from the extraction directory.
IS_FROZEN = bool(getattr(sys, "frozen", False))
if IS_FROZEN:
    BASE_DIR = Path(sys.executable).resolve().parent
    BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", BASE_DIR))
else:
    BASE_DIR = Path(__file__).resolve().parent.parent
    BUNDLE_DIR = BASE_DIR.parent

load_dotenv(BASE_DIR / ".env")

DATA_DIR = Path(os.getenv("DATA_DIR", str(BASE_DIR / "data")))
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR = Path(os.getenv("LOG_DIR", str(BASE_DIR / "logs")))

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{(DATA_DIR / 'app.db').as_posix()}")
SECRET_KEY = os.getenv("SECRET_KEY", "b3-dev-secret-key-change-me-in-production")
TOKEN_EXPIRE_MINUTES = int(os.getenv("TOKEN_EXPIRE_MINUTES", "720"))
CORS_ORIGINS = [o.strip() for o in os.getenv(
    "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
).split(",") if o.strip()]

# LLM / embedding service (OpenAI-compatible endpoint). All optional.
LLM_API_KEY = os.getenv("LLM_API_KEY", "").strip()
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "20"))
LLM_RETRIES = int(os.getenv("LLM_RETRIES", "2"))
LLM_ALLOW_PERSONAL_DATA = os.getenv("LLM_ALLOW_PERSONAL_DATA", "false").lower() == "true"

EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY", "").strip()
EMBEDDING_BASE_URL = os.getenv("EMBEDDING_BASE_URL", LLM_BASE_URL).rstrip("/")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_TIMEOUT = float(os.getenv("EMBEDDING_TIMEOUT", "15"))

MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(5 * 1024 * 1024)))
ALLOWED_UPLOAD_SUFFIXES = {".csv", ".xlsx"}

DEFAULT_ADVISOR_WEIGHTS = {
    "direction": 0.40,
    "topic": 0.25,
    "needs": 0.20,
    "capacity": 0.15,
}
DEFAULT_CANDIDATE_WEIGHTS = {
    "direction": 0.45,
    "outputs": 0.25,
    "projects": 0.20,
    "teaching": 0.10,
}

APP_VERSION = "1.0.0"
AUTO_SEED_ON_STARTUP = os.getenv("AUTO_SEED_ON_STARTUP", "true").lower() == "true"

