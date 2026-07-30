from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import (
    Usuario, Hermano, Reporte, Seguimiento,
    Supervisor, Pastore, AyudaPastor, Contacto,
    Diezmo, Gasto, Inventario, Insumo, Privilegio,
    Cronograma, Bitacora, Configuracion, Envio, GeneradorReporte, Bautizo
)
import jwt
import bcrypt
import os
import json
import requests
from datetime import datetime, timedelta
from dateutil import parser as dateparser
from app.email_utils import send_email
from sqlalchemy import func

router = APIRouter()
SECRET = os.getenv("JWT_SECRET", "redil_secret_key_2026")

def esc(s):
    return str(s or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;").replace("'","&#39;")

ALL_MENU_IDS = [
    'dashboard','reportes','reporteDigital','formulario','generador',
    'hermanos','cargaMasiva','seguimientos','privilegios',
    'diezmos','gastos','inventario','insumos','bautizos',
    'supervisores','pastores','ayudapastor',
    'envio','contactos','usuarios','configuracion','bitacora'
]

ROL_DEFAULT_MENU = {
    'Admin':     ['dashboard','reportes','reporteDigital','formulario','generador','hermanos','cargaMasiva','seguimientos','privilegios','diezmos','inventario','insumos','envio','contactos','usuarios','supervisores','pastores','ayudapastor','configuracion','bitacora'],
    'Líder':     ['dashboard','reportes','reporteDigital','formulario','seguimientos'],
    'Secretario':['dashboard','reportes','reporteDigital','generador','seguimientos','envio','contactos'],
    'Tesorero':  ['dashboard','reportes','diezmos','gastos','generador','envio'],
    'Digitador': ['dashboard','reportes','envio','contactos'],
    'Solo Lectura': ['envio','contactos']
}

DB_TO_GAS_ROLE = {
    'propietario': 'Admin', 'admin': 'Admin', 'lider': 'Líder',
    'secretario': 'Secretario', 'tesorero': 'Tesorero', 'digitador': 'Digitador'
}

HERMANO_MAP = {"CodigoL": "codigo_lead", "NombreL": "nombre", "Distrito": "distrito", "Zona": "zona", "Area": "area", "Sector": "sector", "Grupo": "grupo", "Pastor Zona": "pastor_zona", "Sup SectorL": "sup_sector", "Sup AreaL": "sup_area", "Ayuda Pastor": "ayuda_pastor", "Anfitrion": "anfitrion", "Direccion": "direccion", "CodigoSup": "codigo_sup", "CodigoPastor": "codigo_pastor"}
SUPERVISOR_MAP = {"CodigoSup": "codigo_sup", "NombreSup": "nombre_sup", "Distrito": "distrito", "Zona": "zona", "Area": "area", "Sector": "sector", "Telefono": "telefono", "Email": "email", "Activo": "activo"}
PASTOR_MAP = {"CodigoPastor": "codigo_pastor", "NombrePastor": "nombre_pastor", "Distrito": "distrito", "Zona": "zona", "Telefono": "telefono", "Email": "email", "Activo": "activo"}
AYUDA_PASTOR_MAP = {"CodigoAyuda": "codigo_ayuda", "NombreAyuda": "nombre_ayuda", "Distrito": "distrito", "Zona": "zona", "Area": "area", "Telefono": "telefono", "Email": "email", "Activo": "activo"}
CONTACTO_MAP = {"Nombre": "nombre", "Correo": "email", "Telefono": "telefono", "Direccion": "direccion", "Notas": "notas", "Activo": "activo"}
DIEZMO_MAP = {"Fecha": "fecha", "Nombre": "nombre", "Telefono": "telefono", "Grupo": "grupo", "Tipo": "tipo", "MontoQ": "monto_q", "Descripcion": "descripcion"}
GASTO_MAP = {"ID": "id", "Fecha": "fecha", "Evento": "evento", "Categoria": "categoria", "Descripcion": "descripcion", "MontoQ": "monto", "Responsable": "responsable", "Metodo": "metodo", "Comprobante": "comprobante", "Observaciones": "observaciones"}
INVENTARIO_MAP = {"Articulo": "articulo", "Categoria": "categoria", "Cantidad": "cantidad", "Unidad": "unidad", "Estado": "estado", "Ubicacion": "ubicacion", "ValorQ": "valor_q", "Observaciones": "observaciones"}
INSUMO_MAP = {"Articulo": "articulo", "Categoria": "categoria", "Cantidad": "cantidad", "Unidad": "unidad", "PrecioUnitarioQ": "precio_unitario_q", "StockMinimo": "stock_minimo", "Proveedor": "proveedor", "Observaciones": "observaciones"}
PRIVILEGIO_MAP = {"Hermano": "hermano", "Area": "area", "CodigoL": "codigo_l", "Privilegio": "privilegio", "FechaInicio": "fecha_inicio", "FechaFin": "fecha_fin", "Observaciones": "observaciones", "Activo": "activo"}
CRONOGRAMA_MAP = {"Hermano": "hermano", "Area": "area", "Servicio": "servicio", "Privilegio": "privilegio", "Lunes": "lunes", "Jueves": "jueves", "Domingo_Mañana": "domingo_manana", "Domingo_Tarde": "domingo_tarde", "FechaAsignacion": "fecha_asignacion", "Observaciones": "observaciones", "Activo": "activo"}
BITACORA_MAP = {"FechaHora": "fecha_hora", "Usuario": "usuario", "Email": "email", "Rol": "rol", "Accion": "accion", "Detalles": "detalle"}
ENVIO_MAP = {"IDEnvio": "id_envio", "Fecha Hora": "fecha_hora", "Asunto Correo": "asunto_correo", "Cuerpo Mensaje": "cuerpo_mensaje", "Archivos a Enviar": "archivos_a_enviar", "Destinatarios": "destinatarios", "Estado": "estado", "Rutas Reales PDF": "rutas_reales_pdf"}
USUARIO_MAP = {"Nombre": "nombre", "Email": "email", "Rol": "rol", "Activo": "activo", "MenuPermitido": "menu_permitido", "PuedeVerBitacora": "puede_ver_bitacora"}
GENERADOR_MAP = {"ID_Reporte": "id_reporte", "Fecha Inicio": "fecha_inicio", "Fecha Fin": "fecha_fin", "Total Ofrenda": "total_ofrenda", "Total Asistencia": "total_asistencia", "Titulo de Reporte": "titulo_reporte", "Archivo Generado": "archivo_generado", "No Serie": "no_serie", "Mes Reporte": "mes_reporte", "Ano Reporte": "ano_reporte", "Filtro Lider": "filtro_lider", "Filtro Sup Sector": "filtro_sup_sector", "Filtro Sup Area": "filtro_sup_area", "Filtro Pastor Zona": "filtro_pastor_zona", "Filtro Distrito": "filtro_distrito", "Filtro Zona": "filtro_zona"}
BAUTIZO_MAP = {"ID": "id", "Fecha": "fecha", "Nombre": "nombre", "Edad": "edad", "Telefono": "telefono", "Direccion": "direccion", "PastorOficiante": "pastor_oficiante", "Lugar": "lugar", "Observaciones": "observaciones", "Activo": "activo"}

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
    return {"id": u.id, "nombre": u.nombre, "email": u.email, "rol": gas_role, "menu": menu, "isPropietario": u.rol == "propietario", "puedeVerBitacora": u.puede_ver_bitacora if hasattr(u, 'puede_ver_bitacora') else True, "PuedeEditar": "SI" if u.rol in ("propietario", "admin") else "NO", "inactMin": 60}

def gas_to_db(gas_key, field_map):
    return field_map.get(gas_key)

def payload_to_kwargs(field_map, payload):
    kwargs = {}
    for gas_key, db_key in field_map.items():
        if gas_key in payload:
            kwargs[db_key] = payload[gas_key]
    return kwargs

def db_to_gas(obj, field_map):
    d = {}
    for gas_key, db_key in field_map.items():
        val = getattr(obj, db_key, None)
        if val is not None:
            d[gas_key] = val
    return d

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
    item_id = payload.get(id_key) if isinstance(payload, dict) else payload
    if not item_id:
        return {"ok": False, "msg": "ID requerido"}
    obj = db.query(model_class).filter(model_class.id == item_id).first()
    if not obj:
        return {"ok": False, "msg": "Registro no encontrado"}
    db.delete(obj)
    db.commit()
    return {"ok": True}

@router.post("/dispatch")
def dispatch(data: dict, db: Session = Depends(get_db)):
    action = data.get("action", "")
    payload = data.get("payload", {})
    token = payload.get("token", data.get("token", ""))
    user = get_user_from_token(token, db) if token else None

    try:
        # ── AUTH ──
        if action == "login":
            email = payload.get("email", ""); password = payload.get("password", "")
            u = db.query(Usuario).filter(Usuario.email == email).first()
            if not u or not bcrypt.checkpw(password.encode(), u.password.encode()):
                return {"ok": False, "msg": "Credenciales inválidas"}
            if not u.activo: return {"ok": False, "msg": "Usuario inactivo"}
            new_token = jwt.encode({"id": u.id, "email": u.email, "rol": u.rol, "exp": datetime.utcnow() + timedelta(days=7)}, SECRET, algorithm="HS256")
            return {"ok": True, "token": new_token, "user": make_user_response(u)}

        if action == "validateSession":
            u = get_user_from_token(payload.get("token", ""), db)
            if u: return {"ok": True, "user": make_user_response(u)}
            return {"ok": False}

        if action == "destroySession":
            return {"ok": True}

        if action == "registrarAcceso":
            db.add(Bitacora(fecha_hora=datetime.utcnow(), usuario=payload.get("usuario",""), email=payload.get("email",""), rol=payload.get("rol",""), accion=payload.get("accion","Login"), detalle=payload.get("detalles","")))
            db.commit()
            return {"ok": True}

        # ── DASHBOARD ──
        if action == "getDashboard":
            lideres = db.query(Hermano).filter(Hermano.codigo_lead != None).count()
            reportes_mes = db.query(Reporte).count()
            pendientes = db.query(Reporte).filter(Reporte.ofrenda_recibida.in_(["Pendiente", ""])).count()
            asistencia_total = db.query(func.coalesce(func.sum(Reporte.asistencia), 0)).scalar()
            of_total = float(db.query(func.coalesce(func.sum(Reporte.ofrenda_total), 0)).scalar())
            seg_total = db.query(Seguimiento).count()
            return {"ok": True, "lideres": lideres, "reportesMes": reportes_mes, "gruposRealizados": reportes_mes, "asistencia": int(asistencia_total), "ofTotal": round(of_total, 2), "convertidos": 0, "reconciliados": 0, "segTotal": seg_total, "pendientes": pendientes, "metaGrupos": 407, "proxCron": [], "grafica": []}

        # ── HERMANOS (returns RAW ARRAY, matching GAS) ──
        if action == "getHermanos":
            hermanos = db.query(Hermano).all()
            return [db_to_gas(h, HERMANO_MAP) for h in hermanos]

        if action == "getHermanoByCodigo":
            h = db.query(Hermano).filter(Hermano.codigo_lead == payload.get("codigo")).first()
            if h: return {"ok": True, "data": db_to_gas(h, HERMANO_MAP)}
            return {"ok": False, "msg": "Hermano no encontrado"}

        if action == "saveHermano":
            return save_entity(db, Hermano, HERMANO_MAP, payload)

        if action == "deleteHermano":
            return delete_entity(db, Hermano, payload)

        # ── REPORTES (returns raw array) ──
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
            return [{"ID": r.id, "Codigo": r.codigo, "Lider": r.lider, "Fecha": str(r.fecha) if r.fecha else "", "Distrito": r.distrito, "Zona": r.zona, "Area": r.area, "Sector": r.sector, "Grupo": r.grupo, "Ofrenda Total": float(r.ofrenda_total or 0), "Ofrenda Recibida": r.ofrenda_recibida or "Pendiente", "Asistencia Grupo Familiar": r.asistencia or 0, "Hnos": r.hnos or 0, "Amigos": r.amigos or 0, "Niños": r.ninos or 0, "Tipo de Reporte": r.tipo_reporte or ""} for r in reportes]

        if action == "saveReporte":
            return save_entity(db, Reporte, HERMANO_MAP, payload)

        if action == "deleteReporte":
            return delete_entity(db, Reporte, payload)

        if action == "buscarLiderFormulario":
            query = payload.get("query", "")
            h = db.query(Hermano).filter(
                (Hermano.codigo_lead == query) | (Hermano.nombre.ilike(f"%{query}%"))
            ).first()
            if h: return {"ok": True, "data": db_to_gas(h, HERMANO_MAP)}
            return {"ok": False, "msg": "No encontrado"}

        if action == "registrarReporteDigital":
            from datetime import date
            codigo = str(payload.get("codigo","")).strip()
            herm = db.query(Hermano).filter(Hermano.codigo_lead == codigo).first()
            hnos = int(payload.get("hermanos",0) or 0)
            amigos = int(payload.get("amigos",0) or 0)
            ninos = int(payload.get("ninos",0) or 0)
            agf = hnos + amigos + ninos
            martes = int(payload.get("martes",0) or 0)
            jueves = int(payload.get("jueves",0) or 0)
            domingo = int(payload.get("domingo",0) or 0)
            otros = int(payload.get("otros",0) or 0)
            total_cultos_val = martes + jueves + domingo + otros
            of_ig = float(payload.get("ofrendaIglesia",0) or 0)
            of_bus = float(payload.get("ofrendaBus",0) or 0)
            of_tot = of_ig + of_bus
            seg_count = sum(1 for i in range(1,11) if payload.get(f"nombre{i}","") and str(payload.get(f"nombre{i}","")).strip())
            today = date.today()
            r = Reporte(
                codigo=codigo,
                lider=herm.nombre if herm else codigo,
                fecha=today,
                distrito=herm.distrito if herm else "",
                zona=herm.zona if herm else "",
                area=herm.area if herm else "",
                sector=herm.sector if herm else "",
                grupo=herm.grupo if herm else "",
                ofrenda_total=of_tot,
                ofrenda_recibida="Pendiente",
                asistencia=agf,
                hnos=hnos, amigos=amigos, ninos=ninos,
                tipo_reporte=payload.get("tipoReunion","Mixta (Reunión Regular)"),
                hora_inicio=str(payload.get("horaInicio","")),
                hora_final=str(payload.get("horaFinal","")),
                ofrenda_iglesia=of_ig, ofrenda_bus=of_bus,
                martes=martes, jueves=jueves, domingo=domingo, otros=otros,
                total_cultos=total_cultos_val,
                reporte_origen="Digital",
                sup_sector=herm.sup_sector if herm else "",
                sup_area=herm.sup_area if herm else "",
                pastor_zona=herm.pastor_zona if herm else "",
                anfitrion=herm.anfitrion if herm else "",
                direccion=herm.direccion if herm else "",
                seguimientos_count=seg_count,
            )
            db.add(r)
            db.commit()
            # Auto-registrar seguimientos
            lider_nombre = herm.nombre if herm else codigo
            for i in range(1, 11):
                nom = payload.get(f"nombre{i}","")
                if nom and str(nom).strip():
                    tipo = payload.get(f"tipo{i}","Otro")
                    existing = db.query(Seguimiento).filter(
                        Seguimiento.persona == str(nom).strip(),
                        Seguimiento.fecha == today,
                        Seguimiento.responsable == lider_nombre
                    ).first()
                    if not existing:
                        db.add(Seguimiento(
                            fecha=today, persona=str(nom).strip(),
                            tipo=tipo or "Otro", responsable=lider_nombre,
                            estado="En Proceso",
                            observaciones=f"Auto-registrado desde Formulario Digital · {lider_nombre}"
                        ))
            db.commit()
            return {"ok": True}

        if action == "getResumen":
            q = db.query(Reporte)
            if payload.get("desde"): q = q.filter(Reporte.fecha >= payload["desde"])
            if payload.get("hasta"): q = q.filter(Reporte.fecha <= payload["hasta"])
            reportes = q.all()
            total = len(reportes)
            asistencia = sum(r.asistencia or 0 for r in reportes)
            of_total = sum(float(r.ofrenda_total or 0) for r in reportes)
            pendientes = sum(1 for r in reportes if r.ofrenda_recibida in ("Pendiente", ""))
            hnos = sum(r.hnos or 0 for r in reportes)
            amigos = sum(r.amigos or 0 for r in reportes)
            return {"ok": True, "total": total, "asistencia": asistencia, "ofTotal": round(of_total, 2), "pendientes": pendientes, "hnos": hnos, "amigos": amigos}

        # ── CONFIG ──
        if action == "getConfig":
            configs = {}
            try:
                for c in db.query(Configuracion).all():
                    configs[c.clave] = c.valor
            except: pass
            return {"ok": True, "ssId": configs.get("ssId",""), "nombre": configs.get("nombre","REDIL"), "formUrl": configs.get("formUrl",""), "formUrlPublic": configs.get("formUrlPublic","https://redilrestauracion.totalappgt.online/formulario_digital.html"), "activo": True, "logo_url": configs.get("logo_url","https://i.postimg.cc/SsCZVFwp/Logo-Icono2.jpg"), "logoUrl": configs.get("logoUrl","https://i.postimg.cc/SsCZVFwp/Logo-Icono2.jpg"), "menuConfig": {m: True for m in ALL_MENU_IDS}, "ownerEmail": configs.get("ownerEmail","totalappgt@gmail.com"), "inactividadMinutos": int(configs.get("inactividadMinutos","60")), "metaGrupos": configs.get("metaGrupos","407"), "driveFolderId": configs.get("driveFolderId","1OHBSDIk7e1FOyC1tgkkAJoRb_nJh2CKM"), "botPdfFolderId": configs.get("botPdfFolderId",""), "pdf_id": configs.get("pdf_id",""), "gemini_api_key": configs.get("gemini_api_key",""), "openrouter_api_key": configs.get("openrouter_api_key",""), "deepseek_api_key": configs.get("deepseek_api_key",""), "telegram_token": configs.get("telegram_token",""), "telegram_chat_id": configs.get("telegram_chat_id",""), "whatsapp_soporte": configs.get("whatsapp_soporte","+502 5830-3182"), "nombre_soporte": configs.get("nombre_soporte","Total App GT - Daniel Martínez"), "titleMantenimiento": configs.get("titleMantenimiento","Sistema en Mantenimiento"), "msgMantenimiento": configs.get("msgMantenimiento","El sistema no está disponible en este momento."), "bot_habilitado": configs.get("bot_habilitado","True") == "True", "ai_provider": configs.get("ai_provider","auto"), "servicios_dinamicos": [], "cron_lunes": configs.get("cron_lunes","Lunes 6:30 PM"), "cron_jueves": configs.get("cron_jueves","Jueves 6:30 PM"), "cron_domTarde": configs.get("cron_domTarde","Domingo 10:30 AM"), "theme_colors": configs.get("theme_colors",""), "smtp_user": configs.get("smtp_user","totalappgt@gmail.com"), "smtp_password": configs.get("smtp_password","nnqx ifkr vecb imxq")}

        if action == "saveConfig":
            for key, val in payload.items():
                if key in ("token", "action"): continue
                existing = db.query(Configuracion).filter(Configuracion.clave == key).first()
                if existing: existing.valor = str(val)
                else: db.add(Configuracion(clave=key, valor=str(val)))
            db.commit()
            return {"ok": True}

        if action == "inicializarSistema":
            return {"ok": True, "msg": "Sistema listo. Configura tu bot de Telegram en Config."}

        # ── SEGUIMIENTOS (returns raw array) ──
        if action == "getSeguimientos":
            return [{"ID": s.id, "Fecha": str(s.fecha) if s.fecha else "", "Persona": s.persona, "Tipo": s.tipo, "Responsable": s.responsable, "Estado": s.estado, "Observaciones": s.observaciones} for s in db.query(Seguimiento).order_by(Seguimiento.fecha.desc()).limit(200).all()]

        if action == "saveSeguimiento":
            return save_entity(db, Seguimiento, {"Persona":"persona","Tipo":"tipo","Responsable":"responsable","Estado":"estado","Observaciones":"observaciones"}, payload)

        if action == "deleteSeguimiento":
            return delete_entity(db, Seguimiento, payload)

        # ── SUPERVISORES / PASTORES / AYUDA (wrapped in {ok, data}) ──
        if action == "getSupervisores":
            return {"ok": True, "data": [db_to_gas(s, SUPERVISOR_MAP) for s in db.query(Supervisor).all()]}

        if action == "saveSupervisor":
            return save_entity(db, Supervisor, SUPERVISOR_MAP, payload)

        if action == "deleteSupervisor":
            return delete_entity(db, Supervisor, payload)

        if action == "getPastores":
            return {"ok": True, "data": [db_to_gas(p, PASTOR_MAP) for p in db.query(Pastore).all()]}

        if action == "savePastor":
            return save_entity(db, Pastore, PASTOR_MAP, payload)

        if action == "deletePastor":
            return delete_entity(db, Pastore, payload)

        if action == "getAyudaPastor":
            return {"ok": True, "data": [db_to_gas(a, AYUDA_PASTOR_MAP) for a in db.query(AyudaPastor).all()]}

        if action == "saveAyudaPastor":
            return save_entity(db, AyudaPastor, AYUDA_PASTOR_MAP, payload)

        if action == "deleteAyudaPastor":
            return delete_entity(db, AyudaPastor, payload)

        # ── CONTACTOS (raw array) ──
        if action == "getContactos":
            return [db_to_gas(c, CONTACTO_MAP) for c in db.query(Contacto).all()]

        if action == "saveContacto":
            return save_entity(db, Contacto, CONTACTO_MAP, payload, id_key="IDContacto")

        if action == "deleteContacto":
            return delete_entity(db, Contacto, payload)

        # ── DIEZMOS (raw array) ──
        if action == "getDiezmos":
            q = db.query(Diezmo)
            if payload.get("desde"): q = q.filter(Diezmo.fecha >= payload["desde"])
            if payload.get("hasta"): q = q.filter(Diezmo.fecha <= payload["hasta"])
            return [db_to_gas(d, DIEZMO_MAP) for d in q.all()]

        if action == "saveDiezmo":
            return save_entity(db, Diezmo, DIEZMO_MAP, payload)

        if action == "deleteDiezmo":
            return delete_entity(db, Diezmo, payload)

        # ── GASTOS (returns {ok, gastos}) ──
        if action == "getGastos":
            q = db.query(Gasto)
            if payload.get("evento"): q = q.filter(Gasto.evento == payload["evento"])
            if payload.get("desde"): q = q.filter(Gasto.fecha >= payload["desde"])
            if payload.get("hasta"): q = q.filter(Gasto.fecha <= payload["hasta"])
            return {"ok": True, "gastos": [db_to_gas(g, GASTO_MAP) for g in q.all()]}

        if action == "saveGasto":
            return save_entity(db, Gasto, GASTO_MAP, payload, id_key="id")

        if action == "deleteGasto":
            return delete_entity(db, Gasto, payload)

        # ── INVENTARIO (raw array) ──
        if action == "getInventario":
            return [db_to_gas(i, INVENTARIO_MAP) for i in db.query(Inventario).all()]

        if action == "saveInventario":
            return save_entity(db, Inventario, INVENTARIO_MAP, payload)

        if action == "deleteInventario":
            return delete_entity(db, Inventario, payload)

        # ── INSUMOS (raw array) ──
        if action == "getInsumos":
            return [db_to_gas(i, INSUMO_MAP) for i in db.query(Insumo).all()]

        if action == "saveInsumo":
            return save_entity(db, Insumo, INSUMO_MAP, payload)

        if action == "deleteInsumo":
            return delete_entity(db, Insumo, payload)

        # ── PRIVILEGIOS (raw array) ──
        if action == "getPrivilegios":
            return [db_to_gas(p, PRIVILEGIO_MAP) for p in db.query(Privilegio).all()]

        if action == "savePrivilegio":
            return save_entity(db, Privilegio, PRIVILEGIO_MAP, payload)

        if action == "deletePrivilegio":
            return delete_entity(db, Privilegio, payload)

        # ── CRONOGRAMA (wrapped) ──
        if action == "getCronograma":
            return {"ok": True, "data": [db_to_gas(c, CRONOGRAMA_MAP) for c in db.query(Cronograma).all()]}

        if action == "saveCronograma":
            return save_entity(db, Cronograma, CRONOGRAMA_MAP, payload)

        if action == "deleteCronograma":
            return delete_entity(db, Cronograma, payload)

        # ── BAUTIZOS ──
        if action == "getBautizos":
            q = db.query(Bautizo).order_by(Bautizo.fecha.desc())
            if payload.get("desde"): q = q.filter(Bautizo.fecha >= payload["desde"])
            if payload.get("hasta"): q = q.filter(Bautizo.fecha <= payload["hasta"])
            return [db_to_gas(b, BAUTIZO_MAP) for b in q.all()]

        if action == "saveBautizo":
            return save_entity(db, Bautizo, BAUTIZO_MAP, payload)

        if action == "deleteBautizo":
            return delete_entity(db, Bautizo, payload)

        # ── BITACORA (raw array) ──
        if action == "getBitacora":
            q = db.query(Bitacora).order_by(Bitacora.fecha_hora.desc()).limit(500)
            if payload.get("desde"): q = q.filter(Bitacora.fecha_hora >= payload["desde"])
            if payload.get("hasta"): q = q.filter(Bitacora.fecha_hora <= payload["hasta"])
            return [db_to_gas(b, BITACORA_MAP) for b in q.all()]

        if action == "limpiarBitacora":
            db.query(Bitacora).delete(); db.commit()
            return {"ok": True}

        # ── ENVIOS (raw array) ──
        if action == "getEnvios":
            return [db_to_gas(e, ENVIO_MAP) for e in db.query(Envio).all()]

        # ── USUARIOS (raw array) ──
        if action == "getUsuarios":
            return [{"ID": u.id, "Nombre": u.nombre, "Email": u.email, "Rol": u.rol, "Activo": "SI" if u.activo else "NO", "MenuPermitido": u.menu_permitido or "", "PuedeVerBitacora": "SI" if u.puede_ver_bitacora else "NO"} for u in db.query(Usuario).all()]

        if action == "saveUsuario":
            item_id = payload.get("ID")
            data = payload_to_kwargs(USUARIO_MAP, payload)
            password = payload.get("Password", "")
            if password: data["password"] = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            if item_id:
                obj = db.query(Usuario).filter(Usuario.id == item_id).first()
                if not obj: return {"ok": False, "msg": "Usuario no encontrado"}
                for key, val in data.items(): setattr(obj, key, val)
            else:
                if "password" not in data: data["password"] = bcrypt.hashpw(b"redil2026", bcrypt.gensalt()).decode()
                obj = Usuario(**data)
                db.add(obj)
            db.commit()
            return {"ok": True}

        if action == "deleteUsuario":
            return delete_entity(db, Usuario, payload)

        # ── GENERADORES (raw array) ──
        if action == "getGeneradores":
            return [db_to_gas(g, GENERADOR_MAP) for g in db.query(GeneradorReporte).all()]

        # ── FORM URL ──
        if action == "getFormUrl":
            c = db.query(Configuracion).filter(Configuracion.clave == "formUrlPublic").first()
            url = c.valor if c else "https://redilrestauracion.totalappgt.online/formulario_digital.html"
            return {"ok": True, "url": url}

        if action == "getFormHtml":
            import os
            # Buscar en múltiples ubicaciones posibles
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            possible_paths = [
                os.path.join(base, "static", "formulario_digital.html"),
                os.path.join(os.getcwd(), "static", "formulario_digital.html"),
                os.path.join(os.getcwd(), "app", "static", "formulario_digital.html"),
            ]
            html_content = None
            for p in possible_paths:
                if os.path.exists(p):
                    with open(p, "r", encoding="utf-8") as f:
                        html_content = f.read()
                    break
            if html_content:
                return {"ok": True, "html": html_content}
            return {"ok": False, "msg": f"Formulario no encontrado. Buscado en: {possible_paths}"}

        # ── REPORTE FINANCIERO ──
        if action == "getReporteFinancieroDistrito":
            q = db.query(Reporte.distrito, Reporte.zona, func.count(Reporte.id).label("total_reportes"), func.coalesce(func.sum(Reporte.asistencia), 0).label("total_asistencia"), func.coalesce(func.sum(Reporte.ofrenda_total), 0).label("total_ofrenda"))
            if payload.get("desde"): q = q.filter(Reporte.fecha >= payload["desde"])
            if payload.get("hasta"): q = q.filter(Reporte.fecha <= payload["hasta"])
            rows = q.group_by(Reporte.distrito, Reporte.zona).all()
            data = [{"distrito": r.distrito or "", "zona": r.zona or "", "reportes": r.total_reportes, "asistencia": int(r.total_asistencia), "ofrendaTotal": float(r.total_ofrenda), "ofrendaRecibida": 0, "pendientes": 0} for r in rows]
            total_reportes = sum(r["reportes"] for r in data)
            total_asistencia = sum(r["asistencia"] for r in data)
            total_ofrenda = sum(r["ofrendaTotal"] for r in data)
            return {"ok": True, "byZona": data, "totalReportes": total_reportes, "totalAsistencia": total_asistencia, "totalOfrenda": round(total_ofrenda, 2)}

        # ── CUADRE DOMINICAL ──
        if action == "getCuadreDominical":
            fecha = payload.get("fecha", "")
            lideres = db.query(Hermano).filter(Hermano.codigo_lead != None).all()
            reportes_q = db.query(Reporte)
            if fecha:
                reportes_q = reportes_q.filter(Reporte.fecha == fecha)
            reportes = reportes_q.all()
            codigos_reportados = set(r.codigo for r in reportes)
            data, total_lideres, entregaron, pendientes_c, ofrenda_total = [], 0, 0, 0, 0.0
            for h in lideres:
                total_lideres += 1
                reporto = h.codigo_lead in codigos_reportados
                rpts = [r for r in reportes if r.codigo == h.codigo_lead]
                ofrenda = sum(float(r.ofrenda_total or 0) for r in rpts)
                ofrenda_total += ofrenda
                if reporto: entregaron += 1
                else: pendientes_c += 1
                data.append({"codigo": h.codigo_lead or "", "nombre": h.nombre or "", "tieneReporte": reporto, "ofrendaTotal": round(ofrenda, 2), "ofrendaRecibida": True if rpts and rpts[0].ofrenda_recibida not in ("Pendiente", "", None) else False, "pastorZona": h.pastor_zona or "", "supSector": h.sup_sector or ""})
            return {"ok": True, "data": data, "totalLideres": total_lideres, "entregaron": entregaron, "pendientes": pendientes_c, "ofrendaTotal": round(ofrenda_total, 2)}

        # ── CARGA MASIVA ──
        if action == "getEncabezadosCargaMasiva":
            tipo = payload.get("tipo", "")
            headers_map = {"hermanos": ['ID','CodigoL','NombreL','Distrito','Zona','Area','Sector','Grupo','Anfitrion','Direccion','Sup SectorL','Sup AreaL','Ayuda Pastor','Pastor Zona','CodigoSup','CodigoPastor'], "supervisores": ['ID','CodigoSup','NombreSup','Distrito','Zona','Area','Sector','Telefono','Email','Direccion','Activo'], "pastores": ['ID','CodigoPastor','NombrePastor','Distrito','Zona','Telefono','Email','Direccion','Activo'], "ayudapastor": ['ID','CodigoAyuda','NombreAyuda','Distrito','Zona','Area','Telefono','Email','Direccion','Activo']}
            return {"ok": True, "data": headers_map.get(tipo, [])}

        if action == "importarDatosMasivos":
            tipo = payload.get("tipo", ""); rows = payload.get("rows", [])
            if not rows: return {"ok": False, "msg": "No hay datos para importar"}
            tipo_map = {"hermanos": (Hermano, HERMANO_MAP), "supervisores": (Supervisor, SUPERVISOR_MAP), "pastores": (Pastore, PASTOR_MAP), "ayudapastor": (AyudaPastor, AYUDA_PASTOR_MAP)}
            pair = tipo_map.get(tipo)
            if not pair: return {"ok": False, "msg": f"Tipo '{tipo}' no soportado"}
            model_class, field_map = pair
            insertados = 0
            for row in rows:
                data = payload_to_kwargs(field_map, row)
                if data: db.add(model_class(**data)); insertados += 1
            db.commit()
            return {"ok": True, "msg": f"{insertados} registros importados"}

        # ── MISC ──
        if action == "invalidateDashCache":
            return {"ok": True}

        if action == "preguntarAI":
            pregunta = payload.get("pregunta", "")
            if not pregunta: return {"ok": False, "msg": "Pregunta requerida"}
            c = db.query(Configuracion).filter(Configuracion.clave == "gemini_api_key").first()
            api_key = c.valor if c else os.getenv("GEMINI_API_KEY", "")
            if not api_key: return {"ok": False, "msg": "API key de Gemini no configurada"}
            try:
                resp = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}", json={"contents": [{"parts": [{"text": pregunta}]}]}, timeout=30)
                if resp.status_code == 200:
                    parts = resp.json().get("candidates", [{}])[0].get("content", {}).get("parts", [])
                    return {"ok": True, "respuesta": parts[0].get("text","") if parts else ""}
                return {"ok": False, "msg": f"Error Gemini API: {resp.status_code}"}
            except Exception as e: return {"ok": False, "msg": str(e)}

        # ── ENVÍO DE CORREOS ──
        if action == "enviarReportesPorSeries":
            dest = payload.get("destinatarios", "")
            series = payload.get("series", [])
            asunto = payload.get("asunto", "")
            cuerpo = payload.get("cuerpo", "")
            emails_list = [e.strip() for e in dest.replace(";", ",").split(",") if e.strip()]
            if not emails_list: return {"ok": False, "msg": "Sin destinatarios"}
            cfg_dict = {}
            for c in db.query(Configuracion).all(): cfg_dict[c.clave] = c.valor
            sys_nom = cfg_dict.get("nombre", "REDIL")
            smtp_user = cfg_dict.get("smtp_user", "totalappgt@gmail.com")
            smtp_password = cfg_dict.get("smtp_password", "")
            gen_records = db.query(GeneradorReporte).filter(GeneradorReporte.no_serie.in_(series)).all()
            if not gen_records: return {"ok": False, "msg": f"No se encontraron reportes: {','.join(series)}"}
            html_parts = []
            total_asist, total_of, total_rptes = 0, 0, 0
            for gr in gen_records:
                q = db.query(Reporte)
                if gr.fecha_inicio: q = q.filter(Reporte.fecha >= gr.fecha_inicio)
                if gr.fecha_fin: q = q.filter(Reporte.fecha <= gr.fecha_fin)
                if gr.filtro_lider: q = q.filter(Reporte.lider == gr.filtro_lider)
                if gr.filtro_sup_area: q = q.filter(Reporte.sup_area == gr.filtro_sup_area)
                if gr.filtro_distrito: q = q.filter(Reporte.distrito == gr.filtro_distrito)
                if gr.filtro_zona: q = q.filter(Reporte.zona == gr.filtro_zona)
                rep_rows = q.order_by(Reporte.lider).all()
                total_rptes += len(rep_rows)
                by_lider = {}
                for r in rep_rows:
                    ln = r.lider or "Sin líder"
                    if ln not in by_lider:
                        by_lider[ln] = {"cod": r.codigo or "", "rptes": 0, "agf": 0, "hnos": 0, "amigos": 0, "ninos": 0, "of": 0, "pend": 0}
                    by_lider[ln]["rptes"] += 1
                    by_lider[ln]["agf"] += r.asistencia or 0
                    by_lider[ln]["hnos"] += r.hnos or 0
                    by_lider[ln]["amigos"] += r.amigos or 0
                    by_lider[ln]["ninos"] += r.ninos or 0
                    by_lider[ln]["of"] += float(r.ofrenda_total or 0)
                    if r.ofrenda_recibida in ("Pendiente", ""): by_lider[ln]["pend"] += 1
                asist_gr = sum(v["agf"] for v in by_lider.values())
                of_gr = sum(v["of"] for v in by_lider.values())
                total_asist += asist_gr; total_of += of_gr
                lider_rows = "".join(
                    f'<tr>'
                    f'<td style="padding:6px 10px;font-weight:700">{esc(ln)}{" <span style=color:#e74c3c>⚠"+str(v["pend"])+"</span>" if v["pend"] else ""}</td>'
                    f'<td style="padding:6px 10px;text-align:center">{v["cod"]}</td>'
                    f'<td style="padding:6px 10px;text-align:center">{v["rptes"]}</td>'
                    f'<td style="padding:6px 10px;text-align:center;font-weight:800">{v["agf"]}</td>'
                    f'<td style="padding:6px 10px;text-align:center">{v["hnos"]}</td>'
                    f'<td style="padding:6px 10px;text-align:center">{v["amigos"]}</td>'
                    f'<td style="padding:6px 10px;text-align:center">{v["ninos"]}</td>'
                    f'<td style="padding:6px 10px;text-align:right;font-weight:800">Q{v["of"]:.2f}</td></tr>'
                    for ln, v in sorted(by_lider.items())
                )
                fecha_desde = gr.fecha_inicio.strftime("%d/%m/%Y") if gr.fecha_inicio else "—"
                fecha_hasta = gr.fecha_fin.strftime("%d/%m/%Y") if gr.fecha_fin else "—"
                html_parts.append(f'''
                <div style="margin-bottom:24px;border-radius:12px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.1)">
                  <table width="100%" style="background:linear-gradient(135deg,#1a3a5c,#2563a8);color:#fff">
                    <tr>
                      <td style="padding:10px 14px;vertical-align:middle">
                        <div style="font-size:11px;opacity:.7;text-transform:uppercase;letter-spacing:1px">Reporte</div>
                        <div style="font-size:20px;font-weight:900">{gr.no_serie}</div>
                        <div style="font-size:12px;opacity:.8">{gr.titulo_reporte}</div>
                      </td>
                      <td style="padding:10px 14px;text-align:right;vertical-align:middle">
                        <div style="font-size:13px;opacity:.7">{fecha_desde} → {fecha_hasta}</div>
                        <div style="font-size:24px;font-weight:900;margin-top:2px">{len(rep_rows)}</div>
                        <div style="font-size:11px;opacity:.7">grupos</div>
                      </td>
                    </tr>
                  </table>
                  <table width="100%" style="border-collapse:collapse;background:#fff">
                    <tr>
                      <td style="padding:10px 6px;text-align:center;border-right:1px solid #eef0f5;vertical-align:middle">
                        <div style="font-size:18px;font-weight:900;color:#1a3a5c">{asist_gr}</div>
                        <div style="font-size:9px;color:#888;margin-top:2px">Asistencia</div>
                      </td>
                      <td style="padding:10px 6px;text-align:center;border-right:1px solid #eef0f5;vertical-align:middle">
                        <div style="font-size:18px;font-weight:900;color:#1e7e34">{sum(v["hnos"] for v in by_lider.values())}</div>
                        <div style="font-size:9px;color:#888;margin-top:2px">Hnos</div>
                      </td>
                      <td style="padding:10px 6px;text-align:center;border-right:1px solid #eef0f5;vertical-align:middle">
                        <div style="font-size:18px;font-weight:900;color:#2563a8">{sum(v["amigos"] for v in by_lider.values())}</div>
                        <div style="font-size:9px;color:#888;margin-top:2px">Amigos</div>
                      </td>
                      <td style="padding:10px 6px;text-align:center;border-right:1px solid #eef0f5;vertical-align:middle">
                        <div style="font-size:18px;font-weight:900;color:#7d3c98">{sum(v["ninos"] for v in by_lider.values())}</div>
                        <div style="font-size:9px;color:#888;margin-top:2px">Niños</div>
                      </td>
                      <td style="padding:10px 6px;text-align:center;border-right:1px solid #eef0f5;vertical-align:middle">
                        <div style="font-size:18px;font-weight:900;color:#c87f00">Q{of_gr:.2f}</div>
                        <div style="font-size:9px;color:#888;margin-top:2px">Ofrenda</div>
                      </td>
                    </tr>
                  </table>
                  <table style="width:100%;border-collapse:collapse;font-size:12px;background:#fff">
                    <thead><tr style="background:#f0f4ff">
                      <th style="padding:6px 10px;text-align:left;font-size:11px">Líder</th>
                      <th style="padding:6px 10px;text-align:center;font-size:11px">Cód</th>
                      <th style="padding:6px 10px;text-align:center;font-size:11px">Rptes</th>
                      <th style="padding:6px 10px;text-align:center;font-size:11px">AGF</th>
                      <th style="padding:6px 10px;text-align:center;font-size:11px">Hnos</th>
                      <th style="padding:6px 10px;text-align:center;font-size:11px">Amigos</th>
                      <th style="padding:6px 10px;text-align:center;font-size:11px">Niños</th>
                      <th style="padding:6px 10px;text-align:right;font-size:11px">Ofrenda</th>
                    </tr></thead>
                    <tbody>{lider_rows}</tbody>
                  </table>
                </div>''')
            subj = asunto or f"{sys_nom} · Informes · {datetime.now().strftime('%d/%m/%Y')}"
            logo_url = cfg_dict.get("logo_url", "")
            logo_html = f'<img src="{logo_url}" style="height:40px;vertical-align:middle;margin-right:10px">' if logo_url else ""
            full_html = f'''<!DOCTYPE html><html><head><meta charset="UTF-8"></head><body style="font-family:Arial,sans-serif;background:#f0f4f8;padding:20px">
              <div style="max-width:700px;margin:0 auto">
                <div style="text-align:center;padding:16px 0;color:#1a3a5c">
                  {logo_html}<span style="font-size:22px;font-weight:900">{sys_nom}</span>
                </div>
                {cuerpo + "<br><br>" if cuerpo else ""}
                {"".join(html_parts)}
                <div style="text-align:center;padding:16px;font-size:11px;color:#999">
                  {sys_nom} · Sistema de Reportes · {datetime.now().strftime('%d/%m/%Y %H:%M')}
                </div>
              </div></body></html>'''
            try:
                send_email(emails_list, subj, full_html, smtp_user=smtp_user, smtp_password=smtp_password)
                estado = "Enviado"
            except Exception as e:
                estado = f"Error: {str(e)}"
            db.add(Envio(fecha_envio=datetime.utcnow(), asunto=subj, mensaje=cuerpo, archivos_a_enviar=",".join(series), destinatarios=",".join(emails_list), estado=estado))
            db.commit()
            if estado != "Enviado":
                return {"ok": False, "msg": estado}
            return {"ok": True, "msg": "Enviado", "enviados": len(emails_list)}

        if action == "enviarReporte":
            dest = payload.get("destinatarios", "")
            asunto = payload.get("asunto", "")
            cuerpo = payload.get("cuerpo", "")
            filtros = payload.get("filtros", {})
            emails_list = [e.strip() for e in dest.replace(";", ",").split(",") if e.strip()]
            if not emails_list: return {"ok": False, "msg": "Sin destinatarios"}
            cfg_dict = {}
            for c in db.query(Configuracion).all(): cfg_dict[c.clave] = c.valor
            sys_nom = cfg_dict.get("nombre", "REDIL")
            smtp_user = cfg_dict.get("smtp_user", "totalappgt@gmail.com")
            smtp_password = cfg_dict.get("smtp_password", "")
            subj = asunto or f"{sys_nom} · Informe · {datetime.now().strftime('%d/%m/%Y')}"
            full_html = f'''<!DOCTYPE html><html><head><meta charset="UTF-8"></head><body style="font-family:Arial,sans-serif;padding:20px">
              <div style="max-width:600px;margin:0 auto"><h2 style="color:#1a3a5c">{sys_nom}</h2>
              {cuerpo or "<p>Se adjunta el informe solicitado.</p>"}</div></body></html>'''
            try:
                send_email(emails_list, subj, full_html, smtp_user=smtp_user, smtp_password=smtp_password)
                estado = "Enviado"
            except Exception as e:
                estado = f"Error: {str(e)}"
            db.add(Envio(fecha_envio=datetime.utcnow(), asunto=subj, mensaje=cuerpo, archivos_a_enviar="", destinatarios=",".join(emails_list), estado=estado))
            db.commit()
            if estado != "Enviado":
                return {"ok": False, "msg": estado}
            return {"ok": True, "msg": "Enviado", "enviados": len(emails_list)}

        if action == "exportExcel":
            return {"ok": False, "msg": "Exportación Excel disponible próximamente"}

        if action == "getAreaSupervisores":
            sup_map = {}
            for s in db.query(Supervisor).all():
                area = s.area or "Sin Area"
                if area not in sup_map: sup_map[area] = []
                sup_map[area].append(db_to_gas(s, SUPERVISOR_MAP))
            return {"ok": True, "data": sup_map}

        return {"ok": False, "msg": f"Acción '{action}' no implementada en API"}

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"ok": False, "msg": str(e)}
