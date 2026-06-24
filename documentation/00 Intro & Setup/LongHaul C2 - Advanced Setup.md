# Advanced Setup & Makefile Reference

If you want more control over your LongHaul C2 deployment or just want to know exactly what's happening under the hood, this page is for you. 

We use a `Makefile` to automate the heavy lifting. By default, it sets up everything you need for a local development environment, but it is highly customizable.

---

## Customizing the Installation

You can override the default credentials and paths by passing variables directly to the `make` command. 

**Security Note:** *Never use the default passwords in a production or internet-facing environment.*

**Example:**
```bash
make install MYSQL_ROOT_PASSWORD=MySuperSecretPassword123 REDIS_PASSWORD=AnotherSecret456

```

### Available Variables

| Variable | Default Value | Description |
| --- | --- | --- |
| `MYSQL_ROOT_PASSWORD` | `P@ssw0rd1!` | Password for the MySQL root user. |
| `MYSQL_ROOT_USER` | `root` | Username for the MySQL database. |
| `REDIS_PASSWORD` | `P@ssw0rd1!` | Password for the Redis database. |
| `REDIS_USER` | `default` | Username for Redis. |
| `VENV_PATH` | `./venv` | Path where the Python virtual environment will be created. |
| `DOCKER_DIR` | `setup/docker_images` | Directory containing custom Dockerfiles for cross-compilation. |

---

## Available `make` Commands

Here is exactly what each command does to your system.

### `make install`

The main setup routine. When you run this, the script performs the following actions:

1. **Installs System Dependencies:** Runs `apt-get` to install `Python3`, `pip`, `virtualenv`, `docker.io`, `redis-tools`, and `postgresql-client`.
2. **Deploys Infrastructure:** Pulls the latest MySQL and Redis-Stack Docker images and spins them up in detached containers (`C2_mysql` and `C2_redis-stack`).
3. **Builds Compilers:** Calls `create_docker_images` to build the isolated Docker containers used for cross-compiling your payloads.
4. **Sets up Python:** Creates a virtual environment at `VENV_PATH` and installs both the server and client requirements.
5. **Configures the Environment:** Generates a `.env` file in your root directory populated with the database credentials you specified (or the defaults).

### `make uninstall`

The nuclear option. Use this to completely wipe your LongHaul C2 local environment.

* Stops and removes the `C2_mysql` and `C2_redis-stack` Docker containers.
* Deletes the local MySQL and Redis Docker images.
* Deletes the Python `venv` folder.
* Deletes the `.env` file containing your configurations.

### `make reset`

Simply runs `make uninstall` followed immediately by `make install`. If you want a quick fresh start, this is it. I use it constantly while doing dev work. 

### `make create_docker_images`

*(Automatically run during `make install`)*
This target ensures your user is added to the `docker` group (preventing annoying permission issues). It then iterates through the `setup/docker_images` directory, building a fresh Docker image for every builder environment found.

---

## Ports & Infrastructure Summary

If you are running firewalls or deploying on a remote VPS, be aware of the following ports opened by the default installation:

* **MySQL:** `127.0.0.1:3306` (and `33060`)
* **Redis:** `127.0.0.1:6379`
* **Redis Insights (Web GUI):** `0.0.0.0:8001` *(Note: Exposed globally by default for dev convenience. You should lock this down in prod).*