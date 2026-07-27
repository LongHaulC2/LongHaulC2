---
id: LongHaul C2 - Quickstart Guide
---

# Quickstart Guide

## Quick Links

- **[GitHub Org](https://github.com/LongHaulC2):** Source code, issues, PRs
- **[Video Documentation](https://www.youtube.com/@longhaulc2)**
- **[Latest Releases](https://github.com/LongHaulC2/LongHaulC2/releases)**

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

**Credentials**: 

Credentials are randomly generated for all services. The default credentials for the `longhaul` user will be printed on screen as the deploy script completes. 

Ex:
```
==================================================
  Deployment complete.
==================================================

  Initial operator credentials:
    Username: longhaul
    Password: SOMEPASSWORDTHATIS32CHARSLONG

  Save these credentials — they will not be shown again.
  All service passwords are stored in .env
==================================================
```


**Access the UI:** `https://<server>:8083`

**API + Swagger:** `https://<server>:45045/doc`

---

## Dev Install

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

**Default credentials for DEV:** `longhaul` / `P@ssw0rd1!`


---

## What Got Installed?

See `install_reference` (created by `make deploy`) for a full list of everything that was touched on your system: apt packages, directories, systemd units, Docker containers, and the workspace path.

---

## Next Steps

- [Advanced Setup](Advanced%20Setup/LongHaul%20C2%20-%20Advanced%20Setup.md) — customize credentials, Makefile reference, port summary
- [Listeners](01%20Listeners/Overview.md) — create your first listener
- [Commands](02%20Implants/1.%20Commands.md) — full implant command reference
- [Scripting / API](03%20Scripting/Overview.md) — automate operations via the REST API
