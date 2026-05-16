from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

load_dotenv()

from config.db import init, close
from controllers import goal as goal_router
from controllers import session as session_router
from utils.stream import ws_endpoint
from security.rate_limiter import limiter

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init()
    yield
    await close()

app = FastAPI(title="AgentSystem", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
)

app.include_router(goal_router.router)
app.include_router(session_router.router)
app.add_api_websocket_route("/ws/{goal_id}", ws_endpoint)
app.mount("/static", StaticFiles(directory="static"), name="static")
