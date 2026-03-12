import base64
import hashlib
import ipaddress

import structlog
from neomodel import db

from ...db.mysql_connector import get_mysql_session
from ...db.mysql_functions import MySQLImplantTaskService
from ...db.neo4j_functions import (
    Neo4jChainingService,
    Neo4jFileNodeService,
    Neo4jHostNodeService,
    Neo4jImplantNodeService,
    Neo4jMemstoreFileNodeService,
    Neo4jNicNodeService,
)

response_pipeline_logger = structlog.getLogger("response_pipeline")
server_logger = structlog.getLogger("server")


def _handle_discover_neighbors(task_request_dict: dict, task_response_dict: dict, implant_uuid: str):  # noqa
    discover_neighbors_logger = response_pipeline_logger.bind(task="discover neighbors", implant_uuid=implant_uuid)

    try:
        neighbor_list = task_response_dict.get("result", {}).get("data", [])
        if not neighbor_list:
            return

        # Fetch all networks the scanning implant is currently connected to
        query = """
        MATCH (i:Neo4jImplantNode {implant_uuid: $implant_uuid})-[:RUNNING_ON]->(h:Neo4jHostNode)
        MATCH (h)<-[:ATTACHED_TO]-(n:Neo4jNicNode)-[:IN_NETWORK]->(net:Neo4jNetworkNode)
        RETURN net.cidr AS cidr, net.network_uuid AS net_uuid
        """
        results, _ = db.cypher_query(query, {"implant_uuid": implant_uuid})

        if not results:
            discover_neighbors_logger.error("Implant has no known network context. Neighbors cannot be mapped.")
            return

        # Convert results into a list of (IPv4Network, network_uuid) tuples for fast checking
        available_networks = []
        for cidr, net_uuid in results:
            try:
                available_networks.append((ipaddress.ip_network(cidr, strict=False), net_uuid))
            except ValueError:
                continue

        # Process each neighbor
        for neighbor in neighbor_list:
            neighbor_ip_str = neighbor.get("ip")
            neighbor_mac = neighbor.get("mac")
            neighbor_host = neighbor.get("hostname", f"UNK-{neighbor_ip_str}")

            if not neighbor_ip_str:
                continue

            # find the matching network for each NIC
            target_net_uuid = None
            target_cidr_str = None

            try:
                # resolove NIC to the net node, i.e. if the implant has multiple nics
                # make sure we use the right network node when attaching neighbors
                # tldr: make sure 192.168.0.2 doesn't go to 10.0.0.1/24
                neighbor_ip_obj = ipaddress.ip_address(neighbor_ip_str)
                for network_obj, net_uuid in available_networks:
                    if neighbor_ip_obj in network_obj:
                        target_net_uuid = net_uuid
                        target_cidr_str = str(network_obj)
                        break
            except ValueError:
                discover_neighbors_logger.debug("Invalid neighbor IP address format", ip=neighbor_ip_str)
                continue

            if not target_net_uuid:
                discover_neighbors_logger.debug(
                    "Neighbor not in any known implant subnets, skipping", ip=neighbor_ip_str
                )
                continue

            # plot it

            # Create/Get the neighbor Host
            host_node = Neo4jHostNodeService.create_or_get_node(
                hostname=neighbor_host, ip_address=neighbor_ip_str, mac_address=neighbor_mac
            )

            # Create/Get the neighbor NIC
            nic_node = Neo4jNicNodeService.create_or_get_node(mac_address=neighbor_mac, ip_address=neighbor_ip_str)

            # Update NIC with the CIDR we matched
            nic_node.cidr = target_cidr_str
            nic_node.save()

            # connect our new nic, to our new host in the graph
            Neo4jNicNodeService.connect_nic_to_host(
                host_uuid=host_node.host_uuid, mac_address=neighbor_mac, ip_address=neighbor_ip_str
            )

            # Connect NIC to the specific Network segment matched via UUID
            Neo4jNicNodeService.connect_nic_to_network_by_uuid(network_uuid=target_net_uuid, nic_uuid=nic_node.nic_uuid)

        discover_neighbors_logger.info("Successfully plotted discovery results across subnets")

    except Exception as e:
        discover_neighbors_logger.error("An error occurred during discovery processing", error=str(e))


def _handle_memstore_upload(task_request_dict: dict, task_response_dict: dict, implant_uuid: str):  # noqa
    # try a local logger and bind to it for this scope
    memstore_upload_logger = response_pipeline_logger.bind(task="memstore upload")
    try:
        file_name = task_request_dict.get("task", {}).get("args", {}).get("file_name", "")
        if not file_name:
            memstore_upload_logger.info("file_name is empty", file_name=file_name)
            return

        file_contents = (
            task_request_dict.get("task", {}).get("args", {}).get("file_contents", "")  # store as bytes in db
        )
        if not file_contents:
            memstore_upload_logger.info("file_contents are empty", file_contents=file_contents)
            return

        decoded_bytes = base64.b64decode(file_contents)
        hash = hashlib.md5(decoded_bytes).hexdigest()

        Neo4jMemstoreFileNodeService.connect_memstore_file_to_implant(
            file_name=file_name, implant_uuid=implant_uuid, file_hash_md5=hash
        )
        # add addtl metadata
        file_node = Neo4jMemstoreFileNodeService.create_or_get_node(file_name)

        # only get first 20 chars
        try:
            # add 0x for preivew/user knows it's hex
            file_node.file_preview = "0x" + decoded_bytes.hex()[:20]
        except Exception as e:
            memstore_upload_logger.error("Error saving file_preview", error=e)

        try:
            # add 0x for preivew/user knows it's hex
            file_node.file_size_kb = len(decoded_bytes) / 1000  # convert to kb
        except Exception as e:
            memstore_upload_logger.error("Error saving file_size_kb", error=e)

        file_node.save()
    except Exception as e:
        memstore_upload_logger.error("An error occurred", error=e)


def _handle_memstore_clear(task_request_dict: dict, task_response_dict: dict, implant_uuid: str):  # noqa
    # remove all file from host
    memstore_clear_logger = response_pipeline_logger.bind(task="memstore clear")
    try:
        # get all files connected to implant
        connected_file_nodes = Neo4jMemstoreFileNodeService.get_all_files_nodes_for_implant(implant_uuid=implant_uuid)
        for node in connected_file_nodes:
            node.delete()

    except Exception as e:
        memstore_clear_logger.error("An error occurred", error=e)


def _handle_memstore_delete(task_request_dict: dict, task_response_dict: dict, implant_uuid: str):  # noqa
    # remove a memstore file from host
    memstore_delete_logger = response_pipeline_logger.bind(task="memstore delete")

    try:
        file_name = task_request_dict.get("task", {}).get("args", {}).get("file_name", "")

        # the one file connected to the implant
        # note - this might create it if it doesn't exist for some reason, just for it to be deleted.
        file_node = Neo4jMemstoreFileNodeService.create_or_get_node(file_name=file_name)
        # and delete it
        if file_node:
            file_node.delete()

    except Exception as e:
        memstore_delete_logger.error("An error occured", error=e)


def _handle_file_upload(task_request_dict: dict, task_response_dict: dict, implant_uuid: str):  # noqa
    # get file name, contents, path
    # add node
    file_upload_logger = response_pipeline_logger.bind(task="file upload")

    try:
        file_path = task_request_dict.get("task", {}).get("args", {}).get("file_path", "")

        file_contents = (
            task_request_dict.get("task", {}).get("args", {}).get("file_contents", "")  # store as bytes in db
        )

        host_node = Neo4jImplantNodeService.get_host_implant_is_connected_to(implant_uuid)

        if not host_node:
            response_pipeline_logger.error("Could not find host that implant is connected to")
            return

        hostname = host_node.hostname

        decoded_bytes = base64.b64decode(file_contents)
        hash = hashlib.md5(decoded_bytes).hexdigest()

        Neo4jFileNodeService.connect_file_to_host(file_path=file_path, hostname=hostname, file_hash_md5=hash)

        # addtl metadata
        file_node = Neo4jFileNodeService.create_or_get_node(file_path)

        try:
            # add 0x for preivew/user knows it's hex
            file_node.file_preview = "0x" + decoded_bytes.hex()[:20]
        except Exception as e:
            response_pipeline_logger.error("Error saving file_preview", error=e)

        try:
            # add 0x for preivew/user knows it's hex
            file_node.file_size_kb = len(decoded_bytes) / 1000  # convert to kb
        except Exception as e:
            response_pipeline_logger.error("Error saving file_size_kb", error=e)

        file_node.save()
    except Exception as e:
        file_upload_logger.error("An error occured", error=e)

    # # I don't have a file delete, damn.
    # case "file delete":
    #     file_name = task_request_dict.get("task", {}).get("args", {}).get("file_name", "")

    #     # the one file connected to the implant
    #     # note - this might create it if it doesn't exist for some reason, just for it to be deleted.
    #     file_node = Neo4jFileNodeService.create_or_get_node(file_name=file_name)
    #     # and delete it
    #     if file_node:
    #         file_node.delete()

    # could do a file clear, that attempts to nuke all files, which would use the get_all_files_nodes_for_host


def _handle_link(task_request_dict: dict, task_response_dict: dict, implant_uuid: str):  # noqa
    """
    Link actions.

    If our link is successful,
    - create or get child node by child_uuid
    - add relationship of CHILD_OF (to parent)

    - create or get parent node by implant_uuid
    - add relationship of PARENT_TO (child)

    This should be enough for querying parent/child rel's
    """
    link_logger = response_pipeline_logger.bind(task="link")
    try:
        child_uuid = task_response_dict.get("result", {}).get("data", {}).get("child_uuid", "")
        # parent_uuid = task_request_dict.get("task", {}).get("args", {}).get("implant_uuid", "")
        parent_uuid = implant_uuid

        if not child_uuid:
            link_logger.error("Child uuid empty")
            return

        if not parent_uuid:
            link_logger.error("Parent uuid empty")
            return

        # create parent -> child,
        Neo4jChainingService.link_child_to_parent_node(child_uuid=child_uuid, parent_uuid=parent_uuid)
    except Exception as e:
        link_logger.error("An error occured", error=e)


TASK_HANDLERS = {
    "discover neighbors": _handle_discover_neighbors,
    "memstore upload": _handle_memstore_upload,
    "memstore clear": _handle_memstore_clear,
    "memstore delete": _handle_memstore_delete,
    "file upload": _handle_file_upload,
    "link": _handle_link,
}


def correlate_task_results(task_response_dict: dict):
    # response_pipeline_logger.critical("IT IS WORKING")
    task_uuid = task_response_dict.get("task_uuid", "")
    implant_uuid = task_response_dict.get("implant_uuid")

    if not task_uuid:
        response_pipeline_logger.warning("Task response did not have a task_uuid")
        return

    if not implant_uuid:
        response_pipeline_logger.warning("Task response did not have a implant_uuid")
        return

    # get full task from DB
    task_request_dict = {}
    with get_mysql_session() as session:
        task = MySQLImplantTaskService(implant_uuid=implant_uuid, session=session)
        # fyi - this returns the full task: task_request, task_response, implant_uuid, task_uuid.
        # Need to pull out task request
        task_dict = task.get_task_by_uuid(task_uuid)

    if not task_dict:
        response_pipeline_logger.warning("Task lookup did not yield any data")
        return

    # filter down to task_request
    task_request_dict = task_dict.get("task_request", {})
    task_name = task_request_dict.get("task", {}).get("task_name", "")

    # check if task was successful. If not, return.
    windows_error_code = task_response_dict.get("result", {}).get("windows_error_code", "")
    if windows_error_code != 0:
        response_pipeline_logger.warning(
            "Task Result was not successful. Not updating Neo4j",
            windows_error_code=windows_error_code,
        )
        return

    # based off task name, do neo4j actions
    handler_func = TASK_HANDLERS.get(task_name)

    if handler_func:
        handler_func(task_request_dict, task_response_dict, implant_uuid)
    else:
        # Logging for when a new task type is processed but doesn't have a Neo4j routine
        response_pipeline_logger.debug("No specific Neo4j handler for this task", task_name=task_name)
