from nicegui import ui

'''
Data notes:

A dict that is bound/updated with the gui is a good idea for tracking transforms.

I.e.:

[
{"transform":"append", args:{"text":"ABCDEFG"}},
{"transform":"append", args:{"text":"ABCDEFG"}},

]
Bonus, making it ordered would be sweet. 

This can either be done by:
1. Adding an "order"/index field to it
2. Using ORderedDict.

it is important we can either then 
1. reorder inline,
2. re-create the dict on the fly based on current order/on order change

Note: reorder on fly is likely the simplest implementation path, at the cost of re-computing every change. 

'''

@ui.page("/")
def page():
    '''
    page
    '''
    with ui.splitter().classes("w-full h-screen outline") as splitter:
        with splitter.before:
            with ui.scroll_area().classes("h-full outline"):
                transform_parent()
        with splitter.after:
            with ui.scroll_area().classes("h-full outline"):
                render_box()


# card references keyed by (chain, sub_chain) e.g. ("GET", "req")
# the card's children ARE the ordered transforms — no separate list needed
transform_cards = {}

def transform_parent():
    """parent element to hold all  transform  sub elements.
    
    
    Contains logic for GET, POST, and OPTIONS
    """
    with ui.tabs().classes('w-full').props("dense") as tabs:
        get = ui.tab('GET')
        post = ui.tab('POST')
        options = ui.tab('OPTIONS')

    with ui.tab_panels(tabs, value=get).classes('w-full outline'):
        with ui.tab_panel(get).classes():
            transform_split("GET")
        with ui.tab_panel(post):
            transform_split("POST")

    ui.button("debug print dicts", on_click=lambda:extract_chain())

def transform_split(transform_chain_name:str="GET"):
    """Split elements between the REQ and RESP for GET/POST

    """
    with ui.tabs().classes('w-full').props("dense") as tabs:
        metadata = ui.tab('REQ (to server)')
        response = ui.tab('RESP (from server)')

    with ui.tab_panels(tabs, value=metadata).classes('w-full'):
        with ui.tab_panel(metadata):
            transform_box(transform_chain_name, "req")
        with ui.tab_panel(response):
            transform_box(transform_chain_name, "resp")

def transform_box(transform_chain_name:str="GET", sub_chain:str="req"):
    '''
    The actual transform box, with the add transform button.

    flexible element for transform chains.
    '''
    with ui.column().classes("w-full h-full outline"):
        ui.button(f"Add {transform_chain_name} Transform", on_click=lambda: new_transform()).classes("w-full")

    card = ui.card().classes("w-full outline")
    card.make_sortable(handle=".drag-handle")

    # register this card so extract_chain() can find it by (chain, sub_chain)
    # i.e. GET, REQ, or POST, RESP
    transform_cards[(transform_chain_name, sub_chain)] = card

    def new_transform():
        #expansionin the card for draggaibility
        with card:
            with ui.expansion(text="transform_example").classes("w-full") as expansion:
                # Adding just the drag icon breaks text, so we are doing a row with icon and text
                with expansion.add_slot("header"):
                    with ui.row().classes("items-center gap-2 w-full"):
                        ui.icon("drag_indicator").classes(
                            "drag-handle cursor-grab active:cursor-grabbing"
                        )
                        ui.label("transform_example")

                # add new attribtue to each object to track the operation, and value of each transform. 
                # this allows us to access them later with parent object
                expansion.transform_op = ui.select(["Append", "Prepend", "..."], value="Append")
                expansion.transform_val = ui.input("Value")

                ui.button("delete transform", on_click=lambda: expansion.delete())

def extract_chain():
    '''
    Extract GUI data -> profile.
    Reads current drag order straight from each card's children.
    '''
    result = {}
    for (transform_chain_name, sub_chain), card in transform_cards.items():
        transforms = []
        # grab each transform, in order, from the card element, 
        # pull out the transform, and add to dict.  
        for child in card.default_slot.children:
            transforms.append({
                "op": child.transform_op.value,
                "val": child.transform_val.value,
            })
        result.setdefault(transform_chain_name, {})[sub_chain] = {"transforms": transforms}

    print(result)


def render_box():
    ''''''
    with ui.column().classes("w-full h-full outline"):
        ui.label("render preview")

ui.run()

