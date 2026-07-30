from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Usuario, Hermano, Reporte, Seguimiento
import jwt
import bcrypt
import os
from datetime import datetime, timedelta
import json

router = APIRouter()
SECRET = os.getenv("JWT_SECRET", "redil_secret_key_2026")

ALL_MENU_IDS = [
    'dashboard','reportes','reporteDigital','formulario','generador',
    'hermanos','cargaMasiva','seguimientos','privilegios',
    'diezmos','gastos','inventario','insumos',
    'supervisores','pastores','ayudapastor',
    'envio','contactos','usuarios','configuracion','bitacora'
]

ROL_DEFAULT_MENU = {
    'Admin':     ['dashboard','reportes','reporteDigital','formulario','generador','hermanos','cargaMasiva','seguimientos','privilegios','diezmos','inventario','insumos','envio','contactos','usuarios','supervisores','pastores','ayudapastor'],
    'Líder':     ['dashboard','reportes','reporteDigital','formulario','seguimientos'],
    'Secretario':['dashboard','reportes','reporteDigital','generador','seguimientos','envio','contactos'],
    'Tesorero':  ['dashboard','reportes','diezmos','gastos','generador','envio'],
    'Digitador': ['dashboard','reportes','envio','contactos'],
    'Solo Lectura': ['envio','contactos']
}

DB_TO_GAS_ROLE = {
    'propietario': 'Admin',
    'admin': 'Admin',
    'lider': 'Líder',
    'secretario': 'Secretario',
    'tesorero': 'Tesorero',
    'digitador': 'Digitador'
}

def get_user_from_token(token: str, db: Session):
    try:
        payload = jwt.decode(token, SECRET, algorithms=["HS256"])
        user = db.query(Usuario).filter(Usuario.email == payload.get("email")).first()
        return user
    except:
        return None

def make_user_response(u):
    gas_role = DB_TO_GAS_ROLE.get(u.rol, 'Solo Lectura')
    menu = list(ROL_DEFAULT_MENU.get(gas_role, ROL_DEFAULT_MENU['Solo Lectura']))
    if u.menu_permitido:
        try:
            menu = json.loads(u.menu_permitido) if isinstance(u.menu_permitido, str) else u.menu_permitido
        except:
            pass
    return {
        "id": u.id, "nombre": u.nombre, "email": u.email,
        "rol": gas_role,
        "menu": menu,
        "isPropietario": u.rol == "propietario",
        "puedeVerBitacora": u.puede_ver_bitacora if hasattr(u, 'puede_ver_bitacora') else True,
        "PuedeEditar": "SI" if u.rol in ("propietario", "admin") else "NO",
        "inactMin": 60
    }

@router.post("/dispatch")
def dispatch(data: dict, db: Session = Depends(get_db)):
    action = data.get("action", "")
    payload = data.get("payload", {})
    token = payload.get("token", data.get("token", ""))
    user = get_user_from_token(token, db) if token else None

    try:
        if action == "login":
            email = payload.get("email", "")
            password = payload.get("password", "")
            u = db.query(Usuario).filter(Usuario.email == email).first()
            if not u or not bcrypt.checkpw(password.encode(), u.password.encode()):
                return {"ok": False, "msg": "Credenciales inválidas"}
            if not u.activo:
                return {"ok": False, "msg": "Usuario inactivo"}
            new_token = jwt.encode({
                "id": u.id, "email": u.email, "rol": u.rol,
                "exp": datetime.utcnow() + timedelta(days=7)
            }, SECRET, algorithm="HS256")
            return {"ok": True, "token": new_token, "user": make_user_response(u)}

        if action == "validateSession":
            u = get_user_from_token(payload.get("token", ""), db)
            if u:
                return {"ok": True, "user": make_user_response(u)}
            return {"ok": False}

        if action == "destroySession":
            return {"ok": True}

        if action == "getDashboard":
            return {"ok": True, "data": {
                "totalHermanos": db.query(Hermano).count(),
                "totalReportes": db.query(Reporte).count(),
                "pendientes": db.query(Reporte).filter(Reporte.ofrenda_recibida.in_(["Pendiente", ""])).count(),
                "seguimientos": db.query(Seguimiento).count()
            }}

        if action == "getHermanos":
            hermanos = db.query(Hermano).all()
            return {"ok": True, "data": [{
                "ID": h.id, "CodigoL": h.codigo_lead, "NombreL": h.nombre,
                "Distrito": h.distrito, "Zona": h.zona, "Area": h.area,
                "Sector": h.sector, "Grupo": h.grupo,
                "Pastor Zona": h.pastor_zona, "Sup SectorL": h.sup_sector,
                "Sup AreaL": h.sup_area, "Ayuda Pastor": h.ayuda_pastor,
                "Anfitrion": h.anfitrion, "Direccion": h.direccion,
                "CodigoSup": h.codigo_sup, "CodigoPastor": h.codigo_pastor
            } for h in hermanos]}

        if action == "getHermanoByCodigo":
            h = db.query(Hermano).filter(Hermano.codigo_lead == payload.get("codigo")).first()
            if h:
                return {"ok": True, "data": {
                    "ID": h.id, "CodigoL": h.codigo_lead, "NombreL": h.nombre,
                    "Distrito": h.distrito, "Zona": h.zona, "Area": h.area,
                    "Sector": h.sector, "Grupo": h.grupo,
                    "Pastor Zona": h.pastor_zona, "Sup SectorL": h.sup_sector,
                    "Sup AreaL": h.sup_area, "Ayuda Pastor": h.ayuda_pastor,
                    "Anfitrion": h.anfitrion, "Direccion": h.direccion,
                    "CodigoSup": h.codigo_sup, "CodigoPastor": h.codigo_pastor
                }}
            return {"ok": False, "msg": "Hermano no encontrado"}

        if action == "getReportes":
            q = db.query(Reporte)
            if payload.get("pendientes"):
                q = q.filter(Reporte.ofrenda_recibida.in_(["Pendiente", ""]))
            if payload.get("desde"):
                q = q.filter(Reporte.fecha >= payload["desde"])
            if payload.get("hasta"):
                q = q.filter(Reporte.fecha <= payload["hasta"])
            if payload.get("codigo"):
                q = q.filter(Reporte.codigo == payload["codigo"])
            reportes = q.order_by(Reporte.fecha.desc()).limit(500).all()
            return {"ok": True, "data": [{
                "ID": r.id, "Codigo": r.codigo, "Lider": r.lider,
                "Fecha": str(r.fecha) if r.fecha else "",
                "Distrito": r.distrito, "Zona": r.zona, "Area": r.area,
                "Sector": r.sector, "Grupo": r.grupo,
                "Ofrenda Total": float(r.ofrenda_total or 0),
                "Ofrenda Recibida": r.ofrenda_recibida or "Pendiente",
                "Asistencia Grupo Familiar": r.asistencia or 0,
                "Hnos": r.hnos or 0, "Amigos": r.amigos or 0, "Niños": r.ninos or 0,
                "Tipo de Reporte": r.tipo_reporte or ""
            } for r in reportes]}

        if action == "getResumen":
            q = db.query(Reporte)
            if payload.get("desde"):
                q = q.filter(Reporte.fecha >= payload["desde"])
            if payload.get("hasta"):
                q = q.filter(Reporte.fecha <= payload["hasta"])
            reportes = q.all()
            total = len(reportes)
            asistencia = sum(r.asistencia or 0 for r in reportes)
            of_total = sum(float(r.ofrenda_total or 0) for r in reportes)
            pendientes = sum(1 for r in reportes if r.ofrenda_recibida in ("Pendiente", ""))
            hnos = sum(r.hnos or 0 for r in reportes)
            amigos = sum(r.amigos or 0 for r in reportes)
            return {"ok": True, "total": total, "asistencia": asistencia,
                    "ofTotal": round(of_total, 2), "pendientes": pendientes,
                    "hnos": hnos, "amigos": amigos}

        if action == "getConfig":
            return {
                "ok": True,
                "ssId": os.getenv("SPREADSHEET_ID", ""),
                "nombre": "REDIL",
                "formUrl": "",
                "formUrlPublic": "",
                "activo": True,
                "logo_url": "https://i.postimg.cc/SsCZVFwp/Logo-Icono2.jpg",
                "logoUrl": "https://i.postimg.cc/SsCZVFwp/Logo-Icono2.jpg",
                "menuConfig": {m: True for m in ALL_MENU_IDS},
                "ownerEmail": "totalappgt@gmail.com",
                "inactividadMinutos": 60,
                "metaGrupos": "407",
                "driveFolderId": "",
                "botPdfFolderId": "",
                "pdf_id": "",
                "gemini_api_key": "",
                "openrouter_api_key": "",
                "deepseek_api_key": "",
                "telegram_token": "",
                "telegram_chat_id": "",
                "whatsapp_soporte": "+502 5830-3182",
                "nombre_soporte": "Total App GT - Daniel Martínez",
                "titleMantenimiento": "Sistema en Mantenimiento",
                "msgMantenimiento": "El sistema no está disponible en este momento.",
                "bot_habilitado": True,
                "ai_provider": "auto",
                "servicios_dinamicos": [],
                "cron_lunes": "Lunes 6:30 PM",
                "cron_jueves": "Jueves 6:30 PM",
                "cron_domTarde": "Domingo 10:30 AM",
                "theme_colors": ""
            }

        if action == "inicializarSistema":
            return {"ok": True, "msg": "Sistema listo. Configura tu bot de Telegram en Config."}

        if action == "getSeguimientos":
            seguimientos = db.query(Seguimiento).order_by(Seguimiento.fecha.desc()).limit(200).all()
            return {"ok": True, "data": [{
                "ID": s.id, "Fecha": str(s.fecha) if s.fecha else "",
                "Persona": s.persona, "Tipo": s.tipo,
                "Responsable": s.responsable, "Estado": s.estado,
                "Observaciones": s.observaciones
            } for s in seguimientos]}

        return {"ok": False, "msg": f"Acción '{action}' no implementada en API"}

    except Exception as e:
        return {"ok": False, "msg": str(e)}
