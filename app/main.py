from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from app.database import engine, Base, SessionLocal
from app.routers import reportes, hermanos, seguimientos, auth, telegram, dispatch
from app.models import Usuario
import bcrypt
import os

# Crear tablas en BD
Base.metadata.create_all(bind=engine)

# Migración: agregar columnas nuevas si no existen
try:
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    cols_u = [c["name"] for c in inspector.get_columns("usuarios")]
    cols_r = [c["name"] for c in inspector.get_columns("reportes")]
    cols_g = [c["name"] for c in inspector.get_columns("gastos")]
    with engine.connect() as conn:
        if "menu_permitido" not in cols_u:
            conn.execute(text("ALTER TABLE usuarios ADD COLUMN menu_permitido TEXT"))
        if "puede_ver_bitacora" not in cols_u:
            conn.execute(text("ALTER TABLE usuarios ADD COLUMN puede_ver_bitacora BOOLEAN DEFAULT TRUE"))
        for col in ["hora_inicio","hora_final","ofrenda_iglesia","ofrenda_bus","martes","jueves","domingo","otros","total_cultos","reporte_origen","sup_sector","sup_area","pastor_zona","anfitrion","seguimientos_count"]:
            if col not in cols_r:
                t = "INTEGER DEFAULT 0" if col in ("martes","jueves","domingo","otros","total_cultos","seguimientos_count") else "NUMERIC(12,2) DEFAULT 0" if col in ("ofrenda_iglesia","ofrenda_bus") else "VARCHAR(200) DEFAULT ''"
                conn.execute(text(f"ALTER TABLE reportes ADD COLUMN {col} {t}"))
        if "direccion" not in cols_r:
            conn.execute(text("ALTER TABLE reportes ADD COLUMN direccion TEXT DEFAULT ''"))
        if "evento" not in cols_g:
            conn.execute(text("ALTER TABLE gastos ADD COLUMN evento VARCHAR(200) DEFAULT ''"))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS bautizos (
                id SERIAL PRIMARY KEY,
                fecha DATE,
                nombre VARCHAR(200),
                edad INTEGER DEFAULT 0,
                telefono VARCHAR(50),
                direccion TEXT,
                pastor_oficiante VARCHAR(200),
                lugar VARCHAR(200),
                observaciones TEXT,
                activo BOOLEAN DEFAULT TRUE,
                timestamp TIMESTAMP DEFAULT NOW()
            )
        """))
        conn.commit()
except Exception as e:
    print(f"⚠️ Migración: {e}")

# Seed: crear admin por defecto
try:
    db = SessionLocal()
    admin = db.query(Usuario).filter(Usuario.email == "totalappgt@gmail.com").first()
    if not admin:
        admin = Usuario(
            nombre="TotalAppGT",
            email="totalappgt@gmail.com",
            password=bcrypt.hashpw("admintotal".encode(), bcrypt.gensalt()).decode(),
            rol="propietario",
            activo=True,
            menu_permitido=None,
            puede_ver_bitacora=True
        )
        db.add(admin)
        db.commit()
        print("✅ Admin creado: totalappgt@gmail.com")
    db.close()
except Exception as e:
    print(f"⚠️ Seed admin: {e}")

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
app.include_router(dispatch.router, prefix="/api", tags=["Dispatch"])

# Crear directorio para PDFs
os.makedirs("static/pdfs", exist_ok=True)

@app.get("/api/health")
def health():
    return {"status": "ok", "version": "7.0"}

@app.get("/form", response_class=HTMLResponse)
async def form_redirect():
    with open("static/formulario_digital.html", "r", encoding="utf-8") as f:
        return f.read()

# Servir frontend
app.mount("/", StaticFiles(directory="static", html=True), name="static")
