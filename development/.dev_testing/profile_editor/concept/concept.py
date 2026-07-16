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

last_extract = {"data": {}}

transforms = {
    "append":{"desc":"Append literal bytes after the data", "input":True},
    "prepend":{"desc":"Prepend literal bytes before the data", "input":True},
    "base64":{"desc":"URL-safe Base64 (no padding)", "input":False},
    "base64url":{"desc":"Standard Base64 encode/decode", "input":False},
    "netbios":{"desc":"NetBIOS encoding (lowercase a-p)", "input":False},
    "netbiosu":{"desc":"NetBIOS encoding (uppercase A-P)", "input":False},
    "symcrypt":{"desc":"AES-256-GCM symmetric encryption", "input":True}
}

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
                        expansion_name = ui.label("transform_example")

                # list of all transforms:
                key_list = list(transforms.keys())

                # add new attribtue to each object to track the operation, and value of each transform. 
                # this allows us to access them later with parent object
                expansion.transform_op = ui.select(key_list, value="append", on_change=lambda: on_change_handler())
                
                target_transform = transforms.get(expansion.transform_op.value,{})
                expansion.transform_val = ui.input("Value")

                # store label object as well for updates to desc.
                expansion.transform_desc = ui.label(target_transform.get("desc",""))

                ui.button("delete transform", on_click=lambda: expansion.delete())
        
        def on_change_handler():
            # update expansion name to current transform
            expansion_name.set_text(expansion.transform_op.value)

            # look up the *current* selection each time, not the stale initial capture
            current_transform = transforms.get(expansion.transform_op.value, {})
            needs_input = current_transform.get("input", False)

            expansion.transform_val.set_visibility(needs_input)
            if not needs_input:
                expansion.transform_val.set_value("")

            # add in desc to label object.
            expansion.transform_desc.set_text(current_transform.get("desc",""))

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
    #placeholdr add to global result dict for gui purposes
    last_extract["data"] = result
    render_box.refresh()


@ui.refreshable
def render_box():
    ''''''
    with ui.column().classes("w-full h-full outline"):
        ui.label("render preview")
        ui.code(content=str(last_extract.get("data", {})), language="json").classes("w-full")

ui.run()

