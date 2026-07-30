from sqlalchemy import Column, Integer, String, Date, Numeric, Boolean, DateTime, Text
from app.database import Base
import datetime

class Hermano(Base):
    __tablename__ = "hermanos"
    id = Column(Integer, primary_key=True, index=True)
    codigo_lead = Column(String(50), unique=True, index=True)
    nombre = Column(String(200))
    distrito = Column(String(10))
    zona = Column(String(10))
    area = Column(String(10))
    sector = Column(String(10))
    grupo = Column(String(10))
    pastor_zona = Column(String(200))
    sup_sector = Column(String(200))
    sup_area = Column(String(200))
    ayuda_pastor = Column(String(200))
    anfitrion = Column(String(200))
    direccion = Column(Text)
    codigo_sup = Column(String(50))
    codigo_pastor = Column(String(50))

class Reporte(Base):
    __tablename__ = "reportes"
    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(50), index=True)
    lider = Column(String(200))
    fecha = Column(Date, index=True)
    distrito = Column(String(10))
    zona = Column(String(10))
    area = Column(String(10))
    sector = Column(String(10))
    grupo = Column(String(10))
    ofrenda_total = Column(Numeric(12, 2), default=0)
    ofrenda_recibida = Column(String(20), default="Pendiente")
    asistencia = Column(Integer, default=0)
    hnos = Column(Integer, default=0)
    amigos = Column(Integer, default=0)
    ninos = Column(Integer, default=0)
    tipo_reporte = Column(String(50))
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class Seguimiento(Base):
    __tablename__ = "seguimientos"
    id = Column(Integer, primary_key=True, index=True)
    fecha = Column(Date)
    persona = Column(String(200))
    tipo = Column(String(100))
    responsable = Column(String(200))
    estado = Column(String(50), default="Pendiente")
    observaciones = Column(Text)

class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(200))
    email = Column(String(200), unique=True, index=True)
    password = Column(String(200))
    rol = Column(String(50), default="usuario")
    activo = Column(Boolean, default=True)
    menu_permitido = Column(Text, nullable=True)
    puede_ver_bitacora = Column(Boolean, default=True)
