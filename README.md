# REDIL SaaS v7.0

Migración profesional del sistema REDIL desde Google Apps Script a FastAPI + PostgreSQL + React.

## Estructura

```
REDIL_SAAS/
├── backend/           # API FastAPI (Python)
│   └── app/
│       ├── main.py        # Punto de entrada
│       ├── database.py    # Conexión PostgreSQL
│       ├── models.py      # Modelos SQLAlchemy
│       └── routers/       # Endpoints
│           ├── auth.py
│           ├── reportes.py
│           ├── hermanos.py
│           ├── seguimientos.py
│           └── telegram.py
├── frontend/          # React (futuro)
├── scripts/           # Migración de datos
└── .env.example
```

## Despliegue en Railway

1. Sube este proyecto a GitHub
2. En Railway: New Project → Deploy from GitHub
3. Railway detecta Python automáticamente
4. Agrega PostgreSQL: New → Database → PostgreSQL
5. Agrega variables de entorno en Railway Dashboard

## Variables de entorno

- DATABASE_URL: (Railway la asigna automática)
- JWT_SECRET: clave secreta para tokens
- TELEGRAM_TOKEN: token de tu bot
- TELEGRAM_CHAT_ID: chat ID
