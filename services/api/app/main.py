"""FastAPI app entry point (architecture.md: the backend skeleton).

Run locally:
    cd services/api
    uvicorn app.main:app --reload --port 8000

The Vite dev server proxies /api → http://localhost:8000 (apps/web/vite.config.ts).
"""
import logging
import re

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers.brief import router as brief_router
from app.api.routers.insights import router as insights_router
from app.api.routers.day import router as day_router
from app.api.routers.care import router as care_router
from app.api.routers.me_settings import router as me_settings_router
from app.api.routers.share import router as share_router
from app.api.routers.onboarding import router as onboarding_router
from app.api.routers.users import router as users_router
from app.api.routers.urgent import router as urgent_router
from app.api.routers.notify import router as notify_router
from app.api.routers.chat import router as chat_router
from app.api.routers.review import router as review_router
from app.api.routers.calendar import router as calendar_router
from app.api.routers.doses import router as doses_router
from app.api.routers.interactions import router as interactions_router
from app.api.routers.logs import router as logs_router
from app.api.routers.med_explain import router as med_explain_router
from app.api.routers.medications import router as medications_router
from app.api.routers.med_stock import router as med_stock_router
from app.api.routers.meals import router as meals_router
from app.api.routers.notifications import router as notifications_router
from app.api.routers.workouts import router as workouts_router
from app.api.routers.memory import router as memory_router
from app.api.routers.nutrition import router as nutrition_router
from app.api.routers.home import router as home_router
from app.api.routers.scans import router as scans_router
from app.core.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# What a visitor may still send while looking at Mr Tan's example record. None of these changes what is kept for him in a way another visitor
# would notice: asking the assistant, reading a meal photo or a typed answer, and noting that a reminder was opened.
EXAMPLE_MAY_SEND = ("/api/v1/chat/", "/api/v1/meals/analyze", "/api/v1/onboarding/chat", "/api/v1/users")
EXAMPLE_MAY_SEND_RE = re.compile(r"/api/v1/notifications/[^/]+/open")
EXAMPLE_REFUSED = "Mr Tan is an example record, so it cannot be changed. Create your own user to log your own information."


async def _act_as(request: Request, x_user: str | None = Header(default=None), x_lang: str | None = Header(default=None)) -> None:
    """Who this request acts as: the `X-User` header ("mr-tan", or the key of a person started in the app; none means Mr Tan). Async on purpose,
    so the choice is set in the same context the endpoint (and its threadpool work) runs in. Mr Tan's record is shown to everyone and is
    never changed by a request: anything that would write is refused in plain words."""
    from app.db import logstore
    from app.services import texts

    texts.set_request_language((x_lang or "").strip().lower() or None)    # the language the person chose in the app, for wording the server builds
    try:
        logstore.set_user(x_user)
    except KeyError:
        raise HTTPException(400, f"unknown user {x_user!r}; use mr-tan or a key from Start as new person")
    if logstore.is_read_only(logstore.current_user()) and request.method not in ("GET", "HEAD", "OPTIONS"):
        path = request.url.path
        if not (path.startswith(EXAMPLE_MAY_SEND) or EXAMPLE_MAY_SEND_RE.fullmatch(path)):
            raise HTTPException(403, EXAMPLE_REFUSED)


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
app.include_router(medications_router, prefix="/api/v1")
app.include_router(med_stock_router, prefix="/api/v1")
app.include_router(med_explain_router, prefix="/api/v1")
app.include_router(doses_router, prefix="/api/v1")
app.include_router(interactions_router, prefix="/api/v1")
app.include_router(calendar_router, prefix="/api/v1")
app.include_router(meals_router, prefix="/api/v1")
app.include_router(workouts_router, prefix="/api/v1")
app.include_router(notifications_router, prefix="/api/v1")
app.include_router(nutrition_router, prefix="/api/v1")
app.include_router(home_router, prefix="/api/v1")
app.include_router(memory_router, prefix="/api/v1")
app.include_router(brief_router, prefix="/api/v1")
app.include_router(insights_router, prefix="/api/v1")
app.include_router(day_router, prefix="/api/v1")
app.include_router(care_router, prefix="/api/v1")
app.include_router(me_settings_router, prefix="/api/v1")
app.include_router(share_router, prefix="/api/v1")
app.include_router(onboarding_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(urgent_router, prefix="/api/v1")
app.include_router(notify_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(review_router, prefix="/api/v1")


@app.on_event("startup")
def _start_scheduler() -> None:
    """The app has no sign-in yet: a request is Mr Tan's example record unless it names a person started in the app (X-User header)."""
    from app.services import scheduler

    try:
        scheduler.start()
    except Exception:  # database unreachable: the log endpoints will report it when called
        logger.exception("could not start the scheduler")

logger.info("FastAPI app started. Demo mode: %s", settings.demo_mode)
