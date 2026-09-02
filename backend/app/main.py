from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers import users, schemes, partners, applications
from app.routers import engine as engine_router
from app.routers import ocr as ocr_router
from app.routers import digilocker as digilocker_router
from app.routers import auth as auth_router

# Create all tables on startup
Base.metadata.create_all(bind=engine)

# Seed database on startup if empty
import sys
from pathlib import Path
seed_path = str(Path(__file__).parent.parent)
if seed_path not in sys.path:
    sys.path.insert(0, seed_path)

try:
    import seed
except Exception as e:
    print(f"Failed to run seed script: {e}")

app = FastAPI(
    title="UdyamSetu API",
    description="Backend for UdyamSetu – NSFDC loan scheme recommendation & management platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS – allow all origins for production deployment
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router,        prefix="/api/v1")
app.include_router(schemes.router,      prefix="/api/v1")
app.include_router(partners.router,     prefix="/api/v1")
app.include_router(applications.router, prefix="/api/v1")
app.include_router(ocr_router.router,        prefix="/api/v1")
app.include_router(digilocker_router.router, prefix="/api/v1")
app.include_router(auth_router.router,       prefix="/api/v1")
app.include_router(engine_router.router)  # mounts at /api/match-scheme, /api/calculate-emi, /api/find-partners


@app.get("/", tags=["health"])
def root():
    return {"status": "ok", "message": "UdyamSetu API is running"}


@app.get("/health", tags=["health"])
def health():
    return {"status": "healthy"}
