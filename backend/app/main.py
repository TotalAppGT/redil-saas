from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.routers import reportes, hermanos, seguimientos, auth, telegram
import os

# Crear tablas en BD
Base.metadata.create_all(bind=engine)

app = FastAPI(title="REDIL API", version="7.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(hermanos.router, prefix="/api/hermanos", tags=["Hermanos"])
app.include_router(reportes.router, prefix="/api/reportes", tags=["Reportes"])
app.include_router(seguimientos.router, prefix="/api/seguimientos", tags=["Seguimientos"])
app.include_router(telegram.router, prefix="/api/telegram", tags=["Telegram"])

@app.get("/api/health")
def health():
    return {"status": "ok", "version": "7.0"}
