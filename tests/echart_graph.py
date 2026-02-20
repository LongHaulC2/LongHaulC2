from nicegui import ui

# 1. Define the graph data (Mimicking a Neo4j Cypher response)
nodes = [
    {"id": "0", "name": "Ryan", "category": 0, "symbolSize": 60},
    {"id": "1", "name": "Python", "category": 1, "symbolSize": 40},
    {"id": "2", "name": "NiceGUI", "category": 1, "symbolSize": 40},
    {"id": "3", "name": "Neo4j", "category": 2, "symbolSize": 50},
]

links = [
    {"source": "0", "target": "1", "value": "CODES_IN"},
    {"source": "0", "target": "3", "value": "QUERIES"},
    {"source": "1", "target": "2", "value": "USES_FRAMEWORK"},
    {"source": "2", "target": "3", "value": "CONNECTS_TO"},
]

categories = [{"name": "User"}, {"name": "Language/Framework"}, {"name": "Database"}]

# 2. Configure the EChart options
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

# 3. Render the chart
chart = ui.echart(options).classes("w-full h-[600px]")


# 4. Handle Interactions
def handle_click(e):
    # e.args contains all the data about the node or edge clicked
    item_type = e.args.get("dataType")  # 'node' or 'edge'
    name = e.args.get("name")
    ui.notify(f"Left clicked {item_type}: {name}", color="info")


def handle_right_click(e):
    # This triggers on right-click
    item_type = e.args.get("dataType")
    name = e.args.get("name")
    ui.notify(f"Action Menu opened for: {name}", color="warning")

    # NOTE: You could open a ui.dialog() or ui.context_menu() here
    # based on the node data to mimic Neo4j's exact behavior.


chart.on("click", handle_click)
chart.on("contextmenu", handle_right_click)

# Prevent the default browser right-click menu from covering your UI
ui.add_head_html("<style>.nicegui-echart { align-content: center; }</style>")
ui.run(dark=True)

## thereis some really cool stuff you can do with this:
# graph (it's a bit bouncy):https://echarts.apache.org/examples/en/editor.html?c=graph-webkit-dep
# world map graph: https://echarts.apache.org/examples/en/editor.html?c=geo-graph
