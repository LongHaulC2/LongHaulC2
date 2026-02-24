import docker

from ...instance import active_threads, env_config

# getenv for docker name
MYSQL_CONTAINER = env_config.get("MYSQL_CONTAINER")
REDIS_CONTAINER = env_config.get("REDIS_CONTAINER")
NEO4J_CONTAINER = env_config.get("NEO4J_CONTAINER")

CONTAINERS = {"neo4j": NEO4J_CONTAINER, "redis": REDIS_CONTAINER, "mysql": MYSQL_CONTAINER}


def get_health_status() -> dict[str, str]:
    """Gets the status of core items of the server.

    Returns:
        dict[str,str]: Dict containing: name, status. ex: name="neo4j", status="running"
    """

    # return status dict
    health_dict = {f"{name}_status": get_container_status(cid) for name, cid in CONTAINERS.items()}

    # add in all running threads
    thread_health: dict[str, str] = {
        f"{name}_status": ("running" if t and t.is_alive() else "stopped") for name, t in active_threads.items()
    }

    # join dicts together
    health_dict = health_dict | thread_health

    return health_dict


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
