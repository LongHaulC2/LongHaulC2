import urllib.parse
from datetime import UTC, datetime

import structlog
from nicegui import ui

# Imports
from client.src.client.modules.api_calls import get_all_graph_data
from client.src.client.pages.footer import build_footer
from client.src.client.pages.menu import setup_menu

server_log = structlog.getLogger("server")

# SVG's just stored here because I'm lazy
PATH_NETWORK = "M3 12H21M12 8V12M6.5 12V16M17.5 12V16M10.1 8H13.9C14.4601 8 14.7401 8 14.954 7.89101C15.1422 7.79513 15.2951 7.64215 15.391 7.45399C15.5 7.24008 15.5 6.96005 15.5 6.4V4.6C15.5 4.03995 15.5 3.75992 15.391 3.54601C15.2951 3.35785 15.1422 3.20487 14.954 3.10899C14.7401 3 14.4601 3 13.9 3H10.1C9.53995 3 9.25992 3 9.04601 3.10899C8.85785 3.20487 8.70487 3.35785 8.60899 3.54601C8.5 3.75992 8.5 4.03995 8.5 4.6V6.4C8.5 6.96005 8.5 7.24008 8.60899 7.45399C8.70487 7.64215 8.85785 7.79513 9.04601 7.89101C9.25992 8 9.53995 8 10.1 8ZM15.6 21H19.4C19.9601 21 20.2401 21 20.454 20.891C20.6422 20.7951 20.7951 20.6422 20.891 20.454C21 20.2401 21 19.9601 21 19.4V17.6C21 17.0399 21 16.7599 20.891 16.546C20.7951 16.3578 20.6422 16.2049 20.454 16.109C20.2401 16 19.9601 16 19.4 16H15.6C15.0399 16 14.7599 16 14.546 16.109C14.3578 16.2049 14.2049 16.3578 14.109 16.546C14 16.7599 14 17.0399 14 17.6V19.4C14 19.9601 14 20.2401 14.109 20.454C14.2049 20.6422 14.3578 20.7951 14.546 20.891C14.7599 21 15.0399 21 15.6 21ZM4.6 21H8.4C8.96005 21 9.24008 21 9.45399 20.891C9.64215 20.7951 9.79513 20.6422 9.89101 20.454C10 20.2401 10 19.9601 10 19.4V17.6C10 17.0399 10 16.7599 9.89101 16.546C9.79513 16.3578 9.64215 16.2049 9.45399 16.109C9.24008 16 8.96005 16 8.4 16H4.6C4.03995 16 3.75992 16 3.54601 16.109C3.35785 16.2049 3.20487 16.3578 3.10899 16.546C3 16.7599 3 17.0399 3 17.6V19.4C3 19.9601 3 20.2401 3.10899 20.454C3.20487 20.6422 3.35785 20.7951 3.54601 20.891C3.75992 21 4.03995 21 4.6 21Z"  # noqa: E501 - SVG image
PATH_USER = "M12,4A4,4 0 0,1 16,8A4,4 0 0,1 12,12A4,4 0 0,1 8,8A4,4 0 0,1 12,4M12,14C16.42,14 20,15.79 20,18V20H4V18C4,15.79 7.58,14 12,14Z"  # noqa: E501 - SVG image
PATH_HOST = "M20,19V7H4V19H20M20,3A2,2 0 0,1 22,5V19A2,2 0 0,1 20,21H4A2,2 0 0,1 2,19V5C2,3.89 2.9,3 4,3H20M13,17V15H18V17H13M9.58,13L5.57,9H8.4L11.7,12.3C12.09,12.69 12.09,13.33 11.7,13.72L8.42,17H5.59L9.58,13Z"  # noqa: E501 - SVG image
PATH_GATEWAY = "M9.5 20H6.2C5.0799 20 4.51984 20 4.09202 19.782C3.71569 19.5903 3.40973 19.2843 3.21799 18.908C3 18.4802 3 17.9201 3 16.8V7.2C3 6.0799 3 5.51984 3.21799 5.09202C3.40973 4.71569 3.71569 4.40973 4.09202 4.21799C4.51984 4 5.0799 4 6.2 4H15.8C16.9201 4 17.4802 4 17.908 4.21799C18.2843 4.40973 18.5903 4.71569 18.782 5.09202C19 5.51984 19 6.0799 19 7.2V8H3M3 12H11V8M3 16H9M7 4V8M7 12V16M15 4V8M19.8284 19.8284C18.2663 21.3905 15.7337 21.3905 14.1716 19.8284C13.3905 19.0474 13 18.0237 13 17C13 15.9763 13.3905 14.9526 14.1716 14.1716C14.1716 14.1716 14.5 15 15.5 15.5C15.5 14.5 15.75 13 16.9929 12C18 13 19.0456 13.3887 19.8284 14.1716C20.6095 14.9526 21 15.9763 21 17C21 18.0237 20.6095 19.0474 19.8284 19.8284Z"  # noqa: E501 - SVG image
PATH_IMPLANT = (
    "M7 14.3333C7 13.0872 7 12.4641 7.26795 12C7.44349 11.696 7.69596 11.4435 8 11.2679C8.4641 11 9.08718 11 10.3333 11H13.6667C14.9128 11 15.5359 11 16 11.2679C16.304 11.4435 16.5565 11.696 16.7321 12C17 12.4641 17 13.0872 17 14.3333V16C17 16.9293 17 17.394 16.9231 17.7804C16.6075 19.3671 15.3671 20.6075 13.7804 20.9231C13.394 21 12.9293 21 12 21V21C11.0707 21 10.606 21 10.2196 20.9231C8.63288 20.6075 7.39249 19.3671 7.07686 17.7804C7 17.394 7 16.9293 7 16V14.3333Z "  # noqa: E501 - SVG image
    "M9 9C9 8.06812 9 7.60218 9.15224 7.23463C9.35523 6.74458 9.74458 6.35523 10.2346 6.15224C10.6022 6 11.0681 6 12 6V6C12.9319 6 13.3978 6 13.7654 6.15224C14.2554 6.35523 14.6448 6.74458 14.8478 7.23463C15 7.60218 15 8.06812 15 9V11H9V9Z "  # noqa: E501 - SVG image
    "M12 11V15 M15 3L13 6 M9 3L11 6 M7 16H2 M22 16H17 "
    "M20 9V10C20 11.6569 18.6569 13 17 13V13 "
    "M20 22V22C20 20.3431 18.6569 19 17 19V19 "
    "M4 9V10C4 11.6569 5.34315 13 7 13V13 "
    "M4 22V22C4 20.3431 5.34315 19 7 19V19"
)
PATH_LISTENER = "M3 7C3 4.23858 5.23858 2 8 2C10.7614 2 13 4.23858 13 7V8H10V15H12C13.6569 15 15 13.6569 15 12V7C15 3.13401 11.866 0 8 0C4.13401 0 1 3.13401 1 7V12C1 13.6569 2.34315 15 4 15H6V8H3V7Z"  # noqa: E501 - SVG image
PATH_FILE = "M19 9V17.8C19 18.9201 19 19.4802 18.782 19.908C18.5903 20.2843 18.2843 20.5903 17.908 20.782C17.4802 21 16.9201 21 15.8 21H8.2C7.07989 21 6.51984 21 6.09202 20.782C5.71569 20.5903 5.40973 20.2843 5.21799 19.908C5 19.4802 5 18.9201 5 17.8V6.2C5 5.07989 5 4.51984 5.21799 4.09202C5.40973 3.71569 5.71569 3.40973 6.09202 3.21799C6.51984 3 7.0799 3 8.2 3H13M19 9L13 3M19 9H14C13.4477 9 13 8.55228 13 8V3"  # noqa: E501 - SVG image
PATH_C2_CHANNEL = "M18 5C17.4477 5 17 5.44772 17 6C17 6.27642 17.1108 6.52505 17.2929 6.70711C17.475 6.88917 17.7236 7 18 7C18.5523 7 19 6.55228 19 6C19 5.44772 18.5523 5 18 5ZM15 6C15 4.34315 16.3431 3 18 3C19.6569 3 21 4.34315 21 6C21 7.65685 19.6569 9 18 9C17.5372 9 17.0984 8.8948 16.7068 8.70744L8.70744 16.7068C8.8948 17.0984 9 17.5372 9 18C9 19.6569 7.65685 21 6 21C4.34315 21 3 19.6569 3 18C3 16.3431 4.34315 15 6 15C6.46278 15 6.90157 15.1052 7.29323 15.2926L15.2926 7.29323C15.1052 6.90157 15 6.46278 15 6ZM6 17C5.44772 17 5 17.4477 5 18C5 18.5523 5.44772 19 6 19C6.55228 19 7 18.5523 7 18C7 17.7236 6.88917 17.475 6.70711 17.2929C6.52505 17.1108 6.27642 17 6 17Z"  # noqa: E501 - SVG image

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
    await build_footer()
    await graph_view()


async def graph_view():
    graph_data_response = await get_all_graph_data()
    graph_data = graph_data_response.get("data", {})

    nodes = graph_data.get("nodes", [])
    links = graph_data.get("links", [])
    categories = graph_data.get("categories", [])

    # 1. Define your visual styles per node type
    category_styles = {
        "Neo4jImplantNode": {
            "symbol": wrap_svg(PATH_IMPLANT, "#CF2525"),
            "symbolSize": 45,
            # "itemStyle": {"color": "#ff4d4d"},
        },
        "Neo4jListenerNode": {
            "symbol": wrap_svg(PATH_LISTENER, "#ffcc00"),
            "symbolSize": 40,
            # "itemStyle": {"color": "#ffcc00"},
        },
        "Neo4jHostNode": {
            # Standard SVG path for a server/desktop
            "symbol": wrap_svg(PATH_HOST, "#024FF5"),
            "symbolSize": 35,
            # "itemStyle": {"color": "#4d79ff"},
        },
        "Neo4jNetworkNode": {
            "symbol": wrap_svg(PATH_NETWORK, "#5BE2A3"),
            "symbolSize": 45,  # Width, Height
            # "itemStyle": {"color": "#33cc33"},
        },
        "Neo4jNicNode": {
            "symbol": wrap_svg(PATH_NETWORK, "#22573E"),
            "symbolSize": 45,  # Width, Height
            # "itemStyle": {"color": "#33cc33"},
        },
        "Neo4jC2ChannelNode": {
            "symbol": wrap_svg(PATH_C2_CHANNEL, "#A01DA5"),
            "symbolSize": 45,  # Width, Height
            # "itemStyle": {"color": "#33cc33"},
        },
        "Neo4jFileNode": {
            # You can also use direct web or local image URLs
            "symbol": wrap_svg(PATH_FILE, "#969696"),
            "symbolSize": 30,
        },
        "Neo4jMemstoreFileNode": {
            # You can also use direct web or local image URLs
            "symbol": wrap_svg(PATH_FILE, "#10BB00"),
            "symbolSize": 30,
        },
    }

    # Inject styles into the categories array
    for cat in categories:
        # Default to a gray circle if the label isn't in our map
        style = category_styles.get(cat["name"], {"symbol": "circle", "itemStyle": {"color": "#888888"}})
        cat.update(style)

    for cat in categories:
        old_name = cat["name"]
        new_name = old_name.replace("Neo4j", "").replace("Node", "")
        cat["name"] = new_name  # Updates the legend

    #  Explicitly map categories to specific naming functions
    def get_implant_name(p):
        process = p.get("process", "")
        if process:
            # Slices off the filepath so "C:\...\safe.exe" becomes "safe.exe"
            return process.split("\\")[-1].split("/")[-1]
        # incase there's no process, just return uuid
        return p.get("implant_uuid", "Unknown Implant")[:20]

    def get_file_name(p):
        name = p.get("file_name", "")
        if name:
            return name
        return f"{p.get('file_name', 'Unknown')[:50]}"

    def get_file_path(p):
        name = p.get("file_path", "")
        if name:
            return name
        return f"{p.get('file_name', 'Unknown')[:50]}"

    name_mappers = {
        "Implant": get_implant_name,
        "Listener": lambda p: p.get("name") or p.get("listener_uuid", "Unknown Listener"),
        "Host": lambda p: p.get("hostname") or p.get("system_hostname") or p.get("address", "Unknown Host"),
        "Network": lambda p: p.get("cidr", "Unknown Network"),
        "Nic": lambda p: p.get("ip_address") or p.get("mac_address", "Unknown NIC"),
        "C2Channel": lambda p: f"{p.get('protocol', 'C2').upper()} Channel",
        "File": get_file_path,
        "MemstoreFile": get_file_name,
    }

    # correlate nodes and dynamically assign their mapped names
    for node in nodes:
        # Correlate the nodes category to the newly cleaned legend strings
        old_cat = node.get("category", "")
        new_cat = old_cat.replace("Neo4j", "").replace("Node", "")
        node["category"] = new_cat

        # Look up the specific naming logic for this exact type, fallback to a generic name
        props = node.get("props", {})
        naming_func = name_mappers.get(new_cat, lambda: "Unknown Node")

        # Apply the explicit naming logic to the node
        node["name"] = naming_func(props)

    options = build_chart_options(nodes, links, categories)

    with ui.column().classes("w-full h-full gap-0 tech-glass-panel"):
        # parent bar
        build_header_bar()

        # graph layout
        with ui.row().classes("w-full flex-grow overflow-hidden flex-nowrap"):
            # setup sidebar
            inspector_sidebar = ui.column().classes(
                "w-80 h-full p-4 bg-[#111] border-l border-white/10 overflow-y-auto"
            )
            with inspector_sidebar:
                ui.label("Select a node to view details").classes("text-gray-500 italic")

            # setup graph area
            with ui.column().classes("flex-grow h-full relative p-2"):
                chart = ui.echart(
                    options,
                ).classes("w-full h-full bg-[#0a0a0a] rounded border border-white/5")
                chart.on(
                    "chart:selectchanged",
                    lambda e: handle_click(e, nodes, inspector_sidebar),
                )

                with chart, ui.menu().props("context-menu"):
                    ui.menu_item("Copy")
                    ui.menu_item("Delete")


def build_header_bar():
    with ui.row().classes("w-full items-center justify-between tech-header-bar"):
        with ui.row().classes("items-center gap-3"):
            ui.icon("device_hub", color="emerald-500").classes("text-xl")
            ui.label("NETWORK_TOPOLOGY //").classes("tech-label-title")

        with ui.row().classes("items-center gap-2"):
            ui.label(
                # just hour minute sec is way easier to read than hour:min:sec:subsec
                f"Last Refresh [UTC]: {datetime.now(UTC).strftime('%H:%M:%S')}"
            ).classes("tech-label-title")
            ui.button(icon="refresh", on_click=lambda: ui.navigate.to("/graph")).props("dense flat size=sm").classes(
                "tech-btn-ghost"
            ).tooltip("Refresh Topology")


def handle_click(e, nodes, sidebar_container):
    # Dig into the payload to find which index was selected
    payload = e.args.get("fromActionPayload", {})
    data_index = payload.get("dataIndexInside")

    if data_index is None:
        return

    # Grab the actual node object using the index
    selected_node = nodes[data_index]
    props = selected_node.get("props", {})
    node_name = selected_node.get("name", "Unknown")
    node_type = selected_node.get("category")

    # Clear and Redraw the sidebar
    sidebar_container.clear()
    with sidebar_container:
        ui.label(f"DETAILS: {node_name}").classes("text-emerald-500 font-bold mb-2")
        ui.separator().classes("bg-white/10 mb-4")

        # Loop through props and make a clean key-value list
        with ui.column().classes("gap-1"):
            for key, val in props.items():
                with ui.row().classes("w-full justify-between border-b border-white/5 pb-1"):
                    ui.label(key).classes("text-gray-500 text-xs uppercase")
                    ui.label(str(val)).classes("text-gray-200 text-xs text-right break-all")

        # note, need to pull notes as well for implants/listeners
        ui.separator()
        ui.label("notes placeholder")

        # update options here would be nice as well
        ui.separator()

        if node_type == "Implant":
            with ui.column().classes("w-full"):
                ui.button("Implant Page").classes("w-full")
                ui.button("Implant ...").classes("w-full")

        elif node_type == "Host":
            with ui.column().classes("w-full"):
                ui.button("Host Page").classes("w-full")
                ui.button("something else").classes("w-full")

        elif node_type == "Listener":
            with ui.column().classes("w-full"):
                ui.button("Restart").classes("w-full")
                ui.button("Stop", color="red").classes("w-full")

        elif node_type == "File" or node_type == "MemstoreFile":
            with ui.column().classes("w-full"):
                ui.button("Download").classes("w-full")
                ui.button("Delete", color="red").classes("w-full")
        else:
            ui.label("No actions for this type of node")


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
            # Shows Node Name and any props to highlihgt
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
        "series": [
            {
                "type": "graph",
                "layout": "force",
                "data": nodes,
                "links": links,
                "categories": categories,
                "roam": True,
                "draggable": True,
                "edgeSymbol": ["none", "arrow"],
                "edgeSymbolSize": [0, 8],
                "edgeLabel": {
                    "show": True,
                    "formatter": "{c}",  # '{c}' tells ECharts to use the 'value' of the link
                    "fontSize": 10,
                    "color": "#71717a",  # Subtle gray so it's not distracting
                    "fontFamily": "monospace",
                },
                "label": {
                    "show": True,
                    "position": "right",
                    "color": "#a3a3a3",
                    "fontFamily": "monospace",
                    "fontSize": 10,
                },
                "lineStyle": {
                    "color": "#52525b",
                    "curveness": 0.05,  # Curves help see bi-directional links
                    "width": 1.5,
                    "type": "dashed",
                },
                "force": {
                    # low grav + lowish repulsion allows them to spread, but not too far
                    "repulsion": 500,  # Lower = nodes gather closer
                    "gravity": 0.01,  # Higher = pulls clusters to center
                    "edgeLength": 80,  # Constant length helps stability
                    "friction": 0.3,
                    # "initLayout": "circular", # sets init layout to be circular. can be that or null/none
                },
                "emphasis": {
                    "focus": "adjacency",
                    "lineStyle": {"width": 3, "color": "#10b981"},
                },
            }
        ],
        "animationDuration": 1500,  # Longer intro animation looks smoother
        "animationEasingUpdate": "quinticInOut",
    }


# hack to allow for a "background" around the svg images so you can click anywhere on them, not just on drawn lines
def wrap_svg(path_d, color):
    """
    Wraps SVG in html that allows it to be clicked where the SVG is not drawn. It places a shape *under* the image,
    then draws svg on top
    """
    # fill="#0f0f0f"
    svg_string = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="48" height="48">
        <circle cx="12" cy="12" r="11" stroke="{color}" stroke-width="0" />
        <path d="{path_d}" fill="{color}" />
    </svg>"""
    return "image://data:image/svg+xml;charset=UTF-8," + urllib.parse.quote(svg_string)


# def set_node_icons(nodes, categories):
#     for node in nodes:
#         # Prevent NiceGUI EChartPointClickEventArguments KeyError
#         node.setdefault("value", 0)
#         props = node.get("props", {})

#         # # Dynamically determine the true category based on properties
#         # use the prim keys for this
#         if "implant_uuid" in props:
#             cat = 0  # Implant
#         elif "listener_uuid" in props:
#             cat = 1  # Listener
#         elif "channel_id" in props:
#             cat = 2  # c2 channel
#         elif "address" in props:
#             cat = 3  # Host
#         else:
#             cat = node.get("category", 3)  # Fallback

#         # Overwrite the backend's broken category ID so ECharts maps it correctly
#         # node["category"] = cat

#         # get index of category, according to the nodes field
#         cat_index = node.get("category")

#         # for _cat in categories:
#         #     if cat_index == _cat.get("index"):

#         # take nodes, correlate them, and add props to them.
#         if cat_index == 0:  # Implant
#             user = props.get("user", "").lower()
#             is_admin = "system" in user
#             color = "#ef4444" if is_admin else CHART_COLORS[0]

#             node["symbol"] = wrap_svg(PATH_IMPLANT, color)
#             node["symbolSize"] = 35

#         elif cat_index == 1:  # Network
#             node["symbol"] = wrap_svg(PATH_NETWORK, CHART_COLORS[1])
#             node["symbolSize"] = 45

#         elif cat_index == 2:  # Gateway
#             node["symbol"] = wrap_svg(PATH_GATEWAY, CHART_COLORS[2])
#             node["symbolSize"] = 55

#         elif cat_index == 3:  # Host
#             node["symbol"] = wrap_svg(PATH_HOST, CHART_COLORS[3])
#             node["symbolSize"] = 35

#     return nodes
