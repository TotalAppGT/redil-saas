import httpx
import os

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "EAATUvL0iC3cBSNsEmoNdwUmKBu3ZBaFhMES58Ym2onRFKMF8DwzZCe9O3N5YJDtlfHjnBYYbZBY1QBY2UnUAiO5wP6KAOwXKz500tAZApd0eHiLOVdHu7PFCmptpuWYEg4xXiib2MfhZB1cwQZAexBteGrxX8ZBlVfpAdZBq3TltNL4mekJbu2p8wNukEyT53gZDZD")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID", "1178159198722196")
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

def send_whatsapp_bulk(numbers, message):
    """Send WhatsApp message to multiple numbers"""
    results = []
    for num in numbers:
        r = send_whatsapp(num, message)
        results.append(r)
    ok_count = sum(1 for r in results if r.get("ok"))
    return {"ok": ok_count > 0, "msg": f"Enviado a {ok_count}/{len(numbers)} contactos"}

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
