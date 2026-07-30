from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Reporte, Hermano, Seguimiento
from datetime import date, timedelta, datetime
import os
import httpx
import json

router = APIRouter()

TOKEN = os.getenv("TELEGRAM_TOKEN", "")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

def tg_send(text, chat_id=None):
    if not TOKEN: return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": chat_id or CHAT_ID, "text": str(text)[:4000], "parse_mode": "HTML"}
    try: httpx.post(url, json=payload, timeout=10)
    except: pass

def esc(s): return str(s or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

# -- Pendientes (excepción) --
def cmd_pendientes(db):
    rs = db.query(Reporte).filter(Reporte.ofrenda_recibida.in_(["Pendiente", ""])).all()
    if not rs: return "✅ Todas las ofrendas recibidas."
    hnos = {h.codigo_lead: h for h in db.query(Hermano).all()}
    grupos = {}
    total_monto = 0
    for r in rs:
        h = hnos.get(r.codigo) or {}
        key = f"{h.distrito}|{h.zona}" if hasattr(h,'distrito') else "?|?"
        if key not in grupos:
            grupos[key] = {"distrito": getattr(h, 'distrito', '?'), "zona": getattr(h, 'zona', '?'), "items": [], "subtotal": 0}
        m = float(r.ofrenda_total or 0)
        grupos[key]["items"].append({
            "nombre": r.lider, "codigo": r.codigo, "monto": m,
            "fecha": str(r.fecha) if r.fecha else "—",
            "area": getattr(h, 'area', ''), "sector": getattr(h, 'sector', ''),
            "grupo": getattr(h, 'grupo', ''), "pastor": getattr(h, 'pastor_zona', '—')
        })
        grupos[key]["subtotal"] += m
        total_monto += m
    t = f"⚠️ <b>Pendientes: {len(rs)}</b> | Q{total_monto:.2f}\n"
    for k in sorted(grupos.keys())[:8]:
        g = grupos[k]
        t += f"\n📌 <b>D{g['distrito']} Z{g['zona']}</b> — {len(g['items'])} líderes — Q{g['subtotal']:.2f}\n"
        for it in g['items'][:8]:
            t += f"🔹 <b>{esc(it['nombre'])}</b> ({it['codigo']}) | {it['fecha']}\n   📍 A{it['area']} S{it['sector']} G{it['grupo']} | Q{it['monto']:.2f} | 🙏 {esc(it['pastor'])}\n"
    return t

# -- Webhook para Telegram --
class TelegramUpdate:
    def __init__(self, data):
        self.data = data

@router.post("/webhook")
async def webhook(data: dict, db: Session = Depends(get_db)):
    try:
        msg = data.get("message", {})
        txt = msg.get("text", "").strip()
        cid = msg.get("chat", {}).get("id")
        if not txt or not cid: return {"ok": True}
        
        cmd = txt.split()[0].lower()
        
        if cmd in ("/pendientes", "/pendiente"):
            tg_send(cmd_pendientes(db), cid)
        elif cmd == "/start":
            tg_send("🤖 <b>REDIL Bot v7.0</b>\nUsa /ayuda para comandos.", cid)
        else:
            tg_send("🤷 No entendí. Usa /ayuda para comandos.", cid)
        
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}
