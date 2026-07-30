import smtplib, os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465

def send_email(to_emails, subject, html_body, attachments=None, smtp_user=None, smtp_password=None):
    user = smtp_user or os.getenv("SMTP_USER", "totalappgt@gmail.com")
    password = smtp_password or os.getenv("SMTP_PASSWORD", "")
    if not password:
        raise ValueError("SMTP_PASSWORD no configurado")
    msg = MIMEMultipart("alternative")
    msg["From"] = user
    msg["To"] = ", ".join(to_emails)
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html"))
    if attachments:
        for att_data in attachments:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(att_data["content"])
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f'attachment; filename="{att_data["filename"]}"')
            msg.attach(part)
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
        server.login(user, password)
        server.sendmail(user, to_emails, msg.as_string())
