from nicegui import ui


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



def transform_parent():
    """parent element to hodl all  transform  sub elements"""
    with ui.tabs().classes('w-full') as tabs:
        get = ui.tab('GET')
        post = ui.tab('POST')
        options = ui.tab('OPTIONS')

    with ui.tab_panels(tabs, value=get).classes('w-full'):
        with ui.tab_panel(get):
            transform_box("GET")
        with ui.tab_panel(post):
            transform_box("POST")

def transform_box(transform_chain_name:str="GET"):
    '''
    flexible element for transforms. 
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

                transform_option = ui.select(["Append", "Prepend", "..."], value="Append")
                # delete itself -> turn into a dedicated func to delete the element AND the dict entry
                ui.button("delete transform", on_click=lambda: expansion.delete())

def render_box():
    ''''''
    with ui.column().classes("w-full h-full outline"):
        ui.label("left")

ui.run()

