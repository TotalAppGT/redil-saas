from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Usuario
from pydantic import BaseModel
import bcrypt
import jwt
import os
from datetime import datetime, timedelta

router = APIRouter()
SECRET = os.getenv("JWT_SECRET", "redil_secret_key_2026")

class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(Usuario).filter(Usuario.email == req.email).first()
    if not user or not bcrypt.checkpw(req.password.encode(), user.password.encode()):
        raise HTTPException(401, "Credenciales inválidas")
    if not user.activo:
        raise HTTPException(401, "Usuario inactivo")
    token = jwt.encode({
        "id": user.id, "email": user.email, "rol": user.rol,
        "exp": datetime.utcnow() + timedelta(days=7)
    }, SECRET, algorithm="HS256")
    return {"token": token, "usuario": {"nombre": user.nombre, "email": user.email, "rol": user.rol}}
