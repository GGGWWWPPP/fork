import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from routers import router
from database import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Инициализация БД при старте
    init_db()
    yield


app = FastAPI(title="Node Connect API", version="2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(router, prefix="/api")

# Serve static frontend
app.mount("/", StaticFiles(directory="/app/static", html=True), name="static")
