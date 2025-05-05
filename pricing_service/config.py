import os
from dotenv import load_dotenv

load_dotenv() # Optional: Load .env file

APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "8002")) # Port for this service