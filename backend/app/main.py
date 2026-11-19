import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import Base, engine
from .routers import admin, chat, requests, vapi_webhook

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

Base.metadata.create_all(bind=engine)  # swap for Alembic migrations once the schema settles

app = FastAPI(title="RentVoice API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(requests.router)
app.include_router(vapi_webhook.router)
app.include_router(chat.router)
app.include_router(admin.router)


@app.get("/health")
def health():
    return {"ok": True}
