# EduMúsic Leaderboard API

API REST mínima (FastAPI + SQLite) para el ranking compartido de EduMúsic.
Sustituye a Firebase Firestore (proyecto `edumusic-f67e0`), que era el backend
del ranking hasta 2026-09.

Usa `edutictac-community` como núcleo común para conexión SQLite con WAL y rate
limit en memoria. La lógica de ranking semanal y global sigue siendo local de
EduMúsic.

## Endpoints

- `GET /api/health` → `{"status": "ok"}`
- `GET /api/scores?game_id=<id>&period=all-time|weekly&limit=<n>` → top N por puntuación (desc) y antigüedad (asc).
- `POST /api/scores` con `{"game_id": "...", "name": "ABC", "score": 123}` → crea la entrada.

`name` se normaliza a 3 iniciales (A-Z0-9); `score` entre 0 y 9999. La semana
semanal (`week_key`) se calcula en lunes 00:01 UTC, igual que el cliente.

## Ejecución local

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8003
```

## Núcleo común

Dependencia estable actual:

```txt
edutictac-community @ git+https://git.edutictac.es/Edutictac/edutictac-community.git@v0.1.1
```

Componentes reutilizados:

- `edutictac_community.db.connect` para SQLite con WAL.
- `edutictac_community.ratelimit.RateLimiter` para límites en memoria.

Tests:

```bash
pytest -q
```

## Despliegue (VPS aulessocarrades)

Código en `/opt/edumusic-api`, servicio systemd `edumusic-api.service`
(uvicorn en `127.0.0.1:8003`), expuesto por nginx en
`edumusic.edutictac.es/api/` (mismo origen que la web, sin CORS).

Base de datos SQLite en `/var/lib/edumusic-api/leaderboard.db`
(sobreescribible con `EDUMUSIC_API_DB`).

## Licencia

MIT (ver fichero LICENSE).
