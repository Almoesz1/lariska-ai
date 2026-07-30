import logging
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

# Import Core Config
from app.core.config import settings

# Import API Routers
from app.api.dashboard_api import router as dashboard_router
from app.api.payment_webhook import router as payment_router
from app.api.whatsapp_webhook import router as whatsapp_router
from app.api.sales_brain_api import router as sales_brain_router
from app.api.bridge_api import router as bridge_router


# ============================================================
# LOGGING SETUP
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("lariska-ai")


# ============================================================
# FASTAPI APP INITIALIZATION
# ============================================================
app = FastAPI(
    title="LARISKA AI Backend Engine",
    description="Core API Service for LARISKA AI — WhatsApp Sales Brain & Analytics",
    version="1.0.0"
)

# CORS Origins Configuration (Next.js / Vite / Local React)
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# REGISTER ROUTERS
# ============================================================
app.include_router(dashboard_router)
app.include_router(whatsapp_router)
app.include_router(payment_router)
app.include_router(sales_brain_router)
app.include_router(bridge_router)


# ============================================================
# GLOBAL EXCEPTION HANDLERS
# ============================================================

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    logger.warning(f"HTTPException [{exc.status_code}]: {exc.detail} at {request.url}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"ValidationError: {exc.errors()} at {request.url}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Validasi data gagal", "errors": exc.errors()},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled Exception: {str(exc)} at {request.url}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Terjadi kesalahan internal pada server. Silakan coba lagi nanti."},
    )


# ============================================================
# BASE & HEALTH CHECK ENDPOINTS
# ============================================================

@app.get("/", tags=["Health Check"])
def root():
    return {
        "message": "LARISKA AI Engine is Active 🚀",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", tags=["Health Check"])
def health():
    env_name = getattr(settings, "environment", "development")
    return {
        "status": "ok",
        "environment": env_name
    }