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

# ── PDF DOWNLOAD ENDPOINT ──
@app.get("/api/pdf/{no_serie}")
def descargar_pdf(no_serie: str):
    from app.database import SessionLocal
    from app.models import GeneradorReporte, Reporte, Configuracion
    from fpdf import FPDF
    from io import BytesIO
    from datetime import datetime
    from fastapi.responses import Response
    db = SessionLocal()
    try:
        gr = db.query(GeneradorReporte).filter(GeneradorReporte.no_serie == no_serie).first()
        if not gr:
            return Response(content=b"PDF no encontrado", status_code=404)
        # Re-query data
        q = db.query(Reporte)
        if gr.fecha_inicio: q = q.filter(Reporte.fecha >= gr.fecha_inicio)
        if gr.fecha_fin: q = q.filter(Reporte.fecha <= gr.fecha_fin)
        if gr.filtro_lider: q = q.filter(Reporte.lider.ilike(f"%{gr.filtro_lider}%"))
        if gr.filtro_sup_sector: q = q.filter(Reporte.sup_sector.ilike(f"%{gr.filtro_sup_sector}%"))
        reportes = q.order_by(Reporte.fecha.desc()).all()
        if not reportes:
            return Response(content=b"Sin datos", status_code=404)
        # Get system name
        sys_nom = "REDIL"
        cfg = db.query(Configuracion).filter(Configuracion.clave=="nombre").first()
        if cfg: sys_nom = cfg.valor
        # Build PDF
        def c(s): return str(s or '').encode('latin-1','replace').decode('latin-1')
        total_g = len(reportes)
        total_as = sum(r.asistencia or 0 for r in reportes)
        total_of = sum(float(r.ofrenda_total or 0) for r in reportes)
        total_pend = sum(1 for r in reportes if r.ofrenda_recibida in ("Pendiente",""))
        pct = round((total_g-total_pend)/total_g*100,1) if total_g else 0
        desde = str(gr.fecha_inicio or '')
        hasta = str(gr.fecha_fin or '')
        rango = f"{desde} -> {hasta}"
        pdf = FPDF('L', 'mm', 'Letter')
        pdf.add_page()
        pdf.set_fill_color(26,58,92); pdf.rect(0,0,279,20,'F')
        pdf.set_text_color(255,255,255); pdf.set_font('Helvetica','B',12)
        pdf.set_xy(11,4); pdf.cell(257,7,c(sys_nom),0,0,'L')
        pdf.set_font('Helvetica','',7); pdf.set_xy(11,11)
        pdf.cell(257,5,c(f'{gr.titulo_reporte or "Reporte"}  |  {rango}  |  {datetime.now().strftime("%d/%m/%Y %H:%M")}'),0,0,'L')
        # KPIs
        kpis = [('Grupos',str(total_g)),('Asistencia',str(total_as)),('Ofrenda Q',f'{total_of:,.2f}'),('Pendientes',str(total_pend)),('Recibidas',f'{pct}%'),('Hnos',str(sum(r.hnos or 0 for r in reportes))),('Amigos',str(sum(r.amigos or 0 for r in reportes))),('Ninos',str(sum(r.ninos or 0 for r in reportes)))]
        cw = 257/4
        for i,(l,v) in enumerate(kpis):
            x=11+(i%4)*cw; y=23+(i//4)*13
            pdf.set_xy(x,y); pdf.set_fill_color(245,248,255); pdf.cell(cw-2,11,'',0,0,'C',True)
            pdf.set_xy(x,y+1); pdf.set_text_color(26,58,92); pdf.set_font('Helvetica','B',8); pdf.cell(cw-2,5,v,0,0,'C')
            pdf.set_xy(x,y+7); pdf.set_font('Helvetica','',6); pdf.set_text_color(100,110,120); pdf.cell(cw-2,3,l,0,0,'C')
        # Table
        hdrs = [('Codigo',20),('Lider',48),('Fecha',20),('D-Z',16),('AGF',12),('Ofrenda',22),('Estado',18)]
        pdf.set_fill_color(26,58,92); pdf.set_text_color(255,255,255); pdf.set_font('Helvetica','B',7)
        pdf.set_y(52); x=11
        for h,w in hdrs: pdf.set_xy(x,52); pdf.cell(w,5,h,0,0,'C',True); x+=w
        y=58; rh=4.8
        for ri,r in enumerate(reportes):
            if y>195: pdf.add_page(); y=10
            pdf.set_fill_color(250,252,255) if ri%2==0 else pdf.set_fill_color(255,255,255)
            pend = r.ofrenda_recibida in ("Pendiente","")
            pdf.set_text_color(200,40,40) if pend else pdf.set_text_color(30,60,30)
            pdf.set_font('Helvetica','',6.5)
            vals = [c(str(r.codigo or '')[:10]),c(str(r.lider or '')[:26]),c(str(r.fecha)[:10]) if r.fecha else '',f'D{c(str(r.distrito or "?"))} Z{c(str(r.zona or "?"))}',str(r.asistencia or 0),f'Q{float(r.ofrenda_total or 0):,.2f}','Pendiente' if pend else 'Recibida']
            x=11
            for vi,(_,w) in enumerate(hdrs): pdf.set_xy(x,y); pdf.cell(w,rh,vals[vi],0,0,'C' if vi>=3 else 'L',True); x+=w
            y+=rh
        pdf.set_y(y+3); pdf.set_font('Helvetica','',6); pdf.set_text_color(100,110,120)
        pdf.cell(257,3,f'Total: {total_g} grupos  |  Q{total_of:,.2f}  |  Daniel Martinez - Total App GT',0,0,'C')
        buf = BytesIO()
        pdf.output(buf)
        buf.seek(0)
        return Response(content=buf.read(), media_type="application/pdf", headers={"Content-Disposition": f"inline; filename={no_serie}.pdf"})
    except Exception as e:
        return Response(content=f"Error: {e}".encode(), status_code=500)
    finally:
        db.close()

@app.get("/form", response_class=HTMLResponse)
async def form_redirect():
    with open("static/formulario_digital.html", "r", encoding="utf-8") as f:
        return f.read()

# Servir frontend
app.mount("/", StaticFiles(directory="static", html=True), name="static")
