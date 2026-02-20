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
PATH_IMPLANT = "M20,19V7H4V19H20M20,3A2,2 0 0,1 22,5V19A2,2 0 0,1 20,21H4A2,2 0 0,1 2,19V5C2,3.89 2.9,3 4,3H20M13,17V15H18V17H13M9.58,13L5.57,9H8.4L11.7,12.3C12.09,12.69 12.09,13.33 11.7,13.72L8.42,17H5.59L9.58,13Z"
PATH_GATEWAY = "M9.5 20H6.2C5.0799 20 4.51984 20 4.09202 19.782C3.71569 19.5903 3.40973 19.2843 3.21799 18.908C3 18.4802 3 17.9201 3 16.8V7.2C3 6.0799 3 5.51984 3.21799 5.09202C3.40973 4.71569 3.71569 4.40973 4.09202 4.21799C4.51984 4 5.0799 4 6.2 4H15.8C16.9201 4 17.4802 4 17.908 4.21799C18.2843 4.40973 18.5903 4.71569 18.782 5.09202C19 5.51984 19 6.0799 19 7.2V8H3M3 12H11V8M3 16H9M7 4V8M7 12V16M15 4V8M19.8284 19.8284C18.2663 21.3905 15.7337 21.3905 14.1716 19.8284C13.3905 19.0474 13 18.0237 13 17C13 15.9763 13.3905 14.9526 14.1716 14.1716C14.1716 14.1716 14.5 15 15.5 15.5C15.5 14.5 15.75 13 16.9929 12C18 13 19.0456 13.3887 19.8284 14.1716C20.6095 14.9526 21 15.9763 21 17C21 18.0237 20.6095 19.0474 19.8284 19.8284Z"
CHART_COLORS = [
    "#10b981",
    "#3b82f6",
    "#a855f7",
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
    categories = [
        {"name": "Implant"},  # Index 0
        {"name": "Network"},  # Index 1
        {"name": "Gateway"},  # Index 2
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


def set_node_icons(nodes):
    for node in nodes:
        # ex:
        # {'category': 0, 'id': '2841', 'name': 'DESKTOP-MOCK20', 'props': {'arch': 'x64', 'external_ip': '198.51.100.71', 'implant_uuid': 'f365dc18-f1f2-4dee-ae7c-711bda97a9bb', 'internal_ip': '10.0.2.100', 'pid': '21746', 'process': 'C:\\Windows\\System32\\cmd.exe', 'system_hostname': 'DESKTOP-MOCK20', 'user': 'test_user_20'}}
        # Prevent NiceGUI EChartPointClickEventArguments KeyError
        node.setdefault("value", 0)

        cat = node.get("category", 0)
        # color = CHART_COLORS[cat] if cat < len(CHART_COLORS) else "#a3a3a3"

        if cat == 0:  # Implant
            user = node.get("props", {}).get("user", "").lower()

            # Check for system, admin, or any other high-priv string.
            is_admin = "system" in user
            color = "#ef4444" if is_admin else "#10b981"

            node["symbol"] = wrap_svg(PATH_IMPLANT, color)
            node["symbolSize"] = 35

        elif cat == 1:  # Network
            node["symbol"] = wrap_svg(PATH_NETWORK, "#3b82f6")
            node["symbolSize"] = 45
        elif cat == 2:  # Gateway
            node["symbol"] = wrap_svg(PATH_GATEWAY, "#a855f7")
            node["symbolSize"] = 55
        else:
            node["symbol"] = "circle"
            node["symbolSize"] = 25

    return nodes
