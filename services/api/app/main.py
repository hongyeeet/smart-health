"""FastAPI app entry point (architecture.md: the backend skeleton).

Run locally:
    cd services/api
    uvicorn app.main:app --reload --port 8000

The Vite dev server proxies /api → http://localhost:8000 (apps/web/vite.config.ts).
"""
import logging

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers.logs import router as logs_router
from app.api.routers.meals import router as meals_router
from app.api.routers.notifications import router as notifications_router
from app.api.routers.workouts import router as workouts_router
from app.api.routers.memory import router as memory_router
from app.api.routers.nutrition import router as nutrition_router
from app.api.routers.scans import router as scans_router
from app.core.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

async def _act_as(x_user: str | None = Header(default=None)) -> None:
    """Who this request acts as: the `X-User` header ("demo" or "mr-tan"; none means demo). Async on purpose, so the choice
    is set in the same context the endpoint (and its threadpool work) runs in."""
    from app.db import logstore

    try:
        logstore.set_user(x_user)
    except KeyError:
        raise HTTPException(400, f"unknown user {x_user!r}; choose one of: {', '.join(logstore.USERS)}")


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    dependencies=[Depends(_act_as)],
)

# CORS: allow the web app and mock
origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "demo_mode": settings.demo_mode}


@app.get("/api/v1/users")
async def users() -> dict:
    """The people the app can act as, and which one this request is for (the switcher in the app reads this)."""
    from app.db import logstore

    return {
        "current": logstore.current_user_key(),
        "users": [{"key": k, "label": v["label"], "sub": v["sub"]} for k, v in logstore.USERS.items()],
    }


# Routes are mounted under /api/v1 (architecture.md 7)
app.include_router(scans_router, prefix="/api/v1")
app.include_router(logs_router, prefix="/api/v1")
app.include_router(meals_router, prefix="/api/v1")
app.include_router(workouts_router, prefix="/api/v1")
app.include_router(notifications_router, prefix="/api/v1")
app.include_router(nutrition_router, prefix="/api/v1")
app.include_router(memory_router, prefix="/api/v1")


@app.on_event("startup")
def _ensure_demo_user() -> None:
    """The app has no sign-in yet: a request is the demo user unless it names Mr Tan (X-User header); only the demo user is created here."""
    from app.db import logstore
    from app.services import scheduler

    try:
        logstore.ensure_user()
        scheduler.start()
    except Exception:  # database unreachable: the log endpoints will report it when called
        logger.exception("could not create the demo user")

logger.info("FastAPI app started. Demo mode: %s", settings.demo_mode)
