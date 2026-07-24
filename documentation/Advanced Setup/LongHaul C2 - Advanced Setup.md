# Advanced Setup & Makefile Reference

If you want more control over your LongHaul C2 deployment or just want to know exactly what's happening under the hood, this page is for you.

A `Makefile` handles the heavy lifting for both development and production deployments.

---

## Development vs Production

There are two distinct installation paths:

| Mode | Command | Description |
|---|---|---|
| **Development** | `make dev_install` | Local venv, Docker containers, live reloads. Run directly with Python. |
| **Production** | `sudo make deploy` | Installs as systemd services under a restricted `longhaul` user. |

---

## Development Setup

```bash
git clone https://github.com/LongHaulC2/LongHaulC2
cd LongHaulC2

# Install dependencies, create venv, spin up Docker containers, create .env
make dev_install

# Activate the venv
source venv/bin/activate

# Run the server
PYTHONPATH=. python -m server.main

# Run the client (separate terminal)
PYTHONPATH=. python -m client.main
```

### Development Makefile Commands

| Command | What it does |
|---|---|
| `make dev_install` | Installs apt deps, creates venv, installs Python deps, creates `.env`, creates workspace dirs at `/var/lib/longhaulc2`, pulls and starts Docker containers. |
| `make dev_uninstall` | Stops and removes Docker containers, removes venv and `.env`, wipes workspace and log dirs. |
| `make dev_reinstall` | Runs `dev_uninstall` then `dev_install` — clean slate for dev. |

---

## Production Deployment

```bash
sudo make deploy
```

This installs everything to `/opt/longhaulc2` and runs both services under the `longhaul` system user.

```bash
# Check service status after deploy
sudo systemctl status longhaulc2-server
sudo systemctl status longhaulc2-web
```

### Production Makefile Commands

| Command | What it does |
|---|---|
| `sudo make deploy` | Full production install: apt deps, system user, directory structure, venv, systemd services, Docker Compose services, TLS certs. |
| `sudo make undeploy` | Full removal: stops services, removes systemd units, Docker containers and volumes, install dirs, workspace, logs, and system user. |
| `sudo make undeploy KEEP_DATA=1` | Same as above but **preserves Docker volumes and `/var/lib/longhaulc2`**. Use before an upgrade to retain database state. |
| `sudo make redeploy` | Runs `undeploy KEEP_DATA=1` then `deploy`. The standard upgrade path — tears down and reinstalls code/services while preserving all database and workspace data. |

---

## Credentials

### Production (`make deploy`)

`make deploy` **automatically generates random 32-character passwords** for every service: MySQL, Redis, Neo4j, the JWT signing key, and the initial operator account. No manual credential setup is needed.

At the end of a successful deploy, the operator username and password are printed to the screen:

```
==================================================
  Deployment complete.
==================================================

  Initial operator credentials:
    Username: longhaul
    Password: <randomly generated>

  Save these credentials — they will not be shown again.
  All service passwords are stored in .env
==================================================
```

All generated passwords are stored in `.env`. Back this file up — it is the only record of the service credentials.

On a `make redeploy` (or `make undeploy KEEP_DATA=1` followed by `make deploy`), the existing `.env` is preserved so credentials stay in sync with the database volumes.

### Development (`make dev_install`)

Development installs use the hardcoded defaults below for convenience. These are not suitable for production.

### Overriding Defaults

Pass variables directly to `make dev_install` (or `make create_env`) to override individual defaults:

```bash
make dev_install \
  MYSQL_ROOT_PASSWORD=MySuperSecretPassword \
  REDIS_PASSWORD=AnotherSecret \
  NEO4J_PASSWORD=YetAnotherSecret
```

### All Configurable Variables

| Variable | Dev Default | Production | Description |
|---|---|---|---|
| `MYSQL_ROOT_PASSWORD` | `P@ssw0rd1!` | Auto-generated | MySQL root user password |
| `MYSQL_ROOT_USER` | `root` | `root` | MySQL root username |
| `REDIS_PASSWORD` | `P@ssw0rd1!` | Auto-generated | Redis password |
| `REDIS_USER` | `default` | `default` | Redis username |
| `NEO4J_USER` | `neo4j` | `neo4j` | Neo4j username |
| `NEO4J_PASSWORD` | `P@ssw0rd1!` | Auto-generated | Neo4j password |
| `JWT_SECRET_KEY` | `P@ssw0rd1!` | Auto-generated | Secret key for signing JWT tokens |
| `INIT_API_USER` | `longhaul` | `longhaul` | Username for the initial operator account |
| `INIT_API_PASS` | `P@ssw0rd1!` | Auto-generated | Password for the initial operator account |
| `MYSQL_HOST` | `localhost` | `localhost` | MySQL host |
| `MYSQL_PORT` | `3306` | `3306` | MySQL port |
| `REDIS_HOST` | `localhost` | `localhost` | Redis host |
| `REDIS_PORT` | `6379` | `6379` | Redis port |

---

## Docker Compose

Database services (MySQL, Redis, Neo4j) are managed via `docker-compose.yml` in the project root. The compose file reads credentials and container names directly from `.env`.

### Key properties

- **Auto-restart:** All services use `restart: unless-stopped` — containers come back automatically after a system reboot (as long as the Docker daemon is enabled).
- **Localhost-only networking:** Every port is bound to `127.0.0.1`. No database port is exposed on `0.0.0.0`.
- **Named volumes:** Data is persisted in Docker named volumes (`mysql_data`, `redis_data`, `neo4j_data`), which survive container recreation. Use `KEEP_DATA=1` on undeploy to preserve them across upgrades.

### Docker Makefile Commands

| Command | What it does |
|---|---|
| `make start_docker_images` | Starts all database services via `docker compose up -d`. Pulls images automatically if not present locally. |
| `make stop_docker_images` | Stops all database services via `docker compose down`. Containers are removed but named volumes are kept. |
| `make pull_docker_images` | Pulls latest images for all services via `docker compose pull`. |
| `make create_docker_images` | Builds the cross-compilation Docker images from `setup/docker_images/` (e.g., `win_x64`). This is separate from the database services. |

---

## Infrastructure Summary

### Service Ports

All database ports are bound to `127.0.0.1` only (not externally accessible).

| Service | Port(s) | Notes |
|---|---|---|
| **LongHaulC2 API (Server)** | `0.0.0.0:45045` | Flask REST API |
| **LongHaulC2 UI (Client)** | `0.0.0.0:8083` | NiceGUI web interface |
| **MySQL** | `127.0.0.1:3306`, `127.0.0.1:33060` | C2 database |
| **Redis** | `127.0.0.1:6379` | Task queue |
| **Redis Insight (Web GUI)** | `127.0.0.1:8001` | Redis management UI |
| **Neo4j (Web UI / Browser)** | `127.0.0.1:7474` | Graph database web UI |
| **Neo4j (Bolt)** | `127.0.0.1:7687` | Neo4j driver connection |

### Docker Containers

| Container | Image | Volume | Purpose |
|---|---|---|---|
| `C2_mysql` | `mysql:latest` | `mysql_data` | Long-term storage (tasks, payloads, users, files) |
| `C2_redis-stack` | `redis/redis-stack:latest` | `redis_data` | Task queue and response inbox per implant |
| `C2_neo4j-stack` | `neo4j:latest` | `neo4j_data` | Graph state (implant topology, host/network relationships) |

### Filesystem Layout (Production)

| Path | Purpose |
|---|---|
| `/opt/longhaulc2/server/` | Server application code + venv |
| `/opt/longhaulc2/client/` | Client application code + venv |
| `/var/lib/longhaulc2/` | Workspace: implant templates, user scripts |
| `/var/lib/longhaulc2/implant_templates/` | C++ implant source used by the build system |
| `/var/log/longhaulc2/` | Application logs |
| `/etc/ssl/certs/longhaulc2_api_cert.pem` | TLS certificate (auto-generated on deploy) |

---

## TLS Certificates

`make deploy` automatically generates a self-signed TLS certificate (4096-bit RSA, 365-day validity) and places it in `/etc/ssl/certs/`. The server uses this for HTTPS.

To regenerate:
```bash
sudo make clean-certs
sudo make certs
```

---

## Linting & Pre-Push Checklist

```bash
# Lint & format (runs ruff check + ruff format via pre-commit)
pre-commit run --all-files

# Full pre-push prep: lint, freeze deps, clean .pyc files, dry-run install
make prep_for_push
```

---

## Testing

| Target | Requires | Description |
|---|---|---|
| `make web_tests` | Nothing | UI smoke tests — pages render, auth guards fire |
| `make server_tests` | Server + Docker containers | API tests — all endpoints, CRUD, auth |
| `make local_tests` | Server + Docker containers | Both of the above |
| `make integration_test` | Full stack + live Windows implant | Full E2E with real implant (CI only) |
| `make no_fail_test` | Full stack | Integration tests, exits 0 on failure |

For full prerequisites, per-test-file coverage, and common failure causes, see [Testing Overview](../05%20Testing/Overview.md).
