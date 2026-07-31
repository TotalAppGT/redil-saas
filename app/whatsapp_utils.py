import httpx
import os

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID", "")
WHATSAPP_API = f"https://graph.facebook.com/v22.0/{WHATSAPP_PHONE_ID}/messages" if WHATSAPP_PHONE_ID else ""

def send_whatsapp(to_number, message, db=None):
    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_ID:
        return {"ok": False, "msg": "WhatsApp no configurado"}
    try:
        resp = httpx.post(
            WHATSAPP_API,
            json={
                "messaging_product": "whatsapp",
                "to": str(to_number).replace("+", "").replace(" ", "").replace("-", ""),
                "type": "text",
                "text": {"body": str(message)[:4000]}
            },
            headers={
                "Authorization": f"Bearer {WHATSAPP_TOKEN}",
                "Content-Type": "application/json"
            },
            timeout=15
        )
        return {"ok": resp.status_code < 400, "msg": resp.text[:200] if resp.status_code >= 400 else "Enviado"}
    except Exception as e:
        return {"ok": False, "msg": str(e)}

def send_whatsapp_template(to_number, template_name, params=None):
    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_ID:
        return {"ok": False, "msg": "WhatsApp no configurado"}
    try:
        body = {
            "messaging_product": "whatsapp",
            "to": str(to_number).replace("+", "").replace(" ", "").replace("-", ""),
            "type": "template",
            "template": {"name": template_name, "language": {"code": "es"}}
        }
        if params:
            body["template"]["components"] = [{
                "type": "body",
                "parameters": [{"type": "text", "text": str(p)} for p in params]
            }]
        resp = httpx.post(
            WHATSAPP_API,
            json=body,
            headers={
                "Authorization": f"Bearer {WHATSAPP_TOKEN}",
                "Content-Type": "application/json"
            },
            timeout=15
        )
        return {"ok": resp.status_code < 400, "msg": resp.text[:200] if resp.status_code >= 400 else "Enviado"}
    except Exception as e:
        return {"ok": False, "msg": str(e)}
