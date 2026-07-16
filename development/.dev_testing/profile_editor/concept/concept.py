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


# data elements
transforms_dict = {
    "GET":{
        "req": {
            "body":"", # body that metadata goes into
            "transforms":[] # list of transforms. Ex, {"op":"append", value:"xyz"}
        },
        "resp": {
            "body":"",
            "transforms":[]  
        }
    },
    "POST":{
        "req": {
            "body":"",
            "transforms":[]
        },
        "resp": {
            "body":"",
            "transforms":[]
        }
    }
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
            transform_box(transform_chain_name)
        with ui.tab_panel(response):
            transform_box(transform_chain_name)

def transform_box(transform_chain_name:str="GET"):
    '''
    The actual transform box, with the add transform button.

    flexible element for transform chains.  
    '''
    with ui.column().classes("w-full h-full outline"):
        ui.button(f"Add {transform_chain_name} Transform", on_click=lambda: new_transform()).classes("w-full")



    transform_box = ui.card().classes("w-full outline")
    #https://nicegui.io/documentation/sortable
    transform_box.make_sortable(handle=".drag-handle")  # <- call this ONCE, on the parent

    def new_transform():
        # note, not doing the normal/docs example header for draggable, as that conflicts with 
        # the expansion header, so we are putting a row in the header, THEN an icon and label
        with transform_box:
            with ui.expansion(text="transform_example").classes("w-full") as expansion:
                with expansion.add_slot("header"):
                    with ui.row().classes("items-center gap-2 w-full"):
                        ui.icon("drag_indicator").classes(
                            "drag-handle cursor-grab active:cursor-grabbing"
                        )
                        ui.label("transform_example")

                # !! Important, storing each sub element as an element of the expansion. This way, we can access the element's sub elements
                # reliably
                expansion.transform_op = ui.select(["Append", "Prepend", "..."], value="Append")
                expansion.transform_val = ui.input("Value")

                # delete itself -> turn into a dedicated func to delete the element AND the dict entry
                ui.button("delete transform", on_click=lambda: expansion.delete())

                # holding as an object instead of dict, so at render, we can access object names
                list_of_transforms = transforms_dict.get(transform_chain_name,{}).get("req",{}).get("transforms",{})
                list_of_transforms.append(expansion)
                #print(list_of_transforms)

                # bingo, this now holds the transform op, and the val. 
                # Note, clear previous lists before firing this, to get a fresh order, otherwise it can be stale. 
                # temporarily here for debugging, needs to get triggered ONLY when bake button is hit. 
                #for i in list_of_transforms:
                    #print(i.text)
                    #print(i.transform_op.value) # value holds name of transform. Auto updates value, does not auto update order. Hence why we'd have to clear 
                    # the previous list and bake each time. 
                    #print(i.transform_val.value)

def extract_chain():
    '''
    Extract GUI data -> profile
    '''

    ...

    # !! CLEAR PREV DICTS FIRST??? TLDR need to make sure that on reorder, a new list is created.
    # if we clear, then they won't have the data we need. maybe just pass in the current version of the dict on extract chain?

    # list_of_get_req_transforms = transforms_dict.get("GET",{}).get("req",{}).get("transforms",{})
    # for i in list_of_get_req_transforms:
    #     print(i.text)
    #     print(i.transform_op.value)
    #     print(i.transform_val.value)

    # for child in transform_box.default_slot.children:
    #     print(child.transform_op.value)
    #     print(child.transform_val.value)

    # go over each transform set of objects, add in to gui. 


def render_box():
    ''''''
    with ui.column().classes("w-full h-full outline"):
        #ui.label("right")
        ui.code(str(transforms_dict))

ui.run()

