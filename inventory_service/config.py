import os
from dotenv import load_dotenv

load_dotenv() # Load .env file from project root if running locally

DATABASE_USER = os.getenv("POSTGRES_USER", "user")
DATABASE_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
DATABASE_HOST = os.getenv("POSTGRES_HOST", "postgres") # Docker service name
DATABASE_PORT = os.getenv("POSTGRES_PORT", "5432")
DATABASE_NAME = os.getenv("POSTGRES_DB", "food_delivery_db")

# Async database URL for SQLAlchemy
DATABASE_URL = f"postgresql+asyncpg://{DATABASE_USER}:{DATABASE_PASSWORD}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}"

# For Uvicorn binding inside container
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "8001"))