import json
import logging
import urllib.parse

import httpx
from nicegui import ui

# Imports
from client.src.client.modules.api_calls import get_all_graph_data
from client.src.client.pages.menu import setup_menu
from client.src.client.style import ICON_COLOR, TEXT_COLOR

from ..utils.checks import check_type

server_log = logging.getLogger("server")

PATH_NETWORK = "M3 12H21M12 8V12M6.5 12V16M17.5 12V16M10.1 8H13.9C14.4601 8 14.7401 8 14.954 7.89101C15.1422 7.79513 15.2951 7.64215 15.391 7.45399C15.5 7.24008 15.5 6.96005 15.5 6.4V4.6C15.5 4.03995 15.5 3.75992 15.391 3.54601C15.2951 3.35785 15.1422 3.20487 14.954 3.10899C14.7401 3 14.4601 3 13.9 3H10.1C9.53995 3 9.25992 3 9.04601 3.10899C8.85785 3.20487 8.70487 3.35785 8.60899 3.54601C8.5 3.75992 8.5 4.03995 8.5 4.6V6.4C8.5 6.96005 8.5 7.24008 8.60899 7.45399C8.70487 7.64215 8.85785 7.79513 9.04601 7.89101C9.25992 8 9.53995 8 10.1 8ZM15.6 21H19.4C19.9601 21 20.2401 21 20.454 20.891C20.6422 20.7951 20.7951 20.6422 20.891 20.454C21 20.2401 21 19.9601 21 19.4V17.6C21 17.0399 21 16.7599 20.891 16.546C20.7951 16.3578 20.6422 16.2049 20.454 16.109C20.2401 16 19.9601 16 19.4 16H15.6C15.0399 16 14.7599 16 14.546 16.109C14.3578 16.2049 14.2049 16.3578 14.109 16.546C14 16.7599 14 17.0399 14 17.6V19.4C14 19.9601 14 20.2401 14.109 20.454C14.2049 20.6422 14.3578 20.7951 14.546 20.891C14.7599 21 15.0399 21 15.6 21ZM4.6 21H8.4C8.96005 21 9.24008 21 9.45399 20.891C9.64215 20.7951 9.79513 20.6422 9.89101 20.454C10 20.2401 10 19.9601 10 19.4V17.6C10 17.0399 10 16.7599 9.89101 16.546C9.79513 16.3578 9.64215 16.2049 9.45399 16.109C9.24008 16 8.96005 16 8.4 16H4.6C4.03995 16 3.75992 16 3.54601 16.109C3.35785 16.2049 3.20487 16.3578 3.10899 16.546C3 16.7599 3 17.0399 3 17.6V19.4C3 19.9601 3 20.2401 3.10899 20.454C3.20487 20.6422 3.35785 20.7951 3.54601 20.891C3.75992 21 4.03995 21 4.6 21Z"
PATH_USER = "M12,4A4,4 0 0,1 16,8A4,4 0 0,1 12,12A4,4 0 0,1 8,8A4,4 0 0,1 12,4M12,14C16.42,14 20,15.79 20,18V20H4V18C4,15.79 7.58,14 12,14Z"
PATH_HOST = "M20,19V7H4V19H20M20,3A2,2 0 0,1 22,5V19A2,2 0 0,1 20,21H4A2,2 0 0,1 2,19V5C2,3.89 2.9,3 4,3H20M13,17V15H18V17H13M9.58,13L5.57,9H8.4L11.7,12.3C12.09,12.69 12.09,13.33 11.7,13.72L8.42,17H5.59L9.58,13Z"
PATH_IMPLANT = "M503.462,175.026c-9.17-27.778-27.024-39.163-42.703-33.992c-12.666,4.185-19.858,17.989-17.396,37.745   L383.37,198.58c-11.654-27.844-32.25-50.944-58.14-65.941l21.812-71.596c18.69,1.626,31.462-5.402,35.078-17.272   c4.581-15.034-7.103-31.926-34.563-40.289c-27.46-8.371-46.579-0.866-51.16,14.161c-3.701,12.146,3.394,25.42,20.652,34.522   l-20.682,67.851c-12.632-3.82-26.013-5.924-39.894-5.924c-16.47,0-32.194,3.044-46.833,8.357l-11.274-30.994   c13.419-8.199,18.585-18.988,15.187-28.329c-4.302-11.833-20.507-16.81-43.177-8.55c-22.67,8.244-31.903,22.465-27.591,34.298   c3.473,9.55,14.795,14.49,30.93,11.751l12.071,33.187c-20.129,12.109-36.898,29.15-48.597,49.548L71.2,158.022   c3.1-20.592-3.443-35.022-15.806-39.514c-15.661-5.7-34.492,6.499-45.415,36.506c-10.927,30.001-4.357,51.467,11.311,57.167   c12.642,4.611,27.285-2.679,38.234-21.369l64.362,24.749c-3.122,11.504-4.936,23.554-4.936,36.051   c0,21.152,4.916,41.11,13.448,59.016l-45.956,26.532c-11.008-12.304-23.342-15.527-32.676-10.14   c-11.818,6.827-14.321,24.652-1.671,46.542c12.635,21.89,29.318,28.65,41.14,21.824c9.546-5.514,12.848-18.265,7.17-34.471   l46.284-26.725c19.175,25.449,46.904,44.005,78.99,51.362l-7.767,71.707c-20.357,1.522-32.489,10.192-33.757,21.913   c-1.608,14.862,14.608,28.792,45.836,32.172c31.228,3.388,50.052-6.752,51.66-21.614c1.298-11.99-9.207-23.293-29.676-29.016   l7.771-71.745c33.888-0.806,64.672-13.848,88.23-34.902l53.947,45.616c-10.2,17.831-9.8,32.828-0.739,40.491   c11.478,9.699,32.231,4.036,52.637-20.1c20.406-24.129,22.547-45.542,11.069-55.234c-9.267-7.842-24.602-5.446-40.905,8.394   l-53.28-45.057c14.695-21.89,23.286-48.22,23.286-76.565c0-7.618-0.78-15.041-1.97-22.316l61.572-20.331   c9.747,16.474,23.412,22.875,35.794,18.787C505.062,222.574,512.631,202.796,503.462,175.026z M210.345,319.508   c-11.841-15.638-20.421-37.41-16.004-46.243c4.431,3.447,9.822,7.573,16.004,11.094V319.508z M237.935,336.848   c-0.999,0.03-2.051,0.052-2.887,0.096c-4.006,0.209-8.353-1.738-12.68-4.992v-42.169c3.686,1.193,7.566,2.015,11.64,2.275   c1.19,0.075,2.529,0.158,3.928,0.232V336.848z M201.056,248.822c-9.069-8.752-4.037-29.284-4.037-29.284l42.386,20.368   C239.405,239.906,218.212,265.378,201.056,248.822z M265.526,336.802c-5.305-0.052-10.639-0.089-15.568-0.097v-43.759   c5.23,0.276,10.677,0.537,15.568,0.746V336.802z M293.117,333.587c-3.063,2.134-6.118,3.357-9.009,3.357   c-2.018,0-4.242-0.007-6.558-0.03V294.11c0.91,0.016,1.742,0.03,2.384,0.03c2.477,0,7.494-1.574,13.184-3.805V333.587z    M270.76,239.265l44.236-20.368c0,0,5.253,20.533-4.215,29.284C292.878,264.737,270.76,239.265,270.76,239.265z M305.14,320.388   v-35.246c7.305-3.432,13.713-6.954,15.504-8.745C318.966,292.633,312.769,308.824,305.14,320.388z"
PATH_GATEWAY = "M9.5 20H6.2C5.0799 20 4.51984 20 4.09202 19.782C3.71569 19.5903 3.40973 19.2843 3.21799 18.908C3 18.4802 3 17.9201 3 16.8V7.2C3 6.0799 3 5.51984 3.21799 5.09202C3.40973 4.71569 3.71569 4.40973 4.09202 4.21799C4.51984 4 5.0799 4 6.2 4H15.8C16.9201 4 17.4802 4 17.908 4.21799C18.2843 4.40973 18.5903 4.71569 18.782 5.09202C19 5.51984 19 6.0799 19 7.2V8H3M3 12H11V8M3 16H9M7 4V8M7 12V16M15 4V8M19.8284 19.8284C18.2663 21.3905 15.7337 21.3905 14.1716 19.8284C13.3905 19.0474 13 18.0237 13 17C13 15.9763 13.3905 14.9526 14.1716 14.1716C14.1716 14.1716 14.5 15 15.5 15.5C15.5 14.5 15.75 13 16.9929 12C18 13 19.0456 13.3887 19.8284 14.1716C20.6095 14.9526 21 15.9763 21 17C21 18.0237 20.6095 19.0474 19.8284 19.8284Z"

CHART_COLORS = [
    "#10b981",  # implant
    "#3b82f6",  # network
    "#a855f7",  # gateway
    "#d3eb00",  # host
]


@ui.page("/graph")
async def graph():
    ui.context.client.content.classes("h-full p-0 gap-0")
    ui.context.client.page_container.default_slot.children[0].props(
        ':style-fn="o => ({ height: `calc(100vh - ${o}px)` })"'
    )

    setup_menu("Network")
    await graph_view()


async def graph_view():
    # MATCH (n)
    # RETURN DISTINCT
    #     id(n) AS id,
    #     n.system_hostname AS name,
    #     CASE
    #         WHEN "Neo4jImplantNode" IN labels(n) THEN 0
    #         ELSE 1
    #     END AS category,
    #     properties(n) AS props;
    #
    # MATCH (a)-[r]->(b)
    # RETURN id(a) AS source,
    #     id(b) AS target,
    #     type(r) AS value,
    #     properties(r) AS props;

    graph_data_response = await get_all_graph_data()
    graph_data = graph_data_response.get("data", {})

    nodes = graph_data.get("nodes", [])
    links = graph_data.get("links", [])
    # categories = graph_data.get("categories", [])

    # force this order to render correctly
    # see graph_resouce in server to determine these.
    categories = [
        {"name": "Implant"},  # Index 0
        {"name": "Network"},  # Index 1
        {"name": "Gateway"},  # Index 2
        {"name": "Host"},  # Index 3
    ]

    nodes = set_node_icons(nodes)
    options = build_chart_options(nodes, links, categories)

    with ui.column().classes("w-full h-full gap-0 tech-glass-panel"):

        # parent bar
        build_header_bar()

        # graph layout
        with ui.row().classes("w-full flex-grow overflow-hidden flex-nowrap"):

            with ui.column().classes("flex-grow h-full relative p-2"):
                chart = ui.echart(
                    options,
                    on_point_click=lambda e: handle_click(
                        e, ui_state, nodes, links, categories
                    ),
                ).classes("w-full h-full bg-[#0a0a0a] rounded border border-white/5")

                with chart:
                    with ui.menu().props("context-menu"):
                        ui.menu_item("Copy")
                        ui.menu_item("Delete")

            ui_state = build_inspector_sidebar()


def build_header_bar():
    with ui.row().classes("w-full items-center justify-between tech-header-bar"):
        with ui.row().classes("items-center gap-3"):
            ui.icon("device_hub", color="emerald-500").classes("text-xl")
            ui.label("NETWORK_TOPOLOGY //").classes("tech-label-title")

        with ui.row().classes("items-center gap-2"):
            ui.button(icon="refresh", on_click=lambda: ui.navigate.to("/graph")).props(
                "dense flat size=sm"
            ).classes("tech-btn-ghost").tooltip("Refresh Topology")


def build_inspector_sidebar():
    with ui.column().classes(
        "w-80 h-full border-l border-white/5 bg-[#0f0f0f] flex-shrink-0 flex-nowrap overflow-hidden"
    ):
        with ui.row().classes(
            "w-full p-4 items-center gap-2 border-b border-white/5 bg-white/5"
        ):
            ui.icon("data_object", color="emerald-500").classes("text-lg")
            ui.label("NODE_INSPECTOR").classes(
                "tech-label-subtitle text-xs font-bold text-neutral-300 tracking-wider"
            )

        # Removed the padding from the scroll area so the placeholder can truly center
        with ui.scroll_area().classes("w-full flex-grow"):

            # 1. Perfectly centered placeholder
            placeholder = ui.column().classes(
                "w-full min-h-[50vh] items-center justify-center opacity-40 gap-2"
            )
            with placeholder:
                ui.icon("ads_click", size="3em").classes("text-emerald-500")
                ui.label("AWAITING SELECTION").classes(
                    "font-mono text-[10px] tracking-[0.2em] text-neutral-400"
                )

            # 2. Left-aligned, well-spaced data container
            data_container = ui.column().classes("w-full p-5 gap-6 hidden items-start")
            with data_container:

                # Header Section
                with ui.column().classes("w-full gap-2"):
                    entity_type_badge = ui.label("").classes(
                        "text-[9px] font-bold font-mono tracking-widest px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                    )
                    entity_name = ui.label("").classes(
                        "text-lg font-mono text-white font-bold break-words leading-tight"
                    )

                ui.separator().classes("bg-white/10 w-full")

                # Attributes Section
                with ui.column().classes("w-full gap-3"):
                    ui.label("ATTRIBUTES").classes(
                        "text-[10px] font-mono text-neutral-500 tracking-widest font-bold"
                    )
                    props_view = ui.column().classes("w-full gap-2")

    return {
        "placeholder": placeholder,
        "data_container": data_container,
        "entity_type_badge": entity_type_badge,
        "entity_name": entity_name,
        "props_view": props_view,
    }


def handle_click(e, ui_state, nodes, links, categories):
    ui_state["placeholder"].classes(add="hidden")
    ui_state["data_container"].classes(remove="hidden")
    ui_state["props_view"].clear()

    data_index = e.data_index

    # ECharts "dataType" tells us if it's a "node" or "edge"
    # It's either a direct attribute, or packed inside the data dictionary
    item_type = getattr(e, "data_type", None)
    if item_type is None and isinstance(e.data, dict):
        item_type = e.data.get("dataType", "node")

    raw_props = {}

    # Pull items from node list
    if item_type == "node":
        clicked_node = nodes[data_index]
        raw_props = clicked_node.get("props", {})

        cat_idx = clicked_node.get("category", 0)
        cat_name = categories[cat_idx]["name"] if cat_idx < len(categories) else "NODE"

        ui_state["entity_type_badge"].set_text(cat_name.upper())
        ui_state["entity_name"].set_text(e.name if e.name else "Unknown")

    elif item_type == "edge":
        clicked_link = links[data_index]
        raw_props = clicked_link.get("props", {})

        ui_state["entity_type_badge"].set_text("RELATIONSHIP")
        edge_val = clicked_link.get("value") or "CONNECTION"
        ui_state["entity_name"].set_text(e.name if e.name else edge_val)

    if not raw_props:
        with ui_state["props_view"]:
            ui.label("// No attributes found.").classes(
                "text-xs font-mono text-neutral-600 italic"
            )
    else:
        with ui_state["props_view"]:
            for k, v in raw_props.items():
                # Encapsulate each key-value pair in a subtle tech card
                with ui.column().classes(
                    "w-full gap-0.5 bg-white/[0.02] p-2.5 rounded border border-white/5 hover:bg-white/[0.04] transition-colors"
                ):

                    # Key on top (muted, uppercase)
                    ui.label(str(k).upper()).classes(
                        "text-[9px] font-mono text-neutral-500 tracking-wider"
                    )

                    # Value underneath (brighter, left-aligned, selectable)
                    ui.label(str(v)).classes(
                        "text-xs font-mono text-neutral-200 break-all select-all"
                    )


def build_chart_options(nodes, links, categories):
    return {
        "backgroundColor": "transparent",
        "tooltip": {
            "trigger": "item",
            "backgroundColor": "#171717",
            "borderColor": "#333333",
            "borderWidth": 1,
            "textStyle": {
                "color": "#e5e5e5",
                "fontFamily": "monospace",
                "fontSize": 12,
            },
            "formatter": "{b}",
        },
        "legend": [
            {
                "data": [c["name"] for c in categories],
                "textStyle": {
                    "color": "#a3a3a3",
                    "fontFamily": "monospace",
                    "fontSize": 11,
                },
                "bottom": 10,
                "icon": "circle",
            }
        ],
        "color": CHART_COLORS,  # these match up with the colors above
        "series": [
            {
                "type": "graph",
                "layout": "force",
                "left": "0%",
                "right": "0%",
                "top": "0%",
                "bottom": "0%",
                "data": nodes,
                "links": links,
                "categories": categories,
                "roam": True,
                "draggable": True,
                "symbolSize": 35,
                "edgeSymbol": ["none", "arrow"],
                "edgeSymbolSize": [0, 8],
                "label": {
                    "show": True,
                    "position": "right",
                    "color": "#a3a3a3",
                    "fontFamily": "monospace",
                    "fontSize": 11,
                    "distance": 8,
                },
                "labelLayout": {"hideOverlap": True},
                "itemStyle": {
                    "borderColor": "#000000",
                    "borderWidth": 2,
                },
                "lineStyle": {
                    "color": "#52525b",
                    "curveness": 0.15,
                    "opacity": 0.8,
                    "width": 2,
                },
                "emphasis": {
                    "focus": "adjacency",
                    "lineStyle": {
                        "width": 4,
                        "color": "#10b981",
                        "opacity": 1,
                    },
                    "itemStyle": {
                        "borderColor": "#10b981",
                        "borderWidth": 3,
                    },
                    "label": {"color": "#ffffff", "fontWeight": "bold"},
                },
                "force": {
                    "repulsion": 2500,
                    "edgeLength": [30, 70],
                    "friction": 0.4,
                    "gravity": 0.15,
                },
            }
        ],
        "animationDuration": 250,
        "animationEasingUpdate": "quinticInOut",
    }


# hack to allow for a "background" around the svg images so you can click anywhere on them, not just on drawn lines
def wrap_svg(path_d, color):
    svg_string = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="48" height="48">
        <circle cx="12" cy="12" r="11" fill="#0f0f0f" stroke="{color}" stroke-width="0.5" />
        <path d="{path_d}" fill="{color}" />
    </svg>"""
    return "image://data:image/svg+xml;charset=UTF-8," + urllib.parse.quote(svg_string)


# def set_node_icons(nodes):
#     for node in nodes:
#         # ex:
#         # {'category': 0, 'id': '2841', 'name': 'DESKTOP-MOCK20', 'props': {'arch': 'x64', 'external_ip': '198.51.100.71', 'implant_uuid': 'f365dc18-f1f2-4dee-ae7c-711bda97a9bb', 'internal_ip': '10.0.2.100', 'pid': '21746', 'process': 'C:\\Windows\\System32\\cmd.exe', 'system_hostname': 'DESKTOP-MOCK20', 'user': 'test_user_20'}}
#         # Prevent NiceGUI EChartPointClickEventArguments KeyError
#         node.setdefault("value", 0)

#         cat = node.get("category", 0)
#         # color = CHART_COLORS[cat] if cat < len(CHART_COLORS) else "#a3a3a3"

#         if cat == 0:  # Implant
#             user = node.get("props", {}).get("user", "").lower()

#             # Check for system, admin, or any other high-priv string.
#             is_admin = "system" in user
#             color = "#ef4444" if is_admin else "#10b981"

#             node["symbol"] = wrap_svg(PATH_IMPLANT, color)
#             node["symbolSize"] = 35

#         elif cat == 1:  # Network
#             node["symbol"] = wrap_svg(PATH_NETWORK, "#3b82f6")
#             node["symbolSize"] = 45
#         elif cat == 2:  # Gateway
#             node["symbol"] = wrap_svg(PATH_GATEWAY, "#a855f7")
#             node["symbolSize"] = 55
#         elif cat == 3:  # Host
#             node["symbol"] = wrap_svg(PATH_HOST, "#d3eb00")
#             node["symbolSize"] = 55
#         else:
#             node["symbol"] = "circle"
#             node["symbolSize"] = 25

#     return nodes


def set_node_icons(nodes):
    for node in nodes:
        # Prevent NiceGUI EChartPointClickEventArguments KeyError
        node.setdefault("value", 0)

        props = node.get("props", {})

        # 1. Dynamically determine the true category based on properties
        if "implant_uuid" in props:
            cat = 0  # Implant
        elif "cidr" in props:
            cat = 1  # Network
        elif "host" in props or "external_exposed" in props:
            cat = 2  # Gateway
        elif "address" in props:
            cat = 3  # Host
        else:
            cat = node.get("category", 3)  # Fallback

        # 2. Overwrite the backend's broken category ID so ECharts maps it correctly
        node["category"] = cat

        # 3. Assign Icons and Colors
        if cat == 0:  # Implant
            user = props.get("user", "").lower()
            is_admin = "system" in user
            color = "#ef4444" if is_admin else CHART_COLORS[0]

            node["symbol"] = wrap_svg(PATH_IMPLANT, color)
            node["symbolSize"] = 35

        elif cat == 1:  # Network
            node["symbol"] = wrap_svg(PATH_NETWORK, CHART_COLORS[1])
            node["symbolSize"] = 45

        elif cat == 2:  # Gateway
            node["symbol"] = wrap_svg(PATH_GATEWAY, CHART_COLORS[2])
            node["symbolSize"] = 55

        elif cat == 3:  # Host
            node["symbol"] = wrap_svg(PATH_HOST, CHART_COLORS[3])
            node["symbolSize"] = 35

    return nodes
