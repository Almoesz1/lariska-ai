from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import dashboard_api
from app.core.config import settings

app = FastAPI(title="LARISKA AI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard_api.router)


@app.get("/health")
def health():
    return {"status": "ok", "environment": settings.environment}