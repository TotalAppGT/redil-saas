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

@app.get("/api/health")
def health():
    return {"status": "ok", "version": "7.0"}

# ── PDF DOWNLOAD (HTML→PDF vía weasyprint, idéntico al preview) ──
@app.get("/api/pdf/{no_serie}")
def descargar_pdf(no_serie: str):
    from app.database import SessionLocal
    from app.models import GeneradorReporte, Reporte, Configuracion
    from datetime import datetime
    from fastapi.responses import Response, HTMLResponse
    db = SessionLocal()
    try:
        gr = db.query(GeneradorReporte).filter(GeneradorReporte.no_serie == no_serie).first()
        if not gr: return Response(b"PDF no encontrado",404)
        q = db.query(Reporte)
        if gr.fecha_inicio: q = q.filter(Reporte.fecha >= gr.fecha_inicio)
        if gr.fecha_fin: q = q.filter(Reporte.fecha <= gr.fecha_fin)
        if gr.filtro_lider: q = q.filter(Reporte.lider.ilike(f"%{gr.filtro_lider}%"))
        reportes = q.order_by(Reporte.fecha.desc()).all()
        if not reportes: return Response(b"Sin datos",404)
        # Get config
        sys_nom = "REDIL"
        cfg = db.query(Configuracion).filter(Configuracion.clave=="nombre").first()
        if cfg: sys_nom = cfg.valor
        # Calc stats
        total_g = len(reportes); total_as = sum(r.asistencia or 0 for r in reportes)
        total_of = sum(float(r.ofrenda_total or 0) for r in reportes)
        total_hn = sum(r.hnos or 0 for r in reportes); total_am = sum(r.amigos or 0 for r in reportes)
        total_ni = sum(r.ninos or 0 for r in reportes)
        total_pend = sum(1 for r in reportes if r.ofrenda_recibida in ("Pendiente",""))
        pct = round((total_g-total_pend)/total_g*100,1) if total_g else 0
        desde = str(gr.fecha_inicio or ''); hasta = str(gr.fecha_fin or '')
        titulo = gr.titulo_reporte or "Reporte"; fecha_gen = datetime.now().strftime('%d/%m/%Y %H:%M')
        rango_str = f"{desde or 'Inicio'} \u2192 {hasta or 'Hoy'}"
        # Build matching HTML
        esc = lambda s: str(s or '').replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
        rows = ''.join(f'<tr><td><span class="cod">{esc(str(r.codigo or "")[:10])}</span></td><td><b>{esc(str(r.lider or "")[:30])}</b></td><td>{esc(str(r.fecha)[:10]) if r.fecha else "-"}</td><td>D{esc(str(r.distrito or "?"))} Z{esc(str(r.zona or "?"))}</td><td class="n">{r.asistencia or 0}</td><td class="n">Q{float(r.ofrenda_total or 0):,.2f}</td><td class="n">{r.hnos or 0}</td><td class="n">{r.amigos or 0}</td><td class="{"p" if r.ofrenda_recibida in ("Pendiente","") else "o"}">{"Pendiente" if r.ofrenda_recibida in ("Pendiente","") else "Recibida"}</td></tr>' for r in reportes)
        html = f'<!DOCTYPE html><html><head><meta charset="UTF-8"><link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800;900&display=swap" rel="stylesheet"><style>*{{margin:0;padding:0;box-sizing:border-box}}@page{{size:letter landscape;margin:.28in}}body{{font-family:Inter,-apple-system,sans-serif;background:#fff;color:#2d3436;font-size:9px}}.rpt{{max-width:100%}}.hdr{{background:linear-gradient(135deg,#1a3a5c,#2d6a9f,#3b82c4);color:#fff;padding:12px 18px;display:flex;justify-content:space-between;align-items:flex-start;gap:10px}}.hdr h1{{font-size:16px;font-weight:900}}.hdr .sub{{font-size:8px;opacity:.85;margin-top:2px;line-height:1.3}}.hdr-badge{{background:rgba(255,255,255,.2);padding:5px 12px;border-radius:20px;text-align:center}}.hdr-badge .s{{font-size:10px;font-weight:800}}.hdr-badge .c{{font-size:7px;opacity:.7}}.kpis{{display:grid;grid-template-columns:repeat(4,1fr);gap:5px;padding:10px 16px;background:#f8f9fe;border-bottom:1px solid #eef0f8}}.kpi{{background:#fff;border-radius:7px;padding:9px 11px;box-shadow:0 1px 3px rgba(0,0,0,.05);border-left:3px solid var(--kc)}}.kpi .v{{font-size:15px;font-weight:900;color:var(--kc);line-height:1.1}}.kpi .l{{font-size:7px;color:#8c9bab;font-weight:600;text-transform:uppercase}}.c0{{--kc:#6366f1}}.c1{{--kc:#f59e0b}}.c2{{--kc:#10b981}}.c3{{--kc:#3b82f6}}.c4{{--kc:#ef4444}}.c5{{--kc:#8b5cf6}}.c6{{--kc:#14b8a6}}.c7{{--kc:#f97316}}table{{width:100%;border-collapse:collapse;font-size:8px}}thead th{{background:#1a3a5c;color:#fff;font-size:7px;font-weight:700;text-transform:uppercase;padding:5px 5px;text-align:center}}thead th:first-child{{text-align:left;padding-left:10px}}tbody td{{padding:4px 5px;border-bottom:1px solid #f0f2f5;text-align:center}}tbody td:first-child{{text-align:left;padding-left:10px}}tbody tr:nth-child(even){{background:#fafbfe}}.cod{{font-family:monospace;background:#eef0f8;padding:1px 5px;border-radius:4px;color:#2d6a9f;font-weight:700}}.n{{font-weight:700}}.p{{color:#dc2626;font-weight:700}}.o{{color:#059669;font-weight:700}}.footer{{padding:8px 16px;border-top:2px solid #eef0f8;display:flex;justify-content:space-between;align-items:center;font-size:7.5px;color:#8c9bab}}.footer b{{color:#1a3a5c}}</style></head><body><div class="rpt"><div class="hdr"><div><h1>{esc(sys_nom)}</h1><div class="sub">{esc(titulo)} &mdash; {rango_str} &mdash; {fecha_gen}</div></div><div class="hdr-badge"><div class="s">{no_serie}</div><div class="c">{total_g} grupos</div></div></div><div class="kpis"><div class="kpi c0"><div class="v">{total_g}</div><div class="l">Grupos</div></div><div class="kpi c1"><div class="v">{total_as}</div><div class="l">Asistencia</div></div><div class="kpi c2"><div class="v">Q{total_of:,.2f}</div><div class="l">Ofrenda</div></div><div class="kpi c3"><div class="v">{pct}%</div><div class="l">Recibidas</div></div><div class="kpi c4"><div class="v">{total_pend}</div><div class="l">Pendientes</div></div><div class="kpi c5"><div class="v">{total_hn}</div><div class="l">Hermanos</div></div><div class="kpi c6"><div class="v">{total_am}</div><div class="l">Amigos</div></div><div class="kpi c7"><div class="v">{total_ni}</div><div class="l">Ninos</div></div></div><table><thead><tr><th>Codigo</th><th>Lider</th><th>Fecha</th><th>D-Z</th><th>AGF</th><th>Ofrenda</th><th>Hnos</th><th>Amg</th><th>Estado</th></tr></thead><tbody>{rows}</tbody></table><div class="footer"><div><b>{total_g}</b> reportes &middot; <b>Q{total_of:,.2f}</b></div><div>Daniel Martinez &middot; Total App GT</div></div></div></body></html>'
        try:
            from weasyprint import HTML as WHTML
            pdf_bytes = WHTML(string=html).write_pdf()
            fname = f"{esc(sys_nom)}_{esc(titulo)}_{desde}_{no_serie}.pdf".replace(' ','_').replace('/','-')
            return Response(pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="{fname}"'})
        except Exception as e:
            print(f"[PDF] weasyprint fallback HTML: {e}")
            return HTMLResponse(content=html)
    except Exception as e:
        return Response(f"Error: {e}".encode(),500)
    finally:
        db.close()

@app.get("/form", response_class=HTMLResponse)
async def form_redirect():
    with open("static/formulario_digital.html", "r", encoding="utf-8") as f:
        return f.read()

# Servir frontend
app.mount("/", StaticFiles(directory="static", html=True), name="static")
