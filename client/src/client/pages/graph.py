import logging

import httpx
from nicegui import ui

# Imports
from client.src.client.modules.api_calls import get_all_graph_data
from client.src.client.pages.menu import setup_menu
from client.src.client.style import ICON_COLOR, TEXT_COLOR

from ..utils.checks import check_type

server_log = logging.getLogger("server")


@ui.page("/graph")
async def graph():
    # Full Screen Layout Setup
    ui.context.client.content.classes("h-full p-0 gap-0")
    ui.context.client.page_container.default_slot.children[0].props(
        ':style-fn="o => ({ height: `calc(100vh - ${o}px)` })"'
    )

    setup_menu("Listeners")
    await graph_view()


async def graph_view():
    # basic data struct, can mess around with numbers based on node type, etc.
    # """
    # Cypher for this:

    # MATCH (n)
    # RETURN DISTINCT
    #     id(n) AS id,
    #     n.system_hostname AS name,
    #     CASE
    #         WHEN "Neo4jImplantNode" IN labels(n) THEN 0
    #         ELSE 1
    #     END AS category,
    #     properties(n) AS props;

    # """
    # # 1. Define the graph data (Mimicking a Neo4j Cypher response)
    # nodes = [
    #     {"id": "0", "name": "Ryan", "category": 0, "symbolSize": 60},
    #     {"id": "1", "name": "Python", "category": 1, "symbolSize": 40},
    #     {"id": "2", "name": "NiceGUI", "category": 1, "symbolSize": 40},
    #     {"id": "3", "name": "Neo4j", "category": 2, "symbolSize": 50},
    # ]

    # # cypher queries for this struct:
    # """
    # MATCH (a)-[r]->(b)
    # RETURN id(a) AS source,
    #     id(b) AS target,
    #     type(r) AS value,
    #     properties(r) AS props;

    # """
    # links = [
    #     {"source": "0", "target": "1", "value": "CODES_IN"},
    #     {"source": "0", "target": "3", "value": "QUERIES"},
    #     {"source": "1", "target": "2", "value": "USES_FRAMEWORK"},
    #     {"source": "2", "target": "3", "value": "CONNECTS_TO"},
    # ]

    # categories = [
    #     {"name": "User"},
    #     {"name": "Language/Framework"},
    #     {"name": "Database"},
    # ]
    graph_data = await get_all_graph_data()

    graph_data = graph_data.get("data", {})

    nodes = graph_data.get("nodes", [])
    links = graph_data.get("links", [])
    categories = graph_data.get("categories", [])

    print(graph_data)

    options = {
        "title": {"text": "Interactive Node Graph"},
        "tooltip": {},
        "legend": [{"data": [c["name"] for c in categories]}],
        "series": [
            {
                "type": "graph",
                "layout": "force",  # This makes it bounce and settle like Neo4j
                "data": nodes,
                "links": links,
                "categories": categories,
                "roam": True,  # Allows zooming and panning
                "draggable": True,  # Allows dragging nodes around
                "label": {"show": True, "position": "right", "formatter": "{b}"},
                "force": {
                    "repulsion": 300,  # How far apart nodes push each other
                    "edgeLength": 150,  # Target length of the relationships
                },
            }
        ],
    }

    chart = ui.echart(options).classes("w-full h-full")

    # def handle_click(e):
    #     # e.args contains all the data about the node or edge clicked
    #     item_type = e.args.get("dataType")  # 'node' or 'edge'
    #     name = e.args.get("name")
    #     ui.notify(f"Left clicked {item_type}: {name}", color="info")

    # def handle_right_click(e):
    #     # This triggers on right-click
    #     item_type = e.args.get("dataType")
    #     name = e.args.get("name")
    #     ui.notify(f"Action Menu opened for: {name}", color="warning")
    #     # could do context menu

    # chart.on("click", handle_click)
    # chart.on("contextmenu", handle_right_click)

    # Prevent the default browser right-click menu from covering your UI
    ui.add_head_html("<style>.nicegui-echart { align-content: center; }</style>")
    # ui.run(dark=True)

    ## thereis some really cool stuff you can do with this:
    # graph (it's a bit bouncy):https://echarts.apache.org/examples/en/editor.html?c=graph-webkit-dep
    # world map graph: https://echarts.apache.org/examples/en/editor.html?c=geo-graph
