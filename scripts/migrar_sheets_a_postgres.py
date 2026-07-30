"""
Script para migrar datos de Google Sheets a PostgreSQL.
1. Exporta tus planillas de GAS a CSV manualmente (Google Sheets → Descargar → CSV)
2. Ejecuta este script

O usa el modo automático con Google Sheets API.
"""

import csv
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv("../backend/.env")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/redil")

def migrar_hermanos(archivo_csv):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    with open(archivo_csv, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            cur.execute("""
                INSERT INTO hermanos (codigo_lead, nombre, distrito, zona, area, sector, grupo,
                    pastor_zona, sup_sector, sup_area, ayuda_pastor, anfitrion, direccion,
                    codigo_sup, codigo_pastor)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (codigo_lead) DO UPDATE SET nombre=EXCLUDED.nombre
            """, (
                row.get("CodigoL"), row.get("NombreL"),
                row.get("Distrito"), row.get("Zona"), row.get("Area"),
                row.get("Sector"), row.get("Grupo"),
                row.get("Pastor Zona"), row.get("Sup SectorL"),
                row.get("Sup AreaL"), row.get("Ayuda Pastor"),
                row.get("Anfitrion"), row.get("Direccion"),
                row.get("CodigoSup"), row.get("CodigoPastor")
            ))
            count += 1
        conn.commit()
    cur.close(); conn.close()
    print(f"✅ {count} hermanos migrados")

def migrar_reportes(archivo_csv):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    with open(archivo_csv, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            cur.execute("""
                INSERT INTO reportes (codigo, lider, fecha, distrito, zona, area, sector, grupo,
                    ofrenda_total, ofrenda_recibida, asistencia, hnos, amigos, ninos, tipo_reporte)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                row.get("Codigo"), row.get("Lider"), row.get("Fecha"),
                row.get("Distrito"), row.get("Zona"), row.get("Area"),
                row.get("Sector"), row.get("Grupo"),
                row.get("Ofrenda Total") or 0, row.get("Ofrenda Recibida") or "Pendiente",
                row.get("Asistencia Grupo Familiar") or 0,
                row.get("Hnos") or 0, row.get("Amigos") or 0, row.get("Niños") or 0,
                row.get("Tipo de Reporte") or ""
            ))
            count += 1
        conn.commit()
    cur.close(); conn.close()
    print(f"✅ {count} reportes migrados")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usa: python migrar_sheets_a_postgres.py <tabla> <archivo.csv>")
        print("Ej: python migrar_sheets_a_postgres.py hermanos Hermanos.csv")
        sys.exit(1)
    tabla = sys.argv[1]
    archivo = sys.argv[2]
    if tabla == "hermanos": migrar_hermanos(archivo)
    elif tabla == "reportes": migrar_reportes(archivo)
    else: print(f"Tabla '{tabla}' no soportada")
