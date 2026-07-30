from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Usuario, Hermano, Reporte, Seguimiento
import jwt
import bcrypt
import os

router = APIRouter()
SECRET = os.getenv("JWT_SECRET", "redil_secret_key_2026")

def get_user_from_token(token: str, db: Session):
    try:
        payload = jwt.decode(token, SECRET, algorithms=["HS256"])
        user = db.query(Usuario).filter(Usuario.email == payload.get("email")).first()
        return user
    except:
        return None

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
            user = db.query(Usuario).filter(Usuario.email == email).first()
            if not user or not bcrypt.checkpw(password.encode(), user.password.encode()):
                return {"ok": False, "msg": "Credenciales inválidas"}
            if not user.activo:
                return {"ok": False, "msg": "Usuario inactivo"}
            new_token = jwt.encode({
                "id": user.id, "email": user.email, "rol": user.rol,
                "exp": __import__('datetime').datetime.utcnow() + __import__('datetime').timedelta(days=7)
            }, SECRET, algorithm="HS256")
            return {
                "ok": True,
                "token": new_token,
                "user": {
                    "email": user.email,
                    "nombre": user.nombre,
                    "rol": user.rol,
                    "PuedeEditar": "SI" if user.rol in ("propietario", "admin") else "NO"
                }
            }
        
        if action == "validateSession":
            u = get_user_from_token(payload.get("token", ""), db)
            if u:
                return {"ok": True, "user": {"email": u.email, "nombre": u.nombre, "rol": u.rol, "PuedeEditar": "SI"}}
            return {"ok": False}
        
        if action == "destroySession":
            return {"ok": True}
        
        if action == "getDashboard":
            total_hermanos = db.query(Hermano).count()
            total_reportes = db.query(Reporte).count()
            pendientes = db.query(Reporte).filter(Reporte.ofrenda_recibida.in_(["Pendiente", ""])).count()
            total_seguimientos = db.query(Seguimiento).count()
            return {
                "ok": True,
                "data": {
                    "totalHermanos": total_hermanos,
                    "totalReportes": total_reportes,
                    "pendientes": pendientes,
                    "seguimientos": total_seguimientos
                }
            }
        
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
        
        if action == "getReportes":
            from datetime import date
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
            from datetime import date
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
            return {"ok": True, "data": {"ssId": os.getenv("SPREADSHEET_ID", ""),
                    "nombre": "REDIL", "telegram_token": "", "telegram_chat_id": ""}}
        
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
