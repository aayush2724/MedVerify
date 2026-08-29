# Deploying MedVerify Suite

Target: **a single Linux VPS running Docker Compose.** Two 
containers serve the app (nginx + gunicorn), two support it (PostgreSQL, Redis),
and one worker drains the async verification queue.

---

## 1. What you need

| | |
| :--- | :--- |
| Host | Linux VPS, **4 GB RAM minimum**, 2+ vCPU, 20 GB disk |
| Software | Docker Engine 24+ with the Compose plugin |
| Ports | 80 (and 443 if you terminate TLS here) |
| Network | Outbound HTTPS to `rxnav.nlm.nih.gov` and `api.fda.gov` |

**On memory:** each gunicorn worker loads spaCy, scikit-learn and OpenCV into
its own address space — roughly 300–400 MB apiece. At the default
`WEB_CONCURRENCY=3` plus the Celery worker and PostgreSQL, expect ~2.5 GB
resident. A 2 GB box will OOM under load.

**On outbound access:** Module 2 fetches drug data from RxNorm and openFDA live
on first use, then caches it in PostgreSQL. If the host cannot reach them, the
app still runs — findings degrade to explicit "could not be checked" coverage
notes rather than silently disappearing — but the medication features are close
to useless. Check egress before blaming the app.

---

## 2. Deploy

```bash
git clone <your-repo> medverify && cd medverify

cp .env.production.example .env
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(48))"
python3 -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(48))"
python3 -c "import secrets; print('POSTGRES_PASSWORD=' + secrets.token_urlsafe(24))"
# paste those three into .env, then:

docker compose -f docker-compose.prod.yml up -d --build
```

The first build takes 5–10 minutes; it compiles the ML dependencies and
downloads the spaCy model.

Compose refuses to start if `SECRET_KEY`, `JWT_SECRET_KEY` or
`POSTGRES_PASSWORD` are unset. That is deliberate — the failure is loud rather
than a stack quietly running on a default secret.

### Verify

```bash
curl localhost/api/health          # {"status":"ok"}
curl localhost/api/health/ready    # {"status":"ready","checks":{"database":"ok","redis":"ok"}}
docker compose -f docker-compose.prod.yml ps    # all services healthy
```

`/api/health` is liveness — it touches nothing, so a database blip cannot get a
healthy container killed. `/api/health/ready` is readiness and returns **503**
when PostgreSQL or Redis is unreachable, so a load balancer stops sending
traffic without restarting the app. Point your orchestrator at the right one.

### First account

There is no account until you make one. Either register through the UI, or set
`MEDVERIFY_SEED_ADMIN_PASSWORD` in `.env` and restart `backend` — it creates
`admin@medverify.dev` on boot. **Unset it again afterwards.**

---

## 3. HTTPS

Two options.

**A — let Caddy do it** (easiest; automatic Let's Encrypt certificates):

```bash
# in .env
DOMAIN=medverify.example.com
ACME_EMAIL=ops@example.com
HTTP_PORT=8080          # free port 80 for Caddy's ACME challenge

docker compose -f docker-compose.prod.yml --profile tls up -d
```

Point the domain's A record at the host first — certificate issuance fails
without working DNS.

**B — terminate TLS at an existing proxy.** Leave the `tls` profile off and
point your proxy at `HTTP_PORT`. Forward `X-Forwarded-Proto`; the app reads it
for correct scheme detection behind a proxy.

---

## 4. How the pieces fit

```
                    ┌─────────────────────────────────────────┐
  browser ──:80──▶  │ frontend (nginx)                        │
                    │  /            → built React SPA         │
                    │  /api/*       → proxy to backend:5000   │
                    └──────────────────┬──────────────────────┘
                                       │  (internal network only)
              ┌────────────────────────┼────────────────────────┐
              ▼                        ▼                        ▼
     ┌─────────────────┐      ┌────────────────┐      ┌────────────────┐
     │ backend         │      │ worker         │      │ db / redis     │
     │ gunicorn        │      │ celery         │      │ not published  │
     │ runs migrations │      │ shares uploads │      │                │
     └─────────────────┘      └────────────────┘      └────────────────┘
```

**One origin.** nginx serves the SPA *and* proxies `/api`, so the browser never
makes a cross-origin request and CORS is not involved at all. This is also why
`VITE_API_URL` is built empty — the client falls back to
`window.location.origin`. Do not set it unless you split the frontend and API
onto different hosts.

**PostgreSQL and Redis publish no ports.** They are reachable only on the Docker
network. Do not add a `ports:` entry to reach them from your laptop — use
`docker compose exec db psql …` instead.

**Migrations run from the backend's entrypoint**, not from the app. The worker
starts with `MIGRATE_ON_START=false` so the two containers do not race the same
Alembic lock. `create_all()` is disabled in production (`AUTO_CREATE_TABLES`),
so Alembic is the single owner of the schema.

---

## 5. Persistence

Three named volumes hold everything that must survive a redeploy:

| Volume | Holds | Losing it means |
| :--- | :--- | :--- |
| `pg_data` | The entire database | Total data loss |
| `uploads` | Uploaded certificates and prescriptions | Records survive but documents 404 |
| `redis_data` | Celery queue, JWT blocklist | In-flight jobs lost; revoked tokens valid again until expiry |

`docker compose down` keeps them. **`docker compose down -v` destroys them.**

`uploads` is mounted into *both* the backend and worker: a Celery task receives
a file *path*, so the worker must see the same files the web container wrote.

### Backups

```bash
# Database
docker compose -f docker-compose.prod.yml exec -T db \
  pg_dump -U medverify medverify | gzip > backup-$(date +%F).sql.gz

# Uploaded documents
docker run --rm -v medverify_uploads:/data -v "$PWD":/backup alpine \
  tar czf /backup/uploads-$(date +%F).tar.gz -C /data .
```

Restore the database into a *fresh* volume; restoring over a live one leaves
Alembic's version table disagreeing with the schema.

---

## 6. Operations

```bash
# Logs
docker compose -f docker-compose.prod.yml logs -f backend

# Update
git pull && docker compose -f docker-compose.prod.yml up -d --build

# Migrations only
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
docker compose -f docker-compose.prod.yml exec backend alembic current
```

### Tuning

| Variable | Default | Raise it when |
| :--- | :--- | :--- |
| `WEB_CONCURRENCY` | 3 | Requests queue and you have RAM (~0.5 GB/worker) |
| `WORKER_CONCURRENCY` | 2 | Async verifications back up |
| `GUNICORN_TIMEOUT` | 180 | Large PDFs time out mid-OCR |

Rate limits are stored in Redis in production, not in process memory, so a limit
means the same thing across every worker.

### Rotating the database password

Changing `POSTGRES_PASSWORD` in `.env` does **not** change the password already
stored in the volume — the variable only applies on first initialisation. To
rotate it, change it inside PostgreSQL and then in `.env`:

```bash
docker compose -f docker-compose.prod.yml exec db \
  psql -U medverify -c "ALTER USER medverify WITH PASSWORD 'new-password';"
# update POSTGRES_PASSWORD in .env, then:
docker compose -f docker-compose.prod.yml up -d
```

---

## 7. Troubleshooting

**`ModuleNotFoundError: No module named 'shared'`** — the backend image was
built with `backend/` as its context. It must be built from the repository root
(`docker build -f backend/Dockerfile .`), because `app/errors.py` imports the
root-level `shared/` package. Both compose files already do this.

**`ImportError: libGL.so.1`** — `libgl1` is missing. `requirements.txt` asks for
`opencv-python-headless`, but `rapidocr-onnxruntime` depends on the full
`opencv-python`, and that build wins the `cv2` import. The Dockerfile installs
it; a custom image must too.

**The frontend calls `localhost:5000` in production** — a stale `frontend/.env`
got into the build context. Vite inlines `VITE_*` at build time. `.dockerignore`
excludes it; confirm it is being honoured, then rebuild with `--no-cache`.

**Backend restarts in a loop** — almost always the database. Check
`docker compose logs backend`; the entrypoint waits up to `DB_WAIT_SECONDS`
(default 60) and then exits rather than serving against a database that is not
there.

**Medication findings are all "could not be checked"** — the host cannot reach
RxNorm or openFDA. Verify with:

```bash
docker compose -f docker-compose.prod.yml exec backend \
  python -c "import requests; print(requests.get('https://rxnav.nlm.nih.gov/REST/version.json', timeout=8).status_code)"
```

**Uploads 404 after a redeploy** — the `uploads` volume was removed, or a
compose override dropped the mount. Verification records survive independently
of their files, so the rows will still be listed.

---

## 8. Before going live

- [ ] `SECRET_KEY` and `JWT_SECRET_KEY` are freshly generated and unique
- [ ] `MEDVERIFY_SEED_*` passwords are unset after the first account exists
- [ ] TLS terminates somewhere — Caddy profile or an upstream proxy
- [ ] `docker compose ps` shows every service `healthy`
- [ ] A database backup has been taken **and restored once** as a test
- [ ] `/api/health/ready` is wired to your monitoring
- [ ] Outbound access to RxNorm and openFDA confirmed from the host
- [ ] PostgreSQL and Redis publish no ports (`docker compose ps` shows none)
