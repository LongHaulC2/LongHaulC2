# neo4j functions

import structlog
from edwh_uuid7 import uuid7
from neomodel import db

from ..schemas.listeners import ListenerCreate, ListenerUpdate
from ..utils.checks import check_type
from .neo4j_models import (
    Neo4jC2ChannelNode,
    Neo4jFileNode,
    Neo4jHostNode,
    Neo4jImplantNode,
    Neo4jListenerNode,
    Neo4jMemstoreFileNode,
    Neo4jNetworkNode,
    Neo4jNicNode,
)

neo4j_logger = structlog.getLogger("internal_neo4j")
server_logger = structlog.getLogger("server")

"""
each service class should have a:

@staticmethod
def create_or_get_node(args) -> object that returns model object:

> I try to use `create_or_get_node` when possible, that way, if there isn't a node, and something comes in and wants
that node, it gets created in the DB. It's a bit backwards than making sure that node exists,
but every bit of data that can be pulled out of these implants is important, hence this decision.
"""


class Neo4jCoreService:
    """
    Core/AllGraph operations
    """

    @staticmethod
    def search_everything(search_term: str, inlcude_rels: bool = False) -> list[dict]:
        """
        Global Lucene search across all mapped entities in Neo4j.
        """
        log = neo4j_logger.bind(method="search_everything", search_term=search_term, include_rels=inlcude_rels)
        log.debug("Executing global search")

        # Pro-tip: Only add '*' if the user hasn't provided their own wildcards
        # This allows complex Lucene like: hostname:ws* AND user:admin
        formatted_term = search_term if "*" in search_term or ":" in search_term else f"{search_term}*"

        if inlcude_rels:
            query = """
                CALL db.index.fulltext.queryNodes("global_search_index", $term)
                YIELD node
                MATCH (node)-[r]-(neighbor)
                RETURN node, r, neighbor
                """
        else:
            query = """
            CALL db.index.fulltext.queryNodes("global_search_index", $term)
            YIELD node, score
            RETURN
                properties(node) AS props,
                labels(node)[0] AS category,
                score
            ORDER BY score DESC
            """

        log.debug("Running Cypher query for global search")
        results, _ = db.cypher_query(query, {"term": formatted_term})

        # Combine props and category into a single dict for the frontend
        formatted_results = []
        for props, category, score in results:
            combined = props.copy()
            combined["category"] = category
            combined["search_score"] = score
            formatted_results.append(combined)

        log.debug("Global search complete", result_count=len(formatted_results))
        return formatted_results

    @staticmethod
    def search_graph_structured(search_term: str) -> dict:
        """
        Search the graph, and return it in a structured format for echarts, etc.
        """
        log = neo4j_logger.bind(method="search_graph_structured", search_term=search_term)
        log.debug("Executing structured graph search")

        # Handle wildcards
        formatted_term = search_term if "*" in search_term or ":" in search_term else f"{search_term}*"

        query = """
        // Find the "Hits" via Lucene
        CALL db.index.fulltext.queryNodes("global_search_index", $term)
        YIELD node
        WITH collect(node) AS searchHits

        // 2. Map Categories
        CALL {
            WITH searchHits
            UNWIND searchHits AS n
            WITH DISTINCT labels(n)[0] AS labelName
            RETURN collect({name: labelName}) AS categories
        }

        // Format Nodes
        WITH searchHits, categories, [n IN searchHits | {
            id: toString(elementId(n)),
            name: CASE
                WHEN "Neo4jImplantNode" IN labels(n) THEN coalesce(n.implant_uuid, "Unknown")
                WHEN "Neo4jNetworkNode" IN labels(n) THEN coalesce(n.cidr, "Unknown")
                ELSE coalesce(n.ip_address, n.hostname, n.process, "Unknown")
            END,
            category: labels(n)[0],
            props: properties(n)
        }] AS nodes

        // Find Links ONLY between the search hits
        OPTIONAL MATCH (a)-[r]->(b)
        WHERE a IN searchHits AND b IN searchHits
        WITH nodes, categories, collect(DISTINCT {
            source: toString(elementId(a)),
            target: toString(elementId(b)),
            value: type(r),
            props: properties(r)
        }) AS links

        RETURN {
            categories: categories,
            nodes: nodes,
            links: links
        } AS graph_data
        """
        log.debug("Running Cypher query for structured graph search")
        results, _ = db.cypher_query(query, {"term": formatted_term})

        log.debug("Structured graph search complete")
        return results[0][0] if results else {"categories": [], "nodes": [], "links": []}


class Neo4jChainingService:
    """
    A class meant to hold chaining functions

    Everything here should be a static method
    """

    @staticmethod
    def link_child_to_parent_node(child_uuid, parent_uuid):
        """Links a child node, to a parent node, for Chaining purposes.

        Uses the relationship "Linked"

        Args:
            child_uuid (_type_): uuid of child node
            parent_uuid (_type_): uuid of parent node
        """
        log = neo4j_logger.bind(method="link_child_to_parent_node", child_uuid=child_uuid, parent_uuid=parent_uuid)
        log.debug("Attempting to link child to parent")

        child_node = Neo4jImplantNodeService.create_or_get_node(
            implant_uuid=child_uuid,
        )

        # parent should already exist, so we get by uuid
        parent_node = Neo4jImplantNode.nodes.get_or_none(implant_uuid=parent_uuid)

        # if we aren't already parent of this implant
        if not parent_node.parent_to.is_connected(child_node):
            log.debug("Connecting child to parent")
            # add us to it
            parent_node.parent_to.connect(child_node)

        log.debug("Link successful")

    @staticmethod
    def get_children_of_parent(parent_uuid: str) -> list[dict]:
        """
        Finds all child implants linked TO the specified parent UUID.
        Follows the (Child)-[:LINKED]->(Parent) relationship backwards.
        """
        log = neo4j_logger.bind(method="get_children_of_parent", parent_uuid=parent_uuid)
        log.debug("Retrieving children of parent")

        # Get the parent node (don't create it if it doesn't exist here)
        parent_node = Neo4jImplantNode.nodes.get_or_none(implant_uuid=parent_uuid)

        if not parent_node:
            log.warning("Attempted to get children for non-existent parent")
            return []

        # neomodel handles the traversal. .all() returns a list of Neo4jImplantNode objects
        child_nodes = parent_node.parent_to.all()
        log.debug("Successfully retrieved children", count=len(child_nodes))

        #  Return just the properties dictionaries, matching get_all() and get_by_uuid()
        return [child.__properties__ for child in child_nodes]

    @staticmethod
    def find_egress_node_in_chain(target_uuid):
        """
        Finds the specific egress (root) node for a given implant's chain.
        If the UUID passed in is the egress, it returns that.

        maybe move me to a pathfinding or chaining class?
        """
        log = neo4j_logger.bind(method="find_egress_node_in_chain", target_uuid=target_uuid)
        log.debug("Attempting to find egress node in chain")

        query = """
        MATCH (target:Neo4jImplantNode {implant_uuid: $target_uuid})-[:LINKED*0..]->(egress:Neo4jImplantNode)
        WHERE NOT (egress)-[:LINKED]->(:Neo4jImplantNode)
        RETURN egress.implant_uuid AS egress_uuid
        """

        results, _ = db.cypher_query(query, {"target_uuid": target_uuid})

        # Extract the string from the list of lists
        if results and len(results) > 0:
            log.debug("Egress node found in chain")
            # results[0] is the first row, [0] is the first column
            # should just return uuid of implant
            return results[0][0]

        log.debug("No egress node found for target")
        # Return None if the target doesn't exist or has no path
        return None


# NEW APPROACH, provide methods to hook things together, AVOID auto hooking, it makes things weird and not scalable
class Neo4jImplantNodeService:
    @staticmethod
    def register_node(implant_uuid: str, listener_uuid: str, **kwargs):
        """
        Registers an implant node, dynamically routing arbitrary data into a metadata bucket,
        and builds out the host, listener, and network relationships.
        """
        log = neo4j_logger.bind(method="register_node", implant_uuid=implant_uuid, listener_uuid=listener_uuid)
        log.debug("Starting node registration")

        # grab data we need:
        nics = kwargs.pop("nics", {})
        system_hostname = kwargs.get("system_hostname", "UNKNOWN")

        # NEW: Extract primary IP and MAC to help uniquely identify the host
        primary_mac = None
        primary_ip = None
        if nics:
            primary_mac = list(nics.keys())[0]
            primary_ip = nics[primary_mac].get("ip")

        # Safely get or create the core implant node
        log.debug("Retrieving or creating core implant node")
        implant_node = Neo4jImplantNode.get_or_create({"implant_uuid": implant_uuid})[0]

        for key, value in kwargs.items():
            setattr(implant_node, key, value)
        implant_node.save()

        # hook up core rels
        log.debug("Hooking up core relationships")
        Neo4jImplantNodeService.connect_implant_to_listener(implant_uuid, listener_uuid)

        # NEW: Pass the strong identifiers down!
        host_uuid = Neo4jImplantNodeService.connect_implant_to_host(
            implant_uuid=implant_uuid, hostname=system_hostname, ip_address=primary_ip, mac_address=primary_mac
        )

        # Process and link NICs
        for nic_mac_address, data in nics.items():
            if not nic_mac_address:
                log.debug("MAC address missing from nic, skipping", data=data)
                continue

            nic_ip_address = data.get("ip")
            cidr = data.get("cidr")
            gateway = data.get("gateway")
            #   Create NIC and link to host
            log.debug("Processing NIC", mac_address=nic_mac_address)
            nic_node = Neo4jNicNodeService.create_or_get_node(mac_address=nic_mac_address)

            Neo4jNicNodeService.connect_nic_to_host(
                host_uuid=host_uuid, mac_address=nic_mac_address, ip_address=nic_ip_address
            )

            # Link NIC to network segment if routing data exists
            if cidr and gateway:
                network_segment = f"{gateway}/{cidr}"
                log.debug("Linking NIC to network segment", network_segment=network_segment)
                Neo4jNicNodeService.connect_nic_to_network(network_segment, nic_mac_address)

                # toss cidr on nic too:
                nic_node.cidr = network_segment
                nic_node.save()

        log.info("Node registration complete")
        return implant_node

    @staticmethod
    def update_last_checkin(implant_uuid: str) -> None:
        import time

        node = Neo4jImplantNode.get_or_create({"implant_uuid": implant_uuid})[0]
        node.last_checkin = int(time.time())
        node.save()

    @staticmethod
    def update_sleep_value(implant_uuid: str, sleep_value: int) -> None:
        node = Neo4jImplantNode.get_or_create({"implant_uuid": implant_uuid})[0]
        node.sleep_value = sleep_value
        node.save()

    @staticmethod
    def create_or_get_node(implant_uuid):
        """
        Creates a node. Useful for getting a quick new node and letting this handle all
        the node logic. Uses neomodel's get_or_create to prevent check-then-act race conditions.
        """
        log = neo4j_logger.bind(method="create_or_get_node", implant_uuid=implant_uuid)
        log.debug("Attempting to fetch or create implant node")

        # neomodel's get_or_create expects a dict and ALWAYS returns a list of nodes.
        # We append [0] to grab the actual node object out of the list.
        implant_node = Neo4jImplantNode.get_or_create({"implant_uuid": implant_uuid})[0]

        log.debug("Node fetched or created via get_or_create")
        return implant_node

    @staticmethod
    def connect_implant_to_listener(implant_uuid, listener_uuid):
        # connects this classes implant to a listener based on the listener UUID
        log = neo4j_logger.bind(
            method="connect_implant_to_listener", implant_uuid=implant_uuid, listener_uuid=listener_uuid
        )
        log.debug("Initiating implant to listener connection")

        # 2 step process

        # 1: create listener node if not exist
        # 2: Create c2 channel node if not exist

        # create or get listener node
        # listener_node = Neo4jListenerNodeService.create_or_get_node(listener_uuid)
        listener_node = Neo4jListenerNode.find_existing(listener_uuid=listener_uuid)

        # create or get channel node
        c2_channel_node = Neo4jC2ChannelNodeService.create_or_get_node(listener_uuid)

        implant_node = Neo4jImplantNode.find_existing(implant_uuid)

        # 3: link implant -> c2 channel,
        # if we aren't already hooked up to the c2 channel, add us to it
        if not implant_node.c2_established.is_connected(c2_channel_node):
            log.debug("Connecting implant to C2 channel")
            implant_node.c2_established.connect(c2_channel_node)

        #  then c2 channel -> listener
        if not c2_channel_node.targets.is_connected(listener_node):
            log.debug("Connecting C2 channel to listener")
            c2_channel_node.targets.connect(listener_node)

        log.debug("Implant connected to listener")

    # call these for various things related to enrichement.
    # basically, have caller handle this, not automatically
    @staticmethod
    def connect_implant_to_host(implant_uuid, hostname, ip_address=None, mac_address=None) -> str:
        """Connects the provided implant to the host..."""
        log = neo4j_logger.bind(method="connect_implant_to_host", implant_uuid=implant_uuid, hostname=hostname)
        log.debug("Initiating implant to host connection")

        # NEW: Pass all identifiers to the lookup
        host_node = Neo4jHostNodeService.create_or_get_node(
            hostname=hostname, ip_address=ip_address, mac_address=mac_address
        )
        implant_node = Neo4jImplantNode.find_existing(implant_uuid)

        # if we aren't already running on this host
        if not implant_node.running_on.is_connected(host_node):
            log.debug("Adding RUNNING_ON relationship to host")
            implant_node.running_on.connect(host_node)

        log.debug("Implant connected to host")
        return host_node.host_uuid

    @staticmethod
    def get_all() -> list:
        """Gets all Neo4jImplantNode instances in the DB, returns their properties."""
        log = neo4j_logger.bind(method="get_all")
        log.debug("Executing Cypher query to fetch all Neo4jImplantNodes")

        node_data, _ = db.cypher_query("MATCH (h:Neo4jImplantNode) RETURN properties(h)")

        log.debug("Successfully fetched all implant nodes", count=len(node_data))
        return [row[0] for row in node_data]

        # need to take that, then get .properties, and return just properties

    @staticmethod
    def get_by_uuid(implant_uuid: str) -> dict | None:
        """Gets a single implant node's properties by its UUID.

        Args:
            implant_uuid (str): the uuid of the implant

        Returns:
            dict | None: Dict of properties if a node exists, None, if no node.
        """
        log = neo4j_logger.bind(method="get_by_uuid", implant_uuid=implant_uuid)
        log.debug("Fetching node by UUID")

        node = Neo4jImplantNode.nodes.get_or_none(implant_uuid=implant_uuid)
        if not node:
            log.debug("Node not found")
            return None

        log.debug("Node retrieved successfully")
        # again return only the properties
        return node.__properties__

    @staticmethod
    def update_by_uuid(implant_uuid: str, data: dict):
        """
        Updates a node via its UUID and provided data dict.
        Applies all data as native properties on the SemiStructuredNode.

        Args:
            implant_uuid (str): the uuid of the implant
            data (dict): The data to add/update to the implant
        """
        log = neo4j_logger.bind(method="update_by_uuid", implant_uuid=implant_uuid)
        log.debug("Attempting to update node", data_keys=list(data.keys()))

        node = Neo4jImplantNode.nodes.get_or_none(implant_uuid=implant_uuid)
        if not node:
            log.warning("Update failed: Implant not found")
            return

        # Iterate through the incoming data and set directly on the node.
        # As a SemiStructuredNode, it accepts arbitrary properties natively.
        for key, value in data.items():
            setattr(node, key, value)

        # Save the updated properties directly to Neo4j
        node.save()

        log.debug("Implant updated successfully")

    @staticmethod
    def delete_by_uuid(implant_uuid: str) -> bool:
        """Deletes a node by its UUID

        Args:
            implant_uuid (str): uuid of the implant node to delete

        Returns:
            bool: True: Successful deletion, False: Node failed to delete
        """
        log = neo4j_logger.bind(method="delete_by_uuid", implant_uuid=implant_uuid)
        log.debug("Attempting to delete implant node")

        node = Neo4jImplantNode.nodes.get_or_none(implant_uuid=implant_uuid)
        if not node:
            log.warning("Delete failed: Implant not found")
            return False  # node doesn't exist

        node.delete()
        log.debug("Implant deleted successfully")
        return True

    @staticmethod
    def search_implants(search_term: str) -> list[dict]:
        """
        Search implants using a Full-Text Index.

        Allows for lucene searching, ex `user:...`
        """
        log = neo4j_logger.bind(method="search_implants", search_term=search_term)
        log.debug("Executing full-text search query")

        # Use Lucene syntax. Adding '*' allows for partial matches if the term is incomplete.
        # Example: '192.168' becomes '192.168*'
        formatted_term = f"{search_term}*"

        query = """
        CALL db.index.fulltext.queryNodes("implant_search_index", $term)
        YIELD node, score
        RETURN properties(node) AS props
        ORDER BY score DESC
        """

        # Using your existing db.cypher_query pattern
        results, _ = db.cypher_query(query, {"term": formatted_term})

        log.debug("Search query completed", result_count=len(results))
        return [row[0] for row in results]

    @staticmethod
    def get_host_implant_is_connected_to(implant_uuid: str) -> Neo4jHostNode | None:
        """
        Gets the host the implant is connected to

        implant_uuid: implant to get the host it's connected to
        """
        log = neo4j_logger.bind(method="get_host_implant_is_connected_to", implant_uuid=implant_uuid)
        log.debug("Retrieving connected host for implant")

        # get hostname of host that the implant is connected to
        implant_node = Neo4jImplantNodeService.create_or_get_node(implant_uuid)

        # need to get the host the implant is connected to
        host_nodes = hosts = implant_node.running_on.all()  # returns a list

        # saftey check so we don't get an index err
        if host_nodes:
            log.debug("Successfully found connected host")
            return hosts[0]

        log.debug("No connected host found for implant")
        return None


class Neo4jHostNodeService:
    """
    Host can have:
     - A network its connected to
     - implants that connect to it

    """

    @staticmethod
    def create_or_get_node(hostname=None, ip_address=None, mac_address=None):
        """
        Attempts to find a Host by hostname, IP, or MAC.
        If nothing matches, creates a new Host with a UUIDv7.
        """
        log = neo4j_logger.bind(method="create_or_get_node", hostname=hostname, ip=ip_address, mac=mac_address)
        log.debug("Attempting to find existing host node by available identifiers")

        # Look up the host using any available identifier
        # need to add a custom func for this, or query.
        host_node = Neo4jHostNode.find_by_any_identifier(
            hostname=hostname, ip_address=ip_address, mac_address=mac_address
        )

        # If we found a match, return it
        if host_node:
            log.debug("Found existing Host node.", host_uuid=host_node.host_uuid)
            return host_node

        # If no results, create a new node with a UUIDv7
        new_uuid = str(uuid7())
        log.debug("Host node not found. Creating new with UUIDv7", new_uuid=new_uuid)

        return Neo4jHostNode(host_uuid=new_uuid, hostname=hostname).save()


class Neo4jListenerNodeService:
    # DO NOT include create_or_get_node, we fully control the data of Neo4jListenerNodeServices, and
    # it is a structured node, so this does not make sense here. Listeners are not as variable as the
    # rest of the models/services
    # @staticmethod
    # def create_or_get_node(listener_uuid):

    def create(self, data: ListenerCreate) -> "Neo4jListenerNode":
        """
        Create a new listener node.
        """
        log = server_logger.bind(method="create")
        log.debug("Creating new listener node")
        check_type(data, ListenerCreate, "data")

        try:
            # Convert dataclass/pydantic to dict
            props = vars(data).copy()

            # Check composite uniqueness manually (Neo4j doesn't do multi-property unique constraints
            # natively on SemiStructured nodes)
            log.debug("Enforcing composite unique constraints")
            self._enforce_composite_unique(
                host=props.get("listener_host"), port=props.get("listener_port"), active=props.get("listener_active")
            )

            log.debug("Successfully created listener node")
            return Neo4jListenerNode(**props).save()

        except Exception as e:
            log.error("Error", class_name=self.__class__.__name__, error=e)
            raise

    def get_by_id(self, listener_id: str) -> "Neo4jListenerNode | None":
        """
        Retrieve a listener node by primary key (uuid).
        """
        log = server_logger.bind(method="get_by_id", listener_id=listener_id)
        check_type(listener_id, str, "listener_id")

        try:
            log.debug("Retrieving listener from Neo4j Database")
            return Neo4jListenerNode.find_existing(listener_uuid=listener_id)

        except Exception as e:
            log.error("Error", class_name=self.__class__.__name__, error=e)
            raise

    def get_all(self):
        """
        Gets all listener nodes.
        """
        log = server_logger.bind(method="get_all")
        try:
            log.debug("Retrieving all listeners from Neo4j Database")
            return Neo4jListenerNode.nodes.all()

        except Exception as e:
            log.error("Error", class_name=self.__class__.__name__, error=e)
            raise

    def update(self, listener_id: str, data: ListenerUpdate) -> "Neo4jListenerNode | None":
        """
        Update a listener node by uuid.
        """
        log = server_logger.bind(method="update", listener_uuid=listener_id, data=data)
        log.debug("Updating listener in Neo4j Database")
        check_type(listener_id, str, "listener_id")
        check_type(data, ListenerUpdate, "data")

        try:
            listener = self.get_by_id(listener_id)
            if not listener:
                log.debug("Listener not found for update")
                return None

            # Re-check uniqueness before saving if host/port/active changed
            log.debug("Enforcing composite constraints before save")
            self._enforce_composite_unique(
                host=getattr(listener, "listener_host", None),
                port=getattr(listener, "listener_port", None),
                active=getattr(listener, "listener_active", None),
                exclude_uuid=listener.listener_uuid,
            )

            listener.save()
            log.debug("Successfully updated listener node")
            return listener

        except Exception as e:
            log.error("Error", class_name=self.__class__.__name__, error=e)
            raise

    def set_active(self, listener_id: str, active: bool):
        log = server_logger.bind(method="set_active", listener_uuid=listener_id, state=active)
        log.debug("Setting listener state Neo4j Database")
        check_type(listener_id, str, "listener_id")
        check_type(active, bool, "active")

        listener = self.get_by_id(listener_id)
        if not listener:
            log.debug("Listener not found for state update")
            return

        listener.listener_active = active

        # Enforce constraints
        log.debug("Checking constraints for state update")
        self._enforce_composite_unique(
            host=getattr(listener, "listener_host", None),
            port=getattr(listener, "listener_port", None),
            active=active,
            exclude_uuid=listener.listener_uuid,
        )

        listener.save()
        log.debug("Listener state updated successfully")

    def delete(self, listener_id: str) -> bool:
        """
        Delete a listener node by uuid.
        """
        log = server_logger.bind(method="delete", listener_uuid=listener_id)
        log.debug("Deleting listener in Neo4j Database")
        check_type(listener_id, str, "listener_id")

        try:
            listener = self.get_by_id(listener_id)
            if not listener:
                log.debug("Listener not found to delete")
                return None

            listener.delete()
            log.debug("Listener deleted successfully")
            return True

        except Exception as e:
            log.error("Error", class_name=self.__class__.__name__, error=e)
            raise

    def _enforce_composite_unique(self, host, port, active, exclude_uuid=None):
        """
        Helper to simulate MySQL's UniqueConstraint("listener_host", "listener_port", "listener_active").
        """
        log = server_logger.bind(method="_enforce_composite_unique", host=host, port=port, active=active)
        log.debug("Validating composite constraint")

        if host is None or port is None or active is None:
            log.debug("Missing composite key parts, skipping check")
            return  # Skip check if we don't have all parts of the composite key

        existing = Neo4jListenerNode.nodes.filter(listener_host=host, listener_port=port, listener_active=active)

        for node in existing:
            if node.listener_uuid != exclude_uuid:
                log.warning("UniqueConstraint violated")
                raise ValueError(
                    "UniqueConstraint violated: listener_host, listener_port, listener_active must be unique."
                )


class Neo4jNicNodeService:
    @staticmethod
    def create_or_get_node(mac_address: str = None, ip_address: str = None):
        """
        Creates or retrieves a NIC node. Handles cases where MAC might be missing
        (e.g., VPN adapters) by falling back to IP, and uses UUIDv7 for identity.
        """
        log = neo4j_logger.bind(method="create_or_get_node", mac_address=mac_address, ip_address=ip_address)
        log.debug("Attempting to get or create NIC node")

        # 1. Sanity check: We need at least one piece of data to identify a NIC
        if not mac_address and not ip_address:
            log.warning("Cannot create or get NIC without a MAC or IP address.")
            return None

        # 2. Look up the NIC using either MAC or IP
        # (Requires a custom method on Neo4jNicNode similar to the Host node's lookup)
        nic_node = Neo4jNicNode.find_by_any_identifier(mac_address=mac_address, ip_address=ip_address)

        # 3. If found, check if we need to fill in any newly discovered missing data
        if nic_node:
            log.debug("Found existing NIC node", nic_uuid=nic_node.nic_uuid)
            needs_save = False

            if mac_address and not nic_node.mac_address:
                nic_node.mac_address = mac_address
                needs_save = True

            if ip_address and not nic_node.ip_address:
                nic_node.ip_address = ip_address
                needs_save = True

            if needs_save:
                log.debug("Updating existing NIC with newly discovered data")
                nic_node.save()

            return nic_node

        # 4. If not found, create a brand new one with a UUIDv7
        new_uuid = str(uuid7())
        log.debug("NIC not found, creating new with UUIDv7", nic_uuid=new_uuid)

        nic_node = Neo4jNicNode(nic_uuid=new_uuid, mac_address=mac_address, ip_address=ip_address).save()

        log.debug("New NIC node created", nic_uuid=new_uuid)

        return nic_node

    # @staticmethod
    # def connect_nic_to_host(hostname, mac_address: str, ip_address=""):
    #     """
    #     hostname: hostname of host to connect the nic to

    #     mac_address: mac address of the NIC connecting to a host
    #     ip_address (optional): ip_address of the NIC connecting to a host, if you have the IP for that nic
    #     """
    #     log = neo4j_logger.bind(method="connect_nic_to_host", hostname=hostname, mac_address=mac_address)
    #     log.debug("Connecting NIC to host")

    #     # create or get our NIC
    #     nic_node = Neo4jNicNodeService.create_or_get_node(mac_address)
    #     # add ip to it as well if we have it
    #     nic_node.ip_address = ip_address
    #     nic_node.save()

    #     # create or get host node
    #     host_node = Neo4jHostNodeService.create_or_get_node(hostname)

    #     # 3: link nic to host
    #     if not nic_node.attached_to.is_connected(host_node):
    #         log.debug("Linking NIC to host node")
    #         nic_node.attached_to.connect(host_node)

    #     log.debug("Nic -> host successful")

    @staticmethod
    def connect_nic_to_host(host_uuid: str, mac_address: str = None, ip_address: str = None):
        """
        host_uuid: The UUID of the Host to connect the NIC to.
        mac_address (optional): MAC address of the NIC.
        ip_address (optional): IP address of the NIC.
        """
        log = neo4j_logger.bind(
            method="connect_nic_to_host", host_uuid=host_uuid, mac_address=mac_address, ip_address=ip_address
        )
        log.debug("Connecting NIC to host")

        # Sanity Check: Ensure we have enough data to make a NIC
        if not mac_address and not ip_address:
            log.warning("Skipping NIC connection: Both MAC and IP are missing.")
            return

        # create or get our NIC
        nic_node = Neo4jNicNodeService.create_or_get_node(mac_address=mac_address, ip_address=ip_address)

        # Retrieve the Host node strictly by its UUID
        host_node = Neo4jHostNode.nodes.get_or_none(host_uuid=host_uuid)

        if not host_node:
            log.error("Failed to connect NIC: Host node not found.", host_uuid=host_uuid)
            return

        # Link NIC to Host
        if not nic_node.attached_to.is_connected(host_node):
            log.debug("Linking NIC to host node")
            nic_node.attached_to.connect(host_node)

        log.debug("Nic -> host connection successful")

    @staticmethod
    def connect_nic_to_network(network_cidr: str, nic_mac_address: str):
        """
        Links a NIC node to a Network node based on the CIDR.
        """
        log = neo4j_logger.bind(
            method="connect_nic_to_network", network_cidr=network_cidr, nic_mac_address=nic_mac_address
        )
        log.debug("Connecting NIC to network")

        # Retrieve the NIC (Should already exist from previous step in register_node)
        nic_node = Neo4jNicNodeService.create_or_get_node(nic_mac_address)

        # Retrieve or create the Network node
        # Note: Ensure Neo4jNetworkNode uses 'cidr' or 'network_uuid' as defined in your model
        network_node = Neo4jNetworkNodeService.create_or_get_node(network_cidr)

        if not network_node:
            log.error("Failed to find or create network node", network_cidr=network_cidr)
            return

        # Link NIC to Network
        if not nic_node.in_network.is_connected(network_node):
            log.debug("Linking NIC to network node")
            nic_node.in_network.connect(network_node)

        log.debug("Nic -> network successful")

    @staticmethod
    def connect_nic_to_network_by_uuid(network_uuid: str, nic_uuid: str):
        """
        Links a NIC node to a Network node using their specific UUIDs.
        """
        log = neo4j_logger.bind(method="connect_nic_to_network_by_uuid", network_uuid=network_uuid, nic_uuid=nic_uuid)

        # Lookup both nodes using the exact property names
        nic_node = Neo4jNicNode.nodes.get_or_none(nic_uuid=nic_uuid)
        network_node = Neo4jNetworkNode.nodes.get_or_none(network_uuid=network_uuid)

        if not nic_node or not network_node:
            log.error("Could not find nodes for linking", nic_exists=bool(nic_node), net_exists=bool(network_node))
            return

        # Create the relationship if it doesn't exist
        if not nic_node.in_network.is_connected(network_node):
            log.debug("Linking NIC and Network via UUID")
            nic_node.in_network.connect(network_node)


class Neo4jNetworkNodeService:
    @staticmethod
    def create_or_get_node(network_cidr):
        """
        Creates a node. Useful for getting a quick new node and letting this handle all
        the node logic
        """
        log = neo4j_logger.bind(method="create_or_get_node", network_cidr=network_cidr)
        log.debug("Attempting to get or create network node")

        listener_node = Neo4jNetworkNode.find_existing(cidr=network_cidr)
        if not listener_node:
            log.debug("Network node not found, creating new")
            listener_node = Neo4jNetworkNode(cidr=network_cidr).save()
            log.debug("New network created", network_cidr=network_cidr)

        return listener_node


class Neo4jC2ChannelNodeService:
    @staticmethod
    def create_or_get_node(listener_uuid) -> Neo4jC2ChannelNode:
        """
        Creates a node. This is a handy way to creat the nodes, especially if they have
        addtl logic that may require addtl lookups for their data
        """
        log = neo4j_logger.bind(method="create_or_get_node", listener_uuid=listener_uuid)
        log.debug("Attempting to get or create C2 channel node")

        channel_id = Neo4jC2ChannelNodeService._get_channel_id(listener_uuid)

        listener_class = Neo4jListenerNodeService()
        listener_object = listener_class.get_by_id(listener_uuid)
        listener_type = listener_object.listener_type

        channel_node = Neo4jC2ChannelNode.find_existing(channel_id=channel_id)
        if not channel_node:
            log.debug("Channel node not found, creating new")
            channel_node = Neo4jC2ChannelNode(channel_id=channel_id, protocol=listener_type).save()
            log.debug("New c2 channel node created", channel_id=channel_id)

        return channel_node

    @staticmethod
    def _get_channel_id(listener_uuid) -> str:
        """
        Create a unique key for the channel id in neo4j.
        """
        log = neo4j_logger.bind(method="_get_channel_id", listener_uuid=listener_uuid)
        log.debug("Generating channel ID for listener")

        listener_class = Neo4jListenerNodeService()
        listener_object = listener_class.get_by_id(listener_uuid)

        return f"{listener_object.listener_uuid}_{listener_object.listener_type}_{listener_object.listener_host}_{listener_object.listener_port}"  # noqa - unique channel id


class Neo4jMemstoreFileNodeService:
    @staticmethod
    def create_or_get_node(file_name):
        """
        Creates a node. Useful for getting a quick new node and letting this handle all
        the node logic
        """
        log = neo4j_logger.bind(method="create_or_get_node", file_name=file_name)
        log.debug("Attempting to get or create memstore file node")

        listener_node = Neo4jMemstoreFileNode.find_existing(file_name=file_name)
        if not listener_node:
            log.debug("Memstore file node not found, creating new")
            listener_node = Neo4jMemstoreFileNode(file_name=file_name).save()
            log.debug("New memstore file node created", file_name=file_name)

        return listener_node

    @staticmethod
    def connect_memstore_file_to_implant(file_name, implant_uuid, file_hash_md5: str = ""):
        """
        hostname: hostname of host to connect the nic to

        mac_address: mac address of the NIC connecting to a host
        ip_address (optional): ip_address of the NIC connecting to a host, if you have the IP for that nic

        file_hash_md5: (optional) md5 of file
        """
        log = neo4j_logger.bind(
            method="connect_memstore_file_to_implant", file_name=file_name, implant_uuid=implant_uuid
        )
        log.debug("Connecting memstore file to implant")

        # create or get our implant
        implant_node = Neo4jImplantNodeService.create_or_get_node(implant_uuid)
        # add ip to it as well if we have it

        # create or get our file
        memstore_file_node = Neo4jMemstoreFileNodeService.create_or_get_node(file_name)
        # add in hash
        memstore_file_node.md5 = file_hash_md5
        memstore_file_node.save()

        # 3: link file to implant
        if not memstore_file_node.stored_in.is_connected(implant_node):
            log.debug("Linking memstore file to implant node")
            memstore_file_node.stored_in.connect(implant_node)

        log.debug("Memstore file -> Implant successful")

    @staticmethod
    def get_all_files_nodes_for_implant(
        implant_uuid: str,
    ) -> list[Neo4jMemstoreFileNode]:
        log = neo4j_logger.bind(method="get_all_files_nodes_for_implant", implant_uuid=implant_uuid)
        log.debug("Retrieving all file nodes for implant")

        implant_node = Neo4jImplantNode.nodes.get_or_none(implant_uuid=implant_uuid)

        if not implant_node:
            log.warning("Implant not found, returning empty list")
            return []

        # note, the reverse rel allwos us jsut to do this
        log.debug("Returning linked memstore files")
        return list(implant_node.memstore_files.all())


class Neo4jFileNodeService:
    """
    Track what files the operators have uploaded to a host
    """

    @staticmethod
    def create_or_get_node(file_path):
        """
        Creates a node. Useful for getting a quick new node and letting this handle all
        the node logic
        """
        log = neo4j_logger.bind(method="create_or_get_node", file_path=file_path)
        log.debug("Attempting to get or create file node")

        listener_node = Neo4jFileNode.find_existing(file_path=file_path)
        if not listener_node:
            log.debug("File node not found, creating new")
            listener_node = Neo4jFileNode(file_path=file_path).save()
            log.debug("New file node created", file_path=file_path)

        return listener_node

    @staticmethod
    def connect_file_to_host(file_path, hostname, file_hash_md5: str = ""):
        """
        file_path: path of file
        hostname: hostname of host to connect the file to
        file_hash_md5: (optional) md5 of file
        """
        log = neo4j_logger.bind(method="connect_file_to_host", file_path=file_path, hostname=hostname)
        log.debug("Connecting file to host")

        # create or get our implant
        host_node = Neo4jHostNodeService.create_or_get_node(hostname)
        # add ip to it as well if we have it

        # create or get our file
        file_node = Neo4jFileNodeService.create_or_get_node(file_path)
        # add in hash
        file_node.md5 = file_hash_md5
        file_node.file_path = file_path
        file_node.save()

        # 3: link file to implant
        if not file_node.stored_on.is_connected(host_node):
            log.debug("Linking file to host node")
            file_node.stored_on.connect(host_node)

        log.debug("Disk File -> Implant successful")

    # @staticmethod
    # def get_all_files_nodes_for_host(
    #     hostname: str,
    # ) -> list[Neo4jFileNode]:
    #     host_node = Neo4jHostNode.nodes.get_or_none(hostname=hostname)

    #     if not host_node:
    #         return []

    #     # note, the reverse rel allwos us jsut to do this
    #     return list(host_node.stored_on.all())
