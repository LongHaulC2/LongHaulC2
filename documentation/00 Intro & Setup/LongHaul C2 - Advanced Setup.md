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
| `sudo make deploy` | Full production install: apt deps, system user, directory structure, venv, systemd services, Docker containers, TLS certs. |
| `sudo make undeploy` | Full removal: stops services, removes systemd units, Docker containers, install dirs, workspace, logs, and system user. |
| `sudo make redeploy` | Runs `undeploy` then `deploy`. Use when upgrading. |

---

## Customizing Credentials

Pass variables directly to any `make` command to override defaults.

> **Security:** Never use the default credentials in production or on an internet-facing machine.

```bash
sudo make deploy \
  MYSQL_ROOT_PASSWORD=MySuperSecretPassword \
  REDIS_PASSWORD=AnotherSecret \
  NEO4J_PASSWORD=YetAnotherSecret \
  JWT_SECRET_KEY=MyJWTSecret \
  INIT_API_USER=operator \
  INIT_API_PASS=MyOperatorPass
```

### All Configurable Variables

| Variable | Default | Description |
|---|---|---|
| `MYSQL_ROOT_PASSWORD` | `P@ssw0rd1!` | MySQL root user password |
| `MYSQL_ROOT_USER` | `root` | MySQL root username |
| `REDIS_PASSWORD` | `P@ssw0rd1!` | Redis password |
| `REDIS_USER` | `default` | Redis username |
| `NEO4J_USER` | `neo4j` | Neo4j username |
| `NEO4J_PASSWORD` | `P@ssw0rd1!` | Neo4j password |
| `JWT_SECRET_KEY` | `P@ssw0rd1!` | Secret key for signing JWT tokens |
| `INIT_API_USER` | `longhaul` | Username for the initial operator account |
| `INIT_API_PASS` | `P@ssw0rd1!` | Password for the initial operator account |
| `MYSQL_HOST` | `localhost` | MySQL host |
| `MYSQL_PORT` | `3306` | MySQL port |
| `REDIS_HOST` | `localhost` | Redis host |
| `REDIS_PORT` | `6379` | Redis port |

---

## Docker Utilities

| Command | What it does |
|---|---|
| `make pull_docker_images` | Pulls `mysql:latest`, `redis/redis-stack:latest`, and `neo4j:latest`. |
| `make start_docker_images` | Starts `C2_mysql`, `C2_redis-stack`, and `C2_neo4j-stack` containers. |
| `make create_docker_images` | Builds the cross-compilation Docker images from `setup/docker_images/` (e.g., `win_x64`). Adds your user to the `docker` group. |

---

## Infrastructure Summary

### Service Ports

| Service | Port(s) | Notes |
|---|---|---|
| **LongHaulC2 API (Server)** | `0.0.0.0:45045` | Flask REST API |
| **LongHaulC2 UI (Client)** | `0.0.0.0:8083` | NiceGUI web interface |
| **MySQL** | `0.0.0.0:3306`, `127.0.0.1:33060` | C2 database — bind to localhost in prod |
| **Redis** | `127.0.0.1:6379` | Task queue |
| **Redis Insight (Web GUI)** | `0.0.0.0:8001` | Redis management UI — exposed globally by default, lock this down in prod |
| **Neo4j (Web UI / Browser)** | `0.0.0.0:7474` | Graph database web UI |
| **Neo4j (Bolt)** | `0.0.0.0:7687` | Neo4j driver connection |

### Docker Containers

| Container | Image | Purpose |
|---|---|---|
| `C2_mysql` | `mysql:latest` | Long-term storage (tasks, payloads, users, files) |
| `C2_redis-stack` | `redis/redis-stack:latest` | Task queue and response inbox per implant |
| `C2_neo4j-stack` | `neo4j:latest` | Graph state (implant topology, host/network relationships) |

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
