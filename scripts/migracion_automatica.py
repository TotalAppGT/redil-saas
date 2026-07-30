"""
MIGRACIÓN AUTOMÁTICA: Google Sheets → PostgreSQL (Railway)
Script único que lee tus datos de Google Sheets y los migra a tu base de datos.

INSTRUCCIONES PREVIAS (solo 1 vez):
1. Ve a https://console.cloud.google.com/ → Credenciales → Crear cuenta de servicio
2. Dale rol "Editor" y genera una clave JSON → descárgala
3. Comparte tus planillas con el email de la cuenta de servicio
4. Pon el JSON en esta misma carpeta como "credentials.json"
5. Instala dependencias: pip install gspread google-auth psycopg2-binary python-dotenv
6. Ejecuta: python migracion_automatica.py
"""

import os, sys
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv("../.env")

# ─── CONFIGURACIÓN ────────────────────────────────────
# ID de tu Spreadsheet principal (el mismo de Código.js)
SPREADSHEET_ID = "1iLNbaqKwGRHGqRB1BJ0K1Sbyc53nD7uFD_UmVe91_Io"

# Nombres de las hojas (igual que en Código.js)
SHEETS = {
    "hermanos": "Hermanos",
    "reportes": "Reporte",
    "seguimientos": "Seguimientos",
    "usuarios": "Usuarios",
}

# ─── CONEXIÓN A GOOGLE SHEETS ─────────────────────────
def conectar_google_sheets():
    import gspread
    from google.oauth2.service_account import Credentials
    
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    # Buscar el JSON de credenciales
    json_path = None
    for f in ["credentials.json", "credenciales.json", "service_account.json"]:
        if os.path.exists(f):
            json_path = f
            break
    
    if not json_path:
        print("❌ No encontré el archivo credentials.json")
        print("📌 Pasos para crearlo:")
        print("   1. Ve a https://console.cloud.google.com/")
        print("   2. Crea un proyecto → APIs y Servicios → Habilitar Google Sheets API")
        print("   3. Credenciales → Crear cuenta de servicio → darle rol Editor")
        print("   4. Generar clave JSON → descargar como credentials.json")
        print("   5. Comparte tu planilla con el email que aparece en el JSON")
        sys.exit(1)
    
    creds = Credentials.from_service_account_file(json_path, scopes=scope)
    gc = gspread.authorize(creds)
    return gc

# ─── MIGRACIÓN ────────────────────────────────────────
def migrar_hermanos(db, ws):
    from app.models import Hermano
    from sqlalchemy.orm import Session
    
    data = ws.get_all_records()
    count = 0
    for row in data:
        h = Hermano(
            codigo_lead=row.get("CodigoL", ""),
            nombre=row.get("NombreL", ""),
            distrito=str(row.get("Distrito", "")),
            zona=str(row.get("Zona", "")),
            area=str(row.get("Area", "")),
            sector=str(row.get("Sector", "")),
            grupo=str(row.get("Grupo", "")),
            pastor_zona=row.get("Pastor Zona", ""),
            sup_sector=row.get("Sup SectorL", ""),
            sup_area=row.get("Sup AreaL", ""),
            ayuda_pastor=row.get("Ayuda Pastor", ""),
            anfitrion=row.get("Anfitrion", ""),
            direccion=row.get("Direccion", ""),
            codigo_sup=row.get("CodigoSup", ""),
            codigo_pastor=row.get("CodigoPastor", ""),
        )
        db.add(h)
        count += 1
    db.commit()
    print(f"✅ {count} hermanos migrados")

def migrar_reportes(db, ws):
    from app.models import Reporte
    data = ws.get_all_records()
    count = 0
    for row in data:
        r = Reporte(
            codigo=row.get("Codigo", ""),
            lider=row.get("Lider", ""),
            fecha=row.get("Fecha", None),
            distrito=str(row.get("Distrito", "")),
            zona=str(row.get("Zona", "")),
            area=str(row.get("Area", "")),
            sector=str(row.get("Sector", "")),
            grupo=str(row.get("Grupo", "")),
            ofrenda_total=float(row.get("Ofrenda Total", 0) or 0),
            ofrenda_recibida=row.get("Ofrenda Recibida", "Pendiente") or "Pendiente",
            asistencia=int(row.get("Asistencia Grupo Familiar", 0) or 0),
            hnos=int(row.get("Hnos", 0) or 0),
            amigos=int(row.get("Amigos", 0) or 0),
            ninos=int(row.get("Niños", 0) or 0),
            tipo_reporte=row.get("Tipo de Reporte", ""),
        )
        db.add(r)
        count += 1
    db.commit()
    print(f"✅ {count} reportes migrados")

def migrar_seguimientos(db, ws):
    from app.models import Seguimiento
    data = ws.get_all_records()
    count = 0
    for row in data:
        s = Seguimiento(
            fecha=row.get("Fecha", None),
            persona=row.get("Persona", ""),
            tipo=row.get("Tipo", ""),
            responsable=row.get("Responsable", ""),
            estado=row.get("Estado", "Pendiente"),
            observaciones=row.get("Observaciones", ""),
        )
        db.add(s)
        count += 1
    db.commit()
    print(f"✅ {count} seguimientos migrados")

# ─── MAIN ─────────────────────────────────────────────
def main():
    print("🚀 Iniciando migración Google Sheets → PostgreSQL...\n")
    
    # 1. Conectar a Google Sheets
    gc = conectar_google_sheets()
    sh = gc.open_by_key(SPREADSHEET_ID)
    
    # 2. Conectar a PostgreSQL (Railway)
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL or "localhost" in DATABASE_URL:
        print("❌ DATABASE_URL no está configurada o es localhost")
        print("📌 En Railway: la variable DATABASE_URL se asigna automática")
        sys.exit(1)
    
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.database import Base
    
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    # 3. Migrar cada hoja
    for nombre, hoja in SHEETS.items():
        try:
            ws = sh.worksheet(hoja)
            print(f"📄 Leyendo hoja: {hoja}...")
            if nombre == "hermanos":
                migrar_hermanos(db, ws)
            elif nombre == "reportes":
                migrar_reportes(db, ws)
            elif nombre == "seguimientos":
                migrar_seguimientos(db, ws)
            elif nombre == "usuarios":
                print("⚠️ Usuarios: pendiente de implementar")
        except Exception as e:
            print(f"⚠️ Hoja '{hoja}': {e}")
    
    db.close()
    print("\n🎉 Migración completada")

if __name__ == "__main__":
    main()
