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
        if not gr: return Response(b"PDF no encontrado",404)
        q = db.query(Reporte)
        if gr.fecha_inicio: q = q.filter(Reporte.fecha >= gr.fecha_inicio)
        if gr.fecha_fin: q = q.filter(Reporte.fecha <= gr.fecha_fin)
        if gr.filtro_lider: q = q.filter(Reporte.lider.ilike(f"%{gr.filtro_lider}%"))
        reportes = q.order_by(Reporte.fecha.desc()).all()
        if not reportes: return Response(b"Sin datos",404)
        sys_nom = "REDIL"
        cfg = db.query(Configuracion).filter(Configuracion.clave=="nombre").first()
        if cfg: sys_nom = cfg.valor
        def c(s): return str(s or '').encode('latin-1','replace').decode('latin-1')
        def fmtQ(v): return f"Q {float(v or 0):,.2f}"
        total_g = len(reportes); total_as = sum(r.asistencia or 0 for r in reportes)
        total_of = sum(float(r.ofrenda_total or 0) for r in reportes)
        total_hn = sum(r.hnos or 0 for r in reportes)
        total_am = sum(r.amigos or 0 for r in reportes)
        total_ni = sum(r.ninos or 0 for r in reportes)
        total_pend = sum(1 for r in reportes if r.ofrenda_recibida in ("Pendiente",""))
        pct = round((total_g-total_pend)/total_g*100,1) if total_g else 0
        desde = str(gr.fecha_inicio or ''); hasta = str(gr.fecha_fin or '')
        rango = f"{desde} al {hasta}" if desde and hasta else "Sin filtro de fechas"
        titulo = gr.titulo_reporte or "Reporte"
        fecha_gen = datetime.now().strftime("%d/%m/%Y %H:%M")
        pdf = FPDF('L', 'mm', 'Letter')
        pdf.set_auto_page_break(True, 14)
        pdf.add_page()
        # ── HEADER ── gradient background
        pdf.set_fill_color(26,58,92)
        pdf.rect(0,0,279,32,'F')
        # Accent stripe
        pdf.set_fill_color(59,130,200); pdf.rect(0,32,279,3,'F')
        pdf.set_text_color(255,255,255)
        pdf.set_font('Helvetica','B',17)
        pdf.set_xy(14,6); pdf.cell(180,8,c(sys_nom),0,0,'L')
        pdf.set_font('Helvetica','',9)
        pdf.set_xy(14,15); pdf.cell(180,5,c(titulo),0,0,'L')
        pdf.set_font('Helvetica','',8)
        pdf.set_xy(14,22); pdf.cell(180,5,c(f'Periodo: {rango}  |  Generado: {fecha_gen}'),0,0,'L')
        # Badge
        pdf.set_xy(200,6)
        pdf.set_fill_color(255,255,255)
        pdf.set_text_color(26,58,92)
        pdf.set_font('Helvetica','B',11)
        pdf.cell(65,8,c(no_serie),0,0,'C',True)
        pdf.set_xy(200,14)
        pdf.set_font('Helvetica','',8)
        pdf.set_text_color(255,255,255)
        pdf.cell(65,6,f'{total_g} grupos',0,0,'C')
        # ── KPI CARDS ──
        kpi_data = [
            ('Grupos',str(total_g),'#6366f1'),('Asistencia',str(total_as),'#f59e0b'),
            ('Ofrenda',fmtQ(total_of),'#10b981'),('Recibidas',f'{pct}%','#3b82f6'),
            ('Pendientes',str(total_pend),'#ef4444'),('Hermanos',str(total_hn),'#8b5cf6'),
            ('Amigos',str(total_am),'#14b8a6'),('Ninos',str(total_ni),'#f97316')
        ]
        kpi_x=14; kpi_w=(256-14)/4; kpi_h=17; kpi_y=39
        for i,(l,v,color) in enumerate(kpi_data):
            x=kpi_x+(i%4)*kpi_w; y=kpi_y+(i//4)*kpi_h
            # Card
            pdf.set_fill_color(248,250,255); pdf.set_draw_color(225,230,240)
            pdf.rect(x,y,kpi_w-4,kpi_h-3,'DF')
            # Accent
            r,g,b=int(color[1:3],16),int(color[3:5],16),int(color[5:7],16)
            pdf.set_fill_color(r,g,b)
            pdf.rect(x,y,2.8,kpi_h-3,'F')
            # Value
            pdf.set_text_color(r,g,b); pdf.set_font('Helvetica','B',11)
            pdf.set_xy(x+6,y+1); pdf.cell(kpi_w-12,8,v,0,0,'L')
            # Label
            pdf.set_font('Helvetica','',7.5); pdf.set_text_color(120,130,145)
            pdf.set_xy(x+6,y+10); pdf.cell(kpi_w-12,5,l,0,0,'L')
        # ── TABLE ──
        col_w=[22,58,22,20,16,22,16,14,18]; col_l=['Codigo','Lider','Fecha','D-Z','AGF','Ofrenda','Hnos','Amg','Estado']
        tbl_y=kpi_y+2*kpi_h+6
        pdf.set_fill_color(26,58,92); pdf.set_text_color(255,255,255)
        pdf.set_font('Helvetica','B',7.5); pdf.set_y(tbl_y)
        x=14
        for i,w in enumerate(col_w): pdf.set_xy(x,tbl_y); pdf.cell(w,7.5,col_l[i],0,0,'C',True); x+=w
        row_h=6.2; y=tbl_y+7.5
        mpp=int((195-y)/row_h)
        for ri,r in enumerate(reportes):
            if ri>0 and ri%mpp==0:
                pdf.add_page(); y=12
                pdf.set_fill_color(26,58,92); pdf.set_text_color(255,255,255)
                pdf.set_font('Helvetica','B',7.5); pdf.set_y(y)
                x=14
                for i,w in enumerate(col_w): pdf.set_xy(x,y); pdf.cell(w,7.5,col_l[i],0,0,'C',True); x+=w
                y+=7.5
            pdf.set_fill_color(252,254,255) if ri%2==0 else pdf.set_fill_color(245,248,252)
            pend=r.ofrenda_recibida in ("Pendiente",""); of_val=float(r.ofrenda_total or 0)
            data=[c(str(r.codigo or'-')[:10]),c(str(r.lider or'-')[:30]),c(str(r.fecha)[:10])if r.fecha else'-',
                  f'D{c(str(r.distrito or"?"))} Z{c(str(r.zona or"?"))}',str(r.asistencia or 0),
                  f'Q{of_val:,.2f}',str(r.hnos or 0),str(r.amigos or 0),
                  'Pendiente'if pend else'Recibida']
            if pend: pdf.set_text_color(220,40,40)
            else: pdf.set_text_color(5,150,105)
            pdf.set_font('Helvetica','',7.5)
            x=14
            for vi,w in enumerate(col_w): pdf.set_xy(x,y); pdf.cell(w,row_h,data[vi],0,0,'L'if vi<2 else'C',True); x+=w
            y+=row_h
        # ── FOOTER ──
        pdf.set_y(y+3); pdf.set_draw_color(59,130,200); pdf.set_line_width(.5)
        pdf.line(14,y+3,265,y+3)
        pdf.set_font('Helvetica','B',8); pdf.set_text_color(26,58,92)
        pdf.set_xy(14,y+5); pdf.cell(120,6,f'Total: {total_g} reportes  |  {fmtQ(total_of)}',0,0,'L')
        pdf.set_font('Helvetica','',7); pdf.set_text_color(130,140,155)
        pdf.set_xy(14,y+11); pdf.cell(251,4,'Daniel Martinez  |  Total App GT',0,0,'R')
        # ── OUTPUT ──
        buf = BytesIO()
        pdf.output(buf); buf.seek(0)
        fname = f"{c(sys_nom)}_{c(titulo)}_{desde}_{no_serie}.pdf".replace(' ','_').replace('/','-')
        return Response(buf.read(), media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="{fname}"'})
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
