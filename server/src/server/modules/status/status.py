import docker

from ...instance import active_processes, active_threads, env_config

# getenv for docker name
MYSQL_CONTAINER = env_config.get("MYSQL_CONTAINER")
REDIS_CONTAINER = env_config.get("REDIS_CONTAINER")
NEO4J_CONTAINER = env_config.get("NEO4J_CONTAINER")

CONTAINERS = {"neo4j": NEO4J_CONTAINER, "redis": REDIS_CONTAINER, "mysql": MYSQL_CONTAINER}
CORE_SERVICE_LIST = ["mysql", "neo4j", "redis", "response_pipeline"]


def get_health_status() -> dict:
    containers = {name: get_container_status(cid) for name, cid in CONTAINERS.items()}

    # get threads
    threads = {name: ("running" if t and t.is_alive() else "stopped") for name, t in active_threads.items()}
    processes = {
        name: ("running" if p and p.is_alive() else f"stopped({p.exitcode})") for name, p in active_processes.items()
    }
    # Merge into a single flat map first for processing
    all_statuses = containers | threads | processes

    # split into categories
    health_report = {
        "core": {},
        "listeners": {},
        # "overall_status": "nominal" # nominal, degraded, or failure
    }

    for name, status in all_statuses.items():
        if name in CORE_SERVICE_LIST:
            health_report["core"][name] = status
        else:
            health_report["listeners"][name] = status

    return health_report


def get_container_status(container_name: str) -> str:
    if not container_name:
        return "misconfigured"  # Handle the empty Resource ID case

    client = docker.from_env()
    try:
        container = client.containers.get(container_name)
        # container.status returns 'running', 'exited', 'restarting', etc.
        return container.status
    except docker.errors.NotFound:
        return "not_found"
    except Exception as e:
        return f"error: {str(e)}"
