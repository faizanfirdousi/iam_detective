## Local Postgres (Docker)

1. Copy `.env.example` to `.env` and adjust values if needed.
2. Start Postgres + backend:

   ```bash
   docker compose up --build
   ```

3. Backend runs at `http://localhost:8080` and auto-creates tables on startup.

If you only want Postgres (and run the backend locally with `uvicorn`), start just the DB:

```bash
docker compose up db
```

Then set:

```bash
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/iam_detective
DB_SSL=disable
```

The backend auto-selects the Postgres driver:

- Python < 3.14: uses `postgresql+asyncpg`
- Python >= 3.14: uses `postgresql+psycopg`

## DigitalOcean Managed Postgres

DigitalOcean Managed Databases supports Postgres and works fine with this backend.

1. Create a Managed Database (PostgreSQL) in DigitalOcean.
2. In the database’s “Connection Details”, copy the connection string.
3. Set the backend environment variable `DATABASE_URL` to that value.
4. Ensure SSL is required:
   - Prefer including `sslmode=require` in the `DATABASE_URL`, or
   - Set `DB_SSL=require`

The backend auto-creates tables on startup. For production, prefer running only one instance during the first boot to avoid concurrent table-creation races.
