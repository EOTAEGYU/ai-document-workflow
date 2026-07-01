import os

from dotenv import load_dotenv

load_dotenv()

APP_DB_HOST = os.getenv("APP_DB_HOST", "localhost")
APP_DB_PORT = os.getenv("APP_DB_PORT", "5432")
APP_DB_NAME = os.getenv("APP_DB_NAME", "app_db")
APP_DB_USER = os.getenv("APP_DB_USER", "postgres_user")
APP_DB_PASSWORD = os.getenv("APP_DB_PASSWORD", "postgres_password")

DATABASE_URL = (
    f"postgresql+psycopg2://{APP_DB_USER}:{APP_DB_PASSWORD}"
    f"@{APP_DB_HOST}:{APP_DB_PORT}/{APP_DB_NAME}"
)

TEMPORAL_ADDRESS = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
TEMPORAL_TASK_QUEUE = os.getenv("TEMPORAL_TASK_QUEUE", "document-processing")

STORAGE_DIR = os.getenv("STORAGE_DIR", "./storage")
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "20"))
