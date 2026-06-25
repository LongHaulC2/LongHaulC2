---
id: LongHaul C2 - Quickstart Guide
slug: /
---

# Quickstart Guide

Get rolling fast. This page covers the minimal path from zero to a running server.

## Quick Links

- **[GitHub Org](https://github.com/LongHaulC2):** Source code, issues, PRs
- **[Doxygen](https://longhaulc2.github.io/doxygen):** C++ implant API docs
- **[Video Documentation](#):** *(Coming Soon)*
- **[Latest Releases](#):** *(Coming Soon)*

---

## Prerequisites

- A **Linux box** with `sudo` access
- **Docker** (installed by `make deploy` if not present)
- **Python 3** (installed by `make deploy` if not present)
- An internet connection (to pull Docker images)

---

## Production Install

```bash
git clone https://github.com/LongHaulC2/LongHaulC2
cd LongHaulC2

sudo make deploy
```

That's it. The Makefile installs all apt dependencies, sets up Docker containers (MySQL, Redis, Neo4j), builds the cross-compilation image, installs services, and starts everything.

```bash
# Verify services are running
sudo systemctl status longhaulc2-server
sudo systemctl status longhaulc2-web
```

**Default credentials:** `longhaul` / `P@ssw0rd1!`

> Change the defaults in production: `sudo make deploy INIT_API_USER=operator INIT_API_PASS=<strong_pass> MYSQL_ROOT_PASSWORD=<strong_pass> REDIS_PASSWORD=<strong_pass> NEO4J_PASSWORD=<strong_pass> JWT_SECRET_KEY=<strong_secret>`

**Access the UI:** `http://<server>:8083`

**API + Swagger:** `http://<server>:45045/doc`

---

## Development Install

For local development with live reloads:

```bash
git clone https://github.com/LongHaulC2/LongHaulC2
cd LongHaulC2

make dev_install
source venv/bin/activate

# Run the server (terminal 1)
PYTHONPATH=. python -m server.main

# Run the client (terminal 2)
PYTHONPATH=. python -m client.main
```

---

## What Got Installed?

See `install_reference` (created by `make deploy`) for a full list of everything that was touched on your system: apt packages, directories, systemd units, Docker containers, and the workspace path.

---

## Next Steps

- [Advanced Setup](00%20Intro%20%26%20Setup/LongHaul%20C2%20-%20Advanced%20Setup.md) — customize credentials, Makefile reference, port summary
- [Listeners](01%20Listeners/Overview.md) — create your first listener
- [Commands](02%20Implants/1.%20Commands.md) — full implant command reference
- [Scripting / API](03%20Scripting/Overview.md) — automate operations via the REST API
