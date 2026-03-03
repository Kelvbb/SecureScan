from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, fixes, health, owasp, scans, users, vulnerabilities
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="API d'analyse de sécurité du code — SecureScan",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(scans.router, prefix="/api/scans", tags=["scans"])
app.include_router(
    vulnerabilities.router, prefix="/api/vulnerabilities", tags=["vulnerabilities"]
)
app.include_router(owasp.router, prefix="/api/owasp", tags=["owasp"])
app.include_router(fixes.router, prefix="/api", tags=["Remediation"])


@app.get("/")
def root():
    return {"message": "SecureScan API", "docs": "/docs"}
