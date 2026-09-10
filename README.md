# EduMúsic Leaderboard API

API REST mínima (FastAPI + SQLite) per al rànquing compartit d'EduMúsic.
Substitueix Firebase Firestore (projecte `edumusic-f67e0`), que era el backend
del rànquing fins a 2026-09.

Usa `edutictac-community` com a nucli comú per a connexió SQLite amb WAL i rate
limit en memòria. La lògica de rànquing setmanal i global continua sent local
d'EduMúsic.

## Endpoints

- `GET /api/health` → `{"status": "ok"}`
- `GET /api/scores?game_id=<id>&period=all-time|weekly&limit=<n>` → top N per puntuació (desc) i antiguitat (asc).
- `POST /api/scores` amb `{"game_id": "...", "name": "ABC", "score": 123}` → crea l'entrada.

`name` es normalitza a 3 inicials (A-Z0-9); `score` entre 0 i 9999. La setmana
setmanal (`week_key`) es calcula en dilluns 00:01 UTC, igual que el client.

## Execució local

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8003
```

## Nucli comú

Dependència estable actual:

```txt
edutictac-community @ git+https://git.edutictac.es/Edutictac/edutictac-community.git@v0.1.1
```

Components reutilitzats:

- `edutictac_community.db.connect` per a SQLite amb WAL.
- `edutictac_community.ratelimit.RateLimiter` per a límits en memòria.

Tests:

```bash
pytest -q
```

## Desplegament

Codi en `/opt/edumusic-api`, servei systemd `edumusic-api.service`
(uvicorn en `127.0.0.1:8003`), exposat per nginx en
`edumusic.edutictac.es/api/` (mateix origen que la web, sense CORS).

Base de dades SQLite en `/var/lib/edumusic-api/leaderboard.db`
(sobreescrivible amb `EDUMUSIC_API_DB`).

## Resumen en castellano

API mínima de ranking para EduMúsic. Usa `edutictac-community` para SQLite con
WAL y rate limit, mantiene la lógica de ranking en este servicio y se despliega
como servicio systemd tras nginx en `edumusic.edutictac.es/api/`.

## Llicència

MIT (vegeu el fitxer LICENSE).
