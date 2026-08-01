#!/usr/bin/env python3
"""Seed test data for REDIL system"""
import sys, os, json, random
from datetime import date, timedelta, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.database import SessionLocal
from app.models import (
    Hermano, Reporte, Seguimiento, Supervisor, Pastore, AyudaPastor,
    Contacto, Diezmo, Gasto, Inventario, Insumo, Privilegio,
    Cronograma, Bautizo
)

db = SessionLocal()

# ── LIMPIAR DATOS EXISTENTES ──
for model in [Hermano, Reporte, Seguimiento, Supervisor, Pastore, AyudaPastor, Contacto, Diezmo, Gasto, Inventario, Insumo, Privilegio, Cronograma, Bautizo]:
    try:
        db.query(model).delete()
    except: pass
db.commit()
print("✅ Datos anteriores limpiados")

# ── SUPERVISORES ──
supervisores = [
    Supervisor(codigo_sup="SP001", nombre_sup="Carlos López", distrito="1", zona="1", area="A", sector="1", telefono="5551-0001", email="carlos@iglesia.com", activo=True),
    Supervisor(codigo_sup="SP002", nombre_sup="María Ramírez", distrito="1", zona="2", area="B", sector="1", telefono="5551-0002", email="maria@iglesia.com", activo=True),
    Supervisor(codigo_sup="SP003", nombre_sup="José Méndez", distrito="2", zona="1", area="A", sector="1", telefono="5552-0001", email="jose@iglesia.com", activo=True),
]
db.add_all(supervisores)

# ── PASTORES ──
pastores = [
    Pastore(codigo_pastor="PZ01", nombre_pastor="Fernando García", distrito="1", zona="1", telefono="5550-1001", email="fernando@iglesia.com", activo=True),
    Pastore(codigo_pastor="PZ02", nombre_pastor="Ana Morales", distrito="1", zona="2", telefono="5550-1002", email="ana@iglesia.com", activo=True),
    Pastore(codigo_pastor="PZ03", nombre_pastor="Pedro Hernández", distrito="2", zona="1", telefono="5550-1003", email="pedro@iglesia.com", activo=True),
]
db.add_all(pastores)

# ── AYUDA PASTOR ──
ayudas = [
    AyudaPastor(codigo_ayuda="AP01", nombre_ayuda="Luis Castillo", distrito="1", zona="1", area="A", telefono="5550-2001", email="luis@iglesia.com", activo=True),
    AyudaPastor(codigo_ayuda="AP02", nombre_ayuda="Sofía Díaz", distrito="1", zona="1", area="B", telefono="5550-2002", email="sofia@iglesia.com", activo=True),
]
db.add_all(ayudas)

# ── HERMANOS LÍDERES (50) ──
nombres_lideres = [
    "Juan Pérez", "María Gómez", "Carlos Ruiz", "Ana Martínez", "Luis Sánchez",
    "Elena Torres", "Pedro Vargas", "Sofía López", "Diego Ramírez", "Laura Jiménez",
    "Miguel Ángel Cruz", "Carmen Flores", "Roberto Ortiz", "Patricia Núñez", "Francisco Reyes",
    "Gabriela Mendoza", "Antonio Rojas", "Isabel Delgado", "Ricardo Castro", "Verónica Peña",
    "Alejandro Mora", "Daniela Herrera", "Oscar Pineda", "Lucía Aguirre", "Manuel Esquivel",
    "Raquel Medina", "Felipe Campos", "Natalia Vega", "Héctor Fuentes", "Adriana León",
    "Jorge Rivas", "Cecilia Avila", "Rubén Solís", "Mónica Ortega", "Alberto Farfán",
    "Silvia Calderón", "Eduardo Miranda", "Rosa Benítez", "Enrique Gallardo", "Teresa Cárdenas",
    "Samuel Arévalo", "Paola Gutiérrez", "David Valle", "Margarita Ponce", "Arturo Chávez",
    "Brenda Rosales", "Gustavo Rangel", "Alicia Padilla", "César Ochoa", "Claudia Serrano"
]
distritos = ["1", "1", "1", "1", "2", "2", "2", "3", "3", "1"]
zonas = ["1", "1", "1", "2", "1", "2", "2", "1", "1", "2"]
areas = list("ABCDEFGHIJ")
pastores_zona = ["Fernando García", "Fernando García", "Ana Morales", "Ana Morales",
                  "Pedro Hernández", "Pedro Hernández", "Fernando García", "Ana Morales",
                  "Pedro Hernández", "Fernando García"]
sup_sectores = ["Carlos López", "Carlos López", "María Ramírez", "María Ramírez",
                 "José Méndez", "José Méndez", "Carlos López", "María Ramírez",
                 "José Méndez", "Carlos López"]
sup_areas = ["Luis Castillo", "Luis Castillo", "Sofía Díaz", "Sofía Díaz",
              "Luis Castillo", "Sofía Díaz", "Luis Castillo", "Sofía Díaz",
              "Luis Castillo", "Sofía Díaz"]

hermanos_data = []
for i, nombre in enumerate(nombres_lideres):
    d = distritos[i % 10]
    z = zonas[i % 10]
    a = areas[i // 5 % 10]
    s = str((i % 5) + 1)
    g = str((i % 3) + 1)
    codigo = f"{d}{z}{a}{s}{g}"
    hermanos_data.append(Hermano(
        codigo_lead=codigo, nombre=nombre,
        distrito=d, zona=z, area=a, sector=s, grupo=g,
        pastor_zona=pastores_zona[i % 10],
        sup_sector=sup_sectores[i % 10],
        sup_area=sup_areas[i % 10],
        anfitrion=f"Casa de {nombre.split()[0]}",
        direccion=f"{random.randint(1,50)} Calle {random.choice(['Principal','Real','Central'])} Zona {z}"
    ))
db.add_all(hermanos_data)

# ── REPORTES (150 para los últimos 3 meses) ──
tipos = ["Mixta (Reunión Regular)", "Solo Adultos", "Jóvenes", "Damas", "Caballeros"]
origens = ["Manual", "Digital", "Manual", "Digital", "Manual", "Manual"]
hoy = date.today()
reportes_data = []
for _ in range(150):
    lider_idx = random.randint(0, 49)
    h = hermanos_data[lider_idx]
    dias_offset = random.randint(0, 90)
    f = hoy - timedelta(days=dias_offset)
    asistencia = random.randint(5, 45)
    ofrenda = round(random.uniform(25, 300), 2)
    recibida = random.choice(["Recibida", "Recibida", "Pendiente", "Recibida"])
    reportes_data.append(Reporte(
        codigo=h.codigo_lead, lider=h.nombre,
        fecha=f, distrito=h.distrito, zona=h.zona,
        area=h.area, sector=h.sector, grupo=h.grupo,
        ofrenda_total=ofrenda, ofrenda_recibida=recibida,
        asistencia=asistencia, hnos=random.randint(2, 20),
        amigos=random.randint(0, 15), ninos=random.randint(0, 10),
        tipo_reporte=random.choice(tipos),
        reporte_origen=random.choice(origens),
        sup_sector=h.sup_sector, sup_area=h.sup_area,
        pastor_zona=h.pastor_zona, anfitrion=h.anfitrion,
        seguimientos_count=random.randint(0, 5)
    ))
db.add_all(reportes_data)

# ── SEGUIMIENTOS (80) ──
personas_seg = ["Marta Álvarez", "José Ibarra", "Rosa Elena", "Francisco Paz", "Julia Ventura",
                 "David Reyes", "Sara Montero", "Tomás Aguilar", "Nora Vidal", "Ángel Corona"]
estados_seg = ["Pendiente", "En Proceso", "Completado", "Pendiente", "En Proceso", "Completado"]
tipos_seg = ["Convertido", "Reconciliación", "Visita Programada", "Sanidad", "Oración", "Otro"]
segs = []
for _ in range(80):
    h = random.choice(hermanos_data)
    segs.append(Seguimiento(
        fecha=hoy - timedelta(days=random.randint(0, 60)),
        persona=random.choice(personas_seg),
        tipo=random.choice(tipos_seg),
        responsable=h.nombre,
        estado=random.choice(estados_seg),
        observaciones="Seguimiento registrado por líder"
    ))
db.add_all(segs)

# ── DIEZMOS (40) ──
for _ in range(40):
    h = random.choice(hermanos_data)
    db.add(Diezmo(
        codigo=h.codigo_lead, nombre=h.nombre,
        fecha=hoy - timedelta(days=random.randint(0, 60)),
        telefono=f"5550-{random.randint(1000,9999)}",
        grupo=h.grupo, monto=round(random.uniform(50, 500), 2),
        tipo=random.choice(["Diezmo", "Ofrenda", "Siembra"]),
        observaciones="Registro de diezmo"
    ))

# ── GASTOS (30) ──
categorias = ["Limpieza", "Mantenimiento", "Eventos", "Papelería", "Ayuda Social", "Transporte"]
for _ in range(30):
    db.add(Gasto(
        concepto=random.choice(["Compra insumos", "Reparación equipo", "Actividad especial", "Refrigerio", "Material didáctico"]),
        evento=random.choice(["Servicio Dominical", "Reunión Líderes", "Evento Especial", "Conferencia", ""]),
        monto=round(random.uniform(25, 800), 2),
        fecha=hoy - timedelta(days=random.randint(0, 90)),
        categoria=random.choice(categorias),
        descripcion="Gasto registrado",
        responsable=random.choice(["Fernando García", "Ana Morales", "Pedro Hernández"]),
        metodo=random.choice(["Efectivo", "Transferencia", "Tarjeta"])
    ))

# ── INVENTARIO (15) ──
items_inv = [
    ("Sillas plegables", "Mobiliario", 80, "Unidad", "Bueno", "Salón Principal", 12000),
    ("Mesas", "Mobiliario", 15, "Unidad", "Bueno", "Salón Principal", 4500),
    ("Micrófonos", "Equipo A/V", 4, "Unidad", "Bueno", "Cabina Audio", 3200),
    ("Amplificador", "Equipo A/V", 1, "Unidad", "Bueno", "Cabina Audio", 8500),
    ("Guitarra acústica", "Instrumento", 2, "Unidad", "Bueno", "Sala Ensayos", 4000),
    ("Teclado", "Instrumento", 1, "Unidad", "Regular", "Sala Ensayos", 6500),
    ("Proyector", "Equipo A/V", 1, "Unidad", "Bueno", "Salón Principal", 7800),
    ("Biblias", "Papelería", 40, "Unidad", "Bueno", "Librería", 3200),
    ("Himnarios", "Papelería", 30, "Unidad", "Bueno", "Librería", 1800),
    ("Estufa industrial", "Cocina", 1, "Unidad", "Bueno", "Cocina", 5200),
    ("Refrigerador", "Cocina", 1, "Unidad", "Bueno", "Cocina", 9000),
    ("Bancas largas", "Mobiliario", 10, "Unidad", "Regular", "Patio", 2500),
    ("Pantalla LED", "Equipo A/V", 1, "Unidad", "Bueno", "Salón Principal", 12000),
    ("Batería", "Instrumento", 1, "Unidad", "Regular", "Sala Ensayos", 7000),
    ("Plantas decorativas", "Decoración", 12, "Unidad", "Bueno", "Varios", 2400),
]
for nombre, cat, cant, uni, est, ubi, val in items_inv:
    db.add(Inventario(nombre=nombre, categoria=cat, cantidad=cant, unidad=uni, estado=est, ubicacion=ubi, valor_q=val))

# ── INSUMOS (15) ──
items_ins = [
    ("Papel bond resmas", "Papelería", 25, "Resma", 45, 5, "Office Depot"),
    ("Bolígrafos", "Papelería", 100, "Unidad", 3, 20, "Office Depot"),
    ("Marcadores pizarra", "Papelería", 24, "Unidad", 8, 6, "Office Depot"),
    ("Jabón líquido", "Limpieza", 8, "Galón", 65, 2, "Distribuidora GT"),
    ("Cloro", "Limpieza", 12, "Galón", 28, 3, "Supermercado"),
    ("Papel higiénico", "Higiene", 48, "Rollo", 4, 12, "Supermercado"),
    ("Desinfectante", "Limpieza", 6, "Galón", 55, 2, "Distribuidora GT"),
    ("Platos desechables", "Cocina", 200, "Unidad", 1.5, 50, "Supermercado"),
    ("Vasos desechables", "Cocina", 300, "Unidad", 0.8, 80, "Supermercado"),
    ("Servilletas", "Cocina", 500, "Unidad", 0.3, 100, "Supermercado"),
    ("Pilas AA", "Mantenimiento", 24, "Unidad", 12, 6, "Ferretería"),
    ("Focos LED", "Mantenimiento", 12, "Unidad", 35, 3, "Ferretería"),
    ("Toallas de papel", "Higiene", 18, "Rollo", 22, 4, "Distribuidora GT"),
    ("Bolsas de basura", "Limpieza", 40, "Unidad", 5, 10, "Supermercado"),
    ("Agua pura garrafón", "Cocina", 15, "Garrafón", 18, 3, "Agua Pura GT"),
]
for nombre, cat, cant, uni, precio, stock, prov in items_ins:
    db.add(Insumo(nombre=nombre, categoria=cat, cantidad=cant, unidad=uni, precio_unitario_q=precio, stock_minimo=stock, proveedor=prov))

# ── CONTACTOS ──
contactos = [
    Contacto(nombre="Proveedor Audio", telefono="5550-3001", email="audio@proveedor.com", direccion="Zona 1, Guatemala"),
    Contacto(nombre="Distribuidora Limpieza", telefono="5550-3002", email="ventas@distribuidora.com", direccion="Zona 9, Guatemala"),
    Contacto(nombre="Imprenta Cristiana", telefono="5550-3003", email="info@imprenta.com", direccion="Zona 4, Guatemala"),
    Contacto(nombre="Mantenimiento Equipos", telefono="5550-3004", email="soporte@equipos.com", direccion="Zona 10, Guatemala"),
]
db.add_all(contactos)

# ── BAUTIZOS ──
bautizos_data = [
    Bautizo(fecha=date.today()-timedelta(days=15), nombre="Andrea Castillo", edad=22, telefono="5555-1001", direccion="Zona 1, Mixco", pastor_oficiante="Fernando García", lugar="Iglesia Central"),
    Bautizo(fecha=date.today()-timedelta(days=8), nombre="Ricardo Palma", edad=18, telefono="5555-1002", direccion="Zona 2, Villa Nueva", pastor_oficiante="Ana Morales", lugar="Iglesia Sede Norte"),
    Bautizo(fecha=date.today()-timedelta(days=3), nombre="Valentina Ruiz", edad=15, telefono="5555-1003", direccion="Zona 5, Guatemala", pastor_oficiante="Pedro Hernández", lugar="Iglesia Central"),
]
db.add_all(bautizos_data)

# ── PRIVILEGIOS ──
for _ in range(20):
    h = random.choice(hermanos_data)
    db.add(Privilegio(
        codigo_lead=h.codigo_lead, nombre=h.nombre,
        area=h.area,
        privilegio=random.choice(["Predicador", "Maestro Escuela Dominical", "Diácono", "Ujier", "Líder Alabanza"]),
        fecha_inicio=hoy - timedelta(days=random.randint(30, 180)),
        fecha_fin=hoy + timedelta(days=random.randint(30, 180)),
        activo=True,
        observaciones="Asignación de privilegio"
    ))

# ── CRONOGRAMA ──
servicios = ["Servicio General", "Escuela Dominical", "Jóvenes", "Damas", "Caballeros"]
for _ in range(25):
    h = random.choice(hermanos_data)
    db.add(Cronograma(
        hermano=h.nombre, area=h.area, servicio=random.choice(servicios),
        privilegio=random.choice(["Asignado", "Titular", "Suplente"]),
        lunes=random.choice(["SI", "NO", "SI"]),
        jueves=random.choice(["SI", "NO"]),
        domingo_manana=random.choice(["SI", "SI", "NO"]),
        domingo_tarde=random.choice(["SI", "NO"]),
        fecha_asignacion=hoy - timedelta(days=random.randint(0, 30)),
        activo=True
    ))

db.commit()
print(f"""
✅ DATOS DE PRUEBA CARGADOS:
   👥 {len(hermanos_data)} Hermanos Líderes
   📋 {len(reportes_data)} Reportes
   📝 {len(segs)} Seguimientos
   👤 {len(supervisores)} Supervisores
   🙏 {len(pastores)} Pastores
   💰 40 Diezmos
   💸 30 Gastos
   📦 15 Inventario
   🧴 15 Insumos
   📇 4 Contactos
   💧 {len(bautizos_data)} Bautizos
   👑 20 Privilegios
   📅 25 Cronograma
""")
db.close()
