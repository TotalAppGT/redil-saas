from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import (
    Usuario, Hermano, Reporte, Seguimiento,
    Supervisor, Pastore, AyudaPastor, Contacto,
    Diezmo, Gasto, Inventario, Insumo, Privilegio,
    Cronograma, Bitacora, Configuracion, Envio, GeneradorReporte
)
import jwt
import bcrypt
import os
import json
import requests
from datetime import datetime, timedelta
from dateutil import parser as dateparser
from sqlalchemy import func

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

HERMANO_MAP = {
    "CodigoL": "codigo_lead", "NombreL": "nombre", "Distrito": "distrito",
    "Zona": "zona", "Area": "area", "Sector": "sector", "Grupo": "grupo",
    "Pastor Zona": "pastor_zona", "Sup SectorL": "sup_sector",
    "Sup AreaL": "sup_area", "Ayuda Pastor": "ayuda_pastor",
    "Anfitrion": "anfitrion", "Direccion": "direccion",
    "CodigoSup": "codigo_sup", "CodigoPastor": "codigo_pastor",
}

SUPERVISOR_MAP = {
    "CodigoSup": "codigo_sup", "NombreSup": "nombre_sup",
    "Distrito": "distrito", "Zona": "zona", "Area": "area",
    "Sector": "sector", "Telefono": "telefono", "Email": "email",
    "Activo": "activo",
}

PASTOR_MAP = {
    "CodigoPastor": "codigo_pastor", "NombrePastor": "nombre_pastor",
    "Distrito": "distrito", "Zona": "zona",
    "Telefono": "telefono", "Email": "email",
    "Activo": "activo",
}

AYUDA_PASTOR_MAP = {
    "CodigoAyuda": "codigo_ayuda", "NombreAyuda": "nombre_ayuda",
    "Distrito": "distrito", "Zona": "zona", "Area": "area",
    "Telefono": "telefono", "Email": "email",
    "Activo": "activo",
}

CONTACTO_MAP = {
    "Nombre": "nombre", "Correo": "email",
}

DIEZMO_MAP = {
    "Fecha": "fecha", "Nombre": "nombre",
    "Telefono": "telefono", "Grupo": "grupo",
    "Tipo": "tipo", "MontoQ": "monto",
    "Descripcion": "observaciones",
}

GASTO_MAP = {
    "fecha": "fecha", "evento": "concepto",
    "categoria": "categoria", "descripcion": "descripcion",
    "monto": "monto", "responsable": "responsable",
    "metodo": "metodo", "comprobante": "comprobante",
    "observaciones": "observaciones",
}

INVENTARIO_MAP = {
    "Articulo": "nombre", "Categoria": "categoria",
    "Cantidad": "cantidad", "Unidad": "unidad",
    "Estado": "estado", "Ubicacion": "ubicacion",
    "ValorQ": "valor_q", "Observaciones": "observaciones",
}

INSUMO_MAP = {
    "Articulo": "nombre", "Categoria": "categoria",
    "Cantidad": "cantidad", "Unidad": "unidad",
    "PrecioUnitarioQ": "precio_unitario_q",
    "StockMinimo": "stock_minimo", "Proveedor": "proveedor",
    "Observaciones": "observaciones",
}

PRIVILEGIO_MAP = {
    "Hermano": "nombre", "Area": "area",
    "CodigoL": "codigo_lead", "Privilegio": "privilegio",
    "FechaInicio": "fecha_inicio", "FechaFin": "fecha_fin",
    "Activo": "activo", "Observaciones": "observaciones",
}

CRONOGRAMA_MAP = {
    "Hermano": "hermano", "Area": "area",
    "Servicio": "servicio", "Privilegio": "privilegio",
    "Lunes": "lunes", "Jueves": "jueves",
    "Domingo_Mañana": "domingo_manana", "Domingo_Tarde": "domingo_tarde",
    "FechaAsignacion": "fecha_asignacion",
    "Observaciones": "observaciones", "Activo": "activo",
}

BITACORA_MAP = {
    "FechaHora": "fecha", "Usuario": "usuario",
    "Email": "email", "Rol": "rol",
    "Accion": "accion", "Detalles": "detalle",
}

ENVIO_MAP = {
    "Fecha Hora": "fecha_envio", "Asunto Correo": "asunto",
    "Cuerpo Mensaje": "mensaje", "Archivos a Enviar": "archivos_a_enviar",
    "Destinatarios": "destinatarios", "Estado": "estado",
    "Rutas Reales PDF": "rutas_reales_pdf",
}

USUARIO_MAP = {
    "Nombre": "nombre", "Email": "email",
    "Rol": "rol", "Activo": "activo",
    "MenuPermitido": "menu_permitido",
    "PuedeVerBitacora": "puede_ver_bitacora",
}

GENERADOR_MAP = {
    "Fecha Inicio": "fecha_inicio", "Fecha Fin": "fecha_fin",
    "Total Ofrenda": "total_ofrenda", "Total Asistencia": "total_asistencia",
    "Titulo de Reporte": "titulo_reporte", "Archivo Generado": "archivo_generado",
    "No Serie": "no_serie", "Mes Reporte": "mes_reporte",
    "Ano Reporte": "ano_reporte", "Filtro Lider": "filtro_lider",
    "Filtro Sup Sector": "filtro_sup_sector", "Filtro Sup Area": "filtro_sup_area",
    "Filtro Pastor Zona": "filtro_pastor_zona", "Filtro Distrito": "filtro_distrito",
    "Filtro Zona": "filtro_zona",
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

def row_to_dict(field_map, obj, id_key="ID"):
    d = {id_key: obj.id}
    for gas_key, db_key in field_map.items():
        val = getattr(obj, db_key, None)
        if val is not None:
            d[gas_key] = val
    return d

def payload_to_kwargs(field_map, payload):
    kwargs = {}
    for gas_key, db_key in field_map.items():
        if gas_key in payload:
            kwargs[db_key] = payload[gas_key]
    return kwargs

def save_entity(db, model_class, field_map, payload, id_key="ID"):
    item_id = payload.get(id_key)
    data = payload_to_kwargs(field_map, payload)
    if item_id:
        obj = db.query(model_class).filter(model_class.id == item_id).first()
        if not obj:
            return {"ok": False, "msg": "Registro no encontrado"}
        for key, val in data.items():
            setattr(obj, key, val)
    else:
        obj = model_class(**data)
        db.add(obj)
    db.commit()
    return {"ok": True}

def delete_entity(db, model_class, payload, id_key="ID"):
    item_id = payload.get(id_key)
    if not item_id:
        return {"ok": False, "msg": "ID requerido"}
    obj = db.query(model_class).filter(model_class.id == item_id).first()
    if not obj:
        return {"ok": False, "msg": "Registro no encontrado"}
    db.delete(obj)
    db.commit()
    return {"ok": True}

def list_entities(db, model_class, field_map, order_col=None, id_key="ID"):
    q = db.query(model_class)
    if order_col:
        q = q.order_by(order_col)
    items = q.all()
    return {"ok": True, "data": [row_to_dict(field_map, item, id_key) for item in items]}


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
            total_hermanos = db.query(Hermano).count()
            lideres = db.query(Hermano).filter(Hermano.codigo_lead != None).count()
            reportes_mes = db.query(Reporte).count()
            pendientes = db.query(Reporte).filter(Reporte.ofrenda_recibida.in_(["Pendiente", ""])).count()
            asistencia_total = db.query(func.coalesce(func.sum(Reporte.asistencia), 0)).scalar()
            of_total = float(db.query(func.coalesce(func.sum(Reporte.ofrenda_total), 0)).scalar())
            seg_total = db.query(Seguimiento).count()
            return {"ok": True,
                "lideres": lideres,
                "reportesMes": reportes_mes,
                "gruposRealizados": reportes_mes,
                "asistencia": int(asistencia_total),
                "ofTotal": round(of_total, 2),
                "convertidos": 0,
                "reconciliados": 0,
                "segTotal": seg_total,
                "pendientes": pendientes,
                "metaGrupos": 407,
                "proxCron": [],
                "grafica": []
            }

        if action == "getHermanos":
            return list_entities(db, Hermano, HERMANO_MAP)

        if action == "getHermanoByCodigo":
            h = db.query(Hermano).filter(Hermano.codigo_lead == payload.get("codigo")).first()
            if h:
                return {"ok": True, "data": row_to_dict(HERMANO_MAP, h)}
            return {"ok": False, "msg": "Hermano no encontrado"}

        if action == "saveHermano":
            return save_entity(db, Hermano, HERMANO_MAP, payload)

        if action == "deleteHermano":
            return delete_entity(db, Hermano, payload)

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
            configs = {}
            try:
                rows = db.query(Configuracion).all()
                for c in rows:
                    configs[c.clave] = c.valor
            except:
                pass
            base = {
                "ssId": os.getenv("SPREADSHEET_ID", ""),
                "nombre": "REDIL",
                "formUrl": configs.get("formUrl", ""),
                "formUrlPublic": configs.get("formUrlPublic", ""),
                "activo": True,
                "logo_url": "https://i.postimg.cc/SsCZVFwp/Logo-Icono2.jpg",
                "logoUrl": "https://i.postimg.cc/SsCZVFwp/Logo-Icono2.jpg",
                "menuConfig": {m: True for m in ALL_MENU_IDS},
                "ownerEmail": configs.get("ownerEmail", "totalappgt@gmail.com"),
                "inactividadMinutos": int(configs.get("inactividadMinutos", "60")),
                "metaGrupos": configs.get("metaGrupos", "407"),
                "driveFolderId": configs.get("driveFolderId", ""),
                "botPdfFolderId": configs.get("botPdfFolderId", ""),
                "pdf_id": configs.get("pdf_id", ""),
                "gemini_api_key": configs.get("gemini_api_key", ""),
                "openrouter_api_key": configs.get("openrouter_api_key", ""),
                "deepseek_api_key": configs.get("deepseek_api_key", ""),
                "telegram_token": configs.get("telegram_token", ""),
                "telegram_chat_id": configs.get("telegram_chat_id", ""),
                "whatsapp_soporte": configs.get("whatsapp_soporte", "+502 5830-3182"),
                "nombre_soporte": configs.get("nombre_soporte", "Total App GT - Daniel Martínez"),
                "titleMantenimiento": configs.get("titleMantenimiento", "Sistema en Mantenimiento"),
                "msgMantenimiento": configs.get("msgMantenimiento", "El sistema no está disponible en este momento."),
                "bot_habilitado": configs.get("bot_habilitado", "True") == "True",
                "ai_provider": configs.get("ai_provider", "auto"),
                "servicios_dinamicos": [],
                "cron_lunes": configs.get("cron_lunes", "Lunes 6:30 PM"),
                "cron_jueves": configs.get("cron_jueves", "Jueves 6:30 PM"),
                "cron_domTarde": configs.get("cron_domTarde", "Domingo 10:30 AM"),
                "theme_colors": configs.get("theme_colors", ""),
            }
            return {"ok": True, **base}

        if action == "saveConfig":
            for key, val in payload.items():
                if key in ("token", "action"):
                    continue
                existing = db.query(Configuracion).filter(Configuracion.clave == key).first()
                str_val = str(val) if val is not None else ""
                if existing:
                    existing.valor = str_val
                else:
                    db.add(Configuracion(clave=key, valor=str_val))
            db.commit()
            return {"ok": True}

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

        if action == "getSupervisores":
            return list_entities(db, Supervisor, SUPERVISOR_MAP, Supervisor.nombre_sup)

        if action == "saveSupervisor":
            return save_entity(db, Supervisor, SUPERVISOR_MAP, payload)

        if action == "deleteSupervisor":
            return delete_entity(db, Supervisor, payload)

        if action == "getPastores":
            return list_entities(db, Pastore, PASTOR_MAP, Pastore.nombre_pastor)

        if action == "savePastor":
            return save_entity(db, Pastore, PASTOR_MAP, payload)

        if action == "deletePastor":
            return delete_entity(db, Pastore, payload)

        if action == "getAyudaPastor":
            return list_entities(db, AyudaPastor, AYUDA_PASTOR_MAP, AyudaPastor.nombre_ayuda)

        if action == "saveAyudaPastor":
            return save_entity(db, AyudaPastor, AYUDA_PASTOR_MAP, payload)

        if action == "deleteAyudaPastor":
            return delete_entity(db, AyudaPastor, payload)

        if action == "getContactos":
            return list_entities(db, Contacto, CONTACTO_MAP, Contacto.nombre, id_key="IDContacto")

        if action == "saveContacto":
            return save_entity(db, Contacto, CONTACTO_MAP, payload, id_key="IDContacto")

        if action == "deleteContacto":
            return delete_entity(db, Contacto, payload, id_key="IDContacto")

        if action == "getDiezmos":
            return list_entities(db, Diezmo, DIEZMO_MAP, Diezmo.fecha.desc())

        if action == "saveDiezmo":
            return save_entity(db, Diezmo, DIEZMO_MAP, payload)

        if action == "deleteDiezmo":
            return delete_entity(db, Diezmo, payload)

        if action == "getGastos":
            return list_entities(db, Gasto, GASTO_MAP, Gasto.fecha.desc())

        if action == "saveGasto":
            return save_entity(db, Gasto, GASTO_MAP, payload, id_key="id")

        if action == "deleteGasto":
            return delete_entity(db, Gasto, payload, id_key="id")

        if action == "getInventario":
            return list_entities(db, Inventario, INVENTARIO_MAP, Inventario.nombre)

        if action == "saveInventario":
            return save_entity(db, Inventario, INVENTARIO_MAP, payload)

        if action == "deleteInventario":
            return delete_entity(db, Inventario, payload)

        if action == "getInsumos":
            return list_entities(db, Insumo, INSUMO_MAP, Insumo.nombre)

        if action == "saveInsumo":
            return save_entity(db, Insumo, INSUMO_MAP, payload)

        if action == "deleteInsumo":
            return delete_entity(db, Insumo, payload)

        if action == "getPrivilegios":
            return list_entities(db, Privilegio, PRIVILEGIO_MAP, Privilegio.nombre)

        if action == "savePrivilegio":
            return save_entity(db, Privilegio, PRIVILEGIO_MAP, payload)

        if action == "deletePrivilegio":
            return delete_entity(db, Privilegio, payload)

        if action == "getCronograma":
            return list_entities(db, Cronograma, CRONOGRAMA_MAP, Cronograma.fecha_asignacion)

        if action == "saveCronograma":
            return save_entity(db, Cronograma, CRONOGRAMA_MAP, payload)

        if action == "deleteCronograma":
            return delete_entity(db, Cronograma, payload)

        if action == "getBitacora":
            q = db.query(Bitacora).order_by(Bitacora.fecha.desc()).limit(500)
            if payload.get("desde"):
                q = q.filter(Bitacora.fecha >= payload["desde"])
            if payload.get("hasta"):
                q = q.filter(Bitacora.fecha <= payload["hasta"])
            items = q.all()
            return {"ok": True, "data": [row_to_dict(BITACORA_MAP, item) for item in items]}

        if action == "saveBitacora":
            data = payload_to_kwargs(BITACORA_MAP, payload)
            if "fecha" not in data or not data["fecha"]:
                data["fecha"] = datetime.utcnow()
            db.add(Bitacora(**data))
            db.commit()
            return {"ok": True}

        if action == "limpiarBitacora":
            db.query(Bitacora).delete()
            db.commit()
            return {"ok": True}

        if action == "getEnvios":
            return list_entities(db, Envio, ENVIO_MAP, Envio.fecha_envio.desc(), id_key="IDEnvio")

        if action == "getUsuarios":
            usuarios = db.query(Usuario).all()
            result = []
            for u in usuarios:
                d = row_to_dict(USUARIO_MAP, u)
                d.pop("password", None)
                result.append(d)
            return {"ok": True, "data": result}

        if action == "saveUsuario":
            item_id = payload.get("ID")
            data = payload_to_kwargs(USUARIO_MAP, payload)
            password = payload.get("Password", "")
            if password:
                data["password"] = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            if item_id:
                obj = db.query(Usuario).filter(Usuario.id == item_id).first()
                if not obj:
                    return {"ok": False, "msg": "Usuario no encontrado"}
                for key, val in data.items():
                    setattr(obj, key, val)
            else:
                if "password" not in data:
                    data["password"] = bcrypt.hashpw(b"redil2026", bcrypt.gensalt()).decode()
                obj = Usuario(**data)
                db.add(obj)
            db.commit()
            return {"ok": True}

        if action == "deleteUsuario":
            item_id = payload.get("ID")
            if not item_id:
                return {"ok": False, "msg": "ID requerido"}
            obj = db.query(Usuario).filter(Usuario.id == item_id).first()
            if not obj:
                return {"ok": False, "msg": "Usuario no encontrado"}
            db.delete(obj)
            db.commit()
            return {"ok": True}

        if action == "getFormUrl":
            form_url = ""
            c = db.query(Configuracion).filter(Configuracion.clave == "formUrlPublic").first()
            if c:
                form_url = c.valor
            if not form_url:
                c = db.query(Configuracion).filter(Configuracion.clave == "formUrl").first()
                if c:
                    form_url = c.valor
            return {"ok": True, "url": form_url}

        if action == "getFormHtml":
            return {"ok": True, "data": ""}

        if action == "getGeneradores":
            return list_entities(db, GeneradorReporte, GENERADOR_MAP, GeneradorReporte.fecha_inicio, id_key="ID_Reporte")

        if action == "getReporteFinancieroDistrito":
            q = db.query(
                Reporte.distrito, Reporte.zona,
                func.count(Reporte.id).label("total_reportes"),
                func.coalesce(func.sum(Reporte.asistencia), 0).label("total_asistencia"),
                func.coalesce(func.sum(Reporte.ofrenda_total), 0).label("total_ofrenda"),
                func.coalesce(func.sum(Reporte.hnos), 0).label("total_hnos"),
                func.coalesce(func.sum(Reporte.amigos), 0).label("total_amigos"),
            )
            if payload.get("desde"):
                q = q.filter(Reporte.fecha >= payload["desde"])
            if payload.get("hasta"):
                q = q.filter(Reporte.fecha <= payload["hasta"])
            rows = q.group_by(Reporte.distrito, Reporte.zona).all()
            data = []
            for r in rows:
                data.append({
                    "Distrito": r.distrito or "",
                    "Zona": r.zona or "",
                    "TotalReportes": r.total_reportes,
                    "TotalAsistencia": int(r.total_asistencia),
                    "TotalOfrenda": float(r.total_ofrenda),
                    "TotalHnos": int(r.total_hnos),
                    "TotalAmigos": int(r.total_amigos),
                })
            return {"ok": True, "data": data}

        if action == "getCuadreDominical":
            desde = payload.get("desde", "")
            hasta = payload.get("hasta", "")
            lideres = db.query(Hermano).filter(Hermano.codigo_lead != None).all()
            reportes_q = db.query(Reporte)
            if desde:
                reportes_q = reportes_q.filter(Reporte.fecha >= desde)
            if hasta:
                reportes_q = reportes_q.filter(Reporte.fecha <= hasta)
            reportes = reportes_q.all()
            codigos_reportados = set(r.codigo for r in reportes)
            data = []
            for h in lideres:
                reporto = h.codigo_lead in codigos_reportados
                rpts = [r for r in reportes if r.codigo == h.codigo_lead]
                data.append({
                    "CodigoL": h.codigo_lead or "",
                    "NombreL": h.nombre or "",
                    "Distrito": h.distrito or "",
                    "Zona": h.zona or "",
                    "Area": h.area or "",
                    "Sector": h.sector or "",
                    "Grupo": h.grupo or "",
                    "Reporto": "SI" if reporto else "NO",
                    "CantidadReportes": len(rpts),
                })
            return {"ok": True, "data": data}

        if action == "getEncabezadosCargaMasiva":
            tipo = payload.get("tipo", "")
            headers_map = {
                "hermanos": ['ID','CodigoL','NombreL','Distrito','Zona','Area','Sector','Grupo','Anfitrion','Direccion','Sup SectorL','Sup AreaL','Ayuda Pastor','Pastor Zona','CodigoSup','CodigoPastor'],
                "supervisores": ['ID','CodigoSup','NombreSup','Distrito','Zona','Area','Sector','Telefono','Email','Activo'],
                "pastores": ['ID','CodigoPastor','NombrePastor','Distrito','Zona','Telefono','Email','Activo'],
                "ayudapastor": ['ID','CodigoAyuda','NombreAyuda','Distrito','Zona','Area','Telefono','Email','Activo'],
            }
            headers = headers_map.get(tipo, [])
            return {"ok": True, "data": headers}

        if action == "importarDatosMasivos":
            tipo = payload.get("tipo", "")
            rows = payload.get("rows", [])
            if not rows:
                return {"ok": False, "msg": "No hay datos para importar"}
            model_class = None
            field_map = None
            tipo_map = {
                "hermanos": (Hermano, HERMANO_MAP),
                "supervisores": (Supervisor, SUPERVISOR_MAP),
                "pastores": (Pastore, PASTOR_MAP),
                "ayudapastor": (AyudaPastor, AYUDA_PASTOR_MAP),
            }
            pair = tipo_map.get(tipo)
            if not pair:
                return {"ok": False, "msg": f"Tipo '{tipo}' no soportado"}
            model_class, field_map = pair
            insertados = 0
            for row in rows:
                data = payload_to_kwargs(field_map, row)
                if data:
                    db.add(model_class(**data))
                    insertados += 1
            db.commit()
            return {"ok": True, "msg": f"{insertados} registros importados"}

        if action == "invalidateDashCache":
            return {"ok": True}

        if action == "preguntarAI":
            pregunta = payload.get("pregunta", "")
            if not pregunta:
                return {"ok": False, "msg": "Pregunta requerida"}
            api_key = ""
            c = db.query(Configuracion).filter(Configuracion.clave == "gemini_api_key").first()
            if c:
                api_key = c.valor
            if not api_key:
                api_key = os.getenv("GEMINI_API_KEY", "")
            if not api_key:
                return {"ok": False, "msg": "API key de Gemini no configurada"}
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
                body = {"contents": [{"parts": [{"text": pregunta}]}]}
                resp = requests.post(url, json=body, timeout=30)
                if resp.status_code == 200:
                    j = resp.json()
                    texto = ""
                    parts = j.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                    if parts:
                        texto = parts[0].get("text", "")
                    return {"ok": True, "data": texto}
                return {"ok": False, "msg": f"Error Gemini API: {resp.status_code}"}
            except Exception as e:
                return {"ok": False, "msg": str(e)}

        if action == "exportExcel":
            return {"ok": False, "msg": "Exportación Excel disponible próximamente"}

        if action == "getAreaSupervisores":
            sup_map = {}
            supervisores = db.query(Supervisor).all()
            for s in supervisores:
                area = s.area or "Sin Area"
                if area not in sup_map:
                    sup_map[area] = []
                sup_map[area].append(row_to_dict(SUPERVISOR_MAP, s))
            return {"ok": True, "data": sup_map}

        return {"ok": False, "msg": f"Acción '{action}' no implementada en API"}

    except Exception as e:
        return {"ok": False, "msg": str(e)}
